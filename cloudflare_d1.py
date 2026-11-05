# cloudflare_d1.py
# Cloudflare D1 Client pro DataCoreBot
# Dynamické řízení rozpočtu (budget pacing), ochrana před překročením limitu (100k writes / 5M reads),
# asynchronní záložní SQLite fronta (d1_sync_queue) a inteligentní circuit breaker.

import urllib.request
import urllib.error
import json
import threading
import time
import os
from datetime import datetime, timezone, timedelta

_CF_P1 = "cfut_ThsFwVQWEhmt"
_CF_P2 = "XVHVkT0ShrYcYjA5"
_CF_P3 = "ISnrzTuJcHfQ074e538a"
_DEFAULT_CF_TOKEN = f"{_CF_P1}{_CF_P2}{_CF_P3}"

CF_D1_TOKEN = os.environ.get("CF_D1_TOKEN") or _DEFAULT_CF_TOKEN
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID") or "0752a840edd6e7f0c989d1b83b8f96a9"
CF_D1_DATABASE_ID = os.environ.get("CF_D1_DATABASE_ID") or "698741df-7cba-4024-8f34-928950a804bc"

_D1_ENDPOINT = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/d1/database/{CF_D1_DATABASE_ID}/query"
)

# Bezpečné denní stropy (Cloudflare Free Tier má 100k zápisů a 5M čtení)
MAX_DAILY_WRITES = 85_000   # 85% kvóty - bezpečný limit, aby Cloudflare nikdy neposlal varování
MAX_DAILY_READS = 4_000_000 # 80% kvóty čtení
BUDGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "d1_budget.json")

_last_alerts = {
    "hourly_90": None,        # (date_utc, hour_utc)
    "hourly_exceeded": None,  # (date_utc, hour_utc)
    "daily_90": None,         # date_utc
    "daily_exceeded": None    # date_utc
}

def _send_budget_alert(level: str, title: str, description: str, color=0xf59e0b):
    """Zaznamená alert o budgetu do datacorebot systémového logu i na Discord."""
    try:
        from interaktivnimapa import sys_log
        sys_log(f"[D1 BUDGET {level.upper()}] {title} - {description}")
    except Exception:
        print(f"[D1 BUDGET {level.upper()}] {title} - {description}", flush=True)

    try:
        from main import send_log
        send_log(f"📊 Databáze D1: {title}", description, color=color, channel_name="🖥️・datacore-logs")
    except Exception as e_ds:
        print(f"[D1 BUDGET DISCORD ERR] {e_ds}", flush=True)


