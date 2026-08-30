import re

def patch_main():
    with open('main.py', 'r', encoding='utf-8') as f:
        py_content = f.read()

    # Match the old auth logic
    pattern = r"(# Ověření oprávnění\s+allowed = False\s+if discord_id:\s+try:\s+)resp = supabase\.table\('users'\)\.select\('role'\)\.eq\('discord_id', discord_id\)\.execute\(\)"
    
    replacement = r"\1db = get_db()\n            if discord_id.startswith('email-'):\n                user_id = discord_id.split('-')[1]\n                resp = db.table('users').select('role').eq('id', user_id).execute()\n            else:\n                resp = db.table('users').select('role').eq('discord_id', discord_id).execute()"
    
    new_content = re.sub(pattern, replacement, py_content)
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    patch_main()
    print("Patch done!")
