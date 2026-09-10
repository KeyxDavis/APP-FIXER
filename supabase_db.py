"""Optional Supabase repository for cloud deployments."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client


class SupabaseDatabase:
    """Database adapter matching the local SQLite repository interface."""

    def __init__(self, url: str, anon_key: str, school_id: str) -> None:
        self.client: Client = create_client(url, anon_key)
        self.school_id = school_id
        self.user_id: Optional[str] = None

    @staticmethod
    def _first(data: Any) -> Optional[Dict[str, Any]]:
        if isinstance(data, list):
            return data[0] if data else None
        return data if isinstance(data, dict) else None

    def _profile(self, username: str) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table("user_profiles")
            .select("username, email, role, user_id")
            .eq("username", username)
            .eq("school_id", self.school_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        profile = self._profile(username)
        if not profile:
            return None
        return {
            "username": profile["username"],
            "email": profile["email"],
            "role": profile["role"],
            "user_id": profile["user_id"],
        }

    def authenticate_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        profile = self._profile(username)
        email = profile["email"] if profile else username
        try:
            session = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception:
            return None
        self.user_id = session.user.id
        return self.get_user(username)

    def update_account(
        self,
        username: str,
        new_username: str,
        new_password: Optional[str],
        email: str,
    ) -> bool:
        profile = self._profile(username)
        if not profile:
            return False
        try:
            attributes: Dict[str, str] = {"email": email}
            if new_password:
                attributes["password"] = new_password
            self.client.auth.update_user(attributes)
            self.client.table("user_profiles").update(
                {"username": new_username, "email": email}
            ).eq("user_id", profile["user_id"]).eq(
                "school_id", self.school_id
            ).execute()
            return True
        except Exception:
            return False

    def list_staff(self) -> List[Dict[str, Any]]:
        result = (
            self.client.table("staff")
            .select("id, name, staff_number, department, email")
            .eq("school_id", self.school_id)
            .order("name")
            .execute()
        )
        return result.data or []

    def add_staff(
        self,
        staff_id: str,
        name: str,
        staff_number: str,
        department: str,
        email: str,
    ) -> bool:
        try:
            self.client.table("staff").insert(
                {
                    "school_id": self.school_id,
                    "id": staff_id,
                    "name": name,
                    "staff_number": staff_number,
                    "department": department,
                    "email": email,
                }
            ).execute()
            return True
        except Exception:
            return False

    def delete_staff(self, staff_id: str) -> None:
        self.client.table("staff").delete().eq("school_id", self.school_id).eq(
            "id", staff_id
        ).execute()

    def delete_all_staff(self) -> None:
        self.client.table("staff").delete().eq("school_id", self.school_id).execute()

    @staticmethod
    def _time_value(value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%I:%M:%S %p")
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        return parsed.strftime("%I:%M:%S %p")

    def record_entry(self, staff_id: str) -> Dict[str, Any]:
        try:
            result = self.client.rpc(
                "record_staff_entry",
                {
                    "p_school_id": self.school_id,
                    "p_staff_id": staff_id,
                },
            ).execute()
        except Exception as exc:
            if "already been recorded" in str(exc).lower():
                raise ValueError("Attendance has already been recorded today.") from exc
            raise
        record = self._first(result.data) or result.data
        return {
            "time": self._time_value(record.get("time_in")),
            "late": bool(record.get("is_late", False)),
        }

    def record_exit(self, staff_id: str) -> Optional[str]:
        result = self.client.rpc(
            "record_staff_exit",
            {
                "p_school_id": self.school_id,
                "p_staff_id": staff_id,
            },
        ).execute()
        record = self._first(result.data)
        return self._time_value(record["time_out"]) if record else None

    def get_today_attendance(self) -> Dict[str, Dict[str, Any]]:
        today = datetime.now().date().isoformat()
        result = (
            self.client.table("attendance")
            .select("staff_id, time_in, time_out, is_late")
            .eq("school_id", self.school_id)
            .eq("attendance_date", today)
            .execute()
        )
        return {
            row["staff_id"]: {
                "time": self._time_value(row["time_in"]),
                "exit_time": self._time_value(row["time_out"]),
                "late": bool(row["is_late"]),
            }
            for row in result.data or []
        }

    def attendance_records_between(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        result = (
            self.client.table("attendance")
            .select("staff_id, attendance_date, time_in, time_out, is_late")
            .eq("school_id", self.school_id)
            .gte("attendance_date", start_date)
            .lte("attendance_date", end_date)
            .order("attendance_date")
            .execute()
        )
        return [
            {
                "staff_id": row["staff_id"],
                "date": row["attendance_date"],
                "time_in": row["time_in"],
                "time_out": row["time_out"],
                "is_late": bool(row["is_late"]),
            }
            for row in result.data or []
        ]

    def all_attendance_records(self) -> List[Dict[str, Any]]:
        return self.attendance_records_between("0001-01-01", "9999-12-31")

    def get_term_days(self) -> int:
        result = (
            self.client.table("school_settings")
            .select("term_days")
            .eq("school_id", self.school_id)
            .maybe_single()
            .execute()
        )
        return int((result.data or {}).get("term_days", 0))

    def set_term_days(self, term_days: int) -> None:
        self.client.table("school_settings").upsert(
            {"school_id": self.school_id, "term_days": term_days}
        ).execute()

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
            staff_rows.append(
                {
                    "name": person["name"],
                    "staff_id": person["id"],
                    "days_present": present,
                    "total_days": term_days,
                    "early_days": present - late,
                    "late_days": late,
                    "attendance_percentage": (
                        round(present / term_days * 100, 2) if term_days else 0
                    ),
                }
            )
        total_possible = len(staff) * term_days
        return {
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "term_days": term_days,
            "total_staff": len(staff),
            "total_present_days": len(records),
            "overall_attendance_percentage": (
                round(len(records) / total_possible * 100, 2) if total_possible else 0
            ),
            "top_staff": (
                max(staff_rows, key=lambda row: row["attendance_percentage"])["name"]
                if staff_rows
                else "None"
            ),
            "department_summary": [],
            "staff": staff_rows,
        }

    def recent_activity(self) -> List[Dict[str, Any]]:
        result = (
            self.client.table("activity_logs")
            .select("created_at, username, action, details")
            .eq("school_id", self.school_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return result.data or []

    def get_app_status(self) -> Dict[str, Any]:
        result = (
            self.client.table("application_status")
            .select("enabled, message")
            .eq("school_id", self.school_id)
            .maybe_single()
            .execute()
        )
        return result.data or {"enabled": True, "message": ""}

    def switch_school(self, school_id: str, username: str) -> bool:
        result = (
            self.client.table("user_profiles")
            .select("user_id")
            .eq("username", username)
            .eq("school_id", school_id)
            .maybe_single()
            .execute()
        )
        if result.data:
            self.school_id = school_id
            return True
        return False

    def log_event(
        self, username: str, action: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.client.table("activity_logs").insert(
            {
                "school_id": self.school_id,
                "user_id": self.user_id,
                "username": username,
                "action": action,
                "details": details or {},
            }
        ).execute()
