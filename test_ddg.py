import urllib.request
import urllib.parse
spz = "8P2 9559"
query = urllib.parse.quote_plus(f'\\site:seznam-autobusu.cz "{spz}"')
req = urllib.request.Request(f'https://duckduckgo.com/?q={query}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as response:
        print("Final URL:", response.geturl())
except Exception as e:
    print("Error:", e)
