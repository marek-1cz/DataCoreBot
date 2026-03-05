import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# ==========================================
# 1. ČÁST WEBOVÝ SERVER (PROTI USPÁNÍ)
# ==========================================
app = Flask(__name__)

@app.route('')
def home()
    # Tento text uvidí UptimeRobot, když bota prozvoní
    return MRWEB Bot běží 247 a nespí!

def run()
    # Render automaticky přiřazuje port, na kterém má web běžet
    port = int(os.environ.get(PORT, 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive()
    # Spustí webový server v samostatném vlákně, aby neblokoval bota
    t = Thread(target=run)
    t.start()

# ==========================================
# 2. ČÁST DISCORD BOT
# ==========================================
# Nastavení oprávnění bota (aby mohl číst zprávy atd.)
intents = discord.Intents.default()
intents.message_content = True 

# Prefix pro příkazy bude !
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready()
    print(f'Úspěšně přihlášen jako {bot.user}')

@bot.command()
async def ping(ctx)
    # Testovací příkaz na Discordu
    await ctx.send('Pong! Běžím, nespím a jsem připraven na MRWEB!')

# ==========================================
# SPUŠTĚNÍ VŠEHO
# ==========================================
if __name__ == __main__
    # 1. Zapneme webový server proti uspání
    keep_alive()
    
    # 2. Zapneme bota pomocí Tokenu, který zadáme až na Renderu
    token = os.environ.get(DISCORD_TOKEN)
    
    if token
        bot.run(token)
    else
        print(CHYBA Nebyl nalezen DISCORD_TOKEN! Nastav ho v administraci Renderu.)