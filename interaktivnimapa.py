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

# Globální paměť běžící 24/7 (pamatuje si busy až 12 hodin po odpojení)
GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA = []

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

def calc_mins_to_departure(dep_time_str, current_time):
    try:
        dh, dm = map(int, dep_time_str.split(':'))
        ch, cm = current_time.hour, current_time.minute
        dep_total = dh * 60 + dm
        cur_total = ch * 60 + cm
        diff = dep_total - cur_total
        if diff < -720: # Přes půlnoc (např. teď je 23:50, odjezd 00:10 -> diff = 10 - 1430 = -1420)
            diff += 1440
        return diff
    except:
        return None

def background_map_worker():
    print("[MAPA] Inteligentní mozek s 12h pamětí a JŘ analyzátorem startuje...", flush=True)
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
            req2 = urllib.request.Request(url_arriva, data=json.dumps(arriva_payload).encode('utf-8'),
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/'
                }, method='POST')
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                data_arriva = resp2.get("data", {}).get("busesCurrentLocations", []) if isinstance(resp2, dict) else (resp2[0].get("data", {}).get("busesCurrentLocations", []) if isinstance(resp2, list) else [])
        except Exception as e: print(f"[MAPA] Arriva Error: {e}")

        current_inflow_ids = set()
        assigned_spzs = set()
        
        # 1. Zabezpečení přidělených SPZ z minula
        for bus_id, cached in GLOBAL_BUS_CACHE.items():
            if cached.get("spz") and cached.get("spz_locked"):
                assigned_spzs.add(cached["spz"])

        # 2. Načtení čerstvých dat z Inflow
        if isinstance(data_inflow, list):
            for bus1 in data_inflow:
                try:
                    bus_id = str(bus1.get("id", "0"))
                    current_inflow_ids.add(bus_id)
                    
                    line = str(bus1.get("text", "")).strip()
                    lat1 = bus1.get("lat", 0)
                    lng1 = bus1.get("lng", 0)
                    delay = int(bus1.get("delay", 0)) if bus1.get("delay") is not None else 0
                    dest1_original = str(bus1.get("finalStopName", "")).strip()
                    traction = str(bus1.get("traction", "BUS")).upper()
                    is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]

                    if bus_id not in GLOBAL_BUS_CACHE:
                        GLOBAL_BUS_CACHE[bus_id] = {
                            "id": bus_id, "lat": lat1, "lng": lng1, "line": line, "spz": None,
                            "last_moved": None, "first_seen": now, "last_seen": now,
                            "status": "N/A - Čeká na pohyb", "spz_locked": False, 
                            "color_class": "bg-gray", "destination": dest1_original, 
                            "estimated": False, "finished_at": None, "is_train": is_train,
                            "raw_delay": delay, "first_dep_time": None, "tt_last_fetch": None,
                            "is_offline": False
                        }
                    else:
                        c = GLOBAL_BUS_CACHE[bus_id]
                        c["last_seen"] = now
                        c["is_offline"] = False
                        c["raw_delay"] = delay
                        c["is_train"] = is_train
                        
                        dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])
                        if c["line"] != line:
                            c["line"] = line
                            c["destination"] = dest1_original
                            c["finished_at"] = None
                            c["first_dep_time"] = None # Změnil linku, musíme fetchovat nový JŘ
                            if dist_moved < 0.005: 
                                c["estimated"] = True
                                c["last_moved"] = now
                        
                        if dist_moved > 0.0001:
                            c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                except: continue

        # 3. Zpracování celé naší paměti (i těch, co vypnuli kasu a z Inflow zmizeli)
        new_live_data = []
        tt_fetches_this_tick = 0 # Ochrana proti DDoS na Inflow

        for bus_id, cached in list(GLOBAL_BUS_CACHE.items()):
            # A) Je autobus offline? (Zmizel z Inflow)
            if bus_id not in current_inflow_ids:
                offline_mins = (now - cached["last_seen"]).total_seconds() / 60.0
                if offline_mins > 720: # Paměť na 12 hodin! Poté ho konečně smažeme.
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                else:
                    cached["is_offline"] = True
                    cached["status"] = "Odstaven (Bez signálu)"
                    cached["color_class"] = "bg-gray"
                    # Necháme mu zamčenou SPZ, ať ji neztratíme!
            else:
                # B) Autobus je online. Uděláme veškerou logiku.
                lat1, lng1 = cached["lat"], cached["lng"]
                line, dest1_original = cached["line"], cached["destination"]
                dest1_lower = dest1_original.lower()
                is_train = cached["is_train"]
                
                time_ref = cached["last_moved"] if cached["last_moved"] else cached["first_seen"]
                inactive_mins = (now - time_ref).total_seconds() / 60.0
                is_moving = inactive_mins < 1 # Pohnul se v poslední minutě
                
                delay_val = cached["raw_delay"]

                # PÁROVÁNÍ SPZ (Pouze pokud ještě nemá)
                found_in_arriva = False
                if not is_train and not cached["spz_locked"]:
                    best_spz = None
                    for bus2 in data_arriva:
                        b2_spz = str(bus2.get("spz", "")).strip()
                        if not b2_spz or b2_spz == "Neznámá" or b2_spz in assigned_spzs: continue 
                            
                        if str(bus2.get("linkNumber", "")).strip() == line or str(bus2.get("linkNumberAlias", "")).strip() == line:
                            lat2, lng2 = bus2.get("latitude", 0), bus2.get("longitude", 0)
                            dest2 = str(bus2.get("destinationName", "")).strip().lower()
                            dist = math.hypot(lat1 - lat2, lng1 - lng2)
                            
                            if dist < 0.015: 
                                if (dest1_lower in dest2) or (dest2 in dest1_lower) or dest1_lower == "" or dest2 == "":
                                    best_spz = b2_spz
                                    found_in_arriva = True
                                    break
                                elif dist < 0.001: 
                                    best_spz = b2_spz
                                    found_in_arriva = True
                                    break
                    if best_spz:
                        cached["spz"] = best_spz
                        cached["spz_locked"] = True
                        cached["estimated"] = False
                        assigned_spzs.add(best_spz) 
                
                if not is_train and cached["spz"]:
                    for b2 in data_arriva:
                        if b2.get("spz", "").strip() == cached["spz"]:
                            found_in_arriva = True
                            break

                # TAJNÝ STAHUVAČ JÍZDNÍHO ŘÁDU (Oprava Inflow lži "delay: 0")
                if not is_train and delay_val == 0 and not is_moving and inactive_mins < 120:
                    # Pokud Inflow lže a my nemáme JŘ stáhnutý v posledních 10 minutách, jdeme pro něj!
                    if not cached.get("tt_last_fetch") or (now - cached["tt_last_fetch"]).total_seconds() > 600:
                        if tt_fetches_this_tick < 3: # Max 3 JŘ za každých 10 sekund (ochrana proti BANu)
                            tt_fetches_this_tick += 1
                            cached["tt_last_fetch"] = now
                            try:
                                tt_url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0"
                                req_tt = urllib.request.Request(tt_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req_tt, timeout=2) as r_tt:
                                    tt_html = r_tt.read().decode('utf-8')
                                    times = re.findall(r'\b\d{2}:\d{2}\b', tt_html)
                                    if times: cached["first_dep_time"] = times[0]
                            except: pass

                # PŘEPIS ZPOŽDĚNÍ POMOCÍ TAJNÉHO JŘ
                if cached.get("first_dep_time") and not is_moving:
                    diff = calc_mins_to_departure(cached["first_dep_time"], now)
                    if diff is not None and 0 < diff <= 240:
                        delay_val = -diff # Násilně přepíšeme 0 na mínusové minuty!

                # LOGIKA BAREV A STATUSŮ
                is_buggy_terminus = (delay_val <= -10000)
                is_waiting_departure = (-240 <= delay_val < 0)

                if is_waiting_departure: cached["finished_at"] = None

                is_missing_arriva_terminus = (not is_train and cached["spz"] and not found_in_arriva and delay_val < -2 and not is_waiting_departure)

                if is_buggy_terminus or is_missing_arriva_terminus:
                    if cached["finished_at"] is None: cached["finished_at"] = now
                elif found_in_arriva and delay_val >= -2:
                    cached["finished_at"] = None

                if not cached["last_moved"]:
                    cached["status"] = "N/A - Čeká na pohyb"
                    cached["color_class"] = "bg-gray"
                else:
                    if is_waiting_departure:
                        if is_moving:
                            cached["status"] = "Jízda (Náskok)"
                            cached["color_class"] = "bg-darkblue"
                        else:
                            cached["status"] = "Začátek linky (Čeká)"
                            cached["color_class"] = "bg-blue"
                            
                    elif inactive_mins > 10 and not is_waiting_departure:
                        cached["status"] = "Odstaven"
                        cached["color_class"] = "bg-gray"
                        
                    elif cached["finished_at"] is not None:
                        finished_mins = (now - cached["finished_at"]).total_seconds() / 60.0
                        if finished_mins > 20: 
                            if is_moving:
                                cached["status"] = "Manipulační jízda"
                                cached["color_class"] = "bg-yellow"
                            else:
                                cached["status"] = "Odstaven"
                                cached["color_class"] = "bg-gray"
                        else:
                            cached["status"] = "Konečná zastávka"
                            cached["color_class"] = "bg-purple"
                            
                    elif delay_val < -240 and not is_buggy_terminus:
                        cached["status"] = "Čeká na spoj (>4h)"
                        cached["color_class"] = "bg-gray"
                        
                    else:
                        if is_moving: cached["status"] = "Jízda"
                        else: cached["status"] = "Stojí"
                        cached["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                # Posíláme upravený delay_val ven na frontend
                cached["final_delay_display"] = delay_val

            # ODESLÁNÍ DO FRONTENDU (Pro oba stavy - Online i Offline)
            last_up_str = cached["last_moved"].strftime("%H:%M:%S") if cached["last_moved"] else "N/A"
            new_live_data.append({
                "id": bus_id, "lat": cached["lat"], "lng": cached["lng"], 
                "line": cached["line"] if cached["line"] else ("Vlak" if cached["is_train"] else "Neznámá"),
                "delay": cached.get("final_delay_display", 0), "destination": cached["destination"], 
                "spz": cached["spz"] or "Neznámá", "is_train": cached["is_train"], 
                "status": cached["status"], "color_class": cached["color_class"],
                "inactive_minutes": inactive_mins if not cached.get("is_offline") else 999, 
                "last_updated": last_up_str, "estimated_spz": cached["estimated"]
            })

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
        with urllib.request.urlopen(req1, timeout=5) as r1: info_html = r1.read().decode('utf-8')
            
        tt_html = ""
        req2 = urllib.request.Request(url_tt, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=5) as r2: tt_html = r2.read().decode('utf-8')

        linkospoj, spoj_num = "N/A", "N/A"

        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_linka: linkospoj = m_linka.group(1).strip()
        m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_spoj: spoj_num = m_spoj.group(1).strip()

        tables = re.findall(r'(<table[^>]*>.*?</table>)', tt_html, re.IGNORECASE | re.DOTALL)
        tt_table_only = "".join(tables) if tables else "<p style='color:#ef4444;text-align:center;padding:10px;'>Jízdní řád není momentálně k dispozici.</p>"

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
