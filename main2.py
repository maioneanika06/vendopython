import subprocess
import time
import sys

left_process = None
right_process = None
printer_process = None

print("initializing system...")

try:
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
