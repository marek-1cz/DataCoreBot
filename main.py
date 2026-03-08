import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from threading import Thread
from supabase import create_client
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import uuid
import urllib.request
import re

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 
prague_tz = ZoneInfo("Europe/Prague")

DEPLOY_TIME = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M:%S")

URL_MALE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png"
URL_VELKE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png"

# ==========================================
# 1. HTML ŠABLONY
# ==========================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projekt OIS IDPK</title>
    <link rel="icon" type="image/png" href="{{ logo_male }}">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { --bg-dark: #0f172a; --bg-panel: #1e293b; --blue-main: #38bdf8; --blue-hover: #0284c7; --text-main: #f8fafc; --text-muted: #94a3b8; --danger: #ef4444; --success: #10b981; --warning: #f59e0b; }
        body { font-family: 'Segoe UI', sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; }
        .top-nav { background-color: rgba(15, 23, 42, 0.9); padding: 15px 40px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 100; }
        .logo { font-size: 24px; font-weight: 800; color: var(--blue-main); text-decoration: none; display: flex; align-items: center; gap: 10px; }
        .nav-links a { color: var(--text-main); text-decoration: none; margin-left: 20px; font-weight: 500; }
        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        .btn { display: inline-block; background-color: var(--blue-main); color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; }
        .btn-danger { background-color: var(--danger); }
        .btn-success { background-color: var(--success); }
        input[type="text"], input[type="number"], select { width: 100%; padding: 10px; margin: 8px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; background-color: var(--bg-panel); border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background-color: #0f172a; color: var(--blue-main); }
        .dashboard-wrapper { display: flex; min-height: 100vh; }
        .sidebar { width: 250px; background-color: var(--bg-panel); border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .sidebar-link { display: block; padding: 12px 20px; color: var(--text-muted); text-decoration: none; border-left: 3px solid transparent; }
        .sidebar-link:hover { background-color: rgba(56, 189, 248, 0.1); color: var(--blue-main); border-left-color: var(--blue-main); }
        .dashboard-content { flex-grow: 1; padding: 30px; overflow-y: auto; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }
        .modal { background: var(--bg-panel); padding: 30px; border-radius: 15px; width: 700px; max-width: 90%; border-top: 5px solid var(--blue-main); }
        .role-tag { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin: 2px; color: white; }
    </style>
</head>
<body>{% block layout %}{% endblock %}</body></html>
"""

PUBLIC_LAYOUT = """<nav class="top-nav"><a href="/" class="logo"><img src="{{ logo_male }}" alt="Logo" style="height: 30px;">OIS IDPK</a><div class="nav-links"><a href="/">Domů</a><a href="/download">Download</a><a href="/team">Náš Tým</a><a href="/dashboard" class="admin-link">Dashboard 🔒</a></div></nav><div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for cat, msg in messages %}<div style="padding:15px; border-radius:5px; margin-bottom:20px; background: rgba(56,189,248,0.2); color:white; border:1px solid var(--blue-main);">{{ msg }}</div>{% endfor %}{% endif %}{% endwith %}{% block content %}{% endblock %}</div>"""

DASHBOARD_LAYOUT = """<div class="dashboard-wrapper"><div class="sidebar"><div style="padding:20px; text-align:center;"><a href="/" class="logo" style="font-size:20px;"><img src="{{ logo_male }}" style="height:24px;"> OIS IDPK</a></div><div class="sidebar-menu"><a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a><a href="/dashboard/app_settings" class="sidebar-link"><i class="fas fa-cog"></i> Nastavení Aplikace</a><a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-cloud-download-alt"></i> Správa Stahování</a><a href="/dashboard/pending_roles" class="sidebar-link"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a><a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a><a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a><a href="/dashboard?filter=banned" class="sidebar-link" style="color:var(--warning);"><i class="fas fa-ban"></i> Seznam BANů</a><a href="/dashboard?filter=deleted" class="sidebar-link" style="color:var(--danger);"><i class="fas fa-trash-alt"></i> Smazaní (Záloha)</a></div><div style="padding: 20px; margin-top:auto;"><div style="font-size:10px; color:var(--text-muted); text-align:center; margin-bottom:10px; border-top:1px solid #334155; padding-top:10px;">POSLEDNÍ UPDATE:<br><b>{{ deploy_time }}</b></div><a href="/logout" class="btn btn-danger" style="width:100%; text-align:center; box-sizing:border-box;">Odhlásit</a></div></div><div class="dashboard-content">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for cat, msg in messages %}<div style="padding:15px; border-radius:5px; margin-bottom:20px; background: rgba(56,189,248,0.2); color:white; border:1px solid var(--blue-main);">{{ msg }}</div>{% endfor %}{% endif %}{% endwith %}{% block content %}{% endblock %}</div></div>"""

# --- GLOBÁLNÍ FUNKCE ---
def get_db():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        return create_client(url, key)
    except: return None

async def async_send_log(title, description, color=0x38bdf8):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(prague_tz))
            try: await channel.send(embed=embed)
            except: pass
            break

def send_log(title, description, color=0x38bdf8):
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(async_send_log(title, description, color), bot.loop)

def _cors_jsonify(data):
    resp = jsonify(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

def render_public(template_string, **kwargs):
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = html.replace('{{ deploy_time }}', DEPLOY_TIME)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

# ==========================================
# PUBLIC FLASK STRÁNKY (Nyní vrácené!)
# ==========================================

@app.route('/')
def home():
    html = """
    <div style="text-align: center; padding: 50px 0;">
        <img src="{{ logo_velke }}" alt="DataCoreBot Logo" style="max-width: 450px; width: 100%; height: auto; margin-bottom: 20px; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5));">
        <p style="font-size: 1.2em; color: var(--text-muted); max-width: 600px; margin: 0 auto 30px auto;">Moderní, rychlý a bezpečný software s nejlepším zabezpečením.</p>
        <a href="/download" class="btn" style="font-size: 18px; padding: 15px 30px; border-radius: 30px;"><i class="fas fa-download"></i> Získat Software</a>
    </div>
    """
    return render_public(html)

@app.route('/team')
def team(): 
    try: team_members = get_db().table("team").select("*").execute().data if get_db() else []
    except: team_members = []
    
    html = """
    <h2 style="color: var(--blue-main); border-bottom: 2px solid #334155; padding-bottom: 10px;">Náš Tým</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
        {% for member in team %}
        <div style="background-color: var(--bg-panel); border-radius: 10px; padding: 20px; text-align: center; border-top: 4px solid var(--blue-main);">
            <img src="{{ member.get('image_url', '') }}" alt="Fotka" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 15px; border: 3px solid #334155;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <h3 style="font-size: 20px; font-weight: bold; margin: 0 0 5px 0;">{{ member.get('name', '') }}</h3>
            <div style="color: var(--blue-main); font-size: 14px; margin-bottom: 15px;">@{{ member.get('discord_nick', '') }}</div>
            <p style="color: var(--text-muted); font-size: 14px; line-height: 1.5; margin-bottom: 15px;">{{ member.get('description', '') }}</p>
            <div>
                {% set roles_input = member.get('role_name', '').split(',') if member.get('role_name') else [] %}
                {% for r in roles_input %}
                    {% set parts = r.split('|') %}
                    {% set r_name = parts[0].strip() %}
                    {% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                    <span class="role-tag" style="background-color: {{ r_color }}33; color: {{ r_color }}; border: 1px solid {{ r_color }};">{{ r_name }}</span>
                {% endfor %}
            </div>
        </div>
        {% else %}
        <p style="color: var(--text-muted);">Zatím nebyli přidáni žádní členové týmu.</p>
        {% endfor %}
    </div>
    """
    return render_public(html, team=team_members)

@app.route('/download')
def download_home():
    html = """
    <div style="text-align: center; padding: 60px 20px; max-width: 700px; margin: 50px auto; background-color: var(--bg-panel); border-radius: 15px; box-shadow: 0 15px 30px rgba(0,0,0,0.5); border-top: 5px solid #5865F2;">
        <h2 style="color: var(--text-main); font-size: 2.2em; margin-top: 0;"><i class="fas fa-shield-alt" style="color: var(--blue-main);"></i> Oficiální distribuce softwaru</h2>
        <p style="color: var(--text-muted); font-size: 1.1em; line-height: 1.6; margin-bottom: 20px; text-align: left; padding: 0 20px;">Vážený uživateli,<br><br>velice si vážíme Vašeho zájmu o <b>Projekt OIS IDPK</b>. Z důvodu zachování maximální bezpečnosti jsme se rozhodli přesunout veškerou distribuci našeho softwaru na naši zabezpečenou komunikační platformu.</p>
        <div style="background-color: rgba(88, 101, 242, 0.1); border: 1px solid #5865F2; padding: 30px 20px; border-radius: 10px; margin: 30px 20px;">
            <p style="color: var(--text-main); font-weight: bold; font-size: 1.2em; margin-top: 0;">Pro stažení softwaru se prosím připojte na náš Discord.</p>
            <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Kliknutím na logo níže budete přesměrováni přímo na náš server, kde naleznete instalační panel a další pokyny.</p>
            <a href="https://discord.gg/vmTagbC9mF" target="_blank" style="display: inline-block; text-decoration: none; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'"><i class="fab fa-discord" style="font-size: 120px; color: #5865F2; filter: drop-shadow(0px 10px 15px rgba(88,101,242,0.4));"></i></a>
        </div>
    </div>
    """
    return render_public(html)

@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db: return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if len(resp.data) == 0:
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný odkaz!</h2><p>Vygenerujte si nový na našem Discord serveru.</p></div>")
            
        user = resp.data[0]
        if user.get("is_banned"):
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Přístup zamítnut</h2><p>Váš účet má BAN.</p></div>")
        elif user.get("is_deleted"):
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Účet neexistuje</h2><p>Váš účet byl smazán administrátorem.</p></div>")
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data:
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--warning);'>Chyba verze</h2><p>Vybraná verze již není k dispozici.</p></div>")
            
        v_data = v_resp.data[0]
        html = f"""
        <div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; border-top: 4px solid var(--success);">
            <h2 style="color: var(--success); margin-top: 0;"><i class="fas fa-check-circle"></i> Ověření úspěšné</h2>
            <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Přihlášen jako: <strong>{user.get('nick', 'Neznámý')}</strong> (ID: #{user.get('app_id', '')})</p>
            <div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;">
                <h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3>
                <p style="margin: 0; color: var(--text-main);">Instalátor: <strong>{v_data.get('version_name', '')}</strong></p>
            </div>
            <a href="/api/get_file/{token}?v={version_id}" class="btn btn-success" style="font-size: 18px; padding: 15px 30px; display: block; border-radius: 8px; text-decoration: none;"><i class="fas fa-download"></i> Stáhnout Soubor</a>
        </div>
        """
        return render_public(html)
    except:
        return "Došlo k systémové chybě."

@app.route('/api/get_file/<token>')
def api_get_file(token):
    db = get_db()
    if not db: return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if len(resp.data) == 0: return "Neplatný token."
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"): return "Přístup zamítnut."
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data: return "Verze nenalezena."
            
        file_url = v_resp.data[0]['file_url']
        version_name = v_resp.data[0]['version_name']
        
        now_str = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M")
        try:
            db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": version_name, "downloaded_at": now_str}).execute()
            send_log("📥 Stahování softwaru", f"Uživatel **{user.get('nick', 'Neznámý')}** (ID: `{user['discord_id']}`) zahájil stahování: **{version_name}**.", 0x38bdf8)
        except: pass
        
        version_name_clean = version_name.replace(" ", "_")
        file_ext = "zip" 
        
        if "pixeldrain.com/u/" in file_url: file_url = file_url.replace("/u/", "/api/file/")
        if "1drv.ms" in file_url or "onedrive.live.com" in file_url or "1drv.com" in file_url: file_url = file_url.split("?")[0] + "?download=1"
        if "dropbox.com" in file_url:
            file_url = file_url.replace("dl=0", "dl=1")
            if "dl=1" not in file_url: file_url += "?dl=1" if "?" not in file_url else "&dl=1"

        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Accept': '*/*'})
        remote_response = urllib.request.urlopen(req)

        def generate():
            while True:
                chunk = remote_response.read(8192)
                if not chunk: break
                yield chunk

        content_type = remote_response.headers.get('Content-Type', 'application/octet-stream')
        return Response(stream_with_context(generate()), headers={'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name_clean}.{file_ext}"', 'Content-Type': content_type})
    except Exception as e:
        return f"Chyba: Zkontrolujte prosím, zda je odkaz v Dashboardu platný. ({e})"


# ==========================================
# API PRO SOFTWARE A DASHBOARD
# ==========================================

@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_status():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "disabled", "message": "OMLOUVÁME SE, SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA)."})
    except: pass
    return _cors_jsonify({"status": "enabled"})

@app.route('/api/app_login', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_login():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    if not data: return _cors_jsonify({"status": "error", "message": "Chybí data."})
    
    identifier = str(data.get("identifier", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})

        user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},nick.ilike.{identifier}").execute()
        if not user_resp.data and identifier.isdigit():
            user_resp = db.table("users").select("*").eq("app_id", int(identifier)).execute()
            
        if not user_resp.data: return _cors_jsonify({"status": "error", "message": "Uživatel nenalezen."})
        user = user_resp.data[0]
        
        if user.get("is_banned"):
            send_log("⛔ Pokus o přihlášení (BAN)", f"Zabanovaný uživatel `{user.get('nick')}` se pokusil zapnout software.", 0xef4444)
            return _cors_jsonify({"status": "banned", "message": "Tento účet má BAN."})
        
        db_hwid = user.get("hwid")
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "" and str(db_hwid) != req_hwid:
            send_log("🔒 HWID Neshoda", f"Uživatel `{user.get('nick')}` se hlásí z jiného PC!\nUloženo: `{db_hwid}`\nNové: `{req_hwid}`", 0xf59e0b)
            return _cors_jsonify({"status": "hwid_error", "message": "Tento účet je vázán na jiný počítač."})
            
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", user.get("discord_id")).execute()
        
        async def send():
            try:
                u = bot.get_user(int(user.get("discord_id"))) or await bot.fetch_user(int(user.get("discord_id")))
                if u:
                    embed = discord.Embed(title="🛡️ Ověření přihlášení", description=f"Byl zaznamenán pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPotvrďte přístup tlačítkem níže.", color=0x38bdf8)
                    await u.send(embed=embed, view=AppAuthView(token, user.get("discord_id"), is_dm=True))
            except: pass
        if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
        
        return _cors_jsonify({"status": "waiting", "discord_id": user.get("discord_id")})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        user = user_resp.data[0]
        
        if user.get("login_token") == "approved":
            db_hwid = user.get("hwid")
            if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
                db.table("users").update({"hwid": req_hwid, "login_token": ""}).eq("discord_id", discord_id).execute()
            else:
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "success", "display_name": user.get("nick")}) # OPRAVENO status z "approved" na "success" aby ladil s JS!
            
        elif user.get("login_token") == "rejected":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."}) # OPRAVENO z "rejected" na "error" aby JS ukázal modál
            
        return _cors_jsonify({"status": "pending"}) # OPRAVENO status z "waiting" na "pending" aby to ladilo s JS !!
    except: return _cors_jsonify({"status": "error"})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error", "message": "Tento účet neexistuje."})
        user = user_resp.data[0]
        if user.get("is_banned"): return _cors_jsonify({"status": "error", "message": "Tento účet má BAN."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán."})
        db_hwid = user.get("hwid")
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "" and str(db_hwid) != req_hwid:
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Váš počítač nesouhlasí."})
        return _cors_jsonify({"status": "success"}) # OPRAVENO na success
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_ping', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_ping():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    action = data.get("action", "ping")
    db = get_db()
    try:
        now_str = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M:%S")
        user_resp = db.table("users").select("launch_count, total_time").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        
        updates = {"last_active": now_str, "is_online": True}
        if action == "start":
            count = user_resp.data[0].get("launch_count") or 0
            updates["launch_count"] = count + 1
        elif action == "stop":
            updates["is_online"] = False
        elif action == "ping":
            time_val = user_resp.data[0].get("total_time") or 0
            updates["total_time"] = time_val + 60
            
        db.table("users").update(updates).eq("discord_id", discord_id).execute()
        return _cors_jsonify({"status": "ok"})
    except: return _cors_jsonify({"status": "error"})


# ==========================================
# DASHBOARD A ADMIN ROUTES
# ==========================================
@app.route('/login_request', methods=['POST'])
def login_request():
    discord_id = request.form.get('discord_id'); db = get_db()
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
                if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            else: flash('Účet neexistuje, nemá povolený přístup, nebo byl zablokován.', 'error')
        except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): 
    html = """<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; border-top: 4px solid var(--warning);"><h2 style="color: var(--warning); margin-top: 0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2><p style="color: var(--text-main); font-size: 16px;">Byla Vám odeslána soukromá zpráva na Discord.</p></div><script>setInterval(() => { fetch('/api/check_auth/{{ discord_id }}').then(r => r.json()).then(data => { if(data.status === 'approved') { window.location.href = '/dashboard'; } else if(data.status === 'rejected') { window.location.href = '/dashboard'; } }); }, 2000);</script>"""
    return render_public(html, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    try:
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
            if user:
                t = user[0].get("login_token")
                if t == "approved":
                    session['logged_in'] = True; session['discord_id'] = discord_id
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                    return {"status": "approved"}
                elif t == "rejected":
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                    return {"status": "rejected"}
    except: pass
    return {"status": "waiting"}

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == os.environ.get("ADMIN_PASSWORD", "admin"):
            session['logged_in'] = True; session['discord_id'] = 'admin'
            return redirect(url_for('dashboard_main'))
    if not session.get('logged_in'):
        html_login = """<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; border-top: 4px solid var(--blue-main);"><h2 style="text-align: center; color: var(--blue-main); margin-top: 0;"><i class="fas fa-lock"></i> Dashboard 2FA</h2><form method="POST" action="/login_request"><label style="font-weight: bold; font-size: 12px; color: var(--text-muted);">VAŠE DISCORD ID</label><input type="text" name="discord_id" required><button type="submit" class="btn" style="width: 100%; margin-top: 10px;"><i class="fab fa-discord"></i> Odeslat žádost o přihlášení</button></form></div>"""
        return render_public(html_login)
    
    users_data = []
    try:
        if get_db():
            query = get_db().table("users").select("*")
            f = request.args.get('filter')
            if f == 'banned': query = query.eq("is_banned", True).eq("is_deleted", False)
            elif f == 'deleted': query = query.eq("is_deleted", True)
            elif f: query = query.ilike("role", f"%{f}%").eq("is_deleted", False)
            else: query = query.eq("is_deleted", False).order("app_id")
            users_data = query.execute().data
    except Exception as e: flash(f"Chyba při načítání dat: {e}", "error")
    
    html = """<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);">{{ title }}</h2><div style="background: var(--bg-panel); padding: 10px 20px; border-radius: 8px; font-weight: bold; border: 1px solid #334155;">Celkem: <span style="color: var(--blue-main);">{{ users|length }}</span></div></div><div style="overflow-x: auto;"><table><tr><th>App ID</th><th>Discord ID</th><th>Nick</th><th>Role</th><th>Zaregistrován</th><th>Status</th><th>Akce</th></tr>{% for user in users %}<tr style="opacity: {{ '0.5' if user.get('is_deleted') else '1' }};"><td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td><td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td><td><strong>{{ user.get('nick', '') }}</strong></td><td>{{ user.get('role', '') }}</td><td style="color: var(--text-muted); font-size: 13px;">{{ user.get('registered_at', 'Neznámé') if user.get('registered_at') else 'Neznámé' }}</td><td>{% if user.get('is_deleted') %}<span style="color: var(--danger); font-weight: bold;">Smazán</span>{% elif user.get('is_banned') %}<span style="color: var(--warning); font-weight: bold;">BANNED</span>{% else %}<span style="color: var(--success);">Aktivní</span>{% endif %}</td><td><button class="btn" style="padding: 6px 12px; font-size: 12px;" onclick="openModal('{{ user.get('app_id', '') }}', '{{ user.get('discord_id', '') }}', '{{ user.get('nick', '') }}', '{{ user.get('role', 'User') }}', '{{ user.get('hwid', '') }}', '{{ user.get('is_banned', False) }}', '{{ user.get('is_deleted', False) }}', '{{ user.get('dashboard_access', False) }}', '{{ user.get('registered_at', '') }}')">Profil</button></td></tr>{% endfor %}</table></div>"""
    return render_dashboard(html, users=users_data, title="Přehled uživatelů", deploy_time=DEPLOY_TIME)

@app.route('/api/get_profile_data/<discord_id>')
def get_profile_data(discord_id):
    if not session.get('logged_in'): return jsonify({"joined_at": "Neznámé", "status": "Neznámý", "downloads": []})
    joined_at = "Neznámé"; status = "Neznámý"; app_status_html = "<span style='color: #64748b;'><i>Neaktivní</i></span>"; stats_html = ""; dls = []
    try:
        if bot.guilds:
            for g in bot.guilds:
                m = g.get_member(int(discord_id))
                if m:
                    joined_at = m.joined_at.strftime("%d.%m.%Y") if m.joined_at else "Neznámé"
                    status = str(m.status)
                    break
        db = get_db()
        if db:
            dls = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data
            db_user = db.table("users").select("last_active, is_online, launch_count, total_time").eq("discord_id", discord_id).execute().data
            if db_user:
                u = db_user[0]
                is_on = u.get("is_online", False)
                la_str = u.get("last_active") or ""
                if is_on and la_str:
                    try:
                        last_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S")
                        if (datetime.now(prague_tz).replace(tzinfo=None) - last_dt).total_seconds() > 120:
                            is_on = False
                            db.table("users").update({"is_online": False}).eq("discord_id", discord_id).execute()
                    except: pass
                
                m, s = divmod(u.get("total_time") or 0, 60)
                h, m = divmod(m, 60)
                
                if is_on: app_status_html = '<span style="color: var(--success); font-weight:bold;">🟢 Aktivní právě teď</span>'
                else: app_status_html = f'<span style="color: var(--danger);">🔴 Offline</span> (Naposledy: {la_str or "Nikdy"})'
                stats_html = f"<div style='margin-top:10px; font-size:12px; color:var(--text-muted); border-top: 1px solid #334155; padding-top: 10px;'><div><b>Spuštění:</b> {u.get('launch_count') or 0}x</div><div style='margin-top:5px;'><b>Čas:</b> {h}h {m}m {s}s</div></div>"
    except: pass
    return jsonify({"joined_at": joined_at, "status": status, "app_status": app_status_html, "stats": stats_html, "downloads": dls})

@app.route('/dashboard/app_settings', methods=['GET'])
def dashboard_app_settings():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    soft_enabled = True; dl_enabled = True
    try:
        db = get_db()
        if db:
            res = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled"]).execute()
            for r in res.data:
                if r.get('setting_key') == 'software_enabled' and str(r.get('setting_value')).lower() == 'false': soft_enabled = False
                if r.get('setting_key') == 'downloads_enabled' and str(r.get('setting_value')).lower() == 'false': dl_enabled = False
    except: pass
    
    html = """
    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        <div style="flex: 1; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; text-align: center; border-top: 4px solid {{ 'var(--success)' if soft_enabled else 'var(--danger)' }};">
            <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-desktop"></i> Status Softwaru (Kill-Switch)</h3>
            <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if soft_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if soft_enabled else 'fa-ban' }}"></i></div>
            <form action="/dashboard/toggle_setting" method="POST">
                <input type="hidden" name="key" value="software_enabled">
                <input type="hidden" name="val" value="{{ 'False' if soft_enabled else 'True' }}">
                <button type="submit" class="btn {{ 'btn-danger' if soft_enabled else 'btn-success' }}" style="width: 100%;">{{ 'VYPNOUT SOFTWARE' if soft_enabled else 'ZAPNOUT SOFTWARE' }}</button>
            </form>
        </div>
        <div style="flex: 1; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; text-align: center; border-top: 4px solid {{ 'var(--success)' if dl_enabled else 'var(--danger)' }};">
            <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-cloud-download-alt"></i> Status Stahování</h3>
            <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if dl_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if dl_enabled else 'fa-ban' }}"></i></div>
            <form action="/dashboard/toggle_setting" method="POST">
                <input type="hidden" name="key" value="downloads_enabled">
                <input type="hidden" name="val" value="{{ 'False' if dl_enabled else 'True' }}">
                <button type="submit" class="btn {{ 'btn-danger' if dl_enabled else 'btn-success' }}" style="width: 100%;">{{ 'ZAKÁZAT STAHOVÁNÍ' if dl_enabled else 'POVOLIT STAHOVÁNÍ' }}</button>
            </form>
        </div>
    </div>
    """
    return render_dashboard(html, soft_enabled=soft_enabled, dl_enabled=dl_enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = []
    try:
        db = get_db()
        if db: versions = db.table("software_versions").select("*").order("id").execute().data
    except: pass
    
    html = """
    <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat Instalační Soubor (Verzi)</h3>
        <form action="/dashboard/add_version" method="POST">
            <input type="text" name="version_name" placeholder="Název zobrazený v menu (např. Stabilní v1.0)" required>
            <input type="url" name="file_url" placeholder="Přímý odkaz na stažení souboru" required>
            <select name="target_role" required>
                <option value="User">User (Uvidí všichni)</option>
                <option value="BT">BETA TESTER</option>
                <option value="DEV_SA">DEV / SERVER ADMIN</option>
            </select>
            <button type="submit" class="btn" style="width: 100%; margin-top:10px;">Přidat verzi do menu</button>
        </form>
    </div>
    <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-top: 20px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">📦 Dostupné soubory</h3>
        <table><tr><th>Název v Menu</th><th>Odkaz</th><th>Akce</th></tr>
        {% for v in versions %}
        <tr>
            <td><strong>{{ v.get('version_name', '') }}</strong></td>
            <td><a href="{{ v.get('file_url', '') }}" target="_blank" style="color: var(--blue-main);">Odkaz</a></td>
            <td><form action="/dashboard/delete_version" method="POST"><input type="hidden" name="version_id" value="{{ v.get('id', '') }}"><button type="submit" class="btn btn-danger">Smazat</button></form></td>
        </tr>
        {% endfor %}
        </table>
    </div>
    """
    return render_dashboard(html, versions=versions, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/toggle_setting', methods=['POST'])
def toggle_setting():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); k = request.form.get("key"); v = request.form.get("val")
    try:
        check = db.table("settings").select("*").eq("setting_key", k).execute()
        if not check.data: db.table("settings").insert({"setting_key": k, "setting_value": v}).execute()
        else: db.table("settings").update({"setting_value": v}).eq("setting_key", k).execute()
        flash('Nastavení bylo změněno!', 'success')
    except Exception as e: flash(f"Chyba: {e}", "error")
    return redirect(url_for('dashboard_app_settings'))

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try:
        get_db().table("software_versions").insert({"version_name": request.form.get("version_name"), "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}).execute()
    except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: get_db().table("software_versions").delete().eq("id", request.form.get("version_id")).execute()
    except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): return render_dashboard("Zatím nedostupné pro zkrácení - opravíme v dalším bloku. (Pro teď neřeš, soustředíme se na UI appky a login!)", deploy_time=DEPLOY_TIME)

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); discord_id = request.form.get("discord_id"); action = request.form.get("action"); nick = request.form.get("nick")
    if db and discord_id:
        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                db.table("users").update({"nick": nick, "role": r_str, "hwid": request.form.get("hwid"), "dashboard_access": True if request.form.get("dashboard_access") else False}).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str); flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute(); flash('BAN udělen.', 'warning')
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute(); flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute(); flash('Účet smazán (Soft Delete).', 'danger')
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute(); flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute(); flash('Účet trvale smazán.', 'dark')
        except: pass
    return redirect(url_for('dashboard_main'))

# ==========================================
# DISCORD TLAČÍTKA
# ==========================================
class DashboardAuthView(discord.ui.View):
    def __init__(self, token, discord_id):
        super().__init__(timeout=300)
        self.token = token; self.discord_id = discord_id

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
        super().__init__(timeout=300)
        self.token = token; self.discord_id = discord_id; self.is_dm = is_dm
        btn_verify = discord.ui.Button(label="Ano, ověřit (Jsem to já)", style=discord.ButtonStyle.success, emoji="✅", custom_id=f"av_{token}")
        btn_verify.callback = self.verify_btn; self.add_item(btn_verify)
        if self.is_dm:
            btn_reject = discord.ui.Button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌", custom_id=f"ar_{token}")
            btn_reject.callback = self.decline_btn; self.add_item(btn_reject)

    async def verify_btn(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.discord_id): return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.defer()
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", self.discord_id).execute().data
            if user and user[0].get("login_token") == self.token:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
                await interaction.edit_original_response(content="✅ **Ověřeno! Můžete se vrátit do aplikace.**", view=None, embed=None)
            else: await interaction.edit_original_response(content="❌ **Platnost vypršela.**", view=None, embed=None)
        if not self.is_dm: await asyncio.sleep(2); await interaction.message.delete()

    async def decline_btn(self, interaction: discord.Interaction):
        await interaction.response.defer()
        get_db().table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Zamítnuto.**", view=None, embed=None)

# ==========================================
# DISCORD INSTALÁTOR & VERZE (S pevnými ID)
# ==========================================
class VersionSelect(discord.ui.Select):
    def __init__(self, user_role):
        user_level = 1
        if 'BT' in user_role: user_level = 2
        if 'DEV' in user_role or 'SA' in user_role: user_level = 3
        
        options = []
        try:
            v_resp = get_db().table("software_versions").select("*").order("id").execute().data
            for v in v_resp:
                req_level = 1
                if v.get('target_role') == 'BT': req_level = 2
                if v.get('target_role') == 'DEV_SA': req_level = 3
                if user_level >= req_level:
                    options.append(discord.SelectOption(label=v.get('version_name'), value=str(v.get('id')), emoji="📦"))
        except: pass
            
        if not options: options.append(discord.SelectOption(label="Žádná verze", value="none"))
        super().__init__(placeholder="Vyber verzi k instalaci...", min_values=1, max_values=1, options=options[:25], custom_id="version_select_dropdown")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none": return await interaction.response.send_message("Aktuálně nejsou dostupné žádné soubory.", ephemeral=True)
        await interaction.response.send_message("<a:loading:123> Generuji zabezpečený odkaz...", ephemeral=True)
        try:
            token = str(uuid.uuid4())
            get_db().table("users").update({"download_token": token}).eq("discord_id", str(interaction.user.id)).execute()
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://datacorebot.onrender.com")
            link = f"{base_url}/download/{token}?v={self.values[0]}"
            await interaction.edit_original_response(content=f"**Projekt OIS IDPK - Odkaz připraven**\n🔗 {link}\n*Platí jen pro Vás.*")
        except: await interaction.edit_original_response(content="Chyba databáze.")

class VersionView(discord.ui.View):
    def __init__(self, user_role):
        super().__init__(timeout=None)
        self.add_item(VersionSelect(user_role))

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, custom_id="btn_agree_rules_v3", emoji="✅")
    async def agree_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("<a:loading:123> Ověřuji profil...", ephemeral=True)
        try:
            db = get_db()
            discord_id = str(interaction.user.id); nick = interaction.user.display_name; user_roles = "User"
            
            set_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute()
            if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
                return await interaction.edit_original_response(content="**Stahování softwaru je aktuálně globálně vypnuto.**")
                
            check = db.table("users").select("*").eq("discord_id", discord_id).execute()
            if len(check.data) > 0:
                user_data = check.data[0]
                if user_data.get('is_banned'): return await interaction.edit_original_response(content="**Přístup zamítnut:** Máte udělený BAN. 🛑")
                user_roles = user_data.get('role', 'User')
            else:
                highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                new_app_id = highest.data[0]["app_id"] + 1 if highest.data else 1000
                db.table("users").insert({ "app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "is_banned": False, "is_deleted": False, "dashboard_access": False, "login_token": "", "registered_at": datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M") }).execute()
            
            if isinstance(interaction.user, discord.Member): 
                try: await update_member_roles(interaction.user, user_roles)
                except: pass
            
            await interaction.edit_original_response(content="**Ověření úspěšné.** Vyberte soubor:", view=VersionView(user_roles))
        except: await interaction.edit_original_response(content="Došlo k chybě databáze.")

class DownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, custom_id="btn_start_install_v3", emoji="📥")
    async def download_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pravidla_text = "**Projekt OIS IDPK - Podmínky užití**\n\nPokračováním souhlasíte s pravidly:\n1. Je přísně zakázáno jakkoli modifikovat nebo šířit tento software.\n2. Vygenerovaný odkaz a HWID je vázáno na Váš osobní přístroj.\n\n*Souhlasíte s těmito podmínkami?*"
        await interaction.response.send_message(pravidla_text, view=RulesView(), ephemeral=True)

# ==========================================
# DISCORD BOT EVENTY
# ==========================================
intents = discord.Intents.default()
intents.members = True; intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    bot.add_view(DownloadView())
    bot.add_view(RulesView())
    print(f'Bot online: {bot.user}', flush=True)

def check_web_sa():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="web-sa") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, k tomuto příkazu nemáš oprávnění.", delete_after=10); return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator: return True
        await ctx.send(f"❌ {ctx.author.mention}, k tomuto příkazu nemáš oprávnění.", delete_after=10); return False
    return commands.check(predicate)

@bot.command()
@check_web_sa()
async def setup_download(ctx):
    embed = discord.Embed(title="📥 Projekt OIS IDPK - Instalace", description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a generování osobního odkazu ke stažení.", color=0x38bdf8)
    await ctx.send(embed=embed, view=DownloadView())
    send_log("🛠️ Setup Download", f"Uživatel {ctx.author.mention} vytvořil nový instalační panel v kanálu {ctx.channel.mention}.", 0xf59e0b)
    try: await ctx.message.delete()
    except: pass

@bot.command()
async def auth(ctx):
    try: await ctx.message.delete()
    except: pass
    u = get_db().table("users").select("login_token").eq("discord_id", str(ctx.author.id)).execute().data
    if u and u[0].get('login_token'):
        await ctx.send(f"🛡️ {ctx.author.mention}, potvrďte přihlášení do aplikace:", view=AppAuthView(u[0]['login_token'], str(ctx.author.id), False), delete_after=60)
    else:
        msg = await ctx.send(f"❌ {ctx.author.mention} Aktuálně nemáš žádný čekající požadavek.")
        await asyncio.sleep(5); await msg.delete()

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", description="Seznam dostupných příkazů rozdělený podle oprávnění.", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné příkazy", value="`!register` - Zaregistruje tě do databáze.\n`!auth` - Potvrzení přihlášení do aplikace.\n`!verze` - Seznam dostupných verzí.\n`!ping` - Odezva bota.\n`!help` - Tato nápověda.", inline=False)
    embed.add_field(name="🛡️ Správa databáze (Pro roli SM)", value="`!info [ID]` - Profil uživatele.\n`!db [ID]` - Povolí/zakáže 2FA do webu.\n`!ban [ID]` / `!unban [ID]` - BANování.\n`!delete [ID]` - Blokace z aplikace.\n`!perdelete [ID]` - Trvalé smazání.\n`!register [ID]` - Vytvoří účet cizímu.\n`!message #kanál [text]` - Zpráva jako bot.\n`!dm @uživatel [text]` - PM jako bot.", inline=False)
    embed.add_field(name="⚙️ Administrace (Pro roli web-sa)", value="`!setup_download` - Vygeneruje instalační panel.\n`!sm @uživatel` - Přidělí/odebere roli SM.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id: return await ctx.send(f"❌ Zadejte ID.")
    u = get_db().table("users").select("*").eq("discord_id", discord_id).execute().data
    if not u: return await ctx.send(f"❌ Nenalezen.")
    embed = discord.Embed(title=f"Uživatel: {u[0].get('nick')}", color=0x38bdf8)
    embed.add_field(name="ID", value=u[0].get('discord_id'), inline=True)
    await ctx.send(embed=embed)

def run_web(): app.run(host='0.0.0.0', port=8080, use_reloader=False)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
