from flask import Flask, jsonify, request, render_template, session, redirect, url_for, Response

from datetime import datetime, date
from functools import wraps
import hashlib
import os
import io
import csv

from database import query_one, query_all, execute, init_db
import rules

app = Flask(__name__)
app.secret_key = "smartpresence2026"

# Auth Helper
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "teacher_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "teacher_id" not in session:
            session.clear()
            return redirect(url_for("login"))
        if session.get("room_id") != 0:
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def hash_password(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


@app.route("/login", methods=["GET", "POST"])
def login():
    # Browser cache clear karo
    if request.method == "GET":
        session.clear()

    if "teacher_id" in session:
        if session.get("room_id") == 0:
            return redirect(url_for("admin"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        teacher = query_one(
            "SELECT * FROM teachers WHERE username = ?",
            (username,)
        )
        if teacher and teacher["password_hash"] == hash_password(password):
            session.clear()
            session["teacher_id"] = teacher["teacher_id"]
            session["room_id"]    = teacher["room_id"]
            session["username"]   = teacher["username"]

            if teacher["room_id"] == 0:
                return redirect(url_for("admin"))
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Wrong username or password")

    return render_template("login.html", error=None)


# ← Yahan add karo (login ke bilkul baad)
@app.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("login"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# MAIN ENDPOINT: ESP32-CAM yha POST karega
@app.route("/api/scan", methods=["POST"])
def scan():
    # Step 1: Data receive karo
    uid = request.form.get("uid", "").strip().upper()
    room_id = request.form.get("room_id", type=int)
    image_file = request.files.get("image")

    # Step 2: Validation
    if not uid or room_id is None or image_file is None:
        return jsonify({
            "result": "ERROR",
            "message": "uid, room_id aur image sab chahiye"
        }), 400

    # Step 3: Student dhundho
    student = query_one(
        "SELECT * FROM students WHERE rfid_uid = ?",
        (uid,)
    )
    if not student:
        _log_scan(None, room_id, uid, "UNKNOWN", False, "DENIED_UNKNOWN_CARD")
        return jsonify({
            "result": "DENIED_UNKNOWN_CARD",
            "message": "Card registered nahi hai"
        })

    student_id = student["student_id"]
    branch = student["branch"]

    # Step 4: Face verification
    # Abhi dummy mode mein — always match
    # Pi aane pe real face_recognition 
    jpeg_bytes = image_file.read()
    face_matched = True  # TODO: replace with real face verification
    confidence = 1.0

    if not face_matched:
        _log_scan(student_id, room_id, uid, "FACE_CHECK", False, "DENIED_FACE_MISMATCH")
        return jsonify({
            "result": "DENIED_FACE_MISMATCH",
            "message": "Face match nahi hua"
        })

    # Step 5: Event type decide 
    event_type = _determine_event_type(student_id)
    print(f"\nScan: {student['name']} | Event: {event_type} | Room: {room_id}")

    # Step 6: Event handle
    if event_type == "ATTENDANCE":
        _mark_attendance(student_id, room_id)
        _log_scan(student_id, room_id, uid, "ATTENDANCE", True, "ALLOWED")
        return jsonify({
            "result": "ALLOWED",
            "event_type": "ATTENDANCE",
            "write_status": "IN",
            "message": f"Welcome {student['name']}! Attendance mark ho gayi"
        })

    elif event_type == "WASHROOM_OUT":
        allowed, reason = rules.can_student_go_out(student_id, branch, room_id)

        if not allowed:
            _log_scan(student_id, room_id, uid, "WASHROOM_OUT", True, reason)
            return jsonify({
                "result": reason,
                "event_type": "WASHROOM_OUT",
                "write_status": "IN",
                "message": _reason_message(reason)
            })

        rules.mark_student_out(student_id, room_id, branch)
        _log_scan(student_id, room_id, uid, "WASHROOM_OUT", True, "ALLOWED")
        return jsonify({
            "result": "ALLOWED",
            "event_type": "WASHROOM_OUT",
            "write_status": "OUT",
            "message": f"{student['name']} bahar ja sakta/sakti hai"
        })

    else:  # WASHROOM_IN
        rules.mark_student_in(student_id)
        _log_scan(student_id, room_id, uid, "WASHROOM_IN", True, "ALLOWED")
        return jsonify({
            "result": "ALLOWED",
            "event_type": "WASHROOM_IN",
            "write_status": "IN",
            "message": f"Welcome back {student['name']}!"
        })


# Helper Functions
def _determine_event_type(student_id):
    """Same card tap ka matlab kya hai — context se decide karo"""
    today = date.today().isoformat()

    # Aaj attendance hai?
    attendance = query_one(
        "SELECT * FROM attendance WHERE student_id = ? AND exam_date = ?",
        (student_id, today)
    )

    if not attendance:
        return "ATTENDANCE"  # Pehla tap — attendance

    if rules.is_student_currently_out(student_id):
        return "WASHROOM_IN"  # Bahar tha — wapas aa raha hai

    return "WASHROOM_OUT"  # Andar tha — bahar ja raha hai


def _mark_attendance(student_id, room_id):
    today = date.today().isoformat()
    execute(
        """INSERT INTO attendance 
           (student_id, exam_date, room_id, entry_time, status)
           VALUES (?, ?, ?, ?, 'PRESENT')""",
        (student_id, today, room_id, datetime.now())
    )


def _reason_message(reason):
    messages = {
        "DENIED_MAX_LIMIT": "Abhi 2 students bahar hain — wait karo",
        "DENIED_SAME_BRANCH": "Tumhari branch ka student bahar hai — wait karo"
    }
    return messages.get(reason, "Denied")


def _log_scan(student_id, room_id, uid, scan_type, face_match, rule_result):
    execute(
        """INSERT INTO scan_log 
           (student_id, room_id, rfid_uid, scan_type, face_match, rule_result)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (student_id, room_id, uid, scan_type, face_match, rule_result)
    )


@app.route("/dashboard")
@login_required
def dashboard():
    room_id = session["room_id"]

    students = query_all(
        """SELECT student_id, name, roll_no, branch 
           FROM students WHERE room_id = ? 
           ORDER BY roll_no""",
        (room_id,)
    )

    today = date.today().isoformat()
    live_status = []

    for s in students:
        attendance = query_one(
            "SELECT * FROM attendance WHERE student_id = ? AND exam_date = ?",
            (s["student_id"], today)
        )
        is_out = rules.is_student_currently_out(s["student_id"])

        if not attendance:
            status = "NOT ARRIVED"
        elif is_out:
            status = "OUT (WASHROOM)"
        else:
            status = "PRESENT"

        live_status.append({**s, "status": status})

    # Side wise counters
    outside_left  = len(rules.get_outside_by_side(1))  # Room 1+2
    outside_right = len(rules.get_outside_by_side(3))  # Room 3+4

    return render_template(
        "dashboard.html",
        room_id=room_id,
        username=session["username"],
        students=live_status,
        outside_left=outside_left,
        outside_right=outside_right,
    )


@app.route("/api/status")
@login_required
def api_status():
    room_id = session["room_id"]
    students = query_all(
        """SELECT student_id, name, roll_no, branch 
           FROM students WHERE room_id = ? 
           ORDER BY roll_no""",
        (room_id,)
    )
    today = date.today().isoformat()
    result = []

    for s in students:
        attendance = query_one(
            "SELECT * FROM attendance WHERE student_id = ? AND exam_date = ?",
            (s["student_id"], today)
        )
        is_out = rules.is_student_currently_out(s["student_id"])

        if not attendance:
            status = "NOT ARRIVED"
        elif is_out:
            status = "OUT (WASHROOM)"
        else:
            status = "PRESENT"

        result.append({**s, "status": status})

    return jsonify({
        "students": result,
        "outside_left":  len(rules.get_outside_by_side(1)),
        "outside_right": len(rules.get_outside_by_side(3)),
    })


def setup_test_data():
    """Dummy data — real students aane pe ye replace hoga"""

    # Test students
    test_students = [
        ("2020001", "Raj Kumar", "CSE", 1, "A1B2C3D4"),
        ("2020002", "Priya Sharma", "CSE", 1, "E5F6G7H8"),
        ("2020003", "Amit Patel", "ECE", 2, "I9J0K1L2"),
        ("2020004", "Neha Singh", "ECE", 2, "M3N4O5P6"),
        ("2020005", "Rohit Verma", "MECH", 3, "Q7R8S9T0"),
        ("2020006", "Anjali Gupta", "MECH", 3, "U1V2W3X4"),
        ("2020007", "Vikram Joshi", "CIVIL", 4, "Y5Z6A7B8"),
        ("2020008", "Pooja Yadav", "CIVIL", 4, "C9D0E1F2"),
    ]

    for roll, name, branch, room, rfid in test_students:
        execute("""
            INSERT OR IGNORE INTO students
            (roll_no, name, branch, room_id, rfid_uid, face_encoding)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (roll, name, branch, room, rfid, b"dummy_encoding"))

    # Test teachers (1 per room)
    test_teachers = [
        ("teacher1", "pass1", 1),
        ("teacher2", "pass2", 2),
        ("teacher3", "pass3", 3),
        ("teacher4", "pass4", 4),
    ]

    for username, password, room in test_teachers:
        execute("""
            INSERT OR IGNORE INTO teachers
            (username, password_hash, room_id)
            VALUES (?, ?, ?)
        """, (username, hash_password(password), room))

        # Ye line add karo test teachers ke baad:
    execute("""
    INSERT OR IGNORE INTO teachers
    (username, password_hash, room_id)
    VALUES (?, ?, ?)
""", ("admin", hash_password("admin123"), 0))
        

    print("Test data ready!")


@app.route("/admin")
@admin_required
def admin():
    today = date.today().isoformat()

    # Saare 4 rooms ka data
    all_rooms = {}
    for room_id in [1, 2, 3, 4]:
        students = query_all(
            """SELECT s.student_id, s.name, s.roll_no, s.branch,
                      a.entry_time, a.status
               FROM students s
               LEFT JOIN attendance a
               ON s.student_id = a.student_id AND a.exam_date = ?
               WHERE s.room_id = ?
               ORDER BY s.roll_no""",
            (today, room_id)
        )

        room_students = []
        for s in students:
            is_out = rules.is_student_currently_out(s["student_id"])

            if not s["entry_time"]:
                status = "NOT ARRIVED"
            elif is_out:
                status = "OUT (WASHROOM)"
            else:
                status = "PRESENT"

            room_students.append({**s, "status": status})

        all_rooms[room_id] = room_students

    # Washroom logs per room (with duration)
    washroom_logs = {}
    for room_id in [1, 2, 3, 4]:
        logs = query_all(
            """SELECT lm.*, s.name, s.branch,
                      CASE
                          WHEN lm.in_time IS NOT NULL
                          THEN ROUND((JULIANDAY(lm.in_time) - JULIANDAY(lm.out_time)) * 1440)
                          ELSE NULL
                      END as duration_mins
               FROM live_movement lm
               JOIN students s ON lm.student_id = s.student_id
               WHERE lm.room_id = ?
               AND DATE(lm.out_time) = ?
               ORDER BY lm.out_time DESC""",
            (room_id, today)
        )

        # Duration format karo
        for log in logs:
            if log["duration_mins"]:
                log["duration"] = f"{int(log['duration_mins'])} min"
            else:
                log["duration"] = "—"

        washroom_logs[room_id] = logs

    # System stats
    all_students = query_all("SELECT * FROM students")
    total = len(all_students)
    present = washroom = absent = 0

    for room_students in all_rooms.values():
        for s in room_students:
            if s["status"] == "PRESENT": present += 1
            elif s["status"] == "OUT (WASHROOM)": washroom += 1
            else: absent += 1

    return render_template(
        "admin.html",
        all_rooms=all_rooms,
        washroom_logs=washroom_logs,
        total=total,
        present=present,
        washroom=washroom,
        absent=absent,
        outside_left=len(rules.get_outside_by_side(1)),
        outside_right=len(rules.get_outside_by_side(3)),
        username=session["username"]
    )


@app.route("/api/admin/status")
@admin_required
def api_admin_status():
    """Admin dashboard JS polling ke liye"""
    today = date.today().isoformat()
    all_rooms = {}

    for room_id in [1, 2, 3, 4]:
        students = query_all(
            """SELECT student_id, name, roll_no, branch
               FROM students WHERE room_id = ?
               ORDER BY roll_no""",
            (room_id,)
        )
        room_students = []
        for s in students:
            attendance = query_one(
                "SELECT * FROM attendance WHERE student_id = ? AND exam_date = ?",
                (s["student_id"], today)
            )
            is_out = rules.is_student_currently_out(s["student_id"])

            if not attendance:
                status = "NOT ARRIVED"
            elif is_out:
                status = "OUT (WASHROOM)"
            else:
                status = "PRESENT"

            room_students.append({**s, "status": status})

        all_rooms[str(room_id)] = room_students

    # Counts
    present = washroom = absent = 0
    for room_students in all_rooms.values():
        for s in room_students:
            if s["status"] == "PRESENT": present += 1
            elif s["status"] == "OUT (WASHROOM)": washroom += 1
            else: absent += 1

    # Recent scans
    scan_logs = query_all(
        """SELECT sl.*, st.name, st.branch
           FROM scan_log sl
           LEFT JOIN students st ON sl.student_id = st.student_id
           ORDER BY sl.timestamp DESC
           LIMIT 10"""
    )

    return jsonify({
        "all_rooms": all_rooms,
        "present": present,
        "washroom": washroom,
        "absent": absent,
        "outside_left": len(rules.get_outside_by_side(1)),
        "outside_right": len(rules.get_outside_by_side(3)),
        "scan_logs": scan_logs
    })

import csv
import io
from flask import Response

# Export Routes


@app.route("/export/attendance")
@admin_required
def export_attendance():
    today = date.today().isoformat()

    # Saare students ka attendance data
    students = query_all(
        """SELECT s.name, s.roll_no, s.branch, s.room_id,
                  a.entry_time, a.status
           FROM students s
           LEFT JOIN attendance a
           ON s.student_id = a.student_id AND a.exam_date = ?
           ORDER BY s.room_id, s.roll_no""",
        (today,)
    )

    # CSV banao
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "S.No", "Name", "Roll No", "Branch",
        "Room", "Entry Time", "Status"
    ])

    # Data rows
    for i, s in enumerate(students, 1):
        if not s["entry_time"]:
            status = "NOT ARRIVED"
        elif rules.is_student_currently_out(s["student_id"] if "student_id" in s else 0):
            status = "OUT (WASHROOM)"
        else:
            status = "PRESENT"

        writer.writerow([
            i,
            s["name"],
            s["roll_no"],
            s["branch"],
            f"Room {s['room_id']}",
            s["entry_time"] or "—",
            status
        ])

    # Response
    output.seek(0)
    filename = f"attendance_{today}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.route("/export/washroom")
@admin_required
def export_washroom():
    today = date.today().isoformat()

    # Saare washroom records
    logs = query_all(
        """SELECT s.name, s.roll_no, s.branch, s.room_id,
                  lm.out_time, lm.in_time, lm.status,
                  CASE
                      WHEN lm.in_time IS NOT NULL
                      THEN ROUND((JULIANDAY(lm.in_time) - JULIANDAY(lm.out_time)) * 1440)
                      ELSE NULL
                  END as duration_mins
           FROM live_movement lm
           JOIN students s ON lm.student_id = s.student_id
           WHERE DATE(lm.out_time) = ?
           ORDER BY s.room_id, lm.out_time""",
        (today,)
    )

    # CSV banao
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "S.No", "Name", "Roll No", "Branch",
        "Room", "Out Time", "In Time",
        "Duration (mins)", "Status"
    ])

    # Data rows
    for i, log in enumerate(logs, 1):
        writer.writerow([
            i,
            log["name"],
            log["roll_no"],
            log["branch"],
            f"Room {log['room_id']}",
            log["out_time"],
            log["in_time"] or "Still Outside",
            log["duration_mins"] or "—",
            "Returned" if log["status"] == "IN" else "Outside"
        ])

    # Response
    output.seek(0)
    filename = f"washroom_log_{today}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

if __name__ == "__main__":
    # Fresh database banao
    if os.path.exists("smartpresence.db"):
        os.remove("smartpresence.db")

    init_db()
    setup_test_data()

    print("\nSmartPresence Server Starting...")
    print("Dashboard: http://localhost:5000/login")
    print("Admin: http://localhost:5000/admin (admin/admin123)")
    print(" Login: teacher1 / pass1 (Room 1)")
    print("Login: teacher2 / pass2 (Room 2)\n")

    app.run(host="0.0.0.0", port=5000, debug=True)