"""SQLite + CSV dual logging with dual PassType thresholds."""
from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from .config import csv_path, data_dir, db_path, photos_dir

CSV_HEADERS = [
    "Student Name",
    "Block ID",
    "Pass Type",
    "Time Out",
    "Time In",
    "Duration (Minutes)",
    "Overtime Status",
    "Photo Out Path",
    "Photo In Path",
]


class PassType(str, Enum):
    Bathroom = "Bathroom"
    Water = "Water"


class OvertimeStatus(str, Enum):
    NOT_OVER = "NOT OVER"
    OVERTIME = "OVERTIME"
    CANCELLED = "CANCELLED"


@dataclass
class PassRecord:
    student_name: str
    block_id: str
    pass_type: PassType
    time_out: datetime
    time_in: datetime
    duration_minutes: float
    overtime_status: OvertimeStatus
    photo_out_path: str
    photo_in_path: str


def calculate_overtime(duration_seconds: float, pass_type: PassType, bathroom_threshold: int, water_threshold: int) -> OvertimeStatus:
    threshold = water_threshold if pass_type == PassType.Water else bathroom_threshold
    return OvertimeStatus.OVERTIME if duration_seconds > threshold else OvertimeStatus.NOT_OVER


def _ensure_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pass_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            block_id TEXT NOT NULL,
            pass_type TEXT NOT NULL,
            time_out TEXT NOT NULL,
            time_in TEXT NOT NULL,
            duration_minutes REAL NOT NULL,
            overtime_status TEXT NOT NULL,
            photo_out_path TEXT NOT NULL,
            photo_in_path TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _ensure_csv(csv_file: Path | None = None) -> None:
    p = csv_file or csv_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    photos_dir().mkdir(parents=True, exist_ok=True)
    if not p.exists():
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADERS)


class Storage:
    def __init__(self, db: Path | None = None, csv: Path | None = None):
        self._db_path = db or db_path()
        self._csv_path = csv or csv_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        _ensure_csv(self._csv_path)
        with sqlite3.connect(self._db_path) as conn:
            _ensure_db(conn)

    def append_log(self, record: PassRecord) -> None:
        # CSV append (real-time)
        _ensure_csv(self._csv_path)
        with self._csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    record.student_name,
                    record.block_id,
                    record.pass_type.value,
                    record.time_out.strftime("%Y-%m-%d %H:%M:%S"),
                    record.time_in.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{record.duration_minutes:.2f}",
                    record.overtime_status.value,
                    record.photo_out_path,
                    record.photo_in_path,
                ]
            )
        # SQLite
        with sqlite3.connect(self._db_path) as conn:
            _ensure_db(conn)
            conn.execute(
                "INSERT INTO pass_logs (student_name, block_id, pass_type, time_out, time_in, duration_minutes, overtime_status, photo_out_path, photo_in_path) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    record.student_name,
                    record.block_id,
                    record.pass_type.value,
                    record.time_out.strftime("%Y-%m-%d %H:%M:%S"),
                    record.time_in.strftime("%Y-%m-%d %H:%M:%S"),
                    record.duration_minutes,
                    record.overtime_status.value,
                    record.photo_out_path,
                    record.photo_in_path,
                ),
            )
            conn.commit()

    def get_logs(self) -> list[PassRecord]:
        with sqlite3.connect(self._db_path) as conn:
            _ensure_db(conn)
            rows = conn.execute("SELECT student_name, block_id, pass_type, time_out, time_in, duration_minutes, overtime_status, photo_out_path, photo_in_path FROM pass_logs ORDER BY id").fetchall()
        result: list[PassRecord] = []
        for r in rows:
            result.append(
                PassRecord(
                    student_name=r[0],
                    block_id=r[1],
                    pass_type=PassType(r[2]),
                    time_out=datetime.strptime(r[3], "%Y-%m-%d %H:%M:%S"),
                    time_in=datetime.strptime(r[4], "%Y-%m-%d %H:%M:%S"),
                    duration_minutes=float(r[5]),
                    overtime_status=OvertimeStatus(r[6]),
                    photo_out_path=r[7],
                    photo_in_path=r[8],
                )
            )
        return result

    def get_logs_by_block(self, block_id: str) -> list[PassRecord]:
        return [r for r in self.get_logs() if r.block_id == block_id]

    def ensure_dirs(self) -> None:
        data_dir().mkdir(parents=True, exist_ok=True)
        photos_dir().mkdir(parents=True, exist_ok=True)
