import os, discord, asyncio, uuid, urllib.request, json, traceback, re
from discord.ext import commands, tasks
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

def get_prague_time(): return datetime.utcnow() + timedelta(hours=1)
DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

URL_MALE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png"
URL_VELKE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png"

@app.errorhandler(Exception)
def handle_exception(e):
    error_trace = traceback.format_exc()
    print(error_trace, flush=True)
    return f"<div style='background:#0f172a;color:#ef4444;padding:20px;font-family:monospace;border:2px solid #ef4444;'><h2>CHYBA APLIKACE (500)</h2><pre>{error_trace}</pre></div>", 500

# ==========================================
# 1. HTML ŠABLONY (VŠE V JEDNOM SOUBORU S PLNOU GRAFIKOU)
# ==========================================

BASE_HTML = """
<!DOCTYPE html><html lang="cs"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Projekt OIS IDPK</title>
<link rel="icon" type="image/png" href="{{ logo_male }}"><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg-dark:#0f172a;--bg-panel:#1e293b;--blue-main:#38bdf8;--blue-hover:#0284c7;--text-main:#f8fafc;--text-muted:#94a3b8;--danger:#ef4444;--success:#10b981;--warning:#f59e0b}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg-dark);color:var(--text-main);margin:0;padding:0}
.top-nav{background:rgba(15,23,42,0.9);padding:15px 40px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;backdrop-filter:blur(10px);z-index:100}
.logo{font-size:24px;font-weight:800;color:var(--blue-main);text-decoration:none;letter-spacing:1px;display:flex;align-items:center;gap:10px}
.nav-links a{color:var(--text-main);text-decoration:none;margin-left:20px;font-weight:500;transition:0.3s} .nav-links a:hover{color:var(--blue-main)}
.nav-links .admin-link{color:var(--text-muted);font-size:12px;margin-left:40px;border:1px solid #334155;padding:5px 10px;border-radius:5px}
.container{max-width:1200px;margin:40px auto;padding:0 20px}
.btn{display:inline-block;background:var(--blue-main);color:#000;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;border:none;cursor:pointer;transition:0.3s}
.btn:hover{background:var(--blue-hover);transform:translateY(-2px);color:#fff}
.btn-danger{background:var(--danger);color:#fff} .btn-warning{background:var(--warning);color:#000} .btn-success{background:var(--success);color:#fff} .btn-dark{background:#334155;color:#fff}
input,textarea,select{width:100%;padding:10px;margin:8px 0 15px;background:#0f172a;border:1px solid #334155;color:#fff;border-radius:5px;box-sizing:border-box}
table{width:100%;border-collapse:collapse;margin-top:10px;background:var(--bg-panel);border-radius:10px;overflow:hidden}
th,td{padding:15px;text-align:left;border-bottom:1px solid #334155} th{background:#0f172a;color:var(--blue-main);font-weight:600;font-size:13px;} tr:hover{background:#334155}
.role-tag{display:inline-block;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:bold;margin:2px}
.dashboard-wrapper{display:flex;min-height:100vh}
.sidebar{width:250px;background:var(--bg-panel);border-right:1px solid #334155;display:flex;flex-direction:column}
.sidebar-header{padding:20px;border-bottom:1px solid #334155;text-align:center} .sidebar-menu{padding:20px 0;flex-grow:1}
.sidebar-link{display:block;padding:12px 20px;color:var(--text-muted);text-decoration:none;font-weight:500;transition:0.2s;border-left:3px solid transparent}
.sidebar-link:hover, .sidebar-link.active{background:rgba(56,189,248,0.1);color:var(--blue-main);border-left-color:var(--blue-main)} .sidebar-link i{width:25px}
.dashboard-content{flex-grow:1;padding:30px;background:var(--bg-dark);overflow-y:auto}
.alert{padding:15px;border-radius:5px;margin-bottom:20px;font-weight:bold}
.alert-success{background:rgba(16,185,129,0.2);color:var(--success);border:1px solid var(--success)}
.alert-error,.alert-danger{background:rgba(239,68,68,0.2);color:var(--danger);border:1px solid var(--danger)}
.alert-warning{background:rgba(245,158,11,0.2);color:var(--warning);border:1px solid var(--warning)}
</style></head><body>{% block layout %}{% endblock %}</body></html>
"""

PUBLIC_LAYOUT = """
<nav class="top-nav"><a href="/" class="logo"><img src="{{ logo_male }}" style="height:30px;border-radius:4px;">OIS IDPK</a>
<div class="nav-links"><a href="/">Domů</a><a href="/download">Download</a><a href="/team">Náš Tým</a><a href="/supporters" style="color:var(--blue-main);font-weight:bold;text-shadow:0 0 10px rgba(56,189,248,0.6);"><i class="fas fa-heart"></i> Podporovatelé</a><a href="/dashboard" class="admin-link">Dashboard 🔒</a></div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}{% block content %}{% endblock %}</div>
"""

DASHBOARD_LAYOUT = """
<div class="dashboard-wrapper">
    <div class="sidebar"><div class="sidebar-header"><a href="/" class="logo" style="font-size:20px;justify-content:center;gap:8px;"><img src="{{ logo_male }}" style="height:24px;border-radius:4px;">OIS IDPK</a><div style="font-size:11px;color:var(--text-muted);margin-top:5px;">Dashboard</div></div>
        <div class="sidebar-menu">
            <a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
            <a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-bar"></i> Statistiky Webu</a>
            <a href="/dashboard/app_settings" class="sidebar-link"><i class="fas fa-cog"></i> Nastavení Aplikace</a>
            <a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-cloud-download-alt"></i> Správa Stahování</a>
            <a href="/dashboard/pending_roles" class="sidebar-link" style="color:#10b981;"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a>
            <a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a>
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a>
            <a href="/dashboard/supporters" class="sidebar-link" style="color:var(--blue-main);text-shadow:0 0 5px rgba(56,189,248,0.5);"><i class="fas fa-star"></i> Podporovatelé</a>
            <a href="/dashboard?filter=banned" class="sidebar-link" style="color:var(--warning);"><i class="fas fa-ban"></i> Seznam BANů</a>
            <a href="/dashboard?filter=deleted" class="sidebar-link" style="color:var(--danger);"><i class="fas fa-trash-alt"></i> Smazaní (Záloha)</a>
        </div>
        <div style="padding:20px;"><div style="font-size:11px;color:var(--text-muted);text-align:center;margin-bottom:15px;border-top:1px solid #334155;padding-top:15px;"><i class="fas fa-clock"></i> Poslední update:<br><b>{{ deploy_time }}</b></div><a href="/logout" class="btn btn-danger" style="width:100%;text-align:center;"><i class="fas fa-sign-out-alt"></i> Odhlásit</a></div>
    </div>
    <div class="dashboard-content">
        {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}
        {% block content %}{% endblock %}
    </div>
</div>
"""

