-- Local SQLite schema for the Staff Attendance Application.
-- db.py creates this automatically; this file is provided for reference
-- and for manual database initialization.

PRAGMA foreign_keys = ON;

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

INSERT OR IGNORE INTO settings (name, value) VALUES ('term_days', '0');

CREATE INDEX IF NOT EXISTS attendance_date_idx
    ON attendance (attendance_date);
CREATE INDEX IF NOT EXISTS attendance_staff_date_idx
    ON attendance (staff_id, attendance_date);
