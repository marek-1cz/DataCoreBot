# -*- coding: utf-8 -*-
import os
import sys
import time
import signal
import atexit
from datetime import datetime
import time
import discord
from discord.ext import commands, tasks
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from functools import wraps
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
import uuid
import urllib.request
import http.cookiejar
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback
import re
import gc
import random
import logging
import io
from werkzeug.exceptions import HTTPException

from interaktivnimapa import mapa_bp, start_map_background_task, DEPOT_DISCORD_QUEUE, DEPOT_ZONES

try:
    from html_templates import *
except ImportError as e:
    print(f"KRITICKÁ CHYBA IMPORTU ŠABLON: {e}")

_template_names = [
    'BASE_HTML', 'PUBLIC_LAYOUT', 'DASHBOARD_LAYOUT', 'HTML_HOME', 'HTML_DOWNLOADS_MAIN',
    'HTML_TEAM', 'HTML_PUBLIC_STATS', 'HTML_CLAIM', 'HTML_STATS', 'HTML_APP_MANAGEMENT',
    'HTML_NOTIFICATIONS', 'HTML_DOWNLOADS_MGMT', 'HTML_PENDING_ROLES', 'HTML_TEAM_ADD',
    'HTML_IDS', 'HTML_DASHBOARD_MAIN', 'HTML_SUPPORTERS', 'HTML_SUPPORTERS_MGMT',
    'HTML_FEEDBACK', 'HTML_WAIT_AUTH', 'HTML_LOGIN', 'HTML_PROVOZ_IDPK', 'HTML_REGISTER', 'HTML_UCET'
]
for _name in _template_names:
    if _name not in globals():
        globals()[_name] = f"<div style='background:#0f172a; color:#ef4444; padding:40px; text-align:center; font-family:sans-serif;'><h2>CHYBA ŠABLONY</h2><p>Šablona <b>{_name}</b> chybí!</p></div>"

try:
    from status_dashboard import HTML_STATUS_SECTION
except ImportError:
    HTML_STATUS_SECTION = ""

os.environ['TZ'] = 'Europe/Prague'
try:
    time.tzset()
except AttributeError:
    pass

print("=== START PROJEKTU OIS IDPK ===", flush=True)

import secrets as _secrets
import hmac as _hmac
import hashlib as _hashlib
from collections import defaultdict

app = Flask(__name__)
# ── Secret key MUSTÍ být nastaven jako env proměnná FLASK_SECRET_KEY ──
_flask_secret = os.environ.get('FLASK_SECRET_KEY')
if not _flask_secret:
    # Fallback pro dev prostředí – v produkci VZDY nastav env!
    _flask_secret = _secrets.token_hex(64)
    print('[SECURITY] VAROVANI: FLASK_SECRET_KEY neni nastaven! Pouzivam nahodny klic (sessions se resetuji pri restartu).', flush=True)
app.secret_key = _flask_secret
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Koyeb bezi na HTTPS

app.register_blueprint(mapa_bp)

# ── Whitelist povolených originů pro CORS ──
_CORS_ORIGINS = {
    'https://datacorebot.koyeb.app',
    'https://ois-idpk.cz',
    'https://www.ois-idpk.cz',
}

@app.after_request
def add_security_headers(response):
    # CORS – pouze whitelisted origins
    origin = request.headers.get('Origin', '')
    if origin in _CORS_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Range'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    # Bezpečnostní hlavicky
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval';"
    return response

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return f"<div style='background:#0f172a; color:#f59e0b; padding:40px; font-family:sans-serif; text-align:center; height:100vh; box-sizing:border-box;'><h2 style='font-size:40px;'>CHYBA {e.code}</h2><p style='font-size:18px; color:white;'>Stránka nebyla nalezena.</p><a href='/' style='display:inline-block; margin-top:20px; padding:10px 20px; background:#38bdf8; color:black; text-decoration:none; font-weight:bold; border-radius:5px;'>Zpět domů</a></div>", e.code
    # 500 – NIKDY nezobrazovat traceback věřejnosti!
    print('[ERROR 500]', traceback.format_exc(), flush=True)
    return "<div style='background:#0f172a; color:#ef4444; padding:40px; font-family:sans-serif; text-align:center;'><h2>Došlo k interní chybě.</h2><p>Chyba byla zalogována. Kontaktujte administrátora.</p><a href='/' style='background:#334155;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;'>Zpět</a></div>", 500

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
BMAC_WEBHOOK_SECRET = os.environ.get("BMAC_WEBHOOK_SECRET", "")
_db_client = None

# ── In-memory rate limiter (jednoduchý, bez externí závislosti) ──
_rl_store: dict = defaultdict(list)

def _rate_limit_check(key: str, max_calls: int, window_seconds: int) -> bool:
    """Vrátí True pokud je povolen průchod, False pokud je limit překročen."""
    import time as _time
    now = _time.monotonic()
    window_start = now - window_seconds
    _rl_store[key] = [t for t in _rl_store[key] if t > window_start]
    if len(_rl_store[key]) >= max_calls:
        return False
    _rl_store[key].append(now)
    return True

def get_db():
    global _db_client
    try:
        if _db_client is None and SUPABASE_URL and SUPABASE_KEY:
            _db_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _db_client
    except Exception as e:
        print(f"Chyba připojení k DB: {e}")
    return None

def get_system_statuses():
    try:
        db = get_db()
        if db:
            s_resp = db.table("settings").select("setting_value").eq("setting_key", "system_statuses").execute().data
            if s_resp:
                return json.loads(s_resp[0]['setting_value'])
    except:
        pass
    return {}

def send_magic_link_email(to_email, token, intent='login'):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("[AUTH] SMTP není nastaveno!")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Přihlášení do aplikace OIS IDPK"
        msg["From"] = f"DataCore Bot <{SMTP_EMAIL}>"
        msg["To"] = to_email

        base_url = request.url_root.rstrip('/')
        login_url = f"{base_url}/api/auth/finalize?token={token}&type=email&intent={intent}"
        
        html = f"""
        <html>
          <body style="background-color: #ffffff; color: #000000; font-family: sans-serif; padding: 40px; text-align: center;">
            <p style="color: #000000; font-size: 16px; text-align: left; max-width: 500px; margin: 0 auto 20px auto;">Dobrý den,<br><br>posíláme odkaz pro přístup do aplikace OIS IDPK. Pro dokončení přihlášení stačí kliknout na tlačítko níže:</p>
            <a href="{login_url}" style="display: inline-block; background-color: #38bdf8; color: #000000; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin-bottom: 20px;">Potvrdit přihlášení</a>
            <p style="color: #000000; font-size: 16px; text-align: left; max-width: 500px; margin: 0 auto 20px auto;">Nebo můžete ručně zadat tento 5místný kód: <strong>{token}</strong></p>
            <p style="color: #000000; font-size: 14px; text-align: left; max-width: 500px; margin: 30px auto 10px auto;">Pokud se právě do aplikace nepřihlašujete, nic se neděje a e-mail můžete v klidu smazat. Váš účet je v bezpečí.</p>
            <p style="color: #000000; font-size: 14px; text-align: left; max-width: 500px; margin: 0 auto;">Hezký den přeje<br><br>Tým Projekt OIS IDPK</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[AUTH] Chyba odesílání e-mailu: {e}")
        return False

class AppAuthView(discord.ui.View):
    def __init__(self, token="", discord_id="", is_dm=True):
        super().__init__(timeout=None)
        self.token = token
        self.discord_id = str(discord_id)
        self.is_dm = is_dm

    @discord.ui.button(label="Schválit přihlášení", style=discord.ButtonStyle.success, emoji="✅", custom_id="app_auth_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="✅ **Přihlášení úspěšně schváleno!**", embed=None, view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="app_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="❌ **Přihlášení bylo zamítnuto.**", embed=None, view=None)

class DashboardAuthView(discord.ui.View):
    def __init__(self, token="", discord_id=""):
        super().__init__(timeout=None)
        self.token = token
        self.discord_id = str(discord_id)

    @discord.ui.button(label="Schválit přístup", style=discord.ButtonStyle.success, emoji="✅", custom_id="dash_auth_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="✅ **Přístup na webový Dashboard byl schválen!**", embed=None, view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="dash_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="❌ **Přístup na Dashboard zamítnut.**", embed=None, view=None)

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
            send_log("❌ Selhání stahování", f"Úložiště zablokovalo stahování pro hráče `{nick}`.", 0xef4444)
            return "Chyba na straně úložiště."
        def generate():
            try:
                while True:
                    chunk = resp.read(1024 * 128)
                    if not chunk: break
                    yield chunk
            except Exception as stream_err:
                send_log("⚠️ Spojení přerušeno", f"Uživateli `{nick}` se přerušilo stahování.\nDůvod: {stream_err}", 0xf59e0b)
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
    embed = discord.Embed(title="📥 Projekt OIS IDPK - Instalace", description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a stahování.", color=0x38bdf8)
    if not dl_enabled:
        embed.color = 0xef4444
        embed.add_field(name="⛔ STAHOVÁNÍ JE NYNÍ VYPNUTO", value="Administrátor dočasně zakázal stahování.", inline=False)
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
                    return f"~~• {v['version_name']}~~ ❌"
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
    embed.set_footer(text="Pokud máte BAN, systém vás ke stahování nepustí.")
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
        except Exception:
            pass
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
    data_list.sort(key=lambda x: (float(x.get('norm_val', 0)), str(x.get('id', ''))), reverse=True)
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
    except:
        pass
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
    except:
        pass

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
                        await member.send(embed=discord.Embed(title="🎉 Děkujeme za obrovskou podporu!", description=f"Byly ti přiděleny exkluzivní role:\n\n{roles_str}", color=0x38bdf8))
                    except:
                        pass
                break
    except:
        pass
    return success

async def announce_new_supporter(discord_nick, amount_str, message, role_names_list):
    if not bot.is_ready(): return
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="⭐・podporovatelé")
        if channel:
            roles_str = ", ".join([f"**{r}**" for r in role_names_list])
            embed = discord.Embed(title="🎉 MÁME NOVÉHO PODPOROVATELE!", description=f"Uživatel **{discord_nick}** právě podpořil náš projekt a získal exkluzivní role {roles_str}!", color=0xf59e0b)
            embed.add_field(name="💰 Výše podpory", value=f"**{amount_str}**", inline=False)
            if message and message.strip(): embed.add_field(name="📝 Vzkaz", value=f"*{message}*", inline=False)
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

def _get_avatar_html(req):
    cookie_token = req.cookies.get('web_session_token')
    if cookie_token:
        try:
            db = get_db()
            user = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
            if user:
                u = user[0]

                avatar_src = u.get('avatar_url')
                img_tag = f'<img src="{avatar_src}" style="width:100%; height:100%; object-fit:cover;">' if avatar_src else '<i class="fas fa-user-circle" style="color:#94a3b8; font-size:44px;"></i>'
                display_name = u.get('nick') or u.get('email') or 'Uživatel'
                discord_id_text = f"<br>Discord ID: {u.get('discord_id')}" if u.get('discord_id') else ""
                
                role_str = u.get('role') or ''
                if 'SA' in role_str:
                    role_text = "SUPER ADMIN"
                    role_bg = "#ef4444"
                elif 'DEV' in role_str:
                    role_text = "DEVELOPER"
                    role_bg = "#10b981"
                elif 'BT' in role_str:
                    role_text = "BETA TESTER"
                    role_bg = "#1e3a8a"
                else:
                    role_text = "User"
                    role_bg = "transparent"

                return f"""
                <div class="user-avatar-wrap" style="position:relative; margin-left:15px; cursor:pointer; display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.05); padding:5px 15px 5px 5px; border-radius:30px; border:1px solid #334155; transition:0.3s;" onclick="let d=this.querySelector('.user-dropdown-menu'); if(d) d.style.display=d.style.display==='none'?'block':'none';" onmouseover="this.style.borderColor='#38bdf8'; this.style.boxShadow='0 0 10px rgba(56,189,248,0.5)';" onmouseout="this.style.borderColor='#334155'; this.style.boxShadow='none';">
                  <div style="width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,0.1); border:2px solid #38bdf8; display:flex; align-items:center; justify-content:center; overflow:hidden; box-shadow: 0 0 10px rgba(56,189,248,0.5);">
                    {img_tag}
                  </div>
                  <div class="user-role-switcher" data-name="{display_name}" data-role="{role_text}" data-bg="{role_bg}" style="display:flex; align-items:center;">
                    <span class="switcher-text" data-showing="name" style="color:white; font-weight:bold; font-size:14px; max-width:120px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; background:transparent; padding:2px 6px; border-radius:6px; transition:0.5s;">{display_name}</span>
                  </div>
                  <script>
                  if(!window.roleSwitcherStarted) {{
                      window.roleSwitcherStarted = true;
                      setInterval(() => {{
                          document.querySelectorAll('.user-role-switcher').forEach(el => {{
                              let span = el.querySelector('.switcher-text');
                              let isName = span.getAttribute('data-showing') !== 'role';
                              if(isName) {{
                                  span.innerText = el.getAttribute('data-role');
                                  span.style.background = el.getAttribute('data-bg');
                                  span.setAttribute('data-showing', 'role');
                              }} else {{
                                  span.innerText = el.getAttribute('data-name');
                                  span.style.background = 'transparent';
                                  span.setAttribute('data-showing', 'name');
                              }}
                          }});
                      }}, 10000);
                  }}
                  </script>
                  
                  <div class="user-dropdown-menu" style="display:none; position:absolute; top:calc(100% + 10px); right:0; background:rgba(15,23,42,0.95); backdrop-filter:blur(10px); border:1px solid #334155; border-radius:10px; width:220px; box-shadow: 0 5px 20px rgba(0,0,0,0.8); z-index:9000; padding:15px; text-align:left; box-sizing:border-box;">
                    <div style="color:white; font-size:14px; font-weight:bold; margin-bottom:5px;">{display_name}</div>
                    <div style="color:#94a3b8; font-size:11px; margin-bottom:15px; word-break:break-all;">{u.get('email') or 'Neznámý e-mail'}{discord_id_text}</div>
                    <a href="/ucet" style="display:block; width:auto; box-sizing:border-box; background:#38bdf8; color:black; text-align:center; padding:8px; border-radius:6px; text-decoration:none; font-weight:bold; margin: 0 0 8px 0;"><i class="fas fa-cog"></i> Můj Účet</a>
                    <button onclick="fetch('/api/auth/logout', {{method:'POST'}}).then(()=>location.reload())" style="display:block; width:100%; box-sizing:border-box; background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid #ef4444; padding:8px; border-radius:6px; cursor:pointer; font-weight:bold; transition:0.2s; margin:0;" onmouseover="this.style.background='#ef4444'; this.style.color='white';" onmouseout="this.style.background='rgba(239,68,68,0.2)'; this.style.color='#ef4444';"><i class="fas fa-sign-out-alt"></i> Odhlásit se</button>
                  </div>
                </div>
                """
        except: pass
    return """
    <a href="/register" class="user-avatar-wrap" style="margin-left:15px; text-decoration:none; display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.05); padding:5px 15px 5px 5px; border-radius:30px; border:1px solid #334155; transition:0.3s;" onmouseover="this.style.borderColor='#38bdf8'; this.style.boxShadow='0 0 10px rgba(56,189,248,0.5)';" onmouseout="this.style.borderColor='#334155'; this.style.boxShadow='none';">
      <div style="width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,0.1); border:1px solid #94a3b8; display:flex; align-items:center; justify-content:center; overflow:hidden; transition:0.3s;">
        <i class="fas fa-user-circle" style="color:#94a3b8; font-size:44px;"></i>
      </div>
      <span style="color:#94a3b8; font-weight:bold; font-size:14px;">Přihlásit se</span>
    </a>
    """

def render_public(template_string, **kwargs):
    avatar = _get_avatar_html(request)
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string).replace('__AVATAR__', avatar)
    if 'statuses' not in kwargs:
        kwargs['statuses'] = get_system_statuses()
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    if 'status_section' not in kwargs:
        kwargs['status_section'] = HTML_STATUS_SECTION
    if 'statuses' not in kwargs:
        kwargs['statuses'] = get_system_statuses()
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html.replace('{{ deploy_time }}', DEPLOY_TIME)), **kwargs)

# ─── Dashboard oprávnění ────────────────────────────────────────────────────
# Úrovně: superadmin > admin > viewer
# Nastavuje se sloupcem dashboard_level v tabulce users.
# Pokud sloupec neexistuje, fallback = 'admin' pro starý dashboard_access=True.

DASH_LEVEL_ORDER = {'superadmin': 3, 'admin': 2, 'viewer': 1}

def _get_dash_level(discord_id: str) -> str:
    """Vrátí dashboard_level uživatele nebo '' pokud nemá přístup."""
    try:
        db = get_db()
        if not db or not discord_id:
            return ''
        user = db.table('users').select('dashboard_access, dashboard_level, is_banned, is_deleted').eq('discord_id', discord_id).execute().data
        if not user:
            return ''
        u = user[0]
        if u.get('is_banned') or u.get('is_deleted'):
            return ''
        if not u.get('dashboard_access'):
            return ''
        # Fallback: pokud nemá nastaven dashboard_level, považujeme ho za 'admin'
        return str(u.get('dashboard_level') or 'admin').lower()
    except:
        return ''

def require_dash_level(min_level: str = 'viewer'):
    """Dekorátor – vyžaduje minimální dashboard_level. Přesměruje nebo vrátí 403."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('dashboard_main'))
            discord_id = session.get('discord_id')
            level = _get_dash_level(str(discord_id or ''))
            if not level:
                session.clear()
                flash('Váš přístup byl zrušen.', 'error')
                return redirect(url_for('dashboard_main'))
            if DASH_LEVEL_ORDER.get(level, 0) < DASH_LEVEL_ORDER.get(min_level, 1):
                flash(f'Tato akce vyžaduje oprávnění "{min_level}". Vaše úroveň: "{level}".', 'error')
                return redirect(url_for('dashboard_main'))
            return f(*args, **kwargs)
        return decorated
    return decorator
# ─────────────────────────────────────────────────────────────────────────────

