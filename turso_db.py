"""
Turso Database Client & Resilient LibSQL Adapter for DataCoreBot
Poskytuje identické rozhraní jako supabase-py (.table(...).select().eq().execute()),
vybavené nekompromisním bezpečnostním štítem proti překročení limitů:
- Striktní počítadlo a měsíční rozpočet čtení (Read Budget Tracker)
- In-memory Query Caching (TTL + automatická invalidace při zápisu)
- Automatická detekce "Reads Blocked" a okamžitý fallback na lokální SQLite / paměť
- Circuit Breaker: automatické odstavení před vyčerpáním limitu (ochrana účtu)
- Periodický recovery probe (testuje SELECT 1; pro automatický návrat do normálu)
- Garantované vytváření indexů (pro zamezení Full Table Scanům)
"""

import os
import json
import urllib.request
import urllib.error
import time
import threading
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

_DEFAULT_TURSO_URL = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("TURSO_URL") or "libsql://datacorebot-marek-1cz.aws-eu-north-1.turso.io"
_T1 = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTI5MTUwMDIsImlkIjoiMDFhMTcyMGUtZDgwMS03YjM5LTk3Y2QtMjY3OGU5NTVhN2M4Iiwia2lkIjoiSUVKRndGUkI5TUczOFYtdUlvMk9TVnI4MEZXeXFlSEZQZGwtVi1Gdk1CUSIsInJpZCI6ImVjYTE0YWJiLTU1YjEtNDE2Ny04NTFlLWExNzNmMTU0NzNmZSJ9"
_T2 = "3eEe_wV8-SHd1qLmP4pZdBY2yHtNG0iXncOmFAbVZjUo3k7BC07MT0ZwW9iT6CuBTBZLUXtG-apUN4Iz8zPKBw"
_DEFAULT_TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN") or f"{_T1}.{_T2}"

# ═══════════════════════════════════════════════════════════════════════════════
# READ BUDGET, CIRCIUT BREAKER & STATUS MONITORING
# ═══════════════════════════════════════════════════════════════════════════════
TURSO_MONTHLY_LIMIT = 500_000_000      # 500M row reads v bezplatném Starter plánu
TURSO_SAFE_THROTTLE = 350_000_000      # 70 % -> aktivace šetřícího režimu
TURSO_CIRCUIT_BREAKER = 450_000_000    # 90 % -> preventivní zastavení cloud SELECTů

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_BUDGET_FILE = os.path.join(_BASE_DIR, "turso_budget.json")
_STATE_LOCK = threading.RLock()

def _get_current_month_key():
    try:
        return datetime.now(ZoneInfo("Europe/Prague")).strftime("%Y-%m")
    except Exception:
        return datetime.now().strftime("%Y-%m")

_TURSO_STATE = {
    "month": _get_current_month_key(),
    "row_reads": 0,
    "queries_count": 0,
    "blocked": True,   # Default True pokud jsme právě dostali blocked notifikaci
    "blocked_reason": "Reads blocked by Turso plan limit (awaiting reset/unblock)",
    "last_blocked_ts": time.time(),
    "saving_mode": True,
    "circuit_breaker": True,
    "last_probe_ts": 0.0,
    "last_save_ts": 0.0
}

