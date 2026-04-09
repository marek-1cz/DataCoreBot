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
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle\n    delay\n    destinationName\n    lastStopName\n    latitude\n    longitude\n    linkNumber\n    state\n    type\n    mainType\n    spz\n    updated\n    linkNumberAlias\n    __typename\n  }\n}"
            }
            req2 = urllib.request.Request(
                url_arriva, 
                data=json.dumps(arriva_payload).encode('utf-8'),
                headers={'User-Agent': 'Mozilla/5.0','Content-Type': 'application/json','Origin': 'https://www.arriva.cz','Referer': 'https://www.arriva.cz/'}, 
                method='POST'
            )
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and len(resp2) > 0 and "data" in resp2[0]:
                    data_arriva = resp2[0]["data"].get("busesCurrentLocations", [])
                elif isinstance(resp2, dict) and "data" in resp2:
                    data_arriva = resp2["data"].get("busesCurrentLocations", [])
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
                    delay = bus1.get("delay", 0)
                    dest1 = str(bus1.get("finalStopName", "")).strip()
                    traction = str(bus1.get("traction", "BUS")).upper()
                    
                    is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]
                    current_bus_ids.add(bus_id)

                    if bus_id not in GLOBAL_BUS_CACHE:
                        GLOBAL_BUS_CACHE[bus_id] = {
                            "lat": lat1, "lng": lng1, "line": line, "spz": None,
                            "last_moved": now, "first_seen": now, "status": "N/A"
                        }
                    
                    cached = GLOBAL_BUS_CACHE[bus_id]
                    
                    # Detekce pohybu
                    dist_moved = math.hypot(lat1 - cached["lat"], lng1 - cached["lng"])
                    if dist_moved > 0.0001:
                        cached["last_moved"] = now
                        cached["lat"] = lat1
                        cached["lng"] = lng1

                    inactive_mins = (now - cached["last_moved"]).total_seconds() / 60.0

                    # Status Logika komunikující s JŘ
                    if is_train:
                        cached["status"] = "Jízda" if dist_moved > 0.0001 else "Stojí"
                    else:
                        if delay <= -100000:
                            cached["status"] = "Čeká na spoj"
                        elif delay < -180: # Náskok větší jak 3 minuty = čeká na odjezd
                            cached["status"] = "Začátek linky (Čeká)"
                        elif dist_moved > 0.0001:
                            cached["status"] = "Jízda"
                        else:
                            cached["status"] = "Stojí"

                    # Aktualizace SPZ (pouze pro autobusy)
                    if not is_train and data_arriva:
                        for bus2 in data_arriva:
                            b2_line = str(bus2.get("linkNumber", "")).strip()
                            b2_alias = str(bus2.get("linkNumberAlias", "")).strip()
                            
                            if b2_line == line or b2_alias == line:
                                lat2 = bus2.get("latitude", 0)
                                lng2 = bus2.get("longitude", 0)
                                
                                dist = math.hypot(lat1 - lat2, lng1 - lng2)
                                # Spárování - pokud je poblíž, PŘEPÍŠE / DOPLNÍ SPZ
                                if dist < 0.015:
                                    raw_spz = bus2.get("spz", "").strip()
                                    if raw_spz:
                                        cached["spz"] = raw_spz
                                        break

                    # Zde SPZ nikdy nemažeme. I když bus zmizí z Arrivy nebo stojí hodinu, drží si poslední SPZ.
                    
                    new_live_data.append({
                        "id": bus_id, 
                        "lat": lat1, 
                        "lng": lng1, 
                        "line": line if line else ("Vlak" if is_train else "Neznámá"),
                        "delay": delay, 
                        "destination": dest1, 
                        "spz": cached["spz"] or "Neznámá",
                        "is_train": is_train, 
                        "status": cached["status"],
                        "inactive_minutes": inactive_mins,
                        "last_updated": cached["last_moved"].strftime("%H:%M:%S") if cached["last_moved"] else "N/A"
                    })
                except: continue

        # Čištění pouze u autobusů, které kompletně zmizely z Inflow mapy
        keys_to_remove = [k for k in GLOBAL_BUS_CACHE.keys() if k not in current_bus_ids]
        for k in keys_to_remove: 
            del GLOBAL_BUS_CACHE[k]

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
        # 1. Stažení okna s infem (Linka, Spoj, Zastávka, Zpoždění)
        info_html = ""
        req1 = urllib.request.Request(url_info, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req1, timeout=5) as r1:
            info_html = r1.read().decode('utf-8')
            
        # 2. Stažení samotné tabulky Jízdního řádu
        tt_html = ""
        req2 = urllib.request.Request(url_tt, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=5) as r2:
            tt_html = r2.read().decode('utf-8')

        # BEZPEČNÁ EXTRAKCE DAT (Abychom nerozbili modal cizím kódem)
        linkospoj = "N/A"
        spoj_num = "N/A"
        zastavka = "N/A"
        zpozdeni_str = "N/A"

        # Hledáme hodnoty pomocí regexu přímo z tabulky
        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_linka: linkospoj = m_linka.group(1).strip()
        
        m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_spoj: spoj_num = m_spoj.group(1).strip()
        
        m_zastavka = re.search(r'<th>Zast\u00e1vka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if not m_zastavka: m_zastavka = re.search(r'<th>Zastávka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_zastavka: zastavka = m_zastavka.group(1).strip()

        m_zpozdeni = re.search(r'<th>Zpo\u017ed\u011bn\u00ed</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if not m_zpozdeni: m_zpozdeni = re.search(r'<th>Zpoždění</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_zpozdeni: zpozdeni_str = m_zpozdeni.group(1).strip()

        # Vyříznutí pouze HTML tabulky jízdního řádu (zahodíme tlačítka a skripty Inflow)
        tt_table_only = ""
        m_table = re.search(r'(<table[^>]*>.*?</table>)', tt_html, re.IGNORECASE | re.DOTALL)
        if m_table:
            tt_table_only = m_table.group(1)
        else:
            tt_table_only = "<p style='color:#ef4444;'>Jízdní řád není k dispozici.</p>"

        # Poskládání vlastního čistého HTML
        custom_html = f"""
        <style>
            .ois-detail {{ background: #0f172a; color: white; font-family: sans-serif; }}
            .ois-header {{ color: #38bdf8; font-weight: bold; border-bottom: 1px solid #334155; margin-bottom: 15px; padding-bottom: 10px; font-size: 18px; }}
            .ois-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; background: #1e293b; padding: 10px; border-radius: 5px; }}
            .ois-label {{ color: #94a3b8; }}
            .ois-val {{ font-weight: bold; color: #f8fafc; }}
            .ois-delay {{ color: #fbbf24; }}
            .ois-table-wrapper {{ margin-top: 20px; border: 1px solid #334155; border-radius: 5px; overflow-x: auto; background: #0f172a; }}
            .ois-table-wrapper table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #e2e8f0; }}
            .ois-table-wrapper th {{ background: #1e293b; color: #38bdf8; text-align: left; padding: 10px; border-bottom: 2px solid #334155; }}
            .ois-table-wrapper td {{ padding: 10px; border-bottom: 1px solid #1e293b; }}
            .ois-table-wrapper tr:nth-child(even) td {{ background-color: #1e293b; }}
        </style>
        <div class="ois-detail">
            <div class="ois-header">Spoj: {linkospoj} / {spoj_num}</div>
            <div class="ois-row"><span class="ois-label">Aktuální zastávka:</span><span class="ois-val">{zastavka}</span></div>
            <div class="ois-row"><span class="ois-label">Hlášené zpoždění:</span><span class="ois-val ois-delay">{zpozdeni_str}</span></div>
            <div class="ois-table-wrapper">
                {tt_table_only}
            </div>
        </div>
        """
        return Response(custom_html, mimetype='text/html')
    except Exception as e:
        return f"<div style='color:#ef4444; padding:20px;'>Chyba při komunikaci se serverem: {e}</div>"
