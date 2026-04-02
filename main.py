import os
import time
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
import random
import logging
import io
from werkzeug.exceptions import HTTPException

# BEZPEČNOSTNÍ IMPORT ŠABLON
try:
    from html_templates import *
except ImportError as e:
    print(f"KRITICKÁ CHYBA IMPORTU ŠABLON: {e}")
    BASE_HTML = "<html><body><h1>CHYBA ŠABLON - ZKONTROLUJTE SOUBOR html_templates.py</h1></body></html>"
    PUBLIC_LAYOUT = DASHBOARD_LAYOUT = BASE_HTML
    HTML_HOME = HTML_DOWNLOADS_MAIN = HTML_TEAM = HTML_PUBLIC_STATS = HTML_CLAIM = HTML_STATS = HTML_APP_MANAGEMENT = HTML_NOTIFICATIONS = HTML_DOWNLOADS_MGMT = HTML_PENDING_ROLES = HTML_TEAM_ADD = HTML_IDS = HTML_DASHBOARD_MAIN = HTML_SUPPORTERS_MGMT = HTML_FEEDBACK = HTML_WAIT_AUTH = HTML_LOGIN = ""

# --- TVRDÝ HLÍDAČ ČASU (Vynucení UTC Praha pro celý server Koyebu) ---
os.environ['TZ'] = 'Europe/Prague'
try:
    time.tzset()
except AttributeError:
    pass

try:
    from status_dashboard import HTML_STATUS_SECTION
except ImportError:
    HTML_STATUS_SECTION = ""

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

def stream_proxy_file(file_url_raw, version_name, discord_id, nick):
    urls = [u.strip() for u in file_url_raw.split(',') if u.strip()]
    file_url = random.choice(urls) if urls else file_url_raw

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPRedirectHandler())
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        if "drive.google.com" in file_url and "/d/" in file_url:
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', file_url)
            if match:
                file_id = match.group(1)
                url = f"https://drive.google.com/uc?export=download&id={file_id}"
                req = urllib.request.Request(url, headers=headers)
                resp = opener.open(req, timeout=15)
                
                if 'text/html' in resp.headers.get('Content-Type', '').lower():
                    text = resp.read().decode('utf-8', errors='ignore')
                    token = None
                    for cookie in cj:
                        if cookie.name.startswith("download_warning"):
                            token = cookie.value
                            break
                    if not token:
                        match1 = re.search(r'confirm=([a-zA-Z0-9_-]+)', text)
                        match2 = re.search(r'name="confirm" value="([^"]+)"', text)
                        if match1: token = match1.group(1)
                        elif match2: token = match2.group(1)
                        
                    if token:
                        url = f"{url}&confirm={token}"
                        req = urllib.request.Request(url, headers=headers)
                        resp = opener.open(req, timeout=15)
                    else:
                        send_log("❌ Selhání stahování", f"Úložiště zablokovalo stahování pro hráče `{nick}`.", 0xef4444)
                        return "Chyba: Soubor na Google Drive je buď soukromý, nebo chráněný."
            else:
                req = urllib.request.Request(file_url, headers=headers)
                resp = opener.open(req, timeout=15)
        else:
            if "dropbox.com" in file_url:
                file_url = file_url.replace("dl=0", "dl=1")
                if "dl=1" not in file_url: file_url += "?dl=1" if "?" not in file_url else "&dl=1"
            req = urllib.request.Request(file_url, headers=headers)
            resp = opener.open(req, timeout=15)

        if 'text/html' in resp.headers.get('Content-Type', '').lower():
            send_log("❌ Selhání stahování", f"Úložiště zablokovalo stahování pro hráče `{nick}` (Poslalo HTML místo ZIPu!).", 0xef4444)
            return "Chyba na straně úložiště. Soubor nelze stáhnout."

        def generate():
            try:
                while True:
                    chunk = resp.read(1024 * 128) 
                    if not chunk: break
                    yield chunk
            except Exception as stream_err:
                send_log("⚠️ Spojení přerušeno", f"Uživateli `{nick}` se přerušilo stahování v půlce.\nDůvod: {stream_err}", 0xf59e0b)
            finally:
                resp.close()
                
        resp_headers = {
            'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name.replace(" ", "_")}.zip"',
            'Content-Type': resp.headers.get('Content-Type', 'application/octet-stream')
        }
        if resp.headers.get('Content-Length'):
            resp_headers['Content-Length'] = resp.headers.get('Content-Length')
            
        send_log("✅ Úspěšné stahování", f"Uživatel `{nick}` právě stahuje: **{version_name}**.", 0x10b981)
        return Response(stream_with_context(generate()), headers=resp_headers)
        
    except Exception as e:
        send_log("❌ Selhání stahování", f"Kritická chyba Proxy pro hráče `{nick}`:\n`{e}`", 0xef4444)
        return "Došlo k interní chybě při stahování."

def get_setup_messages(db):
    resp = db.table("settings").select("setting_value").eq("setting_key", "setup_messages").execute()
    if not resp.data: return []
    try: return json.loads(resp.data[0]['setting_value'])
    except: return []

def save_setup_message(db, channel_id, message_id):
    msgs = get_setup_messages(db)
    msgs.append({"channel_id": str(channel_id), "message_id": str(message_id)})
    msgs = msgs[-15:]
    check = db.table("settings").select("*").eq("setting_key", "setup_messages").execute().data
    if not check:
        db.table("settings").insert({"setting_key": "setup_messages", "setting_value": json.dumps(msgs)}).execute()
    else:
        db.table("settings").update({"setting_value": json.dumps(msgs)}).eq("setting_key", "setup_messages").execute()

def build_setup_embed(db):
    settings_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}]
    dl_enabled = str(settings_resp[0].get('setting_value', '')).lower() != 'false'
    
    embed = discord.Embed(title="📥 Projekt OIS IDPK - Instalace", description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a stahování.\n**Při stahování se automaticky přihlásíte do databáze.**\n*(Stahování lze ve vašem prohlížeči kdykoliv pozastavit a obnovit)*", color=0x38bdf8)
    
    if not dl_enabled:
        embed.color = 0xef4444
        embed.add_field(name="⛔ STAHOVÁNÍ JE NYNÍ VYPNUTO", value="Administrátor dočasně zakázal stahování. Zkuste to prosím později.", inline=False)
        return embed

    versions = db.table("software_versions").select("*").eq("is_active", True).order("id", desc=True).execute().data or []
    now = get_prague_time().replace(tzinfo=None)
    
    def format_version(v):
        eol_str = v.get('eol_date', '').strip()
        if eol_str:
            try:
                eol_dt = datetime.strptime(eol_str, "%d.%m.%Y")
                days_left = (eol_dt - now).days
                if days_left <= 14:
                    return f"~~• {v['version_name']}~~ ❌ *(Stahování ukončeno - blížící se konec podpory {eol_str})*"
                else:
                    return f"• {v['version_name']} ⚠️ *(Končí podpora: {eol_str})*"
            except:
                pass
        return f"• {v['version_name']}"

    user_v = [format_version(v) for v in versions if v['target_role'] == 'User']
    bt_v = [format_version(v) for v in versions if v['target_role'] == 'BT']
    
    if user_v: embed.add_field(name="🌍 Dostupné pro všechny (User)", value="\n".join(user_v), inline=False)
    if bt_v: embed.add_field(name="🛠️ Dostupné pro Beta Testery (BT)", value="\n".join(bt_v), inline=False)
    if not user_v and not bt_v: embed.add_field(name="Zatím nejsou dostupné žádné veřejné verze.", value="-", inline=False)
        
    embed.set_footer(text="Neveřejné verze jsou skryté. Pokud máte BAN, systém vás ke stahování nepustí.")
    return embed

async def update_setup_messages_async():
    if not bot.is_ready(): return
    db = get_db()
    if not db: return
    msgs = get_setup_messages(db)
    if not msgs: return
    
    embed = build_setup_embed(db)
    valid_msgs = []
    
    for m in msgs:
        try:
            channel = bot.get_channel(int(m['channel_id'])) or await bot.fetch_channel(int(m['channel_id']))
            if channel:
                msg = await channel.fetch_message(int(m['message_id']))
                await msg.edit(embed=embed)
                valid_msgs.append(m)
        except Exception as e: pass
        
    db.table("settings").update({"setting_value": json.dumps(valid_msgs)}).eq("setting_key", "setup_messages").execute()

def trigger_setup_messages_update():
    if bot.loop and bot.loop.is_running() and bot.is_ready():
        asyncio.run_coroutine_threadsafe(update_setup_messages_async(), bot.loop)

def process_supporters(data_list):
    for s in data_list:
        amt_str = str(s.get('amount', '0'))
        match = re.search(r'([\d\.,]+)', amt_str)
        val = 0.0
        if match:
            try: val = float(match.group(1).replace(',', '.'))
            except: pass
        norm_val = val
        if 'usd' in amt_str.lower() or '$' in amt_str.lower(): norm_val *= 23
        elif 'eur' in amt_str.lower() or '€' in amt_str.lower(): norm_val *= 25
        s['norm_val'] = norm_val
        if norm_val >= 325: s['tier'] = 3
        elif norm_val >= 195: s['tier'] = 2
        else: s['tier'] = 1
    data_list.sort(key=lambda x: (x.get('norm_val', 0), x.get('id', 0)), reverse=True)
    return data_list

def calculate_roles_for_supporter(amount_str):
    match = re.search(r'([\d\.,]+)', str(amount_str))
    val = 0.0
    if match:
        try: val = float(match.group(1).replace(',', '.'))
        except: pass
    if 'usd' in str(amount_str).lower() or '$' in str(amount_str).lower(): val *= 23
    elif 'eur' in str(amount_str).lower() or '€' in str(amount_str).lower(): val *= 25
    if val >= 325: tier_role = "⭐| MEGA PODPOROVATEL"
    elif val >= 195: tier_role = "⭐| VELKÝ PODPOROVATEL"
    else: tier_role = "⭐| PODPOROVATEL"
    return ["🎖️| Beta tester", tier_role], f"BT,{tier_role}"

def user_exists_sync(identifier):
    try:
        if not bot.is_ready(): return False
        for guild in bot.guilds:
            if identifier.isdigit():
                member = guild.get_member(int(identifier))
                if member: return True
            member = discord.utils.find(lambda m: m.name.lower() == identifier.lower() or (m.global_name and m.global_name.lower() == identifier.lower()), guild.members)
            if member: return True
    except: pass
    return False

async def send_user_dm(discord_identifier, title, description, color=0x38bdf8):
    if not discord_identifier or not bot.is_ready(): return
    try:
        for guild in bot.guilds:
            member = guild.get_member(int(discord_identifier)) if discord_identifier.isdigit() else None
            if not member: member = discord.utils.find(lambda m: m.name.lower() == discord_identifier.lower() or (m.global_name and m.global_name.lower() == discord_identifier.lower()), guild.members)
            if member:
                await member.send(embed=discord.Embed(title=title, description=description, color=color))
                return
    except: pass

async def assign_supporter_role(identifier, role_names_list):
    success = False
    if not bot.is_ready(): return False
    try:
        for guild in bot.guilds:
            member = guild.get_member(int(identifier)) if identifier.isdigit() else None
            if not member: member = discord.utils.find(lambda m: m.name.lower() == identifier.lower() or (m.global_name and m.global_name.lower() == identifier.lower()), guild.members)
            if member:
                assigned_any = False
                for r_name in role_names_list:
                    role = discord.utils.get(guild.roles, name=r_name)
                    if role:
                        await member.add_roles(role)
                        assigned_any = True
                if assigned_any:
                    success = True
                    try:
                        roles_str = "\n".join([f"**{r}**" for r in role_names_list])
                        await member.send(embed=discord.Embed(title="🎉 Děkujeme za obrovskou podporu!", description=f"Na našem Discord serveru a v databázi ti byly automaticky přiděleny tyto exkluzivní role:\n\n{roles_str}\n\nMoc si toho vážíme!", color=0x38bdf8))
                    except: pass
                break
    except: pass
    return success

async def announce_new_supporter(discord_nick, amount_str, message, role_names_list):
    if not bot.is_ready(): return
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="⭐・podporovatelé")
        if channel:
            roles_str = ", ".join([f"**{r}**" for r in role_names_list])
            embed = discord.Embed(title="🎉 MÁME NOVÉHO PODPOROVATELE!", description=f"Uživatel **{discord_nick}** právě podpořil náš projekt a získal exkluzivní role {roles_str} na serveru i v aplikaci!", color=0xf59e0b)
            embed.add_field(name="💰 Výše podpory", value=f"**{amount_str}**", inline=False)
            if message and message.strip(): embed.add_field(name="📝 Vzkaz od podporovatele", value=f"*{message}*", inline=False)
            embed.set_footer(text="Obrovsky děkujeme za Vaši podporu! ❤️ Projekt OIS IDPK")
            try: await channel.send(embed=embed)
            except: pass
            break

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
    if request.path.startswith('/dashboard') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize'] and session.get('logged_in'):
        discord_id = session.get('discord_id')
        if discord_id:
            try:
                db = get_db()
                if db:
                    users_data = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                    if users_data:
                        user = users_data[0]
                        if not user.get("dashboard_access") or user.get("is_banned") or user.get("is_deleted"):
                            session.clear()
                            flash('Váš přístup byl zablokován.', 'error')
                            return redirect(url_for('dashboard_main'))
            except: pass

async def update_member_roles(member, role_string):
    if not member or not role_string: return
    try:
        roles_to_assign = [r.strip() for r in role_string.split(',') if r.strip()]
        for r_name in roles_to_assign:
            role = discord.utils.get(member.guild.roles, name=r_name)
            if role and role not in member.roles:
                await member.add_roles(role)
    except Exception as e:
        print(f"Chyba při updatu rolí pro {member.display_name}: {e}", flush=True)

def sync_roles_from_flask(discord_id, role_string):
    async def sync():
        if not bot.is_ready(): return
        try:
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id)) or await guild.fetch_member(int(discord_id))
                if member: await update_member_roles(member, role_string)
        except: pass
    if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(sync(), bot.loop)

