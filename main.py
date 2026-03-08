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
        body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; }
        .top-nav { background-color: rgba(15, 23, 42, 0.9); padding: 15px 40px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 100; }
        .logo { font-size: 24px; font-weight: 800; color: var(--blue-main); text-decoration: none; letter-spacing: 1px; display: flex; align-items: center; gap: 10px; }
        .nav-links a { color: var(--text-main); text-decoration: none; margin-left: 20px; font-weight: 500; transition: color 0.3s; }
        .nav-links a:hover { color: var(--blue-main); }
        .nav-links .admin-link { color: var(--text-muted); font-size: 12px; margin-left: 40px; border: 1px solid #334155; padding: 5px 10px; border-radius: 5px; }
        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        .btn { display: inline-block; background-color: var(--blue-main); color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; transition: 0.3s; }
        .btn:hover { background-color: var(--blue-hover); transform: translateY(-2px); }
        .btn-danger { background-color: var(--danger); } .btn-danger:hover { background-color: #dc2626; }
        .btn-warning { background-color: var(--warning); color: #000; } .btn-warning:hover { background-color: #d97706; }
        .btn-success { background-color: var(--success); } .btn-success:hover { background-color: #059669; }
        .btn-dark { background-color: #334155; color: white; } .btn-dark:hover { background-color: #475569; }
        input[type="text"], input[type="number"], input[type="password"], input[type="url"], textarea, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; box-sizing: border-box; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background-color: var(--bg-panel); border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background-color: #0f172a; color: var(--blue-main); font-weight: 600; text-transform: uppercase; font-size: 13px; }
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
<body>{% block layout %}{% endblock %}</body></html>
"""

PUBLIC_LAYOUT = """<nav class="top-nav"><a href="/" class="logo"><img src="{{ logo_male }}" alt="Logo" style="height: 30px; width: auto; border-radius: 4px;">OIS IDPK</a><div class="nav-links"><a href="/">Domů</a><a href="/download">Download</a><a href="/team">Náš Tým</a><a href="/dashboard" class="admin-link">Dashboard 🔒</a></div></nav><div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}{% block content %}{% endblock %}</div>"""

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
            <a href="/dashboard/app_settings" class="sidebar-link"><i class="fas fa-cog"></i> Nastavení Aplikace</a>
            <a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-cloud-download-alt"></i> Správa Stahování</a>
            <a href="/dashboard/pending_roles" class="sidebar-link" style="color: #10b981;"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a>
            <a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a>
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a>
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
        {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}{% block content %}{% endblock %}
    </div>
</div>
<div class="modal-overlay" id="editModal"><div class="modal" id="modalContent"><div style="width: 100%;"><h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;"><span><i class="fas fa-user"></i> Profil <span id="modalAppId" style="color: var(--text-muted); font-size: 16px;"></span></span><span id="modalStatusDot" style="font-size: 14px;"></span></h2><div class="profile-grid"><div class="profile-card"><div class="profile-stat">Členem Discordu od:</div><div class="profile-val" id="profJoined"><i class="fas fa-spinner fa-spin"></i> Načítání...</div><div class="profile-stat" style="margin-top: 10px;">Datum registrace v DB:</div><div class="profile-val" id="profRegistered"></div><div class="profile-stat" style="margin-top: 10px;">Aktivita v aplikaci (Status):</div><div class="profile-val" id="profAppStatus" style="color: #64748b;"><i>Připravuje se...</i></div><div id="profStats"></div><div class="profile-stat" style="margin-top: 10px;">Přístup do webové DB:</div><div class="profile-val" id="profDbAccess"></div></div><div class="profile-card" style="max-height: 250px; overflow-y: auto;"><div class="profile-stat" style="margin-bottom: 10px; font-weight:bold; color: var(--blue-main);">Historie stahování:</div><table class="dl-table" style="width: 100%; margin-top: 0; background: transparent; border-radius: 0;"><tbody id="profDownloads"><tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr></tbody></table></div></div><form action="/dashboard/edit_user" method="POST" style="border-top: 1px solid #334155; padding-top: 15px;"><input type="hidden" name="discord_id" id="modalDiscordId"><label>Herní Nick:</label><input type="text" name="nick" id="modalNick" required><label>Role:</label><div class="checkbox-group"><label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label><label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label><label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label><label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label></div><label>HWID (Zámek na PC):</label><input type="text" name="hwid" id="modalHwid" placeholder="Pro odblokování smažte text zde"><div style="background-color: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 5px; border: 1px solid var(--blue-main); margin-bottom: 15px;"><label style="cursor: pointer; font-weight: bold; color: var(--blue-main); margin: 0; display: flex; align-items: center; gap: 10px;"><input type="checkbox" name="dashboard_access" id="modalDashboardAccess" value="True" style="width: auto; margin: 0;">Povolit přístup do Dashboardu (2FA ověření)</label></div><div id="activeActions"><div style="display: flex; gap: 10px; margin-top: 10px;"><button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit úpravy</button><button type="submit" name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;"><i class="fas fa-ban"></i> Dát BAN</button><button type="submit" name="action" value="unban" id="btnUnban" class="btn btn-success" style="flex: 1; display: none;"><i class="fas fa-check"></i> Un-BAN</button></div><div style="margin-top: 15px; border-top: 1px solid #334155; padding-top: 15px;"><button type="submit" name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Smazat účet? (Zablokuje ID, umožní novou registraci)')"><i class="fas fa-trash"></i> Smazat účet (Soft Delete)</button></div></div><div id="deletedActions" style="display: none; margin-top: 20px; border-top: 1px solid #334155; padding-top: 15px;"><p style="color: var(--danger); font-weight: bold; text-align: center; margin-top: 0;">Tento účet je smazaný.</p><div style="display: flex; gap: 10px;"><button type="submit" name="action" value="restore" class="btn btn-success" style="flex: 1;"><i class="fas fa-undo"></i> Obnovit účet</button><button type="submit" name="action" value="hard_delete" class="btn btn-dark" style="flex: 1;" onclick="return confirm('PERMANENTNÍ SMAZÁNÍ: Tato akce kompletně vymaže veškerá data o tomto uživateli. Pokračovat?')"><i class="fas fa-skull"></i> Smazat permanentně</button></div></div></form><button class="btn" onclick="closeModal()" style="background: transparent; color: var(--text-muted); width: 100%; margin-top: 10px; border: 1px solid #334155;">Zrušit</button></div></div></div>
<script>
    function openModal(app_id, discord_id, nick, roles, hwid, is_banned, is_deleted, dashboard_access, registered_at) {
        document.getElementById('editModal').style.display = 'flex'; document.getElementById('modalAppId').innerText = "#" + app_id; document.getElementById('modalDiscordId').value = discord_id; document.getElementById('modalNick').value = nick; document.getElementById('modalHwid').value = hwid === 'None' ? '' : hwid; document.getElementById('profRegistered').innerText = registered_at && registered_at !== 'None' ? registered_at : 'Neznámé (Starý účet)';
        document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True'); 
        document.querySelectorAll('input[name="roles"]').forEach(cb => cb.checked = false); roles.split(',').forEach(r => { let el = document.querySelector(`input[name="roles"][value="${r.trim()}"]`); if(el) el.checked = true; });
        if (is_deleted === 'True') { document.getElementById('activeActions').style.display = 'none'; document.getElementById('deletedActions').style.display = 'block'; } else { document.getElementById('activeActions').style.display = 'block'; document.getElementById('deletedActions').style.display = 'none'; if (is_banned === 'True') { document.getElementById('btnBan').style.display = 'none'; document.getElementById('btnUnban').style.display = 'block'; } else { document.getElementById('btnBan').style.display = 'block'; document.getElementById('btnUnban').style.display = 'none'; } }
        document.getElementById('profJoined').innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('modalStatusDot').innerHTML = ''; document.getElementById('profDownloads').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>';
        document.getElementById('profAppStatus').innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('profStats').innerHTML = '';
        fetch('/api/get_profile_data/' + discord_id).then(r => r.json()).then(data => { 
            document.getElementById('profJoined').innerText = data.joined_at; document.getElementById('modalStatusDot').innerHTML = data.status; document.getElementById('profAppStatus').innerHTML = data.app_status; document.getElementById('profStats').innerHTML = data.stats;
            let dlHtml = ""; if(data.downloads && data.downloads.length > 0) { data.downloads.forEach(d => { dlHtml += `<tr><td style="color: var(--blue-main);"><b>${d.version_name}</b></td><td style="color: var(--text-muted);">${d.downloaded_at}</td></tr>`; }); } else { dlHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím nestáhl žádný soubor.</td></tr>"; } document.getElementById('profDownloads').innerHTML = dlHtml; 
        });
    }
    function closeModal() { document.getElementById('editModal').style.display = 'none'; }
</script>
"""

HTML_HOME = """<div style="text-align: center; padding: 50px 0;"><img src="{{ logo_velke }}" alt="DataCoreBot Logo" style="max-width: 450px; width: 100%; height: auto; margin-bottom: 20px; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5));"><p style="font-size: 1.2em; color: var(--text-muted); max-width: 600px; margin: 0 auto 30px auto;">Moderní, rychlý a bezpečný software s nejlepším zabezpečením.</p><a href="/download" class="btn" style="font-size: 18px; padding: 15px 30px; border-radius: 30px;"><i class="fas fa-download"></i> Získat Software</a></div>"""

HTML_LOGIN = """<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-top: 4px solid var(--blue-main);"><h2 style="text-align: center; color: var(--blue-main); margin-top: 0;"><i class="fas fa-lock"></i> Dashboard 2FA</h2><div style="background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--danger); padding: 12px; margin-bottom: 20px; border-radius: 0 5px 5px 0;"><p style="color: var(--danger); margin: 0; font-size: 13px; font-weight: 800; text-transform: uppercase;"><i class="fas fa-shield-alt"></i> Zabezpečená zóna</p><p style="color: var(--text-muted); margin: 5px 0 0 0; font-size: 12px; line-height: 1.4;">Tato databáze je přísně vyhrazena <b>pouze pro administrátory a pověřené správce</b> projektu. Běžní uživatelé sem nemají přístup. Každý pokus o neoprávněné přihlášení je monitorován a logován.</p></div><p style="color: var(--text-muted); text-align: center; font-size: 13px;">Pro přístup do systému zadejte své <b>Discord ID</b>.</p><form method="POST" action="/login_request"><label style="font-weight: bold; font-size: 12px; color: var(--text-muted);">VAŠE DISCORD ID</label><input type="text" name="discord_id" placeholder="Např. 123456789012345678" required><button type="submit" class="btn" style="width: 100%; margin-top: 10px;"><i class="fab fa-discord"></i> Odeslat žádost o přihlášení</button></form></div>"""

HTML_WAIT_AUTH = """<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; border-top: 4px solid var(--warning);"><h2 style="color: var(--warning); margin-top: 0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2><p style="color: var(--text-main); font-size: 16px;">Byla Vám odeslána soukromá zpráva na Discord.</p><p style="color: var(--text-muted); font-size: 14px;">Zkontrolujte si aplikaci Discord a klikněte na tlačítko <b>Ověřit přístup</b>. Tato stránka se poté automaticky přesměruje.</p></div><script>setInterval(() => { fetch('/api/check_auth/{{ discord_id }}').then(r => r.json()).then(data => { if(data.status === 'approved') { window.location.href = '/dashboard'; } else if(data.status === 'rejected') { window.location.href = '/dashboard'; } }); }, 2000);</script>"""

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
        <p style="color: var(--text-muted); font-size: 14px;">Globální vypínač celé PC aplikace.</p>
        <form action="/dashboard/toggle_software" method="POST" style="margin-top: 20px;">
            <input type="hidden" name="new_status" value="{{ 'False' if soft_enabled else 'True' }}">
            <button type="submit" class="btn {{ 'btn-danger' if soft_enabled else 'btn-success' }}" style="width: 100%; font-size: 16px;"><i class="fas fa-power-off"></i> {{ 'VYPNOUT SOFTWARE GLOBÁLNĚ' if soft_enabled else 'ZAPNOUT SOFTWARE' }}</button>
        </form>
    </div>

    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-cloud-download-alt"></i> Status Stahování</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if enabled else 'var(--danger)' }}; text-shadow: 0 0 15px {{ 'rgba(16, 185, 129, 0.5)' if enabled else 'rgba(239, 68, 68, 0.5)' }};">
            <i class="fas {{ 'fa-check-circle' if enabled else 'fa-ban' }}"></i>
        </div>
        <p style="color: var(--text-muted); font-size: 14px;">Vypínač instalačního procesu přes Discord bota.</p>
        <form action="/dashboard/toggle_downloads" method="POST" style="margin-top: 20px;">
            <input type="hidden" name="new_status" value="{{ 'False' if enabled else 'True' }}">
            <input type="hidden" name="return_to" value="app_settings">
            <button type="submit" class="btn {{ 'btn-danger' if enabled else 'btn-success' }}" style="width: 100%; font-size: 16px;"><i class="fas fa-power-off"></i> {{ 'ZAKÁZAT STAHOVÁNÍ' if enabled else 'POVOLIT STAHOVÁNÍ' }}</button>
        </form>
    </div>
</div>
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
                    <form action="/dashboard/delete_version" method="POST" style="display:inline;">
                        <input type="hidden" name="version_id" value="{{ v.get('id', '') }}">
                        <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat tuto verzi ze stahování?')"><i class="fas fa-trash"></i></button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Zatím nebyly přidány žádné soubory ke stažení.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
"""

HTML_TEAM = """
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

HTML_DASHBOARD_MAIN = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">{{ title }}</h2>
    <div style="background: var(--bg-panel); padding: 10px 20px; border-radius: 8px; font-weight: bold; border: 1px solid #334155;">
        Celkem uživatelů: <span style="color: var(--blue-main);">{{ users|length }}</span>
    </div>
</div>
<div style="overflow-x: auto;">
    <table>
        <tr>
            <th>App ID</th>
            <th>Discord ID</th>
            <th>Nick</th>
            <th>Role</th>
            <th>Zaregistrován</th>
            <th>Status</th>
            <th>Akce</th>
        </tr>
        {% for user in users %}
        <tr style="opacity: {{ '0.5' if user.get('is_deleted') else '1' }};">
            <td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td>
            <td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td>
            <td><strong>{{ user.get('nick', '') }}</strong></td>
            <td>
                {% set role_list = user.get('role').split(',') if user.get('role') else ['User'] %}
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
            <td style="color: var(--text-muted); font-size: 13px;">
                {{ user.get('registered_at', 'Neznámé') if user.get('registered_at', 'Neznámé') != '' else 'Neznámé' }}
            </td>
            <td>
                {% if user.get('is_deleted') %}
                    <span style="color: var(--danger); font-weight: bold;"><i class="fas fa-skull"></i> Smazán</span>
                {% elif user.get('is_banned') %}
                    <span style="color: var(--warning); font-weight: bold;"><i class="fas fa-ban"></i> BANNED</span>
                {% else %}
                    <span style="color: var(--success);"><i class="fas fa-check-circle"></i> Aktivní</span>
                {% endif %}
            </td>
            <td>
                <button class="btn" style="padding: 6px 12px; font-size: 12px;" onclick="openModal('{{ user.get('app_id', '') }}', '{{ user.get('discord_id', '') }}', '{{ user.get('nick', '') }}', '{{ user.get('role', 'User') }}', '{{ user.get('hwid', '') }}', '{{ user.get('is_banned', False) }}', '{{ user.get('is_deleted', False) }}', '{{ user.get('dashboard_access', False) }}', '{{ user.get('registered_at', '') }}')"><i class="fas fa-cog"></i> Profil</button>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="7" style="text-align: center; padding: 30px; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td></tr>
        {% endfor %}
    </table>
</div>
"""

# ==========================================
# 2. FLASK ROUTES, API & LOGGING
# ==========================================

def get_db():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

async def async_send_log_to_discord(title, description, color=0x38bdf8):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(prague_tz))
            try: await channel.send(embed=embed)
            except: pass
            break

def send_log_from_flask(title, description, color=0x38bdf8):
    if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(async_send_log_to_discord(title, description, color), bot.loop)

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
    if request.path.startswith('/dashboard/') and request.path != '/dashboard/wait_auth':
        if not session.get('logged_in'):
            return redirect(url_for('dashboard_main'))
            
    if request.path.startswith('/dashboard') and request.path != '/dashboard/wait_auth' and session.get('logged_in'):
        discord_id = session.get('discord_id')
        if discord_id == 'admin': return 
        if discord_id:
            try:
                db = get_db()
                if db:
                    user = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                    if not user or not user[0].get("dashboard_access") or user[0].get("is_banned") or user[0].get("is_deleted"):
                        session.clear(); flash('Váš přístup do administrace byl zablokován, zrušen nebo Váš účet neexistuje.', 'error'); return redirect(url_for('dashboard_main'))
            except Exception as e: pass

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

# ---------------------------------------------------------
# API PRO ELECTRON SOFTWARE
# ---------------------------------------------------------

@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_status():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
            if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')) == 'False':
                return _cors_jsonify({"status": "disabled", "message": "SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA)."})
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
    if not db: return _cors_jsonify({"status": "error", "message": "Chyba databáze."})
    
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')) == 'False':
            return _cors_jsonify({"status": "error", "message": "OMLOUVÁME SE, SOFTWARE JE NYNÍ DOČASNĚ VYPNUT (ÚDRŽBA)."})
    except: pass
    
    try:
        user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},nick.ilike.{identifier}").execute()
        if not user_resp.data and identifier.isdigit():
            user_resp = db.table("users").select("*").eq("app_id", int(identifier)).execute()
            
        if not user_resp.data: return _cors_jsonify({"status": "error", "message": "Uživatel nenalezen. Zkontrolujte App ID nebo Nick."})
            
        user = user_resp.data[0]
        if user.get("is_banned"): return _cors_jsonify({"status": "banned", "message": "Tento účet má zakázaný přístup (BAN)."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán administrátorem."})
            
        db_hwid = user.get("hwid")
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "" and str(db_hwid) != req_hwid:
            return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID: Tento účet je vázán na jiný počítač."})
            
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", user.get("discord_id")).execute()
        
        async def send():
            try:
                u = bot.get_user(int(user.get("discord_id"))) or await bot.fetch_user(int(user.get("discord_id")))
                if u:
                    embed = discord.Embed(title="🛡️ Bezpečnostní ověření - Aplikace", description=f"Byl zaznamenán pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPokud jste to Vy, potvrďte přístup kliknutím na tlačítko níže.", color=0x38bdf8)
                    await u.send(embed=embed, view=AppAuthView(token, user.get("discord_id"), is_dm=True))
            except: pass
        if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
        
        return _cors_jsonify({"status": "waiting", "token": token, "discord_id": user.get("discord_id"), "nick": user.get("nick")})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error", "message": "Účet nenalezen."})
        user = user_resp.data[0]
        
        if user.get("is_banned"): return _cors_jsonify({"status": "banned", "message": "Máte udělený BAN."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "error", "message": "Účet byl smazán."})
            
        db_token = user.get("login_token")
        if db_token == "approved":
            db_hwid = user.get("hwid")
            if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
                db.table("users").update({"hwid": req_hwid, "login_token": ""}).eq("discord_id", discord_id).execute()
            else:
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "approved", "app_id": user.get("app_id"), "nick": user.get("nick")})
            
        elif db_token == "rejected":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "rejected", "message": "Přístup zamítnut uživatelem na Discordu."})
            
        return _cors_jsonify({"status": "waiting"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')) == 'False':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA)."})
        
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "rejected", "message": "Tento účet již v databázi neexistuje."})
        
        user = user_resp.data[0]
        if user.get("is_banned"): return _cors_jsonify({"status": "banned", "message": "Tento účet má zakázaný přístup (BAN)."})
        if user.get("is_deleted"): return _cors_jsonify({"status": "rejected", "message": "Tento účet byl smazán administrátorem."})
        
        db_hwid = user.get("hwid")
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "" and str(db_hwid) != req_hwid:
            return _cors_jsonify({"status": "hwid_error", "message": "ZÁMEK HWID: Váš počítač nesouhlasí s profilem v databázi."})
            
        return _cors_jsonify({"status": "approved", "nick": user.get("nick")})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_ping', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_ping():
    if request.method == 'OPTIONS': return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.json
    discord_id = str(data.get("discord_id", ""))
    action = data.get("action", "ping") 
    session_time = int(data.get("session_time", 0)) 
    
    db = get_db()
    if not db: return _cors_jsonify({"status": "error"})
    
    try:
        now_str = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M:%S")
        user_resp = db.table("users").select("launch_count, total_time, is_banned, is_deleted").eq("discord_id", discord_id).execute()
        if not user_resp.data: return _cors_jsonify({"status": "error"})
        
        u = user_resp.data[0]
        if u.get("is_banned") or u.get("is_deleted"): return _cors_jsonify({"status": "force_logout"})
        
        updates = {"last_active": now_str, "is_online": True}
        
        if action == "start": 
            l_count = u.get("launch_count")
            if not isinstance(l_count, int): l_count = 0
            updates["launch_count"] = l_count + 1
        elif action == "stop": 
            updates["is_online"] = False
        
        if session_time > 0: 
            t_time = u.get("total_time")
            if not isinstance(t_time, int): t_time = 0
            updates["total_time"] = t_time + session_time
            
        db.table("users").update(updates).eq("discord_id", discord_id).execute()
        return _cors_jsonify({"status": "ok"})
    except Exception as e:
        print(f"Ping Error: {e}", flush=True)
        return _cors_jsonify({"status": "error", "message": str(e)})


# ---------------------------------------------------------
# DISCORD TLAČÍTKA A FLASK STRÁNKY
# ---------------------------------------------------------
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
                await interaction.edit_original_response(content="✅ **Přístup do administrace byl úspěšně schválen!**\nNyní můžete zavřít tuto zprávu a vrátit se do prohlížeče.", view=None)
                await async_send_log_to_discord("🔐 Přihlášení do Dashboardu", f"Uživatel s ID `{self.discord_id}` se úspěšně přihlásil do webové administrace přes 2FA.", 0x10b981)
            else: await interaction.edit_original_response(content="❌ **Platnost požadavku vypršela nebo je neplatný.**", view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db = get_db()
        if db: db.table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Žádost o přihlášení zamítnuta.**", view=None)

class AppAuthView(discord.ui.View):
    def __init__(self, token, discord_id, is_dm=True):
        super().__init__(timeout=300)
        self.token = token; self.discord_id = discord_id; self.is_dm = is_dm
        btn_verify = discord.ui.Button(label="Ano, ověřit (Jsem to já)", style=discord.ButtonStyle.success, emoji="✅")
        btn_verify.callback = self.verify_btn
        self.add_item(btn_verify)
        if self.is_dm:
            btn_reject = discord.ui.Button(label="Zamítnout (Nejsem to já)", style=discord.ButtonStyle.danger, emoji="❌")
            btn_reject.callback = self.decline_btn
            self.add_item(btn_reject)

    async def verify_btn(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.discord_id): return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.defer()
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", self.discord_id).execute().data
            if user and user[0].get("login_token") == self.token:
                db.table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
                await interaction.edit_original_response(content="✅ **Přihlášení do softwaru schváleno!**", view=None, embed=None)
                await async_send_log_to_discord("🖥️ Přihlášení do Aplikace", f"Uživatel s ID `{self.discord_id}` se úspěšně ověřil a přihlásil do softwaru.", 0x10b981)
            else: await interaction.edit_original_response(content="❌ **Platnost požadavku vypršela nebo je neplatný.**", view=None, embed=None)
        if not self.is_dm:
            await asyncio.sleep(3)
            try: await interaction.message.delete()
            except: pass

    async def decline_btn(self, interaction: discord.Interaction):
        await interaction.response.defer()
        db = get_db()
        if db: db.table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Přihlášení zamítnuto.**", view=None, embed=None)

@app.route('/')
def home(): return render_public(HTML_HOME)

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
def secure_download(token): return render_public("Stránka byla zrušena, použijte Discord panel.")
@app.route('/team')
def team(): 
    try: team_members = get_db().table("team").select("*").execute().data if get_db() else []
    except: team_members = []
    return render_public(HTML_TEAM, team=team_members)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == os.environ.get("ADMIN_PASSWORD", "admin"):
            session['logged_in'] = True; session['discord_id'] = 'admin'
            return redirect(url_for('dashboard_main'))
    if not session.get('logged_in'): return render_public(HTML_LOGIN)
    users_data = []
    try:
        if get_db():
            query = get_db().table("users").select("*")
            filter_type = request.args.get('filter')
            if filter_type == 'banned': query = query.eq("is_banned", True).eq("is_deleted", False)
            elif filter_type == 'deleted': query = query.eq("is_deleted", True)
            elif filter_type: query = query.ilike("role", f"%{filter_type}%").eq("is_deleted", False)
            else: query = query.eq("is_deleted", False).order("app_id")
            users_data = query.execute().data
    except Exception as e: flash(f"Chyba při načítání dat: {e}", "error")
    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title="Přehled uživatelů")

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
                        if u: await u.send(embed=discord.Embed(title="🔐 Bezpečnostní ověření - Dashboard", description="Byl zaznamenán pokus o přihlášení do administračního panelu Projektu OIS IDPK z prohlížeče.\n\nPokud jste to Vy, potvrďte přístup kliknutím na tlačítko níže.", color=0x38bdf8), view=DashboardAuthView(token, discord_id))
                    except: pass
                if bot.loop and bot.loop.is_running(): asyncio.run_coroutine_threadsafe(send(), bot.loop)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            else: flash('Účet neexistuje, nemá povolený přístup, nebo byl zablokován.', 'error')
        except Exception as e: flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): return render_public(HTML_WAIT_AUTH, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
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
    return {"status": "waiting"}

@app.route('/api/get_profile_data/<discord_id>')
def get_profile_data(discord_id):
    if not session.get('logged_in'): return {"joined_at": "Neznámé", "status": "Neznámý", "downloads": []}
    joined_at = "Neznámé"; status = "Neznámý"; member = None
    if bot.guilds:
        for g in bot.guilds:
            member = g.get_member(int(discord_id))
            if member: break
    if member:
        joined_at = member.joined_at.strftime("%d.%m.%Y") if member.joined_at else "Neznámé"
        status_map = {"online": "🟢 Online", "offline": "⚫ Offline", "idle": "🌙 Nečinný", "dnd": "🔴 Nerušit"}
        status = status_map.get(str(member.status), str(member.status))
        
    dls = []
    app_status_html = "<span style='color: #64748b;'><i>Neaktivní</i></span>"
    stats_html = ""
    db = get_db()
    if db:
        try:
            dls = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data
            db_user = db.table("users").select("last_active, is_online, launch_count, total_time").eq("discord_id", discord_id).execute().data
            if db_user:
                u = db_user[0]
                is_online = u.get("is_online", False)
                last_active_str = u.get("last_active") or ""
                launch_count = u.get("launch_count")
                if not isinstance(launch_count, int): launch_count = 0
                total_time = u.get("total_time")
                if not isinstance(total_time, int): total_time = 0
                
                if is_online and last_active_str:
                    try:
                        last_dt = datetime.strptime(last_active_str, "%d.%m.%Y %H:%M:%S")
                        if (datetime.now(prague_tz).replace(tzinfo=None) - last_dt).total_seconds() > 120:
                            is_online = False
                            db.table("users").update({"is_online": False}).eq("discord_id", discord_id).execute()
                    except: pass
                
                m, s = divmod(total_time, 60)
                h, m = divmod(m, 60)
                formatted_time = f"{h}h {m}m {s}s"
                
                if is_online: app_status_html = '<span style="color: var(--success); font-weight:bold;">🟢 Aktivní právě teď</span>'
                else: app_status_html = f'<span style="color: var(--danger);">🔴 Offline</span> (Naposledy: {last_active_str or "Nikdy"})'
                stats_html = f"<div style='margin-top:10px; font-size:12px; color:var(--text-muted); border-top: 1px solid #334155; padding-top: 10px;'><div><b>Počet spuštění:</b> {launch_count}x</div><div style='margin-top:5px;'><b>Celkový čas:</b> {formatted_time}</div></div>"
        except Exception as e:
            print(f"Profile API Error: {e}", flush=True)
            
    return {"joined_at": joined_at, "status": status, "app_status": app_status_html, "stats": stats_html, "downloads": dls}

@app.route('/dashboard/app_settings', methods=['GET'])
def dashboard_app_settings():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    enabled = True; soft_enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").in_("setting_key", ["downloads_enabled", "software_enabled"]).execute()
            if set_resp.data:
                for s in set_resp.data:
                    if s.get('setting_key') == 'downloads_enabled' and str(s.get('setting_value')) == 'False': enabled = False
                    if s.get('setting_key') == 'software_enabled' and str(s.get('setting_value')) == 'False': soft_enabled = False
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_APP_SETTINGS, enabled=enabled, soft_enabled=soft_enabled)

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main')) 
    versions = []; enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute()
            if set_resp.data and str(set_resp.data[0].get('setting_value')) == 'False': enabled = False
            versions = db.table("software_versions").select("*").order("id").execute().data
    except Exception as e: flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled)

@app.route('/dashboard/toggle_downloads', methods=['POST'])
def toggle_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); new_status = request.form.get("new_status")
    return_to = request.form.get("return_to", "downloads")
    if db:
        try: db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute(); flash('Status stahování byl změněn.', 'success')
        except Exception as e: flash(f"Chyba: {e}", "error")
    if return_to == 'app_settings': return redirect(url_for('dashboard_app_settings'))
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/toggle_software', methods=['POST'])
def toggle_software():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db(); new_status = request.form.get("new_status")
    if db:
        try:
            db.table("settings").update({"setting_value": new_status}).eq("setting_key", "software_enabled").execute()
            flash('Globální stav softwaru byl změněn!', 'success')
            send_log_from_flask("🚨 Kill-Switch", f"Software byl přes administraci **{'ZAPNUT' if new_status == 'True' else 'VYPNUT'}**.", 0xef4444 if new_status == 'False' else 0x10b981)
        except Exception as e: flash(f"Chyba: Zkontrolujte, zda máte vytvořený řádek 'software_enabled' v tabulce settings! ({e})", "error")
    return redirect(url_for('dashboard_app_settings'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): 
    try: data = get_db().table("pending_roles").select("*").order("id").execute().data if get_db() else []
    except: data = []
    return render_dashboard(HTML_PENDING_ROLES, pending=data)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids(): 
    try: data = get_db().table("users").select("*").order("app_id").execute().data if get_db() else []
    except: data = []
    return render_dashboard(HTML_IDS, users=data)

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page(): 
    try: data = get_db().table("team").select("*").execute().data if get_db() else []
    except: data = []
    return render_dashboard(HTML_TEAM_ADD, team=data)

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

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# ==========================================
# 3. DISCORD BOT & INTERAKTIVNÍ TLAČÍTKA
# ==========================================
intents = discord.Intents.default()
intents.message_content = True; intents.members = True; intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)
bot.remove_command('help')
bot.invites_cache = {}

@bot.event
async def on_ready():
    bot.add_view(DownloadView())
    bot.add_view(RulesView())
    for guild in bot.guilds:
        try: bot.invites_cache[guild.id] = await guild.invites()
        except: pass
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)

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
    await async_send_log_to_discord("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum připojení:** {datetime.now(prague_tz).strftime('%d.%m.%Y %H:%M')}{link_info}", 0x10b981)

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
        await interaction.response.edit_message(content="❌ Akce zrušena. Účet smazán nebyl.", view=None, embed=None)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Zkontroluj si `!help`.", delete_after=15)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!**", delete_after=15)
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

@bot.command(aliases=['overit', 'verify'])
async def auth(ctx):
    db = get_db()
    if not db: return
    discord_id = str(ctx.author.id)
    user_data = db.table("users").select("login_token, nick").eq("discord_id", discord_id).execute().data
    
    if not user_data:
        msg = await ctx.send(f"❌ {ctx.author.mention} Nejsi zaregistrován v databázi.")
        await asyncio.sleep(10)
        try: await msg.delete(); await ctx.message.delete()
        except: pass
        return
        
    token = user_data[0].get("login_token")
    if not token or token in ["approved", "rejected"]:
        msg = await ctx.send(f"ℹ️ {ctx.author.mention} Aktuálně nemáš žádný čekající požadavek na přihlášení od aplikace.")
        await asyncio.sleep(10)
        try: await msg.delete(); await ctx.message.delete()
        except: pass
        return
        
    embed = discord.Embed(title="🛡️ Ruční ověření přihlášení", description=f"Potvrzuješ přihlášení do softwaru jako **{user_data[0].get('nick')}**?\n\n*Tato zpráva a tlačítko funguje pouze pro tebe.*", color=0x38bdf8)
    await ctx.send(embed=embed, view=AppAuthView(token, discord_id, is_dm=False))
    try: await ctx.message.delete()
    except: pass

@bot.command()
async def register(ctx, target_id: str = None):
    db = get_db()
    if not db: return
    if target_id:
        is_admin = discord.utils.get(ctx.author.roles, name="web-sa") or discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator
        if not is_admin: return await ctx.send(f"❌ {ctx.author.mention} Nemáš oprávnění registrovat cizí účty.")
        discord_id = target_id
        target_member = ctx.guild.get_member(int(discord_id)) if discord_id.isdigit() else None
        nick = target_member.display_name if target_member else f"Uživatel {discord_id}"
    else:
        discord_id = str(ctx.author.id); nick = ctx.author.display_name; target_member = ctx.author
        
    now_str = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M")
    check = db.table("users").select("*").eq("discord_id", discord_id).execute()
    if len(check.data) > 0:
        if check.data[0].get('is_banned'): return await ctx.send("❌ Nemůžete se zaregistrovat, tento účet má BAN.")
        elif check.data[0].get('is_deleted'):
            highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
            new_app_id = highest_id_resp.data[0]["app_id"] + 1 if highest_id_resp.data else 1000
            db.table("users").update({"app_id": new_app_id, "nick": nick, "is_deleted": False, "deleted_at": "", "registered_at": now_str}).eq("discord_id", discord_id).execute()
            await ctx.send(f"✅ Smazaný účet byl úspěšně obnoven! Nové App ID je **#{new_app_id}**.")
            if target_member and isinstance(target_member, discord.Member): await update_member_roles(target_member, check.data[0].get('role', 'User'))
        else: await ctx.send(f"ℹ️ {'Tento uživatel' if target_id else 'Vy'} už {'je' if target_id else 'jste'} v databázi zaregistrován!")
    else:
        highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
        new_app_id = highest_id_resp.data[0]["app_id"] + 1 if highest_id_resp.data else 1000
        novy = { "app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": now_str }
        db.table("users").insert(novy).execute()
        await ctx.send(f"✅ Úspěšně zaregistrován do databáze! Vaše App ID je **#{new_app_id}**.")

@bot.command(name="sm")
@check_web_sa()
async def sm_cmd(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role: return await ctx.send(f"❌ Role `SM` neexistuje.")
    if role in member.roles:
        await member.remove_roles(role); await ctx.send(f"➖ Role **SM** odebrána.")
    else:
        await member.add_roles(role); await ctx.send(f"➕ Role **SM** přidělena.")

@bot.command(name="db")
@check_sm_role()
async def db_cmd(ctx, discord_id: str):
    db = get_db(); 
    if not db: return
    user_data = db.table("users").select("dashboard_access, nick").eq("discord_id", discord_id).execute().data
    if not user_data: return await ctx.send(f"❌ Nenalezen.")
    new_status = not user_data[0].get("dashboard_access", False)
    db.table("users").update({"dashboard_access": new_status}).eq("discord_id", discord_id).execute()
    await ctx.send(f"⚙️ Přístup DB: **{'POVOLEN ✅' if new_status else 'ODEBRÁN ❌'}**.")

@bot.command(name="ban")
@check_sm_role()
async def ban_cmd(ctx, discord_id: str):
    db = get_db()
    if not db: return
    user_data = db.table("users").select("nick").eq("discord_id", discord_id).execute().data
    if not user_data: return await ctx.send(f"❌ Nenalezen.")
    db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"🔨 BAN udělen.")

@bot.command(name="unban")
@check_sm_role()
async def unban_cmd(ctx, discord_id: str):
    db = get_db()
    if not db: return
    db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"🕊️ BAN zrušen.")

@bot.command(name="delete")
@check_sm_role()
async def delete_cmd(ctx, discord_id: str):
    db = get_db()
    if not db: return
    now = datetime.now(prague_tz).strftime("%d.%m.%Y %H:%M")
    db.table("users").update({"is_deleted": True, "deleted_at": now, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"☠️ Smazáno.")

@bot.command(name="perdelete")
@check_sm_role()
async def perdelete_cmd(ctx, discord_id: str):
    embed = discord.Embed(title="⚠️ Varování: Permanentní smazání", description=f"Opravdu chceš nevratně smazat účet `{discord_id}`?", color=0xef4444)
    await ctx.send(embed=embed, view=PerDeleteConfirm(discord_id, ctx.author.id))

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - IDPK OIS PROJEKT", description="Jsem systémový bot.", color=0x38bdf8)
    embed.add_field(name="🌍 Příkazy", value="`!register`, `!auth`, `!help`, `!ping`, `!info`, `!verze`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id: return await ctx.send(f"❌ Zadejte ID.")
    db = get_db()
    user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not user: return await ctx.send(f"❌ Nenalezen.")
    u = user[0]
    embed = discord.Embed(title=f"Uživatel: {u.get('nick')}", color=0x38bdf8)
    embed.add_field(name="ID", value=u.get('discord_id'), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def verze(ctx):
    db = get_db()
    if not db: return
    v_resp = db.table("software_versions").select("*").order("id").execute().data
    if not v_resp: return await ctx.send("Aktuálně nejsou v databázi k dispozici žádné verze.")
    embed = discord.Embed(title="📦 Dostupné verze aplikace", color=0x10b981)
    for v in v_resp:
        role_text = "Všichni (User)"
        if v.get('target_role') == 'BT': role_text = "BT, DEV, SA"
        if v.get('target_role') == 'DEV_SA': role_text = "DEV, SA"
        embed.add_field(name=v.get('version_name'), value=f"Dostupnost: **{role_text}**", inline=False)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token: bot.run(token)
