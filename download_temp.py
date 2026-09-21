import requests, zipfile, io, os
target_dir = os.path.expandvars(r'%APPDATA%\idpk-palubni-pocitac\data')
os.makedirs(target_dir, exist_ok=True)
zip_path = os.path.join(target_dir, '..', 'gtfs.zip')
print('Downloading...')
r = requests.get('https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip', headers={'User-Agent': 'Mozilla/5.0'})
open(zip_path, 'wb').write(r.content)
print('Extracting...')
zipfile.ZipFile(zip_path).extractall(target_dir)
print('Updating version...')
with open(os.path.join(target_dir, '..', 'gtfs_version.json'), 'w') as f:
    f.write('{"version": "gtfs-2026-08-30"}')
print('Done!')
