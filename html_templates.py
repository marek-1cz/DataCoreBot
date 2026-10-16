# -*- coding: utf-8 -*-
BASE_HTML = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Projekt OIS IDPK</title>
<link rel="icon" type="image/png" href="/static/img/datacorebot_pf-lepsi.png">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root { --bg-dark: #0f172a; --bg-panel: #1e293b; --blue-main: #38bdf8; --blue-hover: #0284c7; --text-main: #f8fafc; --text-muted: #94a3b8; --danger: #ef4444; --success: #10b981; --warning: #f59e0b; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; overflow-x: hidden; }
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
.modal { background: var(--bg-panel); padding: 30px; border-radius: 15px; width: 900px; max-width: 95%; border-top: 5px solid var(--blue-main); box-shadow: 0 15px 30px rgba(0,0,0,0.5); transform: translateY(20px); transition: 0.3s; max-height: 90vh; overflow-y: auto;}
.modal.active { display: flex; }
.alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
.alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
.alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
.alert-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
.checkbox-group { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }
.checkbox-group label { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: bold; cursor: pointer; }
.profile-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.profile-card { background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #334155; }
.profile-stat { font-size: 12px; color: var(--text-muted); margin-bottom: 5px; }
.profile-val { font-size: 14px; font-weight: bold; color: var(--text-main); }
.dl-table th, .dl-table td { padding: 8px; font-size: 12px; border-bottom: 1px solid #334155; }
@keyframes pulseShiny { 
    0% { transform: scale(1); box-shadow: 0 0 15px rgba(245, 158, 11, 0.4); } 
    100% { transform: scale(1.05); box-shadow: 0 0 40px rgba(245, 158, 11, 1); } 
}
@keyframes glowMega { 
    0% { box-shadow: 0 0 30px rgba(255, 51, 51, 0.4); border-color: #cc0000; transform: scale(1); } 
    100% { box-shadow: 0 0 80px rgba(255, 51, 51, 0.9); border-color: #ff6666; transform: scale(1.02); } 
}
@keyframes glowVelky { 
    0% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); border-color: #d97706; transform: scale(1); } 
    100% { box-shadow: 0 0 60px rgba(245, 158, 11, 0.8); border-color: #fcd34d; transform: scale(1.01); } 
}
@keyframes glowNormal { 
    0% { box-shadow: 0 0 10px rgba(56, 189, 248, 0.2); border-color: #0284c7; transform: scale(1); } 
    100% { box-shadow: 0 0 35px rgba(56, 189, 248, 0.6); border-color: #bae6fd; transform: scale(1.005); } 
}
@media (max-width: 768px) {
    .nav-brand-mobile { justify-content: space-between !important; margin-bottom: 15px; }
    .desktop-avatar-slot { display: none !important; }
    .mobile-avatar-slot { display: block !important; }
    .top-nav { flex-direction: column; padding: 15px 10px; gap: 5px; }
    .nav-links { flex-wrap: wrap; justify-content: center; gap: 10px; }
    .nav-links a { margin-left: 0; font-size: 13px; }
    .nav-links .admin-link { margin-left: 0; }
    .user-avatar-wrap { padding: 6px 15px 6px 6px !important; margin-left: 0 !important; justify-content: center; width: auto !important; box-sizing: border-box; }
    .user-avatar-wrap span { font-size: 12px !important; max-width: 80px !important; }
    .user-avatar-wrap .fa-user-circle { font-size: 32px !important; }
    .user-avatar-wrap > div { width: 34px !important; height: 34px !important; }
    .user-dropdown-menu { right: 0; left: auto; transform: none; width: 250px; max-width: 90vw; }
    .container { margin: 20px auto; padding: 0 10px; }
    h1 { font-size: 1.8em !important; line-height: 1.3; }
    .screenshot-pair { flex-direction: column !important; }
    .screenshot-pair img { width: 100% !important; margin-bottom: 0px; }
    .btn { padding: 12px 20px; font-size: 16px !important; }
    .home-wrap { padding: 30px 10px !important; }
    .info-box { padding: 15px !important; }
    .footer-box { padding: 20px !important; }
    
    .dashboard-wrapper { flex-direction: column !important; }
    .sidebar { width: 100% !important; border-right: none !important; border-bottom: 1px solid #334155; }
    .sidebar-menu { display: flex; flex-wrap: wrap; padding: 10px !important; gap: 5px; justify-content: center; }
    .sidebar-menu a { flex: 1 1 45%; font-size: 11px; padding: 10px !important; border-left: none !important; border-bottom: 3px solid transparent; text-align: center; }
    .sidebar-menu a:hover, .sidebar-menu a.active { border-bottom-color: var(--blue-main) !important; border-left-color: transparent !important; background: rgba(56, 189, 248, 0.1); }
    .dashboard-content { padding: 15px !important; }
    table { display: block; overflow-x: auto; white-space: nowrap; }
    .profile-grid { grid-template-columns: 1fr !important; }
}
</style>
</head>
<body>
{% block layout %}{% endblock %}

<script>
document.addEventListener("DOMContentLoaded", function() {
    if(localStorage.getItem('hide_discord_popup') === 'true' || sessionStorage.getItem('discord_popup_shown') === 'true') return;
    fetch('/api/auth/me')
        .then(r => r.json())
        .then(data => {
            if(data.status === 'success' && data.user && data.user.discord_id === 'čeká na odpověd') {
                sessionStorage.setItem('discord_popup_shown', 'true');
                const popupHtml = `
                <div id="discord-link-popup" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.85); backdrop-filter: blur(5px); display: flex; align-items: center; justify-content: center; z-index: 999999; animation: fadeIn 0.3s ease;">
                    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 30px 25px; width: 90%; max-width: 420px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.4);">
                        <div style="font-size: 48px; color: #5865F2; margin-bottom: 20px; filter: drop-shadow(0 0 15px rgba(88,101,242,0.4));">
                            <i class="fab fa-discord"></i>
                        </div>
                        <h2 style="color: white; margin-top: 0; margin-bottom: 12px; font-size: 24px; font-weight: 600;">Propojit s Discordem</h2>
                        <div id="discord-popup-content">
                            <p style="color: #94a3b8; font-size: 15px; margin-bottom: 25px; line-height: 1.5;">Upozornění: Pro více funkcí, plný přístup k systému a oznámení, přidejte své Discord ID.</p>
                            <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px;">
                                <button onclick="showDiscordInput()" style="background: #5865F2; color: white; border: none; border-radius: 10px; padding: 14px; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 15px rgba(88,101,242,0.3);">Propojit s Discordem</button>
                                <button onclick="document.getElementById('discord-link-popup').style.display='none'" style="background: transparent; color: #94a3b8; border: 1px solid #475569; border-radius: 10px; padding: 14px; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.2s;">Později</button>
                            </div>
                            <a href="javascript:void(0)" onclick="localStorage.setItem('hide_discord_popup', 'true'); document.getElementById('discord-link-popup').style.display='none'" style="color: #64748b; font-size: 13px; text-decoration: underline; transition: color 0.2s;">Již neupozorňovat</a>
                        </div>
                    </div>
                </div>
                `;
                document.body.insertAdjacentHTML('beforeend', popupHtml);
                
                window.showDiscordInput = function() {
                    const content = document.getElementById('discord-popup-content');
                    content.innerHTML = `
                        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">Zadejte vaše Discord ID (dlouhé číslo). Otevřete si poté Discord, přijde vám zpráva k potvrzení.</p>
                        <input type="text" id="discord-popup-input" placeholder="Např. 123456789012345678" style="width: 100%; box-sizing: border-box; background: rgba(0,0,0,0.3); border: 1px solid #475569; border-radius: 10px; padding: 12px; color: white; font-size: 16px; margin-bottom: 15px; text-align: center;">
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <button onclick="submitDiscordPopup()" style="background: #10b981; color: white; border: none; border-radius: 10px; padding: 14px; font-weight: bold; font-size: 16px; cursor: pointer; box-shadow: 0 4px 15px rgba(16,185,129,0.3);">Odeslat a ověřit</button>
                            <button onclick="document.getElementById('discord-link-popup').style.display='none'" style="background: transparent; color: #94a3b8; border: none; padding: 10px; cursor: pointer;">Zrušit</button>
                        </div>
                    `;
                };
                
                window.submitDiscordPopup = function() {
                    const id = document.getElementById('discord-popup-input').value.trim();
                    if(!id) return alert('Zadejte Discord ID.');
                    
                    const content = document.getElementById('discord-popup-content');
                    content.innerHTML = '<div style="padding: 20px;"><i class="fas fa-spinner fa-spin" style="font-size: 30px; color: #5865F2; margin-bottom: 15px;"></i><p style="color: #94a3b8;">Odesílám požadavek na Discord...</p></div>';
                    
                    fetch('/api/auth/discord/request', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({discord_id: id})
                    }).then(r=>r.json()).then(data => {
                        if(data.status === 'success') {
                            content.innerHTML = `
                                <div style="padding: 10px;">
                                    <i class="fas fa-check-circle" style="font-size: 40px; color: #10b981; margin-bottom: 15px;"></i>
                                    <p style="color: white; font-weight: bold; margin-bottom: 10px;">Zpráva odeslána!</p>
                                    <p style="color: #94a3b8; font-size: 14px; line-height: 1.5; margin-bottom: 20px;">Otevřete si soukromé zprávy od DataCore Bota a klikněte na "Přihlásit se na Web". Čekám na vaše potvrzení...</p>
                                    <div style="display:flex; justify-content:center;"><i class="fas fa-spinner fa-spin" style="color:#5865F2;"></i></div>
                                </div>
                            `;
                            
                            let checkInterval = setInterval(() => {
                                fetch('/api/auth/status?discord_id=' + data.discord_id)
                                .then(r=>r.json()).then(statusData => {
                                    if(statusData.status === 'approved') {
                                        clearInterval(checkInterval);
                                        content.innerHTML = '<div style="padding: 20px;"><i class="fas fa-check-circle" style="font-size: 40px; color: #10b981; margin-bottom: 15px;"></i><p style="color: white; font-weight: bold;">Propojení úspěšné!</p></div>';
                                        setTimeout(() => location.reload(), 1500);
                                    } else if(statusData.status === 'rejected') {
                                        clearInterval(checkInterval);
                                        content.innerHTML = '<div style="padding: 20px;"><i class="fas fa-times-circle" style="font-size: 40px; color: #ef4444; margin-bottom: 15px;"></i><p style="color: white; font-weight: bold;">Propojení zamítnuto.</p></div>';
                                        setTimeout(() => document.getElementById('discord-link-popup').style.display='none', 3000);
                                    }
                                });
                            }, 2000);
                            
                        } else {
                            alert('Chyba: ' + data.message);
                            document.getElementById('discord-link-popup').style.display='none';
                        }
                    }).catch(e => {
                        alert('Chyba komunikace se serverem.');
                        document.getElementById('discord-link-popup').style.display='none';
                    });
                };
            }
        })
        .catch(err => console.error("Discord popup check error:", err));
});
</script>

</body>
</html>
"""

PUBLIC_LAYOUT = """
<nav class="top-nav">
<div class="nav-brand-mobile" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
<a href="/" class="logo"><img src="/static/img/datacorebot_pf-lepsi.png" alt="Logo" style="height: 30px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 8px rgba(56, 189, 248, 0.6));">OIS IDPK</a>
<div class="mobile-avatar-slot" style="display:none;">__AVATAR__</div>
</div>
<div class="nav-links" style="display:flex; align-items:center;">
<a href="/dashboard" class="admin-link">Dashboard 🔒</a>
<a href="/">Domů</a><a href="/download">Download</a><a href="/team">Náš Tým</a><a href="/stats">Statistiky</a>
<a href="/supporters" style="color: var(--blue-main); font-weight: bold; text-shadow: 0 0 10px rgba(56, 189, 248, 0.6);"><i class="fas fa-heart"></i> Podporovatelé</a>
<a href="/provoz-idpk" style="color: #10b981; font-weight: bold;"><i class="fas fa-bus"></i> Provoz IDPK</a>
<a href="/led-panel" style="color: #f59e0b; font-weight: bold;"><i class="fas fa-tv"></i> LED Panel Simulátor</a>
<div class="desktop-avatar-slot">__AVATAR__</div>
</div>
</nav>
<div class="container">
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}
{% endwith %}
{% block content %}{% endblock %}
</div>
"""

DASHBOARD_LAYOUT = """
<div class="dashboard-wrapper">
<div class="sidebar">
<div class="sidebar-header"><a href="/" class="logo" style="font-size: 20px; display: flex; justify-content: center; align-items: center; gap: 8px;"><img src="/static/img/datacorebot_pf-lepsi.png" alt="Logo" style="height: 24px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 6px rgba(56, 189, 248, 0.6));">OIS IDPK</a><div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div></div>
<div class="sidebar-menu">
<a href="/" class="sidebar-link" style="color: #10b981; border-bottom: 1px solid #334155; margin-bottom: 5px;"><i class="fas fa-globe"></i> Veřejný Web (Bypass)</a>
<a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
<a href="/dashboard/interaktivni-mapa" class="sidebar-link" style="color: #38bdf8; font-weight: 600;"><i class="fas fa-map-marked-alt"></i> Interaktivní mapa</a>
<a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-line"></i> Statistiky Webu & Aplikace</a>
<a href="/dashboard/app_management" class="sidebar-link"><i class="fas fa-desktop"></i> Správa Aplikace</a>
<a href="/dashboard/sprava-notifikaci" class="sidebar-link" style="color: #a78bfa; font-weight: 600;"><i class="fas fa-paper-plane"></i> Správa Notifikací & Zprávy</a>
<a href="/dashboard/notifications" class="sidebar-link" style="color: #f59e0b;"><i class="fas fa-bell"></i> Oznámení</a>
<a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-code-branch"></i> Správa Verzí a Přístupů</a>
<a href="/dashboard/pending_roles" class="sidebar-link" style="color: #10b981;"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a>
<a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a>
<a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a>
<a href="/dashboard/admins" class="sidebar-link"><i class="fas fa-users-cog"></i> Správa Dashboard Adminů</a>
<a href="/dashboard/supporters" class="sidebar-link" style="color: var(--blue-main); text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);"><i class="fas fa-star"></i> Podporovatelé</a>
<a href="/dashboard/feedback" class="sidebar-link" style="color: #a855f7; text-shadow: 0 0 5px rgba(168, 85, 247, 0.5);"><i class="fas fa-comments"></i> Zpětná vazba</a>
<a href="/dashboard?filter=banned" class="sidebar-link" style="color: var(--warning);"><i class="fas fa-ban"></i> Seznam BANů</a>
<a href="/dashboard?filter=deleted" class="sidebar-link" style="color: var(--danger);"><i class="fas fa-trash-alt"></i> Smazaní (Záloha)</a>
<div style="padding: 15px 20px 5px 20px; font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold;">Hledat roli</div>
<a href="/dashboard?filter=SA" class="sidebar-link"><i class="fas fa-crown"></i> SA (SERVER ADMIN)</a>
<a href="/dashboard?filter=DEV" class="sidebar-link"><i class="fas fa-code"></i> DEV (DEVELOPER)</a>
<a href="/dashboard?filter=BT" class="sidebar-link"><i class="fas fa-bug"></i> BT (BETA TESTER)</a>
</div>
<div style="padding: 20px;"><div style="font-size: 11px; color: var(--text-muted); text-align: center; margin-bottom: 15px; border-top: 1px solid #334155; padding-top: 15px;"><i class="fas fa-clock"></i> Poslední update bota:<br><b>{{ deploy_time }}</b></div><a href="/logout" class="btn btn-danger" style="width: 100%; text-align: center; box-sizing: border-box;"><i class="fas fa-sign-out-alt"></i> Odhlásit</a></div>
</div>
<div class="dashboard-content">
{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}
{% block content %}{% endblock %}
</div>
</div>

<div class="modal-overlay" id="editModal">
<div class="modal" id="modalContent" style="max-width: 1100px;">
<div style="width: 100%;">
<h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;"><span><i class="fas fa-user"></i> Profil hráče <span id="modalAppId" style="color: var(--text-muted); font-size: 16px;"></span></span><span id="modalStatusDot" style="font-size: 14px;"></span></h2>
<div class="profile-grid">
<div class="profile-card"><div class="profile-stat">Členem Discordu od:</div><div class="profile-val" id="profJoined"><i class="fas fa-spinner fa-spin"></i> Načítání...</div><div class="profile-stat" style="margin-top: 10px;">Datum registrace v DB:</div><div class="profile-val" id="profRegistered"></div><div class="profile-stat" style="margin-top: 10px;">Aktivita v aplikaci (Status):</div><div class="profile-val" id="profAppStatus" style="color: #64748b;"><i>Připravuje se...</i></div><div id="profStats" style="margin-top: 10px;"></div><div class="profile-stat" style="margin-top: 10px;">Přístup do webové DB:</div><div class="profile-val" id="profDbAccess"></div></div>
<div class="profile-card" style="max-height: 250px; overflow-y: auto;"><div class="profile-stat" style="margin-bottom: 10px; font-weight:bold; color: var(--blue-main);">Historie stahování:</div><table class="dl-table" style="width: 100%; margin-top: 0; background: transparent; border-radius: 0;"><tbody id="profDownloads"><tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr></tbody></table></div>
<div class="profile-card" style="max-height: 250px; overflow-y: auto;"><div class="profile-stat" style="margin-bottom: 10px; font-weight:bold; color: var(--warning);">Historie sezení (Logy):</div><table class="dl-table" style="width: 100%; margin-top: 0; background: transparent; border-radius: 0;"><tbody id="profSessions"><tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr></tbody></table></div>
</div>
<form action="/dashboard/edit_user" method="POST" style="border-top: 1px solid #334155; padding-top: 15px; margin-top: 15px;">
<input type="hidden" name="discord_id" id="modalDiscordId">
<input type="hidden" name="app_id" id="modalAppIdHidden">
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
<div>
<label>Herní Nick:</label><input type="text" name="nick" id="modalNick" required>
<label>E-mail:</label><input type="email" name="email" id="modalEmail" placeholder="Nevyplněno">
<label>Zámek na PC (HWID a IP adresa):</label>
<div style="display: flex; gap: 10px;">
<input type="text" name="hwid" id="modalHwid" placeholder="Pro odblokování HWID smažte text" style="flex:1;">
<input type="text" name="ip_address" id="modalIp" placeholder="Pro odblokování IP smažte text" style="flex:1;">
</div>
<div style="background-color: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 5px; border: 1px solid var(--blue-main); margin-bottom: 15px; margin-top: 10px;"><label style="cursor: pointer; font-weight: bold; color: var(--blue-main); margin: 0; display: flex; align-items: center; gap: 10px;"><input type="checkbox" name="dashboard_access" id="modalDashboardAccess" value="True" style="width: auto; margin: 0;"> Přístup do Dashboardu (2FA)</label></div>
</div>
<div>
<label>Role:</label><div class="checkbox-group" style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label><label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label><label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label><label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label></div>
<div id="activeActions" style="margin-top: 20px;"><div style="display: flex; gap: 10px;"><button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit</button><button type="submit" formnovalidate name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;"><i class="fas fa-ban"></i> Dát BAN</button><button type="submit" formnovalidate name="action" value="unban" id="btnUnban" class="btn btn-success" style="flex: 1; display: none;"><i class="fas fa-check"></i> Un-BAN</button></div><div style="margin-top: 10px;"><button type="submit" formnovalidate name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Smazat účet? (Zablokuje ID, umožní novou registraci)')"><i class="fas fa-trash"></i> Smazat (Soft Delete)</button></div></div>
<div id="deletedActions" style="display: none; margin-top: 20px;"><p style="color: var(--danger); font-weight: bold; text-align: center; margin-top: 0; margin-bottom: 5px;">Tento účet je smazaný.</p><div style="display: flex; gap: 10px;"><button type="submit" formnovalidate name="action" value="restore" class="btn btn-success" style="flex: 1;"><i class="fas fa-undo"></i> Obnovit účet</button><button type="submit" formnovalidate name="action" value="hard_delete" class="btn btn-dark" style="flex: 1;" onclick="return confirm('PERMANENTNÍ SMAZÁNÍ: Tato akce kompletně vymaže veškerá data. Pokračovat?')"><i class="fas fa-skull"></i> Smazat permanentně</button></div></div>
</div></div>
</form>
<button class="btn" onclick="closeModal()" style="background: transparent; color: var(--text-muted); width: 100%; margin-top: 15px; border: 1px solid #334155;">Zavřít profil</button>
</div></div></div>
<script>
function openModal(btn) {
    try {
        document.getElementById('editModal').style.display = 'flex';
        let app_id = btn.getAttribute('data-app-id') || "";
        document.getElementById('modalAppId').innerText = "#" + app_id;
        document.getElementById('modalAppIdHidden').value = app_id;
        let discord_id = btn.getAttribute('data-discord-id') || "";
        document.getElementById('modalDiscordId').value = discord_id;
        document.getElementById('modalNick').value = btn.getAttribute('data-nick') || "";
        document.getElementById('modalEmail').value = btn.getAttribute('data-email') || "";
        document.getElementById('modalHwid').value = (!btn.getAttribute('data-hwid') || btn.getAttribute('data-hwid') === 'None') ? '' : btn.getAttribute('data-hwid');
        document.getElementById('modalIp').value = (!btn.getAttribute('data-ip') || btn.getAttribute('data-ip') === 'None') ? '' : btn.getAttribute('data-ip');
        let registered_at = btn.getAttribute('data-reg-at');
        document.getElementById('profRegistered').innerText = (registered_at && registered_at !== 'None') ? registered_at : 'Neznámé (Starý účet)';
        let dashboard_access = btn.getAttribute('data-db-access');
        document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True');
        document.getElementById('profDbAccess').innerHTML = dashboard_access === 'True' ? '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Povoleno</span>' : '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> Zakázáno</span>';
        document.querySelectorAll('input[name="roles"]').forEach(cb => cb.checked = false);
        let rolesStr = btn.getAttribute('data-roles') || "";
        rolesStr.split(',').forEach(r => { let el = document.querySelector(`input[name="roles"][value="${r.trim()}"]`); if(el) el.checked = true; });
        let is_deleted = btn.getAttribute('data-deleted');
        let is_banned = btn.getAttribute('data-banned');
        if (is_deleted === 'True') {
            document.getElementById('activeActions').style.display = 'none';
            document.getElementById('deletedActions').style.display = 'block';
        } else {
            document.getElementById('activeActions').style.display = 'block';
            document.getElementById('deletedActions').style.display = 'none';
            if (is_banned === 'True') { document.getElementById('btnBan').style.display = 'none'; document.getElementById('btnUnban').style.display = 'block';
            } else { document.getElementById('btnBan').style.display = 'block'; document.getElementById('btnUnban').style.display = 'none'; }
        }
        document.getElementById('profJoined').innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('modalStatusDot').innerHTML = ''; document.getElementById('profDownloads').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>'; document.getElementById('profSessions').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>'; document.getElementById('profAppStatus').innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('profStats').innerHTML = '';
        if (!discord_id || discord_id.trim() === '' || discord_id === 'None') {
            document.getElementById('profJoined').innerText = "Chybí ID"; document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Chyba dat (ID nenalezeno)</span>"; return;
        }
        fetch('/api/get_profile_data/' + discord_id).then(r => r.json()).then(data => {
            if (data.error) { document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Chyba dat: " + data.error + "</span>"; return; }
            document.getElementById('profJoined').innerText = data.joined_at || "Nenalezen";
            document.getElementById('modalStatusDot').innerHTML = data.status || "";
            document.getElementById('profAppStatus').innerHTML = data.app_status || "";
            document.getElementById('profStats').innerHTML = data.stats || "";
            let dlHtml = "";
            if(data.downloads && data.downloads.length > 0) { data.downloads.forEach(d => { dlHtml += `<tr><td style="color: var(--blue-main);"><b>${d.version_name}</b></td><td style="color: var(--text-muted);">${d.downloaded_at}</td></tr>`; }); } else { dlHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím nestáhl žádný soubor.</td></tr>"; }
            document.getElementById('profDownloads').innerHTML = dlHtml;
            let sessHtml = "";
            if(data.sessions && data.sessions.length > 0) { data.sessions.forEach(s => { sessHtml += `<tr><td style="color: var(--success); font-weight:bold; white-space:nowrap;">🟢 ${s.start_time.split(' ')[1] || s.start_time}</td><td style="color: var(--danger); font-weight:bold; white-space:nowrap;">🔴 ${s.end_time.split(' ')[1] || s.end_time}</td></tr><tr><td colspan="2" style="color: var(--text-muted); padding-top:0; padding-bottom:10px; border-bottom:1px solid #334155; text-align:center;">${s.start_time.split(' ')[0]}</td></tr>`; }); } else { sessHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím žádná aktivita.</td></tr>"; }
            document.getElementById('profSessions').innerHTML = sessHtml;
        }).catch(e => { document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Spojení selhalo</span>"; });
    } catch(e) { alert("Chyba: " + e.message); }
}
function closeModal() { document.getElementById('editModal').style.display = 'none'; }
</script>
"""

HTML_HOME = """
<div class="home-wrap" style="text-align: center; padding: 60px 20px; max-width: 800px; margin: 0 auto;">
    <h1 style="color: var(--blue-main); font-size: 2.5em; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);">OFICIÁLNÍ STRÁNKA PROJEKTU OIS IDPK</h1>
    <div class="info-box" style="font-size: 1.1em; color: var(--text-main); line-height: 1.6; margin-bottom: 40px; background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 10px; border-left: 4px solid var(--blue-main); text-align: left;">
        <p style="margin-top:0;">Projekt OIS IDPK je fanouškovský software inspirovaný skutečnými vnitřními informačními panely, které se používají v autobusech Plzeňského kraje. Cílem projektu je co nejvěrněji napodobit jejich vzhled i způsob fungování.</p>
        <p>Software simuluje zobrazování zastávek, průběh celé linky i další informace, které běžně vidí cestující během jízdy. Díky tomu si můžeš jednoduše vyzkoušet, jak se panel chová při jízdě po trase, jak se postupně mění zastávky nebo jak vypadají informace o aktuální části linky.</p>
        <p style="margin-bottom:0;">Celý projekt vznikl z nadšení pro dopravu, technologie a informační systems ve veřejné dopravě. Projekt není oficiálním produktem ani službou dopravců nebo organizací veřejné dopravy a nijak s nimi nespolupracuje. Jedná se čistě o fanouškovský projekt vytvořený pro zábavu, experimentování a zájem o dopravní technologie.</p>
    </div>
    <a href="/download" class="btn" style="font-size: 18px; padding: 15px 40px; border-radius: 30px; box-shadow: 0 5px 15px rgba(56, 189, 248, 0.4);"><i class="fas fa-download"></i> Získat Software</a>
    <div style="margin-top: 50px;">
        <h2 style="color: var(--blue-main); margin-bottom: 20px; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4);">Ukázky z aplikace</h2>
        <div style="display: flex; flex-direction: column; gap: 25px; align-items: center;">
            <img src="/static/img/sc1.png" alt="Screenshot 1" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="/static/img/sc2.png" alt="Screenshot 2" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="/static/img/sc3.png" alt="Screenshot 3" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="/static/img/sc4.png" alt="Screenshot 4" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <div class="screenshot-pair" style="display: flex; justify-content: center; gap: 20px; width: 100%; max-width: 800px;">
                <img src="/static/img/sc5.png" alt="Screenshot 5" style="width: 48%; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
                <img src="/static/img/sc6.png" alt="Screenshot 6" style="width: 48%; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            </div>
        </div>
    </div>
    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 60px 0;">
    <div class="footer-box" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; background: var(--bg-panel); padding: 40px; border-radius: 15px; border: 1px solid #334155;">
        <img src="/static/img/datacorebot_n.png" alt="DataCoreBot Logo" style="max-width: 250px; height: auto; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5)); margin-bottom: 10px;">
        <div style="text-align: center; max-width: 600px;">
            <h3 style="color: var(--warning); margin-top: 0; font-size: 1.6em; text-shadow: 0 0 5px rgba(245, 158, 11, 0.5);">Poháněno systémem DataCoreBot</h3>
            <p style="color: var(--text-muted); font-size: 1em; line-height: 1.6; margin: 0 0 15px 0;">Celá infrastruktura, od databází po ověřování uživatelů, je bezpečně řízena a chráněna unikátním systémem DataCoreBot. Zajišťuje bleskovou synchronizaci dat, striktní Hardware ID (HWID) ochranu a nepřetržitý chod palubních počítačů.</p>
            <div style="display: inline-block; background: rgba(0,0,0,0.3); padding: 10px 20px; border-radius: 8px; border: 1px solid var(--blue-main);">
                <p style="color: var(--text-main); font-weight: bold; margin: 0; font-size: 1em; letter-spacing: 1px;"><i class="fas fa-code" style="color: var(--blue-main);"></i> Vytvořeno vývojářem <span style="color: var(--blue-main);">marekk_czz</span></p>
            </div>
        </div>
    </div>
</div>
"""

HTML_DOWNLOADS_MAIN = """
<div style="max-width: 650px; margin: 60px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: var(--text-main); margin-top: 0; display: flex; align-items: center; justify-content: center; gap: 15px; font-size: 26px;"><i class="fas fa-shield-alt" style="color: var(--blue-main); font-size: 30px;"></i> Oficiální distribuce softwaru</h2>
        <p style="color: var(--text-muted); line-height: 1.6; font-size: 15px; margin-top: 20px;">Z důvodu ochrany projektu a samotného softwaru jsme se rozhodli přesunout jeho distribuci na náš Discord server. Díky tomu máme větší kontrolu nad přístupem k softwaru a můžeme lépe zabránit jeho zneužití nebo neautorizovanému šíření.</p>
    </div>
    <div style="border: 1px solid #334155; border-radius: 10px; padding: 30px; text-align: center; background: rgba(15, 23, 42, 0.4);">
        <h3 style="color: var(--text-main); margin-top: 0; margin-bottom: 15px; font-size: 18px;">Jak získat software:</h3>
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Připojte se na náš Discord, ověřte, že nejste robot, a poté přejděte do kanálu 💾 • download, kde stačí postupovat podle pokynů DataCoreBota. 🚀</p>
        <a href="https://discord.gg/vmTagbC9mF" target="_blank" style="display: inline-block; transition: 0.3s; color: #5865F2; font-size: 90px; filter: drop-shadow(0 0 15px rgba(88, 101, 242, 0.4)); text-decoration: none;" onmouseover="this.style.transform='scale(1.1)'; this.style.filter='drop-shadow(0 0 25px rgba(88, 101, 242, 0.8))';" onmouseout="this.style.transform='scale(1)'; this.style.filter='drop-shadow(0 0 15px rgba(88, 101, 242, 0.4))';"><i class="fab fa-discord"></i></a>
    </div>
</div>
"""

HTML_TEAM = """
<style>
    .team-card { transition: all 0.3s ease; cursor: default; border: 1px solid #334155; }
    .team-card:hover { box-shadow: 0 0 25px rgba(56, 189, 248, 0.8) !important; transform: translateY(-10px) !important; border-color: var(--blue-main) !important; }
</style>
<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="color: var(--blue-main); font-size: 36px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);">Náš Tým</h1>
    <p style="color: var(--text-muted); font-size: 16px;">Lidé, kteří stojí za tímto projektem a starají se o jeho chod.</p>
</div>
<div style="display: flex; flex-wrap: wrap; gap: 30px; justify-content: center;">
    {% for member in team %}
    <div class="team-card" style="background-color: var(--bg-panel); border-radius: 10px; width: 300px; padding: 20px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
        {% set img_url = member.get('image_url', '') %}
        {% if 'hynek' in member.get('name', '').lower() %}
            {% set img_url = '/static/img/IMG_3650.jpg' %}
        {% endif %}
        <img src="{{ img_url }}" onerror="this.onerror=null; this.src='/static/img/datacorebot_pf-lepsi.png';" alt="Avatar" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid var(--blue-main); margin-bottom: 15px; background-color: var(--bg-dark);">
        <h3 style="color: var(--text-main); margin: 0 0 5px 0; font-size: 22px;">{{ member.get('name', '') }}</h3>
        <div style="color: var(--text-muted); font-size: 12px; margin-bottom: 15px;"><i class="fab fa-discord"></i> {{ member.get('discord_nick', '') }}</div>
        <div style="margin-bottom: 15px;">
            {% set roles_input = member.get('role_name', '').split(',') if member.get('role_name') else [] %}
            {% for r in roles_input %}
                {% set parts = r.split('|') %}
                {% set r_name = parts[0].strip() %}
                {% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                <span class="role-tag" style="color: {{ r_color }}; border: 1px solid {{ r_color }}; background-color: {{ r_color }}33;">{{ r_name }}</span>
            {% endfor %}
        </div>
        <p style="color: var(--text-muted); font-size: 14px; line-height: 1.5; font-style: italic;">"{{ member.get('description', '') }}"</p>
    </div>
    {% else %}
    <div style="color: var(--text-muted); width: 100%; text-align: center; padding: 50px;">Zatím zde nejsou žádní členové.</div>
    {% endfor %}
</div>
"""

HTML_PUBLIC_STATS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; flex-wrap: wrap; gap: 20px;">
    <h1 style="color: var(--blue-main); font-size: 36px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4); margin: 0;"><i class="fas fa-chart-line"></i> Globální Statistiky</h1>
    <form action="/stats" method="GET" style="display: flex; gap: 10px; align-items: center; background: var(--bg-panel); padding: 10px 15px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <i class="fas fa-search" style="color: var(--text-muted);"></i>
        <input type="text" name="q" placeholder="Hledat hráče (Nick nebo ID)..." style="margin: 0; padding: 8px; width: 250px; border: none; background: #0f172a; color: white; border-radius: 5px; font-size: 14px;" required>
        <button type="submit" class="btn" style="padding: 8px 15px; margin: 0;">Hledat</button>
    </form>
</div>
{% if searched_user %}
<div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(15, 23, 42, 0.9)); border: 2px solid var(--blue-main); border-radius: 12px; padding: 30px; margin-bottom: 40px; box-shadow: 0 0 20px rgba(56, 189, 248, 0.3);">
    <h2 style="color: var(--text-main); margin-top: 0; display: flex; align-items: center; gap: 15px;"><i class="fas fa-user-circle" style="font-size: 30px; color: var(--blue-main);"></i> Profil hráče: <span style="color: var(--blue-main);">{{ searched_user.get('nick', 'Neznámý') }}</span></h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">První registrace</div><div style="color: var(--text-main); font-size: 18px; font-weight: bold;">{{ searched_user.get('registered_at', 'Neznámé') }}</div></div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Nahráno hodin</div><div style="color: #f59e0b; font-size: 18px; font-weight: bold;">{{ (searched_user.get('total_time') or 0) // 60 }}h {{ (searched_user.get('total_time') or 0) % 60 }}m</div></div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Počet spuštění</div><div style="color: var(--success); font-size: 18px; font-weight: bold;">{{ searched_user.get('launch_count') or 0 }}x</div></div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Role</div><div style="color: var(--text-main); font-size: 18px; font-weight: bold;">{{ searched_user.get('role', 'User') }}</div></div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;"><div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Naposledy hráno</div><div style="color: var(--blue-main); font-size: 18px; font-weight: bold;">{% if searched_user.get('is_online') %}<span style="color: var(--success);">Nyní hraje</span>{% else %}{{ searched_user.get('last_active', 'Nikdy') }}{% endif %}</div></div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 30px;">
        <div style="background: var(--bg-dark); border-radius: 10px; border: 1px solid #334155; padding: 20px;">
            <h3 style="color: var(--blue-main); margin-top: 0; font-size: 18px;"><i class="fas fa-route"></i> Odjeté linky</h3>
            <div style="max-height: 250px; overflow-y: auto; padding-right: 10px;">
                {% if all_searched_user_lines %}
                    {% for l in all_searched_user_lines %}
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b;">
                        <span style="color: var(--text-main); font-weight: bold;">{{ l.line_name }}</span>
                        <span style="color: #10b981; font-weight: bold; background: rgba(16, 185, 129, 0.1); padding: 2px 8px; border-radius: 10px;">{{ l.play_count }}x</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="color: var(--text-muted); font-size: 14px;">Zatím neodjel žádnou linku.</div>
                {% endif %}
            </div>
        </div>
        <div style="background: var(--bg-dark); border-radius: 10px; border: 1px solid #334155; padding: 20px;">
            <h3 style="color: var(--warning); margin-top: 0; font-size: 18px;"><i class="fas fa-map-marker-alt"></i> Vyhlášené zastávky</h3>
            <div style="max-height: 250px; overflow-y: auto; padding-right: 10px;">
                {% if all_searched_user_stops %}
                    {% for s in all_searched_user_stops %}
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e293b;">
                        <span style="color: var(--text-main); font-weight: bold;">{{ s.stop_name }}</span>
                        <span style="color: #f59e0b; font-weight: bold; background: rgba(245, 158, 11, 0.1); padding: 2px 8px; border-radius: 10px;">{{ s.announce_count }}x</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="color: var(--text-muted); font-size: 14px;">Zatím nevyhlásil žádnou zastávku.</div>
                {% endif %}
            </div>
        </div>
    </div>
    <a href="/stats" class="btn btn-dark" style="margin-top: 20px; font-size: 12px;"><i class="fas fa-times"></i> Zavřít profil</a>
</div>
{% endif %}
<style>
.stat-card-hover { transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; background: linear-gradient(145deg, var(--bg-panel), #141e30); padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.3); flex: 1 1 230px; max-width: 320px; }
.stat-card-hover:hover, .stat-card-hover.highlight-active { transform: translateY(-10px) scale(1.05); box-shadow: 0 20px 40px rgba(0,0,0,0.6); border-color: var(--blue-main); z-index: 10; }
.stat-card-hover.highlight-active { border-color: #fcd34d; box-shadow: 0 0 30px rgba(252, 211, 77, 0.4); }
.stat-card-hover::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 3px; background: linear-gradient(90deg, transparent, var(--blue-main), transparent); transition: left 0.6s ease; }
.stat-card-hover:hover::before, .stat-card-hover.highlight-active::before { left: 100%; }
.stat-card-icon { font-size: 42px; margin-bottom: 15px; transition: transform 0.5s ease; }
.stat-card-hover:hover .stat-card-icon, .stat-card-hover.highlight-active .stat-card-icon { transform: scale(1.2); }
.stat-card-val { font-size: 38px; font-weight: 900; color: var(--text-main); line-height: 1.2; text-shadow: 0 0 10px rgba(255,255,255,0.1); }
.stat-card-label { color: var(--text-muted); font-size: 13px; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; margin-top: 5px; }
.stat-card-badge { font-size: 11px; font-weight: bold; background: rgba(0,0,0,0.4); padding: 4px 10px; border-radius: 20px; display: inline-block; margin-top: 10px; border: 1px solid #334155; }
.carousel-container { position: relative; width: 100%; height: 350px; overflow: hidden; margin-bottom: 40px; border-radius: 15px; box-sizing: border-box; }
.carousel-slide { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; transition: opacity 0.8s ease-in-out; pointer-events: none; display: flex; flex-direction: column; align-items: center; justify-content: center; box-sizing: border-box; }
.carousel-slide.active { opacity: 1; pointer-events: auto; }
.glow-blob-1 { position: absolute; top: -50px; left: -50px; width: 150px; height: 150px; filter: blur(60px); border-radius: 50%; z-index: 0; opacity: 0.6; }
.glow-blob-2 { position: absolute; bottom: -50px; right: -50px; width: 150px; height: 150px; filter: blur(60px); border-radius: 50%; z-index: 0; opacity: 0.6; }
</style>
<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 25px; margin-bottom: 40px;">
    <div class="stat-card-hover global-stat-card"><i class="fas fa-users stat-card-icon" style="color: var(--success); text-shadow: 0 0 15px rgba(16, 185, 129, 0.6);"></i><div class="stat-card-val">{{ activated_users }}</div><div class="stat-card-label">Aktivních uživatelů</div></div>
    <div class="stat-card-hover global-stat-card"><i class="fas fa-heart stat-card-icon" style="color: #ef4444; text-shadow: 0 0 15px rgba(239, 68, 68, 0.6);"></i><div class="stat-card-val">{{ total_supporters }}</div><div class="stat-card-label">Podporovatelů</div></div>
    <div class="stat-card-hover global-stat-card"><i class="fas fa-clock stat-card-icon" style="color: var(--warning); text-shadow: 0 0 15px rgba(245, 158, 11, 0.6);"></i><div class="stat-card-val">{{ total_hours }}h</div><div class="stat-card-label">Celkově nahráno</div><div class="stat-card-badge" style="color: var(--warning); border-color: rgba(245, 158, 11, 0.3);">Dnes: {{ today_time_str }} | Měsíc: {{ month_time_str }}</div></div>
    <div class="stat-card-hover global-stat-card"><i class="fas fa-rocket stat-card-icon" style="color: var(--blue-main); text-shadow: 0 0 15px rgba(56, 189, 248, 0.6);"></i><div class="stat-card-val">{{ total_launches }}x</div><div class="stat-card-label">Celkově spuštěno</div></div>
    <div class="stat-card-hover global-stat-card"><i class="fas fa-route stat-card-icon" style="color: #10b981; text-shadow: 0 0 15px rgba(16, 185, 129, 0.6);"></i><div class="stat-card-val">{{ total_lines_driven }}x</div><div class="stat-card-label">Odjetých linek</div></div>
    <div class="stat-card-hover global-stat-card"><i class="fas fa-map-marker-alt stat-card-icon" style="color: #a855f7; text-shadow: 0 0 15px rgba(168, 85, 247, 0.6);"></i><div class="stat-card-val">{{ total_stops_announced }}x</div><div class="stat-card-label">Vyhlášených zastávek</div></div>
</div>

<div class="carousel-container">
    <div class="carousel-slide active" style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(15, 23, 42, 0.9)); border: 1px solid #d97706; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div class="glow-blob-1" style="background: rgba(245, 158, 11, 0.3);"></div>
        <div class="glow-blob-2" style="background: rgba(245, 158, 11, 0.3);"></div>
        <div style="position: absolute; top: 20%; left: 50%; transform: translateX(-50%); width: 120px; height: 120px; background: rgba(252, 211, 77, 0.4); filter: blur(40px); border-radius: 50%; z-index: 0; animation: pulseShiny 3s infinite alternate;"></div>
        <div style="z-index: 1; display: flex; flex-direction: column; align-items: center; width: 100%;">
            <i class="fas fa-sun" style="font-size: 60px; color: #fcd34d; margin-bottom: 15px; position: relative; z-index: 2; text-shadow: none;"></i>
            <div style="color: #fcd34d; font-size: 16px; text-transform: uppercase; font-weight: 900; letter-spacing: 3px;">Dnešní Statistiky</div>
            <div style="display: flex; justify-content: center; gap: 40px; margin-top: 30px; flex-wrap: wrap; width: 100%;">
                <div style="background: rgba(0,0,0,0.5); padding: 20px; border-radius: 12px; border: 1px solid #334155; min-width: 250px; z-index: 2;">
                    <div style="color: var(--text-muted); font-size: 16px; text-transform: uppercase; margin-bottom: 10px;">Nejdéle hrál</div>
                    <div style="font-size: 32px; font-weight: 900; color: var(--text-main);">{{ top_today_time_nick }}</div>
                    <div style="color: #fcd34d; font-weight: 900; font-size: 20px; margin-top: 5px;">{{ top_today_time_val }} min</div>
                </div>
                <div style="background: rgba(0,0,0,0.5); padding: 20px; border-radius: 12px; border: 1px solid #334155; min-width: 250px; z-index: 2;">
                    <div style="color: var(--text-muted); font-size: 16px; text-transform: uppercase; margin-bottom: 10px;">Nejvíce spuštění</div>
                    <div style="font-size: 32px; font-weight: 900; color: var(--text-main);">{{ top_today_launch_nick }}</div>
                    <div style="color: #10b981; font-weight: 900; font-size: 20px; margin-top: 5px;">{{ top_today_launch_val }}x</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="carousel-slide" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(15, 23, 42, 0.9)); border: 1px solid #10b981; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div class="glow-blob-1" style="background: rgba(16, 185, 129, 0.3);"></div>
        <div class="glow-blob-2" style="background: rgba(16, 185, 129, 0.3);"></div>
        <div style="z-index: 1; display: flex; flex-direction: column; align-items: center; width: 100%;">
            <i class="fas fa-route" style="font-size: 50px; color: #10b981; text-shadow: 0 0 25px rgba(16, 185, 129, 1); margin-bottom: 15px;"></i>
            <div style="color: #10b981; font-size: 16px; text-transform: uppercase; font-weight: 900; letter-spacing: 3px;">TOP 5 - Odjeté Linky</div>
            <div style="display: flex; justify-content: center; gap: 20px; margin-top: 20px; flex-wrap: wrap;">
                {% for u in top_5_lines_users %}
                <div style="background: rgba(0,0,0,0.5); border: 1px solid #334155; padding: 15px; border-radius: 10px; width: 140px; z-index: 2;">
                    <div style="color: var(--text-main); font-weight: bold; font-size: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ u.nick }}</div>
                    <div style="color: #10b981; font-weight: 900; font-size: 22px; margin-top: 5px;">{{ u.count }}x</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <div class="carousel-slide" style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(15, 23, 42, 0.9)); border: 1px solid #a855f7; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div class="glow-blob-1" style="background: rgba(168, 85, 247, 0.3);"></div>
        <div class="glow-blob-2" style="background: rgba(168, 85, 247, 0.3);"></div>
        <div style="z-index: 1; display: flex; flex-direction: column; align-items: center; width: 100%;">
            <i class="fas fa-map-marker-alt" style="font-size: 50px; color: #a855f7; text-shadow: 0 0 25px rgba(168, 85, 247, 1); margin-bottom: 15px;"></i>
            <div style="color: #a855f7; font-size: 16px; text-transform: uppercase; font-weight: 900; letter-spacing: 3px;">TOP 5 - Vyhlášené Zastávky</div>
            <div style="display: flex; justify-content: center; gap: 20px; margin-top: 20px; flex-wrap: wrap;">
                {% for u in top_5_stops_users %}
                <div style="background: rgba(0,0,0,0.5); border: 1px solid #334155; padding: 15px; border-radius: 10px; width: 140px; z-index: 2;">
                    <div style="color: var(--text-main); font-weight: bold; font-size: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ u.nick }}</div>
                    <div style="color: #a855f7; font-weight: 900; font-size: 22px; margin-top: 5px;">{{ u.count }}x</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <div class="carousel-slide" style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(15, 23, 42, 0.9)); border: 1px solid #38bdf8; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div class="glow-blob-1" style="background: rgba(56, 189, 248, 0.3);"></div>
        <div class="glow-blob-2" style="background: rgba(56, 189, 248, 0.3);"></div>
        <div style="z-index: 1; display: flex; flex-direction: column; align-items: center; width: 100%;">
            <i class="fas fa-clock" style="font-size: 50px; color: #38bdf8; text-shadow: 0 0 25px rgba(56, 189, 248, 1); margin-bottom: 15px;"></i>
            <div style="color: #38bdf8; font-size: 16px; text-transform: uppercase; font-weight: 900; letter-spacing: 3px;">TOP 5 - Nahraný čas</div>
            <div style="display: flex; justify-content: center; gap: 20px; margin-top: 20px; flex-wrap: wrap;">
                {% for u in top_time %}
                <div style="background: rgba(0,0,0,0.5); border: 1px solid #334155; padding: 15px; border-radius: 10px; width: 140px; z-index: 2;">
                    <div style="color: var(--text-main); font-weight: bold; font-size: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ u.get('nick', 'Neznámý') }}</div>
                    <div style="color: #38bdf8; font-weight: 900; font-size: 18px; margin-top: 5px;">{{ (u.get('total_time') or 0) // 60 }}h</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 40px; margin-bottom: 40px;">
    <div style="background: var(--bg-panel); border-radius: 15px; border: 1px solid #334155; padding: 25px;">
        <h3 style="color: var(--text-main); margin-top: 0; display: flex; justify-content: space-between; align-items: center;">
            <span><i class="fas fa-route" style="color: #10b981;"></i> Seznam Linek</span>
            <span style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 3px 10px; border-radius: 20px; font-size: 12px;">{{ all_lines|length }}</span>
        </h3>
        <input type="text" id="lines-search" onkeyup="filterLines()" placeholder="Hledat linku..." style="width: 100%; padding: 10px 15px; margin-bottom: 20px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: white; box-sizing: border-box;">
        <div style="max-height: 400px; overflow-y: auto; padding-right: 10px;">
            {% for l in all_lines %}
            <div class="line-row" style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #1e293b;">
                <span style="color: var(--text-main); font-weight: bold; font-size: 16px;">{{ l.line_name }}</span>
                <span style="color: #10b981; font-weight: bold; background: rgba(16, 185, 129, 0.1); padding: 2px 10px; border-radius: 12px;">{{ l.play_count }}x odjeto</span>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div style="background: var(--bg-panel); border-radius: 15px; border: 1px solid #334155; padding: 25px;">
        <h3 style="color: var(--text-main); margin-top: 0; display: flex; justify-content: space-between; align-items: center;">
            <span><i class="fas fa-map-marker-alt" style="color: #a855f7;"></i> Seznam Zastávek</span>
            <span style="background: rgba(168, 85, 247, 0.2); color: #a855f7; padding: 3px 10px; border-radius: 20px; font-size: 12px;">{{ all_stops|length }}</span>
        </h3>
        <input type="text" id="stops-search" onkeyup="filterStops()" placeholder="Hledat zastávku..." style="width: 100%; padding: 10px 15px; margin-bottom: 20px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: white; box-sizing: border-box;">
        <div style="max-height: 400px; overflow-y: auto; padding-right: 10px;">
            {% for s in all_stops %}
            <div class="stop-row" style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #1e293b;">
                <span style="color: var(--text-main); font-weight: bold; font-size: 16px;">{{ s.stop_name }}</span>
                <span style="color: #a855f7; font-weight: bold; background: rgba(168, 85, 247, 0.1); padding: 2px 10px; border-radius: 12px;">{{ s.announce_count }}x vyhlášena</span>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filterLines(){let i=document.getElementById("lines-search").value.toUpperCase();document.querySelectorAll(".line-row").forEach(r=>{r.style.display=r.innerText.toUpperCase().indexOf(i)>-1?"flex":"none";});}
function filterStops(){let i=document.getElementById("stops-search").value.toUpperCase();document.querySelectorAll(".stop-row").forEach(r=>{r.style.display=r.innerText.toUpperCase().indexOf(i)>-1?"flex":"none";});}
document.addEventListener("DOMContentLoaded", function() {
    const slides = document.querySelectorAll('.carousel-slide');
    if(slides.length > 0) {
        let currentSlide = 0;
        setInterval(() => {
            slides[currentSlide].classList.remove('active');
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].classList.add('active');
        }, 6000);
    }
    
    // Rotating Highlight logic
    const globalCards = document.querySelectorAll('.global-stat-card');
    if(globalCards.length > 0) {
        let highlightIndex = 0;
        setInterval(() => {
            globalCards.forEach(c => c.classList.remove('highlight-active'));
            globalCards[highlightIndex].classList.add('highlight-active');
            highlightIndex = (highlightIndex + 1) % globalCards.length;
        }, 3000); // changes every 3 seconds
    }
});
</script>
"""

HTML_SUPPORTERS = """
<style>
/* === PODPOROVATELÉ - EPIC PRESTIGE REDESIGN === */
.supporters-page-wrap {
  max-width: 1180px;
  margin: 0 auto 70px auto;
  padding: 0 20px;
}

/* Hero Section */
.supporters-hero {
  position: relative;
  text-align: center;
  padding: 40px 25px 30px 25px;
  margin-bottom: 40px;
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 18px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 50px;
  color: #fcd34d;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 18px;
  box-shadow: 0 2px 10px rgba(245, 158, 11, 0.15);
}

.hero-title {
  color: #ffffff;
  font-size: 38px;
  font-weight: 900;
  letter-spacing: -0.8px;
  margin: 0 0 10px 0;
  line-height: 1.2;
}

.hero-subtitle {
  color: #38bdf8;
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px 0;
  letter-spacing: 0.2px;
}

.hero-desc {
  color: #94a3b8;
  font-size: 16px;
  max-width: 780px;
  margin: 0 auto 26px auto;
  line-height: 1.65;
}

/* Notice Cards Grid */
.hero-notices {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
  max-width: 860px;
  margin: 0 auto 30px auto;
  text-align: left;
}

.notice-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}

.notice-box.box-gold {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  color: #fef3c7;
}
.notice-box.box-gold i {
  color: #f59e0b;
  font-size: 18px;
  margin-top: 2px;
  flex-shrink: 0;
}

.notice-box.box-blue {
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.25);
  color: #e0f2fe;
}
.notice-box.box-blue i {
  color: #38bdf8;
  font-size: 18px;
  margin-top: 2px;
  flex-shrink: 0;
}
.notice-link {
  color: #38bdf8;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.notice-link:hover {
  color: #7dd3fc;
}

/* Action Buttons */
.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-premium {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #ffffff;
  padding: 14px 30px;
  font-size: 16px;
  font-weight: 800;
  border-radius: 14px;
  text-decoration: none;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 20px rgba(217, 119, 6, 0.35);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.btn-premium:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(217, 119, 6, 0.5);
  color: #ffffff;
}

.btn-claim {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: rgba(30, 41, 59, 0.85);
  color: #f1f5f9;
  padding: 14px 26px;
  font-size: 16px;
  font-weight: 700;
  border-radius: 14px;
  text-decoration: none;
  border: 1px solid #334155;
  transition: all 0.25s ease;
}
.btn-claim:hover {
  background: #334155;
  color: #38bdf8;
  border-color: #38bdf8;
  transform: translateY(-2px);
}

/* === TIERS SECTION === */
.tiers-section {
  margin-bottom: 60px;
}
.section-heading-wrap {
  text-align: center;
  margin-bottom: 30px;
}
.section-title {
  color: #ffffff;
  font-size: 26px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 8px 0;
}
.section-subtitle {
  color: #64748b;
  font-size: 15px;
  margin: 0;
}

.tiers-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
  align-items: stretch;
}

.tier-card {
  position: relative;
  background: rgba(30, 41, 59, 0.55);
  border: 1px solid #334155;
  border-radius: 20px;
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.tier-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 35px rgba(0, 0, 0, 0.5);
}

/* Tier 3: Mega */
.tier-card.tier-card-3 {
  border-color: rgba(239, 68, 68, 0.5);
  background: linear-gradient(180deg, rgba(127, 29, 29, 0.25) 0%, rgba(30, 41, 59, 0.6) 80%);
  box-shadow: 0 8px 28px rgba(220, 38, 38, 0.15);
}
.tier-card.tier-card-3:hover {
  border-color: rgba(239, 68, 68, 0.85);
  box-shadow: 0 16px 45px rgba(220, 38, 38, 0.3);
}

/* Tier 2: Velký (Featured) */
.tier-card.tier-card-2 {
  border-color: rgba(245, 158, 11, 0.55);
  background: linear-gradient(180deg, rgba(180, 83, 9, 0.25) 0%, rgba(30, 41, 59, 0.65) 80%);
  box-shadow: 0 10px 32px rgba(245, 158, 11, 0.2);
  transform: scale(1.02);
}
.tier-card.tier-card-2:hover {
  transform: scale(1.02) translateY(-6px);
  border-color: rgba(245, 158, 11, 0.9);
  box-shadow: 0 20px 45px rgba(245, 158, 11, 0.35);
}

/* Tier 1: Normal */
.tier-card.tier-card-1 {
  border-color: rgba(56, 189, 248, 0.35);
  background: linear-gradient(180deg, rgba(14, 165, 233, 0.12) 0%, rgba(30, 41, 59, 0.55) 80%);
}
.tier-card.tier-card-1:hover {
  border-color: rgba(56, 189, 248, 0.7);
  box-shadow: 0 16px 35px rgba(14, 165, 233, 0.2);
}

.tier-ribbon {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  background: linear-gradient(90deg, #f59e0b, #d97706);
  color: #0f172a;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  text-align: center;
  padding: 4px 10px;
}
.tier-ribbon.ribbon-mega {
  background: linear-gradient(90deg, #ef4444, #b91c1c);
  color: #ffffff;
}

.tier-top {
  margin-top: 8px;
  text-align: center;
}

.tier-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.pill-3 { background: rgba(239, 68, 68, 0.25); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.5); }
.pill-2 { background: rgba(245, 158, 11, 0.25); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.5); }
.pill-1 { background: rgba(56, 189, 248, 0.2); color: #bae6fd; border: 1px solid rgba(56, 189, 248, 0.4); }

.tier-price {
  font-size: 26px;
  font-weight: 900;
  color: #ffffff;
  letter-spacing: -0.5px;
  margin: 0 0 6px 0;
}
.tier-approx {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 600;
  margin: 0 0 20px 0;
}

.tier-perks-box {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 18px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.tier-perk-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13.5px;
  color: #cbd5e1;
  line-height: 1.45;
}
.tier-perk-row i {
  color: #10b981;
  font-size: 13px;
  margin-top: 3px;
  flex-shrink: 0;
}

.tier-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px 18px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 800;
  text-decoration: none;
  transition: all 0.2s ease;
  box-sizing: border-box;
}
.tier-btn-3 {
  background: linear-gradient(135deg, #ef4444, #b91c1c);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.35);
}
.tier-btn-3:hover {
  background: linear-gradient(135deg, #f87171, #dc2626);
  color: #ffffff;
  transform: translateY(-2px);
}
.tier-btn-2 {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35);
}
.tier-btn-2:hover {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #ffffff;
  transform: translateY(-2px);
}
.tier-btn-1 {
  background: rgba(30, 41, 59, 0.85);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
}
.tier-btn-1:hover {
  background: rgba(56, 189, 248, 0.15);
  color: #ffffff;
  border-color: #38bdf8;
  transform: translateY(-2px);
}

.thank-you-banner {
  margin-top: 25px;
  text-align: center;
  padding: 16px 20px;
  background: rgba(30, 41, 59, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  color: #f1f5f9;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

/* === EPIC SÍŇ SLÁVY (HALL OF FAME) === */
.supporters-wall-section {
  margin-top: 15px;
}

.wall-header-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 24px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.wall-title {
  color: #ffffff;
  font-size: 28px;
  font-weight: 900;
  margin: 0 0 6px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.wall-title i {
  color: #f59e0b;
}
.wall-subtitle {
  color: #94a3b8;
  font-size: 15px;
  margin: 0;
}

.epic-supporters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
}

/* Epic Cards (NO AVATARS - HUGE PROMINENT NAMES) */
.epic-card {
  position: relative;
  background: rgba(20, 26, 40, 0.85);
  border-radius: 20px;
  padding: 26px;
  border: 1px solid #334155;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.epic-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.6);
}

/* Tier 3 Epic Card - MEGA PODPOROVATEL */
.epic-card.epic-tier-3 {
  background: radial-gradient(circle at 50% 0%, rgba(220, 38, 38, 0.38) 0%, rgba(35, 15, 25, 0.96) 65%, rgba(15, 23, 42, 0.98) 100%);
  border: 2px solid rgba(239, 68, 68, 0.85);
  box-shadow: 0 16px 45px rgba(220, 38, 38, 0.35), 0 0 35px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}
.epic-card.epic-tier-3::after {
  content: '👑';
  position: absolute;
  right: 16px;
  bottom: 8px;
  font-size: 80px;
  opacity: 0.12;
  pointer-events: none;
  line-height: 1;
}
.epic-card.epic-tier-3:hover {
  transform: translateY(-7px) scale(1.01);
  border-color: #f87171;
  box-shadow: 0 24px 60px rgba(220, 38, 38, 0.55), 0 0 50px rgba(239, 68, 68, 0.35);
}

/* Tier 2 Epic Card - VELKÝ PODPOROVATEL */
.epic-card.epic-tier-2 {
  background: radial-gradient(circle at 50% 0%, rgba(245, 158, 11, 0.32) 0%, rgba(35, 25, 20, 0.96) 65%, rgba(15, 23, 42, 0.98) 100%);
  border: 2px solid rgba(245, 158, 11, 0.8);
  box-shadow: 0 14px 40px rgba(245, 158, 11, 0.25), 0 0 25px rgba(245, 158, 11, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}
.epic-card.epic-tier-2::after {
  content: '🚀';
  position: absolute;
  right: 16px;
  bottom: 8px;
  font-size: 75px;
  opacity: 0.1;
  pointer-events: none;
  line-height: 1;
}
.epic-card.epic-tier-2:hover {
  transform: translateY(-6px) scale(1.01);
  border-color: #fbbf24;
  box-shadow: 0 20px 50px rgba(245, 158, 11, 0.45), 0 0 40px rgba(245, 158, 11, 0.25);
}

/* Tier 1 Card - Clean & Basic */
.epic-card.epic-tier-1 {
  background: rgba(20, 28, 45, 0.75);
  border: 1px solid rgba(56, 189, 248, 0.25);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
}
.epic-card.epic-tier-1:hover {
  transform: translateY(-4px);
  border-color: rgba(56, 189, 248, 0.6);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.5);
}

.epic-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 18px;
}

.epic-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 14px;
  border-radius: 20px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}
.epic-badge.tier-3-badge {
  background: linear-gradient(90deg, #ef4444, #dc2626);
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 950;
  padding: 6px 16px;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.6);
}
.epic-badge.tier-2-badge {
  background: linear-gradient(90deg, #f59e0b, #d97706);
  color: #0f172a;
  font-size: 12px;
  font-weight: 950;
  padding: 6px 15px;
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.55);
}
.epic-badge.tier-1-badge {
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #38bdf8;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 12px;
}

.epic-amount-pill {
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.tier-3-amount {
  border: 1px solid rgba(239, 68, 68, 0.65);
  background: rgba(25, 12, 18, 0.9);
  color: #fecaca;
  font-size: 15px;
  font-weight: 900;
  padding: 6px 14px;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.35);
}
.tier-2-amount {
  border: 1px solid rgba(245, 158, 11, 0.65);
  background: rgba(25, 18, 12, 0.9);
  color: #fde68a;
  font-size: 14px;
  font-weight: 900;
  padding: 6px 13px;
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
}
.tier-1-amount {
  border: 1px solid rgba(56, 189, 248, 0.25);
  background: rgba(15, 23, 42, 0.75);
  color: #bae6fd;
  font-size: 13px;
  font-weight: 700;
  padding: 5px 12px;
}

/* BIG SUPPORTER NAME */
.epic-name-box {
  margin-bottom: 12px;
}
.epic-supp-name {
  font-weight: 900;
  line-height: 1.2;
  margin: 0;
  word-break: break-word;
}

/* Tier 3 Name: Colossal 34px with Radiant Fiery Gold/Crimson */
.epic-tier-3 .epic-supp-name {
  font-size: 34px;
  font-weight: 950;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #ffffff 0%, #fef08a 30%, #fca5a5 65%, #ef4444 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 22px rgba(239, 68, 68, 0.8)) drop-shadow(0 0 40px rgba(245, 158, 11, 0.45));
}

/* Tier 2 Name: Huge 28px with Glowing Amber/Gold */
.epic-tier-2 .epic-supp-name {
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, #ffffff 0%, #fde68a 45%, #f59e0b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 18px rgba(245, 158, 11, 0.65));
}

/* Tier 1 Name: Clean, basic, crisp 21px */
.epic-tier-1 .epic-supp-name {
  font-size: 21px;
  font-weight: 700;
  color: #f8fafc;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}

.epic-supp-date {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}

.epic-supp-msg {
  position: relative;
  font-size: 14px;
  color: #cbd5e1;
  font-style: italic;
  background: rgba(15, 23, 42, 0.55);
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  line-height: 1.5;
  margin-top: 14px;
}
.epic-supp-msg i {
  color: rgba(255, 255, 255, 0.3);
  margin-right: 6px;
}

/* Empty State */
.supporters-empty {
  text-align: center;
  padding: 55px 25px;
  background: rgba(30, 41, 59, 0.35);
  border-radius: 20px;
  border: 1px dashed rgba(245, 158, 11, 0.3);
  margin: 10px 0 30px 0;
}
.empty-icon-wrap {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #f59e0b;
  margin: 0 auto 18px auto;
  border: 1px solid rgba(245, 158, 11, 0.3);
  box-shadow: 0 0 25px rgba(245, 158, 11, 0.2);
}
.empty-title {
  color: #ffffff;
  font-size: 20px;
  font-weight: 800;
  margin: 0 0 10px 0;
}
.empty-text {
  color: #94a3b8;
  font-size: 15px;
  max-width: 540px;
  margin: 0 auto 24px auto;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .tiers-grid {
    grid-template-columns: 1fr;
  }
  .tier-card.tier-card-2 {
    transform: none;
  }
  .tier-card.tier-card-2:hover {
    transform: translateY(-6px);
  }
}
@media (max-width: 768px) {
  .supporters-hero {
    padding: 35px 15px 25px 15px;
  }
  .hero-title {
    font-size: 28px;
  }
  .hero-subtitle {
    font-size: 16px;
  }
  .hero-desc {
    font-size: 14.5px;
  }
  .hero-notices {
    grid-template-columns: 1fr;
  }
  .btn-premium, .btn-claim {
    width: 100%;
    justify-content: center;
  }
  .epic-supporters-grid {
    grid-template-columns: 1fr;
  }
  .epic-tier-3 .epic-supp-name {
    font-size: 28px;
  }
  .epic-tier-2 .epic-supp-name {
    font-size: 24px;
  }
  .epic-tier-1 .epic-supp-name {
    font-size: 19px;
  }
}
</style>

<div class="supporters-page-wrap">
  <!-- Hero Section -->
  <div class="supporters-hero">
    <h1 class="hero-title"><i class="fas fa-heart" style="color: #ef4444; margin-right: 8px;"></i> Podpora projektu OIS IDPK</h1>
    <div class="hero-subtitle">Neoficiální software inspirovaný reálnou předlohou.</div>
    <p class="hero-desc">Vítejte na stránce podpory projektu OIS IDPK. Pokud chcete projekt podpořit, můžete si vybrat jednu z možností níže. Každá podpora mi pomáhá pokračovat ve vývoji a přinášet nové funkce.</p>

    <!-- Info & Warning Callout Notices -->
    <div class="hero-notices">
      <div class="notice-box box-gold">
        <i class="fas fa-lightbulb"></i>
        <div><b>Trvalé výhody:</b> Podpora je jednorázová a všechny získané výhody vám zůstávají napořád.</div>
      </div>
      <div class="notice-box box-blue">
        <i class="fab fa-discord"></i>
        <div><b>Předání výhod:</b> Role a přístupy na Discordu vám po odeslání podpory nastaví majitel projektu osobně.</div>
      </div>
    </div>
    
    <div class="hero-actions">
      <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="btn-premium">
        <i class="fas fa-coffee"></i> Podpořit na Buy Me a Coffee
      </a>
    </div>
  </div>

  <!-- Tiers Section: Co za podporu získáte -->
  <div class="tiers-section">
    <div class="section-heading-wrap">
      <h2 class="section-title"><i class="fas fa-gem" style="color:#f59e0b;"></i> Co za podporu získáte</h2>
      <p class="section-subtitle">Každý příspěvek pomáhá pokračovat ve vývoji a přinášet nové funkce</p>
    </div>
    
    <div class="tiers-grid">
      <!-- Tier 1: Podporovatel (3 $ / ~65 Kč) -->
      <div class="tier-card tier-card-1">
        <div>
          <div class="tier-top">
            <div class="tier-badge-pill pill-1"><i class="fas fa-star"></i> PODPOROVATEL</div>
            <div class="tier-price">3 $</div>
            <div class="tier-approx">~65 Kč • Jednorázová podpora</div>
          </div>
          
          <div class="tier-perks-box">
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>Beta Tester</b> na Discordu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k novým verzím dříve než ostatní</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k neveřejným verzím softwaru</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>PODPOROVATEL</b> na Discordu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Uvedení jména v softwaru a na stránce projektu</span></div>
          </div>
        </div>
        
        <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="tier-btn tier-btn-1">
          <i class="fas fa-coffee"></i> Podpořit 3 $ (~65 Kč)
        </a>
      </div>

      <!-- Tier 2: Velký podporovatel (9 $ / ~195 Kč) - DOPORUČENO -->
      <div class="tier-card tier-card-2">
        <div class="tier-ribbon">🔥 NEJLEPŠÍ POMĚR PODPORY A VÝHOD</div>
        <div>
          <div class="tier-top">
            <div class="tier-badge-pill pill-2"><i class="fas fa-rocket"></i> VELKÝ PODPOROVATEL</div>
            <div class="tier-price">9 $</div>
            <div class="tier-approx">~195 Kč • Jednorázová podpora</div>
          </div>
          
          <div class="tier-perks-box">
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>Beta Tester</b> na Discordu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k novým verzím dříve než ostatní</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k neveřejným verzím softwaru</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Uvedení jména v softwaru a na stránce projektu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span><b>Vytvoření speciální linky na přání</b> (po domluvě na Discordu)</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Prioritní odpověď na dotazy / pomoc</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Velké poděkování od majitele</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>VELKÝ PODPOROVATEL</b> na Discordu</span></div>
          </div>
        </div>
        
        <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="tier-btn tier-btn-2">
          <i class="fas fa-rocket"></i> Podpořit 9 $ (~195 Kč)
        </a>
      </div>

      <!-- Tier 3: Mega podporovatel (15 $ / ~325 Kč) -->
      <div class="tier-card tier-card-3">
        <div class="tier-ribbon ribbon-mega">👑 PRESTIŽNÍ PODPORA</div>
        <div>
          <div class="tier-top">
            <div class="tier-badge-pill pill-3"><i class="fas fa-crown"></i> MEGA PODPOROVATEL</div>
            <div class="tier-price">15 $</div>
            <div class="tier-approx">~325 Kč • Jednorázová podpora</div>
          </div>
          
          <div class="tier-perks-box">
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>Beta Tester</b> na Discordu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k novým verzím dříve než ostatní</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Přístup k neveřejným verzím softwaru</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Uvedení jména v softwaru a na stránce projektu</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span><b>Vytvoření speciální linky na přání</b> (po domluvě na Discordu)</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Prioritní odpověď na dotazy / pomoc</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Velké poděkování od majitele</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span><b>Zvýrazněné jméno mezi hlavními podporovateli</b></span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Osobní poděkování</span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span><b>Možnost spolupráce nebo pomoci na vašem projektu</b></span></div>
            <div class="tier-perk-row"><i class="fas fa-check-circle"></i> <span>Role <b>MEGA PODPOROVATEL</b> na Discordu</span></div>
          </div>
        </div>
        
        <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="tier-btn tier-btn-3">
          <i class="fas fa-crown"></i> Podpořit 15 $ (~325 Kč)
        </a>
      </div>
    </div>

    <!-- Thank you footer -->
    <div class="thank-you-banner">
      <i class="fas fa-heart" style="color:#ef4444;"></i>
      <span>Děkuji všem, kteří projekt podporují – bez vás by to nešlo!</span>
    </div>
  </div>

  <!-- Supporters Wall / Síň slávy -->
  <div class="supporters-wall-section">
    <div class="wall-header-wrap">
      <div>
        <h2 class="wall-title"><i class="fas fa-trophy"></i> Síň slávy</h2>
        <p class="wall-subtitle">Čestné místo pro hrdiny, kteří umožňují vývoj a provoz projektu OIS IDPK</p>
      </div>
      <a href="https://buymeacoffee.com/marekk_czz" target="_blank" style="color:#f59e0b; font-size:14px; font-weight:800; text-decoration:none; display:inline-flex; align-items:center; gap:6px;">
        Vstoupit do Síně slávy <i class="fas fa-arrow-right"></i>
      </a>
    </div>

    <div class="epic-supporters-grid">
      {% for s in supporters %}
        {% set tier_class = 'epic-tier-3' if s.tier == 3 else ('epic-tier-2' if s.tier == 2 else 'epic-tier-1') %}
        {% set badge_icon = 'fa-crown' if s.tier == 3 else ('fa-rocket' if s.tier == 2 else 'fa-star') %}
        {% set badge_class = 'tier-3-badge' if s.tier == 3 else ('tier-2-badge' if s.tier == 2 else 'tier-1-badge') %}
        {% set amount_class = 'tier-3-amount' if s.tier == 3 else ('tier-2-amount' if s.tier == 2 else 'tier-1-amount') %}
        {% set badge_text = 'MEGA PODPOROVATEL' if s.tier == 3 else ('VELKÝ PODPOROVATEL' if s.tier == 2 else 'PODPOROVATEL') %}
        
        <div class="epic-card {{ tier_class }}">
          <div>
            <div class="epic-card-header">
              <div class="epic-badge {{ badge_class }}"><i class="fas {{ badge_icon }}"></i> {{ badge_text }}</div>
              {% if s.get('amount') %}
              <div class="epic-amount-pill {{ amount_class }}">{{ s.get('amount') }}</div>
              {% endif %}
            </div>
            
            <div class="epic-name-box">
              <h3 class="epic-supp-name">{{ s.get('name', 'Anonymní Hrdina') }}</h3>
              {% if s.get('created_at') %}
              <div class="epic-supp-date"><i class="far fa-calendar-alt"></i> {{ s.get('created_at') }}</div>
              {% endif %}
            </div>
          </div>
          
          {% if s.get('message') %}
          <div class="epic-supp-msg">
            <i class="fas fa-quote-left"></i> {{ s.get('message') }}
          </div>
          {% endif %}
        </div>
      {% else %}
        <div style="grid-column: 1 / -1;">
          <div class="supporters-empty">
            <div class="empty-icon-wrap"><i class="fas fa-trophy"></i></div>
            <h3 class="empty-title">Síň slávy zatím čeká na svého prvního hrdinu</h3>
            <p class="empty-text">Zatím zde nejsou žádní zapsaní podporovatelé. Buďte první, jehož jméno bude navždy vyryto v Síni slávy projektu OIS IDPK!</p>
            <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="btn-premium">
              <i class="fas fa-coffee"></i> Podpořit na Buy Me a Coffee
            </a>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</div>
"""

HTML_CLAIM = """
<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; border-top: 4px solid var(--blue-main); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <h2 style="color: var(--blue-main); text-align: center; margin-top: 0;"><i class="fas fa-gift"></i> Vyzvednutí VIP Role</h2>
    <p style="color: var(--text-muted); font-size: 14px; text-align: center; margin-bottom: 30px;">Zadejte jméno, pod kterým jste před malou chvílí poslali příspěvek na Buy Me a Coffee, a Váš Discord Nick.</p>
    <form method="POST">
        <label style="color: var(--text-muted); font-size: 12px; font-weight: bold;">JMÉNO ZADANÉ NA BUY ME A COFFEE</label>
        <input type="text" name="bmac_name" placeholder="Např. Jan Novák" required style="margin-bottom: 20px;">
        <label style="color: var(--text-muted); font-size: 12px; font-weight: bold; display: block;">VÁŠ DISCORD NICK</label>
        <input type="text" name="discord_nick" placeholder="Např. marekk_czz" required>
        <button type="submit" class="btn" style="width: 100%; margin-top: 20px; font-size: 16px; padding: 15px;"><i class="fab fa-discord"></i> Propojit a získat roli</button>
    </form>
</div>
"""

HTML_STATS = """
<style>
.stats-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 15px;
}
.tab-btn {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}
.tab-btn:hover {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.4);
}
.tab-btn.active {
  background: #0284c7;
  color: #ffffff;
  border-color: #38bdf8;
  box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
}
.pulse-online {
  display: inline-block;
  width: 10px;
  height: 10px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulse-dot 1.8s infinite;
}
@keyframes pulse-dot {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.stats-table th {
  text-align: left;
  padding: 10px 12px;
  color: #64748b;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #334155;
}
.stats-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  color: #e2e8f0;
}
.stats-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}
.badge-path {
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 2px 7px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
}
.badge-role {
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: bold;
}
</style>

<div class="stats-header-bar">
  <div>
    <h2 style="margin: 0; color: var(--text-main); display: flex; align-items: center; gap: 10px;">
      <i class="fas fa-chart-line" style="color:var(--blue-main);"></i> Statistiky Návštěvnosti
    </h2>
    <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">
      Přehled v reálném čase pro Veřejný Web i Desktopovou Aplikaci (OIS IDPK)
    </div>
  </div>
  <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
    <div style="display: flex; background: rgba(0,0,0,0.4); padding: 4px; border-radius: 10px; border: 1px solid #334155;">
      <button type="button" class="tab-btn active" id="tab-all" onclick="switchStatsView('all')"><i class="fas fa-columns"></i> Vše vedle sebe</button>
      <button type="button" class="tab-btn" id="tab-web" onclick="switchStatsView('web')"><i class="fas fa-globe"></i> Pouze Web</button>
      <button type="button" class="tab-btn" id="tab-app" onclick="switchStatsView('app')"><i class="fas fa-desktop"></i> Pouze Aplikace</button>
    </div>
    <form action="/dashboard/stats/clear_web" method="POST" style="margin:0;" onsubmit="return confirm('OPRAVDU SMAZAT HISTORII NÁVŠTĚV WEBU?\\n\\nTato akce vymaže pouze staré záznamy zobrazení webu. Data hráčů, herní statistiky a relace aplikace zůstanou 100% zachovány! Pokračovat?');">
      <button type="submit" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #ef4444; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: bold; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s;" onmouseover="this.style.background='#ef4444'; this.style.color='white';" onmouseout="this.style.background='rgba(239, 68, 68, 0.15)'; this.style.color='#ef4444';" title="Smazat dosavadní záznamy návštěv webu">
        <i class="fas fa-trash-alt"></i> Vymazat historii webu
      </button>
    </form>
    <button onclick="location.reload()" style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); color: #38bdf8; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: bold; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s;" onmouseover="this.style.background='rgba(56, 189, 248, 0.25)';" onmouseout="this.style.background='rgba(56, 189, 248, 0.15)';" title="Znovu načíst data">
      <i class="fas fa-sync-alt"></i> Obnovit
    </button>
  </div>
</div>

<!-- HLAVNÍ METRIKY (KPI KARTY) -->
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
  <!-- Web Celkem -->
  <div style="background: var(--bg-panel); padding: 18px 20px; border-radius: 12px; border: 1px solid #334155; border-top: 4px solid #38bdf8; display: flex; align-items: center; justify-content: space-between;">
    <div>
      <div style="color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Web: Unikátní zobrazení</div>
      <div style="font-size: 32px; font-weight: 900; color: #f8fafc; margin-top: 4px;">{{ web_total_visits }}</div>
      <div style="color: #38bdf8; font-size: 11px; margin-top: 2px;">Dnes: <b>{{ web_today_visits }}</b></div>
    </div>
    <div style="width: 48px; height: 48px; border-radius: 10px; background: rgba(56, 189, 248, 0.12); display: flex; align-items: center; justify-content: center; color: #38bdf8; font-size: 22px;">
      <i class="fas fa-globe"></i>
    </div>
  </div>

  <!-- Web za 7 dní -->
  <div style="background: var(--bg-panel); padding: 18px 20px; border-radius: 12px; border: 1px solid #334155; border-top: 4px solid #10b981; display: flex; align-items: center; justify-content: space-between;">
    <div>
      <div style="color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Web: Za posledních 7 dní</div>
      <div style="font-size: 32px; font-weight: 900; color: #10b981; margin-top: 4px;">{{ web_last_7_days }}</div>
      <div style="color: #64748b; font-size: 11px; margin-top: 2px;">Aktivita návštěvníků</div>
    </div>
    <div style="width: 48px; height: 48px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); display: flex; align-items: center; justify-content: center; color: #10b981; font-size: 22px;">
      <i class="fas fa-calendar-week"></i>
    </div>
  </div>

  <!-- App Celkem -->
  <div style="background: var(--bg-panel); padding: 18px 20px; border-radius: 12px; border: 1px solid #334155; border-top: 4px solid #8b5cf6; display: flex; align-items: center; justify-content: space-between;">
    <div>
      <div style="color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Aplikace: Spuštění celkem</div>
      <div style="font-size: 32px; font-weight: 900; color: #c4b5fd; margin-top: 4px;">{{ app_total_launches }}</div>
      <div style="color: #a78bfa; font-size: 11px; margin-top: 2px;">Dnes spuštěno: <b>{{ app_today_launches }}x</b></div>
    </div>
    <div style="width: 48px; height: 48px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); display: flex; align-items: center; justify-content: center; color: #a78bfa; font-size: 22px;">
      <i class="fas fa-rocket"></i>
    </div>
  </div>

  <!-- App Online -->
  <div style="background: var(--bg-panel); padding: 18px 20px; border-radius: 12px; border: 1px solid #334155; border-top: 4px solid #f59e0b; display: flex; align-items: center; justify-content: space-between;">
    <div>
      <div style="color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
        <span class="pulse-online"></span> Aplikace: Hráči Online
      </div>
      <div style="font-size: 32px; font-weight: 900; color: #f59e0b; margin-top: 4px;">{{ app_online_count }}</div>
      <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Odehráno: <b>{{ app_total_hours }}h</b></div>
    </div>
    <div style="width: 48px; height: 48px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); display: flex; align-items: center; justify-content: center; color: #f59e0b; font-size: 22px;">
      <i class="fas fa-gamepad"></i>
    </div>
  </div>
</div>

<!-- DVA HLAVNÍ SLOUPCE: WEB (VLEVO) A APLIKACE (VPRAVO) -->
<div id="stats-grid-container" style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; align-items: start;">

  <!-- ═══════════════ SLOUPEC 1: STATISTIKY WEBU ═══════════════ -->
  <div id="col-web" style="display: flex; flex-direction: column; gap: 20px;">
    
    <!-- Hlavička sekce Web -->
    <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 12px 18px; display: flex; align-items: center; gap: 10px;">
      <i class="fas fa-globe" style="color: #38bdf8; font-size: 18px;"></i>
      <h3 style="margin: 0; color: #ffffff; font-size: 15px; font-weight: bold;">Statistiky Veřejného Webu</h3>
      <span style="margin-left: auto; background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: bold;">Reálné IP & Lokace</span>
    </div>

    <!-- Grafy webu -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #38bdf8; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-calendar-week"></i> Návštěvnost webu za 7 dní
      </h4>
      <div style="position: relative; height: 210px; width: 100%;">
        <canvas id="chartWeb7d"></canvas>
      </div>
    </div>

    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #38bdf8; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-clock"></i> Dnešní návštěvy webu po hodinách
      </h4>
      <div style="position: relative; height: 180px; width: 100%;">
        <canvas id="chartWeb24h"></canvas>
      </div>
    </div>

    <!-- Návštěvnost podle států -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #f59e0b; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-flag"></i> Návštěvníci podle států a regionů
      </h4>
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        {% for cc, data in country_totals.items() %}
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; padding: 8px 14px; border-radius: 8px; display: flex; align-items: center; gap: 8px;">
          <img src="{{ data.flag }}" alt="" style="width: 20px; height: 15px; border-radius: 2px; object-fit: cover;">
          <span style="color: #ffffff; font-weight: 600; font-size: 13px;">{{ data.name }}</span>
          <span style="background: #0284c7; color: #ffffff; padding: 1px 7px; border-radius: 10px; font-weight: 900; font-size: 11px;">{{ data.count }}</span>
        </div>
        {% else %}
        <div style="color: #64748b; font-size: 13px;">Zatím žádná zaznamenaná data.</div>
        {% endfor %}
      </div>
    </div>

    <!-- Tabulka posledních návštěv webu -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #e2e8f0; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-list"></i> Poslední návštěvníci webu
      </h4>
      <div style="overflow-x: auto; max-height: 380px;">
        <table class="stats-table">
          <thead>
            <tr>
              <th>Čas vstupu</th>
              <th>Stát & Region</th>
              <th>Stránka</th>
              <th>IP adresa</th>
            </tr>
          </thead>
          <tbody>
            {% for v in recent_web_visits %}
            <tr>
              <td style="color:#38bdf8; font-weight:600; white-space:nowrap;">{{ v.visited_at }}</td>
              <td style="white-space:nowrap;">
                <span style="display:inline-flex; align-items:center; gap:6px;">
                  <img src="{{ v.flag }}" alt="" style="width:18px; height:13px; border-radius:2px;">
                  <span>{{ v.location }}</span>
                </span>
              </td>
              <td><span class="badge-path">{{ v.path }}</span></td>
              <td style="color:#64748b; font-family:monospace; font-size:11px;">{{ v.ip }}</td>
            </tr>
            {% else %}
            <tr>
              <td colspan="4" style="text-align:center; color:#64748b; padding:20px;">Zatím žádní zaznamenaní návštěvníci webu.</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- ═══════════════ SLOUPEC 2: STATISTIKY APLIKACE ═══════════════ -->
  <div id="col-app" style="display: flex; flex-direction: column; gap: 20px;">

    <!-- Hlavička sekce Aplikace -->
    <div style="background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 10px; padding: 12px 18px; display: flex; align-items: center; gap: 10px;">
      <i class="fas fa-desktop" style="color: #a78bfa; font-size: 18px;"></i>
      <h3 style="margin: 0; color: #ffffff; font-size: 15px; font-weight: bold;">Statistiky Aplikace & Hráčů</h3>
      <span style="margin-left: auto; background: rgba(16, 185, 129, 0.2); color: #10b981; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: flex; align-items: center; gap: 5px;">
        <span class="pulse-online"></span> {{ app_online_count }} ve hře
      </span>
    </div>

    <!-- Hráči právě online -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 18px 20px;">
      <h4 style="margin: 0 0 12px 0; color: #10b981; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <span class="pulse-online"></span> Hráči právě připojení v aplikaci ({{ app_online_count }})
      </h4>
      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        {% for u in app_online_users %}
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); padding: 8px 12px; border-radius: 8px; display: flex; align-items: center; gap: 10px;">
          {% if u.avatar_url %}
          <img src="{{ u.avatar_url }}" alt="" style="width: 26px; height: 26px; border-radius: 50%;">
          {% else %}
          <i class="fas fa-user-circle" style="color:#10b981; font-size:24px;"></i>
          {% endif %}
          <div>
            <div style="color: #ffffff; font-weight: bold; font-size: 12px;">{{ u.nick or u.discord_id }}</div>
            <div style="color: #10b981; font-size: 10px;">{{ u.role or 'User' }} &bull; Aktivní</div>
          </div>
        </div>
        {% else %}
        <div style="color: #64748b; font-size: 12px;">V aplikaci momentálně není nikdo aktivní.</div>
        {% endfor %}
      </div>
    </div>

    <!-- Grafy aplikace -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #a78bfa; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-calendar-week"></i> Spuštění aplikace za 7 dní
      </h4>
      <div style="position: relative; height: 210px; width: 100%;">
        <canvas id="chartApp7d"></canvas>
      </div>
    </div>

    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #a78bfa; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-clock"></i> Dnešní spuštění aplikace po hodinách
      </h4>
      <div style="position: relative; height: 180px; width: 100%;">
        <canvas id="chartApp24h"></canvas>
      </div>
    </div>

    <!-- Tabulka posledních relací aplikace -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #e2e8f0; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-history"></i> Poslední spuštění aplikace (relace)
      </h4>
      <div style="overflow-x: auto; max-height: 380px;">
        <table class="stats-table">
          <thead>
            <tr>
              <th>Hráč</th>
              <th>Čas spuštění</th>
              <th>Doba trvání</th>
              <th>Stav</th>
            </tr>
          </thead>
          <tbody>
            {% for s in recent_app_sessions %}
            <tr>
              <td style="white-space:nowrap;">
                <span style="display:inline-flex; align-items:center; gap:8px;">
                  {% if s.avatar_url %}
                  <img src="{{ s.avatar_url }}" alt="" style="width:22px; height:22px; border-radius:50%;">
                  {% else %}
                  <i class="fas fa-user-circle" style="color:#94a3b8; font-size:20px;"></i>
                  {% endif %}
                  <span style="color:#ffffff; font-weight:600;">{{ s.user_nick }}</span>
                  <span class="badge-role">{{ s.role }}</span>
                </span>
              </td>
              <td style="color:#94a3b8; font-size:11px; white-space:nowrap;">{{ s.start_time }}</td>
              <td style="color:#e2e8f0; font-weight:600;">{{ s.duration }}</td>
              <td>
                {% if s.is_active %}
                <span style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid #10b981; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:bold;">🟢 Hraje</span>
                {% else %}
                <span style="color:#64748b; font-size:11px;">Ukončeno</span>
                {% endif %}
              </td>
            </tr>
            {% else %}
            <tr>
              <td colspan="4" style="text-align:center; color:#64748b; padding:20px;">Zatím žádné zaznamenané relace aplikace.</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Žebříček nejaktivnějších hráčů -->
    <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 12px; padding: 20px;">
      <h4 style="margin: 0 0 14px 0; color: #f59e0b; font-size: 14px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-trophy"></i> Nejaktivnější hráči v aplikaci
      </h4>
      <div style="display:flex; flex-direction:column; gap:8px;">
        {% for u in top_active_users %}
        <div style="background:rgba(15,23,42,0.6); border:1px solid #334155; border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-weight:900; color:{% if loop.index == 1 %}#f59e0b{% elif loop.index == 2 %}#cbd5e1{% elif loop.index == 3 %}#d97706{% else %}#64748b{% endif %}; font-size:13px; width:20px;">#{{ loop.index }}</span>
            {% if u.avatar_url %}
            <img src="{{ u.avatar_url }}" alt="" style="width:24px; height:24px; border-radius:50%;">
            {% else %}
            <i class="fas fa-user-circle" style="color:#94a3b8; font-size:22px;"></i>
            {% endif %}
            <span style="color:#ffffff; font-weight:bold; font-size:13px;">{{ u.nick or u.discord_id }}</span>
            <span class="badge-role">{{ u.role }}</span>
          </div>
          <div style="display:flex; align-items:center; gap:12px; font-size:12px;">
            <span style="color:#38bdf8; font-weight:bold;" title="Počet spuštění"><i class="fas fa-play" style="font-size:10px;"></i> {{ u.launch_count or 0 }}x</span>
            <span style="color:#10b981; font-weight:bold;" title="Celkový čas"><i class="fas fa-clock" style="font-size:10px;"></i> {{ (u.total_time or 0) // 60 }}h {{ (u.total_time or 0) % 60 }}m</span>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>

  </div>

</div>

<script>
function switchStatsView(mode) {
  const container = document.getElementById('stats-grid-container');
  const colWeb = document.getElementById('col-web');
  const colApp = document.getElementById('col-app');
  const tabAll = document.getElementById('tab-all');
  const tabWeb = document.getElementById('tab-web');
  const tabApp = document.getElementById('tab-app');

  [tabAll, tabWeb, tabApp].forEach(t => t.classList.remove('active'));

  if (mode === 'all') {
    tabAll.classList.add('active');
    container.style.gridTemplateColumns = '1fr 1fr';
    colWeb.style.display = 'flex';
    colApp.style.display = 'flex';
  } else if (mode === 'web') {
    tabWeb.classList.add('active');
    container.style.gridTemplateColumns = '1fr';
    colWeb.style.display = 'flex';
    colApp.style.display = 'none';
  } else if (mode === 'app') {
    tabApp.classList.add('active');
    container.style.gridTemplateColumns = '1fr';
    colWeb.style.display = 'none';
    colApp.style.display = 'flex';
  }
}

// Responzivní přizpůsobení pro mobily
function handleResize() {
  if (window.innerWidth < 1000) {
    const container = document.getElementById('stats-grid-container');
    if (container && document.getElementById('tab-all').classList.contains('active')) {
      container.style.gridTemplateColumns = '1fr';
    }
  } else {
    const container = document.getElementById('stats-grid-container');
    if (container && document.getElementById('tab-all').classList.contains('active')) {
      container.style.gridTemplateColumns = '1fr 1fr';
    }
  }
}
window.addEventListener('resize', handleResize);
handleResize();

// Inicializace Chart.js grafů
const webLabels7d = {{ web_labels_7d | safe }};
const webData7d = {{ web_data_7d | safe }};
const webLabels24h = {{ web_labels_24h | safe }};
const webData24h = {{ web_data_24h | safe }};

const appLabels7d = {{ app_labels_7d | safe }};
const appData7d = {{ app_data_7d | safe }};
const appLabels24h = {{ app_labels_24h | safe }};
const appData24h = {{ app_data_24h | safe }};

// 1. Web 7d
new Chart(document.getElementById('chartWeb7d').getContext('2d'), {
  type: 'line',
  data: {
    labels: webLabels7d,
    datasets: [{
      label: 'Návštěvy webu',
      data: webData7d,
      borderColor: '#38bdf8',
      backgroundColor: 'rgba(56, 189, 248, 0.15)',
      borderWidth: 3,
      tension: 0.35,
      fill: true,
      pointBackgroundColor: '#38bdf8',
      pointRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } },
      x: { ticks: { color: '#94a3b8' }, grid: { display: false } }
    }
  }
});

// 2. Web 24h
new Chart(document.getElementById('chartWeb24h').getContext('2d'), {
  type: 'bar',
  data: {
    labels: webLabels24h,
    datasets: [{
      label: 'Dnešní návštěvy',
      data: webData24h,
      backgroundColor: '#38bdf8',
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } },
      x: { ticks: { color: '#94a3b8', maxTicksLimit: 12 }, grid: { display: false } }
    }
  }
});

// 3. App 7d
new Chart(document.getElementById('chartApp7d').getContext('2d'), {
  type: 'line',
  data: {
    labels: appLabels7d,
    datasets: [{
      label: 'Spuštění aplikace',
      data: appData7d,
      borderColor: '#a78bfa',
      backgroundColor: 'rgba(139, 92, 246, 0.15)',
      borderWidth: 3,
      tension: 0.35,
      fill: true,
      pointBackgroundColor: '#a78bfa',
      pointRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } },
      x: { ticks: { color: '#94a3b8' }, grid: { display: false } }
    }
  }
});

// 4. App 24h
new Chart(document.getElementById('chartApp24h').getContext('2d'), {
  type: 'bar',
  data: {
    labels: appLabels24h,
    datasets: [{
      label: 'Dnešní spuštění',
      data: appData24h,
      backgroundColor: '#a78bfa',
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } },
      x: { ticks: { color: '#94a3b8', maxTicksLimit: 12 }, grid: { display: false } }
    }
  }
});
</script>
"""

HTML_APP_MANAGEMENT = """
<style>
.toggle-card { background: var(--bg-panel); border: 1px solid #334155; border-radius: 14px; padding: 24px; display: flex; flex-direction: column; align-items: center; text-align: center; flex: 1; min-width: 220px; transition: all 0.3s ease; position: relative; overflow: hidden; }
.toggle-card:hover { transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
.toggle-circle { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 16px; transition: all 0.4s ease; }
.toggle-on { background: #10b981; box-shadow: 0 0 30px rgba(16,185,129,0.6); }
.toggle-off { background: #ef4444; box-shadow: 0 0 30px rgba(239,68,68,0.6); }
.toggle-card h3 { color: white; margin: 0 0 6px 0; font-size: 16px; }
.toggle-card p { color: #94a3b8; font-size: 12px; margin: 0 0 16px 0; line-height: 1.4; }
.toggle-btn-on { background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 14px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.3s; }
.toggle-btn-off { background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 50px; font-size: 14px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.3s; }
.section-divider { width: 100%; border: none; border-top: 1px solid #334155; margin: 30px 0; }
.section-title { color: var(--text-muted); font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 2px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
.section-title::after { content: ''; flex: 1; border-top: 1px solid #334155; }
</style>

<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; flex-wrap: wrap; gap: 15px;">
  <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-cogs" style="color:var(--blue-main);"></i> Správa Aplikace</h2>
</div>

<div class="section-title"><i class="fas fa-gamepad" style="color:#38bdf8;"></i> Ovládání Softwaru</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
  <div class="toggle-card">
    <div class="toggle-circle {% if soft_enabled %}toggle-on{% else %}toggle-off{% endif %}"><i class="fas {% if soft_enabled %}fa-globe{% else %}fa-power-off{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Globální Software</h3>
    <p>Zapíná/vypíná přístup k aplikaci pro všechny uživatele.</p>
    <form action="/dashboard/toggle_software" method="POST" style="width:100%;">
      <input type="hidden" name="new_status" value="{% if soft_enabled %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if soft_enabled %}toggle-btn-on{% else %}toggle-btn-off{% endif %}"><i class="fas {% if soft_enabled %}fa-times-circle{% else %}fa-check-circle{% endif %}"></i> {% if soft_enabled %}Vypnout{% else %}Zapnout{% endif %}</button>
    </form>
  </div>
  <div class="toggle-card">
    <div class="toggle-circle {% if launcher_enabled %}toggle-on{% else %}toggle-off{% endif %}"><i class="fas {% if launcher_enabled %}fa-rocket{% else %}fa-power-off{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Zámek Launcheru</h3>
    <p>Zablokuje vstup do Launcheru pro všechny uživatele.</p>
    <form action="/dashboard/toggle_launcher" method="POST" style="width:100%;">
      <input type="hidden" name="new_status" value="{% if launcher_enabled %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if launcher_enabled %}toggle-btn-on{% else %}toggle-btn-off{% endif %}"><i class="fas {% if launcher_enabled %}fa-times-circle{% else %}fa-check-circle{% endif %}"></i> {% if launcher_enabled %}Vypnout{% else %}Zapnout{% endif %}</button>
    </form>
  </div>
  <div class="toggle-card">
    <div class="toggle-circle {% if dl_enabled %}toggle-on{% else %}toggle-off{% endif %}" style="{% if dl_enabled %}background:#3b82f6; box-shadow: 0 0 30px rgba(59,130,246,0.6);{% endif %}"><i class="fas {% if dl_enabled %}fa-download{% else %}fa-times{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Stahování Softwaru</h3>
    <p>Povoluje/zakazuje stahování přes Discord bot a web.</p>
    <form action="/dashboard/toggle_downloads" method="POST" style="width:100%;">
      <input type="hidden" name="return_to" value="app_management">
      <input type="hidden" name="new_status" value="{% if dl_enabled %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if dl_enabled %}toggle-btn-on{% else %}toggle-btn-off{% endif %}"><i class="fas {% if dl_enabled %}fa-times-circle{% else %}fa-check-circle{% endif %}"></i> {% if dl_enabled %}Zakázat{% else %}Povolit{% endif %}</button>
    </form>
  </div>
</div>

<div class="section-title"><i class="fas fa-shield-alt" style="color:#ef4444;"></i> Bezpečnostní Vypínače Webu</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
  <div class="toggle-card" style="border-color: {% if web_login_enabled %}#334155{% else %}rgba(239,68,68,0.5){% endif %};">
    <div class="toggle-circle {% if web_login_enabled %}toggle-on{% else %}toggle-off{% endif %}"><i class="fas {% if web_login_enabled %}fa-sign-in-alt{% else %}fa-ban{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Přihlašování na Web</h3>
    <p>Vypnutím zabráníte novým přihlášením (prevence útoku). Přihlášení na /dashboard zůstane funkční.</p>
    {% if web_login_enabled %}
    <span style="font-size: 11px; font-weight: bold; color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid #10b981; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;">🟢 POVOLENO</span>
    {% else %}
    <span style="font-size: 11px; font-weight: bold; color: #ef4444; background: rgba(239,68,68,0.1); border: 1px solid #ef4444; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;">🔴 BLOKOVÁNO</span>
    {% endif %}
    <form action="/dashboard/toggle_web_login" method="POST" style="width:100%;">
      <input type="hidden" name="new_status" value="{% if web_login_enabled %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if web_login_enabled %}toggle-btn-on{% else %}toggle-btn-off{% endif %}"><i class="fas {% if web_login_enabled %}fa-lock{% else %}fa-unlock{% endif %}"></i> {% if web_login_enabled %}Zablokovat přihlášení{% else %}Povolit přihlášení{% endif %}</button>
    </form>
  </div>
  <div class="toggle-card" style="border-color: {% if map_enabled %}#334155{% else %}rgba(239,68,68,0.5){% endif %};">
    <div class="toggle-circle {% if map_enabled %}toggle-on{% else %}toggle-off{% endif %}"><i class="fas {% if map_enabled %}fa-map-marked-alt{% else %}fa-map{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Interaktivní Mapa</h3>
    <p>Zapíná/vypíná /mapa. Při vypnutí se zobrazí stránka s informací a odkazem na Discord.</p>
    {% if map_enabled %}
    <span style="font-size: 11px; font-weight: bold; color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid #10b981; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;">🟢 ONLINE</span>
    {% else %}
    <span style="font-size: 11px; font-weight: bold; color: #ef4444; background: rgba(239,68,68,0.1); border: 1px solid #ef4444; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;">🔴 OFFLINE</span>
    {% endif %}
    <form action="/dashboard/toggle_map" method="POST" style="width:100%;">
      <input type="hidden" name="new_status" value="{% if map_enabled %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if map_enabled %}toggle-btn-on{% else %}toggle-btn-off{% endif %}"><i class="fas {% if map_enabled %}fa-eye-slash{% else %}fa-eye{% endif %}"></i> {% if map_enabled %}Vypnout mapu{% else %}Zapnout mapu{% endif %}</button>
    </form>
  </div>
  <div class="toggle-card" style="border-color: {% if web_maintenance %}rgba(239,68,68,0.7){% else %}#334155{% endif %}; {% if web_maintenance %}background: rgba(239,68,68,0.05);{% endif %}">
    <div class="toggle-circle {% if web_maintenance %}toggle-off{% else %}toggle-on{% endif %}"><i class="fas {% if web_maintenance %}fa-hard-hat{% else %}fa-check-double{% endif %}" style="color: white; font-size: 32px;"></i></div>
    <h3>Globální Maintenance</h3>
    <p>⚠️ Přesměruje VEŠKERÝ traffic na /blocked. Výjimka: /dashboard a admin přihlášení.</p>
    {% if web_maintenance %}
    <span style="font-size: 11px; font-weight: bold; color: #ef4444; background: rgba(239,68,68,0.1); border: 1px solid #ef4444; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px; animation: pulse 1s infinite alternate;">🔴 WEB JE OFFLINE</span>
    {% else %}
    <span style="font-size: 11px; font-weight: bold; color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid #10b981; padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;">🟢 WEB BĚŽÍ</span>
    {% endif %}
    <form action="/dashboard/toggle_maintenance" method="POST" style="width:100%;">
      <input type="hidden" name="new_status" value="{% if web_maintenance %}False{% else %}True{% endif %}">
      <button type="submit" class="{% if web_maintenance %}toggle-btn-off{% else %}toggle-btn-on{% endif %}" {% if not web_maintenance %}onclick="return confirm('VAROVÁNÍ: Tím vypnete celý web pro všechny uživatele! Pokračovat?')"{% endif %}><i class="fas {% if web_maintenance %}fa-power-off{% else %}fa-hard-hat{% endif %}"></i> {% if web_maintenance %}Obnovit web{% else %}Spustit Maintenance{% endif %}</button>
    </form>
  </div>
</div>
"""

HTML_NOTIFICATIONS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-bell" style="color:#f59e0b;"></i> Systém Oznámení Webu</h2>
    <div style="display: flex; gap: 10px;">
        <a href="/dashboard/notifications" class="btn" style="background: #f59e0b; color: #000; font-weight: bold; font-size: 13px;"><i class="fas fa-bullhorn"></i> Web Oznámení</a>
        <a href="/dashboard/sprava-notifikaci" class="btn btn-dark" style="color: #a78bfa; font-size: 13px;"><i class="fas fa-paper-plane"></i> Notifikace Busů & Přímé Zprávy</a>
    </div>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning);">
        <h3 style="margin-top: 0; color: var(--warning);"><i class="fas fa-paper-plane"></i> Odeslat nové oznámení</h3>
        <form action="/dashboard/send_app_message" method="POST">
            <label style="color: var(--text-muted); font-size: 13px;">Nadpis oznámení:</label><input type="text" name="title" placeholder="Např. Vánoční Update 1.5!" required>
            <label style="color: var(--text-muted); font-size: 13px;">Text oznámení:</label><textarea name="content" rows="4" placeholder="Napište text zprávy..." required></textarea>
            <label style="color: var(--text-muted); font-size: 13px;">Pro koho?</label>
            <select name="target_type" id="target_type" onchange="toggleTargetData()" style="margin-bottom: 10px;"><option value="GLOBAL">Všichni uživatelé</option><option value="ROLE">Podle Rolí</option><option value="USERS">Vybraní uživatelé</option></select>
            <div id="target_data_container" style="display: none;"><input type="text" name="target_data" id="target_data" placeholder=""></div>
            <div style="background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin: 15px 0;"><label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: var(--text-main); font-size: 13px;"><input type="checkbox" name="repeat" style="width: auto; margin: 0;"> Zobrazovat uživatelům DOKOLA</label></div>
            <input type="text" name="expires_at" placeholder="Expirace: Např. 31.12.2026 23:59 (Volitelné)">
            <button type="submit" class="btn btn-warning" style="width: 100%; margin-top: 10px;"><i class="fas fa-paper-plane"></i> Vytvořit Oznámení</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px;">
        <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: var(--success); margin-top: 0;"><i class="fas fa-broadcast-tower"></i> Aktivní Oznámení</h3>
            <table><tr><th>Nadpis</th><th>Cílení</th><th>Opakování</th><th>Expirace</th><th>Akce</th></tr>
            {% for m in messages %}{% if not m.get('is_archived') %}<tr><td style="color: var(--text-main); font-weight: bold;">{{ m.get('title', '') }}</td><td>{% if m.get('target_type') == 'GLOBAL' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">Globálně</span>{% else %}<span class="role-tag" style="background-color: #ef4444; color: white;">{{ m.get('target_type', '') }}</span>{% endif %}</td><td>{% if m.get('repeat') %}<span style="color:var(--warning); font-size: 12px;"><i class="fas fa-sync"></i> Ano</span>{% else %}<span style="color:var(--success); font-size: 12px;">Jen jednou</span>{% endif %}</td><td style="color: var(--text-muted); font-size: 12px;">{{ m.get('expires_at', 'Nikdy') or 'Nikdy' }}</td><td style="display: flex; gap: 5px;"><form action="/dashboard/archive_app_message" method="POST" style="margin:0;"><input type="hidden" name="message_id" value="{{ m.get('message_id', '') }}"><button type="submit" class="btn btn-dark" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-archive"></i></button></form><form action="/dashboard/delete_app_message" method="POST" style="margin:0;"><input type="hidden" name="message_id" value="{{ m.get('message_id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Smazat?')"><i class="fas fa-trash"></i></button></form></td></tr>{% endif %}{% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádná aktivní oznámení.</td></tr>{% endfor %}</table>
        </div>
    </div>
</div>

<div class="section-title" style="margin-top: 40px;"><i class="fas fa-bullhorn" style="color:#ef4444;"></i> Globální Oznámení na Webu</div>
<div id="announcement-app" style="max-width: 800px;">
  <p style="color: #94a3b8; font-size: 13px; margin-top: 0;">Zde můžete nastavit více oznámení pro různé URL adresy.</p>
  
  <div id="announcement-list" style="display:flex; flex-direction:column; gap:20px; margin-bottom:20px;"></div>
  
  <button type="button" onclick="addAnnouncement()" class="btn btn-dark" style="margin-bottom: 20px;"><i class="fas fa-plus"></i> Přidat další oznámení</button>

  <form action="/dashboard/set_announcement" method="POST" id="announcement-form">
    <input type="hidden" name="announcements_json" id="announcements_json">
    <button type="button" onclick="saveAnnouncements()" class="btn btn-warning" style="width: 100%;"><i class="fas fa-save"></i> Uložit všechna oznámení</button>
  </form>
</div>

<script>
let announcements = {{ announcements_json | safe }};
if (!Array.isArray(announcements)) announcements = [];

function renderAnnouncements() {
    const list = document.getElementById('announcement-list');
    list.innerHTML = '';
    announcements.forEach((a, index) => {
        list.innerHTML += `
        <div style="background: var(--bg-panel); border: 1px solid #334155; border-radius: 14px; padding: 24px; position:relative;">
            <button type="button" onclick="removeAnnouncement(${index})" style="position:absolute; top:15px; right:15px; background:rgba(239,68,68,0.2); color:#ef4444; border:none; border-radius:5px; padding:5px 10px; cursor:pointer; font-size: 12px;"><i class="fas fa-trash"></i> Smazat</button>
            
            <div style="display:flex; flex-direction:column; gap:15px;">
                <div>
                  <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Aktivovat Oznámení</label>
                  <select onchange="updateAnnouncement(${index}, 'active', this.value === 'true')" style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white;">
                    <option value="false" ${!a.active ? 'selected' : ''}>🔴 Vypnuto</option>
                    <option value="true" ${a.active ? 'selected' : ''}>🟢 Zapnuto (Zobrazuje se)</option>
                  </select>
                </div>
                
                <div style="display:flex; gap:15px; flex-wrap:wrap;">
                    <div style="flex:1; min-width:200px;">
                        <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Zapnout od (volitelné)</label>
                        <input type="datetime-local" onchange="updateAnnouncement(${index}, 'start_time', this.value)" value="${a.start_time || ''}" style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white; box-sizing:border-box;">
                    </div>
                    <div style="flex:1; min-width:200px;">
                        <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Vypnout do (volitelné)</label>
                        <input type="datetime-local" onchange="updateAnnouncement(${index}, 'end_time', this.value)" value="${a.end_time || ''}" style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white; box-sizing:border-box;">
                    </div>
                </div>

                <div>
                  <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Zobrazit na URL (oddělujte čárkou, např. /mapa,/download)</label>
                  <input type="text" onchange="updateAnnouncement(${index}, 'urls', this.value)" value="${a.urls || ''}" placeholder="/mapa, /download" style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white; box-sizing:border-box;">
                </div>
                <div>
                  <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Volitelný nadpis (nech prázdné pro výchozí)</label>
                  <input type="text" onchange="updateAnnouncement(${index}, 'title', this.value)" value="${a.title || ''}" placeholder="Nouzový Režim!" style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white; box-sizing:border-box;">
                </div>
                <div>
                  <label style="color:white; font-size:14px; display:block; margin-bottom:5px;">Text oznámení (nové řádky se zachovají, HTML funguje)</label>
                  <textarea onchange="updateAnnouncement(${index}, 'text', this.value)" rows="4" placeholder="Nějaký problém s mapou..." style="width:100%; padding:10px; border-radius:8px; background:rgba(0,0,0,0.2); border:1px solid #334155; color:white; font-family:sans-serif; box-sizing:border-box;">${a.text || ''}</textarea>
                </div>
            </div>
        </div>
        `;
    });
}

function updateAnnouncement(index, field, value) {
    announcements[index][field] = value;
}

function addAnnouncement() {
    announcements.push({
        id: Date.now().toString(),
        active: false,
        urls: '/',
        title: '',
        text: '',
        start_time: '',
        end_time: ''
    });
    renderAnnouncements();
}

function removeAnnouncement(index) {
    if(confirm('Opravdu smazat toto oznámení?')) {
        announcements.splice(index, 1);
        renderAnnouncements();
    }
}

function saveAnnouncements() {
    document.getElementById('announcements_json').value = JSON.stringify(announcements);
    document.getElementById('announcement-form').submit();
}

document.addEventListener('DOMContentLoaded', () => {
    if (announcements.length === 0) {
        addAnnouncement();
    } else {
        renderAnnouncements();
    }
});
</script>

<script>
function toggleTargetData(){const t=document.getElementById('target_type').value,c=document.getElementById('target_data_container'),i=document.getElementById('target_data');if(t==='GLOBAL'){c.style.display='none';i.removeAttribute('required');}else{c.style.display='block';i.setAttribute('required','true');}}
</script>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
  <h2 style="margin:0;color:var(--text-main);display:flex;align-items:center;gap:10px;">
    <i class="fas fa-layer-group" style="color:var(--blue-main);"></i> Manager Verzí Launcheru
  </h2>
  <button onclick="document.getElementById('modal-add-version').style.display='flex'"
    style="background:var(--blue-main);color:#fff;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:8px;">
    <i class="fas fa-plus"></i> Přidat verzi
  </button>
</div>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}
    <div style="padding:12px 16px;border-radius:8px;margin-bottom:16px;background:{% if cat=='success' %}rgba(16,185,129,0.15);border:1px solid #10b981;color:#10b981{% else %}rgba(239,68,68,0.15);border:1px solid #ef4444;color:#ef4444{% endif %};">
      <i class="fas fa-{% if cat=='success' %}check-circle{% else %}exclamation-circle{% endif %}"></i> {{msg}}
    </div>
  {% endfor %}
{% endwith %}
<!-- Global Launcher URL -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:20px;margin-bottom:20px;">
  <h3 style="margin-top:0;color:var(--text-main);font-size:16px;"><i class="fas fa-link" style="color:#10b981;margin-right:8px;"></i>Globální odkaz na stažení Launcheru (.exe)</h3>
  <p style="color:var(--text-muted);font-size:13px;margin-bottom:15px;">Tento odkaz se použije pro stahování instalačního souboru z webové stránky při autorizaci Discordem.</p>
  <form action="/dashboard/update_launcher_url" method="POST" style="display:flex;gap:10px;">
    <input type="text" name="launcher_url" value="{{ launcher_url | e }}" style="flex:1;padding:10px;background:rgba(0,0,0,0.2);border:1px solid #334155;color:#fff;border-radius:6px;" placeholder="https://github.com/...">
    <button type="submit" style="background:var(--blue-main);color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:bold;">Uložit odkaz</button>
  </form>
</div>

<!-- Tabulka verzí -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="background:rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.08);">
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Verze</th>
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">DB verze</th>
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Role</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Aktivní = verze existuje. Vypnuto = nikdo ji nevidí.">Aktivní</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Viditelné v Launcheru">Viditelné</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Lze stáhnout">Stáhnout</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Lze spustit">Spustit</th>
        <th style="padding:14px 16px;text-align:right;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Akce</th>
      </tr>
    </thead>
    <tbody>
    {% for v in versions %}
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);{% if not v.get('is_active') %}opacity:0.45;{% endif %}"
          data-vid="{{ v.get('id','') }}"
          data-vname="{{ v.get('version_name','') | e }}"
          data-dbver="{{ v.get('db_version','') | e }}"
          data-furl="{{ v.get('file_url','') | e }}"
          data-role="{{ v.get('target_role','User') | e }}"
          data-active="{{ '1' if v.get('is_active') else '0' }}"
          data-show="{{ '1' if v.get('show_in_launcher', True) else '0' }}"
          data-dl="{{ '1' if v.get('can_download', True) else '0' }}"
          data-launch="{{ '1' if v.get('can_launch', True) else '0' }}">
        <td style="padding:14px 16px;">
          <div style="font-weight:600;color:var(--text-main);">{{ v.get('version_name','—') }}</div>
        </td>
        <td style="padding:14px 16px;">
          <span style="font-size:13px;color:var(--text-muted);font-family:monospace;">{{ v.get('db_version','—') }}</span>
        </td>
        <td style="padding:14px 16px;">
          <span style="background:rgba(96,165,250,0.15);color:#60a5fa;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">
            {{ v.get('target_role','—') }}
          </span>
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('is_active') %}
            <span style="color:#10b981;font-size:18px;" title="Aktivní – verze je dostupná"><i class="fas fa-toggle-on"></i></span>
          {% else %}
            <span style="color:#ef4444;font-size:18px;" title="Vypnuto – verze neexistuje pro nikoho"><i class="fas fa-toggle-off"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('show_in_launcher', True) %}
            <span style="color:#10b981;" title="Viditelné v Launcheru"><i class="fas fa-eye"></i></span>
          {% else %}
            <span style="color:#6b7280;" title="Skryté – zobrazí se jako Nedostupné"><i class="fas fa-eye-slash"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('can_download', True) %}
            <span style="color:#10b981;" title="Stahování povoleno"><i class="fas fa-download"></i></span>
          {% else %}
            <span style="color:#ef4444;" title="Stahování zakázáno"><i class="fas fa-ban"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('can_launch', True) %}
            <span style="color:#10b981;" title="Spuštění povoleno"><i class="fas fa-play-circle"></i></span>
          {% else %}
            <span style="color:#ef4444;" title="Spuštění zakázáno"><i class="fas fa-stop-circle"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 16px;text-align:right;">
          <button class="btn-edit-version"
            style="background:rgba(96,165,250,0.15);color:#60a5fa;border:1px solid rgba(96,165,250,0.3);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;margin-right:6px;">
            <i class="fas fa-edit"></i> Upravit
          </button>
          <form method="POST" action="/dashboard/delete_version" style="display:inline;"
            onsubmit="return confirm('Smazat tuto verzi?')">
            <input type="hidden" name="version_id" value="{{ v.get('id') }}">
            <button type="submit" style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;">
              <i class="fas fa-trash"></i>
            </button>
          </form>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="8" style="padding:40px;text-align:center;color:var(--text-muted);">
        <i class="fas fa-inbox" style="font-size:32px;opacity:0.3;display:block;margin-bottom:10px;"></i>
        Zatím nebyly přidány žádné verze. Klikni na <b>Přidat verzi</b> výše.
      </td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>

<!-- LEGENDA -->
<div style="margin-top:16px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:var(--text-muted);">
  <span><i class="fas fa-toggle-off" style="color:#ef4444;"></i> <b>Aktivní=VYP</b> – nikdo nevidí</span>
  <span><i class="fas fa-eye-slash" style="color:#6b7280;"></i> <b>Viditelné=VYP</b> – zobrazí se jako "Nedostupné"</span>
  <span><i class="fas fa-ban" style="color:#ef4444;"></i> <b>Stáhnout=VYP</b> – nelze stáhnout</span>
  <span><i class="fas fa-stop-circle" style="color:#ef4444;"></i> <b>Spustit=VYP</b> – nelze spustit</span>
</div>

<!-- MODAL: Přidat verzi -->
<div id="modal-add-version" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;justify-content:center;align-items:center;">
  <div style="background:#0f172a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:32px;width:520px;max-width:95vw;max-height:90vh;overflow-y:auto;">
    <h3 style="margin:0 0 24px;color:var(--text-main);"><i class="fas fa-plus-circle" style="color:var(--blue-main);"></i> Přidat novou verzi</h3>
    <form method="POST" action="/dashboard/add_version">
      <div style="display:grid;gap:16px;">
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Název verze *</label>
          <input name="version_name" required placeholder="např. 1.6.1" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Verze DB * <span style="color:var(--text-muted);font-weight:400;">(kontrola kompatibility – např. 2026-09)</span></label>
          <input name="db_version" required placeholder="např. 2026-09" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">URL ke stažení (ZIP) *</label>
          <input name="file_url" required placeholder="https://github.com/.../releases/download/..." style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Minimální role pro přístup *</label>
          <select name="target_role" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
            <option value="User" style="background:#0f172a; color:#fff;">User (všichni)</option>
            <option value="BT" style="background:#0f172a; color:#fff;">BT (Beta Testeři)</option>
            <option value="DEV" style="background:#0f172a; color:#fff;">DEV (Vývojáři)</option>
            <option value="SA" style="background:#0f172a; color:#fff;">SA (Super Admin)</option>
          </select>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px;display:grid;gap:14px;">
          <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Nastavení přístupu</div>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Aktivní</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí skryje verzi úplně pro všechny (ani SA ji neuvidí)</div>
            </div>
            <input type="checkbox" name="is_active" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Viditelné v Launcheru</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí zobrazí verzi jako „Nedostupné" – nikdo ji nemůže stáhnout ani spustit</div>
            </div>
            <input type="checkbox" name="show_in_launcher" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze stáhnout</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Stáhnout – pokud vypnuto, nelze nově stáhnout</div>
            </div>
            <input type="checkbox" name="can_download" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze spustit</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Spustit – pokud vypnuto, verze nejde spustit ani ze stažené kopie</div>
            </div>
            <input type="checkbox" name="can_launch" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-top:24px;">
        <button type="submit" style="flex:1;background:var(--blue-main);color:#fff;border:none;padding:12px;border-radius:8px;cursor:pointer;font-weight:600;font-size:15px;">
          <i class="fas fa-plus"></i> Přidat verzi
        </button>
        <button type="button" onclick="document.getElementById('modal-add-version').style.display='none'"
          style="padding:12px 24px;background:rgba(255,255,255,0.06);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);border-radius:8px;cursor:pointer;">
          Zrušit
        </button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL: Upravit verzi -->
<div id="modal-edit-version" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;justify-content:center;align-items:center;">
  <div style="background:#0f172a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:32px;width:520px;max-width:95vw;max-height:90vh;overflow-y:auto;">
    <h3 style="margin:0 0 24px;color:var(--text-main);"><i class="fas fa-edit" style="color:#f59e0b;"></i> Upravit verzi</h3>
    <form method="POST" action="/dashboard/edit_version" id="form-edit-version">
      <input type="hidden" name="version_id" id="edit-version-id">
      <div style="display:grid;gap:16px;">
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Název verze *</label>
          <input name="version_name" id="edit-version-name" required style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Verze DB * <span style="color:var(--text-muted);font-weight:400;">(kontrola kompatibility)</span></label>
          <input name="db_version" id="edit-db-version" required style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">URL ke stažení (ZIP)</label>
          <input name="file_url" id="edit-file-url" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Minimální role</label>
          <select name="target_role" id="edit-target-role" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
            <option value="User" style="background:#0f172a; color:#fff;">User (všichni)</option>
            <option value="BT" style="background:#0f172a; color:#fff;">BT (Beta Testeři)</option>
            <option value="DEV" style="background:#0f172a; color:#fff;">DEV (Vývojáři)</option>
            <option value="SA" style="background:#0f172a; color:#fff;">SA (Super Admin)</option>
          </select>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px;display:grid;gap:14px;">
          <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Nastavení přístupu</div>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Aktivní</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí skryje verzi úplně pro všechny</div></div>
            <input type="checkbox" name="is_active" id="edit-is-active" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Viditelné v Launcheru</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí zobrazí badge „Nedostupné"</div></div>
            <input type="checkbox" name="show_in_launcher" id="edit-show-in-launcher" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze stáhnout</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Stáhnout v Launcheru</div></div>
            <input type="checkbox" name="can_download" id="edit-can-download" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze spustit</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Spustit (i ze stažené kopie)</div></div>
            <input type="checkbox" name="can_launch" id="edit-can-launch" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-top:24px;">
        <button type="submit" style="flex:1;background:#f59e0b;color:#000;border:none;padding:12px;border-radius:8px;cursor:pointer;font-weight:600;font-size:15px;">
          <i class="fas fa-save"></i> Uložit změny
        </button>
        <button type="button" onclick="document.getElementById('modal-edit-version').style.display='none'"
          style="padding:12px 24px;background:rgba(255,255,255,0.06);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);border-radius:8px;cursor:pointer;">
          Zrušit
        </button>
      </div>
    </form>
  </div>
</div>

<script>
// Edit button – reads data-* attrs from the <tr> row
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.btn-edit-version').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tr = this.closest('tr');
      document.getElementById('edit-version-id').value = tr.dataset.vid || '';
      document.getElementById('edit-version-name').value = tr.dataset.vname || '';
      document.getElementById('edit-db-version').value = tr.dataset.dbver || '';
      document.getElementById('edit-file-url').value = tr.dataset.furl || '';
      var roleEl = document.getElementById('edit-target-role');
      for (var i = 0; i < roleEl.options.length; i++) {
        if (roleEl.options[i].value === tr.dataset.role) { roleEl.selectedIndex = i; break; }
      }
      document.getElementById('edit-is-active').checked = tr.dataset.active === '1';
      document.getElementById('edit-show-in-launcher').checked = tr.dataset.show === '1';
      document.getElementById('edit-can-download').checked = tr.dataset.dl === '1';
      document.getElementById('edit-can-launch').checked = tr.dataset.launch === '1';
      document.getElementById('modal-edit-version').style.display = 'flex';
    });
  });
  // Close modals on backdrop click
  ['modal-add-version','modal-edit-version'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('click', function(e) { if (e.target === this) this.style.display = 'none'; });
  });
});
</script>
"""


HTML_PENDING_ROLES = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);">Rezervace Rolí</h2></div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Předpřipravit Roli</h3>
        <form action="/dashboard/add_pending_role" method="POST">
            <input type="text" name="discord_identifier" placeholder="Discord Nick nebo Discord ID" required>
            <div class="checkbox-group"><label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label><label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label><label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label><label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label></div>
            <button type="submit" class="btn" style="width: 100%; margin-top: 15px;">Vytvořit Rezervaci</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">⏳ Čekající rezervace</h3>
        <table><tr><th>Discord Identifikátor</th><th>Rezervovaná Role</th><th>Akce</th></tr>
        {% for p in pending %}<tr><td><strong>{{ p.get('discord_identifier', '') }}</strong></td><td>{{ p.get('roles', 'User') }}</td><td><form action="/dashboard/delete_pending_role" method="POST" style="display:inline;"><input type="hidden" name="pending_id" value="{{ p.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Zrušit?')"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">Žádné čekající rezervace.</td></tr>{% endfor %}</table>
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
            <input type="url" name="image_url" placeholder="URL obrázku" required>
            <textarea name="description" placeholder="Něco o něm..." rows="3" required></textarea>
            <div id="roles-container"><div class="role-entry" style="display: flex; gap: 10px; margin-bottom: 5px;"><input type="text" name="role_name[]" placeholder="Název Role" required style="flex: 2; margin: 0;"><input type="color" name="role_color[]" value="#ef4444" style="flex: 1; padding: 2px; height: 40px; margin: 0;"></div></div>
            <button type="button" class="btn btn-dark" onclick="addRoleField()" style="width: 100%; margin-bottom: 15px; margin-top: 5px; padding: 5px; font-size: 12px;">+ Přidat další roli</button>
            <button type="submit" class="btn" style="width: 100%;">Přidat do týmu</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">👥 Aktuální členové týmu</h3>
        <table><tr><th>Jméno</th><th>Discord Nick</th><th>Role</th><th>Akce</th></tr>
        {% for member in team %}<tr><td><strong>{{ member.get('name', '') }}</strong></td><td>{{ member.get('discord_nick', '') }}</td><td>{{ member.get('role_name', '') }}</td><td><form action="/dashboard/delete_team" method="POST" style="display:inline;"><input type="hidden" name="discord_nick" value="{{ member.get('discord_nick', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat?')"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Žádní členové.</td></tr>{% endfor %}</table>
    </div>
</div>
<script>function addRoleField(){const c=document.getElementById('roles-container');const d=document.createElement('div');d.className='role-entry';d.style='display:flex;gap:10px;margin-bottom:5px;';d.innerHTML=`<input type="text" name="role_name[]" placeholder="Název Role" required style="flex:2;margin:0;"><input type="color" name="role_color[]" value="#38bdf8" style="flex:1;padding:2px;height:40px;margin:0;"><button type="button" class="btn btn-danger" onclick="this.parentElement.remove()" style="padding:0 10px;margin:0;">X</button>`;c.appendChild(d);}</script>
"""

