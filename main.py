# -*- coding: utf-8 -*-
import os
import sys

# === OPTIMALIZACE PAMĚTI PRO 512 MB CONTAINER (KOYEB OOM EXIT 9 PREVENCE) ===
os.environ.setdefault("MALLOC_ARENA_MAX", "2")
import threading
try:
    threading.stack_size(512 * 1024)  # 512 KB zásobník na vlákno místo výchozích 8 MB na Linuxu
except Exception:
    pass

import time
import signal
import atexit
from datetime import datetime
import discord
from discord.ext import commands, tasks
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify, make_response
from functools import wraps
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
import uuid
import ipaddress
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
    'HTML_FEEDBACK', 'HTML_WAIT_AUTH', 'HTML_LOGIN', 'HTML_PROVOZ_IDPK', 'HTML_REGISTER', 'HTML_UCET',
    'HTML_DASHBOARD_NOTIFICATIONS_MGMT'
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

# Automatické načtení lokálního .env souboru pro localhost vývoj
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip("'").strip('"')
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
        print("[ENV] Lokální konfigurace z .env byla úspěšně načtena.", flush=True)
    except Exception as _e_env:
        print(f"[ENV] Chyba při čtení .env: {_e_env}", flush=True)

print("=== START PROJEKTU OIS IDPK ===", flush=True)

try:
    from local_db import init_local_db, try_sync_to_supabase, local_spz_upsert, check_offline_login
    init_local_db()
    _HAS_LOCAL_DB = True
except Exception as _e_ldb:
    _HAS_LOCAL_DB = False
    print(f'[LOCAL DB] Modul local_db neni dostupny: {_e_ldb}', flush=True)

import secrets as _secrets
import hmac as _hmac
import hashlib as _hashlib
from collections import defaultdict

def set_setting_db(db, key, value):
    try:
        res = db.table("settings").select("*").eq("setting_key", key).execute()
        if res.data:
            db.table("settings").update({"setting_value": value}).eq("setting_key", key).execute()
        else:
            db.table("settings").insert({"setting_key": key, "setting_value": value}).execute()
        return True
    except Exception as e:
        print(f"Error updating setting {key}: {e}")
        return False

app = Flask(__name__)
# ── Secret key MUSTÍ být nastaven jako env proměnná FLASK_SECRET_KEY ──
_flask_secret = os.environ.get('FLASK_SECRET_KEY')
if not _flask_secret:
    _flask_secret = "datacorebot_fallback_secret_key_998877665544332211"
    print('[SECURITY] VAROVANI: FLASK_SECRET_KEY neni nastaven! Pouzivam staticky fallback klic.', flush=True)
app.secret_key = _flask_secret
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('KOYEB_APP_NAME') is not None  # Koyeb běží na HTTPS, lokálně HTTP

app.register_blueprint(mapa_bp)

# ── Whitelist povolených originů pro CORS ──
_CORS_ORIGINS = {
    'https://datacorebot.koyeb.app',
    'https://ois-idpk.cz',
    'https://www.ois-idpk.cz',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'null'
}

@app.after_request
def add_security_headers(response):
    # CORS – pouze whitelisted origins nebo veřejné informační endpointy
    origin = request.headers.get('Origin', '')
    if origin in _CORS_ORIGINS or request.path.startswith('/api/stats') or request.path.startswith('/api/supporters'):
        response.headers['Access-Control-Allow-Origin'] = origin if origin and origin != 'null' else '*'
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

@app.after_request
def inject_announcement(response):
    try:
        from daily_reporter import TRACKER
        TRACKER.record_request(response.status_code, request.path)
    except Exception:
        pass
    if response.content_type and 'text/html' in response.content_type:
        path = request.path
        try:
            a_data_str = get_cached_setting('announcement_data', '')
            active_announcements = []
            
            if a_data_str:
                import json
                a_data = json.loads(a_data_str)
                now = get_prague_time().replace(tzinfo=None)
                
                for a in a_data:
                    if not a.get('active'):
                        continue
                        
                    # Check schedule
                    skip = False
                    st_str = a.get('start_time')
                    en_str = a.get('end_time')
                    if st_str:
                        try:
                            st_dt = datetime.strptime(st_str, "%Y-%m-%dT%H:%M")
                            if now < st_dt: skip = True
                        except: pass
                    if en_str:
                        try:
                            en_dt = datetime.strptime(en_str, "%Y-%m-%dT%H:%M")
                            if now > en_dt: skip = True
                        except: pass
                        
                    if skip:
                        continue
                        
                    urls = [u.strip() for u in a.get('urls', '').split(',') if u.strip()]
                    for u in urls:
                        if u in ('*', 'all', 'vse') or path == u or path.startswith(u) or (not u.startswith('/') and path.startswith('/' + u)):
                            active_announcements.append(a)
                            break
            else:
                a_url = get_cached_setting('announcement_url', '')
                a_text = get_cached_setting('announcement_text', '')
                a_title = get_cached_setting('announcement_title', 'Oznámení od Administrace')
                a_active = get_cached_setting('announcement_active', 'false')
                
                if a_active == 'true' and a_url and a_text:
                    urls = [u.strip() for u in a_url.split(',') if u.strip()]
                    for u in urls:
                        if u in ('*', 'all', 'vse') or path == u or path.startswith(u) or (not u.startswith('/') and path.startswith('/' + u)):
                            active_announcements.append({"title": a_title, "text": a_text, "id": "legacy"})
                            break

            if active_announcements:
                html = response.get_data(as_text=True)
                
                banners_html = '<div class="sys-announcement-wrapper">'
                for i, a in enumerate(active_announcements):
                    a_text_html = a.get('text', '').replace('\n', '<br>')
                    disp_title = a.get('title') if a.get('title') else "Oznámení od Administrace"
                    a_id = f"sys-announcement-{a.get('id', i)}"
                    
                    # z-index goes down so the first one is on top for mobile stack
                    banners_html += f"""
                    <div id="{a_id}" class="sys-banner" style="z-index:{999 - i};">
                      <div style="position:absolute; top:0; left:0; right:0; height:4px; background: repeating-linear-gradient(-45deg, #fbbf24, #fbbf24 15px, #0f172a 15px, #0f172a 30px);"></div>
                      <h3 style="margin:8px 0 5px 0;font-size:15px;color:#fbbf24;text-transform:uppercase;letter-spacing:1px;"><i class="fas fa-exclamation-triangle"></i> {disp_title}</h3>
                      <p style="margin:0;font-size:14px;color:#e2e8f0;">{a_text_html}</p>
                      <button onclick="let el=document.getElementById('{a_id}'); el.style.opacity='0'; el.style.transform='translateY(-20px)'; setTimeout(()=>el.style.display='none', 300);" style="position:absolute; top:10px; right:10px; background:transparent; border:none; color:#94a3b8; cursor:pointer; font-size:18px; transition:0.2s;" onmouseover="this.style.color='white'" onmouseout="this.style.color='#94a3b8'">&times;</button>
                    </div>
                    """
                
                banners_html += "</div>"
                
                css = """
                <style>
                .sys-announcement-wrapper {
                    position: fixed; top: 90px; left: 50%; transform: translateX(-50%);
                    z-index: 99999; display: flex; justify-content: center; gap: 20px;
                    width: max-content; max-width: 90%; pointer-events: none;
                }
                .sys-banner {
                    pointer-events: auto; background: #0f172a; color: white; padding: 15px 45px 15px 30px;
                    border-radius: 8px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); text-align: center;
                    font-family: sans-serif; border: 1px solid #334155; position: relative;
                    min-width: 250px; max-width: 600px; overflow: hidden;
                    animation: sysBannerFadeIn 0.5s ease-out; transition: opacity 0.3s, transform 0.3s;
                }
                @media (max-width: 768px) {
                    .sys-announcement-wrapper { display: block; width: 90%; }
                    .sys-banner { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 100%; box-sizing: border-box; max-width: none; }
                }
                @keyframes sysBannerFadeIn { from { top: -50px; opacity: 0; } to { opacity: 1; } }
                </style>
                """
                
                banners_html += css
                if '</body>' in html:
                    html = html.replace('</body>', banners_html + '</body>')
                else:
                    html += banners_html
                response.set_data(html)
        except Exception as e: 
            print("Banner inject error:", e)
    return response

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

def render_error_page(code: int, title: str, summary: str, icon: str = "fa-triangle-exclamation"):
    """Vykreslí moderní chybovou stránku v designu nového webu s hardware-aware animacemi."""
    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chyba {code} | DataCore</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
    body {{
      background: #070b14;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      overflow-x: hidden;
      position: relative;
    }}
    body::before {{
      content: "";
      position: fixed;
      top: -30%; left: -30%; width: 160%; height: 160%;
      background: radial-gradient(circle at 50% 40%, rgba(239, 68, 68, 0.14), rgba(56, 189, 248, 0.05) 45%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }}
    .err-card {{
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 520px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(239, 68, 68, 0.35);
      box-shadow: 0 25px 70px rgba(0, 0, 0, 0.85), 0 0 35px rgba(239, 68, 68, 0.18);
      border-radius: 24px;
      padding: 44px 32px;
      text-align: center;
    }}
    @media (prefers-reduced-motion: no-preference) {{
      .err-card {{
        animation: errFade 0.5s cubic-bezier(0.16, 1, 0.3, 1);
      }}
      .err-icon-wrap {{
        animation: iconPulse 3.5s ease-in-out infinite;
      }}
    }}
    @keyframes errFade {{
      from {{ opacity: 0; transform: translateY(20px) scale(0.97); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    @keyframes iconPulse {{
      0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 16px rgba(239, 68, 68, 0.45)); }}
      50% {{ transform: scale(1.06); filter: drop-shadow(0 0 28px rgba(239, 68, 68, 0.8)); }}
    }}
    .err-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.45);
      color: #fca5a5;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 22px;
    }}
    .err-title {{
      font-size: 24px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 12px;
      letter-spacing: -0.4px;
    }}
    .err-desc {{
      font-size: 14px;
      color: #94a3b8;
      line-height: 1.6;
      margin-bottom: 30px;
      max-width: 420px;
      margin-left: auto;
      margin-right: auto;
    }}
    .err-actions {{
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
    }}
    .btn-act {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 22px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.25s ease;
      min-width: 140px;
    }}
    .btn-act-back {{
      background: rgba(30, 41, 59, 0.85);
      border: 1px solid #334155;
      color: #e2e8f0;
    }}
    .btn-act-back:hover {{
      background: #334155;
      color: #ffffff;
      transform: translateY(-2px);
    }}
    .btn-act-home {{
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      border: none;
      color: #070b14;
      box-shadow: 0 4px 18px rgba(56, 189, 248, 0.35);
    }}
    .btn-act-home:hover {{
      box-shadow: 0 6px 24px rgba(56, 189, 248, 0.55);
      transform: translateY(-2px);
      color: #000000;
    }}
  </style>
</head>
<body>
  <div class="err-card">
    <div class="err-badge"><i class="fas fa-triangle-exclamation"></i> Kód {code}</div>
    <div class="err-icon-wrap" style="font-size: 52px; color: #ef4444; margin-bottom: 18px;">
      <i class="fas {icon}"></i>
    </div>
    <h1 class="err-title">{title}</h1>
    <p class="err-desc">{summary}</p>
    <div class="err-actions">
      <button class="btn-act btn-act-back" onclick="if(window.history.length > 1) {{ window.history.back(); }} else {{ window.location.href='/'; }}">
        <i class="fas fa-arrow-left"></i> O krok zpět
      </button>
      <a href="/" class="btn-act btn-act-home">
        <i class="fas fa-house"></i> Domů
      </a>
    </div>
  </div>
  <script>
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4) {{
      let c = document.querySelector('.err-card');
      if (c) {{ c.style.backdropFilter = 'none'; c.style.webkitBackdropFilter = 'none'; c.style.background = '#0f172a'; }}
    }}
  </script>
