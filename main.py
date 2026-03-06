import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# ==========================================
# 1. ČÁST: WEBOVÝ SERVER (PROTI USPÁNÍ)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    # Tento text uvidí UptimeRobot, když bota "prozvoní"
    return "DataCoreBot běží 24/7 a nespí!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 2. ČÁST: SUPABASE DATABÁZE
# ==========================================
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Připojíme databázi pouze pokud máme klíče z Renderu
if url and key:
    supabase: Client = create_client(url, key)
    print("Supabase databáze úspěšně připojena!")
else:
    supabase = None
    print("POZOR: Supabase klíče nebyly nalezeny. Přidej SUPABASE_URL a SUPABASE_KEY na Render.")

# ==========================================
# 3. ČÁST: DISCORD BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Úspěšně přihlášen jako {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! Běžím, nespím a jsem připraven na MRWEB!')

@bot.command()
async def db(ctx):
    # Testovací příkaz pro ověření spojení s databází
    if supabase:
        await ctx.send('Databáze Supabase je připojena a připravena na ukládání uživatelů! 🟢')
    else:
        await ctx.send('Databáze není připojena! Chybí klíče na Renderu. 🔴')

# ==========================================
# SPUŠTĚNÍ VŠEHO
# ==========================================
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("CHYBA: Nebyl nalezen DISCORD_TOKEN!")
