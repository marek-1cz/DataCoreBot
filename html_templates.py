BASE_HTML = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Projekt OIS IDPK</title>
<link rel="icon" type="image/png" href="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png">
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
</body>
</html>
"""

PUBLIC_LAYOUT = """
<nav class="top-nav">
<div class="nav-brand-mobile" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
<a href="/" class="logo"><img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png" alt="Logo" style="height: 30px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 8px rgba(56, 189, 248, 0.6));">OIS IDPK</a>
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
<div class="sidebar-header"><a href="/" class="logo" style="font-size: 20px; display: flex; justify-content: center; align-items: center; gap: 8px;"><img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png" alt="Logo" style="height: 24px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 6px rgba(56, 189, 248, 0.6));">OIS IDPK</a><div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div></div>
<div class="sidebar-menu">
<a href="/" class="sidebar-link" style="color: #10b981; border-bottom: 1px solid #334155; margin-bottom: 5px;"><i class="fas fa-globe"></i> Veřejný Web (Bypass)</a>
<a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
<a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-bar"></i> Statistiky Webu</a>
<a href="/dashboard/app_management" class="sidebar-link"><i class="fas fa-desktop"></i> Správa Aplikace</a>
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
            <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc1.png" alt="Screenshot 1" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc2.png" alt="Screenshot 2" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc3.png" alt="Screenshot 3" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc4.png" alt="Screenshot 4" style="width: 100%; max-width: 800px; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            <div class="screenshot-pair" style="display: flex; justify-content: center; gap: 20px; width: 100%; max-width: 800px;">
                <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc5.png" alt="Screenshot 5" style="width: 48%; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
                <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/sc/sc6.png" alt="Screenshot 6" style="width: 48%; border-radius: 8px; border: 1px solid #334155; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
            </div>
        </div>
    </div>
    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 60px 0;">
    <div class="footer-box" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; background: var(--bg-panel); padding: 40px; border-radius: 15px; border: 1px solid #334155;">
        <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png" alt="DataCoreBot Logo" style="max-width: 250px; height: auto; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5)); margin-bottom: 10px;">
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
            {% set img_url = 'https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/IMG_3650.jpg' %}
        {% endif %}
        <img src="{{ img_url }}" onerror="this.onerror=null; this.src='https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png';" alt="Avatar" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid var(--blue-main); margin-bottom: 15px; background-color: var(--bg-dark);">
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
/* Hero Section */
.supporters-hero { position: relative; text-align: center; padding: 60px 20px; margin-bottom: 50px; border-radius: 20px; background: radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.15), transparent 60%); }
.hero-glow-1 { position: absolute; top: -50px; left: 10%; width: 300px; height: 300px; background: rgba(245, 158, 11, 0.3); filter: blur(120px); z-index: -1; }
.hero-glow-2 { position: absolute; bottom: -50px; right: 10%; width: 300px; height: 300px; background: rgba(239, 68, 68, 0.3); filter: blur(120px); z-index: -1; }
.hero-title { position: relative; z-index: 1; color: var(--warning); font-size: 52px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 30px rgba(245, 158, 11, 0.8); margin-bottom: 20px; line-height: 1.1; }
.hero-desc { position: relative; z-index: 1; color: #cbd5e1; font-size: 20px; max-width: 800px; margin: 0 auto 40px auto; line-height: 1.6; }

/* Premium Button */
.btn-premium { position: relative; z-index: 1; display: inline-flex; align-items: center; gap: 15px; background: linear-gradient(135deg, #f59e0b, #ea580c); color: white; padding: 20px 60px; font-size: 26px; font-weight: 900; border-radius: 50px; text-decoration: none; text-transform: uppercase; border: 2px solid rgba(255,255,255,0.4); box-shadow: 0 10px 40px rgba(234, 88, 12, 0.5), inset 0 2px 10px rgba(255,255,255,0.4); overflow: hidden; transition: all 0.4s ease; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
.btn-premium:hover { transform: translateY(-5px) scale(1.05); box-shadow: 0 20px 50px rgba(234, 88, 12, 0.8), inset 0 2px 10px rgba(255,255,255,0.6); }
.btn-premium::after { content: ''; position: absolute; top: 0; left: -100%; width: 50%; height: 100%; background: linear-gradient(to right, transparent, rgba(255,255,255,0.4), transparent); transform: skewX(-25deg); animation: premiumShine 4s infinite; }
@keyframes premiumShine { 0% { left: -100%; } 20% { left: 200%; } 100% { left: 200%; } }

/* Grid Layout */
.supporters-grid { display: flex; flex-direction: column; align-items: center; gap: 30px; max-width: 800px; margin: 0 auto; padding: 0 20px 60px 20px; }

/* Glassmorphism Cards */
.supp-card { position: relative; border-radius: 20px; padding: 30px; width: 100%; display: flex; flex-direction: column; justify-content: space-between; align-items: center; text-align: center; overflow: hidden; backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); transition: all 0.4s ease; box-sizing: border-box; }
.supp-card:hover { transform: translateY(-10px); z-index: 10; }

/* Tiers */
.tier-3 { grid-column: 1 / -1; background: linear-gradient(135deg, rgba(127, 29, 29, 0.4), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(239, 68, 68, 0.3); box-shadow: 0 15px 35px rgba(220, 38, 38, 0.15), inset 0 0 40px rgba(220, 38, 38, 0.05); }
.tier-3:hover { box-shadow: 0 25px 50px rgba(220, 38, 38, 0.4), inset 0 0 60px rgba(220, 38, 38, 0.1); border-color: rgba(239, 68, 68, 0.8); }
.tier-3 .supp-badge { background: linear-gradient(135deg, #ef4444, #991b1b); color: white; border: 1px solid #fca5a5; text-shadow: 0 0 10px rgba(255,255,255,0.5); }
.tier-3 .supp-name { color: #fca5a5; font-size: 38px; text-shadow: 0 0 20px rgba(252, 165, 165, 0.6); margin-bottom: 15px; }

.tier-2 { background: linear-gradient(135deg, rgba(180, 83, 9, 0.4), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(245, 158, 11, 0.3); box-shadow: 0 10px 25px rgba(245, 158, 11, 0.1), inset 0 0 30px rgba(245, 158, 11, 0.05); }
.tier-2:hover { box-shadow: 0 20px 40px rgba(245, 158, 11, 0.3), inset 0 0 40px rgba(245, 158, 11, 0.1); border-color: rgba(245, 158, 11, 0.8); }
.tier-2 .supp-badge { background: linear-gradient(135deg, #f59e0b, #b45309); color: white; border: 1px solid #fde68a; }
.tier-2 .supp-name { color: #fde68a; font-size: 30px; text-shadow: 0 0 15px rgba(253, 230, 138, 0.4); margin-bottom: 15px; }

.tier-1 { background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 10px 25px rgba(56, 189, 248, 0.05); }
.tier-1:hover { box-shadow: 0 20px 40px rgba(56, 189, 248, 0.2); border-color: rgba(56, 189, 248, 0.6); }
.tier-1 .supp-badge { background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; border: 1px solid #bae6fd; }
.tier-1 .supp-name { color: #bae6fd; font-size: 26px; margin-bottom: 15px; }

/* Elements */
.supp-header { display: flex; flex-direction: column; justify-content: center; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 20px; width: 100%; }
.supp-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 30px; font-size: 13px; font-weight: 900; letter-spacing: 1px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
.supp-name { margin: 15px 0 15px 0; font-weight: 900; text-transform: uppercase; line-height: 1.1; }
.supp-amount { font-size: 28px; font-weight: 900; background: rgba(0,0,0,0.4); padding: 12px 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); color: #fcd34d; display: inline-block; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 15px rgba(252, 211, 77, 0.3); white-space: nowrap; animation: pulseAmount 2s infinite alternate; }
@keyframes pulseAmount { from { text-shadow: 0 0 5px rgba(252, 211, 77, 0.3); box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 10px rgba(252, 211, 77, 0.2); } to { text-shadow: 0 0 15px rgba(252, 211, 77, 0.8); box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), 0 0 25px rgba(252, 211, 77, 0.6); border-color: rgba(252, 211, 77, 0.4); } }
.supp-msg { position: relative; font-size: 16px; color: #cbd5e1; font-style: italic; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.05); line-height: 1.6; max-width: 600px; }
.supp-msg::before { content: '\\f10d'; font-family: 'Font Awesome 5 Free'; font-weight: 900; font-size: 20px; color: rgba(255,255,255,0.2); display: block; margin-bottom: 10px; }
.supp-footer { display: flex; justify-content: center; align-items: center; margin-top: auto; width: 100%; }
.supp-date { color: #64748b; font-size: 14px; font-weight: bold; display: flex; align-items: center; gap: 6px; }

.tier-3-glow { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 100%; height: 100%; background: radial-gradient(circle, rgba(239, 68, 68, 0.15) 0%, transparent 70%); pointer-events: none; }
@media (max-width: 768px) {
  .supporters-hero { padding: 30px 10px; margin-bottom: 30px; }
  .hero-title { font-size: 32px; }
  .hero-desc { font-size: 16px; margin-bottom: 20px; }
  .btn-premium { padding: 15px 25px; font-size: 16px; border-radius: 30px; }
  .supp-card { padding: 20px; }
  .tier-3 .supp-name { font-size: 28px; }
  .tier-2 .supp-name { font-size: 24px; }
  .tier-1 .supp-name { font-size: 20px; }
  .supp-amount { font-size: 22px; padding: 10px 15px; }
  .supp-msg { font-size: 14px; padding: 15px; }
  .supporters-grid { padding: 0 10px 30px 10px; }
}
</style>

<div class="supporters-hero">
    <div class="hero-glow-1"></div>
    <div class="hero-glow-2"></div>
    <h1 class="hero-title"><i class="fas fa-crown"></i> Podporovatelé Projektu</h1>
    <p class="hero-desc">Tenhle projekt tvořím ve svém volném čase a je kompletně zdarma pro všechny. Podpora je čistě dobrovolná a nesmírně mi pomáhá hradit náklady na servery a tvořit pro vás neustále nové skvělé aktualizace.</p>
    <a href="https://buymeacoffee.com/marekk_czz" target="_blank" class="btn-premium">
        <i class="fas fa-coffee" style="text-shadow: 0 0 10px rgba(255,255,255,0.5);"></i> Stát se VIP Podporovatelem
    </a>
</div>

<div class="supporters-grid">
    {% for s in supporters %}
        {% set tier_class = 'tier-3' if s.tier == 3 else ('tier-2' if s.tier == 2 else 'tier-1') %}
        {% set icon = 'fa-gem' if s.tier == 3 else ('fa-star' if s.tier == 2 else 'fa-medal') %}
        {% set badge_text = 'MEGA PODPOROVATEL' if s.tier == 3 else ('VELKÝ PODPOROVATEL' if s.tier == 2 else 'PODPOROVATEL') %}
        
        <div class="supp-card {{ tier_class }}">
            {% if s.tier == 3 %}<div class="tier-3-glow"></div>{% endif %}
            <div style="position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; width: 100%;">
                <div class="supp-header">
                    <div class="supp-badge"><i class="fas {{ icon }}"></i> {{ badge_text }}</div>
                    <h3 class="supp-name">{{ s.get('name', 'Anonym') }}</h3>
                    <div class="supp-amount">{{ s.get('amount', '') }}</div>
                </div>
                
                {% if s.get('message') %}
                <div class="supp-msg">
                    {{ s.get('message') }}
                </div>
                {% endif %}
                
                <div class="supp-footer">
                    <div class="supp-date"><i class="fas fa-clock"></i> Přidáno: {{ s.get('created_at', '') }}</div>
                </div>
            </div>
        </div>
    {% else %}
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px; background: var(--bg-panel); border-radius: 20px; border: 1px dashed #334155; color: #64748b; font-size: 20px;">
            <i class="fas fa-sad-tear" style="font-size: 50px; margin-bottom: 20px; opacity: 0.5;"></i><br>
            Zatím zde nejsou žádní podporovatelé. Buďte ten první, kdo vstoupí do Síně slávy!
        </div>
    {% endfor %}
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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-chart-line" style="color:var(--blue-main);"></i> Statistiky Webu</h2>
    <div style="color: var(--text-muted); font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-weight: bold;"><i class="fas fa-sync-alt" style="color: var(--blue-main);"></i> Automaticky aktualizováno</div>
</div>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); text-align: center;"><h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0; text-transform: uppercase;">Unikátní zobrazení (Celkem)</h3><div style="font-size: 40px; font-weight: 900; color: var(--text-main);">{{ total_visits }}</div></div>
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--success); text-align: center;"><h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0; text-transform: uppercase;">Zobrazení za 7 dní</h3><div style="font-size: 40px; font-weight: 900; color: var(--success);">{{ last_7_days }}</div></div>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px;"><h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-calendar-week"></i> Návštěvnost za posledních 7 dní</h3><div style="position: relative; height: 250px; width: 100%;"><canvas id="chart7d"></canvas></div></div>
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px;"><h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-clock"></i> Dnešní aktivita po hodinách</h3><div style="position: relative; height: 250px; width: 100%;"><canvas id="chart24h"></canvas></div></div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;"><i class="fas fa-globe"></i> Návštěvnost podle států</h3>
    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
        {% for cc, data in country_totals.items() %}<div style="background: rgba(0,0,0,0.3); border: 1px solid #334155; padding: 10px 20px; border-radius: 8px; display: flex; align-items: center; gap: 10px;"><img src="{{ data.flag }}" alt="" style="border-radius: 3px;"><span style="color: var(--text-main); font-weight: bold;">{{ data.name }}</span><span style="background: var(--blue-main); color: #000; padding: 2px 8px; border-radius: 12px; font-weight: 900; font-size: 12px;">{{ data.count }}</span></div>{% else %}<div style="color: var(--text-muted);">Zatím žádná data.</div>{% endfor %}
    </div>
</div>
<script>
    const labels7d = {{ labels_7d | safe }};
    const data7d = {{ data_7d | safe }};
    const labels24h = {{ labels_24h | safe }};
    const data24h = {{ data_24h | safe }};
    new Chart(document.getElementById('chart7d').getContext('2d'), { type: 'line', data: { labels: labels7d, datasets: [{ label: 'Počet návštěv', data: data7d, borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.2)', borderWidth: 3, tension: 0.3, fill: true }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } } } });
    new Chart(document.getElementById('chart24h').getContext('2d'), { type: 'bar', data: { labels: labels24h, datasets: [{ label: 'Dnešní návštěvy', data: data24h, backgroundColor: '#38bdf8', borderRadius: 4 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8', maxTicksLimit: 12 }, grid: { display: false } } } } });
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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-bell" style="color:#f59e0b;"></i> Systém Oznámení</h2>
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
<script>
function toggleTargetData(){const t=document.getElementById('target_type').value,c=document.getElementById('target_data_container'),i=document.getElementById('target_data');if(t==='GLOBAL'){c.style.display='none';i.removeAttribute('required');}else{c.style.display='block';i.setAttribute('required','true');}}
</script>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"><h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-code-branch" style="color:var(--blue-main);"></i> Manažer Verzí a Přístupů</h2></div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Vydat novou verzi</h3>
        <form action="/dashboard/add_version" method="POST">
            <input type="text" name="version_name" placeholder="Zobrazený Název (např. Jarní Update 1.5)" required>
            <input type="text" name="db_version" placeholder="Verze Databáze (Přesně z logic-ovladac.js!)" required>
            <input type="text" name="file_url" placeholder="Odkaz(y) na stažení (více odkazů oddělte čárkou)" required>
            <label style="color: var(--text-muted); font-size: 13px;">Pro jakou roli?</label>
            <select name="target_role" required><option value="User">User (Všichni)</option><option value="BT">BETA TESTER</option><option value="DEV_SA">DEV / SERVER ADMIN</option></select>
            <button type="submit" class="btn" style="width: 100%;">Přidat verzi</button>
        </form>
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">📦 Vydané verze softwaru</h3>
    <table><tr><th>Název</th><th>Verze pro DB</th><th>Stav</th><th>Cílová Skupina</th><th>Akce</th></tr>
    {% for v in versions %}{% set is_active = (v.get('is_active', True) | string | lower) != 'false' %}<tr style="opacity: {{ '1' if is_active else '0.5' }};"><td><strong>{{ v.get('version_name', '') }}</strong></td><td style="color: var(--warning); font-family: monospace;">{{ v.get('db_version', '') }}</td><td>{% if is_active %}<span class="role-tag" style="background-color: var(--success); color: white;">Aktivní</span>{% else %}<span class="role-tag" style="background-color: var(--danger); color: white;">Zablokováno</span>{% endif %}</td><td>{% if v.get('target_role') == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User</span>{% elif v.get('target_role') == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BT+</span>{% else %}<span class="role-tag" style="background-color: #ef4444; color: white;">DEV/SA</span>{% endif %}</td><td style="display:flex; gap:5px;"><form action="/dashboard/delete_version" method="POST" style="display:inline;"><input type="hidden" name="version_id" value="{{ v.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat?')"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Zatím nebyly přidány žádné verze.</td></tr>{% endfor %}</table>
</div>
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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">{{ title }}</h2>
    <div id="refresh-timer" style="color: var(--text-muted); font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-weight: bold;"><i class="fas fa-sync-alt" style="color: var(--blue-main);"></i> Aktualizace za: <span id="timer-sec" style="color: white;">60</span>s</div>
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
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); margin-bottom: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">Nové zprávy od uživatelů</h3>
    <table><tr><th>Uživatel</th><th>Zpráva</th><th>Datum</th><th>Akce</th></tr>
    {% for f in general_pending %}<tr><td style="color:white; font-weight:bold;">{{ f.get('nick', '') }}</td><td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td><td style="color:#aaa; font-size:12px;">{{ f.get('fcreated_at', '') }}</td><td style="display:flex; gap:5px;"><form action="/dashboard/feedback_resolve" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check-circle"></i> Vyřešeno</button></form><form action="/dashboard/feedback_delete" method="POST" style="margin:0;"><input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i></button></form></td></tr>{% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Žádná nová zpětná vazba.</td></tr>{% endfor %}</table>
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
    setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}').then(r => r.json()).then(d => {
            if (d.status === 'approved') window.location.href = '/dashboard/login_finalize?discord_id={{ discord_id }}';
            else if (d.status === 'rejected') { document.getElementById('status-text').innerText = "Přihlášení bylo zamítnuto!"; document.getElementById('status-text').style.color = "var(--danger)"; setTimeout(() => window.location.href = '/', 2000); }
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
  <a href="/" class="prov-back"><i class="fas fa-arrow-left"></i> Zpět na hlavní stránku</a>
</div>
"""

HTML_REGISTER = """
<style>
  .register-wrapper { background: url('https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/bg-map.jpg') no-repeat center center fixed; background-size: cover; display: flex; align-items: center; justify-content: center; min-height: calc(100vh - 60px); margin: -20px; padding: 20px; position: relative; }
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
  <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png" style="width:60px; height:60px; border-radius:12px; margin-bottom:15px; box-shadow: 0 0 15px rgba(56,189,248,0.5);">
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
        body: JSON.stringify({email: email})
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
        window.location.href = `/api/auth/finalize?token=${code}&type=email`;
    } else {
        alert("Kód musí mít 5 čísel.");
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
  .ucet-wrapper { background: url('https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/bg-map.jpg') no-repeat center center fixed; background-size: cover; display: flex; align-items: center; justify-content: center; min-height: calc(100vh - 60px); margin: -20px; padding: 20px; position: relative; }
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
      <h3>Moje upozornění na spoje</h3>
      __NOTIFICATIONS__
    </div>
  </div>
</div>

<script>
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


<script>
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
<link rel="icon" type="image/png" href="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png">
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
<link rel="icon" type="image/png" href="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png">
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
<link rel="icon" type="image/png" href="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png">
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
