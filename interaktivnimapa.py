import os
import time
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, Response, render_template_string
from zoneinfo import ZoneInfo
import math
import re
import http.cookiejar
from supabase import create_client

mapa_bp = Blueprint('mapa_bp', __name__)

# --- HTML ŠABLONA PRO STRÁNKU HISTORIE ---
HTML_HISTORIE = """
<div style="padding: 20px; max-width: 1200px; margin: auto; font-family: sans-serif;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 24px;"><i class="fas fa-history"></i> Historie Spojů (Černá skříňka)</h2>
        <div class="field" style="margin-bottom: 0;">
          <p class="control has-icons-left">
            <input class="input" id="historySearch" type="text" placeholder="Hledat SPZ nebo Linku..." style="background: #1e293b; color: white; border-color: #334155; min-width: 250px;">
            <span class="icon is-small is-left" style="color: #94a3b8;">
              <i class="fas fa-search"></i>
            </span>
          </p>
        </div>
    </div>

    <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <table class="table is-fullwidth is-hoverable" style="background: transparent; color: #cbd5e1; margin-bottom: 0; min-width: 800px;">
            <thead>
                <tr style="background: #0f172a;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Čas záznamu</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">SPZ</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka/Spoj</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední cíl</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Status</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Poloha na mapě</th>
                </tr>
            </thead>
            <tbody id="historyTableBody">
                <tr><td colspan="6" style="text-align:center; padding: 30px; color: #38bdf8;"><i class="fas fa-spinner fa-spin"></i> Načítám data z databáze...</td></tr>
            </tbody>
        </table>
    </div>
    <p style="color: #94a3b8; font-size: 12px; margin-top: 10px;">* Zobrazuje posledních 200 záznamů. Data starší než 30 dní jsou automaticky promazána.</p>

    <script>
        async function loadHistory() {
            try {
                const response = await fetch('/api/history_data');
                const data = await response.json();
                const tbody = document.getElementById('historyTableBody');
                tbody.innerHTML = '';

                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px;">Žádné záznamy nebyly nalezeny (nebo chybí Supabase klíče v Koyebu).</td></tr>';
                    return;
                }

                data.forEach(row => {
                    const date = new Date(row.created_at);
                    const timeStr = date.toLocaleDateString('cs-CZ') + ' ' + date.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                    
                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${timeStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;"><span class="tag is-warning" style="background:#f59e0b; color:#0f172a; font-weight:bold;">${row.spz}</span></td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold;">${row.linka || '---'}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${row.destination || '---'}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-size: 13px;">${row.status}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="http://maps.google.com/maps?q=${row.last_lat},${row.last_lng}" target="_blank" class="button is-small is-info is-outlined" style="background: transparent; color: #38bdf8; border-color: #38bdf8; text-decoration: none;">
                                <i class="fas fa-map-marker-alt" style="margin-right: 5px;"></i> Mapa
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                
                // Znovu aplikovat filtr, pokud je něco napsané
                triggerSearch();
            } catch(e) { 
                document.getElementById('historyTableBody').innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px; color:#ef4444;">Chyba připojení k databázi.</td></tr>';
            }
        }

        function triggerSearch() {
            const val = document.getElementById('historySearch').value.toLowerCase();
            const rows = document.querySelectorAll('#historyTableBody tr');
            rows.forEach(row => {
                row.style.display = row.innerText.toLowerCase().includes(val) ? '' : 'none';
            });
        }

        document.getElementById('historySearch').addEventListener('input', triggerSearch);

        loadHistory();
        setInterval(loadHistory, 30000); 
    </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
"""

# Globální paměť běžící 24/7 (pamatuje si busy až 12 hodin po odpojení)
GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA = []

# Globální CookieJar pro maskování (Stealth Mode proti 400 Error)
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

def calc_mins_to_departure(dep_time_str, current_time):
    try:
        dh, dm = map(int, dep_time_str.split(':'))
        ch, cm = current_time.hour, current_time.minute
        dep_total = dh * 60 + dm
        cur_total = ch * 60 + cm
        diff = dep_total - cur_total
        
        if diff < -720: 
            diff += 1440
        elif diff > 720:
            diff -= 1440
            
        return diff
    except:
        return None