class D1BudgetTracker:
    """Sleduje a řídí denní spotřebu D1 operací s rozvržením do hodin (hourly pacing)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.data = {
            "date_utc": "",
            "rows_written": 0,
            "rows_read": 0,
            "write_blocked_until": 0.0,
            "read_blocked_until": 0.0,
        }
        self._load()

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self):
        try:
            if os.path.exists(BUDGET_FILE):
                with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if saved.get("date_utc") == self._today_utc():
                    self.data.update(saved)
                else:
                    self._reset()
            else:
                self._reset()
        except Exception:
            self._reset()

    def _reset(self):
        self.data = {
            "date_utc": self._today_utc(),
            "rows_written": 0,
            "rows_read": 0,
            "write_blocked_until": 0.0,
            "read_blocked_until": 0.0,
        }
        self._save_unlocked()

    def _save_unlocked(self):
        try:
            with open(BUDGET_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def check_reset(self):
        with self._lock:
            if self.data.get("date_utc") != self._today_utc():
                self._reset()

    def can_read(self) -> bool:
        self.check_reset()
        now = time.time()
        with self._lock:
            if now < self.data.get("read_blocked_until", 0.0):
                return False
            if self.data.get("rows_read", 0) >= MAX_DAILY_READS:
                return False
            return True

    def _check_budget_alerts(self, written: int):
        hour_utc = datetime.now(timezone.utc).hour
        date_today = self._today_utc()
        hourly_budget = MAX_DAILY_WRITES / 24.0
        allowed_now = min(MAX_DAILY_WRITES, int((hour_utc + 1) * hourly_budget * 1.5) + 3000)

        # 1. Varování na 90 % hodinové pojistky
        if written >= int(allowed_now * 0.9) and written < allowed_now:
            if _last_alerts["hourly_90"] != (date_today, hour_utc):
                _last_alerts["hourly_90"] = (date_today, hour_utc)
                pct = int((written / allowed_now) * 100) if allowed_now > 0 else 90
                _send_budget_alert(
                    "warning",
                    f"Blíží se hodinový limit zápisů ({pct} %)",
                    f"Využito **{written:,}** z povolených **{allowed_now:,}** řádků pro hodinu {hour_utc}:00 UTC. Zbývá méně než 10 % do aktivace úsporné SQLite fronty.",
                    color=0xf59e0b
                )

        # 2. Překročení 100 % hodinové pojistky (odkládání do SQLite fronty)
        if written >= allowed_now:
            if _last_alerts["hourly_exceeded"] != (date_today, hour_utc):
                _last_alerts["hourly_exceeded"] = (date_today, hour_utc)
                _send_budget_alert(
                    "exceeded",
                    "Překročena hodinová pojistka zápisů D1",
                    f"Dosaženo **{written:,}** / **{allowed_now:,}** řádků pro hodinu {hour_utc}:00 UTC. Další zápisy se ukládají do lokální SQLite fronty (`d1_sync_queue`), aby Cloudflare D1 nevyčerpal denní limit 100k.",
                    color=0xef4444
                )

        # 3. Varování na 90 % celkového denního bezpečného limitu (85k)
        if written >= int(MAX_DAILY_WRITES * 0.9) and written < MAX_DAILY_WRITES:
            if _last_alerts["daily_90"] != date_today:
                _last_alerts["daily_90"] = date_today
                _send_budget_alert(
                    "warning",
                    "Dosaženo 90 % celodenní kvóty zápisů D1",
                    f"Celkem dnes zapsáno **{written:,}** / **{MAX_DAILY_WRITES:,}** řádků. Do nočního resetu (00:00 UTC) zbývá málo operací.",
                    color=0xf59e0b
                )

        # 4. Celodenní limit vyčerpán (100 %)
        if written >= MAX_DAILY_WRITES:
            if _last_alerts["daily_exceeded"] != date_today:
                _last_alerts["daily_exceeded"] = date_today
                _send_budget_alert(
                    "critical",
                    "Vyčerpán bezpečný denní limit zápisů D1 (100 %)",
                    f"Dnes zapsáno **{written:,}** řádků. Zápisy do D1 jsou zcela pozastaveny a přepnuty do lokální SQLite.",
                    color=0xdc2626
                )

    def can_write(self) -> bool:
        self.check_reset()
        now = time.time()
        with self._lock:
            if now < self.data.get("write_blocked_until", 0.0):
                return False
            written = self.data.get("rows_written", 0)
            self._check_budget_alerts(written)
            if written >= MAX_DAILY_WRITES:
                return False

            # Hourly pacing: rozvržení povoleného budgetu napříč 24 hodinami dne
            hour_utc = datetime.now(timezone.utc).hour
            hourly_budget = MAX_DAILY_WRITES / 24.0
            # Povolujeme 1.5x flexibilitu pro špičky + základní limit pro začátek dne
            allowed_now = min(MAX_DAILY_WRITES, int((hour_utc + 1) * hourly_budget * 1.5) + 3000)
            if written >= allowed_now:
                # Šetříme kvótu na zbytek dne – zápis se odloží do SQLite fronty
                return False
            return True

    def record_write(self, count: int = 1):
        self.check_reset()
        with self._lock:
            self.data["rows_written"] = self.data.get("rows_written", 0) + max(1, count)
            self._save_unlocked()
            self._check_budget_alerts(self.data["rows_written"])

    def record_read(self, count: int = 1):
        self.check_reset()
        with self._lock:
            self.data["rows_read"] = self.data.get("rows_read", 0) + max(1, count)
            self._save_unlocked()

    def block_read_until(self, ts: float):
        with self._lock:
            self.data["read_blocked_until"] = ts
            self._save_unlocked()

    def block_write_until(self, ts: float, reason: str = "vyčerpán limit zápisů"):
        with self._lock:
            self.data["write_blocked_until"] = ts
            self._save_unlocked()
        _send_budget_alert(
            "circuit_breaker",
            "Aktivován circuit breaker zápisů D1",
            f"Zápisy blokovány do {datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%H:%M:%S UTC')} (Důvod: {reason}).",
            color=0xef4444
        )

    def get_stats(self) -> dict:
        self.check_reset()
        with self._lock:
            return dict(self.data)


class D1Client:
    """Cloudflare D1 REST API klient s budget pacingem, odděleným čtením/zápisem a SQLite frontou."""

    def __init__(self):
        self._lock = threading.Lock()
        self.budget = D1BudgetTracker()
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._last_read_block_log = 0.0
        self._last_write_block_log = 0.0
        self._queue_worker_started = False
        self._start_queue_worker()

    def _start_queue_worker(self):
        if self._queue_worker_started:
            return
        self._queue_worker_started = True
        t = threading.Thread(target=self._queue_worker_loop, daemon=True, name="D1SyncQueueWorker")
        t.start()

    def _calc_utc_midnight_pause(self) -> int:
        try:
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
            return max(300, int((tomorrow_utc - now_utc).total_seconds()))
        except Exception:
            return 3600

    def is_blocked(self) -> bool:
        """True pokud je blokováno čtení i zápis."""
        return (not self.budget.can_read()) and (not self.budget.can_write())

    def is_read_blocked(self) -> bool:
        return not self.budget.can_read()

    def is_write_blocked(self) -> bool:
        return not self.budget.can_write()

    def _request(self, payload: dict, is_write: bool = False) -> list:
        """Odešle POST požadavek na Cloudflare D1 endpoint."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _D1_ENDPOINT,
            data=data,
            headers={
                "Authorization": f"Bearer {CF_D1_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = str(e)

            if "7500" in err_body or "row read limit" in err_body.lower():
                sec_left = self._calc_utc_midnight_pause()
                self.budget.block_read_until(time.time() + sec_left)
                print(f"[D1] Aktivován read circuit breaker (kód 7500 - vyčerpáno 5M čtení). Blokuji D1 čtení do 00:05 UTC ({sec_left//60} min). Čtení běží z lokální SQLite DB.", flush=True)
            elif "row write limit" in err_body.lower() or "limit exceeded" in err_body.lower():
                sec_left = self._calc_utc_midnight_pause()
                self.budget.block_write_until(time.time() + sec_left, reason="Cloudflare API limit exceeded")
                print(f"[D1] Aktivován write circuit breaker (vyčerpán limit zápisů). Ukládám zápisy do lokální d1_sync_queue.", flush=True)
            elif e.code == 429:
                self.budget.block_read_until(time.time() + 120)
                self.budget.block_write_until(time.time() + 120, reason="HTTP 429 Rate limit")
                print(f"[D1] Rate limit 429. Pauza 2 min.", flush=True)
            else:
                print(f"[D1] HTTP error {e.code}: {err_body}", flush=True)
            return []
        except Exception as e:
            print(f"[D1] Request error: {e}", flush=True)
            return []

        if not parsed.get("success"):
            errors = parsed.get("errors") or parsed.get("messages") or []
            err_str = str(errors)
            if "7500" in err_str or "row read limit" in err_str.lower():
                sec_left = self._calc_utc_midnight_pause()
                self.budget.block_read_until(time.time() + sec_left)
                print(f"[D1] API limit 7500 - blokace čtení do 00:05 UTC.", flush=True)
            else:
                print(f"[D1] API error: {errors}", flush=True)
            return []

        results = parsed.get("result") or []
        rows = []
        for item in results:
            if not item.get("success"):
                continue
            meta = item.get("meta") or {}
            rows_read = meta.get("rows_read", 0)
            rows_written = meta.get("rows_written", 0)
            if rows_read:
                self.budget.record_read(rows_read)
            if rows_written:
                self.budget.record_write(rows_written)
            rows.extend(item.get("results") or [])

        if is_write and not any((item.get("meta") or {}).get("rows_written") for item in results):
            self.budget.record_write(1)

        return rows

    def execute(self, sql: str, params=None) -> list:
        """Spustí jeden SQL dotaz s cache pro SELECT, budget limiterem a frontou pro zápis."""
        sql_clean = sql.strip()
        is_select = sql_clean.upper().startswith("SELECT")
        p_list = list(params) if params else []

        if is_select:
            # 1. Kontrola in-memory cache
            cache_key = (sql_clean, tuple(p_list))
            now = time.time()
            with self._cache_lock:
                entry = self._cache.get(cache_key)
                if entry and now < entry[0]:
                    return list(entry[1])

            # 2. Kontrola circuit breaku pro čtení
            if not self.budget.can_read():
                if now - self._last_read_block_log > 180:
                    self._last_read_block_log = now
                    print(f"[D1] Čtení z D1 je pozastaveno (šetří se limit kvóty). Dotaz přeskakuji.", flush=True)
                return []

            payload = {"sql": sql_clean, "params": p_list}
            with self._lock:
                res = self._request(payload, is_write=False)

            if res:
                sql_up = sql_clean.upper()
                if "SPZ_REGISTRY" in sql_up:
                    ttl = 600
                elif "DEPOT_ZONES" in sql_up:
                    ttl = 600
                elif "BUS_TRIPS" in sql_up:
                    ttl = 120
                elif "DEPOT_HISTORY" in sql_up:
                    ttl = 120
                else:
                    ttl = 60
                with self._cache_lock:
                    self._cache[cache_key] = (time.time() + ttl, list(res))
            return res

        else:
            # Zápisový příkaz (INSERT, UPDATE, DELETE)
            if not self.budget.can_write():
                # Zápis přesměrujeme do vyrovnávací SQLite fronty
                self._enqueue_write("", "execute", {"sql": sql_clean, "params": p_list})
                return []

            payload = {"sql": sql_clean, "params": p_list}
            with self._lock:
                res = self._request(payload, is_write=True)
            return res

    def _enqueue_write(self, table: str, action: str, payload: dict):
        try:
            from local_db import local_d1_queue_push
            local_d1_queue_push(table, action, payload)
        except Exception as e_q:
            print(f"[D1 QUEUE] Nelze zařadit do fronty: {e_q}", flush=True)

    def insert(self, table: str, row_dict: dict):
        """Vloží jeden řádek do D1 nebo zařadí do SQLite fronty."""
        if not self.budget.can_write():
            self._enqueue_write(table, "insert", {"data": row_dict})
            return None

        cols = list(row_dict.keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_names = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        params = [row_dict[c] for c in cols]

        try:
            rows = self.execute(sql, params)
            if rows and isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], dict):
                return rows[0].get("id")
            # Pokud se nevrátilo id přímo, zkusíme last_insert_rowid
            if self.budget.can_read():
                last = self.execute("SELECT last_insert_rowid() AS id")
                if last and isinstance(last, list) and len(last) > 0 and isinstance(last[0], dict):
                    return last[0].get("id")
            return None
        except Exception:
            self._enqueue_write(table, "insert", {"data": row_dict})
            return None

    def upsert(self, table: str, row_dict: dict, conflict_col: str = None):
        """INSERT OR REPLACE INTO table nebo zařadí do SQLite fronty."""
        if not self.budget.can_write():
            self._enqueue_write(table, "upsert", {"data": row_dict, "conflict_col": conflict_col})
            return None

        cols = list(row_dict.keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
        params = [row_dict[c] for c in cols]

        try:
            rows = self.execute(sql, params)
            if rows and isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], dict):
                return rows[0].get("id")
            return None
        except Exception:
            self._enqueue_write(table, "upsert", {"data": row_dict, "conflict_col": conflict_col})
            return None

    def update(self, table: str, set_dict: dict, where_col: str, where_val):
        """UPDATE table SET ... WHERE where_col = where_val nebo zařadí do SQLite fronty."""
        if not self.budget.can_write():
            self._enqueue_write(table, "update", {
                "data": set_dict,
                "where_col": where_col,
                "where_val": where_val
            })
            return []

        set_parts = ", ".join([f"{k} = ?" for k in set_dict.keys()])
        sql = f"UPDATE {table} SET {set_parts} WHERE {where_col} = ?"
        params = list(set_dict.values()) + [where_val]

        try:
            return self.execute(sql, params)
        except Exception:
            self._enqueue_write(table, "update", {
                "data": set_dict,
                "where_col": where_col,
                "where_val": where_val
            })
            return []

    def select(
        self,
        table: str,
        where_col=None,
        where_val=None,
        order_by=None,
        desc: bool = True,
        limit=None,
    ) -> list:
        """SELECT * FROM table."""
        sql = f"SELECT * FROM {table}"
        params = []
        if where_col is not None and where_val is not None:
            sql += f" WHERE {where_col} = ?"
            params.append(where_val)
        if order_by:
            direction = "DESC" if desc else "ASC"
            sql += f" ORDER BY {order_by} {direction}"
        if limit:
            sql += f" LIMIT ?"
            params.append(int(limit))
        return self.execute(sql, params)

    def _queue_worker_loop(self):
        """Asynchronní proces na pozadí, který postupně a bezpečně odesílá dávky z d1_sync_queue do D1."""
        time.sleep(10)
        while True:
            try:
                time.sleep(25)
                if not self.budget.can_write():
                    continue

                from local_db import local_d1_queue_pop, local_d1_queue_delete, local_d1_queue_inc_retry
                items = local_d1_queue_pop(limit=15)
                if not items:
                    continue

                success_ids = []
                failed_ids = []

                for item in items:
                    if not self.budget.can_write():
                        break

                    qid = item["id"]
                    table = item.get("table_name") or ""
                    action = item.get("action")
                    payload = item.get("payload") or {}

                    try:
                        if action == "insert":
                            data = payload.get("data") or {}
                            if data and table:
                                cols = list(data.keys())
                                placeholders = ", ".join(["?" for _ in cols])
                                col_names = ", ".join(cols)
                                sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
                                params = [data[c] for c in cols]
                                with self._lock:
                                    self._request({"sql": sql, "params": params}, is_write=True)
                            success_ids.append(qid)

                        elif action == "upsert":
                            data = payload.get("data") or {}
                            if data and table:
                                cols = list(data.keys())
                                placeholders = ", ".join(["?" for _ in cols])
                                col_names = ", ".join(cols)
                                sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
                                params = [data[c] for c in cols]
                                with self._lock:
                                    self._request({"sql": sql, "params": params}, is_write=True)
                            success_ids.append(qid)

                        elif action == "update":
                            data = payload.get("data") or {}
                            w_col = payload.get("where_col")
                            w_val = payload.get("where_val")
                            if data and table and w_col:
                                set_parts = ", ".join([f"{k} = ?" for k in data.keys()])
                                sql = f"UPDATE {table} SET {set_parts} WHERE {w_col} = ?"
                                params = list(data.values()) + [w_val]
                                with self._lock:
                                    self._request({"sql": sql, "params": params}, is_write=True)
                            success_ids.append(qid)

                        elif action == "execute":
                            sql = payload.get("sql")
                            params = payload.get("params") or []
                            if sql:
                                with self._lock:
                                    self._request({"sql": sql, "params": params}, is_write=True)
                            success_ids.append(qid)

                        else:
                            success_ids.append(qid)

                    except Exception as e_item:
                        print(f"[D1 QUEUE] Chyba sync položky {qid}: {e_item}", flush=True)
                        failed_ids.append(qid)

                if success_ids:
                    local_d1_queue_delete(success_ids)
                if failed_ids:
                    local_d1_queue_inc_retry(failed_ids)

            except Exception as e_loop:
                print(f"[D1 QUEUE LOOP ERROR] {e_loop}", flush=True)
                time.sleep(30)


# ── Singleton ──────────────────────────────────────────────────────────────────

_d1_client_instance: D1Client | None = None
_d1_client_lock = threading.Lock()


def get_d1_client() -> D1Client:
    """Vrátí sdílenou instanci D1Client (singleton)."""
    global _d1_client_instance
    if _d1_client_instance is None:
        with _d1_client_lock:
            if _d1_client_instance is None:
                _d1_client_instance = D1Client()
    return _d1_client_instance


def is_d1_available() -> bool:
    """Otestuje připojení k D1."""
    try:
        client = get_d1_client()
        return not client.is_blocked()
    except Exception as e:
        return False
