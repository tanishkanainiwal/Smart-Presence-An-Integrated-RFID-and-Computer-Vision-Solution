import numpy as np

FACE_MATCH_TOLERANCE = 0.5
DUMMY_MODE = True


def verify_face(jpeg_bytes, stored_encoding_bytes):
    if DUMMY_MODE:
        print("DUMMY MODE — always matched")
        return True, 1.0

    try:
        import cv2
        import face_recognition

        np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return False, 0.0

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if not face_locations:
            print("No face detected")
            return False, 0.0

        live_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
        distances = face_recognition.face_distance(live_encodings, stored_encoding)
        best_distance = float(np.min(distances))
        confidence = round(1.0 - best_distance, 2)
        matched = best_distance <= FACE_MATCH_TOLERANCE

        print(f"Distance: {best_distance:.3f}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Result: {'MATCH' if matched else 'NO MATCH'}")

        return matched, confidence

    except ImportError:
        print("face_recognition/cv2 not installed — Pi pe chalega")
        return False, 0.0

    except Exception as e:
        print(f"Error: {e}")
        return False, 0.0


def encode_face_from_photo(photo_path):
    try:
        import face_recognition

        image = face_recognition.load_image_file(photo_path)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            print(f"No face found: {photo_path}")
            return None

        return encodings[0].tobytes()

    except ImportError:
        print("face_recognition not installed")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    print("=== Face Module Test ===\n")

    print("Test 1: Dummy mode")
    matched, confidence = verify_face(b"fake", b"fake")
    print(f"Matched: {matched}, Confidence: {confidence}\n")

    DUMMY_MODE = False
    print("Test 2: Real mode")
    matched, confidence = verify_face(b"fake", b"fake")
    print(f"Matched: {matched}, Confidence: {confidence}\n")

    print("Done!")