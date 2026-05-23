import subprocess
import time
import sys
import shutil
import os
from pathlib import Path

PRINT_QUEUE_DIR = Path('/tmp/vendy_print_queue')

left_process = None
right_process = None
printer_process = None

print("initializing system...")

def stop_old_vendy_processes():
    current_pid = str(os.getpid())
    process_names = ("printer_worker.py", "left.py", "right.py")

    try:
        result = subprocess.run(
            ["pgrep", "-f", "|".join(process_names)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return

    pids = [
        pid.strip()
        for pid in result.stdout.splitlines()
        if pid.strip() and pid.strip() != current_pid
    ]
    if not pids:
        return

    print(f"[SYSTEM] Stopping old Vendy process(es): {', '.join(pids)}")
    subprocess.run(["kill", *pids], check=False)
    time.sleep(0.5)

    still_running = []
    for pid in pids:
        check = subprocess.run(["kill", "-0", pid], capture_output=True, check=False)
        if check.returncode == 0:
            still_running.append(pid)

    if still_running:
        print(f"[SYSTEM] Force stopping old Vendy process(es): {', '.join(still_running)}")
        subprocess.run(["kill", "-9", *still_running], check=False)

try:
    stop_old_vendy_processes()

    if PRINT_QUEUE_DIR.exists():
        shutil.rmtree(PRINT_QUEUE_DIR)
        print(f"[SYSTEM] Cleared stale print queue: {PRINT_QUEUE_DIR}")

    print("Starting PRINTER worker...")
    printer_process = subprocess.Popen([sys.executable, "printer_worker.py"])
    time.sleep(0.5)

    print("Starting LEFT screen...")
    left_process = subprocess.Popen([sys.executable, "left.py"])
    time.sleep(1)
    
    print("Starting RIGHT screen...")
    right_process = subprocess.Popen([sys.executable, "right.py"])

    while True:
        left_code = left_process.poll()
        right_code = right_process.poll()
        printer_code = printer_process.poll()

        if printer_code is not None:
            print(f"[SYSTEM] PRINTER worker exited with code {printer_code}.")
            break
        if left_code is not None:
            print(f"[SYSTEM] LEFT screen exited with code {left_code}.")
            break
        if right_code is not None:
            print(f"[SYSTEM] RIGHT screen exited with code {right_code}.")
            break

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n?? SYSTEM SHUTDOWN INITIATED...")
finally:
    for name, process in (("LEFT", left_process), ("RIGHT", right_process), ("PRINTER", printer_process)):
        if process and process.poll() is None:
            print(f"[SYSTEM] Stopping {name} screen...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    print("? System successfully closed.")
