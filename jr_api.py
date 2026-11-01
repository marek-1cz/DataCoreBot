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

SAMPLE_LINES = {
    "L21": {
        "id": "L21", "short": "21", "name": "Plzeň, CAN – Dobřany, náměstí", "color": "#2f6bff",
        "directions": [
            {
                "id": 0,
                "stops": [
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False},
                    {"id": "plzen-anglicke-nabrezi", "name": "Plzeň, Anglické nábřeží", "request": False},
                    {"id": "plzen-slovany", "name": "Plzeň, Slovany", "request": False},
                    {"id": "plzen-skvrnany", "name": "Plzeň, Skvrňany", "request": True},
                    {"id": "plzen-krimice", "name": "Plzeň, Křimice", "request": False},
                    {"id": "chotesov-namesti", "name": "Chotěšov, náměstí", "request": False},
                    {"id": "dobrany-namesti", "name": "Dobřany, náměstí", "request": False}
                ],
                "offsets": [0, 4, 9, 15, 22, 31, 38]
            },
            {
                "id": 1,
                "stops": [
                    {"id": "dobrany-namesti", "name": "Dobřany, náměstí", "request": False},
                    {"id": "chotesov-namesti", "name": "Chotěšov, náměstí", "request": False},
                    {"id": "plzen-krimice", "name": "Plzeň, Křimice", "request": False},
                    {"id": "plzen-skvrnany", "name": "Plzeň, Skvrňany", "request": True},
                    {"id": "plzen-slovany", "name": "Plzeň, Slovany", "request": False},
                    {"id": "plzen-anglicke-nabrezi", "name": "Plzeň, Anglické nábřeží", "request": False},
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False}
                ],
                "offsets": [0, 7, 16, 23, 29, 34, 38]
            }
        ],
        "hw": [20, 40, 60]
    },
    "L36": {
        "id": "L36", "short": "36", "name": "Plzeň, CAN – Horní Bříza, náměstí", "color": "#1f9d5c",
        "directions": [
            {
                "id": 0,
                "stops": [
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False},
                    {"id": "plzen-bolevec", "name": "Plzeň, Bolevec", "request": False},
                    {"id": "plzen-lochotin", "name": "Plzeň, Lochotín", "request": False},
                    {"id": "plzen-vochov", "name": "Plzeň, Vochov", "request": True},
                    {"id": "tremosna-namesti", "name": "Třemošná, náměstí", "request": False},
                    {"id": "horni-briza-namesti", "name": "Horní Bříza, náměstí", "request": False}
                ],
                "offsets": [0, 7, 12, 20, 27, 36]
            },
            {
                "id": 1,
                "stops": [
                    {"id": "horni-briza-namesti", "name": "Horní Bříza, náměstí", "request": False},
                    {"id": "tremosna-namesti", "name": "Třemošná, náměstí", "request": False},
                    {"id": "plzen-vochov", "name": "Plzeň, Vochov", "request": True},
                    {"id": "plzen-lochotin", "name": "Plzeň, Lochotín", "request": False},
                    {"id": "plzen-bolevec", "name": "Plzeň, Bolevec", "request": False},
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False}
                ],
                "offsets": [0, 9, 16, 24, 29, 36]
            }
        ],
        "hw": [30, 60, 90]
    },
    "L54": {
        "id": "L54", "short": "54", "name": "Plzeň, hlavní nádraží – Nezvěstice, náměstí", "color": "#c77d00",
        "directions": [
            {
                "id": 0,
                "stops": [
                    {"id": "plzen-hl-nadr", "name": "Plzeň, hlavní nádraží", "request": False},
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False},
                    {"id": "plzen-doudlevce", "name": "Plzeň, Doudlevce", "request": False},
                    {"id": "stary-plzenec", "name": "Starý Plzenec, náměstí", "request": False},
                    {"id": "stahnavy", "name": "Šťáhlavy, žel. st.", "request": False},
                    {"id": "nezvestice", "name": "Nezvěstice, náměstí", "request": False}
                ],
                "offsets": [0, 3, 10, 24, 33, 41]
            },
            {
                "id": 1,
                "stops": [
                    {"id": "nezvestice", "name": "Nezvěstice, náměstí", "request": False},
                    {"id": "stahnavy", "name": "Šťáhlavy, žel. st.", "request": False},
                    {"id": "stary-plzenec", "name": "Starý Plzenec, náměstí", "request": False},
                    {"id": "plzen-doudlevce", "name": "Plzeň, Doudlevce", "request": False},
                    {"id": "plzen-can", "name": "Plzeň, CAN", "request": False},
                    {"id": "plzen-hl-nadr", "name": "Plzeň, hlavní nádraží", "request": False}
                ],
                "offsets": [0, 8, 17, 31, 38, 41]
            }
        ],
        "hw": [60, 120, 120]
    }
}

