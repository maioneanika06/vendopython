import customtkinter as ctk
import config

class VendoUI(ctk.CTkFrame):
    def __init__(self, master):
        # Gawing buong screen ang frame at gamitin ang deep dark background
        super().__init__(master, fg_color=config.COLORS["bg"])
        self.pack(fill="both", expand=True)
        
        # --- TOP HEADER SECTION ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(60, 20))
        
        self.status_label = ctk.CTkLabel(
            self.header_frame, 
            text="WELCOME", 
            font=config.FONTS["title"], 
            text_color=config.COLORS["idle"]
        )
        self.status_label.pack()
        
        self.msg_label = ctk.CTkLabel(
            self.header_frame, 
            text="Press the button to start", 
            font=config.FONTS["subtitle"], 
            text_color=config.COLORS["text_sub"]
        )
        self.msg_label.pack(pady=(5, 0))

        # --- CAMERA CARD SECTION (Inspired by your web app cards) ---
        self.card_frame = ctk.CTkFrame(
            self, 
            fg_color=config.COLORS["card"], 
            border_color=config.COLORS["card_border"], 
            border_width=2, 
            corner_radius=20
        )
        self.card_frame.pack(pady=30, padx=50)

        # Ang mismong screen ng camera sa loob ng card
        self.video_label = ctk.CTkLabel(
            self.card_frame, 
            text="CAMERA INACTIVE", 
            width=640, 
            height=480, 
            corner_radius=15, 
            font=config.FONTS["subtitle"],
            text_color=config.COLORS["text_sub"]
        )
        self.video_label.pack(padx=15, pady=15)

    # Functions para tawagin ng main code natin
    def update_texts(self, status, msg, color):
        self.status_label.configure(text=f"? {status}", text_color=color)
        self.msg_label.configure(text=msg)

    def update_camera_image(self, ctk_image):
        self.video_label.configure(image=ctk_image, text="")

    def set_camera_off(self, blank_image):
        self.video_label.configure(image=blank_image, text="CAMERA INACTIVE")