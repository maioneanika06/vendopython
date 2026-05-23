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

ARDUINO_PORT = '/dev/ttyACM0'
ARDUINO_BAUDRATE = 9600
ARDUINO_LOCK_PATH = Path('/tmp/vendy_arduino.lock')
RAW_PRINTER_PATHS = (
    Path('/dev/usb/lp0'),
    Path('/dev/usb/lp1'),
)

@contextmanager
def arduino_connection():
    lock_file = ARDUINO_LOCK_PATH.open('a+')
    arduino = None

    try:
        if fcntl:
            print("[HARDWARE] Waiting for Arduino dispense lock...")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=1)
        time.sleep(2) 
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
    try:
        with arduino_connection() as arduino:
            command = f"{target_slot}\n"
            arduino.write(command.encode('utf-8'))
            arduino.flush()
            print(f"Command sent: Dispensing Slot {target_slot}")

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                print(f"Arduino replied: {line}")
                if line == "DONE":
                    print(f"Dispense confirmed for Slot {target_slot}.")
                    return True
                if line == "FAILED":
                    print(f"[HARDWARE ERROR] Arduino did not confirm IR drop for Slot {target_slot}.")
                    return False

            print(f"[HARDWARE ERROR] Timeout waiting for DONE from Arduino.")
            return False
    except Exception as e:
        print(f"[HARDWARE ERROR] Dispense failed: {e}")
        return False

def print_id_sticker(user_name, company_name):
    print(f"[PRINTER] Printing sticker for {user_name}...")
    
    try:
        safe_name = clean_sticker_text(user_name or "Attendee")[:18]
        safe_company = clean_sticker_text(company_name or "N/A")[:18]
        tspl_cmd = build_printer_clear_command() + build_sticker_command(safe_name, safe_company)

        print(f"[PRINTER] Sending sticker data: name='{safe_name}', company='{safe_company}'")
        if send_raw_printer(tspl_cmd):
            return True

        print("[PRINTER] Raw printer device unavailable. Falling back to PyUSB.")
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

        bytes_written = endpoint.write(tspl_cmd)
        time.sleep(0.5)
        usb.util.dispose_resources(printer_dev)
        print(f"[PRINTER] Sticker print command sent ({bytes_written} bytes).")
        return True

    except Exception as e:
        print(f"[PRINTER ERROR] {e}")
        return False

def clean_sticker_text(value):
    """Keep TSPL text fields on one command line and inside their quotes."""
    return str(value).replace('"', "'").replace('\r', ' ').replace('\n', ' ').strip()

def build_sticker_command(safe_name, safe_company):
    # Start with CR/LF and CLS so the printer does not repeat its previous label buffer.
    return (
        "SIZE 40 mm,30 mm\r\n"
        "GAP 2 mm,0 mm\r\n"
        "DIRECTION 0\r\n"
        "CLS\r\n"
        f'TEXT 20,40,"2",0,1,1,"{safe_name}"\r\n'
        f'TEXT 20,110,"2",0,1,1,"{safe_company}"\r\n'
        "PRINT 1\r\n"
    ).encode('utf-8')

def build_printer_clear_command():
    return b"\r\nCLS\r\n"

def send_raw_printer(tspl_cmd):
    for printer_path in RAW_PRINTER_PATHS:
        if not printer_path.exists():
            continue

        try:
            with printer_path.open('wb', buffering=0) as printer_file:
                printer_file.write(tspl_cmd)
                printer_file.flush()
            time.sleep(0.5)
            print(f"[PRINTER] Sticker print command sent through {printer_path}.")
            return True
        except Exception as e:
            print(f"[PRINTER] Could not write to {printer_path}: {e}")

    return False
