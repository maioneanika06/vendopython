import time

import cv2
import face_recognition
import numpy as np

FACE_MATCH_TOLERANCE = 0.50
FACE_MISMATCH_TOLERANCE = 0.62
REQUIRED_CONSECUTIVE_MATCHES = 2
REQUIRED_CONSECUTIVE_MISMATCHES = 4
FACE_SCAN_TIMEOUT = 20
FACE_PROCESS_INTERVAL = 0.18
FACE_RESIZE_SCALE = 0.35

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
    next_process_time = 0

    while time.time() - start_time < FACE_SCAN_TIMEOUT:
        now = time.time()
        if now < next_process_time:
            time.sleep(0.02)
            continue
        next_process_time = now + FACE_PROCESS_INTERVAL

        frame = get_current_frame()
        if frame is None:
            time.sleep(0.03)
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        small_frame = cv2.resize(
            rgb_frame,
            (0, 0),
            fx=FACE_RESIZE_SCALE,
            fy=FACE_RESIZE_SCALE,
        )
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
        elif distance >= FACE_MISMATCH_TOLERANCE:
            consecutive_matches = 0
            consecutive_mismatches += 1
            if consecutive_mismatches >= REQUIRED_CONSECUTIVE_MISMATCHES:
                print(f"[{side_name}] Face mismatch. Best distance: {best_distance:.3f}.")
                return "mismatch"
        else:
            consecutive_matches = 0
            consecutive_mismatches = 0

    if best_distance is None:
        print(f"[{side_name}] Face verification failed: no usable face detected.")
        return "no_face"
    else:
        print(f"[{side_name}] Face verification failed. Best distance: {best_distance:.3f}.")
        return "timeout"