HTML_HOME = """
<div style="text-align:center;padding:60px 20px;max-width:800px;margin:0 auto;">
    <h1 style="color:var(--blue-main);font-size:2.5em;text-transform:uppercase;letter-spacing:2px;text-shadow:0 0 15px rgba(56,189,248,0.4);">OFICIÁLNÍ STRÁNKA PROJEKTU OIS IDPK</h1>
    <div style="font-size:1.1em;color:var(--text-main);line-height:1.6;margin-bottom:40px;background:rgba(30,41,59,0.5);padding:25px;border-radius:10px;border-left:4px solid var(--blue-main);text-align:left;">
        <p style="margin-top:0;">Projekt OIS IDPK je fanouškovský software inspirovaný skutečnými vnitřními informačními panely, které se používají v autobusech Plzeňského kraje. Cílem projektu je co nejvěrněji napodobit jejich vzhled i způsob fungování.</p>
        <p>Software simuluje zobrazování zastávek, průběh celé linky i další informace, které běžně vidí cestující během jízdy. Díky tomu si můžeš jednoduše vyzkoušet, jak se panel chová při jízdě po trase, jak se postupně mění zastávky nebo jak vypadají informace o aktuální části linky.</p>
        <p style="margin-bottom:0;">Celý projekt vznikl z nadšení pro dopravu, technologie a informační systémy ve veřejné dopravě. Projekt není oficiálním produktem ani službou dopravců nebo organizací veřejné dopravy a nijak s nimi nespolupracuje. Jedná se čistě o fanouškovský projekt vytvořený pro zábavu, experimentování a zájem o dopravní technologie.</p>
    </div>
    <a href="/download" class="btn" style="font-size:18px;padding:15px 40px;border-radius:30px;box-shadow:0 5px 15px rgba(56,189,248,0.4);"><i class="fas fa-download"></i> Získat Software</a>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:60px 0;">
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;background:var(--bg-panel);padding:40px;border-radius:15px;border:1px solid #334155;">
        <img src="{{ logo_velke }}" alt="Logo" style="max-width:250px;height:auto;filter:drop-shadow(0px 10px 15px rgba(0,0,0,0.5));margin-bottom:10px;">
        <div style="text-align:center;max-width:600px;">
            <h3 style="color:var(--warning);margin-top:0;font-size:1.6em;text-shadow:0 0 5px rgba(245,158,11,0.5);">Poháněno systémem DataCoreBot</h3>
            <p style="color:var(--text-muted);font-size:1em;line-height:1.6;margin:0 0 15px 0;">Celá infrastruktura, od databází po ověřování uživatelů, je bezpečně řízena a chráněna unikátním systémem DataCoreBot. Zajišťuje bleskovou synchronizaci dat, striktní Hardware ID (HWID) ochranu a nepřetržitý chod palubních počítačů.</p>
            <div style="display:inline-block;background:rgba(0,0,0,0.3);padding:10px 20px;border-radius:8px;border:1px solid var(--blue-main);">
                <p style="color:var(--text-main);font-weight:bold;margin:0;font-size:1em;letter-spacing:1px;"><i class="fas fa-code" style="color:var(--blue-main);"></i> Vytvořeno vývojářem <span style="color:var(--blue-main);">marekk_czz</span></p>
            </div>
        </div>
    </div>
</div>
"""

HTML_CLAIM = """
<div style="max-width:500px;margin:50px auto;background:var(--bg-panel);padding:40px;border-radius:10px;border-top:4px solid var(--blue-main);box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    <h2 style="color:var(--blue-main);text-align:center;margin-top:0;"><i class="fas fa-gift"></i> Vyzvednutí VIP Role</h2>
    <p style="color:var(--text-muted);font-size:14px;text-align:center;margin-bottom:30px;">Zadejte jméno, pod kterým jste před malou chvílí poslali příspěvek na Buy Me a Coffee, a Váš Discord Nick. Náš systém Vám obratem automaticky přidělí roli!</p>
    <form method="POST">
        <label style="color:var(--text-muted);font-size:12px;font-weight:bold;">JMÉNO ZADANÉ NA BUY ME A COFFEE</label>
        <input type="text" name="bmac_name" placeholder="Např. Jan Novák" required style="margin-bottom:20px;">
        <label style="color:var(--text-muted);font-size:12px;font-weight:bold;display:block;">VÁŠ DISCORD NICK</label>
        <input type="text" name="discord_nick" placeholder="Např. marekk_czz" required>
        <button type="submit" class="btn" style="width:100%;margin-top:20px;font-size:16px;padding:15px;"><i class="fab fa-discord"></i> Propojit a získat roli</button>
    </form>
</div>
"""

HTML_STATS = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;"><h2 style="margin:0;color:var(--text-main);"><i class="fas fa-chart-line" style="color:var(--blue-main);"></i> Statistiky Webu</h2><div style="color:var(--text-muted);font-size:13px;background:rgba(0,0,0,0.3);padding:8px 12px;border-radius:6px;border:1px solid #334155;font-weight:bold;"><i class="fas fa-sync-alt" style="color:var(--blue-main);"></i> Auto aktualizace</div></div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-bottom:20px;">
    <div style="background:var(--bg-panel);padding:20px;border-radius:10px;border-top:4px solid var(--blue-main);text-align:center;"><h3 style="color:var(--text-muted);font-size:14px;margin-top:0;text-transform:uppercase;">Unikátní zobrazení (Celkem)</h3><div style="font-size:40px;font-weight:900;color:var(--text-main);">{{ total_visits }}</div></div>
    <div style="background:var(--bg-panel);padding:20px;border-radius:10px;border-top:4px solid var(--success);text-align:center;"><h3 style="color:var(--text-muted);font-size:14px;margin-top:0;text-transform:uppercase;">Zobrazení za 7 dní</h3><div style="font-size:40px;font-weight:900;color:var(--success);">{{ last_7_days }}</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div style="background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;"><i class="fas fa-calendar-week"></i> Návštěvnost za 7 dní</h3><div style="position:relative;height:250px;width:100%;"><canvas id="chart7d"></canvas></div></div>
    <div style="background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;"><i class="fas fa-clock"></i> Dnešní aktivita</h3><div style="position:relative;height:250px;width:100%;"><canvas id="chart24h"></canvas></div></div>
