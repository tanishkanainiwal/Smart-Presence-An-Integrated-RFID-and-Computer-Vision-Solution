
-- Students table
CREATE TABLE IF NOT EXISTS students (
    student_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no       TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    branch        TEXT NOT NULL,
    room_id       INTEGER NOT NULL,
    rfid_uid      TEXT UNIQUE NOT NULL,
    face_encoding BLOB NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teachers table
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    room_id       INTEGER NOT NULL
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id),
    exam_date     DATE NOT NULL,
    room_id       INTEGER NOT NULL,
    entry_time    TIMESTAMP,
    status        TEXT NOT NULL DEFAULT 'PRESENT',
    UNIQUE(student_id, exam_date)
);

-- Live Movement table
CREATE TABLE IF NOT EXISTS live_movement (
    movement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id),
    room_id       INTEGER NOT NULL,
    branch        TEXT NOT NULL,
    out_time      TIMESTAMP NOT NULL,
    in_time       TIMESTAMP,
    status        TEXT NOT NULL DEFAULT 'OUT'
);

-- Scan Log table
-- Audit trail ke liye (exam dispute mein kam aata h)
CREATE TABLE IF NOT EXISTS scan_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER,
    room_id       INTEGER NOT NULL,
    rfid_uid      TEXT NOT NULL,
    scan_type     TEXT NOT NULL,
    face_match    BOOLEAN,
    rule_result   TEXT,
    timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_students_rfid 
    ON students(rfid_uid);
CREATE INDEX IF NOT EXISTS idx_live_movement_status 
    ON live_movement(status);
CREATE INDEX IF NOT EXISTS idx_attendance_date 
    ON attendance(exam_date);