# Pomocná funkce pro bezpečné získání DB klienta v daném vlákně
def get_db_client():
    supa_url = os.environ.get("SUPABASE_URL")
    supa_key = os.environ.get("SUPABASE_KEY")
    if supa_url and supa_key:
        try:
            return create_client(supa_url, supa_key)
        except:
            return None
    return None

# --- NEZÁVISLÉ VLÁKNO PRO BLESKOVÉ STAŽENÍ JŘ ---
def fetch_tt_bg(bus_id, cached_dict):
    try:
        cb_time = int(time.time() * 1000)
        tt_url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://pvvd.idpk.cz/',
            'Cache-Control': 'no-cache'
        }
        req_tt = urllib.request.Request(tt_url, headers=headers)
        with opener.open(req_tt, timeout=4) as r_tt:
            tt_html = r_tt.read().decode('utf-8')
            times = re.findall(r'\b\d{2}:\d{2}\b', tt_html)
            if times:
                cached_dict["first_dep_time"] = times[0]
    except Exception:
        pass
    finally:
        cached_dict["tt_is_fetching"] = False

# --- FUNKCE PRO ZÁPIS DO HISTORIE (SUPABASE) ---
def log_to_history(db, cached_dict, status_text):
    if not db or not cached_dict.get("spz") or cached_dict["spz"] == "Neznámá":
        return
    
    try:
        now_prague = get_prague_time()
        data = {
            "spz": cached_dict["spz"],
            "linka": cached_dict.get("line", "Neznámá"),
            "destination": cached_dict.get("destination", "Neznámý cíl"),
            "last_lat": cached_dict.get("lat"),
            "last_lng": cached_dict.get("lng"),
            "status": status_text,
            "created_at": now_prague.isoformat()
        }
        db.table("bus_history").insert(data).execute()
        print(f"[MAPA-DB] Uložena historie pro {cached_dict['spz']} ({status_text})")
    except Exception as e:
        print(f"[MAPA-DB] Chyba ukládání historie: {e}")

