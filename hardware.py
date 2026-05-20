import serial
import time
# from escpos.printer import Usb  # ?? Tanggalin ang '#' kung gamit niyo ay standard ESC/POS USB Printer

# ==========================================
# ?? ARDUINO CONNECTION
# ==========================================
try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2) # Bigyan ng 2 seconds ang Arduino para mag-initialize
    print("[HARDWARE] Arduino Connected Successfully.")
except Exception as e:
    print(f"[HARDWARE WARNING] Hindi ma-connect ang Arduino: {e}")
    arduino = None

# ==========================================
# ?? DISPENSE LOGIC
# ==========================================
def dispense_item(target_slot):
    """Nagpapadala ng numero sa Arduino para paikutin ang motor"""
    if arduino:
        command = f"{target_slot}\n"
        arduino.write(command.encode('utf-8'))
        print(f"[HARDWARE] Command sent: Dispensing Slot {target_slot}")
    else:
        print(f"[HARDWARE SIMULATION] Arduino not connected. Supposed to drop Slot {target_slot}.")

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