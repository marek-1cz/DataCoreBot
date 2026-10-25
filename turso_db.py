"""
Turso Database Client & Supabase-compatible Adapter for DataCoreBot
Poskytuje identické rozhraní jako supabase-py (.table(...).select().eq().execute()),
ale běží přímo nad Turso (LibSQL / Cloud SQLite) bez limitů přenosu dat a s 1 miliardou čtení měsíčně.
"""

import os
import json
import urllib.request
import urllib.error
import time
import threading

_DEFAULT_TURSO_URL = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("TURSO_URL") or "libsql://datacorebot-marek-1cz.aws-eu-north-1.turso.io"
_T1 = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTI5MTUwMDIsImlkIjoiMDFhMTcyMGUtZDgwMS03YjM5LTk3Y2QtMjY3OGU5NTVhN2M4Iiwia2lkIjoiSUVKRndGUkI5TUczOFYtdUlvMk9TVnI4MEZXeXFlSEZQZGwtVi1Gdk1CUSIsInJpZCI6ImVjYTE0YWJiLTU1YjEtNDE2Ny04NTFlLWExNzNmMTU0NzNmZSJ9"
_T2 = "3eEe_wV8-SHd1qLmP4pZdBY2yHtNG0iXncOmFAbVZjUo3k7BC07MT0ZwW9iT6CuBTBZLUXtG-apUN4Iz8zPKBw"
_DEFAULT_TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN") or f"{_T1}.{_T2}"

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
        # PostgREST syntax parser: "col1.eq.val1,col2.like.val2"
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
            return self.client._execute_single(sql, self.args)

        elif self.action == "INSERT":
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
                sql = f"INSERT INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders});"
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
                sql = f"INSERT OR REPLACE INTO \"{self.table_name}\" ({col_str}) VALUES ({placeholders});"
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

    def table(self, table_name):
        return TursoQueryBuilder(self, table_name)

    def execute_raw(self, sql, args=None):
        """Umožňuje přímé spuštění libovolného SQL dotazu"""
        return self._execute_single(sql, [_py_to_turso_arg(a) for a in (args or [])])

    def _execute_single(self, sql, args=None, returning_data=None):
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
            print(f"[TursoClient ERROR] SQL: {sql} | Error: {err_msg}", flush=True)
            return TursoResponse(error=err_msg)

        resp = r.get("response", {})
        result = resp.get("result", {})
        cols = [c.get("name") for c in result.get("cols", [])]
        rows = result.get("rows", [])
        affected = result.get("affected_row_count", 0)

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
                with urllib.request.urlopen(req, timeout=12) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                last_exc = e
                if attempt < max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
        if last_exc:
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
