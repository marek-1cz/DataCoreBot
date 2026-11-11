# -*- coding: utf-8 -*-
"""
jr_api.py - GTFS API pro jizdni-rad.html
Poskytuje endpointy:
  - /api/jr/featured?count=6
  - /api/jr/search?q=<query>
  - /api/jr/line?id=<lineId>
  - /api/jr/trips?line=<id>&dir=<dirIndex>&day=<weekday|saturday|sunday>
"""
import os
import sqlite3
import unicodedata
import threading
import json
from datetime import datetime
from collections import defaultdict

_CACHE_FEATURED = None
_CACHE_ROUTES = None
_CACHE_STOPS = None
_LINE_CACHE = {}
_TRIPS_CACHE = {}
_LINE_MAPPING = None
_REV_LINE_MAPPING = None

def _get_line_mapping():
    global _LINE_MAPPING, _REV_LINE_MAPPING
    if _LINE_MAPPING is None:
        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            p = os.path.join(curr_dir, "gtfs_line_mapping.json")
            if not os.path.exists(p):
                p = os.path.join(os.path.dirname(curr_dir), "gtfs_line_mapping.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    _LINE_MAPPING = json.load(f)
                    _REV_LINE_MAPPING = {v: k for k, v in _LINE_MAPPING.items()}
        except Exception as e:
            print(f"[JR API MAPPING ERROR] {e}", flush=True)
            _LINE_MAPPING = {}
            _REV_LINE_MAPPING = {}
    return _LINE_MAPPING or {}, _REV_LINE_MAPPING or {}

def ensure_db_indexes(conn=None):
    """Vytvoří chybějící indexy v GTFS SQLite databázi pro zrychlení dotazů z minut na milisekundy."""
    close_at_end = False
    if conn is None:
        db_path = _get_db_path()
        if not os.path.exists(db_path):
            return
        conn = sqlite3.connect(db_path)
        close_at_end = True
    try:
        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trips_route_id ON trips(route_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trips_service_id ON trips(service_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trips_trip_id ON trips(trip_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stops_stop_id ON stops(stop_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stops_name ON stops(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_route_id ON routes(route_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_short ON routes(route_short_name)")
        conn.commit()
    except Exception as e:
        print(f"[JR DB INDEX ERROR] {e}", flush=True)
    finally:
        if close_at_end:
            conn.close()

def align_trip_times(trip_stops, target_stops):
    """
    Monotonically aligns an ordered trip's served stops to the master route sequence.
    trip_stops: list of (stop_name, time_str) in stop_sequence order
    target_stops: list of stop_name in the route master sequence
    Returns: list of time_str or None of length len(target_stops)
    """
    n = len(target_stops)
    m = len(trip_stops)
    if not m or not n:
        return [None] * n

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    parent = [[None] * (n + 1) for _ in range(m + 1)]

    for k in range(1, m + 1):
        ts_name = trip_stops[k - 1][0]
        row_dp_prev = dp[k - 1]
        row_dp_curr = dp[k]
        row_parent = parent[k]
        for i in range(1, n + 1):
            best = row_dp_curr[i - 1]
            p = (k, i - 1, False)

            if row_dp_prev[i] > best:
                best = row_dp_prev[i]
                p = (k - 1, i, False)

            if ts_name == target_stops[i - 1]:
                match_val = row_dp_prev[i - 1] + 1
                if match_val > best:
                    best = match_val
                    p = (k - 1, i - 1, True)

            row_dp_curr[i] = best
            row_parent[i] = p

    curr_k, curr_i = m, n
    matched = {}
    while curr_k > 0 and curr_i > 0:
        pk, pi, is_match = parent[curr_k][curr_i]
        if is_match:
            matched[curr_i - 1] = trip_stops[curr_k - 1][1]
        curr_k, curr_i = pk, pi

    return [matched.get(i, None) for i in range(n)]

def _get_db_path():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ["gtfs_stops_idpk.db", "gtfs_idpk.db", "gtfs.db"]:
        p = os.path.join(curr_dir, name)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p
        p2 = os.path.join(os.path.dirname(curr_dir), name)
        if os.path.exists(p2) and os.path.getsize(p2) > 1000:
            return p2
    return os.path.join(curr_dir, "gtfs_stops_idpk.db")

def _norm(s):
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

def _short_name(sn):
    sn = str(sn).strip()
    _, rev_map = _get_line_mapping()
    if sn in rev_map:
        return rev_map[sn]
    if len(sn) == 6 and sn.isdigit():
        return str(int(sn[3:]))
    return sn

def _get_color(short_name):
    sn = str(short_name).strip()
    if sn.isdigit():
        num = int(sn)
        if 1 <= num <= 19:
            return "#e11d48"
        elif 20 <= num <= 99:
            return "#2f6bff"
        else:
            return "#7b4dff"
    if sn.startswith("N"):
        return "#0ea5e9"
    return "#2f6bff"

def _init_caches():
    global _CACHE_ROUTES, _CACHE_STOPS
    if _CACHE_ROUTES is not None and _CACHE_STOPS is not None:
        return

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        _CACHE_ROUTES = []
        _CACHE_STOPS = []
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        ensure_db_indexes(conn)
        cur = conn.cursor()

        # Collect trip counts per route_id
        cur.execute("SELECT route_id, count(*) FROM trips GROUP BY route_id")
        trip_counts = dict(cur.fetchall())

        # Collect all routes and group by line short name
        cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes")
        routes_by_short = defaultdict(list)
        for r in cur.fetchall():
            rid = r["route_id"]
            raw_sn = r["route_short_name"] or ""
            sn = _short_name(raw_sn)
            tc = trip_counts.get(rid, 0)
            routes_by_short[sn].append({
                "id": rid,
                "short": sn,
                "raw_short": raw_sn,
                "name": r["route_long_name"] or "",
                "color": _get_color(sn),
                "_norm_short": _norm(sn),
                "_norm_name": _norm(r["route_long_name"] or ""),
                "_norm_raw": _norm(raw_sn),
                "trip_count": tc
            })

        # Pick the representative route with the most trips for each line
        routes_list = []
        for sn, variants in routes_by_short.items():
            variants.sort(key=lambda x: x["trip_count"], reverse=True)
            best = variants[0]
            # Save total trips of all variants
            total_trips = sum(v["trip_count"] for v in variants)
            best["trip_count"] = total_trips
            routes_list.append(best)

        # Sort routes by line number
        def _sort_key(x):
            sn = x["short"]
            return (0, int(sn)) if sn.isdigit() else (1, sn)
        routes_list.sort(key=_sort_key)
        _CACHE_ROUTES = routes_list

        # Stops
        cur.execute("""
            SELECT s.name as stop_name, 
                   GROUP_CONCAT(DISTINCT r.route_id || '|' || r.route_short_name || '|' || r.route_long_name) as r_info
            FROM stops s
            JOIN stop_times st ON s.stop_id = st.stop_id
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            GROUP BY s.name
        """)
        stops_list = []
        for r in cur.fetchall():
            s_name = r["stop_name"] or ""
            r_info = r["r_info"] or ""
            lines_map = {}
            for part in r_info.split(','):
                bits = part.split('|')
                if len(bits) >= 3:
                    rid, r_sn, r_ln = bits[0], bits[1], bits[2]
                    sn = _short_name(r_sn)
                    if sn not in lines_map:
                        lines_map[sn] = {
                            "id": rid,
                            "short": sn,
                            "name": r_ln,
                            "color": _get_color(sn)
                        }
            sorted_lines = sorted(lines_map.values(), key=lambda x: (len(x["short"]), x["short"]))
            stops_list.append({
                "id": s_name,
                "name": s_name,
                "lines": sorted_lines,
                "_norm": _norm(s_name)
            })
        _CACHE_STOPS = stops_list
        conn.close()
    except Exception as e:
        print(f"[JR API CACHE ERROR] {e}", flush=True)
        _CACHE_ROUTES = _CACHE_ROUTES or []
        _CACHE_STOPS = _CACHE_STOPS or []

def get_featured(count=9):
    _init_caches()
    if not _CACHE_ROUTES:
        return {"lines": [], "all_lines": []}
    import random
    candidates = [r for r in _CACHE_ROUTES if len(r["short"]) <= 3 and r["name"] and r["trip_count"] > 10]
    sample = random.sample(candidates, min(len(candidates), count)) if candidates else _CACHE_ROUTES[:count]
    lines = [{
        "id": r["id"],
        "short": r["short"],
        "name": r["name"],
        "color": r["color"]
    } for r in sample]
    all_lines = [{
        "id": r["id"],
        "short": r["short"],
        "name": r["name"],
        "color": r["color"]
    } for r in _CACHE_ROUTES]
    return {"lines": lines, "all_lines": all_lines}


def search(q):
    _init_caches()
    if not q or not q.strip():
        return {"lines": [], "stops": []}
    k = _norm(q).strip()

    # Match lines with exactness scoring
    scored_lines = []
    seen_keys = set()
    for r in (_CACHE_ROUTES or []):
        sn_n = r["_norm_short"]
        name_n = r["_norm_name"]
        raw_n = r["_norm_raw"]
        score = 0
        if sn_n == k or raw_n == k:
            score = 100
        elif sn_n.startswith(k) or raw_n.startswith(k):
            score = 80
        elif k in sn_n:
            score = 60
        elif name_n.startswith(k):
            score = 50
        elif k in name_n:
            score = 30

        if score > 0:
            key = (r["short"], r["name"])
            if key not in seen_keys:
                seen_keys.add(key)
                scored_lines.append((score, r["trip_count"], r))

    scored_lines.sort(key=lambda x: (x[0], x[1]), reverse=True)
    matched_lines = [{
        "id": item[2]["id"],
        "short": item[2]["short"],
        "name": item[2]["name"],
        "color": item[2]["color"]
    } for item in scored_lines[:15]]

    # Match stops
    scored_stops = []
    for s in (_CACHE_STOPS or []):
        sn = s["_norm"]
        score = 0
        if sn == k:
            score = 100
        elif sn.startswith(k):
            score = 80
        elif f" {k}" in sn or f",{k}" in sn or f", {k}" in sn:
            score = 60
        elif k in sn:
            score = 40

        if score > 0:
            scored_stops.append((score, s))

    scored_stops.sort(key=lambda x: (x[0], len(x[1]["lines"])), reverse=True)
    matched_stops = [{
        "id": item[1]["id"],
        "name": item[1]["name"],
        "lines": item[1]["lines"]
    } for item in scored_stops[:12]]

    return {"lines": matched_lines, "stops": matched_stops}

def _resolve_line_route_ids(cur, line_id):
    """Vrací (raw_short, sn, route_long_name, [route_ids]) pro danou linku."""
    mapping, _ = _get_line_mapping()
    line_id_str = str(line_id).strip()

    # 1. Přímé ID route_id (např. R4837)
    cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_id = ?", (line_id_str,))
    r = cur.fetchone()
    if r:
        raw_sn = r["route_short_name"]
        sn = _short_name(raw_sn)
        cur.execute("SELECT route_id FROM routes WHERE route_short_name = ?", (raw_sn,))
        all_rids = [row["route_id"] for row in cur.fetchall()]
        return raw_sn, sn, r["route_long_name"] or "", all_rids

    # 2. V mapování z gtfs_line_mapping.json (např. "1" -> "436001", "722" -> "490722")
    if line_id_str in mapping:
        target_raw = mapping[line_id_str]
        cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_short_name = ?", (target_raw,))
        rows = cur.fetchall()
        if rows:
            raw_sn = rows[0]["route_short_name"]
            sn = _short_name(raw_sn)
            all_rids = [row["route_id"] for row in rows]
            return raw_sn, sn, rows[0]["route_long_name"] or "", all_rids

    # 3. Přesný název raw linky (např. 490722)
    cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_short_name = ?", (line_id_str,))
    rows = cur.fetchall()
    if rows:
        raw_sn = rows[0]["route_short_name"]
        sn = _short_name(raw_sn)
        all_rids = [row["route_id"] for row in rows]
        return raw_sn, sn, rows[0]["route_long_name"] or "", all_rids

    # 4. Hledání podle zkratky linky (např. sn == "722")
    cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes")
    for row in cur.fetchall():
        if _short_name(row["route_short_name"]) == line_id_str:
            raw_sn = row["route_short_name"]
            sn = line_id_str
            cur.execute("SELECT route_id FROM routes WHERE route_short_name = ?", (raw_sn,))
            all_rids = [x["route_id"] for x in cur.fetchall()]
            return raw_sn, sn, row["route_long_name"] or "", all_rids

    return None, None, "", []

def resolve_services_for_route(cur, all_rids, day, today_str=None):
    """
    Vybere platná service_id pro dané linky a typ dne.
    Pokrývá standardní týdenní kalendář (vč. všech pracovních dnů po-pá),
    výjimky v calendar_dates a automatický fallback pro sezónní či specifické linky,
    aby uživatel nikdy neviděl falešné 'žádné spoje' a zároveň se nepletly pracovní dny do neděle.
    """
    if not today_str:
        today_str = datetime.now().strftime("%Y%m%d")

    q_marks = ','.join('?' for _ in all_rids)

    if day == 'weekday':
        cal_day_cond = "(c.monday = 1 OR c.tuesday = 1 OR c.wednesday = 1 OR c.thursday = 1 OR c.friday = 1)"
        cd_dow_cond = "strftime('%w', substr(cd.date, 1, 4) || '-' || substr(cd.date, 5, 2) || '-' || substr(cd.date, 7, 2)) IN ('1', '2', '3', '4', '5')"
    elif day == 'saturday':
        cal_day_cond = "(c.saturday = 1)"
        cd_dow_cond = "strftime('%w', substr(cd.date, 1, 4) || '-' || substr(cd.date, 5, 2) || '-' || substr(cd.date, 7, 2)) = '6'"
    else:  # sunday / svátky
        cal_day_cond = "(c.sunday = 1)"
        cd_dow_cond = "strftime('%w', substr(cd.date, 1, 4) || '-' || substr(cd.date, 5, 2) || '-' || substr(cd.date, 7, 2)) = '0'"

    # 1. Běžný kalendář v aktuálním provozním období
    cur.execute(f"""
        SELECT c.service_id
        FROM trips t
        JOIN calendar c ON t.service_id = c.service_id
        WHERE t.route_id IN ({q_marks})
          AND c.start_date <= ? AND c.end_date >= ?
          AND {cal_day_cond}
    """, all_rids + [today_str, today_str])
    active_services = set(r[0] for r in cur.fetchall())

    # Přidat aktivní služby z calendar_dates POUZE pro linky s nulovým kalendářem (např. nepravidelné/prázdninové),
    # aby se běžné pracovní linky (které měly jednorázovou výjimku na svátek) nepřidaly do nedělního řádu!
    cur.execute(f"""
        SELECT cd.service_id
        FROM trips t
        JOIN calendar c ON t.service_id = c.service_id
        JOIN calendar_dates cd ON t.service_id = cd.service_id
        WHERE t.route_id IN ({q_marks})
          AND (c.monday + c.tuesday + c.wednesday + c.thursday + c.friday + c.saturday + c.sunday) = 0
          AND cd.exception_type = 1
          AND {cd_dow_cond}
          AND cd.date >= ?
    """, all_rids + [today_str[:6] + '01'])
    active_services.update(r[0] for r in cur.fetchall())

    if active_services:
        return active_services

    # 2. Fallback: Nejbližší / nejnovější platné provozní období pro tuto linku se stejným dnem
    cur.execute(f"""
        SELECT c.service_id, c.end_date
        FROM trips t
        JOIN calendar c ON t.service_id = c.service_id
        WHERE t.route_id IN ({q_marks})
          AND {cal_day_cond}
        ORDER BY c.end_date DESC
    """, all_rids)
    rows = cur.fetchall()
    if rows:
        max_end = rows[0][1]
        fallback_services = set(r[0] for r in rows if r[1] == max_end)
        if fallback_services:
            return fallback_services

    # 3. Fallback: Záznamy v calendar_dates pro linky s nulovým calendar
    cur.execute(f"""
        SELECT cd.service_id
        FROM trips t
        JOIN calendar c ON t.service_id = c.service_id
        JOIN calendar_dates cd ON t.service_id = cd.service_id
        WHERE t.route_id IN ({q_marks})
          AND (c.monday + c.tuesday + c.wednesday + c.thursday + c.friday + c.saturday + c.sunday) = 0
          AND cd.exception_type = 1
          AND {cd_dow_cond}
    """, all_rids)
    cd_services = set(r[0] for r in cur.fetchall())
    if cd_services:
        return cd_services

    return set()



def get_line(line_id):
    if line_id in _LINE_CACHE:
        return _LINE_CACHE[line_id]

    _init_caches()
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        ensure_db_indexes(conn)
        cur = conn.cursor()

        raw_sn, sn, route_long_name, all_rids = _resolve_line_route_ids(cur, line_id)
        if not all_rids:
            conn.close()
            return None

        color = _get_color(sn)
        q_marks = ','.join('?' for _ in all_rids)

        cur.execute(f"""
            SELECT (spoj_cislo % 2) as parity, count(*) as cnt
            FROM trips
            WHERE route_id IN ({q_marks})
            GROUP BY parity
            ORDER BY parity DESC
        """, all_rids)
        parity_counts = {r["parity"]: r["cnt"] for r in cur.fetchall()}

        target_parities = []
        if parity_counts.get(1, 0) > 0: target_parities.append(1)
        if parity_counts.get(0, 0) > 0: target_parities.append(0)
        if not target_parities and parity_counts: target_parities = list(parity_counts.keys())

        directions = []
        for dir_idx, parity in enumerate(target_parities):
            cur.execute(f"""
                SELECT t.trip_id, t.spoj_cislo,
                       (SELECT s.name FROM stop_times st JOIN stops s ON st.stop_id = s.stop_id WHERE st.trip_id = t.trip_id AND NOT (st.pickup_type = '1' AND (st.arrival_time = '' OR st.arrival_time IS NULL)) ORDER BY st.stop_sequence ASC LIMIT 1) as first_stop,
                       (SELECT s.name FROM stop_times st JOIN stops s ON st.stop_id = s.stop_id WHERE st.trip_id = t.trip_id AND NOT (st.pickup_type = '1' AND (st.arrival_time = '' OR st.arrival_time IS NULL)) ORDER BY st.stop_sequence DESC LIMIT 1) as last_stop,
                       count(CASE WHEN NOT (st.pickup_type = '1' AND (st.arrival_time = '' OR st.arrival_time IS NULL)) THEN 1 END) as stop_count
                FROM trips t
                JOIN stop_times st ON t.trip_id = st.trip_id
                WHERE t.route_id IN ({q_marks}) AND (t.spoj_cislo % 2) = ?
                GROUP BY t.trip_id
            """, all_rids + [parity])
            trips_info = cur.fetchall()
            if not trips_info:
                continue

            var_groups = {}
            trip_stop_counts = {}
            for r in trips_info:
                f, l = r["first_stop"], r["last_stop"]
                if not f or not l:
                    continue
                k = (f, l)
                if k not in var_groups:
                    var_groups[k] = []
                var_groups[k].append(r["trip_id"])
                trip_stop_counts[r["trip_id"]] = r["stop_count"]

            raw_variants = []
            for (f, l), tids in var_groups.items():
                best_tid = max(tids, key=lambda tid: trip_stop_counts.get(tid, 0))
                cur.execute("""
                    SELECT s.name as stop_name, st.pickup_type
                    FROM stop_times st
                    JOIN stops s ON st.stop_id = s.stop_id
                    WHERE st.trip_id = ?
                    AND NOT (st.pickup_type = '1' AND (st.arrival_time = '' OR st.arrival_time IS NULL))
                    ORDER BY st.stop_sequence
                """, (best_tid,))
                v_stops = [{
                    "id": row["stop_name"],
                    "name": row["stop_name"],
                    "request": row["pickup_type"] in ('2', '3')
                } for row in cur.fetchall()]
                raw_variants.append({
                    "name": f"{f} ➜ {l}",
                    "from": f,
                    "to": l,
                    "trip_count": len(tids),
                    "stops": v_stops
                })

            if not raw_variants:
                continue

            # Hlavní variantu určíme kombinací pokrytí zastávek (délka trasy) a počtu spojů,
            # aby se výchozí trasou nestala zkrácená lokální kyvadlová varianta o 4 zastávkách!
            raw_variants.sort(key=lambda v: -(len(v["stops"]) * 12 + v["trip_count"]))

            variants = []
            for idx, v in enumerate(raw_variants):
                v["id"] = f"v{idx}"
                v["is_main"] = (idx == 0)
                variants.append(v)

            main_from = variants[0]["from"]
            main_to = variants[0]["to"]
            dir_name = f"{main_from} ➜ {main_to}"
            main_stops = variants[0]["stops"]

            directions.append({
                "id": dir_idx,
                "name": dir_name,
                "parity": parity,
                "main_from": main_from,
                "main_to": main_to,
                "variants": variants,
                "stops": main_stops
            })

        # Pokud linka reálně jezdí jen v jednom směru (např. okružní linka), nesyntetizujeme
        # fiktivní opačný směr, který by v databázi neměl žádné spoje.

        conn.close()
        res = {
            "id": all_rids[0],
            "short": sn,
            "name": route_long_name,
            "color": color,
            "directions": directions
        }
        _LINE_CACHE[line_id] = res
        _LINE_CACHE[all_rids[0]] = res
        return res
    except Exception as e:
        print(f"[JR API LINE ERROR] {e}", flush=True)
        return None

def get_trips(line_id, dir_idx=0, day="weekday", variant_id=None):
    try:
        dir_idx = int(dir_idx)
    except (TypeError, ValueError):
        dir_idx = 0

    cache_key = (str(line_id), dir_idx, str(day), str(variant_id or ''))
    if cache_key in _TRIPS_CACHE:
        return _TRIPS_CACHE[cache_key]

    line_info = get_line(line_id)
    if not line_info or not line_info.get("directions"):
        return {"trips": []}

    if dir_idx >= len(line_info["directions"]):
        dir_idx = 0

    dir_obj = line_info["directions"][dir_idx]
    target_stops = [s["name"] for s in dir_obj.get("stops", [])]

    if variant_id:
        for v in dir_obj.get("variants", []):
            if v.get("id") == variant_id:
                target_stops = [s["name"] for s in v.get("stops", [])]
                break

    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        ensure_db_indexes(conn)
        cur = conn.cursor()

        raw_sn, sn, _, all_rids = _resolve_line_route_ids(cur, line_id)
        if not all_rids:
            all_rids = [line_id]

        q_marks = ','.join('?' for _ in all_rids)
        now_dt = datetime.now()
        today_str = now_dt.strftime("%Y%m%d")
        dow_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        today_col = dow_names[now_dt.weekday()]

        allowed_services = resolve_services_for_route(cur, all_rids, day, today_str)

        target_parity = dir_obj.get("parity", 1 if dir_idx == 0 else 0)
        cur.execute(f"""
            SELECT trip_id, service_id, spoj_cislo 
            FROM trips 
            WHERE route_id IN ({q_marks}) AND (spoj_cislo % 2) = ?
        """, all_rids + [target_parity])
        trip_candidates = cur.fetchall()

        if not trip_candidates:
            cur.execute(f"""
                SELECT trip_id, service_id, spoj_cislo 
                FROM trips 
                WHERE route_id IN ({q_marks})
            """, all_rids)
            trip_candidates = cur.fetchall()

        matching_rows = [r for r in trip_candidates if r["service_id"] in allowed_services]
        if not matching_rows:
            return {"trips": []}

        # Deduplikace podle spoj_cislo
        seen_spoj = set()
        matching_trips = []
        trip_services = {}
        for r in matching_rows:
            sc = r["spoj_cislo"]
            if sc not in seen_spoj:
                seen_spoj.add(sc)
                matching_trips.append((r["trip_id"], sc))
                trip_services[r["trip_id"]] = r["service_id"]

        res_trips = []
        if matching_trips:
            used_sids = list(set(trip_services.values()))
            q_s = ','.join('?' for _ in used_sids)
            cur.execute(f"SELECT service_id, exception_type FROM calendar_dates WHERE date = ? AND service_id IN ({q_s})", [today_str] + used_sids)
            today_exceptions = dict(cur.fetchall())

            cur.execute(f"""
                SELECT service_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date
                FROM calendar 
                WHERE service_id IN ({q_s})
            """, used_sids)
            cal_info_map = {r["service_id"]: r for r in cur.fetchall()}

            # Detekce školních spojů: služby s výlukou na školní prázdniny (např. 29.10. podzimní prázdniny)
            cur.execute(f"""
                SELECT DISTINCT service_id 
                FROM calendar_dates 
                WHERE service_id IN ({q_s}) 
                  AND date IN ('20261029', '20260130', '20260402', '20261223', '20270130')
                  AND exception_type = 2
            """, used_sids)
            school_services = set(r[0] for r in cur.fetchall())

            tids = [m[0] for m in matching_trips]
            q_marks_trips = ','.join('?' for _ in tids)
            cur.execute(f"""
                SELECT st.trip_id, st.stop_id, s.name as stop_name, st.arrival_time, st.departure_time, st.pickup_type, st.stop_sequence
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id IN ({q_marks_trips})
                ORDER BY st.trip_id, st.stop_sequence
            """, tids)
            trip_rows_map = defaultdict(list)
            for r in cur.fetchall():
                trip_rows_map[r["trip_id"]].append(r)

            # Návaznosti (čekání na spoj a garantované přestupy z GTFS)
            waiting_map = defaultdict(lambda: defaultdict(list))
            transfer_map = defaultdict(lambda: defaultdict(list))
            try:
                # 1. to_trip_id je náš spoj -> NÁŠ SPOJ ČEKÁ na spoj from_line / from_spoj (trojúhelník)
                cur.execute(f"""
                    SELECT to_trip_id, from_line, from_spoj, stop_name, max_waiting_time, transfer_type
                    FROM transfers
                    WHERE to_trip_id IN ({q_marks_trips})
                """, tids)
                for r in cur.fetchall():
                    t_id = str(r[0])
                    from_l = _short_name(r[1])
                    from_sp = str(r[2] or "")
                    s_name = r[3]
                    wait_m = r[4]
                    wait_str = f" nejvýše {wait_m} min" if wait_m else ""
                    txt = f"V této zastávce vyčká příjezdu spoje {from_sp} linky {from_l}{wait_str}."
                    info = {
                        "type": "wait",
                        "line": from_l,
                        "spoj": from_sp,
                        "wait_min": wait_m,
                        "text": txt
                    }
                    if s_name:
                        waiting_map[t_id][s_name].append(info)

                # 2. from_trip_id je náš spoj -> GARANTOVANÝ PŘESTUP / PŘESTUP z našeho spoje
                cur.execute(f"""
                    SELECT from_trip_id, to_line, to_spoj, to_headsign, stop_name, max_waiting_time, transfer_type
                    FROM transfers
                    WHERE from_trip_id IN ({q_marks_trips})
                """, tids)
                for r in cur.fetchall():
                    t_id = str(r[0])
                    to_l = _short_name(r[1])
                    to_sp = str(r[2] or "")
                    to_head = str(r[3] or "")
                    s_name = r[4]
                    wait_m = r[5]
                    tt = r[6]
                    is_guar = (tt == '1' or (wait_m and wait_m > 0))
                    dest_str = f" do směru {to_head}" if to_head else ""
                    wait_str = f" (spoj vyčká až {wait_m} min)" if wait_m else ""
                    if is_guar:
                        txt = f"Garantovaný přestup na spoj {to_sp} linky {to_l}{dest_str}{wait_str}."
                        itype = "guaranteed"
                    else:
                        txt = f"Možnost přestupu na spoj {to_sp} linky {to_l}{dest_str}."
                        itype = "transfer"
                    info = {
                        "type": itype,
                        "line": to_l,
                        "spoj": to_sp,
                        "headsign": to_head,
                        "wait_min": wait_m,
                        "text": txt
                    }
                    if s_name:
                        transfer_map[t_id][s_name].append(info)
            except Exception as e_trans:
                print(f"[JR TRANSFERS WARN] {e_trans}", flush=True)

            is_today_weekday = (now_dt.weekday() < 5)
            is_today_saturday = (now_dt.weekday() == 5)
            is_today_sunday = (now_dt.weekday() == 6)

            for tid, sc in matching_trips:
                rows = trip_rows_map.get(tid, [])
                if not rows:
                    continue

                served_stops = []
                stop_time_map = {}
                tid_str = str(tid)
                for idx, r in enumerate(rows):
                    is_last = (idx == len(rows) - 1)
                    # Pro konečnou preferujeme arrival_time, pro ostatní departure_time
                    if is_last:
                        t_str = (r["arrival_time"] or r["departure_time"] or "").strip()[:5]
                    else:
                        t_str = (r["departure_time"] or r["arrival_time"] or "").strip()[:5]

                    if t_str:
                        s_name = r["stop_name"]
                        s_id = r["stop_id"]
                        
                        stop_conns = []
                        seen_c = set()
                        for c in waiting_map.get(tid_str, {}).get(s_name, []):
                            ck = (c["type"], c["line"], c["spoj"])
                            if ck not in seen_c:
                                seen_c.add(ck)
                                stop_conns.append(c)
                        for c in transfer_map.get(tid_str, {}).get(s_name, []):
                            ck = (c["type"], c["line"], c["spoj"])
                            if ck not in seen_c:
                                seen_c.add(ck)
                                stop_conns.append(c)

                        served_stops.append({
                            "name": s_name,
                            "time": t_str,
                            "request": r["pickup_type"] in ('2', '3'),
                            "exit_only": r["pickup_type"] == '1',
                            "transfers": stop_conns
                        })
                        if s_name not in stop_time_map:
                            stop_time_map[s_name] = t_str

                if not served_stops:
                    continue

                first_stop = served_stops[0]["name"]
                last_stop = served_stops[-1]["name"]
                dep_t = served_stops[0]["time"]
                # Příjezd na konečnou: přesný čas příjezdu z posledního záznamu
                arr_t = (rows[-1]["arrival_time"] or rows[-1]["departure_time"] or served_stops[-1]["time"]).strip()[:5]

                aligned_times = [stop_time_map.get(s_name, None) for s_name in target_stops]

                sid = trip_services.get(tid)
                scal = cal_info_map.get(sid)

                # Flags & Notes z GTFS kalendáře
                flags = ["low"]
                is_we = False
                is_sch = False
                is_hol = False

                if scal:
                    is_we = (scal["saturday"] == 1 or scal["sunday"] == 1) and (
                        scal["monday"] + scal["tuesday"] + scal["wednesday"] + scal["thursday"] + scal["friday"] == 0
                    )
                    is_sch = (sid in school_services)
                    is_hol = (scal["monday"] + scal["tuesday"] + scal["wednesday"] + scal["thursday"] + scal["friday"] + scal["saturday"] + scal["sunday"] == 0)

                    if is_we:
                        flags.append("weekend")
                    if is_sch:
                        flags.append("school")
                    if is_hol:
                        flags.append("holiday")

                note_parts = []
                if is_sch:
                    note_parts.append("Školní spoj (nejede o prázdninách)")
                elif is_we:
                    note_parts.append("Jede o víkendu a svátcích")
                elif is_hol:
                    note_parts.append("Jede pouze o svátcích")
                else:
                    note_parts.append("Jede v pracovní dny (po–pá)")

                if scal and scal["start_date"] and scal["end_date"]:
                    sd, ed = scal["start_date"], scal["end_date"]
                    if len(sd) == 8 and len(ed) == 8:
                        note_parts.append(f"Platí {sd[6:8]}.{sd[4:6]}. – {ed[6:8]}.{ed[4:6]}.{ed[:4]}")

                # Příznak zda spoj jede DNES podle reálného dne v týdnu
                if day == "weekday":
                    runs_today = is_today_weekday
                elif day == "saturday":
                    runs_today = is_today_saturday
                elif day == "sunday":
                    runs_today = is_today_sunday
                else:
                    runs_today = True

                res_trips.append({
                    "id": str(tid),
                    "spoj_cislo": sc,
                    "first_stop": first_stop,
                    "last_stop": last_stop,
                    "dep_time": dep_t,
                    "arr_time": arr_t,
                    "first_time": dep_t,
                    "today": runs_today,
                    "flags": flags,
                    "note": " · ".join(note_parts),
                    "stops": served_stops,
                    "times": aligned_times
                })

        res_trips.sort(key=lambda x: x["dep_time"])
        conn.close()
        out = {"trips": res_trips}
        _TRIPS_CACHE[cache_key] = out
        return out
    except Exception as e:
        print(f"[JR API TRIPS ERROR] {e}", flush=True)
        return {"trips": []}

