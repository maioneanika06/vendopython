import shutil

from printer_queue import PRINT_QUEUE_DIR

if PRINT_QUEUE_DIR.exists():
    shutil.rmtree(PRINT_QUEUE_DIR)
    print(f"Deleted {PRINT_QUEUE_DIR}")
else:
    print(f"No print queue found at {PRINT_QUEUE_DIR}")
