import sys
import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from supabase import create_client, Client

print("=== START BOTA ===", flush=True)

# ==========================================
# 1. ČÁST: WEBOVÝ SERVER (PROTI USPÁNÍ)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "DataCoreBot běží 24/7 a nespí!"

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
             # Zkoušíme reálnou tabulku users, co jsi právě vytvořil
             supabase.table("users").select("*").limit(1).execute()
             await ctx.send('Databáze Supabase je připojena a tabulka users funguje! 🟢')
        else:
            await ctx.send('Chybí klíče na Renderu. 🔴')
    except Exception as e:
        await ctx.send(f'Chyba při připojování k databázi: {e} 🔴')

@bot.command()
async def register(ctx, nick: str = None):
    # Pokud uživatel nezadá nick, bot ho upozorní
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
        
        # 1. Zkontrolujeme, jestli už uživatel není v databázi
        response = supabase.table("users").select("*").eq("discord_id", discord_id).execute()
        
        if len(response.data) > 0:
            await ctx.send(f"Už jsi v databázi zaregistrovaný, {ctx.author.mention}! 🛑")
        else:
            # 2. Pokud není, přidáme ho jako nového uživatele
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
