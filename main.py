import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context
from threading import Thread
from supabase import create_client
from datetime import datetime
import asyncio
import uuid
import urllib.request
import re

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 

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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a; 
            --bg-panel: #1e293b; 
            --blue-main: #38bdf8; 
            --blue-hover: #0284c7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --danger: #ef4444;
            --success: #10b981;
            --warning: #f59e0b;
        }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; }
        
        .top-nav { background-color: rgba(15, 23, 42, 0.9); padding: 15px 40px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 100; }
        .logo { font-size: 24px; font-weight: 800; color: var(--blue-main); text-decoration: none; letter-spacing: 1px; }
        .nav-links a { color: var(--text-main); text-decoration: none; margin-left: 20px; font-weight: 500; transition: color 0.3s; }
        .nav-links a:hover { color: var(--blue-main); }
        .nav-links .admin-link { color: var(--text-muted); font-size: 12px; margin-left: 40px; border: 1px solid #334155; padding: 5px 10px; border-radius: 5px; }

        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        
        .btn { display: inline-block; background-color: var(--blue-main); color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; transition: 0.3s; }
        .btn:hover { background-color: var(--blue-hover); transform: translateY(-2px); }
        .btn-danger { background-color: var(--danger); }
        .btn-danger:hover { background-color: #dc2626; }
        .btn-warning { background-color: var(--warning); color: #000; }
        .btn-warning:hover { background-color: #d97706; }
        .btn-success { background-color: var(--success); }
        .btn-success:hover { background-color: #059669; }
        .btn-dark { background-color: #334155; color: white; }
        .btn-dark:hover { background-color: #475569; }
        
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
        
        /* Nové styly pro profil */
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
    <a href="/" class="logo">OIS IDPK</a>
    <div class="nav-links">
        <a href="/">Domů</a>
        <a href="/download">Download</a>
        <a href="/team">Náš Tým</a>
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
            <a href="/" class="logo" style="font-size: 20px;">OIS IDPK</a>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div>
        </div>
        <div class="sidebar-menu">
            <a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
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
                    <div class="profile-val" style="color: #64748b;"><i>Připravuje se...</i></div>
                </div>
                
                <div class="profile-card" style="max-height: 150px; overflow-y: auto;">
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
        document.getElementById('profRegistered').innerText = registered_at || 'Neznámé (Starý účet)';
        
        document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True');
        
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

        // Fetch Discord Status & Downloads
        document.getElementById('profJoined').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        document.getElementById('modalStatusDot').innerHTML = '';
        document.getElementById('profDownloads').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>';
        
        fetch('/api/get_profile_data/' + discord_id)
            .then(r => r.json())
            .then(data => {
                document.getElementById('profJoined').innerText = data.joined_at;
                document.getElementById('modalStatusDot').innerHTML = data.status;
                
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
    function closeModal() {
        document.getElementById('editModal').style.display = 'none';
    }
</script>
"""

HTML_HOME = """
<div style="text-align: center; padding: 50px 0;">
    <h1 style="font-size: 3.5em; color: var(--blue-main); margin-bottom: 10px; letter-spacing: 2px;">Projekt OIS IDPK</h1>
    <p style="font-size: 1.2em; color: var(--text-muted); max-width: 600px; margin: 0 auto 30px auto;">
        Moderní, rychlý a bezpečný software s nejlepším zabezpečením.
    </p>
    <a href="/download" class="btn" style="font-size: 18px; padding: 15px 30px; border-radius: 30px;"><i class="fas fa-download"></i> Získat Software</a>
</div>
"""

HTML_LOGIN = """
<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-top: 4px solid var(--blue-main);">
    <h2 style="text-align: center; color: var(--blue-main);"><i class="fas fa-lock"></i> Dashboard 2FA</h2>
    <p style="color: var(--text-muted); text-align: center; font-size: 13px;">Pro přístup do systému zadejte své <b>Discord ID</b>. Systém Vám obratem zašle potvrzovací zprávu.</p>
    <form method="POST" action="/login_request">
        <label>Discord ID</label>
        <input type="text" name="discord_id" placeholder="Např. 123456789012345678" required>
        <button type="submit" class="btn" style="width: 100%;"><i class="fab fa-discord"></i> Odeslat žádost o přihlášení</button>
    </form>
</div>
"""

HTML_WAIT_AUTH = """
<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; border-top: 4px solid var(--warning);">
    <h2 style="color: var(--warning); margin-top: 0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2>
    <p style="color: var(--text-main); font-size: 16px;">Byla Vám odeslána soukromá zpráva na Discord.</p>
    <p style="color: var(--text-muted); font-size: 14px;">Zkontrolujte si aplikaci Discord a klikněte na tlačítko <b>Ověřit přístup</b>. Tato stránka se poté automaticky přesměruje.</p>
</div>
<script>
    setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}')
        .then(r => r.json())
        .then(data => {
            if(data.status === 'approved') {
                window.location.href = '/dashboard';
            } else if(data.status === 'rejected') {
                window.location.href = '/dashboard';
            }
        });
    }, 2000);
</script>
"""

HTML_TEAM = """
<h2 style="color: var(--blue-main); border-bottom: 2px solid #334155; padding-bottom: 10px;">Náš Tým</h2>
<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
    {% for member in team %}
    <div style="background-color: var(--bg-panel); border-radius: 10px; padding: 20px; text-align: center; border-top: 4px solid var(--blue-main);">
        <img src="{{ member.image_url }}" alt="Fotka" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 15px; border: 3px solid #334155;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <h3 style="font-size: 20px; font-weight: bold; margin: 0 0 5px 0;">{{ member.name }}</h3>
        <div style="color: var(--blue-main); font-size: 14px; margin-bottom: 15px;">@{{ member.discord_nick }}</div>
        <p style="color: var(--text-muted); font-size: 14px; line-height: 1.5; margin-bottom: 15px;">{{ member.description }}</p>
        <div>
            {% set roles_input = member.role_name.split(',') if member.role_name else [] %}
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

HTML_DOWNLOADS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">Správa Stahování</h2>
</div>

<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if enabled else 'var(--danger)' }};">
        <h3 style="margin-top: 0; color: var(--text-main);"><i class="fas fa-power-off"></i> Hlavní vypínač</h3>
        <p style="color: var(--text-muted); font-size: 14px;">Pokud je vypnuto, nikdo nebude moci zahájit instalaci přes Discord bota.</p>
        
        <form action="/dashboard/toggle_downloads" method="POST" style="margin-top: 20px;">
            {% if enabled %}
                <input type="hidden" name="new_status" value="False">
                <button type="submit" class="btn btn-danger" style="width: 100%; font-size: 18px;"><i class="fas fa-times-circle"></i> ZAKÁZAT STAHOVÁNÍ</button>
            {% else %}
                <input type="hidden" name="new_status" value="True">
                <button type="submit" class="btn btn-success" style="width: 100%; font-size: 18px;"><i class="fas fa-check-circle"></i> POVOLIT STAHOVÁNÍ</button>
            {% endif %}
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
                <td><strong>{{ v.version_name }}</strong></td>
                <td>
                    {% if v.target_role == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User (Všichni)</span>{% endif %}
                    {% if v.target_role == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BETA TESTER+</span>{% endif %}
                    {% if v.target_role == 'DEV_SA' %}<span class="role-tag" style="background-color: #ef4444; color: white;">DEV / SA</span>{% endif %}
                </td>
                <td style="font-size: 12px; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    <a href="{{ v.file_url }}" target="_blank" style="color: var(--blue-main);">{{ v.file_url }}</a>
                </td>
                <td>
                    <form action="/dashboard/delete_version" method="POST" style="display:inline;">
                        <input type="hidden" name="version_id" value="{{ v.id }}">
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
                    <td><strong>{{ p.discord_identifier }}</strong></td>
                    <td>
                        {% set role_list = p.roles.split(',') if p.roles else ['User'] %}
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
                            <input type="hidden" name="pending_id" value="{{ p.id }}">
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
                    <td><strong>{{ member.name }}</strong></td>
                    <td>{{ member.discord_nick }}</td>
                    <td>
                        {% set roles_input = member.role_name.split(',') if member.role_name else [] %}
                        {% for r in roles_input %}
                            {% set parts = r.split('|') %}
                            {% set r_name = parts[0].strip() %}
                            {% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                            <span class="role-tag" style="color: {{ r_color }}; border: 1px solid {{ r_color }}; background-color: {{ r_color }}33;">{{ r_name }}</span>
                        {% endfor %}
                    </td>
                    <td>
                        <form action="/dashboard/delete_team" method="POST" style="display:inline;">
                            <input type="hidden" name="discord_nick" value="{{ member.discord_nick }}">
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
        div.innerHTML = `
            <input type="text" name="role_name[]" placeholder="Název Role" required style="flex: 2; margin: 0;">
            <input type="color" name="role_color[]" value="#38bdf8" style="flex: 1; padding: 2px; height: 40px; margin: 0;">
            <button type="button" class="btn btn-danger" onclick="this.parentElement.remove()" style="padding: 0 10px; margin: 0;">X</button>
        `;
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
            <tr style="opacity: {{ '0.6' if user.is_deleted else '1' }};">
                <td style="font-weight: bold; color: var(--blue-main);">#{{ user.app_id }}</td>
                <td><strong>{{ user.nick }}</strong></td>
                <td style="font-size: 12px; color: var(--text-muted);">{{ user.discord_id }}</td>
                <td>
                    {% if user.is_deleted %}
                        <span style="color: var(--danger); font-size: 12px; font-weight: bold;">Smazán (Blokuje ID)</span>
                    {% else %}
                        <span style="color: var(--success); font-size: 12px;">Aktivní</span>
                    {% endif %}
                </td>
                <td>
                    <form action="/dashboard/change_id" method="POST" style="display: flex; gap: 5px;">
                        <input type="hidden" name="discord_id" value="{{ user.discord_id }}">
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
            <th>Přístup k DB</th>
            <th>Status</th>
            <th>Akce</th>
        </tr>
        {% for user in users %}
        <tr style="opacity: {{ '0.5' if user.is_deleted else '1' }};">
            <td style="font-weight: bold; color: var(--blue-main);">#{{ user.app_id }}</td>
            <td style="font-size: 12px; color: var(--text-muted);">{{ user.discord_id }}</td>
            <td><strong>{{ user.nick }}</strong></td>
            <td>
                {% set role_list = user.role.split(',') if user.role else ['User'] %}
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
            <td style="text-align: center;">
                {% if user.dashboard_access %}
                    <span style="color: var(--success);"><i class="fas fa-check"></i></span>
                {% else %}
                    <span style="color: var(--danger);"><i class="fas fa-times"></i></span>
                {% endif %}
            </td>
            <td>
                {% if user.is_deleted %}
                    <span style="color: var(--danger); font-weight: bold;"><i class="fas fa-skull"></i> Smazán</span>
                {% elif user.is_banned %}
                    <span style="color: var(--warning); font-weight: bold;"><i class="fas fa-ban"></i> BANNED</span>
                {% else %}
                    <span style="color: var(--success);"><i class="fas fa-check-circle"></i> Aktivní</span>
                {% endif %}
            </td>
            <td>
                <button class="btn" style="padding: 6px 12px; font-size: 12px;" onclick="openModal('{{ user.app_id }}', '{{ user.discord_id }}', '{{ user.nick }}', '{{ user.role }}', '{{ user.hwid }}', '{{ user.is_banned }}', '{{ user.is_deleted }}', '{{ user.dashboard_access }}', '{{ user.registered_at }}')"><i class="fas fa-cog"></i> Profil</button>
            </td>
        </tr>
        {% else %}
        <tr>
            <td colspan="7" style="text-align: center; padding: 30px; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td>
        </tr>
        {% endfor %}
    </table>
</div>
"""

# ==========================================
# 2. FLASK ROUTES & LOGGING
# ==========================================

def get_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

async def async_send_log_to_discord(title, description, color=0x38bdf8):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
            try:
                await channel.send(embed=embed)
            except: pass
            break

def send_log_from_flask(title, description, color=0x38bdf8):
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(async_send_log_to_discord(title, description, color), bot.loop)

def render_public(template_string, **kwargs):
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = BASE_HTML.replace('{% block layout %}{% endblock %}', html)
    return render_template_string(html, **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = BASE_HTML.replace('{% block layout %}{% endblock %}', html)
    return render_template_string(html, **kwargs)

@app.before_request
def check_session_validity():
    if request.path.startswith('/dashboard') and request.path != '/dashboard/wait_auth' and session.get('logged_in'):
        discord_id = session.get('discord_id')
        if discord_id == 'admin': return 
        if discord_id:
            db = get_db()
            if db:
                user = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                if not user or not user[0].get("dashboard_access") or user[0].get("is_banned") or user[0].get("is_deleted"):
                    session.clear()
                    flash('Váš přístup do administrace byl zablokován, zrušen nebo Váš účet neexistuje.', 'error')
                    return redirect(url_for('dashboard_main'))

def sync_roles_from_flask(discord_id, role_string):
    async def sync():
        try:
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id))
                if not member:
                    try:
                        member = await guild.fetch_member(int(discord_id))
                    except: pass
                if member:
                    await update_member_roles(member, role_string)
        except: pass
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(sync(), bot.loop)

def send_dm_from_flask(discord_id, message):
    if not discord_id: return
    async def send():
        try:
            user = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
            if user:
                await user.send(message)
        except Exception as e:
            print(f"[CHYBA] Nepodařilo se odeslat DM: {e}", flush=True)
            
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(send(), bot.loop)

class AuthView(discord.ui.View):
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
                await interaction.edit_original_response(content="✅ **Přístup do administrace byl úspěšně schválen!**\nNyní můžete zavřít tuto zprávu a vrátit se do prohlížeče.", view=None)
                await async_send_log_to_discord("🔐 Přihlášení do Dashboardu", f"Uživatel s ID `{self.discord_id}` se úspěšně přihlásil do webové administrace přes 2FA.", 0x10b981)
            else:
                await interaction.edit_original_response(content="❌ **Platnost požadavku vypršela nebo je neplatný.** Zkuste to znovu na webu.", view=None)

    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db = get_db()
        if db:
            db.table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Žádost o přihlášení byla úspěšně zamítnuta.** Přístup zablokován.", view=None)

def send_login_dm_from_flask(discord_id, token):
    async def send():
        try:
            user = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
            if user:
                embed = discord.Embed(
                    title="🔐 Bezpečnostní ověření - Dashboard", 
                    description="Byl zaznamenán pokus o přihlášení do administračního panelu Projektu OIS IDPK z prohlížeče.\n\nPokud jste to Vy, potvrďte přístup kliknutím na tlačítko níže. Pokud jste žádost nepodali, klikněte na **Zamítnout**.", 
                    color=0x38bdf8
                )
                await user.send(embed=embed, view=AuthView(token, discord_id))
        except: pass
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(send(), bot.loop)

@app.route('/')
def home():
    return render_public(HTML_HOME)

@app.route('/download')
def download_home():
    return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--blue-main);'>Stažení</h2><p>Pro stažení softwaru se prosím připojte na náš Discord a využijte instalační panel.</p></div>")

@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db: return "Chyba databáze."
    
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
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">
            Přihlášen jako: <strong>{user['nick']}</strong> (ID: #{user['app_id']})
        </p>
        <div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;">
            <h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3>
            <p style="margin: 0; color: var(--text-main);">Instalátor: <strong>{v_data['version_name']}</strong></p>
        </div>
        <a href="/api/get_file/{token}?v={version_id}" class="btn btn-success" style="font-size: 18px; padding: 15px 30px; display: block; border-radius: 8px; text-decoration: none;"><i class="fas fa-download"></i> Stáhnout Soubor</a>
        <p style="color: var(--text-muted); font-size: 12px; margin-top: 25px; line-height: 1.5;">
            <i class="fas fa-info-circle" style="color: var(--blue-main);"></i> 
            <b>Upozornění:</b> Stahování probíhá přes zabezpečený proxy server. Může to trvat déle v závislosti na rychlosti Vašeho připojení.
        </p>
    </div>
    """
    return render_public(html)

@app.route('/api/get_file/<token>')
def api_get_file(token):
    db = get_db()
    if not db: return "Chyba databáze."
    
    resp = db.table("users").select("*").eq("download_token", token).execute()
    if len(resp.data) == 0: return "Neplatný token."
    user = resp.data[0]
    if user.get("is_banned") or user.get("is_deleted"): return "Přístup zamítnut."
        
    version_id = request.args.get('v')
    v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
    if not v_resp.data: return "Verze nenalezena."
        
    file_url = v_resp.data[0]['file_url']
    version_name = v_resp.data[0]['version_name']
    
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    try:
        db.table("download_logs").insert({
            "discord_id": user['discord_id'], "version_name": version_name, "downloaded_at": now_str
        }).execute()
        send_log_from_flask("📥 Stahování softwaru", f"Uživatel **{user['nick']}** (ID: `{user['discord_id']}`) právě zahájil stahování verze **{version_name}**.", 0x38bdf8)
    except: pass
    
    version_name_clean = version_name.replace(" ", "_")
    file_ext = "zip" 
    clean_url = file_url.split("?")[0] 
    if "." in clean_url.split("/")[-1]:
        extracted_ext = clean_url.split("/")[-1].split(".")[-1]
        if len(extracted_ext) <= 4 and extracted_ext.isalnum(): file_ext = extracted_ext

    if "pixeldrain.com/u/" in file_url: file_url = file_url.replace("/u/", "/api/file/")
    if "1drv.ms" in file_url or "onedrive.live.com" in file_url or "1drv.com" in file_url: file_url = file_url.split("?")[0] + "?download=1"
    if "dropbox.com" in file_url:
        file_url = file_url.replace("dl=0", "dl=1")
        if "dl=1" not in file_url: file_url += "?dl=1" if "?" not in file_url else "&dl=1"

    try:
        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Accept': '*/*'})
        remote_response = urllib.request.urlopen(req)

        remote_filename = remote_response.info().get_filename()
        if remote_filename and '.' in remote_filename:
            ext = remote_filename.split('.')[-1]
            if len(ext) <= 4 and ext.isalnum(): file_ext = ext 

        def generate():
            while True:
                chunk = remote_response.read(8192)
                if not chunk: break
                yield chunk

        content_type = remote_response.headers.get('Content-Type', 'application/octet-stream')
        return Response(stream_with_context(generate()), headers={'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name_clean}.{file_ext}"', 'Content-Type': content_type})
    except Exception as e:
        return f"Chyba: Zkontrolujte prosím, zda je odkaz v Dashboardu platný. ({e})"

@app.route('/team')
def team():
    db = get_db()
    team_members = []
    if db:
        try:
            team_members = db.table("team").select("*").execute().data
        except: pass 
    return render_public(HTML_TEAM, team=team_members)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == os.environ.get("ADMIN_PASSWORD", "admin"):
            session['logged_in'] = True
            session['discord_id'] = 'admin'
            send_log_from_flask("🔑 Master Login", "Někdo se právě přihlásil do Dashboardu přes hlavní Master Heslo.", 0xf59e0b)
            return redirect(url_for('dashboard_main'))
        else:
            flash('Špatné heslo!', 'error')

    if not session.get('logged_in'):
        return render_public(HTML_LOGIN)
        
    db = get_db()
    users_data = []
    title = "Přehled uživatelů"
    
    if db:
        try:
            query = db.table("users").select("*")
            filter_type = request.args.get('filter')
            
            if filter_type == 'banned':
                query = query.eq("is_banned", True).eq("is_deleted", False)
                title = "Seznam zabanovaných"
            elif filter_type == 'deleted':
                query = query.eq("is_deleted", True)
                title = "Smazané účty (Záloha)"
            elif filter_type:
                query = query.ilike("role", f"%{filter_type}%").eq("is_deleted", False)
                title = f"Uživatelé s rolí: {filter_type}"
            else:
                query = query.eq("is_deleted", False).order("app_id")
                
            users_data = query.execute().data
        except Exception as e:
            flash(f'Chyba databáze: {e}', 'error')

    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title=title)

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
                send_login_dm_from_flask(discord_id, token)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            else:
                flash('Účet neexistuje, nemá povolený přístup, nebo byl zablokován.', 'error')
        except Exception as e:
            flash(f'Chyba při komunikaci s databází: {e}', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth():
    discord_id = request.args.get("discord_id")
    if not discord_id: return redirect(url_for('dashboard_main'))
    return render_public(HTML_WAIT_AUTH, discord_id=discord_id)

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    db = get_db()
    if db:
        user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
        if user:
            token_status = user[0].get("login_token")
            if token_status == "approved":
                session['logged_in'] = True
                session['discord_id'] = discord_id
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                return {"status": "approved"}
            elif token_status == "rejected":
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                return {"status": "rejected"}
    return {"status": "waiting"}

@app.route('/api/get_profile_data/<discord_id>')
def get_profile_data(discord_id):
    if not session.get('logged_in'): return {"joined_at": "Neznámé", "status": "Neznámý", "downloads": []}
    
    joined_at = "Neznámé"
    status = "Neznámý"
    member = None
    
    if bot.guilds:
        for guild in bot.guilds:
            member = guild.get_member(int(discord_id))
            if member: break
            
    if member:
        joined_at = member.joined_at.strftime("%d.%m.%Y") if member.joined_at else "Neznámé"
        status_map = {"online": "🟢 Online", "offline": "⚫ Offline", "idle": "🌙 Nečinný", "dnd": "🔴 Nerušit"}
        status = status_map.get(str(member.status), str(member.status))
    
    db = get_db()
    downloads = []
    if db:
        try:
            downloads = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data
        except: pass
        
    return {"joined_at": joined_at, "status": status, "downloads": downloads}

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    versions = []
    enabled = True
    if db:
        try:
            set_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute()
            if set_resp.data and set_resp.data[0]['setting_value'] == 'False':
                enabled = False
            versions = db.table("software_versions").select("*").order("id").execute().data
        except: pass
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled)

@app.route('/dashboard/toggle_downloads', methods=['POST'])
def toggle_downloads():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    new_status = request.form.get("new_status")
    db = get_db()
    if db:
        try:
            db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute()
            flash('Status stahování byl změněn.', 'success')
            send_log_from_flask("⚙️ Nastavení Stahování", f"Globální stahování bylo přenastaveno na: **{'Povoleno' if new_status == 'True' else 'Zakázáno'}**", 0xf59e0b)
        except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            v_name = request.form.get("version_name")
            v_data = {"version_name": v_name, "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}
            db.table("software_versions").insert(v_data).execute()
            flash('Verze úspěšně přidána.', 'success')
            send_log_from_flask("📦 Nová verze", f"Do systému byla přidána nová verze: **{v_name}**", 0x10b981)
        except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    v_id = request.form.get("version_id")
    if db and v_id:
        try:
            db.table("software_versions").delete().eq("id", v_id).execute()
            flash('Verze odebrána.', 'success')
            send_log_from_flask("🗑️ Smazání verze", "Z databáze byla odstraněna verze aplikace.", 0xef4444)
        except: pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    pending = []
    if db:
        try:
            pending = db.table("pending_roles").select("*").order("id").execute().data
        except: pass
    return render_dashboard(HTML_PENDING_ROLES, pending=pending)

@app.route('/dashboard/add_pending_role', methods=['POST'])
def add_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            roles_list = request.form.getlist("roles")
            roles_str = ",".join(roles_list) if roles_list else "User"
            ident = request.form.get("discord_identifier")
            p_data = {"discord_identifier": ident, "roles": roles_str}
            db.table("pending_roles").insert(p_data).execute()
            flash('Rezervace role byla vytvořena!', 'success')
            send_log_from_flask("🎟️ Nová rezervace role", f"Byla vytvořena rezervace role **{roles_str}** pro: `{ident}`", 0x38bdf8)
        except: pass
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/delete_pending_role', methods=['POST'])
def delete_pending_role():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    p_id = request.form.get("pending_id")
    if db and p_id:
        try:
            db.table("pending_roles").delete().eq("id", p_id).execute()
            flash('Rezervace byla zrušena.', 'success')
        except: pass
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    users_data = []
    if db:
        try:
            users_data = db.table("users").select("*").order("app_id").execute().data
        except: pass
    return render_dashboard(HTML_IDS, users=users_data)

@app.route('/dashboard/change_id', methods=['POST'])
def change_id():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    discord_id = request.form.get("discord_id")
    new_app_id = request.form.get("new_app_id")
    db = get_db()
    if db and discord_id and new_app_id:
        try:
            db.table("users").update({"app_id": int(new_app_id)}).eq("discord_id", discord_id).execute()
            flash(f'ID úspěšně změněno na #{new_app_id}.', 'success')
            send_log_from_flask("🔢 Změna ID", f"Uživateli s Discord ID `{discord_id}` bylo změněno App ID na **#{new_app_id}**.", 0xf59e0b)
        except: pass
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    team_data = []
    if db:
        try:
            team_data = db.table("team").select("*").execute().data
        except: pass
    return render_dashboard(HTML_TEAM_ADD, team=team_data)

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            role_names = request.form.getlist("role_name[]")
            role_colors = request.form.getlist("role_color[]")
            combined_roles = [f"{n.strip()}|{c.strip()}" for n, c in zip(role_names, role_colors) if n.strip()]
            new_member = {
                "name": request.form.get("name"), "discord_nick": request.form.get("discord_nick"),
                "image_url": request.form.get("image_url"), "description": request.form.get("description"),
                "role_name": ",".join(combined_roles)
            }
            db.table("team").insert(new_member).execute()
            flash('Člen týmu přidán!', 'success')
            send_log_from_flask("👥 Tým", f"Do týmu byl přidán: **{request.form.get('name')}**", 0x38bdf8)
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            db.table("team").delete().eq("discord_nick", request.form.get("discord_nick")).execute()
            flash('Člen týmu odebrán.', 'success')
        except: pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    db = get_db()
    discord_id = request.form.get("discord_id")
    action = request.form.get("action")
    nick = request.form.get("nick")
    
    if db and discord_id:
        try:
            if action == 'save':
                roles_list = request.form.getlist("roles")
                db_access = True if request.form.get("dashboard_access") else False
                new_roles_str = ",".join(roles_list) if roles_list else "User"
                
                db.table("users").update({
                    "nick": nick,
                    "role": new_roles_str,
                    "hwid": request.form.get("hwid"),
                    "dashboard_access": db_access
                }).eq("discord_id", discord_id).execute()
                
                sync_roles_from_flask(discord_id, new_roles_str)
                flash('Údaje byly úspěšně upraveny!', 'success')
                send_log_from_flask("📝 Úprava profilu", f"Profil uživatele **{nick}** (`{discord_id}`) byl upraven v Dashboardu.\nNové role: **{new_roles_str}**\n2FA Přístup: **{'Zapnuto' if db_access else 'Vypnuto'}**", 0x3b82f6)
                
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, Váš účet na Projektu OIS IDPK má nyní BAN a přístup do administrace Vám byl zablokován.")
                flash('BAN udělen a přístup do administrace zrušen.', 'warning')
                send_log_from_flask("🔨 Udělen BAN", f"Uživateli **{nick}** (`{discord_id}`) byl udělen BAN přes Dashboard.", 0xf59e0b)
                
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, Váš BAN na Projektu OIS IDPK byl úspěšně zrušen.")
                flash('BAN zrušen.', 'success')
                send_log_from_flask("🕊️ Zrušen BAN", f"Uživateli **{nick}** (`{discord_id}`) byl zrušen BAN.", 0x10b981)
                
            elif action == 'delete':
                now = datetime.now().strftime("%d.%m.%Y %H:%M")
                db.table("users").update({"is_deleted": True, "deleted_at": now, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Váš účet na Projektu OIS IDPK byl administrátorem smazán a přístup odepřen.")
                flash('Účet smazán a přístup do administrace zrušen.', 'danger')
                send_log_from_flask("☠️ Účet Smazán", f"Účet uživatele **{nick}** (`{discord_id}`) byl smazán (Soft Delete).", 0xef4444)
                
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Váš smazaný účet na Projektu OIS IDPK byl administrátorem obnoven ze zálohy.")
                flash('Účet obnoven!', 'success')
                send_log_from_flask("♻️ Účet Obnoven", f"Smazaný účet uživatele **{nick}** (`{discord_id}`) byl obnoven.", 0x10b981)
                
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                flash('Účet trvale smazán.', 'dark')
                send_log_from_flask("🔥 Permanentní smazání", f"Účet uživatele `{discord_id}` byl z databáze PERMANENTNĚ vymazán.", 0x000000)
        except: pass
    return redirect(url_for('dashboard_main'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('discord_id', None)
    return redirect(url_for('home'))

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 3. DISCORD BOT & INTERAKTIVNÍ TLAČÍTKA
# ==========================================

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

bot.remove_command('help')

@bot.event
async def on_member_join(member):
    await async_send_log_to_discord("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum připojení:** {datetime.now().strftime('%d.%m.%Y %H:%M')}", 0x10b981)

async def update_member_roles(member, role_string):
    if not member: return
    guild = member.guild
    if not guild: return
    
    u_roles = [r.strip() for r in role_string.split(',')]
    
    role_sa = discord.utils.get(guild.roles, name="web-sa")
    role_dev = discord.utils.get(guild.roles, name="web-dev")
    role_bt = discord.utils.get(guild.roles, name="web-bt")
    
    try:
        if role_sa:
            if "SA" in u_roles and role_sa not in member.roles: 
                await member.add_roles(role_sa)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky přidělena role **web-sa**.", 0xef4444)
            elif "SA" not in u_roles and role_sa in member.roles: 
                await member.remove_roles(role_sa)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky odebrána role **web-sa**.", 0x64748b)
            
        if role_dev:
            if "DEV" in u_roles and role_dev not in member.roles: 
                await member.add_roles(role_dev)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky přidělena role **web-dev**.", 0x10b981)
            elif "DEV" not in u_roles and role_dev in member.roles: 
                await member.remove_roles(role_dev)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky odebrána role **web-dev**.", 0x64748b)
            
        if role_bt:
            if "BT" in u_roles and role_bt not in member.roles: 
                await member.add_roles(role_bt)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky přidělena role **web-bt**.", 0x3b82f6)
            elif "BT" not in u_roles and role_bt in member.roles: 
                await member.remove_roles(role_bt)
                await async_send_log_to_discord("🎭 Automatická role", f"Uživateli {member.mention} byla automaticky odebrána role **web-bt**.", 0x64748b)
    except Exception as e:
        print(f"[CHYBA ROLÍ] Nemám oprávnění měnit role na serveru: {e}", flush=True)

@tasks.loop(minutes=15)
async def sync_discord_roles():
    db = get_db()
    if not db: return
    try:
        db_users = db.table("users").select("discord_id", "role", "is_deleted", "is_banned").execute().data
        if not db_users: return
        user_dict = {u['discord_id']: u for u in db_users if not u.get('is_deleted') and not u.get('is_banned')}
        
        for guild in bot.guilds:
            for member in guild.members:
                if str(member.id) in user_dict:
                    await update_member_roles(member, user_dict[str(member.id)]['role'])
    except Exception as e:
        print(f"[ROLE SYNC ERROR] {e}", flush=True)

@tasks.loop(hours=24)
async def keep_pixeldrain_alive():
    db = get_db()
    if not db: return
    try:
        versions = db.table("software_versions").select("file_url").execute().data
        for v in versions:
            url = v.get("file_url", "")
            if "pixeldrain.com/u/" in url:
                api_url = url.replace("/u/", "/api/file/")
                try:
                    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        response.read(10)
                except: pass
    except: pass

class VersionSelect(discord.ui.Select):
    def __init__(self, user_role):
        user_level = 1
        if 'BT' in user_role: user_level = 2
        if 'DEV' in user_role or 'SA' in user_role: user_level = 3
        
        db = get_db()
        options = []
        if db:
            try:
                v_resp = db.table("software_versions").select("*").order("id").execute()
                for v in v_resp.data:
                    req_level = 1
                    if v['target_role'] == 'BT': req_level = 2
                    if v['target_role'] == 'DEV_SA': req_level = 3
                    
                    if user_level >= req_level:
                        options.append(discord.SelectOption(label=v['version_name'], description="Dostupné pro tvou roli", value=str(v['id']), emoji="📦"))
            except: pass
            
        if not options:
            options.append(discord.SelectOption(label="Žádná verze nenalezena", value="none"))
            
        super().__init__(placeholder="Vyber verzi k instalaci...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="<a:loading:123> Generuji zabezpečený odkaz, prosím čekejte...", view=None)
        
        if self.values[0] == "none":
            await interaction.edit_original_response(content="Aktuálně nejsou dostupné žádné soubory.", view=None)
            return
            
        try:
            version_id = self.values[0]
            discord_id = str(interaction.user.id)
            
            token = str(uuid.uuid4())
            db = get_db()
            if db:
                db.table("users").update({"download_token": token}).eq("discord_id", discord_id).execute()
                
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://datacorebot.onrender.com")
            link = f"{base_url}/download/{token}?v={version_id}"
            
            await interaction.edit_original_response(content=f"**Projekt OIS IDPK - Odkaz připraven**\n\nZde je Váš zabezpečený odkaz ke stažení. Kliknutím budete přesměrováni na náš portál.\n🔗 {link}\n\n*Tento odkaz funguje pouze pro Vás.*", view=None)
        except Exception as e:
            print(e, flush=True)
            await interaction.edit_original_response(content="Chyba při generování odkazu.", view=None)

class VersionView(discord.ui.View):
    def __init__(self, user_role):
        super().__init__(timeout=None)
        self.add_item(VersionSelect(user_role))

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, custom_id="btn_agree", emoji="✅")
    async def agree_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="<a:loading:123> Ověřuji profil v databázi a synchronizuji role...", view=None)
        try:
            db = get_db()
            discord_id = str(interaction.user.id)
            nick = interaction.user.display_name
            user_roles = "User"
            
            if db:
                set_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute()
                if set_resp.data and set_resp.data[0]['setting_value'] == 'False':
                    await interaction.edit_original_response(content="**Stahování softwaru je aktuálně nedostupné.**\nObraťte se prosím na admin team.", view=None)
                    return
                
                pending_resp = db.table("pending_roles").select("*").execute().data
                matched_pending = None
                if pending_resp:
                    for p in pending_resp:
                        if p['discord_identifier'] == discord_id or p['discord_identifier'] == nick:
                            matched_pending = p
                            break
                
                check = db.table("users").select("*").eq("discord_id", discord_id).execute()
                if len(check.data) > 0:
                    user_data = check.data[0]
                    if user_data.get('is_banned'):
                        await interaction.edit_original_response(content="**Přístup zamítnut:** Máte udělený BAN na Projektu OIS IDPK. 🛑", view=None)
                        return
                    elif user_data.get('is_deleted'):
                        highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                        new_app_id = 1000
                        if highest_id_resp.data and highest_id_resp.data[0].get("app_id"):
                            new_app_id = highest_id_resp.data[0]["app_id"] + 1

                        new_role = matched_pending['roles'] if matched_pending else "User"
                        updates = {"app_id": new_app_id, "nick": nick, "is_deleted": False, "deleted_at": "", "role": new_role}
                        db.table("users").update(updates).eq("discord_id", discord_id).execute()
                        user_roles = new_role
                        if matched_pending: db.table("pending_roles").delete().eq("id", matched_pending['id']).execute()
                        
                        await async_send_log_to_discord("♻️ Znovuregistrace", f"Uživatel **{nick}** ({discord_id}) si obnovil smazaný účet.\nPřiřazená role: **{new_role}**", 0x10b981)
                    else:
                        user_roles = user_data.get('role', 'User')
                else:
                    highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                    new_app_id = 1000
                    if highest_id_resp.data and highest_id_resp.data[0].get("app_id"):
                        new_app_id = highest_id_resp.data[0]["app_id"] + 1

                    new_role = matched_pending['roles'] if matched_pending else "User"
                    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
                    novy = {
                        "app_id": new_app_id, "discord_id": discord_id, "nick": nick, 
                        "role": new_role, "hwid": "", "is_banned": False, 
                        "is_deleted": False, "deleted_at": "",
                        "dashboard_access": False, "login_token": "", "registered_at": now_str
                    }
                    db.table("users").insert(novy).execute()
                    user_roles = new_role
                    if matched_pending: db.table("pending_roles").delete().eq("id", matched_pending['id']).execute()
                    
                    await async_send_log_to_discord("👤 Nová registrace", f"**Uživatel:** {nick}\n**ID:** `{discord_id}`\n**App ID:** #{new_app_id}\n**Přiřazená role:** {new_role}", 0x10b981)
            
            if isinstance(interaction.user, discord.Member):
                await update_member_roles(interaction.user, user_roles)
            
            await interaction.edit_original_response(content="**Ověření úspěšné.**\nNyní si prosím vyberte soubor k instalaci:", view=VersionView(user_roles))
        except Exception as e:
            print(e, flush=True)
            await interaction.edit_original_response(content="Došlo k chybě. Zkuste to prosím znovu.", view=None)

    @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, custom_id="btn_disagree", emoji="❌")
    async def disagree_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="**Akce zrušena.**\nPro stažení softwaru je nutné vyjádřit souhlas s pravidly.", view=None)

class DownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, custom_id="btn_start_download", emoji="📥")
    async def download_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pravidla_text = (
            "**Projekt OIS IDPK - Podmínky užití**\n\n"
            "Pokračováním souhlasíte s pravidly:\n"
            "1. Je přísně zakázáno jakkoli modifikovat nebo šířit tento software.\n"
            "2. Vygenerovaný odkaz a HWID je vázáno na Váš osobní přístroj.\n\n"
            "*Souhlasíte s těmito podmínkami?*"
        )
        await interaction.response.send_message(pravidla_text, view=RulesView(), ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(DownloadView())
    keep_pixeldrain_alive.start()
    sync_discord_roles.start()
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)

# --- CHYTRÉ ZACHYTÁVÁNÍ CHYB PŘÍKAZŮ ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        cmd = ctx.command.name.lower()
        if cmd == "message":
            await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Správně to je: `!message #kanál tvůj text`", delete_after=15)
        elif cmd == "dm":
            await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Správně to je: `!dm @uživatel tvůj text`", delete_after=15)
        elif cmd == "info":
            await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Správně to je: `!info 123456789012345678`", delete_after=15)
        elif cmd == "sm":
            await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Správně to je: `!SM @uživatel`", delete_after=15)
        elif cmd == "db":
            await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Správně to je: `!DB 123456789012345678`", delete_after=15)
        else:
            await ctx.send(f"{ctx.author.mention} ❌ **Chybí argument:** Zkontroluj si `!help` pro správný formát.", delete_after=15)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!** Ujisti se, že zadáváš platné ID uživatele nebo ho označuješ přes zavináč (@jméno).", delete_after=15)
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send(f"{ctx.author.mention} ❌ **Kanál nenalezen!** Ujisti se, že označuješ správný kanál (#název).", delete_after=15)
    elif isinstance(error, commands.CheckFailure):
        pass 
    else:
        print(f"[CMD ERROR] {error}", flush=True)

# --- VLASTNÍ OPRÁVNĚNÍ PRO PŘÍKAZY ---
def check_web_sa():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="web-sa") or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send(f"❌ {ctx.author.mention}, k tomuto příkazu nemáš oprávnění (vyžadována role `web-sa`).", delete_after=10)
        try: await ctx.message.delete()
        except: pass
        return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send(f"❌ {ctx.author.mention}, k tomuto příkazu nemáš oprávnění (vyžadována role `SM`).", delete_after=10)
        try: await ctx.message.delete()
        except: pass
        return False
    return commands.check(predicate)

# --- DISCORD PŘÍKAZY ---

@bot.command()
@check_web_sa()
async def setup_download(ctx):
    embed = discord.Embed(
        title="📥 Projekt OIS IDPK - Instalace", 
        description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a generování osobního odkazu ke stažení.", 
        color=0x38bdf8
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/8205/8205562.png")
    await ctx.send(embed=embed, view=DownloadView())
    await async_send_log_to_discord("🛠️ Setup Download", f"Uživatel {ctx.author.mention} vytvořil nový instalační panel v kanálu {ctx.channel.mention}.", 0xf59e0b)
    try: await ctx.message.delete()
    except: pass

@bot.command(name="sm")
@check_web_sa()
async def sm_cmd(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role:
        await ctx.send(f"❌ {ctx.author.mention} Role `SM` na tomto serveru neexistuje. Vytvoř ji prosím.", delete_after=10)
        return
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"➖ Role **SM** byla uživateli {member.mention} úspěšně odebrána.")
        await async_send_log_to_discord("🛡️ Správa rolí", f"Admin {ctx.author.mention} **odebral** roli `SM` uživateli {member.mention}.", 0xef4444)
    else:
        await member.add_roles(role)
        await ctx.send(f"➕ Role **SM** byla uživateli {member.mention} úspěšně přidělena.")
        await async_send_log_to_discord("🛡️ Správa rolí", f"Admin {ctx.author.mention} **přidělil** roli `SM` uživateli {member.mention}.", 0x10b981)

@bot.command(name="db")
@check_sm_role()
async def db_cmd(ctx, discord_id: str):
    db = get_db()
    if not db: return
    user_data = db.table("users").select("dashboard_access, nick").eq("discord_id", discord_id).execute().data
    if not user_data:
        await ctx.send(f"❌ {ctx.author.mention} Uživatel s ID `{discord_id}` nebyl v databázi nalezen.", delete_after=10)
        return
    
    current_status = user_data[0].get("dashboard_access", False)
    new_status = not current_status
    nick = user_data[0].get("nick", "Neznámý")
    
    db.table("users").update({"dashboard_access": new_status}).eq("discord_id", discord_id).execute()
    
    stav_text = "POVOLEN ✅" if new_status else "ODEBRÁN ❌"
    await ctx.send(f"⚙️ Přístup do administrace pro uživatele **{nick}** byl úspěšně **{stav_text}**.")
    await async_send_log_to_discord("💻 Přístup do DB", f"Manažer {ctx.author.mention} změnil přístup uživateli **{nick}** na: **{stav_text}**", 0xf59e0b)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Odezva serveru je **{latency}ms**.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Nápověda - IDPK OIS PROJEKT", 
        description="Jsem systémový bot spravující databázi a infrastrukturu Projektu OIS IDPK. Níže najdeš seznam dostupných příkazů.", 
        color=0x38bdf8
    )
    embed.add_field(name="🌍 Veřejné příkazy", value="`!help` - Zobrazí tuto nápovědu.\n`!verze` - Vypíše dostupné verze aplikace.\n`!ping` - Odezva serveru bota.\n`!info [ID]` - Informace o účtu z databáze.", inline=False)
    embed.add_field(name="🛡️ Správa Discordu (Pro roli SM)", value="`!message #kanál text` - Odešle libovolnou zprávu do vybraného kanálu.\n`!dm @uživatel text` - Odešle uživateli soukromou zprávu.\n`!DB [ID]` - Přepne (povolí/zakáže) uživateli přístup do webové administrace.", inline=False)
    embed.add_field(name="⚙️ Administrace (Pro roli web-sa)", value="`!setup_download` - Vytvoří instalační panel pro uživatele.\n`!SM @uživatel` - Rychle přidělí/odebere uživateli roli SM.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def verze(ctx):
    db = get_db()
    if not db: return
    v_resp = db.table("software_versions").select("*").order("id").execute().data
    if not v_resp:
        await ctx.send("Aktuálně nejsou v databázi k dispozici žádné verze.")
        return
    embed = discord.Embed(title="📦 Dostupné verze aplikace", color=0x10b981)
    for v in v_resp:
        role_text = "Všichni (User)"
        if v['target_role'] == 'BT': role_text = "BT, DEV, SA"
        if v['target_role'] == 'DEV_SA': role_text = "DEV, SA"
        embed.add_field(name=v['version_name'], value=f"Dostupnost: **{role_text}**", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id:
        await ctx.send(f"❌ {ctx.author.mention} **Špatný formát!** Zadejte prosím platné ID Discordu, např.: `!info 123456789012345678`", delete_after=10)
        return
    db = get_db()
    if not db: return
    user = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not user:
        await ctx.send(f"❌ {ctx.author.mention} Uživatel s Discord ID `{discord_id}` nebyl v databázi nalezen.", delete_after=10)
        return
    u = user[0]
    status = "Aktivní"
    if u.get('is_deleted'): status = "Smazán"
    if u.get('is_banned'): status = "BANNED"
    
    embed = discord.Embed(title=f"Informace o uživateli: {u.get('nick')}", color=0x38bdf8)
    embed.add_field(name="App ID", value=f"#{u.get('app_id')}", inline=True)
    embed.add_field(name="Discord ID", value=u.get('discord_id'), inline=True)
    embed.add_field(name="Zapsané Role", value=u.get('role'), inline=False)
    embed.add_field(name="Status Účtu", value=status, inline=True)
    embed.add_field(name="2FA Dashboard", value="Povolen" if u.get('dashboard_access') else "Zakázán", inline=True)
    if u.get('registered_at'):
        embed.add_field(name="Zaregistrován", value=u.get('registered_at'), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="dm")
@check_sm_role()
async def dm_cmd(ctx, user: discord.Member, *, text: str):
    try:
        await user.send(text)
        await ctx.send(f"✅ Zpráva úspěšně odeslána do DM uživateli **{user.display_name}**.")
        await async_send_log_to_discord("✉️ Odesláno DM", f"Manažer {ctx.author.mention} odeslal zprávu uživateli {user.mention}:\n`{text}`", 0x3b82f6)
    except Exception:
        await ctx.send(f"❌ {ctx.author.mention} Nelze odeslat zprávu. Uživatel má pravděpodobně zablokované soukromé zprávy na serveru.", delete_after=10)

@bot.command(name="message")
@check_sm_role()
async def message_cmd(ctx, channel: discord.TextChannel, *, text: str):
    try:
        await channel.send(text)
        await ctx.send(f"✅ Zpráva úspěšně odeslána do kanálu {channel.mention}.")
        await async_send_log_to_discord("📣 Odeslána zpráva", f"Manažer {ctx.author.mention} odeslal zprávu do {channel.mention}:\n`{text}`", 0x3b82f6)
    except Exception:
        await ctx.send(f"❌ {ctx.author.mention} Nemám oprávnění posílat zprávy do tohoto kanálu.", delete_after=10)

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token: bot.run(token)