@app.before_request
def check_session_validity():
    if request.headers.get('User-Agent', '').startswith('UptimeRobot'):
        return "OK", 200
    path = request.path
    def is_maintenance_exempt():
        if path == '/blocked': return True
        if path == '/login_blocked': return True
        if path.startswith('/dashboard'): return True
        if path.startswith('/api/keepalive'): return True
        if path.startswith('/static'): return True
        if path.startswith('/api/check_auth'): return True
        if path.startswith('/api/auth/status'): return True
        if path.startswith('/api/admin/check'): return True
        return False

    try:
        db = get_db()
        if db:
            settings_keys = ['web_maintenance', 'web_login_enabled']
            s_data = db.table('settings').select('setting_key, setting_value').in_('setting_key', settings_keys).execute().data or []
            s_map = {s['setting_key']: s['setting_value'] for s in s_data}

            maintenance = str(s_map.get('web_maintenance', 'False')).lower() == 'true'
            if maintenance and not is_maintenance_exempt():
                # Allow SM/SA/DEV admin bypass if logged in
                role = ""
                discord_id = session.get('discord_id')
                if session.get('logged_in') and discord_id:
                    u_data = db.table('users').select('role').eq('discord_id', discord_id).execute().data
                    if u_data:
                        role = u_data[0].get('role', '')
                if not any(r in role for r in ['SM', 'SA', 'DEV']):
                    return redirect('/blocked')

            web_login_enabled = str(s_map.get('web_login_enabled', 'True')).lower() != 'false'
            LOGIN_PATHS = ['/register', '/login', '/api/auth/discord/request', '/api/auth/email/request']
            if not web_login_enabled and path in LOGIN_PATHS:
                if request.is_json or path.startswith('/api/'):
                    return jsonify({'status': 'error', 'message': 'Přihlašování je z bezpečnostních důvodů dočasně nedostupné.'}), 503
                else:
                    return redirect('/login_blocked')
    except:
        pass

    if path.startswith('/dashboard/') and path not in ['/dashboard/wait_auth', '/dashboard/login_finalize']:
        if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    if path.startswith('/dashboard') and path not in ['/dashboard/wait_auth', '/dashboard/login_finalize'] and session.get('logged_in'):
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
            except:
                pass

async def update_member_roles(member, role_string):
    if not member: return
    try:
        role_map = {"SA": "web-sa", "DEV": "web-dev", "BT": "web-bt"}
        roles_to_assign = [r.strip() for r in (role_string or "").split(',') if r.strip()]
        
        target_discord_roles = [role_map.get(r, r) for r in roles_to_assign]
        
        # Add roles they should have
        for r_name in target_discord_roles:
            role = discord.utils.find(lambda r: r.name.lower() == r_name.lower(), member.guild.roles)
            if role and role not in member.roles:
                await member.add_roles(role)
                
        # Remove managed roles they shouldn't have anymore
        for internal_name, discord_name in role_map.items():
            if discord_name not in target_discord_roles:
                role = discord.utils.find(lambda r: r.name.lower() == discord_name.lower(), member.guild.roles)
                if role and role in member.roles:
                    await member.remove_roles(role)
                    
    except Exception as e:
        print(f"Chyba při updatu rolí: {e}", flush=True)

def sync_roles_from_flask(discord_id, role_string):
    async def sync():
        if not bot.is_ready(): return
        try:
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id)) or await guild.fetch_member(int(discord_id))
                if member: await update_member_roles(member, role_string)
        except:
            pass
    if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(sync(), bot.loop)

def check_version_access(db, app_version_from_pc, user):
    if user.get("admin_bypass") == True:
        return {"allowed": True}
    user_role_str = user.get("role", "")
    if not app_version_from_pc or str(app_version_from_pc).strip() == "":
        return {"allowed": False, "msg": "Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
    try:
        v_data = db.table("software_versions").select("*").eq("db_version", app_version_from_pc).execute().data
        if not v_data: return {"allowed": False, "msg": f"Verze '{app_version_from_pc}' neexistuje v databázi!"}
        v_info = v_data[0]
        if str(v_info.get("is_active", "True")).lower() == "false":
            return {"allowed": False, "msg": "Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
        eol = v_info.get("eol_date")
        if eol and str(eol).strip():
            try:
                eol_dt = datetime.strptime(str(eol).strip(), "%d.%m.%Y")
                if get_prague_time().replace(tzinfo=None) > eol_dt:
                    db.table("software_versions").update({"is_active": False}).eq("id", v_info["id"]).execute()
                    return {"allowed": False, "msg": "Nepodporovaná verze aplikace. Stáhněte si novou verzi přes náš Discord."}
            except:
                pass
        target = v_info.get("target_role", "User")
        if target != "User":
            roles = [r.strip() for r in user_role_str.split(",")] if user_role_str else []
            if "SA" not in roles and "DEV" not in roles:
                if target == "BT" and "BT" not in roles:
                    return {"allowed": False, "msg": "Tato verze je omezena pouze pro Beta Testery."}
                elif target == "DEV_SA":
                    return {"allowed": False, "msg": "Tato verze je neveřejná."}
        return {"allowed": True}
    except:
        return {"allowed": True}

class DynamicDownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, emoji="📥", custom_id="persistent_install_main_btn")
    async def dl_btn(self, interaction, button):
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            pass
        db = get_db()
        settings_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}]
        if str(settings_resp[0].get('setting_value', '')).lower() == 'false':
            return await interaction.followup.send("**⛔ Stahování je momentálně globálně zakázáno.** Zkuste to prosím později.", ephemeral=True)
        chk = db.table("users").select("is_banned").eq("discord_id", str(interaction.user.id)).execute()
        if chk.data and chk.data[0].get('is_banned'):
            return await interaction.followup.send("**⛔ Přístup zamítnut:** Váš účet má BAN.", ephemeral=True)

        class DynamicRulesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)

            @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, emoji="✅")
            async def agree(self, i2, b2):
                try:
                    await i2.response.defer(ephemeral=True)
                except:
                    pass
                try:
                    db = get_db()
                    d_id = str(i2.user.id)
                    n = i2.user.display_name
                    u_role = "User"
                    chk = db.table("users").select("*").eq("discord_id", d_id).execute()
                    pend_data = db.table("pending_roles").select("*").execute().data or []
                    pend = next((p for p in pend_data if p['discord_identifier'] in [d_id, n]), None)
                    if chk.data:
                        if chk.data[0].get('is_banned'): return await i2.followup.send("**Přístup zamítnut:** Máte BAN.", ephemeral=True)
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
                                            if (eol_dt - now).days <= 14: is_dl = False
                                            else: desc = f"Končí podpora: {eol_str}"
                                        except: pass
                                    if is_dl:
                                        opts.append(discord.SelectOption(label=v['version_name'], description=desc or "Dostupné pro vaši roli", value=str(v['id']), emoji="📦"))
                            if not opts: opts.append(discord.SelectOption(label="Žádná verze nenalezena", description="Pro vaše oprávnění aktuálně není nic ke stažení.", value="none"))
                            super().__init__(placeholder="Vyber verzi k instalaci...", options=opts)

                        async def callback(self, i3):
                            try: await i3.response.defer(ephemeral=True)
                            except: pass
                            if self.values[0] == "none": return await i3.followup.send("Pro vaše role nejsou dostupné žádné verze.", ephemeral=True)
                            t = str(uuid.uuid4())
                            get_db().table("users").update({"download_token": t}).eq("discord_id", str(i3.user.id)).execute()
                            link = f"https://datacorebot.koyeb.app/download/{t}?v={self.values[0]}"
                            await i3.followup.send(content=f"**Odkaz připraven:**\n🔗 {link}\n*Platí jen pro Vás.*", ephemeral=True)

                    v_view = discord.ui.View()
                    v_view.add_item(DynamicVersionSelect(3 if 'SA' in u_role or 'DEV' in u_role else (2 if 'BT' in u_role else 1)))
                    await i2.followup.send(content="**Ověření úspěšné.** Vyberte soubor:", view=v_view, ephemeral=True)
                except Exception as e:
                    await i2.followup.send(content=f"Chyba DB: {e}", ephemeral=True)

            @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, emoji="❌")
            async def disagree(self, i2, b2):
                try: await i2.response.defer(ephemeral=True)
                except: pass
                await i2.followup.send(content="**Akce zrušena.**", ephemeral=True)

        await interaction.followup.send("**PODMÍNKY UŽÍVÁNÍ:**\n1. Přísný zákaz šíření, kopírování nebo sdílení aplikace bez výslovného souhlasu autora.\n2. Systém využívá HWID ochranu a shromažďuje telemetrická data.\n3. Každý pokus o modifikaci kódu nebo obcházení zabezpečení povede k okamžitému zablokování.\n\nSouhlasíte s těmito podmínkami?", view=DynamicRulesView(), ephemeral=True)


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/report_error', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_report_error():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", "Neznámé ID"))
    nick = str(data.get("nick", "Neznámý"))
    error_type = str(data.get("type", "ERROR"))
    msg = str(data.get("message", "Neznámá chyba"))
    
    send_log(f"⚠️ APLIKAČNÍ CHYBA: {error_type}", f"**Hráč:** {nick} (`{discord_id}`)\n**Chyba:**\n`{msg}`", 0xef4444)
    
    return _cors_jsonify({"status": "success"})

