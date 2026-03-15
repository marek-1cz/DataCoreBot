import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta
import asyncio
import uuid
import urllib.request
import json
import traceback
import re

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

def get_prague_time():
    return datetime.utcnow() + timedelta(hours=1)

DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

URL_MALE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png"
URL_VELKE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png"

@app.errorhandler(Exception)
def handle_exception(e):
    error_trace = traceback.format_exc()
    print(error_trace, flush=True)
    return f"<div style='background:#0f172a; color:#ef4444; padding:20px; font-family:monospace; border:2px solid #ef4444;'><h2>CHYBA APLIKACE (500)</h2><p>Pošli tohle vývojáři:</p><pre>{error_trace}</pre></div>", 500

# ==========================================
# HTML ŠABLONY
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg-dark: #0f172a; --bg-panel: #1e293b; --blue-main: #38bdf8; --blue-hover: #0284c7; --text-main: #f8fafc; --text-muted: #94a3b8; --danger: #ef4444; --success: #10b981; --warning: #f59e0b; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; }
        .top-nav { background-color: rgba(15, 23, 42, 0.9); padding: 15px 40px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 100; }
        .logo { font-size: 24px; font-weight: 800; color: var(--blue-main); text-decoration: none; letter-spacing: 1px; display: flex; align-items: center; gap: 10px; }
        .nav-links a { color: var(--text-main); text-decoration: none; margin-left: 20px; font-weight: 500; transition: color 0.3s; }
        .nav-links a:hover { color: var(--blue-main); }
        .nav-links .admin-link { color: var(--text-muted); font-size: 12px; margin-left: 40px; border: 1px solid #334155; padding: 5px 10px; border-radius: 5px; }
        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        .btn { display: inline-block; background-color: var(--blue-main); color: #000; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; transition: 0.3s; }
        .btn:hover { background-color: var(--blue-hover); transform: translateY(-2px); color: #fff; }
        .btn-danger { background-color: var(--danger); color: #fff;}
        .btn-danger:hover { background-color: #dc2626; color: #fff;}
        .btn-warning { background-color: var(--warning); color: #000; }
        .btn-warning:hover { background-color: #d97706; color: #000;}
        .btn-success { background-color: var(--success); color: #fff;}
        .btn-success:hover { background-color: #059669; color: #fff;}
        .btn-dark { background-color: #334155; color: white; }
        .btn-dark:hover { background-color: #475569; color: white;}
        input[type="text"], input[type="number"], input[type="password"], input[type="url"], textarea, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; box-sizing: border-box; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background-color: var(--bg-panel); border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background-color: #0f172a; color: var(--blue-main); font-weight: 600; text-transform: uppercase; font-size: 13px; cursor: pointer; transition: background 0.2s;}
        th:hover { background-color: #1e293b; }
        tr:hover { background-color: #334155; }
        .role-tag { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin: 2px; }
        .dashboard-wrapper { display: flex; min-height: 100vh; }
        .sidebar { width: 250px; background-color: var(--bg-panel); border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid #334155; text-align: center; }
        .sidebar-menu { padding: 20px 0; flex-grow: 1; }
        .sidebar-link { display: block; padding: 12px 20px; color: var(--text-muted); text-decoration: none; font-weight: 500; transition: 0.2s; border-left: 3px solid transparent; }
        .sidebar-link:hover, .sidebar-link.active { background-color: rgba(56, 189, 248, 0.1); color: var(--blue-main); border-left-color: var(--blue-main); }
        .sidebar-link i { width: 25px; }
        .dashboard-content { flex-grow: 1; padding: 30px; background-color: var(--bg-dark); overflow-y: auto; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(5px); z-index: 1000; align-items: center; justify-content: center; }
        .modal { background: var(--bg-panel); padding: 30px; border-radius: 15px; width: 700px; max-width: 90%; border-top: 5px solid var(--blue-main); box-shadow: 0 15px 30px rgba(0,0,0,0.5); transform: translateY(20px); transition: 0.3s; max-height: 90vh; overflow-y: auto;}
        .modal.active { display: flex; }
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
        .alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .alert-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
        .checkbox-group { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }
        .checkbox-group label { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: bold; cursor: pointer; }
        .profile-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .profile-card { background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #334155; }
        .profile-stat { font-size: 12px; color: var(--text-muted); margin-bottom: 5px; }
        .profile-val { font-size: 14px; font-weight: bold; color: var(--text-main); }
        .dl-table th, .dl-table td { padding: 8px; font-size: 12px; border-bottom: 1px solid #334155; }
    </style>
</head>
<body>
    {% block layout %}{% endblock %}
</body>
</html>
"""

PUBLIC_LAYOUT = """
<nav class="top-nav">
    <a href="/" class="logo">
        <img src="{{ logo_male }}" alt="Logo" style="height: 30px; width: auto; border-radius: 4px;">
        OIS IDPK
    </a>
    <div class="nav-links">
        <a href="/">Domů</a>
        <a href="/download">Download</a>
        <a href="/team">Náš Tým</a>
        <a href="/supporters" style="color: var(--blue-main); font-weight: bold; text-shadow: 0 0 10px rgba(56, 189, 248, 0.6);"><i class="fas fa-heart"></i> Podporovatelé</a>
        <a href="/dashboard" class="admin-link">Dashboard 🔒</a>
    </div>
</nav>
<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
"""

DASHBOARD_LAYOUT = """
<div class="dashboard-wrapper">
    <div class="sidebar">
        <div class="sidebar-header">
            <a href="/" class="logo" style="font-size: 20px; display: flex; justify-content: center; align-items: center; gap: 8px;">
                <img src="{{ logo_male }}" alt="Logo" style="height: 24px; width: auto; border-radius: 4px;">
                OIS IDPK
            </a>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div>
        </div>
        <div class="sidebar-menu">
            <a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
            <a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-bar"></i> Statistiky Webu</a>
            <a href="/dashboard/app_settings" class="sidebar-link"><i class="fas fa-cog"></i> Nastavení Aplikace</a>
            <a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-cloud-download-alt"></i> Správa Stahování</a>
            <a href="/dashboard/pending_roles" class="sidebar-link" style="color: #10b981;"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a>
            <a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a>
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a>
            
            <a href="/dashboard/supporters" class="sidebar-link" style="color: var(--blue-main); text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);"><i class="fas fa-star"></i> Podporovatelé</a>
            
            <a href="/dashboard?filter=banned" class="sidebar-link" style="color: var(--warning);"><i class="fas fa-ban"></i> Seznam BANů</a>
            <a href="/dashboard?filter=deleted" class="sidebar-link" style="color: var(--danger);"><i class="fas fa-trash-alt"></i> Smazaní (Záloha)</a>
            <div style="padding: 15px 20px 5px 20px; font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold;">Hledat roli</div>
            <a href="/dashboard?filter=SA" class="sidebar-link"><i class="fas fa-crown"></i> SA (SERVER ADMIN)</a>
            <a href="/dashboard?filter=DEV" class="sidebar-link"><i class="fas fa-code"></i> DEV (DEVELOPER)</a>
            <a href="/dashboard?filter=BT" class="sidebar-link"><i class="fas fa-bug"></i> BT (BETA TESTER)</a>
        </div>
        <div style="padding: 20px;">
            <div style="font-size: 11px; color: var(--text-muted); text-align: center; margin-bottom: 15px; border-top: 1px solid #334155; padding-top: 15px;">
                <i class="fas fa-clock"></i> Poslední update bota:<br><b>{{ deploy_time }}</b>
            </div>
            <a href="/logout" class="btn btn-danger" style="width: 100%; text-align: center; box-sizing: border-box;"><i class="fas fa-sign-out-alt"></i> Odhlásit</a>
        </div>
    </div>
    
    <div class="dashboard-content">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</div>

<div class="modal-overlay" id="editModal">
    <div class="modal" id="modalContent">
        <div style="width: 100%;">
            <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-user"></i> Profil <span id="modalAppId" style="color: var(--text-muted); font-size: 16px;"></span></span>
                <span id="modalStatusDot" style="font-size: 14px;"></span>
            </h2>
            
            <div class="profile-grid">
                <div class="profile-card">
                    <div class="profile-stat">Členem Discordu od:</div>
                    <div class="profile-val" id="profJoined"><i class="fas fa-spinner fa-spin"></i> Načítání...</div>
                    <div class="profile-stat" style="margin-top: 10px;">Datum registrace v DB:</div>
                    <div class="profile-val" id="profRegistered"></div>
                    <div class="profile-stat" style="margin-top: 10px;">Aktivita v aplikaci (Status):</div>
                    <div class="profile-val" id="profAppStatus" style="color: #64748b;"><i>Připravuje se...</i></div>
                    <div id="profStats"></div>
                    <div class="profile-stat" style="margin-top: 10px;">Přístup do webové DB:</div>
                    <div class="profile-val" id="profDbAccess"></div>
                </div>
                
                <div class="profile-card" style="max-height: 250px; overflow-y: auto;">
                    <div class="profile-stat" style="margin-bottom: 10px; font-weight:bold; color: var(--blue-main);">Historie stahování:</div>
                    <table class="dl-table" style="width: 100%; margin-top: 0; background: transparent; border-radius: 0;">
                        <tbody id="profDownloads">
                            <tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <form action="/dashboard/edit_user" method="POST" style="border-top: 1px solid #334155; padding-top: 15px;">
                <input type="hidden" name="discord_id" id="modalDiscordId">
                <label>Herní Nick:</label>
                <input type="text" name="nick" id="modalNick" required>
                <label>Role:</label>
                <div class="checkbox-group">
                    <label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label>
                    <label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label>
                    <label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label>
                    <label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label>
                </div>
                <label>HWID (Zámek na PC):</label>
                <input type="text" name="hwid" id="modalHwid" placeholder="Pro odblokování smažte text zde">
                <div style="background-color: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 5px; border: 1px solid var(--blue-main); margin-bottom: 15px;">
                    <label style="cursor: pointer; font-weight: bold; color: var(--blue-main); margin: 0; display: flex; align-items: center; gap: 10px;">
                        <input type="checkbox" name="dashboard_access" id="modalDashboardAccess" value="True" style="width: auto; margin: 0;"> 
                        Povolit přístup do Dashboardu (2FA ověření)
                    </label>
                </div>
                <div id="activeActions">
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit úpravy</button>
                        <button type="submit" name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;"><i class="fas fa-ban"></i> Dát BAN</button>
                        <button type="submit" name="action" value="unban" id="btnUnban" class="btn btn-success" style="flex: 1; display: none;"><i class="fas fa-check"></i> Un-BAN</button>
                    </div>
                    <div style="margin-top: 15px; border-top: 1px solid #334155; padding-top: 15px;">
                        <button type="submit" name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Smazat účet? (Zablokuje ID, umožní novou registraci)')"><i class="fas fa-trash"></i> Smazat účet (Soft Delete)</button>
                    </div>
                </div>
                <div id="deletedActions" style="display: none; margin-top: 20px; border-top: 1px solid #334155; padding-top: 15px;">
                    <p style="color: var(--danger); font-weight: bold; text-align: center; margin-top: 0;">Tento účet je smazaný.</p>
                    <div style="display: flex; gap: 10px;">
                        <button type="submit" name="action" value="restore" class="btn btn-success" style="flex: 1;"><i class="fas fa-undo"></i> Obnovit účet</button>
                        <button type="submit" name="action" value="hard_delete" class="btn btn-dark" style="flex: 1;" onclick="return confirm('PERMANENTNÍ SMAZÁNÍ: Tato akce kompletně vymaže veškerá data o tomto uživateli. Pokračovat?')"><i class="fas fa-skull"></i> Smazat permanentně</button>
                    </div>
                </div>
            </form>
            <button class="btn" onclick="closeModal()" style="background: transparent; color: var(--text-muted); width: 100%; margin-top: 10px; border: 1px solid #334155;">Zrušit</button>
        </div>
    </div>
</div>

<script>
    function openModal(app_id, discord_id, nick, roles, hwid, is_banned, is_deleted, dashboard_access, registered_at) {
        document.getElementById('editModal').style.display = 'flex';
        document.getElementById('modalAppId').innerText = "#" + app_id;
        document.getElementById('modalDiscordId').value = discord_id;
        document.getElementById('modalNick').value = nick;
        document.getElementById('modalHwid').value = hwid === 'None' ? '' : hwid;
        document.getElementById('profRegistered').innerText = registered_at && registered_at !== 'None' ? registered_at : 'Neznámé (Starý účet)';
        document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True');
        document.getElementById('profDbAccess').innerHTML = dashboard_access === 'True' ? '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Povoleno</span>' : '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> Zakázáno</span>';
        document.querySelectorAll('input[name="roles"]').forEach(cb => cb.checked = false);
        roles.split(',').forEach(r => {
            let el = document.querySelector(`input[name="roles"][value="${r.trim()}"]`);
            if(el) el.checked = true;
        });
        if (is_deleted === 'True') {
            document.getElementById('activeActions').style.display = 'none';
            document.getElementById('deletedActions').style.display = 'block';
        } else {
            document.getElementById('activeActions').style.display = 'block';
            document.getElementById('deletedActions').style.display = 'none';
            if (is_banned === 'True') {
                document.getElementById('btnBan').style.display = 'none';
                document.getElementById('btnUnban').style.display = 'block';
            } else {
                document.getElementById('btnBan').style.display = 'block';
                document.getElementById('btnUnban').style.display = 'none';
            }
        }
        document.getElementById('profJoined').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        document.getElementById('modalStatusDot').innerHTML = '';
        document.getElementById('profDownloads').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>';
        document.getElementById('profAppStatus').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        document.getElementById('profStats').innerHTML = '';
        
        fetch('/api/get_profile_data/' + discord_id)
            .then(r => r.json())
            .then(data => {
                document.getElementById('profJoined').innerText = data.joined_at;
                document.getElementById('modalStatusDot').innerHTML = data.status;
                document.getElementById('profAppStatus').innerHTML = data.app_status;
                document.getElementById('profStats').innerHTML = data.stats;
                let dlHtml = "";
                if(data.downloads && data.downloads.length > 0) {
                    data.downloads.forEach(d => {
                        dlHtml += `<tr><td style="color: var(--blue-main);"><b>${d.version_name}</b></td><td style="color: var(--text-muted);">${d.downloaded_at}</td></tr>`;
                    });
                } else {
                    dlHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím nestáhl žádný soubor.</td></tr>";
                }
                document.getElementById('profDownloads').innerHTML = dlHtml;
            });
    }
    function closeModal() { document.getElementById('editModal').style.display = 'none'; }
</script>
"""

HTML_HOME = """
<div style="text-align: center; padding: 60px 20px; max-width: 800px; margin: 0 auto;">
    <h1 style="color: var(--blue-main); font-size: 2.5em; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);">OFICIÁLNÍ STRÁNKA PROJEKTU OIS IDPK</h1>
    
    <div style="font-size: 1.1em; color: var(--text-main); line-height: 1.6; margin-bottom: 40px; background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 10px; border-left: 4px solid var(--blue-main); text-align: left;">
        <p style="margin-top:0;">Projekt OIS IDPK je fanouškovský software inspirovaný skutečnými vnitřními informačními panely, které se používají v autobusech Plzeňského kraje. Cílem projektu je co nejvěrněji napodobit jejich vzhled i způsob fungování.</p>
        <p>Software simuluje zobrazování zastávek, průběh celé linky i další informace, které běžně vidí cestující během jízdy. Díky tomu si můžeš jednoduše vyzkoušet, jak se panel chová při jízdě po trase, jak se postupně mění zastávky nebo jak vypadají informace o aktuální části linky.</p>
        <p style="margin-bottom:0;">Celý projekt vznikl z nadšení pro dopravu, technologie a informační systémy ve veřejné dopravě. Projekt není oficiálním produktem ani službou dopravců nebo organizací veřejné dopravy a nijak s nimi nespolupracuje. Jedná se čistě o fanouškovský projekt vytvořený pro zábavu, experimentování a zájem o dopravní technologie.</p>
    </div>
    
    <a href="/download" class="btn" style="font-size: 18px; padding: 15px 40px; border-radius: 30px; box-shadow: 0 5px 15px rgba(56, 189, 248, 0.4);"><i class="fas fa-download"></i> Získat Software</a>
    
    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 60px 0;">
    
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; background: var(--bg-panel); padding: 40px; border-radius: 15px; border: 1px solid #334155;">
        <img src="{{ logo_velke }}" alt="DataCoreBot Logo" style="max-width: 250px; height: auto; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5)); margin-bottom: 10px;">
        <div style="text-align: center; max-width: 600px;">
            <h3 style="color: var(--warning); margin-top: 0; font-size: 1.6em; text-shadow: 0 0 5px rgba(245, 158, 11, 0.5);">Poháněno systémem DataCoreBot</h3>
            <p style="color: var(--text-muted); font-size: 1em; line-height: 1.6; margin: 0 0 15px 0;">
                Celá infrastruktura, od databází po ověřování uživatelů, je bezpečně řízena a chráněna unikátním systémem DataCoreBot. 
                Zajišťuje bleskovou synchronizaci dat, striktní Hardware ID (HWID) ochranu a nepřetržitý chod palubních počítačů.
            </p>
            <div style="display: inline-block; background: rgba(0,0,0,0.3); padding: 10px 20px; border-radius: 8px; border: 1px solid var(--blue-main);">
                <p style="color: var(--text-main); font-weight: bold; margin: 0; font-size: 1em; letter-spacing: 1px;">
                    <i class="fas fa-code" style="color: var(--blue-main);"></i> Vytvořeno vývojářem <span style="color: var(--blue-main);">marekk_czz</span>
                </p>
            </div>
        </div>
    </div>
</div>
"""

HTML_STATS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-chart-line" style="color:var(--blue-main);"></i> Statistiky Webu</h2>
    <div style="color: var(--text-muted); font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-weight: bold;">
        <i class="fas fa-sync-alt" style="color: var(--blue-main);"></i> Automaticky aktualizováno
    </div>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); text-align: center;">
        <h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0; text-transform: uppercase;">Unikátní zobrazení (Celkem)</h3>
        <div style="font-size: 40px; font-weight: 900; color: var(--text-main);">{{ total_visits }}</div>
    </div>
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--success); text-align: center;">
        <h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0; text-transform: uppercase;">Zobrazení za 7 dní</h3>
        <div style="font-size: 40px; font-weight: 900; color: var(--success);">{{ last_7_days }}</div>
    </div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-calendar-week"></i> Návštěvnost za posledních 7 dní</h3>
        <div style="position: relative; height: 250px; width: 100%;">
            <canvas id="chart7d"></canvas>
        </div>
    </div>
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-clock"></i> Dnešní aktivita po hodinách</h3>
        <div style="position: relative; height: 250px; width: 100%;">
            <canvas id="chart24h"></canvas>
        </div>
    </div>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;"><i class="fas fa-globe"></i> Návštěvnost podle států (Souhrn)</h3>
    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
        {% for cc, data in country_totals.items() %}
        <div style="background: rgba(0,0,0,0.3); border: 1px solid #334155; padding: 10px 20px; border-radius: 8px; display: flex; align-items: center; gap: 10px;">
            <img src="{{ data.flag }}" alt="" style="border-radius: 3px; box-shadow: 0 0 5px rgba(0,0,0,0.5);">
            <span style="color: var(--text-main); font-weight: bold;">{{ data.name }}</span>
            <span style="background: var(--blue-main); color: #000; padding: 2px 8px; border-radius: 12px; font-weight: 900; font-size: 12px;">{{ data.count }}</span>
        </div>
        {% else %}
        <div style="color: var(--text-muted);">Zatím žádná data k zobrazení.</div>
        {% endfor %}
    </div>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-map-marker-alt"></i> Detailní přehled regionů</h3>
    <table style="width: 100%;">
        <tr>
            <th>Stát / Region</th>
            <th>Počet zobrazení</th>
        </tr>
        {% for c_name, data in region_totals.items() %}
        <tr>
            <td style="font-weight: bold; color: var(--text-main); display: flex; align-items: center; gap: 10px;">
                {% if data.flag %}
                <img src="{{ data.flag }}" alt="" style="border-radius: 3px; box-shadow: 0 0 5px rgba(0,0,0,0.5);">
                {% endif %}
                {{ c_name }}
            </td>
            <td style="color: var(--blue-main); font-weight: bold; font-size: 16px;">{{ data.count }}</td>
        </tr>
        {% else %}
        <tr><td colspan="2" style="text-align: center; color: var(--text-muted);">Zatím žádná data k zobrazení. Tabulka "page_visits" je prázdná.</td></tr>
        {% endfor %}
    </table>
</div>

<script>
    const labels7d = {{ labels_7d | safe }};
    const data7d = {{ data_7d | safe }};
    const labels24h = {{ labels_24h | safe }};
    const data24h = {{ data_24h | safe }};

    new Chart(document.getElementById('chart7d').getContext('2d'), {
        type: 'line',
        data: {
            labels: labels7d,
            datasets: [{
                label: 'Počet návštěv',
                data: data7d,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                borderWidth: 3,
                tension: 0.3,
                fill: true
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } } }
    });

    new Chart(document.getElementById('chart24h').getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels24h,
            datasets: [{
                label: 'Dnešní návštěvy',
                data: data24h,
                backgroundColor: '#38bdf8',
                borderRadius: 4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8', maxTicksLimit: 12 }, grid: { display: false } } } }
    });
</script>
"""

HTML_APP_SETTINGS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">Nastavení Aplikace a Systému</h2>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if soft_enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-desktop"></i> Status Softwaru (Kill-Switch)</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if soft_enabled else 'var(--danger)' }}; text-shadow: 0 0 15px {{ 'rgba(16, 185, 129, 0.5)' if soft_enabled else 'rgba(239, 68, 68, 0.5)' }};">
            <i class="fas {{ 'fa-check-circle' if soft_enabled else 'fa-ban' }}"></i>
        </div>
        <p style="color: var(--text-muted); font-size: 14px;">Globální vypínač celé PC aplikace. Pokud je vypnuto, nepustí nikoho dál.</p>
        <form action="/dashboard/toggle_software" method="POST" style="margin-top: 20px;">
            <input type="hidden" name="new_status" value="{{ 'False' if soft_enabled else 'True' }}">
            <button type="submit" class="btn {{ 'btn-danger' if soft_enabled else 'btn-success' }}" style="width: 100%; font-size: 16px;"><i class="fas fa-power-off"></i> {{ 'VYPNOUT SOFTWARE GLOBÁLNĚ' if soft_enabled else 'ZAPNOUT SOFTWARE' }}</button>
        </form>
    </div>

    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if dl_enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-cloud-download-alt"></i> Status Stahování</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if dl_enabled else 'var(--danger)' }}; text-shadow: 0 0 15px {{ 'rgba(16, 185, 129, 0.5)' if dl_enabled else 'rgba(239, 68, 68, 0.5)' }};">
            <i class="fas {{ 'fa-check-circle' if dl_enabled else 'fa-ban' }}"></i>
        </div>
        <p style="color: var(--text-muted); font-size: 14px;">Vypínač instalačního procesu přes Discord bota.</p>
        <form action="/dashboard/toggle_downloads" method="POST" style="margin-top: 20px;">
            <input type="hidden" name="new_status" value="{{ 'False' if dl_enabled else 'True' }}">
            <input type="hidden" name="return_to" value="app_settings">
            <button type="submit" class="btn {{ 'btn-danger' if dl_enabled else 'btn-success' }}" style="width: 100%; font-size: 16px;"><i class="fas fa-power-off"></i> {{ 'ZAKÁZAT STAHOVÁNÍ' if dl_enabled else 'POVOLIT STAHOVÁNÍ' }}</button>
        </form>
    </div>
</div>
"""

HTML_DOWNLOADS_MAIN = """
<div style="text-align: center; padding: 60px 20px; max-width: 700px; margin: 50px auto; background-color: var(--bg-panel); border-radius: 15px; box-shadow: 0 15px 30px rgba(0,0,0,0.5); border-top: 5px solid #5865F2;">
    <h2 style="color: var(--text-main); font-size: 2.2em; margin-top: 0;"><i class="fas fa-shield-alt" style="color: var(--blue-main);"></i> Oficiální distribuce softwaru</h2>
    <p style="color: var(--text-muted); font-size: 1.1em; line-height: 1.6; margin-bottom: 20px;">
        Z důvodu ochrany projektu a samotného softwaru jsme se rozhodli přesunout jeho distribuci na náš Discord server. Díky tomu máme větší kontrolu nad přístupem k softwaru a můžeme lépe zabránit jeho zneužití nebo neautorizovanému šíření.
    </p>
    <div style="background-color: rgba(88, 101, 242, 0.1); border: 1px solid #5865F2; padding: 30px 20px; border-radius: 10px; margin: 30px 20px;">
        <p style="color: var(--text-main); font-weight: bold; font-size: 1.2em; margin-top: 0;">Jak získat software:</p>
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">
            Připojte se na náš Discord, ověřte, že nejste robot, a poté přejděte do kanálu <b>💾・download</b>, kde stačí postupovat podle pokynů DataCoreBota. 🚀
        </p>
        <a href="https://discord.gg/vmTagbC9mF" target="_blank" style="display: inline-block; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'"><i class="fab fa-discord" style="font-size: 120px; color: #5865F2; filter: drop-shadow(0px 10px 15px rgba(88,101,242,0.4));"></i></a>
    </div>
</div>
"""

HTML_LOGIN = """
<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-top: 4px solid var(--blue-main);">
    <h2 style="text-align: center; color: var(--blue-main); margin-top: 0;"><i class="fas fa-lock"></i> Dashboard 2FA</h2>
    <div style="background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--danger); padding: 12px; margin-bottom: 20px; border-radius: 0 5px 5px 0;">
        <p style="color: var(--danger); margin: 0; font-size: 13px; font-weight: 800; text-transform: uppercase;"><i class="fas fa-shield-alt"></i> Zabezpečená zóna</p>
        <p style="color: var(--text-muted); margin: 5px 0 0 0; font-size: 12px; line-height: 1.4;">Tato databáze je přísně vyhrazena <b>pouze pro administrátory a pověřené správce</b> projektu. Běžní uživatelé sem nemají přístup. Každý pokus o neoprávněné přihlášení je monitorován a logován.</p>
    </div>
    <p style="color: var(--text-muted); text-align: center; font-size: 13px;">Pro přístup do systému zadejte své <b>Discord ID</b>.</p>
    <form method="POST" action="/login_request">
        <label style="font-weight: bold; font-size: 12px; color: var(--text-muted);">VAŠE DISCORD ID</label>
        <input type="text" name="discord_id" placeholder="Např. 123456789012345678" required>
        <button type="submit" class="btn" style="width: 100%; margin-top: 10px;"><i class="fab fa-discord"></i> Odeslat žádost o přihlášení</button>
    </form>
</div>
"""

HTML_WAIT_AUTH = """
<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; border-top: 4px solid var(--warning);">
    <h2 style="color: var(--warning); margin-top: 0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2>
    <p style="color: var(--text-main); font-size: 16px;">Byla Vám odeslána soukromá zpráva na Discord.</p>
    <p style="color: var(--text-muted); font-size: 14px;">Zkontrolujte si aplikaci Discord a klikněte na tlačítko <b>Ověřit přístup</b>.</p>
</div>
<script>
    setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}')
        .then(r => r.json())
        .then(data => {
            if(data.status === 'approved') { window.location.href = '/dashboard/login_finalize?discord_id={{ discord_id }}'; } 
            else if(data.status === 'rejected') { window.location.href = '/dashboard'; }
        });
    }, 2000);
</script>
"""

HTML_TEAM = """
<h2 style="color: var(--blue-main); border-bottom: 2px solid #334155; padding-bottom: 10px; text-align:center;">Náš Tým</h2>
<div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 20px;">
    {% for member in team %}
    <div style="background-color: var(--bg-panel); border-radius: 10px; padding: 20px; text-align: center; border-top: 4px solid var(--blue-main); width: 300px; max-width:100%; transition: transform 0.5s ease, box-shadow 0.5s ease;">
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
    <p style="color: var(--text-muted); text-align:center; width:100%;">Zatím nebyli přidáni žádní členové týmu.</p>
    {% endfor %}
</div>
<style>
    div[style*="width: 300px"]:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 30px rgba(56, 189, 248, 0.4);
    }
</style>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">Správa Stahování</h2>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-power-off"></i> Hlavní vypínač instalací</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if enabled else 'var(--danger)' }}; text-shadow: 0 0 15px {{ 'rgba(16, 185, 129, 0.5)' if enabled else 'rgba(239, 68, 68, 0.5)' }};">
            <i class="fas {{ 'fa-check-circle' if enabled else 'fa-ban' }}"></i>
        </div>
        <p style="color: var(--text-muted); font-size: 14px;">Pokud je vypnuto, nikdo nebude moci zahájit instalaci přes Discord bota.</p>
        <form action="/dashboard/toggle_downloads" method="POST" style="margin-top: 20px;">
            <input type="hidden" name="new_status" value="{{ 'False' if enabled else 'True' }}">
            <input type="hidden" name="return_to" value="downloads">
            <button type="submit" class="btn {{ 'btn-danger' if enabled else 'btn-success' }}" style="width: 100%; font-size: 16px;"><i class="fas fa-power-off"></i> {{ 'ZAKÁZAT STAHOVÁNÍ' if enabled else 'POVOLIT STAHOVÁNÍ' }}</button>
        </form>
    </div>

    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat Instalační Soubor (Verzi)</h3>
        <p style="color: var(--warning); font-size: 12px; margin-top: -5px;">Můžete vložit odkaz na <b>PixelDrain.com</b>, <b>OneDrive</b>, nebo Dropbox.</p>
        <form action="/dashboard/add_version" method="POST">
            <input type="text" name="version_name" placeholder="Název zobrazený v menu (např. Stabilní v1.0)" required>
            <input type="url" name="file_url" placeholder="Přímý odkaz na stažení souboru" required>
            <label style="color: var(--text-muted); font-size: 13px;">Pro jakou minimální roli je tato verze určena?</label>
            <select name="target_role" required>
                <option value="User">User (Uvidí všichni - Normální verze)</option>
                <option value="BT">BETA TESTER (Uvidí BT, DEV, SA - Testovací verze)</option>
                <option value="DEV_SA">DEV / SERVER ADMIN (Uvidí pouze vývojáři a admini)</option>
            </select>
            <button type="submit" class="btn" style="width: 100%;">Přidat verzi do menu</button>
        </form>
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">📦 Dostupné soubory</h3>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>Název v Menu</th>
                <th>Cílová Skupina</th>
                <th>Odkaz na soubor</th>
                <th>Akce</th>
            </tr>
            {% for v in versions %}
            <tr>
                <td><strong>{{ v.get('version_name', '') }}</strong></td>
                <td>
                    {% if v.get('target_role') == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User (Všichni)</span>{% endif %}
                    {% if v.get('target_role') == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BETA TESTER+</span>{% endif %}
                    {% if v.get('target_role') == 'DEV_SA' %}<span class="role-tag" style="background-color: #ef4444; color: white;">DEV / SA</span>{% endif %}
                </td>
                <td style="font-size: 12px; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    <a href="{{ v.get('file_url', '') }}" target="_blank" style="color: var(--blue-main);">{{ v.get('file_url', '') }}</a>
                </td>
                <td>
                    <button type="button" class="btn btn-warning" style="padding: 5px 10px; font-size: 12px;" onclick="openEditVerModal('{{ v.get('id', '') }}', '{{ v.get('version_name', '') }}', '{{ v.get('file_url', '') }}', '{{ v.get('target_role', '') }}')"><i class="fas fa-edit"></i> Úprava</button>
                    <form action="/dashboard/delete_version" method="POST" style="display:inline;">
                        <input type="hidden" name="version_id" value="{{ v.get('id', '') }}">
                        <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat tuto verzi ze stahování?')"><i class="fas fa-trash"></i> Smazat</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Zatím nebyly přidány žádné soubory ke stažení.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="modal-overlay" id="editVerModal">
    <div class="modal">
        <div style="width: 100%;">
            <h2 style="color: var(--warning); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                <i class="fas fa-edit"></i> Upravit verzi
            </h2>
            <form action="/dashboard/edit_version" method="POST">
                <input type="hidden" name="version_id" id="ev_id">
                
                <label style="color: var(--text-muted); font-size: 13px;">Název v Menu:</label>
                <input type="text" name="version_name" id="ev_name" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">URL odkazu:</label>
                <input type="url" name="file_url" id="ev_url" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">Pro jakou minimální roli?</label>
                <select name="target_role" id="ev_role" required>
                    <option value="User">User (Všichni)</option>
                    <option value="BT">BETA TESTER (Testovací)</option>
                    <option value="DEV_SA">DEV / SERVER ADMIN (Neveřejné)</option>
                </select>
                
                <button type="submit" class="btn btn-warning" style="width: 100%; margin-top: 15px;">Uložit změny</button>
            </form>
            <button type="button" class="btn" style="width: 100%; margin-top: 10px; background: transparent; border: 1px solid #334155; color: var(--text-muted);" onclick="document.getElementById('editVerModal').style.display='none'">Zrušit</button>
        </div>
    </div>
</div>
<script>
    function openEditVerModal(id, name, url, role) {
        document.getElementById('ev_id').value = id;
        document.getElementById('ev_name').value = name;
        document.getElementById('ev_url').value = url;
        document.getElementById('ev_role').value = role;
        document.getElementById('editVerModal').style.display = 'flex';
    }
</script>
"""

HTML_PENDING_ROLES = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">Rezervace Rolí (Nezaregistrovaní)</h2>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Předpřipravit Roli</h3>
        <p style="color: var(--text-muted); font-size: 13px;">Jakmile uživatel s tímto ID nebo Nickem na Discordu klikne na instalaci, systém mu automaticky přiřadí vybranou roli místo základního "User".</p>
        <form action="/dashboard/add_pending_role" method="POST">
            <input type="text" name="discord_identifier" placeholder="Discord Nick (nebo Discord ID)" required>
            <label style="color: var(--text-muted); font-size: 13px; display: block; margin-bottom: 8px;">Vyberte roli pro rezervaci:</label>
            <div class="checkbox-group">
                <label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label>
                <label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label>
                <label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label>
                <label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label>
            </div>
            <button type="submit" class="btn" style="width: 100%; margin-top: 15px;">Vytvořit Rezervaci</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">⏳ Čekající rezervace</h3>
        <div style="overflow-x: auto;">
            <table>
                <tr>
                    <th>Discord Identifikátor</th>
                    <th>Rezervovaná Role</th>
                    <th>Akce</th>
                </tr>
                {% for p in pending %}
                <tr>
                    <td><strong>{{ p.get('discord_identifier', '') }}</strong></td>
                    <td>
                        {% set role_list = p.get('roles', '').split(',') if p.get('roles') else ['User'] %}
                        {% for r in role_list %}
                            {% set r_clean = r.strip() %}
                            {% if r_clean == 'SA' %}
                                <span class="role-tag" style="color: white; background-color: #ef4444; border-color: #ef4444;">SERVER ADMIN</span>
                            {% elif r_clean == 'DEV' %}
                                <span class="role-tag" style="color: white; background-color: #10b981; border-color: #10b981;">DEVELOPER</span>
                            {% elif r_clean == 'BT' %}
                                <span class="role-tag" style="color: white; background-color: #3b82f6; border-color: #3b82f6;">BETA TESTER</span>
                            {% elif r_clean == 'User' %}
                                <span class="role-tag" style="color: white; background-color: #64748b; border-color: #64748b;">User</span>
                            {% endif %}
                        {% endfor %}
                    </td>
                    <td>
                        <form action="/dashboard/delete_pending_role" method="POST" style="display:inline;">
                            <input type="hidden" name="pending_id" value="{{ p.get('id', '') }}">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Zrušit tuto rezervaci?')"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">Zatím žádné čekající rezervace.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</div>
"""

HTML_TEAM_ADD = """
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat člena týmu</h3>
        <form action="/dashboard/add_team" method="POST">
            <input type="text" name="name" placeholder="Jméno / Přezdívka" required>
            <input type="text" name="discord_nick" placeholder="Discord Nick (bez @)" required>
            <input type="url" name="image_url" placeholder="URL obrázku (odkaz na fotku)" required>
            <textarea name="description" placeholder="Něco o něm..." rows="3" required></textarea>
            <label style="color: var(--text-muted); font-size: 13px; display: block; margin-bottom: 8px;">Role a jejich barvy:</label>
            <div id="roles-container">
                <div class="role-entry" style="display: flex; gap: 10px; margin-bottom: 5px;">
                    <input type="text" name="role_name[]" placeholder="Název Role (např. SA)" required style="flex: 2; margin: 0;">
                    <input type="color" name="role_color[]" value="#ef4444" style="flex: 1; padding: 2px; height: 40px; margin: 0;">
                </div>
            </div>
            <button type="button" class="btn btn-dark" onclick="addRoleField()" style="width: 100%; margin-bottom: 15px; margin-top: 5px; padding: 5px; font-size: 12px;">+ Přidat další roli</button>
            <button type="submit" class="btn" style="width: 100%;">Přidat do týmu</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">👥 Aktuální členové týmu</h3>
        <div style="overflow-x: auto;">
            <table>
                <tr>
                    <th>Jméno</th>
                    <th>Discord Nick</th>
                    <th>Role</th>
                    <th>Akce</th>
                </tr>
                {% for member in team %}
                <tr>
                    <td><strong>{{ member.get('name', '') }}</strong></td>
                    <td>{{ member.get('discord_nick', '') }}</td>
                    <td>
                        {% set roles_input = member.get('role_name', '').split(',') if member.get('role_name') else [] %}
                        {% for r in roles_input %}
                            {% set parts = r.split('|') %}
                            {% set r_name = parts[0].strip() %}
                            {% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                            <span class="role-tag" style="color: {{ r_color }}; border: 1px solid {{ r_color }}; background-color: {{ r_color }}33;">{{ r_name }}</span>
                        {% endfor %}
                    </td>
                    <td>
                        <form action="/dashboard/delete_team" method="POST" style="display:inline;">
                            <input type="hidden" name="discord_nick" value="{{ member.get('discord_nick', '') }}">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat tohoto člena z týmu?')"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Zatím nebyl přidán žádný člen týmu.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</div>
<script>
    function addRoleField() {
        const container = document.getElementById('roles-container');
        const div = document.createElement('div');
        div.className = 'role-entry';
        div.style = 'display: flex; gap: 10px; margin-bottom: 5px;';
        div.innerHTML = `<input type="text" name="role_name[]" placeholder="Název Role" required style="flex: 2; margin: 0;"><input type="color" name="role_color[]" value="#38bdf8" style="flex: 1; padding: 2px; height: 40px; margin: 0;"><button type="button" class="btn btn-danger" onclick="this.parentElement.remove()" style="padding: 0 10px; margin: 0;">X</button>`;
        container.appendChild(div);
    }
</script>
"""

HTML_IDS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">Správa Aplikačních ID</h2>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">Zde můžete ručně změnit ID libovolnému uživateli. Tímto způsobem lze také znovu obsadit ID, které bylo dříve zablokováno smazaným uživatelem.</p>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>App ID</th>
                <th>Nick</th>
                <th>Discord ID</th>
                <th>Status Účtu</th>
                <th>Změnit ID na:</th>
            </tr>
            {% for user in users %}
            <tr style="opacity: {{ '0.6' if user.get('is_deleted') else '1' }};">
                <td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td>
                <td><strong>{{ user.get('nick', '') }}</strong></td>
                <td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td>
                <td>
                    {% if user.get('is_deleted') %}
                        <span style="color: var(--danger); font-size: 12px; font-weight: bold;">Smazán (Blokuje ID)</span>
                    {% else %}
                        <span style="color: var(--success); font-size: 12px;">Aktivní</span>
                    {% endif %}
                </td>
                <td>
                    <form action="/dashboard/change_id" method="POST" style="display: flex; gap: 5px;">
                        <input type="hidden" name="discord_id" value="{{ user.get('discord_id', '') }}">
                        <input type="number" name="new_app_id" placeholder="Nové ID" required style="width: 100px; margin: 0; padding: 5px;">
                        <button type="submit" class="btn" style="padding: 5px 10px; font-size: 12px;">Změnit</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
"""

# ==========================================
# GLOBÁLNÍ FUNKCE A TŘÍDĚNÍ PODPOROVATELŮ
# ==========================================

def get_db():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

def process_supporters(data_list):
    for s in data_list:
        amt_str = str(s.get('amount', '0'))
        match = re.search(r'([\d\.,]+)', amt_str)
        val = 0.0
        if match:
            val_str = match.group(1).replace(',', '.')
            try: val = float(val_str)
            except: pass
        
        norm_val = val
        lower_amt = amt_str.lower()
        if 'usd' in lower_amt or '$' in lower_amt: norm_val *= 23
        elif 'eur' in lower_amt or '€' in lower_amt: norm_val *= 25
        
        s['norm_val'] = norm_val
        
        if norm_val >= 325: s['tier'] = 3
        elif norm_val >= 195: s['tier'] = 2
        else: s['tier'] = 1

    data_list.sort(key=lambda x: (x.get('norm_val', 0), x.get('id', 0)), reverse=True)
    return data_list

async def assign_supporter_role(identifier, role_name):
    try:
        for guild in bot.guilds:
            member = None
            if identifier.isdigit():
                member = guild.get_member(int(identifier))
            if not member:
                member = discord.utils.find(
                    lambda m: m.name.lower() == identifier.lower() or 
                              (m.global_name and m.global_name.lower() == identifier.lower()), 
                    guild.members
                )

            if member:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.add_roles(role)
                    try:
                        embed = discord.Embed(
                            title="🎉 Děkujeme za obrovskou podporu!", 
                            description=f"Na našem Discord serveru a v databázi ti byla automaticky přidělena exkluzivní role:\n\n**{role_name}**\n\nMoc si toho vážíme!", 
                            color=0x38bdf8
                        )
                        await member.send(embed=embed)
                    except: pass
                break
    except Exception as e:
        print(f"Chyba pri pridelovani role: {e}")

async def async_send_log(title, description, color=0x38bdf8):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=get_prague_time())
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

@app.before_request
def check_session_validity():
    if request.path.startswith('/dashboard/') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize']:
        if not session.get('logged_in'):
            return redirect(url_for('dashboard_main'))
            
    if request.path.startswith('/dashboard') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize'] and session.get('logged_in'):
        discord_id = session.get('discord_id')
        if discord_id:
            try:
                db = get_db()
                if db:
                    users_data = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                    user = users_data[0] if users_data else None
                    if not user or not user.get("dashboard_access") or user.get("is_banned") or user.get("is_deleted"):
                        session.clear()
                        flash('Váš přístup byl zablokován nebo odebrán.', 'error')
                        return redirect(url_for('dashboard_main'))
            except: pass

def sync_roles_from_flask(discord_id, role_string):
    async def sync():
        try:
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id))
                if not member:
                    try: member = await guild.fetch_member(int(discord_id))
                    except: pass
                if member: await update_member_roles(member, role_string)
        except: pass
    if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(sync(), bot.loop)

# ==========================================
# PUBLIC FLASK STRÁNKY A BMAC
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
                if record.get("visited_at", "").startswith(today_str):
                    return
            
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
            
            if not country_code or country_code.lower() == 'us' or country_name.lower() in ["neznámá", "unknown", "neznámá (nepodporováno)", "none", "united states", "us"]:
                return 
            
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
        data = db.table("supporters").select("*").execute().data or [] if db else []
        support_data = process_supporters(data)
    except: support_data = []
    return render_public(HTML_SUPPORTERS, supporters=support_data)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        if not db: return _cors_jsonify({"error": "DB not ready"}), 500
        data = db.table("supporters").select("name, amount, message, created_at").execute().data or []
        support_data = process_supporters(data)
        return _cors_jsonify({"supporters": support_data})
    except Exception as e: return _cors_jsonify({"error": str(e)}), 500

@app.route('/webhook/bmac', methods=['GET', 'POST'])
def bmac_webhook():
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
        
        # Výpočet Tieru
        norm_val = float(amount_val)
        if 'usd' in currency.lower() or '$' in currency.lower(): norm_val *= 23
        elif 'eur' in currency.lower() or '€' in currency.lower(): norm_val *= 25

        if norm_val >= 325: assigned_role = "⭐| MEGA PODPOROVATEL"
        elif norm_val >= 195: assigned_role = "⭐| VELKÝ PODPOROVATEL"
        else: assigned_role = "⭐| PODPOROVATEL"

        # Získání Discord ID/Nicku
        discord_identifier = None
        id_match = re.search(r'\b\d{17,19}\b', message)
        if id_match:
            discord_identifier = id_match.group(0)
        else:
            nick_match = re.search(r'(?i)(?:discord|dc|nick)[\s:]+([a-zA-Z0-9_.-]+)', message)
            if nick_match:
                discord_identifier = nick_match.group(1).strip()
            else:
                custom_questions = data.get('custom_questions', [])
                if isinstance(custom_questions, list):
                    for q in custom_questions:
                        ans = str(q.get('answer', ''))
                        if ans:
                            discord_identifier = ans.strip()
                            break
                elif isinstance(custom_questions, dict):
                    for k, v in custom_questions.items():
                        if v:
                            discord_identifier = str(v).strip()
                            break

        db = get_db()
        if db:
            db.table("supporters").insert({"name": str(name), "message": str(message), "amount": str(amount_str), "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            send_log("🍕 Nový dárce!", f"Uživatel **{name}** právě poslal **{amount_str}**.\n\n*Vzkaz: {message}*", 0xF4CC17)

            if discord_identifier:
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_identifier},nick.ilike.{discord_identifier}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    if assigned_role not in current_roles:
                        new_roles = f"{current_roles},{assigned_role}" if current_roles else assigned_role
                        db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
                else:
                    db.table("pending_roles").insert({"discord_identifier": discord_identifier, "roles": assigned_role}).execute()

                if bot.loop and bot.loop.is_running():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_identifier, assigned_role), bot.loop)

        if request.method == 'GET': return f"<h1>ÚSPĚCH! 🎉</h1><p>Testovací podpora zapsána!</p><a href='/supporters'>Zpět</a>"
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
        if not resp.data: return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný odkaz!</h2></div>")
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"): return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Přístup zamítnut</h2></div>")
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data: return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--warning);'>Chyba verze</h2></div>")
            
        v_data = v_resp.data[0]
        html = f"""<div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; border-top: 4px solid var(--success);"><h2 style="color: var(--success); margin-top: 0;"><i class="fas fa-check-circle"></i> Ověření úspěšné</h2><p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Přihlášen jako: <strong>{user.get('nick', '')}</strong></p><div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;"><h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3><p style="margin: 0; color: var(--text-main);">Instalátor: <strong>{v_data.get('version_name', '')}</strong></p></div><a href="/api/get_file/{token}?v={version_id}" class="btn btn-success" style="font-size: 18px; padding: 15px 30px;"><i class="fas fa-download"></i> Stáhnout Soubor</a></div>"""
        return render_public(html)
    except: return "Systémová chyba."

@app.route('/api/get_file/<token>')
def api_get_file(token):
    db = get_db()
    if not db: return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if not resp.data: return "Neplatný token."
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"): return "Přístup zamítnut."
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data: return "Verze nenalezena."
            
        file_url = v_resp.data[0]['file_url']
        version_name = v_resp.data[0]['version_name']
        
        try:
            db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": version_name, "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            send_log("📥 Stahování", f"Uživatel `{user.get('nick')}` zahájil stahování: **{version_name}**.", 0x38bdf8)
        except: pass
        
        file_ext = "zip" 
        if "pixeldrain.com/u/" in file_url: file_url = file_url.replace("/u/", "/api/file/")
        if "1drv.ms" in file_url or "onedrive.live.com" in file_url or "1drv.com" in file_url: file_url = file_url.split("?")[0] + "?download=1"
        if "dropbox.com" in file_url:
            file_url = file_url.replace("dl=0", "dl=1")
            if "dl=1" not in file_url: file_url += "?dl=1" if "?" not in file_url else "&dl=1"

        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        remote_response = urllib.request.urlopen(req)
        def generate():
            while True:
                chunk = remote_response.read(8192)
                if not chunk: break
                yield chunk
        content_type = remote_response.headers.get('Content-Type', 'application/octet-stream')
        return Response(stream_with_context(generate()), headers={'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name.replace(" ", "_")}.{file_ext}"', 'Content-Type': content_type})
    except Exception as e: return f"Chyba odkazu: {e}"

# ==========================================
# API PRO SOFTWARE
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
    data = request.get_json(silent=True) or {}
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
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "":
            if str(db_hwid) != req_hwid:
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
    data = request.get_json(silent=True) or {}
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
                if req_hwid and req_hwid.startswith("PC-"):
                    db.table("users").update({"hwid": req_hwid, "login_token": ""}).eq("discord_id", discord_id).execute()
                else:
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            else:
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "success", "display_name": user.get("nick")})
            
        elif user.get("login_token") == "rejected":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."})
            
        return _cors_jsonify({"status": "pending"})
    except: return _cors_jsonify({"status": "error"})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
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
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                return _cors_jsonify({"status": "success"})
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Chyba čtení PC."})

        if str(db_hwid) != req_hwid:
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Váš počítač nesouhlasí."})
            
        return _cors_jsonify({"status": "success"})
    except Exception as e: return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_ping', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_ping():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    action = data.get("action", "ping")
    db = get_db()
    try:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")
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
    return render_public(HTML_WAIT_AUTH, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    try:
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
            if user:
                t = user[0].get("login_token")
                if t == "approved":
                    return {"status": "approved"}
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
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard/stats')
def dashboard_stats():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    total_visits = 0
    last_7_days = 0
    country_totals = {}
    region_totals = {}
    
    dates_7_days = [(get_prague_time().replace(tzinfo=None) - timedelta(days=i)).strftime("%d.%m.") for i in range(6, -1, -1)]
    chart_data_7d = {d: 0 for d in dates_7_days}
    chart_data_24h = {f"{i:02d}:00": 0 for i in range(24)}
    
    try:
        db = get_db()
        if db:
            visits = db.table("page_visits").select("*").execute().data or []
            total_visits = len(visits)
            now = get_prague_time().replace(tzinfo=None)
            
            for v in visits:
                c_raw = v.get('country', '')
                if not c_raw or 'neznámá' in c_raw.lower() or 'unknown' in c_raw.lower() or 'none' in c_raw.lower() or 'us' in c_raw.lower():
                    continue
                
                parts = c_raw.split('|')
                cc = parts[0] if len(parts) > 0 else ""
                c_name = parts[1] if len(parts) > 1 else c_raw
                reg = parts[2] if len(parts) > 2 else ""
                
                if not cc or cc == 'us': continue
                
                flag_url = f"https://flagcdn.com/24x18/{cc}.png"
                
                if cc not in country_totals:
                    country_totals[cc] = {"name": c_name, "count": 0, "flag": flag_url}
                country_totals[cc]["count"] += 1
                
                display_name = f"{c_name} - {reg}" if reg else c_name
                if display_name not in region_totals:
                    region_totals[display_name] = {"count": 0, "flag": flag_url}
                region_totals[display_name]["count"] += 1
                
                try:
                    v_time = datetime.strptime(v['visited_at'], "%d.%m.%Y %H:%M")
                    if (now - v_time).days <= 7:
                        last_7_days += 1
                        
                    day_str = v_time.strftime("%d.%m.")
                    hour_str = v_time.strftime("%H:00")
                    if day_str in chart_data_7d: chart_data_7d[day_str] += 1
                    if v_time.date() == now.date():
                        if hour_str in chart_data_24h: chart_data_24h[hour_str] += 1
                except: pass
                
    except Exception as e: flash(f"Chyba při načítání statistik: {e}", "error")
    
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
                            if (now - last_dt).total_seconds() > 120:
                                u["is_online"] = False
                                db.table("users").update({"is_online": False}).eq("discord_id", u["discord_id"]).execute()
                        except: pass
    except Exception as e: flash(f"Chyba při načítání dat: {e}", "error")
    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title="Přehled uživatelů", deploy_time=DEPLOY_TIME)

@app.route('/dashboard/supporters', methods=['GET'])
def dashboard_supporters():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    try: 
        db = get_db()
        support_data = process_supporters(db.table("supporters").select("*").execute().data or []) if db else []
    except Exception as e: 
        flash(f"Chyba při stahování seznamu dárů: {e}", "error")
        support_data = []
    return render_dashboard(HTML_SUPPORTERS_MGMT, supporters=support_data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_supporter', methods=['POST'])
def add_supporter():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("supporters").insert({"name": request.form.get("name"), "amount": request.form.get("amount"), "message": request.form.get("message", ""), "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
        flash('Podporovatel byl úspěšně přidán!', 'success')
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

@app.route('/api/get_profile_data/<discord_id>')
def get_profile_data(discord_id):
    if not session.get('logged_in'): return jsonify({"joined_at": "Neznámé", "status": "Neznámý", "downloads": []})
    joined_at = "Neznámé"
    app_status_html = "<span style='color: #64748b;'><i>Neaktivní</i></span>"
    stats_html = ""
    dls = []
    status_map = { "online": "<span style='color:#10b981; font-weight:bold;'><i class='fas fa-circle'></i> Online</span>", "idle": "<span style='color:#f59e0b; font-weight:bold;'><i class='fas fa-moon'></i> Nečinný</span>", "dnd": "<span style='color:#ef4444; font-weight:bold;'><i class='fas fa-minus-circle'></i> Nerušit</span>", "offline": "<span style='color:#64748b; font-weight:bold;'><i class='fas fa-circle'></i> Offline</span>" }
    status_html = status_map["offline"]
    try:
        if bot.guilds:
            for g in bot.guilds:
                m = g.get_member(int(discord_id))
                if m:
                    joined_at = m.joined_at.strftime("%d.%m.%Y") if m.joined_at else "Neznámé"
                    status_html = status_map.get(str(m.status), status_map["offline"])
                    break
        db = get_db()
        if db:
            dls = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data or []
            db_user = db.table("users").select("last_active, is_online, launch_count, total_time").eq("discord_id", discord_id).execute().data
            if db_user:
                u = db_user[0]
                is_on = u.get("is_online", False)
                la_str = u.get("last_active") or ""
                if is_on and la_str:
                    try:
                        last_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S")
                        if (get_prague_time().replace(tzinfo=None) - last_dt).total_seconds() > 120:
                            is_on = False
                            db.table("users").update({"is_online": False}).eq("discord_id", discord_id).execute()
                    except: pass
                
                m, s = divmod(u.get("total_time") or 0, 60)
                h, m = divmod(m, 60)
                
                if is_on: app_status_html = '<span style="color: var(--success); font-weight:bold;">🟢 AKTIVNÍ</span>'
                else: app_status_html = f'<span style="color: var(--danger);">🔴 Offline</span> (Naposledy: {la_str or "Nikdy"})'
                stats_html = f"<div style='margin-top:10px; font-size:12px; color:var(--text-muted); border-top: 1px solid #334155; padding-top: 10px;'><div><b>Spuštění:</b> {u.get('launch_count') or 0}x</div><div style='margin-top:5px;'><b>Čas:</b> {h}h {m}m {s}s</div></div>"
    except: pass
    return jsonify({"joined_at": joined_at, "status": status_html, "app_status": app_status_html, "stats": stats_html, "downloads": dls})

@app.route('/dashboard/app_settings', methods=['GET'])
def dashboard_app_settings():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    soft_enabled = True; dl_enabled = True
    try:
        db = get_db()
        if db:
            res = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled"]).execute().data or []
            for r in res:
                if r.get('setting_key') == 'software_enabled' and str(r.get('setting_value')).lower() == 'false': soft_enabled = False
                if r.get('setting_key') == 'downloads_enabled' and str(r.get('setting_value')).lower() == 'false': dl_enabled = False
    except: pass
    return render_dashboard(HTML_APP_SETTINGS, soft_enabled=soft_enabled, dl_enabled=dl_enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = []; enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if set_resp and str(set_resp[0].get('setting_value')).lower() == 'false': enabled = False
            versions = db.table("software_versions").select("*").order("id").execute().data or []
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled, deploy_time=DEPLOY_TIME)

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
    return redirect(url_for('dashboard_app_settings'))

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
        except Exception as e: flash(f"Chyba: {e}", "error")
    if return_to == 'app_settings': return redirect(url_for('dashboard_app_settings'))
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: get_db().table("software_versions").insert({"version_name": request.form.get("version_name"), "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}).execute()
    except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/edit_version', methods=['POST'])
def edit_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("software_versions").update({"version_name": request.form.get("version_name"), "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}).eq("id", request.form.get("version_id")).execute()
        flash('Verze byla úspěšně upravena.', 'success')
    except Exception as e: flash(f'Chyba při úpravě verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    try: get_db().table("software_versions").delete().eq("id", request.form.get("version_id")).execute()
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
        try: db.table("users").update({"app_id": int(request.form.get("new_app_id"))}).eq("discord_id", request.form.get("discord_id")).execute()
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
    if get_db(): 
        try: get_db().table("team").delete().eq("discord_nick", request.form.get("discord_nick")).execute()
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
                db.table("users").update({"nick": nick, "role": r_str, "hwid": request.form.get("hwid"), "dashboard_access": True if request.form.get("dashboard_access") else False}).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str); flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute(); flash('BAN udělen.', 'warning')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute(); flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute(); flash('Účet smazán (Soft Delete).', 'danger')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute(); flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute(); flash('Účet trvale smazán.', 'dark')
                if str(session.get('discord_id')) == str(discord_id): session.clear()
        except: pass
    return redirect(url_for('dashboard_main'))

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
        self.token = token; self.discord_id = discord_id; self.is_dm = is_dm
    @discord.ui.button(label="Ano, ověřit", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        if str(interaction.user.id) != str(self.discord_id): return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        get_db().table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
        await interaction.response.edit_message(content="✅ **Ověřeno! Můžete se vrátit do aplikace.**", view=None)
        send_log("🖥️ Přihlášení do Aplikace", f"Uživatel s ID `{self.discord_id}` se úspěšně ověřil a vstoupil do softwaru.", 0x10b981)
        if not self.is_dm: await asyncio.sleep(2); await interaction.message.delete()

intents = discord.Intents.default()
intents.members = True; intents.message_content = True; intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.invites_cache = {}

@tasks.loop(hours=24)
async def pixeldrain_keepalive():
    db = get_db()
    if not db: return
    try:
        resp = db.table("software_versions").select("version_name, file_url").execute()
        versions = getattr(resp, "data", []) or []
        refreshed = []
        for v in versions:
            url = v.get("file_url", "")
            name = v.get("version_name", "Neznámá verze")
            if "pixeldrain.com/u/" in url:
                api_url = url.replace("/u/", "/api/file/")
                try:
                    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-10'})
                    await asyncio.to_thread(urllib.request.urlopen, req, timeout=15)
                    refreshed.append(name)
                except: pass
        if refreshed:
            files_str = "\n• ".join(refreshed)
            await async_send_log("🔄 Anti-Delete Ochrana", f"Systém právě úspěšně nasimuloval stažení.\n**Ochráněné soubory:**\n• {files_str}", 0x3b82f6)
    except: pass

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)
    try: bot.add_view(DynamicDownloadView())
    except: pass
    try:
        for guild in bot.guilds: bot.invites_cache[guild.id] = await guild.invites()
    except: pass
    if not pixeldrain_keepalive.is_running(): pixeldrain_keepalive.start()

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

async def update_member_roles(member, role_string):
    if not member or not member.guild: return
    u_roles = [r.strip() for r in role_string.split(',')]
    try:
        r_sa = discord.utils.get(member.guild.roles, name="web-sa")
        r_dev = discord.utils.get(member.guild.roles, name="web-dev")
        r_bt = discord.utils.get(member.guild.roles, name="web-bt")
        if r_sa:
            if "SA" in u_roles and r_sa not in member.roles: await member.add_roles(r_sa)
            elif "SA" not in u_roles and r_sa in member.roles: await member.remove_roles(r_sa)
        if r_dev:
            if "DEV" in u_roles and r_dev not in member.roles: await member.add_roles(r_dev)
            elif "DEV" not in u_roles and r_dev in member.roles: await member.remove_roles(r_dev)
        if r_bt:
            if "BT" in u_roles and r_bt not in member.roles: await member.add_roles(r_bt)
            elif "BT" not in u_roles and r_bt in member.roles: await member.remove_roles(r_bt)
    except: pass

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
            await interaction.edit_original_response(content=f"✅ Účet `{self.target_id}` byl z databáze PERMANENTNĚ smazán.", view=None, embed=None)
    @discord.ui.button(label="Zrušit", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.edit_message(content="❌ Akce zrušena.", view=None, embed=None)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Zkontroluj si `!help`.", delete_after=15)
    elif isinstance(error, commands.MemberNotFound): await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!**", delete_after=15)
    elif isinstance(error, commands.CheckFailure): pass 

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

class DynamicDownloadView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, emoji="📥", custom_id="persistent_install_main_btn")
    async def dl_btn(self, interaction, button):
        class DynamicRulesView(discord.ui.View):
            def __init__(self): super().__init__(timeout=None)
            @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, emoji="✅")
            async def agree(self, i2, b2):
                await i2.response.edit_message(content="<a:loading:123> Ověřuji profil...", view=None)
                try:
                    db = get_db(); d_id = str(i2.user.id); n = i2.user.display_name; u_role = "User"
                    if str((db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}])[0].get('setting_value', '')).lower() == 'false':
                        return await i2.edit_original_response(content="**Stahování je globálně vypnuto.**")
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
                            vers_data = get_db().table("software_versions").select("*").order("id").execute().data or []
                            for v in vers_data:
                                req = 2 if v['target_role'] == 'BT' else (3 if v['target_role'] == 'DEV_SA' else 1)
                                if u_lvl >= req: opts.append(discord.SelectOption(label=v['version_name'], value=str(v['id']), emoji="📦"))
                            if not opts: opts.append(discord.SelectOption(label="Nic není k dispozici", value="none"))
                            super().__init__(placeholder="Vyber verzi k instalaci...", options=opts)
                        async def callback(self, i3):
                            if self.values[0] == "none": return await i3.response.send_message("Nic tu není.", ephemeral=True)
                            await i3.response.send_message("<a:loading:123> Generuji odkaz...", ephemeral=True)
                            t = str(uuid.uuid4())
                            get_db().table("users").update({"download_token": t}).eq("discord_id", str(i3.user.id)).execute()
                            await i3.edit_original_response(content=f"**Odkaz připraven:**\n🔗 {os.environ.get('RENDER_EXTERNAL_URL', 'https://datacorebot.onrender.com')}/download/{t}?v={self.values[0]}\n*Platí jen pro Vás.*")
                    v_view = discord.ui.View()
                    v_view.add_item(DynamicVersionSelect(3 if 'SA' in u_role or 'DEV' in u_role else (2 if 'BT' in u_role else 1)))
                    await i2.edit_original_response(content="**Ověření úspěšné.** Vyberte soubor:", view=v_view)
                except Exception as e: await i2.edit_original_response(content=f"Chyba DB: {e}")
            @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, emoji="❌")
            async def disagree(self, i2, b2):
                await i2.response.edit_message(content="**Akce zrušena.**", view=None)
        await interaction.response.send_message("**Podmínky užití:**\n1. Zákaz úprav a šíření.\n2. Zámek na Váš PC (HWID).\n\nSouhlasíte?", view=DynamicRulesView(), ephemeral=True)

@bot.command()
@check_web_sa()
async def setup_download(ctx):
    embed = discord.Embed(title="📥 Projekt OIS IDPK - Instalace", description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a generování osobního odkazu ke stažení.", color=0x38bdf8)
    await ctx.send(embed=embed, view=DynamicDownloadView())
    try: await ctx.message.delete()
    except: pass

@bot.command()
async def auth(ctx):
    try: await ctx.message.delete()
    except: pass
    u = get_db().table("users").select("login_token").eq("discord_id", str(ctx.author.id)).execute().data
    if u and u[0].get('login_token'): await ctx.send(f"🛡️ {ctx.author.mention}, potvrďte přihlášení do aplikace:", view=AppAuthView(u[0]['login_token'], str(ctx.author.id), False), delete_after=60)
    else: msg = await ctx.send(f"❌ {ctx.author.mention} Nemáš čekající požadavek na přihlášení."); await asyncio.sleep(5); await msg.delete()

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", description="Seznam dostupných příkazů rozdělený podle oprávnění.", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné příkazy", value="`!auth` - Potvrzení přihlášení do aplikace.\n`!ping` - Odezva bota.\n`!help` - Tato nápověda.", inline=False)
    embed.add_field(name="🛡️ Správa (SM)", value="`!info [ID]` - Profil.\n`!db [ID]` - 2FA do webu.\n`!ban`/`!unban [ID]` - BANY.\n`!delete [ID]` - Blokace.\n`!perdelete [ID]` - Úplné smazání.\n`!register [ID]` - Vytvoří účet cizímu.\n`!message #kanál [text]` - Zpráva přes bota.\n`!dm @uzivatel [text]` - Soukromá zpráva.", inline=False)
    embed.add_field(name="⚙️ Administrace (web-sa)", value="`!setup_download` - Generuje instalátor.\n`!sm @uživatel` - Přidá/odebere roli SM.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx): 
    await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id: return await ctx.send(f"❌ Zadejte ID.")
    u = get_db().table("users").select("*").eq("discord_id", discord_id).execute().data
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
    await ctx.send(f"🔨 Uživateli `{discord_id}` byl udělen BAN.")

@bot.command()
@check_sm_role()
async def unban(ctx, discord_id: str):
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"🕊️ Uživateli `{discord_id}` byl zrušen BAN.")

@bot.command()
@check_sm_role()
async def db(ctx, discord_id: str):
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
    await ctx.send(f"☠️ Účet `{discord_id}` byl smazán (Soft Delete).")

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
        db.table("users").insert({ "app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": now_str }).execute()
        await ctx.send(f"✅ Úspěšně zaregistrován! App ID: **#{new_app_id}**.")

@bot.command()
@check_web_sa()
async def sm(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role: return await ctx.send("❌ Role `SM` neexistuje.")
    if role in member.roles: await member.remove_roles(role); await ctx.send(f"➖ Role **SM** odebrána.")
    else: await member.add_roles(role); await ctx.send(f"➕ Role **SM** přidělena.")

@bot.command()
@check_sm_role()
async def message(ctx, channel: discord.TextChannel, *, text: str):
    try: await channel.send(text); await ctx.send(f"✅ Odesláno.")
    except: await ctx.send("❌ Nemám oprávnění.")

@bot.command()
@check_sm_role()
async def dm(ctx, member: discord.Member, *, text: str):
    try: await member.send(embed=discord.Embed(title="Zpráva od administrace", description=text, color=0x38bdf8)); await ctx.send(f"✅ Odesláno.")
    except: await ctx.send("❌ Zablokované SZ.")

def run_web(): app.run(host='0.0.0.0', port=8080, use_reloader=False)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
