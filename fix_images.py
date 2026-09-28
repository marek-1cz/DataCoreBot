import os
import re
import urllib.request
from urllib.parse import urlparse, unquote

def process_directory(base_dir, static_prefix, save_dir):
    pattern = re.compile(r'(https://tdonrppusbwhoftdontz\.supabase\.co/storage/v1/object/public/([^"\']+))')
    
    os.makedirs(save_dir, exist_ok=True)
    
    for root, dirs, files in os.walk(base_dir):
        # Skip node_modules and .git
        if 'node_modules' in root or '.git' in root or 'dist-launcher' in root or 'versions' in root:
            continue
            
        for file in files:
            if not file.endswith(('.py', '.html', '.js', '.css')):
                continue
                
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
                
            matches = pattern.findall(content)
            if not matches:
                continue
                
            new_content = content
            for url, path in matches:
                # path is like 'logo/datacorebot%20pf-lepsi.png'
                filename = unquote(path.split('/')[-1])
                # clean filename
                filename = filename.replace(' ', '_')
                
                local_save_path = os.path.join(save_dir, filename)
                
                # Download if not exists
                if not os.path.exists(local_save_path):
                    print(f"Downloading {url} to {local_save_path}")
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response, open(local_save_path, 'wb') as out_file:
                            out_file.write(response.read())
                    except Exception as e:
                        print(f"Failed to download {url}: {e}")
                        continue
                
                # Replace in content
                local_url = f"{static_prefix}{filename}"
                new_content = new_content.replace(url, local_url)
                print(f"Replaced {url} -> {local_url} in {filepath}")
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)

print("Processing DataCoreBot...")
process_directory(r"c:\Users\marek\Desktop\testa\DataCoreBot", "/static/img/", r"c:\Users\marek\Desktop\testa\DataCoreBot\static\img")

print("Processing IDPK Launcher...")
process_directory(r"c:\Users\marek\Desktop\testa\IDPK-OIS-RC-EDITION-V1.6", "assets/img/", r"c:\Users\marek\Desktop\testa\IDPK-OIS-RC-EDITION-V1.6\assets\img")
