import serial
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None
# from escpos.printer import Usb  # ?? Tanggalin ang '#' kung gamit niyo ay standard ESC/POS USB Printer

# ==========================================
# ?? ARDUINO CONNECTION
# ==========================================
ARDUINO_PORT = '/dev/ttyACM0'
ARDUINO_BAUDRATE = 9600
ARDUINO_LOCK_PATH = Path('/tmp/vendy_arduino.lock')

@contextmanager
def arduino_connection():
    lock_file = ARDUINO_LOCK_PATH.open('a+')
    arduino = None

    try:
        if fcntl:
            print("[HARDWARE] Waiting for Arduino dispense lock...")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=1)
        time.sleep(2) # Opening serial can reset the Arduino.
        arduino.reset_input_buffer()
        print("[HARDWARE] Arduino Connected Successfully.")
        yield arduino
    finally:
        if arduino:
            arduino.close()
        if fcntl:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

# ==========================================
# ?? DISPENSE LOGIC
# ==========================================
def dispense_item(target_slot):
    """Nagpapadala ng numero sa Arduino at naghihintay ng DONE confirmation."""
    try:
        with arduino_connection() as arduino:
            command = f"{target_slot}\n"
            arduino.write(command.encode('utf-8'))
            arduino.flush()
            print(f"[HARDWARE] Command sent: Dispensing Slot {target_slot}")

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                print(f"[HARDWARE] Arduino replied: {line}")
                if line == "DONE":
                    print(f"[HARDWARE] Dispense confirmed for Slot {target_slot}.")
                    return True

            print(f"[HARDWARE ERROR] Timeout waiting for DONE from Arduino.")
            return False
    except Exception as e:
        print(f"[HARDWARE ERROR] Dispense failed: {e}")
        return False

# ==========================================
# ??? PRINTER LOGIC
# ==========================================
def print_id_sticker(user_name, company_name):
    """Mag-print ng ID Sticker gamit ang Thermal Printer"""
    print(f"[PRINTER] Printing sticker for {user_name}...")
    
    try:
        # ?? KUNG GAGAMIT KAYO NG ESC/POS PRINTER, HETO ANG STANDARD CODE:
        # (Palitan ang 0x04b8 at 0x0202 ng mismong USB Vendor ID at Product ID ng printer niyo)
        
        """
        p = Usb(0x04b8, 0x0202, 0, 0x81, 0x01)
        
        # Design ng Sticker
        p.set(align='center', text_type='B', width=2, height=2)
        p.text("VENDY EVENT 2026\n\n")
        
        p.set(align='center', text_type='B', width=3, height=3)
        p.text(f"{user_name}\n") # Pangalan ng Attendee
        
        p.set(align='center', text_type='normal', width=1, height=1)
        p.text(f"{company_name}\n\n") # Company o Role
        
        p.cut()
        print("[PRINTER] Success!")
        """
        
        # ?? KUNG MAY LUMA KAYONG CODE PARA SA PRINTER KAGABI, I-PASTE MO DITO PABABA!
        pass 

    except Exception as e:
        print(f"[PRINTER ERROR] Hindi makapag-print: {e}")
