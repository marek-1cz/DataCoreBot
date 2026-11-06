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
from datetime import datetime
from collections import defaultdict

_CACHE_FEATURED = None
_CACHE_ROUTES = None
_CACHE_STOPS = None
_LINE_CACHE = {}
_TRIPS_CACHE = {}

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

def get_featured(count=6):
    _init_caches()
    if not _CACHE_ROUTES:
        return {"lines": []}
    import random
    candidates = [r for r in _CACHE_ROUTES if len(r["short"]) <= 3 and r["name"] and r["trip_count"] > 10]
    sample = random.sample(candidates, min(len(candidates), count)) if candidates else _CACHE_ROUTES[:count]
    lines = [{
        "id": r["id"],
        "short": r["short"],
        "name": r["name"],
        "color": r["color"]
    } for r in sample]
    return {"lines": lines}

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
    """Vrací (raw_short, sn, [route_ids]) pro danou linku."""
    cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_id = ?", (line_id,))
    r = cur.fetchone()
    if r:
        raw_sn = r["route_short_name"]
        sn = _short_name(raw_sn)
        cur.execute("SELECT route_id FROM routes WHERE route_short_name = ?", (raw_sn,))
        all_rids = [row["route_id"] for row in cur.fetchall()]
        return raw_sn, sn, r["route_long_name"] or "", all_rids

    # Pokud line_id byl zadán jako číslo linky (např. 722 nebo 424)
    cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_short_name LIKE ? OR route_short_name = ?", (f"%{line_id}", line_id))
    rows = cur.fetchall()
    if rows:
        raw_sn = rows[0]["route_short_name"]
        sn = _short_name(raw_sn)
        all_rids = [row["route_id"] for row in rows]
        return raw_sn, sn, rows[0]["route_long_name"] or "", all_rids

    return None, None, "", []

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
        cur = conn.cursor()

        raw_sn, sn, route_long_name, all_rids = _resolve_line_route_ids(cur, line_id)
        if not all_rids:
            conn.close()
            return None

        color = _get_color(sn)
        q_marks = ','.join('?' for _ in all_rids)

        today_str = datetime.now().strftime("%Y%m%d")

        directions = []
        for dir_idx, parity in enumerate([1, 0]):
            # 1. Zjistit aktivní trips v tomto směru
            cur.execute(f"""
                SELECT t.trip_id, t.spoj_cislo
                FROM trips t
                JOIN calendar c ON t.service_id = c.service_id
                WHERE t.route_id IN ({q_marks})
                  AND c.start_date <= ? AND c.end_date >= ?
                  AND (t.spoj_cislo % 2) = ?
                ORDER BY t.spoj_cislo
            """, all_rids + [today_str, today_str, parity])
            active_trips = cur.fetchall()
            tids = [row["trip_id"] for row in active_trips]

            if not tids:
                # Fallback: vzít nejnovější období kalendáře
                cur.execute(f"""
                    SELECT t.trip_id, t.spoj_cislo, c.end_date
                    FROM trips t
                    JOIN calendar c ON t.service_id = c.service_id
                    WHERE t.route_id IN ({q_marks}) AND (t.spoj_cislo % 2) = ?
                    ORDER BY c.end_date DESC
                """, all_rids + [parity])
                rows = cur.fetchall()
                if rows:
                    max_e = rows[0]["end_date"]
                    tids = [r["trip_id"] for r in rows if r["end_date"] == max_e]

            if not tids:
                cur.execute(f"SELECT trip_id FROM trips WHERE route_id IN ({q_marks}) AND (spoj_cislo % 2) = ?", all_rids + [parity])
                tids = [row["trip_id"] for row in cur.fetchall()]

            if not tids:
                continue

            # 2. Zjistit reálně obsluhované zastávky v tomto směru (pickup_type != '1' a čas není prázdný)
            cur.execute(f"""
                SELECT s.name as stop_name, st.pickup_type
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id IN ({','.join('?' for _ in tids[:100])})
                  AND st.arrival_time != '' AND st.arrival_time IS NOT NULL AND st.pickup_type != '1'
                GROUP BY s.name
            """, tids[:100])
            valid_rows = cur.fetchall()
            valid_stop_names = {row["stop_name"]: (row["pickup_type"] in ('2', '3')) for row in valid_rows}

            # 3. Nalezení nejúplnější trasy (master sequence)
            # Vybrat spoje s největším počtem zastávek
            cur.execute(f"""
                SELECT t.trip_id, count(st.stop_sequence) as cnt
                FROM trips t
                JOIN stop_times st ON t.trip_id = st.trip_id
                WHERE t.trip_id IN ({','.join('?' for _ in tids[:200])})
                GROUP BY t.trip_id
                ORDER BY cnt DESC
                LIMIT 25
            """, tids[:200])
            best_candidate_tids = [r["trip_id"] for r in cur.fetchall()] or tids[:10]

            best_seq = []
            for tid in best_candidate_tids[:6]:
                cur.execute("""
                    SELECT s.name as stop_name, st.pickup_type, st.arrival_time
                    FROM stop_times st
                    JOIN stops s ON st.stop_id = s.stop_id
                    WHERE st.trip_id = ?
                    ORDER BY st.stop_sequence
                """, (tid,))
                rows = cur.fetchall()
                seq = [
                    (row["stop_name"], row["pickup_type"] in ('2', '3') or valid_stop_names.get(row["stop_name"], False))
                    for row in rows
                    if row["stop_name"] in valid_stop_names
                ]
                if len(seq) > len(best_seq):
                    best_seq = seq

            if best_seq:
                stops = [{
                    "id": s_name,
                    "name": s_name,
                    "request": is_req
                } for s_name, is_req in best_seq]
                directions.append({
                    "id": dir_idx,
                    "stops": stops
                })

        if len(directions) == 1 and len(directions[0]["stops"]) > 1:
            rev_stops = list(reversed(directions[0]["stops"]))
            directions.append({
                "id": 1,
                "stops": rev_stops
            })

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