def check_version_access(db, app_version_from_pc, user):
    if user.get("admin_bypass") == True:
        return {"allowed": True}

    user_role_str = user.get("role", "")
    if not app_version_from_pc or str(app_version_from_pc).strip() == "": 
        return {"allowed": False, "msg": "Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
    
    try:
        v_data = db.table("software_versions").select("*").eq("db_version", app_version_from_pc).execute().data
        if not v_data: return {"allowed": False, "msg": f"Verze '{app_version_from_pc}' neexistuje v databázi! Stáhněte si aktuální verzi z našeho Discordu."}
        
        v_info = v_data[0]
        if str(v_info.get("is_active", "True")).lower() == "false":
            return {"allowed": False, "msg": f"Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
            
        eol = v_info.get("eol_date")
        if eol and str(eol).strip():
            try:
                eol_dt = datetime.strptime(str(eol).strip(), "%d.%m.%Y")
                if get_prague_time().replace(tzinfo=None) > eol_dt:
                    db.table("software_versions").update({"is_active": False}).eq("id", v_info["id"]).execute()
                    return {"allowed": False, "msg": f"Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
            except Exception as d_err:
                pass 

        target = v_info.get("target_role", "User")
        if target != "User":
            roles = [r.strip() for r in user_role_str.split(",")] if user_role_str else []
            if "SA" not in roles and "DEV" not in roles:
                if target == "BT" and "BT" not in roles:
                    return {"allowed": False, "msg": f"Tato verze je omezena pouze pro Beta Testery. Nemáte dostatečné oprávnění."}
                elif target == "DEV_SA":
                    return {"allowed": False, "msg": f"Tato verze je neveřejná. Nemáte dostatečné oprávnění pro její spuštění."}

        return {"allowed": True}
    except Exception as e:
        return {"allowed": True}

@app.route('/api/keepalive', methods=['GET', 'OPTIONS'])
def api_keepalive():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    return _cors_jsonify({"status": "alive", "time": get_prague_time().strftime("%d.%m.%Y %H:%M:%S")})

# === PŘIJÍMAČ CHYB Z APLIKACE DO DISCORDU ===
@app.route('/api/report_error', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_report_error():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", "Neznámé ID"))
    nick = str(data.get("nick", "Neznámý"))
    error_type = str(data.get("type", "ERROR"))
    msg = str(data.get("message", "Neznámá chyba"))
    
    if bot.loop and bot.loop.is_running() and bot.is_ready():
        async def send_err():
            for guild in bot.guilds:
                channel = discord.utils.get(guild.channels, name="📲・error-app")
                if channel:
                    embed = discord.Embed(title=f"⚠️ APLIKAČNÍ CHYBA: {error_type}", description=f"**Hráč:** {nick} (`{discord_id}`)\n**Chyba:**\n`{msg}`", color=0xef4444, timestamp=get_prague_time())
                    try: await channel.send(embed=embed)
                    except: pass
                    break
        asyncio.run_coroutine_threadsafe(send_err(), bot.loop)
    return _cors_jsonify({"status": "success"})

# === PŘIJÍMAČ STATISTIK ===
@app.route('/api/submit_stats', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_submit_stats():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    line = str(data.get("line", "")).strip()
    stops = data.get("stops", [])
    discord_id = str(data.get("discord_id", "")).strip()
    
    db = get_db()
    if not db or not line: return _cors_jsonify({"status": "error"})
    
    try:
        # Globální
        try:
            line_res = db.table("stats_lines").select("*").eq("line_name", line).execute().data
            if line_res: db.table("stats_lines").update({"play_count": int(line_res[0].get("play_count", 0)) + 1}).eq("id", line_res[0]["id"]).execute()
            else: db.table("stats_lines").insert({"line_name": line, "play_count": 1}).execute()
        except: pass
            
        for stop in stops:
            stop_name = str(stop).strip()
            if not stop_name: continue
            try:
                stop_res = db.table("stats_stops").select("*").eq("stop_name", stop_name).execute().data
                if stop_res: db.table("stats_stops").update({"announce_count": int(stop_res[0].get("announce_count", 0)) + 1}).eq("id", stop_res[0]["id"]).execute()
                else: db.table("stats_stops").insert({"stop_name": stop_name, "announce_count": 1}).execute()
            except: pass
        
        # Osobní (pokud máme ID hráče)
        if discord_id and discord_id != "None" and discord_id != "":
            try:
                u_line_res = db.table("user_stats_lines").select("*").eq("discord_id", discord_id).eq("line_name", line).execute().data
                if u_line_res: db.table("user_stats_lines").update({"play_count": int(u_line_res[0].get("play_count", 0)) + 1}).eq("id", u_line_res[0]["id"]).execute()
                else: db.table("user_stats_lines").insert({"discord_id": discord_id, "line_name": line, "play_count": 1}).execute()
            except Exception as e: print(f"Osobní statistiky (linky) selhaly: {e}")
                
            for stop in stops:
                stop_name = str(stop).strip()
                if not stop_name: continue
                try:
                    u_stop_res = db.table("user_stats_stops").select("*").eq("discord_id", discord_id).eq("stop_name", stop_name).execute().data
                    if u_stop_res: db.table("user_stats_stops").update({"announce_count": int(u_stop_res[0].get("announce_count", 0)) + 1}).eq("id", u_stop_res[0]["id"]).execute()
                    else: db.table("user_stats_stops").insert({"discord_id": discord_id, "stop_name": stop_name, "announce_count": 1}).execute()
                except Exception as e:
                    print(f"Osobní statistiky (zastávky) selhaly: {e}")
                    break 

        return _cors_jsonify({"status": "success"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/')
def home(): 
    def log_visit(ip, cf_country):
        try:
            if not ip or ip in ["127.0.0.1", "::1", "0.0.0.0"]: return
            clean_ip = ip.split(',')[0].strip()
            db = get_db()
            if not db: return
            today_str = get_prague_time().strftime("%d.%m.%Y")
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            existing = db.table("page_visits").select("visited_at").eq("ip", clean_ip).execute().data or []
            for record in existing:
                if record.get("visited_at", "").startswith(today_str): return
            country_name = cf_country; region = ""; country_code = ""
            try:
                url = f"http://ip-api.com/json/{clean_ip}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    geo_data = json.loads(response.read().decode())
                    if geo_data.get("status") == "success":
                        country_name = geo_data.get("country", country_name)
                        region = geo_data.get("regionName", "")
                        country_code = geo_data.get("countryCode", "").lower()
            except: pass
            if not country_code or country_code.lower() == 'us' or country_name.lower() in ["neznámá", "unknown", "none", "united states", "us"]: return 
            combined_location = f"{country_code}|{country_name}|{region}"
            db.table("page_visits").insert({"ip": clean_ip, "country": combined_location, "visited_at": now_str}).execute()
        except: pass
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    country = request.headers.get('CF-IPCountry', 'Neznámá')
    Thread(target=log_visit, args=(ip, country)).start()
    return render_public(HTML_HOME)

@app.route('/download')
def download_home(): return render_public(HTML_DOWNLOADS_MAIN)

@app.route('/team')
def team(): 
    try: team_members = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except: team_members = []
    return render_public(HTML_TEAM, team=team_members)

@app.route('/supporters')
def supporters():
    support_data = []
    try: 
        db = get_db()
        if db:
            data = db.table("supporters").select("*").eq("status", "completed").execute().data or []
            support_data = process_supporters(data)
    except: pass
    return render_public(HTML_SUPPORTERS, supporters=support_data)

@app.route('/stats', methods=['GET'])
def public_stats():
    db = get_db()
    if not db:
        flash("Databáze není dostupná.", "error")
        return redirect(url_for('home'))
    
    search_query = request.args.get('q', '').strip()
    searched_user = None
    all_users = db.table("users").select("*").execute().data or []
    
    if search_query:
        for u in all_users:
            if str(u.get('discord_id')) == search_query or str(u.get('nick', '')).lower() == search_query.lower():
                searched_user = u
                break
        if not searched_user:
            flash(f"Hráč s ID nebo Nickem '{search_query}' nebyl nalezen.", "warning")
            
    versions = db.table("software_versions").select("*").eq("is_active", True).order("id", desc=True).execute().data or []
    user_ver = next((v['version_name'] for v in versions if v['target_role'] == 'User'), "Žádná")
    bt_ver = next((v['version_name'] for v in versions if v['target_role'] == 'BT'), "Žádná")
    
    activated_users = len([u for u in all_users if u.get('hwid') and str(u.get('hwid')) not in ['None', '']])
    
    total_time_mins = 0
    total_launches = 0
    for u in all_users:
        try:
            t = u.get('total_time')
            if t: total_time_mins += int(t)
        except: pass
        try:
            l = u.get('launch_count')
            if l: total_launches += int(l)
        except: pass
        
    total_hours = total_time_mins // 60
    
    today_str = get_prague_time().strftime("%d.%m.%Y")
    sessions_today = db.table("app_sessions").select("start_time, end_time").like("start_time", f"{today_str}%").execute().data or []
    today_mins = 0
    for s in sessions_today:
        try:
            st_str = s.get('start_time')
            et_str = s.get('end_time')
            if st_str and et_str:
                fmt_st = "%d.%m.%Y %H:%M:%S" if st_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                fmt_et = "%d.%m.%Y %H:%M:%S" if et_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                st = datetime.strptime(st_str, fmt_st)
                et = datetime.strptime(et_str, fmt_et)
                diff = int((et - st).total_seconds() / 60)
                if diff > 0: today_mins += diff
        except: pass
    today_hours = today_mins // 60
    today_rem_mins = today_mins % 60
    today_time_str = f"{today_hours}h {today_rem_mins}m" if today_hours > 0 else f"{today_rem_mins}m"
    
    supporters_data = db.table("supporters").select("id").eq("status", "completed").execute().data or []
    total_supporters = len(supporters_data)
    
    valid_time_users = [u for u in all_users if int(u.get('total_time') or 0) > 0]
    top_time_users = sorted(valid_time_users, key=lambda x: int(x.get('total_time') or 0), reverse=True)[:3]
    
    valid_launch_users = [u for u in all_users if int(u.get('launch_count') or 0) > 0]
    top_launches = sorted(valid_launch_users, key=lambda x: int(x.get('launch_count') or 0), reverse=True)[:3]
    
    try:
        top_lines = db.table("stats_lines").select("*").order("play_count", desc=True).limit(10).execute().data or []
        top_stops = db.table("stats_stops").select("*").order("announce_count", desc=True).limit(10).execute().data or []
        all_lines = db.table("stats_lines").select("*").order("play_count", desc=True).execute().data or []
        all_stops = db.table("stats_stops").select("*").order("announce_count", desc=True).execute().data or []
    except Exception as e:
        print(f"Chyba při načítání globálních statistik: {e}")
        top_lines, top_stops, all_lines, all_stops = [], [], [], []
    
    searched_user_lines = []
    searched_user_stops = []
    if searched_user:
        d_id = searched_user.get('discord_id')
        try:
            searched_user_lines = db.table("user_stats_lines").select("*").eq("discord_id", d_id).order("play_count", desc=True).limit(5).execute().data or []
            searched_user_stops = db.table("user_stats_stops").select("*").eq("discord_id", d_id).order("announce_count", desc=True).limit(5).execute().data or []
        except Exception as e:
            print(f"Chyba při načítání osobních statistik pro /stats: {e}")
    
    return render_public(HTML_PUBLIC_STATS, 
                         user_ver=user_ver, bt_ver=bt_ver, 
                         activated_users=activated_users, 
                         total_supporters=total_supporters,
                         today_time_str=today_time_str, 
                         total_hours=total_hours,
                         total_launches=total_launches,
                         top_time=top_time_users, top_launches=top_launches,
                         top_lines=top_lines, top_stops=top_stops,
                         all_lines=all_lines, all_stops=all_stops,
                         searched_user=searched_user,
                         searched_user_lines=searched_user_lines,
                         searched_user_stops=searched_user_stops)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    try:
        db = get_db()
        if not db: return _cors_jsonify({"error": "DB not ready"}), 500
        data = db.table("supporters").select("name, amount, message, created_at").eq("status", "completed").execute().data or []
        support_data = process_supporters(data)
        return _cors_jsonify({"supporters": support_data})
    except Exception as e:
        return _cors_jsonify({"error": str(e)}), 500

@app.route('/claim', methods=['GET', 'POST'])
def claim_role():
    if request.method == 'POST':
        bmac_name = request.form.get('bmac_name', '').strip()
        discord_nick = request.form.get('discord_nick', '').strip()
        db = get_db()
        if not db: 
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('claim_role'))
        all_records = db.table("supporters").select("*").eq("name", bmac_name).execute().data
        if any(r['status'] == 'completed' for r in all_records):
            send_log("⚠️ Pokus o zneužití (Double Claim)", f"Uživatel **{discord_nick}** se pokusil znovu použít BMAC jméno **{bmac_name}**!", 0xef4444)
            flash('Chyba: Platba pod tímto jménem již byla spárována!', 'error')
            return redirect(url_for('claim_role'))
        valid_records = []; expired_records = []
        now = get_prague_time().replace(tzinfo=None)
        for r in all_records:
            if r['status'] == 'pending': valid_records.append(r)
            elif r['status'] == 'manual_review':
                try:
                    c_time = datetime.strptime(r['created_at'], "%d.%m.%Y %H:%M")
                    if (now - c_time).total_seconds() <= 86400: valid_records.append(r)
                    else: expired_records.append(r)
                except: valid_records.append(r)
        if valid_records:
            record = valid_records[0]; old_status = record['status']
            discord_roles, db_role_string = calculate_roles_for_supporter(record.get('amount', '0'))
            if user_exists_sync(discord_nick):
                if bot.loop and bot.loop.is_running() and bot.is_ready():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
                    asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_nick, record.get('amount', '0'), record.get('message', ''), discord_roles), bot.loop)
                new_sys_note = "Spárováno (zachráněno z kontroly)" if old_status == "manual_review" else "Spárováno včas"
                db.table("supporters").update({"status": "completed", "discord_nick": discord_nick, "sys_note": new_sys_note}).eq("id", record['id']).execute()
                send_log("✅ Role vyzvednuta", f"Uživatel **{discord_nick}** úspěšně spároval BMAC od **{bmac_name}**.", 0x10b981)
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_nick},nick.ilike.{discord_nick}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                    for new_r in db_role_string.split(','):
                        if new_r.strip() not in roles_list: roles_list.append(new_r.strip())
                    db.table("users").update({"role": ",".join(roles_list)}).eq("discord_id", db_user[0]['discord_id']).execute()
                else: db.table("pending_roles").insert({"discord_identifier": discord_nick, "roles": db_role_string}).execute()
                flash('Úspěch! Role přidělena.', 'success')
            else:
                db.table("supporters").update({"status": "manual_review", "discord_nick": discord_nick, "sys_note": "Účet nenalezen."}).eq("id", record['id']).execute()
                send_log("⚠️ Žádost o kontrolu", f"Uživatel **{discord_nick}** nenalezen na serveru. Manuální kontrola.", 0xf59e0b)
                flash('Discord účet nenalezen! Odesláno administrátorovi.', 'warning')
        else:
            if expired_records: flash('Časový limit 24 hodin vypršel. Čeká se na manuální schválení.', 'warning')
            elif any(r['status'] == 'manual_review' for r in all_records): flash('Tato platba již čeká na manuální schválení.', 'warning')
            else:
                db.table("supporters").insert({"name": bmac_name, "discord_nick": discord_nick, "amount": "Neznámá", "message": "", "sys_note": "Nezaznamenáno z BMAC.", "status": "manual_review", "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
                send_log("🚨 VYŽADUJE KONTROLU: Neznámá platba 🚨", f"Uživatel **{discord_nick}** žádá o platbu od **{bmac_name}**, ale webhookem neprošla.\n\n👉 **BĚŽTE DO DASHBOARDU A ZKONTROLUJTE TO!**", 0xef4444)
                flash('Platba nenalezena. Odesláno administrátorovi k ruční kontrole.', 'warning')
        return redirect(url_for('claim_role'))
    return render_public(HTML_CLAIM)

@app.route('/webhook/bmac', methods=['GET', 'POST', 'OPTIONS'])
def bmac_webhook():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            data = payload.get('data', payload) if isinstance(payload, dict) else {}
        else: data = request.args
        name = data.get('supporter_name') or data.get('payer_name') or data.get('name') or 'Anonymní dárce'
        message = data.get('support_note') or data.get('message') or ''
        amount_val = data.get('amount') or data.get('support_coffees') or 1
        currency = data.get('currency') or 'CZK'
        amount_str = f"{amount_val} {currency}"
        discord_roles, db_role_string = calculate_roles_for_supporter(amount_str)
        discord_identifier = None
        id_match = re.search(r'\b\d{17,19}\b', message)
        if id_match: discord_identifier = id_match.group(0)
        else:
            nick_match = re.search(r'(?i)(?:discord|dc|nick)[\s:]+([a-zA-Z0-9_.-]+)', message)
            if nick_match: discord_identifier = nick_match.group(1).strip()
        db = get_db()
        if db:
            status = 'pending'; sys_note = "Čeká na spárování."
            if discord_identifier and user_exists_sync(discord_identifier):
                status = 'completed'; sys_note = "Automaticky spárováno."
            db.table("supporters").insert({"name": str(name), "message": str(message), "amount": str(amount_str), "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "status": status, "sys_note": sys_note, "discord_nick": discord_identifier or ""}).execute()
            send_log("🍕 Nová platba zaznamenána!", f"Uživatel **{name}** poslal **{amount_str}**.\nZpráva: *{message}*\n\nStatus: `{status}`", 0xF4CC17)
            if status == 'completed':
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_identifier},nick.ilike.{discord_identifier}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                    for new_r in db_role_string.split(','):
                        if new_r.strip() not in roles_list: roles_list.append(new_r.strip())
                    db.table("users").update({"role": ",".join(roles_list)}).eq("discord_id", db_user[0]['discord_id']).execute()
                else: db.table("pending_roles").insert({"discord_identifier": discord_identifier, "roles": db_role_string}).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_identifier, discord_roles), bot.loop)
                    asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_identifier, amount_str, message, discord_roles), bot.loop)
        if request.method == 'GET': return f"<h1>ÚSPĚCH! 🎉</h1>"
        return jsonify({"status": "success"}), 200
    except Exception as e:
        if request.method == 'GET': return f"<h1>❌ CHYBA DATABÁZE</h1><p><b>Důvod:</b> {str(e)}</p>"
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db: return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if not resp.data: return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný odkaz, nebo již vypršel!</h2><p style='color: #aaa;'>Vraťte se na Discord a vygenerujte si odkaz znovu.</p></div>")
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"): return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Přístup zamítnut</h2></div>")
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data: return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--warning);'>Chyba verze</h2></div>")
        v_data = v_resp.data[0]
        
        html = f"""<div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; border-top: 4px solid var(--success);">
            <h2 style="color: var(--success); margin-top: 0;"><i class="fas fa-check-circle"></i> Ověření úspěšné</h2>
            <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Přihlášen jako: <strong>{user.get('nick', '')}</strong></p>
            
            <div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;">
                <h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3>
                <p style="margin: 0; color: var(--text-main);">Instalátor: <strong>{v_data.get('version_name', '')}</strong></p>
            </div>
            
            <div id="download-area">
                <a href="#" onclick="startDownload()" class="btn btn-success" style="font-size: 18px; padding: 15px 30px; display: inline-block;" id="dl-btn">
                    <i class="fas fa-download"></i> Stáhnout Soubor
                </a>
            </div>
            
            <div id="loading-area" style="display: none;">
                <div class="spinner" style="margin: 0 auto 10px auto; border-color: rgba(16, 185, 129, 0.3); border-top-color: #10b981;"></div>
                <p style="color: var(--text-main); font-weight: bold;">Zahajuji stahování...</p>
                <p style="color: var(--text-muted); font-size: 12px;">Generuji bezpečné připojení...</p>
            </div>
            
            <div id="success-area" style="display: none; margin-top: 20px;">
                <h3 style="color: var(--success); margin-top: 0;"><i class="fas fa-check"></i> Úspěšně zahájeno</h3>
                <p style="color: var(--text-main); font-size: 14px; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border-left: 3px solid var(--blue-main);">
                    Stahování běží. Po stažení souboru jej nezapomeňte rozbalit pomocí programů jako <b>7-ZIP</b> nebo <b>WinRAR</b>.
                </p>
            </div>
            
            <div id="error-area" style="display: none; margin-top: 20px;">
                <h3 style="color: var(--danger); margin-top: 0;"><i class="fas fa-times-circle"></i> Stahování se nezdařilo</h3>
                <p style="color: var(--text-main); font-size: 14px; background: rgba(239,68,68,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid var(--danger);">
                    Omlouváme se, stahování nebylo možné spustit.<br><b>Důvod:</b> <span id="error-msg"></span><br><br>Zkuste to prosím později, administrátor byl o chybě informován do logu.
                </p>
            </div>
            
            <style>
                .spinner {{ width: 40px; height: 40px; border: 4px solid; border-radius: 50%; animation: spin 1s linear infinite; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
            
            <script>
            async function startDownload() {{
                document.getElementById('download-area').style.display = 'none';
                document.getElementById('loading-area').style.display = 'block';
                
                try {{
                    let response = await fetch("/api/pre_download/{token}?v={version_id}");
                    let data = await response.json();
                    
                    if (data.status === 'ok') {{
                        window.location.href = "/api/stream_download/{token}?v={version_id}";
                        setTimeout(() => {{
                            document.getElementById('loading-area').style.display = 'none';
                            document.getElementById('success-area').style.display = 'block';
                        }}, 2000);
                    }} else {{
                        document.getElementById('loading-area').style.display = 'none';
                        document.getElementById('error-area').style.display = 'block';
                        document.getElementById('error-msg').innerText = data.message || "Neznámá chyba na serveru.";
                    }}
                }} catch(e) {{
                    document.getElementById('loading-area').style.display = 'none';
                    document.getElementById('error-area').style.display = 'block';
                    document.getElementById('error-msg').innerText = "Chyba připojení k serveru.";
                }}
            }}
            </script>
        </div>"""
        return render_public(html)
    except: return "Systémová chyba."

