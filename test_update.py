import os
from turso_db import get_turso_db

try:
    db = get_turso_db()
    res = db.table("users").select("id, discord_id, nick, role").limit(5).execute()
    print(f"Turso DB connection OK! Sample users: {res.data}")
except Exception as e:
    print(f"Turso Error: {e}")
