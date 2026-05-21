from supabase import create_client

# Gamitin ang credentials mula sa iyong Supabase project
URL = "https://zjumaqabzoogpoeadvtn.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqdW1hcWFiem9vZ3BvZWFkdnRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwODI0OTIsImV4cCI6MjA5NDY1ODQ5Mn0.L6gfpuC8rHH04RS6sOeSz6EPJqp6xaohRD-lRFkRzZU"
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

def get_active_event_id():
    try:
        response = supabase.table('events') \
            .select('*') \
            .eq('status', 'ACTIVE') \
            .limit(1) \
            .execute()

        if response.data and len(response.data) > 0:
            event = response.data[0]
            return event.get('event_id') or event.get('id')

        return None
    except Exception as e:
        print(f"[DB ERROR] Could not fetch active event id: {e}")
        return None

# ITO ANG IDINAGDAG NATIN PARA SA INVENTORY SLOTS (1 hanggang 6)
def get_available_slot(user_type, side_name):
    try:
        event_id = get_active_event_id()
        if not event_id:
            print("[INVENTORY] No ACTIVE event found.")
            return None

        side_name = side_name.upper()
        if side_name == "LEFT":
            allowed_slots = [1, 2, 3]
        elif side_name == "RIGHT":
            allowed_slots = [4, 5, 6]
        else:
            print(f"[INVENTORY] Unknown side_name: {side_name}")
            return None

        # Hahanapin nito ang slot para sa active event, role, at screen side.
        # Magbabalik lang ito kapag may stock pa (> 0).
        response = supabase.table('inventory') \
            .select('slot_number') \
            .eq('event_id', event_id) \
            .eq('assigned_role', user_type) \
            .in_('slot_number', allowed_slots) \
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

def deduct_inventory(slot_number):
    try:
        event_id = get_active_event_id()
        if not event_id:
            print("[INVENTORY] Cannot deduct. No ACTIVE event found.")
            return False

        slot_number = int(slot_number)
        response = supabase.table('inventory') \
            .select('stock_count') \
            .eq('event_id', event_id) \
            .eq('slot_number', slot_number) \
            .gt('stock_count', 0) \
            .limit(1) \
            .execute()

        if not response.data:
            print(f"[INVENTORY] Cannot deduct. Slot {slot_number} is out of stock.")
            return False

        current_stock = int(response.data[0]['stock_count'])
        new_stock = current_stock - 1

        supabase.table('inventory') \
            .update({'stock_count': new_stock}) \
            .eq('event_id', event_id) \
            .eq('slot_number', slot_number) \
            .execute()

        print(f"[INVENTORY] Deducted Slot {slot_number}. New stock: {new_stock}")
        return True
    except Exception as e:
        print(f"Inventory Deduction Error: {e}")
        return False

def get_active_event_name():
    """
    Kukuha ng pangalan ng event na naka 'LIVE' o 'ACTIVE' sa Supabase.
    Kung walang makuha o walang internet, may default fallback text.
    """
    try:
        # Palitan mo yung 'events', 'status', 'LIVE', at 'name' depende 
        # sa totoong pangalan ng mga columns sa Supabase table niyo.
        response = supabase.table('events').select('name').eq('status', 'ACTIVE').execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['name'].upper() # Para laging naka-caps lock sa screen
        else:
            return "WELCOME TO VENDY" # Fallback kung walang active event
            
    except Exception as e:
        print(f"[DB ERROR] Could not fetch event name: {e}")
        return "WELCOME TO VENDY" # Fallback kung walang internet
