import sys
import io

with io.open('c:/Users/marek/Desktop/testa/DataCoreBot/interaktivnimapa.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '                # ── Vozovna check'
end_marker = 'print(f"[DEPOT] Bus {bus_id} opustil vozovnu", flush=True)'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print('Markers not found')
    sys.exit(1)
    
end_idx = content.find('\n', end_idx) + 1

block = content[start_idx:end_idx]

# Remove the block from original position
content = content[:start_idx] + content[end_idx:]

# Fix variables inside the block
block = block.replace('_check_depot_zones(lat1, lng1)', '_check_depot_zones(c.get("lat"), c.get("lng"))')
block = block.replace('not is_train', 'not c.get("is_train")')

# Now insert the block right after 'inact = (now - c["last_moved"]).total_seconds() / 60.0'
insert_marker = 'inact = (now - c["last_moved"]).total_seconds() / 60.0\n'
insert_idx = content.find(insert_marker)
if insert_idx == -1:
    print('Insert marker not found')
    sys.exit(1)

insert_idx += len(insert_marker)

new_content = content[:insert_idx] + block + '\n' + content[insert_idx:]

with io.open('c:/Users/marek/Desktop/testa/DataCoreBot/interaktivnimapa.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Successfully moved Vozovna check')
