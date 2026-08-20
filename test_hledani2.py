import urllib.request
import urllib.parse
import re

params = {
    'search': '8P2 9559',
    '_submit': 'vyhledat',
    '_do': 'header-combinedSearch-search-submit'
}
query = urllib.parse.urlencode(params)
req = urllib.request.Request(f'https://seznam-autobusu.cz/?{query}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as response:
        print("URL after redirect:", response.geturl())
        html = response.read().decode('utf-8')
        links = re.findall(r'href="(/vuz/\d+)"', html)
        print("Found bus links:", list(set(links)))
except Exception as e:
    print("Error:", e)
