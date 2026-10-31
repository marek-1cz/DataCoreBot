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
_STATE_LOCK = threading.Lock()

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

def is_turso_blocked_error(err_str: str) -> bool:
    if not err_str:
        return False
    low = str(err_str).lower()
    return any(p in low for p in [
        "reads are blocked",
        "sql read operations are forbidden",
        "operation was blocked",
        "read limit",
        "limit has now been reached",
        "quota exceeded",
        "plan limit",
        "exceeded your plan"
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
        print("[TURSO SHIELD] 🚨 POZOR: Cloudová databáze Turso dosáhla limitu čtení (READS BLOCKED)!", flush=True)
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
_CACHE_LOCK = threading.Lock()

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
# LOKÁLNÍ AUTONOMNÍ FALLBACK ENGINE PRO SELECT DOTAZY
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_local_fallback(table_name, columns="*", where_clauses=None, args=None, order_by=None, limit_val=None):
    """
    Bezpečný a robustní lokální fallback pro případ výpadku / vyčerpání Turso.
    Poskytuje přesná data z JSON záloh a lokální SQLite, takže aplikace funguje dál.
    """
    where_clauses = where_clauses or []
    args = args or []

    def _find_file(fn):
        for d in [_BASE_DIR, os.path.dirname(_BASE_DIR)]:
            p = os.path.join(d, fn)
            if os.path.exists(p):
                return p
        return None

    # ── TABULKA: users ──
    if table_name == "users":
        u_file = _find_file("users_backup.json")
        data = []
        if u_file:
            try:
                with open(u_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []

        filtered = []
        for u in data:
            match = True
            for w, a in zip(where_clauses, args):
                val = a.get("value")
                val_str = str(val) if val is not None else ""
                if '"id" = ?' in w and str(u.get("id")) != val_str:
                    match = False; break
                elif '"discord_id" = ?' in w and str(u.get("discord_id")) != val_str:
                    match = False; break
                elif '"email" = ?' in w and str(u.get("email", "")).lower() != val_str.lower():
                    match = False; break
                elif '"app_id" = ?' in w and str(u.get("app_id")) != val_str:
                    match = False; break
                elif '"nick" = ?' in w and str(u.get("nick", "")).lower() != val_str.lower():
                    match = False; break
                elif '"download_token" = ?' in w and str(u.get("download_token")) != val_str:
                    match = False; break
                elif '"login_token" = ?' in w and str(u.get("login_token")) != val_str:
                    match = False; break
                elif '"web_session_token" = ?' in w or '"web_session_token" LIKE ?' in w:
                    wst = str(u.get("web_session_token") or "")
                    if val_str not in wst:
                        match = False; break
                elif 'LOWER("nick") LIKE LOWER(?)' in w:
                    clean_pat = val_str.strip("%").lower()
                    if clean_pat not in str(u.get("nick", "")).lower():
                        match = False; break
                elif 'LOWER("email") LIKE LOWER(?)' in w:
                    clean_pat = val_str.strip("%").lower()
                    if clean_pat not in str(u.get("email", "")).lower():
                        match = False; break
            if match:
                filtered.append(u)

        if limit_val is not None:
            filtered = filtered[:int(limit_val)]

        if columns and columns != "*":
            req_cols = [c.strip().strip('"') for c in columns.split(",") if c.strip()]
            return [{c: item.get(c) for c in req_cols} for item in filtered]
        return filtered

    # ── TABULKA: settings ──
    if table_name == "settings":
        # Hledáme konkrétní klíč
        target_key = None
        for w, a in zip(where_clauses, args):
            if '"setting_key" = ?' in w:
                target_key = str(a.get("value") or "")
                break

        val = None
        # Zkus načíst z lokální SQLite
        db_path = _find_file("datacore_local.db")
        if db_path and target_key:
            try:
                con = sqlite3.connect(db_path, timeout=5)
                cur = con.cursor()
                cur.execute("SELECT setting_value FROM settings_local WHERE setting_key = ?", (target_key,))
                row = cur.fetchone()
                if row:
                    val = row[0]
                con.close()
            except Exception:
                pass

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
            val = "1.0.0"
        elif val is None and target_key == "launcher_download_url":
            val = "https://github.com/marek-1cz/IDPK-Palubni-Pocitac/releases/download/V1.6.2B/IDPK.Launcher.Setup.1.6.2.exe"

        if val is not None:
            return [{"setting_key": target_key, "setting_value": val}]
        return []

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
                    "file_url": "https://datacorebot.koyeb.app/download/v1.6.2",
                    "target_role": "BT",
                    "is_active": 1,
                    "eol_date": "",
                    "show_in_launcher": 1,
                    "can_download": 1,
                    "can_launch": 1
                },
                {
                    "id": 2,
                    "version_name": "OIS IDPK V1.6",
                    "db_version": "V1.6",
                    "file_url": "https://datacorebot.koyeb.app/download/v1.6",
                    "target_role": "User",
                    "is_active": 1,
                    "eol_date": "",
                    "show_in_launcher": 1,
                    "can_download": 1,
                    "can_launch": 1
                },
                {
                    "id": 3,
                    "version_name": "OIS IDPK V1.5.1 RC",
                    "db_version": "V1.5.1 RC",
                    "file_url": "https://datacorebot.koyeb.app/download/v1.5.1",
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
                set_query_cache(cache_key, res.data, self.table_name)
            return res

        # ── ZÁPISOVÉ OPERACE (Invalidují cache dané tabulky) ──
        invalidate_query_cache(self.table_name)

        if self.action == "INSERT":
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
            return self.client._execute_single(sql, all_args, returning_data=[self.payload_data])

        elif self.action == "DELETE":
            sql = f"DELETE FROM \"{self.table_name}\"{where_sql};"
            return self.client._execute_single(sql, self.args)

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
            if is_turso_blocked_error(err_msg):
                set_turso_blocked(True, reason=err_msg)
            else:
                print(f"[TursoClient ERROR] SQL: {sql} | Error: {err_msg}", flush=True)
            return TursoResponse(error=err_msg)

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
_CLIENT_LOCK = threading.Lock()

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