@app.route('/api/pre_download/<token>')
def api_pre_download(token):
    db = get_db()
    if not db: return jsonify({"status": "error", "message": "Chyba databáze."})
    
    resp = db.table("users").select("*").eq("download_token", token).execute()
    if not resp.data:
        send_log("⚠️ Neplatný odkaz", "Někdo se pokusil použít propadlý nebo cizí odkaz na stahování.", 0xf59e0b)
        return jsonify({"status": "error", "message": "Neplatný nebo vypršelý odkaz. Vygenerujte si na Discordu nový."})
        
    user = resp.data[0]
    if user.get("is_banned") or user.get("is_deleted"):
        send_log("⛔ Zablokovaný přístup", f"Zablokovaný uživatel `{user.get('nick')}` se pokusil stahovat.", 0xef4444)
        return jsonify({"status": "error", "message": "Přístup zamítnut administrátorem."})
        
    version_id = request.args.get('v')
    v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
    if not v_resp.data:
        send_log("❌ Selhání stahování", f"Hráč `{user.get('nick')}` zkusil stáhnout verzi, která už neexistuje v DB.", 0xef4444)
        return jsonify({"status": "error", "message": "Tato verze již není k dispozici."})
        
    now_prague = get_prague_time()
    last_log = db.table("download_logs").select("*").eq("discord_id", user['discord_id']).order("id", desc=True).limit(1).execute().data
    if last_log:
        try:
            time_str = last_log[0]['downloaded_at']
            if time_str.count(':') == 2: last_dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M:%S")
            else: last_dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
            if (now_prague - last_dt).total_seconds() < 30:
                send_log("🛑 SPAM Ochrana", f"Uživatel `{user.get('nick')}` klikal na stahování příliš rychle.", 0xf59e0b)
                return jsonify({"status": "error", "message": "Detekován SPAM! Počkejte 30 vteřin před dalším stažením."})
        except: pass
        
    return jsonify({"status": "ok"})

@app.route('/api/stream_download/<token>')
def api_stream_download(token):
    db = get_db()
    if not db: return "Chyba databáze."
    
    resp = db.table("users").select("*").eq("download_token", token).execute()
    if not resp.data: return "Neplatný odkaz."
    user = resp.data[0]
    
    version_id = request.args.get('v')
    v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
    if not v_resp.data: return "Verze nenalezena."
    
    v_data = v_resp.data[0]
    file_url_raw = v_data['file_url']
    version_name = v_data['version_name']
    
    db.table("users").update({"download_token": ""}).eq("discord_id", user['discord_id']).execute()
    
    try:
        db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": version_name, "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M:%S")}).execute()
    except: pass
    
    return stream_proxy_file(file_url_raw, version_name, user['discord_id'], user.get('nick', 'Neznámý'))

@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_status():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    try:
        db = get_db()
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "disabled", "message": "OMLOUVÁME SE, SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA)."})
    except: pass
    return _cors_jsonify({"status": "enabled"})

@app.route('/api/app_login', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_login():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    if not data: return _cors_jsonify({"status": "error", "message": "Chybí data."})
    
    identifier = str(data.get("identifier", "")).strip()
    req_hwid = str(data.get("hwid", ""))
    app_version = str(data.get("app_version", ""))
    db = get_db()
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
            
        client_ip_raw = request.headers.get('X-Forwarded-For', request.remote_addr)
        client_ip = client_ip_raw.split(',')[0].strip() if client_ip_raw else "Neznámá"
        
        if identifier.isdigit():
            user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},app_id.eq.{int(identifier)}").execute()
        else:
            user_resp = db.table("users").select("*").eq("nick", identifier).execute()
            
        if not user_resp.data: 
            return _cors_jsonify({"status": "error", "message": "Uživatel nenalezen. Pokud má váš Nick speciální znaky, použijte k přihlášení raději číselné Discord ID."})
            
        user = user_resp.data[0]
        discord_id = user.get("discord_id")
        
        if user.get("is_banned"):
            send_log("⛔ Pokus o přihlášení (BAN)", f"Zabanovaný uživatel `{user.get('nick')}` se pokusil zapnout software.", 0xef4444)
            return _cors_jsonify({"status": "banned", "message": "Tento účet má BAN."})
            
        version_check = check_version_access(db, app_version, user)
        if not version_check["allowed"]:
            send_log("🛡️ Neoprávněný přístup verze", f"Uživatel `{user.get('nick')}` se pokusil zapnout zakázanou/neoprávněnou verzi: **{app_version}**", 0xf59e0b)
            return _cors_jsonify({"status": "error", "message": version_check["msg"]})
            
        db_hwid = user.get("hwid")
        db_ip = user.get("ip_address")
        
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                db.table("users").update({"hwid": req_hwid, "ip_address": client_ip}).eq("discord_id", discord_id).execute()
        else:
            if str(db_hwid) != req_hwid:
                if db_ip and str(db_ip).strip() != "" and str(db_ip) == client_ip:
                    db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                    send_log("🔄 HWID Auto-oprava", f"Uživateli `{user.get('nick')}` se změnilo HWID, ale IP adresa souhlasila. HWID bylo automaticky aktualizováno.", 0x38bdf8)
                else:
                    send_log("🔒 Zámek (HWID+IP)", f"Uživatel `{user.get('nick')}` se hlásí z cizího PC i sítě!\nUloženo HWID: `{db_hwid}` | IP: `{db_ip}`\nNové HWID: `{req_hwid}` | IP: `{client_ip}`", 0xf59e0b)
                    return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK: Váš počítač ani IP adresa nesouhlasí s registrací."})
            else:
                if not db_ip or str(db_ip).strip() == "":
                    db.table("users").update({"ip_address": client_ip}).eq("discord_id", discord_id).execute()
        
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
        async def send():
            try:
                u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                if u: await u.send(embed=discord.Embed(title="🛡️ Ověření přihlášení", description=f"Byl zaznamenán pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPotvrďte přístup tlačítkem níže.", color=0x38bdf8), view=AppAuthView(token, discord_id, is_dm=True))
            except: pass
        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
        return _cors_jsonify({"status": "waiting", "discord_id": discord_id})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    try:
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        user = user_resp.data[0]
        if user.get("login_token") == "approved":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "success", "display_name": user.get("nick"), "app_id": str(user.get("app_id", ""))})
        elif user.get("login_token") == "rejected":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."})
        return _cors_jsonify({"status": "pending"})
    except: return _cors_jsonify({"status": "error"})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    app_version = str(data.get("app_version", ""))
    db = get_db()
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false': return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
        
        client_ip_raw = request.headers.get('X-Forwarded-For', request.remote_addr)
        client_ip = client_ip_raw.split(',')[0].strip() if client_ip_raw else "Neznámá"
        
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error", "message": "Tento účet neexistuje."})
        user = user_resp.data[0]
        
        if user.get("is_banned"): return _cors_jsonify({"status": "error", "message": "Tento účet má BAN."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán."})
        
        version_check = check_version_access(db, app_version, user)
        if not version_check["allowed"]:
            return _cors_jsonify({"status": "error", "message": version_check["msg"]})
            
        db_hwid = user.get("hwid")
        db_ip = user.get("ip_address")
        
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                db.table("users").update({"hwid": req_hwid, "ip_address": client_ip}).eq("discord_id", discord_id).execute()
                return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Chyba čtení PC."})
            
        if str(db_hwid) != req_hwid:
            if db_ip and str(db_ip).strip() != "" and str(db_ip) == client_ip:
                db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                send_log("🔄 HWID Auto-oprava (Tichá)", f"Uživateli `{user.get('nick')}` se změnilo HWID, ale IP seděla. Aktualizováno.", 0x38bdf8)
                return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
            else:
                return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID/IP: Váš počítač ani síť nesouhlasí s registrací."})
        else:
            if not db_ip or str(db_ip).strip() == "":
                db.table("users").update({"ip_address": client_ip}).eq("discord_id", discord_id).execute()
                
        return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_ping', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_ping():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    action = data.get("action", "ping")
    session_id = data.get("session_id", "")
    db = get_db()
    if not db: return _cors_jsonify({"status": "error"})
    try:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")
        user_resp = db.table("users").select("launch_count, total_time").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        
        updates = {"last_active": now_str, "is_online": True}
        
        if action == "start": 
            updates["launch_count"] = (user_resp.data[0].get("launch_count") or 0) + 1
            new_session_id = str(uuid.uuid4())
            db.table("app_sessions").insert({"session_id": new_session_id, "discord_id": discord_id, "start_time": now_str, "end_time": now_str}).execute()
            db.table("users").update(updates).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "ok", "session_id": new_session_id})
            
        elif action == "ping": 
            updates["total_time"] = (user_resp.data[0].get("total_time") or 0) + 1
            if session_id: 
                db.table("app_sessions").update({"end_time": now_str}).eq("session_id", session_id).execute()
                
        elif action == "stop": 
            updates["is_online"] = False
            updates["admin_bypass"] = False 
            if session_id: 
                db.table("app_sessions").update({"end_time": now_str}).eq("session_id", session_id).execute()
            
        db.table("users").update(updates).eq("discord_id", discord_id).execute()
        return _cors_jsonify({"status": "ok", "session_id": session_id})
    except: return _cors_jsonify({"status": "error"})

