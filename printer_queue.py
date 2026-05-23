import json
import time
from pathlib import Path
from uuid import uuid4

PRINT_QUEUE_DIR = Path('/tmp/vendy_print_queue')

def enqueue_print_job(side_name, attendee_id, user_name, company_name):
    PRINT_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    job = {
        'id': uuid4().hex,
        'created_at': time.time(),
        'side': side_name,
        'attendee_id': attendee_id,
        'user_name': str(user_name or 'Attendee'),
        'company_name': str(company_name or 'N/A'),
    }

    final_path = PRINT_QUEUE_DIR / f"{int(job['created_at'] * 1000)}-{job['id']}.json"
    temp_path = final_path.with_suffix('.tmp')
    temp_path.write_text(json.dumps(job), encoding='utf-8')
    temp_path.replace(final_path)

    print(
        f"[PRINT QUEUE] Queued job {job['id']} "
        f"side={side_name} attendee={attendee_id} name={job['user_name']}"
    )
    return job['id']
