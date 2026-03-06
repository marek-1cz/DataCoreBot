import sys
import os
import discord
from discord.ext import commands
from flask import Flask, render_template_string
from threading import Thread
from supabase import create_client, Client

print("=== START BOTA ===", flush=True)

# ==========================================
# 1. ČÁST: WEBOVÝ SERVER A ADMIN PANEL
# ==========================================
app = Flask(__name__)

# Tady je design tvé nové tajné webové stránky
HTML_ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>MRWEB - Admin Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 40px; }
        .container { max-width: 1000px; margin: 0 auto; background-color: #1e1e1e; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h1 { color: #bb86fc; border-bottom: 2px solid #333; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #333; }
        th { background-color: #2c2c2c; color: #bb86fc; font-weight: bold; }
        tr:hover { background-color: #2a2a2a; }
        .role-SA { color: #cf6679; font-weight: bold; }
        .role-User { color: #03dac6; }
        .btn { background-color: #bb86fc; color: #121212; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 14px; }
        .btn:hover { background-color: #9d4edd; }
    </style>
</head>
<body>
    <div class="container">
        <h1>👑 MRWEB - Databáze Uživatelů</h1>
        <table>
            <tr>
                <th>Discord ID</th>
                <th>Herní Nick</th>
                <th>Role</th>
                <th>HWID (Zámek)</th>
                <th>Akce</th>
            </tr>
            {% for user in users %}
            <tr>
                <td>{{ user.discord_id }}</td>
                <td><strong>{{ user.nick }}</strong></td>
                <td class="role-{{ user.role }}">{{ user.role }}</td>
                <td>{{ user.hwid if user.hwid else 'Zatím prázdné' }}</td>
                <td><a href="#" class="btn">Upravit</a></td>
            </tr>
            {% else %}
            <tr>
                <td colspan="5" style="text-align: center; padding: 30px;">Zatím zde nejsou žádní uživatelé.</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    # Tohle vidí UptimeRobot (a náhodní kolemjdoucí)
    return "DataCoreBot běží 24/7 a nespí!"

@app.route('/tajny-mrweb-admin')
def admin_panel():
    # Tohle je tvá tajná stránka!
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            return "Kritická chyba: Chybí klíče k databázi na Renderu!"
        
        supabase = create_client(url, key)
        # Vytáhneme všechny uživatele z databáze
        response = supabase.table("users").select("*").execute()
        users = response.data
        
        # Vykreslíme HTML stránku s daty
        return render_template_string(HTML_ADMIN_PAGE, users=users)
    except Exception as e:
        return f"Chyba při načítání databáze: {e}"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 2. ČÁST: DISCORD BOT & PŘÍKAZY
# ==========================================
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'[OK] Úspěšně přihlášen jako {bot.user}', flush=True)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! Běžím, nespím a jsem připraven na MRWEB!')

@bot.command()
async def db(ctx):
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
             supabase = create_client(url, key)
             supabase.table("users").select("*").limit(1).execute()
             await ctx.send('Databáze Supabase je připojena a tabulka users funguje! 🟢')
        else:
            await ctx.send('Chybí klíče na Renderu. 🔴')
    except Exception as e:
        await ctx.send(f'Chyba při připojování k databázi: {e} 🔴')

@bot.command()
async def register(ctx, nick: str = None):
    if not nick:
        await ctx.send("Musíš zadat svůj herní nick! Použití: `!register TvujNick`")
        return
        
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            await ctx.send("Databáze není nakonfigurována (chybí klíče na Renderu).")
            return
            
        supabase = create_client(url, key)
        discord_id = str(ctx.author.id)
        
        response = supabase.table("users").select("*").eq("discord_id", discord_id).execute()
        
        if len(response.data) > 0:
            await ctx.send(f"Už jsi v databázi zaregistrovaný, {ctx.author.mention}! 🛑")
        else:
            novy_uzivatel = {
                "discord_id": discord_id,
                "nick": nick,
                "role": "User",
                "hwid": ""
            }
            supabase.table("users").insert(novy_uzivatel).execute()
            await ctx.send(f"Paráda! Byl jsi úspěšně zaregistrován jako **{nick}**! ✅")
            
    except Exception as e:
        await ctx.send(f"Něco se pokazilo při registraci: {e} 🔴")

# ==========================================
# SPUŠTĚNÍ VŠEHO
# ==========================================
if __name__ == "__main__":
    print("[INFO] Zapínám webový server...", flush=True)
    keep_alive()
    
    token = os.environ.get("DISCORD_TOKEN")
    
    if token:
        print("[INFO] Spouštím připojení na Discord...", flush=True)
        bot.run(token)
    else:
        print("[CHYBA] Nebyl nalezen DISCORD_TOKEN!", flush=True)
