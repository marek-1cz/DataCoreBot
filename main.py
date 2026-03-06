import sys
print("=== START BOTA ===", flush=True)

try:
    import os
    print("[OK] OS knihovna načtena", flush=True)
    
    import discord
    from discord.ext import commands
    print("[OK] Discord knihovna načtena", flush=True)
    
    from flask import Flask
    from threading import Thread
    print("[OK] Flask webserver načten", flush=True)
    
    from supabase import create_client, Client
    print("[OK] Supabase knihovna načtena", flush=True)

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
    # 2. ČÁST: SUPABASE DATABÁZE
    # ==========================================
    print("[INFO] Načítám Supabase klíče z Renderu...", flush=True)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if url and key:
        supabase = create_client(url, key)
        print("[OK] Supabase databáze úspěšně připojena!", flush=True)
    else:
        supabase = None
        print("[CHYBA] Supabase klíče nebyly nalezeny!", flush=True)

    # ==========================================
    # 3. ČÁST: DISCORD BOT
    # ==========================================
    print("[INFO] Nastavuji Discord bota...", flush=True)
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
        if supabase:
            await ctx.send('Databáze Supabase je připojena a připravena na ukládání uživatelů! 🟢')
        else:
            await ctx.send('Databáze není připojena! Chybí klíče na Renderu. 🔴')

    # ==========================================
    # SPUŠTĚNÍ VŠEHO
    # ==========================================
    if __name__ == "__main__":
        print("[INFO] Zapínám webový server...", flush=True)
        keep_alive()
        
        print("[INFO] Získávám Discord Token...", flush=True)
        token = os.environ.get("DISCORD_TOKEN")
        
        if token:
            print("[INFO] Spouštím připojení na Discord...", flush=True)
            bot.run(token)
        else:
            print("[CHYBA] Nebyl nalezen DISCORD_TOKEN!", flush=True)

except Exception as e:
    # Pokud se cokoliv pokazí, tahle část to okamžitě práskne do logu!
    print(f"\n!!! KRITICKÁ CHYBA PŘI STARTU: {e} !!!\n", flush=True)
