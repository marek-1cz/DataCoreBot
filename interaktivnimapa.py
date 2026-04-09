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

# Globální paměť běžící 24/7
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
            # OPRAVA 400: Přesně ten původní, nezkrácený payload!
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle\n    delay\n    destinationName\n    lastStopName\n    latitude\n    longitude\n    linkNumber\n    state\n    type\n    mainType\n    spz\n    updated\n    linkNumberAlias\n    __typename\n  }\n}"
            }
            req2 = urllib.request.Request(url_arriva, data=json.dumps(arriva_payload).encode('utf-8'),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/'
                }, method='POST')
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and len(resp2) > 0 and "data" in resp2[0]:
                    data_arriva = resp2[0]["data"].get("busesCurrentLocations", [])
                elif isinstance(resp2, dict) and "data" in resp2:
                    data_arriva = resp2["data"].get("busesCurrentLocations", [])
        except Exception as e: print(f"[MAPA] Arriva Error: {e}")

        current_bus_ids = set()
        assigned_spzs = set() # Registr zabraných SPZ pro zamezení duplikací
        new_live_data = []

        if isinstance(data_inflow, list):
            # 1. PRŮCHOD: Registrace již zamknutých SPZ z minula
            for bus_id, cached in GLOBAL_BUS_CACHE.items():
                if cached.get("spz") and cached.get("spz_locked"):
                    assigned_spzs.add(cached["spz"])

            # 2. PRŮCHOD: Zpracování a párování
            for bus1 in data_inflow:
                try:
                    bus_id = str(bus1.get("id", "0"))
                    line = str(bus1.get("text", "")).strip()
                    lat1 = bus1.get("lat", 0)
                    lng1 = bus1.get("lng", 0)
                    delay = bus1.get("delay", 0)
                    # Přesné zachování velikosti písmen! Žádné .title()
                    dest1_original = str(bus1.get("finalStopName", "")).strip() 
                    dest1_lower = dest1_original.lower()
                    traction = str(bus1.get("traction", "BUS")).upper()
                    
                    is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]
                    current_bus_ids.add(bus_id)

                    # INICIALIZACE DO PAMĚTI
                    if bus_id not in GLOBAL_BUS_CACHE:
                        GLOBAL_BUS_CACHE[bus_id] = {
                            "lat": lat1, "lng": lng1, "line": line, "spz": None,
                            "last_moved": None, "first_seen": now, "status": "N/A - Čeká na pohyb", 
                            "spz_locked": False, "color_class": "bg-gray", "destination": dest1_original, "estimated": False
                        }
                    
                    cached = GLOBAL_BUS_CACHE[bus_id]
                    
                    # DETEKCE POHYBU (Tolerance cca 10 metrů)
                    dist_moved = math.hypot(lat1 - cached["lat"], lng1 - cached["lng"])
                    line_changed = cached["line"] != line

                    if line_changed and dist_moved < 0.005: 
                        # Změnil linku, ale nepohnul se -> Držíme ho
                        cached["line"] = line
                        cached["destination"] = dest1_original
                        cached["estimated"] = True
                        cached["last_moved"] = now
                    elif dist_moved > 0.0001:
                        cached["last_moved"] = now
                        cached["lat"] = lat1
                        cached["lng"] = lng1

                    time_ref = cached["last_moved"] if cached["last_moved"] else cached["first_seen"]
                    inactive_mins = (now - time_ref).total_seconds() / 60.0

                    # PÁROVÁNÍ SPZ Z ARRIVY (PŘÍSNÁ KONTROLA DUPLICIT)
                    found_in_arriva = False
                    if not is_train and not cached["spz_locked"]:
                        best_spz = None
                        for bus2 in data_arriva:
                            b2_spz = str(bus2.get("spz", "")).strip()
                            if not b2_spz or b2_spz == "Neznámá" or b2_spz in assigned_spzs:
                                continue # Tuhle SPZ už někdo má
                                
                            b2_line = str(bus2.get("linkNumber", "")).strip()
                            b2_alias = str(bus2.get("linkNumberAlias", "")).strip()
                            
                            if b2_line == line or b2_alias == line:
                                lat2 = bus2.get("latitude", 0)
                                lng2 = bus2.get("longitude", 0)
                                dest2 = str(bus2.get("destinationName", "")).strip().lower()
                                dist = math.hypot(lat1 - lat2, lng1 - lng2)
                                
                                if dist < 0.015: # Do cca 1.5 km
                                    if (dest1_lower in dest2) or (dest2 in dest1_lower) or dest1_lower == "" or dest2 == "":
                                        best_spz = b2_spz
                                        found_in_arriva = True
                                        break
                                    elif dist < 0.001: # Extrémně blízko, ignorujeme cíl
                                        best_spz = b2_spz
                                        found_in_arriva = True
                                        break
                        
                        if best_spz:
                            cached["spz"] = best_spz
                            cached["spz_locked"] = True
                            cached["estimated"] = False
                            assigned_spzs.add(best_spz) # Zamknout ihned pro ostatní iterace
                    
                    # Ověření pro fialovou (jestli zmizel z Arrivy)
                    if not is_train and cached["spz"]:
                        for b2 in data_arriva:
                            if b2.get("spz", "").strip() == cached["spz"]:
                                found_in_arriva = True
                                break

                    # STATUSY A BARVY
                    # Nejvyšší priorita: Čeká na odjezd (i když stojí >10min, ale odjezd je za <= 30 min)
                    if delay <= -100000 or (-1800 <= delay < -60):
                        cached["status"] = "Začátek linky (Čeká)"
                        cached["color_class"] = "bg-blue"
                    
                    # Jinak kontrolujeme standardní věci
                    elif cached["last_moved"]:
                        if inactive_mins > 10:
                            cached["status"] = "Odstaven"
                            cached["color_class"] = "bg-gray"
                            # SPZ ZŮSTÁVÁ!
                            
                        elif not is_train and cached["spz"] and not found_in_arriva and delay < -300:
                            # Má naši SPZ, z Inflow hlásí masivní mínus, na Arrivě zmizel -> Konec
                            cached["status"] = "Konečná zastávka"
                            cached["color_class"] = "bg-purple"
                            
                        else:
                            if dist_moved > 0.0001: # V Jízdě
                                if delay < -60: 
                                    cached["status"] = "Jízda (Náskok)"
                                    cached["color_class"] = "bg-darkblue"
                                else:
                                    cached["status"] = "Jízda"
                                    cached["color_class"] = "bg-red" if delay >= 300 else "bg-green"
                            else: # Stojí
                                cached["status"] = "Stojí"
                                cached["color_class"] = "bg-red"
                    else:
                        cached["status"] = "N/A - Čeká na pohyb"
                        cached["color_class"] = "bg-gray"

                    last_up_str = cached["last_moved"].strftime("%H:%M:%S") if cached["last_moved"] else "N/A"

                    new_live_data.append({
                        "id": bus_id, "lat": lat1, "lng": lng1, 
                        "line": line if line else ("Vlak" if is_train else "Neznámá"),
                        "delay": delay, "destination": dest1_original, 
                        "spz": cached["spz"] or "Neznámá", "is_train": is_train, 
                        "status": cached["status"], "color_class": cached["color_class"],
                        "inactive_minutes": inactive_mins, "last_updated": last_up_str,
                        "estimated_spz": cached["estimated"]
                    })
                except: continue

        # Vyčištění mrtvých záznamů
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
        info_html = ""
        req1 = urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req1, timeout=5) as r1:
            info_html = r1.read().decode('utf-8')
            
        tt_html = ""
        req2 = urllib.request.Request(url_tt, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=5) as r2:
            tt_html = r2.read().decode('utf-8')

        linkospoj = "N/A"
        spoj_num = "N/A"

        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_linka: linkospoj = m_linka.group(1).strip()
        
        m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_spoj: spoj_num = m_spoj.group(1).strip()

        tables = re.findall(r'(<table[^>]*>.*?</table>)', tt_html, re.IGNORECASE | re.DOTALL)
        tt_table_only = "".join(tables) if tables else "<p style='color:#ef4444;text-align:center;padding:10px;'>Jízdní řád není momentálně k dispozici.</p>"

        # Odstraněny zbytečné N/A kolonky, zůstalo čisté JŘ
        custom_html = f"""
        <style>
            .ois-detail {{ background: #0f172a; color: white; font-family: sans-serif; padding: 15px; border-radius: 8px; }}
            .ois-header {{ color: #38bdf8; font-weight: bold; border-bottom: 1px solid #334155; margin-bottom: 15px; padding-bottom: 10px; font-size: 18px; }}
            .ois-table-wrapper {{ margin-top: 10px; border: 1px solid #4b5563; border-radius: 5px; overflow-x: auto; background: #374151; }}
            .ois-table-wrapper table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #f8fafc; margin-bottom: 0; }}
            .ois-table-wrapper th {{ background: #1f2937; color: #38bdf8; text-align: left; padding: 10px; border-bottom: 2px solid #374151; white-space: nowrap; }}
            .ois-table-wrapper td {{ padding: 10px; border-bottom: 1px solid #4b5563; white-space: nowrap; }}
            .ois-table-wrapper tr:nth-child(even) td {{ background-color: #374151; }}
            .ois-table-wrapper tr:nth-child(odd) td {{ background-color: #4b5563; }}
            .ois-table-wrapper tr:hover td {{ background-color: #6b7280; transition: 0.2s; }}
        </style>
        <div class="ois-detail">
            <div class="ois-header"><i class="fas fa-bus"></i> Spoj: {linkospoj} / {spoj_num}</div>
            <div class="ois-table-wrapper">
                {tt_table_only}
            </div>
        </div>
        """
        return Response(custom_html, mimetype='text/html')
    except Exception as e:
        return f"<div style='color:#ef4444; padding:20px; background:#0f172a;'>Chyba při stahování JŘ z Inflow: {e}</div>"