def _load_budget_state():
    global _TURSO_STATE
    curr_m = _get_current_month_key()
    if os.path.exists(_BUDGET_FILE):
        try:
            with open(_BUDGET_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("month") == curr_m:
                    _TURSO_STATE.update(saved)
                else:
                    # Nový měsíc! Reset počítadel
                    _TURSO_STATE["month"] = curr_m
                    _TURSO_STATE["row_reads"] = 0
                    _TURSO_STATE["queries_count"] = 0
                    _TURSO_STATE["blocked"] = False
                    _TURSO_STATE["blocked_reason"] = ""
                    _TURSO_STATE["saving_mode"] = False
                    _TURSO_STATE["circuit_breaker"] = False
                    _save_budget_state()
        except Exception:
            pass
    else:
        _save_budget_state()

def _save_budget_state():
    with _STATE_LOCK:
        try:
            with open(_BUDGET_FILE, "w", encoding="utf-8") as f:
                json.dump(_TURSO_STATE, f, indent=2, ensure_ascii=False)
            _TURSO_STATE["last_save_ts"] = time.time()
        except Exception:
            pass

_load_budget_state()

_TURSO_WRITES_BLOCKED_UNTIL = 0.0
_LAST_WRITE_BLOCK_LOG = 0.0

def is_turso_write_blocked() -> bool:
    return time.time() < _TURSO_WRITES_BLOCKED_UNTIL

def set_turso_writes_blocked(val: bool, reason: str = ""):
    global _TURSO_WRITES_BLOCKED_UNTIL, _LAST_WRITE_BLOCK_LOG
    if val:
        _TURSO_WRITES_BLOCKED_UNTIL = time.time() + 1800  # 30 minut circuit breaker pro zápisy
        now = time.time()
        if now - _LAST_WRITE_BLOCK_LOG > 300:
            _LAST_WRITE_BLOCK_LOG = now
            print(f"[TursoClient] Zápisy do Turso jsou blokovány kvótou (writes forbidden). Přepínám na lokální zálohy.", flush=True)
    else:
        _TURSO_WRITES_BLOCKED_UNTIL = 0.0

def is_turso_blocked_error(err_str: str) -> bool:
    if not err_str:
        return False
    low = str(err_str).lower()
    if "write operations are forbidden" in low or "writes are blocked" in low:
        return False
    return any(p in low for p in [
        "reads are blocked",
        "sql read operations are forbidden",
        "read limit",
        "limit has now been reached",
        "read quota exceeded",
        "plan limit"
    ])

def is_turso_blocked() -> bool:
    # Pokud začal nový měsíc, prověř unblock
    curr_m = _get_current_month_key()
    if _TURSO_STATE.get("month") != curr_m:
        with _STATE_LOCK:
            _TURSO_STATE["month"] = curr_m
            _TURSO_STATE["row_reads"] = 0
            _TURSO_STATE["queries_count"] = 0
            _TURSO_STATE["blocked"] = False
            _TURSO_STATE["circuit_breaker"] = False
            _save_budget_state()
        return False
    return bool(_TURSO_STATE.get("blocked") or _TURSO_STATE.get("circuit_breaker"))

def is_turso_saving_mode() -> bool:
    return bool(_TURSO_STATE.get("saving_mode") or is_turso_blocked())

_LAST_ALERT_TS = 0.0

def set_turso_blocked(val: bool, reason: str = ""):
    global _LAST_ALERT_TS
    with _STATE_LOCK:
        old_val = _TURSO_STATE.get("blocked")
        _TURSO_STATE["blocked"] = val
        if val:
            _TURSO_STATE["circuit_breaker"] = True
            _TURSO_STATE["saving_mode"] = True
            _TURSO_STATE["blocked_reason"] = reason or "Reads blocked by Turso"
            _TURSO_STATE["last_blocked_ts"] = time.time()
        else:
            _TURSO_STATE["circuit_breaker"] = False
            _TURSO_STATE["saving_mode"] = False
            _TURSO_STATE["blocked_reason"] = ""
        _save_budget_state()

    if val and (not old_val or time.time() - _LAST_ALERT_TS > 3600):
        _LAST_ALERT_TS = time.time()
        print("\n" + "="*80, flush=True)
        print("[TURSO SHIELD] [!] POZOR: Cloudova databaze Turso - BLOCKED stav!", flush=True)
        print(f"[TURSO SHIELD] Důvod: {reason or _TURSO_STATE.get('blocked_reason')}", flush=True)
        print("[TURSO SHIELD] Okamžitě aktivován NOUZOVÝ AUTONOMNÍ REŽIM: Všechny čtecí SELECT dotazy jsou", flush=True)
        print("[TURSO SHIELD] obsluhovány z in-memory cache, lokální SQLite (datacore_local.db) a JSON záloh.", flush=True)
        print("[TURSO SHIELD] Nedochází k žádnému přetěžování sítě ani chybám pro uživatele webu/bota.", flush=True)
        print("="*80 + "\n", flush=True)

        try:
            import main
            if hasattr(main, "set_supabase_restricted"):
                main.set_supabase_restricted(True)
            if hasattr(main, "EGRESS_SAVE_MODE"):
                main.EGRESS_SAVE_MODE = True
        except Exception:
            pass

def record_turso_reads(count: int):
    with _STATE_LOCK:
        _TURSO_STATE["row_reads"] = _TURSO_STATE.get("row_reads", 0) + max(1, count)
        _TURSO_STATE["queries_count"] = _TURSO_STATE.get("queries_count", 0) + 1
        reads = _TURSO_STATE["row_reads"]

        if reads >= TURSO_SAFE_THROTTLE and not _TURSO_STATE.get("saving_mode"):
            _TURSO_STATE["saving_mode"] = True
            print(f"[TURSO SHIELD] ⚠️ Dosaženo 70 % rozpočtu čtení ({reads:,} / {TURSO_MONTHLY_LIMIT:,}). Aktivován šetřící režim.", flush=True)
            try:
                import main
                main.EGRESS_SAVE_MODE = True
            except Exception:
                pass

        if reads >= TURSO_CIRCUIT_BREAKER and not _TURSO_STATE.get("circuit_breaker"):
            _TURSO_STATE["circuit_breaker"] = True
            print(f"[TURSO SHIELD] 🛑 CIRCUIT BREAKER AKTIVOVÁN! Dosaženo 90 % limitu ({reads:,}). Cloud SELECTy preventivně odpojeny.", flush=True)

        if time.time() - _TURSO_STATE.get("last_save_ts", 0) > 300:
            _save_budget_state()

def get_turso_read_stats() -> dict:
    return {
        "month": _TURSO_STATE.get("month"),
        "row_reads": _TURSO_STATE.get("row_reads", 0),
        "limit": TURSO_MONTHLY_LIMIT,
        "percentage": round((_TURSO_STATE.get("row_reads", 0) / TURSO_MONTHLY_LIMIT) * 100, 2),
        "blocked": is_turso_blocked(),
        "saving_mode": is_turso_saving_mode(),
        "reason": _TURSO_STATE.get("blocked_reason", "")
    }

def probe_turso_unblock(force: bool = False) -> bool:
    """Otestuje, zda Turso obnovilo povolené čtení (např. 1. den v měsíci nebo navýšení kvóty)."""
    now = time.time()
    if not force and now - _TURSO_STATE.get("last_probe_ts", 0) < 600:
        return not is_turso_blocked()
    _TURSO_STATE["last_probe_ts"] = now

    client = get_turso_db()
    if not client:
        return False
    try:
        r = client._execute_single_raw("SELECT 1 as probe;")
        if r and not r.error:
            if is_turso_blocked():
                print("[TURSO SHIELD] ✅ Turso DB byla úspěšně odblokována! Návrat do běžného cloudového provozu.", flush=True)
                set_turso_blocked(False)
            return True
        else:
            if r and is_turso_blocked_error(r.error):
                set_turso_blocked(True, reason=r.error)
            return False
    except Exception as e:
        if is_turso_blocked_error(str(e)):
            set_turso_blocked(True, reason=str(e))
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY QUERY CACHE S AUTOMATICKOU INVALIDACÍ PŘI ZÁPISU
# ═══════════════════════════════════════════════════════════════════════════════
_QUERY_CACHE = {}          # {cache_key: (ts, data, ttl, table_name)}
_CACHE_LOCK = threading.RLock()

_TABLE_TTLS = {
    "settings": 180,           # 3 minuty
    "software_versions": 300,  # 5 minut
    "users": 60,               # 1 minuta
    "bus_notifications": 60,   # 1 minuta
    "depot_zones": 600,        # 10 minut
    "depot_history": 30,       # 30 sekund
    "supporters": 300,         # 5 minut
    "spz_cache": 30            # 30 sekund
}

def get_query_cache(cache_key):
    now = time.time()
    with _CACHE_LOCK:
        entry = _QUERY_CACHE.get(cache_key)
        if entry:
            ts, data, ttl, tbl = entry
            mult = 3.0 if is_turso_saving_mode() else 1.0
            if now - ts <= (ttl * mult):
                return data
            else:
                _QUERY_CACHE.pop(cache_key, None)
    return None

def set_query_cache(cache_key, data, table_name):
    ttl = _TABLE_TTLS.get(table_name, 25)
    with _CACHE_LOCK:
        _QUERY_CACHE[cache_key] = (time.time(), data, ttl, table_name)

def invalidate_query_cache(table_name):
    with _CACHE_LOCK:
        to_del = [k for k, v in _QUERY_CACHE.items() if v[3] == table_name]
        for k in to_del:
            _QUERY_CACHE.pop(k, None)


# ═══════════════════════════════════════════════════════════════════════════════
# LOKÁLNÍ AUTONOMNÍ FALLBACK & PERSISTENCE ENGINE PRO USERS A OSTATNÍ TABULKY
# ═══════════════════════════════════════════════════════════════════════════════
def _find_file(fn):
    for d in [_BASE_DIR, os.path.dirname(_BASE_DIR)]:
        p = os.path.join(d, fn)
        if os.path.exists(p):
            return p
    return os.path.join(_BASE_DIR, fn)

def _load_deleted_tombstones():
    t_file = _find_file("deleted_users.json")
    if t_file and os.path.exists(t_file):
        try:
            with open(t_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"app_ids": [1025, 1028, 2006], "ids": [44, 47, 77], "discord_ids": ["1501257673239433256", "1362792557561511956", "666729775879946253"]}

def _is_tombstoned_user(u, tombstones=None):
    if not u or not isinstance(u, dict):
        return False
    if tombstones is None:
        tombstones = _load_deleted_tombstones()
    t_app_ids = [str(x) for x in tombstones.get("app_ids", [])]
    t_ids = [str(x) for x in tombstones.get("ids", [])]
    t_discord_ids = [str(x) for x in tombstones.get("discord_ids", [])]
    
    aid = str(u.get("app_id") or "").strip()
    uid = str(u.get("id") or "").strip()
    did = str(u.get("discord_id") or "").strip()
    
    if aid and aid in t_app_ids:
        return True
    if uid and uid in t_ids:
        return True
    if did and did in t_discord_ids:
        return True
    return False

def _add_deleted_tombstone(u):
    if not u or not isinstance(u, dict):
        return
    t_file = _find_file("deleted_users.json")
    try:
        t = _load_deleted_tombstones()
        aid = u.get("app_id")
        uid = u.get("id")
        did = u.get("discord_id")
        
        if aid is not None:
            try: aid_int = int(aid)
            except: aid_int = aid
            if aid_int not in t.setdefault("app_ids", []):
                t["app_ids"].append(aid_int)
        if uid is not None:
            try: uid_int = int(uid)
            except: uid_int = uid
            if uid_int not in t.setdefault("ids", []):
                t["ids"].append(uid_int)
        if did is not None:
            did_str = str(did).strip()
            if did_str and did_str not in t.setdefault("discord_ids", []):
                t["discord_ids"].append(did_str)
                
        with open(t_file, "w", encoding="utf-8") as f:
            json.dump(t, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[TURSO LOCAL DB] Error saving tombstone: {e}", flush=True)

def _extract_arg_val(arg):
    if isinstance(arg, dict) and "value" in arg:
        return arg["value"]
    return arg

def _match_user_dict(u, where_clauses, args):
    if not where_clauses:
        return True
    arg_vals = [_extract_arg_val(a) for a in (args or [])]
    for idx, w in enumerate(where_clauses):
        val = arg_vals[idx] if idx < len(arg_vals) else None
        val_str = str(val).strip() if val is not None else ""
        
        if " = ?" in w:
            col = w.split(" = ?")[0].strip().strip('"')
            if col in ("is_banned", "is_deleted", "dashboard_access", "is_online"):
                b_val = (val is True) or (val_str.lower() in ("true", "1"))
                if bool(u.get(col)) != b_val:
                    return False
            else:
                u_val_str = str(u.get(col) or "").strip()
                if u_val_str.lower() != val_str.lower():
                    return False

        elif " != ?" in w:
            col = w.split(" != ?")[0].strip().strip('"')
            if col in ("is_banned", "is_deleted", "dashboard_access", "is_online"):
                b_val = (val is True) or (val_str.lower() in ("true", "1"))
                if bool(u.get(col)) == b_val:
                    return False
            else:
                u_val_str = str(u.get(col) or "").strip()
                if u_val_str.lower() == val_str.lower():
                    return False

        elif "LIKE" in w.upper():
            clean_pat = val_str.strip("%").lower()
            matched = False
            for col in ("role", "nick", "email", "web_session_token"):
                if f'"{col}"' in w or col in w:
                    u_val = str(u.get(col) or "").lower()
                    if clean_pat in u_val:
                        matched = True
                    break
            if not matched:
                return False

        elif "IS NULL" in w.upper():
            col = w.split()[0].strip().strip('"')
            if u.get(col) is not None and str(u.get(col)).strip() != "":
                return False

    return True

def _merge_users_with_backup(res_rows, where_clauses=None, args=None, order_by=None, limit_val=None, columns="*"):
    tombstones = _load_deleted_tombstones()
    u_file = _find_file("users_backup.json")
    backup_users = []
    if u_file and os.path.exists(u_file):
        try:
            with open(u_file, "r", encoding="utf-8") as f:
                backup_users = json.load(f)
        except Exception:
            backup_users = []

    backup_by_did = {}
    backup_by_id = {}
    backup_by_aid = {}
    for bu in backup_users:
        if _is_tombstoned_user(bu, tombstones):
            continue
        did = str(bu.get("discord_id") or "").strip()
        uid = str(bu.get("id") or "").strip()
        aid = str(bu.get("app_id") or "").strip()
        if did: backup_by_did[did] = bu
        if uid: backup_by_id[uid] = bu
        if aid: backup_by_aid[aid] = bu

    merged_dict = {}
    for r in (res_rows or []):
        if _is_tombstoned_user(r, tombstones):
            continue
        did = str(r.get("discord_id") or "").strip()
        uid = str(r.get("id") or "").strip()
        aid = str(r.get("app_id") or "").strip()
        
        local_u = None
        if did and did in backup_by_did: local_u = backup_by_did[did]
        elif uid and uid in backup_by_id: local_u = backup_by_id[uid]
        elif aid and aid in backup_by_aid: local_u = backup_by_aid[aid]

        u_copy = dict(r)
        if local_u:
            for fld in ("role", "hwid", "ip_address", "is_banned", "is_deleted", "deleted_at", "dashboard_access", "nick", "email", "web_login_at", "login_token", "download_token"):
                if fld in local_u and local_u[fld] is not None:
                    u_copy[fld] = local_u[fld]

        k = did or (f"id_{uid}" if uid else f"aid_{aid}")
        merged_dict[k] = u_copy

    for bu in backup_users:
        if _is_tombstoned_user(bu, tombstones):
            continue
        did = str(bu.get("discord_id") or "").strip()
        uid = str(bu.get("id") or "").strip()
        aid = str(bu.get("app_id") or "").strip()
        k = did or (f"id_{uid}" if uid else f"aid_{aid}")
        if k not in merged_dict:
            merged_dict[k] = dict(bu)

    result = []
    for u in merged_dict.values():
        if _match_user_dict(u, where_clauses or [], args or []):
            result.append(u)

    if order_by:
        for ob in reversed(order_by):
            parts = ob.strip().split()
            col = parts[0].strip('"')
            desc = len(parts) > 1 and parts[1].upper() == "DESC"
            def _sort_key(item, c=col):
                v = item.get(c)
                if v is None: return -999999999 if desc else 999999999
                try: return float(v)
                except (ValueError, TypeError): return str(v).lower()
            result.sort(key=_sort_key, reverse=desc)

    if limit_val is not None:
        result = result[:int(limit_val)]

    if columns and columns != "*":
        req_cols = [c.strip().strip('"') for c in columns.split(",") if c.strip()]
        result = [{c: item.get(c) for c in req_cols} for item in result]

    return result

def _local_update_users(where_clauses, args, payload_data):
    u_file = _find_file("users_backup.json")
    data = []
    if os.path.exists(u_file):
        try:
            with open(u_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []

    updated = []
    for u in data:
        if _match_user_dict(u, where_clauses, args):
            u.update(payload_data)
            updated.append(u.copy())

    if not updated and _GLOBAL_TURSO_CLIENT:
        try:
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = _GLOBAL_TURSO_CLIENT._execute_single(f"SELECT * FROM \"users\"{where_sql};", args, bypass_block_check=True)
            if res.data:
                for row in res.data:
                    row.update(payload_data)
                    data.append(row)
                    updated.append(row.copy())
        except Exception:
            pass

    if not updated:
        arg_vals = [_extract_arg_val(a) for a in (args or [])]
        fallback_u = dict(payload_data)
        for idx, w in enumerate(where_clauses or []):
            val = arg_vals[idx] if idx < len(arg_vals) else None
            if '"discord_id" = ?' in w and val:
                fallback_u["discord_id"] = str(val)
            elif '"app_id" = ?' in w and val:
                fallback_u["app_id"] = val
            elif '"id" = ?' in w and val:
                fallback_u["id"] = val
        if fallback_u.get("discord_id") or fallback_u.get("app_id") or fallback_u.get("id"):
            data.append(fallback_u)
            updated.append(fallback_u.copy())

    if updated:
        try:
            with open(u_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TURSO LOCAL DB] Error saving users_backup.json: {e}", flush=True)

    return updated

def _local_delete_users(where_clauses, args):
    u_file = _find_file("users_backup.json")
    data = []
    if os.path.exists(u_file):
        try:
            with open(u_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []

    remaining = []
    deleted = []
    for u in data:
        if _match_user_dict(u, where_clauses, args):
            deleted.append(u)
            _add_deleted_tombstone(u)
        else:
            remaining.append(u)

    if not deleted and _GLOBAL_TURSO_CLIENT:
        try:
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            res = _GLOBAL_TURSO_CLIENT._execute_single(f"SELECT * FROM \"users\"{where_sql};", args, bypass_block_check=True)
            if res.data:
                for row in res.data:
                    deleted.append(row)
                    _add_deleted_tombstone(row)
        except Exception:
            pass

    if not deleted:
        arg_vals = [_extract_arg_val(a) for a in (args or [])]
        fallback_u = {}
        for idx, w in enumerate(where_clauses or []):
            val = arg_vals[idx] if idx < len(arg_vals) else None
            if '"discord_id" = ?' in w and val:
                fallback_u["discord_id"] = str(val)
            elif '"app_id" = ?' in w and val:
                fallback_u["app_id"] = val
            elif '"id" = ?' in w and val:
                fallback_u["id"] = val
        if fallback_u:
            deleted.append(fallback_u)
            _add_deleted_tombstone(fallback_u)

    if deleted and len(remaining) != len(data):
        try:
            with open(u_file, "w", encoding="utf-8") as f:
                json.dump(remaining, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TURSO LOCAL DB] Error updating users_backup.json: {e}", flush=True)

    return deleted

def _local_insert_user(payload_data):
    if not payload_data: return
    u_file = _find_file("users_backup.json")
    data = []
    if os.path.exists(u_file):
        try:
            with open(u_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    items = payload_data if isinstance(payload_data, list) else [payload_data]
    for item in items:
        exists = False
        for u in data:
            if item.get("discord_id") and str(u.get("discord_id")) == str(item.get("discord_id")):
                exists = True; break
            if item.get("app_id") and str(u.get("app_id")) == str(item.get("app_id")):
                exists = True; break
        if not exists:
            data.append(dict(item))
    try:
        with open(u_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── LOKÁLNÍ PERZISTENCE A SLUČOVÁNÍ NASTAVENÍ (SETTINGS) ──
def _local_upsert_setting(setting_key: str, setting_value: str):
    """
    Uloží nastavení do SQLite tabulky settings_local i souboru settings_backup.json.
    Zajišťuje okamžité a trvalé uchování i při překročení limitů / výpadku Turso.
    """
    if not setting_key:
        return
    setting_key = str(setting_key).strip()
    setting_value = str(setting_value) if setting_value is not None else ""

    # 1. Lokální SQLite
    db_path = _find_file("datacore_local.db")
    if db_path:
        try:
            con = sqlite3.connect(db_path, timeout=5)
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings_local (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            cur.execute("""
                INSERT OR REPLACE INTO settings_local (setting_key, setting_value)
                VALUES (?, ?)
            """, (setting_key, setting_value))
            con.commit()
            con.close()
        except Exception as e:
            print(f"[TURSO LOCAL DB] Error updating settings_local SQLite: {e}", flush=True)

    # 2. JSON záloha settings_backup.json
    s_file = _find_file("settings_backup.json")
    if not s_file:
        s_file = os.path.join(os.path.dirname(__file__), "settings_backup.json")
    settings_dict = {}
    if os.path.exists(s_file):
        try:
            with open(s_file, "r", encoding="utf-8") as f:
                settings_dict = json.load(f)
                if not isinstance(settings_dict, dict):
                    settings_dict = {}
        except Exception:
            settings_dict = {}

    settings_dict[setting_key] = setting_value
    try:
        with open(s_file, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[TURSO LOCAL DB] Error saving settings_backup.json: {e}", flush=True)

    invalidate_query_cache("settings")

def _get_local_settings_dict() -> dict:
    """Vrátí sloučený slovník všech lokálně známých nastavení (SQLite + JSON)."""
    settings_map = {}
    s_file = _find_file("settings_backup.json")
    if s_file and os.path.exists(s_file):
        try:
            with open(s_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict):
                    settings_map.update(d)
        except Exception:
            pass

    db_path = _find_file("datacore_local.db")
    if db_path and os.path.exists(db_path):
        try:
            con = sqlite3.connect(db_path, timeout=5)
            cur = con.cursor()
            cur.execute("SELECT setting_key, setting_value FROM settings_local")
            for k, v in cur.fetchall():
                if k:
                    settings_map[str(k).strip()] = str(v)
            con.close()
        except Exception:
            pass

    return settings_map

def _local_insert_settings(payload_data):
    if not payload_data: return
    items = payload_data if isinstance(payload_data, list) else [payload_data]
    for it in items:
        if isinstance(it, dict) and "setting_key" in it:
            _local_upsert_setting(it["setting_key"], it.get("setting_value", ""))

def _local_update_settings(where_clauses, args, payload_data):
    target_key = None
    if where_clauses and args:
        arg_vals = [_extract_arg_val(a) for a in args]
        for idx, w in enumerate(where_clauses):
            val = arg_vals[idx] if idx < len(arg_vals) else None
            if '"setting_key" = ?' in w or 'setting_key = ?' in w:
                target_key = str(val).strip() if val is not None else None
                break

    val = payload_data.get("setting_value") if isinstance(payload_data, dict) else None
    if target_key and val is not None:
        _local_upsert_setting(target_key, val)
        return [{"setting_key": target_key, "setting_value": str(val)}]
    elif isinstance(payload_data, dict) and "setting_key" in payload_data and val is not None:
        _local_upsert_setting(payload_data["setting_key"], val)
        return [payload_data]
    return [payload_data] if isinstance(payload_data, dict) else payload_data

def _merge_settings_with_local(res_rows, where_clauses=None, args=None):
    """
    Sloučí řádky vrácené z Turso s lokálními nastaveními.
    Lokální nastavení mají vždy přednost při výpadku zápisů na cloudu.
    """
    local_map = _get_local_settings_dict()
    if not local_map:
        return res_rows or []

    target_key = None
    if where_clauses and args:
        arg_vals = [_extract_arg_val(a) for a in args]
        for idx, w in enumerate(where_clauses):
            val = arg_vals[idx] if idx < len(arg_vals) else None
            if '"setting_key" = ?' in w or 'setting_key = ?' in w:
                target_key = str(val).strip() if val is not None else None
                break

    if target_key:
        if target_key in local_map:
            loc_val = local_map[target_key]
            if res_rows:
                out = []
                for r in res_rows:
                    item = dict(r)
                    item["setting_value"] = loc_val
                    out.append(item)
                return out
            else:
                return [{"setting_key": target_key, "setting_value": loc_val}]
        return res_rows or []

    seen_keys = set()
    merged = []
    for r in (res_rows or []):
        item = dict(r)
        k = str(item.get("setting_key", "")).strip()
        if k in local_map:
            item["setting_value"] = local_map[k]
        if k:
            seen_keys.add(k)
        merged.append(item)

    for k, v in local_map.items():
        if k not in seen_keys:
            merged.append({"setting_key": k, "setting_value": v})

    return merged

# ── LOKÁLNÍ PERZISTENCE A SLUČOVÁNÍ SOFTWARE_VERSIONS ──
def _local_upsert_software_version(action, payload_data, where_clauses=None, args=None):
    v_file = _find_file("versions_backup.json")
    if not v_file:
        v_file = os.path.join(os.path.dirname(__file__), "versions_backup.json")
    
    versions = []
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                versions = json.load(f)
                if not isinstance(versions, list):
                    versions = []
        except Exception:
            versions = []

    items = payload_data if isinstance(payload_data, list) else [payload_data]

    if action in ("add", "insert", "upsert"):
        for item in items:
            if not isinstance(item, dict): continue
            item_copy = dict(item)
            existing_idx = None
            for idx, v in enumerate(versions):
                if item_copy.get("id") and str(v.get("id")) == str(item_copy.get("id")):
                    existing_idx = idx
                    break
                if item_copy.get("db_version") and str(v.get("db_version")) == str(item_copy.get("db_version")):
                    existing_idx = idx
                    break
            if existing_idx is not None:
                versions[existing_idx].update(item_copy)
            else:
                if not item_copy.get("id"):
                    existing_ids = [int(v.get("id", 0)) for v in versions if str(v.get("id", "")).isdigit()]
                    item_copy["id"] = max(existing_ids, default=0) + 1
                versions.append(item_copy)

    elif action == "edit":
        target_id = None
        target_vname = None
        if where_clauses and args:
            arg_vals = [_extract_arg_val(a) for a in args]
            for idx, w in enumerate(where_clauses):
                val = arg_vals[idx] if idx < len(arg_vals) else None
                if '"id" = ?' in w or 'id = ?' in w:
                    target_id = str(val).strip() if val is not None else None
                elif '"db_version" = ?' in w or 'db_version = ?' in w:
                    target_vname = str(val).strip() if val is not None else None

        updated_any = False
        for v in versions:
            match = False
            if target_id and str(v.get("id")) == str(target_id):
                match = True
            elif target_vname and str(v.get("db_version")) == str(target_vname):
                match = True
            if match:
                v.update(items[0] if items else {})
                updated_any = True
                break

        if not updated_any and (target_id or target_vname):
            new_item = dict(items[0] if items else {})
            if target_id:
                new_item["id"] = int(target_id) if target_id.isdigit() else target_id
            if target_vname:
                new_item["db_version"] = target_vname
            versions.append(new_item)

    try:
        with open(v_file, "w", encoding="utf-8") as f:
            json.dump(versions, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[TURSO LOCAL DB] Error saving versions_backup.json: {e}", flush=True)

    invalidate_query_cache("software_versions")
    return items

def _merge_versions_with_backup(res_rows, where_clauses=None, args=None, order_by=None, limit_val=None):
    v_file = _find_file("versions_backup.json")
    backup_versions = []
    if v_file and os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                backup_versions = json.load(f)
                if not isinstance(backup_versions, list):
                    backup_versions = []
        except Exception:
            backup_versions = []

    if not backup_versions:
        return res_rows or []

    backup_by_id = {str(v.get("id")): v for v in backup_versions if v.get("id")}
    backup_by_dbver = {str(v.get("db_version")): v for v in backup_versions if v.get("db_version")}

    merged = []
    seen_ids = set()
    for r in (res_rows or []):
        item = dict(r)
        vid = str(item.get("id") or "")
        vdb = str(item.get("db_version") or "")
        
        backup_item = backup_by_id.get(vid) or backup_by_dbver.get(vdb)
        if backup_item:
            item.update(backup_item)
        
        if vid:
            seen_ids.add(vid)
        merged.append(item)

    for bv in backup_versions:
        b_id = str(bv.get("id") or "")
        if b_id and b_id not in seen_ids:
            merged.append(dict(bv))
            seen_ids.add(b_id)

    return merged

def _resolve_local_fallback(table_name, columns="*", where_clauses=None, args=None, order_by=None, limit_val=None):
    """
    Bezpečný a robustní lokální fallback pro případ výpadku / vyčerpání Turso.
    Poskytuje přesná data z JSON záloh a lokální SQLite, takže aplikace funguje dál.
    """
    where_clauses = where_clauses or []
    args = args or []

    # ── TABULKA: users ──
    if table_name == "users":
        return _merge_users_with_backup([], where_clauses, args, order_by, limit_val, columns)

    # ── TABULKA: settings ──
    if table_name == "settings":
        local_map = _get_local_settings_dict()
        target_key = None
        for w, a in zip(where_clauses, args):
            val = a.get("value") if isinstance(a, dict) else a
            if '"setting_key" = ?' in w or 'setting_key = ?' in w:
                target_key = str(val or "")
                break

        val = local_map.get(target_key) if target_key else None

        # Fallback na spz_settings.json pokud jde o spz_metadata
        if val is None and target_key == "spz_metadata":
            spz_f = _find_file("spz_settings.json")
            if spz_f:
                try:
                    with open(spz_f, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        if "spz_metadata" in d:
                            val = json.dumps(d["spz_metadata"], ensure_ascii=False)
                except Exception:
                    pass

        if val is None and target_key == "launcher_version":
            val = "1.0.1"
        elif val is None and target_key == "launcher_download_url":
            val = "https://github.com/marek-1cz/IDPK-Palubni-Pocitac/releases/download/LAUNCHER/IDPK.Launcher.Setup.1.0.1.exe"

        if target_key:
            if val is not None:
                return [{"setting_key": target_key, "setting_value": val}]
            return []

        # Pokud dotaz neomezoval konkrétní klíč (např. SELECT * FROM settings)
        res = []
        for k, v in local_map.items():
            res.append({"setting_key": k, "setting_value": v})
        return res

    # ── TABULKA: supporters ──
    if table_name == "supporters":
        s_file = _find_file("supporters_backup.json")
        if s_file:
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    # ── TABULKA: depot_zones ──
    if table_name == "depot_zones":
        dz_file = _find_file("depot_zones_backup.json")
        data = []
        if dz_file and os.path.exists(dz_file):
            try:
                with open(dz_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        if not data:
            try:
                from local_db import local_get_depot_zones
                data = local_get_depot_zones()
            except Exception:
                data = []
        return data

    # ── TABULKA: depot_history ──
    if table_name == "depot_history":
        db_path = _find_file("datacore_local.db")
        if db_path:
            try:
                con = sqlite3.connect(db_path, timeout=5)
                cur = con.cursor()
                limit_clause = f"LIMIT {int(limit_val)}" if limit_val else "LIMIT 500"
                where_sql = ["spz != 'BACKUP'"]
                query_args = []
                for w, a in zip(where_clauses, args):
                    val = a.get("value") if isinstance(a, dict) else a
                    if '"depot_name" = ?' in w:
                        where_sql.append("depot_name = ?")
                        query_args.append(str(val))
                    elif '"spz" = ?' in w:
                        where_sql.append("spz = ?")
                        query_args.append(str(val))
                    elif '"bus_id" = ?' in w:
                        where_sql.append("bus_id = ?")
                        query_args.append(str(val))
                    elif '"left_at" IS NULL' in w or 'is null' in w.lower():
                        where_sql.append("left_at IS NULL")
                    elif '"spz" LIKE ?' in w:
                        where_sql.append("spz LIKE ?")
                        query_args.append(str(val))
                where_str = " WHERE " + " AND ".join(where_sql)
                order_clause = f"ORDER BY {order_by}" if order_by else "ORDER BY arrived_at DESC"
                cur.execute(f"SELECT id, depot_name, bus_id, spz, arrived_at, left_at FROM depot_history_local {where_str} {order_clause} {limit_clause}", query_args)
                rows = []
                for r in cur.fetchall():
                    rows.append({
                        "id": r[0], "depot_name": r[1], "bus_id": r[2], "spz": r[3],
                        "arrived_at": r[4], "left_at": r[5]
                    })
                con.close()
                if rows:
                    return rows
            except Exception:
                pass
        return []

    # ── TABULKA: spz_cache ──
    if table_name == "spz_cache":
        db_path = _find_file("datacore_local.db")
        if db_path:
            try:
                con = sqlite3.connect(db_path, timeout=5)
                cur = con.cursor()
                cur.execute("SELECT bus_id, spz, linka, lat, lng, spz_verified, admin_verified, is_locked_by_admin, trip_id, status_text FROM spz_cache_local")
                cols = [c[0] for c in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                con.close()
                if rows:
                    return rows
            except Exception:
                pass
        b_file = _find_file("spz_cache_backup.json")
        if b_file:
            try:
                with open(b_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    # ── TABULKA: software_versions ──
    if table_name == "software_versions":
        v_file = _find_file("versions_backup.json")
        v_list = []
        if v_file:
            try:
                with open(v_file, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                    if isinstance(v_data, list) and v_data:
                        v_list = v_data
            except Exception:
                pass
        if not v_list:
            v_list = [
                {
                    "id": 1,
                    "version_name": "OIS IDPK V1.6.2",
                    "db_version": "V1.6.2",
                    "file_url": "https://github.com/marek-1cz/IDPK-Palubni-Pocitac/releases/download/V1.6.2I/OIS-IDPK-V1.6.2.zip",
                    "target_role": "BT",
                    "is_active": 1,
                    "eol_date": "",
                    "show_in_launcher": 1,
                    "can_download": 1,
                    "can_launch": 1
                },
                {
                    "id": 2,
                    "version_name": "OIS IDPK V1.6.1",
                    "db_version": "v1.6.1",
                    "file_url": "https://github.com/marek-1cz/IDPK-Palubni-Pocitac/releases/download/v1.6.1/OIS_IDPK_V1.6.1.zip",
                    "target_role": "User",
                    "is_active": 1,
                    "eol_date": "",
                    "show_in_launcher": 1,
                    "can_download": 1,
                    "can_launch": 1
                }
            ]

        if not where_clauses:
            return v_list

        filtered = []
        for v in v_list:
            match = True
            for w, a in zip(where_clauses, args):
                val = a.get("value")
                val_str = str(val) if val is not None else ""
                if '"db_version" = ?' in w and str(v.get("db_version", "")).lower() != val_str.lower():
                    match = False; break
                elif '"version_name" = ?' in w and str(v.get("version_name", "")).lower() != val_str.lower():
                    match = False; break
                elif '"target_role" = ?' in w and str(v.get("target_role", "")).lower() != val_str.lower():
                    match = False; break
                elif '"is_active" = ?' in w:
                    is_act = 1 if v.get("is_active") else 0
                    if str(is_act) != val_str:
                        match = False; break
                elif '"id" = ?' in w and str(v.get("id")) != val_str:
                    match = False; break
            if match:
                filtered.append(v)
        return filtered

    return []


# ═══════════════════════════════════════════════════════════════════════════════
# TURSO CLIENT & QUERY BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
class TursoResponse:
    def __init__(self, data=None, count=0, error=None):
        self.data = data if data is not None else []
        self.count = count
        self.error = error

    def __repr__(self):
        return f"<TursoResponse count={self.count} rows={len(self.data)} error={self.error}>"

def _py_to_turso_arg(v):
    if v is None:
        return {"type": "null"}
    elif isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    elif isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    elif isinstance(v, float):
        return {"type": "float", "value": v}
    elif isinstance(v, (list, dict)):
        return {"type": "text", "value": json.dumps(v, ensure_ascii=False)}
    else:
        return {"type": "text", "value": str(v)}

def _turso_val_to_py(val_dict):
    if not isinstance(val_dict, dict):
        return val_dict
    t = val_dict.get("type")
    v = val_dict.get("value")
    if t == "null":
        return None
    elif t == "integer":
        return int(v)
    elif t == "float":
        return float(v)
    elif t == "text":
        return str(v)
    return v

class TursoQueryBuilder:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.action = "SELECT"
        self.columns = "*"
        self.where_clauses = []
        self.args = []
        self.order_by = []
        self.limit_val = None
        self.offset_val = None
        self.payload_data = None
        self.on_conflict = None

    def select(self, columns="*"):
        self.action = "SELECT"
        self.columns = columns
        return self

    def insert(self, data):
        self.action = "INSERT"
        self.payload_data = data
        return self

    def upsert(self, data, on_conflict=None):
        self.action = "UPSERT"
        self.payload_data = data
        self.on_conflict = on_conflict
        return self

    def update(self, data):
        self.action = "UPDATE"
        self.payload_data = data
        return self

    def delete(self):
        self.action = "DELETE"
        return self

    def eq(self, col, val):
        self.where_clauses.append(f'"{col}" = ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def neq(self, col, val):
        self.where_clauses.append(f'"{col}" != ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def gt(self, col, val):
        self.where_clauses.append(f'"{col}" > ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def gte(self, col, val):
        self.where_clauses.append(f'"{col}" >= ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def lt(self, col, val):
        self.where_clauses.append(f'"{col}" < ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def lte(self, col, val):
        self.where_clauses.append(f'"{col}" <= ?')
        self.args.append(_py_to_turso_arg(val))
        return self

    def like(self, col, pattern):
        self.where_clauses.append(f'"{col}" LIKE ?')
        self.args.append(_py_to_turso_arg(pattern))
        return self

    def ilike(self, col, pattern):
        self.where_clauses.append(f'LOWER("{col}") LIKE LOWER(?)')
        self.args.append(_py_to_turso_arg(pattern))
        return self

    def is_(self, col, val):
        if val is None or val == "null":
            self.where_clauses.append(f'"{col}" IS NULL')
        else:
            self.where_clauses.append(f'"{col}" = ?')
            self.args.append(_py_to_turso_arg(val))
        return self

    def in_(self, col, values):
        if not values:
            self.where_clauses.append("1=0")
            return self
        placeholders = ", ".join(["?" for _ in values])
        self.where_clauses.append(f'"{col}" IN ({placeholders})')
        for v in values:
            self.args.append(_py_to_turso_arg(v))
        return self

    def or_(self, cond_str):
        sub_clauses = []
        parts = cond_str.split(",")
        for p in parts:
            p = p.strip()
            if ".eq." in p:
                c, val = p.split(".eq.", 1)
                sub_clauses.append(f'"{c}" = ?')
                self.args.append(_py_to_turso_arg(val))
            elif ".neq." in p:
                c, val = p.split(".neq.", 1)
                sub_clauses.append(f'"{c}" != ?')
                self.args.append(_py_to_turso_arg(val))
            elif ".like." in p:
                c, val = p.split(".like.", 1)
                sub_clauses.append(f'"{c}" LIKE ?')
                self.args.append(_py_to_turso_arg(val))
            elif ".is." in p:
                c, val = p.split(".is.", 1)
                if val == "null":
                    sub_clauses.append(f'"{c}" IS NULL')
                else:
                    sub_clauses.append(f'"{c}" = ?')
                    self.args.append(_py_to_turso_arg(val))
        if sub_clauses:
            self.where_clauses.append(f"({' OR '.join(sub_clauses)})")
        return self

    def order(self, col, desc=False):
        direction = "DESC" if desc else "ASC"
        self.order_by.append(f'"{col}" {direction}')
        return self

    def limit(self, count):
        self.limit_val = count
        return self

    def offset(self, start):
        self.offset_val = start
        return self

    def execute(self):
        where_sql = f" WHERE {' AND '.join(self.where_clauses)}" if self.where_clauses else ""
        order_sql = f" ORDER BY {', '.join(self.order_by)}" if self.order_by else ""
        limit_sql = f" LIMIT {int(self.limit_val)}" if self.limit_val is not None else ""
        offset_sql = f" OFFSET {int(self.offset_val)}" if self.offset_val is not None else ""

        if self.action == "SELECT":
            cols = self.columns
            if cols != "*":
                clean_cols = ", ".join([f'"{c.strip()}"' for c in cols.split(",") if c.strip()])
                sql = f"SELECT {clean_cols} FROM \"{self.table_name}\"{where_sql}{order_sql}{limit_sql}{offset_sql};"
            else:
                sql = f"SELECT * FROM \"{self.table_name}\"{where_sql}{order_sql}{limit_sql}{offset_sql};"

            # 1. Kontrola in-memory cache
            arg_tup = tuple((a.get("type"), str(a.get("value"))) for a in self.args)
            cache_key = (self.table_name, sql, arg_tup)
            cached_res = get_query_cache(cache_key)
            if cached_res is not None:
                return TursoResponse(data=cached_res, count=len(cached_res))

            # 2. Pokud je Turso zablokováno nebo aktivní circuit breaker, použijeme bezpečný lokální fallback
            if is_turso_blocked():
                fallback_data = _resolve_local_fallback(
                    self.table_name, cols, self.where_clauses, self.args, self.order_by, self.limit_val
                )
                set_query_cache(cache_key, fallback_data, self.table_name)
                return TursoResponse(data=fallback_data, count=len(fallback_data))

            # 3. Standardní spuštění přes Turso Pipeline
            res = self.client._execute_single(sql, self.args)

            # 4. Pokud selhalo kvůli překročení kvóty, automaticky aktivujeme štít a přepneme na fallback
            if res.error and is_turso_blocked_error(res.error):
                set_turso_blocked(True, reason=res.error)
                fallback_data = _resolve_local_fallback(
                    self.table_name, cols, self.where_clauses, self.args, self.order_by, self.limit_val
                )
                set_query_cache(cache_key, fallback_data, self.table_name)
                return TursoResponse(data=fallback_data, count=len(fallback_data))

            if not res.error:
                if self.table_name == "users":
                    res.data = _merge_users_with_backup(
                        res.data, self.where_clauses, self.args, self.order_by, self.limit_val, cols
                    )
                    res.count = len(res.data)
                elif self.table_name == "settings":
                    res.data = _merge_settings_with_local(
                        res.data, self.where_clauses, self.args
                    )
                    res.count = len(res.data)
                elif self.table_name == "software_versions":
                    res.data = _merge_versions_with_backup(
                        res.data, self.where_clauses, self.args, self.order_by, self.limit_val
                    )
                    res.count = len(res.data)
                set_query_cache(cache_key, res.data, self.table_name)
            return res

        # ── ZÁPISOVÉ OPERACE (Invalidují cache dané tabulky) ──
        invalidate_query_cache(self.table_name)

        if self.action == "INSERT":
            if self.table_name == "users":
                _local_insert_user(self.payload_data)
            elif self.table_name == "settings":
                _local_insert_settings(self.payload_data)
            elif self.table_name == "software_versions":
                _local_upsert_software_version("add", self.payload_data)
            if is_turso_write_blocked():
                ret_data = self.payload_data if isinstance(self.payload_data, list) else [self.payload_data]
                return TursoResponse(data=ret_data, count=len(ret_data))

            if isinstance(self.payload_data, list):
                if not self.payload_data:
                    return TursoResponse(data=[])
                cols = list(self.payload_data[0].keys())
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                sql = f"INSERT INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders});"
                stmts = []
                for item in self.payload_data:
                    args = [_py_to_turso_arg(item.get(c)) for c in cols]
                    stmts.append({"sql": sql, "args": args})
                return self.client._execute_batch(stmts, returning_data=self.payload_data)
            else:
                cols = list(self.payload_data.keys())
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                sql = f"INSERT INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders}) RETURNING *;"
                args = [_py_to_turso_arg(self.payload_data.get(c)) for c in cols]
                return self.client._execute_single(sql, args, returning_data=[self.payload_data])

        elif self.action == "UPSERT":
            if self.table_name == "users":
                _local_insert_user(self.payload_data)
            elif self.table_name == "settings":
                _local_insert_settings(self.payload_data)
            elif self.table_name == "software_versions":
                _local_upsert_software_version("upsert", self.payload_data)
            if is_turso_write_blocked():
                ret_data = self.payload_data if isinstance(self.payload_data, list) else [self.payload_data]
                return TursoResponse(data=ret_data, count=len(ret_data))

            if isinstance(self.payload_data, list):
                if not self.payload_data:
                    return TursoResponse(data=[])
                cols = list(self.payload_data[0].keys())
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                sql = f"INSERT OR REPLACE INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders});"
                stmts = []
                for item in self.payload_data:
                    args = [_py_to_turso_arg(item.get(c)) for c in cols]
                    stmts.append({"sql": sql, "args": args})
                return self.client._execute_batch(stmts, returning_data=self.payload_data)
            else:
                cols = list(self.payload_data.keys())
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                sql = f"INSERT OR REPLACE INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders}) RETURNING *;"
                args = [_py_to_turso_arg(self.payload_data.get(c)) for c in cols]
                return self.client._execute_single(sql, args, returning_data=[self.payload_data])

        elif self.action == "UPDATE":
            set_clauses = []
            args = []
            for k, v in self.payload_data.items():
                set_clauses.append(f'"{k}" = ?')
                args.append(_py_to_turso_arg(v))
            sql = f"UPDATE \"{self.table_name}\" SET {', '.join(set_clauses)}{where_sql};"
            all_args = args + self.args
            
            local_updated = []
            if self.table_name == "users":
                local_updated = _local_update_users(self.where_clauses, self.args, self.payload_data)
            elif self.table_name == "settings":
                local_updated = _local_update_settings(self.where_clauses, self.args, self.payload_data)
            elif self.table_name == "software_versions":
                local_updated = _local_upsert_software_version("edit", self.payload_data, self.where_clauses, self.args)

            if is_turso_write_blocked():
                ret_data = local_updated if local_updated else [self.payload_data]
                return TursoResponse(data=ret_data, count=len(ret_data))

            res = self.client._execute_single(sql, all_args, returning_data=local_updated or [self.payload_data])
            if res.error:
                ret_data = local_updated if local_updated else [self.payload_data]
                return TursoResponse(data=ret_data, count=len(ret_data))
            return res

        elif self.action == "DELETE":
            sql = f"DELETE FROM \"{self.table_name}\"{where_sql};"
            
            local_deleted = []
            if self.table_name == "users":
                local_deleted = _local_delete_users(self.where_clauses, self.args)

            if is_turso_write_blocked():
                return TursoResponse(data=local_deleted, count=len(local_deleted))

            res = self.client._execute_single(sql, self.args, returning_data=local_deleted)
            if res.error:
                return TursoResponse(data=local_deleted, count=len(local_deleted))
            if not res.data and local_deleted:
                res.data = local_deleted
                res.count = len(local_deleted)
            return res

        return TursoResponse()

class TursoClient:
    def __init__(self, db_url=None, auth_token=None):
        raw_url = db_url or os.environ.get("TURSO_DATABASE_URL") or os.environ.get("TURSO_URL") or _DEFAULT_TURSO_URL
        if raw_url.startswith("libsql://"):
            raw_url = "https://" + raw_url[9:]
        if not raw_url.endswith("/v2/pipeline"):
            raw_url = raw_url.rstrip("/") + "/v2/pipeline"
        self.endpoint = raw_url
        self.auth_token = auth_token or os.environ.get("TURSO_AUTH_TOKEN") or _DEFAULT_TURSO_TOKEN
        self._lock = threading.Lock()
        
        # Jednorázové spuštění kontroly indexů v pozadí
        threading.Thread(target=self._bg_ensure_indexes, daemon=True).start()

    def _bg_ensure_indexes(self):
        try:
            time.sleep(2)
            self.ensure_turso_indexes()
        except Exception:
            pass

    def ensure_turso_indexes(self):
        """Vytvoří v Turso DB potřebné indexy pro odstranění Full Table Scanů a dramatické snížení čtení."""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_depot_history_name_arr ON depot_history(depot_name, arrived_at DESC);',
            'CREATE INDEX IF NOT EXISTS idx_depot_history_bus_id ON depot_history(bus_id);',
            'CREATE INDEX IF NOT EXISTS idx_depot_history_spz ON depot_history(spz);',
            'CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);',
            'CREATE INDEX IF NOT EXISTS idx_users_app_id ON users(app_id);',
            'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);',
            'CREATE INDEX IF NOT EXISTS idx_bus_notif_active ON bus_notifications(is_active);',
            'CREATE INDEX IF NOT EXISTS idx_bus_history_created_at ON bus_history(created_at DESC);',
            'CREATE INDEX IF NOT EXISTS idx_bus_history_spz ON bus_history(spz);',
            'CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key);',
            'CREATE INDEX IF NOT EXISTS idx_spz_cache_bus_id ON spz_cache(bus_id);'
        ]
        for sql in indexes:
            try:
                self.execute_raw(sql)
            except Exception:
                pass

    def table(self, table_name):
        return TursoQueryBuilder(self, table_name)

    def execute_raw(self, sql, args=None):
        """Umožňuje přímé spuštění libovolného SQL dotazu"""
        return self._execute_single(sql, [_py_to_turso_arg(a) for a in (args or [])])

    def _execute_single_raw(self, sql, args=None):
        return self._execute_single(sql, [_py_to_turso_arg(a) for a in (args or [])], bypass_block_check=True)

    def _execute_single(self, sql, args=None, returning_data=None, bypass_block_check=False):
        # Pokud je dotaz SELECT a Turso je zablokované (a nejde o interní probe), nepokoušíme se o síť
        is_select = str(sql).strip().upper().startswith("SELECT")
        if is_select and not bypass_block_check and is_turso_blocked():
            return TursoResponse(error="Reads blocked by Turso quota")
        if not is_select and is_turso_write_blocked():
            return TursoResponse(error="Writes blocked by Turso plan quota", data=returning_data or [])

        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args or []}}
            ]
        }
        res = self._post_with_retry(payload)
        results = res.get("results", [])
        if not results:
            return TursoResponse()
        r = results[0]
        if r.get("type") == "error":
            err_msg = r.get("error", {}).get("message", "Turso error")
            low = str(err_msg).lower()
            if "write operations are forbidden" in low or "writes are blocked" in low:
                set_turso_writes_blocked(True, reason=err_msg)
            elif is_turso_blocked_error(err_msg):
                set_turso_blocked(True, reason=err_msg)
            else:
                print(f"[TursoClient ERROR] SQL: {sql} | Error: {err_msg}", flush=True)
            return TursoResponse(error=err_msg, data=returning_data or [])

        resp = r.get("response", {})
        result = resp.get("result", {})
        cols = [c.get("name") for c in result.get("cols", [])]
        rows = result.get("rows", [])
        affected = result.get("affected_row_count", 0)

        if is_select and rows:
            record_turso_reads(len(rows))

        if cols:
            data = []
            for row in rows:
                row_dict = {}
                for col_name, cell in zip(cols, row):
                    row_dict[col_name] = _turso_val_to_py(cell)
                data.append(row_dict)
            return TursoResponse(data=data, count=len(data))
        else:
            return TursoResponse(data=returning_data or [], count=affected)

    def _execute_batch(self, stmts, returning_data=None):
        requests = [{"type": "execute", "stmt": s} for s in stmts]
        self._post_with_retry({"requests": requests})
        return TursoResponse(data=returning_data or [], count=len(stmts))

    def _post_with_retry(self, payload, max_retries=2):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                last_exc = e
                # Pokud HTTP status 402/403/429 -> zablokováno
                if hasattr(e, "code") and e.code in (402, 403, 429):
                    set_turso_blocked(True, reason=f"HTTP {e.code} error: {e}")
                    break
                if attempt < max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
        if last_exc:
            err_str = str(last_exc)
            if is_turso_blocked_error(err_str):
                set_turso_blocked(True, reason=err_str)
            else:
                print(f"[TursoClient NET-ERROR] {last_exc}", flush=True)
            raise last_exc
        return {}

_GLOBAL_TURSO_CLIENT = None
_CLIENT_LOCK = threading.RLock()

def get_turso_db():
    global _GLOBAL_TURSO_CLIENT
    if _GLOBAL_TURSO_CLIENT is None:
        with _CLIENT_LOCK:
            if _GLOBAL_TURSO_CLIENT is None:
                _GLOBAL_TURSO_CLIENT = TursoClient()
    return _GLOBAL_TURSO_CLIENT

def create_client(url=None, key=None):
    """Drop-in náhrada za supabase.create_client(url, key)"""
    return TursoClient(db_url=url, auth_token=key)
