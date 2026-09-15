"""
enroll_student.py
Real students ko register karne ke liye
Ye script Raspberry Pi pe chalegi 

Kya karta hai:
1. Student ki photo se face encoding nikalta hai
2. RFID card ka UID store karta hai
3. Database mein student add karta hai
"""

import os
from database import execute, query_one, init_db


# SINGLE STUDENT ENROLL
def enroll_student(name, roll_no, branch, room_id, rfid_uid, photo_path):
    """
    Args:
        name      : "Raj Kumar"
        roll_no   : "2020001"
        branch    : "CSE"
        room_id   : 1 (1, 2, 3, ya 4)
        rfid_uid  : "A1B2C3D4" (card se padha hua UID)
        photo_path: "photos/raj.jpg"
    """

    print(f"\nEnrolling: {name} ({roll_no})")

    # Step 1: Photo exist karti hai?
    if not os.path.exists(photo_path):
        print(f" Photo nahi mili: {photo_path}")
        return False

    # Step 2: Face encoding 

    try:
        import face_recognition
        image = face_recognition.load_image_file(photo_path)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            print(f" Photo mein face nahi mila!")
            return False

        encoding_bytes = encodings[0].tobytes()
        print(f" Face encoding generated (128 floats)")

    except ImportError:
        # PC pe test ke liye dummy encoding
        print(f" face_recognition not installed — dummy encoding use ho rahi hai")
        print(f"      (Pi pe real encoding generate hogi)")
        import numpy as np
        dummy = np.zeros(128, dtype=np.float64)
        encoding_bytes = dummy.tobytes()

    # Step 3: Already registered hai
    existing = query_one(
        "SELECT * FROM students WHERE roll_no = ? OR rfid_uid = ?",
        (roll_no, rfid_uid)
    )

    if existing:
        print(f" Already registered: {existing['name']} ({existing['roll_no']})")
        print(f"      Update karna hai? (y/n): ", end="")
        choice = input().strip().lower()

        if choice == 'y':
            execute("""
                UPDATE students
                SET name=?, branch=?, room_id=?, rfid_uid=?, face_encoding=?
                WHERE roll_no=?
            """, (name, branch, room_id, rfid_uid, encoding_bytes, roll_no))
            print(f" Updated: {name}")
            return True
        else:
            print(f"Skipped: {name}")
            return False

    # Step 4: Database mein insert 
    execute("""
        INSERT INTO students
        (name, roll_no, branch, room_id, rfid_uid, face_encoding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, roll_no, branch, room_id, rfid_uid, encoding_bytes))

    print(f"Enrolled successfully!")
    return True



# BULK ENROLL — CSV file se
def enroll_from_csv(csv_path):
    """
    CSV file se saare students ek saath enroll
    CSV format:
    name, roll_no, branch, room_id, rfid_uid, photo_path
    Example CSV (students.csv):
    Raj Kumar,2020001,CSE,1,A1B2C3D4,photos/raj.jpg
    Priya Sharma,2020002,CSE,1,E5F6G7H8,photos/priya.jpg
    """
    import csv

    if not os.path.exists(csv_path):
        print(f"CSV file nahi mili: {csv_path}")
        return

    print(f"\nBulk enrollment from: {csv_path}")
    print("=" * 50)

    success = 0
    failed = 0

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)

        # Header skip agar h
        first_row = next(reader)
        if first_row[0].lower() == 'name':
            print("Header row skipped")
        else:
            # Header nahi hai — pehli row bhi process 
            name, roll_no, branch, room_id, rfid_uid, photo = first_row
            result = enroll_student(
                name.strip(), roll_no.strip(), branch.strip(),
                int(room_id), rfid_uid.strip().upper(), photo.strip()
            )
            if result: success += 1
            else: failed += 1

        # Baaki rows
        for row in reader:
            if not row or len(row) < 6:
                continue
            name, roll_no, branch, room_id, rfid_uid, photo = row
            result = enroll_student(
                name.strip(), roll_no.strip(), branch.strip(),
                int(room_id), rfid_uid.strip().upper(), photo.strip()
            )
            if result: success += 1
            else: failed += 1

    print("\n" + "=" * 50)
    print(f"Successfully enrolled: {success}")
    print(f"Failed: {failed}")
    print(f"Total processed: {success + failed}")

# RFID UID READ HELPER
def print_registered_students():
    """Saare registered students dikhao"""
    from database import query_all
    students = query_all(
        "SELECT * FROM students ORDER BY room_id, roll_no"
    )

    if not students:
        print("Koi student registered nahi hai")
        return

    print(f"\n{'='*60}")
    print(f"{'S.No':<5} {'Name':<20} {'Roll No':<12} {'Branch':<8} {'Room':<6} {'RFID UID'}")
    print(f"{'='*60}")

    for i, s in enumerate(students, 1):
        print(f"{i:<5} {s['name']:<20} {s['roll_no']:<12} {s['branch']:<8} {s['room_id']:<6} {s['rfid_uid']}")

    print(f"{'='*60}")
    print(f"Total: {len(students)} students\n")


# MAIN MENU
if __name__ == "__main__":
    print("=" * 50)
    print("  SmartPresence — Student Enrollment")
    print("  IIT Indore")
 
    # Database ready karo
    init_db()
    while True:
        print("\nOptions:")
        print("1. Single student enroll karo")
        print("2. Bulk enroll (CSV se)")
        print("3. Registered students dekho")
        print("4. Exit")
        print("\nChoice: ", end="")

        choice = input().strip()

        if choice == "1":
            print("\n--- Single Student Enrollment ---")
            print("Name: ", end="")
            name = input().strip()

            print("Roll No: ", end="")
            roll_no = input().strip()

            print("Branch (CSE/ECE/MECH/CIVIL): ", end="")
            branch = input().strip().upper()

            print("Room ID (1/2/3/4): ", end="")
            room_id = int(input().strip())

            print("RFID UID (card tap karke note karo): ", end="")
            rfid_uid = input().strip().upper()

            print("Photo path (e.g. photos/raj.jpg): ", end="")
            photo_path = input().strip()

            enroll_student(name, roll_no, branch, room_id, rfid_uid, photo_path)

        elif choice == "2":
            print("\nCSV file path (e.g. students.csv): ", end="")
            csv_path = input().strip()
            enroll_from_csv(csv_path)

        elif choice == "3":
            print_registered_students()

        elif choice == "4":
            print("\nBye!")
            break

        else:
            print("Invalid choice — 1, 2, 3, ya 4 likho")