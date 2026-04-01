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
        .modal { background: var(--bg-panel); padding: 30px; border-radius: 15px; width: 900px; max-width: 95%; border-top: 5px solid var(--blue-main); box-shadow: 0 15px 30px rgba(0,0,0,0.5); transform: translateY(20px); transition: 0.3s; max-height: 90vh; overflow-y: auto;}
        .modal.active { display: flex; }
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
        .alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .alert-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
        .checkbox-group { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }
        .checkbox-group label { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: bold; cursor: pointer; }
        .profile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
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
        <img src="{{ logo_male }}" alt="Logo" style="height: 30px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 8px rgba(56, 189, 248, 0.6));">
        OIS IDPK
    </a>
    <div class="nav-links">
        <a href="/">Domů</a>
        <a href="/download">Download</a>
        <a href="/team">Náš Tým</a>
        <a href="/stats">Statistiky</a>
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
                <img src="{{ logo_male }}" alt="Logo" style="height: 24px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 6px rgba(56, 189, 248, 0.6));">
                OIS IDPK
            </a>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div>
        </div>
        <div class="sidebar-menu">
            <a href="/dashboard" class="sidebar-link"><i class="fas fa-home"></i> Přehled</a>
            <a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-bar"></i> Statistiky Webu</a>
            <a href="/dashboard/app_management" class="sidebar-link"><i class="fas fa-desktop"></i> Správa Aplikace</a>
            <a href="/dashboard/notifications" class="sidebar-link" style="color: #f59e0b;"><i class="fas fa-bell"></i> Oznámení</a>
            <a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-code-branch"></i> Správa Verzí a Přístupů</a>
            <a href="/dashboard/pending_roles" class="sidebar-link" style="color: #10b981;"><i class="fas fa-ticket-alt"></i> Rezervace Rolí</a>
            <a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge"></i> Správa ID</a>
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Správa Týmu</a>
            
            <a href="/dashboard/supporters" class="sidebar-link" style="color: var(--blue-main); text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);"><i class="fas fa-star"></i> Podporovatelé</a>
            <a href="/dashboard/feedback" class="sidebar-link" style="color: #a855f7; text-shadow: 0 0 5px rgba(168, 85, 247, 0.5);"><i class="fas fa-comments"></i> Zpětná vazba</a>
            
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
    <div class="modal" id="modalContent" style="max-width: 1100px;">
        <div style="width: 100%;">
            <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-user"></i> Profil hráče <span id="modalAppId" style="color: var(--text-muted); font-size: 16px;"></span></span>
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
                    <div id="profStats" style="margin-top: 10px;"></div>
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

                <div class="profile-card" style="max-height: 250px; overflow-y: auto;">
                    <div class="profile-stat" style="margin-bottom: 10px; font-weight:bold; color: var(--warning);">Historie sezení (Logy):</div>
                    <table class="dl-table" style="width: 100%; margin-top: 0; background: transparent; border-radius: 0;">
                        <tbody id="profSessions">
                            <tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <form action="/dashboard/edit_user" method="POST" style="border-top: 1px solid #334155; padding-top: 15px; margin-top: 15px;">
                <input type="hidden" name="discord_id" id="modalDiscordId">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <label>Herní Nick:</label>
                        <input type="text" name="nick" id="modalNick" required>
                        <label>Zámek na PC (HWID a IP adresa):</label>
                        <input type="text" name="hwid" id="modalHwid" placeholder="Pro odblokování smažte text zde (vymaže HWID i IP)">
                        <div style="background-color: rgba(56, 189, 248, 0.1); padding: 10px; border-radius: 5px; border: 1px solid var(--blue-main); margin-bottom: 15px; margin-top: 10px;">
                            <label style="cursor: pointer; font-weight: bold; color: var(--blue-main); margin: 0; display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" name="dashboard_access" id="modalDashboardAccess" value="True" style="width: auto; margin: 0;"> 
                                Přístup do Dashboardu (2FA)
                            </label>
                        </div>
                    </div>
                    <div>
                        <label>Role:</label>
                        <div class="checkbox-group" style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
                            <label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label>
                            <label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label>
                            <label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label>
                            <label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label>
                        </div>
                        <div id="activeActions" style="margin-top: 20px;">
                            <div style="display: flex; gap: 10px;">
                                <button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit</button>
                                <button type="submit" name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;"><i class="fas fa-ban"></i> Dát BAN</button>
                                <button type="submit" name="action" value="unban" id="btnUnban" class="btn btn-success" style="flex: 1; display: none;"><i class="fas fa-check"></i> Un-BAN</button>
                            </div>
                            <div style="margin-top: 10px;">
                                <button type="submit" name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Smazat účet? (Zablokuje ID, umožní novou registraci)')"><i class="fas fa-trash"></i> Smazat (Soft Delete)</button>
                            </div>
                        </div>
                        <div id="deletedActions" style="display: none; margin-top: 20px;">
                            <p style="color: var(--danger); font-weight: bold; text-align: center; margin-top: 0; margin-bottom: 5px;">Tento účet je smazaný.</p>
                            <div style="display: flex; gap: 10px;">
                                <button type="submit" name="action" value="restore" class="btn btn-success" style="flex: 1;"><i class="fas fa-undo"></i> Obnovit účet</button>
                                <button type="submit" name="action" value="hard_delete" class="btn btn-dark" style="flex: 1;" onclick="return confirm('PERMANENTNÍ SMAZÁNÍ: Tato akce kompletně vymaže veškerá data. Pokračovat?')"><i class="fas fa-skull"></i> Smazat permanentně</button>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
            <button class="btn" onclick="closeModal()" style="background: transparent; color: var(--text-muted); width: 100%; margin-top: 15px; border: 1px solid #334155;">Zavřít profil</button>
        </div>
    </div>
</div>

