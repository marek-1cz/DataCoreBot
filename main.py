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
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html.replace('{{ deploy_time }}', DEPLOY_TIME)), **kwargs)

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

@app.route('/dashboard/app_management', methods=['GET'], strict_slashes=False)
def dashboard_app_management():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    soft_enabled = True
    dl_enabled = True
    try:
        if db:
            s_resp = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled"]).execute().data or []
            for s in s_resp:
                if s['setting_key'] == 'software_enabled':
                    soft_enabled = str(s['setting_value']).lower() != 'false'
                elif s['setting_key'] == 'downloads_enabled':
                    dl_enabled = str(s['setting_value']).lower() != 'false'
    except: pass
    return render_dashboard(HTML_APP_MANAGEMENT, soft_enabled=soft_enabled, dl_enabled=dl_enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/toggle_software', methods=['POST'])
def toggle_software():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "software_enabled").execute()
        status_text = "ZAPNUT" if new_status.lower() == 'true' else "VYPNUT"
        flash(f'Globální stav softwaru byl změněn na: {status_text}', 'success')
        send_log("⚙️ Změna globálního stavu", f"Administrátor právě **{'ZAPNUL' if new_status.lower() == 'true' else 'VYPNUL'}** celý software.", 0xf59e0b)
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_downloads', methods=['POST'])
def toggle_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute()
        status_text = "POVOLENO" if new_status.lower() == 'true' else "ZAKÁZÁNO"
        flash(f'Stahování softwaru bylo: {status_text}', 'success')
        send_log("📥 Změna stahování", f"Administrátor právě **{'POVOLIL' if new_status.lower() == 'true' else 'ZAKÁZAL'}** stahování softwaru.", 0x3b82f6)
        trigger_setup_messages_update()
    ret = request.form.get('return_to', 'app_management')
    if ret == 'downloads':
        return redirect(url_for('dashboard_downloads'))
    return redirect(url_for('dashboard_app_management'))

class DynamicDownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, emoji="📥", custom_id="persistent_install_main_btn")
    async def dl_btn(self, interaction, button):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            pass
            
        db = get_db()
        settings_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}]
        if str(settings_resp[0].get('setting_value', '')).lower() == 'false': 
            return await interaction.followup.send("**⛔ Stahování je momentálně globálně zakázáno administrátorem.** Zkuste to prosím později.", ephemeral=True)
            
        chk = db.table("users").select("is_banned").eq("discord_id", str(interaction.user.id)).execute()
        if chk.data and chk.data[0].get('is_banned'):
            return await interaction.followup.send("**⛔ Přístup zamítnut:** Váš účet má udělený BAN a stahování bylo zablokováno.", ephemeral=True)

        class DynamicRulesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, emoji="✅")
            async def agree(self, i2, b2):
                try:
                    await i2.response.defer(ephemeral=True)
                except:
                    pass
                await i2.followup.send("<a:loading:123> Ověřuji profil...", ephemeral=True)
                
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
                        db.table("users").insert({"app_id": nid, "discord_id": d_id, "nick": n, "role": r, "hwid": "", "ip_address": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
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
            async def disagree(self, i2, b2): 
                try:
                    await i2.response.defer(ephemeral=True)
                except:
                    pass
                await i2.edit_original_response(content="**Akce zrušena.**", view=None)
                
        await interaction.followup.send("**PODMÍNKY UŽÍVÁNÍ:**\n1. Přísný zákaz šíření, kopírování nebo sdílení aplikace bez výslovného souhlasu autora.\n2. Systém využívá HWID ochranu a shromažďuje telemetrická data pro zajištění správného chodu a bezpečnosti aplikace.\n3. Každý pokus o modifikaci kódu nebo obcházení zabezpečení povede k okamžitému a trvalému zablokování.\n\nSouhlasíte s těmito podmínkami?", view=DynamicRulesView(), ephemeral=True)

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
    # Přidáno run_simple, protože standartní app.run někdy na Koyebu neprochází Health Checky kvůli multi-threadingu s Botem.
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', port, app, use_reloader=False)

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        Thread(target=run_discord_bot, args=(token,), daemon=True).start()
    else:
        print("KRITICKÁ CHYBA: DISCORD_TOKEN chybí! (Web běží dál bez Bota)")

    run_web()