def get_trips(line_id, dir_idx=0, day="weekday"):
    try:
        dir_idx = int(dir_idx)
    except (TypeError, ValueError):
        dir_idx = 0

    cache_key = (str(line_id), dir_idx, str(day))
    if cache_key in _TRIPS_CACHE:
        return _TRIPS_CACHE[cache_key]

    line_info = get_line(line_id)
    if not line_info or not line_info.get("directions"):
        return {"trips": []}

    if dir_idx >= len(line_info["directions"]):
        dir_idx = 0

    target_stops = [s["name"] for s in line_info["directions"][dir_idx]["stops"]]
    if not target_stops:
        return {"trips": []}

    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        raw_sn, sn, _, all_rids = _resolve_line_route_ids(cur, line_id)
        if not all_rids:
            all_rids = [line_id]

        q_marks = ','.join('?' for _ in all_rids)
        today_str = datetime.now().strftime("%Y%m%d")
        col = "monday" if day == "weekday" else ("saturday" if day == "saturday" else "sunday")

        # Najít platné service_id pro tento den a linku
        cur.execute(f"""
            SELECT c.service_id 
            FROM trips t
            JOIN calendar c ON t.service_id = c.service_id
            WHERE t.route_id IN ({q_marks})
              AND c.start_date <= ? AND c.end_date >= ?
              AND c.{col} = 1
        """, all_rids + [today_str, today_str])
        allowed_services = set(r["service_id"] for r in cur.fetchall())

        if not allowed_services:
            # Fallback: nejnovější kalendář pro tento den
            cur.execute(f"""
                SELECT c.service_id, c.end_date
                FROM trips t
                JOIN calendar c ON t.service_id = c.service_id
                WHERE t.route_id IN ({q_marks}) AND c.{col} = 1
                ORDER BY c.end_date DESC
            """, all_rids)
            rows = cur.fetchall()
            if rows:
                max_e = rows[0]["end_date"]
                allowed_services = set(r["service_id"] for r in rows if r["end_date"] == max_e)

        if not allowed_services:
            cur.execute(f"SELECT service_id FROM calendar WHERE {col} = 1")
            allowed_services = set(r["service_id"] for r in cur.fetchall())

        # Vybrat spoje v daném směru
        target_parity = 1 if dir_idx == 0 else 0
        cur.execute(f"""
            SELECT trip_id, service_id, spoj_cislo 
            FROM trips 
            WHERE route_id IN ({q_marks}) AND (spoj_cislo % 2) = ?
        """, all_rids + [target_parity])
        
        matching_rows = [
            r for r in cur.fetchall() 
            if r["service_id"] in allowed_services
        ]

        seen_spoj = set()
        matching_trips = []
        for r in matching_rows:
            sc = r["spoj_cislo"]
            if sc not in seen_spoj:
                seen_spoj.add(sc)
                matching_trips.append(r["trip_id"])

        res_trips = []
        if matching_trips:
            q_marks_trips = ','.join('?' for _ in matching_trips)
            cur.execute(f"""
                SELECT st.trip_id, s.name as stop_name, st.arrival_time, st.pickup_type
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id IN ({q_marks_trips})
                ORDER BY st.trip_id, st.stop_sequence
            """, matching_trips)
            trip_rows_map = defaultdict(list)
            for r in cur.fetchall():
                trip_rows_map[r["trip_id"]].append(r)

            for tid in matching_trips:
                rows = trip_rows_map.get(tid, [])
                if not rows:
                    continue

                trip_stops = []
                for r in rows:
                    arr = (r["arrival_time"] or "").strip()
                    if arr and r["pickup_type"] != '1':
                        trip_stops.append((r["stop_name"], arr[:5]))

                times = align_trip_times(trip_stops, target_stops)
                non_null = [t for t in times if t]
                if len(non_null) < 2:
                    continue

                first_t = non_null[0]
                res_trips.append({
                    "id": str(tid),
                    "flags": ["low"],
                    "first_time": first_t,
                    "times": times
                })

        res_trips.sort(key=lambda x: x["first_time"])
        conn.close()
        out = {"trips": res_trips}
        _TRIPS_CACHE[cache_key] = out
        return out
    except Exception as e:
        print(f"[JR API TRIPS ERROR] {e}", flush=True)
        return {"trips": []}