<script>
    function openModal(btn) {
        try {
            document.getElementById('editModal').style.display = 'flex';
            document.getElementById('modalAppId').innerText = "#" + (btn.getAttribute('data-app-id') || "");
            
            let discord_id = btn.getAttribute('data-discord-id') || "";
            document.getElementById('modalDiscordId').value = discord_id;
            
            document.getElementById('modalNick').value = btn.getAttribute('data-nick') || "";
            
            let hwid = btn.getAttribute('data-hwid');
            document.getElementById('modalHwid').value = (!hwid || hwid === 'None') ? '' : hwid;
            
            let registered_at = btn.getAttribute('data-reg-at');
            document.getElementById('profRegistered').innerText = (registered_at && registered_at !== 'None') ? registered_at : 'Neznámé (Starý účet)';
            
            let dashboard_access = btn.getAttribute('data-db-access');
            document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True');
            document.getElementById('profDbAccess').innerHTML = dashboard_access === 'True' ? '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Povoleno</span>' : '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> Zakázáno</span>';
            
            document.querySelectorAll('input[name="roles"]').forEach(cb => cb.checked = false);
            let rolesStr = btn.getAttribute('data-roles') || "";
            rolesStr.split(',').forEach(r => {
                let el = document.querySelector(`input[name="roles"][value="${r.trim()}"]`);
                if(el) el.checked = true;
            });
            
            let is_deleted = btn.getAttribute('data-deleted');
            let is_banned = btn.getAttribute('data-banned');
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
            document.getElementById('profSessions').innerHTML = '<tr><td colspan="2" style="text-align: center;"><i class="fas fa-spinner fa-spin"></i></td></tr>';
            document.getElementById('profAppStatus').innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            document.getElementById('profStats').innerHTML = '';
            
            if (!discord_id || discord_id.trim() === '' || discord_id === 'None') {
                document.getElementById('profJoined').innerText = "Chybí ID";
                document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Chyba dat (ID nenalezeno)</span>";
                return;
            }

            fetch('/api/get_profile_data/' + discord_id)
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Chyba dat: " + data.error + "</span>";
                        return;
                    }
                    document.getElementById('profJoined').innerText = data.joined_at || "Nenalezen";
                    document.getElementById('modalStatusDot').innerHTML = data.status || "";
                    document.getElementById('profAppStatus').innerHTML = data.app_status || "";
                    document.getElementById('profStats').innerHTML = data.stats || "";
                    
                    let dlHtml = "";
                    if(data.downloads && data.downloads.length > 0) {
                        data.downloads.forEach(d => {
                            dlHtml += `<tr><td style="color: var(--blue-main);"><b>${d.version_name}</b></td><td style="color: var(--text-muted);">${d.downloaded_at}</td></tr>`;
                        });
                    } else {
                        dlHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím nestáhl žádný soubor.</td></tr>";
                    }
                    document.getElementById('profDownloads').innerHTML = dlHtml;

                    let sessHtml = "";
                    if(data.sessions && data.sessions.length > 0) {
                        data.sessions.forEach(s => {
                            sessHtml += `<tr>
                                <td style="color: var(--success); font-weight:bold; white-space:nowrap;">🟢 ${s.start_time.split(' ')[1] || s.start_time}</td>
                                <td style="color: var(--danger); font-weight:bold; white-space:nowrap;">🔴 ${s.end_time.split(' ')[1] || s.end_time}</td>
                            </tr>
                            <tr><td colspan="2" style="color: var(--text-muted); padding-top:0; padding-bottom:10px; border-bottom:1px solid #334155; text-align:center;">${s.start_time.split(' ')[0]}</td></tr>`;
                        });
                    } else {
                        sessHtml = "<tr><td colspan='2' style='color: var(--text-muted);'>Zatím žádná aktivita.</td></tr>";
                    }
                    document.getElementById('profSessions').innerHTML = sessHtml;
                })
                .catch(e => {
                    document.getElementById('profAppStatus').innerHTML = "<span style='color:#ef4444;'>Spojení selhalo</span>";
                });
        } catch(e) {
            alert("Chyba při otevírání modalu: " + e.message);
        }
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
        <p style="margin-bottom:0;">Celý projekt vznikl z nadšení pro dopravu, technologie a informační systems ve veřejné dopravě. Projekt není oficiálním produktem ani službou dopravců nebo organizací veřejné dopravy a nijak s nimi nespolupracuje. Jedná se čistě o fanouškovský projekt vytvořený pro zábavu, experimentování a zájem o dopravní technologie.</p>
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
HTML_DOWNLOADS_MAIN = """
<div style="max-width: 650px; margin: 60px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: var(--text-main); margin-top: 0; display: flex; align-items: center; justify-content: center; gap: 15px; font-size: 26px;">
            <i class="fas fa-shield-alt" style="color: var(--blue-main); font-size: 30px;"></i> Oficiální distribuce softwaru
        </h2>
        <p style="color: var(--text-muted); line-height: 1.6; font-size: 15px; margin-top: 20px;">
            Z důvodu ochrany projektu a samotného softwaru jsme se rozhodli přesunout jeho distribuci na náš Discord server. Díky tomu máme větší kontrolu nad přístupem k softwaru a můžeme lépe zabránit jeho zneužití nebo neautorizovanému šíření.
        </p>
    </div>
    <div style="border: 1px solid #334155; border-radius: 10px; padding: 30px; text-align: center; background: rgba(15, 23, 42, 0.4);">
        <h3 style="color: var(--text-main); margin-top: 0; margin-bottom: 15px; font-size: 18px;">Jak získat software:</h3>
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">
            Připojte se na náš Discord, ověřte, že nejste robot, a poté přejděte do kanálu 💾 • download, kde stačí postupovat podle pokynů DataCoreBota. 🚀
        </p>
        <a href="https://discord.gg/vmTagbC9mF" target="_blank" style="display: inline-block; transition: 0.3s; color: #5865F2; font-size: 90px; filter: drop-shadow(0 0 15px rgba(88, 101, 242, 0.4)); text-decoration: none;" onmouseover="this.style.transform='scale(1.1)'; this.style.filter='drop-shadow(0 0 25px rgba(88, 101, 242, 0.8))';" onmouseout="this.style.transform='scale(1)'; this.style.filter='drop-shadow(0 0 15px rgba(88, 101, 242, 0.4))';">
            <i class="fab fa-discord"></i>
        </a>
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
        <img src="{{ img_url }}" onerror="this.onerror=null; this.src='{{ logo_male }}';" alt="Avatar" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid var(--blue-main); margin-bottom: 15px; background-color: var(--bg-dark);">
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
    <h2 style="color: var(--text-main); margin-top: 0; display: flex; align-items: center; gap: 15px;">
        <i class="fas fa-user-circle" style="font-size: 30px; color: var(--blue-main);"></i> Profil hráče: <span style="color: var(--blue-main);">{{ searched_user.get('nick', 'Neznámý') }}</span>
    </h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
            <div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">První registrace</div>
            <div style="color: var(--text-main); font-size: 18px; font-weight: bold;">{{ searched_user.get('registered_at', 'Neznámé') }}</div>
        </div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
            <div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Nahráno hodin</div>
            <div style="color: #f59e0b; font-size: 18px; font-weight: bold;">{{ (searched_user.get('total_time') or 0) // 60 }}h {{ (searched_user.get('total_time') or 0) % 60 }}m</div>
        </div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
            <div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Počet spuštění</div>
            <div style="color: var(--success); font-size: 18px; font-weight: bold;">{{ searched_user.get('launch_count') or 0 }}x</div>
        </div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
            <div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Role</div>
            <div style="color: var(--text-main); font-size: 18px; font-weight: bold;">{{ searched_user.get('role', 'User') }}</div>
        </div>
        <div style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid #334155;">
            <div style="color: var(--text-muted); font-size: 12px; text-transform: uppercase;">Naposledy hráno</div>
            <div style="color: var(--blue-main); font-size: 18px; font-weight: bold;">
                {% if searched_user.get('is_online') %}<span style="color: var(--success);">Nyní hraje</span>{% else %}{{ searched_user.get('last_active', 'Nikdy') }}{% endif %}
            </div>
        </div>
    </div>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
        <div style="background: var(--bg-dark); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
            <h3 style="color: var(--blue-main); margin-top: 0; font-size: 16px;">Nejhranější linky hráče (TOP 5)</h3>
            <table style="width: 100%; margin: 0; background: transparent;">
                {% for l in searched_user_lines %}
                <tr>
                    {% set color = '#ffd700' if loop.index0 == 0 else ('#c0c0c0' if loop.index0 == 1 else ('#cd7f32' if loop.index0 == 2 else 'white')) %}
                    <td style="padding: 5px 0; color: {{color}}; font-weight:bold;">{{ loop.index }}. {{ l.get('line_name', '') }}</td>
                    <td style="padding: 5px 0; text-align: right; color: var(--blue-main); font-weight: bold;">{{ l.get('play_count', 0) }}x</td>
                </tr>
                {% else %}
                <tr><td colspan="2" style="padding: 5px 0; color: var(--text-muted);">Zatím nehrál žádnou linku.</td></tr>
                {% endfor %}
            </table>
            {% if searched_user_lines %}
            <button class="btn btn-dark" onclick="document.getElementById('personal-lines-modal').style.display='flex'" style="width: 100%; font-size: 12px; margin-top: 15px;"><i class="fas fa-list"></i> Zobrazit celou historii linek hráče</button>
            {% endif %}
        </div>
        <div style="background: var(--bg-dark); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
            <h3 style="color: var(--success); margin-top: 0; font-size: 16px;">Nejoblíbenější zastávky hráče (TOP 5)</h3>
            <table style="width: 100%; margin: 0; background: transparent;">
                {% for s in searched_user_stops %}
                <tr>
                    {% set color = '#ffd700' if loop.index0 == 0 else ('#c0c0c0' if loop.index0 == 1 else ('#cd7f32' if loop.index0 == 2 else 'white')) %}
                    <td style="padding: 5px 0; color: {{color}}; font-weight:bold;">{{ loop.index }}. {{ s.get('stop_name', '') }}</td>
                    <td style="padding: 5px 0; text-align: right; color: var(--success); font-weight: bold;">{{ s.get('announce_count', 0) }}x</td>
                </tr>
                {% else %}
                <tr><td colspan="2" style="padding: 5px 0; color: var(--text-muted);">Zatím nevyhlásil žádnou zastávku.</td></tr>
                {% endfor %}
            </table>
            {% if searched_user_stops %}
            <button class="btn btn-dark" onclick="document.getElementById('personal-stops-modal').style.display='flex'" style="width: 100%; font-size: 12px; margin-top: 15px;"><i class="fas fa-list"></i> Zobrazit celou historii zastávek hráče</button>
            {% endif %}
        </div>
    </div>

    <a href="/stats" class="btn btn-dark" style="margin-top: 20px; font-size: 12px;"><i class="fas fa-times"></i> Zavřít profil</a>
</div>

<div class="modal-overlay" id="personal-lines-modal">
    <div class="modal" style="width: 700px;">
        <div style="width: 100%;">
            <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-route"></i> Všechny linky hráče</span>
                <span onclick="document.getElementById('personal-lines-modal').style.display='none'" style="cursor:pointer; color:var(--danger);"><i class="fas fa-times"></i></span>
            </h2>
            <input type="text" id="personal-lines-search" placeholder="Hledat linku hráče..." onkeyup="filterPersonalLines()" style="margin-bottom: 15px; width: 100%;">
            <div style="max-height: 500px; overflow-y: auto;">
                <table style="width: 100%;" id="personal-lines-table">
                    <tr><th>Linka</th><th style="text-align:right;">Počet odehrání</th></tr>
                    {% for l in searched_user_lines %}
                    <tr class="pline-row">
                        <td style="color: white; font-weight:bold;">{{ l.get('line_name', '') }}</td>
                        <td style="text-align:right; color: var(--blue-main); font-weight:bold;">{{ l.get('play_count', 0) }}x</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <button class="btn btn-dark" style="width: 100%; margin-top: 15px;" onclick="document.getElementById('personal-lines-modal').style.display='none'">Zavřít</button>
        </div>
    </div>
</div>

<div class="modal-overlay" id="personal-stops-modal">
    <div class="modal" style="width: 700px;">
        <div style="width: 100%;">
            <h2 style="color: var(--success); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-map-marker-alt"></i> Všechny zastávky hráče</span>
                <span onclick="document.getElementById('personal-stops-modal').style.display='none'" style="cursor:pointer; color:var(--danger);"><i class="fas fa-times"></i></span>
            </h2>
            <input type="text" id="personal-stops-search" placeholder="Hledat zastávku hráče..." onkeyup="filterPersonalStops()" style="margin-bottom: 15px; width: 100%;">
            <div style="max-height: 500px; overflow-y: auto;">
                <table style="width: 100%;" id="personal-stops-table">
                    <tr><th>Zastávka</th><th style="text-align:right;">Počet vyhlášení</th></tr>
                    {% for s in searched_user_stops %}
                    <tr class="pstop-row">
                        <td style="color: white; font-weight:bold;">{{ s.get('stop_name', '') }}</td>
                        <td style="text-align:right; color: var(--success); font-weight:bold;">{{ s.get('announce_count', 0) }}x</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <button class="btn btn-dark" style="width: 100%; margin-top: 15px;" onclick="document.getElementById('personal-stops-modal').style.display='none'">Zavřít</button>
        </div>
    </div>
</div>
{% endif %}

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; border-left: 5px solid var(--blue-main); box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase; font-weight: bold;">Aktuální verze (User)</div>
        <div style="font-size: 32px; font-weight: 900; color: var(--text-main); text-shadow: 0 0 10px rgba(255,255,255,0.2);">{{ user_ver }}</div>
    </div>
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; border-left: 5px solid #a855f7; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase; font-weight: bold;">Aktuální verze (Beta Tester)</div>
        <div style="font-size: 32px; font-weight: 900; color: var(--text-main); text-shadow: 0 0 10px rgba(168, 85, 247, 0.4);">{{ bt_ver }}</div>
    </div>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 40px;">
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <i class="fas fa-users" style="font-size: 40px; color: var(--success); margin-bottom: 15px; text-shadow: 0 0 15px rgba(16, 185, 129, 0.5);"></i>
        <div style="font-size: 36px; font-weight: 900; color: var(--text-main);">{{ activated_users }}</div>
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase;">Aktivních uživatelů</div>
    </div>
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <i class="fas fa-heart" style="font-size: 40px; color: #ef4444; margin-bottom: 15px; text-shadow: 0 0 15px rgba(239, 68, 68, 0.5);"></i>
        <div style="font-size: 36px; font-weight: 900; color: var(--text-main);">{{ total_supporters }}</div>
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase;">Podporovatelů</div>
    </div>
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <i class="fas fa-clock" style="font-size: 40px; color: var(--warning); margin-bottom: 15px; text-shadow: 0 0 15px rgba(245, 158, 11, 0.5);"></i>
        <div style="font-size: 36px; font-weight: 900; color: var(--text-main);">{{ total_hours }}h</div>
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase;">Celkově nahráno</div>
        <div style="color: var(--warning); font-size: 12px; font-weight: bold; margin-top: 5px;">Dnes: {{ today_time_str }}</div>
    </div>
    <div style="background: var(--bg-panel); padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <i class="fas fa-rocket" style="font-size: 40px; color: var(--blue-main); margin-bottom: 15px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.5);"></i>
        <div style="font-size: 36px; font-weight: 900; color: var(--text-main);">{{ total_launches }}x</div>
        <div style="color: var(--text-muted); font-size: 14px; text-transform: uppercase;">Celkově spuštěno</div>
    </div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
    <div style="background: var(--bg-panel); padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <h2 style="color: var(--warning); margin-top: 0; text-align: center; border-bottom: 1px solid #334155; padding-bottom: 15px;"><i class="fas fa-trophy"></i> TOP 3: Nahrané hodiny</h2>
        <div style="display: flex; flex-direction: column; gap: 15px; margin-top: 20px;">
            {% set colors = ['#ffd700', '#c0c0c0', '#cd7f32'] %}
            {% set bg_colors = ['rgba(255, 215, 0, 0.1)', 'rgba(192, 192, 192, 0.1)', 'rgba(205, 127, 50, 0.1)'] %}
            {% for u in top_time %}
            <div style="display: flex; justify-content: space-between; align-items: center; background: {{ bg_colors[loop.index0] }}; border: 1px solid {{ colors[loop.index0] }}; border-left: 5px solid {{ colors[loop.index0] }}; padding: 15px 20px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="font-size: 24px; font-weight: 900; color: {{ colors[loop.index0] }};">{{ loop.index }}.</div>
                    <div style="font-size: 18px; font-weight: bold; color: var(--text-main);">{{ u.get('nick', 'Neznámý') }}</div>
                </div>
                <div style="font-size: 20px; font-weight: 900; color: {{ colors[loop.index0] }};">{{ (u.get('total_time') or 0) // 60 }}h {{ (u.get('total_time') or 0) % 60 }}m</div>
            </div>
            {% else %}
            <div style="text-align: center; color: var(--text-muted); padding: 20px;">Zatím žádná data k zobrazení.</div>
            {% endfor %}
        </div>
    </div>

    <div style="background: var(--bg-panel); padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <h2 style="color: var(--blue-main); margin-top: 0; text-align: center; border-bottom: 1px solid #334155; padding-bottom: 15px;"><i class="fas fa-trophy"></i> TOP 3: Nejvíce spuštění</h2>
        <div style="display: flex; flex-direction: column; gap: 15px; margin-top: 20px;">
            {% set colors = ['#ffd700', '#c0c0c0', '#cd7f32'] %}
            {% set bg_colors = ['rgba(255, 215, 0, 0.1)', 'rgba(192, 192, 192, 0.1)', 'rgba(205, 127, 50, 0.1)'] %}
            {% for u in top_launches %}
            <div style="display: flex; justify-content: space-between; align-items: center; background: {{ bg_colors[loop.index0] }}; border: 1px solid {{ colors[loop.index0] }}; border-left: 5px solid {{ colors[loop.index0] }}; padding: 15px 20px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="font-size: 24px; font-weight: 900; color: {{ colors[loop.index0] }};">{{ loop.index }}.</div>
                    <div style="font-size: 18px; font-weight: bold; color: var(--text-main);">{{ u.get('nick', 'Neznámý') }}</div>
                </div>
                <div style="font-size: 20px; font-weight: 900; color: {{ colors[loop.index0] }};">{{ u.get('launch_count') or 0 }}x</div>
            </div>
            {% else %}
            <div style="text-align: center; color: var(--text-muted); padding: 20px;">Zatím žádná data k zobrazení.</div>
            {% endfor %}
        </div>
    </div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 40px; margin-bottom: 40px;">
    <div style="background: var(--bg-panel); padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <h2 style="color: var(--blue-main); margin-top: 0; text-align: center; border-bottom: 1px solid #334155; padding-bottom: 15px;"><i class="fas fa-route"></i> TOP 10: Nejhranější linky (Globálně)</h2>
        <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 20px;">
            {% set colors = ['#ffd700', '#c0c0c0', '#cd7f32'] %}
            {% set bg_colors = ['rgba(255, 215, 0, 0.1)', 'rgba(192, 192, 192, 0.1)', 'rgba(205, 127, 50, 0.1)'] %}
            {% for l in top_lines %}
                {% if loop.index0 < 3 %}
                <div style="display: flex; justify-content: space-between; align-items: center; background: {{ bg_colors[loop.index0] }}; padding: 12px 20px; border-radius: 8px; border: 1px solid {{ colors[loop.index0] }}; border-left: 5px solid {{ colors[loop.index0] }};">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-size: 20px; font-weight: 900; color: {{ colors[loop.index0] }};"><i class="fas fa-medal"></i> {{ loop.index }}.</div>
                        <div style="font-weight: bold; color: white; font-size: 18px;">{{ l.get('line_name', '') }}</div>
                    </div>
                    <div style="color: {{ colors[loop.index0] }}; font-weight: bold; font-size: 18px;">{{ l.get('play_count', 0) }}x</div>
                </div>
                {% else %}
                <div style="display: flex; justify-content: space-between; background: rgba(0,0,0,0.2); padding: 12px 20px; border-radius: 8px; border-left: 4px solid var(--blue-main);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-size: 16px; font-weight: bold; color: var(--text-muted);">{{ loop.index }}.</div>
                        <div style="font-weight: bold; color: white; font-size: 16px;">{{ l.get('line_name', '') }}</div>
                    </div>
                    <div style="color: var(--blue-main); font-weight: bold;">{{ l.get('play_count', 0) }}x</div>
                </div>
                {% endif %}
            {% else %}
            <div style="text-align: center; color: var(--text-muted);">Zatím žádná data.</div>
            {% endfor %}
        </div>
        
        <div style="text-align: center; margin-top: 20px;">
            <button class="btn btn-dark" onclick="document.getElementById('all-lines-modal').style.display='flex'" style="font-size: 13px; width: 100%;"><i class="fas fa-list"></i> Zobrazit kompletní databázi linek</button>
        </div>
    </div>

    <div style="background: var(--bg-panel); padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <h2 style="color: var(--success); margin-top: 0; text-align: center; border-bottom: 1px solid #334155; padding-bottom: 15px;"><i class="fas fa-map-marker-alt"></i> TOP 10: Nejoblíbenější zastávky (Globálně)</h2>
        <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 20px; max-height: 500px; overflow-y: auto; padding-right: 10px;">
            {% set colors = ['#ffd700', '#c0c0c0', '#cd7f32'] %}
            {% set bg_colors = ['rgba(255, 215, 0, 0.1)', 'rgba(192, 192, 192, 0.1)', 'rgba(205, 127, 50, 0.1)'] %}
            {% for s in top_stops %}
                {% if loop.index0 < 3 %}
                <div style="display: flex; justify-content: space-between; align-items: center; background: {{ bg_colors[loop.index0] }}; padding: 12px 20px; border-radius: 8px; border: 1px solid {{ colors[loop.index0] }}; border-left: 5px solid {{ colors[loop.index0] }};">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-size: 20px; font-weight: 900; color: {{ colors[loop.index0] }};"><i class="fas fa-medal"></i> {{ loop.index }}.</div>
                        <div style="font-weight: bold; color: white; font-size: 15px;">{{ s.get('stop_name', '') }}</div>
                    </div>
                    <div style="color: {{ colors[loop.index0] }}; font-weight: bold; font-size: 16px;">{{ s.get('announce_count', 0) }}x</div>
                </div>
                {% else %}
                <div style="display: flex; justify-content: space-between; background: rgba(0,0,0,0.2); padding: 10px 15px; border-radius: 8px; border-left: 4px solid var(--success);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-size: 14px; font-weight: bold; color: var(--text-muted);">{{ loop.index }}.</div>
                        <div style="font-weight: bold; color: white; font-size: 14px;">{{ s.get('stop_name', '') }}</div>
                    </div>
                    <div style="color: var(--success); font-weight: bold; font-size: 14px;">{{ s.get('announce_count', 0) }}x</div>
                </div>
                {% endif %}
            {% else %}
            <div style="text-align: center; color: var(--text-muted);">Zatím žádná data.</div>
            {% endfor %}
        </div>
        
        <div style="text-align: center; margin-top: 20px;">
            <button class="btn btn-dark" onclick="document.getElementById('all-stops-modal').style.display='flex'" style="font-size: 13px; width: 100%;"><i class="fas fa-list"></i> Zobrazit kompletní databázi zastávek</button>
        </div>
    </div>
</div>

<div class="modal-overlay" id="all-lines-modal">
    <div class="modal" style="width: 700px;">
        <div style="width: 100%;">
            <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-route"></i> Databáze odehraných linek</span>
                <span onclick="document.getElementById('all-lines-modal').style.display='none'" style="cursor:pointer; color:var(--danger);"><i class="fas fa-times"></i></span>
            </h2>
            <input type="text" id="lines-search" placeholder="Hledat linku..." onkeyup="filterLines()" style="margin-bottom: 15px; width: 100%;">
            <div style="max-height: 500px; overflow-y: auto;">
                <table style="width: 100%;" id="lines-table">
                    <tr><th>Linka</th><th style="text-align:right;">Počet odehrání</th></tr>
                    {% for l in all_lines %}
                    <tr class="line-row">
                        <td style="color: white; font-weight:bold;">{{ l.get('line_name', '') }}</td>
                        <td style="text-align:right; color: var(--blue-main); font-weight:bold;">{{ l.get('play_count', 0) }}x</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <button class="btn btn-dark" style="width: 100%; margin-top: 15px;" onclick="document.getElementById('all-lines-modal').style.display='none'">Zavřít</button>
        </div>
    </div>
</div>

<div class="modal-overlay" id="all-stops-modal">
    <div class="modal" style="width: 700px;">
        <div style="width: 100%;">
            <h2 style="color: var(--success); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-map-marker-alt"></i> Databáze vyhlášených zastávek</span>
                <span onclick="document.getElementById('all-stops-modal').style.display='none'" style="cursor:pointer; color:var(--danger);"><i class="fas fa-times"></i></span>
            </h2>
            <input type="text" id="stops-search" placeholder="Hledat zastávku..." onkeyup="filterStops()" style="margin-bottom: 15px; width: 100%;">
            <div style="max-height: 500px; overflow-y: auto;">
                <table style="width: 100%;" id="stops-table">
                    <tr><th>Zastávka</th><th style="text-align:right;">Počet vyhlášení</th></tr>
                    {% for s in all_stops %}
                    <tr class="stop-row">
                        <td style="color: white; font-weight:bold;">{{ s.get('stop_name', '') }}</td>
                        <td style="text-align:right; color: var(--success); font-weight:bold;">{{ s.get('announce_count', 0) }}x</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <button class="btn btn-dark" style="width: 100%; margin-top: 15px;" onclick="document.getElementById('all-stops-modal').style.display='none'">Zavřít</button>
        </div>
    </div>
</div>

<script>
    function filterLines() {
        let input = document.getElementById("lines-search").value.toUpperCase();
        let rows = document.querySelectorAll(".line-row");
        rows.forEach(r => {
            let text = r.innerText.toUpperCase();
            r.style.display = text.indexOf(input) > -1 ? "" : "none";
        });
    }
    function filterStops() {
        let input = document.getElementById("stops-search").value.toUpperCase();
        let rows = document.querySelectorAll(".stop-row");
        rows.forEach(r => {
            let text = r.innerText.toUpperCase();
            r.style.display = text.indexOf(input) > -1 ? "" : "none";
        });
    }
    function filterPersonalLines() {
        let input = document.getElementById("personal-lines-search").value.toUpperCase();
        let rows = document.querySelectorAll(".pline-row");
        rows.forEach(r => {
            let text = r.innerText.toUpperCase();
            r.style.display = text.indexOf(input) > -1 ? "" : "none";
        });
    }
    function filterPersonalStops() {
        let input = document.getElementById("personal-stops-search").value.toUpperCase();
        let rows = document.querySelectorAll(".pstop-row");
        rows.forEach(r => {
            let text = r.innerText.toUpperCase();
            r.style.display = text.indexOf(input) > -1 ? "" : "none";
        });
    }
</script>
"""