@app.route('/api/get_profile_data/<discord_id>', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_get_profile_data(discord_id):
    if request.method == 'OPTIONS': return _cors_jsonify({})
    if not session.get('logged_in'): return _cors_jsonify({"error": "Unauthorized"}), 401
    
    if not discord_id or discord_id == 'None' or discord_id.strip() == '':
        return _cors_jsonify({"error": "Chybí Discord ID"})

    try:
        db = get_db()
        if not db: return _cors_jsonify({"error": "DB Error"}), 500
        
        u_data = db.table("users").select("*").eq("discord_id", discord_id).execute().data
        stats = ""
        app_status = "<span style='color: var(--text-muted);'>Neznámý</span>"
        
        if u_data:
            u = u_data[0]
            try: t_time = int(u.get("total_time") or 0)
            except: t_time = 0
            try: l_count = int(u.get("launch_count") or 0)
            except: l_count = 0
            
            hours = t_time // 60
            mins = t_time % 60
            stats = f"<div style='margin-bottom:5px;'><b style='color:var(--blue-main);'>{hours}h {mins}m</b> v aplikaci</div><div><b style='color:var(--blue-main);'>{l_count}x</b> spuštěno</div>"
            
            if u.get("is_online"):
                app_status = "<span style='color: var(--success); font-weight:bold;'><i class='fas fa-circle'></i> Nyní hraje</span>"
            else:
                app_status = f"<span style='color: var(--text-muted);'><i class='fas fa-moon'></i> {u.get('last_active', 'Nikdy')}</span>"

        joined_at = "Nenalezen na serveru"
        try:
            if bot.is_ready():
                for guild in bot.guilds:
                    member = guild.get_member(int(discord_id))
                    if member and member.joined_at:
                        joined_at = member.joined_at.strftime("%d.%m.%Y")
                        break
        except: pass

        downloads = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(10).execute().data or []
        sessions_data = db.table("app_sessions").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data or []
        
        top_lines = db.table("user_stats_lines").select("*").eq("discord_id", discord_id).order("play_count", desc=True).limit(5).execute().data or []
        top_stops = db.table("user_stats_stops").select("*").eq("discord_id", discord_id).order("announce_count", desc=True).limit(5).execute().data or []

        return _cors_jsonify({
            "joined_at": joined_at,
            "status": "", 
            "app_status": app_status,
            "stats": stats,
            "downloads": downloads,
            "sessions": sessions_data,
            "top_lines": top_lines,
            "top_stops": top_stops
        })
    except Exception as e:
        return _cors_jsonify({"error": str(e)}), 500

@app.route('/api/get_messages', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_get_messages():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    app_id = str(data.get("app_id", ""))
    db = get_db()
    if not db or not discord_id: return _cors_jsonify({"messages": []})
    try:
        user_data = db.table("users").select("role, nick").eq("discord_id", discord_id).execute().data
        user_roles = []
        user_nick = ""
        if user_data:
            user_nick = str(user_data[0].get("nick", ""))
            r_str = user_data[0].get("role", "")
            user_roles = [r.strip() for r in r_str.split(",")] if r_str else ["User"]

        all_msgs = db.table("app_messages").select("*").execute().data or []
        read_msgs = db.table("read_messages").select("message_id").eq("discord_id", discord_id).execute().data or []
        read_ids = [m['message_id'] for m in read_msgs]
        
        valid_msgs = []
        now = get_prague_time().replace(tzinfo=None)

        for msg in all_msgs:
            if str(msg.get("is_archived")).lower() == 'true': 
                continue

            expires_at_str = msg.get("expires_at")
            if expires_at_str and expires_at_str.strip():
                try:
                    exp_dt = datetime.strptime(expires_at_str.strip(), "%d.%m.%Y %H:%M")
                    if now > exp_dt:
                        db.table("app_messages").update({"is_archived": True}).eq("message_id", msg["message_id"]).execute()
                        continue
                except: pass

            target_type = msg.get("target_type", "GLOBAL")
            target_data = str(msg.get("target_data", ""))

            is_target = False
            if target_type == 'GLOBAL':
                is_target = True
            elif target_type == 'ROLE':
                target_roles = [r.strip() for r in target_data.split(',')]
                if any(tr in user_roles for tr in target_roles):
                    is_target = True
            elif target_type == 'USERS':
                targets = [t.strip() for t in target_data.split(',')]
                if discord_id in targets or app_id in targets or user_nick in targets:
                    is_target = True

            if is_target:
                is_repeat = str(msg.get('repeat')).lower() == 'true'
                if is_repeat or msg['message_id'] not in read_ids:
                    valid_msgs.append({
                        "id": msg['message_id'], 
                        "title": msg['title'], 
                        "content": msg['content'],
                        "link_url": msg.get('link_url', "")
                    })
        return _cors_jsonify({"messages": valid_msgs})
    except: return _cors_jsonify({"messages": []})

@app.route('/api/mark_message_read', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_mark_message_read():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    message_id = str(data.get("message_id", ""))
    db = get_db()
    if db and discord_id and message_id:
        try:
            read_id = str(uuid.uuid4())
            db.table("read_messages").insert({"read_id": read_id, "discord_id": discord_id, "message_id": message_id}).execute()
        except: pass
    return _cors_jsonify({"status": "ok"})

@app.route('/api/submit_feedback', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_submit_feedback():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    db = get_db()
    if not db: return _cors_jsonify({"status": "error", "message": "DB Error"})
    
    try:
        d_id = str(data.get("discord_id", "")).strip()
        nick = str(data.get("nick", "Neznámý Uživatel")).strip()
        type_str = str(data.get("type", "GENERAL")).strip()
        msg = str(data.get("message", "")).strip()

        if not d_id or d_id.lower() in ["není zadáno", "none", "null", ""]:
            if not re.search(r'\d{17,}', msg):
                return _cors_jsonify({
                    "status": "error", 
                    "message": "⚠️ OCHRANA: Aplikace nedokázala načíst vaše ID. Napište prosím své číselné DISCORD ID přímo do textu žádosti, abychom účet dohledali!"
                })
            else:
                d_id = "Napsáno v textu"

        db.table("feedback").insert({
            "discord_id": d_id, "nick": nick, "type": type_str, "message": msg,
            "status": "pending", "sys_note": "", "fcreated_at": get_prague_time().strftime("%d.%m.%Y %H:%M")
        }).execute()
        
        if type_str == "HWID": log_title = "🚨 VYŽADUJE KONTROLU: Žádost o HWID a IP 🚨"; log_color = 0xef4444
        elif type_str == "ADMIN_BYPASS": log_title = "🔓 VYŽADUJE SCHVÁLENÍ: Admin Bypass 🔓"; log_color = 0xf59e0b
        else: log_title = "🔔 NOVÁ ZPĚTNÁ VAZBA (NÁPAD/CHYBA) 🔔"; log_color = 0xa855f7
            
        desc = f"**Od:** {nick} (`{d_id}`)\n**Zpráva:**\n*{msg}*\n\n👉 **BĚŽTE DO DASHBOARDU A VYŘEŠTE TO!**"
        send_log(log_title, desc, log_color)
        
        return _cors_jsonify({"status": "success"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/login_request', methods=['POST'])
def login_request():
    discord_id = request.form.get('discord_id')
    db = get_db()
    if db and discord_id:
        try:
            user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
            if user and user[0].get("dashboard_access") == True and not user[0].get("is_banned") and not user[0].get("is_deleted"):
                token = str(uuid.uuid4())
                db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
                async def send():
                    try:
                        u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                        if u: await u.send(embed=discord.Embed(title="🔐 Bezpečnostní ověření", description="Byl zaznamenán pokus o přihlášení do administračního panelu.\n\nPokud jste to Vy, potvrďte přístup kliknutím na tlačítko níže.", color=0x38bdf8), view=DashboardAuthView(token, discord_id))
                    except: pass
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            else: flash('Účet neexistuje, nemá povolený přístup, nebo byl zablokován.', 'error')
        except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): return render_public(HTML_WAIT_AUTH, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    try:
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
            if user:
                t = user[0].get("login_token")
                if t == "approved": return {"status": "approved"}
                elif t == "rejected":
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                    return {"status": "rejected"}
    except: pass
    return {"status": "waiting"}

@app.route('/dashboard/login_finalize')
def login_finalize():
    discord_id = request.args.get('discord_id')
    db = get_db()
    if db and discord_id:
        user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
        if user and user[0].get("login_token") == "approved":
            session.permanent = True
            session['logged_in'] = True
            session['discord_id'] = discord_id
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return redirect(url_for('dashboard_main'))
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard/stats')
def dashboard_stats():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    total_visits = 0; last_7_days = 0; country_totals = {}; region_totals = {}
    dates_7_days = [(get_prague_time().replace(tzinfo=None) - timedelta(days=i)).strftime("%d.%m.") for i in range(6, -1, -1)]
    chart_data_7d = {d: 0 for d in dates_7_days}
    chart_data_24h = {f"{i:02d}:00": 0 for i in range(24)}
    try:
        db = get_db()
        if db:
            visits = db.table("page_visits").select("*").order("id", desc=True).limit(1500).execute().data or []
            total_visits = len(visits)
            now = get_prague_time().replace(tzinfo=None)
            for v in visits:
                c_raw = v.get('country', '')
                if not c_raw or 'neznámá' in c_raw.lower() or 'unknown' in c_raw.lower() or 'none' in c_raw.lower() or 'us' in c_raw.lower(): continue
                parts = c_raw.split('|')
                cc = parts[0] if len(parts) > 0 else ""
                c_name = parts[1] if len(parts) > 1 else c_raw
                reg = parts[2] if len(parts) > 2 else ""
                if not cc or cc == 'us': continue
                flag_url = f"https://flagcdn.com/24x18/{cc}.png"
                if cc not in country_totals: country_totals[cc] = {"name": c_name, "count": 0, "flag": flag_url}
                country_totals[cc]["count"] += 1
                display_name = f"{c_name} - {reg}" if reg else c_name
                if display_name not in region_totals: region_totals[display_name] = {"count": 0, "flag": flag_url}
                region_totals[display_name]["count"] += 1
                try:
                    v_time = datetime.strptime(v['visited_at'], "%d.%m.%Y %H:%M")
                    if (now - v_time).days <= 7: last_7_days += 1
                    day_str = v_time.strftime("%d.%m.")
                    hour_str = v_time.strftime("%H:00")
                    if day_str in chart_data_7d: chart_data_7d[day_str] += 1
                    if v_time.date() == now.date():
                        if hour_str in chart_data_24h: chart_data_24h[hour_str] += 1
                except: pass
    except Exception as e: flash(f"Chyba při načítání statistik: {e}", "error")
    gc.collect()
    return render_dashboard(HTML_STATS, total_visits=total_visits, last_7_days=last_7_days, country_totals=country_totals, region_totals=region_totals, labels_7d=json.dumps(list(chart_data_7d.keys())), data_7d=json.dumps(list(chart_data_7d.values())), labels_24h=json.dumps(list(chart_data_24h.keys())), data_24h=json.dumps(list(chart_data_24h.values())), deploy_time=DEPLOY_TIME)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if not session.get('logged_in'): return render_public(HTML_LOGIN)
    users_data = []
    try:
        db = get_db()
        if db:
            query = db.table("users").select("*")
            f = request.args.get('filter')
            if f == 'banned': query = query.eq("is_banned", True).eq("is_deleted", False)
            elif f == 'deleted': query = query.eq("is_deleted", True)
            elif f: query = query.ilike("role", f"%{f}%").eq("is_deleted", False)
            else: query = query.eq("is_deleted", False).order("app_id")
            users_data = query.execute().data or []
            now = get_prague_time().replace(tzinfo=None)
            for u in users_data:
                if u.get("is_online"):
                    la_str = u.get("last_active")
                    if la_str:
                        try:
                            last_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S")
                            if (now - last_dt).total_seconds() > 90:
                                u["is_online"] = False
                                db.table("users").update({"is_online": False}).eq("discord_id", u["discord_id"]).execute()
                        except: pass
    except Exception as e: flash(f"Chyba při načítání dat: {e}", "error")
    gc.collect()
    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title="Přehled uživatelů", deploy_time=DEPLOY_TIME)

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); discord_id = request.form.get("discord_id"); action = request.form.get("action"); nick = request.form.get("nick")
    if db and discord_id:
        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                new_hwid = request.form.get("hwid", "").strip()
                new_ip = request.form.get("ip_address", "").strip()
                
                updates = {"nick": nick, "role": r_str, "hwid": new_hwid, "ip_address": new_ip, "dashboard_access": True if request.form.get("dashboard_access") else False}
                
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str)
                
                hwid_log = new_hwid if new_hwid else "Zrušeno"
                ip_log = new_ip if new_ip else "Zrušeno"
                send_log("✏️ Úprava uživatele", f"Administrátor upravil uživatele **{nick}** (ID: `{discord_id}`).\nNové role: `{r_str}`\nHWID: `{hwid_log}`\nIP Adresa: `{ip_log}`", 0xf59e0b)
                
                flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_log("🔨 BAN", f"Administrátor udělil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0xef4444)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace a databáze byl trvale zablokován administrátorem.", 0xef4444), bot.loop)
                flash('BAN udělen.', 'warning')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_log("🕊️ UN-BAN", f"Administrátor zrušil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0x10b981)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace a databáze byl obnoven.", 0x10b981), bot.loop)
                flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "⚠️ Účet smazán", "Váš uživatelský účet byl smazán administrátorem.", 0xf59e0b), bot.loop)
                send_log("☠️ Účet smazán", f"Administrátor smazal účet uživatele **{nick}** (ID: `{discord_id}`).", 0xef4444)
                flash('Účet smazán (Soft Delete).', 'danger')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "✅ Účet obnoven", "Váš uživatelský účet byl úspěšně obnoven administrátorem.", 0x10b981), bot.loop)
                send_log("✅ Obnova účtu", f"Administrátor obnovil účet uživatele **{nick}** (ID: `{discord_id}`).", 0x10b981)
                flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                send_log("💀 Permanentní výmaz", f"Administrátor TRVALE vymazal uživatele s ID: `{discord_id}` z databáze.", 0x0f172a)
                flash('Účet trvale smazán.', 'dark')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
        except: pass
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/supporters', methods=['GET'])
def dashboard_supporters():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    pending_claims = []; supporters_history = []
    try: 
        db = get_db()
        if db:
            pending_claims = db.table("supporters").select("*").eq("status", "manual_review").execute().data or []
            s_data = db.table("supporters").select("*").in_("status", ["completed", "rejected"]).execute().data or []
            supporters_history = process_supporters(s_data)
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_SUPPORTERS_MGMT, pending_claims=pending_claims, supporters_history=supporters_history, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/feedback', methods=['GET'])
def dashboard_feedback():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    hwid_p = []; bypass_p = []; gen_p = []; res_all = []
    try:
        db = get_db()
        if db:
            data = db.table("feedback").select("*").order("id", desc=True).execute().data or []
            for item in data:
                if item.get('status') == 'pending':
                    if item.get('type') == 'HWID' or item.get('type') == 'HWID_IP': hwid_p.append(item)
                    elif item.get('type') == 'ADMIN_BYPASS': bypass_p.append(item)
                    else: gen_p.append(item)
                else: res_all.append(item)
    except: pass
    return render_dashboard(HTML_FEEDBACK, hwid_pending=hwid_p, bypass_pending=bypass_p, general_pending=gen_p, resolved_all=res_all, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/bypass_approve', methods=['POST'])
def bypass_approve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        fb = db.table("feedback").select("*").eq("id", fb_id).execute().data
        if fb:
            d_id = fb[0]['discord_id']
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            db.table("users").update({"admin_bypass": True}).eq("discord_id", d_id).execute()
            db.table("feedback").update({"status": "resolved", "sys_note": f"Bypass schválen [{now_str}]"}).eq("id", fb_id).execute()
            send_log("🔓 Admin Bypass", f"Administrátor jednorázově odemkl starou verzi pro uživatele: `{d_id}`.", 0x10b981)
            if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔓 Přístup povolen", "Tvá žádost o jednorázový vstup do staré verze byla schválena. Můžeš se přihlásit. Po vypnutí aplikace se přístup opět zamkne.", 0x10b981), bot.loop)
            flash('Bypass schválen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/bypass_reject', methods=['POST'])
def bypass_reject():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        fb = db.table("feedback").select("*").eq("id", fb_id).execute().data
        if fb:
            d_id = fb[0]['discord_id']
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            db.table("feedback").update({"status": "resolved", "sys_note": f"Bypass zamítnut [{now_str}]"}).eq("id", fb_id).execute()
            send_log("❌ Bypass Zamítnut", f"Administrátor zamítl vstup do staré verze pro: `{d_id}`.", 0xef4444)
            flash('Bypass zamítnut.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reset_hwid', methods=['POST'])
def feedback_reset_hwid():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id")
    db = get_db()
    if db and fb_id and d_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("users").update({"hwid": "", "ip_address": ""}).eq("discord_id", d_id).execute()
        db.table("feedback").update({"status": "resolved", "sys_note": f"HWID a IP byly resetovány [{now_str}]"}).eq("id", fb_id).execute()
        send_log("🔄 Zámek Resetován", f"Administrátor vyhověl žádosti a resetoval HWID a IP adresu pro ID: `{d_id}`.", 0x10b981)
        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔄 Zámek PC Resetován", "Vaše žádost byla schválena. HWID a IP adresa vašeho účtu byly úspěšně vymazány. Při dalším spuštění aplikace se spáruje s novým počítačem/sítí.", 0x10b981), bot.loop)
        flash('HWID a IP resetováno.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reject', methods=['POST'])
def feedback_reject():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); reason = request.form.get("reason", "Zamítnuto administrátorem.")
    db = get_db()
    if db and fb_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Zamítnuto: {reason} [{now_str}]"}).eq("id", fb_id).execute()
        send_log("❌ Žádost zamítnuta", f"Administrátor zamítl žádost pro ID: `{d_id}`.\nDůvod: {reason}", 0xef4444)
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "❌ Žádost zamítnuta", f"Vaše žádost v aplikaci byla administrátorem zamítnuta.\n\n**Důvod:** {reason}", 0xef4444), bot.loop)
        flash('Žádost zamítnuta.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reply', methods=['POST'])
