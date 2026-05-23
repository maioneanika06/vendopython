import json
import time

import hardware
from printer_queue import PRINT_QUEUE_DIR

DONE_DIR = PRINT_QUEUE_DIR / 'done'
FAILED_DIR = PRINT_QUEUE_DIR / 'failed'

def read_job(path):
    return json.loads(path.read_text(encoding='utf-8'))

def move_finished(path, target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    path.replace(target_dir / path.name.replace('.printing', '.json'))

def claim_next_job():
    PRINT_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    jobs = sorted(PRINT_QUEUE_DIR.glob('*.json'))
    if not jobs:
        return None

    job_path = jobs[0]
    claimed_path = job_path.with_suffix('.printing')
    try:
        job_path.replace(claimed_path)
        return claimed_path
    except FileNotFoundError:
        return None

def process_job(path):
    job = read_job(path)
    print(
        f"[PRINT WORKER] Printing job {job.get('id')} "
        f"side={job.get('side')} attendee={job.get('attendee_id')} "
        f"name={job.get('user_name')}"
    )

    success = hardware.print_id_sticker(
        job.get('user_name', 'Attendee'),
        job.get('company_name', 'N/A'),
    )

    if success:
        move_finished(path, DONE_DIR)
        print(f"[PRINT WORKER] Done job {job.get('id')}")
    else:
        move_finished(path, FAILED_DIR)
        print(f"[PRINT WORKER] Failed job {job.get('id')}")

def main():
    print("[PRINT WORKER] Started.")
    while True:
        job_path = claim_next_job()
        if not job_path:
            time.sleep(0.2)
            continue

        try:
            process_job(job_path)
        except Exception as e:
            print(f"[PRINT WORKER ERROR] {e}")
            try:
                move_finished(job_path, FAILED_DIR)
            except Exception:
                pass

if __name__ == "__main__":
    main()
