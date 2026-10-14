import os
import re
import json
import sqlite3
import threading
import time
import bcrypt
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_DB_PATH = os.path.join(_BASE_DIR, "datacore_local.db")
_OFFLINE_ADMINS_PATH = os.path.join(_BASE_DIR, "offline_admins.json")

# Pokud soubor neexistuje ale je nastaven env var OFFLINE_ADMINS_B64, automaticky ho rozbalíme
# (Koyeb – obsah souboru zakódován do base64 a uložen v environment variables)
def _maybe_restore_offline_admins():
    import base64
    if os.path.exists(_OFFLINE_ADMINS_PATH):
        return
    b64 = os.environ.get("OFFLINE_ADMINS_B64", "")
    if not b64:
        return
    try:
        decoded = base64.b64decode(b64.encode()).decode("utf-8")
        with open(_OFFLINE_ADMINS_PATH, "w", encoding="utf-8") as f:
            f.write(decoded)
        print("[LOCAL DB] offline_admins.json obnoven z env promenne OFFLINE_ADMINS_B64", flush=True)
    except Exception as e:
        print(f"[LOCAL DB] Chyba obnovy offline_admins.json z env: {e}", flush=True)

_maybe_restore_offline_admins()

_local_db_lock = threading.Lock()

def _get_local_conn():
    conn = sqlite3.connect(_LOCAL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_local_db():
    try:
        with _get_local_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spz_cache_local (
                    bus_id TEXT PRIMARY KEY,
                    spz TEXT,
                    linka TEXT,
                    lat REAL,
                    lng REAL,
                    spz_verified INTEGER DEFAULT 0,
                    admin_verified INTEGER DEFAULT 0,
                    admin_flag INTEGER DEFAULT 0,
                    manual_spz INTEGER DEFAULT 0,
                    is_locked_by_admin INTEGER DEFAULT 0,
                    trip_id TEXT,
                    color_class TEXT,
                    status_text TEXT,
                    admin_note TEXT DEFAULT '',
                    admin_driver TEXT DEFAULT '',
                    updated_at TEXT,
                    synced_to_supabase INTEGER DEFAULT 0
                )
            """)
            # Migration check pro existujici tabulky
            try:
                conn.execute("ALTER TABLE spz_cache_local ADD COLUMN is_locked_by_admin INTEGER DEFAULT 0")
            except Exception:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bus_notifications_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_session TEXT,
                    rule_id TEXT,
                    identifier TEXT,
                    trigger TEXT,
                    channel TEXT,
                    message TEXT,
                    fired_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT,
                    detail TEXT,
                    ts TEXT
                )
            """)
            conn.commit()
        print("[LOCAL DB] Inicializovana: datacore_local.db (vcetne is_locked_by_admin a history)", flush=True)
    except Exception as e:
        print(f"[LOCAL DB] Chyba inicializace: {e}", flush=True)

