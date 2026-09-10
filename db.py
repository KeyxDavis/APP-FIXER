"""SQLite persistence for the Staff Attendance application."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

DB_FILENAME = "attendance.db"


class Database:
    """Small SQLite repository used when cloud mode is not configured."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'staff'
                    CHECK (role IN ('staff', 'admin', 'builder')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS staff (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                staff_number TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id TEXT NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
                attendance_date TEXT NOT NULL,
                time_in TEXT,
                time_out TEXT,
                is_late INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (staff_id, attendance_date),
                CHECK (time_out IS NULL OR time_in IS NOT NULL)
            );
            CREATE TABLE IF NOT EXISTS settings (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                action TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO settings (name, value)
                VALUES ('term_days', '0');
            """)
        self.connection.commit()

    @staticmethod
    def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row else None

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT username, password_hash, email, role FROM users "
            "WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        return self._row_to_dict(row)

    def create_user(self, username: str, password_hash: str, email: str) -> bool:
        role = "admin" if self._user_count() == 0 else "staff"
        try:
            self.connection.execute(
                "INSERT INTO users (username, password_hash, email, role) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, email, role),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user(
        self, old_username: str, new_username: str, password_hash: str, email: str
    ) -> bool:
        try:
            cursor = self.connection.execute(
                "UPDATE users SET username = ?, password_hash = ?, email = ? "
                "WHERE username = ? COLLATE NOCASE",
                (new_username, password_hash, email, old_username),
            )
            self.connection.commit()
            return cursor.rowcount == 1
        except sqlite3.IntegrityError:
            return False

    def _user_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])

    def add_staff(
        self,
        staff_id: str,
        name: str,
        staff_number: str,
        department: str,
        email: str,
    ) -> bool:
        try:
            self.connection.execute(
                "INSERT INTO staff (id, name, staff_number, department, email) "
                "VALUES (?, ?, ?, ?, ?)",
                (staff_id, name, staff_number, department, email),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_staff(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT id, name, staff_number, department, email "
            "FROM staff ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_staff(self, staff_id: str) -> None:
        self.connection.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
        self.connection.commit()

    def delete_all_staff(self) -> None:
        self.connection.execute("DELETE FROM staff")
        self.connection.commit()

    @staticmethod
    def _now() -> datetime:
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def _display_time(value: datetime) -> str:
        return value.strftime("%I:%M:%S %p")

    def record_entry(self, staff_id: str) -> Dict[str, Any]:
        current = self._now()
        late = (current.hour, current.minute) > (7, 30)
        values = (
            staff_id,
            current.date().isoformat(),
            self._display_time(current),
            int(late),
        )
        try:
            self.connection.execute(
                "INSERT INTO attendance "
                "(staff_id, attendance_date, time_in, is_late) "
                "VALUES (?, ?, ?, ?)",
                values,
            )
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("Attendance has already been recorded today.") from exc
        self.connection.commit()
        return {"time": values[2], "late": late}

    def record_exit(self, staff_id: str) -> Optional[str]:
        current = self._now()
        time_value = self._display_time(current)
        cursor = self.connection.execute(
            "UPDATE attendance SET time_out = ? "
            "WHERE staff_id = ? AND attendance_date = ? AND time_in IS NOT NULL "
            "AND time_out IS NULL",
            (time_value, staff_id, current.date().isoformat()),
        )
        self.connection.commit()
        return time_value if cursor.rowcount else None

    def get_today_attendance(self) -> Dict[str, Dict[str, Any]]:
        today = date.today().isoformat()
        rows = self.connection.execute(
            "SELECT staff_id, time_in, time_out, is_late FROM attendance "
            "WHERE attendance_date = ?",
            (today,),
        ).fetchall()
        return {
            row["staff_id"]: {
                "time": row["time_in"],
                "exit_time": row["time_out"],
                "late": bool(row["is_late"]),
            }
            for row in rows
        }

    def attendance_records_between(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT staff_id, attendance_date, time_in, time_out, is_late "
            "FROM attendance WHERE attendance_date BETWEEN ? AND ? "
            "ORDER BY attendance_date, staff_id",
            (start_date, end_date),
        ).fetchall()
        return [
            {
                "staff_id": row["staff_id"],
                "date": row["attendance_date"],
                "time_in": row["time_in"],
                "time_out": row["time_out"],
                "is_late": bool(row["is_late"]),
            }
            for row in rows
        ]

    def all_attendance_records(self) -> List[Dict[str, Any]]:
        return self.attendance_records_between("0001-01-01", "9999-12-31")

    def get_term_days(self) -> int:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = 'term_days'"
        ).fetchone()
        return int(row["value"]) if row else 0

    def set_term_days(self, term_days: int) -> None:
        self.connection.execute(
            "INSERT INTO settings (name, value) VALUES ('term_days', ?) "
            "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            (str(term_days),),
        )
        self.connection.commit()

    def term_summary(
        self, term_days: int, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        staff = self.list_staff()
        records = self.attendance_records_between(start_date, end_date)
        by_staff: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            by_staff.setdefault(record["staff_id"], []).append(record)

        staff_rows = []
        for person in staff:
            staff_records = by_staff.get(person["id"], [])
            present = len(staff_records)
            late = sum(1 for record in staff_records if record["is_late"])
            percentage = round((present / term_days) * 100, 2) if term_days else 0
            staff_rows.append(
                {
                    "name": person["name"],
                    "staff_id": person["id"],
                    "days_present": present,
                    "total_days": term_days,
                    "early_days": present - late,
                    "late_days": late,
                    "attendance_percentage": percentage,
                }
            )

        departments: Dict[str, Dict[str, int]] = {}
        for person in staff:
            department = person["department"]
            data = departments.setdefault(department, {"staff_count": 0, "present": 0})
            data["staff_count"] += 1
            data["present"] += len(by_staff.get(person["id"], []))
        department_rows = []
        for department, data in departments.items():
            percentage = (
                round(data["present"] / (data["staff_count"] * term_days) * 100, 2)
                if data["staff_count"] and term_days
                else 0
            )
            department_rows.append(
                {
                    "department": department,
                    "total_present_days": data["present"],
                    "staff_count": data["staff_count"],
                    "attendance_percentage": percentage,
                }
            )

        top_staff = "None"
        if staff_rows:
            top_staff = max(staff_rows, key=lambda row: row["attendance_percentage"])[
                "name"
            ]
        total_present = len(records)
        total_possible = len(staff) * term_days
        return {
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "term_days": term_days,
            "total_staff": len(staff),
            "total_present_days": total_present,
            "overall_attendance_percentage": (
                round(total_present / total_possible * 100, 2) if total_possible else 0
            ),
            "top_staff": top_staff,
            "department_summary": department_rows,
            "staff": staff_rows,
        }

    def recent_activity(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT created_at, username, action, details FROM activity_logs "
            "ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "username": row["username"] or "",
                "action": row["action"],
                "details": json.loads(row["details"] or "{}"),
            }
            for row in rows
        ]

    def log_event(
        self, username: str, action: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.connection.execute(
            "INSERT INTO activity_logs (username, action, details) VALUES (?, ?, ?)",
            (username, action, json.dumps(details or {})),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