HTML_SUPPORTERS = """
<style>
    .glowing-btn-blue { background-color: var(--blue-main); color: #000; padding: 15px 40px; font-size: 20px; font-weight: 900; border-radius: 50px; text-decoration: none; display: inline-block; margin-top: 20px; box-shadow: 0 0 20px rgba(56, 189, 248, 0.6); transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 1px; border: none; cursor: pointer; }
    .glowing-btn-blue:hover { box-shadow: 0 0 40px rgba(56, 189, 248, 1); transform: scale(1.05); color: #000; }
    .supporter-wrapper { width: 100%; max-width: 500px; min-height: 230px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; text-align: center; box-sizing: border-box; }
    .tier-1 { background-color: rgba(15, 23, 42, 0.8); padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.3); border-left: 5px solid #38bdf8; transition: transform 0.5s ease, box-shadow 0.5s ease; }
    .tier-1:hover { transform: scale(1.05); box-shadow: 0 10px 25px rgba(56, 189, 248, 0.4); }
    .tier-1 .name-title { color: #e0f2fe; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5); font-size: 20px; margin: 0 0 10px 0; }
    .tier-1 .title-badge { font-size: 10px; color: #38bdf8; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; margin-bottom: 10px; }
    .tier-1 .amt-badge { display: inline-block; margin-bottom: 25px; background-color: rgba(56, 189, 248, 0.1); color: var(--blue-main); padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; border: 1px solid rgba(56, 189, 248, 0.3); }
    @keyframes pulseMedium { from { box-shadow: 0 0 10px rgba(245, 158, 11, 0.3); } to { box-shadow: 0 0 20px rgba(245, 158, 11, 0.6); } }
    .tier-2 { background-color: rgba(30, 41, 59, 0.9); padding: 25px; border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.6); border-left: 6px solid #f59e0b; animation: pulseMedium 2s infinite alternate; transition: transform 0.5s ease, box-shadow 0.5s ease; }
    .tier-2:hover { transform: scale(1.05) !important; animation: none; box-shadow: 0 10px 35px rgba(245, 158, 11, 0.8); }
    .tier-2 .name-title { color: #fcd34d; font-size: 26px; margin: 0 0 10px 0; text-shadow: 0 0 10px rgba(245, 158, 11, 0.5); }
    .tier-2 .title-badge { font-size: 12px; color: #f59e0b; text-transform: uppercase; font-weight: bold; letter-spacing: 2px; margin-bottom: 10px; }
    .tier-2 .amt-badge { display: inline-block; margin-bottom: 25px; background-color: rgba(245, 158, 11, 0.1); color: var(--warning); padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 16px; border: 1px solid rgba(245, 158, 11, 0.5); }
    @keyframes epicWebGlow { from { box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); } to { box-shadow: 0 0 50px rgba(239, 68, 68, 0.9), inset 0 0 30px rgba(239, 68, 68, 0.3); } }
    .tier-3 { background: linear-gradient(135deg, #2a0a18, #450a0a); padding: 30px; border-radius: 15px; border: 2px solid #ef4444; animation: epicWebGlow 1.5s infinite alternate; transition: transform 0.5s ease, box-shadow 0.5s ease; }
    .tier-3:hover { transform: scale(1.08) !important; animation: none; box-shadow: 0 15px 60px rgba(239, 68, 68, 1); }
    .tier-3 .name-title { color: #fca5a5; font-size: 32px !important; margin: 0 0 15px 0; text-shadow: 0 0 20px #ef4444, 0 0 40px #ef4444; text-transform: uppercase; font-weight: 900; }
    .tier-3 .title-badge { font-size: 14px; color: #ef4444; text-transform: uppercase; font-weight: 900; letter-spacing: 3px; margin-bottom: 10px; text-shadow: 0 0 10px #ef4444; }
    .tier-3 .amt-badge { display: inline-block; margin-bottom: 25px; background-color: #ef4444 !important; color: #fff !important; border: 2px solid #fca5a5 !important; padding: 8px 20px; border-radius: 25px; font-weight: bold; font-size: 20px !important; box-shadow: 0 0 20px #ef4444; }
</style>

<div style="max-width: 800px; margin: 0 auto; padding: 20px; position: relative;">
    <div style="text-align: center; margin-bottom: 40px;">
        <h1 style="color: var(--blue-main); font-size: 36px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);">Děkuji všem za podporu!</h1>
        <p style="color: var(--text-muted); font-size: 16px; line-height: 1.6; max-width: 600px; margin: 0 auto;">Zde vidíte lidi, kteří tento projekt finančně podpořili. Vaše příspěvky mi obrovsky pomáhají hradit náklady na servery a motivují mě do dalšího vývoje Projektu OIS IDPK. Jsem neskutečně rád za každého z vás!</p>
        <a href="https://www.buymeacoffee.com/marekk_czz" target="_blank" class="glowing-btn-blue"><i class="fas fa-heart"></i> Podpořit Projekt OIS IDPK</a>
    </div>
    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 40px 0;">
    <h2 style="text-align: center; color: var(--text-main); letter-spacing: 3px; margin-bottom: 30px; text-shadow: 0 0 10px rgba(255,255,255,0.2);">SEZNAM PODPOROVATELŮ</h2>
    <div style="display: flex; flex-direction: column; gap: 40px; padding-bottom: 50px; align-items: center;">
        {% for s in supporters %}
        <div class="tier-{{ s.get('tier', 1) }} supporter-wrapper">
            <div style="width: 100%;">
                {% if s.get('tier') == 3 %} <div class="title-badge">MEGA PODPOROVATEL</div>
                {% elif s.get('tier') == 2 %} <div class="title-badge">VELKÝ PODPOROVATEL</div>
                {% else %} <div class="title-badge">PODPOROVATEL</div> {% endif %}
                <h3 class="name-title">{{ s.get('name', 'Neznámý dárce') }}</h3>
                <div class="amt-badge">{{ s.get('amount', '') }}</div>
            </div>
            <div style="width: 100%; margin-top: auto;">
                {% if s.get('message') %}
                <p style="color: var(--text-main); font-size: 16px; font-style: italic; margin: 0 auto 15px auto; line-height: 1.5; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border-left: 2px solid rgba(255,255,255,0.2); max-width: 90%;">
                    "{{ s.get('message') }}"
                </p>
                {% endif %}
                <div style="font-size: 11px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; text-align: center;">Datum podpory: {{ s.get('created_at', '') }}</div>
            </div>
        </div>
        {% else %}
        <div style="text-align: center; color: var(--text-muted); padding: 40px; background: rgba(0,0,0,0.2); border-radius: 10px; border: 1px dashed rgba(255,255,255,0.1); width: 100%;">Zatím zde nikdo není. Buďte první!</div>
        {% endfor %}
    </div>
</div>
"""