def feedback_reply():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); msg = request.form.get("message")
    db = get_db()
    if db and fb_id and msg:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Odpověď: {msg} [{now_str}]"}).eq("id", fb_id).execute()
        send_log("📩 Odpověď na feedback", f"Administrátor odpověděl uživateli `{d_id}`:\n*{msg}*", 0x38bdf8)
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "📩 Zpráva od administrace", f"Odpověď na vaši zprávu z aplikace:\n\n{msg}", 0x38bdf8), bot.loop)
        flash('Odpověď odeslána a ticket uzavřen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_resolve', methods=['POST'])
def feedback_resolve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Označen za vyřešený [{now_str}]"}).eq("id", fb_id).execute()
        flash('Ticket uzavřen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_delete', methods=['POST'])
def feedback_delete():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        db.table("feedback").delete().eq("id", fb_id).execute()
        flash('Záznam smazán.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/notifications', methods=['GET'])
def dashboard_notifications():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    messages = []
    try:
        db = get_db()
        if db: 
            now = get_prague_time().replace(tzinfo=None)
            msgs = db.table("app_messages").select("*").order("created_at", desc=True).execute().data or []
            for m in msgs:
                if not str(m.get('is_archived')).lower() == 'true':
                    exp_str = m.get('expires_at')
                    if exp_str and exp_str.strip():
                        try:
                            exp_dt = datetime.strptime(exp_str.strip(), "%d.%m.%Y %H:%M")
                            if now > exp_dt:
                                db.table("app_messages").update({"is_archived": True}).eq("message_id", m["message_id"]).execute()
                                m['is_archived'] = True
                        except: pass
                m['is_archived'] = str(m.get('is_archived')).lower() == 'true'
                m['repeat'] = str(m.get('repeat')).lower() == 'true'
            messages = msgs
    except: pass
    return render_dashboard(HTML_NOTIFICATIONS, messages=messages, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/send_app_message', methods=['POST'])
def send_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            target_type = request.form.get("target_type", "GLOBAL")
            target_data = request.form.get("target_data", "").strip()
            title = request.form.get("title", "Zpráva od vývojáře")
            content = request.form.get("content", "")
            repeat = True if request.form.get("repeat") else False
            has_link = True if request.form.get("has_link") else False
            link_url = request.form.get("link_url", "") if has_link else ""
            expires_at = request.form.get("expires_at", "")
            
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            new_msg_id = str(uuid.uuid4())
            db.table("app_messages").insert({
                "message_id": new_msg_id, "target_type": target_type, "target_data": target_data, 
                "title": title, "content": content, "repeat": repeat, "link_url": link_url, 
                "expires_at": expires_at, "is_archived": False, "created_at": now_str
            }).execute()
            flash('Oznámení pro aplikaci bylo úspěšně odesláno!', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/edit_app_message', methods=['POST'])
def edit_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    msg_id = request.form.get("message_id")
    if db and msg_id:
        try:
            target_type = request.form.get("target_type", "GLOBAL")
            target_data = request.form.get("target_data", "").strip()
            title = request.form.get("title", "Zpráva od vývojáře")
            content = request.form.get("content", "")
            repeat = True if request.form.get("repeat") else False
            has_link = True if request.form.get("has_link") else False
            link_url = request.form.get("link_url", "") if has_link else ""
            expires_at = request.form.get("expires_at", "")
            
            db.table("app_messages").update({
                "target_type": target_type, "target_data": target_data, "title": title, 
                "content": content, "repeat": repeat, "link_url": link_url, "expires_at": expires_at
            }).eq("message_id", msg_id).execute()
            flash('Oznámení bylo úspěšně upraveno!', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/archive_app_message', methods=['POST'])
def archive_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    msg_id = request.form.get("message_id")
    if db and msg_id:
        try: db.table("app_messages").update({"is_archived": True}).eq("message_id", msg_id).execute()
        except: pass
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/delete_app_message', methods=['POST'])
def delete_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); msg_id = request.form.get("message_id")
    if db and msg_id:
        try: db.table("app_messages").delete().eq("message_id", msg_id).execute()
        except: pass
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = []; enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if set_resp and str(set_resp[0].get('setting_value')).lower() == 'false': enabled = False
            versions = db.table("software_versions").select("*").order("id", desc=True).execute().data or []
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try:
        v_name = request.form.get("version_name")
        db_ver = request.form.get("db_version")
        get_db().table("software_versions").insert({
            "version_name": v_name, 
            "db_version": db_ver,
            "file_url": request.form.get("file_url"), 
            "target_role": request.form.get("target_role"),
            "is_active": True,
            "eol_date": ""
        }).execute()
        send_log("📦 Nová verze softwaru", f"Administrátor přidal novou verzi do Manažeru: **{v_name}**.", 0x10b981)
        flash('Nová verze úspěšně vydána!', 'success')
        trigger_setup_messages_update() 
    except Exception as e: 
        flash(f'Chyba při přidávání verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/edit_version', methods=['POST'])
def edit_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("software_versions").update({
            "version_name": request.form.get("version_name"), 
            "db_version": request.form.get("db_version"),
            "file_url": request.form.get("file_url"), 
            "target_role": request.form.get("target_role"),
            "is_active": True if request.form.get("is_active") else False,
            "eol_date": request.form.get("eol_date", "")
        }).eq("id", request.form.get("version_id")).execute()
        flash('Verze byla úspěšně upravena.', 'success')
        trigger_setup_messages_update() 
    except Exception as e: flash(f'Chyba při úpravě verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try:
        get_db().table("software_versions").delete().eq("id", request.form.get("version_id")).execute()
        send_log("🗑️ Verze smazána", "Administrátor smazal jednu z verzí v Manažeru stahování.", 0xef4444)
        flash('Verze smazána.', 'success')
        trigger_setup_messages_update() 
    except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): 
    try: data = get_db().table("pending_roles").select("*").order("id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_PENDING_ROLES, pending=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids(): 
    try: data = get_db().table("users").select("*").order("app_id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_IDS, users=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page(): 
    try: data = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_TEAM_ADD, team=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_pending_role', methods=['POST'])
def add_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            roles_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
            dc_id = request.form.get("discord_identifier")
            db.table("pending_roles").insert({"discord_identifier": dc_id, "roles": roles_str}).execute()
            send_log("🎫 Nová rezervace role", f"Administrátor vytvořil předpřipravenou roli pro: `{dc_id}`.\nRole: `{roles_str}`", 0x3b82f6)
            flash('Rezervace vytvořena.', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/delete_pending_role', methods=['POST'])
def delete_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); p_id = request.form.get("pending_id")
    if db and p_id: 
        try: db.table("pending_roles").delete().eq("id", p_id).execute()
        except: pass
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/change_id', methods=['POST'])
def change_id():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            discord_id = request.form.get("discord_id"); new_app_id = int(request.form.get("new_app_id"))
            user_info = db.table("users").select("nick, app_id").eq("discord_id", discord_id).execute().data
            if user_info:
                old_app_id = user_info[0].get('app_id'); nick = user_info[0].get('nick')
                db.table("users").update({"app_id": new_app_id}).eq("discord_id", discord_id).execute()
                send_log("🆔 Změna ID", f"Administrátor změnil ID hráči **{nick}** z `#{old_app_id}` na **#{new_app_id}**.", 0x38bdf8)
        except: pass
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            combined_roles = [f"{n.strip()}|{c.strip()}" for n, c in zip(request.form.getlist("role_name[]"), request.form.getlist("role_color[]")) if n.strip()]
            n = request.form.get("name")
            db.table("team").insert({"name": n, "discord_nick": request.form.get("discord_nick"), "image_url": request.form.get("image_url"), "description": request.form.get("description"), "role_name": ",".join(combined_roles)}).execute()
            send_log("🤝 Nový člen týmu", f"Do týmu na webu byl přidán: **{n}**.", 0x10b981)
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            dc_nick = request.form.get("discord_nick")
            db.table("team").delete().eq("discord_nick", dc_nick).execute()
            send_log("👋 Odebrání člena týmu", f"Člen týmu `{dc_nick}` byl odebrán z webu.", 0xef4444)
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); discord_id = request.form.get("discord_id"); action = request.form.get("action"); nick = request.form.get("nick")
    if db and discord_id:
        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                new_hwid = request.form.get("hwid", "").strip()
                new_ip = request.form.get("ip_address", "").strip()
                
                updates = {"nick": nick, "role": r_str, "hwid": new_hwid, "ip_address": new_ip, "dashboard_access": True if request.form.get("dashboard_access") else False}
                
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str)
                
                hwid_log = new_hwid if new_hwid else "Zrušeno"
                ip_log = new_ip if new_ip else "Zrušeno"
                send_log("✏️ Úprava uživatele", f"Administrátor upravil uživatele **{nick}** (ID: `{discord_id}`).\nNové role: `{r_str}`\nHWID: `{hwid_log}`\nIP Adresa: `{ip_log}`", 0xf59e0b)
                
                flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_log("🔨 BAN", f"Administrátor udělil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0xef4444)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace a databáze byl trvale zablokován administrátorem.", 0xef4444), bot.loop)
                flash('BAN udělen.', 'warning')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_log("🕊️ UN-BAN", f"Administrátor zrušil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0x10b981)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace a databáze byl obnoven.", 0x10b981), bot.loop)
                flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "⚠️ Účet smazán", "Váš uživatelský účet byl smazán administrátorem.", 0xf59e0b), bot.loop)
                send_log("☠️ Účet smazán", f"Administrátor smazal účet uživatele **{nick}** (ID: `{discord_id}`).", 0xef4444)
                flash('Účet smazán (Soft Delete).', 'danger')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "✅ Účet obnoven", "Váš uživatelský účet byl úspěšně obnoven administrátorem.", 0x10b981), bot.loop)
                send_log("✅ Obnova účtu", f"Administrátor obnovil účet uživatele **{nick}** (ID: `{discord_id}`).", 0x10b981)
                flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                send_log("💀 Permanentní výmaz", f"Administrátor TRVALE vymazal uživatele s ID: `{discord_id}` z databáze.", 0x0f172a)
                flash('Účet trvale smazán.', 'dark')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
        except: pass
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/supporters', methods=['GET'])
def dashboard_supporters():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    pending_claims = []; supporters_history = []
    try: 
        db = get_db()
        if db:
            pending_claims = db.table("supporters").select("*").eq("status", "manual_review").execute().data or []
            s_data = db.table("supporters").select("*").in_("status", ["completed", "rejected"]).execute().data or []
            supporters_history = process_supporters(s_data)
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_SUPPORTERS_MGMT, pending_claims=pending_claims, supporters_history=supporters_history, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/feedback', methods=['GET'])
def dashboard_feedback():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    hwid_p = []; bypass_p = []; gen_p = []; res_all = []
    try:
        db = get_db()
        if db:
            data = db.table("feedback").select("*").order("id", desc=True).execute().data or []
            for item in data:
                if item.get('status') == 'pending':
                    if item.get('type') == 'HWID' or item.get('type') == 'HWID_IP': hwid_p.append(item)
                    elif item.get('type') == 'ADMIN_BYPASS': bypass_p.append(item)
                    else: gen_p.append(item)
                else: res_all.append(item)
    except: pass
    return render_dashboard(HTML_FEEDBACK, hwid_pending=hwid_p, bypass_pending=bypass_p, general_pending=gen_p, resolved_all=res_all, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/bypass_approve', methods=['POST'])
def bypass_approve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        fb = db.table("feedback").select("*").eq("id", fb_id).execute().data
        if fb:
            d_id = fb[0]['discord_id']
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            db.table("users").update({"admin_bypass": True}).eq("discord_id", d_id).execute()
            db.table("feedback").update({"status": "resolved", "sys_note": f"Bypass schválen [{now_str}]"}).eq("id", fb_id).execute()
            send_log("🔓 Admin Bypass", f"Administrátor jednorázově odemkl starou verzi pro uživatele: `{d_id}`.", 0x10b981)
            if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔓 Přístup povolen", "Tvá žádost o jednorázový vstup do staré verze byla schválena. Můžeš se přihlásit. Po vypnutí aplikace se přístup opět zamkne.", 0x10b981), bot.loop)
            flash('Bypass schválen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/bypass_reject', methods=['POST'])
def bypass_reject():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        fb = db.table("feedback").select("*").eq("id", fb_id).execute().data
        if fb:
            d_id = fb[0]['discord_id']
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            db.table("feedback").update({"status": "resolved", "sys_note": f"Bypass zamítnut [{now_str}]"}).eq("id", fb_id).execute()
            send_log("❌ Bypass Zamítnut", f"Administrátor zamítl vstup do staré verze pro: `{d_id}`.", 0xef4444)
            flash('Bypass zamítnut.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reset_hwid', methods=['POST'])
def feedback_reset_hwid():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id")
    db = get_db()
    if db and fb_id and d_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("users").update({"hwid": "", "ip_address": ""}).eq("discord_id", d_id).execute()
        db.table("feedback").update({"status": "resolved", "sys_note": f"HWID a IP byly resetovány [{now_str}]"}).eq("id", fb_id).execute()
        send_log("🔄 Zámek Resetován", f"Administrátor vyhověl žádosti a resetoval HWID a IP adresu pro ID: `{d_id}`.", 0x10b981)
        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔄 Zámek PC Resetován", "Vaše žádost byla schválena. HWID a IP adresa vašeho účtu byly úspěšně vymazány. Při dalším spuštění aplikace se spáruje s novým počítačem/sítí.", 0x10b981), bot.loop)
        flash('HWID a IP resetováno.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reject', methods=['POST'])
def feedback_reject():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); reason = request.form.get("reason", "Zamítnuto administrátorem.")
    db = get_db()
    if db and fb_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Zamítnuto: {reason} [{now_str}]"}).eq("id", fb_id).execute()
        send_log("❌ Žádost zamítnuta", f"Administrátor zamítl žádost pro ID: `{d_id}`.\nDůvod: {reason}", 0xef4444)
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "❌ Žádost zamítnuta", f"Vaše žádost v aplikaci byla administrátorem zamítnuta.\n\n**Důvod:** {reason}", 0xef4444), bot.loop)
        flash('Žádost zamítnuta.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reply', methods=['POST'])
