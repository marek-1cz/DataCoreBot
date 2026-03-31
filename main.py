import os
import discord
from discord.ext import commands, tasks
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
import uuid
import urllib.request
import http.cookiejar
import json
import traceback
import re
import gc
import time
import random
import logging
import io
from werkzeug.exceptions import HTTPException
from html_templates import *

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

URL_MALE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png"
URL_VELKE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png"

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Range'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return f"<div style='background:#0f172a; color:#f59e0b; padding:40px; font-family:sans-serif; text-align:center; height:100vh; box-sizing:border-box;'><h2 style='font-size:40px;'>CHYBA {e.code}</h2><p style='font-size:18px; color:white;'>Stránka nebyla nalezena.</p><a href='/' style='display:inline-block; margin-top:20px; padding:10px 20px; background:#38bdf8; color:black; text-decoration:none; font-weight:bold; border-radius:5px;'>Zpět domů</a></div>", e.code
    return f"<div style='background:#0f172a; color:#ef4444; padding:20px; font-family:monospace; border:2px solid #ef4444;'><h2>CHYBA (500)</h2><pre>{traceback.format_exc()}</pre></div>", 500

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
_db_client = None

def get_db():
    global _db_client
    try:
        if _db_client is None and SUPABASE_URL and SUPABASE_KEY:
            _db_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _db_client
    except Exception as e: print(f"Chyba připojení k DB: {e}")
    return None

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, max_messages=10)
bot.invites_cache = {}

# --- POMOCNÉ FUNKCE ---

async def async_send_log(title, description, color=0x38bdf8):
    if not bot.is_ready(): return
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            try: await channel.send(embed=discord.Embed(title=title, description=description, color=color, timestamp=get_prague_time()))
            except: pass
            break

def send_log(title, description, color=0x38bdf8):
    if bot.loop and bot.loop.is_running() and bot.is_ready(): 
        asyncio.run_coroutine_threadsafe(async_send_log(title, description, color), bot.loop)

def _cors_jsonify(data):
    return jsonify(data)

def render_public(template_string, **kwargs):
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html.replace('{{ deploy_time }}', DEPLOY_TIME)), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

@app.before_request
def check_session_validity():
    if request.path.startswith('/dashboard/') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize']:
        if not session.get('logged_in'): return redirect(url_for('dashboard_main'))

# --- STATUSY A DASHBOARD ---

@app.route('/dashboard/update_statuses', methods=['POST'])
def update_statuses():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if not db: return redirect(url_for('dashboard_app_management'))
    
    # Načtení dat z formuláře
    s_dl = request.form.get("status_dl", "🟢 Stahování softwaru běží v pořádku.")
    s_db = request.form.get("status_db", "🟢 Databáze je stabilní.")
    s_global = request.form.get("status_global", "🟢 Všechny systémy softwaru jsou online.")
    maint_dl = True if request.form.get("status_dl_manual") else False
    
    # Uložení do DB settings
    settings_to_update = {
        "status_dl_msg": s_dl,
        "status_db_msg": s_db,
        "status_global_msg": s_global,
        "status_dl_maintenance": maint_dl
    }
    
    try:
        for key, val in settings_to_update.items():
            check = db.table("settings").select("*").eq("setting_key", key).execute().data
            if not check: db.table("settings").insert({"setting_key": key, "setting_value": str(val)}).execute()
            else: db.table("settings").update({"setting_value": str(val)}).eq("setting_key", key).execute()
        
        flash('Statusy byly uloženy v databázi.', 'success')
        
        # Pokud bylo kliknuto na tlačítko odeslat na Discord
        if request.form.get("send_to_discord"):
            async def send_status_embed():
                if not bot.is_ready(): return
                for guild in bot.guilds:
                    channel = discord.utils.get(guild.channels, name="🛜・status")
                    if channel:
                        color = 0x10b981 # Zelená
                        dl_final_msg = s_dl
                        
                        if maint_dl:
                            color = 0xf59e0b # Oranžová
                            dl_final_msg = "🟠 **Probíhá oprava systému.** Stahování některých souborů nemusí fungovat správně."
                        
                        embed = discord.Embed(title="📊 AKTUÁLNÍ STAV SYSTÉMŮ", color=color, timestamp=get_prague_time())
                        embed.add_field(name="📥 Stahování & Instalace", value=dl_final_msg, inline=False)
                        embed.add_field(name="🗄️ Databáze & Synchronizace", value=s_db, inline=False)
                        embed.add_field(name="💻 Globální provoz Softwaru", value=s_global, inline=False)
                        embed.set_footer(text="Poslední aktualizace")
                        
                        # Pokusíme se najít poslední zprávu a upravit ji, nebo poslat novou
                        last_id_data = db.table("settings").select("setting_value").eq("setting_key", "status_message_id").execute().data
                        msg_sent = False
                        if last_id_data:
                            try:
                                old_msg = await channel.fetch_message(int(last_id_data[0]['setting_value']))
                                await old_msg.edit(embed=embed)
                                msg_sent = True
                            except: pass
                        
                        if not msg_sent:
                            new_msg = await channel.send(embed=embed)
                            db.table("settings").upsert({"setting_key": "status_message_id", "setting_value": str(new_msg.id)}).execute()
                        break

            if bot.loop and bot.loop.is_running():
                asyncio.run_coroutine_threadsafe(send_status_embed(), bot.loop)
                flash('Statusy byly odeslány do kanálu 🛜・status!', 'info')

    except Exception as e:
        flash(f"Chyba při ukládání: {e}", "error")
        
    return redirect(url_for('dashboard_app_management'))

# --- ZBYTEK API A CEST (ZKRÁCENO PRO PŘEHLEDNOST, ALE VŠE ZŮSTÁVÁ) ---

@app.route('/')
def home(): return render_public(HTML_HOME)

@app.route('/dashboard/app_management', methods=['GET'])
def dashboard_app_management():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    soft_enabled = True; dl_enabled = True
    st_dl = ""; st_db = ""; st_global = ""; st_maint = False
    try:
        db = get_db()
        if db:
            res = db.table("settings").select("*").execute().data or []
            for r in res:
                key = r.get('setting_key')
                val = r.get('setting_value')
                if key == 'software_enabled' and str(val).lower() == 'false': soft_enabled = False
                if key == 'downloads_enabled' and str(val).lower() == 'false': dl_enabled = False
                if key == 'status_dl_msg': st_dl = val
                if key == 'status_db_msg': st_db = val
                if key == 'status_global_msg': st_global = val
                if key == 'status_dl_maintenance' and str(val).lower() == 'true': st_maint = True
    except: pass
    return render_dashboard(HTML_APP_MANAGEMENT, soft_enabled=soft_enabled, dl_enabled=dl_enabled, 
                            status_dl=st_dl, status_db=st_db, status_global=st_global, status_dl_manual=st_maint,
                            deploy_time=DEPLOY_TIME)

# ... (Zde by pokračovaly všechny ostatní API a příkazy bota, které už máš funkční) ...

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)
    send_log("🔄 Systém Online", "Bot byl úspěšně restartován. Statusy na Discordu nebyly automaticky odeslány (čekají na manuální trigger).", 0x10b981)
    try: bot.add_view(DynamicDownloadView())
    except: pass

# --- BĚH SYSTÉMU ---

def run_discord_bot(bot_token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(bot.start(bot_token))
        except Exception as e:
            time.sleep(10)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if token: Thread(target=run_discord_bot, args=(token,), daemon=True).start()
    run_web()