def background_map_worker():
    print("[MAPA] Inteligentní mozek (Stealth + DB Databáze) startuje...", flush=True)
    url_inflow_base = "https://pvvd.idpk.cz/Ajax/GetPoints" 
    url_arriva = "https://www.arriva.cz/api/graphql" 
    
    inflow_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://pvvd.idpk.cz/',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    try:
        opener.open(urllib.request.Request("https://pvvd.idpk.cz/", headers={'User-Agent': 'Mozilla/5.0'}))
    except: pass

    # Připojení k Supabase
    db_client = get_db_client()
    last_db_cleanup = get_prague_time()

    while True:
        now = get_prague_time()
        
        # Samočistící rutina - 1x denně smaže data starší 30 dnů
        if db_client and (now - last_db_cleanup).total_seconds() > 86400:
            try:
                thirty_days_ago = (now - timedelta(days=30)).isoformat()
                db_client.table("bus_history").delete().lt("created_at", thirty_days_ago).execute()
                print("[MAPA-DB] Automatické pročištění historie starší 30 dnů proběhlo.")
            except Exception as e:
                pass
            last_db_cleanup = now

        data_inflow = []
        data_arriva = []
        
        url_inflow = f"{url_inflow_base}?_={int(time.time() * 1000)}"

        try:
            req1 = urllib.request.Request(url_inflow, headers=inflow_headers)
            with urllib.request.urlopen(req1, timeout=5) as r1:
                data_inflow = json.loads(r1.read().decode())
        except Exception as e: 
            try:
                req1_post = urllib.request.Request(url_inflow, data=b"{}", headers=inflow_headers, method='POST')
                with urllib.request.urlopen(req1_post, timeout=5) as r1_post:
                    data_inflow = json.loads(r1_post.read().decode())
            except Exception as ex:
                pass

        try:
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle\n    delay\n    destinationName\n    lastStopName\n    latitude\n    longitude\n    linkNumber\n    state\n    type\n    mainType\n    spz\n    updated\n    linkNumberAlias\n    __typename\n  }\n}"
            }
            req2 = urllib.request.Request(url_arriva, data=json.dumps(arriva_payload).encode('utf-8'),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Content-Type': 'application/json',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/',
                    'Cache-Control': 'no-cache'
                }, method='POST')
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and len(resp2) > 0:
                    data_arriva = resp2[0].get("data", {}).get("busesCurrentLocations", [])
                elif isinstance(resp2, dict):
                    data_arriva = resp2.get("data", {}).get("busesCurrentLocations", [])
        except Exception as e: pass

        current_inflow_ids = set()

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
                        # NOVÝ AUTOBUS! Zkusíme najít "Ducha" ze stejné GPS pozice
                        ghost_spz = None
                        ghost_locked = False
                        
                        for gid, g_cached in list(GLOBAL_BUS_CACHE.items()):
                            if g_cached.get("is_offline") and g_cached.get("spz"):
                                g_dist = math.hypot(lat1 - g_cached["lat"], lng1 - g_cached["lng"])
                                if g_dist < 0.0005: 
                                    ghost_spz = g_cached["spz"]
                                    ghost_locked = True
                                    del GLOBAL_BUS_CACHE[gid] 
                                    break

                        GLOBAL_BUS_CACHE[bus_id] = {
                            "lat": lat1, "lng": lng1, "line": line, 
                            "spz": ghost_spz, "spz_locked": ghost_locked, "estimated": bool(ghost_spz),
                            "last_moved": now, "first_seen": now, "last_seen": now,
                            "status": "Načítání...", "color_class": "bg-gray", "destination": dest1_original, 
                            "finished_at": None, "is_train": is_train,
                            "raw_delay": delay, "first_dep_time": None, "tt_last_fetch": None,
                            "tt_is_fetching": False, "is_offline": False,
                            "db_trip_logged": False, "db_offline_logged": False
                        }
                    else:
                        c = GLOBAL_BUS_CACHE[bus_id]
                        c["last_seen"] = now
                        c["is_offline"] = False
                        c["raw_delay"] = delay
                        c["is_train"] = is_train
                        
                        dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])
                        if c["line"] != line or c["destination"] != dest1_original:
                            c["line"] = line
                            c["destination"] = dest1_original
                            c["finished_at"] = None
                            c["first_dep_time"] = None 
                            c["db_trip_logged"] = False 
                            if dist_moved < 0.005: 
                                c["estimated"] = True
                                c["last_moved"] = now
                        
                        if dist_moved > 0.0001:
                            c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                except: continue

        for bus_id, cached in list(GLOBAL_BUS_CACHE.items()):
            if cached.get("spz") and cached.get("spz_locked") and not cached.get("is_train"):
                arriva_match = next((b for b in data_arriva if str(b.get("spz", "")).strip() == cached["spz"]), None)
                if arriva_match:
                    a_lat, a_lng = arriva_match.get("latitude", 0), arriva_match.get("longitude", 0)
                    dist_check = math.hypot(cached.get("lat", 0) - a_lat, cached.get("lng", 0) - a_lng)
                    if dist_check > 0.015:
                        cached["spz"] = None
                        cached["spz_locked"] = False
                        cached["estimated"] = False

        assigned_spzs = set()
        for bus_id, cached in GLOBAL_BUS_CACHE.items():
            if cached.get("spz") and cached.get("spz_locked"):
                assigned_spzs.add(cached["spz"])

        new_live_data = []
        tt_fetches_this_tick = 0 

        for bus_id, cached in list(GLOBAL_BUS_CACHE.items()):
            # A) OFFLINE BUSY (DUCHOVÉ)
            if bus_id not in current_inflow_ids:
                offline_mins = (now - cached["last_seen"]).total_seconds() / 60.0
                if offline_mins > 720: 
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                else:
                    cached["is_offline"] = True
                    # Zápis do DB
                    if not cached.get("db_offline_logged"):
                        log_to_history(db_client, cached, "Ztráta signálu / Odstaven")
                        cached["db_offline_logged"] = True

                    if offline_mins < 20:
                        cached["status"] = "Konečná / Bez dat"
                        cached["color_class"] = "bg-purple"
                    else:
                        cached["status"] = "Odstaven (Bez signálu)"
                        cached["color_class"] = "bg-gray"
                        if offline_mins > 60: cached["spz_locked"] = False
            else:
                # B) ONLINE BUSY
                lat1, lng1 = cached["lat"], cached["lng"]
                line, dest1_original = cached["line"], cached["destination"]
                dest1_lower = dest1_original.lower()
                is_train = cached["is_train"]
                
                time_ref = cached["last_moved"] if cached["last_moved"] else cached["first_seen"]
                inactive_mins = (now - time_ref).total_seconds() / 60.0
                is_moving = inactive_mins < 1 
                
                delay_val = cached["raw_delay"]

                found_in_arriva = False
                if not is_train and not cached["spz_locked"]:
                    buses_on_line = [b for b in data_arriva if str(b.get("linkNumber","")).strip() == line or str(b.get("linkNumberAlias","")).strip() == line]
                    close_buses = [b for b in buses_on_line if math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0)) < 0.015]
                    
                    best_spz = None
                    if len(close_buses) == 1:
                        best_spz = close_buses[0].get("spz", "").strip()
                        found_in_arriva = True
                    elif len(close_buses) > 1:
                        d1_clean = re.sub(r'\W+', '', dest1_lower)
                        for cb in close_buses:
                            d2_clean = re.sub(r'\W+', '', str(cb.get("destinationName", "")).lower())
                            if d1_clean in d2_clean or d2_clean in d1_clean or d1_clean == "" or d2_clean == "":
                                best_spz = cb.get("spz", "").strip()
                                found_in_arriva = True
                                break

                    if not best_spz and inactive_mins > 1:
                        ultra_close = [b for b in data_arriva if math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0)) < 0.0005]
                        valid_ultra = [b for b in ultra_close if b.get("spz", "").strip() not in assigned_spzs and b.get("spz", "").strip() != "Neznámá"]
                        if len(valid_ultra) == 1:
                            best_spz = valid_ultra[0].get("spz", "").strip()
                            found_in_arriva = True
                            cached["estimated"] = True 

                    if best_spz and best_spz != "Neznámá" and best_spz not in assigned_spzs:
                        cached["spz"] = best_spz
                        cached["spz_locked"] = True
                        assigned_spzs.add(best_spz) 
                
                if not is_train and cached["spz"]:
                    for b2 in data_arriva:
                        if b2.get("spz", "").strip() == cached["spz"]:
                            found_in_arriva = True
                            break

                needs_tt = not is_train and not cached.get("first_dep_time") and not cached.get("is_offline")
                if needs_tt and not cached.get("tt_is_fetching"):
                    if not cached.get("tt_last_fetch") or (now - cached["tt_last_fetch"]).total_seconds() > 300:
                        if tt_fetches_this_tick < 5: 
                            tt_fetches_this_tick += 1
                            cached["tt_last_fetch"] = now
                            cached["tt_is_fetching"] = True
                            threading.Thread(target=fetch_tt_bg, args=(bus_id, cached), daemon=True).start()

                is_before_departure = False
                time_to_dep = 0
                
                if cached.get("first_dep_time"):
                    diff = calc_mins_to_departure(cached["first_dep_time"], now)
                    if diff is not None and diff > 0:
                        is_before_departure = True
                        time_to_dep = diff

                is_buggy_terminus = (delay_val <= -10000)
                is_missing_arriva_terminus = (not is_train and cached["spz"] and not found_in_arriva and delay_val < -2 and not is_before_departure)

                if is_buggy_terminus or is_missing_arriva_terminus:
                    if cached["finished_at"] is None: 
                        cached["finished_at"] = now
                elif found_in_arriva and delay_val >= -2:
                    cached["finished_at"] = None

                # ROZHODOVACÍ STROM
                if is_before_departure:
                    cached["finished_at"] = None 
                    if time_to_dep <= 240:
                        cached["status"] = "Začátek linky (Čeká)"
                        cached["color_class"] = "bg-blue"
                        delay_val = -time_to_dep 
                    else: 
                        if is_moving:
                            cached["status"] = "Manipulační jízda"
                            cached["color_class"] = "bg-yellow"
                            delay_val = -time_to_dep
                        else:
                            cached["status"] = "Čeká na spoj (>4h)"
                            cached["color_class"] = "bg-gray"
                            delay_val = -time_to_dep
                            if inactive_mins > 60: cached["spz_locked"] = False
                            
                elif not cached["last_moved"]:
                    cached["status"] = "N/A - Čeká na data"
                    cached["color_class"] = "bg-gray"

                elif inactive_mins > 10:
                    cached["status"] = "Odstaven"
                    cached["color_class"] = "bg-gray"
                    if cached["finished_at"]:
                        if (now - cached["finished_at"]).total_seconds() / 60.0 > 60:
                            cached["spz_locked"] = False
                            
                elif cached["finished_at"] is not None:
                    finished_mins = (now - cached["finished_at"]).total_seconds() / 60.0
                    
                    # ZÁPIS DO DATABÁZE PŘI DOKONČENÍ LINKY
                    if finished_mins > 1 and not cached.get("db_trip_logged"):
                        log_to_history(db_client, cached, "Konečná zastávka (Dokončeno)")
                        cached["db_trip_logged"] = True

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
                        
                else:
                    if delay_val < -1: 
                        if is_moving:
                            cached["status"] = "Jízda (Náskok)"
                            cached["color_class"] = "bg-darkblue"
                        else:
                            cached["status"] = "Stojí (Vyčkává)"
                            cached["color_class"] = "bg-darkblue"
                    else: 
                        if is_moving: cached["status"] = "Jízda"
                        else: cached["status"] = "Stojí"
                        cached["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                cached["final_delay_display"] = delay_val

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

# --- API ROUTY PRO KLIENTA ---

@mapa_bp.route('/historie')
def stranka_historie():
    return render_template_string(f"""
    <!DOCTYPE html>
    <html style="background: #0f172a;">
    <head>
        <title>Historie Spojů | OIS IDPK</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="background: #0f172a; color: white;">
        {HTML_HISTORIE}
    </body>
    </html>
    """)

@mapa_bp.route('/api/history_data')
def api_history_data():
    db = get_db_client()
    if not db:
        return jsonify([])
    try:
        response = db.table("bus_history").select("*").order("created_at", desc=True).limit(200).execute()
        return jsonify(response.data)
    except:
        return jsonify([])

@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({"status": "success", "buses": LIVE_BUSES_DATA})

@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    cb = int(time.time() * 1000)
    url_info = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb}"
    url_tt = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://pvvd.idpk.cz/',
        'Cache-Control': 'no-cache'
    }
    
    try:
        info_html = ""
        req1 = urllib.request.Request(url_info, headers=headers)
        with urllib.request.urlopen(req1, timeout=5) as r1: info_html = r1.read().decode('utf-8')
            
        tt_html = ""
        req2 = urllib.request.Request(url_tt, headers=headers)
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
            .ois-header {{ color: #38bdf8; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 15px; padding-bottom: 10px; font-size: 18px; }}
            .ois-table-wrapper {{ margin-top: 10px; border: 1px solid #555; border-radius: 5px; overflow-x: auto; background: #2a2a2a; }}
            .ois-table-wrapper table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #f8fafc; margin-bottom: 0; }}
            .ois-table-wrapper th {{ background: #222; color: #38bdf8; text-align: left; padding: 10px; border-bottom: 2px solid #555; white-space: nowrap; }}
            .ois-table-wrapper td {{ padding: 10px; border-bottom: 1px solid #444; white-space: nowrap; }}
            .ois-table-wrapper tr:nth-child(even) td {{ background-color: #2a2a2a; }}
            .ois-table-wrapper tr:nth-child(odd) td {{ background-color: #333333; }}
            .ois-table-wrapper tr:hover td {{ background-color: #555555; transition: 0.2s; }}
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
        return f"<div style='color:#ef4444; padding:20px; background:#1a1a1a;'>Chyba při stahování JŘ z Inflow: {e}</div>"
