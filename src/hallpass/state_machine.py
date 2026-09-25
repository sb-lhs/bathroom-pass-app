"""Application state machine: IDLE -> ACTIVE -> OVERTIME with multiple concurrent passes.

Two modes (from AppConfig):
  headcount: up to cfg.max_concurrent simultaneous passes, one shared queue.
  slots:     one occupant per named cfg.pass_slots entry, each slot its own queue.

Legacy single-pass calls (no slot/key) operate on the primary pass
(first overtime, else first started) so old UI/tests keep working.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
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
    slot: str = ""

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
    slot: str = ""
    place_key: str = ""


def _pool_key(i: int) -> str:
    return f"pool:{i}"


class PassStateMachine:
    """Multi-pass logic; UI binds via callbacks.

    Flow per place:
      free --select(name, pass_type)--> active (photo out)
      active --tick--> overtime when elapsed > threshold (shared alarm)
      active --return_pass--> log + advance that place's queue
    """

    def __init__(self, cfg: AppConfig, storage: Storage, block_id_provider: Callable[[], str]):
        self.cfg = cfg
        self.storage = storage
        self.block_id_provider = block_id_provider
        self.state: State = State.IDLE
        self.actives: dict[str, ActivePass] = {}
        self.queue: deque[QueuedStudent] = deque()
        self.slot_queues: dict[str, deque[QueuedStudent]] = {}
        self._alarming = False
        # Callbacks for UI
        self.on_tts: Callable[[str], None] | None = None
        self.on_alarm_start: Callable[[], None] | None = None
        self.on_alarm_stop: Callable[[], None] | None = None
        self.on_state_changed: Callable[[State], None] | None = None

    # --- Compat: primary pass (first overtime, else first started) ---
    @property
    def active(self) -> ActivePass | None:
        overs = [a for a in self.actives.values() if self._is_over(a)]
        if overs:
            return overs[0]
        return next(iter(self.actives.values()), None)

    def _set_state(self, s: State) -> None:
        if self.state != s:
            self.state = s
            if self.on_state_changed:
                self.on_state_changed(s)
        else:
            self.state = s

    def current_block(self) -> str:
        return self.block_id_provider()

    def _places(self) -> list[str]:
        mode = getattr(self.cfg, "pass_mode", "simple") or "simple"
        if mode == "slots":
            return list(getattr(self.cfg, "pass_slots", []) or [])
        if mode == "simple":
            return [_pool_key(0)]
        n = max(1, int(getattr(self.cfg, "max_concurrent", 1) or 1))
        return [_pool_key(i) for i in range(n)]

    def _is_over(self, a: ActivePass) -> bool:
        try:
            thresh = threshold_for(a.pass_type.value, self.cfg)
            return a.elapsed_seconds > thresh
        except Exception:
            return False

    def _sync(self) -> None:
        if any(self._is_over(a) for a in self.actives.values()):
            self._set_state(State.OVERTIME)
        elif self.actives:
            self._set_state(State.ACTIVE)
        else:
            self._set_state(State.IDLE)
        any_unmuted = any(self._is_over(a) and not a.muted for a in self.actives.values())
        if any_unmuted and not self._alarming:
            self._alarming = True
            if self.on_alarm_start:
                self.on_alarm_start()
        elif not any_unmuted and self._alarming:
            self._alarming = False
            if self.on_alarm_stop:
                self.on_alarm_stop()

    def _name_busy(self, name: str) -> bool:
        low = name.strip().lower()
        if any(a.student_name.strip().lower() == low for a in self.actives.values()):
            return True
        if any(q.name.strip().lower() == low for q in self.queue):
            return True
        for dq in self.slot_queues.values():
            if any(q.name.strip().lower() == low for q in dq):
                return True
        return False

    def active_passes(self) -> list[ActivePass]:
        return list(self.actives.values())

    def free_places(self) -> list[str]:
        return [p for p in self._places() if p not in self.actives]

    def select_student(self, name: str, pass_type: PassType, photo_out_path: str, slot: str = "") -> str:
        if not name or not name.strip():
            return ""
        if self._name_busy(name):
            return ""
        places = self._places()
        if not places:
            return ""
        if getattr(self.cfg, "pass_mode", "headcount") == "slots":
            want = (slot or "").strip()
            if not want:
                free = self.free_places()
                if not free:
                    return ""
                want = free[0]
            if want not in places or want in self.actives:
                return ""
            key = want
            label = want
        else:
            free = self.free_places()
            if not free:
                return ""
            key = free[0]
            label = ""
        self.actives[key] = ActivePass(
            student_name=name.strip(),
            block_id=self.current_block(),
            pass_type=pass_type,
            time_out=datetime.now(),
            photo_out_path=photo_out_path,
            slot=label,
            place_key=key,
        )
        self._sync()
        return key

    def enqueue(self, name: str, pass_type: PassType, photo_out_path: str = "", slot: str = "") -> bool:
        if not name or not name.strip():
            return False
        if self._name_busy(name):
            return False
        q = QueuedStudent(name=name.strip(), pass_type=pass_type, photo_out_path=photo_out_path, queued_at=datetime.now(), block_id=self.current_block(), slot=(slot or "").strip())
        if getattr(self.cfg, "pass_mode", "headcount") == "slots":
            want = (slot or "").strip()
            if want and want in self._places():
                self.slot_queues.setdefault(want, deque()).append(q)
                return True
            return False
        self.queue.append(q)
        return True

    def _find_queued(self, name: str, slot: str = "") -> tuple[str, int] | None:
        low = name.strip().lower()
        if not slot or slot == "shared":
            for i, q in enumerate(self.queue):
                if q.name.strip().lower() == low:
                    return ("shared", i)
        for sk, dq in self.slot_queues.items():
            if slot and sk != slot:
                continue
            for i, q in enumerate(dq):
                if q.name.strip().lower() == low:
                    return (sk, i)
        if slot and slot != "shared":
            for i, q in enumerate(self.queue):
                if q.name.strip().lower() == low:
                    return ("shared", i)
        return None

    def dequeue(self, name: str, slot: str = "") -> bool:
        found = self._find_queued(name, slot or "")
        if not found:
            return False
        sk, i = found
        if sk == "shared":
            del self.queue[i]
        else:
            del self.slot_queues[sk][i]
        return True

    def cancel_queued(self, name: str, slot: str = "") -> bool:
        found = self._find_queued(name, slot or "")
        if not found:
            return False
        sk, i = found
        if sk == "shared":
            cancelled = self.queue[i]
            del self.queue[i]
        else:
            cancelled = self.slot_queues[sk][i]
            del self.slot_queues[sk][i]
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
                slot=cancelled.slot or "",
            )
            self.storage.append_log(rec)
        except Exception:
            pass
        return True

    def tick(self, elapsed_seconds: int | None = None) -> None:
        if elapsed_seconds is not None:
            prim = self.active
            if not prim:
                return
            prim.elapsed_seconds = int(elapsed_seconds)
            self._sync()
            return
        now = datetime.now()
        for a in self.actives.values():
            try:
                a.elapsed_seconds = int((now - a.time_out).total_seconds())
            except Exception:
                pass
        self._sync()

    def mute_alarm(self, key: str | None = None) -> None:
        if key:
            a = self.actives.get(key)
            if a:
                a.muted = True
        else:
            for a in self.actives.values():
                a.muted = True
        self._sync()

    def return_pass(self, photo_in_path: str, key: str | None = None) -> PassRecord | None:
        if key:
            leaving = self.actives.get(key)
        else:
            leaving = self.active
        if not leaving:
            return None
        time_in = datetime.now()
        duration_s = (time_in - leaving.time_out).total_seconds()
        duration_m = duration_s / 60.0
        overtime = calculate_overtime(
            duration_s, leaving.pass_type, self.cfg.bathroom_threshold_seconds, self.cfg.water_threshold_seconds
        )
        record = PassRecord(
            student_name=leaving.student_name,
            block_id=leaving.block_id,
            pass_type=leaving.pass_type,
            time_out=leaving.time_out,
            time_in=time_in,
            duration_minutes=round(duration_m, 2),
            overtime_status=overtime,
            photo_out_path=leaving.photo_out_path,
            photo_in_path=photo_in_path,
            slot=leaving.slot or "",
        )
        self.storage.append_log(record)
        freed = leaving.place_key
        try:
            del self.actives[freed]
        except KeyError:
            pass

        # Advance: slot's own queue in slots mode, shared queue in headcount
        nxt = None
        if getattr(self.cfg, "pass_mode", "headcount") == "slots":
            dq = self.slot_queues.get(freed)
            if dq:
                nxt = dq.popleft()
        else:
            if self.queue:
                nxt = self.queue.popleft()
        if nxt is not None:
            if self.cfg.tts_enabled and self.on_tts:
                self.on_tts(f"Next up, {nxt.name}, you may go for {nxt.pass_type.value}.")
            self.actives[freed] = ActivePass(
                student_name=nxt.name,
                block_id=self.current_block(),
                pass_type=nxt.pass_type,
                time_out=datetime.now(),
                photo_out_path=nxt.photo_out_path or "",
                slot=leaving.slot or "",
                place_key=freed,
            )
        self._sync()
        return record

    def set_next_photo(self, photo_out_path: str) -> None:
        prim = self.active
        if prim and not prim.photo_out_path:
            prim.photo_out_path = photo_out_path

    def remaining_seconds(self, key: str | None = None) -> int | None:
        a = self.actives.get(key) if key else self.active
        if not a:
            return None
        thresh = threshold_for(a.pass_type.value, self.cfg)
        return max(0, thresh - a.elapsed_seconds)

    def elapsed_for(self, key: str) -> int:
        a = self.actives.get(key)
        return int(a.elapsed_seconds) if a else 0

    def is_overtime(self) -> bool:
        return self.state == State.OVERTIME

    def queue_list(self, slot: str = "") -> list[QueuedStudent]:
        if slot and slot in self.slot_queues:
            return list(self.slot_queues[slot])
        if slot:
            return []
        return list(self.queue)

    def queue_counts(self) -> dict[str, int]:
        out = {"shared": len(self.queue)}
        for sk, dq in self.slot_queues.items():
            out[sk] = len(dq)
        return out
