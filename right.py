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
from pyzbar.pyzbar import decode
import hardware
import config
from gui import VendoUI
from modules.database import deduct_inventory, fetch_attendee, get_active_event_name, get_available_slot, mark_attendee_claimed, normalize_inventory_role

SIDE_NAME = "RIGHT"
CAM_INDEX = 2
BTN_PIN = 23   
X_POSITION = 1024



ctk.set_appearance_mode("dark")

class RightVendoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry(f"{config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT}+{X_POSITION}+0")
        self.title(f"Vendy - {SIDE_NAME}")
        self.attributes('-fullscreen', True)
        
        self.ui = VendoUI(self)
        self.ui.show_idle_view()  # Start with beautiful Idle View
        current_event_name = get_active_event_name()
        self.ui.update_event_name(current_event_name)

        self.is_processing = False
        self.camera_active = False
        self.current_frame = None
        self.cap = None

        self.blank_pil = Image.new('RGB', (640, 480), color=config.COLORS["card"])
        self.blank_ctk = ctk.CTkImage(light_image=self.blank_pil, dark_image=self.blank_pil, size=(640, 480))
        self.current_ctk_image = self.blank_ctk 

        self.update_video_feed()
        
        try:
            self.btn = Button(BTN_PIN, pull_up=True, bounce_time=0.1)
            self.btn.when_pressed = self.on_button_press
            print(f"[{SIDE_NAME}] Button ready on GPIO {BTN_PIN}.")
        except Exception as e:
            self.btn = None
            print(f"[{SIDE_NAME} BUTTON ERROR] GPIO {BTN_PIN} unavailable: {e}")
            self.bind('<Button-1>', lambda e: self.on_button_press())
            
        self.bind('<Escape>', self.close_app)

    def safe_update_ui(self, status, msg, color):
        self.after(0, lambda: self.ui.update_texts(status, msg, color))

    def safe_set_camera_state(self, is_active):
        def toggle_cam():
            self.camera_active = is_active
            if is_active:
                self.ui.show_active_view()  # Show camera and status when active
                self.cap = cv2.VideoCapture(CAM_INDEX)
            else:
                if self.cap:
                    self.cap.release()
                    self.cap = None
                self.ui.set_camera_off(self.blank_ctk)
                self.current_ctk_image = self.blank_ctk 
        self.after(0, toggle_cam)

    def update_video_feed(self):
        if self.camera_active and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.current_frame = frame
                cv2_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cv2_rgb)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(640, 480))
                
                self.ui.update_camera_image(ctk_img)
                self.current_ctk_image = ctk_img 
        self.after(30, self.update_video_feed)

    def on_button_press(self):
        if self.is_processing:
            print(f"[{SIDE_NAME}] Button press ignored while vending sequence is active.")
            return
        print(f"[{SIDE_NAME}] Button press accepted.")
        self.is_processing = True
        threading.Thread(target=self.vending_sequence, daemon=True).start()


    def vending_sequence(self):
        try:
            self.safe_update_ui("SCAN QR", "Please show your QR Code to the camera", config.COLORS["scan"])
            self.safe_set_camera_state(True)
            
            qr_id = None
            start_time = time.time()
            time.sleep(1) 
            
            while time.time() - start_time < 30:
                if self.current_frame is not None:
                    gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
                    barcodes = decode(gray)
                    for barcode in barcodes:
                        qr_id = barcode.data.decode('utf-8').strip()
                        break
                    if qr_id: break

            if not qr_id:
                self.safe_update_ui("TIMEOUT", "No QR detected. Please try again.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            self.safe_update_ui("VERIFYING", "Verifying QR Code, please wait...", config.COLORS["warning"])
            user_data = fetch_attendee(qr_id)
            
            if not user_data or 'face_encoding' not in user_data:
                self.safe_update_ui("ERROR", "Invalid QR or Face Data missing", config.COLORS["error"])
                self.cleanup_and_reset()
                return
                
            user_name = user_data.get('full_name', 'Attendee').upper()
            user_type = normalize_inventory_role(user_data.get('role', 'Attendee'))
            registered_encoding = np.array(user_data['face_encoding'])
            
            self.safe_update_ui("Welcome", f"{user_name}!", config.COLORS["success"])
            time.sleep(1.5)
            
            self.safe_update_ui("FACE SCAN", "Please look directly at the camera", config.COLORS["scan"])
            face_matched = False
            start_time = time.time()
            
            while time.time() - start_time < 20:
                if self.current_frame is not None:
                    rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
                    face_locs = face_recognition.face_locations(small_frame)
                    face_encs = face_recognition.face_encodings(small_frame, face_locs)
                    
                    for enc in face_encs:
                        match = face_recognition.compare_faces([registered_encoding], enc, tolerance=0.5)
                        if True in match:
                            face_matched = True
                            break
                    if face_matched: break

            if not face_matched:
                self.safe_update_ui("ERROR", "Face verification failed!", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            self.safe_update_ui("FACE MATCHED", "Face Verification Complete", config.COLORS["success"])
            time.sleep(1.5)

            target_slot = get_available_slot(user_type, SIDE_NAME)
            if not target_slot:
                self.safe_update_ui("OUT OF STOCK", f"No items left for {user_type.upper()}", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            self.safe_update_ui("DISPENSING", f"Dropping item from Slot {target_slot}...", config.COLORS["success"])
            
            success = hardware.dispense_item(target_slot)
            if not success:
                self.safe_update_ui("HARDWARE ERROR", "Item was not confirmed. Please call staff.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            deduct_inventory(target_slot)
            mark_attendee_claimed(user_data['id'])
            print_success = hardware.print_id_sticker(user_name, user_data.get('company', ''))
            print(f"[{SIDE_NAME}] Sticker print success: {print_success}")

            time.sleep(4)
            self.safe_update_ui("SUCCESS", "Thank you! Please claim your item below.", config.COLORS["success"])
            self.cleanup_and_reset()

        except Exception as e:
            print(f"[ERROR] Vending Sequence: {e}")
            self.cleanup_and_reset()

    def cleanup_and_reset(self):
        self.safe_set_camera_state(False)
        time.sleep(1)
        self.ui.show_idle_view()  # Return to beautiful Idle View
        self.is_processing = False

    def close_app(self, event=None):
        if self.btn:
            self.btn.close()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = RightVendoGUI()
    app.mainloop()