def _fmt_min(m):
    h = (m // 60) % 24
    mi = m % 60
    return f"{h:02d}:{mi:02d}"

def _generate_sample_trips(line_id, dir_idx, day):
    item = SAMPLE_LINES.get(line_id)
    if not item:
        return {"trips": []}
    dirs = item["directions"]
    d_info = dirs[dir_idx if dir_idx < len(dirs) else 0]
    hw_idx = 0 if day == "weekday" else (1 if day == "saturday" else 2)
    hw = item["hw"][hw_idx]
    first_min = 260 if day == "weekday" else (330 if day == "saturday" else 390)
    last_min = 22 * 60
    trips = []
    i = 0
    start_offset = 10 if dir_idx else 0
    t = first_min + start_offset
    while t <= last_min:
        times = [_fmt_min(t + off) for off in d_info["offsets"]]
        fl = ["low"]
        if i % 4 == 0:
            fl.append("school")
        trips.append({
            "id": f"{line_id}-{dir_idx}-{day}-{i}",
            "flags": fl,
            "first_time": times[0],
            "times": times
        })
        t += hw
        i += 1
    return {"trips": trips}

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

    routes_list = []
    # 1. Add canonical sample lines
    for lid, sl in SAMPLE_LINES.items():
        routes_list.append({
            "id": sl["id"],
            "short": sl["short"],
            "raw_short": sl["short"],
            "name": sl["name"],
            "color": sl["color"],
            "_norm_short": _norm(sl["short"]),
            "_norm_name": _norm(sl["name"]),
            "_norm_raw": _norm(sl["short"]),
            "trip_count": 999
        })

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        _CACHE_ROUTES = routes_list
        _CACHE_STOPS = []
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Count trips per route to prioritize canonical route_id when duplicates exist
        cur.execute("SELECT route_id, count(*) as cnt FROM trips GROUP BY route_id")
        trip_counts = {r["route_id"]: r["cnt"] for r in cur.fetchall()}

        # Routes
        cur.execute("SELECT route_id, route_short_name, route_long_name FROM routes")
        for r in cur.fetchall():
            sn = _short_name(r["route_short_name"])
            rid = r["route_id"]
            routes_list.append({
                "id": rid,
                "short": sn,
                "raw_short": r["route_short_name"],
                "name": r["route_long_name"] or "",
                "color": _get_color(sn),
                "_norm_short": _norm(sn),
                "_norm_name": _norm(r["route_long_name"] or ""),
                "_norm_raw": _norm(r["route_short_name"]),
                "trip_count": trip_counts.get(rid, 0)
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
                    key = (sn, r_ln)
                    if key not in seen:
                        seen.add(key)
                        lines.append({
                            "id": rid,
                            "short": sn,
                            "name": r_ln,
                            "color": _get_color(sn)
                        })
            stops_list.append({
                "id": s_name,
                "name": s_name,
                "lines": sorted(lines, key=lambda x: (len(x["short"]), x["short"])),
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
    candidates = [r for r in _CACHE_ROUTES if len(r["short"]) <= 3 and r["name"] and r["trip_count"] > 5]
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
            score = 40

        if score > 0:
            key = (r["short"], r["name"])
            if key not in seen_keys:
                seen_keys.add(key)
                scored_lines.append((score, r["trip_count"], r))

    # Sort lines: score DESC, trip_count DESC, length of short name ASC
    scored_lines.sort(key=lambda x: (-x[0], -x[1], len(x[2]["short"]), x[2]["short"]))
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
        if sn == k:
            score = 100
        elif sn.startswith(k):
            score = 80
        elif k in sn:
            score = 50
        else:
            score = 0
        if score > 0:
            scored_stops.append((score, s))

    scored_stops.sort(key=lambda x: (-x[0], len(x[1]["name"])))
    matched_stops = [{
        "id": s[1]["id"],
        "name": s[1]["name"],
        "lines": s[1]["lines"][:8]
    } for s in scored_stops[:10]]

    return {"lines": matched_lines, "stops": matched_stops}

_LINE_CACHE = {}

def get_line(line_id):
    if line_id in SAMPLE_LINES:
        item = SAMPLE_LINES[line_id]
        return {
            "id": item["id"],
            "short": item["short"],
            "name": item["name"],
            "color": item["color"],
            "directions": [
                {"id": d["id"], "stops": d["stops"]} for d in item["directions"]
            ]
        }

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

        today_str = datetime.now().strftime("%Y%m%d")
        cur.execute("SELECT count(*) FROM calendar WHERE start_date <= ? AND end_date >= ?", (today_str, today_str))
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT max(end_date) FROM calendar")
            m_end = cur.fetchone()[0]
            if m_end:
                today_str = m_end

        directions = []
        for dir_idx, parity in enumerate([1, 0]):
            cur.execute("""
                SELECT t.trip_id, t.spoj_cislo
                FROM trips t
                JOIN calendar c ON t.service_id = c.service_id
                WHERE t.route_id = ?
                  AND c.start_date <= ?
                  AND c.end_date >= ?
                  AND (t.spoj_cislo % 2) = ?
                ORDER BY t.spoj_cislo
            """, (line_id, today_str, today_str, parity))
            active_trips = cur.fetchall()
            tids = [row["trip_id"] for row in active_trips]

            if not tids:
                cur.execute("SELECT trip_id FROM trips WHERE route_id = ? AND (spoj_cislo % 2) = ?", (line_id, parity))
                tids = [row["trip_id"] for row in cur.fetchall()]

            if not tids:
                continue

            cur.execute(f"""
                SELECT s.name as stop_name, st.pickup_type
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id IN ({','.join('?' for _ in tids)})
                  AND st.arrival_time != '' AND st.arrival_time IS NOT NULL AND st.pickup_type != '1'
                GROUP BY s.name
            """, tids)
            valid_rows = cur.fetchall()
            valid_stop_names = {row["stop_name"]: (row["pickup_type"] in ('2', '3')) for row in valid_rows}

            best_seq = []
            for tid in tids[:40]:
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
    if line_id in SAMPLE_LINES:
        return _generate_sample_trips(line_id, dir_idx, day)

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

        today_str = datetime.now().strftime("%Y%m%d")
        cur.execute("SELECT count(*) FROM calendar WHERE start_date <= ? AND end_date >= ?", (today_str, today_str))
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT max(end_date) FROM calendar")
            m_end = cur.fetchone()[0]
            if m_end:
                today_str = m_end

        col = "monday" if day == "weekday" else ("saturday" if day == "saturday" else "sunday")
        
        cur.execute(f"SELECT service_id FROM calendar WHERE {col} = 1 AND start_date <= ? AND end_date >= ?", (today_str, today_str))
        allowed_services = set(r["service_id"] for r in cur.fetchall())

        if not allowed_services:
            cur.execute(f"SELECT service_id FROM calendar WHERE {col} = 1")
            allowed_services = set(r["service_id"] for r in cur.fetchall())

        cur.execute("SELECT trip_id, service_id, spoj_cislo FROM trips WHERE route_id = ?", (line_id,))
        target_parity = 1 if dir_idx == 0 else 0
        matching_rows = [
            r for r in cur.fetchall() 
            if r["service_id"] in allowed_services and (r["spoj_cislo"] or 1) % 2 == target_parity
        ]

        seen_spoj = set()
        matching_trips = []
        for r in matching_rows:
            sc = r["spoj_cislo"]
            if sc not in seen_spoj:
                seen_spoj.add(sc)
                matching_trips.append(r["trip_id"])

        res_trips = []
        for tid in matching_trips:
            cur.execute("""
                SELECT s.name as stop_name, st.arrival_time, st.pickup_type
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY st.stop_sequence
            """, (tid,))
            rows = cur.fetchall()
            if not rows:
                continue

            t_map = {}
            for r in rows:
                arr = (r["arrival_time"] or "").strip()
                if arr and r["pickup_type"] != '1':
                    t_map[r["stop_name"]] = arr[:5]

            times = [t_map.get(s_name) for s_name in target_stops]
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
        return {"trips": res_trips}
    except Exception as e:
        print(f"[JR API TRIPS ERROR] {e}", flush=True)
        return {"trips": []}
