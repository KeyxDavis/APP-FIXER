import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a lightweight supabase stub so the cloud adapter can be imported in tests.
supabase_stub = types.ModuleType("supabase")


class Client:  # pragma: no cover - simple stub for import-time compatibility
    pass


def create_client(*args, **kwargs):
    return Client()


supabase_stub.Client = Client
supabase_stub.create_client = create_client
sys.modules.setdefault("supabase", supabase_stub)

from db import Database
from supabase_db import SupabaseDatabase


class DatabaseSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.temp_dir.name, "attendance.db"))

    def tearDown(self):
        self.db.connection.close()
        self.temp_dir.cleanup()

    def test_local_attendance_flow(self):
        self.assertTrue(self.db.create_user("admin", "hash123", "admin@example.com"))
        self.assertTrue(
            self.db.add_staff(
                "s-1", "Alice Staff", "STF-001", "IT", "alice@example.com"
            )
        )

        entry = self.db.record_entry("s-1")
        self.assertIn("time", entry)
        self.assertIn("late", entry)

        exit_time = self.db.record_exit("s-1")
        self.assertIsNotNone(exit_time)

        today = self.db.get_today_attendance()
        self.assertIn("s-1", today)
        self.assertEqual(today["s-1"]["late"], entry["late"])

        records = self.db.attendance_records_between("2026-01-01", "2026-12-31")
        self.assertTrue(records)
        self.assertEqual(records[0]["staff_id"], "s-1")

        summary = self.db.term_summary(10, "2026-01-01", "2026-12-31")
        self.assertEqual(summary["total_staff"], 1)
        self.assertEqual(summary["staff"][0]["staff_id"], "s-1")


class SupabaseSmokeTest(unittest.TestCase):
    def test_cloud_term_summary_uses_staff_id(self):
        class FakeResult:
            def __init__(self, data):
                self.data = data

        class FakeTable:
            def __init__(self, items=None):
                self.items = items or []
                self._query = None

            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def gte(self, *_args, **_kwargs):
                return self

            def lte(self, *_args, **_kwargs):
                return self

            def order(self, *_args, **_kwargs):
                return self

            def maybe_single(self):
                return self

            def execute(self):
                return FakeResult(self.items)

        class FakeClient:
            def __init__(self):
                self.tables = {
                    "staff": FakeTable(
                        [
                            {
                                "id": "s-2",
                                "name": "Bob Staff",
                                "staff_number": "STF-002",
                                "department": "HR",
                                "email": "bob@example.com",
                            }
                        ]
                    ),
                    "attendance": FakeTable(
                        [
                            {
                                "staff_id": "s-2",
                                "attendance_date": "2026-09-09",
                                "time_in": "08:15:00",
                                "time_out": "17:00:00",
                                "is_late": False,
                            }
                        ]
                    ),
                    "school_settings": FakeTable({"term_days": 10}),
                    "application_status": FakeTable({"enabled": True, "message": ""}),
                    "activity_logs": FakeTable([]),
                }

            def table(self, name):
                return self.tables[name]

            def rpc(self, *_args, **_kwargs):
                return FakeResult(
                    [{"time_in": "08:15:00", "is_late": False, "time_out": "17:00:00"}]
                )

            @property
            def auth(self):
                return types.SimpleNamespace(
                    sign_in_with_password=lambda *_args, **_kwargs: types.SimpleNamespace(
                        user=types.SimpleNamespace(id="user-1")
                    ),
                    update_user=lambda *_args, **_kwargs: None,
                )

        db = SupabaseDatabase("https://example.com", "anon-key", "school-1")
        db.client = FakeClient()

        records = db.attendance_records_between("2026-09-01", "2026-09-30")
        self.assertEqual(records[0]["staff_id"], "s-2")

        summary = db.term_summary(10, "2026-09-01", "2026-09-30")
        self.assertEqual(summary["staff"][0]["staff_id"], "s-2")


if __name__ == "__main__":
    unittest.main()
