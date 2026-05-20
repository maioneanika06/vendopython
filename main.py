import os
os.environ["QT_QPA_PLATFORM"] = "xcb" 

import cv2
import face_recognition
import numpy as np
import time
import serial
import usb.core
import usb.util
import sys
import threading
import customtkinter as ctk
from PIL import Image
from gpiozero import Button

from modules.database import fetch_attendee, get_available_slot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


print("Initializing Hardware...")
try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=10)
    time.sleep(2)
    print("[OK] Arduino Connected")
except:
    arduino = None
    print("[WARN] Arduino not found")

try:
    printer_dev = usb.core.find(idVendor=0x2e3c, idProduct=0x5750)
    if printer_dev:
        if printer_dev.is_kernel_driver_active(0): 
            printer_dev.detach_kernel_driver(0)
        printer_dev.set_configuration()
        print("[OK] Printer Connected")
except:
    printer_dev = None
    print("[WARN] Printer not found")


class VendoKiosk(ctk.CTkToplevel):
    def __init__(self, master, side_name, cam_index, btn_pin, x_position):
        super().__init__(master)
        
        self.side = side_name
        self.cam_index = cam_index
        
        self.geometry(f"1920x1080+{x_position}+0")
        self.title(f"{self.side} VENDO")
        self.attributes('-fullscreen', True)
        
        # UI Elements
        self.status_label = ctk.CTkLabel(self, text="IDLE", font=("Helvetica", 60, "bold"), text_color="#FFD700")
        self.status_label.pack(pady=(100, 20))
        
        self.msg_label = ctk.CTkLabel(self, text="PRESS THE BUTTON TO START", font=("Helvetica", 35))
        self.msg_label.pack(pady=(0, 50))
        
        self.video_label = ctk.CTkLabel(self, text="CAMERA OFF", width=640, height=480, fg_color="#1a1a1a", corner_radius=20, font=("Helvetica", 20))
        self.video_label.pack()

        self.is_processing = False
        self.current_frame = None
        self.camera_active = False
        
        try:
            self.btn = Button(btn_pin, pull_up=True)
            self.btn.when_pressed = self.on_button_press
            print(f"[OK] {self.side} Button Ready on GPIO {btn_pin}")
        except:
            self.bind('<Button-1>', lambda e: self.on_button_press()) 

    def update_ui(self, status, msg, color="#FFFFFF"):
        self.status_label.configure(text=status, text_color=color)
        self.msg_label.configure(text=msg)

    def update_video_feed(self):
        if self.camera_active and self.current_frame is not None:
            cv2_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv2_rgb)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(640, 480))
            self.video_label.configure(image=ctk_img, text="")
        elif not self.camera_active:
            self.video_label.configure(image=None, text="CAMERA OFF")

        if self.camera_active:
            self.after(30, self.update_video_feed)

    def on_button_press(self):
        if self.is_processing: return
        self.is_processing = True
        threading.Thread(target=self.vending_sequence, daemon=True).start()

    def vending_sequence(self):
        try:
            # --- STEP 1: SCAN QR ---
            self.update_ui("STEP 1: SCAN QR", "PLEASE ALIGN YOUR QR CODE", "#00D7FF")
            cap = cv2.VideoCapture(self.cam_index)
            self.camera_active = True
            self.after(0, self.update_video_feed)
            
            qr_detector = cv2.QRCodeDetector()
            qr_id = None
            start_time = time.time()
            
            while time.time() - start_time < 60: #may 1 min para mag scan qr to avoid too much sa webcam
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame
                    qr_raw, _, _ = qr_detector.detectAndDecode(frame)
                    if qr_raw:
                        qr_id = qr_raw.strip()
                        break

            if not qr_id:
                self.update_ui("TIMEOUT", "NO QR DETECTED. PLEASE TRY AGAIN.", "#FF0000")
                self.cleanup_and_reset(cap)
                return
            

            self.update_ui("VERIFYING", "FETCHING DATABASE...", "#FFD700")
            user_data = fetch_attendee(qr_id)
            
            if not user_data or 'face_encoding' not in user_data:
                self.update_ui("ERROR", "INVALID QR OR NO FACE DATA", "#FF0000")
                self.cleanup_and_reset(cap)
                return
                
            user_name = user_data.get('full_name', 'Attendee').upper()
            user_company = user_data.get('company', 'N/A')
            user_type = user_data.get('role', 'Attendee').capitalize()
            registered_encoding = np.array(user_data['face_encoding'])
            
            self.update_ui("MATCH FOUND!", f"HELLO, {user_name}!", "#00FF00")
            time.sleep(1.5)
            
            # --- STEP 3: TOTOONG FACE SCAN (Galing sa code mo) ---
            self.update_ui("STEP 2: FACE VERIFICATION", "PLEASE LOOK AT THE CAMERA", "#00D7FF")
            
            face_matched = False
            start_time = time.time()
            
            while time.time() - start_time < 8: # 8 seconds to match
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locs = face_recognition.face_locations(rgb_frame)
                    face_encs = face_recognition.face_encodings(rgb_frame, face_locs)
                    
                    match_found_in_frame = False
                    for enc in face_encs:
                        match = face_recognition.compare_faces([registered_encoding], enc, tolerance=0.5)
                        if True in match:
                            match_found_in_frame = True
                            break
                    
                    if match_found_in_frame:
                        face_matched = True
                        break

            self.camera_active = False
            cap.release()

            if not face_matched:
                self.update_ui("ERROR", "FACE DOESN'T MATCH!", "#FF0000")
                time.sleep(3)
                self.reset_idle()
                return

            # --- STEP 4: DISPENSE & PRINT (Galing sa code mo) ---
            target_slot = get_available_slot(user_type)
            
            if not target_slot:
                self.update_ui("OUT OF STOCK!", f"NO ITEMS LEFT FOR {user_type.upper()}", "#FF0000")
                time.sleep(3)
                self.reset_idle()
                return

            self.update_ui("SUCCESS!", f"DISPENSING SLOT {target_slot}...", "#00FF00")
            
            # ARDUINO
            if arduino:
                try:
                    arduino.write(f"{target_slot}\n".encode())
                    arduino.readline()
                except:
                    print(f"[{self.side}] Arduino Error")


            if printer_dev:
                try:
                    cfg = printer_dev.get_active_configuration()
                    intf = cfg[(0,0)]
                    ep = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)==usb.util.ENDPOINT_OUT)
                    tspl_cmd = f"\r\nSIZE 40 mm,30 mm\nGAP 2 mm,0 mm\nDIRECTION 0\nCLS\nTEXT 20,40,\"2\",0,1,1,\"{user_name[:18]}\"\nTEXT 20,110,\"2\",0,1,1,\"{user_company[:18]}\"\nPRINT 1\r\n"
                    ep.write(tspl_cmd.encode('utf-8'))
                    usb.util.dispose_resources(printer_dev)
                except:
                    print(f"[{self.side}] Printer Error")

            time.sleep(4)
            self.update_ui("DONE", "THANK YOU! PLEASE CLAIM YOUR ITEM.", "#00FF00")
            time.sleep(3)
            self.reset_idle()

        except Exception as e:
            print(f"[{self.side}] Error: {e}")
            self.cleanup_and_reset(cap)

    def cleanup_and_reset(self, cap):
        self.camera_active = False
        if cap and cap.isOpened():
            cap.release()
        time.sleep(3)
        self.reset_idle()

    def reset_idle(self):
        self.camera_active = False
        self.current_frame = None
        self.is_processing = False
        self.update_ui("IDLE", "PRESS THE BUTTON TO START", "#FFD700")
        self.video_label.configure(image=None, text="CAMERA OFF")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        
        # Monitor 1 (Left) & Monitor 2 (Right)
        self.left_kiosk = VendoKiosk(self, "LEFT", cam_index=0, btn_pin=23, x_position=0)
        self.right_kiosk = VendoKiosk(self, "RIGHT", cam_index=2, btn_pin=22, x_position=1920)
        
        self.bind_all('<Escape>', self.close_all)

    def close_all(self, event=None):
        if arduino: arduino.close()
        if printer_dev: usb.util.dispose_resources(printer_dev)
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()