</div>
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;margin-bottom:20px;">
    <h3 style="color:var(--warning);margin-top:0;"><i class="fas fa-globe"></i> Návštěvnost podle států (Souhrn)</h3>
    <div style="display:flex;gap:15px;flex-wrap:wrap;">{% for cc, data in country_totals.items() %}<div style="background:rgba(0,0,0,0.3);border:1px solid #334155;padding:10px 20px;border-radius:8px;display:flex;align-items:center;gap:10px;"><img src="{{ data.flag }}" style="border-radius:3px;box-shadow:0 0 5px rgba(0,0,0,0.5);"><span style="color:var(--text-main);font-weight:bold;">{{ data.name }}</span><span style="background:var(--blue-main);color:#000;padding:2px 8px;border-radius:12px;font-weight:900;font-size:12px;">{{ data.count }}</span></div>{% else %}<div style="color:var(--text-muted);">Zatím žádná data k zobrazení.</div>{% endfor %}</div>
</div>
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;"><i class="fas fa-map-marker-alt"></i> Detailní přehled regionů</h3><table style="width:100%;"><tr><th>Stát / Region</th><th>Počet zobrazení</th></tr>{% for c_name, data in region_totals.items() %}<tr><td style="font-weight:bold;color:var(--text-main);display:flex;align-items:center;gap:10px;">{% if data.flag %}<img src="{{ data.flag }}" style="border-radius:3px;box-shadow:0 0 5px rgba(0,0,0,0.5);">{% endif %} {{ c_name }}</td><td style="color:var(--blue-main);font-weight:bold;font-size:16px;">{{ data.count }}</td></tr>{% else %}<tr><td colspan="2" style="text-align:center;color:var(--text-muted);">Zatím žádná data.</td></tr>{% endfor %}</table></div>
<script>
    new Chart(document.getElementById('chart7d').getContext('2d'), { type:'line', data:{ labels:{{ labels_7d|safe }}, datasets:[{ label:'Návštěv', data:{{ data_7d|safe }}, borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.2)', borderWidth:3, tension:0.3, fill:true }] }, options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true, ticks:{color:'#94a3b8', stepSize:1}, grid:{color:'#334155'}}, x:{ticks:{color:'#94a3b8'}, grid:{display:false}} } } });
    new Chart(document.getElementById('chart24h').getContext('2d'), { type:'bar', data:{ labels:{{ labels_24h|safe }}, datasets:[{ label:'Dnešní', data:{{ data_24h|safe }}, backgroundColor:'#38bdf8', borderRadius:4 }] }, options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{ y:{beginAtZero:true, ticks:{color:'#94a3b8', stepSize:1}, grid:{color:'#334155'}}, x:{ticks:{color:'#94a3b8'}, grid:{display:false}} } } });
</script>
"""

HTML_TEAM = """
<h2 style="color:var(--blue-main);border-bottom:2px solid #334155;padding-bottom:10px;text-align:center;">Náš Tým</h2>
<div style="display:flex;justify-content:center;flex-wrap:wrap;gap:20px;">
    {% for member in team %}
    <div style="background:var(--bg-panel);border-radius:10px;padding:20px;text-align:center;border-top:4px solid var(--blue-main);width:300px;transition:transform 0.5s ease, box-shadow 0.5s ease;" onmouseover="this.style.transform='translateY(-8px)';this.style.boxShadow='0 12px 30px rgba(56,189,248,0.4)';" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none';">
        <img src="{{ member.get('image_url', '') }}" style="width:100px;height:100px;border-radius:50%;object-fit:cover;margin-bottom:15px;border:3px solid #334155;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <h3 style="font-size:20px;font-weight:bold;margin:0 0 5px 0;">{{ member.get('name', '') }}</h3>
        <div style="color:var(--blue-main);font-size:14px;margin-bottom:15px;">@{{ member.get('discord_nick', '') }}</div>
        <p style="color:var(--text-muted);font-size:14px;line-height:1.5;margin-bottom:15px;">{{ member.get('description', '') }}</p>
        <div>
            {% set roles_input = member.get('role_name', '').split(',') if member.get('role_name') else [] %}
            {% for r in roles_input %}
                {% set parts = r.split('|') %}{% set r_name = parts[0].strip() %}{% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                <span class="role-tag" style="background-color:{{ r_color }}33;color:{{ r_color }};border:1px solid {{ r_color }};">{{ r_name }}</span>
            {% endfor %}
        </div>
    </div>
    {% else %}<p style="color:var(--text-muted);text-align:center;width:100%;">Zatím nebyli přidáni žádní členové týmu.</p>{% endfor %}
</div>
"""

HTML_DOWNLOADS_MAIN = """
<div style="text-align:center;padding:60px 20px;max-width:700px;margin:50px auto;background:var(--bg-panel);border-radius:15px;box-shadow:0 15px 30px rgba(0,0,0,0.5);border-top:5px solid #5865F2;">
    <h2 style="color:var(--text-main);font-size:2.2em;margin-top:0;"><i class="fas fa-shield-alt" style="color:var(--blue-main);"></i> Oficiální distribuce softwaru</h2>
    <p style="color:var(--text-muted);font-size:1.1em;line-height:1.6;margin-bottom:20px;">Z důvodu ochrany projektu jsme se rozhodli přesunout jeho distribuci na náš Discord server. Díky tomu máme kontrolu a můžeme zabránit zneužití.</p>
    <div style="background:rgba(88,101,242,0.1);border:1px solid #5865F2;padding:30px 20px;border-radius:10px;margin:30px 20px;">
        <p style="color:var(--text-main);font-weight:bold;font-size:1.2em;margin-top:0;">Jak získat software:</p>
        <p style="color:var(--text-muted);font-size:14px;margin-bottom:30px;">Připojte se na Discord a přejděte do kanálu <b>💾・download</b>, kde stačí postupovat podle pokynů. 🚀</p>
        <a href="https://discord.gg/vmTagbC9mF" target="_blank" style="display:inline-block;transition:transform 0.3s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'"><i class="fab fa-discord" style="font-size:120px;color:#5865F2;filter:drop-shadow(0px 10px 15px rgba(88,101,242,0.4));"></i></a>
    </div>
</div>
"""

HTML_LOGIN = """
<div style="max-width:400px;margin:50px auto;background:var(--bg-panel);padding:30px;border-radius:10px;box-shadow:0 10px 25px rgba(0,0,0,0.5);border-top:4px solid var(--blue-main);">
    <h2 style="text-align:center;color:var(--blue-main);margin-top:0;"><i class="fas fa-lock"></i> Dashboard 2FA</h2>
    <div style="background:rgba(239,68,68,0.1);border-left:4px solid var(--danger);padding:12px;margin-bottom:20px;border-radius:0 5px 5px 0;">
        <p style="color:var(--danger);margin:0;font-size:13px;font-weight:800;"><i class="fas fa-shield-alt"></i> Zabezpečená zóna</p>
        <p style="color:var(--text-muted);margin:5px 0 0 0;font-size:12px;line-height:1.4;">Tato databáze je přísně vyhrazena <b>pouze pro administrátory</b> projektu.</p>
    </div>
    <form method="POST" action="/login_request">
        <label style="font-weight:bold;font-size:12px;color:var(--text-muted);">VAŠE DISCORD ID</label>
        <input type="text" name="discord_id" placeholder="Např. 123456789012345678" required>
        <button type="submit" class="btn" style="width:100%;margin-top:10px;"><i class="fab fa-discord"></i> Odeslat žádost</button>
    </form>
</div>
"""

HTML_WAIT_AUTH = """
<div style="max-width:500px;margin:50px auto;background:var(--bg-panel);padding:40px;border-radius:10px;text-align:center;border-top:4px solid var(--warning);">
    <h2 style="color:var(--warning);margin-top:0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2>
    <p style="color:var(--text-main);font-size:16px;">Byla Vám odeslána zpráva na Discord.</p>
</div>
<script>setInterval(()=>{fetch('/api/check_auth/{{ discord_id }}').then(r=>r.json()).then(data=>{if(data.status==='approved'){window.location.href='/dashboard/login_finalize?discord_id={{ discord_id }}';}else if(data.status==='rejected'){window.location.href='/dashboard';}});},2000);</script>
"""

HTML_APP_SETTINGS = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;"><h2 style="margin:0;color:var(--text-main);">Nastavení Aplikace</h2></div>
<div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="flex:1;min-width:300px;background:var(--bg-panel);padding:20px;border-radius:10px;border-top:4px solid {{ 'var(--success)' if soft_enabled else 'var(--danger)' }};text-align:center;">
        <h3 style="margin-top:0;color:var(--text-main);"><i class="fas fa-desktop"></i> Status Softwaru (Kill-Switch)</h3>
        <div style="font-size:50px;margin:15px 0;color:{{ 'var(--success)' if soft_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if soft_enabled else 'fa-ban' }}"></i></div>
        <form action="/dashboard/toggle_software" method="POST"><input type="hidden" name="new_status" value="{{ 'False' if soft_enabled else 'True' }}"><button type="submit" class="btn {{ 'btn-danger' if soft_enabled else 'btn-success' }}" style="width:100%;"><i class="fas fa-power-off"></i> PŘEPNOUT</button></form>
    </div>
    <div style="flex:1;min-width:300px;background:var(--bg-panel);padding:20px;border-radius:10px;border-top:4px solid {{ 'var(--success)' if dl_enabled else 'var(--danger)' }};text-align:center;">
        <h3 style="margin-top:0;color:var(--text-main);"><i class="fas fa-cloud-download-alt"></i> Status Stahování</h3>
        <div style="font-size:50px;margin:15px 0;color:{{ 'var(--success)' if dl_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if dl_enabled else 'fa-ban' }}"></i></div>
        <form action="/dashboard/toggle_downloads" method="POST"><input type="hidden" name="new_status" value="{{ 'False' if dl_enabled else 'True' }}"><input type="hidden" name="return_to" value="app_settings"><button type="submit" class="btn {{ 'btn-danger' if dl_enabled else 'btn-success' }}" style="width:100%;"><i class="fas fa-power-off"></i> PŘEPNOUT</button></form>
    </div>
</div>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;"><h2 style="margin:0;color:var(--text-main);">Správa Stahování</h2></div>
<div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="flex:1;min-width:300px;background:var(--bg-panel);padding:20px;border-radius:10px;">
        <h3 style="color:var(--blue-main);margin-top:0;">➕ Přidat Verzi</h3>
        <form action="/dashboard/add_version" method="POST"><input type="text" name="version_name" placeholder="Název zobrazený v menu" required><input type="url" name="file_url" placeholder="Odkaz" required><select name="target_role" required><option value="User">User</option><option value="BT">BT</option><option value="DEV_SA">DEV / SA</option></select><button type="submit" class="btn" style="width:100%;">Přidat verzi</button></form>
    </div>
</div>
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;margin-top:20px;">
    <h3 style="color:var(--blue-main);margin-top:0;">📦 Dostupné soubory</h3>
    <table style="width:100%;"><tr><th>Název</th><th>Role</th><th>Odkaz</th><th>Akce</th></tr>{% for v in versions %}<tr><td>{{ v.get('version_name', '') }}</td><td>{{ v.get('target_role', '') }}</td><td><a href="{{ v.get('file_url', '') }}" style="color:var(--blue-main);">Link</a></td><td><form action="/dashboard/delete_version" method="POST"><input type="hidden" name="version_id" value="{{ v.get('id', '') }}"><button type="submit" class="btn btn-danger">Smazat</button></form></td></tr>{% endfor %}</table>
</div>
"""

HTML_PENDING_ROLES = """
<div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="flex:1;background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;">➕ Roli</h3><form action="/dashboard/add_pending_role" method="POST"><input type="text" name="discord_identifier" placeholder="Discord Nick" required><div class="checkbox-group"><label><input type="checkbox" name="roles" value="SA"> SA</label><label><input type="checkbox" name="roles" value="DEV"> DEV</label><label><input type="checkbox" name="roles" value="BT"> BT</label><label><input type="checkbox" name="roles" value="User"> User</label></div><button type="submit" class="btn" style="width:100%;">Vytvořit</button></form></div>
    <div style="flex:2;background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;">⏳ Čekající rezervace</h3><table><tr><th>Discord</th><th>Role</th><th>Akce</th></tr>{% for p in pending %}<tr><td>{{ p.get('discord_identifier', '') }}</td><td>{{ p.get('roles', '') }}</td><td><form action="/dashboard/delete_pending_role" method="POST"><input type="hidden" name="pending_id" value="{{ p.get('id', '') }}"><button type="submit" class="btn btn-danger">X</button></form></td></tr>{% endfor %}</table></div>
</div>
"""

HTML_TEAM_ADD = """
<div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="flex:1;background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;">➕ Přidat člena</h3><form action="/dashboard/add_team" method="POST"><input type="text" name="name" placeholder="Jméno" required><input type="text" name="discord_nick" placeholder="Nick" required><input type="url" name="image_url" placeholder="URL" required><textarea name="description" required></textarea><button type="submit" class="btn" style="width:100%;">Přidat</button></form></div>
    <div style="flex:2;background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;">👥 Tým</h3><table><tr><th>Jméno</th><th>Nick</th><th>Akce</th></tr>{% for member in team %}<tr><td>{{ member.get('name', '') }}</td><td>{{ member.get('discord_nick', '') }}</td><td><form action="/dashboard/delete_team" method="POST"><input type="hidden" name="discord_nick" value="{{ member.get('discord_nick', '') }}"><button type="submit" class="btn btn-danger">X</button></form></td></tr>{% endfor %}</table></div>
</div>
"""

HTML_IDS = """
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;"><h3 style="color:var(--blue-main);margin-top:0;">Správa ID</h3><table><tr><th>App ID</th><th>Nick</th><th>Discord ID</th><th>Status</th><th>Změnit</th></tr>{% for user in users %}<tr><td>#{{ user.get('app_id', '') }}</td><td>{{ user.get('nick', '') }}</td><td>{{ user.get('discord_id', '') }}</td><td>{% if user.get('is_deleted') %}<span style="color:var(--danger)">Smazán</span>{% else %}<span style="color:var(--success)">Aktivní</span>{% endif %}</td><td><form action="/dashboard/change_id" method="POST" style="display:flex;gap:5px;"><input type="hidden" name="discord_id" value="{{ user.get('discord_id', '') }}"><input type="number" name="new_app_id" required style="width:80px;"><button type="submit" class="btn">Změnit</button></form></td></tr>{% endfor %}</table></div>
"""

HTML_SUPPORTERS = """
<style>
.glowing-btn-blue{background:var(--blue-main);color:#000;padding:15px 40px;font-size:20px;font-weight:900;border-radius:50px;text-decoration:none;display:inline-block;margin-top:20px;box-shadow:0 0 20px rgba(56,189,248,0.6);transition:0.3s;text-transform:uppercase}
.glowing-btn-blue:hover{box-shadow:0 0 40px rgba(56,189,248,1);transform:scale(1.05);color:#000}
.supporter-wrapper{width:100%;max-width:500px;min-height:230px;display:flex;flex-direction:column;justify-content:space-between;align-items:center;text-align:center;box-sizing:border-box}
.tier-1{background:rgba(15,23,42,0.8);padding:20px;border-radius:10px;box-shadow:0 0 10px rgba(56,189,248,0.2);border:1px solid rgba(56,189,248,0.3);border-left:5px solid #38bdf8;transition:transform 0.5s ease}
.tier-1:hover{transform:scale(1.05);box-shadow:0 10px 25px rgba(56,189,248,0.4)}
.tier-1 .name-title{color:#e0f2fe;text-shadow:0 0 10px rgba(56,189,248,0.5);font-size:20px;margin:0 0 10px 0}
.tier-1 .title-badge{font-size:10px;color:#38bdf8;text-transform:uppercase;font-weight:bold;margin-bottom:10px}
.tier-1 .amt-badge{display:inline-block;margin-bottom:25px;background:rgba(56,189,248,0.1);color:var(--blue-main);padding:5px 15px;border-radius:20px;font-weight:bold;font-size:14px;border:1px solid rgba(56,189,248,0.3)}
@keyframes pulseMedium{from{box-shadow:0 0 10px rgba(245,158,11,0.3)}to{box-shadow:0 0 20px rgba(245,158,11,0.6)}}
.tier-2{background:rgba(30,41,59,0.9);padding:25px;border-radius:12px;border:1px solid rgba(245,158,11,0.6);border-left:6px solid #f59e0b;animation:pulseMedium 2s infinite alternate;transition:transform 0.5s ease}
.tier-2:hover{transform:scale(1.05)!important;animation:none;box-shadow:0 10px 35px rgba(245,158,11,0.8)}
.tier-2 .name-title{color:#fcd34d;font-size:26px;margin:0 0 10px 0;text-shadow:0 0 10px rgba(245,158,11,0.5)}
.tier-2 .title-badge{font-size:12px;color:#f59e0b;text-transform:uppercase;font-weight:bold;margin-bottom:10px}
.tier-2 .amt-badge{display:inline-block;margin-bottom:25px;background:rgba(245,158,11,0.1);color:var(--warning);padding:5px 15px;border-radius:20px;font-weight:bold;font-size:16px;border:1px solid rgba(245,158,11,0.5)}
@keyframes epicWebGlow{from{box-shadow:0 0 20px rgba(239,68,68,0.4)}to{box-shadow:0 0 50px rgba(239,68,68,0.9),inset 0 0 30px rgba(239,68,68,0.3)}}
.tier-3{background:linear-gradient(135deg,#2a0a18,#450a0a);padding:30px;border-radius:15px;border:2px solid #ef4444;animation:epicWebGlow 1.5s infinite alternate;transition:transform 0.5s ease}
.tier-3:hover{transform:scale(1.08)!important;animation:none;box-shadow:0 15px 60px rgba(239,68,68,1)}
.tier-3 .name-title{color:#fca5a5;font-size:32px!important;margin:0 0 15px 0;text-shadow:0 0 20px #ef4444,0 0 40px #ef4444;text-transform:uppercase;font-weight:900}
.tier-3 .title-badge{font-size:14px;color:#ef4444;text-transform:uppercase;font-weight:900;margin-bottom:10px;text-shadow:0 0 10px #ef4444}
.tier-3 .amt-badge{display:inline-block;margin-bottom:25px;background:#ef4444!important;color:#fff!important;border:2px solid #fca5a5!important;padding:8px 20px;border-radius:25px;font-weight:bold;font-size:20px!important;box-shadow:0 0 20px #ef4444}
</style>
<div style="max-width:800px;margin:0 auto;padding:20px;">
    <div style="text-align:center;margin-bottom:40px;"><h1 style="color:var(--blue-main);font-size:36px;">Děkuji všem za podporu!</h1><a href="https://www.buymeacoffee.com/marekk_czz" target="_blank" class="glowing-btn-blue"><i class="fas fa-heart"></i> Podpořit Projekt</a></div>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:40px 0;">
    <div style="display:flex;flex-direction:column;gap:40px;align-items:center;">
        {% for s in supporters %}
        <div class="tier-{{ s.get('tier', 1) }} supporter-wrapper">
            <div style="width:100%;">
                {% if s.get('tier') == 3 %}<div class="title-badge">MEGA PODPOROVATEL</div>{% elif s.get('tier') == 2 %}<div class="title-badge">VELKÝ PODPOROVATEL</div>{% else %}<div class="title-badge">PODPOROVATEL</div>{% endif %}
                <h3 class="name-title">{{ s.get('name', 'Neznámý dárce') }}</h3><div class="amt-badge">{{ s.get('amount', '') }}</div>
            </div>
            <div style="width:100%;margin-top:auto;">
                {% if s.get('message') %}<p style="color:var(--text-main);font-size:16px;font-style:italic;background:rgba(0,0,0,0.3);padding:15px;border-radius:8px;">"{{ s.get('message') }}"</p>{% endif %}
                <div style="font-size:11px;color:#64748b;">{{ s.get('created_at', '') }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
"""

HTML_SUPPORTERS_MGMT = """
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;border-top:4px solid var(--warning);margin-bottom:20px;">
    <h3 style="color:var(--warning);margin-top:0;"><i class="fas fa-exclamation-triangle"></i> Ke schválení (Manuální)</h3>
    <table style="width:100%;"><tr><th>Jméno</th><th>Discord Nick</th><th>Akce</th></tr>{% for p in pending_claims %}<tr><td>{{ p.get('name', '') }}</td><td>{{ p.get('discord_nick', '') }}</td><td><form action="/dashboard/approve_claim" method="POST" style="display:inline;"><input type="hidden" name="claim_id" value="{{ p.get('id', '') }}"><input type="hidden" name="discord_nick" value="{{ p.get('discord_nick', '') }}"><input type="hidden" name="amount" value="{{ p.get('amount', '0') }}"><button class="btn btn-success">Schválit</button></form><form action="/dashboard/reject_claim" method="POST" style="display:inline;"><input type="hidden" name="claim_id" value="{{ p.get('id', '') }}"><button class="btn btn-danger">Zamítnout</button></form></td></tr>{% endfor %}</table>
</div>
<div style="display:flex;gap:20px;flex-wrap:wrap;">
    <div style="flex:1;min-width:300px;background:var(--bg-panel);padding:20px;border-radius:10px;">
        <h3 style="color:var(--blue-main);margin-top:0;">➕ Ruční přidání</h3>
        <form action="/dashboard/add_supporter" method="POST"><input type="text" name="name" placeholder="Jméno" required><input type="text" name="amount" placeholder="Částka" required><textarea name="message" placeholder="Zpráva"></textarea><button type="submit" class="btn" style="width:100%;">Přidat</button></form>
    </div>
    <div style="flex:2;min-width:300px;background:var(--bg-panel);padding:20px;border-radius:10px;">
        <h3 style="color:var(--blue-main);margin-top:0;">☕ Historie</h3>
        <table style="width:100%;"><tr><th>Jméno</th><th>Částka</th><th>Datum</th><th>Akce</th></tr>{% for s in supporters %}<tr><td>{{ s.get('name', '') }}</td><td style="color:var(--success);">{{ s.get('amount', '') }}</td><td>{{ s.get('created_at', '') }}</td><td><form action="/dashboard/delete_supporter" method="POST"><input type="hidden" name="supporter_id" value="{{ s.get('id', '') }}"><button class="btn btn-danger">X</button></form></td></tr>{% endfor %}</table>
    </div>
</div>
"""

HTML_DASHBOARD_MAIN = """
<div style="background:var(--bg-panel);padding:20px;border-radius:10px;overflow-x:auto;">
    <table id="usersTable">
        <tr><th>App ID</th><th>Nick</th><th>Stav</th><th>Role</th><th>Aktivita</th><th>Akce</th></tr>
        {% for user in users %}
        <tr>
            <td style="color:var(--blue-main);font-weight:bold;">#{{ user.get('app_id', '') }}</td>
            <td><strong>{{ user.get('nick', '') }}</strong></td>
            <td>{% if user.get('is_banned') %}<span style="color:var(--danger);">BAN</span>{% elif user.get('is_deleted') %}<span style="color:var(--text-muted);">DEL</span>{% else %}<span style="color:var(--success);">OK</span>{% endif %}</td>
            <td>{{ user.get('role', '') }}</td>
            <td>{% if user.get('is_online') %}<span style="color:var(--success);">ONLINE</span>{% else %}{{ user.get('last_active', 'Nikdy') }}{% endif %}</td>
            <td><button class="btn btn-dark" style="padding:5px;" onclick="alert('Pro úpravu vytvořte modální okno nebo použijte plnou verzi.')">Edit</button></td>
        </tr>
        {% endfor %}
    </table>
</div>
"""

# HTML Šablony - Modal Okno Editace (Sjednoceno pro úsporu místa)
MODAL_HTML = """<script>function openModal(a,d,n,r,h,b,dl,da,reg){ alert("Zde by se otevřel profil " + n); }</script>"""
HTML_DASHBOARD_MAIN += MODAL_HTML

# ==========================================
# GLOBÁLNÍ FUNKCE 
# ==========================================

def get_db():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key: return create_client(url, key)
    except: pass
    return None

def process_supporters(data_list):
    for s in data_list:
        amt_str = str(s.get('amount', '0'))
        match = re.search(r'([\d\.,]+)', amt_str)
        val = 0.0
        if match:
            try: val = float(match.group(1).replace(',', '.'))
            except: pass
        if 'usd' in amt_str.lower() or '$' in amt_str.lower(): val *= 23
        elif 'eur' in amt_str.lower() or '€' in amt_str.lower(): val *= 25
        s['norm_val'] = val
        if val >= 325: s['tier'] = 3
        elif val >= 195: s['tier'] = 2
        else: s['tier'] = 1
    data_list.sort(key=lambda x: (x.get('norm_val', 0), x.get('id', 0)), reverse=True)
    return data_list

def calculate_role_from_amount(amount_str):
    match = re.search(r'([\d\.,]+)', str(amount_str))
    val = 0.0
    if match:
        try: val = float(match.group(1).replace(',', '.'))
        except: pass
    if 'usd' in str(amount_str).lower() or '$' in str(amount_str).lower(): val *= 23
    elif 'eur' in str(amount_str).lower() or '€' in str(amount_str).lower(): val *= 25
    if val >= 325: return "⭐| MEGA PODPOROVATEL"
    elif val >= 195: return "⭐| VELKÝ PODPOROVATEL"
    else: return "⭐| PODPOROVATEL"

def user_exists_sync(identifier):
    try:
        for guild in bot.guilds:
            if identifier.isdigit() and guild.get_member(int(identifier)): return True
            if discord.utils.find(lambda m: m.name.lower() == identifier.lower() or (m.global_name and m.global_name.lower() == identifier.lower()), guild.members): return True
    except: pass
    return False

async def assign_supporter_role(identifier, role_name):
    try:
        for guild in bot.guilds:
            member = guild.get_member(int(identifier)) if identifier.isdigit() else discord.utils.find(lambda m: m.name.lower() == identifier.lower() or (m.global_name and m.global_name.lower() == identifier.lower()), guild.members)
            if member:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.add_roles(role)
                    try: await member.send(embed=discord.Embed(title="🎉 Děkujeme!", description=f"Role udělena:\n**{role_name}**", color=0x38bdf8))
                    except: pass
                break
    except: pass

def send_log(title, description, color=0x38bdf8):
    async def async_log():
        for guild in bot.guilds:
            channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
            if channel:
                try: await channel.send(embed=discord.Embed(title=title, description=description, color=color, timestamp=get_prague_time()))
                except: pass
                break
    if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(async_log(), bot.loop)

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
                    u = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                    if u and (not u[0].get("dashboard_access") or u[0].get("is_banned") or u[0].get("is_deleted")):
                        session.clear(); flash('Přístup zablokován.', 'error'); return redirect(url_for('dashboard_main'))
            except: pass

async def update_member_roles(member, role_string):
    if not member or not member.guild: return
    u_roles = [r.strip() for r in role_string.split(',')]
    try:
        for r_code, db_role in [("SA", "web-sa"), ("DEV", "web-dev"), ("BT", "web-bt")]:
            role_obj = discord.utils.get(member.guild.roles, name=db_role)
            if role_obj:
                if r_code in u_roles and role_obj not in member.roles: await member.add_roles(role_obj)
                elif r_code not in u_roles and role_obj in member.roles: await member.remove_roles(role_obj)
    except: pass

# ==========================================
# PUBLIC FLASK STRÁNKY 
# ==========================================

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
            
            country_name = cf_country
            region = ""
            country_code = ""
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
            
            if not country_code or country_code.lower() == 'us' or country_name.lower() in ["neznámá", "unknown", "none"]: return 
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
    try: 
        db = get_db()
        data = db.table("supporters").select("*").eq("status", "completed").execute().data or [] if db else []
        support_data = process_supporters(data)
    except: support_data = []
    return render_public(HTML_SUPPORTERS, supporters=support_data)

@app.route('/claim', methods=['GET', 'POST'])
def claim_role():
    if request.method == 'POST':
        bmac_name = request.form.get('bmac_name', '').strip()
        discord_nick = request.form.get('discord_nick', '').strip()
        db = get_db()
        if not db: return redirect(url_for('claim_role'))

        records = db.table("supporters").select("*").eq("name", bmac_name).in_("status", ["pending", "manual_review"]).execute().data
        if records:
            record = records[0] 
            assigned_role = calculate_role_from_amount(record.get('amount', '0'))
            if user_exists_sync(discord_nick):
                if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, assigned_role), bot.loop)
                db.table("supporters").update({"status": "completed", "discord_nick": discord_nick}).eq("id", record['id']).execute()
                
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_nick},nick.ilike.{discord_nick}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    if assigned_role not in current_roles:
                        new_roles = f"{current_roles},{assigned_role}" if current_roles else assigned_role
                        db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
                else: db.table("pending_roles").insert({"discord_identifier": discord_nick, "roles": assigned_role}).execute()
                flash('Úspěch! Role ti byla právě přidělena.', 'success')
            else:
                db.table("supporters").update({"status": "manual_review", "discord_nick": discord_nick}).eq("id", record['id']).execute()
                flash('Discord účet nebyl nalezen! Odesláno ke schválení.', 'warning')
        else:
            db.table("supporters").insert({"name": bmac_name, "discord_nick": discord_nick, "amount": "?", "message": "Špatné jméno BMAC", "status": "manual_review", "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            flash('Odesláno administrátorovi k ruční kontrole.', 'warning')
        return redirect(url_for('claim_role'))
    return render_public(HTML_CLAIM)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        data = db.table("supporters").select("name, amount, message, created_at").eq("status", "completed").execute().data or []
        return _cors_jsonify({"supporters": process_supporters(data)})
    except Exception as e: return _cors_jsonify({"error": str(e)}), 500

@app.route('/webhook/bmac', methods=['GET', 'POST'])
def bmac_webhook():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}; data = payload.get('data', payload) if isinstance(payload, dict) else {}
        else: data = request.args
        name = data.get('supporter_name', 'Anonym'); message = data.get('support_note', ''); amount_val = data.get('amount', 1); currency = data.get('currency', 'CZK')
        amount_str = f"{amount_val} {currency}"
        assigned_role = calculate_role_from_amount(amount_str)
        discord_identifier = None
        id_match = re.search(r'\b\d{17,19}\b', message)
        if id_match: discord_identifier = id_match.group(0)
        else:
            nick_match = re.search(r'(?i)(?:discord|dc|nick)[\s:]+([a-zA-Z0-9_.-]+)', message)
            if nick_match: discord_identifier = nick_match.group(1).strip()

        db = get_db()
        if db:
            status = 'pending'
            if discord_identifier and user_exists_sync(discord_identifier): status = 'completed'
            db.table("supporters").insert({"name": str(name), "message": str(message), "amount": str(amount_str), "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "status": status, "discord_nick": discord_identifier or ""}).execute()
            send_log("🍕 Nový dárce!", f"Uživatel **{name}** poslal **{amount_str}**.\n\n*Vzkaz: {message}*", 0xF4CC17)

            if status == 'completed':
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_identifier},nick.ilike.{discord_identifier}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    if assigned_role not in current_roles: db.table("users").update({"role": f"{current_roles},{assigned_role}" if current_roles else assigned_role}).eq("discord_id", db_user[0]['discord_id']).execute()
                else: db.table("pending_roles").insert({"discord_identifier": discord_identifier, "roles": assigned_role}).execute()
                if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_identifier, assigned_role), bot.loop)
        if request.method == 'GET': return f"<h1>ÚSPĚCH! 🎉</h1>"
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/get_file/<token>')
def api_get_file(token):
    db = get_db()
    try:
        user = db.table("users").select("*").eq("download_token", token).execute().data[0]
        if user.get("is_banned") or user.get("is_deleted"): return "Přístup zamítnut."
        v_data = db.table("software_versions").select("*").eq("id", request.args.get('v')).execute().data[0]
        file_url = v_data['file_url']
        try: db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": v_data['version_name'], "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
        except: pass
        if "pixeldrain.com/u/" in file_url: file_url = file_url.replace("/u/", "/api/file/")
        if "1drv.ms" in file_url: file_url = file_url.split("?")[0] + "?download=1"
        if "dropbox.com" in file_url: file_url = file_url.replace("dl=0", "dl=1")
        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
        remote_response = urllib.request.urlopen(req)
        def generate():
            while True:
                chunk = remote_response.read(8192)
                if not chunk: break
                yield chunk
        return Response(stream_with_context(generate()), headers={'Content-Disposition': f'attachment; filename="OIS_IDPK.zip"'})
    except: return "Chyba"

@app.route('/download/<token>')
def secure_download(token):
    return render_public(f"""<div style="text-align:center;padding:50px;"><h2>Ověřeno!</h2><a href="/api/get_file/{token}?v={request.args.get('v')}" class="btn btn-success">Stáhnout</a></div>""")

# ==========================================
# DASHBOARD A ADMIN ROUTES
# ==========================================

@app.route('/login_request', methods=['POST'])
def login_request():
    discord_id = request.form.get('discord_id'); db = get_db()
    if db and discord_id:
        try:
            user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
            if user and user[0].get("dashboard_access") == True and not user[0].get("is_banned"):
                token = str(uuid.uuid4())
                db.table("users").update({"login_token": token}).eq("discord_id", discord_id).execute()
                async def send():
                    u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                    if u: await u.send(embed=discord.Embed(title="🔐 2FA Ověření", description="Potvrďte přístup.", color=0x38bdf8), view=DashboardAuthView(token, discord_id))
                if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            flash('Odepřeno', 'error')
        except: pass
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): return render_public(HTML_WAIT_AUTH)

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    try:
        user = get_db().table("users").select("login_token").eq("discord_id", discord_id).execute().data
        if user and user[0].get("login_token") == "approved": return {"status": "approved"}
        elif user and user[0].get("login_token") == "rejected": return {"status": "rejected"}
    except: pass
    return {"status": "waiting"}