HTML_CLAIM = """
<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; border-top: 4px solid var(--blue-main); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <h2 style="color: var(--blue-main); text-align: center; margin-top: 0;"><i class="fas fa-gift"></i> Vyzvednutí VIP Role</h2>
    <p style="color: var(--text-muted); font-size: 14px; text-align: center; margin-bottom: 30px;">Zadejte jméno, pod kterým jste před malou chvílí poslali příspěvek na Buy Me a Coffee, a Váš Discord Nick. Náš systém Vám obratem automaticky přidělí roli!</p>
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
    new Chart(document.getElementById('chart7d').getContext('2d'), { type: 'line', data: { labels: labels7d, datasets: [{ label: 'Počet návštěv', data: data7d, borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.2)', borderWidth: 3, tension: 0.3, fill: true }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } } } });
    new Chart(document.getElementById('chart24h').getContext('2d'), { type: 'bar', data: { labels: labels24h, datasets: [{ label: 'Dnešní návštěvy', data: data24h, backgroundColor: '#38bdf8', borderRadius: 4 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8', maxTicksLimit: 12 }, grid: { display: false } } } } });
</script>
"""

HTML_APP_MANAGEMENT = """
<h2 style="color: var(--blue-main);"><i class="fas fa-cogs"></i> Správa aplikace</h2>
<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
    <div class="card" style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; flex: 1; min-width: 250px; text-align: center; border: 1px solid #334155;">
        
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            {% if soft_enabled %}
                <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #10b981; box-shadow: 0 0 25px #10b981; display: flex; align-items: center; justify-content: center; transition: all 0.3s;">
                    <i class="fas fa-globe" style="color: white; font-size: 35px;"></i>
                </div>
            {% else %}
                <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #ef4444; box-shadow: 0 0 25px #ef4444; display: flex; align-items: center; justify-content: center; transition: all 0.3s;">
                    <i class="fas fa-power-off" style="color: white; font-size: 35px;"></i>
                </div>
            {% endif %}
        </div>

        <h3 style="color: white; margin-top: 0;">Globální stav softwaru</h3>
        <p style="color: var(--text-muted); font-size: 14px;">Vypne nebo zapne celou aplikaci.</p>
        <form action="/dashboard/toggle_software" method="POST">
            <input type="hidden" name="new_status" value="{% if soft_enabled %}False{% else %}True{% endif %}">
            {% if soft_enabled %}
                <button type="submit" class="btn" style="background-color: #ef4444; color: white; border: none; padding: 12px 25px; border-radius: 50px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%;"><i class="fas fa-times-circle"></i> Vypnout software</button>
            {% else %}
                <button type="submit" class="btn" style="background-color: #10b981; color: white; border: none; padding: 12px 25px; border-radius: 50px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%;"><i class="fas fa-check-circle"></i> Zapnout software</button>
            {% endif %}
        </form>
    </div>

    <div class="card" style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; flex: 1; min-width: 250px; text-align: center; border: 1px solid #334155;">
        
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            {% if dl_enabled %}
                <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #3b82f6; box-shadow: 0 0 25px #3b82f6; display: flex; align-items: center; justify-content: center; transition: all 0.3s;">
                    <i class="fas fa-download" style="color: white; font-size: 35px;"></i>
                </div>
            {% else %}
                <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #ef4444; box-shadow: 0 0 25px #ef4444; display: flex; align-items: center; justify-content: center; transition: all 0.3s;">
                    <i class="fas fa-times" style="color: white; font-size: 35px;"></i>
                </div>
            {% endif %}
        </div>

        <h3 style="color: white; margin-top: 0;">Stahování softwaru</h3>
        <p style="color: var(--text-muted); font-size: 14px;">Povolí nebo zakáže stahování.</p>
        <form action="/dashboard/toggle_downloads" method="POST">
            <input type="hidden" name="return_to" value="app_management">
            <input type="hidden" name="new_status" value="{% if dl_enabled %}False{% else %}True{% endif %}">
            {% if dl_enabled %}
                <button type="submit" class="btn" style="background-color: #ef4444; color: white; border: none; padding: 12px 25px; border-radius: 50px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%;"><i class="fas fa-times-circle"></i> Zakázat stahování</button>
            {% else %}
                <button type="submit" class="btn" style="background-color: #10b981; color: white; border: none; padding: 12px 25px; border-radius: 50px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%;"><i class="fas fa-check-circle"></i> Povolit stahování</button>
            {% endif %}
        </form>
    </div>
</div>
"""