def feedback_reply():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); msg = request.form.get("message")
    db = get_db()
    if db and fb_id and msg:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Odpověď: {msg} [{now_str}]"}).eq("id", fb_id).execute()
        send_log("📩 Odpověď na feedback", f"Administrátor odpověděl uživateli `{d_id}`:\n*{msg}*", 0x38bdf8)
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "📩 Zpráva od administrace", f"Odpověď na vaši zprávu z aplikace:\n\n{msg}", 0x38bdf8), bot.loop)
        flash('Odpověď odeslána a ticket uzavřen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_resolve', methods=['POST'])
def feedback_resolve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Označen za vyřešený [{now_str}]"}).eq("id", fb_id).execute()
        flash('Ticket uzavřen.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_delete', methods=['POST'])
def feedback_delete():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        db.table("feedback").delete().eq("id", fb_id).execute()
        flash('Záznam smazán.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/notifications', methods=['GET'])
def dashboard_notifications():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    messages = []
    try:
        db = get_db()
        if db: 
            now = get_prague_time().replace(tzinfo=None)
            msgs = db.table("app_messages").select("*").order("created_at", desc=True).execute().data or []
            for m in msgs:
                if not str(m.get('is_archived')).lower() == 'true':
                    exp_str = m.get('expires_at')
                    if exp_str and exp_str.strip():
                        try:
                            exp_dt = datetime.strptime(exp_str.strip(), "%d.%m.%Y %H:%M")
                            if now > exp_dt:
                                db.table("app_messages").update({"is_archived": True}).eq("message_id", m["message_id"]).execute()
                                m['is_archived'] = True
                        except: pass
                m['is_archived'] = str(m.get('is_archived')).lower() == 'true'
                m['repeat'] = str(m.get('repeat')).lower() == 'true'
            messages = msgs
    except: pass
    return render_dashboard(HTML_NOTIFICATIONS, messages=messages, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/send_app_message', methods=['POST'])
def send_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            target_type = request.form.get("target_type", "GLOBAL")
            target_data = request.form.get("target_data", "").strip()
            title = request.form.get("title", "Zpráva od vývojáře")
            content = request.form.get("content", "")
            repeat = True if request.form.get("repeat") else False
            has_link = True if request.form.get("has_link") else False
            link_url = request.form.get("link_url", "") if has_link else ""
            expires_at = request.form.get("expires_at", "")
            
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            new_msg_id = str(uuid.uuid4())
            db.table("app_messages").insert({
                "message_id": new_msg_id, "target_type": target_type, "target_data": target_data, 
                "title": title, "content": content, "repeat": repeat, "link_url": link_url, 
                "expires_at": expires_at, "is_archived": False, "created_at": now_str
            }).execute()
            flash('Oznámení pro aplikaci bylo úspěšně odesláno!', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/edit_app_message', methods=['POST'])
def edit_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    msg_id = request.form.get("message_id")
    if db and msg_id:
        try:
            target_type = request.form.get("target_type", "GLOBAL")
            target_data = request.form.get("target_data", "").strip()
            title = request.form.get("title", "Zpráva od vývojáře")
            content = request.form.get("content", "")
            repeat = True if request.form.get("repeat") else False
            has_link = True if request.form.get("has_link") else False
            link_url = request.form.get("link_url", "") if has_link else ""
            expires_at = request.form.get("expires_at", "")
            
            db.table("app_messages").update({
                "target_type": target_type, "target_data": target_data, "title": title, 
                "content": content, "repeat": repeat, "link_url": link_url, "expires_at": expires_at
            }).eq("message_id", msg_id).execute()
            flash('Oznámení bylo úspěšně upraveno!', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/archive_app_message', methods=['POST'])
def archive_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    msg_id = request.form.get("message_id")
    if db and msg_id:
        try: db.table("app_messages").update({"is_archived": True}).eq("message_id", msg_id).execute()
        except: pass
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/delete_app_message', methods=['POST'])
def delete_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); msg_id = request.form.get("message_id")
    if db and msg_id:
        try: db.table("app_messages").delete().eq("message_id", msg_id).execute()
        except: pass
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = []; enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if set_resp and str(set_resp[0].get('setting_value')).lower() == 'false': enabled = False
            versions = db.table("software_versions").select("*").order("id", desc=True).execute().data or []
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try:
        v_name = request.form.get("version_name")
        db_ver = request.form.get("db_version")
        get_db().table("software_versions").insert({
            "version_name": v_name, 
            "db_version": db_ver,
            "file_url": request.form.get("file_url"), 
            "target_role": request.form.get("target_role"),
            "is_active": True,
            "eol_date": ""
        }).execute()
        send_log("📦 Nová verze softwaru", f"Administrátor přidal novou verzi do Manažeru: **{v_name}**.", 0x10b981)
        flash('Nová verze úspěšně vydána!', 'success')
        trigger_setup_messages_update() 
    except Exception as e: 
        flash(f'Chyba při přidávání verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/edit_version', methods=['POST'])
def edit_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("software_versions").update({
            "version_name": request.form.get("version_name"), 
            "db_version": request.form.get("db_version"),
            "file_url": request.form.get("file_url"), 
            "target_role": request.form.get("target_role"),
            "is_active": True if request.form.get("is_active") else False,
            "eol_date": request.form.get("eol_date", "")
        }).eq("id", request.form.get("version_id")).execute()
        flash('Verze byla úspěšně upravena.', 'success')
        trigger_setup_messages_update() 
    except Exception as e: flash(f'Chyba při úpravě verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try:
        get_db().table("software_versions").delete().eq("id", request.form.get("version_id")).execute()
        send_log("🗑️ Verze smazána", "Administrátor smazal jednu z verzí v Manažeru stahování.", 0xef4444)
        flash('Verze smazána.', 'success')
        trigger_setup_messages_update() 
    except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): 
    try: data = get_db().table("pending_roles").select("*").order("id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_PENDING_ROLES, pending=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids(): 
    try: data = get_db().table("users").select("*").order("app_id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_IDS, users=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page(): 
    try: data = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_TEAM_ADD, team=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_pending_role', methods=['POST'])
def add_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            roles_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
            dc_id = request.form.get("discord_identifier")
            db.table("pending_roles").insert({"discord_identifier": dc_id, "roles": roles_str}).execute()
            send_log("🎫 Nová rezervace role", f"Administrátor vytvořil předpřipravenou roli pro: `{dc_id}`.\nRole: `{roles_str}`", 0x3b82f6)
            flash('Rezervace vytvořena.', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/delete_pending_role', methods=['POST'])
def delete_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); p_id = request.form.get("pending_id")
    if db and p_id: 
        try: db.table("pending_roles").delete().eq("id", p_id).execute()
        except: pass
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/change_id', methods=['POST'])
def change_id():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            discord_id = request.form.get("discord_id"); new_app_id = int(request.form.get("new_app_id"))
            user_info = db.table("users").select("nick, app_id").eq("discord_id", discord_id).execute().data
            if user_info:
                old_app_id = user_info[0].get('app_id'); nick = user_info[0].get('nick')
                db.table("users").update({"app_id": new_app_id}).eq("discord_id", discord_id).execute()
                send_log("🆔 Změna ID", f"Administrátor změnil ID hráči **{nick}** z `#{old_app_id}` na **#{new_app_id}**.", 0x38bdf8)
        except: pass
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            combined_roles = [f"{n.strip()}|{c.strip()}" for n, c in zip(request.form.getlist("role_name[]"), request.form.getlist("role_color[]")) if n.strip()]
            n = request.form.get("name")
            db.table("team").insert({"name": n, "discord_nick": request.form.get("discord_nick"), "image_url": request.form.get("image_url"), "description": request.form.get("description"), "role_name": ",".join(combined_roles)}).execute()
            send_log("🤝 Nový člen týmu", f"Do týmu na webu byl přidán: **{n}**.", 0x10b981)
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            dc_nick = request.form.get("discord_nick")
            db.table("team").delete().eq("discord_nick", dc_nick).execute()
            send_log("👋 Odebrání člena týmu", f"Člen týmu `{dc_nick}` byl odebrán z webu.", 0xef4444)
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); discord_id = request.form.get("discord_id"); action = request.form.get("action"); nick = request.form.get("nick")
    if db and discord_id:
        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                new_hwid = request.form.get("hwid", "").strip()
                new_ip = request.form.get("ip_address", "").strip()
                
                updates = {"nick": nick, "role": r_str, "hwid": new_hwid, "ip_address": new_ip, "dashboard_access": True if request.form.get("dashboard_access") else False}
                
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str)
                
                hwid_log = new_hwid if new_hwid else "Zrušeno"
                ip_log = new_ip if new_ip else "Zrušeno"
                send_log("✏️ Úprava uživatele", f"Administrátor upravil uživatele **{nick}** (ID: `{discord_id}`).\nNové role: `{r_str}`\nHWID: `{hwid_log}`\nIP Adresa: `{ip_log}`", 0xf59e0b)
                
                flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_log("🔨 BAN", f"Administrátor udělil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0xef4444)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace a databáze byl trvale zablokován administrátorem.", 0xef4444), bot.loop)
                flash('BAN udělen.', 'warning')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_log("🕊️ UN-BAN", f"Administrátor zrušil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0x10b981)
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace a databáze byl obnoven.", 0x10b981), bot.loop)
                flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "⚠️ Účet smazán", "Váš uživatelský účet byl smazán administrátorem.", 0xf59e0b), bot.loop)
                send_log("☠️ Účet smazán", f"Administrátor smazal účet uživatele **{nick}** (ID: `{discord_id}`).", 0xef4444)
                flash('Účet smazán (Soft Delete).', 'danger')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "✅ Účet obnoven", "Váš uživatelský účet byl úspěšně obnoven administrátorem.", 0x10b981), bot.loop)
                send_log("✅ Obnova účtu", f"Administrátor obnovil účet uživatele **{nick}** (ID: `{discord_id}`).", 0x10b981)
                flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                send_log("💀 Permanentní výmaz", f"Administrátor TRVALE vymazal uživatele s ID: `{discord_id}` z databáze.", 0x0f172a)
                flash('Účet trvale smazán.', 'dark')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
        except: pass
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/approve_claim', methods=['POST'])
def approve_claim():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    claim_id = request.form.get("claim_id")
    discord_nick = request.form.get("discord_nick")
    amount = request.form.get("amount", "0")
    db = get_db()
    if db and claim_id and discord_nick:
        discord_roles, db_role_string = calculate_roles_for_supporter(amount)
        if bot.loop and bot.loop.is_running() and bot.is_ready():
            asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
            rec = db.table("supporters").select("*").eq("id", claim_id).execute().data
            if rec: asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_nick, amount, rec[0].get('message', ''), discord_roles), bot.loop)
        db.table("supporters").update({"status": "completed", "sys_note": "Schváleno manuálně", "discord_nick": discord_nick}).eq("id", claim_id).execute()
        send_log("✅ Manuální schválení", f"Administrátor právě schválil roli pro uživatele **{discord_nick}**.", 0x10b981)
        db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_nick},nick.ilike.{discord_nick}").execute().data
        if db_user:
            current_roles = db_user[0].get('role', '')
            roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
            for new_r in db_role_string.split(','):
                if new_r.strip() not in roles_list: roles_list.append(new_r.strip())
            db.table("users").update({"role": ",".join(roles_list)}).eq("discord_id", db_user[0]['discord_id']).execute()
        else: db.table("pending_roles").insert({"discord_identifier": discord_nick, "roles": db_role_string}).execute()
        flash(f'Požadavek schválen pro: {discord_nick}', 'success')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/reject_claim', methods=['POST'])
