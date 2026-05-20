import customtkinter as ctk
import config

class VendoUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=config.COLORS["bg"])
        self.pack(fill="both", expand=True)
        
        # Main container for all views
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)
        
        # Create Idle View
        self.idle_view = self._create_idle_view()
        
        # Create Active View
        self.active_view = self._create_active_view()
        
        # Start in Idle state
        self.show_idle_view()
    
    def _create_idle_view(self):
        """Creates the beautiful centered Idle/Standby View"""
        idle_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # --- EVENT NAME LABEL (Dito natin nilagyan ng self.) ---
        self.event_label = ctk.CTkLabel(
            idle_frame,
            text=f"{config.EVENT_NAME}",
            font=config.FONTS["event_name"],
            text_color=config.COLORS["accent_light"]
        )
        self.event_label.pack(pady=(80, 40))
        
        # --- WELCOME TEXT (Huge, centered) ---
        welcome_label = ctk.CTkLabel(
            idle_frame,
            text="WELCOME",
            font=config.FONTS["welcome_title"],
            text_color=config.COLORS["idle"]
        )
        welcome_label.pack(pady=(20, 0))
        
        # --- SUBTEXT ---
        subtext_label = ctk.CTkLabel(
            idle_frame,
            text="Please press the button to start",
            font=config.FONTS["idle_subtitle"],
            text_color=config.COLORS["accent_light"]
        )
        subtext_label.pack(pady=(30, 0))
        
        return idle_frame
    

    def _create_active_view(self):
        """Creates the Active View with camera and status indicators"""
        active_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # --- TOP STATUS SECTION ---
        self.header_frame = ctk.CTkFrame(active_frame, fg_color="transparent")
        self.header_frame.pack(pady=(60, 20))
        
        self.status_label = ctk.CTkLabel(
            self.header_frame, 
            text="SCAN QR", 
            font=config.FONTS["title"], 
            text_color=config.COLORS["scan"]
        )
        self.status_label.pack()
        
        self.msg_label = ctk.CTkLabel(
            self.header_frame, 
            text="Please show your QR Code to the camera", 
            font=config.FONTS["subtitle"], 
            text_color=config.COLORS["text_sub"]
        )
        self.msg_label.pack(pady=(5, 0))

        # --- CAMERA CARD SECTION ---
        self.card_frame = ctk.CTkFrame(
            active_frame, 
            fg_color=config.COLORS["card"], 
            border_color=config.COLORS["card_border"], 
            border_width=2, 
            corner_radius=20
        )
        self.card_frame.pack(pady=30, padx=50)

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
        
        return active_frame
    
    def show_idle_view(self):
        """Displays the Idle View and hides Active View"""
        # Hide active view
        self.active_view.pack_forget()
        # Show idle view
        self.idle_view.pack(fill="both", expand=True)
    
    def show_active_view(self):
        """Displays the Active View and hides Idle View"""
        # Hide idle view
        self.idle_view.pack_forget()
        # Show active view
        self.active_view.pack(fill="both", expand=True)
    
    # ==================================================
    # ??? MGA FUNCTIONS PARA MA-CONTROL NG MAIN CODE
    # ==================================================
    
    def update_event_name(self, new_name):
        """Update ang pangalan ng event mula sa Database"""
        self.event_label.configure(text=f"{new_name}")

    def update_texts(self, status, msg, color):
        """Update status and message text in Active View"""
        self.status_label.configure(text=status, text_color=color)
        self.msg_label.configure(text=msg)

    def update_camera_image(self, ctk_image):
        """Display camera feed"""
        self.video_label.configure(image=ctk_image, text="")

    def set_camera_off(self, blank_image):
        """Display inactive camera screen"""
        self.video_label.configure(image=blank_image, text="CAMERA INACTIVE")