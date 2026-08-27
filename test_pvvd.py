import urllib.request
import json
import re

url = "https://pvvd.idpk.cz/Ajax/GetPoints?_=123"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as r:
        buses = json.loads(r.read().decode())
        print(f"Found {len(buses)} buses via GetPoints")
        if buses:
            print("Sample bus:", buses[0])
            bus_id = buses[0]['id']
            
            # Now test OpenInfoWindow
            info_url = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_=123"
            req2 = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2) as r2:
                html = r2.read().decode('utf-8')
                print("HTML snippet:", html[:500])
                ml = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
                ms = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
                print("Linka regex:", ml.group(1).strip() if ml else None)
                print("Spoj regex:", ms.group(1).strip() if ms else None)
                
                # Check what else is there
                print("Full HTML table:")
                table = re.findall(r'<th>(.*?)</th>\s*<td>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
                for k, v in table:
                    print(f"  {k.strip()}: {v.strip()}")
except Exception as e:
    print("Error:", e)
