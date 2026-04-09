import time
import json
import urllib.request
import threading
from datetime import datetime
from flask import Blueprint, jsonify, Response
from zoneinfo import ZoneInfo
import math
import re

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
                dest1 = str(bus1.get("finalStopName", "")).strip().lower()
                
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

                # HLEDÁNÍ SPZ V ARRIVĚ
                found_in_arriva = False
                if not is_train and data_arriva:
                    for bus2 in data_arriva:
                        # Odstraněn filtr na region! Nyní hledá všude.
                        b2_line = str(bus2.get("linkNumber", "")).strip()
                        b2_alias = str(bus2.get("linkNumberAlias", "")).strip()
                        
                        if b2_line == line or b2_alias == line:
                            lat2 = bus2.get("latitude", 0)
                            lng2 = bus2.get("longitude", 0)
                            dest2 = str(bus2.get("destinationName", "")).strip().lower()
                            
                            # Vzdálenost v GPS (0.02 je zhruba 2 kilometry)
                            dist = math.hypot(lat1 - lat2, lng1 - lng2)
                            
                            # Pokud je bus extrémně blízko (< 1km) NEBO sedí cíl cesty (dest1 v dest2)
                            if dist < 0.015 or (dist < 0.05 and (dest1 in dest2 or dest2 in dest1)):
                                raw_spz = bus2.get("spz", "").strip()
                                if raw_spz:
                                    cached["spz"] = raw_spz
                                    cached["estimated"] = False
                                    cached["state"] = "normal"
                                    found_in_arriva = True
                                    break

                # LOGIKA FIALOVÝCH DUCHŮ (Zmizení z Arrivy)
                if not is_train and not found_in_arriva and cached["spz"]:
                    if cached["line"] != line:
                        # Přejel na jinou linku na Inflow, z Arrivy zmizel -> Necháme SPZ, ale dáme "Odhadovaná"
                        cached["line"] = line
                        cached["estimated"] = True
                        cached["state"] = "normal"
                    else:
                        # Je na stejné lince, ale zmizel z Arrivy (pravděpodobně dojel na konečnou) -> Fialová
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

        # Odstranit smazané autobusy
        keys_to_remove = [k for k in GLOBAL_BUS_CACHE.keys() if k not in current_bus_ids]
        for k in keys_to_remove:
            del GLOBAL_BUS_CACHE[k]

        global LIVE_BUSES_DATA
        LIVE_BUSES_DATA = new_live_data
        
        time.sleep(10)

def start_map_background_task():
    t = threading.Thread(target=background_map_worker, daemon=True)
    t.start()

# --- FLASK ENDPOINTY ---
@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({"status": "success", "buses": LIVE_BUSES_DATA})

@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    # Tento endpoint stáhne a zkombinuje obě HTML data (Okno s infem i Tabulku s JŘ)
    url_info = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}"
    url_tt = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0"
    
    html_output = ""
    
    # 1. Stáhnout Základní Info (Spoj, Aktuální zastávka)
    try:
        req1 = urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req1, timeout=3) as r1:
            info_raw = r1.read().decode('utf-8')
            # Vyčistíme to od nepotřebného HTML balastu kolem (vezmeme jen tabulku)
            match = re.search(r'(<table.*?>.*?</table>)', info_raw, re.DOTALL | re.IGNORECASE)
            if match:
                html_output += f"<div style='margin-bottom: 20px;'>{match.group(1)}</div>"
    except Exception as e:
        pass
        
    # 2. Stáhnout Jízdní řád
    try:
        req2 = urllib.request.Request(url_tt, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=3) as r2:
            tt_raw = r2.read().decode('utf-8')
            html_output += tt_raw
    except Exception as e:
        html_output += f"<p style='color:#ef4444;'>Jízdní řád nelze načíst.</p>"

    # 3. Zabalit do luxusního temného designu
    dark_theme_css = """
    <style>
        /* Styl pro kontejner obsahu */
        #timetable-content { background-color: #0f172a; color: #e2e8f0; font-family: sans-serif; }
        
        /* Styly pro všechny tabulky */
        #timetable-content table { background-color: transparent !important; width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        #timetable-content th { color: #38bdf8 !important; border-bottom: 2px solid #334155 !important; text-align: left; padding: 10px; }
        #timetable-content td { border-bottom: 1px solid #1e293b !important; padding: 10px; color: #e2e8f0 !important; }
        #timetable-content tbody tr:nth-child(even) td { background-color: #1e293b !important; }
        #timetable-content tbody tr:nth-child(odd) td { background-color: #0f172a !important; }
        
        /* Tlačítka a navigace uvnitř infowindow */
        #timetable-content .button { background-color: #38bdf8 !important; color: #0f172a !important; border: none !important; border-radius: 5px; font-weight: bold; cursor: pointer; margin-top: 5px;}
        #timetable-content .button:hover { background-color: #0284c7 !important; }
        #timetable-content .level-item span { color: #38bdf8 !important; font-weight: bold; }
        #timetable-content nav { margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
        
        /* Úprava první tabulky (Základní info) aby vypadala jako štítky */
        #timetable-content div > table:first-child th { width: 40%; color: #94a3b8 !important; border: none !important; }
        #timetable-content div > table:first-child td { font-weight: bold; border: none !important; }
    </style>
    """
    
    return Response(dark_theme_css + html_output, mimetype='text/html')
