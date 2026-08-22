import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
print(f"URL: {SUPABASE_URL}, KEY: {SUPABASE_KEY[:5] if SUPABASE_KEY else None}")

try:
    if SUPABASE_URL and SUPABASE_KEY:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", "000000000").execute()
        print(f"Success: {res.data}")
    else:
        print("Missing SUPABASE env vars.")
except Exception as e:
    print(f"Error: {e}")
