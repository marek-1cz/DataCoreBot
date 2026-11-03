# scripts/cleanup_d1_depots.py
import sys, os
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from cloudflare_d1 import get_d1_client

def cleanup():
    d1 = get_d1_client()

    # 1. Uzavřít staré neuzavřené návštěvy z října
    d1.execute("UPDATE depot_history SET left_at = '2026-10-26T18:00:00+01:00', status = 'LEFT' WHERE bus_id = '273' AND left_at IS NULL")

    # 2. Uzavřít starší duplicity, ponechat pouze 1 nejnovější pobyt na vůz/SPZ
    rows = d1.execute("SELECT id, bus_id, spz, arrived_at FROM depot_history WHERE left_at IS NULL ORDER BY arrived_at DESC")
    seen_buses = set()
    seen_spzs = set()
    closed = 0
    for r in rows:
        b = str(r.get("bus_id") or "")
        s = str(r.get("spz") or "").replace(" ", "").upper()
        if b in seen_buses or (s and s in seen_spzs):
            d1.execute("UPDATE depot_history SET left_at = arrived_at, status = 'LEFT' WHERE id = ?", [r["id"]])
            closed += 1
        else:
            if b: seen_buses.add(b)
            if s: seen_spzs.add(s)

    print(f"Uzavřeno {closed} duplicitních starších pobytů.")
    remaining = d1.execute("SELECT id, depot_name, bus_id, spz, arrived_at FROM depot_history WHERE left_at IS NULL ORDER BY arrived_at DESC")
    print(f"Nyní aktivně v D1 evidováno {len(remaining)} unikátních vozidel:")
    for r in remaining:
        print(f"  ID:{r['id']} | Vůz:{r['bus_id']} | SPZ:{r['spz']} | {r['depot_name']} | Příjezd:{r['arrived_at']}")

if __name__ == "__main__":
    cleanup()