HTML_IDS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-id-badge" style="color:var(--blue-main);"></i> Správa Aplikačních ID</h2></div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <table><tr><th>App ID</th><th>Nick</th><th>Discord ID</th><th>Status</th><th>Změnit ID na:</th></tr>
    {% for user in users %}<tr style="opacity: {{ '0.6' if user.get('is_deleted') else '1' }};"><td style="font-weight: bold; color: var(--blue-main); font-size: 16px;">#{{ user.get('app_id', '') }}</td><td><strong>{{ user.get('nick', '') }}</strong></td><td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td><td>{% if user.get('is_deleted') %}<span style="color: var(--danger); font-size: 12px; font-weight: bold;">Smazán</span>{% else %}<span style="color: var(--success); font-size: 12px; font-weight: bold;">Aktivní</span>{% endif %}</td><td style="display: flex; gap: 10px; align-items: center;"><form action="/dashboard/change_id" method="POST" style="display: flex; gap: 10px; margin: 0; width: 100%;"><input type="hidden" name="discord_id" value="{{ user.get('discord_id', '') }}"><input type="number" name="new_app_id" placeholder="Nové ID" required style="width: 100px; margin: 0; text-align: center; font-weight: bold;"><button type="submit" class="btn btn-warning" style="padding: 8px 15px; font-size: 12px;"><i class="fas fa-edit"></i> Změnit</button></form></td></tr>{% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td></tr>{% endfor %}</table>
