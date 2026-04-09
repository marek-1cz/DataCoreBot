import time
import json
import urllib.request
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, Response
from zoneinfo import ZoneInfo
import math
import re

mapa_bp = Blueprint('mapa_bp', __name__)

# Globální paměť
GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA = []

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

def background_map_worker():
    print("[MAPA] Inteligentní mozek mapy startuje...", flush=True)
    url_inflow = "https://pvvd.idpk.cz/Ajax/GetPoints" 
    url_arriva = "https://www.arriva.cz/api/graphql" 
    
    while True:
        now = get_prague_time()
        data_inflow = []
        data_arriva = []

        try:
            req1 = urllib.request.Request(url_inflow, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req1, timeout=5) as r1:
                data_inflow = json.loads(r1.read().decode())
        except Exception as e: print(f"[MAPA] Inflow Error: {e}")

        try:
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation { busesCurrentLocations { latitude longitude linkNumber spz type destinationName linkNumberAlias } }"
            }
            req2 = urllib.request.Request(url_arriva, data=json.dumps(arriva_payload).encode('utf-8'),
                headers={'User-Agent': 'Mozilla/5.0','Content-Type': 'application/json','Origin': 'https://www.arriva.cz'}, method='POST')
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                data_arriva = resp2.get("data", {}).get("busesCurrentLocations", [])
        except Exception as e: print(f"[MAPA] Arriva Error: {e}")

        current_bus_ids = set()
        new_live_data = []

        if isinstance(data_inflow, list):
            for bus1 in data_inflow:
                try:
                    bus_id = str(bus1.get("id", "0"))
                    line = str(bus1.get("text", "")).strip()
                    lat1 = bus1.get("lat", 0)
                    lng1 = bus1.get("lng", 0)
                    # Oprava zpoždění - Inflow GetPoints posílá minuty
                    delay = bus1.get("delay", 0)
                    dest1 = str(bus1.get("finalStopName", "")).strip()
                    traction = str(bus1.get("traction", "BUS")).upper()
                    is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]
                    
                    current_bus_ids.add(bus_id)

                    if bus_id not in GLOBAL_BUS_CACHE:
                        GLOBAL_BUS_CACHE[bus_id] = {
                            "lat": lat1, "lng": lng1, "line": line, "spz": None,
                            "last_moved": now, "first_seen": now, "spz_locked": False, "status": "N/A"
                        }
                    
                    cached = GLOBAL_BUS_CACHE[bus_id]
                    
                    # Detekce pohybu pro Status
                    dist_moved = math.hypot(lat1 - cached["lat"], lng1 - cached["lng"])
                    if dist_moved > 0.0001: # Opravdu se pohnul
                        cached["status"] = "Jízda"
                        cached["last_moved"] = now
                        cached["lat"] = lat1
                        cached["lng"] = lng1
                    else:
                        cached["status"] = "Stojí"

                    inactive_mins = (now - cached["last_moved"]).total_seconds() / 60.0

                    # PÁROVÁNÍ SPZ S POJISTKOU (LOCK)
                    if not is_train and not cached["spz_locked"]:
                        for bus2 in data_arriva:
                            b2_line = str(bus2.get("linkNumber", "")).strip()
                            b2_alias = str(bus2.get("linkNumberAlias", "")).strip()
                            if b2_line == line or b2_alias == line:
                                dist = math.hypot(lat1 - bus2.get("latitude", 0), lng1 - bus2.get("longitude", 0))
                                if dist < 0.015: # Bus je blízko
                                    cached["spz"] = bus2.get("spz", "Neznámá").strip()
                                    cached["spz_locked"] = True # Zamkneme SPZ pro tento bus_id
                                    break
                    
                    # Pokud bus neodpovídá > 10 min, odemkneme SPZ (možná ji dostal jiný vůz)
                    if inactive_mins > 10:
                        cached["spz_locked"] = False

                    new_live_data.append({
                        "id": bus_id, "lat": lat1, "lng": lng1, "line": line,
                        "delay": delay, "destination": dest1, "spz": cached["spz"] or "Neznámá",
                        "is_train": is_train, "status": cached["status"],
                        "inactive_minutes": inactive_mins,
                        "last_updated": cached["last_moved"].strftime("%H:%M:%S") if inactive_mins < 10 else "N/A"
                    })
                except: continue

        # Clean old
        keys_to_remove = [k for k in GLOBAL_BUS_CACHE.keys() if k not in current_bus_ids]
        for k in keys_to_remove: del GLOBAL_BUS_CACHE[k]

        global LIVE_BUSES_DATA
        LIVE_BUSES_DATA = new_live_data
        time.sleep(10)