HTML_NOTIFICATIONS = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-bell" style="color:#f59e0b;"></i> Systém Oznámení (Pop-up do aplikace)</h2>
</div>

<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning);">
        <h3 style="margin-top: 0; color: var(--warning);"><i class="fas fa-paper-plane"></i> Odeslat nové oznámení</h3>
        <p style="color: var(--text-muted); font-size: 13px;">Toto vyskočí lidem ihned po spuštění palubáku.</p>
        <form action="/dashboard/send_app_message" method="POST">
            <label style="color: var(--text-muted); font-size: 13px;">Nadpis oznámení:</label>
            <input type="text" name="title" placeholder="Např. Vánoční Update 1.5!" required>
            
            <label style="color: var(--text-muted); font-size: 13px;">Text oznámení (lze použít HTML tagy jako &lt;br&gt;):</label>
            <textarea name="content" rows="4" placeholder="Napište text zprávy..." required></textarea>
            
            <label style="color: var(--text-muted); font-size: 13px;">Pro koho je zpráva určena?</label>
            <select name="target_type" id="target_type" onchange="toggleTargetData()" style="margin-bottom: 10px;">
                <option value="GLOBAL">Všichni uživatelé (Globálně)</option>
                <option value="ROLE">Podle Rolí</option>
                <option value="USERS">Vybraní uživatelé (Podle ID nebo Nicku)</option>
            </select>
            
            <div id="target_data_container" style="display: none;">
                <label style="color: var(--text-muted); font-size: 13px;" id="target_label">Specifikace:</label>
                <input type="text" name="target_data" id="target_data" placeholder="">
            </div>

            <div style="background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin: 15px 0;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: var(--text-main); font-size: 13px;">
                    <input type="checkbox" name="has_link" id="has_link" onchange="toggleLinkUrl()" style="width: auto; margin: 0;">
                    Přidat do aplikace speciální tlačítko s odkazem
                </label>
            </div>
            
            <div id="link_url_container" style="display: none;">
                <label style="color: var(--text-muted); font-size: 13px;">URL adresa tlačítka (např. odkaz na novinky):</label>
                <input type="url" name="link_url" placeholder="https://...">
            </div>

            <div style="background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin: 15px 0;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: var(--text-main); font-size: 13px;">
                    <input type="checkbox" name="repeat" style="width: auto; margin: 0;">
                    Zobrazovat uživatelům DOKOLA (Při každém startu)
                </label>
                <span style="font-size: 11px; color: var(--text-muted); margin-left: 23px;">Pokud nezaškrtneš, uživateli to vyskočí jen jednou a pak se to skryje.</span>
            </div>

            <label style="color: var(--text-muted); font-size: 13px;">Kdy má oznámení automaticky zmizet? (Expirace)</label>
            <input type="text" name="expires_at" placeholder="Např. 31.12.2026 23:59 (Volitelné)">

            <button type="submit" class="btn btn-warning" style="width: 100%; margin-top: 10px;"><i class="fas fa-paper-plane"></i> Vytvořit Oznámení</button>
        </form>
    </div>

    <div style="flex: 2; min-width: 300px;">
        <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: var(--success); margin-top: 0;"><i class="fas fa-broadcast-tower"></i> Aktivní Oznámení</h3>
            <div style="overflow-x: auto;">
                <table>
                    <tr>
                        <th>Nadpis</th>
                        <th>Cílení</th>
                        <th>Opakování</th>
                        <th>Expirace</th>
                        <th>Akce</th>
                    </tr>
                    {% for m in messages %}
                    {% if not m.get('is_archived') %}
                    <tr>
                        <td style="color: var(--text-main); font-weight: bold;">{{ m.get('title', '') }}</td>
                        <td>
                            {% if m.get('target_type') == 'GLOBAL' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">Globálně</span>
                            {% elif m.get('target_type') == 'ROLE' %}<span class="role-tag" style="background-color: #a855f7; color: white;">Role: {{ m.get('target_data', '') }}</span>
                            {% else %}<span class="role-tag" style="background-color: #ef4444; color: white;">Hráči: {{ m.get('target_data', '')[:15] }}...</span>{% endif %}
                        </td>
                        <td>
                            {% if m.get('repeat') %}<span style="color:var(--warning); font-size: 12px; font-weight:bold;"><i class="fas fa-sync"></i> Ano</span>
                            {% else %}<span style="color:var(--success); font-size: 12px; font-weight:bold;">Jen jednou</span>{% endif %}
                        </td>
                        <td style="color: var(--text-muted); font-size: 12px;">{{ m.get('expires_at', 'Nikdy') or 'Nikdy' }}</td>
                        <td style="display: flex; gap: 5px;">
                            <button type="button" class="btn btn-warning" style="padding: 5px 10px; font-size: 12px;" title="Upravit" 
                                data-id="{{ m.get('message_id', '') }}"
                                data-title="{{ (m.get('title') or '') | e }}"
                                data-content="{{ (m.get('content') or '') | e }}"
                                data-type="{{ (m.get('target_type') or '') | e }}"
                                data-data="{{ (m.get('target_data') or '') | e }}"
                                data-url="{{ (m.get('link_url') or '') | e }}"
                                data-exp="{{ (m.get('expires_at') or '') | e }}"
                                data-repeat="{{ 'true' if m.get('repeat') else 'false' }}"
                                onclick="openEditMessageModal(this)">
                                <i class="fas fa-edit"></i>
                            </button>
                            <form action="/dashboard/archive_app_message" method="POST" style="margin:0;">
                                <input type="hidden" name="message_id" value="{{ m.get('message_id', '') }}">
                                <button type="submit" class="btn btn-dark" style="padding: 5px 10px; font-size: 12px;" title="Archivovat (Zmizí z aplikace)"><i class="fas fa-archive"></i></button>
                            </form>
                            <form action="/dashboard/delete_app_message" method="POST" style="margin:0;">
                                <input type="hidden" name="message_id" value="{{ m.get('message_id', '') }}">
                                <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Opravdu smazat oznámení?')"><i class="fas fa-trash"></i></button>
                            </form>
                        </td>
                    </tr>
                    {% endif %}
                    {% else %}
                    <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádná aktivní oznámení.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; opacity: 0.8;">
            <h3 style="color: var(--text-muted); margin-top: 0;"><i class="fas fa-archive"></i> Archivovaná Oznámení</h3>
            <div style="overflow-x: auto;">
                <table>
                    <tr>
                        <th>Nadpis</th>
                        <th>Cílení</th>
                        <th>Vytvořeno</th>
                        <th>Akce</th>
                    </tr>
                    {% for m in messages %}
                    {% if m.get('is_archived') %}
                    <tr>
                        <td style="color: var(--text-muted);">{{ m.get('title', '') }}</td>
                        <td style="font-size: 12px; color: var(--text-muted);">{{ m.get('target_type', '') }}</td>
                        <td style="color: var(--text-muted); font-size: 12px;">{{ m.get('created_at', '') }}</td>
                        <td>
                            <form action="/dashboard/delete_app_message" method="POST" style="margin:0;">
                                <input type="hidden" name="message_id" value="{{ m.get('message_id', '') }}">
                                <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Trvale smazat z archivu?')"><i class="fas fa-trash"></i></button>
                            </form>
                        </td>
                    </tr>
                    {% endif %}
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
</div>

<div class="modal-overlay" id="editMessageModal">
    <div class="modal" style="width: 500px; border-top: 5px solid var(--warning);">
        <div style="width: 100%;">
            <h2 style="color: var(--warning); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                <i class="fas fa-edit"></i> Úprava Oznámení
            </h2>
            <form action="/dashboard/edit_app_message" method="POST">
                <input type="hidden" name="message_id" id="em_id">
                
                <label style="color: var(--text-muted); font-size: 13px;">Nadpis:</label>
                <input type="text" name="title" id="em_title" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">Text:</label>
                <textarea name="content" id="em_content" rows="4" required></textarea>
                
                <label style="color: var(--text-muted); font-size: 13px;">Typ cílení:</label>
                <select name="target_type" id="em_type" required>
                    <option value="GLOBAL">Globálně</option>
                    <option value="ROLE">Podle Rolí</option>
                    <option value="USERS">Vybraní uživatelé</option>
                </select>

                <label style="color: var(--text-muted); font-size: 13px;">Data cílení:</label>
                <input type="text" name="target_data" id="em_data">

                <label style="color: var(--text-muted); font-size: 13px;">Odkaz tlačítka (prázdné = bez tlačítka):</label>
                <input type="url" name="link_url" id="em_url">

                <label style="color: var(--text-muted); font-size: 13px;">Expirace:</label>
                <input type="text" name="expires_at" id="em_exp">

                <div style="background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin: 15px 0;">
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: var(--text-main); font-size: 13px;">
                        <input type="checkbox" name="repeat" id="em_repeat" style="width: auto; margin: 0;">
                        Zobrazovat uživatelům DOKOLA
                    </label>
                </div>
                
                <button type="submit" class="btn btn-warning" style="width: 100%; margin-top: 15px;"><i class="fas fa-save"></i> Uložit změny</button>
            </form>
            <button type="button" class="btn" style="width: 100%; margin-top: 10px; background: transparent; border: 1px solid #334155; color: var(--text-muted);" onclick="document.getElementById('editMessageModal').style.display='none'">Zrušit</button>
        </div>
    </div>
</div>

<script>
    function toggleTargetData() {
        const type = document.getElementById('target_type').value;
        const container = document.getElementById('target_data_container');
        const input = document.getElementById('target_data');
        const label = document.getElementById('target_label');
        
        if (type === 'GLOBAL') {
            container.style.display = 'none';
            input.removeAttribute('required');
        } else {
            container.style.display = 'block';
            input.setAttribute('required', 'true');
            if (type === 'ROLE') {
                label.innerText = 'Zadej role oddělené čárkou (např. BT, DEV, SA):';
                input.placeholder = 'BT, DEV';
            } else if (type === 'USERS') {
                label.innerText = 'Zadej Herní ID, Discord ID nebo Nick (oddělené čárkou):';
                input.placeholder = '1001, marekk_czz, 1234567890';
            }
        }
    }
    
    function toggleLinkUrl() {
        const hasLink = document.getElementById('has_link').checked;
        const container = document.getElementById('link_url_container');
        if (hasLink) {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }

    function openEditMessageModal(btn) {
        try {
            document.getElementById('em_id').value = btn.getAttribute('data-id') || "";
            document.getElementById('em_title').value = btn.getAttribute('data-title') || "";
            document.getElementById('em_content').value = btn.getAttribute('data-content') || "";
            document.getElementById('em_type').value = btn.getAttribute('data-type') || "GLOBAL";
            document.getElementById('em_data').value = btn.getAttribute('data-data') || "";
            document.getElementById('em_url').value = btn.getAttribute('data-url') || "";
            document.getElementById('em_exp').value = btn.getAttribute('data-exp') || "";
            document.getElementById('em_repeat').checked = btn.getAttribute('data-repeat') === 'true';
            document.getElementById('editMessageModal').style.display = 'flex';
            
            document.getElementById('target_type').value = btn.getAttribute('data-type') || "GLOBAL";
            toggleTargetData();
        } catch(e) {
            alert("Chyba při otevírání okna: " + e.message);
        }
    }
</script>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-code-branch" style="color:var(--blue-main);"></i> Manažer Verzí a Přístupů</h2>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Vydat novou verzi</h3>
        <p style="color: var(--warning); font-size: 12px; margin-top: -5px;">Po přidání se ihned objeví ke stažení na webu i Discordu.</p>
        <form action="/dashboard/add_version" method="POST">
            <input type="text" name="version_name" placeholder="Zobrazený Název (např. Jarní Update 1.5)" required>
            <input type="text" name="db_version" placeholder="Verze Databáze (Přesně z logic-ovladac.js!)" required>
            <input type="text" name="file_url" placeholder="Odkaz(y) na stažení (více odkazů oddělte čárkou)" required>
            
            <label style="color: var(--text-muted); font-size: 13px;">Pro jakou roli je tato verze určena?</label>
            <select name="target_role" required>
                <option value="User">User (Uvidí všichni - Normální verze)</option>
                <option value="BT">BETA TESTER (Uvidí BT, DEV, SA - Testovací verze)</option>
                <option value="DEV_SA">DEV / SERVER ADMIN (Neveřejná verze)</option>
            </select>
            
            <button type="submit" class="btn" style="width: 100%;">Přidat verzi</button>
        </form>
    </div>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">📦 Tabulka vydaných verzí softwaru</h3>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>Název (Zobrazený)</th>
                <th>Verze pro DB (Přihlášení)</th>
                <th>Stav Podpory</th>
                <th>Cílová Skupina</th>
                <th>Akce</th>
            </tr>
            {% for v in versions %}
            {% set is_active = (v.get('is_active', True) | string | lower) != 'false' %}
            <tr style="opacity: {{ '1' if is_active else '0.5' }};">
                <td><strong>{{ v.get('version_name', '') }}</strong></td>
                <td style="color: var(--warning); font-family: monospace;">{{ v.get('db_version', '') }}</td>
                <td>
                    {% if is_active %}
                        <span class="role-tag" style="background-color: var(--success); color: white;">Aktivní</span>
                    {% else %}
                        <span class="role-tag" style="background-color: var(--danger); color: white;">Zablokováno (Konec)</span>
                    {% endif %}
                    <br>
                    <span style="font-size: 11px; color: var(--text-muted);">Konec: {{ v.get('eol_date', '') or 'Nikdy' }}</span>
                </td>
                <td>
                    {% if v.get('target_role') == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User (Všichni)</span>{% endif %}
                    {% if v.get('target_role') == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BETA TESTER+</span>{% endif %}
                    {% if v.get('target_role') == 'DEV_SA' %}<span class="role-tag" style="background-color: #ef4444; color: white;">DEV / SA</span>{% endif %}
                </td>
                <td>
                    <button type="button" class="btn btn-warning" style="padding: 5px 10px; font-size: 12px;" 
                        data-id="{{ v.get('id', '') }}"
                        data-name="{{ (v.get('version_name') or '') | e }}"
                        data-db="{{ (v.get('db_version') or '') | e }}"
                        data-url="{{ (v.get('file_url') or '') | e }}"
                        data-role="{{ (v.get('target_role') or '') | e }}"
                        data-active="{{ 'true' if is_active else 'false' }}"
                        data-eol="{{ (v.get('eol_date') or '') | e }}"
                        onclick="openEditVerModal(this)"><i class="fas fa-edit"></i> Úprava</button>
                    <form action="/dashboard/delete_version" method="POST" style="display:inline;">
                        <input type="hidden" name="version_id" value="{{ v.get('id', '') }}">
                        <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Odebrat tuto verzi z databáze?')"><i class="fas fa-trash"></i> Smazat</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Zatím nebyly přidány žádné verze.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="modal-overlay" id="editVerModal">
    <div class="modal">
        <div style="width: 100%;">
            <h2 style="color: var(--warning); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                <i class="fas fa-edit"></i> Řízení Verze
            </h2>
            <form action="/dashboard/edit_version" method="POST">
                <input type="hidden" name="version_id" id="ev_id">
                
                <label style="color: var(--text-muted); font-size: 13px;">Název Verze (Zobrazený):</label>
                <input type="text" name="version_name" id="ev_name" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">Verze Databáze (Z logic-ovladac.js):</label>
                <input type="text" name="db_version" id="ev_db" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">URL odkazu (více odkazů oddělte čárkou):</label>
                <input type="text" name="file_url" id="ev_url" required>
                
                <label style="color: var(--text-muted); font-size: 13px;">Pro jakou minimální roli?</label>
                <select name="target_role" id="ev_role" required>
                    <option value="User">User (Všichni)</option>
                    <option value="BT">BETA TESTER (Testovací)</option>
                    <option value="DEV_SA">DEV / SERVER ADMIN (Neveřejné)</option>
                </select>

                <div style="background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin: 15px 0;">
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: var(--text-main); font-size: 13px;">
                        <input type="checkbox" name="is_active" id="ev_active" style="width: auto; margin: 0;">
                        <b>Tato verze je aktivní (Povolit přihlášení do Palubáku)</b>
                    </label>
                    <span style="font-size: 11px; color: #ef4444; margin-left: 23px; display: block; margin-top: 5px;">Pokud toto odškrtneš, každý, kdo má tuto verzi staženou, dostane při pokusu o přihlášení banovací hlášku s odkazem na stažení nové verze.</span>
                </div>

                <label style="color: var(--text-muted); font-size: 13px;">Konec podpory (Datum, kdy se automaticky verze uzamkne - Volitelné):</label>
                <input type="text" name="eol_date" id="ev_eol" placeholder="Např. 31.12.2026">
                
                <button type="submit" class="btn btn-warning" style="width: 100%; margin-top: 15px;">Uložit změny</button>
            </form>
            <button type="button" class="btn" style="width: 100%; margin-top: 10px; background: transparent; border: 1px solid #334155; color: var(--text-muted);" onclick="document.getElementById('editVerModal').style.display='none'">Zrušit</button>
        </div>
    </div>
</div>
<script>
    function openEditVerModal(btn) {
        try {
            document.getElementById('ev_id').value = btn.getAttribute('data-id') || "";
            document.getElementById('ev_name').value = btn.getAttribute('data-name') || "";
            document.getElementById('ev_db').value = btn.getAttribute('data-db') || "";
            document.getElementById('ev_url').value = btn.getAttribute('data-url') || "";
            document.getElementById('ev_role').value = btn.getAttribute('data-role') || "User";
            document.getElementById('ev_active').checked = btn.getAttribute('data-active') === 'true';
            document.getElementById('ev_eol').value = btn.getAttribute('data-eol') || "";
            document.getElementById('editVerModal').style.display = 'flex';
        } catch(e) {
            alert("Chyba při otevírání: " + e.message);
        }
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
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-id-badge" style="color:var(--blue-main);"></i> Správa Aplikačních ID</h2>
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
                <td style="font-weight: bold; color: var(--blue-main); font-size: 16px;">#{{ user.get('app_id', '') }}</td>
                <td><strong>{{ user.get('nick', '') }}</strong></td>
                <td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td>
                <td>
                    {% if user.get('is_deleted') %}
                        <span style="color: var(--danger); font-size: 12px; font-weight: bold;">Smazán (Blokuje ID)</span>
                    {% else %}
                        <span style="color: var(--success); font-size: 12px; font-weight: bold;">Aktivní</span>
                    {% endif %}
                </td>
                <td style="display: flex; gap: 10px; align-items: center;">
                    <form action="/dashboard/change_id" method="POST" style="display: flex; gap: 10px; margin: 0; width: 100%;">
                        <input type="hidden" name="discord_id" value="{{ user.get('discord_id', '') }}">
                        <input type="number" name="new_app_id" placeholder="Nové ID" required style="width: 100px; margin: 0; text-align: center; font-weight: bold;">
                        <button type="submit" class="btn btn-warning" style="padding: 8px 15px; font-size: 12px;"><i class="fas fa-edit"></i> Změnit ID</button>
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

HTML_WAIT_AUTH = """
<div style="text-align: center; margin-top: 100px;">
    <h2 style="color: var(--blue-main);"><i class="fas fa-shield-alt"></i> Čekání na ověření...</h2>
    <p style="color: var(--text-muted);">Byla vám zaslána zpráva na Discord (uživateli s ID {{ discord_id }}). Prosím, potvrďte přihlášení kliknutím na tlačítko ve zprávě.</p>
    <div class="spinner" style="margin: 30px auto; width: 50px; height: 50px; border: 5px solid rgba(56, 189, 248, 0.2); border-top-color: var(--blue-main); border-radius: 50%; animation: spin 1s linear infinite;"></div>
    <p id="status-text" style="color: var(--warning); font-weight: bold;">Čekám na vaši akci...</p>
</div>
<style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
<script>
    setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}')
        .then(r => r.json())
        .then(d => {
            if (d.status === 'approved') window.location.href = '/dashboard/login_finalize?discord_id={{ discord_id }}';
            else if (d.status === 'rejected') {
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
    <p style="color: var(--text-muted); margin-bottom: 30px; font-size: 14px;">Zadejte své Discord ID pro přihlášení. Systém vám zašle ověřovací zprávu.</p>
    <form action="/login_request" method="POST">
        <input type="text" name="discord_id" placeholder="Vaše Discord ID (např. 1234567890)" required style="text-align: center; font-size: 16px; letter-spacing: 1px;">
        <button type="submit" class="btn" style="width: 100%; font-size: 16px; margin-top: 10px;"><i class="fas fa-sign-in-alt"></i> Přihlásit se</button>
    </form>
</div>
"""
