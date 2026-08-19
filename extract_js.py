import ast
import re

with open('interaktivnimapa.py', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'HTML_MAPA\s*=\s*\"\"\"(.*?)\"\"\"', content, re.DOTALL)
if match:
    html = match.group(1)
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for i, s in enumerate(scripts):
        with open(f'test_{i}.js', 'w', encoding='utf-8') as out:
            out.write(s)
    print(f'Extracted {len(scripts)} scripts')
else:
    print('No HTML_MAPA found')