def local_spz_upsert(rows: list):
    if not rows:
        return
    filtered_rows = []
    for r in rows:
        bid = str(r.get("bus_id", "")).strip()
        linka = str(r.get("linka", "")).strip()
        if bid.startswith("-"):
            continue
        if linka.startswith(("Os", "Sp", "R ", "Ex", "IC", "EC", "SC", "rj", "RJ", "EN", "LE", "TL", "Vlak")) or re.match(r'^P\d{1,2}\b', linka, re.IGNORECASE):
            continue
        filtered_rows.append(r)
    if not filtered_rows:
        return
    try:
        with _local_db_lock:
            with _get_local_conn() as conn:
                for row in filtered_rows:
                    is_lock = 1 if (row.get("is_locked_by_admin") or row.get("admin_verified")) else 0
                    conn.execute("""
                        INSERT INTO spz_cache_local
                            (bus_id, spz, linka, lat, lng, spz_verified, admin_verified,
                             admin_flag, manual_spz, is_locked_by_admin, trip_id, color_class, status_text,
                             admin_note, admin_driver, updated_at, synced_to_supabase)
                        VALUES
                            (:bus_id, :spz, :linka, :lat, :lng, :spz_verified, :admin_verified,
                             :admin_flag, :manual_spz, :is_locked_by_admin, :trip_id, :color_class, :status_text,
                             :admin_note, :admin_driver, :updated_at, 0)
                        ON CONFLICT(bus_id) DO UPDATE SET
                            spz = CASE
                                WHEN spz_cache_local.is_locked_by_admin = 1 OR spz_cache_local.admin_verified = 1
                                THEN spz_cache_local.spz
                                WHEN excluded.spz IS NOT NULL AND excluded.spz != 'Neznámá' AND excluded.spz != 'Neznama' AND excluded.spz != ''
                                THEN excluded.spz
                                ELSE spz_cache_local.spz
                            END,
                            linka = excluded.linka,
                            lat = excluded.lat,
                            lng = excluded.lng,
                            spz_verified = CASE
                                WHEN spz_cache_local.is_locked_by_admin = 1 OR spz_cache_local.admin_verified = 1
                                THEN 1
                                ELSE excluded.spz_verified
                            END,
                            admin_verified = CASE
                                WHEN spz_cache_local.is_locked_by_admin = 1 OR spz_cache_local.admin_verified = 1
                                THEN 1
                                ELSE excluded.admin_verified
                            END,
                            is_locked_by_admin = CASE
                                WHEN spz_cache_local.is_locked_by_admin = 1 OR excluded.is_locked_by_admin = 1 OR excluded.admin_verified = 1
                                THEN 1
                                ELSE 0
                            END,
                            admin_flag = excluded.admin_flag,
                            manual_spz = CASE
                                WHEN spz_cache_local.is_locked_by_admin = 1
                                THEN 1
                                ELSE excluded.manual_spz
                            END,
                            trip_id = excluded.trip_id,
                            color_class = excluded.color_class,
                            status_text = excluded.status_text,
                            admin_note = excluded.admin_note,
                            admin_driver = excluded.admin_driver,
                            updated_at = excluded.updated_at,
                            synced_to_supabase = 0
                    """, {
                        "bus_id": row.get("bus_id", ""),
                        "spz": row.get("spz", ""),
                        "linka": row.get("linka", ""),
                        "lat": row.get("lat"),
                        "lng": row.get("lng"),
                        "spz_verified": 1 if row.get("spz_verified") else 0,
                        "admin_verified": 1 if row.get("admin_verified") else 0,
                        "admin_flag": 1 if row.get("admin_flag") else 0,
                        "manual_spz": 1 if row.get("manual_spz") else 0,
                        "is_locked_by_admin": is_lock,
                        "trip_id": row.get("trip_id", ""),
                        "color_class": row.get("color_class", ""),
                        "status_text": row.get("status_text", ""),
                        "admin_note": row.get("admin_note", ""),
                        "admin_driver": row.get("admin_driver", ""),
                        "updated_at": row.get("updated_at") or datetime.now().isoformat(),
                    })
                conn.commit()
    except Exception as e:
        print(f"[LOCAL DB] Chyba zapisu SPZ: {e}", flush=True)

def local_notif_log_history(user_session: str, rule_id: str, identifier: str, trigger: str, channel: str, message: str, fired_at: str = None):
    """Zaznamena odpalenou notifikaci do lokalni historie."""
    try:
        if not fired_at:
            fired_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _local_db_lock:
            with _get_local_conn() as conn:
                conn.execute("""
                    INSERT INTO bus_notifications_history (user_session, rule_id, identifier, trigger, channel, message, fired_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(user_session), str(rule_id), str(identifier), str(trigger), str(channel), str(message), str(fired_at)))
                conn.commit()
    except Exception as e:
        print(f"[LOCAL DB] Chyba zapisu historie notifikace: {e}", flush=True)

def local_notif_get_history(user_session: str = None, limit: int = 50) -> list:
    """Vrati historii notifikaci pro daneho uzivatele nebo pro cely system (pokud user_session je None)."""
    try:
        with _local_db_lock:
            with _get_local_conn() as conn:
                if user_session:
                    rows = conn.execute("""
                        SELECT id, user_session, rule_id, identifier, trigger, channel, message, fired_at
                        FROM bus_notifications_history
                        WHERE user_session = ?
                        ORDER BY id DESC LIMIT ?
                    """, (str(user_session), limit)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT id, user_session, rule_id, identifier, trigger, channel, message, fired_at
                        FROM bus_notifications_history
                        ORDER BY id DESC LIMIT ?
                    """, (limit,)).fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        print(f"[LOCAL DB] Chyba cteni historie notifikaci: {e}", flush=True)
        return []

def local_spz_purge_trains():
    try:
        with _local_db_lock:
            with _get_local_conn() as conn:
                conn.execute("DELETE FROM spz_cache_local WHERE bus_id LIKE '-%'")
                train_prefixes = ["Os%", "Sp%", "R %", "Ex%", "IC%", "EC%", "SC%", "rj%", "RJ%", "EN%", "LE%", "TL%", "Vlak%", "P1%", "P2%", "P3%", "P4%", "P5%", "P11%", "P12%", "P21%", "P22%"]
                for pref in train_prefixes:
                    conn.execute("DELETE FROM spz_cache_local WHERE linka LIKE ?", (pref,))
                conn.commit()
    except Exception as e:
        print(f"[LOCAL DB] Chyba cisteni vlaku: {e}", flush=True)