def reject_claim():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    claim_id = request.form.get("claim_id")
    discord_nick = request.form.get("discord_nick", "")
    sys_note = request.form.get("sys_note", "Zamítnuto administrátorem bez udání důvodu.")
    db = get_db()
    if db and claim_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("supporters").update({"status": "rejected", "sys_note": f"Zamítnuto: {sys_note} [{now_str}]"}).eq("id", claim_id).execute()
        send_log("❌ Manuální zamítnutí", f"Administrátor zamítl platbu pro uživatele **{discord_nick}**.\nDůvod: {sys_note}", 0xef4444)
        if discord_nick and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(discord_nick, "❌ Žádost o roli zamítnuta", f"Tvoje žádost o spárování platby byla zamítnuta administrátorem.\n\n**Důvod:** {sys_note}", 0xef4444), bot.loop)
        flash('Požadavek byl zamítnut.', 'success')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/edit_supporter', methods=['POST'])
def edit_supporter():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    supporter_id = request.form.get("supporter_id")
    db = get_db()
    if db and supporter_id:
        try:
            db.table("supporters").update({"name": request.form.get("name"), "discord_nick": request.form.get("discord_nick", ""), "amount": request.form.get("amount"), "message": request.form.get("message", "")}).eq("id", supporter_id).execute()
            flash('Údaje podporovatele byly úspěšně upraveny!', 'success')
        except Exception as e: flash(f'Chyba při úpravě: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/add_supporter', methods=['POST'])
def add_supporter():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        db = get_db()
        d_nick = request.form.get("discord_nick", "").strip()
        amt = request.form.get("amount", "0 CZK")
        msg = request.form.get("message", "")
        db.table("supporters").insert({"name": request.form.get("name"), "discord_nick": d_nick, "amount": amt, "message": msg, "status": "completed", "sys_note": "Přidáno manuálně z Dashboardu", "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
        if d_nick:
            discord_roles, db_role_string = calculate_roles_for_supporter(amt)
            if bot.loop and bot.loop.is_running() and bot.is_ready():
                asyncio.run_coroutine_threadsafe(assign_supporter_role(d_nick, discord_roles), bot.loop)
                asyncio.run_coroutine_threadsafe(announce_new_supporter(d_nick, amt, msg, discord_roles), bot.loop)
            db_user = db.table("users").select("*").or_(f"discord_id.eq.{d_nick},nick.ilike.{d_nick}").execute().data
            if db_user:
                current_roles = db_user[0].get('role', '')
                roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                for new_r in db_role_string.split(','):
                    if new_r.strip() not in roles_list: roles_list.append(new_r.strip())
                db.table("users").update({"role": ",".join(roles_list)}).eq("discord_id", db_user[0]['discord_id']).execute()
            else: db.table("pending_roles").insert({"discord_identifier": d_nick, "roles": db_role_string}).execute()
        send_log("➕ Přidán podporovatel", f"Administrátor ručně přidal podporovatele **{request.form.get('name')}** (Discord: {d_nick}).\nČástka: {amt}", 0x10b981)
        flash('Podporovatel přidán!', 'success')
    except Exception as e: flash(f'Chyba při přidávání: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/delete_supporter', methods=['POST'])
def delete_supporter():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("supporters").delete().eq("id", request.form.get("supporter_id")).execute()
        flash('Podporovatel smazán.', 'success')
    except Exception as e: flash(f'Chyba při mazání: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/update_statuses', methods=['POST'])
def update_statuses():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if not db: return redirect(url_for('dashboard_app_management'))
    
    dl_mode = request.form.get("dl_status_mode", "auto")
    dl_custom_icon = request.form.get("dl_status_custom_icon", "🟢")
    dl_custom_text = request.form.get("dl_status_custom_text", "")
    
    settings_to_update = {
        "dl_status_mode": dl_mode,
        "dl_status_custom_icon": dl_custom_icon,
        "dl_status_custom_text": dl_custom_text
    }
    
    try:
        for key, val in settings_to_update.items():
            check = db.table("settings").select("*").eq("setting_key", key).execute().data
            if not check: db.table("settings").insert({"setting_key": key, "setting_value": str(val)}).execute()
            else: db.table("settings").update({"setting_value": str(val)}).eq("setting_key", key).execute()
        
        if request.form.get("send_to_discord"):
            async def send_status_embed():
                if not bot.is_ready(): return
                for guild in bot.guilds:
                    channel = discord.utils.get(guild.channels, name="🛜・status")
                    if channel:
                        res = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled"]).execute().data or []
                        soft_enabled = True; dl_enabled = True
                        for r in res:
                            if r['setting_key'] == 'software_enabled' and str(r['setting_value']).lower() == 'false': soft_enabled = False
                            if r['setting_key'] == 'downloads_enabled' and str(r['setting_value']).lower() == 'false': dl_enabled = False
                        
                        if soft_enabled: s_global = "🟢 Všechny systémy softwaru jsou online a v provozu."
                        else: s_global = "🔴 Systém je nyní v režimu údržby (Software globálně vypnut)."
                        
                        s_db = "🟢 Databáze je stabilní a synchronizovaná."
                        
                        color = 0x10b981
                        if dl_mode == "auto":
                            if dl_enabled: s_dl = "🟢 Stahování softwaru a instalátorů běží v pořádku."
                            else: 
                                s_dl = "🔴 Stahování je momentálně administrátorem zakázáno."
                                color = 0xef4444
                        elif dl_mode == "maintenance":
                            s_dl = "🟠 **Probíhá oprava systému.** Stahování některých souborů nemusí fungovat správně."
                            color = 0xf59e0b
                        else:
                            s_dl = f"{dl_custom_icon} {dl_custom_text}"
                            if dl_custom_icon == "🟢": color = 0x10b981
                            elif dl_custom_icon == "🟠": color = 0xf59e0b
                            elif dl_custom_icon == "🔴": color = 0xef4444
                            else: color = 0x3b82f6
                        
                        embed = discord.Embed(title="📊 AKTUÁLNÍ STAV SYSTÉMŮ", color=color, timestamp=get_prague_time())
                        embed.add_field(name="📥 Stahování & Instalace", value=s_dl, inline=False)
                        embed.add_field(name="🗄️ Databáze & Synchronizace", value=s_db, inline=False)
                        embed.add_field(name="💻 Globální provoz Softwaru", value=s_global, inline=False)
                        embed.set_footer(text="Poslední aktualizace")
                        
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
                flash('Zpráva byla aktualizována v Discord kanálu 🛜・status!', 'success')
        
    except Exception as e: pass
    
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/app_management', methods=['GET'])
def dashboard_app_management():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    soft_enabled = True; dl_enabled = True
    dl_mode = "auto"; dl_custom_icon = "🟢"; dl_custom_text = ""
    try:
        db = get_db()
        if db:
            res = db.table("settings").select("*").execute().data or []
            for r in res:
                key = r.get('setting_key')
                val = r.get('setting_value')
                if key == 'software_enabled' and str(val).lower() == 'false': soft_enabled = False
                if key == 'downloads_enabled' and str(val).lower() == 'false': dl_enabled = False
                if key == 'dl_status_mode': dl_mode = val
                if key == 'dl_status_custom_icon': dl_custom_icon = val
                if key == 'dl_status_custom_text': dl_custom_text = val
    except: pass
    
    return render_dashboard(HTML_APP_MANAGEMENT + HTML_STATUS_SECTION, 
                            soft_enabled=soft_enabled, dl_enabled=dl_enabled, 
                            dl_status_mode=dl_mode, dl_status_custom_icon=dl_custom_icon, dl_status_custom_text=dl_custom_text,
                            deploy_time=DEPLOY_TIME)

@app.route('/dashboard/toggle_software', methods=['POST'])
def toggle_software():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); new_status = request.form.get("new_status")
    if db:
        try:
            check = db.table("settings").select("*").eq("setting_key", "software_enabled").execute().data or []
            if not check: db.table("settings").insert({"setting_key": "software_enabled", "setting_value": new_status}).execute()
            else: db.table("settings").update({"setting_value": new_status}).eq("setting_key", "software_enabled").execute()
            flash('Globální stav softwaru byl změněn!', 'success')
            send_log("🚨 Kill-Switch", f"Software byl přes administraci **{'ZAPNUT' if new_status == 'True' else 'VYPNUT'}**.", 0xef4444 if new_status == 'False' else 0x10b981)
        except Exception as e: flash(f"Chyba: Zkontrolujte DB. ({e})", "error")
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_downloads', methods=['POST'])
def toggle_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); new_status = request.form.get("new_status"); return_to = request.form.get("return_to", "downloads")
    if db:
        try: 
            check = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if not check: db.table("settings").insert({"setting_key": "downloads_enabled", "setting_value": new_status}).execute()
            else: db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute()
            flash('Status stahování byl změněn.', 'success')
            send_log("📥 Stahování přepnuto", f"Administrátor **{'POVOLIL' if new_status == 'True' else 'ZAKÁZAL'}** stahování softwaru.", 0x3b82f6)
        except Exception as e: flash(f"Chyba: {e}", "error")
    if return_to == 'app_management': return redirect(url_for('dashboard_app_management'))
    return redirect(url_for('dashboard_downloads'))

class DashboardAuthView(discord.ui.View):
    def __init__(self, token, discord_id):
        super().__init__(timeout=300)
        self.token = token
        self.discord_id = discord_id
        
    @discord.ui.button(label="Ověřit přístup", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", self.discord_id).execute().data
            if user and user[0].get("login_token") == self.token:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
                await interaction.edit_original_response(content="✅ **Přístup do administrace byl úspěšně schválen!**", view=None)
            else: await interaction.edit_original_response(content="❌ **Platnost vypršela.**", view=None)
                
    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db = get_db()
        if db: db.table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Zamítnuto.**", view=None)

class AppAuthView(discord.ui.View):
    def __init__(self, token, discord_id, is_dm=True):
        super().__init__(timeout=180)
        self.token = token
        self.discord_id = discord_id
        self.is_dm = is_dm
        
    @discord.ui.button(label="Ano, ověřit", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        if str(interaction.user.id) != str(self.discord_id): return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        db = get_db()
        if db: db.table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
        await interaction.response.edit_message(content="✅ **Ověřeno! Můžete se vrátit do aplikace.**", view=None)
        send_log("🖥️ Přihlášení do Aplikace", f"Uživatel s ID `{self.discord_id}` se úspěšně ověřil a vstoupil do softwaru.", 0x10b981)
        if not self.is_dm:
            await asyncio.sleep(2); await interaction.message.delete()

class DynamicDownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, emoji="📥", custom_id="persistent_install_main_btn")
    async def dl_btn(self, interaction, button):
        db = get_db()
        settings_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}]
        if str(settings_resp[0].get('setting_value', '')).lower() == 'false': 
            return await interaction.response.send_message("**⛔ Stahování je momentálně globálně zakázáno administrátorem.** Zkuste to prosím později.", ephemeral=True)
            
        chk = db.table("users").select("is_banned").eq("discord_id", str(interaction.user.id)).execute()
        if chk.data and chk.data[0].get('is_banned'):
            return await interaction.response.send_message("**⛔ Přístup zamítnut:** Váš účet má udělený BAN a stahování bylo zablokováno.", ephemeral=True)

        class DynamicRulesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, emoji="✅")
            async def agree(self, i2, b2):
                await i2.response.edit_message(content="<a:loading:123> Ověřuji profil...", view=None)
                try:
                    db = get_db()
                    d_id = str(i2.user.id)
                    n = i2.user.display_name
                    u_role = "User"
                    
                    chk = db.table("users").select("*").eq("discord_id", d_id).execute()
                    pend_data = db.table("pending_roles").select("*").execute().data or []
                    pend = next((p for p in pend_data if p['discord_identifier'] in [d_id, n]), None)
                    if chk.data:
                        if chk.data[0].get('is_banned'): return await i2.edit_original_response(content="**Přístup zamítnut:** Máte BAN.")
                        if chk.data[0].get('is_deleted'):
                            hid = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                            nid = hid.data[0]["app_id"] + 1 if hid.data else 1000
                            r = pend['roles'] if pend else "User"
                            db.table("users").update({"app_id": nid, "nick": n, "is_deleted": False, "role": r}).eq("discord_id", d_id).execute()
                            u_role = r
                            if pend: db.table("pending_roles").delete().eq("id", pend['id']).execute()
                        else: u_role = chk.data[0].get('role', 'User')
                    else:
                        hid = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                        nid = hid.data[0]["app_id"] + 1 if hid.data else 1000
                        r = pend['roles'] if pend else "User"
                        db.table("users").insert({"app_id": nid, "discord_id": d_id, "nick": n, "role": r, "hwid": "", "is_banned": False, "is_deleted": False, "dashboard_access": False, "login_token": "", "registered_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
                        u_role = r
                        if pend: db.table("pending_roles").delete().eq("id", pend['id']).execute()
                            
                    if isinstance(i2.user, discord.Member): 
                        try: await update_member_roles(i2.user, u_role)
                        except: pass
                            
                    class DynamicVersionSelect(discord.ui.Select):
                        def __init__(self, u_lvl):
                            opts = []
                            vers_data = get_db().table("software_versions").select("*").eq("is_active", True).order("id", desc=True).execute().data or []
                            now = get_prague_time().replace(tzinfo=None)
                            
                            for v in vers_data:
                                req = 2 if v['target_role'] == 'BT' else (3 if v['target_role'] == 'DEV_SA' else 1)
                                if u_lvl >= req:
                                    eol_str = v.get('eol_date', '').strip()
                                    is_dl = True
                                    desc = ""
                                    if eol_str:
                                        try:
                                            eol_dt = datetime.strptime(eol_str, "%d.%m.%Y")
                                            days_left = (eol_dt - now).days
                                            if days_left <= 14:
                                                is_dl = False
                                            else:
                                                desc = f"Končí podpora: {eol_str}"
                                        except: pass
                                    
                                    if is_dl:
                                        opts.append(discord.SelectOption(label=v['version_name'], description=desc or "Dostupné pro vaši roli", value=str(v['id']), emoji="📦"))
                            
                            if not opts: opts.append(discord.SelectOption(label="Žádná verze nenalezena", description="Pro vaše oprávnění aktuálně není nic ke stažení.", value="none"))
                            super().__init__(placeholder="Vyber verzi k instalaci...", options=opts)
                            
                        async def callback(self, i3):
                            if self.values[0] == "none": return await i3.response.send_message("Pro vaše role nejsou dostupné žádné verze.", ephemeral=True)
                            await i3.response.send_message("<a:loading:123> Generuji odkaz...", ephemeral=True)
                            t = str(uuid.uuid4())
                            get_db().table("users").update({"download_token": t}).eq("discord_id", str(i3.user.id)).execute()
                            
                            link = f"https://datacorebot.koyeb.app/download/{t}?v={self.values[0]}"
                            await i3.edit_original_response(content=f"**Odkaz připraven:**\n🔗 {link}\n*Platí jen pro Vás.*")
                            
                    v_view = discord.ui.View()
                    v_view.add_item(DynamicVersionSelect(3 if 'SA' in u_role or 'DEV' in u_role else (2 if 'BT' in u_role else 1)))
                    await i2.edit_original_response(content="**Ověření úspěšné.** Vyberte soubor:", view=v_view)
                except Exception as e: await i2.edit_original_response(content=f"Chyba DB: {e}")
                    
            @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, emoji="❌")
            async def disagree(self, i2, b2): await i2.response.edit_message(content="**Akce zrušena.**", view=None)
                
        await interaction.response.send_message("**PODMÍNKY UŽÍVÁNÍ:**\n1. Přísný zákaz šíření, kopírování nebo sdílení aplikace bez výslovného souhlasu autora.\n2. Systém využívá HWID ochranu a shromažďuje telemetrická data pro zajištění správného chodu a bezpečnosti aplikace.\n3. Každý pokus o modifikaci kódu nebo obcházení zabezpečení povede k okamžitému a trvalému zablokování.\n\nSouhlasíte s těmito podmínkami?", view=DynamicRulesView(), ephemeral=True)

def check_web_sa():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="web-sa") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění k tomuto příkazu.", delete_after=10)
        return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění k tomuto příkazu.", delete_after=10)
        return False
    return commands.check(predicate)

