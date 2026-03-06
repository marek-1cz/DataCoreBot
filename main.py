import os
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from threading import Thread
from supabase import create_client
from datetime import datetime
import asyncio
import uuid

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
        
        input[type="text"], input[type="number"], input[type="password"], input[type="url"], textarea { width: 100%; padding: 10px; margin: 8px 0 15px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; box-sizing: border-box; }
        
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
        .modal { background: var(--bg-panel); padding: 30px; border-radius: 15px; width: 500px; max-width: 90%; border-top: 5px solid var(--blue-main); box-shadow: 0 15px 30px rgba(0,0,0,0.5); transform: translateY(20px); transition: 0.3s; }
        .modal.active { display: flex; }
        
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
        .alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .alert-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
        
        .checkbox-group { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }
        .checkbox-group label { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: bold; cursor: pointer; }
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
            <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                <i class="fas fa-user-edit"></i> Úprava Uživatele <span id="modalAppId" style="color: var(--text-muted); font-size: 16px;"></span>
            </h2>
            
            <form action="/dashboard/edit_user" method="POST">
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
                
                <div id="activeActions">
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit</button>
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
    function openModal(app_id, discord_id, nick, roles, hwid, is_banned, is_deleted) {
        document.getElementById('editModal').style.display = 'flex';
        document.getElementById('modalAppId').innerText = "#" + app_id;
        document.getElementById('modalDiscordId').value = discord_id;
        document.getElementById('modalNick').value = nick;
        document.getElementById('modalHwid').value = hwid === 'None' ? '' : hwid;
        
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
    <h2 style="text-align: center; color: var(--blue-main);"><i class="fas fa-lock"></i> Dashboard Login</h2>
    <form method="POST">
        <label>Bezpečnostní heslo</label>
        <input type="password" name="password" required>
        <button type="submit" class="btn" style="width: 100%;">Odemknout</button>
    </form>
</div>
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
                <button class="btn" style="padding: 6px 12px; font-size: 12px;" onclick="openModal('{{ user.app_id }}', '{{ user.discord_id }}', '{{ user.nick }}', '{{ user.role }}', '{{ user.hwid }}', '{{ user.is_banned }}', '{{ user.is_deleted }}')"><i class="fas fa-cog"></i> Spravovat</button>
            </td>
        </tr>
        {% else %}
        <tr>
            <td colspan="6" style="text-align: center; padding: 30px; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td>
        </tr>
        {% endfor %}
    </table>
</div>
"""

# ==========================================
# 2. FLASK ROUTES (LOGIKA WEBU)
# ==========================================

def render_public(template_string, **kwargs):
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = BASE_HTML.replace('{% block layout %}{% endblock %}', html)
    return render_template_string(html, **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = BASE_HTML.replace('{% block layout %}{% endblock %}', html)
    return render_template_string(html, **kwargs)

def get_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

def send_dm_from_flask(discord_id, message):
    if not discord_id: return
    async def send():
        try:
            user = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
            if user:
                await user.send(message)
                print(f"[OK] DM odesláno uživateli {discord_id}", flush=True)
        except Exception as e:
            print(f"[CHYBA] Nepodařilo se odeslat DM uživateli {discord_id}: {e}", flush=True)
            
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(send(), bot.loop)

@app.route('/')
def home():
    return render_public(HTML_HOME)

@app.route('/download')
def download_home():
    return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--blue-main);'>Stažení</h2><p>Pro stažení softwaru se prosím připojte na náš Discord a využijte instalační panel k vygenerování osobního odkazu.</p></div>")

# ==========================================
# NOVÁ STRÁNKA - ZPRACOVÁNÍ JEDNORÁZOVÉHO ODKAZU
# ==========================================
@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db: 
        return "Chyba připojení k databázi."
    
    resp = db.table("users").select("*").eq("download_token", token).execute()
    if len(resp.data) == 0:
        return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný nebo vypršený odkaz!</h2><p>Tento odkaz neexistuje nebo již byl použit. Vygenerujte si nový na našem Discord serveru.</p></div>")
        
    user = resp.data[0]
    
    if user.get("is_banned"):
        return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Přístup zamítnut</h2><p>Váš účet byl administrátorem zablokován (BAN).</p></div>")
    elif user.get("is_deleted"):
        return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Účet neexistuje</h2><p>Váš účet byl smazán administrátorem.</p></div>")
        
    version = request.args.get('v', 'Neznámá verze')
    
    html = f"""
    <div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; border-top: 4px solid var(--success);">
        <h2 style="color: var(--success); margin-top: 0;"><i class="fas fa-check-circle"></i> Ověření proběhlo úspěšně</h2>
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">
            Vítejte zpět, <strong>{user['nick']}</strong> (ID: #{user['app_id']})
        </p>
        
        <div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;">
            <h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3>
            <p style="margin: 0; color: var(--text-main);">Vybraná verze k instalaci: <strong>{version}</strong></p>
        </div>
        
        <button class="btn btn-success" style="font-size: 18px; padding: 15px 30px; width: 100%; border-radius: 8px;" onclick="alert('Zde se v budoucnu spustí stahování souboru!')"><i class="fas fa-download"></i> Stáhnout aplikaci</button>
        
        <p style="color: var(--text-muted); font-size: 12px; margin-top: 20px;">
            <i class="fas fa-exclamation-triangle" style="color: var(--warning);"></i> 
            Upozornění: Software bude při prvním spuštění uzamčen na Váš osobní přístroj (HWID).
        </p>
    </div>
    """
    return render_public(html)

@app.route('/team')
def team():
    db = get_db()
    team_members = []
    if db:
        try:
            team_members = db.table("team").select("*").execute().data
        except:
            pass 
    return render_public(HTML_TEAM, team=team_members)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == os.environ.get("ADMIN_PASSWORD", "admin"):
            session['logged_in'] = True
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
                
            resp = query.execute()
            users_data = resp.data
        except Exception as e:
            flash(f'Chyba databáze: {e}', 'error')

    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title=title)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    users_data = []
    if db:
        try:
            resp = db.table("users").select("*").order("app_id").execute()
            users_data = resp.data
        except Exception as e:
            flash(f'Chyba načítání databáze: {e}', 'error')
            
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
        except Exception as e:
            flash(f'Chyba při změně ID: {e}', 'error')
            
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    team_data = []
    if db:
        try:
            team_data = db.table("team").select("*").execute().data
        except:
            pass
            
    return render_dashboard(HTML_TEAM_ADD, team=team_data)

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    if db:
        try:
            role_names = request.form.getlist("role_name[]")
            role_colors = request.form.getlist("role_color[]")
            
            combined_roles = []
            for n, c in zip(role_names, role_colors):
                if n.strip():
                    combined_roles.append(f"{n.strip()}|{c.strip()}")
            
            roles_str = ",".join(combined_roles)

            new_member = {
                "name": request.form.get("name"),
                "discord_nick": request.form.get("discord_nick"),
                "image_url": request.form.get("image_url"),
                "description": request.form.get("description"),
                "role_name": roles_str
            }
            db.table("team").insert(new_member).execute()
            flash('Člen týmu byl úspěšně přidán!', 'success')
        except Exception as e:
            flash(f'Chyba při přidávání do týmu: {e}', 'error')
            
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    discord_nick = request.form.get("discord_nick")
    db = get_db()
    if db and discord_nick:
        try:
            db.table("team").delete().eq("discord_nick", discord_nick).execute()
            flash('Člen týmu byl odebrán.', 'success')
        except Exception as e:
            flash(f'Chyba při mazání: {e}', 'error')
            
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    discord_id = request.form.get("discord_id")
    action = request.form.get("action")
    
    if db and discord_id:
        try:
            if action == 'save':
                roles_list = request.form.getlist("roles")
                roles_str = ",".join(roles_list) if roles_list else "User"
                
                updates = {
                    "nick": request.form.get("nick"),
                    "role": roles_str,
                    "hwid": request.form.get("hwid")
                }
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
                flash('Uživatel úspěšně upraven!', 'success')
                
            elif action == 'ban':
                db.table("users").update({"is_banned": True}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, oznamujeme Vám, že Vám byl udělen trvalý zákaz přístupu (BAN) administrátorem Projektu OIS IDPK.")
                flash('Uživatel dostal BAN a byla mu odeslána zpráva do DM!', 'warning')
                
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, Váš zákaz přístupu (BAN) na Projektu OIS IDPK byl administrací zrušen. Nyní můžete software opět využívat.")
                flash('BAN byl zrušen a uživateli byla odeslána notifikace do DM.', 'success')
                
            elif action == 'delete':
                now = datetime.now().strftime("%d.%m.%Y %H:%M")
                db.table("users").update({"is_deleted": True, "deleted_at": now}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, Váš stávající účet v Projektu OIS IDPK byl administrací smazán. Pokud máte nadále zájem o naše služby, můžete si vytvořit novou registraci.")
                flash('Účet byl smazán (Soft Delete). Původní ID je zachováno v záloze. Zpráva odeslána do DM.', 'danger')
                
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                send_dm_from_flask(discord_id, "Vážený uživateli, Váš účet v Projektu OIS IDPK byl administrací úspěšně obnoven ze zálohy.")
                flash('Účet byl úspěšně obnoven ze zálohy a uživateli byla odeslána notifikace do DM!', 'success')
                
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                flash('Veškerá data o uživateli byla PERMANENTNĚ a nevratně smazána.', 'dark')
                
        except Exception as e:
            flash(f'Chyba při úpravě: {e}', 'error')
            
    return redirect(url_for('dashboard_main'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 3. DISCORD BOT & INTERAKTIVNÍ TLAČÍTKA
# ==========================================

class VersionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.select(placeholder="Vyber verzi softwaru...", options=[
        discord.SelectOption(label="Verze 1.0 (Stabilní)", description="Doporučená verze pro všechny", value="v1.0", emoji="✅"),
        discord.SelectOption(label="Verze 2.0 (Beta)", description="Testovací verze s novými funkcemi", value="v2.0", emoji="🛠️")
    ])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        version = select.values[0]
        discord_id = str(interaction.user.id)
        
        # 1. Vygenerování unikátního tokenu pro tohoto uživatele
        token = str(uuid.uuid4())
        db = get_db()
        if db:
            db.table("users").update({"download_token": token}).eq("discord_id", discord_id).execute()
            
        # 2. Sestavení zabezpečeného odkazu
        # Render používá RENDER_EXTERNAL_URL, pokud tam není, fallbackne se to
        base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://tvojestranka.onrender.com")
        link = f"{base_url}/download/{token}?v={version}"
        
        await interaction.response.edit_message(content=f"**Projekt OIS IDPK - Odkaz připraven**\n\nTady je Váš vygenerovaný zabezpečený odkaz pro verzi **{version}**:\n🔗 {link}\n\n*Upozornění: Tento odkaz nikomu nesdělujte, je svázán s Vaším profilem.*", view=None)

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, custom_id="btn_agree", emoji="✅")
    async def agree_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = get_db()
        discord_id = str(interaction.user.id)
        nick = interaction.user.display_name
        
        if db:
            check = db.table("users").select("*").eq("discord_id", discord_id).execute()
            if len(check.data) > 0:
                user_data = check.data[0]
                if user_data.get('is_banned'):
                    await interaction.response.edit_message(content="**Přístup zamítnut:** Máte udělený BAN na Projektu OIS IDPK. 🛑", view=None)
                    return
                elif user_data.get('is_deleted'):
                    # Zpracování uživatele se smazaným účtem - přepíše se
                    highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                    new_app_id = 1000
                    if highest_id_resp.data and highest_id_resp.data[0].get("app_id"):
                        new_app_id = highest_id_resp.data[0]["app_id"] + 1

                    updates = {
                        "app_id": new_app_id,
                        "nick": nick,
                        "is_deleted": False,
                        "deleted_at": "",
                        "role": "User"
                    }
                    db.table("users").update(updates).eq("discord_id", discord_id).execute()
            else:
                highest_id_resp = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                new_app_id = 1000
                if highest_id_resp.data and highest_id_resp.data[0].get("app_id"):
                    new_app_id = highest_id_resp.data[0]["app_id"] + 1

                novy = {
                    "app_id": new_app_id,
                    "discord_id": discord_id, 
                    "nick": nick, 
                    "role": "User", 
                    "hwid": "",
                    "is_banned": False,
                    "is_deleted": False,
                    "deleted_at": ""
                }
                db.table("users").insert(novy).execute()
        
        await interaction.response.edit_message(content="**Ověření úspěšné.**\nNyní si prosím vyberte verzi softwaru k instalaci:", view=VersionView())

    @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, custom_id="btn_disagree", emoji="❌")
    async def disagree_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="**Akce zrušena.**\nPro stažení softwaru je nutné vyjádřit souhlas s pravidly Projektu OIS IDPK.", view=None)

class DownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, custom_id="btn_start_download", emoji="📥")
    async def download_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pravidla_text = (
            "**Projekt OIS IDPK - Podmínky užití**\n\n"
            "Pokračováním souhlasíte s následujícími pravidly:\n"
            "1. Je přísně zakázáno jakkoli modifikovat nebo šířit tento software třetím stranám.\n"
            "2. Vygenerovaný odkaz a HWID je vázáno pouze na Váš osobní přístroj.\n"
            "3. Administrace si vyhrazuje právo omezit přístup v případě porušení pravidel.\n\n"
            "*Souhlasíte s těmito podmínkami?*"
        )
        await interaction.response.send_message(pravidla_text, view=RulesView(), ephemeral=True)

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    bot.add_view(DownloadView())
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)

@bot.command()
async def setup_download(ctx):
    embed = discord.Embed(
        title="📥 Projekt OIS IDPK - Instalace", 
        description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a generování osobního odkazu ke stažení.", 
        color=0x38bdf8
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/8205/8205562.png")
    
    await ctx.send(embed=embed, view=DownloadView())
    await ctx.message.delete()

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
