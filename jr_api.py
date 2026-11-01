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
from collections import defaultdict, Counter

_CACHE_FEATURED = None
_CACHE_ROUTES = None
_CACHE_STOPS = None

def _get_db_path():
    curr = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(curr, "gtfs_stops_idpk.db")
    if not os.path.exists(p):
        p = "gtfs_stops_idpk.db"
    return p

def _norm(s):
    if not s:
        return ""
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('utf-8').lower()

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
    if sn.startswith("P") or sn.startswith("Os") or sn.startswith("Sp") or sn.startswith("R"):
        return "#f59e0b"
    return "#2f6bff"

def _init_caches():
    global _CACHE_ROUTES, _CACHE_STOPS
    if _CACHE_ROUTES is not None:
        return
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Routes
        cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes")
        routes_list = []
        for r in cur.fetchall():
            sn = _short_name(r["route_short_name"])
            routes_list.append({
                "id": r["route_id"],
                "short": sn,
                "raw_short": r["route_short_name"],
                "name": r["route_long_name"] or "",
                "color": _get_color(sn),
                "_norm_short": _norm(sn),
                "_norm_name": _norm(r["route_long_name"] or ""),
                "_norm_raw": _norm(r["route_short_name"])
            })
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
            lines = []
            seen = set()
            for part in r_info.split(','):
                bits = part.split('|')
                if len(bits) >= 3:
                    rid, r_sn, r_ln = bits[0], bits[1], bits[2]
                    sn = _short_name(r_sn)
                    if rid not in seen:
                        seen.add(rid)
                        lines.append({
                            "id": rid,
                            "short": sn,
                            "name": r_ln,
                            "color": _get_color(sn)
                        })
            stops_list.append({
                "id": s_name,
                "name": s_name,
                "lines": lines,
                "_norm": _norm(s_name)
            })
        _CACHE_STOPS = stops_list
        conn.close()
    except Exception as e:
        print(f"[JR API CACHE ERROR] {e}", flush=True)

def get_featured(count=6):
    _init_caches()
    if not _CACHE_ROUTES:
        return {"lines": []}
    import random
    candidates = [r for r in _CACHE_ROUTES if len(r["short"]) <= 3 and r["name"]]
    sample = random.sample(candidates, min(len(candidates), count)) if candidates else []
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

    # Match lines
    matched_lines = []
    seen_l = set()
    for r in (_CACHE_ROUTES or []):
        if k in r["_norm_short"] or k in r["_norm_name"] or k in r["_norm_raw"]:
            if r["id"] not in seen_l:
                seen_l.add(r["id"])
                matched_lines.append({
                    "id": r["id"],
                    "short": r["short"],
                    "name": r["name"],
                    "color": r["color"]
                })
        if len(matched_lines) >= 15:
            break

    # Match stops
    matched_stops = []
    for s in (_CACHE_STOPS or []):
        if k in s["_norm"]:
            matched_stops.append({
                "id": s["id"],
                "name": s["name"],
                "lines": s["lines"][:8]
            })
        if len(matched_stops) >= 10:
            break

    return {"lines": matched_lines, "stops": matched_stops}

_LINE_CACHE = {}

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

        cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_id = ?", (line_id,))
        r = cur.fetchone()
        if not r:
            conn.close()
            return None
        sn = _short_name(r["route_short_name"])
        color = _get_color(sn)

        cur.execute("SELECT trip_id FROM trips WHERE route_id = ?", (line_id,))
        trips = [row["trip_id"] for row in cur.fetchall()]

        trip_stops = []
        for tid in trips[:40]:
            cur.execute("""
                SELECT s.name as stop_name, st.pickup_type
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY st.stop_sequence
            """, (tid,))
            rows = cur.fetchall()
            if rows:
                trip_stops.append([(row["stop_name"], row["pickup_type"] in ('2', '3')) for row in rows])

        dirs_map = defaultdict(list)
        for seq in trip_stops:
            key = (seq[0][0], seq[-1][0])
            dirs_map[key].append(seq)

        sorted_dirs = sorted(dirs_map.items(), key=lambda x: len(x[1]), reverse=True)[:2]
        directions = []
        for dir_idx, ((start_stop, end_stop), seq_list) in enumerate(sorted_dirs):
            best_seq = max(seq_list, key=len)
            stops = []
            for s_name, is_req in best_seq:
                stops.append({
                    "id": s_name,
                    "name": s_name,
                    "request": is_req
                })
            directions.append({
                "id": dir_idx,
                "stops": stops
            })

        conn.close()
        res = {
            "id": r["route_id"],
            "short": sn,
            "name": r["route_long_name"] or "",
            "color": color,
            "directions": directions
        }
        _LINE_CACHE[line_id] = res
        return res
    except Exception as e:
        print(f"[JR API LINE ERROR] {e}", flush=True)
        return None

def get_trips(line_id, dir_idx=0, day="weekday"):
    line_info = get_line(line_id)
    if not line_info or not line_info.get("directions"):
        return {"trips": []}

    try:
        dir_idx = int(dir_idx)
    except (TypeError, ValueError):
        dir_idx = 0

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

        col = "monday" if day == "weekday" else ("saturday" if day == "saturday" else "sunday")
        cur.execute(f"SELECT service_id FROM calendar WHERE {col} = 1")
        allowed_services = set(r["service_id"] for r in cur.fetchall())

        cur.execute("SELECT trip_id, service_id FROM trips WHERE route_id = ?", (line_id,))
        matching_trips = [r["trip_id"] for r in cur.fetchall() if r["service_id"] in allowed_services]

        res_trips = []
        for tid in matching_trips:
            cur.execute("""
                SELECT s.name as stop_name, st.arrival_time
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY st.stop_sequence
            """, (tid,))
            rows = cur.fetchall()
            if not rows:
                continue
            first_s, last_s = rows[0]["stop_name"], rows[-1]["stop_name"]
            # Match direction roughly (start stop in first half of target stops, or matching end)
            if first_s != target_stops[0] and last_s != target_stops[-1]:
                # If neither start nor end matches, check if it fits the route sequence
                pass

            t_map = {r["stop_name"]: r["arrival_time"][:5] for r in rows}
            times = [t_map.get(s_name) for s_name in target_stops]
            # Must have at least 2 stops matching
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

        conn.close()
        res_trips.sort(key=lambda x: x["first_time"])
        return {"trips": res_trips}
    except Exception as e:
        print(f"[JR API TRIPS ERROR] {e}", flush=True)
        return {"trips": []}
