import time
import json
import urllib.request
import threading
from datetime import datetime
from flask import Blueprint, jsonify, Response
from zoneinfo import ZoneInfo
import math

mapa_bp = Blueprint('mapa_bp', __name__)

# Globální paměť běžící 24/7
GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA = []

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

# --- 24/7 BACKGROUND TRACKING ---
def background_map_worker():
    print("[MAPA] Startuji 24/7 sledování autobusů na pozadí...", flush=True)
    url_inflow = "https://pvvd.idpk.cz/Ajax/GetPoints" 
    url_arriva = "https://www.arriva.cz/api/graphql" 
    
    while True:
        now = get_prague_time()
        data_inflow = []
        data_arriva = []

        # 1. Stáhnout Inflow
        try:
            req1 = urllib.request.Request(url_inflow, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req1, timeout=5) as r1:
                data_inflow = json.loads(r1.read().decode())
        except Exception as e:
            print(f"[MAPA] Chyba Inflow: {e}")

        # 2. Stáhnout Arrivu
        try:
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle\n    delay\n    destinationName\n    lastStopName\n    latitude\n    longitude\n    linkNumber\n    state\n    type\n    mainType\n    spz\n    updated\n    linkNumberAlias\n    __typename\n  }\n}"
            }
            req2 = urllib.request.Request(
                url_arriva, 
                data=json.dumps(arriva_payload).encode('utf-8'),
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/'
                },
                method='POST'
            )
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and len(resp2) > 0 and "data" in resp2[0]:
                    data_arriva = resp2[0]["data"].get("busesCurrentLocations", [])
                elif isinstance(resp2, dict) and "data" in resp2:
                    data_arriva = resp2["data"].get("busesCurrentLocations", [])
        except Exception as e:
            print(f"[MAPA] Chyba Arriva: {e}")

        # 3. Sloučení a logika SPZ
        current_bus_ids = set()
        new_live_data = []

        if isinstance(data_inflow, list):
            for bus1 in data_inflow:
                line = str(bus1.get("text", "")).strip()
                lat1 = bus1.get("lat", 0)
                lng1 = bus1.get("lng", 0)
                traction = str(bus1.get("traction", "BUS")).upper()
                
                try: bus_id = int(bus1.get("id", 0))
                except: bus_id = 0
                
                is_train = bus_id < 0 or traction == "TRAIN" or traction == "UNKNOWN"
                current_bus_ids.add(bus_id)

                # Inicializace v paměti
                if bus_id not in GLOBAL_BUS_CACHE:
                    GLOBAL_BUS_CACHE[bus_id] = {
                        "lat": lat1, "lng": lng1, "line": line, 
                        "first_seen": now, "last_moved": None,
                        "spz": None, "state": "normal", "estimated": False
                    }
                
                cached = GLOBAL_BUS_CACHE[bus_id]
                
                # Kontrola pohybu
                if cached["lat"] != lat1 or cached["lng"] != lng1:
                    cached["last_moved"] = now
                    cached["lat"] = lat1
                    cached["lng"] = lng1

                last_updated_dt = cached["last_moved"] if cached["last_moved"] else cached["first_seen"]
                inactive_minutes = (now - last_updated_dt).total_seconds() / 60.0

                # HLEDÁNÍ SPZ V ARRIVĚ (Pouze autobusy)
                found_in_arriva = False
                if not is_train and data_arriva:
                    for bus2 in data_arriva:
                        # Filtr jen na Prahu, SČ a Express
                        t_type = bus2.get("type", "")
                        if t_type not in ["Praha a Střední Čechy", "Express"]:
                            continue
                            
                        b2_line = str(bus2.get("linkNumber", "")).strip()
                        b2_alias = str(bus2.get("linkNumberAlias", "")).strip()
                        
                        if b2_line == line or b2_alias == line:
                            lat2 = bus2.get("latitude", 0)
                            lng2 = bus2.get("longitude", 0)
                            # Striktní GPS shoda (cca 500 metrů)
                            dist = math.hypot(lat1 - lat2, lng1 - lng2)
                            if dist < 0.01: 
                                raw_spz = bus2.get("spz", "").strip()
                                if raw_spz:
                                    cached["spz"] = raw_spz
                                    cached["estimated"] = False
                                    cached["state"] = "normal"
                                    found_in_arriva = True
                                    break

                # LOGIKA PRO ZMIZENÍ Z ARRIVY (Dojetí linky / Změna)
                if not is_train and not found_in_arriva and cached["spz"]:
                    if cached["line"] != line:
                        # Změnil linku na Inflow, ale z Arrivy zmizel -> Odhadovaná SPZ
                        cached["line"] = line
                        cached["estimated"] = True
                        cached["state"] = "normal"
                    else:
                        # Stejná linka, ale zmizel z Arrivy -> Asi dojel, fialová barva
                        cached["state"] = "finished"

                new_live_data.append({
                    "id": bus_id,
                    "lat": lat1,
                    "lng": lng1,
                    "line": line if line else ("Vlak" if is_train else "Neznámá"),
                    "delay": bus1.get("delay"),
                    "destination": bus1.get("finalStopName"),
                    "spz": cached["spz"] or "Neznámá",
                    "is_train": is_train,
                    "inactive_minutes": inactive_minutes,
                    "last_updated": "N/A" if not cached["last_moved"] else cached["last_moved"].strftime("%H:%M:%S"),
                    "state": cached["state"],
                    "estimated_spz": cached["estimated"]
                })

        # Smazat z paměti autobusy, co zmizely úplně odevšad
        keys_to_remove = [k for k in GLOBAL_BUS_CACHE.keys() if k not in current_bus_ids]
        for k in keys_to_remove:
            del GLOBAL_BUS_CACHE[k]

        global LIVE_BUSES_DATA
        LIVE_BUSES_DATA = new_live_data
        
        # Mapa se aktualizuje každých 10 sekund
        time.sleep(10)

def start_map_background_task():
    t = threading.Thread(target=background_map_worker, daemon=True)
    t.start()

# --- FLASK ENDPOINTY ---
@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({"status": "success", "buses": LIVE_BUSES_DATA})

@mapa_bp.route('/api/timetable/<bus_id>')
def api_timetable(bus_id):
    url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            html = r.read().decode('utf-8')
            
            # Injekce Dark Mode CSS přímo do HTML od Inflow
            dark_theme_css = """
            <style>
                body, table, div, span, td, th { background-color: #0f172a !important; color: #e2e8f0 !important; font-family: sans-serif; }
                th { color: #38bdf8 !important; border-bottom: 2px solid #334155 !important; }
                td { border-bottom: 1px solid #1e293b !important; }
                .table.is-striped tbody tr:nth-child(even) { background-color: #1e293b !important; }
                .table.is-striped tbody tr:nth-child(odd) { background-color: #0f172a !important; }
                .button { background-color: #38bdf8 !important; color: #0f172a !important; border: none !important; border-radius: 5px; font-weight: bold;}
                .button:hover { background-color: #0284c7 !important; }
                .level-item span { color: #38bdf8 !important; font-weight: bold; }
            </style>
            """
            
            # Vložíme naše styly hned na začátek
            html = dark_theme_css + html
            return Response(html, mimetype='text/html')
    except Exception as e:
        return f"<div style='padding:20px;color:#ef4444;background:#0f172a;'>Nelze načíst jízdní řád. ({e})</div>"
