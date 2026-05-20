import subprocess
import time
import sys

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

    # Hihintayin ng script na ito na matapos o isara ang mga screens
    left_process.wait()
    right_process.wait()

except KeyboardInterrupt:
    print("\n?? SYSTEM SHUTDOWN INITIATED...")
    # Kapag pinindot mo ang Ctrl+C, papatayin niya parehas ang Left at Right
    left_process.terminate()
    right_process.terminate()
    print("? System successfully closed.")