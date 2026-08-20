import urllib.request
import re

req = urllib.request.Request('https://seznam-autobusu.cz/', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
        for i, form in enumerate(forms):
            print(f"--- Form {i} ---")
            inputs = re.findall(r'<input[^>]+>', form, re.IGNORECASE)
            for inp in inputs:
                print("Input:", inp)
            action = re.search(r'action=[\"\']([^\"\']+)[\"\']', html)
            print("Action?", action.group(1) if action else "None")
except Exception as e:
    print("Error:", e)
