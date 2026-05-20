from supabase import create_client

# Gamitin ang credentials mula sa iyong Supabase project
URL = "https://zjumaqabzoogpoeadvtn.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqdW1hcWFiem9vZ3BvZWFkdnRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwODI0OTIsImV4cCI6MjA5NDY1ODQ5Mn0.L6gfpuC8rHH04RS6sOeSz6EPJqp6xaohRD-lRFkRzZU"
supabase = create_client(URL, KEY)

supabase = create_client(URL, KEY)

def fetch_attendee(search_id):
    try:
        # Kinukuha ang data sa 'attendees' table gamit ang QR code
        response = supabase.table('attendees').select('*').eq('id', search_id).execute()
        
        if len(response.data) > 0:
            return response.data[0] # Ibabalik nito ang buong row ng attendee
        else:
            return None
            
    except Exception as e:
        print(f"Database Query Error: {e}")
        return None

# ITO ANG IDINAGDAG NATIN PARA SA INVENTORY SLOTS (1 hanggang 6)
def get_available_slot(attendee_type):
    try:
        # Hahanapin nito sa inventory_slots kung saang slot naka-assign ang role (VIP/Speaker/Attendee)
        # at sisiguraduhin na may stock pa (> 0)
        response = supabase.table('inventory') \
            .select('slot_number') \
            .eq('assigned_role', attendee_type) \
            .gt('stock_count', 0) \
            .order('slot_number') \
            .limit(1) \
            .execute()
            
        if len(response.data) > 0:
            return str(response.data[0]['slot_number']) # Ibalik halimbawa: "1" o "6"
        else:
            return None
    except Exception as e:
        print(f"Inventory DB Error: {e}")
        return None

def get_active_event_name():
    """
    Kukuha ng pangalan ng event na naka 'LIVE' o 'ACTIVE' sa Supabase.
    Kung walang makuha o walang internet, may default fallback text.
    """
    try:
        # Palitan mo yung 'events', 'status', 'LIVE', at 'name' depende 
        # sa totoong pangalan ng mga columns sa Supabase table niyo.
        response = supabase.table('events').select('name').eq('status', 'LIVE').execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['name'].upper() # Para laging naka-caps lock sa screen
        else:
            return "WELCOME TO VENDY" # Fallback kung walang active event
            
    except Exception as e:
        print(f"[DB ERROR] Could not fetch event name: {e}")
        return "WELCOME TO VENDY" # Fallback kung walang internet