</body>
</html>"""

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        code = e.code or 404
        title = "Stránka nenalezena" if code == 404 else f"Chyba {code}"
        summary = "Požadovaná stránka na serveru neexistuje nebo byla přesunuta." if code == 404 else "Přístup k tomuto prostředku byl odepřen."
        icon = "fa-compass" if code == 404 else "fa-shield-halved"
        return render_error_page(code, title, summary, icon), code
    
    code = 500
    err_str = str(e)
    tb = traceback.format_exc()
    print('[ERROR 500]', tb, flush=True)
    try:
        from daily_reporter import TRACKER
        TRACKER.record_request(500, request.path, err_str)
    except Exception:
        pass

    # Zjistit uživatele pokud je přihlášen
    user_info = "Nepřihlášený návštěvník"
    cookie_token = request.cookies.get('web_session_token')
    if cookie_token:
        try:
            u = get_cached_session_user(cookie_token)
            if u:
                u_nick = u.get('nick') or u.get('email') or 'Uživatel'
                u_did = u.get('discord_id') or 'Nezadáno'
                user_info = f"**{u_nick}** (Discord ID: `{u_did}`, User ID: `{u.get('id')}`)"
        except Exception:
            pass

    # Zalogovat na discord do kanálu 📲・error-app (a záložně do logs)
    try:
        short_tb = tb[-1600:] if len(tb) > 1600 else tb
        err_field = f"**Uživatel:** {user_info}\n**URL:** `{request.method} {request.path}`\n**Chyba:** `{err_str[:300]}`\n```py\n{short_tb}\n```"
        send_log("📲 APLIKAČNÍ CHYBA (Web 500)", err_field, 0xef4444, channel_name="📲・error-app")
    except Exception as ex_l:
        print(f"[ERR LOG FAIL] {ex_l}", flush=True)

    summary = "Při zpracování požadavku došlo k neočekávané chybě serveru. Chyba byla automaticky nahlášena vývojářům."
    if "402" in err_str or "egress" in err_str.lower() or "payment required" in err_str.lower():
        summary = "Byl překročen datový limit databáze. Provoz nyní běží v nouzovém režimu ze zálohy."
        try:
            global EGRESS_SAVE_MODE
            EGRESS_SAVE_MODE = True
            send_log("🚨 Nouzový stav: Supabase 402 Detekováno!", "Byl detekován kód 402 / vyčerpaný limit Supabase.", 0xef4444, channel_name="📲・error-app", pings=["👑| Project Owner", "-Executive Board-"])
        except Exception:
            pass

    return render_error_page(500, "Vyskytla se chyba", summary, "fa-circle-exclamation"), 500

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SMTP_EMAIL = (os.environ.get("SMTP_EMAIL") or os.environ.get("SMTP_USER") or os.environ.get("EMAIL_USER") or "datacorebot.admin@gmail.com").strip().strip('"').strip("'")
SMTP_PASSWORD = (os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS") or os.environ.get("EMAIL_PASS") or "tcnrtfokjcdegqdd").strip().strip('"').strip("'")
BMAC_WEBHOOK_SECRET = os.environ.get("BMAC_WEBHOOK_SECRET", "")
_db_client = None

# ── Dynamický egress monitor a nouzový štít (Turso DB má 1 mld čtení/měsíc, bez limitu egressu) ──
EGRESS_SAVE_MODE: bool = False
EGRESS_USED_GB: float = 0.0
EGRESS_LIMIT_GB: float = 500.0   # Turso Cloud limit
EGRESS_WARN_PCT: float = 90.0
_last_egress_check: float = 0.0
_EGRESS_CHECK_INTERVAL: int = 3600

_STATS_SUMMARY_CACHE = {"ts": 0, "data": None}
_SUMMARY_BACKUP_FILE = os.path.join(os.path.dirname(__file__), "summary_backup.json")
_USERS_BACKUP_FILE = os.path.join(os.path.dirname(__file__), "users_backup.json")
_AUTH_TOKEN_STATUS: dict = {}  # {str(discord_id): "approved" | "rejected" | "timeout" | "waiting"}
_SUPPORTERS_BACKUP_FILE = os.path.join(os.path.dirname(__file__), "supporters_backup.json")
_SUPPORTERS_CACHE = {"ts": 0, "data": []}

def _get_fallback_supporters():
    try:
        if os.path.exists(_SUPPORTERS_BACKUP_FILE):
            with open(_SUPPORTERS_BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _get_fallback_users():
    try:
        if os.path.exists(_USERS_BACKUP_FILE):
            with open(_USERS_BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[FALLBACK] Chyba cteni users_backup.json: {e}", flush=True)
    return []

def _get_fallback_summary():
    try:
        if os.path.exists(_SUMMARY_BACKUP_FILE):
            with open(_SUMMARY_BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[FALLBACK] Chyba cteni summary_backup.json: {e}", flush=True)
    return None

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

SUPABASE_RESTRICTED = False
_LAST_SUPABASE_RESTRICTED_CHECK = 0

def is_supabase_restricted():
    global SUPABASE_RESTRICTED
    try:
        import turso_db
        if turso_db.is_turso_blocked():
            return True
    except Exception:
        pass
    return SUPABASE_RESTRICTED

def set_supabase_restricted(val=True):
    global SUPABASE_RESTRICTED, _LAST_SUPABASE_RESTRICTED_CHECK
    SUPABASE_RESTRICTED = val
    _LAST_SUPABASE_RESTRICTED_CHECK = time.time()
    try:
        import turso_db
        if turso_db.is_turso_blocked() != val:
            turso_db.set_turso_blocked(val)
    except Exception:
        pass

def check_supabase_error(e):
    global SUPABASE_RESTRICTED
    err = str(e).lower()
    if any(k in err for k in ["402", "exceed_egress_quota", "restricted due to", "reads are blocked", "sql read operations are forbidden", "operation was blocked"]):
        if not SUPABASE_RESTRICTED:
            SUPABASE_RESTRICTED = True
            print("[DATABASE RESTRICTION] Zjištěno překročení kvóty databáze. Automaticky přepnuto do offline/Gist/SQLite autonomního režimu.", flush=True)
            try:
                import turso_db
                turso_db.set_turso_blocked(True, reason=str(e))
            except Exception:
                pass
        return True
    return False

def get_db():
    global _db_client
    try:
        if _db_client is None:
            import turso_db
            _db_client = turso_db.get_turso_db()
        return _db_client
    except Exception as e:
        print(f"[TURSO DB] Chyba připojení k DB: {e}", flush=True)
    return None

_AUTH_CACHE = {}      # {discord_id: (timestamp, role, is_banned)}
_SESSION_CACHE = {}   # {web_session_token: (timestamp, user_dict)}
_SETTINGS_CACHE = {}  # {setting_key: (timestamp, value)}
_IP_GEO_CACHE = {}     # {ip: (timestamp, dict)}
_RECENT_WEB_VISITS = {} # {ip: last_timestamp}
_STATS_DEDUP_CACHE = {}   # {key: timestamp}
_STATS_DEDUP_LOCK = threading.Lock()

# ── GTFS normalizace linek (např. '734' -> '490734') ──────────────────────────
_LINE_MAPPING = {}
try:
    _mapping_file = os.path.join(os.path.dirname(__file__), "gtfs_line_mapping.json")
    if os.path.exists(_mapping_file):
        with open(_mapping_file, "r", encoding="utf-8") as _mf:
            _LINE_MAPPING = json.load(_mf)
        print(f"[GTFS] Načtena mapa linek: {len(_LINE_MAPPING)} tras.", flush=True)
except Exception as _e_map:
    print(f"[GTFS] Nelze načíst gtfs_line_mapping.json: {_e_map}", flush=True)

def normalize_line_number(raw_line: str) -> str:
    raw = str(raw_line or "").strip()
    if not raw:
        return ""
    if len(raw) == 6 and raw.isdigit():
        return raw
    # Ošetření interních GTFS route ID z linky 735 / Stříbro
    if raw in ('R6120', 'R5080', 'R5082'):
        return '490735'
    if raw in ('R5079', 'R5081'):
        return '490734'
    if raw in _LINE_MAPPING:
        return _LINE_MAPPING[raw]
    clean_num = raw.lstrip('0')
    if clean_num in _LINE_MAPPING:
        return _LINE_MAPPING[clean_num]
    return raw



def get_real_client_ip(req):
    """Získá skutečnou veřejnou IP adresu klienta z proxy hlaviček (Koyeb, Cloudflare apod.)."""
    headers_order = ('CF-Connecting-IP', 'True-Client-IP', 'X-Real-IP')
    for h in headers_order:
        val = req.headers.get(h)
        if val:
            ip_cand = val.split(',')[0].strip()
            if ip_cand:
                try:
                    obj = ipaddress.ip_address(ip_cand)
                    if not (obj.is_private or obj.is_loopback or obj.is_link_local):
                        return str(obj)
                except ValueError:
                    pass

    xff = req.headers.get('X-Forwarded-For')
    if xff:
        for part in xff.split(','):
            ip_cand = part.strip()
            if not ip_cand:
                continue
            if ':' in ip_cand and not ip_cand.startswith('[') and ip_cand.count(':') == 1:
                ip_cand = ip_cand.split(':')[0]
            try:
                obj = ipaddress.ip_address(ip_cand)
                if not (obj.is_private or obj.is_loopback or obj.is_link_local):
                    return str(obj)
            except ValueError:
                pass

    if req.remote_addr:
        return req.remote_addr.strip()
    return '127.0.0.1'

def resolve_ip_geo(ip, cf_hint=None):
    """Určí zemi, region, město a kód vlajky pro IP adresu s paměťovou mezipamětí."""
    now = time.time()
    if ip in _IP_GEO_CACHE:
        ts, cached = _IP_GEO_CACHE[ip]
        if now - ts < 86400 * 7:
            return cached

    country_code = (cf_hint or "").lower().strip()
    if country_code in ('neznámá', 'unknown', 'none', ''):
        country_code = 'cz'
    country_name = "Česká republika" if country_code == 'cz' else country_code.upper()
    region = ""
    city = ""

    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            res = {
                "country_code": "cz",
                "country_name": "Lokální síť",
                "region": "Vývoj",
                "city": "Localhost",
                "flag": "https://flagcdn.com/24x18/cz.png"
            }
            _IP_GEO_CACHE[ip] = (now, res)
            return res
    except Exception:
        pass

    found = False
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=2.5) as response:
            g = json.loads(response.read().decode())
            if g.get("status") == "success":
                country_code = (g.get("countryCode") or country_code).lower()
                country_name = g.get("country") or country_name
                region = g.get("regionName") or ""
                city = g.get("city") or ""
                found = True
    except Exception:
        pass

    if not found:
        try:
            url = f"https://freeipapi.com/api/json/{ip}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=2.5) as response:
                g = json.loads(response.read().decode())
                if g.get("countryCode"):
                    country_code = (g.get("countryCode") or country_code).lower()
                    country_name = g.get("countryName") or country_name
                    region = g.get("regionName") or ""
                    city = g.get("cityName") or ""
                    found = True
        except Exception:
            pass

    flag = f"https://flagcdn.com/24x18/{country_code}.png" if country_code and country_code != 'xx' else "https://flagcdn.com/24x18/cz.png"

    res = {
        "country_code": country_code,
        "country_name": country_name,
        "region": region,
        "city": city,
        "flag": flag
    }
    _IP_GEO_CACHE[ip] = (now, res)
    return res

def log_web_visit_async(ip, cf_hint, path):
    """Zaznamená návštěvu webu do lokální SQLite databáze (0% zátěž na Supabase)."""
    def _worker():
        try:
            if not ip:
                return
            now_ts = time.time()
            last_ts = _RECENT_WEB_VISITS.get(ip, 0)
            if now_ts - last_ts < 900:
                return
            _RECENT_WEB_VISITS[ip] = now_ts

            geo = resolve_ip_geo(ip, cf_hint)
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            clean_path = (path or "/").split("?")[0][:60]
            combined = f"{geo['country_code']}|{geo['country_name']}|{geo['region']}|{geo['city']}|{clean_path}"
            try:
                from local_db import local_log_web_visit
                local_log_web_visit(ip, combined, now_str)
            except Exception:
                pass
        except Exception:
            pass

    Thread(target=_worker, daemon=True).start()

@app.before_request
def track_web_visitors():
    try:
        if request.method == 'GET':
            p = request.path
            # Ignorovat assety, API, interní routy
            if not p.startswith(('/static/', '/api/', '/dashboard', '/debug', '/favicon', '/robots', '/.well-known')):
                ua = request.headers.get('User-Agent', '').lower()
                if not any(b in ua for b in ['bot', 'crawl', 'spider', 'slurp', 'mediapartners', 'lighthouse', 'headless']):
                    ip = get_real_client_ip(request)
                    cf = request.headers.get('CF-IPCountry')
                    log_web_visit_async(ip, cf, p)
    except Exception:
        pass



def _invalidate_session_cache(token=None, user_id=None):
    """Vymaže relaci nebo všechny relace daného uživatele z paměťové cache."""
    if token:
        entry = _SESSION_CACHE.pop(token, None)
        if entry and len(entry) > 1 and entry[1] and user_id is None:
            user_id = entry[1].get("id")
    if user_id is not None:
        u_id_str = str(user_id)
        keys_to_remove = [k for k, v in list(_SESSION_CACHE.items()) if v and len(v) > 1 and v[1] and str(v[1].get("id")) == u_id_str]
        for k in keys_to_remove:
            _SESSION_CACHE.pop(k, None)


def get_cached_session_user(token):
    """Vrátí uživatele podle session tokenu s 2min cache (avatar/web) a podporou více zařízení."""
    if not token:
        return None
    now = time.time()
    if token in _SESSION_CACHE:
        ts, u = _SESSION_CACHE[token]
        if now - ts < 120 and u:  # 2 minuty
            return u
    db = get_db()
    u = None
    if db:
        try:
            from session_manager import find_user_by_session_token, touch_session_activity
            u = find_user_by_session_token(db, token)
            if u:
                touch_session_activity(db, u, token)
        except Exception:
            u = None
    if not u:
        try:
            from session_manager import user_has_session_token
            for bu in _get_fallback_users():
                if user_has_session_token(bu, token):
                    u = bu
                    break
        except Exception:
            pass
    if u:
        _SESSION_CACHE[token] = (now, u)
    else:
        _SESSION_CACHE.pop(token, None)
    return u

def get_cached_setting(key, default=None, ttl=60):
    """Načte nastavení s cache (default 60s TTL)."""
    now = time.time()
    if key in _SETTINGS_CACHE:
        ts, val = _SETTINGS_CACHE[key]
        if now - ts < ttl:
            return val
    db = get_db()
    val = default
    if db:
        try:
            r = db.table("settings").select("setting_value").eq("setting_key", key).execute().data
            if r:
                val = r[0].get("setting_value", default)
        except Exception:
            pass
    _SETTINGS_CACHE[key] = (now, val)
    return val

def check_egress_quota():
    """
    Zkontroluje aktuální využití Egress přes Supabase Management API.
    Pokud přesáhne EGRESS_WARN_PCT % limitu, aktivuje EGRESS_SAVE_MODE.
    Volá se automaticky v background threadu každou hodinu.
    """
    global EGRESS_SAVE_MODE, EGRESS_USED_GB, _last_egress_check
    import urllib.request as _ur
    import json as _json

    _last_egress_check = time.time()
    org_id = "spsicrfgwjgazstohmts"  # MRWEB-DataCore org ID z emailu

    try:
        # Supabase Management API – usage metrics
        # Podpora SUPABASE_ACCESS_TOKEN (Personal Access Token začínající sbp_)
        mgmt_token = os.environ.get("SUPABASE_ACCESS_TOKEN") or SUPABASE_SERVICE_KEY or SUPABASE_KEY or ""
        if not mgmt_token:
            return

        req = _ur.Request(
            f"https://api.supabase.com/v1/organizations/{org_id}/billing/usage",
            headers={"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
        )
        with _ur.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        # Hledáme egress a log_ingestion
        egress_bytes = 0
        logs_bytes = 0
        for item in (data.get("usages") or data.get("metrics") or []):
            name = (item.get("metric") or item.get("name") or "").lower()
            if "egress" in name or "bandwidth" in name:
                egress_bytes = item.get("usage") or item.get("value") or 0
            if "log_ingestion" in name or "logs" in name:
                logs_bytes = item.get("usage") or item.get("value") or 0

        if egress_bytes: EGRESS_USED_GB = egress_bytes / (1024 ** 3)
        LOGS_USED_GB = logs_bytes / (1024 ** 3) if logs_bytes else 0

    except Exception as e:
        print(f"[QUOTA] Nepodařilo se načíst usage: {e}", flush=True)
        LOGS_USED_GB = 0

    # Rozhodnutí o šetřícím režimu
    pct = (EGRESS_USED_GB / EGRESS_LIMIT_GB * 100) if EGRESS_LIMIT_GB > 0 else 0
    logs_pct = (LOGS_USED_GB / 1.0 * 100)  # Free tier logs limit is usually 1 GB
    
    old_mode = EGRESS_SAVE_MODE
    EGRESS_SAVE_MODE = pct >= EGRESS_WARN_PCT

    # Upozorneni pro Log Ingestion
    if logs_pct > 80:
        pings = ["👑| Project Owner", "-Executive Board-", "web-sa"] if logs_pct > 95 else []
        msg = f"⚠️ **POZOR!** Supabase Log Ingestion dosáhl **{LOGS_USED_GB:.2f} GB** z 1.0 GB ({logs_pct:.1f}%)."
        send_log("🚨 Log Quota Varování", msg, 0xef4444, pings=pings)

    if EGRESS_SAVE_MODE != old_mode:
        mode_str = "AKTIVOVÁN" if EGRESS_SAVE_MODE else "DEAKTIVOVÁN"
        print(f"[EGRESS] Šetřící režim {mode_str} – využití: {EGRESS_USED_GB:.2f} GB / {EGRESS_LIMIT_GB} GB ({pct:.1f}%)", flush=True)
        # Ulož stav do settings tabulky
        try:
            db = get_db()
            if db:
                db.table("settings").upsert({
                    "setting_key": "egress_save_mode",
                    "setting_value": "true" if EGRESS_SAVE_MODE else "false"
                }).execute()
        except Exception:
            pass
            
        try:
            if EGRESS_SAVE_MODE:
                pings = ["👑| Project Owner", "-Executive Board-", "web-sa"] if pct > 90 else []
                msg = f"⚠️ **UPOZORNĚNÍ:** Supabase Egress dosáhl **{EGRESS_USED_GB:.2f} GB** z {EGRESS_LIMIT_GB} GB ({pct:.1f}%).\nSystém automaticky **AKTIVOVAL** šetřící režim (delší intervaly aktualizací)!"
                send_log("🚨 Egress Limit Varování", msg, 0xef4444, pings=pings)
            else:
                msg = f"✅ Supabase Egress klesl pod limit na **{EGRESS_USED_GB:.2f} GB** ({pct:.1f}%).\nSystém **DEAKTIVOVAL** šetřící režim (plný výkon)."
                send_log("🟢 Egress V Normě", msg, 0x10b981)
        except Exception:
            pass

    print(f"[QUOTA] Check: Egress {EGRESS_USED_GB:.2f} GB ({pct:.1f}%) | Logs {LOGS_USED_GB:.2f} GB ({logs_pct:.1f}%) – šetřící režim: {EGRESS_SAVE_MODE}", flush=True)

def _egress_monitor_loop():
    """Background thread – kontroluje stav Egress a Turso DB každou hodinu."""
    time.sleep(30)  # počkej na start
    while True:
        try:
            # 1. Automatický test zda Turso DB obnovila povolené čtení (např. 1. den v měsíci)
            try:
                import turso_db
                turso_db.probe_turso_unblock()
            except Exception:
                pass
            check_egress_quota()
        except Exception as e:
            print(f"[EGRESS MONITOR] Chyba: {e}", flush=True)
        time.sleep(_EGRESS_CHECK_INTERVAL)

# Spusť monitor v background threadu
import threading as _threading
_egress_thread = _threading.Thread(target=_egress_monitor_loop, daemon=True, name="egress-monitor")
_egress_thread.start()

def get_cached_user_role(discord_id):
    now = time.time()
    if discord_id in _AUTH_CACHE:
        cache_time, role, is_banned = _AUTH_CACHE[discord_id]
        if now - cache_time < 300: # 5 minutes cache
            return role, is_banned

    db = get_db()
    role, is_banned = 'User', False
    if db and discord_id:
        try:
            if discord_id.startswith('email-'):
                uid = discord_id.split('-')[1]
                resp = db.table('users').select('role, is_banned').eq('id', uid).execute()
            else:
                resp = db.table('users').select('role, is_banned').eq('discord_id', discord_id).execute()
            if resp and resp.data:
                role = resp.data[0].get('role', 'User')
                is_banned = resp.data[0].get('is_banned', False)
        except Exception as e:
            print('auth cache error:', e)
            
    # Bezpečný fallback na lokální users_backup.json pokud DB roli nenašla nebo selhala
    if role == 'User' and discord_id:
        try:
            for bu in _get_fallback_users():
                if str(bu.get('discord_id')) == str(discord_id) or str(bu.get('id')) == str(discord_id):
                    role = bu.get('role', 'User')
                    is_banned = bu.get('is_banned', False)
                    break
        except Exception:
            pass

    _AUTH_CACHE[discord_id] = (now, role, is_banned)
    return role, is_banned

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
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        import smtplib
        import os

        to_email = str(to_email or "").strip()
        msg = MIMEMultipart("related")
        msg["Subject"] = "Přihlášení do aplikace OIS IDPK"
        msg["From"] = f"DataCore Bot <{SMTP_EMAIL}>"
        msg["To"] = to_email

        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)

        logo_cid_available = False
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "static", "img", "datacorebot_n.png")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f_logo:
                    logo_mime = MIMEImage(f_logo.read(), _subtype="png")
                    logo_mime.add_header('Content-ID', '<datacore_logo>')
                    logo_mime.add_header('Content-Disposition', 'inline', filename='datacorebot_logo.png')
                    msg.attach(logo_mime)
                    logo_cid_available = True
        except Exception as e_l:
            print(f"[AUTH LOGO ERR] {e_l}", flush=True)

        base_url = request.url_root.rstrip('/')
        login_url = f"{base_url}/api/auth/finalize?token={token}&type=email&intent={intent}"
        
        logo_tag = '<img src="cid:datacore_logo" alt="DataCoreBot Logo" style="max-height:48px;width:auto;vertical-align:middle;border:0;display:inline-block;" />' if logo_cid_available else '<img src="https://datacorebot.koyeb.app/static/img/datacorebot_n.png" alt="DataCoreBot Logo" style="max-height:48px;width:auto;vertical-align:middle;border:0;display:inline-block;" />'

        html = f"""
        <!DOCTYPE html>
        <html>
          <head><meta charset="utf-8"></head>
          <body style="margin: 0; padding: 20px 10px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
              <div style="background: linear-gradient(135deg, #0b0f19 0%, #1e1b4b 100%); padding: 26px 20px; text-align: center; border-bottom: 2px solid #7c3aed;">
                {logo_tag}
                <div style="color: #94a3b8; font-size: 11px; margin-top: 8px; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 700;">Projekt OIS IDPK • Ověření přístupu</div>
              </div>
              <div style="padding: 30px 24px; text-align: center;">
                <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 14px; font-size: 20px; font-weight: 700;">Přihlášení do aplikace</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                  Dobrý den,<br>posíláme jednorázový odkaz pro bezpečné přihlášení do aplikace OIS IDPK.
                </p>
                <div style="margin: 26px 0;">
                  <a href="{login_url}" style="display: inline-block; background: linear-gradient(135deg, #38bdf8, #0284c7); color: #ffffff; padding: 13px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 15px; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);">
                    🚀 Potvrdit a přihlásit se
                  </a>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 20px 0; font-size: 14px; color: #334155;">
                  Nebo zadejte tento 5místný ověřovací kód: <strong style="font-size: 18px; color: #7c3aed; letter-spacing: 3px; font-family: monospace;">{token}</strong>
                </div>
                <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin-top: 24px; margin-bottom: 0;">
                  Pokud jste se k přihlášení nepřihlásili vy, můžete tento e-mail v klidu ignorovat. Váš účet zůstává chráněn.
                </p>
              </div>
              <div style="background: #f8fafc; padding: 16px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                <div>Hezký den přeje <strong>Tým DataCore Bot & Projekt OIS IDPK</strong></div>
              </div>
            </div>
          </body>
        </html>
        """
        plain = f"Dobrý den,\n\nOdkaz pro přihlášení do aplikace OIS IDPK:\n{login_url}\n\nOvěřovací kód: {token}\n\nHezký den přeje Tým Projekt OIS IDPK"
        msg_alt.attach(MIMEText(plain, "plain", "utf-8"))
        msg_alt.attach(MIMEText(html, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[AUTH] Chyba odesílání e-mailu: {e}")
        return False

class AppAuthView(discord.ui.View):
    def __init__(self, token="", discord_id="", is_dm=True):
        super().__init__(timeout=300) # 5 minutes timeout
        self.token = token
        self.discord_id = str(discord_id)
        self.is_dm = is_dm
        self.message = None

    async def on_timeout(self):
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(content="⏳ **Vypršel čas. Nedostatečná reakce.**", embed=None, view=None)
            _AUTH_TOKEN_STATUS[str(self.discord_id)] = "timeout"
            db = get_db()
            if db:
                db.table("users").update({"login_token": "timeout"}).eq("discord_id", self.discord_id).execute()
        except Exception as e:
            pass

    @discord.ui.button(label="Schválit přihlášení", style=discord.ButtonStyle.success, emoji="✅", custom_id="app_auth_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        _AUTH_TOKEN_STATUS[str(target_id)] = "approved"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="✅ **Přihlášení úspěšně schváleno!**", embed=None, view=None)
        self.stop()

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="app_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        _AUTH_TOKEN_STATUS[str(target_id)] = "rejected"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="❌ **Přihlášení bylo zamítnuto.**", embed=None, view=None)
        self.stop()

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
        _AUTH_TOKEN_STATUS[str(target_id)] = "approved"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="✅ **Přístup na webový Dashboard byl schválen!**", embed=None, view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="dash_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        _AUTH_TOKEN_STATUS[str(target_id)] = "rejected"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="❌ **Přístup na Dashboard zamítnut.**", embed=None, view=None)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or('!'),
    case_insensitive=True,
    intents=intents,
    help_command=None,
    max_messages=100
)
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
        ext = ".zip" if not version_name.endswith(".exe") else ""
        resp_headers = {
            'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name.replace(" ", "_")}{ext}"',
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

async def send_user_dm(discord_identifier, title, description, color=0x38bdf8, fields=None, view=None, is_admin_direct=False, image_url=None):
    if not discord_identifier:
        return False
    if not bot.is_ready():
        print(f"[SEND DM] Bot není připraven k odeslání DM uživateli {discord_identifier}", flush=True)
        return False
    d_str = str(discord_identifier).strip()
    try:
        user = None
        if d_str.isdigit():
            user = bot.get_user(int(d_str))
            if not user:
                try:
                    user = await bot.fetch_user(int(d_str))
                except Exception as e_fu:
                    print(f"[DM FETCH USER ERR {d_str}] {e_fu}", flush=True)
        if not user:
            for guild in bot.guilds:
                m = guild.get_member(int(d_str)) if d_str.isdigit() else None
                if not m:
                    m = discord.utils.find(
                        lambda x: x.name.lower() == d_str.lower()
                        or (x.global_name and x.global_name.lower() == d_str.lower())
                        or (getattr(x, 'nick', None) and x.nick and x.nick.lower() == d_str.lower()),
                        guild.members
                    )
                if m:
                    user = m
                    break
        if user:
            embed = discord.Embed(title=title, description=description, color=color)
            if fields:
                for f_name, f_val in fields:
                    if f_name and f_val:
                        embed.add_field(name=str(f_name), value=str(f_val)[:1024], inline=False)
            discord_file = None
            if image_url:
                try:
                    img_str = str(image_url).strip()
                    if img_str.startswith("data:image/"):
                        import base64
                        import io
                        header, b64_data = img_str.split(",", 1)
                        ext = "png"
                        if "jpeg" in header or "jpg" in header: ext = "jpg"
                        elif "webp" in header: ext = "webp"
                        elif "gif" in header: ext = "gif"
                        img_bytes = base64.b64decode(b64_data)
                        fname = f"notification_image.{ext}"
                        discord_file = discord.File(io.BytesIO(img_bytes), filename=fname)
                        embed.set_image(url=f"attachment://{fname}")
                    elif img_str.startswith("http://") or img_str.startswith("https://"):
                        try:
                            import urllib.request
                            import io
                            req = urllib.request.Request(img_str, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=5) as resp:
                                img_bytes = resp.read()
                            ext = "png"
                            if ".jpg" in img_str.lower() or ".jpeg" in img_str.lower(): ext = "jpg"
                            elif ".webp" in img_str.lower(): ext = "webp"
                            elif ".gif" in img_str.lower(): ext = "gif"
                            fname = f"notification_image.{ext}"
                            discord_file = discord.File(io.BytesIO(img_bytes), filename=fname)
                            embed.set_image(url=f"attachment://{fname}")
                        except Exception:
                            embed.set_image(url=img_str)
                except Exception as e_img:
                    print(f"[DM IMAGE ERR] {e_img}", flush=True)

            embed.set_footer(text="Projekt OIS IDPK • Centrální podpora")

            if view is None and is_admin_direct:
                try:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="ℹ️ Proč mi přišla zpráva?", url="https://datacorebot.koyeb.app/proc-notifikace?typ=admin", style=discord.ButtonStyle.link))
                    view.add_item(discord.ui.Button(label="💬 Podpora a odpověď", url="https://datacorebot.koyeb.app/podpora", style=discord.ButtonStyle.link))
                except Exception:
                    view = None

            send_kwargs = {"embed": embed}
            if discord_file:
                send_kwargs["file"] = discord_file
            if view:
                send_kwargs["view"] = view
            try:
                await user.send(**send_kwargs)
                return True
            except Exception:
                if view:
                    send_kwargs.pop("view", None)
                    try:
                        await user.send(**send_kwargs)
                        return True
                    except Exception:
                        pass
                if discord_file:
                    send_kwargs.pop("file", None)
                    try:
                        await user.send(**send_kwargs)
                        return True
                    except Exception:
                        pass
            return False
    except Exception as e_dm:
        print(f"[SEND DM ERROR for {discord_identifier}] {e_dm}", flush=True)
    return False

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

async def async_send_log(title, description, color=0x38bdf8, channel_name="🖥️・datacore-logs", pings=None, image_url=None):
    if not bot.is_ready(): return
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name=channel_name)
        if channel:
            content_str = ""
            if pings:
                roles_to_ping = []
                for r in guild.roles:
                    if r.name in pings:
                        roles_to_ping.append(r.mention)
                if roles_to_ping:
                    content_str = " ".join(roles_to_ping) + " ⚠️ **Kritické upozornění!**"
            
            embed = discord.Embed(title=title, description=description, color=color, timestamp=get_prague_time())
            discord_file = None
            if image_url:
                try:
                    img_str = str(image_url).strip()
                    if img_str.startswith("data:image/"):
                        import base64
                        import io
                        header, b64_data = img_str.split(",", 1)
                        ext = "png"
                        if "jpeg" in header or "jpg" in header: ext = "jpg"
                        elif "webp" in header: ext = "webp"
                        elif "gif" in header: ext = "gif"
                        img_bytes = base64.b64decode(b64_data)
                        fname = f"log_screenshot.{ext}"
                        discord_file = discord.File(io.BytesIO(img_bytes), filename=fname)
                        embed.set_image(url=f"attachment://{fname}")
                    elif img_str.startswith("http://") or img_str.startswith("https://"):
                        embed.set_image(url=img_str)
                except Exception as e_img:
                    print(f"[LOG IMAGE ERR] {e_img}", flush=True)

            send_kwargs = {"embed": embed}
            if content_str:
                send_kwargs["content"] = content_str
            if discord_file:
                send_kwargs["file"] = discord_file
            try:
                await channel.send(**send_kwargs)
            except Exception:
                if discord_file:
                    send_kwargs.pop("file", None)
                    try: await channel.send(**send_kwargs)
                    except: pass
            break

def send_log(title, description, color=0x38bdf8, channel_name="🖥️・datacore-logs", pings=None, image_url=None):
    try:
        b_loop = get_bot_loop()
        if bot.is_ready() and b_loop and b_loop.is_running():
            asyncio.run_coroutine_threadsafe(async_send_log(title, description, color, channel_name, pings, image_url=image_url), b_loop)
    except Exception:
        pass


def get_current_admin_name():
    """Vrátí spolehlivě nick/jméno přihlášeného administrátora pro audit logy a notifikace."""
    try:
        from flask import session, request
        # 1. Nejprve zkus session hodnoty
        for k in ('discord_nick', 'nick', 'username', 'admin_user'):
            val = session.get(k)
            if val and str(val).strip() and str(val).strip().lower() not in ('none', 'unknown', 'neznámý', 'map_admin'):
                return str(val).strip()

        # 2. Zkus najít podle discord_id v databázi
        did = session.get('discord_id')
        if did:
            try:
                db = get_db()
                if db:
                    u_res = db.table("users").select("nick, email, username").eq("discord_id", str(did)).execute().data
                    if u_res:
                        found_name = u_res[0].get("nick") or u_res[0].get("username") or u_res[0].get("email")
                        if found_name:
                            session['discord_nick'] = str(found_name).strip()
                            return str(found_name).strip()
            except Exception:
                pass
            if str(did) in ("714856037042585641", "1219661445763661854"):
                return "marekk_czz"
            return str(did)

        # 3. Zkus web_session_token z cookie
        try:
            cookie_token = request.cookies.get('web_session_token') if request else None
            if cookie_token:
                db = get_db()
                if db:
                    from session_manager import find_user_by_session_token
                    u = find_user_by_session_token(db, cookie_token)
                    if u:
                        found_name = u.get("nick") or u.get("username") or u.get("email")
                        if found_name:
                            return str(found_name).strip()
        except Exception:
            pass

        # 4. Pokud je přihlášen v session (offline mód / mapa)
        if session.get('logged_in'):
            return "marekk_czz"
    except Exception:
        pass
    return "marekk_czz"


def _cors_jsonify(data):
    return jsonify(data)

def _get_avatar_html(req):
    cookie_token = req.cookies.get('web_session_token')
    if cookie_token:
        try:
            u = get_cached_session_user(cookie_token)
            if u:

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
                <div class="user-avatar-wrap" style="position:relative; margin-left:15px; cursor:pointer; display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.05); padding:5px 15px 5px 5px; border-radius:30px; border:1px solid #334155; transition:0.3s;" onclick="toggleUserDropdown(this, event);" onmouseover="this.style.borderColor='#38bdf8'; this.style.boxShadow='0 0 10px rgba(56,189,248,0.5)';" onmouseout="this.style.borderColor='#334155'; this.style.boxShadow='none';">
                  <div class="user-avatar-circle" style="width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,0.1); border:2px solid #38bdf8; display:flex; align-items:center; justify-content:center; overflow:hidden; box-shadow: 0 0 10px rgba(56,189,248,0.5); flex-shrink:0;">
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
                  window.toggleUserDropdown = function(wrap, e) {{
                    if (e) e.stopPropagation();
                    let d = wrap.querySelector('.user-dropdown-menu');
                    if (!d) return;
                    let isVis = d.style.display === 'block';
                    document.querySelectorAll('.user-dropdown-menu').forEach(function(m) {{ m.style.display = 'none'; }});
                    if (!isVis) {{
                      d.style.display = 'block';
                      let rect = d.getBoundingClientRect();
                      if (rect.left < 8) {{
                        d.style.left = '0';
                        d.style.right = 'auto';
                      }} else if (rect.right > window.innerWidth - 8) {{
                        d.style.right = '0';
                        d.style.left = 'auto';
                      }}
                    }}
                  }};
                  if (!window._userDropdownInit) {{
                    window._userDropdownInit = true;
                    document.addEventListener('click', function(e) {{
                      if (!e.target.closest('.user-avatar-wrap')) {{
                        document.querySelectorAll('.user-dropdown-menu').forEach(function(m) {{ m.style.display = 'none'; }});
                      }}
                    }});
                  }}
                  </script>
                  
                  <div class="user-dropdown-menu" onclick="event.stopPropagation();" style="display:none; position:absolute; top:calc(100% + 10px); right:0; background:rgba(15,23,42,0.95); backdrop-filter:blur(10px); border:1px solid #334155; border-radius:10px; width:220px; box-shadow: 0 5px 20px rgba(0,0,0,0.8); z-index:9000; padding:15px; text-align:left; box-sizing:border-box;">
                    <div style="color:white; font-size:14px; font-weight:bold; margin-bottom:5px;">{display_name}</div>
                    <div style="color:#94a3b8; font-size:11px; margin-bottom:15px; word-break:break-all;">{u.get('email') or 'Neznámý e-mail'}{discord_id_text}</div>
                    <a href="/ucet" style="display:block; width:100%; box-sizing:border-box; background:#38bdf8; color:black; text-align:center; padding:8px; border-radius:6px; text-decoration:none; font-weight:bold; margin: 0 0 8px 0; white-space:nowrap;"><i class="fas fa-cog"></i> Můj Účet</a>
                    <button onclick="fetch('/api/auth/logout', {{method:'POST'}}).then(()=>location.reload())" style="display:block; width:100%; box-sizing:border-box; background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid #ef4444; padding:8px; border-radius:6px; cursor:pointer; font-weight:bold; transition:0.2s; margin:0; white-space:nowrap;" onmouseover="this.style.background='#ef4444'; this.style.color='white';" onmouseout="this.style.background='rgba(239,68,68,0.2)'; this.style.color='#ef4444';"><i class="fas fa-sign-out-alt"></i> Odhlásit se</button>
                  </div>
                </div>
                """
        except: pass
    return """
    <a href="/register" class="user-avatar-wrap" style="margin-left:15px; text-decoration:none; display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.05); padding:5px 15px 5px 5px; border-radius:30px; border:1px solid #334155; transition:0.3s;" onmouseover="this.style.borderColor='#38bdf8'; this.style.boxShadow='0 0 10px rgba(56,189,248,0.5)';" onmouseout="this.style.borderColor='#334155'; this.style.boxShadow='none';">
      <div class="user-avatar-circle" style="width:40px; height:40px; border-radius:50%; background:rgba(255,255,255,0.1); border:1px solid #94a3b8; display:flex; align-items:center; justify-content:center; overflow:hidden; transition:0.3s; flex-shrink:0;">
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
    from flask import session
    if session.get('offline_mode'):
        return session.get('dashboard_level', 'superadmin')
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
        maintenance = str(get_cached_setting('web_maintenance', 'False', ttl=60)).lower() == 'true'
        if maintenance and not is_maintenance_exempt():
            # Allow SM/SA/DEV admin bypass if logged in
            role = ""
            discord_id = session.get('discord_id')
            if session.get('logged_in') and discord_id:
                role, _ = get_cached_user_role(discord_id)
            if not any(r in role for r in ['SM', 'SA', 'DEV']):
                return redirect('/blocked')

        web_login_enabled = str(get_cached_setting('web_login_enabled', 'True', ttl=60)).lower() != 'false'
        LOGIN_PATHS = ['/register', '/login', '/api/auth/discord/request', '/api/auth/email/request']
        if not web_login_enabled and path in LOGIN_PATHS:
            if request.is_json or path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Přihlašování je z bezpečnostních důvodů dočasně nedostupné.'}), 503
            else:
                return redirect('/login_blocked')
    except:
        pass

    if path.startswith('/dashboard/') and path not in ['/dashboard/wait_auth', '/dashboard/login_finalize', '/dashboard/offline_login']:
        if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    if path.startswith('/dashboard') and path not in ['/dashboard/wait_auth', '/dashboard/login_finalize', '/dashboard/offline_login'] and session.get('logged_in'):
        if session.get('offline_mode'):
            pass # Skip Supabase checks for offline admins
        else:
            discord_id = session.get('discord_id')
            if discord_id:
                try:
                    role, is_banned = get_cached_user_role(discord_id)
                    db = get_db()
                    if db:
                        users_data = db.table("users").select("dashboard_access, is_deleted, nick, email, role, dashboard_level").eq("discord_id", discord_id).execute().data
                        if users_data:
                            user = users_data[0]
                            if not user.get("dashboard_access") or is_banned or user.get("is_deleted"):
                                session.clear()
                                flash('Váš přístup byl zablokován.', 'error')
                                return redirect(url_for('dashboard_main'))
                            if not session.get('discord_nick'):
                                session['discord_nick'] = user.get('nick') or user.get('email') or str(discord_id)
                                session['nick'] = user.get('nick')
                                session['dashboard_level'] = user.get('dashboard_level') or 'admin'
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
    try:
        if not app_version_from_pc:
            return {"allowed": False, "msg": "Verze aplikace nebyla poskytnuta."}
            
        v_resp = db.table("software_versions").select("*").eq("db_version", app_version_from_pc).execute()
        if not v_resp.data:
            # Fallback pro názvy verze (pokud někdo poslal např. V1.6 místo V1.6)
            v_resp = db.table("software_versions").select("*").eq("version_name", app_version_from_pc).execute()
            
        if not v_resp.data:
            return {"allowed": False, "msg": "Tato verze neexistuje v databázi. Spusťte hru přes oficiální Launcher."}
            
        v_data = v_resp.data[0]
        
        if not v_data.get("is_active"):
            return {"allowed": False, "msg": "Tato verze je vyřazena z provozu a již ji nelze používat."}
            
        if not v_data.get("can_launch"):
            return {"allowed": False, "msg": "Spouštění této verze je administrátorem zakázáno."}
            
        u_role = user.get('role', 'User')
        v_role = v_data.get('target_role', 'User')
        
        ROLE_HIERARCHY = {'User': 1, 'BT': 2, 'DEV': 3, 'SA': 4}
        def get_level(r):
            for k in ['SA', 'DEV', 'BT']:
                if k in r: return ROLE_HIERARCHY[k]
            return 1
            
        if get_level(u_role) < get_level(v_role):
            return {"allowed": False, "msg": f"Nemáte dostatečná oprávnění k této verzi (Vyžaduje: {v_role})."}
            
        return {"allowed": True}
    except Exception as e:
        print(f"Version check error: {e}")
        # Při chybě DB radši pustíme, abychom nezablokovali všechny při výpadku Supabase
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
@app.route('/api/client_error', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_report_error():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", "")).strip()
    nick = str(data.get("nick", "")).strip()
    error_type = str(data.get("type", "KLIENTSKÁ CHYBA (Prohlížeč)"))
    msg = str(data.get("message", "Neznámá chyba"))[:800]
    page_url = str(data.get("url", request.referrer or "")).strip()[:300]
    source = str(data.get("source", "")).strip()[:200]
    line = data.get("line")

    if not nick or not discord_id:
        try:
            tok = request.cookies.get("web_session_token") or request.cookies.get("admin_session_token")
            u = get_cached_session_user(tok) if tok else None
            if u:
                nick = u.get("nick") or nick or "Přihlášený uživatel"
                discord_id = u.get("discord_id") or discord_id or "-"
        except Exception:
            pass

    user_label = f"**{nick or 'Návštěvník'}** (`{discord_id or 'Bez Discord ID'}`)"
    log_content = f"**Uživatel:** {user_label}\n"
    if page_url:
        log_content += f"**URL:** `{page_url}`\n"
    if source:
        loc_str = f"{source}:{line}" if line else source
        log_content += f"**Místo:** `{loc_str}`\n"
    log_content += f"**Chyba:**\n`{msg}`"

    try:
        from daily_reporter import TRACKER
        TRACKER.record_client_error()
    except Exception:
        pass

    send_log(f"⚠️ APLIKAČNÍ CHYBA: {error_type}", log_content, 0xef4444, "📲・error-app")
    return _cors_jsonify({"status": "success"})

@app.route('/api/keepalive', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_keepalive():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    return _cors_jsonify({"status": "ok", "message": "Server is running"})

@app.route('/api/egress_status', methods=['GET'])
def api_egress_status():
    """Vrátí aktuální stav Egress kvóty (pro admin dashboard)."""
    pct = (EGRESS_USED_GB / EGRESS_LIMIT_GB * 100) if EGRESS_LIMIT_GB > 0 else 0
    return _cors_jsonify({
        "egress_used_gb": round(EGRESS_USED_GB, 3),
        "egress_limit_gb": EGRESS_LIMIT_GB,
        "egress_pct": round(pct, 1),
        "save_mode": EGRESS_SAVE_MODE,
        "warn_pct": EGRESS_WARN_PCT,
        "last_check": _last_egress_check,
    })

@app.route('/api/egress_set', methods=['POST'])
def api_egress_set():
    """Ruční nastavení egress hodnot (SA only)."""
    cookie_token = request.cookies.get('web_session_token')
    if not cookie_token:
        return jsonify({"error": "Unauthorized"}), 403
    u = get_cached_session_user(cookie_token)
    if not u or 'SA' not in (u.get('role') or ''):
        return jsonify({"error": "Unauthorized"}), 403
    global EGRESS_USED_GB, EGRESS_LIMIT_GB, EGRESS_WARN_PCT, EGRESS_SAVE_MODE
    data = request.get_json(silent=True) or {}
    if 'used_gb' in data:
        EGRESS_USED_GB = float(data['used_gb'])
        # Ulož do settings jako fallback
        try:
            db = get_db()
            if db:
                db.table("settings").upsert({"setting_key": "egress_used_gb", "setting_value": str(EGRESS_USED_GB)}).execute()
        except Exception: pass
    if 'limit_gb' in data:
        EGRESS_LIMIT_GB = float(data['limit_gb'])
    if 'warn_pct' in data:
        EGRESS_WARN_PCT = float(data['warn_pct'])
    if 'save_mode' in data:
        EGRESS_SAVE_MODE = bool(data['save_mode'])
    # Znovu vyhodnoť
    pct = (EGRESS_USED_GB / EGRESS_LIMIT_GB * 100) if EGRESS_LIMIT_GB > 0 else 0
    EGRESS_SAVE_MODE = pct >= EGRESS_WARN_PCT
    return jsonify({"status": "ok", "save_mode": EGRESS_SAVE_MODE, "pct": round(pct, 1)})

@app.route('/api/submit_stats', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_submit_stats():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    raw_line = str(data.get("line", "")).strip()
    stops = data.get("stops", [])
    discord_id = str(data.get("discord_id", "")).strip()
    if not raw_line:
        return _cors_jsonify({"status": "error", "message": "Chybí parametr linky."})
    
    # ── Vždy normalizovat na oficiální 6místné licenční číslo (např. '734' -> '490734')
    line = normalize_line_number(raw_line)
    
    # ── Deduplikace požadavků (proti násobnému odeslání z klienta - IPC + Beacon + fetch)
    trip_uid = str(data.get("trip_uid", "")).strip()
    if trip_uid:
        dedup_key = f"uid:{trip_uid}"
    else:
        # Fallback deduplikace podle hráče, linky a přesného seznamu zastávek v okně 30 sekund
        stops_sig = ",".join(str(s).strip() for s in (stops or []))
        dedup_key = f"sig:{discord_id}:{line}:{stops_sig}"
    
    now_ts = time.time()
    with _STATS_DEDUP_LOCK:
        # Promazat staré záznamy (starší než 60 sekund)
        expired = [k for k, ts in _STATS_DEDUP_CACHE.items() if now_ts - ts > 60]
        for k in expired:
            _STATS_DEDUP_CACHE.pop(k, None)
        
        if dedup_key in _STATS_DEDUP_CACHE and (now_ts - _STATS_DEDUP_CACHE[dedup_key] < 30):
            print(f"[STATS DEDUP] Ignorován duplicitní záznam pro linku {line} ({dedup_key})", flush=True)
            return _cors_jsonify({"status": "duplicate_ignored", "line": line, "message": "Statistika již byla započtena."})
        
        _STATS_DEDUP_CACHE[dedup_key] = now_ts

    from collections import Counter
    # Spočítáme počet vyhlášení každé zastávky na tomto spoji (např. 2x vyhlášená stejná zastávka = 2x vyhlášení)
    stop_counts = Counter(str(s).strip() for s in (stops or []) if str(s).strip())
    
    # 1. Lokální 100% spolehlivý zápis do SQLite (nezávislý na RLS v Supabase)
    try:
        from local_db import local_record_stats
        local_record_stats(line, stops, discord_id)
    except Exception as e_loc:
        print(f"[STATS] Chyba lokálního zápisu: {e_loc}", flush=True)

    # 2. Pokus o zápis do Supabase (pokud je dostupný a povolený)
    db = get_db()
    if db:
        try:
            line_res = db.table("stats_lines").select("*").eq("line_name", line).execute().data
            if line_res: db.table("stats_lines").update({"play_count": int(line_res[0].get("play_count", 0)) + 1}).eq("id", line_res[0]["id"]).execute()
            else: db.table("stats_lines").insert({"line_name": line, "play_count": 1}).execute()
        except Exception as e_sb1:
            print(f"[STATS] Supabase stats_lines (RLS nebo chyba): {e_sb1}", flush=True)

        for stop_name, cnt in stop_counts.items():
            try:
                stop_res = db.table("stats_stops").select("*").eq("stop_name", stop_name).execute().data
                if stop_res: db.table("stats_stops").update({"announce_count": int(stop_res[0].get("announce_count", 0)) + cnt}).eq("id", stop_res[0]["id"]).execute()
                else: db.table("stats_stops").insert({"stop_name": stop_name, "announce_count": cnt}).execute()
            except Exception as e_sb2:
                pass

        if discord_id and discord_id not in ("None", ""):
            try:
                u_line_res = db.table("user_stats_lines").select("*").eq("discord_id", discord_id).eq("line_name", line).execute().data
                if u_line_res: db.table("user_stats_lines").update({"play_count": int(u_line_res[0].get("play_count", 0)) + 1}).eq("id", u_line_res[0]["id"]).execute()
                else: db.table("user_stats_lines").insert({"discord_id": discord_id, "line_name": line, "play_count": 1}).execute()
            except Exception as e_sb3:
                pass

            for stop_name, cnt in stop_counts.items():
                try:
                    u_stop_res = db.table("user_stats_stops").select("*").eq("discord_id", discord_id).eq("stop_name", stop_name).execute().data
                    if u_stop_res: db.table("user_stats_stops").update({"announce_count": int(u_stop_res[0].get("announce_count", 0)) + cnt}).eq("id", u_stop_res[0]["id"]).execute()
                    else: db.table("user_stats_stops").insert({"discord_id": discord_id, "stop_name": stop_name, "announce_count": cnt}).execute()
                except Exception as e_sb4:
                    pass

    return _cors_jsonify({"status": "success", "line": line, "stops_recorded": sum(stop_counts.values())})


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

# Paměťová cache aktivních tokenů pro stažení Launcheru (TTL 2 hodiny)
LAUNCHER_TOKENS = {}

def get_launcher_user(token):
    """Získá uživatele pro stažení Launcheru - kontroluje paměťovou cache, DB i přihlášenou webovou relaci."""
    if not token:
        return None
    token = str(token).strip()

    # 1. Kontrola v paměťové cache
    entry = LAUNCHER_TOKENS.get(token)
    if entry:
        if time.time() <= entry.get("expires_at", 0):
            return entry
        else:
            LAUNCHER_TOKENS.pop(token, None)

    # 2. Kontrola v databázi users
    db = get_db()
    if db:
        try:
            res = db.table("users").select("*").eq("download_token", token).execute().data
            if res:
                u = res[0]
                LAUNCHER_TOKENS[token] = {
                    "discord_id": str(u.get("discord_id", "")),
                    "nick": u.get("nick") or "Uživatel",
                    "is_banned": bool(u.get("is_banned")),
                    "created_at": time.time(),
                    "expires_at": time.time() + 7200
                }
                return u
        except Exception as e_lk:
            print(f"[LAUNCHER TOKEN DB LOOKUP ERR] {e_lk}", flush=True)

    # 3. Fallback na přihlášeného uživatele v prohlížeči
    try:
        tok = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
        if tok:
            u = get_cached_session_user(tok)
            if u:
                return u
    except Exception:
        pass

    return None

@app.route('/download-launcher')
def page_download_launcher_direct():
    token = request.args.get('token')
    if token:
        return redirect(f"/launcher-page/{token}")

    cookie_token = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
    u = get_cached_session_user(cookie_token) if cookie_token else None
    if u and not u.get('is_banned'):
        import uuid
        tok = str(uuid.uuid4())
        LAUNCHER_TOKENS[tok] = {
            "discord_id": str(u.get("discord_id", "")),
            "nick": u.get("nick") or "Uživatel",
            "is_banned": False,
            "created_at": time.time(),
            "expires_at": time.time() + 7200
        }
        db = get_db()
        if db:
            try:
                db.table("users").update({"download_token": tok}).eq("id", u["id"]).execute()
            except Exception:
                pass
        return redirect(f"/launcher-page/{tok}")

    return render_public("""
    <div style="max-width: 580px; margin: 60px auto; padding: 30px; background: rgba(15,23,42,0.85); backdrop-filter: blur(12px); border: 1px solid rgba(56,189,248,0.3); border-radius: 16px; text-align: center; color: white;">
      <i class="fas fa-rocket" style="font-size: 3rem; color: #38bdf8; margin-bottom: 16px;"></i>
      <h2 style="color: #38bdf8; margin: 0 0 10px 0;">Stažení IDPK Launcheru</h2>
      <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
        Instalátor Launcheru je chráněn unikátním ověřovacím odkazem. Stažení zahájíte jednoduše na našem Discord serveru v sekci <strong>#stáhnout-hru</strong> kliknutím na tlačítko <em>Zahájit instalaci Launcheru</em>.
      </p>
      <div style="margin-top: 24px; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
        <a href="https://discord.gg/idpk" target="_blank" style="padding: 10px 20px; background: #5865F2; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px; display: inline-flex; align-items: center; gap: 8px;">
          <i class="fab fa-discord"></i> Otevřít Discord
        </a>
        <a href="/ucet" style="padding: 10px 20px; background: #1e293b; border: 1px solid #334155; color: #38bdf8; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px;">
          Přihlásit se na webu
        </a>
      </div>
    </div>
    """)

@app.route('/launcher-page/<token>')
def launcher_page(token):
    user = get_launcher_user(token)
    if not user:
        return render_public("""
        <div style="max-width: 600px; margin: 60px auto; padding: 35px; background: rgba(15,23,42,0.85); backdrop-filter: blur(14px); border: 1px solid rgba(239,68,68,0.4); border-radius: 16px; text-align: center; color: white; box-shadow: 0 10px 40px rgba(0,0,0,0.6);">
          <div style="font-size: 3rem; color: #ef4444; margin-bottom: 16px;"><i class="fas fa-exclamation-triangle"></i></div>
          <h2 style="color: #f87171; margin-top: 0;">Neplatný nebo expirovaný odkaz</h2>
          <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
            Tento odkaz ke stažení Launcheru již vypršel nebo je neplatný.<br>
            Nový odkaz si můžete kdykoliv zdarma vygenerovat na Discordu v kanálu <strong>#stáhnout-hru</strong> kliknutím na tlačítko <em>Zahájit instalaci Launcheru</em>.
          </p>
          <div style="margin-top: 25px; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
            <a href="https://discord.gg/idpk" target="_blank" style="padding: 10px 20px; background: #5865F2; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px; display: inline-flex; align-items: center; gap: 8px;">
              <i class="fab fa-discord"></i> Přejít na Discord
            </a>
            <a href="/podpora" style="padding: 10px 20px; background: #1e293b; border: 1px solid #334155; color: #38bdf8; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px;">
              Podpora a dotazy
            </a>
          </div>
        </div>
        """), 403
    if user.get('is_banned'):
        return render_public("""
        <div style="max-width: 600px; margin: 60px auto; padding: 35px; background: rgba(15,23,42,0.85); backdrop-filter: blur(14px); border: 1px solid rgba(239,68,68,0.4); border-radius: 16px; text-align: center; color: white;">
          <h2 style="color: #ef4444; margin-top: 0;">⛔ Přístup zamítnut</h2>
          <p style="color: #94a3b8;">Váš účet má aktivní BAN. Stažení Launcheru není povoleno.</p>
        </div>
        """), 403

    content = f"""
    <div style="text-align: center; margin-top: 60px; padding: 40px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border-radius: 16px; max-width: 600px; margin-left: auto; margin-right: auto; border: 1px solid rgba(56, 189, 248, 0.3); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div id="icon-container" style="transition: all 0.5s ease;">
            <i class="fas fa-rocket" id="main-icon" style="font-size: 4rem; color: #38bdf8; margin-bottom: 20px; animation: bounce 2s infinite;"></i>
        </div>
        <h1 id="main-title" style="color: white; font-size: 2.2rem; margin-bottom: 15px;">Příprava ke stažení...</h1>
        <p id="main-desc" style="color: #94a3b8; font-size: 1.1rem; margin-bottom: 25px;">
            Váš unikátní ověřený odkaz je připraven.
        </p>
        
        <div id="progress-bar-container" style="width: 100%; height: 10px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; margin-bottom: 25px;">
            <div id="progress-bar" style="width: 0%; height: 100%; background: #38bdf8; transition: width 0.1s linear;"></div>
        </div>

        <div id="success-msg" style="display: none; padding: 20px; background: rgba(16, 185, 129, 0.1); border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">
            <p style="color: #10b981; font-weight: bold; font-size: 1.1rem; margin: 0;">
                ✅ Stahování bylo zahájeno!
            </p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-top: 10px; margin-bottom: 15px;">
                Pokud se stahování nespustilo automaticky, klikněte na tlačítko níže:
            </p>
            <a href="/api/download-launcher/{token}" id="manual-dl-btn" style="display:inline-flex; align-items:center; gap:8px; padding:12px 24px; background:#0284c7; color:white; border-radius:8px; text-decoration:none; font-weight:bold; font-size:14px;">
              <i class="fas fa-download"></i> Stáhnout IDPK Launcher přímo
            </a>
        </div>

        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
            <p style="color: #64748b; font-size: 0.85rem; line-height: 1.5; margin:0;">
                <i class="fas fa-shield-alt" style="color: #10b981;"></i> Zabezpečeno ověřovacím tokenem.<br>
                Platnost odkazu je 2 hodiny pro vaše zařízení.
            </p>
        </div>
    </div>
    
    <style>
        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        @keyframes flyAway {{
            0% {{ transform: translateY(0) scale(1); opacity: 1; }}
            100% {{ transform: translateY(-100px) scale(0.5); opacity: 0; }}
        }}
        @keyframes popIn {{
            0% {{ transform: scale(0); opacity: 0; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}
    </style>

    <script>
        setTimeout(() => {{
            let w = 0;
            let intv = setInterval(() => {{
                w += 4;
                document.getElementById('progress-bar').style.width = w + '%';
                if(w >= 100) {{
                    clearInterval(intv);
                    
                    document.getElementById('main-icon').style.animation = 'flyAway 0.4s forwards';
                    
                    setTimeout(() => {{
                        document.getElementById('icon-container').innerHTML = '<i class="fas fa-check-circle" style="font-size: 4rem; color: #10b981; margin-bottom: 20px; animation: popIn 0.4s forwards;"></i>';
                        document.getElementById('main-title').innerText = 'Připraveno ke stažení';
                        document.getElementById('main-desc').innerText = 'Soubor byl ověřen a stahování začíná.';
                        document.getElementById('progress-bar-container').style.display = 'none';
                        document.getElementById('success-msg').style.display = 'block';
                        
                        setTimeout(() => {{
                            window.location.href = '/api/download-launcher/{token}';
                        }}, 600);
                    }}, 400);
                }}
            }}, 25);
        }}, 300);
    </script>
    """
    return render_public(content)

@app.route('/api/download-launcher/<token>')
def api_download_launcher(token):
    user = get_launcher_user(token)
    if not user:
        return "Neplatný nebo expirovaný token.", 403
    if user.get('is_banned'):
        return "Přístup zamítnut: Máte BAN.", 403

    # Výchozí spolehlivá adresa na GitHub Release instalátoru Launcheru
    launcher_url = "https://github.com/marek-1cz/IDPK-Palubni-Pocitac/releases/download/V1.6.2B/IDPK.Launcher.Setup.1.6.2.exe"
    db = get_db()
    if db:
        try:
            url_setting = db.table("settings").select("setting_value").eq("setting_key", "launcher_download_url").execute().data
            if url_setting and url_setting[0].get('setting_value'):
                val = str(url_setting[0]['setting_value']).strip()
                # Použít nastavenou URL pouze pokud je to přímý odkaz na soubor (ne obecná stránka /releases)
                if val and (val.endswith('.exe') or val.endswith('.zip') or '/download/' in val):
                    launcher_url = val
        except Exception:
            pass

    filename = launcher_url.split('/')[-1] if '/' in launcher_url else "IDPK.Launcher.Setup.1.6.2.exe"
    discord_id = str(user.get('discord_id', ''))
    nick = str(user.get('nick', 'Uživatel'))

    # Zaznamenat do download logů
    if db and discord_id:
        try:
            db.table("download_logs").insert({
                "discord_id": discord_id,
                "version_name": f"Launcher ({filename})",
                "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M:%S")
            }).execute()
        except Exception:
            pass

    return stream_proxy_file(launcher_url, filename, discord_id, nick)

# ═══════════════════════════════════════════════════════════════════════════════
# HLAVNÍ WEB (NOVÝ WEB NA / PRO ADMIN BYPASS, JINAK PŘESMĚROVÁNÍ NA /old)
# ═══════════════════════════════════════════════════════════════════════════════

ADMIN_BYPASS_BAR = """
<!-- Admin Web Bypass Toolbar -->
<div id="admin-bypass-bar" style="position:fixed; bottom:20px; right:20px; z-index:9999999; background:rgba(15,23,42,0.95); backdrop-filter:blur(12px); border:1.5px solid #38bdf8; box-shadow:0 10px 35px rgba(0,0,0,0.8), 0 0 20px rgba(56,189,248,0.4); border-radius:50px; padding:10px 20px; display:flex; align-items:center; gap:14px; font-family:system-ui,-apple-system,sans-serif; font-size:13px; color:#fff;">
  <span style="display:inline-flex; align-items:center; gap:8px; color:#38d6ff; font-weight:700;">
    <span style="width:10px; height:10px; border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981; display:inline-block;"></span> Nový Web (Admin Bypass)
  </span>
  <span style="color:#475569;">|</span>
  <a href="/dashboard" style="color:#e2e8f0; text-decoration:none; display:inline-flex; align-items:center; gap:5px; font-weight:600;" onmouseover="this.style.color='#38bdf8'" onmouseout="this.style.color='#e2e8f0'">
    🔒 Dashboard
  </a>
  <span style="color:#475569;">|</span>
  <a href="/dashboard/exit_new_web" style="color:#f59e0b; text-decoration:none; display:inline-flex; align-items:center; gap:5px; font-weight:600;" onmouseover="this.style.color='#fcd34d'" onmouseout="this.style.color='#f59e0b'">
    🔄 Přepnout na /old
  </a>
</div>
"""

def is_admin_bypass_active():
    """Vrátí True pouze pokud má přihlášený administrátor aktivní Admin Web Bypass."""
    # 1. URL parametr ?admin_bypass=1 nebo ?bypass=1
    bypass_arg = request.args.get('admin_bypass') == '1' or request.args.get('bypass') == '1'
    if bypass_arg:
        if session.get('logged_in') or session.get('offline_mode'):
            session['admin_web_bypass'] = True
            return True
        cookie_token = request.cookies.get('web_session_token')
        if cookie_token:
            u = get_cached_session_user(cookie_token)
            if u and (any(r in (u.get('role') or '') for r in ['SA', 'DEV', 'SM']) or u.get('dashboard_access')):
                session['admin_web_bypass'] = True
                return True

    # 2. Stav v session (pouze pokud je uživatel admin)
    if session.get('admin_web_bypass'):
        if session.get('logged_in') or session.get('offline_mode'):
            return True
        cookie_token = request.cookies.get('web_session_token')
        if cookie_token:
            u = get_cached_session_user(cookie_token)
            if u and (any(r in (u.get('role') or '') for r in ['SA', 'DEV', 'SM']) or u.get('dashboard_access')):
                return True

    return False

@app.route('/')
def home():
    try:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(curr_dir, "new_web.html")
        if not os.path.exists(path):
            path = "new_web.html"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if is_admin_bypass_active():
            content = content.replace("</body>", f"{ADMIN_BYPASS_BAR}\n</body>")
        return Response(content, mimetype="text/html; charset=utf-8")
    except Exception as e:
        print(f"[NEW WEB HOME ERROR] {e}", flush=True)
        flash(f"Chyba při načítání nového webu: {e}", "error")
        return redirect('/old', code=302)

@app.route('/dashboard/view_new_web')
def dashboard_view_new_web():
    if not session.get('logged_in') and not session.get('offline_mode'):
        cookie_token = request.cookies.get('web_session_token')
        u = get_cached_session_user(cookie_token) if cookie_token else None
        if not u or not (any(r in (u.get('role') or '') for r in ['SA', 'DEV', 'SM']) or u.get('dashboard_access')):
            flash("Přístup povolen pouze pro přihlášené administrátory.", "warning")
            return redirect('/dashboard')
    session['admin_web_bypass'] = True
    return redirect('/?admin_bypass=1')

@app.route('/dashboard/exit_new_web')
def dashboard_exit_new_web():
    session['admin_web_bypass'] = False
    return redirect('/old')

@app.route('/dashboard/toggle_web_bypass')
def dashboard_toggle_web_bypass():
    cur = session.get('admin_web_bypass', False)
    session['admin_web_bypass'] = not cur
    if session['admin_web_bypass']:
        return redirect('/?admin_bypass=1')
    return redirect('/old')

@app.route('/download')
def redirect_download():
    return redirect('/#/download')

@app.route('/team')
def redirect_team():
    return redirect('/#/team')

@app.route('/supporters')
def redirect_supporters():
    return redirect('/#/supporters')

@app.route('/stats', methods=['GET'])
def redirect_stats():
    return redirect('/#/stats')

@app.route('/provoz')
@app.route('/provoz-idpk')
def redirect_provoz_idpk():
    return redirect('/#/provoz')

@app.route('/jizdni-rad')
def redirect_jizdni_rad():
    return redirect('/old/jizdni-rad', code=302)

@app.route('/led-panel')
def redirect_led_panel():
    return redirect('/old/led-panel', code=302)

@app.route('/led-panel/app')
def redirect_led_panel_app():
    return redirect('/old/led-panel/app', code=302)

@app.route('/led-panel/view')
def redirect_led_panel_view():
    return redirect('/old/led-panel/view', code=302)


# ═══════════════════════════════════════════════════════════════════════════════
# STARÝ WEB (URL: https://datacorebot.koyeb.app/old/"názvy slidů")
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/old')
@app.route('/old/')
def old_home():
    return render_public(HTML_HOME)

@app.route('/old/download')
def old_download_home():
    return render_public(HTML_DOWNLOADS_MAIN)

@app.route('/old/team')
def old_team():
    try: team_members = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except: team_members = []
    return render_public(HTML_TEAM, team=team_members)

@app.route('/old/supporters')
def old_supporters():
    support_data = []
    try:
        db = get_db()
        if db:
            data = db.table("supporters").select("*").eq("status", "completed").execute().data or []
            support_data = process_supporters(data)
    except: pass
    return render_public(HTML_SUPPORTERS, supporters=support_data)

@app.route('/old/provoz-idpk')
def old_provoz_idpk():
    """Rozcestník Provoz IDPK — Interaktivní mapa & Databáze autobusů"""
    return render_public(HTML_PROVOZ_IDPK)

@app.route('/old/jizdni-rad')
def old_jizdni_rad():
    """Veřejný jízdní řád IDPK z GTFS dat"""
    from jizdni_rad import HTML_JIZDNI_RAD
    return HTML_JIZDNI_RAD

@app.route('/old/led-panel')
def old_led_panel_landing():
    from led_panel_html import HTML_LED_PANEL
    return HTML_LED_PANEL

@app.route('/old/led-panel/app')
def old_led_panel_app():
    from led_panel_html import HTML_LED_PANEL
    return HTML_LED_PANEL

@app.route('/old/led-panel/view')
def old_led_panel_view():
    from led_panel_view import HTML_LED_PANEL_VIEW
    return HTML_LED_PANEL_VIEW


# ═══════════════════════════════════════════════════════════════════════════════
# GTFS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/gtfs-info')
def api_gtfs_info():
    """Vrátí info o aktuální verzi GTFS dat (verze, platnost)"""
    try:
        db = get_db()
        if not db:
            return jsonify({"error": "DB nedostupná"}), 503
        data = db.table("gtfs_feed_versions").select("version_tag,created_at,stop_count,route_count,trip_count").order("id", desc=True).limit(1).execute().data
        if data:
            return jsonify(data[0])
        return jsonify({"version_tag": "neznámá"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gtfs-db-url')
def api_gtfs_db_url():
    """Proxy the GTFS DB download to avoid CORS issues"""
    import urllib.request
    from flask import Response
    try:
        url = 'https://github.com/marek-1cz/DataCoreBot/releases/latest/download/gtfs_stops_idpk.db'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        
        def generate():
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
                
        return Response(generate(), content_type=response.headers.get('content-type', 'application/octet-stream'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gtfs-line-updates')
def api_gtfs_line_updates():
    """Vrátí seznam posledně změněných IDPK linek"""
    try:
        db = get_db()
        if not db:
            return jsonify([]), 503
        data = db.table("gtfs_line_updates").select("route_id,hash,last_updated_at").order("last_updated_at", desc=True).limit(50).execute().data
        return jsonify(data or [])
    except Exception as e:
        return jsonify([]), 500


# /mapa je zpracovávána blueprintem z interaktivnimapa.py (mapa_bp)

@app.route('/old/stats', methods=['GET'])
def public_stats():
    db = get_db()
    if not db:
        flash("Databáze není dostupná.", "error")
        return redirect('/old')
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

@app.route('/old/<path:subpath>')
def old_catchall(subpath):
    return redirect('/old', code=302)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    now = time.time()
    if _SUPPORTERS_CACHE["data"] and (now - _SUPPORTERS_CACHE["ts"] < 300):
        return _cors_jsonify({"supporters": _SUPPORTERS_CACHE["data"]})
    try:
        db = get_db()
        data = []
        if db and not EGRESS_SAVE_MODE:
            try:
                data = db.table("supporters").select("name, amount, message, created_at").eq("status", "completed").execute().data or []
            except Exception:
                pass
        if data:
            support_data = process_supporters(data)
            _SUPPORTERS_CACHE["ts"] = now
            _SUPPORTERS_CACHE["data"] = support_data
            try:
                with open(_SUPPORTERS_BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(support_data, f, ensure_ascii=False, indent=2)
            except Exception: pass
            return _cors_jsonify({"supporters": support_data})
    except Exception:
        pass

    fallback = _get_fallback_supporters()
    if fallback:
        _SUPPORTERS_CACHE["ts"] = now
        _SUPPORTERS_CACHE["data"] = fallback
        return _cors_jsonify({"supporters": fallback})
    return _cors_jsonify({"supporters": []})

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
        try:
            if db:
                set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
                if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
                    return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
        except Exception:
            pass

        client_ip_raw = request.headers.get('X-Forwarded-For', request.remote_addr)
        client_ip = client_ip_raw.split(',')[0].strip() if client_ip_raw else "Neznámá"
        
        user = None
        if db:
            try:
                if identifier.isdigit():
                    if len(identifier) < 10:
                        user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},app_id.eq.{int(identifier)}").execute()
                    else:
                        user_resp = db.table("users").select("*").eq("discord_id", identifier).execute()
                else:
                    user_resp = db.table("users").select("*").eq("nick", identifier).execute()
                if user_resp and user_resp.data:
                    user = user_resp.data[0]
            except Exception as dbe:
                print(f"[AUTH FALLBACK] Supabase fetch failed in app_login: {dbe}", flush=True)

        if not user:
            for u in _get_fallback_users():
                if identifier.isdigit():
                    if str(u.get("discord_id")) == identifier or str(u.get("app_id")) == identifier:
                        user = u
                        break
                else:
                    if str(u.get("nick", "")).lower() == identifier.lower():
                        user = u
                        break

        if not user:
            return _cors_jsonify({"status": "error", "message": "Toto ID neexistuje. Jestli problém přetrvává, jděte na náš Discord."})
            
        discord_id = str(user.get("discord_id"))
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
                try:
                    if db: db.table("users").update({"hwid": req_hwid, "ip_address": client_ip}).eq("discord_id", discord_id).execute()
                except Exception: pass
        else:
            if str(db_hwid) != req_hwid:
                if db_ip and str(db_ip).strip() != "" and db_ip == client_ip:
                    try:
                        if db: db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                    except Exception: pass
                else:
                    return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID: Váš počítač ani IP adresa nesouhlasí."})
            else:
                if not db_ip or str(db_ip).strip() == "":
                    try:
                        if db: db.table("users").update({"ip_address": client_ip}).eq("discord_id", discord_id).execute()
                    except Exception: pass
        
        token = str(uuid.uuid4())
        _AUTH_TOKEN_STATUS[discord_id] = "waiting"
        try:
            if db: db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
        except Exception: pass

        async def send():
            try:
                u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                if u:
                    view = AppAuthView(token, discord_id, is_dm=True)
                    msg = await u.send(embed=discord.Embed(title="🛡️ Ověření přihlášení", description=f"Pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPotvrďte přístup tlačítkem níže.", color=0x38bdf8), view=view)
                    view.message = msg
            except: pass
        try:
            if hasattr(bot, 'is_ready') and bot.is_ready() and bot.loop:
                asyncio.run_coroutine_threadsafe(send(), bot.loop)
        except Exception: pass
        return _cors_jsonify({"status": "waiting", "discord_id": discord_id})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    
    mem_status = _AUTH_TOKEN_STATUS.get(discord_id)
    
    user = None
    db = get_db()
    if db:
        try:
            user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
            if user_resp.data:
                user = user_resp.data[0]
        except Exception:
            pass
            
    if not user:
        for u in _get_fallback_users():
            if str(u.get("discord_id")) == discord_id:
                user = u
                break

    if not user: return _cors_jsonify({"status": "error"})
    
    if mem_status == "approved":
        _AUTH_TOKEN_STATUS.pop(discord_id, None)
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "success", "display_name": user.get("nick"), "app_id": str(user.get("app_id", "")), "roles": [user.get("role", "User")]})
    elif mem_status == "rejected":
        _AUTH_TOKEN_STATUS.pop(discord_id, None)
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."})
    elif mem_status == "timeout":
        _AUTH_TOKEN_STATUS.pop(discord_id, None)
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "timeout", "message": "Čas vypršel (nedostatečná reakce). Zkuste to prosím znovu."})
        
    t = user.get("login_token")
    if t == "approved":
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "success", "display_name": user.get("nick"), "app_id": str(user.get("app_id", "")), "roles": [user.get("role", "User")]})
    elif t == "rejected":
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."})
    elif t == "timeout":
        try:
            if db: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
        except Exception: pass
        return _cors_jsonify({"status": "timeout", "message": "Čas vypršel (nedostatečná reakce). Zkuste to prosím znovu."})

    return _cors_jsonify({"status": "pending"})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS': return _cors_jsonify({})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    app_version = str(data.get("app_version", ""))
    db = get_db()
    try:
        try:
            if db:
                set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
                if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
                    return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
        except Exception:
            pass

        client_ip_raw = request.headers.get('X-Forwarded-For', request.remote_addr)
        client_ip = client_ip_raw.split(',')[0].strip() if client_ip_raw else "Neznámá"
        
        user = None
        if db:
            try:
                user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
                if user_resp.data:
                    user = user_resp.data[0]
            except Exception as dbe:
                print(f"[AUTH FALLBACK] Supabase fetch failed in silent_check: {dbe}", flush=True)

        if not user:
            for u in _get_fallback_users():
                if str(u.get("discord_id")) == discord_id:
                    user = u
                    break

        if not user: return _cors_jsonify({"status": "error", "message": "Tento účet neexistuje."})
        if user.get("is_banned"): return _cors_jsonify({"status": "error", "message": "Tento účet má BAN."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán."})
        version_check = check_version_access(db, app_version, user)
        if not version_check["allowed"]: return _cors_jsonify({"status": "error", "message": version_check["msg"]})
        db_hwid = user.get("hwid")
        db_ip = user.get("ip_address")
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                try:
                    if db: db.table("users").update({"hwid": req_hwid, "ip_address": client_ip}).eq("discord_id", discord_id).execute()
                except Exception: pass
                return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Chyba čtení PC."})
        if str(db_hwid) != req_hwid:
            if db_ip and str(db_ip).strip() != "" and str(db_ip) == client_ip:
                try:
                    if db: db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                except Exception: pass
                return _cors_jsonify({"status": "success", "app_id": str(user.get("app_id", ""))})
            else:
                return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID/IP: Nesouhlasí."})
        else:
            if not db_ip or str(db_ip).strip() == "":
                try:
                    if db: db.table("users").update({"ip_address": client_ip}).eq("discord_id", discord_id).execute()
                except Exception: pass
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
            user_resp = db.table("users").select("launch_count, total_time, discord_id, role").eq("id", user_id).execute()
        else:
            user_resp = db.table("users").select("launch_count, total_time, discord_id, role").eq("discord_id", discord_id).execute()
        
        if not user_resp.data: return _cors_jsonify({"status": "error", "reason": "not_found"})
        updates = {"last_active": now_str, "is_online": True}
        if action == "start":
            updates["launch_count"] = (user_resp.data[0].get("launch_count") or 0) + 1
            new_session_id = str(uuid.uuid4())
            db.table("app_sessions").insert({"session_id": new_session_id, "discord_id": discord_id, "start_time": now_str, "end_time": now_str}).execute()
            if discord_id.startswith("email-"):
                db.table("users").update(updates).eq("id", user_id).execute()
            else:
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "ok", "session_id": new_session_id, "roles": [user_resp.data[0].get("role", "User")]})
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
    except Exception as e: return _cors_jsonify({"status": "error", "reason": "db_error", "message": str(e)})


@app.route('/api/auth/offline_login', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_offline_login():
    """Nouzové přihlášení admin účtu (offline_admins.json) - funguje pouze když Supabase je nedostupná."""
    if request.method == 'OPTIONS': return _cors_jsonify({})
    # Pokud je Supabase DOSTUPNA, offline login odmitneme - uzivatel musi pouzit normalni prihlaseni
    db = get_db()
    if db:
        try:
            # Rychly test - pokud DB odpovi normalne, odmitneme offline login
            db.table('settings').select('setting_key').limit(1).execute()
            return _cors_jsonify({"status": "error", "reason": "db_available", "message": "Databaze je dostupna. Pouzij normalni prihlaseni."}), 403
        except Exception:
            pass  # DB dostupna ale nefunguje - povolime offline login
    
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    
    if not username or not password:
        return _cors_jsonify({"status": "error", "message": "Chybi username nebo heslo."}), 400
    
    if not _HAS_LOCAL_DB:
        return _cors_jsonify({"status": "error", "message": "Offline admin modul neni k dispozici."}), 503
    
    result = check_offline_login(username, password)
    if result:
        print(f"[OFFLINE AUTH] Uspesne prihlaseni uzivatele: {result.get('nick')} ({result.get('discord_id')})", flush=True)
        return _cors_jsonify({
            "status": "ok",
            "discord_id": result['discord_id'],
            "discord_nick": result['nick'],
            "role": result['role'],
            "offline_mode": True,
            "roles": [result['role']]
        })
    return _cors_jsonify({"status": "error", "message": "Nespravne jmeno nebo heslo."}), 401


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
            if msg.get("is_archived") in (1, '1', True, 'true', 'True'): continue
            expires_at_str = msg.get("expires_at")
            if expires_at_str and str(expires_at_str).strip():
                try:
                    exp_dt = datetime.strptime(str(expires_at_str).strip(), "%d.%m.%Y %H:%M")
                    if now > exp_dt:
                        db.table("app_messages").update({"is_archived": 1}).eq("message_id", msg["message_id"]).execute()
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
                is_repeat = msg.get('repeat') in (1, '1', True, 'true', 'True')
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
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not _rate_limit_check(f'feedback:{client_ip}', 6, 3600):
        return _cors_jsonify({"status": "error", "message": "Příliš mnoho odeslaných zpráv. Zkuste to prosím za chvíli."}), 429

    data = request.get_json(silent=True) or {}
    db = get_db()
    if not db: return _cors_jsonify({"status": "error", "message": "Databáze je dočasně nedostupná."}), 500
    try:
        reply_pref = str(data.get("reply_pref", "discord")).lower().strip()
        if reply_pref not in ("discord", "email"):
            reply_pref = "discord"

        contact_discord = str(data.get("contact_discord", "")).strip()[:120]
        contact_email = str(data.get("contact_email", "")).strip()[:120]
        contact = str(data.get("contact", "")).strip()[:120]
        nick = str(data.get("nick", "")).strip()[:60]
        raw_img = str(data.get("image_url", "")).strip()
        image_url = ""
        if raw_img.startswith("data:image/") and len(raw_img) < 8000000:
            image_url = raw_img
        elif (raw_img.startswith("http://") or raw_img.startswith("https://")) and len(raw_img) < 1000:
            image_url = raw_img

        # Povolit pouze bezpečné typy podnětů
        raw_type = str(data.get("type", "GENERAL")).strip().upper()
        allowed_types = (
            "BUG", "BUG_GENERAL", "MAP_NOTIF", "MAP_BUG", "MAP_DATA", "GTFS",
            "FEEDBACK", "WEB_ERROR", "GENERAL", "OTHER", "NOTIF", "QUESTION"
        )
        type_str = raw_type if raw_type in allowed_types else "GENERAL"

        msg = str(data.get("message", "")).strip()[:2000]
        d_id = str(data.get("discord_id", "")).strip()[:120]

        if not msg:
            return _cors_jsonify({"status": "error", "message": "Popis problému nebo dotazu nesmí být prázdný."}), 400

        # Kontrola povinného údaje: Nick nebo E-mail je povinný
        if not nick and not contact_email and not ("@" in contact):
            return _cors_jsonify({"status": "error", "message": "Zadejte prosím své jméno / herní nick nebo e-mailovou adresu."}), 400

        if not nick:
            nick = contact_email.split('@')[0] if contact_email else "Návštěvník webu"

        # Pokud přišel pouze obecný contact parametr
        if not contact_discord and not contact_email and contact:
            if "@" in contact:
                contact_email = contact
                reply_pref = "email"
            else:
                contact_discord = contact

        # Pokud do discord inputu zadali email
        if contact_discord and "@" in contact_discord and not contact_email:
            contact_email = contact_discord
            contact_discord = ""
            reply_pref = "email"

        # Pokud do email inputu zadali discord nick/id (bez @)
        if contact_email and "@" not in contact_email and not contact_discord:
            contact_discord = contact_email
            contact_email = ""
            reply_pref = "discord"

        # Zkusit dohledat a propojit existujícího uživatele z tabulky users
        resolved_discord_id = ""
        resolved_email = contact_email

        if contact_discord.isdigit():
            resolved_discord_id = contact_discord
        elif d_id.isdigit():
            resolved_discord_id = d_id

        if db:
            u_match = None
            if not resolved_discord_id and contact_discord:
                try:
                    u_res = db.table("users").select("discord_id, email, nick").ilike("nick", contact_discord).execute().data
                    if u_res: u_match = u_res[0]
                except Exception: pass
            if not u_match and nick and nick != "Neznámý Uživatel":
                try:
                    u_res = db.table("users").select("discord_id, email, nick").ilike("nick", nick).execute().data
                    if u_res: u_match = u_res[0]
                except Exception: pass
            if not u_match and resolved_email:
                try:
                    u_res = db.table("users").select("discord_id, email, nick").ilike("email", resolved_email).execute().data
                    if u_res: u_match = u_res[0]
                except Exception: pass

            if u_match:
                if not resolved_discord_id and u_match.get("discord_id"):
                    resolved_discord_id = str(u_match["discord_id"])
                if not resolved_email and u_match.get("email"):
                    resolved_email = str(u_match["email"])

        final_discord_id = resolved_discord_id or contact_discord or d_id or "Webový formulář"

        saved_msg = msg
        if image_url:
            if image_url.startswith("data:image/"):
                saved_msg += "\n\n📷 [Přiložen screenshot ze souboru (.png/.jpg)]"
            else:
                saved_msg += f"\n\n📷 [Přiložený screenshot: {image_url}]"

        insert_payload = {
            "discord_id": final_discord_id,
            "nick": nick,
            "type": type_str,
            "message": saved_msg,
            "status": "pending",
            "sys_note": "",
            "fcreated_at": get_prague_time().strftime("%d.%m.%Y %H:%M"),
            "reply_pref": reply_pref,
            "contact_email": resolved_email,
            "contact_discord": contact_discord or (resolved_discord_id if resolved_discord_id != final_discord_id else "")
        }
        db.table("feedback").insert(insert_payload).execute()

        pref_label = "Discord DM" if reply_pref == "discord" else "E-mail"
        contact_display = []
        if contact_discord or resolved_discord_id: contact_display.append(f"Discord: `{resolved_discord_id or contact_discord}`")
        if resolved_email: contact_display.append(f"Email: `{resolved_email}`")
        contacts_str = " | ".join(contact_display) if contact_display else f"`{final_discord_id}`"

        if type_str in ["BUG", "BUG_GENERAL", "CHYBA", "WEB_ERROR", "MAP_BUG"]:
            log_title = "🐛 HLÁŠENÍ CHYBY Z WEBU"; log_color = 0xef4444
        elif type_str in ["NOTIF", "MAP_NOTIF"]:
            log_title = "🔔 PROBLÉM S NOTIFIKACEMI / SLEDOVÁNÍM"; log_color = 0xf59e0b
        elif type_str == "MAP_DATA":
            log_title = "🚌 CHYBĚJÍCÍ SPOJ NEBO LINKA"; log_color = 0x38bdf8
        elif type_str == "GTFS":
            log_title = "📊 DOTAZ K GTFS / JÍZDNÍM ŘÁDŮM"; log_color = 0x6366f1
        elif type_str == "FEEDBACK":
            log_title = "💡 NÁVRH NA VYLEPŠENÍ Z WEBU"; log_color = 0x10b981
        elif type_str == "QUESTION":
            log_title = "❓ DOTAZ / PODPORA Z WEBU"; log_color = 0x38bdf8
        elif type_str == "GENERAL":
            log_title = "💬 OBECNÁ ZPRÁVA Z WEBU"; log_color = 0xa855f7
        else:
            log_title = "📁 NOVÝ PODNĚT / OSTATNÍ"; log_color = 0x8b5cf6

        # Ošetření proti zneužití @everyone/@here a markdownu
        safe_nick = nick.replace("@", "@\u200b")
        safe_contacts = contacts_str.replace("@", "@\u200b")
        safe_msg = saved_msg.replace("@", "@\u200b")

        send_log(log_title, f"**Od:** {safe_nick}\n**Typ:** `{type_str}`\n**Kontakty:** {safe_contacts}\n**Požadovaná odpověď:** {pref_label}\n**Zpráva:**\n*{safe_msg}*", log_color, image_url=image_url)
        return _cors_jsonify({"status": "success"})
    except Exception as e:
        print(f"[FEEDBACK ERROR] {e}", flush=True)
        try:
            tb = traceback.format_exc()
            send_log("📲 APLIKAČNÍ CHYBA (/api/submit_feedback)", f"Chyba při ukládání feedbacku: `{e}`\n```py\n{tb[-800:]}\n```", 0xef4444, channel_name="📲・error-app")
        except Exception:
            pass
        return _cors_jsonify({"status": "error", "message": "Při odesílání hlášení došlo k chybě na serveru. Zkuste to prosím za okamžik znovu."}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH / DASHBOARD ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/login_request', methods=['POST'])
def login_request():
    is_json = request.is_json or bool(request.get_json(silent=True))
    json_data = request.get_json(silent=True) or {}
    
    # Rate limit: 5 pokusů / minutu na IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not _rate_limit_check(f'dash_login:{client_ip}', 5, 60):
        if is_json: return jsonify({"status": "error", "message": "Příliš mnoho pokusů o přihlášení. Zkuste to za minutu."}), 429
        flash('Příliš mnoho pokusů o přihlášení. Zkuste to za minutu.', 'error')
        return redirect(url_for('dashboard_main'))
        
    discord_id = (json_data.get('discord_id') or request.form.get('discord_id', '')).strip()
    # Validace – Discord ID musí být číselne
    if not discord_id.isdigit():
        if is_json: return jsonify({"status": "error", "message": "Neplatné Discord ID (musí obsahovat pouze čísla)."}), 400
        flash('Neplatné Discord ID.', 'error')
        return redirect(url_for('dashboard_main'))
        
    db = get_db()
    if db and discord_id:
        try:
            user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
            if not user:
                msg = 'Účet s tímto Discord ID neexistuje v databázi.'
                if is_json: return jsonify({"status": "error", "message": msg}), 404
                flash(msg, 'error')
            else:
                user_data = user[0]
                if user_data.get("is_deleted"):
                    msg = 'Tento účet byl smazán.'
                    if is_json: return jsonify({"status": "error", "message": msg}), 403
                    flash(msg, 'error')
                elif user_data.get("is_banned"):
                    msg = 'Tento účet byl zablokován (banned).'
                    if is_json: return jsonify({"status": "error", "message": msg}), 403
                    flash(msg, 'error')
                else:
                    # ── Přístup POUZE dle záznamu v DB, bez Discord role check ──
                    has_access = (user_data.get("dashboard_access") == True)

                    if not has_access:
                        msg = 'Přístup zamítnut. Dashboard přístup musí být povolen ručně administrátorem.'
                        if is_json: return jsonify({"status": "error", "message": msg}), 403
                        flash(msg, 'error')
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
                        try:
                            b_loop = get_bot_loop()
                            if b_loop:
                                asyncio.run_coroutine_threadsafe(send(), b_loop)
                            else:
                                print(f"[AUTH] Admin DM: bot loop neběží.")
                        except Exception as e:
                            print(f"[AUTH] Chyba v login_request DM: {e}")
                        if is_json:
                            return jsonify({"status": "ok", "discord_id": discord_id})
                        return redirect(url_for('wait_auth', discord_id=discord_id))
        except Exception as e:
            err_str = str(e)
            if "402" in err_str or "egress" in err_str:
                msg = "Chyba: Systém je dočasně offline (vyčerpán limit databáze). Použijte administrátorský NOUZOVÝ REŽIM (tlačítko DEV)."
            else:
                msg = f'Chyba: {e}'
            if is_json: return jsonify({"status": "error", "message": msg}), 500
            flash(msg, 'error')
    if is_json: return jsonify({"status": "error", "message": "Nepodařilo se zpracovat požadavek."}), 500
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/offline_login', methods=['POST'])
def dashboard_offline_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        flash('Chybí jméno nebo heslo.', 'error')
        return redirect(url_for('dashboard_main'))
        
    result = check_offline_login(username, password)
    if result:
        session['logged_in'] = True
        session['discord_id'] = result['discord_id']
        session['role'] = result['role']
        session['discord_nick'] = result['nick']
        session['dashboard_level'] = 'superadmin' # offline admin has full access
        session['offline_mode'] = True
        flash(f'Úspěšně přihlášen v nouzovém režimu jako {result["nick"]}.', 'success')
        return redirect(url_for('dashboard_main'))
    
    flash('Nesprávné jméno nebo heslo.', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): return render_public(HTML_WAIT_AUTH, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    target_id = str(discord_id)
    mem_status = _AUTH_TOKEN_STATUS.get(target_id)
    if mem_status == "approved":
        _AUTH_TOKEN_STATUS.pop(target_id, None)
        return {"status": "approved"}
    elif mem_status == "rejected":
        _AUTH_TOKEN_STATUS.pop(target_id, None)
        return {"status": "rejected"}
    try:
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", target_id).execute().data
            if user:
                t = user[0].get("login_token")
                if t == "approved": return {"status": "approved"}
                elif t == "rejected":
                    try: db.table("users").update({"login_token": ""}).eq("discord_id", target_id).execute()
                    except: pass
                    return {"status": "rejected"}
    except: pass
    return {"status": "waiting"}

def check_persistent_admin_session():
    if not session.get('logged_in'):
        admin_tok = request.cookies.get('admin_session_token') or request.cookies.get('web_session_token')
        if admin_tok:
            try:
                db = get_db()
                u = None
                if db:
                    u = get_cached_session_user(admin_tok)
                    if not u:
                        try:
                            from session_manager import find_user_by_session_token
                            u = find_user_by_session_token(db, admin_tok)
                        except Exception:
                            pass
                if not u:
                    try:
                        from session_manager import user_has_session_token
                        for bu in _get_fallback_users():
                            if user_has_session_token(bu, admin_tok) or bu.get("web_session_token") == admin_tok:
                                u = bu
                                break
                    except Exception:
                        pass
                if u:
                    if u.get('dashboard_access') == True and not u.get('is_banned') and not u.get('is_deleted'):
                        session.permanent = True
                        session['logged_in'] = True
                        session['discord_id'] = str(u.get('discord_id'))
                        session['discord_nick'] = u.get('nick') or u.get('email') or str(u.get('discord_id'))
                        session['nick'] = u.get('nick')
                        session['email'] = u.get('email')
                        session['role'] = u.get('role')
                        session['dashboard_level'] = u.get('dashboard_level') or 'admin'
            except Exception:
                pass

@app.before_request
def auto_admin_session():
    check_persistent_admin_session()

@app.route('/api/admin/check_session', methods=['GET'])
def api_admin_check_session():
    check_persistent_admin_session()
    if session.get('logged_in'):
        return jsonify({
            "logged_in": True,
            "nick": session.get('discord_nick') or session.get('nick'),
            "discord_id": session.get('discord_id'),
            "level": session.get('dashboard_level') or 'admin'
        })
    return jsonify({"logged_in": False})

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
        user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
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
                session['discord_nick'] = u.get('nick') or u.get('email') or str(discord_id)
                session['nick'] = u.get('nick')
                session['email'] = u.get('email')
                session['role'] = u.get('role')
                session['dashboard_level'] = u.get('dashboard_level') or 'admin'
                
                import uuid
                admin_token = str(uuid.uuid4())
                try:
                    from session_manager import add_user_session
                    add_user_session(db, u, admin_token, request)
                    db.table("users").update({
                        "login_token": "used",
                        "login_token_expires_at": int(_t.time()) + 10
                    }).eq("discord_id", discord_id).execute()
                    _invalidate_session_cache(user_id=u.get("id"))
                    _SESSION_CACHE[admin_token] = (time.time(), u)
                except Exception:
                    pass
                
                # Zabezpečení proti Safari/Chrome Mobile zahazování cookies při 302 redirectu
                resp = make_response("""
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
                """)
                resp.set_cookie('admin_session_token', admin_token, max_age=60*60*24*90, httponly=True, samesite='Lax')
                resp.set_cookie('web_session_token', admin_token, max_age=60*60*24*90, httponly=True, samesite='Lax')
                return resp
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
        _AUTH_TOKEN_STATUS[str(target_id)] = "approved"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="✅ **Přihlášení na web OIS IDPK bylo úspěšné!** Můžete se vrátit do prohlížeče.", embed=None, view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id="web_auth_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.discord_id if self.discord_id else str(interaction.user.id)
        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("Toto ověření není pro tebe!", ephemeral=True)
        _AUTH_TOKEN_STATUS[str(target_id)] = "rejected"
        try:
            db = get_db()
            if db:
                db.table("users").update({"login_token": "rejected"}).eq("discord_id", target_id).execute()
        except Exception:
            pass
        await interaction.response.edit_message(content="❌ **Přihlášení zrušeno.**", embed=None, view=None)

# ═══════════════════════════════════════════════════════════════════════════════
# NOVÝ WEB AUTH SYSTÉM
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/register')
@app.route('/login')
def auth_pages():
    # If user is already logged in with a cookie, redirect to home
    cookie_token = request.cookies.get('web_session_token')
    if cookie_token:
        user = get_cached_session_user(cookie_token)
        if user:
            return redirect(url_for('home'))
    return render_public(HTML_REGISTER) # HTML_REGISTER used for both login and register since it's passwordless

BOT_ASYNC_LOOP = None

def get_bot_loop():
    global BOT_ASYNC_LOOP
    try:
        if BOT_ASYNC_LOOP and BOT_ASYNC_LOOP.is_running():
            return BOT_ASYNC_LOOP
    except Exception:
        pass
    try:
        loop = getattr(bot, '_loop', None)
        if loop and loop.is_running():
            return loop
    except Exception:
        pass
    try:
        sentinel = getattr(discord.client, '_LoopSentinel', None)
        loop = getattr(bot, 'loop', None)
        if loop and (sentinel is None or not isinstance(loop, sentinel)) and loop.is_running():
            return loop
    except Exception:
        pass
    return None

def process_web_auth_discord(discord_id, client_ip):
    if not _rate_limit_check(f'auth_discord:{client_ip}', 10, 60):
        return {'status': 'error', 'message': 'Příliš mnoho pokusů. Zkuste to za chvíli.'}, 429
    discord_id_str = str(discord_id or '').strip()
    if not discord_id_str or not discord_id_str.isdigit():
        return {"status": "error", "message": "Neplatné Discord ID (musí být číselné)."}, 400
    db = get_db()
    if not db:
        return {"status": "error", "message": "Databáze není dostupná."}, 500
    
    try:
        user = db.table("users").select("*").eq("discord_id", discord_id_str).execute().data
        if not user:
            try:
                highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
                new_app_id = (highest[0]["app_id"] + 1) if (highest and highest[0].get("app_id")) else 1001
            except:
                new_app_id = None
            insert_data = {"discord_id": discord_id_str, "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M"), "is_banned": False, "is_deleted": False, "role": "User", "login_token": ""}
            if new_app_id: insert_data["app_id"] = new_app_id
            db.table("users").insert(insert_data).execute()
        
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", discord_id_str).execute()
        
        async def send():
            try:
                if not bot.is_ready():
                    await bot.wait_until_ready()
                u = bot.get_user(int(discord_id_str)) or await bot.fetch_user(int(discord_id_str))
                if u: 
                    await u.send(embed=discord.Embed(title="🔐 Webové ověření", description="Kliknutím na tlačítko níže se přihlásíte do interaktivní mapy a softwaru OIS IDPK.", color=0x38bdf8), view=WebAuthView(token, discord_id_str))
                    print(f"[AUTH] DM úspěšně naplánováno a odesláno uživateli {discord_id_str}")
                else:
                    print(f"[AUTH] Uživatel {discord_id_str} nebyl nalezen na Discordu.")
            except discord.errors.Forbidden:
                print(f"[AUTH] Uživatel {discord_id_str} má zablokované / vypnuté soukromé zprávy (DM) od bota!")
            except Exception as e:
                print(f"[AUTH] Nelze odeslat DM: {e}")
        
        b_loop = get_bot_loop()
        if b_loop: 
            asyncio.run_coroutine_threadsafe(send(), b_loop)
        else:
            print(f"[AUTH] Varování: bot.loop neběží / Discord bot není připojen.")
            
        return {"status": "success", "discord_id": discord_id_str}, 200
    except Exception as e:
        print(f"[AUTH] Chyba v process_web_auth_discord: {e}")
        return {"status": "error", "message": f"Došlo k chybě: {str(e)}"}, 500

def process_web_auth_email(email, intent, client_ip):
    if not _rate_limit_check(f'auth_email:{client_ip}', 6, 120):
        return {'status': 'error', 'message': 'Příliš mnoho pokusů o zaslání e-mailu. Zkuste to za chvíli.'}, 429
    email_str = str(email or '').strip()
    if not email_str or '@' not in email_str:
        return {"status": "error", "message": "Neplatný e-mail."}, 400
    db = get_db()
    if not db:
        return {"status": "error", "message": "Databáze není dostupná."}, 500
    
    try:
        user = db.table("users").select("*").eq("email", email_str).execute().data
        if not user:
            try:
                highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
                if highest and highest[0].get("app_id"):
                    highest_val = int(highest[0]["app_id"])
                    new_app_id = 2001 if highest_val < 2001 else highest_val + 1
                else:
                    new_app_id = 2001
            except:
                new_app_id = 2001
            insert_data = {"email": email_str, "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M"), "is_banned": False, "is_deleted": False, "role": "User", "login_token": "", "discord_id": "čeká na odpověd"}
            if new_app_id: insert_data["app_id"] = new_app_id
            db.table("users").insert(insert_data).execute()
        
        import time as _t
        import random
        import string
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        token_expiry = int(_t.time()) + 600
        db.table("users").update({"login_token": token, "login_token_expires_at": token_expiry}).eq("email", email_str).execute()
        
        if send_magic_link_email(email_str, token, intent=intent):
            return {"status": "success"}, 200
        else:
            return {"status": "error", "message": "E-mail se nepodařilo odeslat. Zkontrolujte prosím nastavení SMTP nebo použijte přihlášení přes Discord."}, 500
    except Exception as e:
        print(f"[AUTH] Chyba v process_web_auth_email: {e}")
        return {"status": "error", "message": f"Došlo k chybě: {str(e)}"}, 500

@app.route('/api/auth/discord/request', methods=['POST'])
def web_auth_discord_request():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    data = request.get_json(silent=True) or {}
    discord_id = data.get('discord_id') or data.get('discordId') or request.form.get('discord_id')
    res, code = process_web_auth_discord(discord_id, client_ip)
    return jsonify(res), code

@app.route('/api/auth/email/request', methods=['POST'])
def web_auth_email_request():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    data = request.get_json(silent=True) or {}
    email = data.get('email') or request.form.get('email')
    intent = data.get('intent', 'login')
    res, code = process_web_auth_email(email, intent, client_ip)
    return jsonify(res), code

@app.route('/api/auth/status')
def web_auth_status():
    discord_id = request.args.get('discord_id')
    cookie_token = request.cookies.get('web_session_token')
    
    # Check in-memory status first
    mem_status = _AUTH_TOKEN_STATUS.get(str(discord_id)) if discord_id else None
    if mem_status == "approved":
        _AUTH_TOKEN_STATUS.pop(str(discord_id), None)
        perm_token = str(uuid.uuid4())
        user_obj = None
        for bu in _get_fallback_users():
            if str(bu.get("discord_id")) == str(discord_id):
                user_obj = bu
                break
        if not user_obj:
            user_obj = {"discord_id": discord_id, "role": "User", "nick": str(discord_id)}
        _SESSION_CACHE[perm_token] = (time.time(), user_obj)
        try:
            db = get_db()
            if db:
                from session_manager import add_user_session
                add_user_session(db, user_obj, perm_token, request)
                _invalidate_session_cache(user_id=user_obj.get("id"))
        except Exception: pass
        return jsonify({"status": "approved", "token": perm_token})
    elif mem_status == "rejected":
        _AUTH_TOKEN_STATUS.pop(str(discord_id), None)
        return jsonify({"status": "rejected"})

    db = get_db()
    if db and discord_id:
        try:
            user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
            if user:
                u = user[0]
                t = u.get("login_token")
                if t == "approved": 
                    if cookie_token:
                        try:
                            # Link k aktualnimu uctu misto vytvoreni noveho
                            curr_user = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
                            if curr_user and curr_user[0].get('id') != u.get('id'):
                                c_u = curr_user[0]
                                app_id_c = int(c_u.get('app_id') or 999999)
                                app_id_u = int(u.get('app_id') or 999999)
                                if app_id_c <= app_id_u:
                                    id_to_keep = c_u.get("id")
                                    id_to_del = u.get("id")
                                else:
                                    id_to_keep = u.get("id")
                                    id_to_del = c_u.get("id")
                                new_email = c_u.get('email') or u.get('email')
                                new_discord = c_u.get('discord_id')
                                if not new_discord or new_discord == "čeká na odpověd":
                                    new_discord = u.get('discord_id') or discord_id
                                db.table("users").delete().eq("id", id_to_del).execute()
                                db.table("users").update({
                                    "discord_id": new_discord,
                                    "email": new_email,
                                    "web_session_token": cookie_token,
                                    "login_token": ""
                                }).eq("id", id_to_keep).execute()
                                return jsonify({"status": "approved", "linked": True})
                        except Exception: pass
                    perm_token = str(uuid.uuid4())
                    try:
                        from session_manager import add_user_session
                        add_user_session(db, u, perm_token, request)
                        _invalidate_session_cache(user_id=u.get("id"))
                    except Exception: pass
                    _SESSION_CACHE[perm_token] = (time.time(), u)
                    return jsonify({"status": "approved", "token": perm_token})
                elif t == "rejected":
                    try: db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                    except Exception: pass
                    return jsonify({"status": "rejected"})
        except Exception: pass
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
            # Zkontrolovat expiraci tokenu (10 minut)
            token_exp = int(u.get('login_token_expires_at') or 0)
            if token_exp > 0 and _t.time() > token_exp:
                db.table("users").update({"login_token": "", "login_token_expires_at": 0}).eq("id", u.get("id")).execute()
                return "Odkaz vypršel (platnost 10 minut). Požádejte o nový odkaz.", 400
            email = u.get("email")
            if cookie_token and intent == 'link':
                curr_user = db.table("users").select("*").eq("web_session_token", cookie_token).execute().data
                if curr_user and curr_user[0].get('id') != u.get('id'):
                    db.table("users").delete().eq("id", u.get("id")).execute()
                    db.table("users").update({"email": email}).eq("web_session_token", cookie_token).execute()
                    return redirect('/ucet')
            perm_token = _secrets.token_hex(32)
            from session_manager import add_user_session
            add_user_session(db, u, perm_token, request)
            _invalidate_session_cache(user_id=u.get("id"))
            _SESSION_CACHE[perm_token] = (time.time(), u)
            
            status_text = "PŘIHLÁŠENO DO APLIKACE I NA WEB" if intent == 'app_login' else "PŘIHLÁŠENO NA WEB"
            
            # Nastavíme cookie přes Flask Response, ale vrátíme meta refresh stránku s animací
            from flask import make_response
            html_content = """
            <html>
            <head>
                <meta http-equiv="refresh" content="4;url=/ucet">
                <title>Úspěšné přihlášení</title>
                <style>
                    body { background-color: #0f172a; color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; flex-direction: column; }
                    .success-checkmark { width: 80px; height: 115px; margin: 0 auto; }
                    .check-icon { width: 80px; height: 80px; position: relative; border-radius: 50%; box-sizing: content-box; border: 4px solid #4CAF50; }
                    .check-icon::before { top: 3px; left: -2px; width: 30px; transform-origin: 100% 50%; border-radius: 100px 0 0 100px; }
                    .check-icon::after { top: 0; left: 30px; width: 60px; transform-origin: 0 50%; border-radius: 0 100px 100px 0; animation: rotate-circle 4.25s ease-in; }
                    .check-icon::before, .check-icon::after { content: ''; height: 100px; position: absolute; background: #0f172a; transform: rotate(-45deg); }
                    .icon-line { height: 5px; background-color: #4CAF50; display: block; border-radius: 2px; position: absolute; z-index: 10; }
                    .icon-line.line-tip { top: 46px; left: 14px; width: 25px; transform: rotate(45deg); animation: icon-line-tip 0.75s; }
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
                <h2>""" + status_text + """</h2>
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
        from session_manager import remove_user_session_by_token
        remove_user_session_by_token(db, cookie_token)
        _invalidate_session_cache(cookie_token)
    resp = jsonify({"status": "success"})
    resp.set_cookie('web_session_token', '', expires=0, secure=True, httponly=True, samesite='Strict')
    return resp

@app.route('/api/auth/me')
def web_auth_me():
    cookie_token = request.cookies.get('web_session_token')
    if cookie_token:
        user = get_cached_session_user(cookie_token)
        if user:
            name = user.get("nick") or user.get("email") or "Uživatel"
            avatar = user.get("avatar_url") or ""
            return jsonify({
                "status": "success",
                "name": name,
                "avatar": avatar,
                "user": {
                    "discord_id": user.get("discord_id"),
                    "email": user.get("email"),
                    "nick": user.get("nick"),
                    "avatar_url": avatar
                }
            })
    return jsonify({"status": "unauthorized"}), 401

# ═══════════════════════════════════════════════════════════════════════════════
# NOVÝ WEB: AUTH & STATS COMPATIBILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats/summary', methods=['GET', 'OPTIONS'])
def api_stats_summary():
    if request.method == 'OPTIONS':
        return jsonify({})
    
    now_ts = time.time()
    # 1. Paměťová cache na 120 sekund (drasticky snižuje Egress a Log Ingestion na Supabase!)
    if _STATS_SUMMARY_CACHE["data"] and (now_ts - _STATS_SUMMARY_CACHE["ts"] < 120):
        return jsonify(_STATS_SUMMARY_CACHE["data"])
    
    try:
        all_users = []
        db = get_db()
        if db and not EGRESS_SAVE_MODE:
            try:
                all_users = db.table("users").select("discord_id, nick, total_time, launch_count, avatar_url").execute().data or []
            except Exception as e_u:
                print(f"[SUPABASE USERS] 402/Chyba při dotazu na users, použita lokální záloha: {e_u}", flush=True)
                all_users = _get_fallback_users()
        else:
            all_users = _get_fallback_users()

        if not all_users:
            all_users = _get_fallback_users()

        nick_map = {str(u.get('discord_id')): u.get('nick', 'Neznámý') for u in all_users}
        
        # TOP 5 time
        valid_time_users = [u for u in all_users if int(u.get('total_time') or 0) > 0]
        top_time_users = sorted(valid_time_users, key=lambda x: int(x.get('total_time') or 0), reverse=True)[:5]
        time_list = [[u.get('nick') or 'Neznámý', round(int(u.get('total_time') or 0) / 60)] for u in top_time_users]
        if not time_list:
            time_list = [['marekk_czz', 22], ['Itz_Winters', 11], ['_Runtik_🦖💗', 9], ['Patrik20201', 5], ['Dopravák z Karlovarska', 5]]
        
        # Získání dat z lokální databáze pro sloučení
        local_s = {}
        try:
            from local_db import local_get_stats
            local_s = local_get_stats()
        except Exception: pass

        # TOP lines & stops (Local DB + Supabase if available)
        merged_lines = {}
        merged_stops = {}
        for ln, cnt in local_s.get('lines', {}).items():
            merged_lines[ln] = max(merged_lines.get(ln, 0), int(cnt or 0))
        for sn, cnt in local_s.get('stops', {}).items():
            merged_stops[sn] = max(merged_stops.get(sn, 0), int(cnt or 0))

        if db and not EGRESS_SAVE_MODE:
            try:
                top_lines = db.table("stats_lines").select("line_name, play_count").order("play_count", desc=True).limit(100).execute().data or []
                for l in top_lines:
                    ln = l.get('line_name')
                    if ln: merged_lines[ln] = max(merged_lines.get(ln, 0), int(l.get('play_count') or 0))
            except Exception: pass
            try:
                top_stops = db.table("stats_stops").select("stop_name, announce_count").order("announce_count", desc=True).limit(200).execute().data or []
                for s in top_stops:
                    sn = s.get('stop_name')
                    if sn: merged_stops[sn] = max(merged_stops.get(sn, 0), int(s.get('announce_count') or 0))
            except Exception: pass
            
        toplines_list = [[ln, cnt] for ln, cnt in sorted(merged_lines.items(), key=lambda x: x[1], reverse=True)]
        topstops_list = [[sn, cnt] for sn, cnt in sorted(merged_stops.items(), key=lambda x: x[1], reverse=True)]
        
        player_line_counts = {}
        for did, lines_dict in local_s.get('user_lines', {}).items():
            if did and did != 'None':
                local_u_sum = sum(int(c or 0) for c in lines_dict.values())
                player_line_counts[did] = max(player_line_counts.get(did, 0), local_u_sum)

        player_stop_counts = {}
        for did, stops_dict in local_s.get('user_stops', {}).items():
            if did and did != 'None':
                local_s_sum = sum(int(c or 0) for c in stops_dict.values())
                player_stop_counts[did] = max(player_stop_counts.get(did, 0), local_s_sum)

        if db and not EGRESS_SAVE_MODE:
            try:
                user_lines_data = db.table("user_stats_lines").select("discord_id, play_count").execute().data or []
                db_u_lines = {}
                for ul in user_lines_data:
                    did = str(ul.get('discord_id'))
                    if did and did != 'None':
                        db_u_lines[did] = db_u_lines.get(did, 0) + int(ul.get('play_count') or 0)
                for did, cnt in db_u_lines.items():
                    player_line_counts[did] = max(player_line_counts.get(did, 0), cnt)
            except Exception: pass
            try:
                user_stops_data = db.table("user_stats_stops").select("discord_id, announce_count").execute().data or []
                db_u_stops = {}
                for us in user_stops_data:
                    did = str(us.get('discord_id'))
                    if did and did != 'None':
                        db_u_stops[did] = db_u_stops.get(did, 0) + int(us.get('announce_count') or 0)
                for did, cnt in db_u_stops.items():
                    player_stop_counts[did] = max(player_stop_counts.get(did, 0), cnt)
            except Exception: pass

        lines_list = [[nick_map.get(did, 'Neznámý'), count] for did, count in sorted(player_line_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        stops_list = [[nick_map.get(did, 'Neznámý'), count] for did, count in sorted(player_stop_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # TOP 5 launches (počet spuštění)
        valid_launch_users = [u for u in all_users if int(u.get('launch_count') or 0) > 0]
        top_launch_users = sorted(valid_launch_users, key=lambda x: int(x.get('launch_count') or 0), reverse=True)[:5]
        launches_list = [[u.get('nick') or 'Neznámý', int(u.get('launch_count') or 0)] for u in top_launch_users]

        # Dnešní statistiky
        today_str = get_prague_time().strftime("%d.%m.%Y")
        sessions_today = []
        if db and not EGRESS_SAVE_MODE:
            try:
                sessions_today = db.table("app_sessions").select("discord_id, start_time, end_time").like("start_time", f"{today_str}%").execute().data or []
            except Exception: pass
        today_user_mins = {}
        today_user_launches = {}
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
                    if diff > 0 and did and did != 'None':
                        today_user_mins[did] = today_user_mins.get(did, 0) + diff
            except: pass
        top_today_time_id = max(today_user_mins, key=today_user_mins.get) if today_user_mins else None
        top_today_time_nick = nick_map.get(str(top_today_time_id), "marekk_czz") if top_today_time_id else "marekk_czz"
        top_today_time_val = today_user_mins.get(top_today_time_id, 18) if top_today_time_id else 18

        top_today_launch_id = max(today_user_launches, key=today_user_launches.get) if today_user_launches else None
        top_today_launch_nick = nick_map.get(str(top_today_launch_id), "marekk_czz") if top_today_launch_id else "marekk_czz"
        top_today_launch_val = today_user_launches.get(top_today_launch_id, 7) if top_today_launch_id else 7

        today_info = {
            "top_time_nick": top_today_time_nick,
            "top_time_val": top_today_time_val,
            "top_launch_nick": top_today_launch_nick,
            "top_launch_val": top_today_launch_val
        }

        total_lines_sum = sum(merged_lines.values())
        total_stops_sum = sum(merged_stops.values())
        total_hours = round(sum(int(u.get('total_time') or 0) for u in all_users) / 60)
        total_launches = sum(int(u.get('launch_count') or 0) for u in all_users)
        active_users_count = len(all_users)
        
        result = {
            "toplines": toplines_list,
            "topstops": topstops_list,
            "lines": lines_list,
            "stops": stops_list,
            "time": time_list,
            "launches": launches_list,
            "today": today_info,
            "total_lines": total_lines_sum,
            "total_stops": total_stops_sum,
            "total_users": active_users_count,
            "total_hours": total_hours,
            "total_launches": total_launches
        }
        _STATS_SUMMARY_CACHE["ts"] = now_ts
        _STATS_SUMMARY_CACHE["data"] = result
        try:
            with open(_SUMMARY_BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception: pass

        return jsonify(result)
    except Exception as e_all:
        print(f"[SUMMARY ERROR] Fallback na zálohu: {e_all}", flush=True)
        if _STATS_SUMMARY_CACHE["data"]:
            return jsonify(_STATS_SUMMARY_CACHE["data"])
        fallback = _get_fallback_summary()
        if fallback:
            return jsonify(fallback)
        return jsonify({})

@app.route('/api/auth/discord/start', methods=['POST'])
def api_auth_discord_start():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get('discordId') or data.get('discord_id') or '').strip()
    if not discord_id:
        return jsonify({"ok": False, "error": "Chybí Discord ID."}), 400
    res, code = process_web_auth_discord(discord_id, client_ip)
    if res.get('status') == 'success':
        return jsonify({"ok": True, "discordId": str(discord_id)})
    return jsonify({"ok": False, "error": res.get('message', 'Chyba')}), code

@app.route('/api/auth/discord/status', methods=['POST', 'GET'])
def api_auth_discord_status():
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get('discordId') or data.get('discord_id') or request.args.get('discord_id') or '').strip()
    db = get_db()
    if not db or not discord_id:
        return jsonify({"confirmed": False})
    user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if user and user[0].get('login_token') == 'approved':
        u = user[0]
        new_token = str(uuid.uuid4())
        from session_manager import add_user_session
        add_user_session(db, u, new_token, request)
        _invalidate_session_cache(user_id=u.get("id"))
        _SESSION_CACHE[new_token] = (time.time(), u)
        resp = jsonify({
            "confirmed": True,
            "name": u.get('nick') or f"Discord {discord_id}",
            "avatar": u.get('avatar_url')
        })
        resp.set_cookie('web_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
        if u.get('dashboard_access') == True or u.get('role') in ['Superadmin', 'Admin', 'DEV', 'SA']:
            resp.set_cookie('admin_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
            session.permanent = True
            session['logged_in'] = True
            session['discord_id'] = str(u.get('discord_id'))
            session['discord_nick'] = u.get('nick') or str(u.get('discord_id'))
            session['nick'] = u.get('nick')
            session['role'] = u.get('role')
            session['dashboard_level'] = u.get('dashboard_level') or 'admin'
        return resp
    return jsonify({"confirmed": False})

@app.route('/api/auth/email/start', methods=['POST'])
def api_auth_email_start():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    data = request.get_json(silent=True) or {}
    email = str(data.get('email') or '').strip()
    mode = str(data.get('mode') or 'code')
    intent = 'code' if mode == 'code' else 'login'
    if not email:
        return jsonify({"ok": False, "error": "Chybí e-mail."}), 400
    res, code = process_web_auth_email(email, intent, client_ip)
    if res.get('status') == 'success':
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": res.get('message', 'Chyba')}), code

@app.route('/api/auth/email/verify', methods=['POST'])
def api_auth_email_verify():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email') or '').strip()
    code = str(data.get('code') or '').strip().upper()
    db = get_db()
    if not db or not email or not code:
        return jsonify({"ok": False, "error": "Neplatný kód nebo e-mail."})
    user = db.table("users").select("*").eq("email", email).execute().data
    if not user:
        return jsonify({"ok": False, "error": "Účet nenalezen."})
    u = user[0]
    expected_token = str(u.get("login_token") or "").strip().upper()
    import time as _t
    exp = u.get("login_token_expires_at") or 0
    if exp and _t.time() > exp:
        return jsonify({"ok": False, "error": "Platnost kódu vypršela. Nechte si poslat nový."})
    if code != expected_token:
        return jsonify({"ok": False, "error": "Zadaný kód nesouhlasí."})
    new_token = str(uuid.uuid4())
    from session_manager import add_user_session
    add_user_session(db, u, new_token, request)
    _invalidate_session_cache(user_id=u.get("id"))
    _SESSION_CACHE[new_token] = (time.time(), u)
    resp = jsonify({
        "ok": True,
        "name": u.get("nick") or email,
        "avatar": u.get("avatar_url")
    })
    resp.set_cookie('web_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
    if u.get('dashboard_access') == True or u.get('role') in ['Superadmin', 'Admin', 'DEV', 'SA']:
        resp.set_cookie('admin_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
        session.permanent = True
        session['logged_in'] = True
        session['discord_id'] = str(u.get('discord_id'))
        session['discord_nick'] = u.get('nick') or str(u.get('discord_id'))
        session['nick'] = u.get('nick')
        session['role'] = u.get('role')
        session['dashboard_level'] = u.get('dashboard_level') or 'admin'
    return resp

@app.route('/api/auth/email/status', methods=['POST', 'GET'])
def api_auth_email_status():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email') or request.args.get('email') or '').strip()
    db = get_db()
    if not db or not email:
        return jsonify({"confirmed": False})
    user = db.table("users").select("*").eq("email", email).execute().data
    if user:
        u = user[0]
        if u.get('login_token') == 'approved':
            new_token = str(uuid.uuid4())
            from session_manager import add_user_session
            add_user_session(db, u, new_token, request)
            _invalidate_session_cache(user_id=u.get("id"))
            _SESSION_CACHE[new_token] = (time.time(), u)
            resp = jsonify({
                "confirmed": True,
                "name": u.get("nick") or email,
                "avatar": u.get("avatar_url")
            })
            resp.set_cookie('web_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
            if u.get('dashboard_access') == True or u.get('role') in ['Superadmin', 'Admin', 'DEV', 'SA']:
                resp.set_cookie('admin_session_token', new_token, max_age=30*86400, httponly=True, samesite='Lax')
                session.permanent = True
                session['logged_in'] = True
                session['discord_id'] = str(u.get('discord_id'))
                session['discord_nick'] = u.get('nick') or str(u.get('discord_id'))
                session['nick'] = u.get('nick')
                session['role'] = u.get('role')
                session['dashboard_level'] = u.get('dashboard_level') or 'admin'
            return resp
    return jsonify({"confirmed": False})

@app.route('/api/stats/user', methods=['POST', 'OPTIONS'])
def api_stats_user():
    if request.method == 'OPTIONS':
        return jsonify({})
    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    if not name:
        return jsonify({"found": False})
    db = get_db()
    u_res = []
    all_users = []

    # 1. Zkus Supabase (pokud není aktivní šetřící režim a Supabase neodpovídá 402)
    if db and not EGRESS_SAVE_MODE:
        try:
            u_res = db.table("users").select("discord_id, nick, avatar_url, total_time, launch_count").ilike("nick", f"%{name}%").limit(1).execute().data
            if not u_res and name.isdigit():
                u_res = db.table("users").select("discord_id, nick, avatar_url, total_time, launch_count").eq("discord_id", name).limit(1).execute().data
            all_users = db.table("users").select("discord_id, nick, total_time, launch_count").execute().data or []
        except Exception as e_sb:
            print(f"[USER STATS] Supabase 402/Chyba, přechod na lokální zálohu: {e_sb}", flush=True)
            u_res = []
            all_users = []

    # 2. Lokální offline záloha (100% spolehlivá i při výpadku/402 Supabase)
    if not all_users:
        all_users = _get_fallback_users()
    if not u_res and all_users:
        name_lower = name.lower()
        for ux in all_users:
            if name_lower in str(ux.get('nick') or '').lower() or str(ux.get('discord_id')) == name:
                u_res = [ux]
                break

    if not u_res:
        return jsonify({"found": False})

    u = u_res[0]
    d_id = str(u.get('discord_id') or '')
    total_time_mins = int(u.get('total_time') or 0)
    hours = total_time_mins // 60
    
    lines_count = 0
    stops_count = 0
    lines_list = []
    stops_list = []

    merged_u_lines = {}
    merged_u_stops = {}
    ls = {}
    try:
        from local_db import local_get_stats
        ls = local_get_stats()
    except Exception: pass

    if d_id:
        if db and not EGRESS_SAVE_MODE:
            try:
                l_res = db.table("user_stats_lines").select("line_name, play_count").eq("discord_id", d_id).order("play_count", desc=True).execute().data or []
                for x in l_res:
                    ln = x.get('line_name')
                    if ln: merged_u_lines[ln] = max(merged_u_lines.get(ln, 0), int(x.get('play_count', 0)))
            except Exception: pass
            try:
                s_res = db.table("user_stats_stops").select("stop_name, announce_count").eq("discord_id", d_id).order("announce_count", desc=True).execute().data or []
                for x in s_res:
                    sn = x.get('stop_name')
                    if sn: merged_u_stops[sn] = max(merged_u_stops.get(sn, 0), int(x.get('announce_count', 0)))
            except Exception: pass
        
        # Přidej lokální záznamy uživatele (pouze max, nikdy nesčítat se Supabase!)
        for ln, cnt in ls.get('user_lines', {}).get(d_id, {}).items():
            merged_u_lines[ln] = max(merged_u_lines.get(ln, 0), int(cnt or 0))
        for sn, cnt in ls.get('user_stops', {}).get(d_id, {}).items():
            merged_u_stops[sn] = max(merged_u_stops.get(sn, 0), int(cnt or 0))
        
        if merged_u_lines:
            lines_list = [[k, v] for k, v in sorted(merged_u_lines.items(), key=lambda x: x[1], reverse=True)]
            lines_count = sum(v for _, v in lines_list)
        if merged_u_stops:
            stops_list = [[k, v] for k, v in sorted(merged_u_stops.items(), key=lambda x: x[1], reverse=True)]
            stops_count = sum(v for _, v in stops_list)

    # 1. Pořadí v odehraném čase (Time Rank)
    if not all_users:
        all_users = _get_fallback_users()
    valid_time_users = sorted([x for x in all_users if int(x.get('total_time') or 0) > 0], key=lambda x: int(x.get('total_time') or 0), reverse=True)
    time_rank = None
    for idx, ux in enumerate(valid_time_users):
        if str(ux.get('discord_id')) == d_id or (u.get('nick') and ux.get('nick') == u.get('nick')):
            time_rank = idx + 1
            break

    # 2. Pořadí v odjetých linkách (Lines Rank - 100% dynamicky z DB)
    lines_rank = None
    all_u_lines = []
    if db and not EGRESS_SAVE_MODE:
        try:
            all_u_lines = db.table("user_stats_lines").select("discord_id, play_count").execute().data or []
        except Exception: pass
    all_line_sums = {}
    for x in all_u_lines:
        xdid = str(x.get('discord_id'))
        if xdid and xdid != 'None':
            all_line_sums[xdid] = all_line_sums.get(xdid, 0) + int(x.get('play_count') or 0)
    for xdid, ldict in ls.get('user_lines', {}).items():
        if xdid and xdid != 'None':
            all_line_sums[xdid] = max(all_line_sums.get(xdid, 0), sum(int(c or 0) for c in ldict.values()))
    if d_id and lines_count > 0:
        all_line_sums[d_id] = max(all_line_sums.get(d_id, 0), lines_count)
    sorted_users_lines = sorted([item for item in all_line_sums.items() if item[1] > 0], key=lambda x: x[1], reverse=True)
    for idx, (xdid, cnt) in enumerate(sorted_users_lines):
        if xdid == d_id:
            lines_rank = idx + 1
            break

    # 3. Pořadí ve vyhlášených zastávkách (Stops Rank - 100% dynamicky z DB)
    stops_rank = None
    all_u_stops = []
    if db and not EGRESS_SAVE_MODE:
        try:
            all_u_stops = db.table("user_stats_stops").select("discord_id, announce_count").execute().data or []
        except Exception: pass
    all_stop_sums = {}
    for x in all_u_stops:
        xdid = str(x.get('discord_id'))
        if xdid and xdid != 'None':
            all_stop_sums[xdid] = all_stop_sums.get(xdid, 0) + int(x.get('announce_count') or 0)
    for xdid, sdict in ls.get('user_stops', {}).items():
        if xdid and xdid != 'None':
            all_stop_sums[xdid] = max(all_stop_sums.get(xdid, 0), sum(int(c or 0) for c in sdict.values()))
    if d_id and stops_count > 0:
        all_stop_sums[d_id] = max(all_stop_sums.get(d_id, 0), stops_count)
    sorted_users_stops = sorted([item for item in all_stop_sums.items() if item[1] > 0], key=lambda x: x[1], reverse=True)
    for idx, (xdid, cnt) in enumerate(sorted_users_stops):
        if xdid == d_id:
            stops_rank = idx + 1
            break

    # 4. Pořadí v počtu spuštění (Launches Rank)
    launch_count = int(u.get('launch_count') or 0)
    launches_rank = None
    valid_launch_users = sorted([x for x in all_users if int(x.get('launch_count') or 0) > 0], key=lambda x: int(x.get('launch_count') or 0), reverse=True)
    for idx, ux in enumerate(valid_launch_users):
        if str(ux.get('discord_id')) == d_id or (u.get('nick') and ux.get('nick') == u.get('nick')):
            launches_rank = idx + 1
            break

    return jsonify({
        "found": True,
        "name": u.get('nick') or name,
        "avatar": u.get('avatar_url') or None,
        "lines": lines_count,
        "stops": stops_count,
        "hours": hours,
        "launches": launch_count,
        "linesList": lines_list,
        "stopsList": stops_list,
        "linesRank": lines_rank,
        "stopsRank": stops_rank,
        "timeRank": time_rank,
        "launchesRank": launches_rank
    })

@app.route('/api/admin/clean_reset_lines_stops', methods=['POST', 'GET'])
def admin_clean_reset_lines_stops():
    """Ruční vymazání statistik linek a zastávek pro čistý začátek."""
    db = get_db()
    deleted_tables = []
    if db:
        for tbl in ["user_stats_stops", "user_stats_lines", "stats_stops", "stats_lines"]:
            try:
                db.table(tbl).delete().gte("id", 0).execute()
                deleted_tables.append(tbl)
            except Exception as e:
                pass
    try:
        from local_db import local_clear_all_stats
        local_clear_all_stats()
        deleted_tables.append("local_sqlite_stats")
    except Exception: pass
    return jsonify({"status": "ok", "cleared": deleted_tables})

@app.route('/logout')
def logout():
    session.clear()
    resp = redirect(url_for('home'))
    resp.delete_cookie('admin_session_token')
    resp.delete_cookie('web_session_token')
    return resp

@app.route('/ucet')
def stranka_ucet():
    try:
        db = get_db()
        cookie_token = request.cookies.get('web_session_token')
        admin_token = request.cookies.get('admin_session_token')
        u = None
        set_new_cookie = False

        if cookie_token:
            u = get_cached_session_user(cookie_token)
            if not u and db:
                try:
                    from session_manager import find_user_by_session_token
                    u = find_user_by_session_token(db, cookie_token)
                except Exception:
                    pass

        if not u and admin_token:
            u = get_cached_session_user(admin_token)
            if not u and db:
                try:
                    from session_manager import find_user_by_session_token
                    u = find_user_by_session_token(db, admin_token)
                except Exception:
                    pass
            if not u and db:
                try:
                    u_data = db.table("users").select("*").eq("web_session_token", admin_token).execute().data
                    if u_data:
                        u = u_data[0]
                except Exception:
                    pass
            if u:
                set_new_cookie = True
                cookie_token = admin_token

        if not u and session.get('discord_id') and db:
            try:
                u_data = db.table("users").select("*").eq("discord_id", str(session.get('discord_id'))).execute().data
                if u_data:
                    u = u_data[0]
                    set_new_cookie = True
            except Exception:
                pass

        if not u and session.get('logged_in') and session.get('nick') and db:
            try:
                u_data = db.table("users").select("*").eq("nick", str(session.get('nick'))).execute().data
                if u_data:
                    u = u_data[0]
                    set_new_cookie = True
            except Exception:
                pass

        if not u:
            tok_check = cookie_token or admin_token
            if tok_check:
                for bu in _get_fallback_users():
                    if bu.get("web_session_token") == tok_check or str(bu.get("id")) == tok_check:
                        u = bu
                        break

        if not u:
            resp = redirect('/register')
            if cookie_token:
                resp.delete_cookie('web_session_token')
            return resp

        # Pokud jsme našli uživatele, ale neměl v prohlížeči web_session_token cookie, vytvoříme relaci
        if not cookie_token or set_new_cookie:
            try:
                import uuid
                new_tok = str(uuid.uuid4())
                from session_manager import add_user_session
                add_user_session(db, u, new_tok, request)
                cookie_token = new_tok
                set_new_cookie = True
            except Exception:
                if not cookie_token:
                    cookie_token = str(u.get("web_session_token") or u.get("id"))

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
            fresh_u = db.table("users").select("*").eq("id", u["id"]).execute().data
            if fresh_u:
                u = fresh_u[0]
                if cookie_token:
                    _SESSION_CACHE[cookie_token] = (time.time(), u)
        except Exception:
            pass
    
        from session_manager import get_user_sessions
        user_sessions = get_user_sessions(u)
        sessions_count = len(user_sessions)
        
        sessions_html = ""
        for s in user_sessions:
            s_id = s.get("id", "")
            s_token = s.get("token", "")
            is_curr = (s_token == cookie_token)
            dev_name = s.get("device", "Neznámé zařízení")
            icon = s.get("icon", "fa-desktop")
            ip = s.get("ip", "Neznámá")
            created_at = s.get("created_at", "Neznámé")
            last_active = s.get("last_active", "Neznámé")
            
            curr_badge = '<span style="background:rgba(16,185,129,0.2); border:1px solid #10b981; color:#10b981; font-size:10px; padding:2px 8px; border-radius:12px; font-weight:bold; letter-spacing:0.5px;">TOTO ZAŘÍZENÍ</span>' if is_curr else ''
            
            sessions_html += f"""
            <div id="session-card-{s_id}" class="session-card" data-is-current="{str(is_curr).lower()}" style="background: rgba(0,0,0,0.35); border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center; transition: all 0.3s ease;">
              <div style="display:flex; align-items:center; gap:12px;">
                <div style="width:42px; height:42px; border-radius:10px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); display:flex; align-items:center; justify-content:center; color:#38bdf8; font-size:18px; flex-shrink:0;">
                  <i class="fas {icon}"></i>
                </div>
                <div>
                  <div style="color:white; font-size:14px; font-weight:bold; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    {dev_name} {curr_badge}
                  </div>
                  <div style="color:#94a3b8; font-size:12px; margin-top:2px;">
                    Naposledy aktivní: <span style="color:#38bdf8; font-weight:600;">{last_active}</span>
                  </div>
                  <div style="color:#64748b; font-size:11px; margin-top:1px;">
                    Přihlášeno: {created_at} &bull; IP: {ip}
                  </div>
                </div>
              </div>
              <div>
                <button onclick="deleteSession('{s_id}', {str(is_curr).lower()})" style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.35); color:#ef4444; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:bold; transition:0.2s;" onmouseover="this.style.background='#ef4444'; this.style.color='white';" onmouseout="this.style.background='rgba(239,68,68,0.15)'; this.style.color='#ef4444';" title="Odhlásit toto zařízení">
                  <i class="fas fa-trash-alt"></i> Smazat
                </button>
              </div>
            </div>
            """
        if not sessions_html:
            sessions_html = '<div style="color:#64748b; font-size:13px; text-align:center; padding:15px; background:rgba(0,0,0,0.2); border-radius:8px;">Žádná aktivní přihlášená zařízení.</div>'
    
        try:
            u_id_str = str(u.get("id") or "")
            d_id_str = str(u.get("discord_id") or "")
            a_id_str = str(u.get("app_id") or "")
            notifs_1 = []
            if u_id_str:
                notifs_1 = db.table("bus_notifications").select("*").eq("user_session", u_id_str).execute().data or []
            notifs_2 = []
            if d_id_str and d_id_str != u_id_str and d_id_str != "čeká na odpověd":
                notifs_2 = db.table("bus_notifications").select("*").eq("user_session", d_id_str).execute().data or []
            notifs_3 = []
            if a_id_str and a_id_str not in (u_id_str, d_id_str):
                notifs_3 = db.table("bus_notifications").select("*").eq("user_session", a_id_str).execute().data or []
            
            seen_ids = set()
            notif_res = []
            for item in (notifs_1 + notifs_2 + notifs_3):
                if item.get("id") not in seen_ids:
                    seen_ids.add(item.get("id"))
                    notif_res.append(item)
        except Exception:
            notif_res = []
            
        notif_html = ""
        once_rules = [r for r in notif_res if r.get("is_one_time")]
        repeat_rules = [r for r in notif_res if not r.get("is_one_time")]
    
        try:
            from local_db import local_notif_get_history
            u_history_1 = local_notif_get_history(user_session=str(u.get("id")), limit=25)
            u_history_2 = []
            if u.get("discord_id") and str(u.get("discord_id")) != str(u.get("id")):
                u_history_2 = local_notif_get_history(user_session=str(u.get("discord_id")), limit=25)
            u_history_3 = []
            if u.get("app_id") and str(u.get("app_id")) not in (str(u.get("id")), str(u.get("discord_id"))):
                u_history_3 = local_notif_get_history(user_session=str(u.get("app_id")), limit=25)
            seen_h_keys = set()
            u_history = []
            for h in (u_history_1 + u_history_2 + u_history_3):
                h_k = (h.get("id"), h.get("fired_at"), h.get("message"))
                if h_k not in seen_h_keys:
                    seen_h_keys.add(h_k)
                    u_history.append(h)
            u_history.sort(key=lambda x: str(x.get("fired_at") or ""), reverse=True)
            u_history = u_history[:25]
        except Exception:
            u_history = []
    
        def _render_rule_card(r, is_once):
            n_id = r.get("id")
            label = r.get("label") or f"Bus {r.get('identifier')}"
            typ_badge = '<span style="background:rgba(124,58,237,0.25);color:#c4b5fd;border:1px solid #7c3aed;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">⚡ Jednorázové</span>' if is_once else '<span style="background:rgba(2,132,199,0.25);color:#38bdf8;border:1px solid #0284c7;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px;">🔁 Opakující se pravidlo</span>'
            triggers = r.get("triggers", {})
            if isinstance(triggers, str):
                try:
                    triggers = json.loads(triggers)
                except Exception:
                    triggers = {}
            if not isinstance(triggers, dict):
                triggers = {}
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
            if triggers.get("delay_threshold"): t_texts.append(f"Zpoždění > {triggers.get('delay_threshold')} min")
            if triggers.get("delay_change"): t_texts.append("Skok zpoždění")
            trig_str = ", ".join(t_texts) or "Událost"
            cnt = r.get("fired_count") or r.get("fire_count") or 0
            unsub_btn = f'<a href="/api/notifications/unsubscribe?id={n_id}" target="_blank" style="text-decoration:none;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.35);color:#ef4444;font-size:11px;padding:4px 8px;border-radius:6px;margin-right:8px;font-weight:bold;" title="Vypnout toto pravidlo">🔕 Vypnout</a>' if not is_once else ''
            return f"""
            <div style="background: rgba(0,0,0,0.4); border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 8px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
                  <span style="color:white; font-weight:bold; font-size:14px;">{label}</span>
                  {typ_badge}
                </div>
                <div style="color:#94a3b8; font-size:12px; margin-bottom:4px;">Události: <span style="color:#e2e8f0;">{trig_str}</span></div>
                <div style="color:#64748b; font-size:11px;">Odesláno: {cnt}x</div>
              </div>
              <div style="display:flex; align-items:center;">
                {unsub_btn}
                <button onclick="deleteNotificationRule('{n_id}')" style="background:transparent; border:none; color:#ef4444; font-size:18px; cursor:pointer; padding:8px;" title="Smazat upozornění"><i class="fas fa-trash"></i></button>
              </div>
            </div>
            """
    
        # 1. Opakující se pravidla
        if repeat_rules:
            notif_html += '<div style="color:#38bdf8;font-size:13px;font-weight:bold;margin:12px 0 6px 0;display:flex;align-items:center;gap:6px;">🔁 Opakující se pravidla (' + str(len(repeat_rules)) + ')</div>'
            for r in repeat_rules:
                notif_html += _render_rule_card(r, False)
    
        # 2. Aktuální jednorázová upozornění
        if once_rules:
            notif_html += '<div style="color:#a78bfa;font-size:13px;font-weight:bold;margin:16px 0 6px 0;display:flex;align-items:center;gap:6px;">⚡ Aktuální jednorázová upozornění (' + str(len(once_rules)) + ')</div>'
            for r in once_rules:
                notif_html += _render_rule_card(r, True)
    
        if not once_rules and not repeat_rules:
            notif_html += '<div style="color:#64748b; font-size:13px; text-align:center; padding:15px; background:rgba(0,0,0,0.2); border-radius:8px; margin-bottom:12px;">Zatím nemáte žádná aktivní pravidla ani jednorázové notifikace.<br><a href="/mapa" style="color:#38bdf8;text-decoration:none;font-weight:bold;display:inline-block;margin-top:6px;">🗺️ Otevřít mapu a nastavit upozornění</a></div>'
    
        # 3. Historie proběhlých notifikací (staré notifikace)
        notif_html += '<div style="color:#e2e8f0;font-size:13px;font-weight:bold;margin:20px 0 8px 0;border-top:1px solid #334155;padding-top:14px;display:flex;align-items:center;gap:6px;">📜 Historie odeslaných notifikací (staré notifikace)</div>'
        if u_history:
            notif_html += '<div style="display:flex;flex-direction:column;gap:6px;max-height:220px;overflow-y:auto;">'
            for h in u_history:
                notif_html += f"""
                <div style="background:rgba(15,23,42,0.6);border:1px solid #334155;border-radius:6px;padding:8px 12px;font-size:11px;display:flex;justify-content:space-between;align-items:center;">
                  <div>
                    <div style="color:#e2e8f0;font-weight:600;">{h.get('message') or h.get('trigger')}</div>
                    <div style="color:#64748b;font-size:10px;">{h.get('fired_at', '')} &bull; Kanál: {h.get('channel', 'DM')}</div>
                  </div>
                  <span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:bold;">Odesláno</span>
                </div>
                """
            notif_html += '</div>'
        else:
            notif_html += '<div style="color:#64748b; font-size:12px; text-align:center; padding:10px;">Zatím žádná proběhlá upozornění.</div>'
    
        revoke_btn_display = "inline-flex" if sessions_count > 1 else "none"
        html = HTML_UCET.replace('__AVATAR_IMG__', avatar_img_html)
        html = html.replace('__NICK__', nick)
        html = html.replace('__AVATAR_URL__', avatar_url)
        html = html.replace('__DISCORD_STATUS__', discord_status)
        html = html.replace('__DISCORD_BTN__', discord_btn)
        html = html.replace('__EMAIL_STATUS__', email_status)
        html = html.replace('__EMAIL_BTN__', email_btn)
        html = html.replace('__APP_ID_BADGE__', app_id_badge)
        html = html.replace('__SESSIONS_COUNT__', str(sessions_count))
        html = html.replace('__REVOKE_BTN_DISPLAY__', revoke_btn_display)
        html = html.replace('__SESSIONS_LIST__', sessions_html)
        html = html.replace('__NOTIFICATIONS__', notif_html)
        html += link_scripts
        
        resp = make_response(render_public(html))
        if set_new_cookie and cookie_token:
            resp.set_cookie('web_session_token', cookie_token, max_age=30*86400, httponly=True, samesite='Lax')
        return resp
    
    except Exception as e_ucet:
        print(f"[UCET ERROR] {e_ucet}", flush=True)
        try:
            tb = traceback.format_exc()
            send_log("📲 APLIKAČNÍ CHYBA (/ucet)", f"Chyba na stránce /ucet: `{e_ucet}`\n```py\n{tb[-1000:]}\n```", 0xef4444, channel_name="📲・error-app")
        except Exception:
            pass
        return render_error_page(500, "Vyskytla se chyba", "Při načítání profilu došlo k chybě. Zkuste to prosím za okamžik znovu."), 500

@app.route('/api/ucet/sessions', methods=['GET'])
def api_ucet_sessions_get():
    cookie_token = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
    db = get_db()
    if not cookie_token or not db:
        return jsonify({"status": "error", "message": "Nepřihlášen"}), 401
    from session_manager import find_user_by_session_token, get_user_sessions
    u = find_user_by_session_token(db, cookie_token)
    if not u:
        u = get_cached_session_user(cookie_token)
    if not u:
        return jsonify({"status": "error", "message": "Uživatel nenalezen"}), 401
    
    _SESSION_CACHE[cookie_token] = (time.time(), u)
    user_sessions = get_user_sessions(u)
    result = []
    for s in user_sessions:
        s_token = s.get("token", "")
        result.append({
            "id": s.get("id", ""),
            "device": s.get("device", "Neznámé zařízení"),
            "icon": s.get("icon", "fa-desktop"),
            "ip": s.get("ip", "Neznámá"),
            "created_at": s.get("created_at", "Neznámé"),
            "last_active": s.get("last_active", "Neznámé"),
            "is_current": bool(s_token == cookie_token)
        })
    return jsonify({"status": "success", "sessions": result, "count": len(result)})

@app.route('/api/ucet/sessions/delete', methods=['POST'])
def api_ucet_session_delete():
    cookie_token = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
    db = get_db()
    if not cookie_token or not db:
        return jsonify({"status": "error", "message": "Nepřihlášen"}), 401
    from session_manager import find_user_by_session_token, remove_user_session_by_id
    u = find_user_by_session_token(db, cookie_token)
    if not u:
        u = get_cached_session_user(cookie_token)
    if not u:
        return jsonify({"status": "error", "message": "Uživatel nenalezen"}), 401
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    if not session_id:
        return jsonify({"status": "error", "message": "Chybí ID relace"}), 400
    
    ok, removed_token = remove_user_session_by_id(db, u["id"], session_id)
    if not ok:
        return jsonify({"status": "error", "message": "Relaci se nepodařilo smazat"}), 400
    
    # Okamžitě vymazat cache pro daného uživatele i smazaný token
    _invalidate_session_cache(token=removed_token, user_id=u["id"])
    _invalidate_session_cache(token=cookie_token, user_id=u["id"])
    
    resp = jsonify({"status": "success"})
    if removed_token and removed_token == cookie_token:
        resp.delete_cookie('web_session_token')
    return resp

@app.route('/api/ucet/sessions/revoke_others', methods=['POST'])
def api_ucet_sessions_revoke_others():
    cookie_token = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
    db = get_db()
    if not cookie_token or not db:
        return jsonify({"status": "error", "message": "Nepřihlášen"}), 401
    from session_manager import find_user_by_session_token, revoke_all_other_sessions
    u = find_user_by_session_token(db, cookie_token)
    if not u:
        u = get_cached_session_user(cookie_token)
    if not u:
        return jsonify({"status": "error", "message": "Uživatel nenalezen"}), 401
    
    ok = revoke_all_other_sessions(db, u["id"], cookie_token)
    if not ok:
        return jsonify({"status": "error", "message": "Nepodařilo se odhlásit ostatní zařízení"}), 500
    
    _invalidate_session_cache(token=cookie_token, user_id=u["id"])
    return jsonify({"status": "success"})

@app.route('/api/ucet/update', methods=['POST'])
def api_ucet_update():
    cookie_token = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
    db = get_db()
    if not cookie_token or not db:
        return jsonify({"status": "error", "message": "Nepřihlášen"}), 401
        
    data = request.get_json(silent=True) or {}
    nick = data.get('nick', '').strip()
    avatar_url = data.get('avatar_url', '').strip()
    
    if not nick:
        return jsonify({"status": "error", "message": "Přezdívka nesmí být prázdná"})
        
    if avatar_url and not avatar_url.startswith('data:image/'):
        return jsonify({"status": "error", "message": "Avatar musí být obrázek."})
        
    u = get_cached_session_user(cookie_token)
    if not u:
        from session_manager import find_user_by_session_token
        u = find_user_by_session_token(db, cookie_token)
    if not u:
        return jsonify({"status": "error", "message": "Uživatel nenalezen"}), 401
        
    try:
        db.table("users").update({"nick": nick, "avatar_url": avatar_url}).eq("id", u["id"]).execute()
        _invalidate_session_cache(cookie_token)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/dashboard/stats/clear_web', methods=['POST'])
def dashboard_stats_clear_web():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try:
        try:
            from local_db import local_clear_web_visits
            local_clear_web_visits()
        except Exception:
            pass
        db = get_db()
        if db and not EGRESS_SAVE_MODE:
            try:
                db.table("page_visits").delete().neq("id", 0).execute()
            except Exception:
                pass
        flash("Data historie webových návštěv byla úspěšně vymazána.", "success")
    except Exception as e:
        flash(f"Chyba při mazání historie webu: {e}", "error")
    return redirect(url_for('dashboard_stats'))

@app.route('/dashboard/stats', methods=['GET'], strict_slashes=False)
def dashboard_stats():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))

    now_dt = get_prague_time().replace(tzinfo=None)
    dates_7_days = [(now_dt - timedelta(days=i)).strftime("%d.%m.") for i in range(6, -1, -1)]

    # 1. Metriky WEBU
    web_total_visits = 0
    web_last_7_days = 0
    web_today_visits = 0
    country_totals = {}
    region_totals = {}
    recent_web_visits = []
    web_chart_7d = {d: 0 for d in dates_7_days}
    web_chart_24h = {f"{i:02d}:00": 0 for i in range(24)}

    # 2. Metriky APLIKACE
    app_total_launches = 0
    app_last_7_days = 0
    app_today_launches = 0
    app_online_users = []
    app_total_hours = 0
    recent_app_sessions = []
    top_active_users = []
    app_chart_7d = {d: 0 for d in dates_7_days}
    app_chart_24h = {f"{i:02d}:00": 0 for i in range(24)}

    try:
        db = get_db()
        # ── Načtení návštěvnosti WEBU (nejdřív z lokální SQLite, 0% zátěž na Supabase) ──
        visits = []
        try:
            from local_db import local_get_web_visits
            visits = local_get_web_visits(limit=2000)
        except Exception:
            pass

        if not visits and db and not EGRESS_SAVE_MODE:
            try:
                visits = db.table("page_visits").select("*").order("id", desc=True).limit(2000).execute().data or []
            except Exception:
                pass

        web_total_visits = len(visits)
        all_web_visits = []
        web_ip_map = {}
        web_chart_all_dict = {}

        for v in visits:
            c_raw = (v.get('country') or '').strip()
            parts = c_raw.split('|')
            cc = parts[0].lower().strip() if len(parts) > 0 and parts[0] else "cz"
            c_name = parts[1].strip() if len(parts) > 1 and parts[1] else "Česká republika"
            reg = parts[2].strip() if len(parts) > 2 else ""
            city = parts[3].strip() if len(parts) > 3 else ""
            path = parts[4].strip() if len(parts) > 4 else "/"
            ip = str(v.get('ip') or 'Neznámá').strip()

            flag_url = f"https://flagcdn.com/24x18/{cc}.png"
            if cc not in country_totals:
                country_totals[cc] = {"name": c_name, "count": 0, "flag": flag_url}
            country_totals[cc]["count"] += 1

            loc_label = f"{c_name} - {reg}" if reg else c_name
            if loc_label not in region_totals:
                region_totals[loc_label] = {"count": 0, "flag": flag_url, "city": city}
            region_totals[loc_label]["count"] += 1

            loc_display = f"{city}, {reg}" if (city and reg) else (reg or city or c_name)

            # Agregace IP adres pro sledování opakovaných návštěvníků
            if ip and ip != "Neznámá":
                if ip not in web_ip_map:
                    web_ip_map[ip] = {
                        "ip": ip,
                        "count": 0,
                        "location": loc_display,
                        "flag": flag_url,
                        "last_visited": v.get('visited_at', ''),
                        "paths": set()
                    }
                web_ip_map[ip]["count"] += 1
                if path:
                    web_ip_map[ip]["paths"].add(path)

            v_time_str = v.get('visited_at', '')
            try:
                v_time = datetime.strptime(v_time_str, "%d.%m.%Y %H:%M")
                if (now_dt - v_time).days <= 7:
                    web_last_7_days += 1
                if v_time.date() == now_dt.date():
                    web_today_visits += 1
                    h_str = v_time.strftime("%H:00")
                    if h_str in web_chart_24h:
                        web_chart_24h[h_str] += 1
                d_str = v_time.strftime("%d.%m.")
                if d_str in web_chart_7d:
                    web_chart_7d[d_str] += 1

                # Celá doba graf
                d_all_key = v_time.strftime("%d.%m.")
                web_chart_all_dict[d_all_key] = web_chart_all_dict.get(d_all_key, 0) + 1
            except Exception:
                pass

            all_web_visits.append({
                "id": v.get("id"),
                "ip": ip,
                "country_name": c_name,
                "flag": flag_url,
                "location": loc_display,
                "path": path,
                "visited_at": v_time_str
            })

        # Nejčastěji opakované IP adresy seřazené podle počtu návštěv
        top_repeated_ips = sorted(
            [
                {
                    "ip": data["ip"],
                    "count": data["count"],
                    "location": data["location"],
                    "flag": data["flag"],
                    "last_visited": data["last_visited"],
                    "paths_str": ", ".join(sorted(data["paths"]))[:50]
                }
                for data in web_ip_map.values()
            ],
            key=lambda x: x["count"],
            reverse=True
        )

        try:
            sorted_all_days = sorted(
                web_chart_all_dict.keys(),
                key=lambda d: datetime.strptime(d + str(now_dt.year), "%d.%m.%Y")
            )
        except Exception:
            sorted_all_days = list(web_chart_all_dict.keys())
        web_labels_all = sorted_all_days
        web_data_all = [web_chart_all_dict[k] for k in sorted_all_days]

        all_users = []
        if db and not is_supabase_restricted():
            try:
                all_users = db.table("users").select("id, discord_id, nick, avatar_url, role, is_online, last_active, total_time, launch_count").execute().data or []
            except Exception as e_users:
                check_supabase_error(e_users)
                all_users = []

        if not all_users:
            try:
                from local_db import _load_offline_admins
                for adm in _load_offline_admins():
                    all_users.append({
                        "id": adm.get("discord_id", "1"),
                        "discord_id": adm.get("discord_id", ""),
                        "nick": adm.get("nick", "marekk_czz"),
                        "avatar_url": "",
                        "role": adm.get("role", "DEV"),
                        "is_online": True,
                        "last_active": get_prague_time().strftime("%d.%m.%Y %H:%M"),
                        "total_time": 120,
                        "launch_count": 5
                    })
            except Exception:
                pass

        user_map = {}
        total_mins = 0
        for u in all_users:
            d_id = str(u.get("discord_id") or "")
            u_id = str(u.get("id") or "")
            if d_id:
                user_map[d_id] = u
            if u_id:
                user_map[f"email-{u_id}"] = u

            if u.get("is_online"):
                la_str = u.get("last_active")
                is_active = True
                if la_str:
                    try:
                        la_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S" if la_str.count(':') == 2 else "%d.%m.%Y %H:%M")
                        if (now_dt - la_dt).total_seconds() > 180:
                            is_active = False
                    except Exception:
                        pass
                if is_active:
                    app_online_users.append(u)

            try:
                total_mins += int(u.get("total_time") or 0)
                app_total_launches += int(u.get("launch_count") or 0)
            except Exception:
                pass

        app_total_hours = round(total_mins / 60, 1)

        # Relace aplikace z app_sessions
        app_sessions_raw = []
        if db and not is_supabase_restricted():
            try:
                app_sessions_raw = db.table("app_sessions").select("*").order("id", desc=True).limit(1000).execute().data or []
            except Exception as e_sess:
                check_supabase_error(e_sess)
                app_sessions_raw = []

        for s in app_sessions_raw:
            st_str = s.get("start_time") or ""
            et_str = s.get("end_time") or ""
            d_id = str(s.get("discord_id") or "")
            u_obj = user_map.get(d_id, {})

            try:
                fmt = "%d.%m.%Y %H:%M:%S" if st_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                st_dt = datetime.strptime(st_str, fmt)
                if (now_dt - st_dt).days <= 7:
                    app_last_7_days += 1
                if st_dt.date() == now_dt.date():
                    app_today_launches += 1
                    h_str = st_dt.strftime("%H:00")
                    if h_str in app_chart_24h:
                        app_chart_24h[h_str] += 1
                d_str = st_dt.strftime("%d.%m.")
                if d_str in app_chart_7d:
                    app_chart_7d[d_str] += 1
            except Exception:
                pass

            duration_str = "Neznámá"
            is_active_session = False
            if st_str and et_str:
                try:
                    fmt_s = "%d.%m.%Y %H:%M:%S" if st_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                    fmt_e = "%d.%m.%Y %H:%M:%S" if et_str.count(':') == 2 else "%d.%m.%Y %H:%M"
                    s_dt = datetime.strptime(st_str, fmt_s)
                    e_dt = datetime.strptime(et_str, fmt_e)
                    dur_sec = max(0, int((e_dt - s_dt).total_seconds()))
                    if dur_sec < 60:
                        duration_str = f"{dur_sec}s"
                    elif dur_sec < 3600:
                        duration_str = f"{dur_sec // 60}m"
                    else:
                        duration_str = f"{dur_sec // 3600}h {(dur_sec % 3600) // 60}m"

                    if (now_dt - e_dt).total_seconds() < 90 and u_obj.get("is_online"):
                        is_active_session = True
                except Exception:
                    pass

            if len(recent_app_sessions) < 100:
                recent_app_sessions.append({
                    "user_nick": u_obj.get("nick") or d_id or "Neznámý hráč",
                    "discord_id": d_id,
                    "avatar_url": u_obj.get("avatar_url") or "",
                    "role": u_obj.get("role") or "User",
                    "start_time": st_str,
                    "duration": duration_str,
                    "is_active": is_active_session
                })

        # Top aktivní hráči
        valid_users = [u for u in all_users if (u.get("total_time") or 0) > 0 or (u.get("launch_count") or 0) > 0]
        valid_users.sort(key=lambda x: int(x.get("total_time") or 0), reverse=True)
        top_active_users = valid_users[:7]

    except Exception as e:
        check_supabase_error(e)
        print(f"[STATS] Chyba při načítání statistik: {e}", flush=True)
        if not is_supabase_restricted():
            flash(f"Chyba při načítání statistik: {e}", "error")

    gc.collect()
    return render_dashboard(
        HTML_STATS,
        web_total_visits=web_total_visits,
        web_last_7_days=web_last_7_days,
        web_today_visits=web_today_visits,
        country_totals=country_totals,
        region_totals=region_totals,
        recent_web_visits=all_web_visits[:25],
        all_web_visits=all_web_visits,
        top_repeated_ips=top_repeated_ips,
        web_labels_7d=json.dumps(list(web_chart_7d.keys())),
        web_data_7d=json.dumps(list(web_chart_7d.values())),
        web_labels_all=json.dumps(web_labels_all),
        web_data_all=json.dumps(web_data_all),
        web_labels_24h=json.dumps(list(web_chart_24h.keys())),
        web_data_24h=json.dumps(list(web_chart_24h.values())),
        
        app_total_launches=app_total_launches,
        app_last_7_days=app_last_7_days,
        app_today_launches=app_today_launches,
        app_online_count=len(app_online_users),
        app_online_users=app_online_users,
        app_total_hours=app_total_hours,
        recent_app_sessions=recent_app_sessions,
        top_active_users=top_active_users,
        app_labels_7d=json.dumps(list(app_chart_7d.keys())),
        app_data_7d=json.dumps(list(app_chart_7d.values())),
        app_labels_24h=json.dumps(list(app_chart_24h.keys())),
        app_data_24h=json.dumps(list(app_chart_24h.values())),
        supabase_restricted=is_supabase_restricted(),
        deploy_time=DEPLOY_TIME
    )

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
    except Exception as e:
        err_str = str(e)
        if "402" in err_str or "egress" in err_str:
            flash("Nepodařilo se načíst data z databáze (limit vyčerpán). Jste v nouzovém režimu.", "warning")
        else:
            flash(f"Chyba při načítání dat: {e}", "error")
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
                if not res.data: flash(f"Chyba: Uživatel ({target_identifier}) nebyl nalezen pro permanentní smazání.", "error")
                else: flash('Účet a všechna jeho data byla trvale smazána.', 'dark')
                if valid_discord_id and str(session.get('discord_id')) == str(valid_discord_id): session.clear()
            
            adm = get_current_admin_name()
            send_log(f"👤 Úprava Uživatele ({action.upper()})", f"**Správce:** {adm}\n**Cíl:** `{target_identifier}` ({nick or ''})\n**Akce:** `{action}`", 0x38bdf8)
        except Exception as e:
            flash(f"Chyba při úpravě uživatele (akce {action}): {e}", "error")
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/app_management', methods=['GET'], strict_slashes=False)
def dashboard_app_management():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); soft_enabled = True; launcher_enabled = True; dl_enabled = True; web_login_enabled = True; map_enabled = True; web_maintenance = False
    a_url = ''; a_text = ''; a_active = 'false'
    try:
        if db:
            s_resp = db.table("settings").select("*").in_("setting_key", ["software_enabled", "launcher_enabled", "downloads_enabled", "web_login_enabled", "map_enabled", "web_maintenance", "announcement_url", "announcement_text", "announcement_active"]).execute().data or []
            for s in s_resp:
                k = s['setting_key']; v = str(s['setting_value'])
                vl = v.lower()
                if k == 'software_enabled': soft_enabled = vl != 'false'
                elif k == 'launcher_enabled': launcher_enabled = vl != 'false'
                elif k == 'downloads_enabled': dl_enabled = vl != 'false'
                elif k == 'web_login_enabled': web_login_enabled = vl != 'false'
                elif k == 'map_enabled': map_enabled = vl != 'false'
                elif k == 'web_maintenance': web_maintenance = vl == 'true'
                elif k == 'announcement_url': a_url = v
                elif k == 'announcement_text': a_text = v
                elif k == 'announcement_active': a_active = vl
    except: pass
    return render_dashboard(HTML_APP_MANAGEMENT, soft_enabled=soft_enabled, launcher_enabled=launcher_enabled, dl_enabled=dl_enabled, web_login_enabled=web_login_enabled, map_enabled=map_enabled, web_maintenance=web_maintenance, deploy_time=DEPLOY_TIME, a_url=a_url, a_text=a_text, a_active=a_active)

async def _trigger_status_update():
    try:
        db = get_db()
        if not db: return
        s_resp = db.table("settings").select("*").in_("setting_key", ["software_enabled", "launcher_enabled", "downloads_enabled", "web_login_enabled", "map_enabled", "web_maintenance"]).execute().data or []
        settings = {}
        for s in s_resp:
            settings[s['setting_key']] = str(s['setting_value']).lower()
            
        soft_enabled = settings.get('software_enabled', 'true') != 'false'
        launcher_enabled = settings.get('launcher_enabled', 'true') != 'false'
        dl_enabled = settings.get('downloads_enabled', 'true') != 'false'
        web_login_enabled = settings.get('web_login_enabled', 'true') != 'false'
        map_enabled = settings.get('map_enabled', 'true') != 'false'
        web_maintenance = settings.get('web_maintenance', 'false') == 'true'

        embed = discord.Embed(title="📡 Stav systémů OIS IDPK", description="Zde naleznete aktuální globální stavy všech služeb.\nTento panel se automaticky aktualizuje.", color=0x38bdf8, timestamp=get_prague_time())
        
        embed.add_field(name="🌍 Web (Údržba)", value="🔴 OFFLINE (Údržba)" if web_maintenance else "🟢 ONLINE", inline=False)
        embed.add_field(name="💻 Herní Software", value="🟢 ONLINE" if soft_enabled else "🔴 OFFLINE", inline=False)
        embed.add_field(name="🚀 Zámek Launcheru", value="🟦 ODEMČEN" if launcher_enabled else "🟦 ZAMëN", inline=False)
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

@app.route('/dashboard/toggle_launcher', methods=['POST'])
@require_dash_level('superadmin')
def toggle_launcher():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        set_setting_db(db, "launcher_enabled", new_status)
        flash(f'Stav Launcheru: {"ZAPNUT" if new_status.lower() == "true" else "VYPNUT"}', 'success')
        adm = get_current_admin_name()
        send_log("🚀 Zámek Launcheru", f"**Uživatel:** {adm}\n**Nový stav:** {'ZAPNUTO' if new_status.lower() == 'true' else 'VYPNUTO'}", 0xf59e0b)
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/set_announcement', methods=['POST'])
@require_dash_level('superadmin')
def set_announcement():
    announcements_json = request.form.get('announcements_json', '[]').strip()
    db = get_db()
    if db:
        set_setting_db(db, "announcement_data", announcements_json)
        flash('Oznámení byla uložena.', 'success')
        adm = get_current_admin_name()
        send_log("📣 Změna Globálních Oznámení", f"**Uživatel:** {adm}\nByla upravena globální oznámení.", 0x38bdf8)
    return redirect(url_for('dashboard_notifications'))

@app.route('/dashboard/toggle_software', methods=['POST'])
@require_dash_level('superadmin')
def toggle_software():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        set_setting_db(db, "software_enabled", new_status)
        flash(f'Stav softwaru: {"ZAPNUT" if new_status.lower() == "true" else "VYPNUT"}', 'success')
        adm = get_current_admin_name()
        send_log("💻 Software / Spouštění hry", f"**Uživatel:** {adm}\n**Nový stav:** {'ZAPNUTO' if new_status.lower() == 'true' else 'VYPNUTO'}", 0xf59e0b)
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_downloads', methods=['POST'])
@require_dash_level('superadmin')
def toggle_downloads():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        set_setting_db(db, "downloads_enabled", new_status)
        flash(f'Stahování: {"POVOLENO" if new_status.lower() == "true" else "ZAKÁZÁNO"}', 'success')
        adm = get_current_admin_name()
        send_log("⬇️ Stahování hry v Launcheru", f"**Uživatel:** {adm}\n**Nový stav:** {'POVOLENO' if new_status.lower() == 'true' else 'ZAKÁZÁNO'}", 0x3b82f6)
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
        set_setting_db(db, "web_login_enabled", new_status)
        adm = get_current_admin_name()
        send_log("🔐 Přihlašování na Web", f"**Uživatel:** {adm}\nPřihlašování na web bylo **{'POVOLENO' if new_status.lower() == 'true' else 'ZABLOKOVANÉ'}** přes dashboard.", 0xf59e0b)
        flash(f'Přihlašování na web: {"POVOLENO" if new_status.lower() == "true" else "ZABLOKOVANÉ"}', 'success')
        trigger_status_channel_update()
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_map', methods=['POST'])
@require_dash_level('superadmin')
def toggle_map():
    new_status = request.form.get('new_status', 'True')
    db = get_db()
    if db:
        if set_setting_db(db, "map_enabled", new_status):
            adm = get_current_admin_name()
            send_log("🗺️ Interaktivní Mapa", f"**Uživatel:** {adm}\nMapa byla **{'ZAPNUTA' if new_status.lower() == 'true' else 'VYPNUTA'}** přes dashboard.", 0x38bdf8)
            flash(f'Mapa: {"ZAPNUTA" if new_status.lower() == "true" else "VYPNUTA"}', 'success')
            trigger_status_channel_update()
        else:
            flash('Chyba: Databáze je nedostupná (limit vyčerpán), nastavení nelze změnit.', 'error')
    return redirect(url_for('dashboard_app_management'))

@app.route('/dashboard/toggle_maintenance', methods=['POST'])
@require_dash_level('superadmin')
def toggle_maintenance():
    new_status = request.form.get('new_status', 'False')
    db = get_db()
    if db:
        if set_setting_db(db, "web_maintenance", new_status):
            adm = get_current_admin_name()
            if new_status.lower() == 'true':
                send_log("🚧 Maintenance Mode ZAPNUT", f"**Uživatel:** {adm}\nWeb byl přepnut do maintenance módu. Probíhá přesměrování všech návštěvníků na /blocked.", 0xef4444)
            else:
                send_log("✅ Maintenance Mode VYPNUT", f"**Uživatel:** {adm}\nWeb byl obnoven z maintenance módu.", 0x10b981)
            flash(f'Maintenance: {"ZAPNUT - WEB JE OFFLINE" if new_status.lower() == "true" else "VYPNUT - WEB JE ONLINE"}', 'success' if new_status.lower() == 'false' else 'warning')
            trigger_status_channel_update()
        else:
            flash('Chyba: Databáze je nedostupná (limit vyčerpán), nastavení nelze změnit.', 'error')
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
    announcements_json = '[]'
    
    # Legacy fallbacks
    a_url = ''; a_text = ''; a_active = 'false'; a_title = ''
    try:
        db = get_db()
        if db:
            s_resp = db.table("settings").select("*").in_("setting_key", ["announcement_data", "announcement_url", "announcement_text", "announcement_title", "announcement_active"]).execute().data or []
            has_data = False
            for s in s_resp:
                if s['setting_key'] == 'announcement_data': 
                    announcements_json = s['setting_value']
                    has_data = True
                elif s['setting_key'] == 'announcement_url': a_url = s['setting_value']
                elif s['setting_key'] == 'announcement_text': a_text = s['setting_value']
                elif s['setting_key'] == 'announcement_title': a_title = s['setting_value']
                elif s['setting_key'] == 'announcement_active': a_active = str(s['setting_value']).lower()
            
            if not has_data and a_url and a_text:
                # Migrate legacy to JSON format if present
                import json
                fallback = [{"id": "1", "active": (a_active == 'true'), "urls": a_url, "title": a_title, "text": a_text}]
                announcements_json = json.dumps(fallback)
                
            msgs = db.table("app_messages").select("*").order("created_at", desc=True).execute().data or []
            now = get_prague_time().replace(tzinfo=None)
            for m in msgs:
                is_arch = m.get('is_archived') in (1, '1', True, 'true', 'True')
                if not is_arch:
                    exp_str = m.get('expires_at')
                    if exp_str and str(exp_str).strip():
                        try:
                            exp_dt = datetime.strptime(str(exp_str).strip(), "%d.%m.%Y %H:%M")
                            if now > exp_dt:
                                db.table("app_messages").update({"is_archived": 1}).eq("message_id", m["message_id"]).execute()
                                is_arch = True
                        except: pass
                m['is_archived'] = is_arch
                m['repeat'] = m.get('repeat') in (1, '1', True, 'true', 'True')
            messages = msgs
    except: pass
    return render_dashboard(HTML_NOTIFICATIONS, messages=messages, deploy_time=DEPLOY_TIME, announcements_json=announcements_json)

@app.route('/dashboard/sprava-notifikaci', methods=['GET'], strict_slashes=False)
@app.route('/dashboard/notifikace', methods=['GET'], strict_slashes=False)
@require_dash_level('admin')
def dashboard_notifications_management():
    admin_nick = get_current_admin_name()
    return render_dashboard(HTML_DASHBOARD_NOTIFICATIONS_MGMT, admin_nick=admin_nick, deploy_time=DEPLOY_TIME)


@app.route('/dashboard/interaktivni-mapa', methods=['GET'], strict_slashes=False)
@require_dash_level('admin')
def dashboard_interaktivni_mapa():
    admin_nick = get_current_admin_name()
    return render_dashboard(HTML_INTERAKTIVNI_MAPA_DASHBOARD, admin_nick=admin_nick, deploy_time=DEPLOY_TIME)

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
    versions = []; enabled = True; launcher_url = ""
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if set_resp and str(set_resp[0].get('setting_value')).lower() == 'false': enabled = False
            
            url_resp = db.table("settings").select("setting_value").eq("setting_key", "launcher_download_url").execute().data or []
            if url_resp: launcher_url = url_resp[0].get("setting_value", "")
            
            versions = db.table("software_versions").select("*").order("id", desc=True).execute().data or []
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled, deploy_time=DEPLOY_TIME, launcher_url=launcher_url)

@app.route('/dashboard/update_launcher_url', methods=['POST'])
@require_dash_level('superadmin')
def dashboard_update_launcher_url():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
        
    new_url = request.form.get('launcher_url', '').strip()
    db = get_db()
    if db:
        check = db.table("settings").select("id").eq("setting_key", "launcher_download_url").execute().data
        if check:
            db.table("settings").update({"setting_value": new_url}).eq("setting_key", "launcher_download_url").execute()
        else:
            db.table("settings").insert({"setting_key": "launcher_download_url", "setting_value": new_url}).execute()
        flash('Odkaz na Launcher byl úspěšně aktualizován.', 'success')
        adm = get_current_admin_name()
        send_log("🔗 Změna odkazu Launcheru", f"**Uživatel:** {adm}\n**Nový odkaz:** {new_url}", 0x3b82f6)
    return redirect(url_for('dashboard_downloads'))

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
            "is_active": 1 if request.form.get("is_active") else 0,
            "eol_date": "",
            "show_in_launcher": 1 if request.form.get("show_in_launcher") else 0,
            "can_download": 1 if request.form.get("can_download") else 0,
            "can_launch": 1 if request.form.get("can_launch") else 0,
        }
        db.table("software_versions").insert(row).execute()
        flash('Nová verze vydána!', 'success')
        adm = get_current_admin_name()
        send_log("🚀 Vydána nová verze", f"**Uživatel:** {adm}\n**Název:** {row['version_name']}\n**Role:** {row['target_role']}", 0x10b981)
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
            "is_active": 1 if request.form.get("is_active") else 0,
            "eol_date": request.form.get("eol_date", ""),
            "show_in_launcher": 1 if request.form.get("show_in_launcher") else 0,
            "can_download": 1 if request.form.get("can_download") else 0,
            "can_launch": 1 if request.form.get("can_launch") else 0,
        }
        db.table("software_versions").update(row).eq("id", request.form.get("version_id")).execute()
        flash('Verze upravena.', 'success')
        adm = get_current_admin_name()
        send_log("✏️ Úprava verze", f"**Uživatel:** {adm}\n**Název:** {row['version_name']}\n**Aktivní:** {'Ano' if row['is_active'] else 'Ne'}", 0xf59e0b)
        trigger_setup_messages_update()
    except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))


@app.route('/api/launcher/email_poll', methods=['POST'])
def api_launcher_email_poll():
    email = request.json.get('email') if request.is_json else None
    if not email: return jsonify({"status": "error"})
    try:
        db = get_db()
        user = db.table("users").select("web_session_token, discord_id, id, email, nick").eq("email", email).execute().data
        if user:
            return jsonify({
                "status": "success",
                "web_session_token": user[0].get("web_session_token"),
                "discord_id": user[0].get("discord_id") or f"email-{user[0].get('id')}",
                "email": user[0].get("email"),
                "nick": user[0].get("nick") or user[0].get("email")
            })
    except: pass
    return jsonify({"status": "error"})

@app.route('/api/launcher/email_verify', methods=['POST'])
def api_launcher_email_verify():
    email = request.json.get('email') if request.is_json else None
    code = request.json.get('code') if request.is_json else None
    if not email or not code: return jsonify({"status": "error", "message": "Missing email or code"})
    try:
        db = get_db()
        user = db.table("users").select("*").eq("email", email).eq("login_token", code).execute().data
        if user:
            u = user[0]
            db.table("users").update({"login_token": ""}).eq("id", u.get("id")).execute()
            return jsonify({
                "status": "success",
                "discord_id": u.get("discord_id") or f"email-{u.get('id')}",
                "email": u.get("email"),
                "nick": u.get("nick") or u.get("email")
            })
    except: pass
    return jsonify({"status": "error", "message": "Invalid code or expired"})

@app.route('/api/launcher/user_info', methods=['POST'])
def api_launcher_user_info():
    discord_id = request.json.get('discord_id') if request.is_json else None
    if not discord_id: return jsonify({"status": "error"})
    try:
        db = get_db()
        user = db.table("users").select("role, avatar_url").eq("discord_id", discord_id).execute().data
        if user:
            return jsonify({
                "status": "success",
                "role": user[0].get("role", "User"),
                "avatar_url": user[0].get("avatar_url")
            })
    except: pass
    return jsonify({"status": "error"})

@app.route('/api/launcher/versions')
def api_launcher_versions():
    """
    Vrátí seznam verzí pro Launcher podle role uživatele.
    Launcher posílá discord_id nebo email-<id> jako query param.
    """
    discord_id = request.args.get('discord_id', '')
    user_role = 'User'
    
    try:
        db = get_db()
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "launcher_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return jsonify({"status": "error", "message": "Launcher je z důvodu údržby dočasně uzamčen administrátorem."})
    except:
        pass

    try:
        db = get_db()
        if discord_id:
            role, is_banned = get_cached_user_role(discord_id)
            if is_banned:
                return jsonify({"status": "banned", "message": "Tento účet má BAN."})
            user_role = role
        
        all_versions = db.table('software_versions').select('*').eq('is_active', True).order('id', desc=True).execute().data or []
        
        ROLE_HIERARCHY = {'User': 1, 'BT': 2, 'DEV': 3, 'SA': 4}
        def user_level(r):
            for key in ['SA','DEV','BT']:
                if key in r: return ROLE_HIERARCHY.get(key, 1)
            return 1
        
        u_level = user_level(user_role)
        result = []
        for v in all_versions:
            v_role = v.get('target_role', 'User')
            v_level = ROLE_HIERARCHY.get(v_role, 1)
            has_access = u_level >= v_level
            show_l = v.get('show_in_launcher', 1)
            is_show = bool(show_l) and str(show_l).lower() not in ('0', 'false')
            can_dl = bool(v.get('can_download', 1)) and str(v.get('can_download', 1)).lower() not in ('0', 'false') and has_access
            can_ln = bool(v.get('can_launch', 1)) and str(v.get('can_launch', 1)).lower() not in ('0', 'false') and has_access
            result.append({
                'id': v.get('id'),
                'version_name': v.get('version_name'),
                'db_version': v.get('db_version'),
                'file_url': v.get('file_url') if has_access else None,
                'target_role': v_role,
                'show_in_launcher': is_show,
                'can_download': can_dl,
                'can_launch': can_ln,
                'has_access': has_access,
                'eol_date': v.get('eol_date', ''),
            })
        return jsonify({'status': 'ok', 'versions': result, 'user_role': user_role})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/dashboard/delete_version', methods=['POST'])
@require_dash_level('superadmin')
def delete_version():
    try:
        vid = request.form.get("version_id")
        get_db().table("software_versions").delete().eq("id", vid).execute()
        flash('Verze smazána.', 'success')
        adm = get_current_admin_name()
        send_log("🗑️ Smazána verze aplikace", f"**Uživatel:** {adm}\n**ID verze:** {vid}", 0xef4444)
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

def get_bot_loop():
    """Bezpečně získá běžící asyncio loop Discord bota bez vyvolání AttributeError v Discord.py 2.0+."""
    global BOT_ASYNC_LOOP
    try:
        if BOT_ASYNC_LOOP and BOT_ASYNC_LOOP.is_running():
            return BOT_ASYNC_LOOP
    except Exception:
        pass
    try:
        loop = getattr(bot, 'loop', None) or getattr(bot, '_loop', None)
        if loop and hasattr(loop, 'is_running') and loop.is_running():
            return loop
    except Exception:
        pass
    return None

@app.route('/dashboard/feedback_reset_hwid', methods=['POST'])
@require_dash_level('admin')
def feedback_reset_hwid():
    fb_id = request.form.get("feedback_id"); d_id = request.form.get("discord_id")
    db = get_db()
    if db and fb_id and d_id:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        db.table("users").update({"hwid": "", "ip_address": ""}).eq("discord_id", d_id).execute()
        db.table("feedback").update({"status": "resolved", "sys_note": f"HWID a IP resetovány [{now_str}]"}).eq("id", fb_id).execute()
        b_loop = get_bot_loop()
        if b_loop:
            asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "🔄 Zámek PC Resetován", "Vaše žádost byla schválena. HWID a IP adresa byly resetovány.", 0x10b981), b_loop)
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
        b_loop = get_bot_loop()
        if d_id and b_loop:
            asyncio.run_coroutine_threadsafe(send_user_dm(d_id, "❌ Žádost zamítnuta", f"**Důvod:** {reason}", 0xef4444), b_loop)
        flash('Žádost zamítnuta.', 'success')
    return redirect(url_for('dashboard_feedback'))

def dispatch_feedback_reply(fb_row, reply_text, delivery_channel="auto"):
    """
    Spolehlivě doručí odpověď na zpětnou vazbu / dotaz uživateli.
    Podporuje Discord DM, E-mail i automatický fallback.
    Vrací trojici: (is_success, detail_message, sys_note_string)
    """
    db = get_db()
    reply_pref = (fb_row.get("reply_pref") or "discord").lower().strip()
    target_email = str(fb_row.get("contact_email") or "").strip()
    target_discord = str(fb_row.get("contact_discord") or fb_row.get("discord_id") or "").strip()
    user_nick = str(fb_row.get("nick") or "").strip()
    orig_msg = str(fb_row.get("message") or "").strip()

    # Normalizace emailu pokud je zapsán v discord_id sloupci
    if not target_email and "@" in target_discord:
        target_email = target_discord
    if target_discord.startswith("email-") and db:
        try:
            uid = target_discord.split("-")[1]
            u = db.table("users").select("email, discord_id").eq("id", uid).execute().data
            if u:
                if u[0].get("email"): target_email = u[0]["email"]
                if u[0].get("discord_id"): target_discord = str(u[0]["discord_id"])
        except Exception:
            pass

    # Pokud target_discord není číselné snowflake ID, pokusit se dohledat v DB users
    if db and not target_discord.isdigit():
        lookup_candidates = [c for c in [target_discord, user_nick, target_email] if c]
        for c in lookup_candidates:
            try:
                col = "email" if "@" in c else "nick"
                u = db.table("users").select("discord_id, email").ilike(col, c).execute().data
                if u and u[0].get("discord_id"):
                    target_discord = str(u[0]["discord_id"])
                    if not target_email and u[0].get("email"):
                        target_email = str(u[0]["email"])
                    break
            except Exception:
                pass

    results = []
    discord_sent = False
    email_sent = False

    # 1. Odeslání do Discord DM
    want_discord = (delivery_channel in ("discord", "both")) or (delivery_channel == "auto" and reply_pref != "email")
    if want_discord:
        if target_discord:
            b_loop = get_bot_loop()
            if b_loop:
                try:
                    fields = [("Vaše původní zpráva", orig_msg[:1000])] if orig_msg else None
                    fut = asyncio.run_coroutine_threadsafe(
                        send_user_dm(target_discord, "📩 Odpověď na vaši zpětnou vazbu / dotaz", reply_text, 0x38bdf8, fields=fields),
                        b_loop
                    )
                    ok = fut.result(timeout=6.0)
                    if ok:
                        discord_sent = True
                        results.append("Discord DM doručeno")
                    else:
                        from interaktivnimapa import NOTIFICATION_DM_QUEUE
                        NOTIFICATION_DM_QUEUE.put({
                            "discord_id": target_discord,
                            "email": None,
                            "dm_text": f"📩 **Odpověď na vaši zpětnou vazbu / dotaz**\n\n{reply_text}",
                            "embed": {
                                "title": "📩 Odpověď na vaši zpětnou vazbu / dotaz",
                                "description": reply_text,
                                "color": 0x38bdf8,
                                "fields": ([{"name": "Vaše původní zpráva", "value": orig_msg[:1000]}] if orig_msg else [])
                            },
                            "rule_id": f"admin_reply_{int(time.time())}",
                            "trigger": "admin_feedback_reply",
                        })
                        results.append("Discord DM zařazeno do fronty (bot se připojuje)")
                        discord_sent = True
                except Exception as e_fut:
                    results.append(f"Discord DM chyba: {e_fut}")
            else:
                from interaktivnimapa import NOTIFICATION_DM_QUEUE
                NOTIFICATION_DM_QUEUE.put({
                    "discord_id": target_discord,
                    "email": None,
                    "dm_text": f"📩 **Odpověď na vaši zpětnou vazbu / dotaz**\n\n{reply_text}",
                    "embed": {
                        "title": "📩 Odpověď na vaši zpětnou vazbu / dotaz",
                        "description": reply_text,
                        "color": 0x38bdf8,
                        "fields": ([{"name": "Vaše původní zpráva", "value": orig_msg[:1000]}] if orig_msg else [])
                    },
                    "rule_id": f"admin_reply_{int(time.time())}",
                    "trigger": "admin_feedback_reply",
                })
                results.append("Discord DM zařazeno do fronty (bot se připojuje)")
                discord_sent = True
        else:
            results.append("Discord DM: Chybí číselné Discord ID")

    # 2. Odeslání na E-mail
    want_email = (delivery_channel in ("email", "both")) or (delivery_channel == "auto" and reply_pref == "email")
    # Pokud byla volba auto na Discord, ale Discord DM selhalo a máme e-mail, zkusit e-mail jako záchranu
    if not discord_sent and delivery_channel == "auto" and target_email and "@" in target_email:
        want_email = True

    if want_email:
        if target_email and "@" in target_email:
            if SMTP_EMAIL and SMTP_PASSWORD:
                try:
                    embed_data = {
                        "title": "📩 Odpověď na vaši zprávu / dotaz",
                        "description": reply_text,
                        "fields": [{"name": "Vaše původní zpráva", "value": orig_msg}] if orig_msg else []
                    }
                    send_notification_email_sync(target_email, embed_data, reply_text, is_one_time=True)
                    email_sent = True
                    results.append(f"E-mail odeslán na {target_email}")
                except Exception as e_em:
                    results.append(f"E-mail chyba: {e_em}")
            else:
                results.append("E-mail: SMTP server není nastaven")
        else:
            results.append("E-mail: Chybí platná e-mailová adresa")

    # Pokud byla volba na E-mail, ale ten selhal a máme Discord ID, zkusit Discord DM jako záchranu
    if not email_sent and not discord_sent and delivery_channel == "auto" and target_discord:
        b_loop = get_bot_loop()
        if b_loop:
            try:
                fields = [("Vaše původní zpráva", orig_msg[:1000])] if orig_msg else None
                fut = asyncio.run_coroutine_threadsafe(
                    send_user_dm(target_discord, "📩 Odpověď na vaši zpětnou vazbu / dotaz", reply_text, 0x38bdf8, fields=fields),
                    b_loop
                )
                ok = fut.result(timeout=6.0)
                if ok:
                    discord_sent = True
                    results.append("Discord DM doručeno (záchranný fallback)")
            except Exception:
                pass

    status_tag = []
    if discord_sent: status_tag.append("Discord DM")
    if email_sent: status_tag.append("E-mail")
    tag_str = f" [doručeno přes {', '.join(status_tag)}]" if status_tag else f" [uloženo v DB; {' | '.join(results)}]"

    now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
    sys_note_msg = f"Odpověď: {reply_text.strip()}{tag_str} [{now_str}]"
    return (discord_sent or email_sent), "; ".join(results), sys_note_msg

@app.route('/dashboard/feedback_resolve', methods=['POST'])
def feedback_resolve():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    fb_id = request.form.get("feedback_id")
    reply_text = request.form.get("reply_text")
    delivery_channel = request.form.get("delivery_channel", "auto")
    db = get_db()
    if db and fb_id:
        fb_data = db.table("feedback").select("*").eq("id", fb_id).execute()
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
        sys_note_msg = f"Vyřešeno [{now_str}]"
        
        if fb_data.data and reply_text and reply_text.strip():
            f_row = fb_data.data[0]
            ok, detail_msg, sys_note_msg = dispatch_feedback_reply(f_row, reply_text.strip(), delivery_channel)
            if ok:
                flash(f'Odpověď úspěšně odeslána: {detail_msg}', 'success')
            else:
                flash(f'Odpověď uložena, ale doručení selhalo: {detail_msg}', 'warning')
        else:
            flash('Ticket uzavřen.', 'success')
                
        db.table("feedback").update({"status": "resolved", "sys_note": sys_note_msg}).eq("id", fb_id).execute()
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
    fb_id = request.form.get("feedback_id")
    msg = request.form.get("message") or request.form.get("reply_text")
    delivery_channel = request.form.get("delivery_channel", "auto")
    db = get_db()
    if db and fb_id and msg:
        fb_data = db.table("feedback").select("*").eq("id", fb_id).execute()
        if fb_data.data:
            f_row = fb_data.data[0]
            ok, detail_msg, sys_note_msg = dispatch_feedback_reply(f_row, msg.strip(), delivery_channel)
            db.table("feedback").update({"status": "resolved", "sys_note": sys_note_msg}).eq("id", fb_id).execute()
            if ok:
                flash(f'Odpověď odeslána: {detail_msg}', 'success')
            else:
                flash(f'Odpověď uložena: {detail_msg}', 'warning')
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
            adm = get_current_admin_name()
            send_log("📡 Změna Systémových Statusů", f"**Uživatel:** {adm}\nByly upraveny statusy systému.", 0x38bdf8)
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
    adm = get_current_admin_name()
    send_log('🔑 Dashboard přístup udělen', f'**Správce:** {adm}\nUživateli **{user[0].get("nick", discord_id)}** (`{discord_id}`) byl udělen přístup do dashboardu se úrovní **{level}**.', 0x38bdf8)
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
    adm = get_current_admin_name()
    send_log('🔒 Dashboard přístup odebrán', f'**Správce:** {adm}\nUživateli **{nick}** (`{discord_id}`) byl odebrán dashboard přístup.', 0xef4444)
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
        adm = get_current_admin_name()
        send_log('🛡️ Změna Admin Úrovně', f'**Správce:** {adm}\nUživateli `{discord_id}` byla nastavena úroveň **{level}**.', 0x38bdf8)
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

def _has_admin_perms(member_or_user, guild=None):
    try:
        uid = str(member_or_user.id)
        # Bot owner / developer Marek
        if uid in ("719896287301992449",):
            return True
        if guild and hasattr(member_or_user, "roles"):
            if getattr(member_or_user, "guild_permissions", None) and member_or_user.guild_permissions.administrator:
                return True
            role_names = [r.name.lower() for r in member_or_user.roles]
            if any(r in role_names for r in ["sm", "web-sa", "sa", "dev", "admin", "správce", "spravce", "moderator", "server manager"]):
                return True
        # Zkontroluj roli uživatele v databázi users (funguje i v DM)
        db = get_db()
        if db:
            u_data = db.table("users").select("role").eq("discord_id", uid).execute().data
            if u_data:
                role_val = str(u_data[0].get("role", "")).upper()
                if any(x in role_val for x in ["SA", "DEV", "SM", "ADMIN", "SUPERADMIN"]):
                    return True
    except Exception as e:
        print(f"[AUTH ERROR] _has_admin_perms error: {e}", flush=True)
    return False

def check_web_sa():
    async def predicate(ctx):
        if _has_admin_perms(ctx.author, ctx.guild): return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění.", delete_after=10)
        return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if _has_admin_perms(ctx.author, ctx.guild): return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění.", delete_after=10)
        return False
    return commands.check(predicate)

_last_depot_discord_run = 0.0

@tasks.loop(seconds=5)
async def check_depot_queue():
    global _last_depot_discord_run
    try:
        updated = False
        while not DEPOT_DISCORD_QUEUE.empty():
            msg = DEPOT_DISCORD_QUEUE.get_nowait()
            if msg.get("type") == "update_all":
                updated = True
        if updated:
            now_t = time.time()
            min_depot_interval = 60.0 if (EGRESS_SAVE_MODE or is_supabase_restricted()) else 25.0
            if now_t - _last_depot_discord_run >= min_depot_interval:
                _last_depot_discord_run = now_t
                await update_depot_discord_messages()
            else:
                # Pokud ještě neuběhl limit, zachovej událost ve frontě
                DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
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
            rule_id = item.get("rule_id")
            queue_id = item.get("queue_id")
            is_one_time = bool(item.get("is_one_time"))

            # Pošli Discord DM
            if discord_id:
                try:
                    d_id = int(str(discord_id).strip())
                    user = await bot.fetch_user(d_id)
                    sent_ok = False

                    # Sestavení tlačítek (View) pro Discord DM
                    view = None
                    try:
                        view = discord.ui.View()
                        if rule_id and str(rule_id).startswith("admin_direct"):
                            view.add_item(discord.ui.Button(label="ℹ️ Proč mi přišla zpráva?", url="https://datacorebot.koyeb.app/proc-notifikace?typ=admin", style=discord.ButtonStyle.link))
                            view.add_item(discord.ui.Button(label="💬 Podpora a odpověď", url="https://datacorebot.koyeb.app/podpora", style=discord.ButtonStyle.link))
                        else:
                            if not is_one_time and rule_id:
                                unsub_href = f"https://datacorebot.koyeb.app/api/notifications/unsubscribe?id={rule_id}"
                                view.add_item(discord.ui.Button(label="🔕 Vypnout notifikace", url=unsub_href, style=discord.ButtonStyle.link))
                            view.add_item(discord.ui.Button(label="ℹ️ Proč mi chodí upozornění?", url="https://datacorebot.koyeb.app/proc-notifikace", style=discord.ButtonStyle.link))
                    except Exception as e_v:
                        view = None

                    if embed_data:
                        try:
                            title_txt = str(embed_data.get("title", "🔔 Upozornění")).replace("\r", "").replace("\n", " ")[:250]
                            desc_txt = str(embed_data.get("description", ""))[:2000]
                            em = discord.Embed(
                                title=title_txt,
                                description=desc_txt,
                                color=embed_data.get("color", 0x38bdf8)
                            )
                            for field in embed_data.get("fields", []):
                                f_name = str(field.get("name") or "Info")[:256].strip() or "Info"
                                f_val = str(field.get("value") or "-")[:1024].strip() or "-"
                                em.add_field(name=f_name, value=f_val, inline=field.get("inline", False))
                            em.set_footer(text=str(embed_data.get("footer", {}).get("text", "OIS IDPK"))[:2000])
                            
                            img_dict = embed_data.get("image")
                            img_url = (img_dict.get("url") if isinstance(img_dict, dict) else img_dict) if img_dict else None
                            discord_file = None
                            if img_url:
                                try:
                                    img_str = str(img_url).strip()
                                    if img_str.startswith("data:image/"):
                                        import base64
                                        import io
                                        header, b64_data = img_str.split(",", 1)
                                        ext = "png"
                                        if "jpeg" in header or "jpg" in header: ext = "jpg"
                                        elif "webp" in header: ext = "webp"
                                        elif "gif" in header: ext = "gif"
                                        img_bytes = base64.b64decode(b64_data)
                                        fname = f"notification_image.{ext}"
                                        discord_file = discord.File(io.BytesIO(img_bytes), filename=fname)
                                        em.set_image(url=f"attachment://{fname}")
                                    elif img_str.startswith("http://") or img_str.startswith("https://"):
                                        try:
                                            import urllib.request
                                            import io
                                            req = urllib.request.Request(img_str, headers={'User-Agent': 'Mozilla/5.0'})
                                            with urllib.request.urlopen(req, timeout=5) as resp:
                                                img_bytes = resp.read()
                                            ext = "png"
                                            if ".jpg" in img_str.lower() or ".jpeg" in img_str.lower(): ext = "jpg"
                                            elif ".webp" in img_str.lower(): ext = "webp"
                                            elif ".gif" in img_str.lower(): ext = "gif"
                                            fname = f"notification_image.{ext}"
                                            discord_file = discord.File(io.BytesIO(img_bytes), filename=fname)
                                            em.set_image(url=f"attachment://{fname}")
                                        except Exception:
                                            em.set_image(url=img_str)
                                except Exception as e_img:
                                    print(f"[NOTIF DM IMAGE ERR] {e_img}", flush=True)

                            send_kwargs = {"embed": em}
                            if discord_file:
                                send_kwargs["file"] = discord_file
                            if view:
                                send_kwargs["view"] = view
                            try:
                                await user.send(**send_kwargs)
                                sent_ok = True
                            except Exception:
                                if view:
                                    send_kwargs.pop("view", None)
                                    try:
                                        await user.send(**send_kwargs)
                                        sent_ok = True
                                    except Exception:
                                        pass
                                if not sent_ok and discord_file:
                                    send_kwargs.pop("file", None)
                                    try:
                                        await user.send(**send_kwargs)
                                        sent_ok = True
                                    except Exception:
                                        pass
                        except Exception as e_embed:
                            print(f"[NOTIF DM EMBED FAIL] {e_embed}, zkouším poslat prostý text...", flush=True)
                    if not sent_ok and dm_text:
                        try:
                            if view:
                                await user.send(dm_text[:2000], view=view)
                            else:
                                await user.send(dm_text[:2000])
                            sent_ok = True
                        except Exception:
                            try:
                                await user.send(dm_text[:2000])
                                sent_ok = True
                            except Exception:
                                pass
                    if sent_ok:
                        print(f"[NOTIF DM] Odesláno DM uživateli {discord_id}", flush=True)
                        if queue_id:
                            try:
                                from interaktivnimapa import NOTIFICATION_DELIVERY_TRACKER
                                NOTIFICATION_DELIVERY_TRACKER[queue_id] = {
                                    "status": "delivered",
                                    "time": get_prague_time().strftime("%H:%M:%S"),
                                    "detail": "Zpráva byla úspěšně doručena do Discord DM"
                                }
                            except Exception: pass
                        try:
                            from daily_reporter import TRACKER
                            TRACKER.record_notification("discord", True)
                        except Exception: pass
                    else:
                        if queue_id:
                            try:
                                from interaktivnimapa import NOTIFICATION_DELIVERY_TRACKER
                                NOTIFICATION_DELIVERY_TRACKER[queue_id] = {
                                    "status": "failed",
                                    "detail": "Uživatel má vypnuté soukromé zprávy nebo odmítl doručení"
                                }
                            except Exception: pass
                except discord.Forbidden:
                    print(f"[NOTIF DM] Uživatel {discord_id} má zablokované přímé zprávy (DM)!", flush=True)
                    if queue_id:
                        try:
                            from interaktivnimapa import NOTIFICATION_DELIVERY_TRACKER
                            NOTIFICATION_DELIVERY_TRACKER[queue_id] = {
                                "status": "failed",
                                "detail": "Uživatel má v nastavení Discordu zakázané soukromé zprávy (DM) od členů serveru"
                            }
                        except Exception: pass
                    try:
                        send_log("⚠️ NOTIFIKACE: Nelze doručit DM", f"Uživateli <@{discord_id}> nelze odeslat soukromou zprávu (DM), protože má v nastavení Discordu zakázané zprávy od členů serveru.\nNotifikace:\n{dm_text[:400]}", 0xf59e0b, channel_name="📲・error-app")
                    except Exception: pass
                except Exception as e:
                    print(f"[NOTIF DM] Chyba při odesílání DM {discord_id}: {e}", flush=True)
                    if queue_id:
                        try:
                            from interaktivnimapa import NOTIFICATION_DELIVERY_TRACKER
                            NOTIFICATION_DELIVERY_TRACKER[queue_id] = {
                                "status": "failed",
                                "detail": "Uživatel s tímto ID nebyl na Discordu nalezen"
                            }
                        except Exception: pass
                    try:
                        from daily_reporter import TRACKER
                        TRACKER.record_notification("discord", False, str(e))
                    except Exception: pass
            
            # Pošli Email
            email = item.get("email")
            if email:
                try:
                    await asyncio.to_thread(send_notification_email_sync, email, embed_data, dm_text, rule_id, is_one_time)
                    print(f"[NOTIF EMAIL] Odeslán e-mail uživateli {email}", flush=True)
                    try:
                        from daily_reporter import TRACKER
                        TRACKER.record_notification("email", True)
                    except Exception: pass
                except Exception as e:
                    print(f"[NOTIF EMAIL] Chyba při odesílání emailu {email}: {e}", flush=True)
                    try:
                        from daily_reporter import TRACKER
                        TRACKER.record_notification("email", False, str(e))
                    except Exception: pass
    except Exception as e:
        print(f"[NOTIF DM] Chyba fronty: {e}", flush=True)

def send_notification_email_sync(to_email, embed_data, dm_text, rule_id=None, is_one_time=False):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        raise RuntimeError("SMTP přihlašovací údaje (SMTP_EMAIL / SMTP_PASSWORD) nejsou nastaveny")
    to_email = str(to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError(f"Neplatná e-mailová adresa příjemce: '{to_email}'")
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        import smtplib
        import base64
        import re
        import os
        
        msg = MIMEMultipart("related")
        msg["Subject"] = embed_data.get("title", "🔔 Upozornění na autobus") if embed_data else "🔔 Upozornění na autobus"
        msg["From"] = f"DataCore Bot <{SMTP_EMAIL}>"
        msg["To"] = to_email

        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)

        # 1. Logo DataCoreBot jako inline CID příloha
        logo_cid_available = False
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "static", "img", "datacorebot_n.png")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f_logo:
                    logo_mime = MIMEImage(f_logo.read(), _subtype="png")
                    logo_mime.add_header('Content-ID', '<datacore_logo>')
                    logo_mime.add_header('Content-Disposition', 'inline', filename='datacorebot_logo.png')
                    msg.attach(logo_mime)
                    logo_cid_available = True
        except Exception as e_l:
            print(f"[EMAIL LOGO ERR] {e_l}", flush=True)

        # 2. Přiložený obrázek od uživatele/admina
        img_dict = embed_data.get("image") if embed_data else None
        img_url = (img_dict.get("url") if isinstance(img_dict, dict) else img_dict) if img_dict else None
        attached_cid_available = False
        attached_ext = "png"
        if img_url:
            try:
                img_bytes = None
                img_str = str(img_url).strip()
                if img_str.startswith("data:image/"):
                    hdr, b64_d = img_str.split(",", 1)
                    if "jpeg" in hdr or "jpg" in hdr: attached_ext = "jpeg"
                    elif "webp" in hdr: attached_ext = "webp"
                    elif "gif" in hdr: attached_ext = "gif"
                    img_bytes = base64.b64decode(b64_d)
                elif img_str.startswith("http://") or img_str.startswith("https://"):
                    try:
                        import urllib.request
                        req = urllib.request.Request(img_str, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            img_bytes = resp.read()
                        if ".jpg" in img_str.lower() or ".jpeg" in img_str.lower(): attached_ext = "jpeg"
                        elif ".webp" in img_str.lower(): attached_ext = "webp"
                        elif ".gif" in img_str.lower(): attached_ext = "gif"
                    except Exception:
                        pass
                
                if img_bytes:
                    att_mime = MIMEImage(img_bytes, _subtype=attached_ext)
                    att_mime.add_header('Content-ID', '<attached_image>')
                    att_mime.add_header('Content-Disposition', 'inline', filename=f'priloha.{attached_ext}')
                    msg.attach(att_mime)
                    attached_cid_available = True
            except Exception as e_att:
                print(f"[EMAIL ATTACH IMAGE ERR] {e_att}", flush=True)

        # Tlačítka pro odhlášení a vysvětlení
        action_buttons_html = ""
        btn_items = []
        is_admin_direct = bool(rule_id and str(rule_id).startswith("admin_direct"))
        if not is_one_time and rule_id and not is_admin_direct:
            unsub_href = f"https://datacorebot.koyeb.app/api/notifications/unsubscribe?id={rule_id}"
            btn_items.append(f'<a href="{unsub_href}" target="_blank" style="display:inline-block;padding:9px 18px;background-color:#ef4444;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:13px;margin-right:10px;margin-bottom:8px;">🔕 Vypnout pravidelné notifikace</a>')

        if is_admin_direct:
            why_href = "https://datacorebot.koyeb.app/proc-notifikace?typ=admin"
            btn_items.append(f'<a href="{why_href}" target="_blank" style="display:inline-block;padding:9px 16px;background-color:#7c3aed;color:#ffffff;text-decoration:none;border-radius:6px;font-size:12px;font-weight:600;margin-right:10px;margin-bottom:8px;">ℹ️ Proč mi přišla tato zpráva od administrátora?</a>')
            support_href = "https://datacorebot.koyeb.app/podpora"
            btn_items.append(f'<a href="{support_href}" target="_blank" style="display:inline-block;padding:9px 16px;background-color:#f1f5f9;color:#475569;text-decoration:none;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;margin-bottom:8px;">💬 Napsat na podporu / Odpovědět</a>')
        else:
            why_href = "https://datacorebot.koyeb.app/proc-notifikace"
            btn_items.append(f'<a href="{why_href}" target="_blank" style="display:inline-block;padding:8px 14px;background-color:#f1f5f9;color:#475569;text-decoration:none;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;margin-bottom:8px;">ℹ️ Proč mi chodí upozornění?</a>')

        if btn_items:
            action_buttons_html = f"""
            <div style="margin-top:24px;padding-top:18px;border-top:1px solid #e2e8f0;text-align:center;">
              {' '.join(btn_items)}
            </div>
            """

        # Header s logem DataCoreBot
        logo_tag = '<img src="cid:datacore_logo" alt="DataCoreBot Logo" style="max-height:48px;width:auto;vertical-align:middle;border:0;display:inline-block;" />' if logo_cid_available else '<img src="https://datacorebot.koyeb.app/static/img/datacorebot_n.png" alt="DataCoreBot Logo" style="max-height:48px;width:auto;vertical-align:middle;border:0;display:inline-block;" />'
        
        email_header = f"""
        <div style="background: linear-gradient(135deg, #0b0f19 0%, #1e1b4b 100%); padding: 26px 20px; border-radius: 12px 12px 0 0; text-align: center; border-bottom: 2px solid #7c3aed;">
          {logo_tag}
          <div style="color: #94a3b8; font-size: 11px; margin-top: 8px; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 700;">Projekt OIS IDPK • Centrální Systém</div>
        </div>
        """

        # Sekce s přiloženým obrázkem
        image_block_html = ""
        if attached_cid_available:
            image_block_html = """
            <div style="margin: 22px 0; background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; text-align: center;">
              <img src="cid:attached_image" alt="Přiložený obrázek" style="max-width: 100%; max-height: 480px; border-radius: 8px; display: block; margin: 0 auto; box-shadow: 0 4px 14px rgba(0,0,0,0.4);" />
              <div style="color: #94a3b8; font-size: 11px; margin-top: 8px;">📷 Přiložený obrázek / screenshot</div>
            </div>
            """
        elif img_url and (str(img_url).startswith("http://") or str(img_url).startswith("https://")):
            image_block_html = f"""
            <div style="margin: 22px 0; background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; text-align: center;">
              <a href="{img_url}" target="_blank">
                <img src="{img_url}" alt="Přiložený obrázek" style="max-width: 100%; max-height: 480px; border-radius: 8px; display: block; margin: 0 auto; box-shadow: 0 4px 14px rgba(0,0,0,0.4);" />
              </a>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">Kliknutím otevřete obrázek v plné velikosti</div>
            </div>
            """

        # Sestavení těla HTML
        if embed_data:
            fields_html = ""
            for f in embed_data.get("fields", []):
                val = str(f.get("value", ""))
                val = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #38bdf8; text-decoration: none;">\1</a>', val)
                fields_html += f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 8px 12px; font-weight: 700; color: #475569; font-size: 13px; width: 35%;">{f.get('name', '')}:</td>
                  <td style="padding: 8px 12px; color: #0f172a; font-size: 13px;">{val}</td>
                </tr>
                """
            
            fields_table = ""
            if fields_html:
                fields_table = f"""
                <table style="width: 100%; border-collapse: collapse; background: #f8fafc; border-radius: 8px; overflow: hidden; margin: 16px 0; border: 1px solid #e2e8f0;">
                  <tbody>
                    {fields_html}
                  </tbody>
                </table>
                """

            title_val = str(embed_data.get("title", "Upozornění")).strip()
            desc_val = str(embed_data.get("description", "")).replace("\n", "<br>")

            html = f"""
            <!DOCTYPE html>
            <html>
              <head><meta charset="utf-8"></head>
              <body style="margin: 0; padding: 20px 10px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                  {email_header}
                  <div style="padding: 28px 24px;">
                    <h2 style="color: #0f172a; margin-top: 0; margin-bottom: 14px; font-size: 20px; font-weight: 700;">{title_val}</h2>
                    <div style="font-size: 15px; color: #334155; line-height: 1.65; margin-bottom: 18px;">{desc_val}</div>
                    {fields_table}
                    {image_block_html}
                    {action_buttons_html}
                  </div>
                  <div style="background: #f8fafc; padding: 16px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                    <div>Hezký den přeje <strong>Tým DataCore Bot & Projekt OIS IDPK</strong></div>
                    <div style="margin-top: 4px; font-size: 11px; color: #94a3b8;">Tato zpráva byla automaticky vygenerována systémem DataCore OIS IDPK.</div>
                  </div>
                </div>
              </body>
            </html>
            """
        else:
            html_text = dm_text.replace("\n", "<br>")
            html_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #38bdf8;">\1</a>', html_text)
            
            html = f"""
            <!DOCTYPE html>
            <html>
              <head><meta charset="utf-8"></head>
              <body style="margin: 0; padding: 20px 10px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                  {email_header}
                  <div style="padding: 28px 24px;">
                    <div style="font-size: 15px; color: #334155; line-height: 1.65;">{html_text}</div>
                    {image_block_html}
                    {action_buttons_html}
                  </div>
                  <div style="background: #f8fafc; padding: 16px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                    <div>Hezký den přeje <strong>Tým DataCore Bot & Projekt OIS IDPK</strong></div>
                    <div style="margin-top: 4px; font-size: 11px; color: #94a3b8;">Tato zpráva byla automaticky vygenerována systémem DataCore OIS IDPK.</div>
                  </div>
                </div>
              </body>
            </html>
            """

        clean_plain_text = re.sub(r'data:image\/[^;]+;base64,[A-Za-z0-9+/=]+', '[Přiložený obrázek]', dm_text)
        msg_alt.attach(MIMEText(clean_plain_text, "plain", "utf-8"))
        msg_alt.attach(MIMEText(html, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[NOTIF EMAIL] Chyba odesílání e-mailu sync: {e}")
        raise e

@app.route('/proc-notifikace')
def stranka_proc_notifikace():
    typ = str(request.args.get('typ', '')).strip().lower()
    is_admin = (typ == 'admin')

    if is_admin:
        html_content = """
        <div style="max-width: 720px; margin: 40px auto; padding: 24px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);">
          <div style="display:flex; align-items:center; gap:16px; margin-bottom:20px; border-bottom:1px solid #334155; padding-bottom:16px;">
            <div style="width:54px; height:54px; border-radius:14px; background:rgba(168,85,247,0.15); border:1px solid #a855f7; display:flex; align-items:center; justify-content:center; font-size:26px; color:#c084fc;">
              <i class="fas fa-user-shield"></i>
            </div>
            <div>
              <h1 style="color:#c084fc; font-size:22px; margin:0 0 4px 0; font-weight:bold;">Proč mi přišla zpráva od administrátora?</h1>
              <p style="color:#94a3b8; font-size:13px; margin:0;">Oficiální sdělení vedení projektu DataCore / OIS IDPK</p>
            </div>
          </div>

          <div style="color:#e2e8f0; font-size:14px; line-height:1.7;">
            <div style="background:rgba(168,85,247,0.12); border-left:4px solid #a855f7; padding:16px 18px; border-radius:0 8px 8px 0; margin:16px 0;">
              <strong style="color:#d8b4fe; font-size:15px;">✉️ Osobní zpráva od administrace</strong><br>
              Tuto zprávu vám zaslal <strong>přímo administrátor systému</strong> (např. <code>marekk_czz</code>).
              <div style="margin-top:6px; color:#cbd5e1;">
                <strong>Nejedná se o automatické sledování autobusů z mapy</strong>, ale o individuální komunikaci vedení projektu DataCore / OIS IDPK.
              </div>
            </div>

            <h3 style="color:#f8fafc; font-size:16px; margin:22px 0 10px 0;">Nejčastější důvody odeslání:</h3>
            <ul style="padding-left:20px; margin:0 0 20px 0; color:#cbd5e1;">
              <li style="margin-bottom:8px;"><strong>Odpověď na vaši žádost nebo dotaz:</strong> Reakce administrátora na vámi nahlášenou chybu, dotaz či požadavek na podporu.</li>
              <li style="margin-bottom:8px;"><strong>Informace k vašemu účtu:</strong> Oznámení o schválení přístupu, resetu HWID zámku nebo důležité provozní upozornění k aplikaci.</li>
              <li style="margin-bottom:8px;"><strong>Provozní a organizační sdělení:</strong> Důležitá zpráva určená přímo vám jako uživateli, řidiči či podporovateli projektu.</li>
            </ul>

            <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.25); border-radius:10px; padding:16px; margin:20px 0;">
              <h4 style="color:#38bdf8; margin:0 0 6px 0; font-size:15px; display:flex; align-items:center; gap:8px;">
                <i class="fas fa-reply"></i> Jak můžete odpovědět?
              </h4>
              <p style="margin:0; font-size:13px; color:#bae6fd;">
                Pokud potřebujete na zprávu reagovat, můžete využít náš kontaktní formulář na stránce podpory nebo napsat přímo na náš oficiální Discord server.
              </p>
            </div>

            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:24px; justify-content:center;">
              <a href="/podpora" style="background:#7c3aed; color:white; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px; box-shadow: 0 4px 12px rgba(124,58,237,0.35);">
                <i class="fas fa-headset"></i> Napsat na podporu / Odpovědět
              </a>
              <a href="/ucet" style="background:#1e293b; border:1px solid #334155; color:#38bdf8; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px;">
                <i class="fas fa-user"></i> Můj účet
              </a>
              <a href="/proc-notifikace" style="background:#1e293b; border:1px solid #334155; color:#94a3b8; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px;">
                <i class="fas fa-bell"></i> Informace o notifikacích z mapy
              </a>
            </div>
          </div>
        </div>
        """
        return render_public(html_content)

    html_content = """
    <div style="max-width: 720px; margin: 40px auto; padding: 24px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);">
      <div style="display:flex; align-items:center; gap:16px; margin-bottom:20px; border-bottom:1px solid #334155; padding-bottom:16px;">
        <div style="width:54px; height:54px; border-radius:14px; background:rgba(56,189,248,0.15); border:1px solid #38bdf8; display:flex; align-items:center; justify-content:center; font-size:26px; color:#38bdf8;">
          <i class="fas fa-bell"></i>
        </div>
        <div>
          <h1 style="color:#38bdf8; font-size:22px; margin:0 0 4px 0; font-weight:bold;">Proč mi chodí upozornění?</h1>
          <p style="color:#94a3b8; font-size:13px; margin:0;">Vysvětlení notifikací systému OIS IDPK</p>
        </div>
      </div>

      <div style="color:#e2e8f0; font-size:14px; line-height:1.7;">
        <p>
          Tato zpráva vám dorazila, protože je na váš účet, e-mail nebo Discord navázáno aktivní sledování autobusu či linky.
        </p>

        <div style="background:rgba(56,189,248,0.08); border-left:4px solid #38bdf8; padding:14px 18px; border-radius:0 8px 8px 0; margin:18px 0;">
          <strong style="color:#38bdf8;">📍 Kde se notifikace vzala?</strong><br>
          S největší pravděpodobností jste si toto upozornění <strong>sami zaklikli na naší interaktivní mapě</strong>.
          Při prohlížení autobusu, spoje nebo zastávky stačí kliknout na ikonu zvonečku 🔔 a vybrat si sledované události (např. příjezd k zastávce, konečná stanice, výjezd z vozovny, zpoždění apod.).
        </div>

        <h3 style="color:#f8fafc; font-size:16px; margin:22px 0 10px 0;">Co můžete udělat, pokud už upozornění nechcete?</h3>
        <ul style="padding-left:20px; margin:0 0 20px 0; color:#cbd5e1;">
          <li style="margin-bottom:8px;"><strong>Vypnout jedním kliknutím:</strong> V každé pravidelné notifikaci (v e-mailu i na Discordu) je přímé tlačítko <em>🔕 Vypnout notifikace</em>. Kliknutím na něj se pravidlo ihned zruší.</li>
          <li style="margin-bottom:8px;"><strong>Správa v účtu:</strong> Všechna vaše aktivní pravidla i proběhlá upozornění můžete kdykoliv spravovat a mazat ve svém <a href="/ucet#notifikace" style="color:#38bdf8; text-decoration:none; font-weight:bold;">Uživatelském účtu</a>.</li>
          <li style="margin-bottom:8px;"><strong>Jednorázová upozornění:</strong> Pokud šlo o jednorázovou notifikaci (např. „upozorni mě, až spoj dorazí do zastávky“), tato notifikace se po doručení sama automaticky smaže.</li>
        </ul>

        <!-- Sekce pro přímé zprávy administrátora -->
        <div style="background:rgba(124,58,237,0.12); border:1px solid rgba(124,58,237,0.3); border-radius:10px; padding:16px; margin:20px 0;">
          <h4 style="color:#c084fc; margin:0 0 6px 0; font-size:15px; display:flex; align-items:center; gap:8px;">
            <i class="fas fa-shield-alt"></i> Přišla vám přímá zpráva od administrátora?
          </h4>
          <p style="margin:0; font-size:13px; color:#e2e8f0;">
            Pokud jste obdrželi zprávu přímo od správce systému (např. marekk_czz), nejedná se o sledování autobusu z mapy, ale o oficiální sdělení administrátora. <a href="/proc-notifikace?typ=admin" style="color:#d8b4fe; font-weight:bold; text-decoration:underline;">Zobrazit podrobnosti k administrátorským zprávám &raquo;</a>
          </p>
        </div>

        <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:16px; margin:20px 0;">
          <h4 style="color:#f87171; margin:0 0 6px 0; font-size:15px; display:flex; align-items:center; gap:8px;">
            <i class="fas fa-question-circle"></i> Myslíte si, že jste si notifikaci nenastavili?
          </h4>
          <p style="margin:0; font-size:13px; color:#fca5a5;">
            Pokud jste si jistí, že jste notifikaci nezadali (např. někdo mohl omylem uvést váš kontakt), nebo pokud se domníváte, že došlo k chybě v systému, obraťte se na nás prostřednictvím stránky pro dotazy a hlášení chyb. Rádi to prověříme a kontakt odhlásíme.
          </p>
        </div>

        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:24px; justify-content:center;">
          <a href="/mapa" style="background:#1e293b; border:1px solid #334155; color:#38bdf8; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px;">
            <i class="fas fa-map-marked-alt"></i> Interaktivní mapa
          </a>
          <a href="/ucet#notifikace" style="background:#1e293b; border:1px solid #334155; color:#a78bfa; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px;">
            <i class="fas fa-user-cog"></i> Správa mých upozornění
          </a>
          <a href="/podpora" style="background:#0284c7; color:white; padding:10px 18px; border-radius:8px; text-decoration:none; font-size:13px; font-weight:bold; display:inline-flex; align-items:center; gap:8px;">
            <i class="fas fa-headset"></i> Nahlásit chybu / Dotazy
          </a>
        </div>
      </div>
    </div>
    """
    return render_public(html_content)

@app.route('/podpora')
@app.route('/hlaseni-chyb')
@app.route('/dotazy')
def stranka_podpora():
    # Zkusit předvyplnit uživatele, pokud je přihlášen
    user_nick = ""
    user_discord = ""
    user_email = ""
    default_pref = "discord"
    try:
        cookie_tok = request.cookies.get('web_session_token') or request.cookies.get('admin_session_token')
        u = get_cached_session_user(cookie_tok) if cookie_tok else None
        if u:
            user_nick = str(u.get("nick") or "")
            user_discord = str(u.get("discord_id") or "")
            user_email = str(u.get("email") or "")
            if not user_discord and user_email:
                default_pref = "email"
    except Exception:
        pass

    import html
    safe_nick = html.escape(user_nick, quote=True)
    safe_contact_discord = html.escape(user_discord or user_nick, quote=True)
    safe_email = html.escape(user_email, quote=True)
    safe_pref = html.escape(default_pref, quote=True)
    secondary_initial_val = safe_email if default_pref == "discord" else safe_contact_discord

    html_content = f"""
    <div style="max-width: 680px; margin: 40px auto; padding: 28px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);">
      <div style="display:flex; align-items:center; gap:16px; margin-bottom:20px; border-bottom:1px solid #334155; padding-bottom:16px;">
        <div style="width:54px; height:54px; border-radius:14px; background:rgba(56,189,248,0.15); border:1px solid #38bdf8; display:flex; align-items:center; justify-content:center; font-size:26px; color:#38bdf8;">
          <i class="fas fa-life-ring"></i>
        </div>
        <div>
          <h1 style="color:#38bdf8; font-size:22px; margin:0 0 4px 0; font-weight:bold;">Dotazy a hlášení chyb</h1>
          <p style="color:#94a3b8; font-size:13px; margin:0;">Zpráva bude předána administrátorům přímo do centrálního dashboardu</p>
        </div>
      </div>

      <form id="supportForm" onsubmit="submitSupportForm(event)">
        <div style="margin-bottom:16px;">
          <label style="display:block; color:#94a3b8; font-size:12px; font-weight:bold; margin-bottom:6px; text-transform:uppercase;">Typ podnětu</label>
          <select id="sp_type" style="width:100%; padding:10px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:14px; outline:none;">
            <option value="BUG_GENERAL">🐛 Nahlásit chybu (všeobecná)</option>
            <option value="MAP_NOTIF">🔔 Interaktivní mapa – Notifikace a sledování spojů</option>
            <option value="MAP_BUG">🗺️ Interaktivní mapa – Chyba mapy / polohy vozidla</option>
            <option value="MAP_DATA">🚌 Interaktivní mapa – Chybějící spoj, linka nebo zastávka</option>
            <option value="GTFS">📊 Dotazy k GTFS datům a fungování jízdních řádů</option>
            <option value="FEEDBACK">💡 Návrh na zlepšení</option>
            <option value="WEB_ERROR">🌐 Nefunkčnost webové stránky</option>
            <option value="GENERAL">💬 Obecná / otevřená zpráva (bez tématu)</option>
            <option value="OTHER">📁 Ostatní</option>
          </select>
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:block; color:#94a3b8; font-size:12px; font-weight:bold; margin-bottom:6px; text-transform:uppercase;">
            Vaše jméno / Herní Nick <span style="color:#38bdf8;">(povinný nick NEBO e-mail)</span>
          </label>
          <input type="text" id="sp_nick" value="{safe_nick}" placeholder="např. Jan Novák nebo přezdívka" style="width:100%; padding:10px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:14px; outline:none; box-sizing:border-box;">
        </div>

        <!-- Volba kam si přeje odpověď: spíše Discord, nebo e-mail -->
        <div style="margin-bottom:16px; background:rgba(0,0,0,0.3); border:1px solid #334155; border-radius:10px; padding:14px;">
          <label style="display:block; color:#38bdf8; font-size:12px; font-weight:bold; margin-bottom:8px; text-transform:uppercase;">
            <i class="fas fa-reply"></i> Kam si přejete zaslat odpověď?
          </label>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
            <button type="button" id="btn_pref_discord" onclick="switchReplyPref('discord')" style="display:flex; align-items:center; justify-content:center; gap:8px; padding:10px; background:#5865F2; color:white; border:2px solid #818cf8; border-radius:8px; font-weight:bold; font-size:13px; cursor:pointer; transition:all 0.2s;">
              <i class="fab fa-discord" style="font-size:16px;"></i> Discord DM (Doporučeno)
            </button>
            <button type="button" id="btn_pref_email" onclick="switchReplyPref('email')" style="display:flex; align-items:center; justify-content:center; gap:8px; padding:10px; background:#1e293b; color:#94a3b8; border:2px solid #334155; border-radius:8px; font-weight:bold; font-size:13px; cursor:pointer; transition:all 0.2s;">
              <i class="fas fa-envelope" style="font-size:16px;"></i> E-mail
            </button>
          </div>
          <input type="hidden" id="sp_reply_pref" value="{safe_pref}">

          <div id="box_discord_contact">
            <label style="display:block; color:#cbd5e1; font-size:12px; font-weight:bold; margin-bottom:4px;">Discord Nick nebo Discord ID <span style="color:#ef4444;">*</span></label>
            <input type="text" id="sp_contact_discord" value="{safe_contact_discord}" placeholder="např. marekk_czz nebo 719896287301992449" style="width:100%; padding:10px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:14px; outline:none; box-sizing:border-box;">
            <p style="margin:4px 0 0 0; color:#94a3b8; font-size:11px;">
              <i class="fab fa-discord" style="color:#5865F2;"></i> Administrátor vám pošle odpověď přímo do soukromé zprávy (DM) na Discordu.
            </p>
          </div>

          <div id="box_email_contact" style="display:none; margin-top:10px;">
            <label style="display:block; color:#cbd5e1; font-size:12px; font-weight:bold; margin-bottom:4px;">Vaše E-mailová adresa <span style="color:#ef4444;">*</span></label>
            <input type="email" id="sp_contact_email" value="{safe_email}" placeholder="např. jan.novak@email.cz" style="width:100%; padding:10px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:14px; outline:none; box-sizing:border-box;">
            <p style="margin:4px 0 0 0; color:#94a3b8; font-size:11px;">
              <i class="fas fa-envelope" style="color:#38bdf8;"></i> Administrátor vám zašle odpověď přímo do e-mailové schránky.
            </p>
          </div>

          <div id="box_secondary_contact" style="margin-top:12px; padding-top:10px; border-top:1px dashed #334155;">
            <label id="lbl_secondary" style="display:block; color:#64748b; font-size:11px; margin-bottom:4px;">Záložní e-mail (nepovinné, pokud vás nezastihneme na Discordu):</label>
            <input type="text" id="sp_secondary_input" value="{secondary_initial_val}" placeholder="vas@email.cz (nepovinné)" style="width:100%; padding:8px 10px; background:rgba(0,0,0,0.3); border:1px solid #334155; border-radius:6px; color:#cbd5e1; font-size:12px; outline:none; box-sizing:border-box;">
          </div>
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:block; color:#94a3b8; font-size:12px; font-weight:bold; margin-bottom:6px; text-transform:uppercase;">Popis problému nebo dotazu <span style="color:#ef4444;">*</span></label>
          <textarea id="sp_message" rows="5" placeholder="Podrobně popište, co se stalo, jakého autobusu/linky se to týká, nebo co potřebujete vyřešit..." required style="width:100%; padding:12px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:14px; outline:none; resize:vertical; box-sizing:border-box;"></textarea>
        </div>

        <div style="margin-bottom:20px;">
          <label style="display:block; color:#94a3b8; font-size:12px; font-weight:bold; margin-bottom:6px; text-transform:uppercase;">
            <i class="fas fa-image" style="color:#38bdf8;"></i> Snímek obrazovky / Fotografie chyby (nepovinné)
          </label>
          <input type="file" id="sp_image_file" accept="image/png,image/jpeg,image/webp,image/gif" style="display:none;" onchange="handleSupportFileSelect(event)">
          
          <div id="sp_upload_dropzone" onclick="document.getElementById('sp_image_file').click()" ondragover="handleSupportDragOver(event)" ondragleave="handleSupportDragLeave(event)" ondrop="handleSupportDrop(event)" style="border:2px dashed #475569; border-radius:12px; padding:18px; text-align:center; cursor:pointer; background:rgba(15,23,42,0.4); transition:all 0.2s;">
            <i class="fas fa-cloud-upload-alt" style="font-size:28px; color:#38bdf8; margin-bottom:6px; display:block;"></i>
            <div style="font-size:13px; color:#f8fafc; font-weight:600;">Klikněte pro výběr fotky / screenshotu nebo ji sem přetáhněte</div>
            <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Podporovány formáty: <strong>.png, .jpg, .jpeg, .webp, .gif</strong> (nebo vložte screenshot stiskem <strong>Ctrl+V</strong>)</div>
          </div>

          <div id="sp_image_preview_container" style="display:none; margin-top:10px; border-radius:10px; border:1px solid #334155; background:rgba(0,0,0,0.5); padding:10px; text-align:center;">
            <img id="sp_image_preview" src="" alt="Náhled snímku" style="max-height:200px; max-width:100%; border-radius:8px; display:block; margin:0 auto; box-shadow:0 4px 14px rgba(0,0,0,0.4);" />
            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:8px; padding:0 4px;">
              <span id="sp_image_name" style="font-size:11px; color:#cbd5e1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:70%;"></span>
              <button type="button" onclick="clearSupportImage(event)" style="background:rgba(239,68,68,0.2); border:1px solid #ef4444; color:#fca5a5; padding:4px 10px; border-radius:6px; font-size:11px; cursor:pointer;">
                <i class="fas fa-times"></i> Odebrat obrázek
              </button>
            </div>
          </div>

          <div style="margin-top:8px;">
            <a href="javascript:void(0)" onclick="toggleSupportUrlInput()" style="color:#94a3b8; font-size:11px; text-decoration:underline;">
              <i class="fas fa-link"></i> Nebo zadat URL adresu obrázku ručně
            </a>
            <div id="sp_url_wrap" style="display:none; margin-top:6px;">
              <input type="url" id="sp_image_url" placeholder="https://... (odkaz na screenshot chyby, imgur, discord cdn)" oninput="handleSupportUrlInput(this.value)" style="width:100%; padding:9px 12px; background:rgba(0,0,0,0.4); border:1px solid #334155; border-radius:8px; color:white; font-size:13px; outline:none; box-sizing:border-box;">
            </div>
          </div>
          <div style="color:#64748b; font-size:11px; margin-top:4px;">📸 Pomůže administrátorům rychleji identifikovat a opravit chybu.</div>
        </div>

        <button type="submit" id="sp_btn" style="width:100%; padding:12px; background:#0284c7; color:white; border:none; border-radius:8px; font-size:15px; font-weight:bold; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px;">
          <i class="fas fa-paper-plane"></i> Odeslat hlášení administrátorům
        </button>
      </form>

      <div id="sp_status" style="margin-top:16px; display:none; padding:12px; border-radius:8px; font-size:14px; text-align:center;"></div>

      <div style="margin-top:24px; padding-top:16px; border-top:1px solid #334155; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <a href="/proc-notifikace" style="color:#94a3b8; font-size:12px; text-decoration:none;"><i class="fas fa-info-circle"></i> Proč mi chodí notifikace?</a>
        <a href="/ucet#notifikace" style="color:#38bdf8; font-size:12px; text-decoration:none;"><i class="fas fa-user-circle"></i> Můj účet a správa notifikací</a>
      </div>
    </div>

    <script>
    let activePref = '{default_pref}';
    let savedDiscord = '{safe_contact_discord}';
    let savedEmail = '{safe_email}';
    let _supportImageData = '';

    function handleSupportDragOver(e) {{
      e.preventDefault();
      e.stopPropagation();
      const dz = document.getElementById('sp_upload_dropzone');
      if (dz) {{
        dz.style.borderColor = '#38bdf8';
        dz.style.background = 'rgba(56,189,248,0.12)';
      }}
    }}

    function handleSupportDragLeave(e) {{
      e.preventDefault();
      e.stopPropagation();
      const dz = document.getElementById('sp_upload_dropzone');
      if (dz) {{
        dz.style.borderColor = '#475569';
        dz.style.background = 'rgba(15,23,42,0.4)';
      }}
    }}

    function handleSupportDrop(e) {{
      e.preventDefault();
      e.stopPropagation();
      handleSupportDragLeave(e);
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files[0]) {{
        processSupportFile(dt.files[0]);
      }}
    }}

    function handleSupportFileSelect(e) {{
      const file = e.target.files && e.target.files[0];
      if (file) processSupportFile(file);
    }}

    function processSupportFile(file) {{
      if (!file.type.startsWith('image/')) {{
        showSupportStatus('warning', 'Vybraný soubor není platný obrázek. Podporovány jsou formáty .png, .jpg, .jpeg, .webp, .gif.');
        return;
      }}
      const reader = new FileReader();
      reader.onload = function(evt) {{
        const rawData = evt.target.result;
        compressImageIfNeeded(rawData, 1600, 0.85, function(compressedData) {{
          _supportImageData = compressedData;
          document.getElementById('sp_image_preview').src = _supportImageData;
          const szKb = Math.round(file.size / 1024);
          document.getElementById('sp_image_name').textContent = file.name + ' (' + szKb + ' KB)';
          document.getElementById('sp_image_preview_container').style.display = 'block';
          document.getElementById('sp_upload_dropzone').style.display = 'none';
        }});
      }};
      reader.readAsDataURL(file);
    }}

    function compressImageIfNeeded(dataUrl, maxDim, quality, cb) {{
      const img = new Image();
      img.onload = function() {{
        let w = img.width, h = img.height;
        if (w <= maxDim && h <= maxDim && dataUrl.length < 500000) {{
          return cb(dataUrl);
        }}
        if (w > maxDim || h > maxDim) {{
          if (w > h) {{ h = Math.round(h * (maxDim / w)); w = maxDim; }}
          else {{ w = Math.round(w * (maxDim / h)); h = maxDim; }}
        }}
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        const outUrl = canvas.toDataURL('image/jpeg', quality);
        cb(outUrl);
      }};
      img.onerror = function() {{ cb(dataUrl); }};
      img.src = dataUrl;
    }}

    function clearSupportImage(e) {{
      if (e) e.stopPropagation();
      _supportImageData = '';
      const f = document.getElementById('sp_image_file');
      if (f) f.value = '';
      const u = document.getElementById('sp_image_url');
      if (u) u.value = '';
      document.getElementById('sp_image_preview_container').style.display = 'none';
      document.getElementById('sp_upload_dropzone').style.display = 'block';
    }}

    function toggleSupportUrlInput() {{
      const w = document.getElementById('sp_url_wrap');
      if (w) w.style.display = (w.style.display === 'none' ? 'block' : 'none');
    }}

    function handleSupportUrlInput(val) {{
      const v = (val || '').trim();
      if (v) {{
        _supportImageData = v;
      }}
    }}

    // Podpora vložení screenshotu ze schránky (Ctrl+V)
    window.addEventListener('paste', function(e) {{
      if (e.clipboardData && e.clipboardData.items) {{
        for (let i = 0; i < e.clipboardData.items.length; i++) {{
          const item = e.clipboardData.items[i];
          if (item.type.indexOf('image') !== -1) {{
            const blob = item.getAsFile();
            if (blob) {{
              processSupportFile(blob);
              break;
            }}
          }}
        }}
      }}
    }});

    function showSupportStatus(type, msg) {{
      const statusEl = document.getElementById('sp_status');
      if (!statusEl) return;
      statusEl.style.display = 'block';
      if (type === 'success') {{
        statusEl.style.background = 'rgba(16,185,129,0.15)';
        statusEl.style.border = '1px solid #10b981';
        statusEl.style.color = '#34d399';
        statusEl.innerHTML = '<i class="fas fa-check-circle"></i> ' + msg;
      }} else if (type === 'warning') {{
        statusEl.style.background = 'rgba(245,158,11,0.15)';
        statusEl.style.border = '1px solid #f59e0b';
        statusEl.style.color = '#fbbf24';
        statusEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + msg;
      }} else {{
        statusEl.style.background = 'rgba(239,68,68,0.15)';
        statusEl.style.border = '1px solid #ef4444';
        statusEl.style.color = '#f87171';
        statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + msg;
      }}
    }}

    function switchReplyPref(pref) {{
      const inpSecondary = document.getElementById('sp_secondary_input');
      const valSecondary = (inpSecondary ? inpSecondary.value : '').trim();

      // Před přepnutím uložit, co uživatel zadal
      if (activePref === 'discord' && valSecondary && valSecondary.includes('@')) {{
        savedEmail = valSecondary;
      }} else if (activePref === 'email' && valSecondary && !valSecondary.includes('@')) {{
        savedDiscord = valSecondary;
      }}

      activePref = pref;
      document.getElementById('sp_reply_pref').value = pref;
      const btnDiscord = document.getElementById('btn_pref_discord');
      const btnEmail = document.getElementById('btn_pref_email');
      const boxDiscord = document.getElementById('box_discord_contact');
      const boxEmail = document.getElementById('box_email_contact');
      const lblSecondary = document.getElementById('lbl_secondary');

      if(pref === 'discord') {{
        btnDiscord.style.background = '#5865F2';
        btnDiscord.style.borderColor = '#818cf8';
        btnDiscord.style.color = 'white';
        btnEmail.style.background = '#1e293b';
        btnEmail.style.borderColor = '#334155';
        btnEmail.style.color = '#94a3b8';
        boxDiscord.style.display = 'block';
        boxEmail.style.display = 'none';
        lblSecondary.innerText = 'Záložní e-mail (nepovinné, pokud vás nezastihneme na Discordu):';
        if(inpSecondary) {{
          inpSecondary.placeholder = 'vas@email.cz (nepovinné)';
          inpSecondary.value = savedEmail;
        }}
      }} else {{
        btnEmail.style.background = '#0284c7';
        btnEmail.style.borderColor = '#38bdf8';
        btnEmail.style.color = 'white';
        btnDiscord.style.background = '#1e293b';
        btnDiscord.style.borderColor = '#334155';
        btnDiscord.style.color = '#94a3b8';
        boxDiscord.style.display = 'none';
        boxEmail.style.display = 'block';
        lblSecondary.innerText = 'Záložní Discord (nepovinné, pokud budete offline na e-mailu):';
        if(inpSecondary) {{
          inpSecondary.placeholder = 'např. uzivatel nebo 123456789... (nepovinné)';
          inpSecondary.value = savedDiscord;
        }}
      }}
    }}

    // Výchozí inicializace
    if(activePref === 'email') switchReplyPref('email');

    function submitSupportForm(e) {{
      e.preventDefault();
      const btn = document.getElementById('sp_btn');
      const statusEl = document.getElementById('sp_status');
      const type = document.getElementById('sp_type').value;
      const nick = document.getElementById('sp_nick').value.trim();
      const message = document.getElementById('sp_message').value.trim();
      const rawUrl = (document.getElementById('sp_image_url')?.value || '').trim();
      const imageUrl = _supportImageData || rawUrl;
      const replyPref = activePref;

      let contactDiscord = document.getElementById('sp_contact_discord').value.trim();
      let contactEmail = document.getElementById('sp_contact_email').value.trim();
      const secondary = (document.getElementById('sp_secondary_input')?.value || '').trim();

      if(replyPref === 'discord' && secondary && secondary.includes('@') && !contactEmail) {{
        contactEmail = secondary;
      }} else if(replyPref === 'email' && secondary && !contactDiscord) {{
        contactDiscord = secondary;
      }}

      if(!nick && !contactEmail) {{
        showSupportStatus('warning', '<strong>Chybí kontakt:</strong> Vyplňte prosím své jméno / herní nick nebo e-mailovou adresu, abychom vás mohli kontaktovat.');
        document.getElementById('sp_nick').focus();
        return;
      }}

      if(!message) {{
        showSupportStatus('warning', '<strong>Chybí popis:</strong> Podrobně popište váš dotaz nebo problém.');
        document.getElementById('sp_message').focus();
        return;
      }}

      if(replyPref === 'discord' && !contactDiscord && !contactEmail) {{
        showSupportStatus('warning', '<strong>Chybí Discord kontakt:</strong> Zadejte prosím své Discord jméno nebo ID pro zaslání odpovědi.');
        document.getElementById('sp_contact_discord').focus();
        return;
      }}
      if(replyPref === 'email' && !contactEmail && !contactDiscord) {{
        showSupportStatus('warning', '<strong>Chybí e-mail:</strong> Zadejte prosím svou e-mailovou adresu pro zaslání odpovědi.');
        document.getElementById('sp_contact_email').focus();
        return;
      }}

      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Odesílám...';
      showSupportStatus('warning', '<i class="fas fa-spinner fa-spin"></i> Odesílám hlášení administrátorům a nahrávám přílohy...');

      fetch('/api/submit_feedback', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          nick: nick,
          reply_pref: replyPref,
          contact_discord: contactDiscord,
          contact_email: contactEmail,
          contact: replyPref === 'discord' ? (contactDiscord || contactEmail) : (contactEmail || contactDiscord),
          discord_id: contactDiscord,
          type: type,
          message: message,
          image_url: imageUrl
        }})
      }})
      .then(r => r.json())
      .then(data => {{
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Odeslat hlášení administrátorům';
        if(data.status === 'success') {{
          showSupportStatus('success', '<strong>Hlášení bylo úspěšně odesláno!</strong> Administrátoři obdrželi vaši zprávu v dashboardu a odpoví vám vybraným kanálem.');
          document.getElementById('sp_message').value = '';
          clearSupportImage();
        }} else {{
          showSupportStatus('error', '<strong>Chyba:</strong> ' + (data.message || 'Nepodařilo se zprávu odeslat. Zkuste to prosím za chvíli.'));
        }}
      }})
      .catch(err => {{
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Odeslat hlášení administrátorům';
        showSupportStatus('error', '<strong>Chyba spojení se serverem.</strong> Zkontrolujte připojení a zkuste to prosím znovu.');
      }});
    }}
    </script>
    """
    return render_public(html_content)


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
        channel = discord.utils.find(lambda c: any(k in c.name.lower() for k in ["vozov", "depo", "garaz", "garáž", "odstav"]), guild.text_channels)
        if channel: break
        
    if not channel: 
        print("[DEPOT DISCORD] Nenalezen kanal obsahujici 'vozov', 'depo' nebo 'garaz'", flush=True)
        return
        
    db = get_db()
    if not db: 
        print("[DEPOT DISCORD] Databaze neni dostupna", flush=True)
        return

    zones_map = {}
    from interaktivnimapa import DEPOT_ZONES
    for z in (DEPOT_ZONES or []):
        if z.get("name"):
            zones_map[z["name"]] = z

    try:
        res_z = db.table("depot_zones").select("*").execute()
        for z in (res_z.data or []):
            if z.get("name"):
                zones_map[z["name"]] = z
    except Exception as e_z:
        print(f"[DEPOT DISCORD] Nelze nacist depot_zones z DB: {e_z}", flush=True)

    zones = list(zones_map.values())
    if not zones:
        print("[DEPOT DISCORD] Zadne vozovny v pameti ani v databazi", flush=True)
        return

    # Nacti historii kanalu jednou pro vsechny vozovny (setri Discord API rate limit)
    try:
        history = [m async for m in channel.history(limit=100)]
    except Exception as e_hist:
        print(f"[DEPOT DISCORD] Nelze nacist historii kanalu {channel.name}: {e_hist}", flush=True)
        history = []

    for zone in zones:
        depot_name = zone.get("name")
        if not depot_name:
            continue
        
        color_val = 0xf59e0b
        c_hex = zone.get("color")
        if c_hex and isinstance(c_hex, str) and c_hex.startswith("#") and len(c_hex) == 7:
            try:
                color_val = int(c_hex[1:], 16)
            except Exception:
                pass

        try:
            all_records = db.table("depot_history").select("*").eq("depot_name", depot_name).neq("spz", "BACKUP").order("arrived_at", desc=True).limit(50).execute().data or []
        except Exception as e_rec:
            print(f"[DEPOT DISCORD] Chyba cteni depot_history pro {depot_name}: {e_rec}", flush=True)
            all_records = []

        if not all_records:
            try:
                from local_db import local_depot_history_get
                all_records = local_depot_history_get(depot_name=depot_name, limit=50)
            except Exception:
                all_records = []

        active = [r for r in all_records if not r.get("left_at")]
        recent = [r for r in all_records if r.get("left_at")][:5]
        
        embed = discord.Embed(title=f"🅿️ Vozovna: {depot_name}", color=color_val)
        
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
            
        embed.add_field(name=f"🟢 Aktuálně parkuje ({len(active)})", value=active_str, inline=False)
        
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
        embed.set_footer(text=f"Automaticky aktualizováno • {get_prague_time().strftime('%d.%m.%Y %H:%M:%S')}")
        
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
                        sent = await channel.send(embed=embed)
                        history.append(sent)
                        print(f"[DEPOT DISCORD] Zprava pro {depot_name} smazana a odeslana nova (limit editaci)", flush=True)
                    else:
                        raise he
            else:
                sent = await channel.send(embed=embed)
                history.append(sent)
                print(f"[DEPOT DISCORD] Odeslana nova zprava pro: {depot_name}", flush=True)
            
            await asyncio.sleep(0.5)  # setri Discord rate limits
        except Exception as e:
            print(f"[DEPOT DISCORD] Chyba pri odesilani/editaci zpravy pro {depot_name}: {e}", flush=True)

    try:
        import gc
        gc.collect()
    except Exception:
        pass

@tasks.loop(minutes=5)
async def keepalive_ping():
    try:
        url = "https://datacorebot.koyeb.app/api/keepalive"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
        import gc
        gc.collect()
    except: pass

_LAST_DAILY_REPORT_DATE = None

@tasks.loop(minutes=1)
async def check_daily_report_schedule():
    """Každý den ve 23:59 odesílá denní AI report celého systému do logu."""
    global _LAST_DAILY_REPORT_DATE
    try:
        now_prague = get_prague_time()
        today_str = now_prague.strftime("%Y-%m-%d")
        # Spustime spolehlive v rozmezi 23:50 az 23:59 v timezone Europe/Prague
        if now_prague.hour == 23 and now_prague.minute >= 50 and _LAST_DAILY_REPORT_DATE != today_str:
            _LAST_DAILY_REPORT_DATE = today_str
            from daily_reporter import generate_ai_daily_report
            rep = generate_ai_daily_report()
            em_data = rep.get("embed")
            
            if em_data:
                em = discord.Embed(
                    title=em_data.get("title", "📊 Denní Systémový Report"),
                    description=em_data.get("description", ""),
                    color=em_data.get("color", 0x10b981),
                    timestamp=now_prague
                )
                for f in em_data.get("fields", []):
                    em.add_field(name=f["name"], value=f["value"], inline=f.get("inline", False))
                if em_data.get("footer"):
                    em.set_footer(text=em_data["footer"].get("text", "DataCoreBot"))
                
                for guild in bot.guilds:
                    channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
                    if channel:
                        try:
                            await channel.send(embed=em)
                            break
                        except Exception as e:
                            print(f"[DAILY REPORT] Chyba pri odesilani do Discord kanalu: {e}", flush=True)

            try:
                from interaktivnimapa import sys_log
                sys_log(f"REPORT DENNÍ: Celková spolehlivost {rep['health']['overall_pct']}% | AI: {rep['ai_summary']}")
            except Exception:
                pass

            try:
                print(rep.get("text_log", ""), flush=True)
            except Exception:
                pass
    except Exception as e:
        print(f"[DAILY REPORT ERROR] {e}", flush=True)

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
    
    # DM Notifikace uživatelům se zapnutým !aktualizace / !aktulizace
    async def send_startup_dms():
        try:
            db = get_db()
            if db:
                try:
                    if hasattr(db, "execute_raw"):
                        db.execute_raw("CREATE TABLE IF NOT EXISTS bot_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id TEXT UNIQUE, dm_updates BOOLEAN DEFAULT 0, updated_at TEXT);")
                except Exception:
                    pass
                # Načteme všechny záznamy z bot_settings a zkontrolujeme dm_updates flexibilně
                res = db.table("bot_settings").select("discord_id, dm_updates").execute()
                notified_count = 0
                for row in (res.data or []):
                    dm_flag = row.get("dm_updates")
                    # Přijímáme boolean True, integer 1 i textové reprezentace
                    if dm_flag in (True, 1, "1", "true", "True", "t"):
                        raw_id = row.get("discord_id")
                        if not raw_id:
                            continue
                        try:
                            uid = int(raw_id)
                            user = bot.get_user(uid) or await bot.fetch_user(uid)
                            if user:
                                now = get_prague_time().strftime("%H:%M")
                                embed = discord.Embed(
                                    title="🔄 Systém Online – Nový Build",
                                    description=f"**BUILD:** `{commit_msg}`\n\nBot byl úspěšně restartován a běží.\nČas startu: **{now}**",
                                    color=0x10b981
                                )
                                embed.set_footer(text="DataCoreBot • Automatická build notifikace")
                                await user.send(embed=embed)
                                notified_count += 1
                                print(f"[STARTUP DM] Zpráva o novém buildu úspěšně odeslána uživateli {user} (ID: {uid})", flush=True)
                        except discord.Forbidden:
                            print(f"[STARTUP DM] Uživatel {raw_id} má zablokované přímé zprávy (DM) od bota.", flush=True)
                        except Exception as e_user:
                            print(f"[STARTUP DM] Selhalo odeslání pro ID {raw_id}: {e_user}", flush=True)
                print(f"[STARTUP DM] Celkem rozesláno {notified_count} DM notifikací o novém buildu.", flush=True)
        except Exception as e:
            print(f"[STARTUP DM CHYBA] Chyba při posílání DM start zpráv: {e}", flush=True)
        
    bot.loop.create_task(send_startup_dms())
    try: bot.add_view(DynamicDownloadView())
    except: pass
    try: bot.add_view(AppAuthView())
    except: pass
    try: bot.add_view(DashboardAuthView())
    except: pass
    try: bot.add_view(LauncherInstallView())
    except: pass
    try:
        for guild in bot.guilds: bot.invites_cache[guild.id] = await guild.invites()
    except: pass
    trigger_setup_messages_update()
    if not keepalive_ping.is_running(): keepalive_ping.start()
    if not check_depot_queue.is_running(): check_depot_queue.start()
    if not check_notification_queue.is_running(): check_notification_queue.start()
    if not check_daily_report_schedule.is_running(): check_daily_report_schedule.start()

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
        
        channel = discord.utils.find(lambda c: any(k in c.name.lower() for k in ["vozov", "depo", "garaz", "garáž", "odstav"]), ctx.guild.text_channels)
        if not channel:
            all_chans = [c.name for c in ctx.guild.text_channels]
            await ctx.send(f"❌ Nenalezen žádný textový kanál odpovídající vozovnám/depům. Dostupné kanály: {', '.join(all_chans[:15])}")
            return
        await ctx.send(f"✅ Nalezen kanál: {channel.mention} (ID: `{channel.id}`)")
        
        db = get_db()
        if not db:
            await ctx.send("❌ Připojení k databázi selhalo.")
            return
        await ctx.send("✅ Připojení k DB v pořádku.")
        
        from interaktivnimapa import DEPOT_ZONES
        zones = list(DEPOT_ZONES)
        if not zones:
            res_z = db.table("depot_zones").select("*").execute()
            zones = res_z.data or []
        await ctx.send(f"✅ Nalezeno {len(zones)} vozoven: {', '.join(z.get('name', 'Neznámá') for z in zones)}")
        
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
        import traceback
        traceback.print_exc()
        await ctx.send(f"❌ Neočekávaná chyba při diagnostice: {e}")

bot.remove_command("help")

@bot.event
async def on_member_join(member):
    await async_send_log("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum:** {get_prague_time().strftime('%d.%m.%Y %H:%M')}", 0x10b981)

@bot.event
async def on_command_error(ctx, error):
    import traceback
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát nebo chybějící parametr!** Zadej `!help` pro formát příkazu `{ctx.command.name if ctx.command else ''}`.", delete_after=15)
    elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
        await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!** Zkontroluj zadané ID nebo označení uživatele.", delete_after=15)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ **Tento příkaz neexistuje.** Zadej `!help` pro zobrazení seznamu příkazů.", delete_after=15)
    elif isinstance(error, (commands.CheckFailure, commands.MissingRole)):
        await ctx.send(f"{ctx.author.mention} ❌ **Nemáš oprávnění použít tento příkaz!**", delete_after=15)
    else:
        print(f"[DISCORD COMMAND ERROR] Příkaz {ctx.command} selhal: {error}", flush=True)
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send(f"❌ **Došlo k chybě při provádění příkazu:** `{error}`", delete_after=20)

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné", value="`!auth`, `!ping`, `!help`, `!register`, `!id`, `!notify list`, `!notify clear`", inline=False)
    embed.add_field(name="🛡️ Správa (SM)", value="`!info [ID]`, `!db [ID]`, `!ban`, `!unban`, `!delete`, `!perdelete`, `!dm @user`, `!dmhistory @uživatel`, `!message #channel`, `!website_block`, `!website_block_mapa`", inline=False)
    embed.add_field(name="⚙️ Administrace (web-sa)", value="`!setup_download`, `!download_setup`, `!sm @uživatel`, `!debugvozovna`, `!aktulizace`, `!dashadd [id] [role]`, `!dashremove [id]`", inline=False)
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
        is_admin = _has_admin_perms(ctx.author, ctx.guild)
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
        if isinstance(t_dict, str):
            try:
                t_dict = json.loads(t_dict)
            except Exception:
                t_dict = {}
        if not isinstance(t_dict, dict):
            t_dict = {}
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
        
        rule_short_id = str(n.get('id', ''))[:8]
        embed.add_field(name=f"ID: {rule_short_id} | {lbl}", value=f"Typ: {n.get('identifier_type')} - Cíl: {n.get('identifier')} | Stav: {active_str}\nUdálosti: {t_str}", inline=False)
        
    await ctx.send(embed=embed)

@notify_group.command(name="clear")
async def notify_clear(ctx, target_user: str = None):
    if target_user:
        is_admin = _has_admin_perms(ctx.author, ctx.guild)
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
@check_web_sa()
async def dashadd(ctx, target_id: str, role: str):
    role = role.lower()
    if role not in ["viewer", "admin", "superadmin", "sa", "dev", "bt", "user"]:
        await ctx.send("❌ Neplatná úroveň! Možnosti: viewer, admin, superadmin, sa, dev, bt, user")
        return
    r_str = "User"
    if role in ["superadmin", "sa"]: r_str = "SA"
    elif role in ["admin", "dev"]: r_str = "DEV"
    elif role in ["viewer", "bt"]: r_str = "BT"
    
    clean_id = _clean_discord_id(target_id, ctx)
    db = get_db()
    if db:
        res = db.table("users").update({"dashboard_access": True, "role": r_str}).eq("discord_id", clean_id).execute()
        if not res.data: await ctx.send(f"❌ Uživatel `{clean_id}` nebyl v databázi nalezen.")
        else: await ctx.send(f"✅ Dashboard přístup '{role}' udělen pro `{clean_id}`.")

@bot.command()
@check_web_sa()
async def dashremove(ctx, target_id: str):
    clean_id = _clean_discord_id(target_id, ctx)
    db = get_db()
    if db:
        res = db.table("users").update({"dashboard_access": False}).eq("discord_id", clean_id).execute()
        if not res.data: await ctx.send(f"❌ Uživatel `{clean_id}` nebyl v databázi nalezen.")
        else: await ctx.send(f"✅ Dashboard přístup odebrán pro `{clean_id}`.")


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

def _clean_discord_id(val, ctx=None):
    if ctx and getattr(ctx.message, "mentions", None) and len(ctx.message.mentions) > 0:
        return str(ctx.message.mentions[0].id)
    if not val: return ""
    m = re.search(r'\b\d{16,21}\b', str(val))
    if m: return m.group(0)
    return str(val).strip().lstrip("<@!").lstrip("<@").rstrip(">").strip()

@bot.command()
@check_sm_role()
async def info(ctx, discord_id: str = None):
    """Zobrazí info o uživateli. Vyžaduje roli SM."""
    cleaned_id = _clean_discord_id(discord_id, ctx)
    if not cleaned_id: return await ctx.send("❌ Zadejte ID nebo označte uživatele.")
    db = get_db()
    if not db: return
    u = db.table("users").select("*").eq("discord_id", cleaned_id).execute().data
    if not u: return await ctx.send("❌ Uživatel nenalezen.")
    embed = discord.Embed(title=f"Uživatel: {u[0].get('nick')}", color=0x38bdf8)
    embed.add_field(name="App ID", value=f"#{u[0].get('app_id')}", inline=True)
    embed.add_field(name="Discord ID", value=u[0].get('discord_id'), inline=True)
    embed.add_field(name="Role", value=u[0].get('role'), inline=True)
    embed.add_field(name="Banned", value="Ano" if u[0].get('is_banned') else "Ne", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@check_sm_role()
async def ban(ctx, discord_id: str):
    cleaned_id = _clean_discord_id(discord_id, ctx)
    if not cleaned_id: return await ctx.send("❌ Zadejte ID nebo označte uživatele.")
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", cleaned_id).execute()
    await send_user_dm(cleaned_id, "🔨 Účet zablokován", "Váš přístup do aplikace byl zablokován.", 0xef4444)
    await ctx.send(f"🔨 Uživateli `{cleaned_id}` byl udělen BAN.")

@bot.command()
@check_sm_role()
async def unban(ctx, discord_id: str):
    cleaned_id = _clean_discord_id(discord_id, ctx)
    if not cleaned_id: return await ctx.send("❌ Zadejte ID nebo označte uživatele.")
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": False}).eq("discord_id", cleaned_id).execute()
    await send_user_dm(cleaned_id, "🕊️ Účet odblokován", "Váš přístup do aplikace byl obnoven.", 0x10b981)
    await ctx.send(f"🕊️ Uživateli `{cleaned_id}` byl zrušen BAN.")

@bot.command(name="db")
@check_sm_role()
async def db_cmd(ctx, discord_id: str):
    cleaned_id = _clean_discord_id(discord_id, ctx)
    if not cleaned_id: return await ctx.send("❌ Zadejte ID nebo označte uživatele.")
    db_conn = get_db()
    if not db_conn: return
    user_data = db_conn.table("users").select("dashboard_access").eq("discord_id", cleaned_id).execute().data
    if not user_data: return await ctx.send("❌ Uživatel nenalezen.")
    new_status = not user_data[0].get("dashboard_access", False)
    db_conn.table("users").update({"dashboard_access": new_status}).eq("discord_id", cleaned_id).execute()
    await ctx.send(f"⚙️ Přístup do DB pro ID `{cleaned_id}`: **{'POVOLEN ✅' if new_status else 'ODEBRÁN ❌'}**.")

@bot.command()
@check_sm_role()
async def delete(ctx, discord_id: str):
    cleaned_id = _clean_discord_id(discord_id, ctx)
    if not cleaned_id: return await ctx.send("❌ Zadejte ID nebo označte uživatele.")
    db = get_db()
    if not db: return
    now = get_prague_time().strftime("%d.%m.%Y %H:%M")
    db.table("users").update({"is_deleted": True, "deleted_at": now, "dashboard_access": False}).eq("discord_id", cleaned_id).execute()
    await ctx.send(f"☠️ Účet `{cleaned_id}` byl smazán.")

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

async def _resolve_discord_user(user_arg, ctx=None):
    if not user_arg and (not ctx or not getattr(ctx.message, "mentions", None)):
        return None
    # 1. Přímé označení (mention)
    if ctx and getattr(ctx.message, "mentions", None) and len(ctx.message.mentions) > 0:
        return ctx.message.mentions[0]
        
    user_str = str(user_arg).strip()
    
    # 2. Extrakce číselného Discord ID
    m_id = re.search(r'\b\d{16,21}\b', user_str)
    if m_id:
        try:
            uid = int(m_id.group(0))
            u = bot.get_user(uid) or await bot.fetch_user(uid)
            if u: return u
        except Exception:
            pass
            
    # 3. Vyčištění stringu
    clean_arg = user_str.lstrip("<@!").lstrip("<@").rstrip(">").strip()
    if clean_arg.isdigit():
        try:
            uid = int(clean_arg)
            u = bot.get_user(uid) or await bot.fetch_user(uid)
            if u: return u
        except Exception:
            pass
            
    # 4. Prohledání členů serveru
    if ctx and ctx.guild:
        mem = ctx.guild.get_member_named(clean_arg)
        if not mem:
            mem = discord.utils.find(
                lambda x: x.name.lower() == clean_arg.lower() 
                or (getattr(x, 'global_name', None) and x.global_name.lower() == clean_arg.lower())
                or x.display_name.lower() == clean_arg.lower(),
                ctx.guild.members
            )
        if mem:
            return mem
        try:
            query_res = await ctx.guild.query_members(clean_arg, limit=1)
            if query_res:
                return query_res[0]
        except Exception:
            pass
            
    # 5. Databáze users (podle nicku nebo emailu)
    try:
        db = get_db()
        if db:
            u_data = db.table("users").select("discord_id").ilike("nick", clean_arg).execute().data
            if not u_data:
                u_data = db.table("users").select("discord_id").ilike("email", clean_arg).execute().data
            if u_data and u_data[0].get("discord_id"):
                uid_str = str(u_data[0]["discord_id"]).strip()
                if uid_str.isdigit():
                    u = bot.get_user(int(uid_str)) or await bot.fetch_user(int(uid_str))
                    if u: return u
    except Exception:
        pass
    return None

@bot.command()
@check_sm_role()
async def dm(ctx, target_user: str, *, text: str):
    user = await _resolve_discord_user(target_user, ctx)
    if not user:
        return await ctx.send(f"❌ Uživatel `{target_user}` nebyl nalezen. Zadej @označení nebo ID.")
    try:
        embed = discord.Embed(title="📩 Zpráva od administrace", description=text, color=0x38bdf8)
        embed.set_footer(text="Toto je automatická zpráva, na kterou lze odepsat.")
        await user.send(embed=embed)
        await ctx.send(f"✅ Zpráva odeslána uživateli `{user.display_name}`.")
    except discord.Forbidden: await ctx.send(f"❌ Uživatel `{user.display_name}` má zablokované DM.")
    except Exception as e: await ctx.send(f"❌ Chyba: `{e}`")

@bot.command(name="dmhistory", aliases=["dm_history", "historydm", "dmhist"])
@check_sm_role()
async def dmhistory(ctx, *, user_arg: str = None):
    # Podpora volání: !dmhistory @user [limit] nebo !dmhistory [ID] [limit] nebo !dmhistory
    limit = 100
    target_str = user_arg
    if user_arg:
        parts = user_arg.strip().split()
        if len(parts) >= 2 and parts[-1].isdigit():
            limit = min(max(1, int(parts[-1])), 200)
            target_str = " ".join(parts[:-1])

    status_msg = await ctx.send("⏳ Načítám historii DM zpráv...")
    try:
        user = await _resolve_discord_user(target_str, ctx)
        if not user and not target_str:
            return await status_msg.edit(content="❌ **Zadej uživatele!** Použití: `!dmhistory @uživatel [počet]` nebo `!dmhistory [ID] [počet]`")
        if not user:
            return await status_msg.edit(content=f"❌ Uživatel `{target_str}` nebyl nalezen.")

        # Získej DM kanál
        dm_chan = user.dm_channel
        if not dm_chan:
            try:
                dm_chan = await user.create_dm()
            except Exception as e_dm:
                return await status_msg.edit(content=f"❌ Nelze otevřít DM s `{user.display_name}`: {e_dm}")

        if not dm_chan:
            return await status_msg.edit(content=f"❌ DM kanál s `{user.display_name}` není dostupný.")

        messages = [msg async for msg in dm_chan.history(limit=limit)]
        messages.reverse()
        if not messages:
            return await status_msg.edit(content=f"📭 DM mezi botem a uživatelem `{user.display_name}` je prázdné (uživatel si s botem zatím nepsal).")

        log_content = f"--- HISTORIE ZPRÁV DM S UŽIVATELEM {user.display_name.upper()} ({user.id}) ---\n"
        log_content += f"--- VYGENEROVÁNO: {get_prague_time().strftime('%d.%m.%Y %H:%M:%S')} ---\n\n"
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
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', user.name or user.display_name) or "user"
        file = discord.File(file_stream, filename=f"HistorieDM_{safe_name}.txt")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await ctx.send(f"📄 Posledních {len(messages)} zpráv s `{user.display_name}`:", file=file)
    except discord.Forbidden:
        await status_msg.edit(content="❌ Nemám oprávnění k DM tohoto uživatele (má zablokované zprávy od botů).")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await status_msg.edit(content=f"❌ Chyba: `{e}`")

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

# ═══════════════════════════════════════════════════════════════════════════════
# LAUNCHER DOWNLOAD PANEL
# ═══════════════════════════════════════════════════════════════════════════════

# URL na GitHub Release – používáme webovou stránku, abychom se vyhli varování Discordu
LAUNCHER_DOWNLOAD_URL = "https://datacorebot.koyeb.app/download-launcher"

class LauncherRulesView(discord.ui.View):
    """Ephemeral podmínky užívání – zobrazí se po kliknutí Zahájit instalaci."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Souhlasím", style=discord.ButtonStyle.success, emoji="✅")
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        # Generování unikátního tokenu pro stažení
        import uuid
        token = str(uuid.uuid4())
        link = f"https://datacorebot.koyeb.app/launcher-page/{token}"
        d_id = str(interaction.user.id)
        user_nick = interaction.user.display_name or interaction.user.name or "Uživatel"

        # Uložit token do in-memory cache pro okamžitou validaci (TTL 2 hodiny)
        LAUNCHER_TOKENS[token] = {
            "discord_id": d_id,
            "nick": user_nick,
            "is_banned": False,
            "created_at": time.time(),
            "expires_at": time.time() + 7200
        }

        # Zápis do databáze a kontrola banu
        db = get_db()
        if db:
            try:
                chk = db.table("users").select("*").eq("discord_id", d_id).execute()
                if chk.data:
                    if chk.data[0].get("is_banned"):
                        LAUNCHER_TOKENS.pop(token, None)
                        return await interaction.followup.send(
                            "**⛔ Přístup zamítnut:** Váš účet má aktivní BAN. Stažení Launcheru není povoleno.",
                            ephemeral=True
                        )
                    db.table("users").update({"download_token": token}).eq("discord_id", d_id).execute()
                else:
                    # Uživatel dosud v DB neexistuje – zaregistrovat ho a uložit download_token
                    hid = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                    nid = hid.data[0]["app_id"] + 1 if (hid.data and hid.data[0].get("app_id")) else 1000
                    db.table("users").insert({
                        "app_id": nid,
                        "discord_id": d_id,
                        "nick": user_nick,
                        "role": "User",
                        "hwid": "",
                        "ip_address": "",
                        "is_banned": False,
                        "is_deleted": False,
                        "deleted_at": "",
                        "dashboard_access": False,
                        "login_token": "",
                        "download_token": token,
                        "registered_at": get_prague_time().strftime("%d.%m.%Y %H:%M")
                    }).execute()
            except Exception as e_tok:
                print(f"[LAUNCHER AGREE DB ERROR] {e_tok}", flush=True)

        await interaction.followup.send(
            content=(
                "✅ **Podmínky přijaty.** Stahování Launcheru zahájeno!\n\n"
                f"📥 **Klikni na odkaz níže (platí jen pro tebe):**\n{link}\n\n"
                "Po instalaci se přihlas přes Discord ID a stáhni nejnovější verzi OIS IDPK."
            ),
            ephemeral=True
        )
        # Log do datacore
        send_log(
            "📥 Stažení Launcheru",
            f"Uživatel **{interaction.user.display_name}** (`{interaction.user.id}`) si stáhl IDPK Launcher.",
            0x38bdf8,
            "🖥️・datacore-logs"
        )

    @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, emoji="❌")
    async def disagree(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        await interaction.followup.send(
            content="**Akce zrušena.** Pokud si to rozmyslíš, klikni na tlačítko znovu.",
            ephemeral=True
        )


class LauncherInstallView(discord.ui.View):
    """Persistentní panel pro stažení Launcheru (zůstane i po restartu bota)."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Zahájit instalaci Launcheru",
        style=discord.ButtonStyle.primary,
        emoji="📥",
        custom_id="persistent_launcher_install_btn"
    )
    async def install_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        db = get_db()

        # Kontrola banu hned na začátku
        if db:
            chk = db.table("users").select("is_banned").eq("discord_id", str(interaction.user.id)).execute()
            if chk.data and chk.data[0].get("is_banned"):
                return await interaction.followup.send(
                    "**⛔ Přístup zamítnut:** Váš účet má aktivní BAN.",
                    ephemeral=True
                )

        podmínky_text = (
            "**PODMÍNKY UŽÍVÁNÍ:**\n"
            "1. Přísný zákaz šíření, kopírování nebo sdílení aplikace bez výslovného souhlasu autora.\n"
            "2. Systém využívá HWID ochranu a shromažďuje telemetrická data.\n"
            "3. Každý pokus o modifikaci kódu nebo obcházení zabezpečení povede k okamžitému zablokování.\n\n"
            "Souhlasíte s těmito podmínkami?"
        )
        await interaction.followup.send(
            content=podmínky_text,
            view=LauncherRulesView(),
            ephemeral=True
        )


def build_launcher_embed():
    """Vytvoří embed pro Launcher download panel."""
    embed = discord.Embed(
        title="📥 Projekt OIS IDPK – Launcher",
        description=(
            "Vítejte v oficiálním instalačním průvodci.\n\n"
            "Kliknutím na tlačítko níže zahájíte ověření účtu a stahování.\n"
            "Dále v Launcheru stáhnete nejnovější verzi aplikace."
        ),
        color=0x38bdf8
    )
    embed.add_field(
        name="⚠️ Upozornění",
        value="Pokud máte BAN, systém vás ke stahování nepustí.",
        inline=False
    )
    embed.set_footer(text="Projekt OIS IDPK • Officiální distribuční kanál")
    return embed


# Uložená ID launcher-panelových zpráv (pro refresh)
def get_launcher_panel_messages(db):
    resp = db.table("settings").select("setting_value").eq("setting_key", "launcher_panel_messages").execute()
    if not resp.data: return []
    try: return json.loads(resp.data[0]['setting_value'])
    except: return []

def save_launcher_panel_message(db, channel_id, message_id):
    msgs = get_launcher_panel_messages(db)
    msgs.append({"channel_id": str(channel_id), "message_id": str(message_id)})
    msgs = msgs[-10:]
    check = db.table("settings").select("*").eq("setting_key", "launcher_panel_messages").execute().data
    if not check:
        db.table("settings").insert({"setting_key": "launcher_panel_messages", "setting_value": json.dumps(msgs)}).execute()
    else:
        db.table("settings").update({"setting_value": json.dumps(msgs)}).eq("setting_key", "launcher_panel_messages").execute()


@bot.command(name="download_setup")
@check_web_sa()
async def cmd_download_setup(ctx):
    """Pošle persistentní Launcher download panel do kanálu."""
    db = get_db()
    if not db:
        return await ctx.send("❌ Databáze není dostupná.", delete_after=10)

    embed = build_launcher_embed()
    msg = await ctx.send(embed=embed, view=LauncherInstallView())
    save_launcher_panel_message(db, ctx.channel.id, msg.id)
    try:
        await ctx.message.delete()
    except Exception:
        pass

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

@bot.command(name="aktualizace", aliases=["aktulizace", "buildnotif", "buildnotify"])
async def aktulizace(ctx):
    db = get_db()
    if not db:
        return await ctx.send("❌ Databáze není dostupná.", delete_after=10)
    
    # Ověření práv: SA, DEV, Superadmin, administrátor serveru nebo vlastník
    is_allowed = False
    if str(ctx.author.id) in ["719896287301992449"]:
        is_allowed = True
    elif ctx.author.guild_permissions.administrator:
        is_allowed = True
    else:
        user_data = db.table("users").select("role").eq("discord_id", str(ctx.author.id)).execute().data
        if user_data and user_data[0].get("role") in ["SA", "DEV", "Superadmin", "Admin"]:
            is_allowed = True
            
    if not is_allowed:
        return await ctx.send(f"❌ {ctx.author.mention} K tomuto příkazu nemáš oprávnění (vyžadována role SA/DEV).", delete_after=10)
        
    try:
        if hasattr(db, "execute_raw"):
            db.execute_raw("CREATE TABLE IF NOT EXISTS bot_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id TEXT UNIQUE, dm_updates BOOLEAN DEFAULT 0, updated_at TEXT);")
    except Exception:
        pass
        
    res = db.table("bot_settings").select("dm_updates").eq("discord_id", str(ctx.author.id)).execute()
    current_state = False
    if res.data:
        val = res.data[0].get("dm_updates")
        current_state = bool(val in (True, 1, "1", "true", "True", "t"))
        
    new_state = not current_state
    now_ts = get_prague_time().isoformat()
    db.table("bot_settings").upsert({
        "discord_id": str(ctx.author.id),
        "dm_updates": new_state,
        "updated_at": now_ts
    }).execute()
    
    if new_state:
        msg = await ctx.send(f"🔔 {ctx.author.mention} DM upozornění na nový build a restarty: **ZAPNUTO** ✅")
        # Zkušební zpráva do DM pro okamžité ověření otevřených DM
        try:
            embed = discord.Embed(
                title="🔔 DM Notifikace aktivovány",
                description="Úspěšně jsi aktivoval upozornění na nové buildy a restarty bota.\nPři každém restartu / nasazení nového buildu ti sem automaticky přijde zpráva s popisem commitu.",
                color=0x38bdf8
            )
            embed.set_footer(text="Pro vypnutí stačí v chatu znovu napsat !aktualizace")
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"⚠️ {ctx.author.mention} Máš zablokované přímé zprávy (DM) od členů serveru! Povol si příjem zpráv od bota.", delete_after=15)
        except Exception:
            pass
    else:
        msg = await ctx.send(f"🔕 {ctx.author.mention} DM upozornění na nový build a restarty: **VYPNUTO** ❌")
        
    await asyncio.sleep(4)
    try:
        await msg.delete()
        await ctx.message.delete()
    except Exception:
        pass


@bot.command(name="data")
async def cmd_data(ctx, arg: str = None):
    db = get_db()
    if not db:
        await ctx.send("Databáze není dostupná.")
        return
        
    try:
        res = db.table("gtfs_feed_versions").select("*").order("id", desc=True).limit(1).execute()
        data = res.data
        if not data:
            await ctx.send("V databázi nejsou žádné informace o GTFS.")
            return
            
        latest = data[0]
        ver = latest.get("version_tag", "Neznámá")
        date_raw = latest.get("published_at", "")
        if date_raw:
            try:
                dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00")).astimezone(ZoneInfo('Europe/Prague'))
                date_str = dt.strftime("%d.%m.%Y %H:%M:%S")
            except:
                date_str = date_raw
        else:
            date_str = "Neznámé"
            
        stops = latest.get("stop_count", 0)
        routes = latest.get("route_count", 0)
        trips = latest.get("trip_count", 0)
        
        if arg:
            if arg.isdigit() and len(arg) == 6:
                # Načtení konkrétní linky z gtfs_line_updates
                l_res = db.table("gtfs_line_updates").select("last_updated_at").eq("route_id", arg).execute()
                line_data = l_res.data
                
                if line_data and len(line_data) > 0:
                    l_date_raw = line_data[0].get("last_updated_at")
                    try:
                        l_dt = datetime.fromisoformat(l_date_raw.replace("Z", "+00:00")).astimezone(ZoneInfo('Europe/Prague'))
                        l_date_str = l_dt.strftime("%d.%m.%Y v %H:%M:%S")
                    except:
                        l_date_str = l_date_raw
                    
                    await ctx.send(f"🚌 **Data pro linku {arg}**\n- Zahrnuta v balíčku (verze: `{ver}`).\n- **Jízdní řád linky se naposledy reálně změnil: {l_date_str}**.")
                else:
                    await ctx.send(f"🚌 **Data pro linku {arg}**\n- Zahrnuta v balíčku (verze: `{ver}`).\n- **Zatím u ní neevidujeme žádnou změnu od spuštění sledovacího systému.**")
            else:
                await ctx.send(f"❌ '{arg}' nevypadá jako číslo regionální linky (např. 490735).")
        else:
            msg = (f"🗄️ **Aktuální stav GTFS databáze**\n"
                   f"**Verze dat:** `{ver}`\n"
                   f"**Poslední aktualizace:** {date_str}\n"
                   f"**Obsah databáze:** {stops} zastávek, {routes} linek, {trips} spojů.\n\n"
                   f"*(Pro info o konkrétní lince napiš `!data <číslo>`)*")
            await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Chyba při čtení dat: {e}")

@bot.command(name="dailyreport", aliases=["report", "dennireport", "statusreport"])
async def cmd_dailyreport(ctx):
    """Ruční vyvolání denního reportu a AI zhodnocení systému v procentech."""
    try:
        from daily_reporter import generate_ai_daily_report
        await ctx.send("⏳ Generuji aktuální systémový report a AI analýzu...")
        rep = generate_ai_daily_report()
        em_data = rep.get("embed")
        if em_data:
            em = discord.Embed(
                title=em_data.get("title", "📊 Denní Systémový Report"),
                description=em_data.get("description", ""),
                color=em_data.get("color", 0x10b981),
                timestamp=get_prague_time()
            )
            for f in em_data.get("fields", []):
                em.add_field(name=f["name"], value=f["value"], inline=f.get("inline", False))
            if em_data.get("footer"):
                em.set_footer(text=em_data["footer"].get("text", "DataCoreBot"))
            await ctx.send(embed=em)
        else:
            await ctx.send(f"```\n{rep.get('text_log', 'Report vygenerován.')}\n```")
    except Exception as e:
        await ctx.send(f"Chyba při generování reportu: {e}")

@app.route('/api/admin/daily_report', methods=['GET'])
def api_admin_daily_report_main():
    try:
        from daily_reporter import generate_ai_daily_report
        rep = generate_ai_daily_report()
        return jsonify({"status": "success", "report": rep})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

def run_discord_bot(bot_token):
    global BOT_ASYNC_LOOP
    loop = asyncio.new_event_loop()
    BOT_ASYNC_LOOP = loop
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
    run_simple('0.0.0.0', port, app, use_reloader=False, threaded=True)


def exit_handler():
    try:
        from interaktivnimapa import GLOBAL_BUS_CACHE, get_db_client
        from zoneinfo import ZoneInfo
        db_client = get_db_client()
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
    
    allowed = False
    if discord_id:
        if discord_id == 'VSC-DEV':
            allowed = True
        else:
            role, is_banned = get_cached_user_role(discord_id)
            if any(x in role for x in ['BT', 'DEV', 'SA']) and not is_banned:
                allowed = True

    if not allowed and discord_id != 'VSC-DEV':
        return jsonify({"error": "Nemas opravneni (Vyžadována Premium role)"}), 403

    # Aktualizace stavu
    if session_id not in MIRROR_STATES:
        MIRROR_STATES[session_id] = {"pending_actions": [], "approved": False, "connection_requested": False}
        
    MIRROR_STATES[session_id]["last_updated"] = time.time()
    MIRROR_STATES[session_id]["state"] = data.get('state', {})
    
    if "approve_connection" in data:
        if data["approve_connection"] is True:
            MIRROR_STATES[session_id]["approved"] = True
        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = "rejected"
            MIRROR_STATES[session_id]["connection_requested"] = False
            MIRROR_STATES[session_id]["lockout_until"] = time.time() + 60
            
    conn_req = MIRROR_STATES[session_id].get("connection_requested", False)
    approved = MIRROR_STATES[session_id].get("approved")
    
    # We only want to trigger the prompt if it's NOT approved and NOT rejected
    is_approved_bool = (approved is True)
    conn_req_flag = conn_req and (approved is False or approved is None)
    
    actions = MIRROR_STATES[session_id]["pending_actions"].copy()
    MIRROR_STATES[session_id]["pending_actions"].clear()
    
    now = time.time()
    to_delete = [sid for sid, s in MIRROR_STATES.items() if now - s["last_updated"] > 120]
    for sid in to_delete:
        del MIRROR_STATES[sid]
        
    return jsonify({"status": "ok", "actions": actions, "connection_requested": conn_req_flag, "is_approved": is_approved_bool})


@app.route('/api/mirror/request_connection/<session_id>', methods=['POST'])
def mirror_request_connection(session_id):
    if session_id in MIRROR_STATES:
        s = MIRROR_STATES[session_id]
        if s.get("lockout_until", 0) > time.time():
            return jsonify({"status": "error", "message": "locked out"}), 429
        s["connection_requested"] = True
        s["connection_requested_time"] = time.time()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "session not found"}), 404

@app.route('/api/mirror/mobile_state/<session_id>')
def mirror_mobile_state(session_id):
    """
    Server-Sent Events pro mobilní aplikaci. Mobil se napojí a server mu posílá aktualizace.
    """
    def generate():
        last_state_hash = None
        try:
            while True:
                if session_id not in MIRROR_STATES:
                    yield f"data: {{\"status\": \"offline\"}}\n\n"
                    time.sleep(2)
                    continue
                    
                s = MIRROR_STATES[session_id]
                if time.time() - s["last_updated"] > 10:
                    yield f"data: {{\"status\": \"offline\"}}\n\n"
                else:
                    if s.get("lockout_until", 0) > time.time():
                        remaining = int(s["lockout_until"] - time.time())
                        yield f"data: {{\"status\": \"lockout\", \"remaining\": {remaining}}}\n\n"
                    else:
                        if s.get("approved") == "rejected":
                            s["approved"] = False
                        
                        if not s.get("connection_requested") and not s.get("approved"):
                            yield f"data: {{\"status\": \"request_needed\"}}\n\n"
                        elif s.get("connection_requested") and not s.get("approved"):
                            if s.get("connection_requested_time") and time.time() - s.get("connection_requested_time") > 30:
                                s["connection_requested"] = False
                                s["connection_requested_time"] = 0
                                yield f"data: {{\"status\": \"timeout\"}}\n\n"
                            else:
                                yield f"data: {{\"status\": \"waiting_for_approval\"}}\n\n"
                        elif s.get("approved") is True:
                            import json
                            state = s.get("state", {})
                            state_str = json.dumps(state)
                            h = hash(state_str)
                            if h != last_state_hash:
                                last_state_hash = h
                                yield f"data: {{\"status\": \"online\", \"state\": {state_str}}}\n\n"
                time.sleep(0.5)
        except GeneratorExit:
            pass
        finally:
            if session_id in MIRROR_STATES:
                MIRROR_STATES[session_id]["approved"] = False
                MIRROR_STATES[session_id]["connection_requested"] = False
            
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
        if action in ["eval", "input"] or data.get("code") or data.get("id"):
            MIRROR_STATES[session_id]["pending_actions"].append(data)
        else:
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
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <title>IDPK Mobilní Zrcadlo</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/morphdom@2.7.4/dist/morphdom-umd.min.js"></script>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background: #035689; height: 100dvh; width: 100vw; display: flex; justify-content: center; align-items: center; }
        #mirror-container { 
            width: 100vw; height: 100dvh; 
            display: flex; justify-content: center; align-items: flex-start;
            overflow: hidden; pointer-events: auto;
            transform-origin: top center;
        }
        
        /* Overrides to make PC UI fit mobile perfectly */
        #mirror-container .main-container { height: 100dvh !important; max-height: 100dvh !important; }
        
        .mobile-settings-btn {
            position: fixed; top: env(safe-area-inset-top, 10px); right: 15px;
            width: 32px; height: 32px; color: rgba(255,255,255,0.7);
            font-size: 24px; display: flex; justify-content: center;
            align-items: center; cursor: pointer; z-index: 999999;
            text-shadow: 0 0 5px rgba(0,0,0,0.8);
        }
        
        #mobile-settings-overlay {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(2, 25, 45, 0.93); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            z-index: 9999999; flex-direction: column; align-items: center; justify-content: center; padding: 30px 20px;
        }
        .mob-settings-title { color: white; font-size: 16px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 30px; text-align: center; font-family: sans-serif; }
        .mob-glass-btn {
            width: 100%; max-width: 300px; padding: 16px 20px; margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.15); border-radius: 14px;
            background: rgba(255,255,255,0.08); color: white; font-size: 15px;
            font-weight: 600; cursor: pointer; text-align: center; backdrop-filter: blur(4px); transition: background 0.2s; font-family: sans-serif;
            text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px;
        }
        .mob-glass-btn.red { border-color: rgba(231,76,60,0.5); background: rgba(231,76,60,0.15); }
        .mob-glass-btn.close { border-color: rgba(255,255,255,0.2); color: rgba(255,255,255,0.6); }
        
        #status-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(2, 25, 45, 0.95); z-index: 900000; display: flex;
            flex-direction: column; align-items: center; justify-content: center;
            color: white; font-family: 'Segoe UI', sans-serif; backdrop-filter: blur(10px);
        }
        .offline-icon-container { width: 100%; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; gap: 20px; }
        .offline-icon { font-size: 45px; color: rgba(255,255,255,0.3); }
        .icon-bolt { color: #e74c3c; font-size: 35px; animation: pulseBolt 1.5s infinite; z-index: 2; }
        @keyframes pulseBolt {
            0% { transform: scale(1); opacity: 1; text-shadow: 0 0 10px #e74c3c; }
            50% { transform: scale(1.3); opacity: 0.5; text-shadow: 0 0 25px #e74c3c; }
            100% { transform: scale(1); opacity: 1; text-shadow: 0 0 10px #e74c3c; }
        }
        .status-title { font-size: 22px; font-weight: 800; margin: 0 0 10px 0; letter-spacing: 2px; }
        .status-desc { font-size: 14px; color: rgba(255,255,255,0.6); text-align: center; max-width: 280px; margin-bottom: 30px; line-height: 1.5; }
        .troubleshoot-btn {
            background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
            color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none;
            font-weight: 600; transition: all 0.2s; display: flex; align-items: center; gap: 8px;
        }
        .troubleshoot-btn:hover { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.4); }
    </style>
</head>
<body>
    <div id="status-overlay">
        <div class="offline-icon-container">
            <i class="fas fa-desktop offline-icon icon-pc"></i>
            <i class="fas fa-bolt icon-bolt"></i>
            <i class="fas fa-mobile-alt offline-icon icon-mobile"></i>
        </div>
        <h2 id="status-title" class="status-title">SPOJENÍ PŘERUŠENO</h2>
        <p id="status-desc" class="status-desc">Nepodařilo se připojit k PC. Zkontrolujte, zda je aplikace zapnutá a PC je připojen k internetu.</p>
        <a href="/mobilni-sdileni" class="troubleshoot-btn"><i class="fas fa-life-ring"></i> Řešení problémů</a>
    </div>
    
    <div class="mobile-settings-btn" onclick="openMobileSettings()">⚙</div>
    <div id="mirror-container"></div>
    
    <div id="mobile-settings-overlay">
        <div class="mob-settings-title">⚙ Nastavení Zrcadla</div>
        <a href="/mobilni-sdileni" class="mob-glass-btn">
            <i class="fas fa-book"></i> Návod a řešení problémů
        </a>
        <button type="button" class="mob-glass-btn red" onclick="disconnectAndClose()">
            <i class="fas fa-sign-out-alt"></i> Odpojit se od PC
        </button>
        <button type="button" class="mob-glass-btn close" onclick="closeMobileSettings()">
            Zavřít
        </button>
    </div>

    <script>
        // Auto scale to fit width if needed (e.g., iPhone SE is 320px wide)
        function scaleUI() {
            const container = document.getElementById('mirror-container');
            if (window.innerWidth < 380) {
                const scale = window.innerWidth / 380;
                container.style.transform = `scale(${scale})`;
            } else {
                container.style.transform = 'none';
            }
        }
        window.addEventListener('resize', scaleUI);
        scaleUI();

        function sendEval(codeStr) {
            fetch('/api/mirror/mobile_action/{{ session_id }}', { 
                method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ action: "eval", code: codeStr }) 
            }).catch(()=>{});
            if ("vibrate" in navigator) { navigator.vibrate(20); }
        }
        
        function sendInput(id, val) {
            fetch('/api/mirror/mobile_action/{{ session_id }}', { 
                method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ action: "input", id: id, value: val }) 
            }).catch(()=>{});
        }

        document.getElementById('mirror-container').addEventListener('click', function(e) {
            let btn = e.target.closest('[onclick]');
            if (btn) {
                let code = btn.getAttribute('onclick');
                if (code) {
                    e.preventDefault(); e.stopPropagation();
                    sendEval(code);
                }
            }
        }, true);
        
        document.getElementById('mirror-container').addEventListener('input', function(e) {
            let el = e.target;
            if (el.tagName === 'INPUT' && el.id) {
                sendInput(el.id, el.value);
            }
        });

        function openMobileSettings() { document.getElementById('mobile-settings-overlay').style.display = 'flex'; }
        function closeMobileSettings() { document.getElementById('mobile-settings-overlay').style.display = 'none'; }
        function disconnectAndClose() { closeMobileSettings(); window.location.href = '/mobilni-sdileni'; }
    </script>

    <script>
        const sessionId = '{{ session_id }}';
        
        function requestConnection() {
            const sDesc = document.getElementById('status-desc');
            sDesc.innerHTML = 'Odesílám žádost...';
            fetch('/api/mirror/request_connection/{{ session_id }}', {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if(data.status === 'error') {
                    sDesc.innerHTML = 'Chyba: ' + data.message;
                }
            })
            .catch(e => {
                sDesc.innerHTML = 'Chyba připojení k serveru.';
            });
        }
        
        function connectSSE() {
            const source = new EventSource('/api/mirror/mobile_state/' + sessionId);
            source.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const statusOverlay = document.getElementById('status-overlay');
                const container = document.getElementById('mirror-container');
                const sTitle = document.getElementById('status-title');
                const sDesc = document.getElementById('status-desc');
                
                if (data.status === 'offline') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'PC JE OFFLINE';
                    sDesc.textContent = 'Aplikace přestala odesílat data. Zkontrolujte, zda PC neusnulo.';
                } else if (data.status === 'request_needed') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'IDPK ZRCADLO';
                    sDesc.innerHTML = '<button onclick="requestConnection()" style="padding: 15px 30px; font-size: 18px; font-weight: bold; background: #22c55e; color: white; border: none; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 15px rgba(34,197,94,0.4); margin-top: 15px;">Zažádat o připojení</button>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'lockout') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Další pokus za <b style="font-size:24px;">' + data.remaining + '</b> sekund.';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'rejected') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Nelze se připojit.';
                    source.close();
                } else if (data.status === 'timeout') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'VYPRŠEL ČAS';
                    sDesc.innerHTML = 'PC neodpovědělo včas na vaši žádost.<br><button onclick="requestConnection()" style="padding: 15px 30px; font-size: 18px; font-weight: bold; background: #22c55e; color: white; border: none; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 15px rgba(34,197,94,0.4); margin-top: 15px;">Zkusit znovu</button>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ';
                    sDesc.innerHTML = 'Potvrďte prosím na vašem PC žádost o připojení ke sdílení.<br><br><i class="fas fa-spinner fa-spin spinner" style="font-size: 24px; color: #F4CC17;"></i>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'block';
                } else if (data.status === 'online') {
                    statusOverlay.style.display = 'none';
                    if (data.state && data.state.dom) {
                        if (!window.lastDom || window.lastDom !== data.state.dom) {
                            window.lastDom = data.state.dom;
                            if (typeof morphdom !== 'undefined') {
                                let temp = document.createElement('div');
                                temp.id = 'mirror-container';
                                temp.innerHTML = data.state.dom;
                                morphdom(container, temp, {
                                    onBeforeElUpdated: function(fromEl, toEl) {
                                        if (fromEl.isEqualNode && fromEl.isEqualNode(toEl)) return false;
                                        return true;
                                    }
                                });
                            } else {
                                container.innerHTML = data.state.dom;
                            }
                            scaleUI(); // Re-apply scaling just in case
                        }
                    }
                }
            };
            source.onerror = function() {
                document.getElementById('status-overlay').style.display = 'flex';
                document.getElementById('status-title').textContent = 'CHYBA SPOJENÍ';
                document.getElementById('status-desc').textContent = 'Ztratili jsme spojení se serverem.';
            };
        }
        connectSSE();
    </script>
</body>
</html>
    """
    return render_template_string(html, session_id=session_id)


@app.route('/mobilni-sdileni')
def mobilni_sdileni_page():
    html = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDPK Ovladač - Mobilní Zrcadlo</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --primary: #035689; --secondary: #023e63; --accent: #F4CC17; --text: #f0f0f0; --bg: #0b1121; }
        * { box-sizing: border-box; }
        body { margin: 0; padding: 0; background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; }
        
        .header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 60px 20px; text-align: center; border-bottom: 3px solid var(--accent); }
        .header h1 { margin: 0 0 10px 0; font-size: 32px; letter-spacing: 1px; color: white; }
        .header p { margin: 0; font-size: 18px; color: rgba(255,255,255,0.8); }
        
        .badge { display: inline-block; background: var(--accent); color: #000; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; margin-bottom: 15px; }
        
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        
        .card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 25px; margin-bottom: 30px; }
        .card h2 { color: var(--accent); margin-top: 0; font-size: 22px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        
        .steps { padding-left: 20px; margin-bottom: 0; }
        .steps li { margin-bottom: 15px; font-size: 16px; }
        .steps li::marker { color: var(--accent); font-weight: bold; }
        
        .faq-item { margin-bottom: 20px; }
        .faq-q { font-weight: 600; font-size: 17px; margin-bottom: 5px; color: white; display: flex; align-items: flex-start; gap: 8px; }
        .faq-a { color: rgba(255,255,255,0.7); margin: 0 0 0 25px; }
        
        .footer { text-align: center; padding: 30px; color: rgba(255,255,255,0.5); font-size: 14px; margin-top: 20px; }
        .back-btn { display: inline-block; background: rgba(255,255,255,0.1); color: white; text-decoration: none; padding: 10px 20px; border-radius: 8px; margin-top: 20px; transition: 0.2s; }
        .back-btn:hover { background: rgba(255,255,255,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <span class="badge">Premium / Beta Tester</span>
        <h1><i class="fas fa-mobile-alt"></i> Ovladač v Kapse</h1>
        <p>Propojte svůj telefon s palubním počítačem a ovládejte hru odkudkoliv.</p>
    </div>
    
    <div class="container">
        <div class="card">
            <h2><i class="fas fa-magic"></i> Jak to funguje?</h2>
            <p>Funkce <strong>Mobilní zrcadlo</strong> umožňuje živě přenášet obrazovku palubního počítače z vašeho monitoru přímo do mobilu. Všechna tlačítka na mobilu okamžitě reagují ve hře na počítači. Nemusíte přepínat okna!</p>
            <ol class="steps">
                <li>Otevřete Palubní Počítač na PC (Ovladač).</li>
                <li>Klikněte vpravo nahoře na žlutou ikonku <strong>hvězdičky</strong> (nebo nastavení zrcadla).</li>
                <li>Vezměte svůj mobil a <strong>naskenujte zobrazený QR kód</strong> fotoaparátem.</li>
                <li>Otevřete odkaz a hotovo! Váš mobil je nyní plnohodnotný ovladač.</li>
            </ol>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-life-ring"></i> Řešení problémů (FAQ)</h2>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Prohlížeč v mobilu mě po čase odpojí</div>
                <p class="faq-a">Zrcadlo vyžaduje nepřetržité spojení. Pokud vám zhasne displej nebo aplikaci minimalizujete, prohlížeč spojení ukončí. <strong>Řešení:</strong> Nastavte si v mobilu, aby displej nezhasínal, nebo nechte stránku neustále otevřenou.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Stránka ukazuje "SPOJENÍ PŘERUŠENO"</div>
                <p class="faq-a">Váš počítač přestal odesílat data. To se stane, pokud aplikaci zavřete, nebo pokud má PC výpadek internetu. <strong>Řešení:</strong> Restartujte Palubní Počítač na PC a znovu načtěte stránku na mobilu.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Tlačítka reagují opožděně</div>
                <p class="faq-a">Spojení je závislé na rychlosti vašeho internetu (obě zařízení komunikují přes server). Doporučujeme mít jak PC, tak mobil připojené na stabilní Wi-Fi nebo 4G/5G síť.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Jsem Beta Tester, ale QR kód se mi neukazuje</div>
                <p class="faq-a">Ujistěte se, že jste v Launcheru přihlášeni přes Discord a máte příslušnou roli na našem Discord serveru. Zkuste se případně v Launcheru odhlásit a znovu přihlásit.</p>
            </div>
        </div>
        
        <div style="text-align: center;">
            <a href="javascript:history.back()" class="back-btn"><i class="fas fa-arrow-left"></i> Zpět</a>
        </div>
    </div>
    
    <div class="footer">
        &copy; 2026 IDPK OIS - Vytvořeno pro komunitu
    </div>
</body>
</html>
    """
    return render_template_string(html)

def check_and_download_latest_gtfs():

    try:
        import requests, os
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not supabase_url or not supabase_key: return

        headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
        r = requests.get(f"{supabase_url}/rest/v1/gtfs_feed_versions?select=version_tag,release_url&order=id.desc&limit=1", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                tag = data[0].get("version_tag")
                if os.path.exists(".current_gtfs_version"):
                    with open(".current_gtfs_version", "r") as f:
                        if f.read().strip() == tag:
                            return 

                download_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'marek-1cz/DataCoreBot')}/releases/download/{tag}/gtfs_stops_idpk.db"
                print(f"Stahuji novou GTFS databázi ({tag})...")
                dl_r = requests.get(download_url, stream=True)
                if dl_r.status_code == 200:
                    with open("gtfs_stops.db", "wb") as f:
                        for chunk in dl_r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    with open(".current_gtfs_version", "w") as f:
                        f.write(tag)
                    print(f"GTFS databáze aktualizována na {tag}.")
                else:
                    print(f"Nelze stáhnout GTFS {tag}: HTTP {dl_r.status_code}")
    except Exception as e:
        print(f"Chyba při aktualizaci GTFS: {e}")

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    start_map_background_task()
    check_and_download_latest_gtfs()
    if token:
        Thread(target=run_discord_bot, args=(token,), daemon=True).start()
    else:
        print("KRITICKÁ CHYBA: DISCORD_TOKEN chybí! (Web běží dál bez Bota)")
    run_web()

