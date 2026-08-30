import os
import sys
import os
import sys
import requests
import hashlib
import zipfile
import csv
import sqlite3
import datetime
import json
import io
import collections

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GTFS_SOURCE_URL = os.environ.get("GTFS_SOURCE_URL", "https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip")

def send_discord(msg):
    if not DISCORD_WEBHOOK_URL: return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except:
        pass

def is_idpk_route(r_short):
    try:
        rNum = int(r_short)
        return (400621 <= rNum <= 405611) or \
               (430432 <= rNum <= 440649) or \
               (450411 <= rNum <= 475211) or \
               (490722 <= rNum <= 496711)
    except:
        return False

def main():
    print("Spouštím GTFS Updater...")
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Chybí Supabase secrets!")
        sys.exit(1)

    print(f"Stahuji GTFS ze zdroje: {GTFS_SOURCE_URL}")
    try:
        resp = requests.get(GTFS_SOURCE_URL, stream=True, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        send_discord(f"❌ **GTFS Update selhal:** Nelze stáhnout GTFS zip. Chyba: {e}")
        sys.exit(1)

    # Spočítat hash
    h = hashlib.sha256()
    content = resp.content
    h.update(content)
    current_hash = h.hexdigest()
    print(f"Staženo {len(content)} bytů. Hash: {current_hash}")

    # Kontrola proti Supabase
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        sb_resp = requests.get(f"{SUPABASE_URL}/rest/v1/gtfs_feed_versions?select=source_hash&order=id.desc&limit=1", headers=headers)
        sb_resp.raise_for_status()
        data = sb_resp.json()
        if data and len(data) > 0:
            last_hash = data[0].get("source_hash")
            if last_hash == current_hash:
                print("Hash je shodný s předchozí verzí. Není třeba aktualizovat.")
                sys.exit(0)
    except Exception as e:
        print(f"Varování: Nelze přečíst hash z databáze, pokračuji: {e}")

    # Rozbalení zipu v paměti
    print("Rozbaluji ZIP...")
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        send_discord("❌ **GTFS Update selhal:** Stažený soubor není validní ZIP.")
        sys.exit(1)

    mandatory = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
    for m in mandatory:
        if m not in zf.namelist():
            send_discord(f"❌ **GTFS Update selhal:** Chybí povinný soubor `{m}`.")
            sys.exit(1)

    # Načtení dat a filtrace IDPK
    print("Zpracovávám routes.txt...")
    routes_idpk = set()
    routes_fallback = set()
    route_id_to_short = {}
    
    # IDPK routes filter
    with zf.open("routes.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            r_id = row['route_id']
            r_short = row.get('route_short_name', '')
            route_id_to_short[r_id] = r_short
            if is_idpk_route(r_short):
                routes_idpk.add(r_id)
            else:
                routes_fallback.add(r_id)

    print("Zpracovávám trips.txt...")
    trips_idpk = set()
    trips_fallback = set()
    trip_to_route = {}
    with zf.open("trips.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            r_id = row['route_id']
            t_id = row['trip_id']
            trip_to_route[t_id] = r_id
            if r_id in routes_idpk:
                trips_idpk.add(t_id)
            else:
                trips_fallback.add(t_id)

    print("Zpracovávám stop_times.txt...")
    stops_idpk = set()
    stops_fallback = set()
    route_hashes_builder = collections.defaultdict(hashlib.md5)
    
    with zf.open("stop_times.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            t_id = row['trip_id']
            s_id = row['stop_id']
            
            # Budování hashe pro detekci změn linek
            r_id = trip_to_route.get(t_id)
            if r_id:
                s = f"{s_id}{row.get('arrival_time','')}{row.get('departure_time','')}{row.get('stop_sequence','')}"
                route_hashes_builder[r_id].update(s.encode('utf-8'))
                
            if t_id in trips_idpk:
                stops_idpk.add(s_id)
            elif t_id in trips_fallback:
                stops_fallback.add(s_id)
                
    current_route_hashes = {r_id: hasher.hexdigest() for r_id, hasher in route_hashes_builder.items()}

    print("Zpracovávám stops.txt a generuji SQLite...")
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    tag_name = f"gtfs-{date_str}"
    
    idpk_db_file = f"gtfs_stops_idpk.db"
    fallback_db_file = f"gtfs_stops_fallback.db"
    
    if os.path.exists(idpk_db_file): os.remove(idpk_db_file)
    if os.path.exists(fallback_db_file): os.remove(fallback_db_file)
    
    conn_idpk = sqlite3.connect(idpk_db_file)
    conn_fall = sqlite3.connect(fallback_db_file)
    
    for conn in [conn_idpk, conn_fall]:
        conn.execute("CREATE TABLE stops (stop_id TEXT, name TEXT, lat REAL, lon REAL, mode TEXT, lines TEXT)")
    
    total_stops_inserted = 0
    with zf.open("stops.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        rows_idpk = []
        rows_fall = []
        for row in reader:
            s_id = row['stop_id']
            s_name = row.get('stop_name', '')
            lat_str = row.get('stop_lat', '').strip()
            lon_str = row.get('stop_lon', '').strip()
            s_lat = float(lat_str) if lat_str else 0.0
            s_lon = float(lon_str) if lon_str else 0.0
            
            mode = 'bus' # Simplified
            val = (s_id, s_name, s_lat, s_lon, mode, "[]")
            
            if s_id in stops_idpk:
                rows_idpk.append(val)
                total_stops_inserted += 1
            elif s_id in stops_fallback:
                rows_fall.append(val)
                total_stops_inserted += 1
                
        conn_idpk.executemany("INSERT INTO stops VALUES (?,?,?,?,?,?)", rows_idpk)
        conn_fall.executemany("INSERT INTO stops VALUES (?,?,?,?,?,?)", rows_fall)
        
    conn_idpk.commit()
    conn_fall.commit()
    conn_idpk.close()
    conn_fall.close()
    
    if total_stops_inserted < 1000:
        send_discord("❌ **GTFS Update selhal:** Nalezeno podezřele málo zastávek.")
        sys.exit(1)
        
    print(f"Ukládám novou verzi do Supabase...")
    try:
        new_row = {
            "version_tag": tag_name,
            "source_hash": current_hash,
            "stop_count": total_stops_inserted,
            "route_count": len(routes_idpk) + len(routes_fallback),
            "trip_count": len(trips_idpk) + len(trips_fallback),
            "validation_status": "OK",
            "release_url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'marek-1cz/DataCoreBot')}/releases/tag/{tag_name}"
        }
        sb_post = requests.post(f"{SUPABASE_URL}/rest/v1/gtfs_feed_versions", headers=headers, json=new_row)
        sb_post.raise_for_status()
    except Exception as e:
        print(f"Nepodařilo se zapsat do Supabase: {e}")

    # Zpracování změn jednotlivých linek
    existing_hashes = {}
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/gtfs_line_updates?select=route_id,hash", headers=headers)
        r.raise_for_status()
        for x in r.json():
            existing_hashes[x['route_id']] = x['hash']
    except Exception as e:
        print("Nepodařilo se stáhnout staré hashe linek:", e)
        
    changed_route_ids = []
    updates_for_db = []
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    
    for r_id, h in current_route_hashes.items():
        if existing_hashes.get(r_id) != h:
            changed_route_ids.append(r_id)
            updates_for_db.append({
                "route_id": r_id,
                "hash": h,
                "last_updated_at": now_iso
            })
            
    if updates_for_db:
        try:
            # Upsert
            headers_upsert = headers.copy()
            headers_upsert["Prefer"] = "resolution=merge-duplicates"
            # Můžeme to poslat po dávkách, kdyby toho bylo moc
            chunk_size = 1000
            for i in range(0, len(updates_for_db), chunk_size):
                requests.post(f"{SUPABASE_URL}/rest/v1/gtfs_line_updates", headers=headers_upsert, json=updates_for_db[i:i+chunk_size])
        except Exception as e:
            print("Nepodařilo se zapsat gtfs_line_updates:", e)

    # Příprava výstupu pro discord
    changed_shorts = [route_id_to_short.get(r, r) for r in changed_route_ids]
    changed_idpk = [rs for rs in changed_shorts if is_idpk_route(rs)]
    changed_str = ", ".join(changed_idpk) if changed_idpk else "Žádné (nebo jen mimo IDPK)"
    if len(changed_str) > 1000:
        changed_str = changed_str[:1000] + "... (více zkráceno)"

    # Uložení tagu pro GitHub Action
    with open(".release_tag", "w") as f:
        f.write(tag_name)
        
    # Uložení notes pro GitHub Action
    with open(".release_notes.md", "w") as f:
        f.write(f"Automatická aktualizace dat.\n- Zastávek: {total_stops_inserted}\n- Linek: {len(routes_idpk)+len(routes_fallback)}\n- Spojů: {len(trips_idpk)+len(trips_fallback)}\n- Hash: `{current_hash}`")
    
    # Odeslání notifikace na Discord
    msg = (f"✅ **GTFS Data úspěšně aktualizována!**\n"
           f"- **Nová verze:** `{tag_name}`\n"
           f"- **Celkem zastávek:** {total_stops_inserted}\n"
           f"- **Celkem linek:** {len(routes_idpk) + len(routes_fallback)}\n"
           f"- **Celkem spojů:** {len(trips_idpk) + len(trips_fallback)}\n"
           f"- **Změněné IDPK linky:** {changed_str}")
    send_discord(msg)
    
    print("Zpracování úspěšně dokončeno.")

if __name__ == "__main__":
    main()