@app.route('/dashboard/login_finalize')
def login_finalize():
    discord_id = request.args.get('discord_id'); db = get_db()
    if db and discord_id:
        user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
        if user and user[0].get("login_token") == "approved":
            session.permanent = True; session['logged_in'] = True; session['discord_id'] = discord_id
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return redirect(url_for('dashboard_main'))
    return redirect(url_for('home'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard/stats')
def dashboard_stats():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    total_visits = 0; last_7_days = 0; country_totals = {}; region_totals = {}
    dates_7_days = [(get_prague_time().replace(tzinfo=None) - timedelta(days=i)).strftime("%d.%m.") for i in range(6, -1, -1)]
    chart_data_7d = {d: 0 for d in dates_7_days}; chart_data_24h = {f"{i:02d}:00": 0 for i in range(24)}
    try:
        db = get_db()
        if db:
            visits = db.table("page_visits").select("*").execute().data or []
            total_visits = len(visits); now = get_prague_time().replace(tzinfo=None)
            for v in visits:
                c_raw = v.get('country', '')
                if not c_raw or 'neznámá' in c_raw.lower() or 'us' in c_raw.lower(): continue
                parts = c_raw.split('|'); cc = parts[0] if len(parts)>0 else ""; c_name = parts[1] if len(parts)>1 else c_raw; reg = parts[2] if len(parts)>2 else ""
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
                    if v_time.strftime("%d.%m.") in chart_data_7d: chart_data_7d[v_time.strftime("%d.%m.")] += 1
                    if v_time.date() == now.date() and v_time.strftime("%H:00") in chart_data_24h: chart_data_24h[v_time.strftime("%H:00")] += 1
                except: pass
    except: pass
    return render_dashboard(HTML_STATS, total_visits=total_visits, last_7_days=last_7_days, country_totals=country_totals, region_totals=region_totals, labels_7d=json.dumps(list(chart_data_7d.keys())), data_7d=json.dumps(list(chart_data_7d.values())), labels_24h=json.dumps(list(chart_data_24h.keys())), data_24h=json.dumps(list(chart_data_24h.values())))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if not session.get('logged_in'): return render_public(HTML_LOGIN)
    users_data = []
    try:
        db = get_db()
        if db:
            query = db.table("users").select("*"); f = request.args.get('filter')
            if f == 'banned': query = query.eq("is_banned", True).eq("is_deleted", False)
            elif f == 'deleted': query = query.eq("is_deleted", True)
            elif f: query = query.ilike("role", f"%{f}%").eq("is_deleted", False)
            else: query = query.eq("is_deleted", False).order("app_id")
            users_data = query.execute().data or []
    except: pass
    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title="Přehled")

@app.route('/dashboard/supporters', methods=['GET'])
def dashboard_supporters():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    try: 
        db = get_db()
        pending_claims = db.table("supporters").select("*").eq("status", "manual_review").execute().data or []
        support_data = process_supporters(db.table("supporters").select("*").eq("status", "completed").execute().data or [])
    except: pending_claims = []; support_data = []
    return render_dashboard(HTML_SUPPORTERS_MGMT, pending_claims=pending_claims, supporters=support_data)

@app.route('/dashboard/approve_claim', methods=['POST'])
def approve_claim():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    claim_id = request.form.get("claim_id"); discord_nick = request.form.get("discord_nick"); db = get_db()
    if db and claim_id:
        assigned_role = calculate_role_from_amount(request.form.get("amount", "0"))
        if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, assigned_role), bot.loop)
        db.table("supporters").update({"status": "completed", "discord_nick": discord_nick}).eq("id", claim_id).execute()
        flash('Schváleno', 'success')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/reject_claim', methods=['POST'])
