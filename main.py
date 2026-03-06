import sys
import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from supabase import create_client, Client

print("=== START BOTA ===", flush=True)

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

# --- DISCORD BOT ---
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
             # Malý testík na databázi - jen jestli odpoví
             supabase.table("test").select("*").limit(1).execute()
             await ctx.send('Databáze Supabase je připojena a odpovídá! 🟢')
        else:
            await ctx.send('Chybí klíče na Renderu. 🔴')
    except Exception as e:
        await ctx.send(f'Chyba při připojování: {e} 🔴')

if __name__ == "__main__":
    print("[INFO] Zapínám webový server...", flush=True)
    keep_alive()
    
    token = os.environ.get("DISCORD_TOKEN")
    
    if token:
        print("[INFO] Spouštím připojení na Discord...", flush=True)
        bot.run(token)
    else:
        print("[CHYBA] Nebyl nalezen DISCORD_TOKEN!", flush=True)
