import subprocess
import time
import sys

left_process = None
right_process = None

print("=========================================")
print("?? STARTING VENDY DUAL-SCREEN SYSTEM...")
print("=========================================")

try:
    # Bubuksan nito ang dalawang files nang magkahiwalay pero sabay!
    print("Starting LEFT screen...")
    left_process = subprocess.Popen([sys.executable, "left.py"])
    time.sleep(1) # Bigyan ng 1 second para hindi mag-agawan sa memory
    
    print("Starting RIGHT screen...")
    right_process = subprocess.Popen([sys.executable, "right.py"])

    # Keep the launcher alive while both screens are running.
    while True:
        left_code = left_process.poll()
        right_code = right_process.poll()

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
    # Kapag tumigil ang isang screen, isara ang kabila para walang stale GPIO owner.
    for name, process in (("LEFT", left_process), ("RIGHT", right_process)):
        if process and process.poll() is None:
            print(f"[SYSTEM] Stopping {name} screen...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    print("? System successfully closed.")
