"""Application state machine: IDLE -> ACTIVE -> OVERTIME -> QUEUE ADVANCE."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable

from .config import AppConfig, threshold_for
from .storage import OvertimeStatus, PassRecord, PassType, Storage, calculate_overtime


class State(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    OVERTIME = "OVERTIME"


@dataclass
class QueuedStudent:
    name: str
    pass_type: PassType
    photo_out_path: str = ""
    queued_at: datetime = None  # type: ignore
    block_id: str = ""

    def __post_init__(self):
        if self.queued_at is None:
            self.queued_at = datetime.now()


@dataclass
class ActivePass:
    student_name: str
    block_id: str
    pass_type: PassType
    time_out: datetime
    photo_out_path: str
    elapsed_seconds: int = 0
    muted: bool = False


class PassStateMachine:
    """Pure logic; UI binds via callbacks.

    Flow:
      idle --select(name, pass_type)--> active (photo out)
      active --tick--> overtime when elapsed > threshold (alarm loops)
      active/overtime --return_pass(photo_in)--> log + queue check
        if queue >0: pop next, TTS, restart active
        else: idle
      idle/active/overtime --enqueue(name, pass_type)--> queue
    """

    def __init__(self, cfg: AppConfig, storage: Storage, block_id_provider: Callable[[], str]):
        self.cfg = cfg
        self.storage = storage
        self.block_id_provider = block_id_provider
        self.state: State = State.IDLE
        self.active: ActivePass | None = None
        self.queue: deque[QueuedStudent] = deque()
        # Callbacks for UI
        self.on_tts: Callable[[str], None] | None = None
        self.on_alarm_start: Callable[[], None] | None = None
        self.on_alarm_stop: Callable[[], None] | None = None
        self.on_state_changed: Callable[[State], None] | None = None

    def _set_state(self, s: State) -> None:
        self.state = s
        if self.on_state_changed:
            self.on_state_changed(s)

    def current_block(self) -> str:
        return self.block_id_provider()

    def select_student(self, name: str, pass_type: PassType, photo_out_path: str) -> bool:
        if self.state != State.IDLE:
            return False
        if not name:
            return False
        self.active = ActivePass(
            student_name=name,
            block_id=self.current_block(),
            pass_type=pass_type,
            time_out=datetime.now(),
            photo_out_path=photo_out_path,
        )
        self._set_state(State.ACTIVE)
        return True

    def enqueue(self, name: str, pass_type: PassType, photo_out_path: str = "") -> bool:
        if not name:
            return False
        lower = {q.name.lower() for q in self.queue}
        if name.lower() in lower:
            return False
        if self.active and self.active.student_name.lower() == name.lower():
            return False
        self.queue.append(QueuedStudent(name=name, pass_type=pass_type, photo_out_path=photo_out_path, queued_at=datetime.now(), block_id=self.current_block()))
        return True

    def dequeue(self, name: str) -> bool:
        for i, q in enumerate(self.queue):
            if q.name.lower() == name.lower():
                del self.queue[i]
                return True
        return False

    def cancel_queued(self, name: str) -> bool:
        for i, q in enumerate(self.queue):
            if q.name.lower() == name.lower():
                cancelled = self.queue[i]
                del self.queue[i]
                try:
                    rec = PassRecord(
                        student_name=cancelled.name,
                        block_id=cancelled.block_id or self.current_block(),
                        pass_type=cancelled.pass_type,
                        time_out=cancelled.queued_at,
                        time_in=datetime.now(),
                        duration_minutes=0.0,
                        overtime_status=OvertimeStatus.CANCELLED,
                        photo_out_path=cancelled.photo_out_path or "",
                        photo_in_path="",
                    )
                    self.storage.append_log(rec)
                except Exception:
                    pass
                return True
        return False

    def tick(self, elapsed_seconds: int) -> None:
        if not self.active:
            return
        self.active.elapsed_seconds = elapsed_seconds
        if self.state == State.ACTIVE:
            thresh = threshold_for(self.active.pass_type.value, self.cfg)
            if elapsed_seconds > thresh:
                self._set_state(State.OVERTIME)
                if not self.active.muted and self.on_alarm_start:
                    self.on_alarm_start()

    def mute_alarm(self) -> None:
        if self.active:
            self.active.muted = True
        if self.on_alarm_stop:
            self.on_alarm_stop()

    def return_pass(self, photo_in_path: str) -> PassRecord | None:
        if not self.active:
            return None
        time_in = datetime.now()
        duration_s = (time_in - self.active.time_out).total_seconds()
        duration_m = duration_s / 60.0
        overtime = calculate_overtime(
            duration_s, self.active.pass_type, self.cfg.bathroom_threshold_seconds, self.cfg.water_threshold_seconds
        )
        record = PassRecord(
            student_name=self.active.student_name,
            block_id=self.active.block_id,
            pass_type=self.active.pass_type,
            time_out=self.active.time_out,
            time_in=time_in,
            duration_minutes=round(duration_m, 2),
            overtime_status=overtime,
            photo_out_path=self.active.photo_out_path,
            photo_in_path=photo_in_path,
        )
        self.storage.append_log(record)

        # Stop alarm
        if self.on_alarm_stop:
            self.on_alarm_stop()

        # Queue advance — use photo captured at enqueue time, do not re-capture
        if self.queue:
            nxt = self.queue.popleft()
            # TTS
            if self.cfg.tts_enabled and self.on_tts:
                self.on_tts(f"Next up, {nxt.name}, you may go for {nxt.pass_type.value}.")
            self.active = ActivePass(
                student_name=nxt.name,
                block_id=self.current_block(),
                pass_type=nxt.pass_type,
                time_out=datetime.now(),
                photo_out_path=nxt.photo_out_path or "",
            )
            self._set_state(State.ACTIVE)
        else:
            self.active = None
            self._set_state(State.IDLE)
        return record

    def set_next_photo(self, photo_out_path: str) -> None:
        if self.active and not self.active.photo_out_path:
            self.active.photo_out_path = photo_out_path

    def remaining_seconds(self) -> int | None:
        if not self.active:
            return None
        thresh = threshold_for(self.active.pass_type.value, self.cfg)
        return max(0, thresh - self.active.elapsed_seconds)

    def is_overtime(self) -> bool:
        return self.state == State.OVERTIME

    def queue_list(self) -> list[QueuedStudent]:
        return list(self.queue)
