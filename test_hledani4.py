import requests
import re

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    r1 = session.get('https://seznam-autobusu.cz/')
    print('Home status:', r1.status_code)
    data = {
        'search': '8P2 9559',
        '_submit': 'vyhledat',
        '_do': 'header-combinedSearch-search-submit'
    }
    r2 = session.post('https://seznam-autobusu.cz/', data=data, allow_redirects=True)
    print('Search final URL:', r2.url)
    html = r2.text
    links = re.findall(r'href="(/vuz/\d+)"', html)
    print('Found links:', list(set(links)))
except Exception as e:
    print('Error:', e)
