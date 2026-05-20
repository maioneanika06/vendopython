import serial
import usb.core
import usb.util
import time

# ==========================================
# ?? HARDWARE SETTINGS
# ==========================================
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

# Subukang i-connect ang Arduino nang isang beses sa background
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
    time.sleep(2) # Bigyan ng oras mag-initialize
    print("[HARDWARE] Arduino Connected Successfully.")
except Exception as e:
    arduino = None
    print(f"[HARDWARE WARNING] Hindi ma-connect ang Arduino: {e}")

def dispense_item(slot):
    """Nagpapadala ng target slot papunta sa Arduino"""
    if arduino:
        try:
            arduino.write(f"{slot}\n".encode())
            print(f"[HARDWARE] Signal sent to dispense Slot {slot}")
            return True
        except Exception as e:
            print(f"[HARDWARE ERROR] Failed to send to Arduino: {e}")
            return False
    else:
        print(f"[HARDWARE SIMULATION] Dispensing Slot {slot} (Arduino not connected)")
        return False
    
def print_id_sticker(name, company):
    """Nagpi-print ng ID gamit ang Thermal Printer (TSPL)"""
    try:
        printer_dev = usb.core.find(idVendor=0x2e3c, idProduct=0x5750)
        if printer_dev:
            if printer_dev.is_kernel_driver_active(0): 
                printer_dev.detach_kernel_driver(0)
            
            printer_dev.set_configuration()
            cfg = printer_dev.get_active_configuration()
            intf = cfg[(0,0)]
            ep = usb.util.find_descriptor(
                intf, 
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)==usb.util.ENDPOINT_OUT
            )
            
            # --- TSPL COMMAND PARA SA ID STICKER ---
            tspl_cmd = (
                f"\r\nSIZE 40 mm,30 mm\n"
                f"GAP 2 mm,0 mm\n"
                f"DIRECTION 0\n"
                f"CLS\n"
                f"TEXT 20,40,\"2\",0,1,1,\"{name[:18]}\"\n"
                f"TEXT 20,110,\"2\",0,1,1,\"{company[:18]}\"\n"
                f"PRINT 1\r\n"
            )
            
            ep.write(tspl_cmd.encode('utf-8'))
            usb.util.dispose_resources(printer_dev)
            print("[HARDWARE] ID Sticker Printed!")
            return True
        else:
            print("[HARDWARE ERROR] Printer not detected via USB.")
            return False
    except Exception as e:
        print(f"[HARDWARE ERROR] Printer Issue: {e}")
        return False