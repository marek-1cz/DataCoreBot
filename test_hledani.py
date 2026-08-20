import urllib.request
import re

req = urllib.request.Request('https://seznam-autobusu.cz/hledani?q=8P2+9559', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as response:
        print("URL:", response.geturl())
        html = response.read().decode('utf-8')
        links = re.findall(r'href="(/vuz/\d+)"', html)
        print("Found links:", list(set(links)))
except Exception as e:
    print("Error:", e)
