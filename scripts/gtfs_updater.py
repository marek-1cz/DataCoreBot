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
GTFS_SOURCE_URL = os.environ.get("GTFS_SOURCE_URL", "https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip")

def write_discord_msg(msg):
    """Uloží Discord zprávu do souboru pro GitHub Actions workflow"""
    try:
        with open(".discord_msg.txt", "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception as e:
        print(f"Nepodařilo se uložit discord zprávu: {e}")

def is_idpk_route(r_short):
    pass # Obsolete, but kept to not break anything if referenced elsewhere

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

    # Uložení zipu na disk pro nahrání do GitHub Releases
    with open("gtfs.zip", "wb") as f:
        f.write(content)

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
                print("Hash je shodný s předchozí verzí. Data jsou aktuální, není třeba aktualizovat.")
                # Uložíme zprávu pro Discord – bez selhání, jen info
                with open(".discord_msg.txt", "w", encoding="utf-8") as f:
                    f.write("✅ **GTFS Pipeline proběhla v pořádku.**\n- Data jsou **aktuální** – žádná nová verze od IDPK nebyla vydána.\n- Systém nebyl zbytečně zatížen.")
                # Smazat .release_tag aby workflow nevytvářelo nový release
                if os.path.exists(".release_tag"):
                    os.remove(".release_tag")
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

    mandatory = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "agency.txt", "calendar.txt", "calendar_dates.txt"]
    for m in mandatory:
        if m not in zf.namelist():
            send_discord(f"❌ **GTFS Update selhal:** Chybí povinný soubor `{m}`.")
            sys.exit(1)

    IDPK_AGENCIES = {
        "arriva střední čechy s.r.o.",
        "čsad autobusy plzeň a.s.",
        "akv bus a.s.",
        "klatovská dopravní společnost s.r.o.",
        "lextrans bus s.r.o."
    }

    print("Zpracovávám agency.txt...")
    allowed_agency_ids = set()
    with zf.open("agency.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            a_name = row.get('agency_name', '').strip().lower()
            a_id = row.get('agency_id', '').strip()
            if a_name in IDPK_AGENCIES:
                allowed_agency_ids.add(a_id)

    # Načtení dat a filtrace IDPK
    print("Zpracovávám routes.txt...")
    routes_idpk = set()
    routes_fallback = set()
    route_id_to_short = {}
    
    # IDPK routes filter
    with zf.open("routes.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        import re
        for row in reader:
            r_id = row['route_id']
            r_short = row.get('route_short_name', '')
            a_id = row.get('agency_id', '').strip()
            r_type = row.get('route_type', '').strip()
            relations = row.get('relations', '')
            m = re.search(r'CISJR:(\d+)', relations)
            if m:
                r_short = m.group(1)

            route_id_to_short[r_id] = r_short
            
            in_range = False
            try:
                num = int(r_short)
                in_range = (400621 <= num <= 405611) or (430432 <= num <= 440649) or (450411 <= num <= 475211) or (490722 <= num <= 496711)
            except:
                pass
            
            if a_id in allowed_agency_ids and r_type in ('701', '704', '3') and in_range:
                routes_idpk.add(r_id)
            else:
                routes_fallback.add(r_id)

    print("Zpracovávám trips.txt...")
    trips_idpk = set()
    trips_fallback = set()
    services_idpk = set()
    services_fallback = set()
    trip_to_route = {}
    with zf.open("trips.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            r_id = row['route_id']
            t_id = row['trip_id']
            s_id = row.get('service_id', '')
            trip_to_route[t_id] = r_id
            if r_id in routes_idpk:
                trips_idpk.add(t_id)
                if s_id: services_idpk.add(s_id)
            else:
                trips_fallback.add(t_id)
                if s_id: services_fallback.add(s_id)

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
        conn.execute("CREATE TABLE stops (stop_id TEXT, name TEXT, lat REAL, lon REAL, mode TEXT, lines TEXT, zone_id TEXT, cisjr_id TEXT)")
        conn.execute("CREATE TABLE routes (route_id TEXT, route_short_name TEXT, route_long_name TEXT, route_type TEXT)")
        conn.execute("CREATE TABLE trips (trip_id TEXT, route_id TEXT, service_id TEXT, trip_headsign TEXT, spoj_cislo INTEGER)")
        conn.execute("CREATE TABLE stop_times (trip_id TEXT, arrival_time TEXT, departure_time TEXT, stop_id TEXT, stop_sequence INTEGER, pickup_type TEXT)")
        conn.execute("CREATE TABLE calendar (service_id TEXT, monday INTEGER, tuesday INTEGER, wednesday INTEGER, thursday INTEGER, friday INTEGER, saturday INTEGER, sunday INTEGER, start_date TEXT, end_date TEXT)")
        conn.execute("CREATE TABLE calendar_dates (service_id TEXT, date TEXT, exception_type INTEGER)")
        conn.execute("CREATE INDEX idx_stop_times_trip_id ON stop_times(trip_id)")
        conn.execute("CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id)")
        conn.execute("CREATE INDEX idx_calendar_service_id ON calendar(service_id)")
        conn.execute("CREATE INDEX idx_calendar_dates_service_id ON calendar_dates(service_id)")
    
    total_stops_inserted = 0
    with zf.open("stops.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        rows_idpk = []
        rows_fall = []
        for row in reader:
            s_id = row['stop_id']
            s_name = row.get('stop_name', '')
            s_name = s_name.replace('autobusová stanice', 'aut. st.')
            s_name = s_name.replace('Autobusová stanice', 'aut. st.')
            s_name = s_name.replace('autobusové nádraží', 'aut. nádr.')
            s_name = s_name.replace('Autobusové nádraží', 'aut. nádr.')
            s_name = s_name.replace('železniční stanice', 'žel. st.')
            s_name = s_name.replace('Železniční stanice', 'žel. st.')
            s_name = s_name.replace('restaurace', 'rest.')
            s_name = s_name.replace('Restaurace', 'rest.')
            s_name = s_name.replace('rozcestí', 'rozc.')
            s_name = s_name.replace('Rozcestí', 'rozc.')
            s_name = s_name.replace('průmyslová zóna', 'prům. zóna')
            s_name = s_name.replace('Průmyslová zóna', 'prům. zóna')
            s_name = s_name.replace('náměstí', 'nám.')
            s_name = s_name.replace('Náměstí', 'nám.')
            s_name = s_name.replace('nemocnice', 'nem.')
            s_name = s_name.replace('Nemocnice', 'nem.')
            s_name = s_name.replace('závod', 'záv.')
            s_name = s_name.replace('Závod', 'záv.')
            lat_str = row.get('stop_lat', '').strip()
            lon_str = row.get('stop_lon', '').strip()
            s_lat = float(lat_str) if lat_str else 0.0
            s_lon = float(lon_str) if lon_str else 0.0
            
            mode = 'bus' # Simplified
            z_id = row.get('zone_id', '')
            relations = row.get('relations', '')
            import re
            m = re.search(r'CISJR:(\d+)', relations)
            cisjr_id = m.group(1) if m else ""
            val = (s_id, s_name, s_lat, s_lon, mode, "[]", z_id, cisjr_id)
            
            if s_id in stops_idpk:
                rows_idpk.append(val)
                total_stops_inserted += 1
            elif s_id in stops_fallback:
                rows_fall.append(val)
                total_stops_inserted += 1
                
        conn_idpk.executemany("INSERT INTO stops VALUES (?,?,?,?,?,?,?,?)", rows_idpk)
        conn_fall.executemany("INSERT INTO stops VALUES (?,?,?,?,?,?,?,?)", rows_fall)
        
    print("Vkládám data do routes...")
    with zf.open("routes.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        routes_db_idpk = []
        routes_db_fall = []
        for row in reader:
            r_id = row['route_id']
            # Použijeme správný route_short_name, který jsme si dříve vydolovali (pokud je dostupný)
            r_short = route_id_to_short.get(r_id, row.get('route_short_name', ''))
            
            r_long = row.get('route_long_name', '')
            r_long = r_long.replace('autobusová stanice', 'aut. st.')
            r_long = r_long.replace('Autobusová stanice', 'aut. st.')
            r_long = r_long.replace('autobusové nádraží', 'aut. nádr.')
            r_long = r_long.replace('Autobusové nádraží', 'aut. nádr.')
            r_long = r_long.replace('železniční stanice', 'žel. st.')
            r_long = r_long.replace('Železniční stanice', 'žel. st.')
            r_long = r_long.replace('restaurace', 'rest.')
            r_long = r_long.replace('Restaurace', 'rest.')
            r_long = r_long.replace('rozcestí', 'rozc.')
            r_long = r_long.replace('Rozcestí', 'rozc.')
            r_long = r_long.replace('průmyslová zóna', 'prům. zóna')
            r_long = r_long.replace('Průmyslová zóna', 'prům. zóna')
            r_long = r_long.replace('náměstí', 'nám.')
            r_long = r_long.replace('Náměstí', 'nám.')
            r_long = r_long.replace('nemocnice', 'nem.')
            r_long = r_long.replace('Nemocnice', 'nem.')
            r_long = r_long.replace('závod', 'záv.')
            r_long = r_long.replace('Závod', 'záv.')
            
            val = (r_id, r_short, r_long, row.get('route_type', ''))
            if r_id in routes_idpk:
                routes_db_idpk.append(val)
            elif r_id in routes_fallback:
                routes_db_fall.append(val)
        conn_idpk.executemany("INSERT INTO routes VALUES (?,?,?,?)", routes_db_idpk)
        conn_fall.executemany("INSERT INTO routes VALUES (?,?,?,?)", routes_db_fall)

    print("Vkládám data do trips...")
    with zf.open("trips.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        trips_db_idpk = []
        trips_db_fall = []
        for row in reader:
            trip_short = row.get('trip_short_name', '')
            trip_rels = row.get('relations', '')
            spoj = 0
            import re
            m = re.search(r'CISJR:(\d+)', trip_rels)
            if m:
                spoj = int(m.group(1))
            elif trip_short:
                parts = trip_short.split()
                if parts:
                    try:
                        spoj = int(parts[-1])
                    except ValueError:
                        pass
            t_head = row.get('trip_headsign', '')
            t_head = t_head.replace('autobusová stanice', 'aut. st.')
            t_head = t_head.replace('Autobusová stanice', 'aut. st.')
            t_head = t_head.replace('autobusové nádraží', 'aut. nádr.')
            t_head = t_head.replace('Autobusové nádraží', 'aut. nádr.')
            t_head = t_head.replace('železniční stanice', 'žel. st.')
            t_head = t_head.replace('Železniční stanice', 'žel. st.')
            t_head = t_head.replace('restaurace', 'rest.')
            t_head = t_head.replace('Restaurace', 'rest.')
            t_head = t_head.replace('rozcestí', 'rozc.')
            t_head = t_head.replace('Rozcestí', 'rozc.')
            t_head = t_head.replace('průmyslová zóna', 'prům. zóna')
            t_head = t_head.replace('Průmyslová zóna', 'prům. zóna')
            t_head = t_head.replace('náměstí', 'nám.')
            t_head = t_head.replace('Náměstí', 'nám.')
            t_head = t_head.replace('nemocnice', 'nem.')
            t_head = t_head.replace('Nemocnice', 'nem.')
            t_head = t_head.replace('závod', 'záv.')
            t_head = t_head.replace('Závod', 'záv.')
            
            val = (row['trip_id'], row['route_id'], row.get('service_id', ''), t_head, spoj)
            if row['trip_id'] in trips_idpk:
                trips_db_idpk.append(val)
            elif row['trip_id'] in trips_fallback:
                trips_db_fall.append(val)
        conn_idpk.executemany("INSERT INTO trips VALUES (?,?,?,?,?)", trips_db_idpk)
        conn_fall.executemany("INSERT INTO trips VALUES (?,?,?,?,?)", trips_db_fall)

    print("Čtu rozsah platnosti dat z calendar...")
    cal_start_date = None
    cal_end_date = None
    cal_idpk = []
    cal_fall = []
    with zf.open("calendar.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        for row in reader:
            s_id = row['service_id']
            s_start = row['start_date']
            s_end = row['end_date']
            if s_id in services_idpk:
                if cal_start_date is None or s_start < cal_start_date:
                    cal_start_date = s_start
                if cal_end_date is None or s_end > cal_end_date:
                    cal_end_date = s_end
            val = (s_id, int(row['monday']), int(row['tuesday']), int(row['wednesday']), int(row['thursday']), int(row['friday']), int(row['saturday']), int(row['sunday']), row['start_date'], row['end_date'])
            if s_id in services_idpk:
                cal_idpk.append(val)
            if s_id in services_fallback:
                cal_fall.append(val)
    conn_idpk.executemany("INSERT INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?)", cal_idpk)
    conn_fall.executemany("INSERT INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?)", cal_fall)

    print("Vkládám data do calendar_dates...")
    with zf.open("calendar_dates.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        cd_idpk = []
        cd_fall = []
        for row in reader:
            s_id = row['service_id']
            val = (s_id, row['date'], int(row['exception_type']))
            if s_id in services_idpk:
                cd_idpk.append(val)
            if s_id in services_fallback:
                cd_fall.append(val)
        conn_idpk.executemany("INSERT INTO calendar_dates VALUES (?,?,?)", cd_idpk)
        conn_fall.executemany("INSERT INTO calendar_dates VALUES (?,?,?)", cd_fall)

    print("Vkládám data do stop_times...")
    with zf.open("stop_times.txt") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        batch_idpk = []
        batch_fall = []
        for row in reader:
            try:
                seq = int(row.get('stop_sequence') or 0)
            except ValueError:
                seq = 0
            val = (row['trip_id'], row.get('arrival_time', ''), row.get('departure_time', ''), row['stop_id'], seq, row.get('pickup_type', '0'))
            if row['trip_id'] in trips_idpk:
                batch_idpk.append(val)
                if len(batch_idpk) >= 100000:
                    conn_idpk.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?)", batch_idpk)
                    batch_idpk = []
            elif row['trip_id'] in trips_fallback:
                batch_fall.append(val)
                if len(batch_fall) >= 100000:
                    conn_fall.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?)", batch_fall)
                    batch_fall = []
                    
        if batch_idpk:
            conn_idpk.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?)", batch_idpk)
        if batch_fall:
            conn_fall.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?,?)", batch_fall)
        
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

    # Format validity dates for display
    def fmt_date(d):
        if d and len(d) == 8:
            return f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
        return d or "?"
    
    validity_str = f"{fmt_date(cal_start_date)} – {fmt_date(cal_end_date)}" if cal_start_date else "neznámo"

    # Příprava výstupu pro discord - changed linky s názvem linky
    changed_shorts = []
    for r_id in changed_route_ids:
        r_short = route_id_to_short.get(r_id, r_id)
        if not r_short:
            continue
        # Only include IDPK routes (numeric in range)
        try:
            num = int(r_short)
            in_range = (400621 <= num <= 405611) or (430432 <= num <= 440649) or (450411 <= num <= 475211) or (490722 <= num <= 496711)
            if in_range:
                changed_shorts.append(r_short)
        except:
            pass

    changed_shorts = list(set(changed_shorts))  # deduplicate
    changed_shorts.sort()

    if changed_shorts:
        changed_str = "\n".join([f"• {rs}" for rs in changed_shorts[:30]])
        if len(changed_shorts) > 30:
            changed_str += f"\n... a {len(changed_shorts) - 30} dalších"
    else:
        changed_str = "Žádné IDPK linky se nezměnily"

    # Uložení tagu pro GitHub Action
    with open(".release_tag", "w") as f:
        f.write(tag_name)

    # Uložení notes pro GitHub Action
    with open(".release_notes.md", "w") as f:
        f.write(f"Automatická aktualizace dat.\n- Zastávek: {total_stops_inserted}\n- Linek: {len(routes_idpk)+len(routes_fallback)}\n- Spojů: {len(trips_idpk)+len(trips_fallback)}\n- Platnost dat: {validity_str}\n- Hash: `{current_hash}`")
    
    # Sestavení Discord zprávy – uloží do souboru pro workflow
    msg = (f"✅ **GTFS Data úspěšně aktualizována!**\n"
           f"- **Platnost JŘ dat:** `{validity_str}`\n"
           f"- **Nová verze:** `{tag_name}`\n"
           f"- **Celkem zastávek:** {total_stops_inserted}\n"
           f"- **Celkem linek (IDPK):** {len(routes_idpk)}\n"
           f"- **Celkem spojů (IDPK):** {len(trips_idpk)}\n"
           f"- **Změněné IDPK linky ({len(changed_shorts)}):**\n{changed_str}")
    write_discord_msg(msg)
    
    print("Zpracování úspěšně dokončeno.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        if len(err_msg) > 1500:
            err_msg = err_msg[:1500] + "...\n(Chyba byla příliš dlouhá)"
        print("Kritická chyba:", err_msg)
        # Write error to discord msg file so workflow can send it
        try:
            with open(".discord_msg.txt", "w", encoding="utf-8") as f:
                f.write(f"❌ **Kritická chyba GTFS Updateru:**\n```\n{err_msg[:800]}\n```")
        except:
            pass
        sys.exit(1)