</div>
"""

HTML_DASHBOARD_MAIN = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
    <h2 style="margin: 0; color: var(--text-main);">{{ title }}</h2>
    <div style="display: flex; gap: 10px; align-items: center;">
        <a href="/dashboard/sprava-notifikaci" class="btn" style="background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; display: inline-flex; align-items: center; gap: 8px; text-decoration: none; padding: 7px 15px; border-radius: 8px; font-weight: 600; font-size: 13px; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);"><i class="fas fa-paper-plane"></i> Správa Notifikací & Zprávy</a>
        <div id="refresh-timer" style="color: var(--text-muted); font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-weight: bold;"><i class="fas fa-sync-alt" style="color: var(--blue-main);"></i> Aktualizace za: <span id="timer-sec" style="color: white;">60</span>s</div>
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <table id="usersTable">
        <thead><tr><th onclick="sortTable(0)">App ID ↕</th><th onclick="sortTable(1)">Nick ↕</th><th onclick="sortTable(2)">E-mail ↕</th><th onclick="sortTable(3)">Web Přihl. ↕</th><th onclick="sortTable(4)">Notify ↕</th><th onclick="sortTable(5)">Stav ↕</th><th onclick="sortTable(6)">Role ↕</th><th onclick="sortTable(7)">Poslední Aktivita ↕</th><th>Akce</th></tr></thead>
        <tbody>
        {% for user in users %}
        <tr>
            <td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td>
            <td><strong>{{ user.get('nick', '') }}</strong></td>
            <td style="color: var(--text-muted); font-size: 13px;">{{ user.get('email', '') or '-' }}</td>
            <td style="color: var(--text-muted); font-size: 13px;">{{ user.get('web_login_at', '') or '-' }}</td>
            <td style="color: var(--text-muted); font-size: 13px;">-</td>
            <td>{% if user.get('is_banned') %}<span style="color: var(--danger); font-size: 11px; font-weight:bold; border:1px solid var(--danger); padding:2px 5px; border-radius:4px;">BANNED</span>{% elif user.get('is_deleted') %}<span style="color: var(--text-muted); font-size: 11px; font-weight:bold; border:1px solid var(--text-muted); padding:2px 5px; border-radius:4px;">DELETED</span>{% elif not user.get('hwid') or user.get('hwid') == 'None' or user.get('hwid') == '' %}<span style="color: var(--warning); font-size: 11px; font-weight:bold; border:1px solid var(--warning); padding:2px 5px; border-radius:4px;">NOT ACTIVATED</span>{% else %}<span style="color: var(--success); font-size: 11px; font-weight:bold; border:1px solid var(--success); padding:2px 5px; border-radius:4px;">ACTIVATED</span>{% endif %}</td>
            {% set role_weight = 1 %}{% if 'SA' in user.get('role', '') %}{% set role_weight = 4 %}{% elif 'DEV' in user.get('role', '') %}{% set role_weight = 3 %}{% elif 'BT' in user.get('role', '') %}{% set role_weight = 2 %}{% endif %}
            <td data-sort="{{ role_weight }}">{% set role_list = user.get('role', '').split(',') %}{% for r in role_list %}{% set r_clean = r.strip() %}{% if r_clean == 'SA' %}<span class="role-tag" style="background-color: #ef4444; color: white;">SA</span>{% elif r_clean == 'DEV' %}<span class="role-tag" style="background-color: #10b981; color: white;">DEV</span>{% elif r_clean == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BT</span>{% elif r_clean == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User</span>{% endif %}{% endfor %}{% if user.get('dashboard_access') %}<i class="fas fa-shield-alt" style="color:var(--blue-main); font-size:12px; margin-left:5px;"></i>{% endif %}</td>
            <td style="color: var(--text-muted); font-size: 13px;" data-sort="{{ '99999999999' if user.get('is_online') else user.get('last_active', '0') }}">{% if user.get('is_online') %}<span style="color: var(--success); font-weight: bold;">🟢 AKTIVNÍ</span>{% else %}{{ user.get('last_active', 'Nikdy nehrál') }}{% endif %}</td>
            <td><button class="btn btn-dark" style="padding: 5px 10px; font-size: 12px;" data-app-id="{{ user.get('app_id', '') }}" data-discord-id="{{ user.get('discord_id', '') }}" data-nick="{{ (user.get('nick') or '') | e }}" data-email="{{ (user.get('email') or '') | e }}" data-roles="{{ (user.get('role') or '') | e }}" data-hwid="{{ (user.get('hwid') or '') | e }}" data-ip="{{ (user.get('ip_address') or '') | e }}" data-banned="{{ user.get('is_banned', False) }}" data-deleted="{{ user.get('is_deleted', False) }}" data-db-access="{{ user.get('dashboard_access', False) }}" data-reg-at="{{ (user.get('registered_at') or '') | e }}" onclick="openModal(this)"><i class="fas fa-edit"></i> Upravit</button></td>
        </tr>
        {% else %}
        <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Žádní uživatelé nenalezeni.</td></tr>
        {% endfor %}
        </tbody>
    </table>
</div>
<script>
    let timeLeft = 60;
    setInterval(() => { if(timeLeft > 0){ timeLeft--; let s=document.getElementById('timer-sec'); if(s) s.innerText=timeLeft; } if(timeLeft===0){ timeLeft=-1; location.reload(); } }, 1000);
    let sortDir = {};
    function sortTable(n) { let table=document.getElementById("usersTable"),switching=true,dir=sortDir[n]==="asc"?"desc":"asc";sortDir[n]=dir;while(switching){switching=false;let rows=table.rows;for(let i=1;i<rows.length-1;i++){let x=rows[i].getElementsByTagName("TD")[n],y=rows[i+1].getElementsByTagName("TD")[n];let xC=x.hasAttribute("data-sort")?x.getAttribute("data-sort"):x.innerHTML.replace(/<[^>]*>?/gm,'').trim();let yC=y.hasAttribute("data-sort")?y.getAttribute("data-sort"):y.innerHTML.replace(/<[^>]*>?/gm,'').trim();if(!isNaN(xC)&&!isNaN(yC)){xC=parseFloat(xC);yC=parseFloat(yC);}else{xC=xC.toLowerCase();yC=yC.toLowerCase();}if(dir=="asc"&&xC>yC){rows[i].parentNode.insertBefore(rows[i+1],rows[i]);switching=true;break;}else if(dir=="desc"&&xC<yC){rows[i].parentNode.insertBefore(rows[i+1],rows[i]);switching=true;break;}}}}
    function openModal(btn) { try { document.getElementById('editModal').style.display='flex'; document.getElementById('modalAppId').innerText="#"+(btn.getAttribute('data-app-id')||""); let discord_id=btn.getAttribute('data-discord-id')||""; document.getElementById('modalDiscordId').value=discord_id; document.getElementById('modalNick').value=btn.getAttribute('data-nick')||""; let email=btn.getAttribute('data-email')||""; document.getElementById('modalEmail').value=email; let hwid=btn.getAttribute('data-hwid'); document.getElementById('modalHwid').value=(!hwid||hwid==='None')?'':hwid; let ip=btn.getAttribute('data-ip'); document.getElementById('modalIp').value=(!ip||ip==='None')?'':ip; let reg=btn.getAttribute('data-reg-at'); document.getElementById('profRegistered').innerText=(reg&&reg!=='None')?reg:'Neznámé'; let da=btn.getAttribute('data-db-access'); document.getElementById('modalDashboardAccess').checked=(da==='True'); document.getElementById('profDbAccess').innerHTML=da==='True'?'<span style="color:var(--success);"><i class="fas fa-check-circle"></i> Povoleno</span>':'<span style="color:var(--danger);"><i class="fas fa-times-circle"></i> Zakázáno</span>'; document.querySelectorAll('input[name="roles"]').forEach(cb=>cb.checked=false); (btn.getAttribute('data-roles')||"").split(',').forEach(r=>{let el=document.querySelector(`input[name="roles"][value="${r.trim()}"]`);if(el)el.checked=true;}); let is_deleted=btn.getAttribute('data-deleted'); let is_banned=btn.getAttribute('data-banned'); if(is_deleted==='True'){document.getElementById('activeActions').style.display='none';document.getElementById('deletedActions').style.display='block';}else{document.getElementById('activeActions').style.display='block';document.getElementById('deletedActions').style.display='none';if(is_banned==='True'){document.getElementById('btnBan').style.display='none';document.getElementById('btnUnban').style.display='block';}else{document.getElementById('btnBan').style.display='block';document.getElementById('btnUnban').style.display='none';}} document.getElementById('profJoined').innerHTML='<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('modalStatusDot').innerHTML=''; document.getElementById('profDownloads').innerHTML='<tr><td colspan="2" style="text-align:center;"><i class="fas fa-spinner fa-spin"></i></td></tr>'; document.getElementById('profSessions').innerHTML='<tr><td colspan="2" style="text-align:center;"><i class="fas fa-spinner fa-spin"></i></td></tr>'; document.getElementById('profAppStatus').innerHTML='<i class="fas fa-spinner fa-spin"></i>'; document.getElementById('profStats').innerHTML=''; if(!discord_id||discord_id.trim()===''||discord_id==='None'){document.getElementById('profJoined').innerText="Chybí ID";return;} fetch('/api/get_profile_data/'+discord_id).then(r=>r.json()).then(data=>{if(data.error){document.getElementById('profAppStatus').innerHTML="<span style='color:#ef4444;'>Chyba: "+data.error+"</span>";return;} document.getElementById('profJoined').innerText=data.joined_at||"Nenalezen"; document.getElementById('modalStatusDot').innerHTML=data.status||""; document.getElementById('profAppStatus').innerHTML=data.app_status||""; document.getElementById('profStats').innerHTML=data.stats||""; let dlHtml=""; if(data.downloads&&data.downloads.length>0){data.downloads.forEach(d=>{dlHtml+=`<tr><td style="color:var(--blue-main);"><b>${d.version_name}</b></td><td style="color:var(--text-muted);">${d.downloaded_at}</td></tr>`;});}else{dlHtml="<tr><td colspan='2' style='color:var(--text-muted);'>Nestáhl žádný soubor.</td></tr>";} document.getElementById('profDownloads').innerHTML=dlHtml; let sessHtml=""; if(data.sessions&&data.sessions.length>0){data.sessions.forEach(s=>{sessHtml+=`<tr><td style="color:var(--success);font-weight:bold;white-space:nowrap;">🟢 ${s.start_time.split(' ')[1]||s.start_time}</td><td style="color:var(--danger);font-weight:bold;white-space:nowrap;">🔴 ${s.end_time.split(' ')[1]||s.end_time}</td></tr><tr><td colspan="2" style="color:var(--text-muted);padding-top:0;padding-bottom:10px;border-bottom:1px solid #334155;text-align:center;">${s.start_time.split(' ')[0]}</td></tr>`;});}else{sessHtml="<tr><td colspan='2' style='color:var(--text-muted);'>Zatím žádná aktivita.</td></tr>";} document.getElementById('profSessions').innerHTML=sessHtml;}).catch(e=>{document.getElementById('profAppStatus').innerHTML="<span style='color:#ef4444;'>Spojení selhalo</span>";});} catch(e){alert("Chyba: "+e.message);}}
    function closeModal(){document.getElementById('editModal').style.display='none';}
</script>
"""

