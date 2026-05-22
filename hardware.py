import serial
import time
import usb.core
import usb.util
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
PRINTER_LOCK_PATH = Path('/tmp/vendy_printer.lock')

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
        # The lock file closes on every return path and releases flock on Linux.
        with PRINTER_LOCK_PATH.open('a+') as lock_file:
            if fcntl:
                print("[PRINTER] Waiting for sticker printer lock...")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            print("[PRINTER] Looking for USB sticker printer 2e3c:5750...")
            printer_dev = usb.core.find(idVendor=0x2e3c, idProduct=0x5750)
            if not printer_dev:
                print("[PRINTER ERROR] USB sticker printer not found.")
                return False

            if printer_dev.is_kernel_driver_active(0):
                print("[PRINTER] Detaching kernel driver from USB interface 0...")
                printer_dev.detach_kernel_driver(0)

            print("[PRINTER] Configuring USB printer...")
            printer_dev.set_configuration()
            cfg = printer_dev.get_active_configuration()
            intf = cfg[(0, 0)]
            endpoint = usb.util.find_descriptor(
                intf,
                custom_match=lambda ep: usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )

            if not endpoint:
                print("[PRINTER ERROR] Printer USB OUT endpoint not found.")
                return False

            safe_name = clean_sticker_text(user_name or "Attendee")[:18]
            safe_company = clean_sticker_text(company_name or "N/A")[:18]
            tspl_cmd = (
                "SIZE 40 mm,30 mm\r\n"
                "GAP 2 mm,0 mm\r\n"
                "DIRECTION 0\r\n"
                "CLS\r\n"
                f'TEXT 20,40,"2",0,1,1,"{safe_name}"\r\n'
                f'TEXT 20,110,"2",0,1,1,"{safe_company}"\r\n'
                "PRINT 1,1\r\n"
            )

            print(f"[PRINTER] Sending sticker data: name='{safe_name}', company='{safe_company}'")
            bytes_written = endpoint.write(tspl_cmd.encode('utf-8'))
            usb.util.dispose_resources(printer_dev)
            print(f"[PRINTER] Sticker print command sent ({bytes_written} bytes).")
            return True

    except Exception as e:
        print(f"[PRINTER ERROR] Hindi makapag-print: {e}")
        return False

def clean_sticker_text(value):
    """Keep TSPL text fields on one command line and inside their quotes."""
    return str(value).replace('"', "'").replace('\r', ' ').replace('\n', ' ').strip()