def local_spz_get_all() -> list:
    try:
        with _get_local_conn() as conn:
            rows = conn.execute("SELECT * FROM spz_cache_local").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[LOCAL DB] Chyba cteni SPZ: {e}", flush=True)
        return []

def local_spz_get_unsynced() -> list:
    try:
        with _get_local_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM spz_cache_local WHERE synced_to_supabase = 0"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[LOCAL DB] Chyba cteni unsynced: {e}", flush=True)
        return []

def local_spz_mark_synced(bus_ids: list):
    if not bus_ids:
        return
    try:
        with _local_db_lock:
            with _get_local_conn() as conn:
                placeholders = ",".join("?" * len(bus_ids))
                conn.execute(
                    f"UPDATE spz_cache_local SET synced_to_supabase=1 WHERE bus_id IN ({placeholders})",
                    bus_ids
                )
                conn.commit()
    except Exception as e:
        print(f"[LOCAL DB] Chyba mark_synced: {e}", flush=True)

def local_spz_delete_inactive(active_bus_ids: list):
    if not active_bus_ids:
        return
    try:
        with _local_db_lock:
            with _get_local_conn() as conn:
                placeholders = ",".join("?" * len(active_bus_ids))
                conn.execute(
                    f"DELETE FROM spz_cache_local WHERE bus_id NOT IN ({placeholders}) AND admin_verified=0",
                    active_bus_ids
                )
                conn.commit()
    except Exception as e:
        print(f"[LOCAL DB] Chyba delete_inactive: {e}", flush=True)

_last_sync_attempt: float = 0.0
_SYNC_COOLDOWN: int = 300

def try_sync_to_supabase(db_client, force: bool = False):
    global _last_sync_attempt
    now = time.time()
    if not force and (now - _last_sync_attempt) < _SYNC_COOLDOWN:
        return
    if not db_client:
        return

    unsynced = local_spz_get_unsynced()
    if not unsynced:
        return

    _last_sync_attempt = now
    synced_ids = []
    errors = 0

    for row in unsynced:
        try:
            payload = {
                "bus_id": row["bus_id"],
                "spz": row["spz"],
                "linka": row["linka"],
                "lat": row["lat"],
                "lng": row["lng"],
                "spz_verified": bool(row["spz_verified"]),
                "admin_verified": bool(row["admin_verified"]),
                "admin_flag": bool(row["admin_flag"]),
                "manual_spz": bool(row["manual_spz"]),
                "is_locked_by_admin": bool(row.get("is_locked_by_admin") or row.get("admin_verified")),
                "trip_id": row["trip_id"],
                "color_class": row["color_class"],
                "status_text": row["status_text"],
                "admin_note": row["admin_note"],
                "admin_driver": row["admin_driver"],
                "updated_at": row["updated_at"],
            }
            try:
                db_client.table("spz_cache").upsert(payload).execute()
            except Exception as e_sup:
                if "is_locked_by_admin" in str(e_sup) or "PGRST204" in str(e_sup):
                    payload.pop("is_locked_by_admin", None)
                    db_client.table("spz_cache").upsert(payload).execute()
                else:
                    raise e_sup
            synced_ids.append(row["bus_id"])
        except Exception:
            errors += 1
            if errors >= 3:
                break

    if synced_ids:
        local_spz_mark_synced(synced_ids)
        print(f"[LOCAL DB SYNC] Synchronizovano {len(synced_ids)} SPZ zaznamu do Supabase.", flush=True)
        try:
            with _local_db_lock:
                with _get_local_conn() as conn:
                    conn.execute(
                        "INSERT INTO sync_log (event, detail, ts) VALUES (?, ?, ?)",
                        ("sync_ok", f"Synced {len(synced_ids)} rows", datetime.now().isoformat())
                    )
                    conn.commit()
        except Exception:
            pass

def _load_offline_admins() -> list:
    if not os.path.exists(_OFFLINE_ADMINS_PATH):
        return []
    try:
        with open(_OFFLINE_ADMINS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("admins", [])
    except Exception as e:
        print(f"[OFFLINE AUTH] Chyba nacitani offline_admins.json: {e}", flush=True)
        return []

def check_offline_login(username: str, password: str):
    admins = _load_offline_admins()
    if not admins:
        return None
    for admin in admins:
        stored_hash = admin.get("password_hash", "")
        admin_username = admin.get("offline_username", "")
        if admin_username != username:
            continue
        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                return {
                    "discord_id": admin.get("discord_id", ""),
                    "nick": admin.get("nick", ""),
                    "email": admin.get("email", ""),
                    "role": admin.get("role", "DEV"),
                    "offline_mode": True,
                }
        except Exception as e:
            print(f"[OFFLINE AUTH] Chyba overeni hesla: {e}", flush=True)
            return None
    return None
