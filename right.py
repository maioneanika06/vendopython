import os
os.environ["QT_QPA_PLATFORM"] = "xcb" 

import cv2
import time
import sys
import threading
import customtkinter as ctk
from PIL import Image
from gpiozero import Button
from pyzbar.pyzbar import decode
import hardware
import config
from face_verify import normalize_registered_encoding, verify_face
from gui import VendoUI
from latency_logger import LatencyRun, now
from modules.database import deduct_inventory, fetch_attendee, get_active_event_name, get_available_slot, is_active_event, mark_attendee_claimed, normalize_inventory_role
from printer_queue import enqueue_print_job

SIDE_NAME = "RIGHT"
CAM_INDEX = 0
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
        self.ui.show_idle_view()  
        current_event_name = get_active_event_name()
        self.ui.update_event_name(current_event_name)

        self.is_processing = False
        self.camera_active = False
        self.current_frame = None
        self.cap = None
        self.button_pressed_at = None

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
            self.current_frame = None
            if is_active:
                self.ui.show_active_view()  # Show camera and status when active
                self.cap = cv2.VideoCapture(CAM_INDEX)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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
        self.button_pressed_at = now()
        self.is_processing = True
        threading.Thread(target=self.vending_sequence, daemon=True).start()


    def vending_sequence(self):
        latency = LatencyRun(SIDE_NAME, self.button_pressed_at)
        try:
            self.safe_update_ui("SCAN QR", "Please show your QR Code to the camera", config.COLORS["scan"])
            self.safe_set_camera_state(True)
            
            qr_id = None
            start_time = time.time()
            qr_scan_start = now()
            time.sleep(1) 
            
            while time.time() - start_time < 60:
                if self.current_frame is not None:
                    gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
                    barcodes = decode(gray)
                    for barcode in barcodes:
                        qr_id = barcode.data.decode('utf-8').strip()
                        break
                    if qr_id: break

            if not qr_id:
                latency.record("qr_scan", qr_scan_start, status="timeout")
                latency.record_total(status="failed", metadata={"reason": "qr_timeout"})
                self.safe_update_ui("TIMEOUT", "No QR detected. Please try again.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            latency.record("button_to_qr_detected", latency.start_time)
            latency.record("qr_scan", qr_scan_start)
            print(f"[{SIDE_NAME}] QR detected: {qr_id}")
            self.safe_update_ui("VERIFYING", "Verifying QR Code, please wait...", config.COLORS["warning"])
            qr_verify_start = now()
            user_data = fetch_attendee(qr_id)
            
            if not user_data or 'face_encoding' not in user_data:
                latency.record("qr_database_verification", qr_verify_start, status="failed")
                latency.record_total(status="failed", metadata={"reason": "invalid_qr"})
                self.safe_update_ui("INVALID QR", "QR is not valid for the active event.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            latency.set_attendee(user_data.get('id'))
            latency.record("qr_database_verification", qr_verify_start)
            if user_data.get('claimed_status') == 'Claimed':
                latency.record_total(status="failed", metadata={"reason": "already_claimed"})
                self.safe_update_ui("ALREADY CLAIMED", "This QR code already claimed a kit.", config.COLORS["warning"])
                self.cleanup_and_reset()
                return
                
            user_name = user_data.get('full_name', 'Attendee').upper()
            user_type = normalize_inventory_role(user_data.get('role', 'Attendee'))
            try:
                registered_encoding = normalize_registered_encoding(user_data['face_encoding'])
            except ValueError as e:
                print(f"[{SIDE_NAME}] Invalid registered face encoding: {e}")
                latency.record_total(status="failed", metadata={"reason": "invalid_face_encoding"})
                self.safe_update_ui("FACE DATA ERROR", "Stored face data is invalid.", config.COLORS["error"])
                self.cleanup_and_reset()
                return
            print(f"[{SIDE_NAME}] QR attendee: id={user_data.get('id')} name={user_name}")
            
            self.safe_update_ui("Welcome", f"{user_name}!", config.COLORS["success"])
            time.sleep(1.5)
            
            self.safe_update_ui("FACE SCAN", "Please look directly at the camera", config.COLORS["scan"])
            self.current_frame = None
            time.sleep(0.2)
            face_verify_start = now()
            face_status = verify_face(lambda: self.current_frame, registered_encoding, SIDE_NAME)
            latency.record("face_authentication_at_machine", face_verify_start, status=face_status)

            if face_status != "matched":
                latency.record_total(status="failed", metadata={"reason": face_status})
                if face_status == "mismatch":
                    self.safe_update_ui("FACE MISMATCH", "Face does not match this QR.", config.COLORS["error"])
                elif face_status == "no_face":
                    self.safe_update_ui("NO FACE DETECTED", "Please try again.", config.COLORS["error"])
                else:
                    self.safe_update_ui("FACE TIMEOUT", "Face verification failed.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            self.safe_update_ui("FACE MATCHED", "Face Verification Complete", config.COLORS["success"])
            time.sleep(1.5)

            if not is_active_event(user_data.get('event_id')):
                latency.record_total(status="failed", metadata={"reason": "inactive_event"})
                self.safe_update_ui("EVENT ENDED", "This event is no longer active.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            slot_lookup_start = now()
            target_slot = get_available_slot(user_type, SIDE_NAME)
            latency.record("role_slot_lookup", slot_lookup_start, status="success" if target_slot else "failed")
            if not target_slot:
                latency.record_total(status="failed", metadata={"reason": "out_of_stock"})
                self.safe_update_ui("OUT OF STOCK", f"No items left for {user_type.upper()}", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            self.safe_update_ui("DISPENSING", f"Dropping item from Slot {target_slot}...", config.COLORS["success"])
            
            dispense_start = now()
            success = hardware.dispense_item(target_slot)
            latency.record("dispense_after_button_command", dispense_start, status="success" if success else "failed", metadata={"slot": target_slot})
            if not success:
                latency.record_total(status="failed", metadata={"reason": "dispense_failed", "slot": target_slot})
                self.safe_update_ui("HARDWARE ERROR", "Item was not confirmed. Please call staff.", config.COLORS["error"])
                self.cleanup_and_reset()
                return

            inventory_start = now()
            deduct_inventory(target_slot)
            latency.record("inventory_deduction_after_dispense", inventory_start, metadata={"slot": target_slot})
            claim_start = now()
            mark_attendee_claimed(user_data['id'])
            latency.record("claim_status_update", claim_start)
            print_queue_start = now()
            print_job_id = enqueue_print_job(
                SIDE_NAME,
                user_data.get('id'),
                user_name,
                user_data.get('company', ''),
                user_data.get('event_id'),
            )
            latency.record("printer_queue", print_queue_start, metadata={"print_job_id": print_job_id})
            print(f"[{SIDE_NAME}] Sticker print queued: {print_job_id}")

            time.sleep(4)
            self.safe_update_ui("SUCCESS", "Thank you! Please claim your item and ID below.", config.COLORS["success"])
            latency.record_total(status="success", metadata={"slot": target_slot})
            self.cleanup_and_reset()

        except Exception as e:
            print(f"[ERROR] Vending Sequence: {e}")
            latency.record_total(status="failed", metadata={"reason": str(e)})
            self.cleanup_and_reset()

    def cleanup_and_reset(self):
        self.safe_set_camera_state(False)
        time.sleep(1)
        self.ui.show_idle_view()  
        self.is_processing = False

    def close_app(self, event=None):
        if self.btn:
            self.btn.close()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = RightVendoGUI()
    app.mainloop()