@tasks.loop(minutes=5)
async def keepalive_ping():
    try:
        url = "https://datacorebot.koyeb.app/api/keepalive"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
    except: pass

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)
    send_log("🔄 Systém Online", "Bot byl úspěšně restartován a běží.", 0x10b981)
    try: bot.add_view(DynamicDownloadView())
    except: pass
    try:
        for guild in bot.guilds: bot.invites_cache[guild.id] = await guild.invites()
    except: pass
    trigger_setup_messages_update() 
    if not keepalive_ping.is_running(): keepalive_ping.start()

@bot.event
async def on_message(message):
    if message.author.bot: return
    if not message.guild:
        for guild in bot.guilds:
            channel = discord.utils.find(lambda c: "bot-dm" in c.name.lower(), guild.text_channels)
            if channel:
                embed = discord.Embed(title="📩 Nová zpráva do DM bota", description=message.content or "*[Žádný text]*", color=0xa855f7)
                embed.set_author(name=f"{message.author.display_name} (@{message.author.name})", icon_url=message.author.display_avatar.url)
                embed.set_footer(text=f"ID: {message.author.id}")
                if message.attachments:
                    urls = "\n".join([f"• [{a.filename}]({a.url})" for a in message.attachments])
                    embed.add_field(name="📎 Přílohy:", value=urls, inline=False)
                    if message.attachments[0].url.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
                        embed.set_image(url=message.attachments[0].url)
                try: await channel.send(embed=embed)
                except: pass
                break
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    used_invite = None
    try:
        new_invites = await member.guild.invites()
        old_invites = bot.invites_cache.get(member.guild.id, [])
        for invite in new_invites:
            for old_invite in old_invites:
                if invite.code == old_invite.code and invite.uses > old_invite.uses:
                    used_invite = invite; break
            if used_invite: break
        bot.invites_cache[member.guild.id] = new_invites
    except: pass
    link_info = "\n\n**🌐 Zdroj:** Uživatel se připojil z odkazu na webové stránce!" if used_invite and used_invite.code == "vmTagbC9mF" else ""
    await async_send_log("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum připojení:** {get_prague_time().strftime('%d.%m.%Y %H:%M')}{link_info}", 0x10b981)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Zkontroluj si `!help`.", delete_after=15)
    elif isinstance(error, commands.MemberNotFound): await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!**", delete_after=15)
    elif isinstance(error, commands.CheckFailure): pass 

@bot.command()
@check_sm_role()
async def dm_view(ctx, discord_id: str):
    if not discord_id.isdigit():
        return await ctx.send("❌ Zadej platné číselné ID uživatele.")
    status_msg = await ctx.send("<a:loading:123> Načítám historii zpráv (Může to chvíli trvat)...")
    try:
        user = await bot.fetch_user(int(discord_id))
        if not user.dm_channel: await user.create_dm()
        messages = [msg async for msg in user.dm_channel.history(limit=100)]
        messages.reverse()
        if not messages: return await status_msg.edit(content=f"📭 Historie DM s uživatelem `{user.display_name}` je prázdná.")
        log_content = f"--- HISTORIE DM S UŽIVATELEM {user.display_name} ({user.name} | ID: {user.id}) ---\n\n"
        for m in messages:
            time_str = (m.created_at + timedelta(hours=1)).strftime("%d.%m.%Y %H:%M:%S")
            author_name = "🤖 BOT" if m.author.bot else f"👤 {m.author.display_name}"
            log_content += f"[{time_str}] {author_name}: {m.content}\n"
            if m.attachments: log_content += f"    [Příloha]: {', '.join([a.url for a in m.attachments])}\n"
        file_stream = io.BytesIO(log_content.encode('utf-8'))
        file = discord.File(file_stream, filename=f"ChatLog_{user.display_name}.txt")
        await status_msg.delete()
        await ctx.send(f"📄 Tady je posledních 100 zpráv ze soukromé konverzace s uživatelem `{user.display_name}`:", file=file)
    except discord.NotFound: await status_msg.edit(content="❌ Uživatel s tímto ID nebyl nalezen na Discordu.")
    except discord.Forbidden: await status_msg.edit(content="❌ Nemám oprávnění k DM tohoto uživatele.")
    except Exception as e: await status_msg.edit(content=f"❌ Nastala chyba při čtení DM zpráv:\n`{e}`")

@bot.command()
@check_web_sa()
async def setup_download(ctx):
    db = get_db()
    embed = build_setup_embed(db)
    msg = await ctx.send(embed=embed, view=DynamicDownloadView())
    save_setup_message(db, ctx.channel.id, msg.id)
    try: await ctx.message.delete()
    except: pass

@bot.command()
async def auth(ctx):
    try: await ctx.message.delete()
    except: pass
    db = get_db()
    if db:
        u = db.table("users").select("login_token").eq("discord_id", str(ctx.author.id)).execute().data
        if u and u[0].get('login_token'): await ctx.send(f"🛡️ {ctx.author.mention}, potvrďte přihlášení do aplikace:", view=AppAuthView(u[0]['login_token'], str(ctx.author.id), False), delete_after=60)
        else:
            msg = await ctx.send(f"❌ {ctx.author.mention} Nemáš čekající požadavek na přihlášení.")
            await asyncio.sleep(5); await msg.delete()

@bot.command()
async def verze(ctx):
    db = get_db()
    if not db: return await ctx.send("❌ Databáze není dostupná.")
    versions = db.table("software_versions").select("*").order("id", desc=True).execute().data or []
    if not versions: return await ctx.send("Zatím nejsou dostupné žádné verze ke stažení.")
    embed = discord.Embed(title="📦 Kompletní seznam verzí", description="Seznam všech verzí softwaru, včetně neveřejných pro DEV/SA.", color=0x38bdf8)
    for v in versions:
        status = "✅ Aktivní" if str(v.get('is_active', 'True')).lower() == 'true' else "❌ Zablokováno"
        embed.add_field(name=f"{v['version_name']} [{v.get('db_version', 'Neznámá v DB')}]", value=f"Dostupné pro: `{v['target_role']}`\nStav: {status}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", description="Seznam dostupných příkazů rozdělený podle oprávnění.", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné příkazy", value="`!auth` - Potvrzení přihlášení do aplikace.\n`!ping` - Odezva bota.\n`!verze` - Seznam dostupných verzí.\n`!help` - Tato nápověda.", inline=False)
    embed.add_field(name="🛡️ Správa (SM)", value="`!info [ID]` - Profil.\n`!db [ID]` - 2FA do webu.\n`!ban`/`!unban [ID]` - BANY.\n`!delete [ID]` - Blokace.\n`!perdelete [ID]` - Úplné smazání.\n`!register [ID]` - Vytvoří účet cizímu.\n`!message #kanál [text]` - Zpráva přes bota.\n`!dm @uzivatel [text]` - Soukromá zpráva.\n`!dm_view [ID]` - Zobrazí celou historii DM konverzace bota s daným hráčem.", inline=False)
    embed.add_field(name="⚙️ Administrace (web-sa)", value="`!setup_download` - Generuje instalátor.\n`!sm @uživatel` - Přidá/odebere roli SM.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id: return await ctx.send(f"❌ Zadejte ID.")
    db = get_db()
    if not db: return
    u = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not u: return await ctx.send(f"❌ Nenalezen.")
    embed = discord.Embed(title=f"Uživatel: {u[0].get('nick')}", color=0x38bdf8)
    embed.add_field(name="App ID", value=f"#{u[0].get('app_id')}", inline=True)
    embed.add_field(name="Discord ID", value=u[0].get('discord_id'), inline=True)
    embed.add_field(name="Role", value=u[0].get('role'), inline=True)
    embed.add_field(name="Banned", value="Ano" if u[0].get('is_banned') else "Ne", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@check_sm_role()
async def ban(ctx, discord_id: str):
    db = get_db()
    if not db: return
    user_data = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not user_data: return await ctx.send("❌ Uživatel nenalezen.")
    db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await send_user_dm(discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace a databáze byl trvale zablokován administrátorem.", 0xef4444)
    await ctx.send(f"🔨 Uživateli `{discord_id}` byl udělen BAN.")

@bot.command()
@check_sm_role()
async def unban(ctx, discord_id: str):
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
    await send_user_dm(discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace a databáze byl obnoven.", 0x10b981)
    await ctx.send(f"🕊️ Uživateli `{discord_id}` byl zrušen BAN.")

@bot.command(name="db")
@check_sm_role()
async def db_cmd(ctx, discord_id: str):
    db_conn = get_db()
    if not db_conn: return
    user_data = db_conn.table("users").select("dashboard_access").eq("discord_id", discord_id).execute().data
    if not user_data: return await ctx.send("❌ Uživatel nenalezen.")
    new_status = not user_data[0].get("dashboard_access", False)
    db_conn.table("users").update({"dashboard_access": new_status}).eq("discord_id", discord_id).execute()
    await ctx.send(f"⚙️ Přístup do DB pro ID `{discord_id}`: **{'POVOLEN ✅' if new_status else 'ODEBRÁN ❌'}**.")

@bot.command()
@check_sm_role()
async def delete(ctx, discord_id: str):
    db = get_db()
    if not db: return
    now = get_prague_time().strftime("%d.%m.%Y %H:%M")
    db.table("users").update({"is_deleted": True, "deleted_at": now, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await send_user_dm(discord_id, "⚠️ Účet smazán", "Váš uživatelský účet byl smazán administrátorem.", 0xf59e0b)
    await ctx.send(f"☠️ Účet `{discord_id}` byl smazán (Soft Delete).")

class PerDeleteConfirm(discord.ui.View):
    def __init__(self, target_id, author_id):
        super().__init__(timeout=60)
        self.target_id = target_id
        self.author_id = author_id

    @discord.ui.button(label="Ano, trvale smazat", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.defer()
        db = get_db()
        if db:
            db.table("users").delete().eq("discord_id", self.target_id).execute()
            await interaction.edit_original_response(content=f"✅ Účet `{self.target_id}` byl z databáze PERMANENTNĚ smazán.", view=None, embed=None)

    @discord.ui.button(label="Zrušit", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.edit_message(content="❌ Akce zrušena.", view=None, embed=None)

@bot.command()
@check_sm_role()
async def perdelete(ctx, discord_id: str):
    embed = discord.Embed(title="⚠️ Varování: Permanentní smazání", description=f"Opravdu chceš nevratně smazat účet `{discord_id}` z databáze?", color=0xef4444)
    await ctx.send(embed=embed, view=PerDeleteConfirm(discord_id, ctx.author.id))

@bot.command()
async def register(ctx, target_id: str = None):
    db = get_db()
    if not db: return await ctx.send("❌ Databáze nedostupná.")
    if target_id:
        is_admin = discord.utils.get(ctx.author.roles, name="web-sa") or discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator
        if not is_admin: return await ctx.send(f"❌ {ctx.author.mention} Nemáš oprávnění.")
        discord_id = target_id
        target_member = ctx.guild.get_member(int(discord_id)) if discord_id.isdigit() else None
        nick = target_member.display_name if target_member else f"Uživatel {discord_id}"
    else:
        discord_id = str(ctx.author.id)
        nick = ctx.author.display_name
        target_member = ctx.author
        
    now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
    check = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if check:
        if check[0].get('is_banned'): return await ctx.send("❌ Tento účet má BAN.")
        elif check[0].get('is_deleted'):
            highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
            new_app_id = highest[0]["app_id"] + 1 if highest else 1000
            db.table("users").update({"app_id": new_app_id, "nick": nick, "is_deleted": False, "deleted_at": "", "registered_at": now_str}).eq("discord_id", discord_id).execute()
            await ctx.send(f"✅ Smazaný účet byl úspěšně obnoven! Nové App ID je **#{new_app_id}**.")
            if target_member: await update_member_roles(target_member, check[0].get('role', 'User'))
        else: await ctx.send(f"ℹ️ Tento uživatel již je zaregistrován!")
    else:
        highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
        new_app_id = highest[0]["app_id"] + 1 if highest else 1000
        db.table("users").insert({ "app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "ip_address": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": now_str }).execute()
        await ctx.send(f"✅ Úspěšně zaregistrován! App ID: **#{new_app_id}**.")

@bot.command()
@check_web_sa()
async def sm(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role: return await ctx.send("❌ Role `SM` neexistuje.")
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"➖ Role **SM** odebrána.")
    else:
        await member.add_roles(role)
        await ctx.send(f"➕ Role **SM** přidělena.")

def run_discord_bot(bot_token):
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            print("==> Pokus o start Discord Bota...", flush=True)
            loop.run_until_complete(bot.start(bot_token))
        except Exception as e:
            print(f"==> [DISCORD CHYBA] Bot havaroval: {e}", flush=True)
            print("==> Čekám 10 vteřin před novým pokusem...", flush=True)
            time.sleep(10)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        Thread(target=run_discord_bot, args=(token,), daemon=True).start()
    else:
        print("KRITICKÁ CHYBA: DISCORD_TOKEN chybí! (Web běží dál bez Bota)")

    run_web()