HTML_SUPPORTERS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-star" style="color:var(--warning);"></i> Správa Podporovatelů</h2></div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning); margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;"><i class="fas fa-exclamation-triangle"></i> Ke schválení</h3>
    <table><tr><th>BMAC Jméno</th><th>Discord Nick</th><th>Částka</th><th>Systémová Zpráva</th><th>Akce</th></tr>
    {% for p in pending_claims %}<tr><td style="color:var(--blue-main); font-weight:bold;">{{ p.get('name', 'Neznámý') }}</td><td>{{ p.get('discord_nick', '') }}</td><td><span class="role-tag" style="background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning);">{{ p.get('amount', '?') }}</span></td><td style="color: var(--danger); font-size: 12px;">{{ p.get('sys_note', '') }}</td><td style="display: flex; gap: 5px;"><form action="/dashboard/approve_claim" method="POST" style="display:inline; margin:0;"><input type="hidden" name="claim_id" value="{{ p.get('id', '') }}"><input type="hidden" name="discord_nick" value="{{ p.get('discord_nick', '') }}"><input type="hidden" name="amount" value="{{ p.get('amount', '0') }}"><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check"></i></button></form><form action="/dashboard/delete_supporter" method="POST" style="display:inline; margin: 0;"><input type="hidden" name="supporter_id" value="{{ p.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Smazat?')"><i class="fas fa-times"></i></button></form></td></tr>{% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Vše je vyřízeno.</td></tr>{% endfor %}</table>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Ruční přidání</h3>
        <form action="/dashboard/add_supporter" method="POST"><input type="text" name="name" placeholder="Jméno" required><input type="text" name="discord_nick" placeholder="Discord Nick (Volitelně)"><input type="text" name="amount" placeholder="Částka (např. 150 CZK)" required><textarea name="message" placeholder="Zpráva (volitelně)..." rows="3"></textarea><button type="submit" class="btn" style="width: 100%; margin-top: 15px;">Přidat</button></form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">☕ Historie</h3>
        <table><tr><th>Stav</th><th>Jméno</th><th>Discord</th><th>Částka</th><th>Datum</th><th>Akce</th></tr>
        {% for s in supporters_history %}<tr><td>{% if s.get('status') == 'rejected' %}<span class="role-tag" style="background-color: var(--danger); color: white;">Zamítnuto</span>{% else %}<span class="role-tag" style="background-color: var(--success); color: white;">Schváleno</span>{% endif %}</td><td style="color:var(--blue-main); font-weight:bold;">{{ s.get('name', '') }}</td><td style="color:#aaa; font-size:12px;">{{ s.get('discord_nick', '') }}</td><td style="color:var(--success); font-weight:bold;">{{ s.get('amount', '') }}</td><td style="color:var(--text-muted); font-size:12px;">{{ s.get('created_at', '') }}</td><td><form action="/dashboard/delete_supporter" method="POST" style="display:inline; margin: 0;"><input type="hidden" name="supporter_id" value="{{ s.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Smazat?')"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Zatím žádná historie.</td></tr>{% endfor %}</table>
    </div>
</div>
"""

HTML_FEEDBACK = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-comments" style="color:#a855f7;"></i> Zpětná vazba a Žádosti</h2></div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning); margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;">Nové žádosti o HWID a IP Reset</h3>
    <table><tr><th>Uživatel</th><th>Zpráva</th><th>Datum</th><th>Akce</th></tr>
    {% for f in hwid_pending %}<tr><td style="color:white; font-weight:bold;">{{ f.get('nick', '') }}<br><span style="font-size:11px; color:#aaa;">{{ f.get('discord_id', '') }}</span></td><td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td><td style="color:#aaa; font-size:12px;">{{ f.get('fcreated_at', '') }}</td><td style="display:flex; gap:5px;"><form action="/dashboard/feedback_reset_hwid" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><input type="hidden" name="discord_id" value="{{ f.get('discord_id', '') }}"><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check"></i> Resetovat</button></form></td></tr>{% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Žádné žádosti.</td></tr>{% endfor %}</table>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid #f59e0b; margin-bottom: 20px;">
    <h3 style="color: #f59e0b; margin-top: 0;">Žádosti o Admin Bypass</h3>
    <table><tr><th>Uživatel</th><th>Zpráva</th><th>Datum</th><th>Akce</th></tr>
    {% for f in bypass_pending %}<tr><td style="color:white; font-weight:bold;">{{ f.get('nick', '') }}<br><span style="font-size:11px; color:#aaa;">{{ f.get('discord_id', '') }}</span></td><td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td><td style="color:#aaa; font-size:12px;">{{ f.get('fcreated_at', '') }}</td><td style="display:flex; gap:5px;"><form action="/dashboard/bypass_approve" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check"></i> Schválit</button></form><form action="/dashboard/bypass_reject" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-times"></i> Zamítnout</button></form></td></tr>{% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Žádné žádosti o bypass.</td></tr>{% endfor %}</table>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); margin-bottom: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">Nové zprávy od uživatelů</h3>
    <table><tr><th>Uživatel</th><th>Zpráva</th><th>Datum</th><th>Akce</th></tr>
    {% for f in general_pending %}<tr><td style="color:white; font-weight:bold;">{{ f.get('nick', '') }}</td><td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td><td style="color:#aaa; font-size:12px;">{{ f.get('fcreated_at', '') }}</td><td style="display:flex; gap:10px;"><form action="/dashboard/feedback_resolve" method="POST" style="margin:0; display:flex; flex-direction:column; gap:5px;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><textarea name="reply_text" rows="2" style="background:#2d3748; color:white; border:1px solid #4a5568; border-radius:5px; padding:5px; resize:vertical; font-size:12px; width:200px;" placeholder="Napsat odpověď (nepovinné)"></textarea><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-paper-plane"></i> Odeslat a vyřešit</button></form><form action="/dashboard/feedback_delete" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Žádná nová zpětná vazba.</td></tr>{% endfor %}</table>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <h3 style="color: var(--success); margin-top: 0;">Vyřešeno / Uzavřeno</h3>
    <table><tr><th>Uživatel</th><th>Typ</th><th>Zpráva</th><th>Odpověď</th><th>Akce</th></tr>
    {% for f in resolved_all %}<tr style="opacity: 0.7;"><td>{{ f.get('nick', '') }}</td><td>{{ f.get('type', '') }}</td><td style="color:#aaa; font-style:italic;">{{ f.get('message', '') }}</td><td style="color:var(--success);">{{ f.get('sys_note', '') }}</td><td><form action="/dashboard/feedback_delete" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádné uzavřené tickety.</td></tr>{% endfor %}</table>
</div>
"""

HTML_WAIT_AUTH = """
<div style="text-align: center; margin-top: 100px;">
    <h2 style="color: var(--blue-main);"><i class="fas fa-shield-alt"></i> Čekání na ověření...</h2>
    <p style="color: var(--text-muted);">Byla vám zaslána zpráva na Discord. Prosím, potvrďte přihlášení kliknutím na tlačítko ve zprávě.</p>
    <div class="spinner" style="margin: 30px auto; width: 50px; height: 50px; border: 5px solid rgba(56, 189, 248, 0.2); border-top-color: var(--blue-main); border-radius: 50%; animation: spin 1s linear infinite;"></div>
    <p id="status-text" style="color: var(--warning); font-weight: bold;">Čekám na vaši akci...</p>
</div>
<style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
<script>
    let authInterval = setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}').then(r => r.json()).then(d => {
            if (d.status === 'approved') {
                clearInterval(authInterval);
                window.location.href = '/dashboard/login_finalize?discord_id={{ discord_id }}';
            } else if (d.status === 'rejected') {
                clearInterval(authInterval);
                document.getElementById('status-text').innerText = "Přihlášení bylo zamítnuto!";
                document.getElementById('status-text').style.color = "var(--danger)";
                setTimeout(() => window.location.href = '/', 2000);
            }
        });
    }, 2000);
</script>
"""

HTML_LOGIN = """
<div style="max-width: 400px; margin: 100px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-top: 4px solid var(--blue-main);">
    <h2 style="color: var(--text-main); margin-top: 0;"><i class="fas fa-lock"></i> Administrace</h2>
    <p style="color: var(--text-muted); margin-bottom: 20px; font-size: 14px;">Zadejte své Discord ID pro přihlášení.</p>
    
    <!-- New Warning Box -->
    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; margin-bottom: 25px; text-align: left;">
        <p style="color: #ef4444; margin: 0; font-size: 13px; font-weight: bold; margin-bottom: 4px;"><i class="fas fa-exclamation-triangle"></i> Pouze pro administrátory</p>
        <p style="color: #cbd5e1; margin: 0; font-size: 12px; line-height: 1.4;">Tato sekce je určena výhradně pro administrátory. Běžní uživatelé zde nemají přístup.</p>
    </div>

    <form action="/login_request" method="POST">
        <input type="text" name="discord_id" placeholder="Vaše Discord ID (např. 1234567890)" required style="text-align: center; font-size: 16px;">
        <button type="submit" class="btn" style="width: 100%; font-size: 16px; margin-top: 10px;"><i class="fas fa-sign-in-alt"></i> Přihlásit se</button>
    </form>
    
    <div style="margin-top:20px; text-align:right;">
        <button onclick="document.getElementById('web-dev-login-panel').style.display='block'; this.style.display='none';" style="background:transparent; border:1px solid rgba(255,255,255,0.1); color:#64748b; padding:3px 8px; border-radius:3px; cursor:pointer; font-size:10px;">DEV</button>
    </div>
    
    <div id="web-dev-login-panel" style="display:none; text-align:left; margin-top:15px; border-top:1px solid rgba(239,68,68,0.2); padding-top:15px;">
        <p style="color:#ef4444; font-size:12px; margin-bottom:10px; font-weight:bold;"><i class="fas fa-shield-alt"></i> NOUZOVÝ REŽIM (ADMIN)</p>
        <form action="/dashboard/offline_login" method="POST">
            <input name="username" type="text" placeholder="Uživatelské jméno" required style="width:100%; padding:8px; background:rgba(255,255,255,0.05); border:1px solid rgba(239,68,68,0.3); border-radius:4px; color:white; font-size:12px; margin-bottom:8px;">
            <input name="password" type="password" placeholder="Heslo" required style="width:100%; padding:8px; background:rgba(255,255,255,0.05); border:1px solid rgba(239,68,68,0.3); border-radius:4px; color:white; font-size:12px; margin-bottom:12px;">
            <button type="submit" style="width:100%; background:rgba(239,68,68,0.15); color:#fca5a5; border:1px solid #ef4444; padding:8px; border-radius:4px; cursor:pointer; font-weight:bold; font-size:12px;">
                PŘIHLÁSIT SE
            </button>
        </form>
    </div>
</div>
"""

# ─── NOVÁ ŠABLONA: Rozcestník Provoz IDPK ────────────────────────────────────
HTML_PROVOZ_IDPK = """
<style>
  .prov-card { display:block; width:100%; padding:30px; border-radius:14px; text-decoration:none; font-size:20px; font-weight:bold; color:white; margin-bottom:18px; transition:transform .2s, box-shadow .2s; text-align:center; }
  .prov-card:hover { transform:translateY(-6px); color:white; }
  .prov-card .ci { font-size:44px; display:block; margin-bottom:10px; }
  .prov-card .cs { font-size:13px; font-weight:normal; opacity:.75; margin-top:5px; display:block; }
  .prov-back { color:#94a3b8; text-decoration:none; padding:9px 20px; border:1px solid #334155; border-radius:8px; font-size:14px; display:inline-block; margin-top:8px; transition:.2s; }
  .prov-back:hover { border-color:#38bdf8; color:#38bdf8; }
  @media (max-width: 768px) {
    .prov-wrap { padding: 30px 15px !important; }
    .prov-card { padding: 20px !important; font-size: 16px !important; margin-bottom: 12px !important; }
    .prov-card .ci { font-size: 30px !important; margin-bottom: 5px !important; }
    .prov-wrap h1 { font-size: 26px !important; }
  }
</style>
<div class="prov-wrap" style="text-align:center; padding:50px 20px; max-width:620px; margin:0 auto;">
  <div style="background:rgba(239,68,68,.1); border:1px solid #ef4444; border-radius:10px; padding:18px 20px; margin-bottom:36px; text-align:left;">
    <h3 style="color:#ef4444; margin:0 0 8px 0; font-size:15px;"><i class="fas fa-exclamation-triangle"></i> Důležité upozornění</h3>
    <p style="color:#cbd5e1; margin:0; font-size:13px; line-height:1.65;">
      Tato stránka <strong>není</strong> officiálním webem IDPK, organizátora dopravy ani žádného dopravce. Veškerý obsah je čistě fanouškovský a data nemusí být 100% přesná — slouží pouze jako orientační přehled.
    </p>
  </div>
  <h1 style="color:#38bdf8; font-size:32px; margin-bottom:8px; text-shadow:0 0 15px rgba(56,189,248,.35);"><i class="fas fa-bus"></i> Provoz IDPK</h1>
  <p style="color:#94a3b8; margin-bottom:36px; font-size:15px;">Vyberte sekci:</p>
  <a href="/mapa" class="prov-card" style="background:linear-gradient(135deg,#1e3a8a,#3b82f6); box-shadow:0 5px 20px rgba(59,130,246,.35);">
    <span class="ci"><i class="fas fa-map-marked-alt"></i></span>
    Interaktivní mapa
    <span class="cs">Live polohy autobusů IDPK s jízdními řády z Inflow</span>
  </a>
  <a href="/historie" class="prov-card" style="background:linear-gradient(135deg,#064e3b,#10b981); box-shadow:0 5px 20px rgba(16,185,129,.35);">
    <span class="ci"><i class="fas fa-database"></i></span>
    Databáze autobusů
    <span class="cs">SPZ záznamy a historie odjetých spojů linek 490 / 496</span>
  </a>
  <a href="/jizdni-rad" class="prov-card" style="background:linear-gradient(135deg,#f59e0b,#d97706); box-shadow:0 5px 20px rgba(245,158,11,.35);">
    <span class="ci"><i class="fas fa-table"></i></span>
    Jízdní Řády IDPK
    <span class="cs">Vyhledávač a prohlížeč GTFS dat pro všechny linky</span>
  </a>
  <a href="/" class="prov-back"><i class="fas fa-arrow-left"></i> Zpět na hlavní stránku</a>
</div>
"""

HTML_REGISTER = """
<style>
  .register-wrapper { background: url('/static/img/bg-map.jpg') no-repeat center center fixed; background-size: cover; display: flex; align-items: center; justify-content: center; min-height: calc(100vh - 60px); margin: -20px; padding: 20px; position: relative; }
  .glass-card { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 20px; padding: 40px; width: 100%; max-width: 400px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7), 0 0 20px rgba(56, 189, 248, 0.2); text-align: center; position: relative; z-index: 10; }
  .glass-card h2 { color: var(--blue-main); margin-bottom: 30px; font-size: 28px; margin-top: 0; }
  .input-group { margin-bottom: 20px; text-align: left; }
  .input-group label { display: block; margin-bottom: 8px; font-size: 13px; color: var(--text-muted); font-weight: bold; }
  .input-group input { width: 100%; padding: 12px; background: rgba(0, 0, 0, 0.5); border: 1px solid #334155; border-radius: 8px; color: white; font-size: 15px; outline: none; transition: border 0.3s, box-shadow 0.3s; margin: 0; box-sizing: border-box; }
  .input-group input:focus { border-color: var(--blue-main); box-shadow: 0 0 8px rgba(56, 189, 248, 0.5); }
  .btn-submit { width: 100%; padding: 12px; border-radius: 8px; border: none; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; }
  .btn-discord { background: #5865F2; color: white; margin-bottom: 15px; }
  .btn-discord:hover { background: #4752C4; box-shadow: 0 0 15px rgba(88, 101, 242, 0.5); }
  .btn-email { background: transparent; border: 1px solid var(--blue-main); color: var(--blue-main); }
  .btn-email:hover { background: rgba(56, 189, 248, 0.1); box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
  .separator { display: flex; align-items: center; text-align: center; margin: 25px 0; color: #64748b; font-size: 13px; }
  .separator::before, .separator::after { content: ''; flex: 1; border-bottom: 1px solid #334155; }
  .separator:not(:empty)::before { margin-right: .5em; }
  .separator:not(:empty)::after { margin-left: .5em; }
  .discord-hint { font-size: 11px; color: var(--text-muted); margin-top: 5px; }
  .status-msg { margin-top: 15px; font-size: 14px; font-weight: bold; min-height: 20px; display: none; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; vertical-align: middle; margin-right: 8px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .back-btn { position: absolute; top: 20px; left: 20px; color: var(--text-muted); text-decoration: none; font-weight: bold; display: flex; align-items: center; gap: 5px; transition: color 0.3s; z-index: 20; background: rgba(15,23,42,0.8); padding: 8px 12px; border-radius: 8px; border: 1px solid #334155; }
  .back-btn:hover { color: var(--blue-main); border-color: var(--blue-main); }
</style>
<div class="register-wrapper">
<a href="/" class="back-btn"><i class="fas fa-arrow-left"></i> Zpět</a>
<div class="glass-card">
  <img src="/static/img/datacorebot_pf-lepsi.png" style="width:60px; height:60px; border-radius:12px; margin-bottom:15px; box-shadow: 0 0 15px rgba(56,189,248,0.5);">
  <h2>Přihlášení</h2>
  
  <div id="login-container">
    <div class="input-group">
      <label>Discord ID</label>
      <input type="text" id="discord_id" placeholder="Např. 123456789012345678">
      <div class="discord-hint">Jak zjistit ID? Zapněte si Nastavení -> Pokročilé -> Vývojářský režim, klikněte pravým na svůj profil a dejte "Kopírovat ID uživatele". V případě potíží zkuste příkaz <code>!auth</code> na našem Discordu.</div>
    </div>
    <button class="btn-submit btn-discord" onclick="reqDiscord()"><i class="fab fa-discord"></i> Pokračovat přes Discord</button>
    
    <div class="separator">NEBO</div>
    
    <div class="input-group">
      <label>E-mailová adresa</label>
      <input type="email" id="email" placeholder="vas@email.cz">
    </div>
    <button class="btn-submit btn-email" onclick="reqEmail()"><i class="fas fa-envelope"></i> Pokračovat přes E-mail</button>
  </div>
  
  <div id="status-container" style="display:none; padding: 20px 0;">
    <div class="spinner" id="spinner"></div>
    <div id="status-text" style="color: var(--blue-main); font-size: 15px; font-weight: bold; display: inline-block;">Čekám na potvrzení...</div>
    <div id="status-desc" style="color: var(--text-muted); font-size: 13px; margin-top: 15px; line-height: 1.5;"></div>
  </div>
</div>
</div>
<script>
let checkInterval = null;
let currentMethod = null;
let currentDiscordId = null;

function showStatus(text, desc, isError = false) {
    document.getElementById('login-container').style.display = 'none';
    const statusContainer = document.getElementById('status-container');
    statusContainer.style.display = 'block';
    
    const statusText = document.getElementById('status-text');
    statusText.innerText = text;
    statusText.style.color = isError ? 'var(--danger)' : 'var(--blue-main)';
    
    document.getElementById('status-desc').innerHTML = desc;
    document.getElementById('spinner').style.display = isError ? 'none' : 'inline-block';
}

function reqDiscord() {
    const id = document.getElementById('discord_id').value.trim();
    if(!id) return alert('Zadejte Discord ID.');
    
    fetch('/api/auth/discord/request', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({discord_id: id})
    }).then(r=>r.json()).then(data => {
        if(data.status === 'success') {
            currentMethod = 'discord';
            currentDiscordId = data.discord_id;
            showStatus('Odesláno na Discord', `Otevřete si soukromé zprávy od DataCore Bota a klikněte na tlačítko <b>Přihlásit se na Web</b>.<br><br><i>Pokud vám zpráva nepřišla, zkontrolujte, zda máte povolené zprávy od členů serveru. Můžete také použít příkaz !auth na našem serveru.</i>`);
            startPolling();
        } else {
            alert('Chyba: ' + data.message);
        }
    }).catch(e => alert('Chyba komunikace se serverem.'));
}

function reqEmail() {
    const email = document.getElementById('email').value.trim();
    if(!email || !email.includes('@')) return alert('Zadejte platný e-mail.');
    
    fetch('/api/auth/email/request', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: email, intent: 'login'})
    }).then(r=>r.json()).then(data => {
        if(data.status === 'success') {
            showStatus('E-mail odeslán', `Na adresu <b>${email}</b> jsme odeslali e-mail s odkazem pro přihlášení. Klikněte na tlačítko v e-mailu a budete automaticky přihlášeni.<br><br><i>Ověřte si složku Spam, pokud e-mail nedorazí do 2 minut.</i><br><br><div style="margin-top:15px; text-align:center;"><p style="font-size:12px; color:#94a3b8; margin-bottom:10px;">Zkuste to zadat ručně, jen tak pro jistotu. (Zadejte 5místný kód z e-mailu)</p><div style="display:flex; gap:10px; justify-content:center;"><input type="text" id="email_code_input" placeholder="12345" maxlength="5" style="width:100px; text-align:center; padding:10px; border-radius:8px; border:1px solid #334155; background:rgba(0,0,0,0.2); color:white; margin:0;"><button onclick="submitEmailCode()" style="background:#38bdf8; color:black; font-weight:bold; border:none; padding:10px 15px; border-radius:8px; cursor:pointer;">Potvrdit kód</button></div></div>`, false);
            document.getElementById('spinner').style.display = 'none';
        } else {
            alert('Chyba: ' + data.message);
        }
    }).catch(e => alert('Chyba komunikace se serverem.'));
}

function submitEmailCode() {
    const code = document.getElementById('email_code_input').value.trim();
    if(code.length === 5) {
        window.location.href = `/api/auth/finalize?token=${code}&type=email&intent=login`;
    } else {
        alert("Kód musí mít 5 znaků.");
    }
}

function startPolling() {
    if(checkInterval) clearInterval(checkInterval);
    checkInterval = setInterval(() => {
        if(currentMethod === 'discord' && currentDiscordId) {
            fetch('/api/auth/status?discord_id=' + currentDiscordId)
            .then(r=>r.json()).then(data => {
                if(data.status === 'approved') {
                    if (data.token) document.cookie = "web_session_token=" + data.token + "; path=/; max-age=" + (60*60*24*30);
                    clearInterval(checkInterval);
                    showStatus('Úspěšně přihlášeno!', 'Přesměrovávám do aplikace...', false);
                    setTimeout(() => window.location.href = '/ucet', 1500);
                } else if(data.status === 'rejected') {
                    clearInterval(checkInterval);
                    showStatus('Přihlášení zamítnuto', 'Požadavek byl zamítnut v Discordu.', true);
                    setTimeout(() => location.reload(), 3000);
                }
            });
        }
    }, 2000);
}
</script>
</body>
</html>
"""

HTML_UCET = """
<style>
  .ucet-wrapper { background: url('/static/img/bg-map.jpg') no-repeat center center fixed; background-size: cover; display: flex; align-items: center; justify-content: center; min-height: calc(100vh - 60px); margin: -20px; padding: 20px; position: relative; }
  .ucet-card { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 20px; padding: 40px; width: 100%; max-width: 500px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7), 0 0 20px rgba(56, 189, 248, 0.2); position: relative; z-index: 10; }
  .ucet-header { display: flex; align-items: center; gap: 20px; border-bottom: 1px solid #334155; padding-bottom: 20px; margin-bottom: 20px; }
  .avatar-preview { width: 80px; height: 80px; border-radius: 50%; border: 3px solid #38bdf8; background: rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; font-size: 85px; color: #38bdf8; overflow: hidden; flex-shrink: 0; box-shadow: 0 0 15px rgba(56,189,248,0.5); }
  .avatar-preview img { width: 100%; height: 100%; object-fit: cover; }
  .ucet-title h2 { color: var(--blue-main); margin: 0 0 5px 0; font-size: 24px; }
  .ucet-title p { color: #94a3b8; margin: 0; font-size: 13px; }
  .input-group { margin-bottom: 20px; }
  .input-group label { display: block; margin-bottom: 8px; font-size: 13px; color: var(--text-muted); font-weight: bold; }
  .input-group input { width: 100%; padding: 12px; background: rgba(0, 0, 0, 0.5); border: 1px solid #334155; border-radius: 8px; color: white; font-size: 15px; outline: none; transition: border 0.3s; box-sizing: border-box; }
  .input-group input:focus { border-color: var(--blue-main); box-shadow: 0 0 8px rgba(56, 189, 248, 0.5); }
  .btn-save { width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; transition: 0.3s; margin-top: 10px; }
  .btn-save:hover { background: #059669; box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); }
  .link-section { margin-top: 30px; background: rgba(0,0,0,0.3); border-radius: 12px; padding: 20px; border: 1px solid #334155; }
  .link-section h3 { color: white; margin-top: 0; font-size: 16px; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
  .link-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #334155; }
  .link-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
  .link-info { display: flex; align-items: center; gap: 10px; }
  .link-info i { font-size: 20px; }
  .link-status { font-size: 13px; font-weight: bold; }
  .status-yes { color: #10b981; }
  .status-no { color: #f59e0b; }
  .btn-link { padding: 6px 12px; border-radius: 6px; border: none; font-size: 12px; font-weight: bold; cursor: pointer; transition: 0.2s; text-decoration: none; color: white; display: inline-block; }
  .btn-link-discord { background: #5865F2; }
  .btn-link-discord:hover { background: #4752C4; }
  .btn-link-email { background: transparent; border: 1px solid var(--blue-main); color: var(--blue-main); }
  .btn-link-email:hover { background: rgba(56, 189, 248, 0.1); }
</style>
<div class="ucet-wrapper">
  <div class="ucet-card">
    <div class="ucet-header">
      <div class="avatar-preview" id="avatarPreview">
        __AVATAR_IMG__
      </div>
      <div class="ucet-title">
        <h2>Nastavení účtu</h2>
        <p>Spravujte svůj profil a přihlášení</p>
        __APP_ID_BADGE__
      </div>
    </div>

    <div class="input-group">
      <label>Přezdívka (Nickname)</label>
      <input type="text" id="nick" value="__NICK__" placeholder="Vaše přezdívka">
    </div>

    <div class="input-group">
      <label>Profilový obrázek</label>
      <div style="display:flex; gap:10px;">
        <input type="file" id="avatar_file" accept="image/png, image/jpeg, image/webp" onchange="previewAvatar(this)" style="padding: 9px; cursor: pointer; flex:1;">
        <button onclick="resetAvatar()" type="button" style="background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid #ef4444; border-radius: 8px; padding: 0 15px; cursor: pointer; font-weight: bold;"><i class="fas fa-trash"></i> Smazat</button>
      </div>
    </div>

    <button class="btn-save" onclick="saveProfile()"><i class="fas fa-save"></i> Uložit profil</button>
    <div id="save-status" style="margin-top: 10px; font-size: 13px; text-align: center; font-weight: bold; display: none;"></div>

    <div class="link-section">
      <h3>Propojené metody přihlášení</h3>
      
      <div class="link-item">
        <div class="link-info">
          <i class="fab fa-discord" style="color: #5865F2;"></i>
          <div>
            <div style="color: white; font-size: 14px; font-weight: bold;">Discord</div>
            __DISCORD_STATUS__
          </div>
        </div>
        __DISCORD_BTN__
      </div>

      <div class="link-item">
        <div class="link-info">
          <i class="fas fa-envelope" style="color: var(--blue-main);"></i>
          <div>
            <div style="color: white; font-size: 14px; font-weight: bold;">E-mail</div>
            __EMAIL_STATUS__
          </div>
        </div>
        __EMAIL_BTN__
      </div>
    </div>
    
    <div class="link-section">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:10px; margin-bottom:15px; flex-wrap:wrap; gap:10px;">
        <h3 style="margin:0; font-size:16px; color:white; display:flex; align-items:center; gap:8px;">
          <i class="fas fa-desktop" style="color:#38bdf8;"></i> Přihlášená zařízení (<span id="sessions-count">__SESSIONS_COUNT__</span>)
          <button type="button" onclick="refreshSessionsList(true)" id="btn-refresh-sessions" style="background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); color:#38bdf8; border-radius:6px; cursor:pointer; font-size:11px; padding:3px 8px; display:inline-flex; align-items:center; gap:4px; transition:0.2s;" onmouseover="this.style.background='rgba(56,189,248,0.2)';" onmouseout="this.style.background='rgba(56,189,248,0.1)';" title="Zkontrolovat nově přihlášená zařízení">
            <i class="fas fa-sync-alt" id="icon-refresh-sessions"></i> Obnovit
          </button>
        </h3>
        <button id="btn-revoke-others" onclick="revokeOtherSessions()" class="btn-link" style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4); color:#ef4444; font-size:11px; padding:4px 8px; cursor:pointer; display:__REVOKE_BTN_DISPLAY__;" title="Odhlásit všechna ostatní zařízení kromě tohoto">
          <i class="fas fa-sign-out-alt"></i> Odhlásit ostatní
        </button>
      </div>
      <div id="sessions-list-container">
        __SESSIONS_LIST__
      </div>
    </div>

    <div class="link-section">
      <h3>Moje upozornění na spoje</h3>
      __NOTIFICATIONS__
    </div>
  </div>
</div>

<script>
function renderSessionCardHtml(s) {
    const isCurr = !!s.is_current;
    const currBadge = isCurr ? '<span style="background:rgba(16,185,129,0.2); border:1px solid #10b981; color:#10b981; font-size:10px; padding:2px 8px; border-radius:12px; font-weight:bold; letter-spacing:0.5px;">TOTO ZAŘÍZENÍ</span>' : '';
    const safeId = s.id;
    const devName = s.device || 'Neznámé zařízení';
    const icon = s.icon || 'fa-desktop';
    const lastActive = s.last_active || 'Neznámé';
    const createdAt = s.created_at || 'Neznámé';
    const ip = s.ip || 'Neznámá';

    return `
    <div id="session-card-${safeId}" class="session-card" data-is-current="${isCurr}" style="background: rgba(0,0,0,0.35); border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center; transition: all 0.3s ease;">
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="width:42px; height:42px; border-radius:10px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); display:flex; align-items:center; justify-content:center; color:#38bdf8; font-size:18px; flex-shrink:0;">
          <i class="fas ${icon}"></i>
        </div>
        <div>
          <div style="color:white; font-size:14px; font-weight:bold; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            ${devName} ${currBadge}
          </div>
          <div style="color:#94a3b8; font-size:12px; margin-top:2px;">
            Naposledy aktivní: <span style="color:#38bdf8; font-weight:600;">${lastActive}</span>
          </div>
          <div style="color:#64748b; font-size:11px; margin-top:1px;">
            Přihlášeno: ${createdAt} &bull; IP: ${ip}
          </div>
        </div>
      </div>
      <div>
        <button onclick="deleteSession('${safeId}', ${isCurr})" style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.35); color:#ef4444; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:bold; transition:0.2s;" onmouseover="this.style.background='#ef4444'; this.style.color='white';" onmouseout="this.style.background='rgba(239,68,68,0.15)'; this.style.color='#ef4444';" title="Odhlásit toto zařízení">
          <i class="fas fa-trash-alt"></i> Smazat
        </button>
      </div>
    </div>
    `;
}

function updateSessionsCountAndUI() {
    const container = document.getElementById('sessions-list-container');
    const cards = container ? container.querySelectorAll('.session-card') : [];
    const cnt = cards.length;
    const countEl = document.getElementById('sessions-count');
    if (countEl) countEl.innerText = cnt;

    const revokeBtn = document.getElementById('btn-revoke-others');
    if (revokeBtn) {
        let hasOther = false;
        cards.forEach(c => {
            if (c.getAttribute('data-is-current') !== 'true') hasOther = true;
        });
        revokeBtn.style.display = hasOther ? 'inline-flex' : 'none';
    }

    if (cnt === 0 && container) {
        container.innerHTML = '<div style="color:#64748b; font-size:13px; text-align:center; padding:15px; background:rgba(0,0,0,0.2); border-radius:8px;">Žádná aktivní přihlášená zařízení.</div>';
    }
}

function deleteSession(sessionId, isCurrent) {
    if (isCurrent) {
        if (!confirm("Toto je vaše aktuální zařízení. Pokud ho smažete, budete odhlášeni. Pokračovat?")) return;
    } else {
        if (!confirm("Opravdu chcete odhlásit toto zařízení?")) return;
    }
    
    const card = document.getElementById('session-card-' + sessionId);
    const delBtn = card ? card.querySelector('button') : null;
    if (delBtn) {
        delBtn.disabled = true;
        delBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    fetch('/api/ucet/sessions/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: sessionId})
    }).then(r => r.json()).then(data => {
        if (data.status === 'success') {
            if (isCurrent) {
                window.location.href = '/login';
                return;
            }
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '0';
                card.style.transform = 'translateX(25px) scale(0.95)';
                setTimeout(() => {
                    card.remove();
                    updateSessionsCountAndUI();
                }, 300);
            } else {
                refreshSessionsList(false);
            }
        } else {
            if (delBtn) {
                delBtn.disabled = false;
                delBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Smazat';
            }
            alert('Chyba: ' + (data.message || 'Nepodařilo se smazat zařízení'));
        }
    }).catch(e => {
        if (delBtn) {
            delBtn.disabled = false;
            delBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Smazat';
        }
        alert('Chyba spojení');
    });
}

function revokeOtherSessions() {
    if (!confirm("Opravdu chcete odhlásit všechna ostatní zařízení kromě tohoto?")) return;
    const btn = document.getElementById('btn-revoke-others');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Odhlašuji...';
    }

    fetch('/api/ucet/sessions/revoke_others', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    }).then(r => r.json()).then(data => {
        if (data.status === 'success') {
            const container = document.getElementById('sessions-list-container');
            const cards = container ? container.querySelectorAll('.session-card') : [];
            cards.forEach(c => {
                if (c.getAttribute('data-is-current') !== 'true') {
                    c.style.transition = 'all 0.3s ease';
                    c.style.opacity = '0';
                    c.style.transform = 'translateX(25px) scale(0.95)';
                    setTimeout(() => c.remove(), 300);
                }
            });
            setTimeout(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Odhlásit ostatní';
                }
                updateSessionsCountAndUI();
            }, 320);
        } else {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Odhlásit ostatní';
            }
            alert('Chyba: ' + (data.message || 'Nepodařilo se odhlásit ostatní zařízení'));
        }
    }).catch(e => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Odhlásit ostatní';
        }
        alert('Chyba spojení');
    });
}

let isRefreshingSessions = false;
function refreshSessionsList(isManual = false) {
    if (isRefreshingSessions) return;
    isRefreshingSessions = true;

    const refreshIcon = document.getElementById('icon-refresh-sessions');
    if (refreshIcon) refreshIcon.classList.add('fa-spin');

    fetch('/api/ucet/sessions')
    .then(r => {
        if (!r.ok) throw new Error('Nelze načíst');
        return r.json();
    })
    .then(data => {
        if (data.status === 'success' && Array.isArray(data.sessions)) {
            const container = document.getElementById('sessions-list-container');
            if (container) {
                const currentCards = Array.from(container.querySelectorAll('.session-card'));
                const currentIds = currentCards.map(c => c.id.replace('session-card-', '')).join(',');
                const newIds = data.sessions.map(s => s.id).join(',');

                if (currentIds !== newIds || isManual) {
                    let newHtml = '';
                    if (data.sessions.length === 0) {
                        newHtml = '<div style="color:#64748b; font-size:13px; text-align:center; padding:15px; background:rgba(0,0,0,0.2); border-radius:8px;">Žádná aktivní přihlášená zařízení.</div>';
                    } else {
                        data.sessions.forEach(s => {
                            newHtml += renderSessionCardHtml(s);
                        });
                    }
                    container.innerHTML = newHtml;
                    updateSessionsCountAndUI();
                }
            }
        }
    })
    .catch(err => {
        if (isManual) console.warn('Chyba při obnově zařízení:', err);
    })
    .finally(() => {
        isRefreshingSessions = false;
        if (refreshIcon) {
            setTimeout(() => {
                refreshIcon.classList.remove('fa-spin');
            }, 300);
        }
    });
}

// Automatická synchronizace relací na pozadí (každé 4 sekundy pokud je okno aktivní)
setInterval(() => {
    if (!document.hidden) {
        refreshSessionsList(false);
    }
}, 4000);

document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        refreshSessionsList(false);
    }
});
window.addEventListener('focus', () => {
    refreshSessionsList(false);
});

function deleteNotificationRule(ruleId) {
    if(!confirm("Opravdu chcete toto upozornění smazat?")) return;
    fetch('/api/notifications/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: ruleId})
    }).then(r => r.json()).then(data => {
        if(data.status === 'success') {
            location.reload();
        } else {
            alert('Chyba: ' + data.message);
        }
    });
}


let currentAvatarBase64 = "__AVATAR_URL__";

function resetAvatar() {
    if (confirm("Opravdu chcete smazat profilový obrázek?")) {
        currentAvatarBase64 = "";
        document.getElementById('avatarPreview').innerHTML = '<i class="fas fa-user-circle"></i>';
        document.getElementById('avatar_file').value = "";
        saveProfile();
    }
}

function previewAvatar(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        if (!validTypes.includes(file.type)) {
            alert('Chyba: Lze nahrát pouze obrázky (JPG, PNG, WEBP, GIF).');
            input.value = '';
            return;
        }
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                const MAX = 200;
                let w = img.width, h = img.height;
                if (w > h) { if (w > MAX) { h *= MAX / w; w = MAX; } }
                else { if (h > MAX) { w *= MAX / h; h = MAX; } }
                canvas.width = w; canvas.height = h;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);
                currentAvatarBase64 = canvas.toDataURL('image/jpeg', 0.85);
                document.getElementById('avatarPreview').innerHTML = '<img src="' + currentAvatarBase64 + '">';
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

function saveProfile() {
    const nick = document.getElementById('nick').value.trim();
    const btn = document.querySelector('.btn-save');
    const status = document.getElementById('save-status');
    
    if(!nick) {
        status.style.display = 'block';
        status.style.color = '#ef4444';
        status.innerText = 'Přezdívka nemůže být prázdná!';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ukládám...';
    
    fetch('/api/ucet/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ nick: nick, avatar_url: currentAvatarBase64 })
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Uložit profil';
        status.style.display = 'block';
        if(data.status === 'success') {
            status.style.color = '#10b981';
            status.innerText = 'Profil úspěšně uložen!';
            setTimeout(() => location.reload(), 1500);
        } else {
            status.style.color = '#ef4444';
            status.innerText = 'Chyba: ' + data.message;
        }
    }).catch(e => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Uložit profil';
        status.style.display = 'block';
        status.style.color = '#ef4444';
        status.innerText = 'Chyba sítě!';
    });
}
</script>
"""

HTML_LOGIN_BLOCKED = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Přihlašování vypnuto | OIS IDPK</title>
<link rel="icon" type="image/png" href="/static/img/datacorebot_pf-lepsi.png">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; overflow: hidden; }
  .bg-particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
  .particle { position: absolute; border-radius: 50%; animation: float 15s infinite ease-in-out; opacity: 0.3; }
  @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-30px) rotate(180deg); } }
  .container { position: relative; z-index: 1; max-width: 600px; width: 100%; }
  .logo-ring { width: 120px; height: 120px; border-radius: 50%; background: rgba(56,189,248,0.1); border: 3px solid rgba(56,189,248,0.5); display: flex; align-items: center; justify-content: center; margin: 0 auto 30px auto; }
  .status-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(245,158,11,0.15); border: 1px solid #f59e0b; border-radius: 30px; padding: 6px 18px; font-size: 13px; font-weight: bold; color: #f59e0b; margin-bottom: 25px; }
  h1 { font-size: clamp(28px, 6vw, 48px); font-weight: 900; line-height: 1.2; margin-bottom: 20px; color: white; }
  .subtitle { color: #94a3b8; font-size: 16px; line-height: 1.6; margin-bottom: 40px; }
  .btn-back { display: inline-flex; align-items: center; gap: 14px; background: var(--blue-main); color: white; padding: 18px 40px; border-radius: 14px; text-decoration: none; font-size: 20px; font-weight: 800; transition: all 0.3s ease; box-shadow: 0 8px 30px rgba(56,189,248,0.5); border: 2px solid rgba(255,255,255,0.2); position: relative; overflow: hidden; }
  .btn-back:hover { transform: translateY(-4px) scale(1.03); background: var(--blue-hover); color: white; }
  .btn-back i { font-size: 28px; }
  .wave { position: fixed; bottom: 0; left: 0; width: 100%; height: 200px; background: linear-gradient(180deg, transparent, rgba(56,189,248,0.03)); pointer-events: none; }
</style>
</head>
<body>
<div class="bg-particles">
  <div class="particle" style="width:300px;height:300px;background:rgba(56,189,248,0.04);top:-100px;left:-100px;animation-duration:20s;"></div>
  <div class="particle" style="width:200px;height:200px;background:rgba(56,189,248,0.06);bottom:-50px;right:-50px;animation-duration:17s;animation-delay:-5s;"></div>
</div>
<div class="container">
  <div class="logo-ring"><i class="fas fa-user-lock" style="font-size:50px;color:#38bdf8;"></i></div>
  <div class="status-badge"><i class="fas fa-exclamation-triangle"></i> PŘIHLAŠOVÁNÍ VYPNUTO</div>
  <h1>Přihlašování na web<br>je dočasně vypnuté</h1>
  <p class="subtitle">Z bezpečnostních důvodů nebo údržby účtů je možnost se přihlásit zakázána.<br>Zbytek webu ale běží dál bez problémů.</p>
  <a href="/" class="btn-back">
    <i class="fas fa-arrow-left"></i>
    Zpět na web
  </a>
</div>
<div class="wave"></div>
</body>
</html>
"""

HTML_BLOCKED = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Web mimo provoz | OIS IDPK</title>
<link rel="icon" type="image/png" href="/static/img/datacorebot_pf-lepsi.png">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; overflow: hidden; }
  .bg-particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
  .particle { position: absolute; border-radius: 50%; animation: float 15s infinite ease-in-out; opacity: 0.3; }
  @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-30px) rotate(180deg); } }
  .container { position: relative; z-index: 1; max-width: 600px; width: 100%; }
  .logo-ring { width: 120px; height: 120px; border-radius: 50%; background: rgba(239,68,68,0.1); border: 3px solid rgba(239,68,68,0.5); display: flex; align-items: center; justify-content: center; margin: 0 auto 30px auto; animation: pulse-ring 2s infinite ease-in-out; }
  @keyframes pulse-ring { 0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); } 50% { box-shadow: 0 0 0 20px rgba(239,68,68,0); } }
  .status-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(239,68,68,0.15); border: 1px solid #ef4444; border-radius: 30px; padding: 6px 18px; font-size: 13px; font-weight: bold; color: #ef4444; margin-bottom: 25px; }
  .blink { animation: blink 1s step-end infinite; } @keyframes blink { 50% { opacity: 0; } }
  h1 { font-size: clamp(28px, 6vw, 48px); font-weight: 900; line-height: 1.2; margin-bottom: 20px; color: white; }
  .subtitle { color: #94a3b8; font-size: 16px; line-height: 1.6; margin-bottom: 40px; }
  .discord-btn { display: inline-flex; align-items: center; gap: 14px; background: #5865F2; color: white; padding: 18px 40px; border-radius: 14px; text-decoration: none; font-size: 20px; font-weight: 800; transition: all 0.3s ease; box-shadow: 0 8px 30px rgba(88,101,242,0.5); border: 2px solid rgba(255,255,255,0.2); position: relative; overflow: hidden; }
  .discord-btn::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent); transition: left 0.5s; }
  .discord-btn:hover { transform: translateY(-4px) scale(1.03); box-shadow: 0 15px 45px rgba(88,101,242,0.7); }
  .discord-btn:hover::before { left: 100%; }
  .discord-btn i { font-size: 28px; }
  .admin-link { position: fixed; bottom: 20px; right: 20px; color: #475569; font-size: 12px; text-decoration: none; opacity: 0.5; transition: opacity 0.3s; padding: 6px 12px; border: 1px solid #334155; border-radius: 6px; }
  .admin-link:hover { opacity: 1; color: #94a3b8; }
  .wave { position: fixed; bottom: 0; left: 0; width: 100%; height: 200px; background: linear-gradient(180deg, transparent, rgba(239,68,68,0.03)); pointer-events: none; }
</style>
</head>
<body>
<div class="bg-particles">
  <div class="particle" style="width:300px;height:300px;background:rgba(239,68,68,0.04);top:-100px;left:-100px;animation-duration:20s;"></div>
  <div class="particle" style="width:200px;height:200px;background:rgba(239,68,68,0.06);bottom:-50px;right:-50px;animation-duration:17s;animation-delay:-5s;"></div>
</div>
<div class="container">
  <div class="logo-ring"><i class="fas fa-hard-hat" style="font-size:50px;color:#ef4444;"></i></div>
  <div class="status-badge"><span class="blink">●</span> PROBÍHÁ ÚDRŽBA</div>
  <h1>Web je momentálně<br>mimo provoz</h1>
  <p class="subtitle">Pracujeme na zlepšeních a brzy se vrátíme zpět.<br>Pro aktuální informace se připojte na náš Discord server.</p>
  <a href="https://discord.gg/vmTagbC9mF" target="_blank" class="discord-btn">
    <i class="fab fa-discord"></i>
    Přejít na Discord
  </a>
</div>
<div class="wave"></div>
<div style="position: fixed; bottom: 20px; right: 20px; display: flex; gap: 10px;">
    <a href="/dashboard" class="admin-link" style="position: relative; bottom: 0; right: 0;"><i class="fas fa-lock"></i> Přihlášení do admin dashboardu</a>
    <a href="/" class="admin-link" style="position: relative; bottom: 0; right: 0; border-color: #10b981; color: #10b981;"><i class="fas fa-shield-alt"></i> Admin Bypass</a>
</div>
</body>
</html>
"""

HTML_MAP_OFFLINE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mapa offline | OIS IDPK</title>
<link rel="icon" type="image/png" href="/static/img/datacorebot_pf-lepsi.png">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; }
  .container { max-width: 600px; width: 100%; }
  .icon-wrap { width: 110px; height: 110px; border-radius: 50%; background: rgba(56,189,248,0.08); border: 3px solid rgba(56,189,248,0.3); display: flex; align-items: center; justify-content: center; margin: 0 auto 28px auto; }
  h1 { font-size: clamp(24px, 5vw, 38px); font-weight: 900; margin-bottom: 16px; }
  .subtitle { color: #94a3b8; font-size: 16px; line-height: 1.7; margin-bottom: 40px; max-width: 500px; margin-left: auto; margin-right: auto; }
  .discord-btn { display: inline-flex; align-items: center; gap: 14px; background: #5865F2; color: white; padding: 18px 40px; border-radius: 14px; text-decoration: none; font-size: 20px; font-weight: 800; transition: all 0.3s ease; box-shadow: 0 8px 30px rgba(88,101,242,0.5); border: 2px solid rgba(255,255,255,0.2); position: relative; overflow: hidden; }
  .discord-btn::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent); transition: left 0.5s; }
  .discord-btn:hover { transform: translateY(-4px) scale(1.03); box-shadow: 0 15px 45px rgba(88,101,242,0.7); }
  .discord-btn:hover::before { left: 100%; }
  .discord-btn i { font-size: 28px; }
  .back-link { display: inline-block; margin-top: 20px; color: #64748b; font-size: 13px; text-decoration: none; padding: 6px 14px; border: 1px solid #334155; border-radius: 6px; transition: 0.2s; }
  .back-link:hover { color: #94a3b8; border-color: #475569; }
  .admin-link { position: fixed; bottom: 20px; right: 20px; color: #475569; font-size: 12px; text-decoration: none; opacity: 0.5; transition: opacity 0.3s; padding: 6px 12px; border: 1px solid #334155; border-radius: 6px; }
  .admin-link:hover { opacity: 1; color: #94a3b8; }
</style>
</head>
<body>
<div class="container">
  <div class="icon-wrap"><i class="fas fa-map" style="font-size:50px;color:#38bdf8;"></i></div>
  <h1>Interaktivní mapa<br>je momentálně mimo provoz</h1>
  <p class="subtitle">Omlouváme se, ale aktuálně je interaktivní mapa mimo provoz.<br>Pro více informací se připojte na náš Discord.</p>
  <a href="https://discord.gg/vmTagbC9mF" target="_blank" class="discord-btn">
    <i class="fab fa-discord"></i>
    Přejít na Discord
  </a>
  <br>
  <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> Zpět na hlavní stránku</a>
</div>
<a href="/dashboard" class="admin-link" id="admin-link-btn"><i class="fas fa-lock"></i> Přihlášení pro adminy</a>
<script>
// If admin is already logged in to dashboard, redirect /mapa link to /mapa_admin
fetch('/api/admin/check').then(r=>r.json()).then(d=>{
  if(d.logged_in) {
    const a = document.getElementById('admin-link-btn');
    a.href = '/mapa_admin';
    a.innerHTML = '<i class="fas fa-map-marked-alt"></i> Přejít na Mapu (Admin)';
    a.style.opacity = '0.8';
    a.style.color = '#38bdf8';
    a.style.borderColor = '#38bdf8';
  }
}).catch(()=>{});
</script>
</body>
</html>
"""

HTML_DASHBOARD_NOTIFICATIONS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; gap: 15px;">
  <div>
    <div style="display: flex; align-items: center; gap: 12px;">
      <div style="background: rgba(124, 58, 237, 0.25); color: #c084fc; width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; border: 1px solid #7c3aed;">
        <i class="fas fa-paper-plane"></i>
      </div>
      <div>
        <h2 style="margin: 0; color: var(--text-main); font-size: 22px;">Správa Notifikací & Zprávy</h2>
        <div style="color: var(--text-muted); font-size: 13px;">Přímé zprávy na Discord / E-mail, centrální audit a správa pravidel</div>
      </div>
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; padding: 6px 14px; border-radius: 8px; font-size: 13px;">
      <span style="color: var(--text-muted);">Administrátor:</span> <strong style="color: #38bdf8;">{{ admin_nick }}</strong>
    </div>
    <a href="/sprava-notifikaci" target="_blank" class="btn btn-dark" style="font-size: 12px; padding: 7px 14px; display: flex; align-items: center; gap: 6px;">
      <i class="fas fa-external-link-alt"></i> Otevřít celou stránku
    </a>
  </div>
</div>

<!-- Záložky -->
<div style="display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 12px; flex-wrap: wrap;">
  <button type="button" id="tab-btn-direct" onclick="switchDashTab('direct')" class="btn" style="background: #7c3aed; color: white; font-weight: bold; font-size: 13px; padding: 8px 18px;">
    <i class="fas fa-paper-plane"></i> Přímá zpráva na ID / E-mail
  </button>
  <button type="button" id="tab-btn-rules" onclick="switchDashTab('rules')" class="btn btn-dark" style="color: var(--text-muted); font-size: 13px; padding: 8px 18px;">
    <i class="fas fa-list-ul"></i> Aktivní pravidla (<span id="d-rules-cnt">0</span>)
  </button>
  <button type="button" id="tab-btn-hist" onclick="switchDashTab('hist')" class="btn btn-dark" style="color: var(--text-muted); font-size: 13px; padding: 8px 18px;">
    <i class="fas fa-history"></i> Historie odeslaných (<span id="d-hist-cnt">0</span>)
  </button>
</div>

<!-- SEKVENCE TAB 1: PŘÍMÁ ZPRÁVA -->
<div id="tab-content-direct" style="display: block;">
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
    <div style="background-color: var(--bg-panel); padding: 25px; border-radius: 12px; border-top: 4px solid #7c3aed; border-left: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
      <h3 style="margin-top: 0; color: #c084fc; font-size: 17px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-envelope-open-text"></i> Odeslat zprávu od Administrátora
      </h3>
      <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 20px;">
        Zpráva se doručí přímo do soukromé Discord zprávy (DM) nebo na zadaný e-mail s oficiálním označením správce.
      </p>

      <form onsubmit="handleSendDirectMsg(event)">
        <div style="margin-bottom: 15px;">
          <label style="color: var(--text-main); font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
            Cílové Discord ID nebo E-mail: <span style="color:#ef4444;">*</span>
          </label>
          <input type="text" id="direct-target" placeholder="Např. 714856037042585641 nebo uzivatel@email.cz" required style="margin: 0; padding: 11px 14px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 8px; font-size: 14px;">
          <div style="color: #64748b; font-size: 11px; margin-top: 4px;">U Discord ID zadejte číselné ID uživatele (17–20 cifer).</div>
        </div>

        <div style="margin-bottom: 15px;">
          <label style="color: var(--text-main); font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
            Nadpis / Předmět:
          </label>
          <input type="text" id="direct-title" placeholder="🔔 Zpráva administrátora DataCore" value="🔔 Zpráva administrátora DataCore" style="margin: 0; padding: 11px 14px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 8px; font-size: 14px;">
        </div>

        <div style="margin-bottom: 20px;">
          <label style="color: var(--text-main); font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
            Text zprávy: <span style="color:#ef4444;">*</span>
          </label>
          <textarea id="direct-message" rows="5" placeholder="Napište text zprávy pro uživatele..." required style="margin: 0; padding: 12px 14px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 8px; font-size: 14px; resize: vertical;"></textarea>
        </div>

        <div style="background: rgba(124, 58, 237, 0.1); border: 1px solid rgba(124, 58, 237, 0.3); border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; font-size: 12px; color: #c4b5fd;">
          <div style="font-weight: bold; margin-bottom: 4px;">🔍 Stopa administrátora v odeslané zprávě:</div>
          <div>Odesílatel: <strong>Administrátor ({{ admin_nick }})</strong></div>
          <div>Auditní stopa: Zaznamenáno do Discord logů a historie notifikací</div>
        </div>

        <button type="submit" id="btn-submit-direct" class="btn" style="width: 100%; background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; padding: 12px; font-size: 14px; font-weight: 700; border-radius: 8px; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);">
          <i class="fas fa-paper-plane"></i> Odeslat zprávu uživateli
        </button>
      </form>

      <div id="direct-msg-status" style="margin-top: 15px; display: none;"></div>
    </div>

    <!-- Nápověda a rychlé info -->
    <div style="display: flex; flex-direction: column; gap: 20px;">
      <div style="background-color: var(--bg-panel); padding: 25px; border-radius: 12px; border: 1px solid #334155;">
        <h4 style="margin-top: 0; color: #38bdf8; font-size: 15px;"><i class="fas fa-info-circle"></i> Jak funguje přímé doručení?</h4>
        <ul style="color: var(--text-muted); font-size: 13px; line-height: 1.7; padding-left: 20px; margin: 0;">
          <li><strong>Discord DM:</strong> Zpráva je odeslána robotem <em>OIS IDPK</em> přímo do soukromé konverzace uživatele. Uživatel musí mít povolené soukromé zprávy.</li>
          <li><strong>E-mail:</strong> Pokud zadáte e-mailovou adresu, zpráva je odeslána v oficiální HTML šabloně ze systémového SMTP.</li>
          <li><strong>Audit log:</strong> Každé odeslání zprávy je automaticky zaznamenáno s vaším jménem do Discord kanálu <code>🖥️・datacore-logs</code>.</li>
        </ul>
      </div>

      <div style="background-color: var(--bg-panel); padding: 25px; border-radius: 12px; border: 1px solid #334155;">
        <h4 style="margin-top: 0; color: #10b981; font-size: 15px;"><i class="fas fa-shield-alt"></i> Bezpečnost & Práva</h4>
        <p style="color: var(--text-muted); font-size: 13px; line-height: 1.6; margin: 0;">
          Tato funkce je zabezpečena rolí <strong>ADMIN</strong>. Všechny operace jsou kryptograficky a databázově chráněny.
        </p>
      </div>
    </div>
  </div>
</div>

<!-- SEKVENCE TAB 2: AKTIVNÍ PRAVIDLA -->
<div id="tab-content-rules" style="display: none;">
  <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid #334155;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
      <h3 style="margin: 0; color: var(--text-main); font-size: 16px;"><i class="fas fa-satellite-dish" style="color: #38bdf8;"></i> Všechna aktivní pravidla v systému</h3>
      <div style="display: flex; gap: 10px; align-items: center;">
        <input type="text" id="dash-rules-filter" oninput="filterDashRules()" placeholder="Hledat pravidlo / SPZ / uživatele..." style="margin: 0; padding: 7px 12px; width: 250px; font-size: 12px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 6px;">
        <button type="button" onclick="loadDashRules()" class="btn btn-dark" style="font-size: 12px; padding: 7px 12px;"><i class="fas fa-sync-alt"></i></button>
      </div>
    </div>

    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr style="border-bottom: 2px solid #334155; font-size: 12px; color: var(--blue-main);">
            <th style="padding: 10px; text-align: left;">ID</th>
            <th style="padding: 10px; text-align: left;">Komu / Uživatel</th>
            <th style="padding: 10px; text-align: left;">Cíl / Typ</th>
            <th style="padding: 10px; text-align: left;">Události</th>
            <th style="padding: 10px; text-align: left;">Kanál</th>
            <th style="padding: 10px; text-align: left;">Zahájeno</th>
            <th style="padding: 10px; text-align: left;">Poslední zpráva</th>
            <th style="padding: 10px; text-align: left;">Spuštěno</th>
            <th style="padding: 10px; text-align: right;">Akce</th>
          </tr>
        </thead>
        <tbody id="dash-rules-tbody" style="font-size: 13px;">
          <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 25px;"><i class="fas fa-spinner fa-spin"></i> Načítání pravidel...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- SEKVENCE TAB 3: HISTORIE -->
<div id="tab-content-hist" style="display: none;">
  <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid #334155;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
      <h3 style="margin: 0; color: var(--text-main); font-size: 16px;"><i class="fas fa-history" style="color: #a78bfa;"></i> Celosystémová historie odeslaných zpráv</h3>
      <div style="display: flex; gap: 10px; align-items: center;">
        <input type="text" id="dash-hist-filter" oninput="filterDashHist()" placeholder="Hledat v historii..." style="margin: 0; padding: 7px 12px; width: 250px; font-size: 12px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 6px;">
        <button type="button" onclick="loadDashHist()" class="btn btn-dark" style="font-size: 12px; padding: 7px 12px;"><i class="fas fa-sync-alt"></i></button>
      </div>
    </div>

    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr style="border-bottom: 2px solid #334155; font-size: 12px; color: #a78bfa;">
            <th style="padding: 10px; text-align: left;">Čas</th>
            <th style="padding: 10px; text-align: left;">Příjemce</th>
            <th style="padding: 10px; text-align: left;">Pravidlo / Typ</th>
            <th style="padding: 10px; text-align: left;">Spouštěč</th>
            <th style="padding: 10px; text-align: left;">Kanál</th>
            <th style="padding: 10px; text-align: left;">Obsah zprávy</th>
          </tr>
        </thead>
        <tbody id="dash-hist-tbody" style="font-size: 13px;">
          <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 25px;"><i class="fas fa-spinner fa-spin"></i> Načítání historie...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
let _dashRules = [];
let _dashHist = [];

function switchDashTab(tab) {
  document.getElementById('tab-content-direct').style.display = tab === 'direct' ? 'block' : 'none';
  document.getElementById('tab-content-rules').style.display = tab === 'rules' ? 'block' : 'none';
  document.getElementById('tab-content-hist').style.display = tab === 'hist' ? 'block' : 'none';

  const btnDirect = document.getElementById('tab-btn-direct');
  const btnRules = document.getElementById('tab-btn-rules');
  const btnHist = document.getElementById('tab-btn-hist');

  btnDirect.style.background = tab === 'direct' ? '#7c3aed' : '#334155';
  btnDirect.style.color = tab === 'direct' ? 'white' : 'var(--text-muted)';

  btnRules.style.background = tab === 'rules' ? '#7c3aed' : '#334155';
  btnRules.style.color = tab === 'rules' ? 'white' : 'var(--text-muted)';

  btnHist.style.background = tab === 'hist' ? '#7c3aed' : '#334155';
  btnHist.style.color = tab === 'hist' ? 'white' : 'var(--text-muted)';

  if (tab === 'rules' && _dashRules.length === 0) loadDashRules();
  if (tab === 'hist' && _dashHist.length === 0) loadDashHist();
}

async function handleSendDirectMsg(e) {
  e.preventDefault();
  const target = document.getElementById('direct-target').value.trim();
  const title = document.getElementById('direct-title').value.trim();
  const message = document.getElementById('direct-message').value.trim();
  const statusEl = document.getElementById('direct-msg-status');
  const btn = document.getElementById('btn-submit-direct');

  if (!target || !message) return;

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Odesílám...';
  statusEl.style.display = 'block';
  statusEl.className = 'alert alert-info';
  statusEl.innerHTML = 'Zařazuji zprávu do odesílací fronty...';

  try {
    const res = await fetch('/api/admin/notifications/send_direct', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ target, title, message })
    });
    const data = await res.json();
    if (data.status === 'success') {
      statusEl.className = 'alert alert-success';
      statusEl.innerHTML = '<i class="fas fa-check-circle"></i> ' + (data.message || 'Zpráva byla úspěšně odeslána!');
      document.getElementById('direct-message').value = '';
      loadDashHist();
    } else {
      statusEl.className = 'alert alert-danger';
      statusEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + (data.message || 'Chyba při odesílání');
    }
  } catch (err) {
    statusEl.className = 'alert alert-danger';
    statusEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Chyba spojení se serverem: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-paper-plane"></i> Odeslat zprávu uživateli';
  }
}

function formatCzechDateTime(isoStr) {
  if (!isoStr) return null;
  try {
    let d = new Date(isoStr);
    if (isNaN(d.getTime())) return String(isoStr).replace('T', ' ').split('.')[0];
    let dd = String(d.getDate()).padStart(2, '0');
    let mm = String(d.getMonth() + 1).padStart(2, '0');
    let yyyy = d.getFullYear();
    let hh = String(d.getHours()).padStart(2, '0');
    let min = String(d.getMinutes()).padStart(2, '0');
    return `${dd}.${mm}.${yyyy} ${hh}:${min}`;
  } catch(e) {
    return String(isoStr);
  }
}

async function loadDashRules() {
  const tbody = document.getElementById('dash-rules-tbody');
  tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 25px;"><i class="fas fa-spinner fa-spin"></i> Načítání pravidel...</td></tr>';
  try {
    const res = await fetch('/api/admin/notifications/all_rules');
    const data = await res.json();
    _dashRules = data.rules || [];
    document.getElementById('d-rules-cnt').innerText = _dashRules.length;
    renderDashRules(_dashRules);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #ef4444; padding: 25px;">Chyba při načítání pravidel: ' + err.message + '</td></tr>';
  }
}

function renderDashRules(rules) {
  const tbody = document.getElementById('dash-rules-tbody');
  tbody.innerHTML = '';
  if (!rules || rules.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 25px;">Žádná aktivní pravidla v systému.</td></tr>';
    return;
  }

  rules.forEach(r => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #334155';
    let triggersArr = [];
    if (r.triggers) {
      for (const [k, v] of Object.entries(r.triggers)) {
        if (v && v !== 'none' && v !== false) triggersArr.push(k);
      }
    }
    const trigStr = triggersArr.join(', ') || '-';
    const channels = Array.isArray(r.delivery_channels) ? r.delivery_channels.join(', ') : (r.channel || 'discord');

    let uNick = r.user_nick || '';
    let uDid = r.user_discord_id || '';
    let uEmail = r.user_email || '';
    let uRole = r.user_role || '';
    let uSess = String(r.user_session || '');

    let mainName = uNick;
    if (!mainName) {
      if (uSess.startsWith('admin_direct_discord_')) mainName = 'Discord DM #' + uSess.replace('admin_direct_discord_', '');
      else if (uSess.startsWith('admin_direct_email_')) mainName = 'E-mail ' + uSess.replace('admin_direct_email_', '');
      else if (uSess) mainName = 'Uživatel #' + uSess;
      else mainName = 'Neznámý';
    }

    let subDetails = [];
    if (uDid && uDid !== mainName) subDetails.push(`<span title="Discord ID" style="display:inline-flex;align-items:center;gap:3px;"><i class="fab fa-discord" style="color:#5865F2;"></i> ${uDid}</span>`);
    if (uEmail && uEmail !== mainName) subDetails.push(`<span title="E-mail" style="display:inline-flex;align-items:center;gap:3px;"><i class="fas fa-envelope" style="color:#38bdf8;"></i> ${uEmail}</span>`);
    if (uSess && !uSess.startsWith('admin_direct_')) subDetails.push(`<span style="color:#64748b;">(ID: ${uSess})</span>`);

    let userHtml = `
      <div style="display:flex;flex-direction:column;gap:3px;">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          <strong style="color:#f8fafc;font-size:13px;">${mainName}</strong>
          ${uRole ? `<span style="background:rgba(59,130,246,0.2);color:#93c5fd;border:1px solid rgba(59,130,246,0.35);padding:1px 5px;border-radius:4px;font-size:9px;font-weight:700;">${uRole}</span>` : ''}
        </div>
        ${subDetails.length ? `<div style="font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">${subDetails.join('')}</div>` : ''}
      </div>
    `;

    let createdStr = formatCzechDateTime(r.created_at);
    let lastFiredStr = formatCzechDateTime(r.last_fired_at);

    tr.innerHTML = `
      <td style="padding: 10px; color: #64748b; font-family: monospace;">#${String(r.id).slice(0, 8)}</td>
      <td style="padding: 10px;">${userHtml}</td>
      <td style="padding: 10px; font-weight: bold; color: var(--blue-main);">
        ${r.identifier || '-'} <span style="font-size: 11px; color: var(--text-muted);">(${r.identifier_type || 'spz'})</span>
        ${r.label ? `<div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">${r.label}</div>` : ''}
      </td>
      <td style="padding: 10px; color: #c4b5fd; font-size: 12px;">${trigStr}</td>
      <td style="padding: 10px;"><span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${channels}</span></td>
      <td style="padding: 10px; white-space: nowrap;">
        ${createdStr ? `<span style="color: #cbd5e1; font-size: 11px;"><i class="far fa-calendar-alt" style="color: #94a3b8; margin-right: 4px;"></i>${createdStr}</span>` : '<span style="color: #64748b; font-size: 11px;">-</span>'}
      </td>
      <td style="padding: 10px; white-space: nowrap;">
        ${lastFiredStr ? `<span style="color: #38bdf8; font-size: 11px;"><i class="fas fa-paper-plane" style="color: #0284c7; margin-right: 4px;"></i>${lastFiredStr}</span>` : '<span style="color: #64748b; font-size: 11px; font-style: italic;">Zatím neodesláno</span>'}
      </td>
      <td style="padding: 10px;"><b style="color: #10b981; font-size: 12px;">${r.fired_count || 0}x</b></td>
      <td style="padding: 10px; text-align: right;">
        <button type="button" class="btn btn-danger" onclick="deleteDashRule('${r.id}')" style="padding: 4px 8px; font-size: 11px;">
          <i class="fas fa-trash"></i> Smazat
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterDashRules() {
  const q = document.getElementById('dash-rules-filter').value.toLowerCase();
  if (!q) return renderDashRules(_dashRules);
  const filtered = _dashRules.filter(r => 
    String(r.identifier || '').toLowerCase().includes(q) ||
    String(r.label || '').toLowerCase().includes(q) ||
    String(r.user_session || '').toLowerCase().includes(q) ||
    String(r.user_nick || '').toLowerCase().includes(q) ||
    String(r.user_discord_id || '').toLowerCase().includes(q) ||
    String(r.user_email || '').toLowerCase().includes(q) ||
    String(r.id || '').toLowerCase().includes(q)
  );
  renderDashRules(filtered);
}
  renderDashRules(filtered);
}

async function deleteDashRule(id) {
  if (!confirm('Opravdu chcete toto pravidlo trvale smazat?')) return;
  try {
    const res = await fetch('/api/admin/notifications/delete_rule', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id })
    });
    const d = await res.json();
    if (d.status === 'success') {
      _dashRules = _dashRules.filter(r => r.id !== id);
      document.getElementById('d-rules-cnt').innerText = _dashRules.length;
      renderDashRules(_dashRules);
    } else {
      alert('Chyba: ' + (d.message || 'Nepodařilo se smazat pravidlo'));
    }
  } catch (e) {
    alert('Chyba spojení: ' + e.message);
  }
}

async function loadDashHist() {
  const tbody = document.getElementById('dash-hist-tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 25px;"><i class="fas fa-spinner fa-spin"></i> Načítání historie...</td></tr>';
  try {
    const res = await fetch('/api/admin/notifications/history');
    const data = await res.json();
    _dashHist = data.history || [];
    document.getElementById('d-hist-cnt').innerText = _dashHist.length;
    renderDashHist(_dashHist);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #ef4444; padding: 25px;">Chyba: ' + err.message + '</td></tr>';
  }
}

function renderDashHist(hist) {
  const tbody = document.getElementById('dash-hist-tbody');
  tbody.innerHTML = '';
  if (!hist || hist.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 25px;">Zatím žádná zaznamenaná historie.</td></tr>';
    return;
  }

  hist.forEach(h => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #334155';
    tr.innerHTML = `
      <td style="padding: 10px; color: #64748b; font-size: 11px; white-space: nowrap;">${h.time || '-'}</td>
      <td style="padding: 10px; font-weight: bold; color: var(--blue-main);">${h.target || '-'}</td>
      <td style="padding: 10px; color: var(--text-main);">${h.rule_id || '-'}</td>
      <td style="padding: 10px; color: #c4b5fd;">${h.trigger || '-'}</td>
      <td style="padding: 10px;"><span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${h.channel || 'DM'}</span></td>
      <td style="padding: 10px; color: #94a3b8; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${h.message || '-'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function filterDashHist() {
  const q = document.getElementById('dash-hist-filter').value.toLowerCase();
  if (!q) return renderDashHist(_dashHist);
  const filtered = _dashHist.filter(h => 
    String(h.target || '').toLowerCase().includes(q) ||
    String(h.rule_id || '').toLowerCase().includes(q) ||
    String(h.trigger || '').toLowerCase().includes(q) ||
    String(h.message || '').toLowerCase().includes(q)
  );
  renderDashHist(filtered);
}

// Inicializace počtů při načtení
loadDashRules();
loadDashHist();
</script>
"""


HTML_INTERAKTIVNI_MAPA_DASHBOARD = """
<style>
  .dash-container { max-width: 1500px; margin: 0 auto; padding-bottom: 50px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .dash-top-card { border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 14px; transition: transform 0.2s; }
  .dash-top-card:hover { transform: translateY(-2px); }
  .dash-tabs-bar { display: flex; gap: 6px; border-bottom: 2px solid #334155; margin-bottom: 20px; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: thin; }
  .dash-tab-btn { background: transparent; border: none; padding: 12px 18px; color: #94a3b8; border-bottom: 3px solid transparent; font-weight: bold; font-size: 14px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0; transition: all 0.2s; }
  .dash-tab-btn.active { color: #38bdf8; border-bottom-color: #38bdf8; }
  .bus-link { color: #38bdf8; text-decoration: none; font-weight: bold; }
  .bus-link:hover { text-decoration: underline; color: #7dd3fc; }
  
  @media (max-width: 768px) {
    .dash-header-wrap { flex-direction: column !important; align-items: stretch !important; gap: 14px !important; }
    .dash-header-actions { flex-direction: column !important; width: 100% !important; gap: 8px !important; }
    .dash-header-actions button, .dash-header-actions a { width: 100% !important; justify-content: center !important; }
    .dash-stats-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 10px !important; }
    .dash-stats-grid > div:last-child { grid-column: span 2; }
    
    /* Mobilní karty místo tabulek */
    .mobile-cards-table, .mobile-cards-table thead, .mobile-cards-table tbody, .mobile-cards-table th, .mobile-cards-table td, .mobile-cards-table tr { 
      display: block !important; 
    }
    .mobile-cards-table thead tr { 
      position: absolute !important; top: -9999px !important; left: -9999px !important; 
    }
    .mobile-cards-table tbody tr { 
      background: #0f172a !important; 
      border: 1px solid #334155 !important; 
      border-radius: 10px !important; 
      margin-bottom: 14px !important; 
      padding: 14px !important; 
    }
    .mobile-cards-table td { 
      padding: 8px 0 !important; 
      border: none !important; 
      border-bottom: 1px dashed rgba(255,255,255,0.08) !important; 
      display: flex !important; 
      flex-direction: column !important; 
      gap: 3px !important; 
    }
    .mobile-cards-table td:last-child { 
      border-bottom: none !important; 
      padding-top: 10px !important; 
    }
    .mobile-cards-table td::before { 
      content: attr(data-label); 
      font-size: 11px; 
      text-transform: uppercase; 
      color: #94a3b8; 
      font-weight: 700; 
      letter-spacing: 0.5px; 
      margin-bottom: 2px;
    }
    .mobile-edit-box {
      flex-direction: column !important;
      align-items: stretch !important;
      gap: 8px !important;
    }
    .mobile-edit-box input {
      width: 100% !important;
      box-sizing: border-box !important;
    }
    .mobile-edit-box button {
      width: 100% !important;
      padding: 8px 12px !important;
    }
  }
</style>

<div class="dash-container">
  <!-- Header -->
  <div class="dash-header-wrap" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; border-bottom: 1px solid #334155; padding-bottom: 15px;">
    <div>
      <h1 style="color: var(--blue-main); margin: 0; font-size: 24px; display: flex; align-items: center; gap: 12px;">
        <i class="fas fa-map-marked-alt"></i> Interaktivní mapa & Přehled chyb
      </h1>
      <div style="color: var(--text-muted); font-size: 13px; margin-top: 5px;">
        Centrální dispečink pro přehled chyb, rozluštění ukradených SPZ, log automatiky a správu zadaných řidičů a poznámek.
      </div>
    </div>
    <div class="dash-header-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
      <button onclick="triggerAnalysis()" id="btn-trigger-analysis" class="btn" style="background: linear-gradient(135deg, #0284c7, #2563eb); color: white; font-weight: bold; padding: 10px 16px; border-radius: 8px; display: flex; align-items: center; gap: 8px; border: none; cursor: pointer; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);">
        <i class="fas fa-bolt"></i> Spustit rozluštění chyb
      </button>
      <button onclick="toggleAutoResolve()" id="btn-auto-resolve" class="btn" style="background: #334155; color: #f1f5f9; font-weight: bold; padding: 10px 16px; border-radius: 8px; display: flex; align-items: center; gap: 8px; border: 1px solid #475569; cursor: pointer;">
        <i class="fas fa-robot"></i> <span id="auto-resolve-label">Režim: Manuální schvalování</span>
      </button>
      <button onclick="loadSpzControlData()" class="btn" style="background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 10px 14px; border-radius: 8px; cursor: pointer;" title="Obnovit data">
        <i class="fas fa-sync-alt" id="refresh-icon"></i>
      </button>
      <a href="https://datacorebot.koyeb.app/mapa" target="_blank" class="btn btn-success" style="padding: 10px 16px; border-radius: 8px; display: flex; align-items: center; gap: 8px; text-decoration: none; font-weight: bold;">
        <i class="fas fa-external-link-alt"></i> Otevřít živou mapu
      </a>
    </div>
  </div>

  <!-- Toast notification banner -->
  <div id="spz-toast" style="display: none; padding: 12px 20px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; transition: all 0.3s ease;"></div>

  <!-- Automode Banner -->
  <div id="automode-banner-container" style="margin-bottom: 22px;"></div>

  <!-- Top Stats Cards -->
  <div class="dash-stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;">
    <!-- Neznámá SPZ -->
    <div class="dash-top-card" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3);">
      <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(239, 68, 68, 0.2); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #ef4444;">
        <i class="fas fa-satellite-dish"></i>
      </div>
      <div>
        <div style="font-size: 11px; text-transform: uppercase; color: #f87171; font-weight: bold;">Aktivní hledání</div>
        <div id="stat-unknown" style="font-size: 24px; font-weight: bold; color: white;">0</div>
        <div style="font-size: 11px; color: #94a3b8;">Čeká na jízdu a Arrivu</div>
      </div>
    </div>

    <!-- Duplicity SPZ -->
    <div class="dash-top-card" style="background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.3);">
      <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(249, 115, 22, 0.2); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #f97316;">
        <i class="fas fa-clone"></i>
      </div>
      <div>
        <div style="font-size: 11px; text-transform: uppercase; color: #fb923c; font-weight: bold;">Duplicitní SPZ</div>
        <div id="stat-duplicate" style="font-size: 24px; font-weight: bold; color: white;">0</div>
        <div style="font-size: 11px; color: #94a3b8;">Konflikty / ukradeno</div>
      </div>
    </div>

    <!-- Neověřená SPZ -->
    <div class="dash-top-card" style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3);">
      <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.2); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #f59e0b;">
        <i class="fas fa-hourglass-half"></i>
      </div>
      <div>
        <div style="font-size: 11px; text-transform: uppercase; color: #fbbf24; font-weight: bold;">Neověřené SPZ</div>
        <div id="stat-unverified" style="font-size: 24px; font-weight: bold; color: white;">0</div>
        <div style="font-size: 11px; color: #94a3b8;">Probíhá stabilizace</div>
      </div>
    </div>

    <!-- Návrhy k řešení -->
    <div class="dash-top-card" style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3);">
      <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(168, 85, 247, 0.2); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #a855f7;">
        <i class="fas fa-balance-scale"></i>
      </div>
      <div>
        <div style="font-size: 11px; text-transform: uppercase; color: #c084fc; font-weight: bold;">Návrhy k posouzení</div>
        <div id="stat-proposals" style="font-size: 24px; font-weight: bold; color: white;">0</div>
        <div style="font-size: 11px; color: #94a3b8;">Rozluštění SPZ</div>
      </div>
    </div>

    <!-- Log automatiky -->
    <div class="dash-top-card" style="background: rgba(2, 132, 199, 0.1); border: 1px solid rgba(2, 132, 199, 0.3);">
      <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(2, 132, 199, 0.2); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #38bdf8;">
        <i class="fas fa-robot"></i>
      </div>
      <div>
        <div style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: bold;">Log automatiky</div>
        <div id="stat-automation" style="font-size: 24px; font-weight: bold; color: white;">0</div>
        <div style="font-size: 11px; color: #94a3b8;">Zaznamenané akce</div>
      </div>
    </div>
  </div>

  <!-- Navigation Tabs -->
  <div class="dash-tabs-bar">
    <button onclick="switchTab('spz')" id="tab-btn-spz" class="dash-tab-btn active">
      <i class="fas fa-exclamation-triangle"></i> Přehled chyb <span id="badge-tab-spz" style="background: #ef4444; color: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 5px;">0</span>
    </button>
    <button onclick="switchTab('proposals')" id="tab-btn-proposals" class="dash-tab-btn">
      <i class="fas fa-balance-scale"></i> Návrhy systému k rozluštění <span id="badge-tab-proposals" style="background: #a855f7; color: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 5px;">0</span>
    </button>
    <button onclick="switchTab('automation')" id="tab-btn-automation" class="dash-tab-btn">
      <i class="fas fa-history"></i> Log automatiky mapy <span id="badge-tab-automation" style="background: #0284c7; color: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 5px;">0</span>
    </button>
    <button onclick="switchTab('drivers')" id="tab-btn-drivers" class="dash-tab-btn">
      <i class="fas fa-user-tag"></i> Zadaná jména & Poznámky <span id="badge-tab-drivers" style="background: #10b981; color: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 5px;">0</span>
    </button>
    <button onclick="switchTab('invalid')" id="tab-btn-invalid" class="dash-tab-btn">
      <i class="fas fa-ban"></i> Neplatná ověření Neznámé <span id="badge-tab-invalid" style="background: #64748b; color: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 5px;">0</span>
    </button>
  </div>

  <!-- TAB 1: PŘEHLED CHYB (BOD 6) -->
  <div id="tab-content-spz">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 15px;">
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button onclick="setSpzFilter('all')" class="spz-filter-btn" id="filter-all" style="background: #334155; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: bold;">Všechny chyby</button>
          <button onclick="setSpzFilter('duplicate')" class="spz-filter-btn" id="filter-duplicate" style="background: #0f172a; color: #fb923c; border: 1px solid #f97316; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">Pouze Duplicity</button>
          <button onclick="setSpzFilter('unknown')" class="spz-filter-btn" id="filter-unknown" style="background: #0f172a; color: #f87171; border: 1px solid #ef4444; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">Aktivní hledání</button>
          <button onclick="setSpzFilter('unverified')" class="spz-filter-btn" id="filter-unverified" style="background: #0f172a; color: #fbbf24; border: 1px solid #f59e0b; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">Neověřené</button>
          <button onclick="setSpzFilter('watched')" class="spz-filter-btn" id="filter-watched" style="background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;"><i class="fas fa-eye"></i> Hlídáno systémem (<span id="stat-watched-badge">0</span>)</button>
          <button onclick="setSpzFilter('ignored')" class="spz-filter-btn" id="filter-ignored" style="background: #0f172a; color: #94a3b8; border: 1px solid #64748b; padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;"><i class="fas fa-eye-slash"></i> Nechat být (<span id="stat-ignored-badge">0</span>)</button>
        </div>
        <div style="position: relative; min-width: 260px; flex: 1; max-width: 420px;">
          <input type="text" id="spz-search" oninput="renderSpzTable()" placeholder="Hledat vůz ID, linku, SPZ, model, chybu..." style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: white; padding: 8px 12px 8px 32px; border-radius: 6px; font-size: 13px;">
          <i class="fas fa-search" style="position: absolute; left: 10px; top: 11px; color: #64748b; font-size: 12px;"></i>
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="mobile-cards-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background: #0f172a; border-bottom: 2px solid #334155; text-align: left; color: #94a3b8;">
              <th style="padding: 12px;">Vůz ID / Linka</th>
              <th style="padding: 12px;">Model vozidla / Spoj</th>
              <th style="padding: 12px;">Stav SPZ</th>
              <th style="padding: 12px;">Důvod chyby / Popis</th>
              <th style="padding: 12px; min-width: 250px;">Rychlá oprava SPZ</th>
              <th style="padding: 12px; text-align: center;">Akce</th>
            </tr>
          </thead>
          <tbody id="spz-table-body">
            <tr><td colspan="6" style="text-align: center; padding: 30px; color: #64748b;"><i class="fas fa-spinner fa-spin"></i> Načítání chybových vozidel z aktivní mapy...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 2: NÁVRHY SYSTÉMU K ROZLUŠTĚNÍ (BOD 3 & 5) -->
  <div id="tab-content-proposals" style="display: none;">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <div>
          <h3 style="color: #c084fc; margin: 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
            <i class="fas fa-balance-scale"></i> Rozluštění ukradených a sporných SPZ
          </h3>
          <p style="color: var(--text-muted); font-size: 12px; margin: 5px 0 0 0;">
            Když systém zjistí, že dva busy stály u sebe a jeden ukradl SPZ druhému, najde na Arriva mapě reálné vysílače a nabídne vám přímé rozluštění s klikem na mapu obou vozů.
          </p>
        </div>
      </div>
      <!-- Proposals sub-filter tabs -->
      <div id="proposal-filters-bar" style="display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap;"></div>
      <div id="proposals-container" style="display: flex; flex-direction: column; gap: 15px;">
        <div style="text-align: center; padding: 30px; color: #64748b;"><i class="fas fa-spinner fa-spin"></i> Načítání návrhů systému...</div>
      </div>
    </div>
  </div>

  <!-- TAB 3: LOG AUTOMATIKY MAPY (BOD 5) -->
  <div id="tab-content-automation" style="display: none;">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;">
        <div>
          <h3 style="color: #38bdf8; margin: 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
            <i class="fas fa-robot"></i> Log automatiky interaktivní mapy
          </h3>
          <p style="color: var(--text-muted); font-size: 12px; margin: 5px 0 0 0;">
            Přehled všech automatických kroků: vyřešení duplicit, přiřazení SPZ, vjezdy do vozoven, příchody na konečné a rozhodnutí dispečinku.
          </p>
        </div>
        <div style="position: relative; min-width: 240px;">
          <input type="text" id="automation-search" oninput="renderAutomationLog()" placeholder="Filtrovat log automatiky..." style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: white; padding: 8px 12px 8px 32px; border-radius: 6px; font-size: 13px;">
          <i class="fas fa-search" style="position: absolute; left: 10px; top: 11px; color: #64748b; font-size: 12px;"></i>
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="mobile-cards-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background: #0f172a; border-bottom: 2px solid #334155; text-align: left; color: #94a3b8;">
              <th style="padding: 12px; width: 90px;">Čas</th>
              <th style="padding: 12px; width: 140px;">Typ akce</th>
              <th style="padding: 12px;">Vůz / Linka / SPZ</th>
              <th style="padding: 12px;">Popis události automatiky</th>
              <th style="padding: 12px; text-align: center; width: 110px;">Zobrazit</th>
            </tr>
          </thead>
          <tbody id="automation-table-body">
            <tr><td colspan="5" style="text-align: center; padding: 30px; color: #64748b;"><i class="fas fa-spinner fa-spin"></i> Načítání logu automatiky...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 4: ZADANÁ JMÉNA A POZNÁMKY (BOD 4) -->
  <div id="tab-content-drivers" style="display: none;">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 15px;">
        <div>
          <h3 style="color: #34d399; margin: 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
            <i class="fas fa-address-book"></i> Seznam všech zadaných řidičů a poznámek z mapy
          </h3>
          <p style="color: var(--text-muted); font-size: 12px; margin: 5px 0 0 0;">
            Kompletní přehled všech jmen řidičů a poznámek, které jste vložili do interaktivní mapy (zahrnuje živou mapu i trvalou paměť).
          </p>
        </div>
        <div style="position: relative; min-width: 250px;">
          <input type="text" id="driver-search" oninput="renderDriversTable()" placeholder="Hledat řidiče či poznámku..." style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: white; padding: 8px 12px 8px 32px; border-radius: 6px; font-size: 13px;">
          <i class="fas fa-search" style="position: absolute; left: 10px; top: 11px; color: #64748b; font-size: 12px;"></i>
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="mobile-cards-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background: #0f172a; border-bottom: 2px solid #334155; text-align: left; color: #94a3b8;">
              <th style="padding: 12px;">Vůz ID / SPZ</th>
              <th style="padding: 12px;">Jméno řidiče (Admin)</th>
              <th style="padding: 12px;">Poznámka vozu</th>
              <th style="padding: 12px;">Linka & Model</th>
              <th style="padding: 12px;">Stav</th>
              <th style="padding: 12px;">Datum / Čas uložení</th>
              <th style="padding: 12px; text-align: center;">Mapa</th>
            </tr>
          </thead>
          <tbody id="drivers-table-body">
            <tr><td colspan="7" style="text-align: center; padding: 30px; color: #64748b;"><i class="fas fa-spinner fa-spin"></i> Načítání řidičů a poznámek...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 5: NEPLATNÁ OVĚŘENÍ NEZNÁMÉ SPZ (BOD 3) -->
  <div id="tab-content-invalid" style="display: none;">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
      <div style="margin-bottom: 15px;">
        <h3 style="color: #f87171; margin: 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
          <i class="fas fa-shield-alt"></i> Automaticky opravená neplatná ověření
        </h3>
        <p style="color: var(--text-muted); font-size: 12px; margin: 5px 0 0 0;">
          Jakmile je detekováno admin ověření pro SPZ "NEZNÁMÁ" či "AKTIVNÍ HLEDÁNÍ", systém automaticky vyhodí chybu, tento neplatný status zruší a zapíše jej do tohoto přehledu.
        </p>
      </div>

      <div id="invalid-log-container">
        <div style="text-align: center; padding: 30px; color: #64748b;">Žádná neplatná ověření nebyla zaznamenána.</div>
      </div>
    </div>
  </div>
</div>

<script>
let _dashData = null;
let _currentSpzFilter = 'all';
let _currentProposalFilter = 'all';

function showToast(text, isError = false) {
  const t = document.getElementById('spz-toast');
  t.innerText = text;
  t.style.display = 'block';
  t.style.background = isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)';
  t.style.color = isError ? '#fca5a5' : '#86efac';
  t.style.border = isError ? '1px solid #ef4444' : '1px solid #10b981';
  setTimeout(() => { t.style.display = 'none'; }, 4000);
}

function switchTab(tabName) {
  ['spz', 'proposals', 'automation', 'drivers', 'invalid'].forEach(t => {
    const el = document.getElementById('tab-content-' + t);
    const btn = document.getElementById('tab-btn-' + t);
    if (t === tabName) {
      if (el) el.style.display = 'block';
      if (btn) btn.classList.add('active');
    } else {
      if (el) el.style.display = 'none';
      if (btn) btn.classList.remove('active');
    }
  });
}

function setSpzFilter(filterName) {
  _currentSpzFilter = filterName;
  ['all', 'unknown', 'duplicate', 'unverified', 'watched', 'ignored'].forEach(f => {
    const b = document.getElementById('filter-' + f);
    if (!b) return;
    if (f === filterName) {
      b.style.background = '#334155';
      b.style.fontWeight = 'bold';
    } else {
      b.style.background = '#0f172a';
      b.style.fontWeight = 'normal';
    }
  });
  renderSpzTable();
}

function setProposalFilter(filterName) {
  _currentProposalFilter = filterName;
  renderProposals();
}

async function loadSpzControlData() {
  const icon = document.getElementById('refresh-icon');
  if (icon) icon.classList.add('fa-spin');
  try {
    const res = await fetch('/api/admin/spz_control_data');
    if (!res.ok) throw new Error('Chyba načtení: ' + res.status);
    _dashData = await res.json();
    renderDashboardUI();
  } catch (err) {
    console.error('Chyba načítání SPZ dashboardu:', err);
    showToast('Chyba komunikace se serverem: ' + err.message, true);
  } finally {
    if (icon) icon.classList.remove('fa-spin');
  }
}

function renderDashboardUI() {
  if (!_dashData) return;
  const s = _dashData.stats || {};
  document.getElementById('stat-unknown').innerText = s.unknown_count || 0;
  document.getElementById('stat-duplicate').innerText = s.duplicate_count || 0;
  document.getElementById('stat-unverified').innerText = s.unverified_count || 0;
  document.getElementById('stat-proposals').innerText = s.pending_proposals_count || 0;
  document.getElementById('stat-automation').innerText = (s.automation_log_count || (_dashData.automation_log || []).length) || 0;
  const watchedBadge = document.getElementById('stat-watched-badge');
  if (watchedBadge) {
    watchedBadge.innerText = s.watched_buses_count || (_dashData.watched_buses || []).length || 0;
  }
  const ignoredBadge = document.getElementById('stat-ignored-badge');
  if (ignoredBadge) {
    ignoredBadge.innerText = s.ignored_buses_count || (_dashData.ignored_buses || []).length || 0;
  }

  document.getElementById('badge-tab-spz').innerText = (s.unknown_count || 0) + (s.duplicate_count || 0) + (s.unverified_count || 0);
  document.getElementById('badge-tab-proposals').innerText = s.pending_proposals_count || 0;
  document.getElementById('badge-tab-automation').innerText = (_dashData.automation_log || []).length;
  document.getElementById('badge-tab-drivers').innerText = s.drivers_notes_count || 0;
  document.getElementById('badge-tab-invalid').innerText = s.invalid_verifications_count || 0;

  // Automode tlačítko v hlavičce
  const autoBtn = document.getElementById('btn-auto-resolve');
  const autoLbl = document.getElementById('auto-resolve-label');
  if (_dashData.auto_resolve) {
    autoBtn.style.background = 'linear-gradient(135deg, #059669, #10b981)';
    autoBtn.style.borderColor = '#10b981';
    autoLbl.innerText = 'Automode: AKTIVNÍ';
  } else {
    autoBtn.style.background = '#334155';
    autoBtn.style.borderColor = '#475569';
    autoLbl.innerText = 'Automode: Vypnuto';
  }

  // Automode status banner (přehledný informační pás)
  const bannerContainer = document.getElementById('automode-banner-container');
  if (bannerContainer) {
    if (_dashData.auto_resolve) {
      bannerContainer.innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(6, 78, 59, 0.28)); border: 1px solid #10b981; border-radius: 12px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.12);">
          <div style="display: flex; align-items: flex-start; gap: 14px; max-width: 950px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.25); display: flex; align-items: center; justify-content: center; font-size: 22px; color: #34d399; flex-shrink: 0; border: 1px solid rgba(16, 185, 129, 0.4);">
              <i class="fas fa-robot"></i>
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 15px; font-weight: 800; color: #6ee7b7; text-transform: uppercase; letter-spacing: 0.5px;">
                  <i class="fas fa-check-circle" style="color: #10b981;"></i> Automode je AKTIVNÍ – Spolehlivé rozluštění duplicit
                </span>
                <span style="background: rgba(16, 185, 129, 0.2); color: #a7f3d0; border: 1px solid #10b981; font-size: 11px; padding: 2px 8px; border-radius: 6px; font-weight: bold;">
                  Ověřování linky & polohy Arriva (do 850m)
                </span>
              </div>
              <div style="color: #cbd5e1; font-size: 13px; margin-top: 5px; line-height: 1.5;">
                Při detekci duplicity systém <b>ponechá SPZ oprávněnému vozu</b>. U duplicitního vozu vyhledá <b>skutečný vysílač z Arriva mapy na shodné lince</b>. Pokud na mapě ještě není, <b>netipuje naslepo</b> cizí vozy a bezpečně nastaví <i>Aktivní hledání</i>.
                <div style="color: #fca5a5; font-size: 11px; margin-top: 3px;">
                  <i class="fas fa-shield-alt"></i> Bezpečnostní pojistka: Zjistí-li systém 2x administrátorsky ověřenou SPZ, rozluštění nepřepíše a předá jej k manuálnímu potvrzení dispečerem.
                </div>
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="toggleAutoResolve()" style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #fca5a5; padding: 8px 14px; border-radius: 8px; font-weight: bold; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s;">
              <i class="fas fa-pause"></i> Pozastavit Automode
            </button>
          </div>
        </div>
      `;
    } else {
      bannerContainer.innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(120, 53, 15, 0.25)); border: 1px solid #f59e0b; border-radius: 12px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; box-shadow: 0 4px 20px rgba(245, 158, 11, 0.12);">
          <div style="display: flex; align-items: flex-start; gap: 14px; max-width: 950px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.25); display: flex; align-items: center; justify-content: center; font-size: 22px; color: #fbbf24; flex-shrink: 0; border: 1px solid rgba(245, 158, 11, 0.4);">
              <i class="fas fa-user-cog"></i>
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 15px; font-weight: 800; color: #fde68a; text-transform: uppercase; letter-spacing: 0.5px;">
                  <i class="fas fa-pause-circle" style="color: #f59e0b;"></i> Automode je POZASTAVEN – Režim manuálního schvalování
                </span>
              </div>
              <div style="color: #cbd5e1; font-size: 13px; margin-top: 5px; line-height: 1.5;">
                Všechny duplicity a sporné situace vyžadují manuální rozhodnutí dispečera v záložce <i>Návrhy systému k rozluštění</i>.
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="toggleAutoResolve()" style="background: linear-gradient(135deg, #059669, #10b981); border: none; color: white; padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);">
              <i class="fas fa-play"></i> Zapnout Automode
            </button>
          </div>
        </div>
      `;
    }
  }

  renderSpzTable();
  renderProposals();
  renderAutomationLog();
  renderDriversTable();
  renderInvalidLog();
}

function setQuickInp(busId, spzVal) {
  const inp = document.getElementById('spz-inp-' + busId);
  if (inp) {
    inp.value = spzVal;
    inp.focus();
  }
}

function renderSpzTable() {
  if (!_dashData) return;
  const tbody = document.getElementById('spz-table-body');
  const q = (document.getElementById('spz-search').value || '').toLowerCase().trim();

  const allList = [...(_dashData.duplicate_buses || []), ...(_dashData.unknown_buses || []), ...(_dashData.unverified_buses || [])];
  const seenBids = new Set();
  const uniqueAll = [];
  for (const b of allList) {
    const k = String(b.bus_id);
    if (!seenBids.has(k)) {
      seenBids.add(k);
      uniqueAll.push(b);
    }
  }

  let list = [];
  if (_currentSpzFilter === 'ignored') {
    list = uniqueAll.filter(b => b.is_ignored);
  } else if (_currentSpzFilter === 'all') {
    list = uniqueAll.filter(b => !b.is_ignored);
  } else if (_currentSpzFilter === 'duplicate') {
    list = (_dashData.duplicate_buses || []).filter(b => !b.is_ignored);
  } else if (_currentSpzFilter === 'unknown') {
    list = (_dashData.unknown_buses || []).filter(b => !b.is_ignored);
  } else if (_currentSpzFilter === 'unverified') {
    list = (_dashData.unverified_buses || []).filter(b => !b.is_ignored);
  } else if (_currentSpzFilter === 'watched') {
    list = uniqueAll.filter(b => b.is_watched && !b.is_ignored);
  }

  if (q) {
    list = list.filter(b => 
      String(b.bus_id || '').toLowerCase().includes(q) ||
      String(b.line || '').toLowerCase().includes(q) ||
      String(b.spz || '').toLowerCase().includes(q) ||
      String(b.vehicle_type || '').toLowerCase().includes(q) ||
      String(b.real_linka_spoj || '').toLowerCase().includes(q) ||
      String(b.reason || '').toLowerCase().includes(q)
    );
  }

  if (list.length === 0) {
    if (_currentSpzFilter === 'ignored') {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 30px; color: #94a3b8;"><i class="fas fa-eye-slash"></i> Žádné vozy nejsou označeny jako "Nechat být".</td></tr>`;
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 30px; color: #10b981;"><i class="fas fa-check-circle"></i> Vše v pořádku! Žádné chyby v této kategorii.</td></tr>`;
    }
    return;
  }

  tbody.innerHTML = list.map(b => {
    const isSearching = !b.spz || b.spz === 'Aktivní hledání' || b.spz.toUpperCase().includes('NEZNÁMÁ');
    const isDuplicate = (_dashData.duplicate_buses || []).some(d => String(d.bus_id) === String(b.bus_id)) || (b.reason && b.reason.includes('Duplicitní'));
    const isWatched = Boolean(b.is_watched);
    const isIgnored = Boolean(b.is_ignored);
    const cannotDetermine = Boolean(b.cannot_determine_reason) || (isSearching && !b.candidate_spz);
    const badgeColor = isIgnored ? '#94a3b8' : (b.admin_verified ? '#10b981' : (b.spz_verified ? '#3b82f6' : (isSearching ? '#38bdf8' : (isDuplicate ? '#f97316' : '#fbbf24'))));
    const statusLabel = isIgnored ? 'Ponecháno (Skryto)' : (b.admin_verified ? 'Admin ověřeno' : (b.spz_verified ? '3F Ověřeno' : (isSearching ? 'Aktivní hledání' : (isDuplicate ? 'Duplicita' : 'Neověřeno'))));
    const trackUrl = b.map_url || `https://datacorebot.koyeb.app/mapa?track=${b.bus_id}`;

    let candChip = '';
    if (b.candidate_spz) {
      const candDetailInfo = b.candidate_detail ? `Ověřeno: ${b.candidate_detail}` : 'Shoda linky, destinace i směru';
      candChip = `<div style="margin-top: 6px;"><button onclick="setQuickInp('${b.bus_id}', '${b.candidate_spz}')" style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #86efac; font-size: 11px; padding: 4px 8px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; font-weight: bold;" title="${candDetailInfo}. Klikněte pro vložení nalezené SPZ"><i class="fas fa-magic"></i> Arriva kandidát (${b.candidate_line || b.line}): <b>${b.candidate_spz}</b> (${b.candidate_dist}m)</button></div>`;
    }

    let watchedBadge = '';
    if (isWatched) {
      watchedBadge = `<div style="display: inline-block; background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; margin-top: 4px;"><i class="fas fa-eye"></i> Systém aktivně hlídá</div>`;
    }

    let ignoredBadge = '';
    if (isIgnored) {
      ignoredBadge = `<div style="display: inline-block; background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #64748b; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; margin-top: 4px;"><i class="fas fa-eye-slash"></i> Ponecháno (Nechat být)</div>`;
    }

    let reasonContent = `<div style="color: #f1f5f9; font-size: 12px; line-height: 1.4;">${b.reason || 'Důvod nezaznamenán'}</div>`;
    if (cannotDetermine && !isDuplicate) {
      reasonContent = `<div style="color: #fb923c; font-size: 12px; line-height: 1.4; font-weight: 500;"><i class="fas fa-info-circle"></i> Nelze určit SPZ z důvodu, že vůz právě nejede a není na mapě Arriva.</div>`;
    } else if (isDuplicate) {
      reasonContent = `<div style="display: inline-block; background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #f97316; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; margin-bottom: 4px; text-transform: uppercase;"><i class="fas fa-clone"></i> Konflikt duplicity</div>` + reasonContent;
      if (cannotDetermine) {
        reasonContent += `<div style="color: #fb923c; font-size: 11px; margin-top: 4px;"><i class="fas fa-info-circle"></i> Nelze určit SPZ z důvodu, že vůz právě nejede a není na mapě Arriva.</div>`;
      }
    }

    let cannotHint = '';
    if (cannotDetermine) {
      cannotHint = `<div style="font-size: 11px; color: #94a3b8; margin-top: 4px; line-height: 1.3;"><i class="fas fa-info-circle" style="color: #fb923c;"></i> Vůz právě nejede na mapě. Klikněte níže na <b>Resetovat SPZ & Aktivně hledat</b> nebo <b>Nechat být</b>.</div>`;
    }

    return `
      <tr style="border-bottom: 1px solid #334155; transition: 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.03)'" onmouseout="this.style.background='transparent'">
        <td data-label="Vůz ID / Linka" style="padding: 12px;">
          <div style="font-weight: bold;"><a href="${trackUrl}" target="_blank" class="bus-link"><i class="fas fa-bus"></i> Vůz #${b.bus_id}</a></div>
          <div style="color: #38bdf8; font-size: 12px; margin-top: 2px;"><i class="fas fa-route"></i> Linka <b>${b.line}</b> (${b.destination || 'Neznámý cíl'})</div>
        </td>
        <td data-label="Model / Spoj" style="padding: 12px;">
          <div style="color: #e2e8f0; font-weight: 500;">${b.vehicle_type || 'Neznámý model'}</div>
          <div style="color: #94a3b8; font-size: 11px;">${b.real_linka_spoj || 'Bez spojení'} • Zpoždění: <span style="color:#f87171;">${b.delay_text}</span></div>
        </td>
        <td data-label="Aktuální SPZ" style="padding: 12px;">
          <span style="display: inline-block; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-family: monospace; font-size: 13px; background: rgba(0,0,0,0.4); border: 1px solid ${badgeColor}; color: ${badgeColor};">
            ${isSearching ? '<i class="fas fa-satellite-dish fa-spin" style="font-size:10px;margin-right:4px;"></i>Aktivní hledání' : b.spz}
          </span>
          <div style="font-size: 10px; color: ${badgeColor}; margin-top: 3px;"><i class="fas fa-shield-alt"></i> ${statusLabel}</div>
          ${watchedBadge}
          ${ignoredBadge}
          ${candChip}
        </td>
        <td data-label="Důvod chyby" style="padding: 12px; max-width: 320px;">
          ${reasonContent}
        </td>
        <td data-label="Rychlá úprava SPZ" style="padding: 12px;">
          <div class="mobile-edit-box" style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
            <input type="text" id="spz-inp-${b.bus_id}" value="${isSearching ? '' : b.spz}" placeholder="Nová SPZ..." style="width: 110px; background: #0f172a; border: 1px solid #475569; color: white; padding: 6px 8px; border-radius: 4px; font-size: 12px; font-family: monospace;">
            <label style="font-size: 11px; color: #94a3b8; display: flex; align-items: center; gap: 4px; cursor: pointer;">
              <input type="checkbox" id="spz-ver-${b.bus_id}" ${b.admin_verified ? 'checked' : ''} style="cursor: pointer;"> Ověřit
            </label>
            <button onclick="saveQuickSpz('${b.bus_id}')" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
              <i class="fas fa-save"></i> Uložit
            </button>
          </div>
          ${cannotHint}
          <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px;">
            <button onclick="resetAndWatchSpz('${b.bus_id}')" style="background: rgba(56, 189, 248, 0.15); border: 1px solid #0284c7; color: #38bdf8; font-size: 11px; padding: 6px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-weight: bold; width: fit-content; transition: all 0.2s;" title="Resetuje SPZ na 'Aktivní hledání', zruší zámek a zařadí vůz do automatického hlídání. Jakmile vyjede a bude na mapě Arriva, systém mu sám přiřadí správnou SPZ (se shodou linky, destinace i směru).">
              <i class="fas fa-sync-alt"></i> Resetovat SPZ & aktivně hledat (až bude dostupný)
            </button>
            ${isIgnored ? `
              <button onclick="toggleIgnoreBus('${b.bus_id}', false)" style="background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24; font-size: 11px; padding: 5px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-weight: bold; width: fit-content;" title="Vrátit vůz zpět do aktivního přehledu chyb">
                <i class="fas fa-undo"></i> Vrátit k řešení chyb
              </button>
            ` : `
              <button onclick="toggleIgnoreBus('${b.bus_id}', true)" style="background: rgba(148, 163, 184, 0.12); border: 1px solid #64748b; color: #cbd5e1; font-size: 11px; padding: 5px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-weight: bold; width: fit-content;" title="Označit chybu jako 'Nechat být' a skrýt ji z aktivních chyb pro zpřehlednění seznamu">
                <i class="fas fa-eye-slash"></i> Nechat být
              </button>
            `}
            ${isWatched ? `
              <div style="font-size: 11px; color: #38bdf8; display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                <i class="fas fa-check-circle"></i> Vůz je aktivně hlídán 
                <button onclick="toggleWatchBus('${b.bus_id}', false)" style="background: none; border: none; color: #94a3b8; font-size: 10px; cursor: pointer; text-decoration: underline; padding: 0;">(zrušit hlídání)</button>
              </div>
            ` : ''}
          </div>
        </td>
        <td data-label="Akce" style="padding: 12px; text-align: center;">
          <a href="${trackUrl}" target="_blank" style="display: inline-block; background: #334155; color: #38bdf8; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;" title="Zobrazit vůz na živé mapě">
            <i class="fas fa-map-marker-alt"></i> Mapa
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

async function resetAndWatchSpz(busId) {
  if (!confirm(`Resetovat vůz #${busId} na "Aktivní hledání" a aktivně hlídat až bude bus dostupný?\n\nSystém vymaže předchozí chybnou SPZ a jakmile se objeví na Arriva mapě (se shodou linky, destinace i směru), automaticky mu sám přiřadí správnou SPZ.`)) {
    return;
  }
  try {
    const res = await fetch('/api/admin/spz_reset_and_watch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bus_id: busId })
    });
    const d = await res.json();
    if (!res.ok || d.status !== 'success') {
      showToast(d.message || 'Chyba při resetování SPZ', true);
    } else {
      showToast(d.message || 'SPZ byla resetována a zařazena do hlídání');
      loadSpzControlData();
    }
  } catch (err) {
    showToast('Chyba komunikace: ' + err.message, true);
  }
}

async function toggleIgnoreBus(busId, doIgnore) {
  try {
    const res = await fetch('/api/admin/spz_ignore_bus', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bus_id: busId, action: doIgnore ? 'ignore' : 'unignore' })
    });
    const d = await res.json();
    if (!res.ok || d.status !== 'success') {
      showToast(d.message || 'Chyba při změně stavu vozu', true);
    } else {
      showToast(d.message || (doIgnore ? 'Vůz byl skryt (Nechat být)' : 'Vůz byl vrácen do řešení chyb'));
      loadSpzControlData();
    }
  } catch (err) {
    showToast('Chyba: ' + err.message, true);
  }
}

async function toggleWatchBus(busId, doWatch) {
  try {
    const res = await fetch('/api/admin/spz_watch_bus', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bus_id: busId, action: doWatch ? 'watch' : 'unwatch' })
    });
    const d = await res.json();
    if (!res.ok || d.status !== 'success') {
      showToast(d.message || 'Chyba při změně hlídání vozu', true);
    } else {
      showToast(d.message || (doWatch ? 'Vůz byl zařazen do hlídání' : 'Vůz byl odebrán ze sledování'));
      loadSpzControlData();
    }
  } catch (err) {
    showToast('Chyba: ' + err.message, true);
  }
}

async function saveQuickSpz(busId) {
  const inp = document.getElementById('spz-inp-' + busId);
  const chk = document.getElementById('spz-ver-' + busId);
  const newSpz = inp ? inp.value.trim() : '';
  const isVerified = chk ? chk.checked : false;

  try {
    const res = await fetch('/api/admin/spz_quick_edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bus_id: busId, new_spz: newSpz, is_verified: isVerified })
    });
    const d = await res.json();
    if (!res.ok || d.status !== 'success') {
      showToast(d.message || 'Chyba při ukládání SPZ!', true);
    } else {
      showToast(d.message || 'SPZ byla úspěšně změněna!');
      loadSpzControlData();
    }
  } catch (e) {
    showToast('Chyba: ' + e.message, true);
  }
}

function renderProposals() {
  if (!_dashData) return;
  const container = document.getElementById('proposals-container');
  const filtersBar = document.getElementById('proposal-filters-bar');
  const allProposals = _dashData.proposals || [];

  const pendingCount = allProposals.filter(p => p.status === 'pending').length;
  const autoCount = allProposals.filter(p => p.status === 'auto_resolved').length;
  const historyCount = allProposals.filter(p => p.status === 'accepted' || p.status === 'rejected' || p.status === 'resolved').length;

  if (filtersBar) {
    filtersBar.innerHTML = `
      <button onclick="setProposalFilter('all')" style="background: ${_currentProposalFilter === 'all' ? '#334155' : '#0f172a'}; color: white; border: 1px solid #475569; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: ${_currentProposalFilter === 'all' ? 'bold' : 'normal'}; display: flex; align-items: center; gap: 6px;">
        Všechny návrhy <span style="background: #475569; padding: 1px 6px; border-radius: 10px; font-size: 10px;">${allProposals.length}</span>
      </button>
      <button onclick="setProposalFilter('pending')" style="background: ${_currentProposalFilter === 'pending' ? '#4c1d95' : '#0f172a'}; color: #c084fc; border: 1px solid #a855f7; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: ${_currentProposalFilter === 'pending' ? 'bold' : 'normal'}; display: flex; align-items: center; gap: 6px;">
        <i class="fas fa-clock"></i> Čeká na schválení <span style="background: ${pendingCount > 0 ? '#ef4444' : '#6b21a8'}; color: white; padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: bold;">${pendingCount}</span>
      </button>
      <button onclick="setProposalFilter('auto')" style="background: ${_currentProposalFilter === 'auto' ? '#064e3b' : '#0f172a'}; color: #6ee7b7; border: 1px solid #10b981; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: ${_currentProposalFilter === 'auto' ? 'bold' : 'normal'}; display: flex; align-items: center; gap: 6px;">
        <i class="fas fa-robot"></i> Vyřešeno automodem <span style="background: #047857; color: white; padding: 1px 6px; border-radius: 10px; font-size: 10px;">${autoCount}</span>
      </button>
      <button onclick="setProposalFilter('history')" style="background: ${_currentProposalFilter === 'history' ? '#1e293b' : '#0f172a'}; color: #94a3b8; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: ${_currentProposalFilter === 'history' ? 'bold' : 'normal'}; display: flex; align-items: center; gap: 6px;">
        <i class="fas fa-history"></i> Manuálně vyřešeno <span style="background: #334155; color: white; padding: 1px 6px; border-radius: 10px; font-size: 10px;">${historyCount}</span>
      </button>
    `;
  }

  let list = allProposals;
  if (_currentProposalFilter === 'pending') {
    list = allProposals.filter(p => p.status === 'pending');
  } else if (_currentProposalFilter === 'auto') {
    list = allProposals.filter(p => p.status === 'auto_resolved');
  } else if (_currentProposalFilter === 'history') {
    list = allProposals.filter(p => p.status === 'accepted' || p.status === 'rejected' || p.status === 'resolved');
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px; background: rgba(0,0,0,0.2); border-radius: 8px;">
        <i class="fas fa-check-circle" style="color: #10b981; font-size: 32px; margin-bottom: 10px;"></i>
        <div style="color: white; font-weight: bold; font-size: 16px;">V této kategorii nejsou žádné záznamy</div>
        <div style="color: #94a3b8; font-size: 12px; margin-top: 5px;">Všechny SPZ v pořádku nebo vyřešeny automatikou.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(p => {
    const isPending = p.status === 'pending';
    const isAuto = p.status === 'auto_resolved';
    const busUrl = p.map_url_bus || `https://datacorebot.koyeb.app/mapa?track=${p.bus_id}`;
    const conflictUrl = p.map_url_conflict || (p.conflict_with_id ? `https://datacorebot.koyeb.app/mapa?track=${p.conflict_with_id}` : null);

    // Karta pro 2x Admin duplikát (Vyžaduje manuální schválení)
    if (p.type === 'admin_duplicate_conflict') {
      const statusBadge = isPending 
        ? '<span style="background: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid #ef4444; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800;"><i class="fas fa-exclamation-triangle"></i> 2x Admin SPZ – Vyžaduje schválení dispečera!</span>'
        : '<span style="background: rgba(16, 185, 129, 0.2); color: #86efac; border: 1px solid #10b981; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Vyřešeno adminem</span>';

      return `
        <div style="background: #1e1b2e; border: 2px solid #ef4444; border-radius: 12px; padding: 18px; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; border-bottom: 1px solid rgba(239,68,68,0.25); padding-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <span style="font-size: 15px; font-weight: 800; color: #f87171;"><i class="fas fa-shield-alt"></i> DUPLIKÁT 2x ADMIN-OVĚŘENÉ SPZ: <span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-family: monospace;">${p.spz}</span></span>
              ${statusBadge}
            </div>
            <span style="color: #64748b; font-size: 11px;"><i class="far fa-clock"></i> ${p.created_at || ''}</span>
          </div>

          <div style="color: #fca5a5; font-size: 13px; line-height: 1.5; margin-bottom: 14px; background: rgba(239,68,68,0.1); padding: 12px; border-radius: 8px; border: 1px dashed rgba(239,68,68,0.4);">
            <i class="fas fa-exclamation-circle" style="color: #ef4444;"></i> ${p.reason}
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 14px;">
            <div style="background: #0f172a; border: 1px solid #38bdf8; border-radius: 8px; padding: 12px;">
              <div style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: bold; margin-bottom: 4px;"><i class="fas fa-bus"></i> Vozidlo A</div>
              <div style="font-size: 15px; font-weight: bold; color: white;">Vůz #${p.bus_id} (Linka ${p.line})</div>
              <div style="margin-top: 8px;">
                <a href="${busUrl}" target="_blank" style="background: #1e293b; border: 1px solid #38bdf8; color: #38bdf8; padding: 5px 10px; border-radius: 6px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; font-weight: bold;">
                  <i class="fas fa-map-marker-alt"></i> Zobrazit #${p.bus_id} na mapě
                </a>
              </div>
            </div>

            <div style="background: #0f172a; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px;">
              <div style="font-size: 11px; text-transform: uppercase; color: #fbbf24; font-weight: bold; margin-bottom: 4px;"><i class="fas fa-bus"></i> Vozidlo B</div>
              <div style="font-size: 15px; font-weight: bold; color: white;">Vůz #${p.conflict_with_id} (Linka ${p.conflict_with_line})</div>
              <div style="margin-top: 8px;">
                ${conflictUrl ? `
                <a href="${conflictUrl}" target="_blank" style="background: #1e293b; border: 1px solid #f59e0b; color: #fbbf24; padding: 5px 10px; border-radius: 6px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; font-weight: bold;">
                  <i class="fas fa-map-marker-alt"></i> Zobrazit #${p.conflict_with_id} na mapě
                </a>` : ''}
              </div>
            </div>
          </div>

          ${isPending ? `
          <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08);">
            <button onclick="resolveProposal('${p.id}', 'keep_bus')" style="background: linear-gradient(135deg, #0284c7, #38bdf8); color: #0f172a; border: none; padding: 9px 15px; border-radius: 8px; font-weight: 800; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 10px rgba(56, 189, 248, 0.3);">
              <i class="fas fa-check"></i> Ponechat SPZ pro #${p.bus_id}
            </button>
            <button onclick="resolveProposal('${p.id}', 'keep_conflict')" style="background: linear-gradient(135deg, #d97706, #f59e0b); color: #0f172a; border: none; padding: 9px 15px; border-radius: 8px; font-weight: 800; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3);">
              <i class="fas fa-check"></i> Ponechat SPZ pro #${p.conflict_with_id}
            </button>
            <button onclick="resolveProposal('${p.id}', 'release_both')" style="background: #334155; color: #cbd5e1; border: 1px solid #475569; padding: 8px 12px; border-radius: 8px; font-weight: bold; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
              <i class="fas fa-undo"></i> Uvolnit obě vozidla
            </button>
          </div>
          ` : `
          <div style="color: #94a3b8; font-size: 12px; font-style: italic; padding-top: 8px;">
            ${p.resolution_note || ('Vyřešeno uživatelem ' + (p.resolved_by || 'Admin'))}
          </div>
          `}
        </div>
      `;
    }

    // Karta vyřešená automodem (Přehledná a jasná se dvěma sloupci)
    if (isAuto) {
      return `
        <div style="background: #0f172a; border: 1px solid #10b981; border-radius: 12px; padding: 18px; box-shadow: 0 4px 16px rgba(16, 185, 129, 0.08);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <span style="background: rgba(16, 185, 129, 0.2); color: #86efac; border: 1px solid #10b981; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800; text-transform: uppercase;">
                <i class="fas fa-robot"></i> Vyřešeno automodem
              </span>
              <span style="font-weight: bold; color: white; font-size: 14px;">
                Duplicita SPZ: <span style="font-family: monospace; color: #38bdf8; background: #1e293b; padding: 2px 7px; border-radius: 4px; border: 1px solid #334155;">${p.spz}</span>
              </span>
            </div>
            <div style="color: #64748b; font-size: 11px;">
              <i class="far fa-clock"></i> ${p.created_at || ''}
            </div>
          </div>

          <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 13px; color: #e2e8f0; margin-bottom: 14px; line-height: 1.5;">
            <i class="fas fa-check-circle" style="color: #10b981; margin-right: 6px;"></i>
            ${p.resolution_note || p.reason}
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">
            <!-- Box 1: Oprávněný vlastník -->
            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: bold;">
                  <i class="fas fa-shield-alt"></i> Původní / Oprávněný vůz
                </span>
                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">
                  SPZ ponechána
                </span>
              </div>
              <div style="font-size: 15px; font-weight: bold; color: white; margin-bottom: 4px;">
                Vůz #${p.conflict_with_id || '?'} (Linka ${p.conflict_with_line || '?'})
              </div>
              <div style="font-size: 12px; color: #94a3b8; margin-bottom: 10px;">
                Zachována SPZ: <b style="color: #38bdf8; font-family: monospace;">${p.spz}</b>
              </div>
              ${p.map_url_conflict ? `
              <a href="${p.map_url_conflict}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background: #0f172a; border: 1px solid #38bdf8; color: #38bdf8; font-size: 12px; padding: 5px 10px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                <i class="fas fa-map-marker-alt"></i> Zobrazit #${p.conflict_with_id} na mapě
              </a>` : ''}
            </div>

            <!-- Box 2: Duplicitní vůz -->
            <div style="background: #1e293b; border: 1px solid ${p.has_candidate ? '#10b981' : '#f97316'}; border-radius: 8px; padding: 14px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 11px; text-transform: uppercase; color: ${p.has_candidate ? '#34d399' : '#fb923c'}; font-weight: bold;">
                  <i class="fas fa-sync-alt"></i> Detekovaný duplikát
                </span>
                <span style="background: ${p.has_candidate ? 'rgba(16, 185, 129, 0.2)' : 'rgba(249, 115, 22, 0.2)'}; color: ${p.has_candidate ? '#86efac' : '#fb923c'}; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">
                  ${p.has_candidate ? 'Nalezena Arriva na lince' : 'Uvolněno na hledání'}
                </span>
              </div>
              <div style="font-size: 15px; font-weight: bold; color: white; margin-bottom: 4px;">
                Vůz #${p.bus_id} (Linka ${p.line || '?'})
              </div>
              <div style="font-size: 12px; color: #94a3b8; margin-bottom: 10px;">
                Nová SPZ: <b style="color: ${p.has_candidate ? '#86efac' : '#fca5a5'}; font-family: monospace;">${p.proposed_spz}</b>
                ${p.candidate_dist ? ` <span style="font-size: 11px; color: #64748b;">(${p.candidate_dist}m)</span>` : ''}
              </div>
              <a href="${busUrl}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background: #0f172a; border: 1px solid ${p.has_candidate ? '#10b981' : '#f97316'}; color: ${p.has_candidate ? '#34d399' : '#fb923c'}; font-size: 12px; padding: 5px 10px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                <i class="fas fa-map-marker-alt"></i> Zobrazit #${p.bus_id} na mapě
              </a>
            </div>
          </div>
        </div>
      `;
    }

    // Standardní návrh
    const statusBadge = isPending 
      ? '<span style="background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #a855f7; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Čeká na schválení adminem</span>'
      : (p.status === 'accepted' ? '<span style="background: rgba(16, 185, 129, 0.2); color: #86efac; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Schváleno adminem</span>'
      : '<span style="background: rgba(100, 116, 139, 0.2); color: #94a3b8; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Odmítnuto (Ponecháno)</span>');

    return `
      <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; display: flex; justify-content: space-between; align-items: stretch; flex-wrap: wrap; gap: 20px;">
        <div style="flex: 1; min-width: 300px;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap;">
            <a href="${busUrl}" target="_blank" class="bus-link" style="font-size: 16px;"><i class="fas fa-bus"></i> Vůz #${p.bus_id} (Linka ${p.line || '?'})</a>
            ${statusBadge}
            <span style="color: #64748b; font-size: 11px;">${p.created_at || ''}</span>
          </div>

          <div style="color: #f1f5f9; font-size: 13px; line-height: 1.5; margin-bottom: 12px;">
            <i class="fas fa-info-circle" style="color: #38bdf8;"></i> ${p.reason}
          </div>

          <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
            <a href="${busUrl}" target="_blank" style="background: #1e293b; border: 1px solid #0284c7; color: #38bdf8; padding: 5px 10px; border-radius: 6px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 5px;">
              <i class="fas fa-map-marker-alt"></i> Zobrazit vůz #${p.bus_id} na mapě
            </a>
            ${conflictUrl ? `
            <a href="${conflictUrl}" target="_blank" style="background: #1e293b; border: 1px solid #f97316; color: #fb923c; padding: 5px 10px; border-radius: 6px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 5px;">
              <i class="fas fa-user-shield"></i> Reálný vlastník: vůz #${p.conflict_with_id} (L${p.conflict_with_line}) na mapě
            </a>` : ''}
          </div>

          <div style="display: flex; gap: 15px; font-size: 12px; flex-wrap: wrap;">
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); padding: 5px 10px; border-radius: 6px; color: #fca5a5;">
              Chybná SPZ: <b>${p.current_spz || 'Neznámá'}</b>
            </div>
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); padding: 5px 10px; border-radius: 6px; color: #86efac;">
              Doporučené řešení: <b>${p.proposed_spz}</b>
            </div>
          </div>
        </div>

        ${isPending ? `
        <div style="display: flex; flex-direction: column; justify-content: center; gap: 10px; min-width: 220px;">
          <button onclick="resolveProposal('${p.id}', 'accept')" style="background: linear-gradient(135deg, #059669, #10b981); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-weight: bold; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);">
            <i class="fas fa-check"></i> ${p.has_candidate ? `Přiřadit SPZ ${p.proposed_spz}` : 'Potvrdit (Aktivní hledání)'}
          </button>
          <button onclick="resolveProposal('${p.id}', 'reject')" style="background: #334155; color: #cbd5e1; border: 1px solid #475569; padding: 10px 16px; border-radius: 8px; font-weight: bold; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <i class="fas fa-times"></i> Zachovat tak jak je
          </button>
        </div>
        ` : `
        <div style="display: flex; align-items: center; color: #94a3b8; font-size: 12px; font-style: italic;">
          ${p.resolution_note || ('Rozhodnuto uživatelem ' + (p.resolved_by || 'Admin'))}
        </div>
        `}
      </div>
    `;
  }).join('');
}

async function resolveProposal(proposalId, action) {
  try {
    const res = await fetch('/api/admin/spz_resolve_proposal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposal_id: proposalId, action: action })
    });
    const d = await res.json();
    if (!res.ok || d.status !== 'success') {
      showToast(d.message || 'Chyba při zpracování návrhu!', true);
    } else {
      showToast(d.message);
      loadSpzControlData();
    }
  } catch (e) {
    showToast('Chyba: ' + e.message, true);
  }
}

function renderAutomationLog() {
  if (!_dashData) return;
  const tbody = document.getElementById('automation-table-body');
  const q = (document.getElementById('automation-search')?.value || '').toLowerCase().trim();
  let list = _dashData.automation_log || [];

  if (q) {
    list = list.filter(item => 
      String(item.bus_id || '').toLowerCase().includes(q) ||
      String(item.spz || '').toLowerCase().includes(q) ||
      String(item.line || '').toLowerCase().includes(q) ||
      String(item.title || '').toLowerCase().includes(q) ||
      String(item.detail || '').toLowerCase().includes(q)
    );
  }

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: #64748b;">Žádný záznam v logu automatiky.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(item => {
    let actionBadge = '<span style="background:#334155;color:#f1f5f9;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;">Událost</span>';
    if (item.action_type === 'duplicate_resolved') {
      actionBadge = '<span style="background:rgba(249,115,22,0.2);color:#fb923c;border:1px solid #f97316;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-clone"></i> Duplicita</span>';
    } else if (item.action_type === 'proposal_resolved') {
      actionBadge = '<span style="background:rgba(16,185,129,0.2);color:#86efac;border:1px solid #10b981;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-check"></i> Vyřešeno</span>';
    } else if (item.action_type === 'admin_edit') {
      actionBadge = '<span style="background:rgba(168,85,247,0.2);color:#c084fc;border:1px solid #a855f7;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-user-shield"></i> Admin úprava</span>';
    } else if (item.action_type === 'spz_verified' || item.action_type === 'spz_match') {
      actionBadge = '<span style="background:rgba(2,132,199,0.2);color:#38bdf8;border:1px solid #0284c7;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-satellite-dish"></i> SPZ ověřena</span>';
    } else if (item.action_type === 'depot_in') {
      actionBadge = '<span style="background:rgba(234,179,8,0.2);color:#fde047;border:1px solid #eab308;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-warehouse"></i> Vjezd do depa</span>';
    } else if (item.action_type === 'depot_out') {
      actionBadge = '<span style="background:rgba(16,185,129,0.2);color:#86efac;border:1px solid #10b981;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-road"></i> Výjezd z depa</span>';
    } else if (item.action_type === 'notification_fired') {
      actionBadge = '<span style="background:rgba(168,85,247,0.25);color:#d8b4fe;border:1px solid #c084fc;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-bell"></i> Notifikace</span>';
    } else if (item.action_type === 'watched_bus_resolved') {
      actionBadge = '<span style="background:rgba(16,185,129,0.25);color:#6ee7b7;border:1px solid #10b981;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-eye"></i> Hlídaný vůz</span>';
    } else if (item.action_type === 'spz_watch') {
      actionBadge = '<span style="background:rgba(56,189,248,0.2);color:#7dd3fc;border:1px solid #38bdf8;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-binoculars"></i> Sledování</span>';
    } else if (item.action_type === 'spz_unwatch') {
      actionBadge = '<span style="background:rgba(148,163,184,0.2);color:#cbd5e1;border:1px solid #64748b;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-eye-slash"></i> Nesledovat</span>';
    } else if (item.action_type === 'spz_change' || item.action_type === 'spz_assigned') {
      actionBadge = '<span style="background:rgba(14,165,233,0.2);color:#38bdf8;border:1px solid #0ea5e9;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-exchange-alt"></i> SPZ změněna</span>';
    } else if (item.action_type === 'system_init') {
      actionBadge = '<span style="background:rgba(99,102,241,0.2);color:#a5b4fc;border:1px solid #6366f1;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:bold;"><i class="fas fa-info-circle"></i> Systém</span>';
    }

    const trackUrl = item.map_url || (item.bus_id ? `https://datacorebot.koyeb.app/mapa?track=${item.bus_id}` : 'https://datacorebot.koyeb.app/mapa');

    return `
      <tr style="border-bottom: 1px solid #334155; transition: 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.03)'" onmouseout="this.style.background='transparent'">
        <td data-label="Čas" style="padding: 12px; color: #94a3b8; font-family: monospace; font-size: 12px; white-space: nowrap;">
          ${item.time} <span style="font-size:10px;color:#64748b;">${item.date || ''}</span>
        </td>
        <td data-label="Typ akce" style="padding: 12px;">
          ${actionBadge}
        </td>
        <td data-label="Vůz / Linka / SPZ" style="padding: 12px;">
          ${item.bus_id ? `<a href="${trackUrl}" target="_blank" class="bus-link"><i class="fas fa-bus"></i> Vůz #${item.bus_id}</a>` : '—'}
          <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">
            ${item.line ? `Linka <b>${item.line}</b> • ` : ''}${item.spz ? `SPZ: <span style="font-family:monospace;color:#38bdf8;">${item.spz}</span>` : ''}
          </div>
        </td>
        <td data-label="Popis události" style="padding: 12px;">
          <div style="color: white; font-weight: 500;">${item.title}</div>
          ${item.detail ? `<div style="color: #94a3b8; font-size: 12px; margin-top: 2px;">${item.detail}</div>` : ''}
        </td>
        <td data-label="Mapa" style="padding: 12px; text-align: center;">
          ${item.bus_id ? `
          <a href="${trackUrl}" target="_blank" style="display: inline-block; background: #334155; color: #38bdf8; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;" title="Zobrazit na mapě">
            <i class="fas fa-eye"></i> Mapa
          </a>` : '—'}
        </td>
      </tr>
    `;
  }).join('');
}

async function toggleAutoResolve() {
  try {
    const res = await fetch('/api/admin/toggle_auto_resolve', { method: 'POST' });
    const d = await res.json();
    if (res.ok && d.status === 'success') {
      showToast(d.message);
      loadSpzControlData();
    }
  } catch (e) {
    showToast('Chyba: ' + e.message, true);
  }
}

async function triggerAnalysis() {
  const btn = document.getElementById('btn-trigger-analysis');
  if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzuji...';
  try {
    const res = await fetch('/api/admin/trigger_spz_analysis', { method: 'POST' });
    const d = await res.json();
    if (res.ok && d.status === 'success') {
      showToast(d.message);
      if (d.data) {
        _dashData = d.data;
        renderDashboardUI();
      } else {
        loadSpzControlData();
      }
    }
  } catch (e) {
    showToast('Chyba analýzy: ' + e.message, true);
  } finally {
    if (btn) btn.innerHTML = '<i class="fas fa-bolt"></i> Spustit rozluštění chyb';
  }
}

function renderDriversTable() {
  if (!_dashData) return;
  const tbody = document.getElementById('drivers-table-body');
  const q = (document.getElementById('driver-search').value || '').toLowerCase().trim();
  let list = _dashData.admin_drivers_and_notes || [];

  if (q) {
    list = list.filter(d => 
      String(d.driver_name || '').toLowerCase().includes(q) ||
      String(d.note || '').toLowerCase().includes(q) ||
      String(d.bus_id || '').toLowerCase().includes(q) ||
      String(d.spz || '').toLowerCase().includes(q) ||
      String(d.line || '').toLowerCase().includes(q)
    );
  }

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 30px; color: #64748b;">Nenalezen žádný zadaný řidič ani poznámka.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(d => {
    const isOnline = Boolean(d.is_online);
    const statusBadge = isOnline
      ? '<span style="color: #10b981; font-weight: bold;"><i class="fas fa-circle" style="font-size: 8px;"></i> Online</span>'
      : '<span style="color: #64748b;"><i class="fas fa-hdd" style="font-size: 10px;"></i> V paměti</span>';
    const trackUrl = d.map_url || `https://datacorebot.koyeb.app/mapa?track=${d.bus_id}`;

    return `
      <tr style="border-bottom: 1px solid #334155; transition: 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.03)'" onmouseout="this.style.background='transparent'">
        <td data-label="Vůz ID / SPZ" style="padding: 12px;">
          <div style="font-weight: bold;"><a href="${trackUrl}" target="_blank" class="bus-link">#${d.bus_id}</a></div>
          <div style="font-family: monospace; font-size: 11px; color: #38bdf8;">${d.spz}</div>
        </td>
        <td data-label="Jméno řidiče" style="padding: 12px; font-weight: bold; color: #f1f5f9; font-size: 14px;">
          <i class="fas fa-user-circle" style="color: #10b981;"></i> ${d.driver_name}
        </td>
        <td data-label="Poznámka vozu" style="padding: 12px; color: #cbd5e1; max-width: 280px;">
          ${d.note !== '—' ? `<span style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 4px 8px; border-radius: 4px; display: inline-block;">${d.note}</span>` : '<span style="color: #64748b;">Bez poznámky</span>'}
        </td>
        <td data-label="Linka & Model" style="padding: 12px;">
          <div style="color: white; font-weight: 500;">Linka ${d.line}</div>
          <div style="color: #94a3b8; font-size: 11px;">${d.vehicle_type}</div>
        </td>
        <td data-label="Stav" style="padding: 12px;">${statusBadge}</td>
        <td data-label="Datum / Čas" style="padding: 12px; color: #64748b; font-size: 12px; white-space: nowrap;">${d.updated_at}</td>
        <td data-label="Mapa" style="padding: 12px; text-align: center;">
          <a href="${trackUrl}" target="_blank" style="display: inline-block; background: #334155; color: #38bdf8; padding: 6px 10px; border-radius: 6px; text-decoration: none; font-size: 12px;" title="Zobrazit vůz na živé mapě">
            <i class="fas fa-eye"></i>
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

function renderInvalidLog() {
  if (!_dashData) return;
  const container = document.getElementById('invalid-log-container');
  const list = _dashData.invalid_verifications || [];

  if (list.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 30px; color: #10b981;"><i class="fas fa-check-double"></i> Vše v pořádku. Žádná neplatná ověření Neznámé SPZ nebyla detekována.</div>`;
    return;
  }

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 10px;">
      ${list.map(item => {
        const trackUrl = `https://datacorebot.koyeb.app/mapa?track=${item.bus_id}`;
        return `
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; border-radius: 6px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-weight: bold; color: #fca5a5; font-size: 13px;">
              <a href="${trackUrl}" target="_blank" class="bus-link" style="color: #fca5a5;"><i class="fas fa-exclamation-circle"></i> Vůz #${item.bus_id} (Linka ${item.line})</a>
            </div>
            <div style="color: #e2e8f0; font-size: 12px; margin-top: 3px;">
              ${item.reason}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="color: #94a3b8; font-size: 11px;">
              ${item.time}
            </div>
            <a href="${trackUrl}" target="_blank" style="background: #334155; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none;">
              <i class="fas fa-map-marker-alt"></i> Mapa
            </a>
          </div>
        </div>
      `;
      }).join('')}
    </div>
  `;
}

// Spustit načítání při startu a obnovovat každých 20 sekund
loadSpzControlData();
setInterval(() => {
  const searchSpz = document.getElementById('spz-search');
  const searchDrv = document.getElementById('driver-search');
  const searchAut = document.getElementById('automation-search');
  if (searchSpz && searchSpz === document.activeElement) return;
  if (searchDrv && searchDrv === document.activeElement) return;
  if (searchAut && searchAut === document.activeElement) return;
  loadSpzControlData();
}, 20000);
</script>
"""

