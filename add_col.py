import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if url and key:
    supabase = create_client(url, key)
    # Píšu přímo přes RPC nebo to musím udělat přes SQL
    print("Mám připojení")
