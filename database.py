
import sqlite3
from contextlib import contextmanager

# Database file ka naam
# Jab pehli baar run hoga → automatically create ho jayega
DB_PATH = "smartpresence.db"

@contextmanager
def get_db():
    # """
    # Database connection manager
    # Usage:
    #     with get_db() as db:
    #         db.execute("SELECT * FROM students")
    
    # Automatically:
    #     - Connection open karta hai
    #     - Commit karta hai (save)
    #     - Error pe rollback karta hai (undo)
    #     - Connection close karta hai
    # """
    conn = sqlite3.connect(DB_PATH)
    
    # Row factory = column name se access karo
    # Example: row["name"] instead of row[0]
    conn.row_factory = sqlite3.Row
    
    # Foreign keys enable karo
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        yield conn        # Connection do
        conn.commit()     # Save karo
    except Exception:
        conn.rollback()   # Error hua → undo karo
        raise
    finally:
        conn.close()      # Hamesha close karo

# Helper Functions


def init_db():
    """
    Database tables banao (pehli baar run karne pe)
    schema.sql file se tables create hoti hain
    """
    with get_db() as db:
        with open("schema.sql", "r") as f:
            db.executescript(f.read())
    print("Database initialized!")


def query_one(sql, params=()):
    """
    Single row fetch karo
    
    Example:
        student = query_one(
            "SELECT * FROM students WHERE rfid_uid = ?",
            ("A1B2C3D4",)
        )
        print(student["name"])  # "Raj Kumar"
    
    Returns: dict ya None (agar nahi mila)
    """
    with get_db() as db:
        cursor = db.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def query_all(sql, params=()):
    """
    Multiple rows fetch karo
    
    Example:
        students = query_all(
            "SELECT * FROM students WHERE room_id = ?",
            (1,)
        )
        for s in students:
            print(s["name"])
    
    Returns: list of dicts
    """
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def execute(sql, params=()):
    """
    INSERT / UPDATE / DELETE karo
    
    Example:
        execute(
            "INSERT INTO attendance (student_id, exam_date) VALUES (?, ?)",
            (1, "2026-08-11")
        )
    
    Returns: last inserted row id
    """
    with get_db() as db:
        cursor = db.execute(sql, params)
        return cursor.lastrowid

if __name__ == "__main__":
    # Database banana
    init_db()
    
    # Test student insert 
    execute("""
        INSERT OR IGNORE INTO students 
        (roll_no, name, branch, room_id, rfid_uid, face_encoding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("2020001", "Raj Kumar", "CSE", 1, "A1B2C3D4", b"dummy_encoding"))
    
    # Test student fetch
    student = query_one(
        "SELECT * FROM students WHERE rfid_uid = ?",
        ("A1B2C3D4",)
    )
    
    if student:
        print(f" Student found: {student['name']}")
        print(f"   Branch: {student['branch']}")
        print(f"   Room: {student['room_id']}")
    else:
        print(" Student not found")
    
    # Test all students
    all_students = query_all("SELECT * FROM students")
    print(f"\n Total students in DB: {len(all_students)}")