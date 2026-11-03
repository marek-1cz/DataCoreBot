# scripts/migrate_to_d1.py
"""
Migrační skript pro přenos dat z Turso / lokální SQLite / JSON do Cloudflare D1.
Přenáší:
1. spz_registry (všechny známé autobusy, SPZ, admin zámky, řidiče, poznámky)
2. depot_history (aktivní pobyty ve vozovnách + posledních 200 dokončených návštěv)
"""

import sys
import os
import json
import sqlite3
import time
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from cloudflare_d1 import get_d1_client, is_d1_available


def normalize_spz(s: str) -> str:
    if not s:
        return ""
    return str(s).replace(" ", "").strip().upper()


def format_spz(s: str) -> str:
    clean = normalize_spz(s)
    if len(clean) == 7:
        return f"{clean[:3]} {clean[3:]}"
    return clean


def migrate_spz(d1):
    print("\n--- 1. Migrace SPZ (spz_registry) ---")
    all_buses = {}  # bus_id -> dict

    # A) Načtení z Turso spz_cache
    try:
        from turso_db import get_turso_db
        db = get_turso_db()
        res = db._execute_single(
            "SELECT bus_id, spz, is_locked_by_admin, admin_note, admin_driver, vehicle_type, updated_at FROM spz_cache",
            bypass_block_check=True
        )
        if res and res.data:
            print(f"[Turso] Nalezeno {len(res.data)} záznamů v spz_cache.")
            for r in res.data:
                b_id = str(r.get("bus_id") or "").strip()
                spz_val = str(r.get("spz") or "").strip()
                if not b_id or not spz_val:
                    continue
                is_l = 1 if r.get("is_locked_by_admin") else 0
                all_buses[b_id] = {
                    "bus_id": b_id,
                    "spz": normalize_spz(spz_val),
                    "spz_display": format_spz(spz_val),
                    "source": "ADMIN" if is_l else "AUTO",
                    "is_locked": is_l,
                    "admin_note": str(r.get("admin_note") or ""),
                    "admin_driver": str(r.get("admin_driver") or ""),
                    "vehicle_type": str(r.get("vehicle_type") or ""),
                    "confidence": 100,
                    "conflict_detected": 0,
                    "conflict_spz": "",
                    "updated_at": str(r.get("updated_at") or datetime.now().isoformat()),
                    "updated_by": "turso_migration"
                }
    except Exception as e:
        print(f"[Turso] Chyba při čtení spz_cache: {e}")

    # B) Doplnění z datacore_local.db pokud existuje
    local_db_path = os.path.join(_BASE_DIR, "datacore_local.db")
    if os.path.exists(local_db_path):
        try:
            con = sqlite3.connect(local_db_path)
            cur = con.cursor()
            rows = cur.execute("SELECT bus_id, spz, is_locked_by_admin, admin_note, admin_driver, vehicle_type, updated_at FROM spz_cache_local").fetchall()
            print(f"[Local DB] Nalezeno {len(rows)} záznamů v spz_cache_local.")
            for r in rows:
                b_id = str(r[0] or "").strip()
                spz_val = str(r[1] or "").strip()
                if not b_id or not spz_val:
                    continue
                if b_id not in all_buses:
                    is_l = 1 if r[2] else 0
                    all_buses[b_id] = {
                        "bus_id": b_id,
                        "spz": normalize_spz(spz_val),
                        "spz_display": format_spz(spz_val),
                        "source": "ADMIN" if is_l else "AUTO",
                        "is_locked": is_l,
                        "admin_note": str(r[3] or ""),
                        "admin_driver": str(r[4] or ""),
                        "vehicle_type": str(r[5] or ""),
                        "confidence": 100,
                        "conflict_detected": 0,
                        "conflict_spz": "",
                        "updated_at": str(r[6] or datetime.now().isoformat()),
                        "updated_by": "local_db_migration"
                    }
            con.close()
        except Exception as e:
            print(f"[Local DB] Chyba čtení spz_cache_local: {e}")

    # C) Doplnění z spz_cache_backup.json pokud existuje
    backup_json = os.path.join(_BASE_DIR, "spz_cache_backup.json")
    if os.path.exists(backup_json):
        try:
            with open(backup_json, "r", encoding="utf-8") as f:
                b_data = json.load(f)
            print(f"[JSON Backup] Nalezeno {len(b_data)} záznamů v spz_cache_backup.json.")
            for r in b_data:
                b_id = str(r.get("bus_id") or "").strip()
                spz_val = str(r.get("spz") or "").strip()
                if not b_id or not spz_val:
                    continue
                if b_id not in all_buses:
                    is_l = 1 if r.get("is_locked_by_admin") else 0
                    all_buses[b_id] = {
                        "bus_id": b_id,
                        "spz": normalize_spz(spz_val),
                        "spz_display": format_spz(spz_val),
                        "source": "ADMIN" if is_l else "AUTO",
                        "is_locked": is_l,
                        "admin_note": str(r.get("admin_note") or ""),
                        "admin_driver": str(r.get("admin_driver") or ""),
                        "vehicle_type": str(r.get("vehicle_type") or ""),
                        "confidence": 100,
                        "conflict_detected": 0,
                        "conflict_spz": "",
                        "updated_at": str(r.get("updated_at") or datetime.now().isoformat()),
                        "updated_by": "json_backup_migration"
                    }
        except Exception as e:
            print(f"[JSON Backup] Chyba čtení backupu: {e}")

    # D) Obohacení o spz_metadata z spz_settings.json
    settings_json = os.path.join(_BASE_DIR, "spz_settings.json")
    if os.path.exists(settings_json):
        try:
            with open(settings_json, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            meta = s_data.get("spz_metadata", {})
            print(f"[Settings JSON] Nalezeno {len(meta)} metadat k SPZ.")
            for norm_k, m in meta.items():
                target_spz = normalize_spz(m.get("spz") or norm_k)
                for b_id, bus in all_buses.items():
                    if bus["spz"] == target_spz:
                        if m.get("driver") and not bus["admin_driver"]:
                            bus["admin_driver"] = m["driver"]
                        if m.get("note") and not bus["admin_note"]:
                            bus["admin_note"] = m["note"]
                        if m.get("vehicle_type") and not bus["vehicle_type"]:
                            bus["vehicle_type"] = m["vehicle_type"]
        except Exception as e:
            print(f"[Settings JSON] Chyba obohacení metadat: {e}")

    print(f"[Celkem] Připraveno {len(all_buses)} unikátních autobusů k zápisu do D1.")

    # Cloudflare D1 má limit 100 SQL proměnných na dotaz.
    # 13 sloupců * 6 řádků = 78 proměnných. Použijeme dávku po 5.
    buses_list = list(all_buses.values())
    batch_size = 5
    inserted = 0
    cols = ["bus_id", "spz", "spz_display", "source", "is_locked", "admin_note", "admin_driver", "vehicle_type", "confidence", "conflict_detected", "conflict_spz", "updated_at", "updated_by"]
    col_str = ", ".join(cols)

    for i in range(0, len(buses_list), batch_size):
        chunk = buses_list[i:i + batch_size]
        placeholders = []
        params = []
        for item in chunk:
            placeholders.append("(" + ", ".join(["?" for _ in cols]) + ")")
            for c in cols:
                params.append(item.get(c))

        sql = f"INSERT OR REPLACE INTO spz_registry ({col_str}) VALUES " + ", ".join(placeholders)
        d1.execute(sql, params)
        inserted += len(chunk)
        if inserted % 50 == 0 or inserted >= len(buses_list):
            print(f"  Zapsáno {inserted}/{len(buses_list)} autobusů do D1...")
        time.sleep(0.05)

    cnt = d1.execute("SELECT COUNT(*) AS c FROM spz_registry")
    locked_cnt = d1.execute("SELECT COUNT(*) AS c FROM spz_registry WHERE is_locked = 1")
    print(f"[D1] Úspěšně uloženo! Celkový počet v D1 spz_registry: {cnt[0]['c'] if cnt else '?'}")
    print(f"[D1] Z toho zamčeno adminem (is_locked=1): {locked_cnt[0]['c'] if locked_cnt else '?'}")


def migrate_depots(d1):
    print("\n--- 2. Migrace Vozoven (depot_history) ---")
    active_sessions = {}  # bus_id -> dict

    # A) Načtení aktivních pobytů (left_at IS NULL) z Turso
    try:
        from turso_db import get_turso_db
        db = get_turso_db()
        res = db._execute_single(
            "SELECT depot_name, bus_id, spz, arrived_at FROM depot_history WHERE left_at IS NULL ORDER BY arrived_at DESC",
            bypass_block_check=True
        )
        if res and res.data:
            print(f"[Turso] Nalezeno {len(res.data)} aktivních pobytů ve vozovnách.")
            for r in res.data:
                b_id = str(r.get("bus_id") or "").strip()
                if not b_id or b_id.startswith("SYSTEM_"):
                    continue
                if b_id not in active_sessions:
                    active_sessions[b_id] = {
                        "depot_name": str(r.get("depot_name") or ""),
                        "bus_id": b_id,
                        "spz": normalize_spz(r.get("spz") or ""),
                        "arrived_at": str(r.get("arrived_at") or datetime.now().isoformat()),
                        "left_at": None,
                        "pvvd_lost_at": None,
                        "status": "IN_DEPOT"
                    }
    except Exception as e:
        print(f"[Turso] Chyba při čtení aktivních pobytů: {e}")

    # B) Načtení posledních 150 dokončených návštěv pro historii
    recent_history = []
    try:
        res_recent = db._execute_single(
            "SELECT depot_name, bus_id, spz, arrived_at, left_at FROM depot_history WHERE left_at IS NOT NULL ORDER BY arrived_at DESC LIMIT 150",
            bypass_block_check=True
        )
        if res_recent and res_recent.data:
            print(f"[Turso] Nalezeno {len(res_recent.data)} nedávných dokončených návštěv.")
            for r in res_recent.data:
                b_id = str(r.get("bus_id") or "").strip()
                if not b_id or b_id.startswith("SYSTEM_"):
                    continue
                recent_history.append({
                    "depot_name": str(r.get("depot_name") or ""),
                    "bus_id": b_id,
                    "spz": normalize_spz(r.get("spz") or ""),
                    "arrived_at": str(r.get("arrived_at") or datetime.now().isoformat()),
                    "left_at": str(r.get("left_at") or ""),
                    "pvvd_lost_at": None,
                    "status": "LEFT"
                })
    except Exception as e:
        print(f"[Turso] Chyba při čtení nedávné historie: {e}")

    all_depot_records = list(active_sessions.values()) + recent_history
    print(f"[Celkem] Připraveno {len(all_depot_records)} záznamů vozoven ({len(active_sessions)} aktivních, {len(recent_history)} z historie).")

    # 7 sloupců * 10 řádků = 70 proměnných (< 100 limit)
    cols = ["depot_name", "bus_id", "spz", "arrived_at", "left_at", "pvvd_lost_at", "status"]
    col_str = ", ".join(cols)
    batch_size = 10
    inserted = 0

    for i in range(0, len(all_depot_records), batch_size):
        chunk = all_depot_records[i:i + batch_size]
        placeholders = []
        params = []
        for item in chunk:
            placeholders.append("(" + ", ".join(["?" for _ in cols]) + ")")
            for c in cols:
                params.append(item.get(c))

        sql = f"INSERT INTO depot_history ({col_str}) VALUES " + ", ".join(placeholders)
        d1.execute(sql, params)
        inserted += len(chunk)
        if inserted % 50 == 0 or inserted >= len(all_depot_records):
            print(f"  Zapsáno {inserted}/{len(all_depot_records)} záznamů vozoven do D1...")
        time.sleep(0.05)

    cnt = d1.execute("SELECT COUNT(*) AS c FROM depot_history")
    active_cnt = d1.execute("SELECT COUNT(*) AS c FROM depot_history WHERE left_at IS NULL")
    print(f"[D1] Celkový počet v D1 depot_history: {cnt[0]['c'] if cnt else '?'}")
    print(f"[D1] Z toho aktivních pobytů ve vozovně (left_at IS NULL): {active_cnt[0]['c'] if active_cnt else '?'}")


def main():
    print("=== START MIGRACE DO CLOUDFLARE D1 ===")
    if not is_d1_available():
        print("[CHYBA] Cloudflare D1 není dostupné! Zkontroluj token a konfiguraci.")
        sys.exit(1)
    print("[OK] Cloudflare D1 je dostupné a odpovídá.")

    d1 = get_d1_client()
    migrate_spz(d1)
    migrate_depots(d1)
    print("\n=== MIGRACE ÚSPĚŠNĚ DOKONČENA ===")


if __name__ == "__main__":
    main()