def reject_claim():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); claim_id = request.form.get("claim_id")
    if db and claim_id: db.table("supporters").delete().eq("id", claim_id).execute()
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/app_settings', methods=['GET'])
def dashboard_app_settings():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    return render_dashboard(HTML_APP_SETTINGS, soft_enabled=True, dl_enabled=True)

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = get_db().table("software_versions").select("*").order("id").execute().data or [] if get_db() else []
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=True)

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): 
    data = get_db().table("pending_roles").select("*").order("id").execute().data or [] if get_db() else []
    return render_dashboard(HTML_PENDING_ROLES, pending=data)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids(): 
    data = get_db().table("users").select("*").order("app_id").execute().data or [] if get_db() else []
    return render_dashboard(HTML_IDS, users=data)

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page(): 
    data = get_db().table("team").select("*").execute().data or [] if get_db() else []
    return render_dashboard(HTML_TEAM_ADD, team=data)

# API
@app.route('/api/status', methods=['GET'])
def api_status(): return _cors_jsonify({"status": "enabled"})
@app.route('/api/app_ping', methods=['POST'])
def api_app_ping(): return _cors_jsonify({"status": "ok"})
@app.route('/api/silent_check', methods=['POST'])
def api_silent_check(): return _cors_jsonify({"status": "success"})

# ==========================================
# DISCORD BOT A TLAČÍTKA
# ==========================================
class DashboardAuthView(discord.ui.View):
    def __init__(self, token, discord_id):
        super().__init__(timeout=300)
        self.token = token; self.discord_id = discord_id
    @discord.ui.button(label="Ověřit přístup", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        get_db().table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="✅ **Přístup schválen!**", view=None)

intents = discord.Intents.default()
intents.members = True; intents.message_content = True; intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)

def run_web(): app.run(host='0.0.0.0', port=8080, use_reloader=False)

if __name__ == "__main__":
    if os.environ.get("DISCORD_TOKEN"):
        Thread(target=run_web).start()
        bot.run(os.environ.get("DISCORD_TOKEN"))
