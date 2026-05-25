import time

import cv2
import face_recognition
import numpy as np

FACE_MATCH_TOLERANCE = 0.42
REQUIRED_CONSECUTIVE_MATCHES = 3
REQUIRED_CONSECUTIVE_MISMATCHES = 5
FACE_SCAN_TIMEOUT = 20

def normalize_registered_encoding(raw_encoding):
    encoding = np.asarray(raw_encoding, dtype=np.float64)
    if encoding.shape != (128,) or not np.isfinite(encoding).all():
        raise ValueError(f"Invalid face encoding shape: {encoding.shape}")
    return encoding

def verify_face(get_current_frame, registered_encoding, side_name):
    consecutive_matches = 0
    consecutive_mismatches = 0
    best_distance = None
    start_time = time.time()

    while time.time() - start_time < FACE_SCAN_TIMEOUT:
        frame = get_current_frame()
        if frame is None:
            time.sleep(0.03)
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        face_locs = face_recognition.face_locations(small_frame, model="hog")
        face_encs = face_recognition.face_encodings(small_frame, face_locs)

        if len(face_encs) != 1:
            consecutive_matches = 0
            consecutive_mismatches = 0
            if len(face_encs) > 1:
                print(f"[{side_name}] Face scan rejected: multiple faces detected.")
            continue

        distance = float(face_recognition.face_distance([registered_encoding], face_encs[0])[0])
        best_distance = distance if best_distance is None else min(best_distance, distance)
        print(f"[{side_name}] Face distance: {distance:.3f} (best {best_distance:.3f})")

        if distance <= FACE_MATCH_TOLERANCE:
            consecutive_matches += 1
            consecutive_mismatches = 0
            if consecutive_matches >= REQUIRED_CONSECUTIVE_MATCHES:
                print(f"[{side_name}] Face verified with distance {distance:.3f}.")
                return "matched"
        else:
            consecutive_matches = 0
            consecutive_mismatches += 1
            if consecutive_mismatches >= REQUIRED_CONSECUTIVE_MISMATCHES:
                print(f"[{side_name}] Face mismatch. Best distance: {best_distance:.3f}.")
                return "mismatch"

    if best_distance is None:
        print(f"[{side_name}] Face verification failed: no usable face detected.")
        return "no_face"
    else:
        print(f"[{side_name}] Face verification failed. Best distance: {best_distance:.3f}.")
        return "timeout"
