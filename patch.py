import sys
import re

file_path = r'c:\Users\marek\Desktop\testa\DataCoreBot\interaktivnimapa.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 4524: "admin_note": "", -> "admin_note": "", "admin_driver": "",
content = re.sub(r'("admin_note":\s*"",\s*\n)', r'\1        "admin_driver": "",\n', content)

# 4673: "admin_note": row.get("admin_note", ""),
content = re.sub(r'("admin_note":\s*row\.get\("admin_note",\s*""\),)', r'\1\n                        "admin_driver": row.get("admin_driver", ""),', content)

# 4692: ghost_entry["admin_note"] = row.get("admin_note") or ""
content = re.sub(r'(ghost_entry\["admin_note"\]\s*=\s*row\.get\("admin_note"\)\s*or\s*""\s*\n)', r'\1                ghost_entry["admin_driver"] = row.get("admin_driver") or ""\n', content)

# 4874: ghost_admin_note = best_gc.get("admin_note", "")
content = re.sub(r'(ghost_admin_note\s*=\s*best_gc\.get\("admin_note",\s*""\)\s*\n)', r'\1                                    ghost_admin_driver = best_gc.get("admin_driver", "")\n', content)

# 5831: "admin_note": bc.get("admin_note", ""),
content = re.sub(r'("admin_note":\s*bc\.get\("admin_note",\s*""\),)', r'\1\n                        "admin_driver": bc.get("admin_driver", ""),', content)

# 6753: c["admin_note"] = ""
content = re.sub(r'(c\["admin_note"\]\s*=\s*""\s*\n)', r'\1        c["admin_driver"] = ""\n', content)

# 6795: "admin_note": c.get("admin_note", "")
content = re.sub(r'("admin_note":\s*c\.get\("admin_note",\s*""\)\s*\n)', r'\1        ,"admin_driver": c.get("admin_driver", "")\n', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Regex patch applied.")
