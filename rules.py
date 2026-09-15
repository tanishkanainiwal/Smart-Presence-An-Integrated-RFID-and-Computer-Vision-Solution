
from database import query_all, query_one, execute
from datetime import datetime

MAX_STUDENTS_OUTSIDE = 2

LEFT_SIDE_ROOMS  = [1, 2]
RIGHT_SIDE_ROOMS = [3, 4]


def get_side(room_id):
    if room_id in LEFT_SIDE_ROOMS:
        return "left"
    return "right"


def get_side_rooms(room_id):
    # Us side ke saare rooms return karne ke liye
    if room_id in LEFT_SIDE_ROOMS:
        return LEFT_SIDE_ROOMS
    return RIGHT_SIDE_ROOMS


def get_currently_outside():
    # saare bahar wale students
    return query_all(
        "SELECT * FROM live_movement WHERE status = 'OUT'"
    )


def get_outside_by_side(room_id):
    #Sirf ek side ke bahar wale students

    side_rooms = get_side_rooms(room_id)

    # SQL mein IN clause ke liye placeholders
    placeholders = ",".join("?" * len(side_rooms))

    return query_all(
        f"""SELECT * FROM live_movement 
            WHERE status = 'OUT' 
            AND room_id IN ({placeholders})""",
        tuple(side_rooms)
    )


def can_student_go_out(student_id, branch, room_id):
    """
    Student bahar ja sakta h ya nahi
    Rules (side-wise):
    1. Us side se max 2 bahar hain already → DENIED
    2. Us side se same branch already bahar hai → DENIED
    """
    # Sirf us side ke bahar wale
    outside = get_outside_by_side(room_id)
    side = get_side(room_id)

    print(f"Side: {side} | Outside on this side: {len(outside)}")

    # Rule 1 Max 2 outside (side wise)
    if len(outside) >= MAX_STUDENTS_OUTSIDE:
        return False, "DENIED_MAX_LIMIT"

    # Rule 2 Same branch outside (side wise)
    for row in outside:
        if row["branch"] == branch:
            return False, "DENIED_SAME_BRANCH"

    return True, "ALLOWED"


def mark_student_out(student_id, room_id, branch):
    """Student bahar gya — record"""
    return execute(
        """INSERT INTO live_movement 
           (student_id, room_id, branch, out_time, status)
           VALUES (?, ?, ?, ?, 'OUT')""",
        (student_id, room_id, branch, datetime.now()),
    )


def mark_student_in(student_id):
    """Student wapas aaya — record close """
    open_row = query_one(
        """SELECT * FROM live_movement
           WHERE student_id = ? AND status = 'OUT'
           ORDER BY out_time DESC LIMIT 1""",
        (student_id,),
    )

    if not open_row:
        return False

    execute(
        """UPDATE live_movement 
           SET in_time = ?, status = 'IN'
           WHERE movement_id = ?""",
        (datetime.now(), open_row["movement_id"]),
    )
    return True


def is_student_currently_out(student_id):
    """Kya student abhi bahar hai?"""
    result = query_one(
        """SELECT * FROM live_movement 
           WHERE student_id = ? AND status = 'OUT'""",
        (student_id,),
    )
    return result is not None

# Test

if __name__ == "__main__":
    import os
    from database import init_db, execute

    if os.path.exists("smartpresence.db"):
        os.remove("smartpresence.db")

    init_db()

    # Students add karo
    students = [
        ("2020001", "Raj Kumar",    "CSE",   1, "A1B2C3D4"),  # Left
        ("2020002", "Priya Sharma", "CSE",   1, "E5F6G7H8"),  # Left
        ("2020003", "Amit Patel",   "ECE",   2, "I9J0K1L2"),  # Left
        ("2020004", "Neha Singh",   "ECE",   2, "M3N4O5P6"),  # Left
        ("2020005", "Rohit Verma",  "MECH",  3, "Q7R8S9T0"),  # Right
        ("2020006", "Anjali Gupta", "MECH",  3, "U1V2W3X4"),  # Right
        ("2020007", "Vikram Joshi", "CIVIL", 4, "Y5Z6A7B8"),  # Right
        ("2020008", "Pooja Yadav",  "CIVIL", 4, "C9D0E1F2"),  # Right
    ]

    for roll, name, branch, room, rfid in students:
        execute("""INSERT OR IGNORE INTO students
            (roll_no, name, branch, room_id, rfid_uid, face_encoding)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (roll, name, branch, room, rfid, b"dummy"))

    print("\n=== Side-wise Rule Tests ===\n")

    # Test 1: Raj (CSE, Room1/Left) bahar ja sakta hai?
    allowed, reason = can_student_go_out(1, "CSE", 1)
    print(f"Test 1 - Raj (CSE, Left) bahar ja sakta hai?")
    print(f"Result: {reason}\n")  # ALLOWED

    # Raj bahar gaya
    mark_student_out(1, 1, "CSE")

    # Test 2: Priya (CSE, Room1/Left) — same branch, same side
    allowed, reason = can_student_go_out(2, "CSE", 1)
    print(f"Test 2 - Priya (CSE, Left) bahar ja sakti hai?")
    print(f"Result: {reason}\n")  # DENIED_SAME_BRANCH

    # Test 3: Amit (ECE, Room2/Left) — alag branch, same side
    allowed, reason = can_student_go_out(3, "ECE", 2)
    print(f"Test 3 - Amit (ECE, Left) bahar ja sakta hai?")
    print(f"Result: {reason}\n")  # ALLOWED

    # Amit bahar gaya — ab Left side full (2/2)
    mark_student_out(3, 2, "ECE")

    # Test 4: Neha (ECE, Room2/Left) — Left side full
    allowed, reason = can_student_go_out(4, "ECE", 2)
    print(f"Test 4 - Neha (ECE, Left) bahar ja sakti hai?")
    print(f"Result: {reason}\n")  # DENIED_MAX_LIMIT

    # Test 5: Rohit (MECH, Room3/Right) — Right side pe abhi koi nahi
    allowed, reason = can_student_go_out(5, "MECH", 3)
    print(f"Test 5 - Rohit (MECH, Right) bahar ja sakta hai?")
    print(f"Result: {reason}\n")  # ALLOWED — Right side independent hai!

    # Rohit bahar gaya
    mark_student_out(5, 3, "MECH")

    # Test 6: Anjali (MECH, Room3/Right) — same branch, Right side
    allowed, reason = can_student_go_out(6, "MECH", 3)
    print(f"Test 6 - Anjali (MECH, Right) bahar ja sakti hai?")
    print(f"Result: {reason}\n")  # DENIED_SAME_BRANCH

    print(f"Left side bahar: {len(get_outside_by_side(1))}")
    print(f"Right side bahar: {len(get_outside_by_side(3))}")