@app.route('/api/keepalive', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_keepalive():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    return _cors_jsonify({"status": "ok", "message": "Server is running"})

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
        if discord_id and discord_id not in ("None", ""):
            try:
                u_line_res = db.table("user_stats_lines").select("*").eq("discord_id", discord_id).eq("line_name", line).execute().data
                if u_line_res: db.table("user_stats_lines").update({"play_count": int(u_line_res[0].get("play_count", 0)) + 1}).eq("id", u_line_res[0]["id"]).execute()
                else: db.table("user_stats_lines").insert({"discord_id": discord_id, "line_name": line, "play_count": 1}).execute()
            except: pass
        return _cors_jsonify({"status": "success"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

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
            if not cf_country or cf_country.lower() in ["neznámá", "unknown", "none"]: return
            country_name = cf_country; region = ""; country_code = ""
            try:
                url = f"http://ip-api.com/json/{clean_ip}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=2) as response:
                    geo_data = json.loads(response.read().decode())
                    if geo_data.get("status") == "success":
                        country_name = geo_data.get("country", country_name)
                        region = geo_data.get("regionName", "")
                        country_code = geo_data.get("countryCode", "").lower()
            except: pass
            
            # Use CF-IPCountry as a reliable fallback if ip-api fails or returns empty
            if not country_code:
                if cf_country.lower() != "neznámá":
                    country_code = "us" if cf_country.lower() == "us" else "cz" # simplified
            
            if not country_code or country_code.lower() == 'us': return
            combined_location = f"{country_code}|{country_name}|{region}"
            db.table("page_visits").insert({"ip": clean_ip, "country": combined_location, "visited_at": now_str}).execute()
        except: pass
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    country = request.headers.get('CF-IPCountry', 'Neznámá')
    Thread(target=log_visit, args=(ip, country)).start()
    return render_public(HTML_HOME)


@app.route('/provoz-idpk')
def provoz_idpk():
    """Rozcestník Provoz IDPK — Interaktivní mapa & Databáze autobusů"""
    return render_public(HTML_PROVOZ_IDPK)

@app.route('/led-panel')
def led_panel_landing():
    from led_panel_html import HTML_LED_PANEL
    return HTML_LED_PANEL

@app.route('/led-panel/app')
def led_panel_app():
    from led_panel_html import HTML_LED_PANEL
    return HTML_LED_PANEL

@app.route('/led-panel/view')
def led_panel_view():
    from led_panel_view import HTML_LED_PANEL_VIEW
    return HTML_LED_PANEL_VIEW

@app.route('/bukova')
def bukova_page():
    try:
        with open("bukova.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>CHYBA: Nenalezen soubor bukova.html</h1><p>{e}</p>"

# /mapa je zpracovávána blueprintem z interaktivnimapa.py (mapa_bp)

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
                searched_user = u; break
        if not searched_user: flash(f"Hráč s ID '{search_query}' nebyl nalezen.", "warning")
    versions = db.table("software_versions").select("*").eq("is_active", True).order("id", desc=True).execute().data or []
    user_ver = next((v['version_name'] for v in versions if v['target_role'] == 'User'), "Žádná")
    bt_ver = next((v['version_name'] for v in versions if v['target_role'] == 'BT'), "Žádná")
    activated_users = len([u for u in all_users if u.get('hwid') and str(u.get('hwid')) not in ['None', '']])
    total_time_mins = 0; total_launches = 0
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
    sessions_today = db.table("app_sessions").select("discord_id, start_time, end_time").like("start_time", f"{today_str}%").execute().data or []
    today_user_mins = {}
    today_user_launches = {}
    today_mins = 0
    for s in sessions_today:
        try:
            st_str = s.get('start_time'); et_str = s.get('end_time')
            did = s.get('discord_id')
            if did and did != 'None':
                today_user_launches[did] = today_user_launches.get(did, 0) + 1
            if st_str and et_str:
                fmt_st = "%d.%m.%Y %H:%M:%S" if st_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                fmt_et = "%d.%m.%Y %H:%M:%S" if et_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                st = datetime.strptime(st_str, fmt_st); et = datetime.strptime(et_str, fmt_et)
                diff = int((et - st).total_seconds() / 60)
                if diff > 0: 
                    today_mins += diff
                    if did and did != 'None':
                        today_user_mins[did] = today_user_mins.get(did, 0) + diff
        except: pass
    today_hours = today_mins // 60; today_rem_mins = today_mins % 60
    today_time_str = f"{today_hours}h {today_rem_mins}m" if today_hours > 0 else f"{today_rem_mins}m"
    
    top_today_time_id = max(today_user_mins, key=today_user_mins.get) if today_user_mins else None
    top_today_time_nick = "Neznámý"
    top_today_time_val = today_user_mins.get(top_today_time_id, 0) if top_today_time_id else 0
    if top_today_time_id:
        for u in all_users:
            if str(u.get('discord_id')) == str(top_today_time_id): top_today_time_nick = u.get('nick', 'Neznámý'); break
            
    top_today_launch_id = max(today_user_launches, key=today_user_launches.get) if today_user_launches else None
    top_today_launch_nick = "Neznámý"
    top_today_launch_val = today_user_launches.get(top_today_launch_id, 0) if top_today_launch_id else 0
    if top_today_launch_id:
        for u in all_users:
            if str(u.get('discord_id')) == str(top_today_launch_id): top_today_launch_nick = u.get('nick', 'Neznámý'); break

    month_str = get_prague_time().strftime(".%m.%Y")
    sessions_month = db.table("app_sessions").select("start_time, end_time").like("start_time", f"%{month_str}%").execute().data or []
    month_mins = 0
    for s in sessions_month:
        try:
            st_str = s.get('start_time'); et_str = s.get('end_time')
            if st_str and et_str:
                fmt_st = "%d.%m.%Y %H:%M:%S" if st_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                fmt_et = "%d.%m.%Y %H:%M:%S" if et_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                st = datetime.strptime(st_str, fmt_st); et = datetime.strptime(et_str, fmt_et)
                diff = int((et - st).total_seconds() / 60)
                if diff > 0: month_mins += diff
        except: pass
    month_hours = month_mins // 60; month_rem_mins = month_mins % 60
    month_time_str = f"{month_hours}h {month_rem_mins}m" if month_hours > 0 else f"{month_rem_mins}m"

    supporters_data = db.table("supporters").select("id").eq("status", "completed").execute().data or []
    total_supporters = len(supporters_data)
    valid_time_users = [u for u in all_users if int(u.get('total_time') or 0) > 0]
    top_time_users = sorted(valid_time_users, key=lambda x: int(x.get('total_time') or 0), reverse=True)[:5]
    valid_launch_users = [u for u in all_users if int(u.get('launch_count') or 0) > 0]
    top_launches = sorted(valid_launch_users, key=lambda x: int(x.get('launch_count') or 0), reverse=True)[:5]
    try:
        top_lines = db.table("stats_lines").select("*").order("play_count", desc=True).limit(10).execute().data or []
        top_stops = db.table("stats_stops").select("*").order("announce_count", desc=True).limit(10).execute().data or []
        all_lines = db.table("stats_lines").select("*").order("play_count", desc=True).execute().data or []
        all_stops = db.table("stats_stops").select("*").order("announce_count", desc=True).execute().data or []
        
        total_lines_driven = sum(int(l.get('play_count') or 0) for l in all_lines)
        total_stops_announced = sum(int(s.get('announce_count') or 0) for s in all_stops)
        
        user_lines_data = db.table("user_stats_lines").select("discord_id, play_count").execute().data or []
        player_line_counts = {}
        for ul in user_lines_data:
            did = ul.get('discord_id')
            if did and did != 'None':
                player_line_counts[did] = player_line_counts.get(did, 0) + int(ul.get('play_count') or 0)
        
        user_stops_data = db.table("user_stats_stops").select("discord_id, announce_count").execute().data or []
        player_stop_counts = {}
        for us in user_stops_data:
            did = us.get('discord_id')
            if did and did != 'None':
                player_stop_counts[did] = player_stop_counts.get(did, 0) + int(us.get('announce_count') or 0)
                
        def get_nick(did):
            for u in all_users:
                if str(u.get('discord_id')) == str(did): return u.get('nick', 'Neznámý')
            return "Neznámý"

        top_5_lines_users = [{"nick": get_nick(did), "count": count} for did, count in sorted(player_line_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        top_5_stops_users = [{"nick": get_nick(did), "count": count} for did, count in sorted(player_stop_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        top_player_id = max(player_line_counts, key=player_line_counts.get) if player_line_counts else None
        top_player_lines = player_line_counts.get(top_player_id, 0) if top_player_id else 0
        top_player_nick = get_nick(top_player_id) if top_player_id else "Neznámý"
    except:
        top_lines = top_stops = all_lines = all_stops = []
        total_lines_driven = 0
        total_stops_announced = 0
        top_5_lines_users = []
        top_5_stops_users = []
        top_player_nick = "Neznámý"
        top_player_lines = 0
        
    searched_user_lines = []; searched_user_stops = []; all_searched_user_lines = []; all_searched_user_stops = []
    if searched_user:
        d_id = searched_user.get('discord_id')
        try:
            all_searched_user_lines = db.table("user_stats_lines").select("*").eq("discord_id", d_id).order("play_count", desc=True).execute().data or []
            all_searched_user_stops = db.table("user_stats_stops").select("*").eq("discord_id", d_id).order("announce_count", desc=True).execute().data or []
            searched_user_lines = all_searched_user_lines[:5]; searched_user_stops = all_searched_user_stops[:5]
        except: pass
    return render_public(HTML_PUBLIC_STATS, user_ver=user_ver, bt_ver=bt_ver, activated_users=activated_users, total_supporters=total_supporters, today_time_str=today_time_str, total_hours=total_hours, total_launches=total_launches, top_time=top_time_users, top_launches=top_launches, top_lines=top_lines, top_stops=top_stops, all_lines=all_lines, all_stops=all_stops, searched_user=searched_user, searched_user_lines=searched_user_lines, searched_user_stops=searched_user_stops, all_searched_user_lines=all_searched_user_lines, all_searched_user_stops=all_searched_user_stops, month_time_str=month_time_str, total_lines_driven=total_lines_driven, total_stops_announced=total_stops_announced, top_player_nick=top_player_nick, top_player_lines=top_player_lines, top_5_lines_users=top_5_lines_users, top_5_stops_users=top_5_stops_users, top_today_time_nick=top_today_time_nick, top_today_time_val=top_today_time_val, top_today_launch_nick=top_today_launch_nick, top_today_launch_val=top_today_launch_val)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    try:
        db = get_db()
        if not db: return _cors_jsonify({"error": "DB not ready"}), 500
        data = db.table("supporters").select("name, amount, message, created_at").eq("status", "completed").execute().data or []
        support_data = process_supporters(data)
        return _cors_jsonify({"supporters": support_data})
    except Exception as e: return _cors_jsonify({"error": str(e)}), 500

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
            flash('Chyba: Platba pod tímto jménem již byla spárována!', 'error')
            return redirect(url_for('claim_role'))
        valid_records = []
        now = get_prague_time().replace(tzinfo=None)
        for r in all_records:
            if r['status'] == 'pending': valid_records.append(r)
            elif r['status'] == 'manual_review':
                try:
                    c_time = datetime.strptime(r['created_at'], "%d.%m.%Y %H:%M")
                    if (now - c_time).total_seconds() <= 86400: valid_records.append(r)
                except: valid_records.append(r)
        if valid_records:
            record = valid_records[0]
            discord_roles, db_role_string = calculate_roles_for_supporter(record.get('amount', '0'))
            if user_exists_sync(discord_nick):
                if bot.loop and bot.loop.is_running() and bot.is_ready():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
                    asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_nick, record.get('amount', '0'), record.get('message', ''), discord_roles), bot.loop)
                db.table("supporters").update({"status": "completed", "discord_nick": discord_nick, "sys_note": "Spárováno včas"}).eq("id", record['id']).execute()
                flash('Úspěch! Role přidělena.', 'success')
            else:
                db.table("supporters").update({"status": "manual_review", "discord_nick": discord_nick, "sys_note": "Účet nenalezen."}).eq("id", record['id']).execute()
                flash('Discord účet nenalezen! Odesláno administrátorovi.', 'warning')
        else:
            db.table("supporters").insert({"name": bmac_name, "discord_nick": discord_nick, "amount": "Neznámá", "message": "", "sys_note": "Nezaznamenáno z BMAC.", "status": "manual_review", "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            flash('Platba nenalezena. Odesláno administrátorovi.', 'warning')
        return redirect(url_for('claim_role'))
    return render_public(HTML_CLAIM)

@app.route('/webhook/bmac', methods=['POST', 'OPTIONS'])
def bmac_webhook():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    if BMAC_WEBHOOK_SECRET:
        sig_header = request.headers.get('X-Signature-Sha256', '')
        expected = 'sha256=' + _hmac.new(BMAC_WEBHOOK_SECRET.encode(), request.data, _hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(expected, sig_header):
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        data = payload.get('data', payload) if isinstance(payload, dict) else {}
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
            send_log("🍕 Nová platba zaznamenána!", f"Uživatel **{name}** poslal **{amount_str}**.\nStatus: `{status}`", 0xF4CC17)
            if status == 'completed' and bot.loop and bot.loop.is_running() and bot.is_ready():
                asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_identifier, discord_roles), bot.loop)
                asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_identifier, amount_str, message, discord_roles), bot.loop)
        if request.method == 'GET': return f"<h1>ÚSPĚCH! 🎉</h1>"
        return jsonify({"status": "success"}), 200
    except Exception as e:
        if request.method == 'GET': return f"<h1>❌ CHYBA DATABÁZE</h1><p>{str(e)}</p>"
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db: return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if not resp.data: return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný odkaz, nebo již vypršel!</h2></div>")
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
            <div id="loading-area" style="display: none;"><p style="color: var(--text-main); font-weight: bold;">Zahajuji stahování...</p></div>
            <div id="success-area" style="display: none; margin-top: 20px;"><h3 style="color: var(--success); margin-top: 0;"><i class="fas fa-check"></i> Úspěšně zahájeno</h3><p style="color: var(--text-main); font-size: 14px;">Nezapomeňte soubor rozbalit pomocí <b>7-ZIP</b> nebo <b>WinRAR</b>.</p></div>
            <div id="error-area" style="display: none; margin-top: 20px;"><h3 style="color: var(--danger);">Chyba</h3><p id="error-msg" style="color: var(--danger);"></p></div>
            <script>
            async function startDownload() {{
                document.getElementById('download-area').style.display='none';
                document.getElementById('loading-area').style.display='block';
                try {{
                    let response = await fetch("/api/pre_download/{token}?v={version_id}");
                    let data = await response.json();
                    if (data.status === 'ok') {{
                        window.location.href = "/api/stream_download/{token}?v={version_id}";
                        setTimeout(() => {{ document.getElementById('loading-area').style.display='none'; document.getElementById('success-area').style.display='block'; }}, 2000);
                    }} else {{
                        document.getElementById('loading-area').style.display='none';
                        document.getElementById('error-area').style.display='block';
                        document.getElementById('error-msg').innerText = data.message || "Neznámá chyba.";
                    }}
                }} catch(e) {{
                    document.getElementById('loading-area').style.display='none';
                    document.getElementById('error-area').style.display='block';
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
    if not resp.data: return jsonify({"status": "error", "message": "Neplatný nebo vypršelý odkaz."})
    user = resp.data[0]
    if user.get("is_banned") or user.get("is_deleted"): return jsonify({"status": "error", "message": "Přístup zamítnut."})
    version_id = request.args.get('v')
    v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
    if not v_resp.data: return jsonify({"status": "error", "message": "Tato verze již není k dispozici."})
    now_prague = get_prague_time()
    last_log = db.table("download_logs").select("*").eq("discord_id", user['discord_id']).order("id", desc=True).limit(1).execute().data
    if last_log:
        try:
            time_str = last_log[0]['downloaded_at']
            if time_str.count(':') == 2: last_dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M:%S")
            else: last_dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M")
            if (now_prague - last_dt).total_seconds() < 30: return jsonify({"status": "error", "message": "Počkejte 30 vteřin před dalším stažením."})
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
    db.table("users").update({"download_token": ""}).eq("discord_id", user['discord_id']).execute()
    try: db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": v_data['version_name'], "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M:%S")}).execute()
    except: pass
    return stream_proxy_file(v_data['file_url'], v_data['version_name'], user['discord_id'], user.get('nick', 'Neznámý'))

@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_status():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    try:
        db = get_db()
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "disabled", "message": "OMLOUVÁME SE, SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT."})
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
            if len(identifier) < 10:
                user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},app_id.eq.{int(identifier)}").execute()
            else:
                user_resp = db.table("users").select("*").eq("discord_id", identifier).execute()
        else:
            user_resp = db.table("users").select("*").eq("nick", identifier).execute()
        if not user_resp.data:
            return _cors_jsonify({"status": "error", "message": "Uživatel nenalezen."})
        user = user_resp.data[0]
        discord_id = user.get("discord_id")
        if user.get("is_banned"):
            return _cors_jsonify({"status": "banned", "message": "Tento účet má BAN."})
        if user.get("is_deleted"):
            return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán."})
        version_check = check_version_access(db, app_version, user)
        if not version_check["allowed"]:
            return _cors_jsonify({"status": "error", "message": version_check["msg"]})
        db_hwid = user.get("hwid")
        db_ip = user.get("ip_address")
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                db.table("users").update({"hwid": req_hwid, "ip_address": client_ip}).eq("discord_id", discord_id).execute()
        else:
            if str(db_hwid) != req_hwid:
                if db_ip and str(db_ip).strip() != "" and db_ip == client_ip:
                    db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                else:
                    return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID: Váš počítač ani IP adresa nesouhlasí."})
            else:
                if not db_ip or str(db_ip).strip() == "":
                    db.table("users").update({"ip_address": client_ip}).eq("discord_id", discord_id).execute()
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
        async def send():
            try:
                u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                if u: await u.send(embed=discord.Embed(title="🛡️ Ověření přihlášení", description=f"Pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPotvrďte přístup tlačkem níže.", color=0x38bdf8), view=AppAuthView(token, discord_id, is_dm=True))
            except: pass
        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
        return _cors_jsonify({"status": "waiting", "discord_id": discord_id})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
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
        if not version_check["allowed"]: return _cors_jsonify({"status": "error", "message": version_check["msg"]})
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
                return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
            else:
                return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID/IP: Nesouhlasí."})
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
        if discord_id.startswith("email-"):
            user_id = discord_id.split("-")[1]
            user_resp = db.table("users").select("launch_count, total_time, discord_id").eq("id", user_id).execute()
        else:
            user_resp = db.table("users").select("launch_count, total_time, discord_id").eq("discord_id", discord_id).execute()
        
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        updates = {"last_active": now_str, "is_online": True}
        if action == "start":
            updates["launch_count"] = (user_resp.data[0].get("launch_count") or 0) + 1
            new_session_id = str(uuid.uuid4())
            db.table("app_sessions").insert({"session_id": new_session_id, "discord_id": discord_id, "start_time": now_str, "end_time": now_str}).execute()
            if discord_id.startswith("email-"):
                db.table("users").update(updates).eq("id", user_id).execute()
            else:
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "ok", "session_id": new_session_id})
        elif action == "ping":
            updates["total_time"] = (user_resp.data[0].get("total_time") or 0) + 1
            if session_id: db.table("app_sessions").update({"end_time": now_str}).eq("session_id", session_id).execute()
        elif action == "stop":
            updates["is_online"] = False
            updates["admin_bypass"] = False
            if session_id: db.table("app_sessions").update({"end_time": now_str}).eq("session_id", session_id).execute()
        
        if discord_id.startswith("email-"):
            db.table("users").update(updates).eq("id", user_id).execute()
        else:
            db.table("users").update(updates).eq("discord_id", discord_id).execute()
        
        return _cors_jsonify({"status": "ok", "session_id": session_id})
    except: return _cors_jsonify({"status": "error"})

@app.route('/api/get_profile_data/<discord_id>', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_get_profile_data(discord_id):
    if request.method == 'OPTIONS': return _cors_jsonify({})
    if not session.get('logged_in'): return _cors_jsonify({"error": "Unauthorized"}), 401
    if not discord_id or discord_id == 'None': return _cors_jsonify({"error": "Chybí Discord ID"})
    try:
        db = get_db()
        if not db: return _cors_jsonify({"error": "DB Error"}), 500
        u_data = db.table("users").select("*").eq("discord_id", discord_id).execute().data
        stats = ""; app_status = "<span style='color: var(--text-muted);'>Neznámý</span>"
        if u_data:
            u = u_data[0]
            try: t_time = int(u.get("total_time") or 0)
            except: t_time = 0
            try: l_count = int(u.get("launch_count") or 0)
            except: l_count = 0
            hours = t_time // 60; mins = t_time % 60
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
        return _cors_jsonify({"joined_at": joined_at, "status": "", "app_status": app_status, "stats": stats, "downloads": downloads, "sessions": sessions_data})
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
        user_roles = []; user_nick = ""
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
            if str(msg.get("is_archived")).lower() == 'true': continue
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
            if target_type == 'GLOBAL': is_target = True
            elif target_type == 'ROLE':
                target_roles = [r.strip() for r in target_data.split(',')]
                if any(tr in user_roles for tr in target_roles): is_target = True
            elif target_type == 'USERS':
                targets = [t.strip() for t in target_data.split(',')]
                if discord_id in targets or app_id in targets or user_nick in targets: is_target = True
            if is_target:
                is_repeat = str(msg.get('repeat')).lower() == 'true'
                if is_repeat or msg['message_id'] not in read_ids:
                    valid_msgs.append({"id": msg['message_id'], "title": msg['title'], "content": msg['content'], "link_url": msg.get('link_url', "")})
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
        try: db.table("read_messages").insert({"read_id": str(uuid.uuid4()), "discord_id": discord_id, "message_id": message_id}).execute()
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
                return _cors_jsonify({"status": "error", "message": "⚠️ OCHRANA: Napište prosím své číselné DISCORD ID přímo do textu žádosti!"})
            else: d_id = "Napsáno v textu"
        db.table("feedback").insert({"discord_id": d_id, "nick": nick, "type": type_str, "message": msg, "status": "pending", "sys_note": "", "fcreated_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
        if type_str == "HWID": log_title = "🚨 VYŽADUJE KONTROLU: Žádost o HWID a IP 🚨"; log_color = 0xef4444
        elif type_str == "ADMIN_BYPASS": log_title = "🔓 VYŽADUJE SCHVÁLENÍ: Admin Bypass 🔓"; log_color = 0xf59e0b
        else: log_title = "🔔 NOVÁ ZPĚTNÁ VAZBA"; log_color = 0xa855f7
        send_log(log_title, f"**Od:** {nick} (`{d_id}`)\n**Zpráva:**\n*{msg}*", log_color)
        return _cors_jsonify({"status": "success"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH / DASHBOARD ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/login_request', methods=['POST'])
def login_request():
    # Rate limit: 5 pokusů / minutu na IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not _rate_limit_check(f'dash_login:{client_ip}', 5, 60):
        flash('Příliš mnoho pokusů o přihlášení. Zkuste to za minutu.', 'error')
        return redirect(url_for('dashboard_main'))
    discord_id = request.form.get('discord_id', '').strip()
    # Validace – Discord ID musí být číselne
    if not discord_id.isdigit():
        flash('Neplatné Discord ID.', 'error')
        return redirect(url_for('dashboard_main'))
    db = get_db()
    if db and discord_id:
        try:
            user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
            if not user:
                flash('Účet s tímto Discord ID neexistuje v databázi.', 'error')
            else:
                user_data = user[0]
                if user_data.get("is_deleted"):
                    flash('Tento účet byl smazán.', 'error')
                elif user_data.get("is_banned"):
                    flash('Tento účet byl zablokován (banned).', 'error')
                else:
                    # ── Přístup POUZE dle záznamu v DB, bez Discord role check ──
                    has_access = (user_data.get("dashboard_access") == True)

                    if not has_access:
                        flash('Přístup zamítnut. Dashboard přístup musí být povolen ručně administrátorem.', 'error')
                    else:
                        import time as _t
                        token = _secrets.token_hex(32)  # Kryptograficky bezpečný token
                        token_expiry = int(_t.time()) + 600  # 10 minut expiry
                        db.table("users").update({"login_token": token, "login_token_expires_at": token_expiry}).eq("discord_id", discord_id).execute()
                        async def send():
                            try:
                                u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                                if u: await u.send(embed=discord.Embed(title="🔐 Bezpečnostní ověření", description="Byl zaznamenán pokus o přihlášení do administračního panelu.", color=0x38bdf8), view=DashboardAuthView(token, discord_id))
                            except: pass
                        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
                        return redirect(url_for('wait_auth', discord_id=discord_id))
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
    discord_id = request.args.get('discord_id', '').strip()
    if not discord_id.isdigit():
        return f"CHYBA: Neplatné Discord ID: '{discord_id}'"
        
    # Pokud prohlížeč (často na mobilech) pošle request 2x kvůli probuzení z pozadí a už má cookies
    if session.get('logged_in') and str(session.get('discord_id')) == str(discord_id):
        return redirect(url_for('dashboard_main'))

    db = get_db()
    if db and discord_id:
        import time as _t
        user = db.table("users").select("login_token, login_token_expires_at, dashboard_access").eq("discord_id", discord_id).execute().data
        if user:
            u = user[0]
            # Ověřit: token, expiry a dashboard_access
            token_exp = int(u.get('login_token_expires_at') or 0)
            token_val = u.get("login_token")
            has_acc = u.get("dashboard_access")
            
            if (token_val in ["approved", "used"]
                    and has_acc
                    and (token_exp == 0 or _t.time() <= token_exp)):
                session.permanent = True
                session['logged_in'] = True
                session['discord_id'] = discord_id
                
                if token_val == "approved":
                    db.table("users").update({"login_token": "used", "login_token_expires_at": int(_t.time()) + 10}).eq("discord_id", discord_id).execute()
                
                # Zabezpečení proti Safari/Chrome Mobile zahazování cookies při 302 redirectu
                return """
                <html>
                <head>
                    <meta http-equiv="refresh" content="0;url=/dashboard">
                    <title>Přihlašování...</title>
                </head>
                <body style="background-color: #0f172a; color: white; font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h2>✅ Úspěšně ověřeno</h2>
                    <p>Přesměrovávám do administrace...</p>
                    <script>
                        setTimeout(() => { window.location.href = '/dashboard'; }, 100);
                    </script>
                </body>
                </html>
                """
            elif token_exp > 0 and _t.time() > token_exp:
                db.table("users").update({"login_token": "", "login_token_expires_at": 0}).eq("discord_id", discord_id).execute()
                return f"CHYBA: Platnost ověření vypršela. Zkuste to znovu od začátku. (Aktuální: {_t.time()}, Expirace: {token_exp})"
            else:
                return f"CHYBA: Něco je špatně s přístupem.<br>Token_v_DB: '{token_val}' (musí být 'approved')<br>Přístup_povolen: {has_acc}<br>Expirovalo: {_t.time() > token_exp}<br>Máte ve svém mobilu zapnuté Cookies?"
        else:
            return "CHYBA: Uživatel nebyl nalezen v databázi!"
    return "CHYBA: Nelze se připojit k databázi."

class WebAuthView(discord.ui.View):
    def __init__(self, token="", discord_id=""):
        super().__init__(timeout=None)
        self.token = token
        self.discord_id = str(discord_id)

    @discord.ui.button(label="Přihlásit se na Web", style=discord.ButtonStyle.success, emoji="✅", custom_id="web_auth_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="✅ **Přihlášení na web OIS IDPK bylo úspěšné!** Můžete se vrátit do prohlížeče.", embed=None, view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="web_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
            await interaction.response.edit_message(content="❌ **Přihlášení zrušeno.**", embed=None, view=None)

# ═══════════════════════════════════════════════════════════════════════════════
# NOVÝ WEB AUTH SYSTÉM
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/register')
@app.route('/login')
def auth_pages():
    # If user is already logged in with a cookie, redirect to home
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if cookie_token and db:
        user = db.table("users").select("id").eq("web_session_token", cookie_token).execute().data
        if user:
            return redirect(url_for('home'))
    return render_public(HTML_REGISTER) # HTML_REGISTER used for both login and register since it's passwordless

@app.route('/api/auth/discord/request', methods=['POST'])
def web_auth_discord_request():
    # Rate limit: 5 pokusu / 2 minuty na IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not _rate_limit_check(f'auth_discord:{client_ip}', 5, 120):
        return jsonify({'status': 'error', 'message': 'Příliš mnoho pokusů. Zkuste to za chvíli.'}), 429
    discord_id = request.json.get('discord_id') if request.is_json else None
    db = get_db()
    if not db or not discord_id or not str(discord_id).isdigit():
        return jsonify({"status": "error", "message": "Neplatný požadavek."})
    
    try:
        user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
        if not user:
            # Auto-assign next app_id and set defaults for new web users
            try:
                highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
                new_app_id = (highest[0]["app_id"] + 1) if (highest and highest[0].get("app_id")) else 1001
            except:
                new_app_id = None
            insert_data = {"discord_id": discord_id, "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M"), "is_banned": False, "is_deleted": False, "role": "User", "login_token": ""}
            if new_app_id: insert_data["app_id"] = new_app_id
            db.table("users").insert(insert_data).execute()
        
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
        
        async def send():
            try:
                u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                if u: 
                    await u.send(embed=discord.Embed(title="🔐 Webové ověření", description="Kliknutím na tlačítko níže se přihlásíte do interaktivní mapy OIS IDPK.", color=0x38bdf8), view=WebAuthView(token, discord_id))
            except Exception as e:
                print(f"[AUTH] Nelze odeslat DM: {e}")
        
        if bot.loop and bot.loop.is_running() and bot.is_ready(): 
            asyncio.run_coroutine_threadsafe(send(), bot.loop)
            
        return jsonify({"status": "success", "discord_id": discord_id})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Došlo k chybě: {str(e)}"})

@app.route('/api/auth/email/request', methods=['POST'])
def web_auth_email_request():
    # Rate limit: 3 pokusu / 5 minut na IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not _rate_limit_check(f'auth_email:{client_ip}', 3, 300):
        return jsonify({'status': 'error', 'message': 'Příliš mnoho pokusů o zaslání e-mailu. Zkuste to za 5 minut.'}), 429
    email = request.json.get('email') if request.is_json else None
    intent = request.json.get('intent', 'login') if request.is_json else 'login'
    db = get_db()
    if not db or not email or '@' not in email:
        return jsonify({"status": "error", "message": "Neplatný e-mail."})
    
    try:
        user = db.table("users").select("*").eq("email", email).execute().data
        if not user:
            # Auto-assign next app_id and set defaults for new web users
            try:
                highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
                if highest and highest[0].get("app_id"):
                    highest_val = int(highest[0]["app_id"])
                    new_app_id = 2001 if highest_val < 2001 else highest_val + 1
                else:
                    new_app_id = 2001
            except:
                new_app_id = 2001
            insert_data = {"email": email, "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M"), "is_banned": False, "is_deleted": False, "role": "User", "login_token": "", "discord_id": "čeká na odpověd"}
            if new_app_id: insert_data["app_id"] = new_app_id
            db.table("users").insert(insert_data).execute()
        
        import time as _t
        import random
        import string
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)) # 5-místný bezpečný kód pro ruční zadání i magic link
        token_expiry = int(_t.time()) + 900  # 15 minut
        db.table("users").update({"login_token": token, "login_token_expires_at": token_expiry}).eq("email", email).execute()
        
        if send_magic_link_email(email, token, intent=intent):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "E-mail se nepodařilo odeslat. Máte nastavený SMTP?"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Došlo k chybě: {str(e)}"})

@app.route('/api/auth/status')
def web_auth_status():
    discord_id = request.args.get('discord_id')
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if db and discord_id:
        user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
        if user:
            u = user[0]
            t = u.get("login_token")
            if t == "approved": 
                if cookie_token:
                    # Link k aktualnimu uctu misto vytvoreni noveho
                    curr_user = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
                    if curr_user and curr_user[0].get('id') != u.get('id'):
                        c_u = curr_user[0]
                        
                        # Vždy zachovat starší účet (s menším app_id)
                        app_id_c = int(c_u.get('app_id') or 999999)
                        app_id_u = int(u.get('app_id') or 999999)
                        
                        if app_id_c <= app_id_u:
                            id_to_keep = c_u.get("id")
                            id_to_del = u.get("id")
                        else:
                            id_to_keep = u.get("id")
                            id_to_del = c_u.get("id")
                            
                        # Sloučit data
                        new_email = c_u.get('email') or u.get('email')
                        new_discord = c_u.get('discord_id')
                        if not new_discord or new_discord == "čeká na odpověd":
                            new_discord = u.get('discord_id')
                            if not new_discord or new_discord == "čeká na odpověd":
                                new_discord = discord_id
                                
                        # Smazat novější účet
                        db.table("users").delete().eq("id", id_to_del).execute()
                        # Sjednotit vše do staršího účtu a zajistit, že zůstaneme přihlášeni
                        db.table("users").update({
                            "discord_id": new_discord,
                            "email": new_email,
                            "web_session_token": cookie_token,
                            "login_token": ""
                        }).eq("id", id_to_keep).execute()
                        
                        return jsonify({"status": "approved", "linked": True})
                        
                # Create permanent token and update login time
                perm_token = str(uuid.uuid4())
                login_time = get_prague_time().strftime("%d.%m.%Y %H:%M")
                try:
                    db.table("users").update({"login_token": "", "web_session_token": perm_token, "web_login_at": login_time}).eq("discord_id", discord_id).execute()
                except:
                    db.table("users").update({"login_token": "", "web_session_token": perm_token}).eq("discord_id", discord_id).execute()
                return jsonify({"status": "approved", "token": perm_token})
            elif t == "rejected":
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                return jsonify({"status": "rejected"})
    return jsonify({"status": "waiting"})

@app.route('/api/auth/finalize')
def web_auth_finalize():
    token = request.args.get('token')
    auth_type = request.args.get('type')
    intent = request.args.get('intent', 'login')
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if db and token and auth_type == "email":
        import time as _t
        user = db.table("users").select("*").eq("login_token", token).execute().data
        if user:
            u = user[0]
            # Zkontrolovat expiraci tokenu (15 minut)
            token_exp = int(u.get('login_token_expires_at') or 0)
            if token_exp > 0 and _t.time() > token_exp:
                db.table("users").update({"login_token": "", "login_token_expires_at": 0}).eq("id", u.get("id")).execute()
                return "Odkaz vypršel (platnost 15 minut). Požádejte o nový odkaz.", 400
            email = u.get("email")
            if cookie_token and intent == 'link':
                curr_user = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
                if curr_user and curr_user[0].get('id') != u.get('id'):
                    db.table("users").delete().eq("id", u.get("id")).execute()
                    db.table("users").update({"email": email}).eq("web_session_token", cookie_token).execute()
                    return redirect('/ucet')
            perm_token = _secrets.token_hex(32)
            db.table("users").update({"login_token": "", "login_token_expires_at": 0, "web_session_token": perm_token}).eq("email", email).execute()
            
            status_text = "PŘIHLÁŠENO DO APLIKACE I NA WEB" if intent == 'app_login' else "PŘIHLÁŠENO NA WEB"
            
            # Nastavíme cookie přes Flask Response, ale vrátíme meta refresh stránku s animací
            from flask import make_response
            html_content = f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="4;url=/ucet">
                <title>Úspěšné přihlášení</title>
                <style>
                    .icon-line.line-long { top: 38px; right: 8px; width: 47px; transform: rotate(-45deg); animation: icon-line-long 0.75s; }
                    .icon-circle { top: -4px; left: -4px; z-index: 10; width: 80px; height: 80px; border-radius: 50%; position: absolute; box-sizing: content-box; border: 4px solid rgba(76, 175, 80, .5); }
                    .icon-fix { top: 8px; width: 5px; left: 26px; z-index: 1; height: 85px; position: absolute; transform: rotate(-45deg); background-color: #0f172a; }
                    @keyframes icon-line-tip { 0% { width: 0; left: 1px; top: 19px; } 54% { width: 0; left: 1px; top: 19px; } 70% { width: 50px; left: -8px; top: 37px; } 84% { width: 17px; left: 21px; top: 48px; } 100% { width: 25px; left: 14px; top: 46px; } }
                    @keyframes icon-line-long { 0% { width: 0; right: 46px; top: 54px; } 65% { width: 0; right: 46px; top: 54px; } 84% { width: 55px; right: 0px; top: 35px; } 100% { width: 47px; right: 8px; top: 38px; } }
                    h2 { margin-top: 20px; font-weight: normal; }
                </style>
            </head>
            <body>
                <div class="success-checkmark">
                    <div class="check-icon">
                        <span class="icon-line line-tip"></span>
                        <span class="icon-line line-long"></span>
                        <div class="icon-circle"></div>
                        <div class="icon-fix"></div>
                    </div>
                </div>
                <h2>{status_text}</h2>
                <script>
                    setTimeout(() => { window.location.href = '/ucet'; }, 4000);
                </script>
            </body>
            </html>
            """
            resp = make_response(html_content)
            resp.set_cookie('web_session_token', perm_token, max_age=60*60*24*30,
                            secure=True, httponly=True, samesite='Lax')
            return resp
    return "Neplatný nebo expirovaný odkaz.", 400

@app.route('/api/auth/logout', methods=['POST'])
def web_auth_logout():
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if cookie_token and db:
        db.table("users").update({"web_session_token": ""}).eq("web_session_token", cookie_token).execute()
    resp = jsonify({"status": "success"})
    resp.set_cookie('web_session_token', '', expires=0, secure=True, httponly=True, samesite='Strict')
    return resp

@app.route('/api/auth/me')
def web_auth_me():
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if cookie_token and db:
        user = db.table("users").select("discord_id, email, nick").eq("web_session_token", cookie_token).execute().data
        if user:
            return jsonify({"status": "success", "user": user[0]})
    return jsonify({"status": "unauthorized"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/ucet')
def stranka_ucet():
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if not cookie_token or not db:
        return redirect('/register')
    user_res = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
    if not user_res:
        resp = redirect('/register')
        resp.delete_cookie('web_session_token')
        return resp
        
    u = user_res[0]
    nick = u.get('nick') or ""
    avatar_url = u.get('avatar_url') or ""
    
    if avatar_url:
        avatar_img_html = f'<img src="{avatar_url}">'
    else:
        avatar_img_html = '<i class="fas fa-user-circle" style="color:#94a3b8;"></i>'
        
    has_discord = bool(u.get('discord_id') and u.get('discord_id') != "čeká na odpověd")
    has_email = bool(u.get('email'))
    
    discord_status = '<div class="link-status status-yes"><i class="fas fa-check-circle"></i> Připojeno</div>' if has_discord else '<div class="link-status status-no"><i class="fas fa-times-circle"></i> Nepřipojeno</div>'
    discord_btn = '' if has_discord else '<button class="btn-link btn-link-discord" onclick="reqDiscord()"><i class="fab fa-discord"></i> Propojit</button>'
    
    email_status = '<div class="link-status status-yes"><i class="fas fa-check-circle"></i> Připojeno</div>' if has_email else '<div class="link-status status-no"><i class="fas fa-times-circle"></i> Nepřipojeno</div>'
    email_btn = '' if has_email else f'<button class="btn-link btn-link-email" onclick="reqEmail()"><i class="fas fa-envelope"></i> Propojit</button>'
    
    # Hack pro pouziti stavajicich js funkci v html_templates
    link_scripts = """
    <script>
    let checkInterval = null;
    function showStatus(text, desc, isError) {
        alert(text + " - " + desc);
    }
    function startPolling(discord_id) {
        if(checkInterval) clearInterval(checkInterval);
        checkInterval = setInterval(() => {
            fetch('/api/auth/status?discord_id=' + discord_id)
            .then(r=>r.json()).then(data => {
                if(data.status === 'approved' && data.linked) {
                    clearInterval(checkInterval);
                    alert('Discord úspěšně propojen!');
                    location.reload();
                } else if(data.status === 'rejected') {
                    clearInterval(checkInterval);
                    alert('Propojení zamítnuto v Discordu.');
                }
            });
        }, 2000);
    }
    function reqDiscord() {
        const d_id = prompt('Zadejte vaše Discord ID pro propojení:');
        if(!d_id) return;
        fetch('/api/auth/discord/request', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({discord_id: d_id})
        }).then(r=>r.json()).then(data => {
            if(data.status === 'success') {
                alert('Byla vám zaslána zpráva na Discord pro potvrzení propojení. Přijměte ji a okno se automaticky obnoví.');
                startPolling(d_id);
            } else alert('Chyba: ' + data.message);
        });
    }
    function reqEmail() {
        const e = prompt('Zadejte váš E-mail pro propojení:');
        if(!e || !e.includes('@')) return;
        fetch('/api/auth/email/request', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: e, intent: 'link'})
        }).then(r=>r.json()).then(data => {
            if(data.status === 'success') {
                const code = prompt('Odeslán e-mail s odkazem k propojení. Zadejte 5místný kód z e-mailu:');
                if(code && code.trim().length === 5) {
                    window.location.href = `/api/auth/finalize?token=${code.trim()}&type=email&intent=link`;
                } else if(code) {
                    alert('Neplatný kód.');
                }
            }
            else alert('Chyba: ' + data.message);
        });
    }
    </script>
    """
    
    app_id = u.get('app_id')
    if app_id:
        app_id_badge = f'<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.4);border-radius:20px;padding:4px 12px;font-size:12px;font-weight:bold;color:#38bdf8;margin-top:5px;"><i class="fas fa-id-badge"></i> App ID #{app_id}</div>'
    else:
        app_id_badge = '<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(100,116,139,0.1);border:1px solid #334155;border-radius:20px;padding:4px 12px;font-size:12px;color:#64748b;margin-top:5px;"><i class="fas fa-clock"></i> App ID přidělováno...</div>'

    try:
        notif_res = db.table("bus_notifications").select("*").eq("user_session", str(u["id"])).execute().data or []
    except Exception:
        notif_res = []
        
    notif_html = ""
    if not notif_res:
        notif_html = '<div style="color:#64748b; font-size:14px; text-align:center; margin-top:20px;">Zatím nemáte žádná aktivní upozornění na spoje. Můžete si je nastavit přímo na mapě kliknutím na autobus.</div>'
    else:
        for r in notif_res:
            n_id = r.get("id")
            label = r.get("label") or f"Bus {r.get('identifier')}"
            typ = "Jednorázové" if r.get("is_one_time") else "Trvalé"
            cnt = r.get("fired_count") or 0
            
            triggers = r.get("triggers", {})
            t_texts = []
            if triggers.get("terminal"): t_texts.append("Konečná")
            if triggers.get("new_line"): t_texts.append("Změna linky")
            if triggers.get("depot_in"):
                dpt = triggers.get("depot_in")
                t_texts.append(f"Do vozovny ({'Všechny' if dpt=='all' else dpt})")
            if triggers.get("depot_out"): t_texts.append("Z vozovny")
            if triggers.get("trip_change"): t_texts.append("Přepnutí spoje")
            if triggers.get("started_moving"): t_texts.append("Rozjetí")
            if triggers.get("stop_near"): t_texts.append(f"Zastávka: {triggers.get('stop_near')}")
            if triggers.get("delay_threshold"): t_texts.append(f"Zpoždění přes {triggers.get('delay_threshold')} min")
            if triggers.get("delay_change"): t_texts.append("Skok zpoždění o 3+ min")
            trig_str = ", ".join(t_texts)
            
            notif_html += f"""
            <div style="background: rgba(0,0,0,0.4); border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="color:white; font-weight:bold; font-size:15px; margin-bottom:4px;">{label}</div>
                <div style="color:#94a3b8; font-size:12px; margin-bottom:4px;">Události: {trig_str}</div>
                <div style="display:flex; gap:10px; font-size:11px;">
                   <span style="color: {'#a78bfa' if not r.get('is_one_time') else '#7c3aed'}; font-weight:bold;">{typ}</span>
                   <span style="color: #64748b;">Spuštěno: {cnt}x</span>
                </div>
              </div>
              <button onclick="deleteNotificationRule('{n_id}')" style="background:transparent; border:none; color:#ef4444; font-size:18px; cursor:pointer; padding:10px;" title="Smazat upozornění"><i class="fas fa-trash"></i></button>
            </div>
            """

    html = HTML_UCET.replace('__AVATAR_IMG__', avatar_img_html)
    html = html.replace('__NICK__', nick)
    html = html.replace('__AVATAR_URL__', avatar_url)
    html = html.replace('__DISCORD_STATUS__', discord_status)
    html = html.replace('__DISCORD_BTN__', discord_btn)
    html = html.replace('__EMAIL_STATUS__', email_status)
    html = html.replace('__EMAIL_BTN__', email_btn)
    html = html.replace('__APP_ID_BADGE__', app_id_badge)
    html = html.replace('__NOTIFICATIONS__', notif_html)
    html += link_scripts
    
    return render_public(html)

@app.route('/api/ucet/update', methods=['POST'])
def api_ucet_update():
    cookie_token = request.cookies.get('web_session_token')
    db = get_db()
    if not cookie_token or not db:
        return jsonify({"status": "error", "message": "Nepřihlášen"}), 401
        
    data = request.get_json(silent=True) or {}
    nick = data.get('nick', '').strip()
    avatar_url = data.get('avatar_url', '').strip()
    
    if not nick:
        return jsonify({"status": "error", "message": "Přezdívka nesmí být prázdná"})
        
    db = get_db()
    try:
        db.table("users").update({"nick": nick, "avatar_url": avatar_url}).eq("web_session_token", cookie_token).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/dashboard/stats', methods=['GET'], strict_slashes=False)
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
                if not c_raw or any(x in c_raw.lower() for x in ['neznámá', 'unknown', 'none', 'us']): continue
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

@app.route('/dashboard', methods=['GET', 'POST'], strict_slashes=False)
def dashboard_main():
    if not session.get('logged_in'): return render_public(HTML_LOGIN)
    users_data = []
    try:
        db = get_db()
        if db:
            query = db.table("users").select("*")
            f = request.args.get('filter')
            if f == 'banned': query = query.eq("is_banned", True).neq("is_deleted", True)
            elif f == 'deleted': query = query.eq("is_deleted", True)
            elif f: query = query.ilike("role", f"%{f}%").neq("is_deleted", True)
            else: query = query.neq("is_deleted", True).order("app_id")
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

@app.route('/debug_log')
def view_debug_log():
    try:
        with open("debug_log.txt", "r") as f:
            return f"<pre>{f.read()}</pre>"
    except Exception as e:
        return str(e)

@app.route('/dashboard/edit_user', methods=['POST'])
@require_dash_level('admin')
def edit_user():
    db = get_db()
    discord_id = request.form.get("discord_id")
    app_id = request.form.get("app_id")
    action = request.form.get("action")
    nick = request.form.get("nick")
    email = request.form.get("email")

    if email: email = email.strip()
    if not email: email = None  # Prevents unique constraint violation for empty strings

    if discord_id: discord_id = discord_id.strip()
    
    if (not discord_id or discord_id == "None") and not app_id:
        flash(f"Chyba: Nebylo předáno discord_id ani app_id! (Akce: {action})", "error")
        return redirect(url_for('dashboard_main'))
    if not action:
        flash("Chyba: Nebyla předána žádná akce z tlačítka!", "error")
        return redirect(url_for('dashboard_main'))
        
    try:
        with open("debug_log.txt", "a") as f: f.write(f"edit_user called: discord_id={discord_id}, app_id={app_id}, action={action}\n")
    except: pass

    if db:
        # Helper pro stavbu query
        def build_query(updates):
            if discord_id and discord_id != "None": return db.table("users").update(updates).eq("discord_id", discord_id)
            else: return db.table("users").update(updates).eq("app_id", app_id)

        def build_delete_query(table):
            if discord_id and discord_id != "None": return db.table(table).delete().eq("discord_id", discord_id)
            else: return db.table(table).delete().eq("app_id", app_id)

        target_identifier = f"discord_id '{discord_id}'" if (discord_id and discord_id != "None") else f"app_id #{app_id}"
        valid_discord_id = discord_id if (discord_id and discord_id != "None") else None

        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                new_hwid = request.form.get("hwid", "").strip()
                new_ip = request.form.get("ip_address", "").strip()
                updates = {"nick": nick, "email": email, "role": r_str, "hwid": new_hwid, "ip_address": new_ip, "dashboard_access": True if request.form.get("dashboard_access") else False}
                res = build_query(updates).execute()
                try:
                    with open("debug_log.txt", "a") as f: f.write(f"save result: {res.data}\n")
                except: pass
                if valid_discord_id: sync_roles_from_flask(valid_discord_id, r_str)
                flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                try:
                    with open("debug_log.txt", "a") as f: f.write("executing ban query...\n")
                except: pass
                res = build_query({"is_banned": True, "dashboard_access": False}).execute()
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl v databázi nalezen.", "error")
                else: flash('BAN udělen.', 'warning')
                if bot.loop and bot.loop.is_running() and bot.is_ready() and valid_discord_id:
                    try: asyncio.run_coroutine_threadsafe(send_user_dm(valid_discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace byl zablokován.", 0xef4444), bot.loop)
                    except: pass
                if valid_discord_id and str(session.get('discord_id')) == str(valid_discord_id): session.clear()
            elif action == 'unban':
                res = build_query({"is_banned": False, "dashboard_access": True}).execute()
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl v databázi nalezen.", "error")
                else: flash('BAN zrušen.', 'success')
                if bot.loop and bot.loop.is_running() and bot.is_ready() and valid_discord_id:
                    try: asyncio.run_coroutine_threadsafe(send_user_dm(valid_discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace byl obnoven.", 0x10b981), bot.loop)
                    except: pass
            elif action == 'delete':
                try:
                    with open("debug_log.txt", "a") as f: f.write("executing delete query...\n")
                except: pass
                now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
                res = build_query({"is_deleted": True, "deleted_at": now_str, "dashboard_access": False}).execute()
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl v databázi nalezen pro smazání.", "error")
                else: flash('Účet smazán (Soft Delete).', 'danger')
                if valid_discord_id and str(session.get('discord_id')) == str(valid_discord_id): session.clear()
            elif action == 'restore':
                res = build_query({"is_deleted": False, "deleted_at": "", "dashboard_access": True}).execute()
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl v databázi nalezen.", "error")
                else: flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                for t in ["user_stats_lines", "user_stats_stops", "app_sessions", "download_logs", "feedback", "read_messages"]:
                    try: build_delete_query(t).execute()
                    except: pass
                res = build_delete_query("users").execute()
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl nalezen pro permanentní smazání.", "error")
                else: flash('Účet a všechna jeho data byla trvale smazána.', 'dark')
                if valid_discord_id and str(session.get('discord_id')) == str(valid_discord_id): session.clear()
        except Exception as e:
            flash(f"Chyba při úpravě uživatele (akce {action}): {e}", "error")
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/app_management', methods=['GET'], strict_slashes=False)
def dashboard_app_management():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); soft_enabled = True; dl_enabled = True; web_login_enabled = True; map_enabled = True; web_maintenance = False
    try:
        if db:
            s_resp = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled", "web_login_enabled", "map_enabled", "web_maintenance"]).execute().data or []
            for s in s_resp:
                k = s['setting_key']; v = str(s['setting_value']).lower()
                if k == 'software_enabled': soft_enabled = v != 'false'
                elif k == 'downloads_enabled': dl_enabled = v != 'false'
                elif k == 'web_login_enabled': web_login_enabled = v != 'false'
                elif k == 'map_enabled': map_enabled = v != 'false'
                elif k == 'web_maintenance': web_maintenance = v == 'true'
    except: pass
    return render_dashboard(HTML_APP_MANAGEMENT, soft_enabled=soft_enabled, dl_enabled=dl_enabled, web_login_enabled=web_login_enabled, map_enabled=map_enabled, web_maintenance=web_maintenance, deploy_time=DEPLOY_TIME)

async def _trigger_status_update():
    try:
        db = get_db()
        if not db: return
        s_resp = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled", "web_login_enabled", "map_enabled", "web_maintenance"]).execute().data or []
        settings = {}
        for s in s_resp:
            settings[s['setting_key']] = str(s['setting_value']).lower()
            
        soft_enabled = settings.get('software_enabled', 'true') != 'false'
        dl_enabled = settings.get('downloads_enabled', 'true') != 'false'
        web_login_enabled = settings.get('web_login_enabled', 'true') != 'false'
        map_enabled = settings.get('map_enabled', 'true') != 'false'
        web_maintenance = settings.get('web_maintenance', 'false') == 'true'

        embed = discord.Embed(title="📡 Stav systémů OIS IDPK", description="Zde naleznete aktuální globální stavy všech služeb.\nTento panel se automaticky aktualizuje.", color=0x38bdf8, timestamp=get_prague_time())
        
        embed.add_field(name="🌍 Web (Údržba)", value="🔴 OFFLINE (Údržba)" if web_maintenance else "🟢 ONLINE", inline=False)
        embed.add_field(name="💻 Herní Software", value="🟢 ONLINE" if soft_enabled else "🔴 OFFLINE", inline=False)
        embed.add_field(name="📥 Stahování softwaru", value="🟢 POVOLENO" if dl_enabled else "🔴 ZAKÁZÁNO", inline=False)
        embed.add_field(name="🔐 Přihlašování na web", value="🟢 POVOLENO" if web_login_enabled else "🔴 ZAKÁZÁNO", inline=False)
        embed.add_field(name="🗺️ Interaktivní Mapa", value="🟢 ONLINE" if map_enabled else "🔴 OFFLINE", inline=False)
        
        embed.set_footer(text="Systémový Status")

        status_channel = discord.utils.get(bot.get_all_channels(), name="🛜・status")
        if not status_channel:
            status_channel = discord.utils.get(bot.get_all_channels(), name="status")
        
        if status_channel:
            bot_msg = None
            async for msg in status_channel.history(limit=20):
                if msg.author == bot.user and msg.embeds and "Stav systémů" in msg.embeds[0].title:
                    bot_msg = msg
                    break
            
            if bot_msg:
                await bot_msg.edit(embed=embed)
            else:
                await status_channel.send(embed=embed)
    except Exception as e:
        print(f"Error updating status channel: {e}")

def trigger_status_channel_update():
    if bot.loop and bot.loop.is_running() and bot.is_ready():
        asyncio.run_coroutine_threadsafe(_trigger_status_update(), bot.loop)

@app.route('/dashboard/toggle_software', methods=['POST'])
@require_dash_level('superadmin')
def toggle_software():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "software_enabled").execute()
        flash(f'Stav softwaru: {"ZAPNUT" if new_status.lower() == "true" else "VYPNUT"}', 'success')
        send_log("💻 Software / Spouštění hry", f"**Uživatel:** {session.get('discord_nick')}\n**Nový stav:** {'ZAPNUTO' if new_status.lower() == 'true' else 'VYPNUTO'}", 0xf59e0b)
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_downloads', methods=['POST'])
@require_dash_level('superadmin')
def toggle_downloads():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute()
        flash(f'Stahování: {"POVOLENO" if new_status.lower() == "true" else "ZAKÁZÁNO"}', 'success')
        send_log("⬇️ Stahování hry v Launcheru", f"**Uživatel:** {session.get('discord_nick')}\n**Nový stav:** {'POVOLENO' if new_status.lower() == 'true' else 'ZAKÁZÁNO'}", 0x3b82f6)
        trigger_setup_messages_update()
        trigger_status_channel_update()
    ret = request.form.get('return_to', 'app_management')
    return redirect(url_for('dashboard_downloads' if ret == 'downloads' else 'dashboard_app_management'))

@app.route('/dashboard/toggle_web_login', methods=['POST'])
@require_dash_level('superadmin')
def toggle_web_login():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "web_login_enabled").execute()
        send_log("🔐 Přihlašování na Web", f"Přihlašování na web bylo **{'POVOLENO' if new_status.lower() == 'true' else 'ZABLOKOVANÉ'}** přes dashboard.", 0xf59e0b)
        flash(f'Přihlašování na web: {"POVOLENO" if new_status.lower() == "true" else "ZABLOKOVANÉ"}', 'success')
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_map', methods=['POST'])
@require_dash_level('superadmin')
def toggle_map():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "map_enabled").execute()
        send_log("🗺️ Interaktivní Mapa", f"Mapa byla **{'ZAPNUTA' if new_status.lower() == 'true' else 'VYPNUTA'}** přes dashboard.", 0x38bdf8)
        flash(f'Mapa: {"ZAPNUTA" if new_status.lower() == "true" else "VYPNUTA"}', 'success')
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_maintenance', methods=['POST'])
@require_dash_level('superadmin')
def toggle_maintenance():
    new_status = request.form.get('new_status', 'False')
    db = get_db()
    if db:
        db.table("settings").update({"setting_value": new_status}).eq("setting_key", "web_maintenance").execute()
        if new_status.lower() == 'true':
            send_log("🚧 Maintenance Mode ZAPNUT", "Web byl přepnut do maintenance módu. Probíhá přesměrování všech návštěvníků na /blocked.", 0xef4444)
        else:
            send_log("✅ Maintenance Mode VYPNUT", "Web byl obnoven z maintenance módu.", 0x10b981)
        flash(f'Maintenance: {"ZAPNUT - WEB JE OFFLINE" if new_status.lower() == "true" else "VYPNUT - WEB JE ONLINE"}', 'success' if new_status.lower() == 'false' else 'warning')
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/login_blocked')
def login_blocked_page():
    try:
        from html_templates import HTML_LOGIN_BLOCKED
        return render_template_string(HTML_LOGIN_BLOCKED)
    except:
        return "Přihlašování je momentálně vypnuté."

@app.route('/blocked')
def blocked_page():
    from html_templates import HTML_BLOCKED
    return HTML_BLOCKED, 200

@app.route('/api/admin/check')
def api_admin_check():
    """Quick endpoint for frontend to check if admin dashboard session is active."""
    return jsonify({"logged_in": bool(session.get('logged_in'))})

@app.route('/mapa_admin')
def mapa_admin_redirect():
    """Admin map access — always available for logged-in dashboard users."""
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    return redirect('/mapa')


@app.route('/dashboard/notifications', methods=['GET'], strict_slashes=False)
def dashboard_notifications():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    messages = []
    try:
        db = get_db()
        if db:
            msgs = db.table("app_messages").select("*").order("created_at", desc=True).execute().data or []
            now = get_prague_time().replace(tzinfo=None)
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
            db.table("app_messages").insert({"message_id": str(uuid.uuid4()), "target_type": request.form.get("target_type", "GLOBAL"), "target_data": request.form.get("target_data", "").strip(), "title": request.form.get("title", "Zpráva od vývojáře"), "content": request.form.get("content", ""), "repeat": True if request.form.get("repeat") else False, "link_url": request.form.get("link_url", "") if request.form.get("has_link") else "", "expires_at": request.form.get("expires_at", ""), "is_archived": False, "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            flash('Oznámení odesláno!', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/archive_app_message', methods=['POST'])
def archive_app_message():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); msg_id = request.form.get("message_id")
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

@app.route('/dashboard/downloads', methods=['GET'], strict_slashes=False)
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
@require_dash_level('superadmin')
def add_version():
    try:
        db = get_db()
        row = {
            "version_name": request.form.get("version_name"),
            "db_version": request.form.get("db_version"),
            "file_url": request.form.get("file_url"),
            "target_role": request.form.get("target_role"),
            "is_active": True,
            "eol_date": "",
            "show_in_launcher": True if request.form.get("show_in_launcher") else False
        }
        try:
            db.table("software_versions").insert(row).execute()
        except Exception as e:
            if "show_in_launcher" in str(e) or "PGRST204" in str(e):
                row.pop("show_in_launcher", None)
                db.table("software_versions").insert(row).execute()
            else:
                raise e
        flash('Nová verze vydána!', 'success')
        send_log("🚀 Vydána nová verze aplikce", f"**Uživatel:** {session.get('discord_nick')}\n**Název:** {row['version_name']}\n**Cílová role:** {row['target_role']}", 0x10b981)
        trigger_setup_messages_update()
    except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/edit_version', methods=['POST'])
@require_dash_level('superadmin')
def edit_version():
    try:
        db = get_db()
        row = {
            "version_name": request.form.get("version_name"),
            "db_version": request.form.get("db_version"),
            "file_url": request.form.get("file_url"),
            "target_role": request.form.get("target_role"),
            "is_active": True if request.form.get("is_active") else False,
            "eol_date": request.form.get("eol_date", ""),
            "show_in_launcher": True if request.form.get("show_in_launcher") else False
        }
        try:
            db.table("software_versions").update(row).eq("id", request.form.get("version_id")).execute()
        except Exception as e:
            if "show_in_launcher" in str(e) or "PGRST204" in str(e):
                row.pop("show_in_launcher", None)
                db.table("software_versions").update(row).eq("id", request.form.get("version_id")).execute()
            else:
                raise e
        flash('Verze upravena.', 'success')
        send_log("✏️ Úprava verze aplikace", f"**Uživatel:** {session.get('discord_nick')}\n**Název:** {row['version_name']}\n**Aktivní:** {'Ano' if row['is_active'] else 'Ne'}", 0xf59e0b)
        trigger_setup_messages_update()
    except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
@require_dash_level('superadmin')
def delete_version():
    try:
        vid = request.form.get("version_id")
        get_db().table("software_versions").delete().eq("id", vid).execute()
        flash('Verze smazána.', 'success')
        send_log("🗑️ Smazána verze aplikace", f"**Uživatel:** {session.get('discord_nick')}\n**ID verze:** {vid}", 0xef4444)
        trigger_setup_messages_update()
    except: pass
    return redirect(url_for('dashboard_downloads'))


@app.route('/dashboard/pending_roles', methods=['GET'], strict_slashes=False)
def pending_roles():
    try: data = get_db().table("pending_roles").select("*").order("id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_PENDING_ROLES, pending=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/ids', methods=['GET'], strict_slashes=False)
def dashboard_ids():
    try: data = get_db().table("users").select("*").order("app_id").execute().data or [] if get_db() else []
    except: data = []
    return render_dashboard(HTML_IDS, users=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/team', methods=['GET'], strict_slashes=False)
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
            db.table("pending_roles").insert({"discord_identifier": request.form.get("discord_identifier"), "roles": roles_str}).execute()
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
            db.table("users").update({"app_id": new_app_id}).eq("discord_id", discord_id).execute()
        except: pass
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            combined_roles = [f"{n.strip()}|{c.strip()}" for n, c in zip(request.form.getlist("role_name[]"), request.form.getlist("role_color[]")) if n.strip()]
            db.table("team").insert({"name": request.form.get("name"), "discord_nick": request.form.get("discord_nick"), "image_url": request.form.get("image_url"), "description": request.form.get("description"), "role_name": ",".join(combined_roles)}).execute()
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try: db.table("team").delete().eq("discord_nick", request.form.get("discord_nick")).execute()
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/supporters', methods=['GET'], strict_slashes=False)
def dashboard_supporters():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    pending_claims = []; supporters_history = []
    try:
        db = get_db()
        if db:
            pending_claims = db.table("supporters").select("*").eq("status", "manual_review").execute().data or []
            supporters_history = process_supporters(db.table("supporters").select("*").in_("status", ["completed", "rejected"]).execute().data or [])
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_SUPPORTERS_MGMT, pending_claims=pending_claims, supporters_history=supporters_history, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_supporter', methods=['POST'])
@require_dash_level('admin')
def add_supporter():
    db = get_db()
    if db:
        try:
            db.table("supporters").insert({"name": request.form.get("name"), "discord_nick": request.form.get("discord_nick", ""), "amount": request.form.get("amount"), "message": request.form.get("message", ""), "status": "completed", "sys_note": "Přidáno ručně", "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            flash('Podporovatel přidán.', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/approve_claim', methods=['POST'])
@require_dash_level('admin')
def approve_claim():
    db = get_db(); claim_id = request.form.get("claim_id"); discord_nick = request.form.get("discord_nick", ""); amount = request.form.get("amount", "0")
    if db and claim_id:
        try:
            discord_roles, db_role_string = calculate_roles_for_supporter(amount)
            db.table("supporters").update({"status": "completed", "sys_note": "Ručně schváleno"}).eq("id", claim_id).execute()
            if bot.loop and bot.loop.is_running() and bot.is_ready():
                asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
            flash('Schváleno a role přidělena.', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/reject_claim', methods=['POST'])
@require_dash_level('admin')
def reject_claim():
    db = get_db(); claim_id = request.form.get("claim_id")
    if db and claim_id:
        try:
            db.table("supporters").update({"status": "rejected", "sys_note": request.form.get("sys_note", "Zamítnuto")}).eq("id", claim_id).execute()
            flash('Zamítnuto.', 'success')
        except: pass
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/delete_supporter', methods=['POST'])
def delete_supporter():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); s_id = request.form.get("supporter_id")
    if db and s_id:
        try: db.table("supporters").delete().eq("id", s_id).execute()
        except: pass
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/feedback', methods=['GET'], strict_slashes=False)
def dashboard_feedback():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    hwid_p = []; bypass_p = []; gen_p = []; res_all = []
    try:
        db = get_db()
        if db:
            data = db.table("feedback").select("*").order("id", desc=True).execute().data or []
            for item in data:
                if item.get('status') == 'pending':
                    if item.get('type') in ('HWID', 'HWID_IP'): hwid_p.append(item)
                    elif item.get('type') == 'ADMIN_BYPASS': bypass_p.append(item)
                    else: gen_p.append(item)
                else: res_all.append(item)
    except: pass
    return render_dashboard(HTML_FEEDBACK, hwid_pending=hwid_p, bypass_pending=bypass_p, general_pending=gen_p, resolved_all=res_all, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/feedback_reset_hwid', methods=['POST'])
@require_dash_level('admin')
def feedback_reset_hwid():
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id")
    db = get_db()
    if db and fb_id and d_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("users").update({"hwid": "", "ip_address": ""}).eq("discord_id", d_id).execute()
        db.table("feedback").update({"status": "resolved", "sys_note": f"HWID a IP resetovány [{now_str}]"}).eq("id", fb_id).execute()
        if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔄 Zámek PC Resetován", "Vaše žádost byla schválena. HWID a IP adresa byly resetovány.", 0x10b981), bot.loop)
        flash('HWID a IP resetováno.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_reject', methods=['POST'])
def feedback_reject():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); reason = request.form.get("reason", "Zamítnuto.")
    db = get_db()
    if db and fb_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Zamítnuto: {reason} [{now_str}]"}).eq("id", fb_id).execute()
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "❌ Žádost zamítnuta", f"**Důvod:** {reason}", 0xef4444), bot.loop)
        flash('Žádost zamítnuta.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/feedback_resolve', methods=['POST'])
def feedback_resolve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    reply_text = request.form.get("reply_text")
    db = get_db()
    if db and fb_id:
        fb_data = db.table("feedback").select("*").eq("id", fb_id).execute()
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        
        sys_note_msg = f"Vyřešeno [{now_str}]"
        
        if fb_data.data and reply_text and reply_text.strip():
            f_row = fb_data.data[0]
            discord_id = f_row.get("discord_id", "")
            
            sys_note_msg = f"Odpověď: {reply_text.strip()} [{now_str}]"
            
            if discord_id.startswith("email-"):
                user_id = discord_id.split("-")[1]
                u_resp = db.table("users").select("email").eq("id", user_id).execute()
                if u_resp.data and u_resp.data[0].get("email"):
                    email = u_resp.data[0].get("email")
                    try:
                        import asyncio
                        embed_data = {
                            "title": "Odpověď na vaši zpětnou vazbu",
                            "description": reply_text.strip(),
                            "fields": [{"name": "Vaše původní zpráva", "value": f_row.get("message", "")}]
                        }
                        if bot.loop and bot.loop.is_running() and bot.is_ready():
                            asyncio.run_coroutine_threadsafe(asyncio.to_thread(send_notification_email_sync, email, embed_data, ""), bot.loop)
                    except: pass
            elif discord_id.isdigit():
                try:
                    import asyncio
                    if bot.loop and bot.loop.is_running() and bot.is_ready():
                        asyncio.run_coroutine_threadsafe(send_user_dm(discord_id, "Odpověď na vaši zpětnou vazbu", reply_text.strip(), 0x10b981), bot.loop)
                except: pass
                
        db.table("feedback").update({"status": "resolved", "sys_note": sys_note_msg}).eq("id", fb_id).execute()
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

@app.route('/dashboard/feedback_reply', methods=['POST'])
def feedback_reply():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id"); msg = request.form.get("message")
    db = get_db()
    if db and fb_id and msg:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("feedback").update({"status": "resolved", "sys_note": f"Odpověď: {msg} [{now_str}]"}).eq("id", fb_id).execute()
        if d_id and bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "📩 Zpráva od administrace", msg, 0x38bdf8), bot.loop)
        flash('Odpověď odeslána.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/bypass_approve', methods=['POST'])
@require_dash_level('admin')
def bypass_approve():
    fb_id = request.form.get("feedback_id")
    db = get_db()
    if db and fb_id:
        fb = db.table("feedback").select("*").eq("id", fb_id).execute().data
        if fb:
            d_id = fb[0]['discord_id']
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            db.table("users").update({"admin_bypass": True}).eq("discord_id", d_id).execute()
            db.table("feedback").update({"status": "resolved", "sys_note": f"Bypass schválen [{now_str}]"}).eq("id", fb_id).execute()
            if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔓 Přístup povolen", "Tvá žádost o jednorázový vstup do staré verze byla schválena.", 0x10b981), bot.loop)
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
            if bot.loop and bot.loop.is_running() and bot.is_ready(): asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "❌ Přístup zamítnut", "Tvá žádost o jednorázový vstup do staré verze byla administrátorem zamítnuta.", 0xef4444), bot.loop)
        flash('Bypass zamítnut.', 'success')
    return redirect(url_for('dashboard_feedback'))

@app.route('/dashboard/update_statuses', methods=['POST'])
@require_dash_level('superadmin')
def update_statuses():
    db = get_db()
    if db:
        try:
            statuses = {}
            for key, value in request.form.items():
                if key.startswith('status_'): statuses[key.replace('status_', '')] = value
            check = db.table("settings").select("*").eq("setting_key", "system_statuses").execute().data
            if check: db.table("settings").update({"setting_value": json.dumps(statuses)}).eq("setting_key", "system_statuses").execute()
            else: db.table("settings").insert({"setting_key": "system_statuses", "setting_value": json.dumps(statuses)}).execute()
            flash('Statusy uloženy!', 'success')
        except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_app_management'))


# ─── Správa dashboard adminů ─────────────────────────────────────────────────

@app.route('/dashboard/admins', methods=['GET'], strict_slashes=False)
@require_dash_level('superadmin')
def dashboard_admins():
    admins = []
    try:
        db = get_db()
        if db:
            admins = db.table('users').select('discord_id, nick, dashboard_access, dashboard_level, role').eq('dashboard_access', True).order('nick').execute().data or []
    except Exception as e:
        flash(f'Chyba DB: {e}', 'error')
    return render_dashboard(_DASH_ADMINS_HTML, admins=admins, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/admins/grant', methods=['POST'])
@require_dash_level('superadmin')
def dashboard_admins_grant():
    discord_id = request.form.get('discord_id', '').strip()
    level = request.form.get('level', 'viewer').strip().lower()
    if level not in ('viewer', 'admin', 'superadmin'):
        level = 'viewer'
    db = get_db()
    if not db or not discord_id:
        flash('Chybí Discord ID.', 'error')
        return redirect(url_for('dashboard_admins'))
    user = db.table('users').select('discord_id, nick').eq('discord_id', discord_id).execute().data
    if not user:
        flash(f'Uživatel s Discord ID {discord_id} nenalezen v databázi.', 'error')
        return redirect(url_for('dashboard_admins'))
    db.table('users').update({'dashboard_access': True, 'dashboard_level': level}).eq('discord_id', discord_id).execute()
    send_log('🔑 Dashboard přístup udělen', f'Uživateli **{user[0].get("nick", discord_id)}** (`{discord_id}`) byl udělen přístup do dashboardu se úrovní **{level}**.', 0x38bdf8)
    flash(f'Přístup udělen: {user[0].get("nick", discord_id)} → {level}', 'success')
    return redirect(url_for('dashboard_admins'))

@app.route('/dashboard/admins/revoke', methods=['POST'])
@require_dash_level('superadmin')
def dashboard_admins_revoke():
    discord_id = request.form.get('discord_id', '').strip()
    # Superadmin nemůže odebrat sám sobě přístup
    if str(discord_id) == str(session.get('discord_id')):
        flash('Nemůžeš odebrat přístup sám sobě!', 'error')
        return redirect(url_for('dashboard_admins'))
    db = get_db()
    if not db or not discord_id:
        flash('Chybí Discord ID.', 'error')
        return redirect(url_for('dashboard_admins'))
    user = db.table('users').select('discord_id, nick').eq('discord_id', discord_id).execute().data
    db.table('users').update({'dashboard_access': False, 'dashboard_level': ''}).eq('discord_id', discord_id).execute()
    nick = user[0].get('nick', discord_id) if user else discord_id
    send_log('🔒 Dashboard přístup odebrán', f'Uživateli **{nick}** (`{discord_id}`) byl odebrán dashboard přístup.', 0xef4444)
    flash(f'Přístup odebrán: {nick}', 'success')
    return redirect(url_for('dashboard_admins'))

@app.route('/dashboard/admins/change_level', methods=['POST'])
@require_dash_level('superadmin')
def dashboard_admins_change_level():
    discord_id = request.form.get('discord_id', '').strip()
    level = request.form.get('level', 'viewer').strip().lower()
    if level not in ('viewer', 'admin', 'superadmin'):
        level = 'viewer'
    if str(discord_id) == str(session.get('discord_id')):
        flash('Nemůžeš měnit vlastní úroveň!', 'error')
        return redirect(url_for('dashboard_admins'))
    db = get_db()
    if db and discord_id:
        db.table('users').update({'dashboard_level': level}).eq('discord_id', discord_id).execute()
        flash(f'Úroveň změněna na {level}.', 'success')
    return redirect(url_for('dashboard_admins'))

_DASH_ADMINS_HTML = '''
<div style="max-width:900px;margin:0 auto;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
    <h2 style="margin:0;color:#38bdf8;"><i class="fas fa-shield-alt"></i> Správa dashboard adminů</h2>
  </div>
  <div style="background:#1e293b;border:1px solid #f59e0b;border-radius:10px;padding:16px;margin-bottom:24px;">
    <div style="color:#f59e0b;font-weight:bold;margin-bottom:10px;"><i class="fas fa-exclamation-triangle"></i> Přidat nového admina</div>
    <form method="POST" action="/dashboard/admins/grant" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
      <div><label style="font-size:12px;color:#94a3b8;">Discord ID uživatele</label><br>
        <input name="discord_id" type="text" placeholder="Např. 123456789012345678" style="background:#0f172a;color:#fff;border:1px solid #334155;border-radius:6px;padding:8px 12px;font-size:13px;width:230px;margin-top:4px;">
      </div>
      <div><label style="font-size:12px;color:#94a3b8;">Úroveň přístupu</label><br>
        <select name="level" style="background:#0f172a;color:#fff;border:1px solid #334155;border-radius:6px;padding:8px 12px;font-size:13px;margin-top:4px;">
          <option value="viewer">👁️ Viewer – pouze čtení</option>
          <option value="admin">🛡️ Admin – správa uživatelů</option>
          <option value="superadmin">⭐ Superadmin – vše</option>
        </select>
      </div>
      <button type="submit" style="background:#10b981;color:#fff;border:none;border-radius:6px;padding:9px 18px;font-weight:bold;cursor:pointer;"><i class="fas fa-plus"></i> Udělit přístup</button>
    </form>
  </div>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;overflow:hidden;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="background:#0f172a;">
        <th style="padding:10px 14px;text-align:left;color:#94a3b8;">Uživatel</th>
        <th style="padding:10px 14px;text-align:left;color:#94a3b8;">Discord ID</th>
        <th style="padding:10px 14px;text-align:left;color:#94a3b8;">Úroveň</th>
        <th style="padding:10px 14px;text-align:center;color:#94a3b8;">Akce</th>
      </tr></thead>
      <tbody>
      {% for a in admins %}
      <tr style="border-top:1px solid #334155;">
        <td style="padding:10px 14px;color:#fff;font-weight:bold;">{{ a.nick or "–" }}</td>
        <td style="padding:10px 14px;color:#94a3b8;font-family:monospace;">{{ a.discord_id }}</td>
        <td style="padding:10px 14px;">
          {% set lv = (a.dashboard_level or "admin").lower() %}
          {% if lv == "superadmin" %}<span style="background:rgba(245,158,11,.2);color:#f59e0b;border:1px solid #f59e0b;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:bold;">⭐ Superadmin</span>
          {% elif lv == "admin" %}<span style="background:rgba(56,189,248,.15);color:#38bdf8;border:1px solid #38bdf8;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:bold;">🛡️ Admin</span>
          {% else %}<span style="background:rgba(148,163,184,.1);color:#94a3b8;border:1px solid #334155;border-radius:20px;padding:2px 10px;font-size:11px;">👁️ Viewer</span>{% endif %}
        </td>
        <td style="padding:10px 14px;text-align:center;">
          {% if a.discord_id|string != session.get("discord_id")|string %}
          <form method="POST" action="/dashboard/admins/change_level" style="display:inline;">
            <input type="hidden" name="discord_id" value="{{ a.discord_id }}">
            <select name="level" onchange="this.form.submit()" style="background:#0f172a;color:#fff;border:1px solid #334155;border-radius:4px;padding:3px 6px;font-size:11px;">
              <option value="viewer" {% if (a.dashboard_level or "admin")=="viewer" %}selected{% endif %}>Viewer</option>
              <option value="admin" {% if (a.dashboard_level or "admin")=="admin" %}selected{% endif %}>Admin</option>
              <option value="superadmin" {% if (a.dashboard_level or "admin")=="superadmin" %}selected{% endif %}>Superadmin</option>
            </select>
          </form>
          <form method="POST" action="/dashboard/admins/revoke" style="display:inline;margin-left:6px;" onsubmit="return confirm('Odebrat přístup?');">
            <input type="hidden" name="discord_id" value="{{ a.discord_id }}">
            <button type="submit" style="background:rgba(239,68,68,.2);color:#ef4444;border:1px solid #ef4444;border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer;"><i class="fas fa-times"></i></button>
          </form>
          {% else %}
          <span style="color:#64748b;font-size:11px;">to jsi ty</span>
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr><td colspan="4" style="padding:20px;text-align:center;color:#64748b;">Žádní admini. Udělte přístup výše.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  <div style="margin-top:16px;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;font-size:12px;color:#94a3b8;line-height:1.7;">
    <b style="color:#38bdf8;">Vysvětlení úrovní:</b><br>
    👁️ <b>Viewer</b> – Pouze čte data (dashboard, statistiky, feedback seznam). Nemůže nic měnit.<br>
    🛡️ <b>Admin</b> – Může spravovat uživatele (ban, unban, edit, HWID reset), schvalovat role a feedback.<br>
    ⭐ <b>Superadmin</b> – Plný přístup včetně zapínání/vypínání systémů, verzí softwaru a správy dalších adminů.<br>
    <br><b style="color:#f59e0b;">⚠️ Tip:</b> Přístup udělíš také bot příkazem <code>!dashadd [discord_id] [viewer|admin|superadmin]</code>
  </div>
</div>
'''
# ─────────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# DISCORD BOT
# ═══════════════════════════════════════════════════════════════════════════════

def check_web_sa():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="web-sa") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění.", delete_after=10)
        return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění.", delete_after=10)
        return False
    return commands.check(predicate)

@tasks.loop(seconds=5)
async def check_depot_queue():
    try:
        updated = False
        while not DEPOT_DISCORD_QUEUE.empty():
            msg = DEPOT_DISCORD_QUEUE.get_nowait()
            if msg.get("type") == "update_all":
                updated = True
        if updated:
            await update_depot_discord_messages()
    except Exception as e:
        print(f"[DEPOT DISCORD] Chyba: {e}", flush=True)

@tasks.loop(seconds=5)
async def check_notification_queue():
    """Zpracuje frontu notifikací a pošle DM přes Discord bota."""
    try:
        from interaktivnimapa import NOTIFICATION_DM_QUEUE
        while not NOTIFICATION_DM_QUEUE.empty():
            item = NOTIFICATION_DM_QUEUE.get_nowait()
            discord_id = item.get("discord_id")
            dm_text = item.get("dm_text", "")
            embed_data = item.get("embed")

            # Pošli Discord DM
            if discord_id:
                try:
                    user = await bot.fetch_user(int(discord_id))
                    if embed_data:
                        em = discord.Embed(
                            title=embed_data.get("title", "🔔 Upozornění"),
                            description=embed_data.get("description", ""),
                            color=embed_data.get("color", 0x38bdf8)
                        )
                        for field in embed_data.get("fields", []):
                            em.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))
                        em.set_footer(text=embed_data.get("footer", {}).get("text", "OIS IDPK"))
                        await user.send(embed=em)
                    else:
                        await user.send(dm_text)
                    print(f"[NOTIF DM] Odesláno DM uživateli {discord_id}", flush=True)
                except Exception as e:
                    print(f"[NOTIF DM] Chyba při odesílání DM {discord_id}: {e}", flush=True)
            
            # Pošli Email
            email = item.get("email")
            if email:
                try:
                    await asyncio.to_thread(send_notification_email_sync, email, embed_data, dm_text)
                    print(f"[NOTIF EMAIL] Odeslán e-mail uživateli {email}", flush=True)
                except Exception as e:
                    print(f"[NOTIF EMAIL] Chyba při odesílání emailu {email}: {e}", flush=True)
    except Exception as e:
        print(f"[NOTIF DM] Chyba fronty: {e}", flush=True)

def send_notification_email_sync(to_email, embed_data, dm_text):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import smtplib
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = embed_data.get("title", "🔔 Upozornění na autobus") if embed_data else "🔔 Upozornění na autobus"
        msg["From"] = f"DataCore Bot <{SMTP_EMAIL}>"
        msg["To"] = to_email

        # Sestavení HTML
        if embed_data:
            import re
            fields_html = ""
            for f in embed_data.get("fields", []):
                val = str(f.get("value", ""))
                val = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #38bdf8; text-decoration: none;">\1</a>', val)
                fields_html += f"<li><strong>{f.get('name', '')}:</strong> {val}</li>"
                
            html = f"""
            <html>
              <body style="background-color: #ffffff; color: #000000; font-family: sans-serif; padding: 20px;">
                <h2 style="color: #38bdf8;">{embed_data.get("title", "Upozornění")}</h2>
                <p><strong>{embed_data.get("description", "")}</strong></p>
                <ul>
                  {fields_html}
                </ul>
                <p>Hezký den přeje<br>Tým Projekt OIS IDPK</p>
              </body>
            </html>
            """
        else:
            import re
            html_text = dm_text.replace(chr(10), '<br>')
            html_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #38bdf8;">\1</a>', html_text)
            
            html = f"""
            <html>
              <body style="background-color: #ffffff; color: #000000; font-family: sans-serif; padding: 20px;">
                <p>{html_text}</p>
                <p>Hezký den přeje<br>Tým Projekt OIS IDPK</p>
              </body>
            </html>
            """

        msg.attach(MIMEText(html, "html"))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[NOTIF EMAIL] Chyba odesílání e-mailu sync: {e}")
        raise e


def format_prague_time(iso_str):
    if not iso_str: return ""
    try:
        iso_str_clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        dt = dt.astimezone(ZoneInfo('Europe/Prague'))
        return dt.strftime('%H:%M')
    except Exception as e:
        p = iso_str.split('T')
        if len(p) > 1: return p[1][:5]
        return iso_str

async def update_depot_discord_messages():
    channel = None
    for guild in bot.guilds:
        channel = discord.utils.find(lambda c: "vozovna" in c.name.lower(), guild.text_channels)
        if channel: break
        
    if not channel: 
        print("[DEPOT DISCORD] Nenalezen kanal obsahujici 'vozovna'", flush=True)
        return
        
    db = get_db()
    if not db: 
        print("[DEPOT DISCORD] Databaze neni dostupna", flush=True)
        return

    if not DEPOT_ZONES:
        print("[DEPOT DISCORD] DEPOT_ZONES je prazdny seznam", flush=True)

    for zone in DEPOT_ZONES:
        depot_name = zone["name"]
        
        all_records = db.table("depot_history").select("*").eq("depot_name", depot_name).order("arrived_at", desc=True).limit(100).execute().data
        active = [r for r in all_records if not r.get("left_at")]
        recent = [r for r in all_records if r.get("left_at")][:5]
        
        embed = discord.Embed(title=f"🅿️ Vozovna: {depot_name}", color=0xf59e0b)
        
        active_str = ""
        if active:
            for a in active:
                spz = a.get("spz", "Neznámá")
                arr = a.get("arrived_at", "")
                if arr: 
                    arr = format_prague_time(arr)
                active_str += f"**{spz}** - Přijel: `{arr}`\n"
        else:
            active_str = "*Prázdno*"
            
        embed.add_field(name="🟢 Aktuálně parkuje", value=active_str, inline=False)
        
        recent_str = ""
        if recent:
            for r in recent:
                spz = r.get("spz", "Neznámá")
                left = r.get("left_at", "")
                if left: 
                    left = format_prague_time(left)
                recent_str += f"**{spz}** - Odjel: `{left}`\n"
        else:
            recent_str = "*Žádné nedávné odjezdy*"
            
        embed.add_field(name="🔴 Nedávné odjezdy", value=recent_str, inline=False)
        embed.set_footer(text="Automaticky aktualizováno")
        
        history = [m async for m in channel.history(limit=50)]
        target_msg = None
        for m in history:
            if m.author == bot.user and m.embeds and m.embeds[0].title == f"🅿️ Vozovna: {depot_name}":
                target_msg = m
                break
                
        try:
            if target_msg:
                try:
                    await target_msg.edit(embed=embed)
                    print(f"[DEPOT DISCORD] Aktualizovana zprava pro: {depot_name}", flush=True)
                except discord.HTTPException as he:
                    if he.code == 30046 or "Maximum number of edits" in str(he):
                        await target_msg.delete()
                        await channel.send(embed=embed)
                        print(f"[DEPOT DISCORD] Zprava pro {depot_name} byla smazana a odeslana nova (limit editaci vycerpan)", flush=True)
                    else:
                        raise he
            else:
                await channel.send(embed=embed)
                print(f"[DEPOT DISCORD] Odeslana nova zprava pro: {depot_name}", flush=True)
        except Exception as e:
            print(f"[DEPOT DISCORD] Chyba pri odesilani/editaci zpravy pro {depot_name}: {e}", flush=True)

@tasks.loop(minutes=5)
async def keepalive_ping():
    try:
        url = "https://datacorebot.koyeb.app/api/keepalive"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
    except: pass

@bot.event
async def on_ready():
    await _trigger_status_update()
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)
    
    commit_msg = os.environ.get("KOYEB_APP_NAME", "Neznámý build")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.github.com/repos/marek-1cz/DataCoreBot/commits/main") as r:
                if r.status == 200:
                    data = await r.json()
                    commit_msg = data.get("commit", {}).get("message", "Neznámý build").split("\n")[0]
    except Exception:
        pass
        
    start_msg = f"**BUILD:** {commit_msg}\nBot byl úspěšně restartován a běží."
    send_log("🔄 Systém Online", start_msg, 0x10b981)
    
    # DM Notifikace uživatelům se zapnutým !aktulizace
    async def send_startup_dms():
        try:
            db = get_db()
            if db:
                res = db.table("bot_settings").select("discord_id").eq("dm_updates", "true").execute()
                for row in (res.data or []):
                    try:
                        uid = int(row["discord_id"])
                        user = bot.get_user(uid) or await bot.fetch_user(uid)
                        if user:
                            now = get_prague_time().strftime("%H:%M")
                            await user.send(f"🔄 **Systém Online**\n\n**BUILD:** {commit_msg}\nBot byl úspěšně restartován a běží.\nDnes v {now}")
                    except Exception: pass
        except Exception as e: print(f"Chyba pri posilani DM start zpráv: {e}", flush=True)
        
    bot.loop.create_task(send_startup_dms())
    try: bot.add_view(DynamicDownloadView())
    except: pass
    try: bot.add_view(AppAuthView())
    except: pass
    try: bot.add_view(DashboardAuthView())
    except: pass
    try:
        for guild in bot.guilds: bot.invites_cache[guild.id] = await guild.invites()
    except: pass
    trigger_setup_messages_update()
    if not keepalive_ping.is_running(): keepalive_ping.start()
    if not check_depot_queue.is_running(): check_depot_queue.start()
    if not check_notification_queue.is_running(): check_notification_queue.start()

    import asyncio
    async def initial_depot_update():
        for _ in range(15):
            if DEPOT_ZONES: break
            await asyncio.sleep(1)
        try: await update_depot_discord_messages()
        except Exception as e: print(f"Chyba pri initial depot update: {e}", flush=True)
    
    bot.loop.create_task(initial_depot_update())

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
                try: await channel.send(embed=embed)
                except: pass
                break
    await bot.process_commands(message)

@bot.command(name="debugvozovna")
@check_web_sa()
async def cmd_debugvozovna(ctx):
    try:
        await ctx.send("Spouštím diagnostiku vozoven...")
        
        channel = discord.utils.find(lambda c: "vozovna" in c.name.lower(), ctx.guild.text_channels)
        if not channel:
            await ctx.send("❌ Nenalezen žádný textový kanál obsahující slovo 'vozovna'.")
            return
        await ctx.send(f"✅ Nalezen kanál: {channel.mention} (ID: {channel.id})")
        
        db = get_db()
        if not db:
            await ctx.send("❌ Připojení k databázi (Supabase) selhalo.")
            return
        await ctx.send("✅ Připojení k DB v pořádku.")
        
        if not DEPOT_ZONES:
            await ctx.send("❌ Proměnná DEPOT_ZONES je prázdná. Vozovny se ještě nenačetly z databáze nebo neexistují.")
            return
        await ctx.send(f"✅ Načteno {len(DEPOT_ZONES)} vozoven z paměti: {', '.join(z['name'] for z in DEPOT_ZONES)}")
        
        await ctx.send(f"Testuji práva kanálu {channel.mention}...")
        try:
            history = [m async for m in channel.history(limit=5)]
            await ctx.send(f"✅ Čtení historie funguje (nalezeno {len(history)} zpráv).")
        except Exception as e:
            await ctx.send(f"❌ Chyba čtení historie kanálu (chybí právo Číst historii zpráv?): {e}")
            return
            
        await ctx.send("Volám hlavní funkci update_depot_discord_messages()...")
        await update_depot_discord_messages()
        await ctx.send("✅ Hlavní funkce proběhla bez pádu.")
        
    except Exception as e:
        await ctx.send(f"❌ Neočekávaná chyba při diagnostice: {e}")

bot.remove_command("help")

@bot.event
async def on_member_join(member):
    await async_send_log("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum:** {get_prague_time().strftime('%d.%m.%Y %H:%M')}", 0x10b981)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!**", delete_after=15)
    elif isinstance(error, commands.MemberNotFound) or isinstance(error, commands.UserNotFound): await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!**", delete_after=15)
    elif isinstance(error, commands.CommandNotFound): await ctx.send(f"❌ **Tento příkaz neexistuje.** Zadej `!help` pro zobrazení seznamu příkazů.", delete_after=15)
    elif isinstance(error, commands.CheckFailure) or isinstance(error, commands.MissingRole): await ctx.send(f"{ctx.author.mention} ❌ **Nemáš oprávnění použít tento příkaz!**", delete_after=15)

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné", value="`!auth`, `!ping`, `!help`, `!register`, `!id`, `!notify list`, `!notify clear`", inline=False)
    embed.add_field(name="🛡️ Správa (SM)", value="`!info [ID]`, `!db [ID]`, `!ban`, `!unban`, `!delete`, `!perdelete`, `!dm @user`, `!dmhistory @uživatel`, `!message #channel`, `!website_block`, `!website_block_mapa`", inline=False)
    embed.add_field(name="⚙️ Administrace (web-sa)", value="`!setup_download`, `!sm @uživatel`, `!debugvozovna`, `!aktulizace`, `!dashadd [id] [role]`, `!dashremove [id]`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def cmds(ctx):
    await help(ctx)

@bot.group(name="notify", invoke_without_command=True)
async def notify_group(ctx):
    await ctx.send("Použití: `!notify list [uživatel]` nebo `!notify clear [uživatel]`", delete_after=15)

@notify_group.command(name="list")
async def notify_list(ctx, target_user: str = None):
    if target_user:
        is_admin = discord.utils.get(ctx.author.roles, name="SM") or discord.utils.get(ctx.author.roles, name="web-sa") or discord.utils.get(ctx.author.roles, name="DEV") or ctx.author.guild_permissions.administrator
        if not is_admin:
            await ctx.send("❌ K prohlížení notifikací ostatních musíš být administrátor.")
            return
        target_discord_id = target_user.strip("<@!>")
    else:
        target_discord_id = str(ctx.author.id)

    db = get_db()
    if not db: return
    
    u_res = db.table("users").select("id").eq("discord_id", target_discord_id).execute()
    if not u_res.data:
        await ctx.send(f"Uživatel {target_discord_id} není registrován.")
        return
    
    user_session = str(u_res.data[0]["id"])
    n_res = db.table("bus_notifications").select("*").eq("user_session", user_session).eq("is_active", True).execute()
    
    if not n_res.data:
        await ctx.send(f"Uživatel {target_discord_id} nemá žádná aktivní upozornění.")
        return
        
    embed = discord.Embed(title=f"🔔 Aktivní upozornění", description=f"Pro uživatele: <@{target_discord_id}>", color=0x38bdf8)
    for n in n_res.data:
        lbl = n.get("label") or n.get("identifier")
        active_str = "Aktivní" if n.get("is_active") else "Neaktivní"
        
        t_dict = n.get("triggers") or {}
        t_list = []
        if t_dict.get("terminal"): t_list.append("Konečná")
        if t_dict.get("new_line"): t_list.append("Nová linka")
        if t_dict.get("depot_in"): t_list.append(f"Do vozovny ({t_dict['depot_in']})")
        if t_dict.get("depot_out"): t_list.append(f"Z vozovny ({t_dict['depot_out']})")
        if t_dict.get("trip_change"): t_list.append("Změna spoje")
        if t_dict.get("started_moving"): t_list.append("Rozjezd")
        if t_dict.get("stop_near"): t_list.append(f"Zastávka ({t_dict['stop_near']})")
        if t_dict.get("delay_threshold"): t_list.append(f"Zpoždění > {t_dict['delay_threshold']} min")
        if t_dict.get("delay_change"): t_list.append("Změna zpoždění")
        t_str = ", ".join(t_list) or "Žádné"
        
        embed.add_field(name=f"ID: {n['id'][:8]} | {lbl}", value=f"Typ: {n['identifier_type']} - Cíl: {n['identifier']} | Stav: {active_str}\nUdálosti: {t_str}", inline=False)
        
    await ctx.send(embed=embed)

@notify_group.command(name="clear")
async def notify_clear(ctx, target_user: str = None):
    if target_user:
        is_admin = discord.utils.get(ctx.author.roles, name="SM") or discord.utils.get(ctx.author.roles, name="web-sa") or discord.utils.get(ctx.author.roles, name="DEV") or ctx.author.guild_permissions.administrator
        if not is_admin:
            await ctx.send("❌ Ke smazání notifikací ostatních musíš být administrátor.")
            return
        target_discord_id = target_user.strip("<@!>")
    else:
        target_discord_id = str(ctx.author.id)
        
    db = get_db()
    if not db: return
        
    u_res = db.table("users").select("id").eq("discord_id", target_discord_id).execute()
    if not u_res.data:
        await ctx.send(f"Uživatel {target_discord_id} není registrován.")
        return
        
    user_session = str(u_res.data[0]["id"])
    db.table("bus_notifications").delete().eq("user_session", user_session).execute()
    
    await ctx.send(f"✅ Všechna upozornění pro uživatele <@{target_discord_id}> byla smazána.")

@bot.command()
@commands.has_role('web-sa')
async def dashadd(ctx, target_id: str, role: str):
    role = role.lower()
    if role not in ["viewer", "admin", "superadmin", "sa", "dev", "bt", "user"]:
        await ctx.send("❌ Neplatná úroveň! Možnosti: viewer, admin, superadmin, sa, dev, bt, user")
        return
    r_str = "User"
    if role in ["superadmin", "sa"]: r_str = "SA"
    elif role in ["admin", "dev"]: r_str = "DEV"
    elif role in ["viewer", "bt"]: r_str = "BT"
    
    db = get_db()
    if db:
        res = db.table("users").update({"dashboard_access": True, "role": r_str}).eq("discord_id", target_id).execute()
        if not res.data: await ctx.send(f"❌ Uživatel `{target_id}` nebyl v databázi nalezen.")
        else: await ctx.send(f"✅ Dashboard přístup '{role}' udělen.")

@bot.command()
@commands.has_role('web-sa')
async def dashremove(ctx, target_id: str):
    db = get_db()
    if db:
        res = db.table("users").update({"dashboard_access": False}).eq("discord_id", target_id).execute()
        if not res.data: await ctx.send(f"❌ Uživatel `{target_id}` nebyl v databázi nalezen.")
        else: await ctx.send(f"✅ Dashboard přístup odebrán pro `{target_id}`.")


@bot.command()
async def id(ctx, user: discord.User = None):
    """Zobrazí Discord ID uživatele. Pokud není zadán uživatel, zobrazí tvé ID."""
    target = user or ctx.author
    if target == ctx.author:
        await ctx.send(f"🆔 Tvoje Discord ID je: `{target.id}`")
    else:
        await ctx.send(f"🆔 Discord ID uživatele {target.mention} je: `{target.id}`")

@bot.command()
async def auth(ctx):
    try: await ctx.message.delete()
    except: pass
    db = get_db()
    if db:
        u = db.table("users").select("login_token").eq("discord_id", str(ctx.author.id)).execute().data
        if u and u[0].get('login_token'): await ctx.send(f"🛡️ {ctx.author.mention}, potvrďte přihlášení:", view=AppAuthView(u[0]['login_token'], str(ctx.author.id), False), delete_after=60)
        else:
            msg = await ctx.send(f"❌ {ctx.author.mention} Nemáš čekající požadavek.")
            await asyncio.sleep(5); await msg.delete()

@bot.command()
async def verze(ctx):
    db = get_db()
    if not db: return await ctx.send("❌ Databáze není dostupná.")
    versions = db.table("software_versions").select("*").order("id", desc=True).execute().data or []
    if not versions: return await ctx.send("Zatím nejsou dostupné žádné verze.")
    embed = discord.Embed(title="📦 Seznam verzí", color=0x38bdf8)
    for v in versions:
        status = "✅ Aktivní" if str(v.get('is_active', 'True')).lower() == 'true' else "❌ Zablokováno"
        embed.add_field(name=f"{v['version_name']} [{v.get('db_version', '')}]", value=f"Pro: `{v['target_role']}` | Stav: {status}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@check_sm_role()
async def info(ctx, discord_id: str = None):
    """Zobrazí info o uživateli. Vyžaduje roli SM."""
    if not discord_id: return await ctx.send("❌ Zadejte ID.")
    db = get_db()
    if not db: return
    u = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not u: return await ctx.send("❌ Nenalezen.")
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
    db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await send_user_dm(discord_id, "🔨 Účet zablokován", "Váš přístup do aplikace byl zablokován.", 0xef4444)
    await ctx.send(f"🔨 Uživateli `{discord_id}` byl udělen BAN.")

@bot.command()
@check_sm_role()
async def unban(ctx, discord_id: str):
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
    await send_user_dm(discord_id, "🕊️ Účet odblokován", "Váš přístup do aplikace byl obnoven.", 0x10b981)
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
    await ctx.send(f"☠️ Účet `{discord_id}` byl smazán.")

class PerDeleteConfirm(discord.ui.View):
    def __init__(self, target_id, author_id):
        super().__init__(timeout=60)
        self.target_id = target_id; self.author_id = author_id

    @discord.ui.button(label="Ano, trvale smazat", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.defer()
        db = get_db()
        if db:
            db.table("users").delete().eq("discord_id", self.target_id).execute()
            await interaction.edit_original_response(content=f"✅ Účet `{self.target_id}` byl PERMANENTNĚ smazán.", view=None, embed=None)

    @discord.ui.button(label="Zrušit", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.edit_message(content="❌ Akce zrušena.", view=None, embed=None)

@bot.command()
@check_sm_role()
async def perdelete(ctx, discord_id: str):
    embed = discord.Embed(title="⚠️ Permanentní smazání", description=f"Opravdu smazat `{discord_id}` permanentně?", color=0xef4444)
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
        discord_id = str(ctx.author.id); nick = ctx.author.display_name; target_member = ctx.author
    now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
    check = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if check:
        if check[0].get('is_banned'): return await ctx.send("❌ Tento účet má BAN.")
        elif check[0].get('is_deleted'):
            highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
            new_app_id = highest[0]["app_id"] + 1 if highest else 1000
            db.table("users").update({"app_id": new_app_id, "nick": nick, "is_deleted": False, "deleted_at": "", "registered_at": now_str}).eq("discord_id", discord_id).execute()
            await ctx.send(f"✅ Smazaný účet obnoven! Nové App ID: **#{new_app_id}**.")
        else: await ctx.send("ℹ️ Tento uživatel již je zaregistrován!")
    else:
        highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
        new_app_id = highest[0]["app_id"] + 1 if highest else 1000
        db.table("users").insert({"app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "ip_address": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": now_str}).execute()
        await ctx.send(f"✅ Zaregistrován! App ID: **#{new_app_id}**.")

@bot.command()
@check_sm_role()
async def dm(ctx, user: discord.User, *, text: str):
    try:
        embed = discord.Embed(title="📩 Zpráva od administrace", description=text, color=0x38bdf8)
        embed.set_footer(text="Toto je automatická zpráva, na kterou lze odepsat.")
        await user.send(embed=embed)
        await ctx.send(f"✅ Zpráva odeslána uživateli `{user.display_name}`.")
    except discord.Forbidden: await ctx.send(f"❌ Uživatel `{user.display_name}` má zablokované DM.")
    except Exception as e: await ctx.send(f"❌ Chyba: `{e}`")

@bot.command()
@check_sm_role()
async def dmhistory(ctx, user: discord.User):
    status_msg = await ctx.send("<a:loading:123> Načítám historii zpráv...")
    try:
        if not user.dm_channel: await user.create_dm()
        messages = [msg async for msg in user.dm_channel.history(limit=100)]
        messages.reverse()
        if not messages: return await status_msg.edit(content=f"📭 DM s `{user.display_name}` je prázdné.")
        log_content = f"--- HISTORIE ZPRÁV DM S UŽIVATELEM {user.display_name.upper()} ({user.id}) ---\n\n"
        for m in messages:
            time_str = (m.created_at + timedelta(hours=1)).strftime("%d.%m.%Y %H:%M:%S")
            author_name = "🤖 BOT" if m.author.bot else f"👤 {m.author.display_name}"
            log_content += f"[{time_str}] {author_name}:\n"
            
            if m.content:
                indented_content = "\n".join([f"    {line}" for line in m.content.split("\n")])
                log_content += f"{indented_content}\n"
            
            for emb in m.embeds:
                log_content += f"    [Embed]: {emb.title or 'Bez titulku'}\n"
                if emb.description:
                    indented_desc = "\n".join([f"      {line}" for line in emb.description.split("\n")])
                    log_content += f"{indented_desc}\n"
                for field in emb.fields:
                    log_content += f"      - {field.name}: {field.value}\n"
            
            if m.attachments: 
                log_content += f"    [Příloha]: {', '.join([a.url for a in m.attachments])}\n"
                
            log_content += "-"*50 + "\n\n"
            
        file_stream = io.BytesIO(log_content.encode('utf-8'))
        file = discord.File(file_stream, filename=f"HistorieDM_{user.display_name}.txt")
        await status_msg.delete()
        await ctx.send(f"📄 Posledních 100 zpráv s `{user.display_name}`:", file=file)
    except discord.Forbidden: await status_msg.edit(content="❌ Nemám oprávnění k DM.")
    except Exception as e: await status_msg.edit(content=f"❌ Chyba: `{e}`")

@bot.command()
@check_sm_role()
async def message(ctx, channel: discord.TextChannel, *, text: str):
    try:
        await channel.send(text)
        await ctx.send(f"✅ Zpráva odeslána do {channel.mention}.")
    except discord.Forbidden: await ctx.send(f"❌ Nemám oprávnění psát do {channel.mention}.")
    except Exception as e: await ctx.send(f"❌ Chyba: `{e}`")

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
@check_sm_role()
async def sm(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role: return await ctx.send("❌ Role `SM` neexistuje.")
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"➖ Role **SM** odebrána.")
    else:
        await member.add_roles(role)
        await ctx.send(f"➕ Role **SM** přidělena.")

@bot.command(name="website_block")
@check_sm_role()
async def cmd_website_block(ctx):
    """Toggle web_maintenance. Role SM required."""
    db = get_db()
    if not db:
        return await ctx.send("❌ Databáze není dostupná.")
    try:
        s = db.table("settings").select("setting_value").eq("setting_key", "web_maintenance").execute().data
        current = str(s[0]['setting_value']).lower() == 'true' if s else False
        new_val = 'False' if current else 'True'
        db.table("settings").update({"setting_value": new_val}).eq("setting_key", "web_maintenance").execute()
        if new_val == 'True':
            embed = discord.Embed(title="🚧 Maintenance Mode ZAPNUT", description="Web byl přepnut do **maintenance módu**.\nVšichni návštěvníci jsou přesměrováni na /blocked.", color=0xef4444)
            send_log("🚧 Maintenance Mode ZAPNUT", f"Web byl zablokován příkazem !website_block od {ctx.author.display_name}.", 0xef4444)
        else:
            embed = discord.Embed(title="✅ Maintenance Mode VYPNUT", description="Web byl **obnoven** z maintenance módu.\nNávštěvníci mají opět přístup.", color=0x10b981)
            send_log("✅ Maintenance Mode VYPNUT", f"Web byl obnoven příkazem !website_block od {ctx.author.display_name}.", 0x10b981)
        embed.set_footer(text=f"Provedl: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        trigger_status_channel_update()
    except Exception as e:
        await ctx.send(f"❌ Chyba: `{e}`")

@bot.command(name="website_block_mapa")
@check_sm_role()
async def cmd_website_block_mapa(ctx):
    """Toggle map_enabled. Role SM required."""
    db = get_db()
    if not db:
        return await ctx.send("❌ Databáze není dostupná.")
    try:
        s = db.table("settings").select("setting_value").eq("setting_key", "map_enabled").execute().data
        current = str(s[0]['setting_value']).lower() != 'false' if s else True
        new_val = 'False' if current else 'True'
        db.table("settings").update({"setting_value": new_val}).eq("setting_key", "map_enabled").execute()
        if new_val == 'False':
            embed = discord.Embed(title="🗺️ Mapa VYPNUTA", description="Interaktivní mapa byla **vypnuta**.\nNávštěvníci vidí stránku \"mapa offline\" s odkazem na Discord.", color=0xef4444)
            send_log("🗺️ Mapa VYPNUTA", f"Mapa byla vypnuta příkazem !website_block_mapa od {ctx.author.display_name}.", 0xef4444)
        else:
            embed = discord.Embed(title="🗺️ Mapa ZAPNUTA", description="Interaktivní mapa byla **obnovena**.\nNávštěvníci mají opět přístup.", color=0x10b981)
            send_log("🗺️ Mapa ZAPNUTA", f"Mapa byla obnovena příkazem !website_block_mapa od {ctx.author.display_name}.", 0x10b981)
        embed.set_footer(text=f"Provedl: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        trigger_status_channel_update()
    except Exception as e:
        await ctx.send(f"❌ Chyba: `{e}`")

@bot.command()
async def aktulizace(ctx):
    db = get_db()
    if not db: return
    user_data = db.table("users").select("role").eq("discord_id", str(ctx.author.id)).execute().data
    if not user_data or user_data[0].get("role") not in ["SA", "DEV"]:
        return
        
    res = db.table("bot_settings").select("dm_updates").eq("discord_id", str(ctx.author.id)).execute()
    current_state = False
    if res.data:
        current_state = res.data[0].get("dm_updates", False)
        
    new_state = not current_state
    db.table("bot_settings").upsert({"discord_id": str(ctx.author.id), "dm_updates": new_state}).execute()
    
    if new_state:
        msg = await ctx.send("🔔 DM upozornění na aktualizace a restarty: **ZAPNUTO**")
    else:
        msg = await ctx.send("🔕 DM upozornění na aktualizace a restarty: **VYPNUTO**")
        
    await asyncio.sleep(3)
    try:
        await msg.delete()
        await ctx.message.delete()
    except: pass


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

def run_discord_bot(bot_token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            print("==> Pokus o start Discord Bota...", flush=True)
            loop.run_until_complete(bot.start(bot_token))
        except Exception as e:
            print(f"==> [DISCORD CHYBA] Bot havaroval: {e}", flush=True)
            time.sleep(10)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', port, app, use_reloader=False)


def exit_handler():
    try:
        from interaktivnimapa import GLOBAL_BUS_CACHE, db_client
        from zoneinfo import ZoneInfo
        if db_client:
            now = datetime.now(ZoneInfo("Europe/Prague"))
            cache_rows = []
            for bid, bc in list(GLOBAL_BUS_CACHE.items()):
                spz_v = bc.get("spz")
                if not spz_v or spz_v in ("Nezn\u00e1m\u00e1", "Neznámá"):
                    continue
                cache_rows.append({
                    "bus_id": bid,
                    "spz": spz_v,
                    "linka": bc.get("line") or "",
                    "lat": bc.get("lat"),
                    "lng": bc.get("lng"),
                    "spz_verified": bc.get("spz_verified", False),
                    "admin_verified": bc.get("admin_spz_verified", False),
                    "trip_id": bc.get("trip_id"),
                    "color_class": bc.get("color_class"),
                    "status_text": bc.get("status"),
                    "admin_note": bc.get("admin_note", ""),
                    "admin_driver": bc.get("admin_driver", ""),
                    "admin_flag": bc.get("admin_flag", False),
                    "manual_spz": bc.get("manual_spz", False),
                    "updated_at": now.isoformat(),
                })
            if cache_rows:
                db_client.table("spz_cache").upsert(cache_rows).execute()
                print("==> SPZ CACHE FLUSH na exit_handler USPESNY", flush=True)
    except Exception as e:
        print(f"Chyba pri exit flush SPZ: {e}", flush=True)

def sigterm_handler(signum, frame):
    print("==> Přijat SIGTERM (redeploy). Ukládám cache...", flush=True)
    exit_handler()
    sys.exit(0)

atexit.register(exit_handler)
try:
    signal.signal(signal.SIGTERM, sigterm_handler)
except Exception:
    pass

import time

# ============================================================
# MOBILE MIRROR (Ovladač Web Zrcadlo pro řidiče)
# ============================================================
MIRROR_STATES = {}
# Struktura:
# MIRROR_STATES[session_id] = {
#     "last_updated": time.time(),
#     "state": { "line": "...", "dest": "...", "next_stop": "...", "current_stop": "...", "ah_active": False, ... },
#     "pending_actions": []
# }

@app.route('/api/mirror/pc_sync', methods=['POST'])
def mirror_pc_sync():
    """
    PC aplikace (Ovladač) sem každou sekundu posílá svůj stav.
    Vrací seznam akcí (stisků tlačítek) z mobilu, aby je PC provedlo.
    """
    data = request.json
    if not data or 'session_id' not in data:
        return jsonify({"error": "Missing session_id"}), 400
        
    session_id = data['session_id']
    discord_id = data.get('discord_id')
    
    # Ověření oprávnění
    allowed = False
    if discord_id:
        try:
            resp = supabase.table('users').select('role').eq('discord_id', discord_id).execute()
            if resp.data and len(resp.data) > 0:
                role = resp.data[0].get('role', '')
                if any(x in role for x in ['BT', 'DEV', 'SA']):
                    allowed = True
        except:
            pass
            
    if not allowed and discord_id != 'VSC-DEV':
        return jsonify({"error": "Nemas opravneni (Vyžadována Premium role)"}), 403

    # Aktualizace stavu
    if session_id not in MIRROR_STATES:
        MIRROR_STATES[session_id] = {"pending_actions": []}
        
    MIRROR_STATES[session_id]["last_updated"] = time.time()
    MIRROR_STATES[session_id]["state"] = data.get('state', {})
    
    # Vrácení a vyčištění akcí, co byly stisknuty na mobilu
    actions = MIRROR_STATES[session_id]["pending_actions"].copy()
    MIRROR_STATES[session_id]["pending_actions"].clear()
    
    # Čištění starých session (starší 2 minuty)
    now = time.time()
    to_delete = [sid for sid, s in MIRROR_STATES.items() if now - s["last_updated"] > 120]
    for sid in to_delete:
        del MIRROR_STATES[sid]
        
    return jsonify({"status": "ok", "actions": actions})


@app.route('/api/mirror/mobile_state/<session_id>')
def mirror_mobile_state(session_id):
    """
    Server-Sent Events pro mobilní aplikaci. Mobil se napojí a server mu posílá aktualizace.
    """
    def generate():
        last_state_hash = None
        while True:
            if session_id not in MIRROR_STATES:
                yield f"data: {{\"status\": \"offline\"}}\n\n"
                time.sleep(2)
                continue
                
            s = MIRROR_STATES[session_id]
            if time.time() - s["last_updated"] > 10:
                yield f"data: {{\"status\": \"offline\"}}\n\n"
            else:
                import json
                state = s.get("state", {})
                state_str = json.dumps(state)
                h = hash(state_str)
                if h != last_state_hash:
                    last_state_hash = h
                    yield f"data: {{\"status\": \"online\", \"state\": {state_str}}}\n\n"
            time.sleep(0.5)
            
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/mirror/mobile_action/<session_id>', methods=['POST'])
def mirror_mobile_action(session_id):
    """
    Mobilní aplikace sem odešle stisknuté tlačítko (např. {"action": "btn-announce"})
    """
    if session_id not in MIRROR_STATES:
        return jsonify({"error": "Offline"}), 404
        
    data = request.json
    action = data.get("action")
    if action:
        MIRROR_STATES[session_id]["pending_actions"].append(action)
        
    return jsonify({"status": "ok"})


@app.route('/m/<session_id>')
def mirror_mobile_ui(session_id):
    """
    Zobrazí mobilní webové rozhraní (Ovladač do kapsy).
    """
    html = """
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <title>IDPK Ovladač - Mobilní Zrcadlo</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {
                --idpk-blue: #035689; --idpk-dark-blue: #023e63; --idpk-yellow: #F4CC17;
                --idpk-green: #048E56; --idpk-red: #e74c3c;
            }
            body { 
                background-color: var(--idpk-blue); 
                margin: 0; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                color: white; 
                display: flex; 
                flex-direction: column; 
                height: 100vh;
                user-select: none;
                overflow: hidden;
            }
            .status-bar {
                background-color: rgba(0,0,0,0.5);
                padding: 8px;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
                color: #e74c3c;
            }
            .status-bar.online { color: #2ecc71; }
            .info-panel {
                flex: 1;
                padding: 15px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
            }
            .line-dest { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: var(--idpk-yellow); }
            .stop-label { font-size: 11px; color: #aaa; margin-bottom: 2px; }
            .next-stop { font-size: 18px; margin-bottom: 15px; font-weight: bold; }
            .curr-stop { font-size: 26px; font-weight: 900; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 2px solid var(--idpk-yellow); width: 100%; box-sizing: border-box;}
            
            .controls-panel {
                background: var(--idpk-dark-blue);
                padding: 15px;
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding-bottom: 30px;
                box-shadow: 0 -4px 10px rgba(0,0,0,0.5);
            }
            .btn-big {
                background: #e0e0e0;
                color: black;
                font-size: 20px;
                font-weight: 900;
                border: none;
                border-radius: 8px;
                padding: 20px 10px;
                box-shadow: 0 4px 0 #999;
                text-align: center;
                cursor: pointer;
            }
            .btn-big:active { transform: translateY(4px); box-shadow: 0 0 0 #999; }
            .row { display: flex; gap: 10px; }
            .btn-small {
                flex: 1;
                background: #e0e0e0;
                color: black;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 15px 5px;
                box-shadow: 0 3px 0 #999;
                cursor: pointer;
            }
            .btn-small:active { transform: translateY(3px); box-shadow: 0 0 0 #999; }
            .btn-red { background: #e74c3c; color: white; box-shadow: 0 3px 0 #c0392b; }
            .btn-red:active { box-shadow: 0 0 0 #c0392b; }
            .offline-overlay {
                position: absolute; top:0; left:0; right:0; bottom:0;
                background: rgba(0,0,0,0.8); z-index: 100;
                display: flex; flex-direction: column; justify-content: center; align-items: center;
            }
        </style>
    </head>
    <body>
        <div id="status-bar" class="status-bar">PŘIPOJOVÁNÍ...</div>
        
        <div id="offline-screen" class="offline-overlay">
            <i class="fas fa-satellite-dish" style="font-size: 40px; color: #e74c3c; margin-bottom: 15px;"></i>
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">OVLADAČ JE OFFLINE</div>
            <div style="font-size: 12px; color: #aaa; text-align: center; padding: 0 20px;">PC s Palubním systémem není připojeno,<br>nebo skončila platnost spojení.</div>
        </div>

        <div class="info-panel">
            <div class="line-dest" id="txt-header">LINKA --- | CÍL ---</div>
            
            <div class="stop-label">PŘÍŠTÍ ZASTÁVKA</div>
            <div class="next-stop" id="txt-next">---</div>
            
            <div class="stop-label">AKTUÁLNÍ ZASTÁVKA</div>
            <div class="curr-stop" id="txt-curr">---</div>
        </div>

        <div class="controls-panel">
            <button class="btn-big" id="btn-smart" onclick="sendAction('btn-announce')">VYHLÁSIT ZASTÁVKU</button>
            <div class="row">
                <button class="btn-small" onclick="sendAction('btn-up')"><i class="fas fa-arrow-up"></i> ZPĚT</button>
                <button class="btn-small" onclick="sendAction('btn-down')"><i class="fas fa-arrow-down"></i> VSTŘÍC</button>
            </div>
            <div class="row">
                <button class="btn-small btn-red" onclick="sendAction('btn-terminate')">UKONČIT</button>
                <button class="btn-small" onclick="sendAction('btn-repeat')">OPAKOVAT</button>
            </div>
        </div>

        <script>
            const sessionId = "{{ session_id }}";
            const statusBar = document.getElementById('status-bar');
            const offlineScreen = document.getElementById('offline-screen');
            const txtHeader = document.getElementById('txt-header');
            const txtNext = document.getElementById('txt-next');
            const txtCurr = document.getElementById('txt-curr');
            const btnSmart = document.getElementById('btn-smart');

            function connectSSE() {
                const source = new EventSource('/api/mirror/mobile_state/' + sessionId);
                
                source.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.status === 'offline') {
                        statusBar.className = 'status-bar';
                        statusBar.innerText = 'OFFLINE';
                        offlineScreen.style.display = 'flex';
                    } else if (data.status === 'online') {
                        statusBar.className = 'status-bar online';
                        statusBar.innerText = 'PŘIPOJENO - LIVE';
                        offlineScreen.style.display = 'none';
                        updateUI(data.state);
                    }
                };
                source.onerror = function() {
                    statusBar.className = 'status-bar';
                    statusBar.innerText = 'SPOJENÍ ZTRACENO, OBNOVUJI...';
                    offlineScreen.style.display = 'flex';
                };
            }

            function updateUI(state) {
                if (state.header) txtHeader.innerText = state.header;
                if (state.nextStop) txtNext.innerText = state.nextStop;
                if (state.currStop) {
                    txtCurr.innerHTML = state.currStop; // může obsahovat HTML (např. ikony)
                }
                if (state.smartBtnMain) {
                    let sub = state.smartBtnSub ? `<br><span style="font-size:12px; color:#555;">${state.smartBtnSub}</span>` : "";
                    btnSmart.innerHTML = state.smartBtnMain + sub;
                }
            }

            function sendAction(actionId) {
                // Haptická odezva
                if (navigator.vibrate) navigator.vibrate(50);
                
                fetch('/api/mirror/mobile_action/' + sessionId, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: actionId })
                }).catch(e => console.error(e));
            }

            connectSSE();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session_id=session_id)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    start_map_background_task()
    if token:
        Thread(target=run_discord_bot, args=(token,), daemon=True).start()
    else:
        print("KRITICKÁ CHYBA: DISCORD_TOKEN chybí! (Web běží dál bez Bota)")
    run_web()

