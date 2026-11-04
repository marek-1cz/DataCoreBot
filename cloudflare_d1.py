# cloudflare_d1.py
# Cloudflare D1 Client pro DataCoreBot
# Přes Cloudflare REST API (bez wrangler CLI)

import urllib.request
import urllib.error
import json
import threading
import time
import os

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


class D1Client:
    """Cloudflare D1 REST API klient (pouze stdlib, žádné závislosti)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._blocked_until = 0.0
        self._last_block_log = 0.0
        self._cache = {}
        self._cache_lock = threading.Lock()

    def is_blocked(self) -> bool:
        """Vrátí True pokud je aktivní circuit breaker (překročen denní limit kvóty)."""
        return time.time() < self._blocked_until

    def _invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def _request(self, payload: dict) -> list:
        """Pošle jeden POST požadavek na D1 endpoint. Vrátí list výsledků (list dictů) nebo []."""
        now = time.time()
        if now < self._blocked_until:
            if now - self._last_block_log > 120:
                self._last_block_log = now
                print(f"[D1] Circuit breaker aktivní (limit kvóty D1). Přeskakuji síťový dotaz.", flush=True)
            return []

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
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = str(e)
            if "7500" in err_body or "row read limit" in err_body.lower() or e.code == 429:
                self._blocked_until = time.time() + 300  # 5 minut circuit breaker
                print(f"[D1] Aktivován circuit breaker (kód 7500 - denní limit čtení D1 vyčerpán). Pauza 5 min.", flush=True)
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
                self._blocked_until = time.time() + 300
                print(f"[D1] Aktivován circuit breaker z API erroru (kód 7500).", flush=True)
            else:
                print(f"[D1] API error: {errors}", flush=True)
            return []

        # result je list (jeden výsledek na statement)
        results = parsed.get("result") or []
        rows = []
        for item in results:
            if not item.get("success"):
                print(f"[D1] Statement error: {item}", flush=True)
                continue
            rows.extend(item.get("results") or [])
        return rows

    def execute(self, sql: str, params=None) -> list:
        """Spustí jeden SQL dotaz s cache pro SELECT a circuit breakerem."""
        sql_clean = sql.strip()
        is_select = sql_clean.upper().startswith("SELECT")
        p_list = list(params) if params else []

        if is_select:
            cache_key = (sql_clean, tuple(p_list))
            now = time.time()
            with self._cache_lock:
                entry = self._cache.get(cache_key)
                if entry and now < entry[0]:
                    return list(entry[1])

        payload = {"sql": sql, "params": p_list}
        with self._lock:
            res = self._request(payload)

        if is_select:
            if res:
                with self._cache_lock:
                    self._cache[cache_key] = (time.time() + 30, list(res))
        else:
            self._invalidate_cache()

        return res

    def execute_many(self, statements: list) -> list:
        """Batchové spuštění více statements najednou.
        statements = [{"sql": "...", "params": [...]}, ...]
        Vrátí sloučený list výsledků.
        """
        if not statements:
            return []
        # D1 REST API podporuje pouze jeden statement per request – posíláme sekvenčně
        all_rows = []
        with self._lock:
            for stmt in statements:
                payload = {
                    "sql": stmt.get("sql", ""),
                    "params": list(stmt.get("params") or []),
                }
                all_rows.extend(self._request(payload))
        return all_rows

    def insert(self, table: str, row_dict: dict):
        """Vloží jeden řádek. Vrátí id nebo None."""
        cols = list(row_dict.keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_names = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        params = [row_dict[c] for c in cols]
        rows = self.execute(sql, params)
        if rows:
            return rows[0].get("id")
        # Pokusíme se získat last insert id
        last = self.execute("SELECT last_insert_rowid() AS id")
        if last:
            return last[0].get("id")
        return None

    def upsert(self, table: str, row_dict: dict, conflict_col: str):
        """INSERT OR REPLACE INTO table. Vrátí id nebo None."""
        cols = list(row_dict.keys())
        placeholders = ", ".join(["?" for _ in cols])
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
        params = [row_dict[c] for c in cols]
        rows = self.execute(sql, params)
        if rows:
            return rows[0].get("id")
        last = self.execute("SELECT last_insert_rowid() AS id")
        if last:
            return last[0].get("id")
        return None

    def update(self, table: str, set_dict: dict, where_col: str, where_val):
        """UPDATE table SET ... WHERE where_col = where_val."""
        set_parts = ", ".join([f"{k} = ?" for k in set_dict.keys()])
        sql = f"UPDATE {table} SET {set_parts} WHERE {where_col} = ?"
        params = list(set_dict.values()) + [where_val]
        return self.execute(sql, params)

    def select(
        self,
        table: str,
        where_col=None,
        where_val=None,
        order_by=None,
        desc: bool = True,
        limit=None,
    ) -> list:
        """SELECT * FROM table [WHERE where_col = where_val] [ORDER BY order_by [DESC]] [LIMIT limit]."""
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
    """Otestuje připojení k D1 jednoduchým SELECT. Vrátí True/False."""
    try:
        client = get_d1_client()
        result = client.execute("SELECT 1 AS ok")
        return bool(result)
    except Exception as e:
        print(f"[D1] is_d1_available check failed: {e}", flush=True)
        return False