def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()

@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({"status": "success", "buses": LIVE_BUSES_DATA})

@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    url_info = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}"
    url_tt = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0"
    
    try:
        # Načtení detailu pro Linku/Spoj/Zastávku
        with urllib.request.urlopen(urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'}), timeout=3) as r:
            info_html = r.read().decode('utf-8')
        
        # Načtení JŘ
        with urllib.request.urlopen(urllib.request.Request(url_tt, headers={'User-Agent': 'Mozilla/5.0'}), timeout=3) as r:
            tt_html = r.read().decode('utf-8')

        # Extrakce dat z Inflow tabulky (Linka, Spoj, Zastávka, Zpoždění)
        # Hledáme <td> hodnoty
        data_cells = re.findall(r'<td>(.*?)</td>', info_html, re.DOTALL)
        # 0: Linka, 1: Spoj, 2: Bezbariérovost (v ignoraci), 3: Zastávka, 4: Zpoždění
        
        linkospoj = data_cells[0].strip() if len(data_cells) > 0 else "N/A"
        spoj_num = data_cells[1].strip() if len(data_cells) > 1 else "N/A"
        zastavka = data_cells[3].strip() if len(data_cells) > 3 else "N/A"
        real_delay = data_cells[4].strip() if len(data_cells) > 4 else "0 min."

        # Výpočet začátek/konec linky z JŘ (první a poslední řádek tabulky)
        times = re.findall(r'\d{2}:\d{2}', tt_html)
        status_msg = "V jízdě"
        if times:
            now_t = get_prague_time().strftime("%H:%M")
            if now_t <= times[0]: status_msg = "Začátek linky (Čeká)"
            elif now_t >= times[-1]: status_msg = "Konec linky"

        custom_html = f"""
        <style>
            .ois-detail {{ background: #0f172a; color: white; font-family: sans-serif; padding: 10px; border-radius: 5px; }}
            .ois-header {{ color: #38bdf8; font-weight: bold; border-bottom: 1px solid #334155; margin-bottom: 10px; padding-bottom: 5px; font-size: 16px; }}
            .ois-row {{ display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 14px; }}
            .ois-label {{ color: #94a3b8; }}
            .ois-val {{ font-weight: bold; color: #f8fafc; }}
            .ois-delay {{ color: #fbbf24; }}
            .ois-table-wrapper {{ margin-top: 15px; border: 1px solid #334155; border-radius: 4px; overflow: hidden; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
            th {{ background: #1e293b; color: #38bdf8; text-align: left; padding: 8px; }}
            td {{ padding: 8px; border-bottom: 1px solid #334155; }}
            tr:nth-child(even) {{ background: #1e293b; }}
        </style>
        <div class="ois-detail">
            <div class="ois-header">Detail spoje {linkospoj}/{spoj_num}</div>
            <div class="ois-row"><span class="ois-label">Aktuální zastávka:</span><span class="ois-val">{zastavka}</span></div>
            <div class="ois-row"><span class="ois-label">Status:</span><span class="ois-val">{status_msg}</span></div>
            <div class="ois-row"><span class="ois-label">Zpoždění:</span><span class="ois-val ois-delay">{real_delay}</span></div>
            <div class="ois-table-wrapper">{tt_html}</div>
        </div>
        """
        return Response(custom_html, mimetype='text/html')
    except Exception as e:
        return f"Chyba načítání: {e}"
