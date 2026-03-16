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
        <img src="{{ logo_male }}" alt="Logo" style="height: 30px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 8px rgba(56, 189, 248, 0.6));">
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
                <img src="{{ logo_male }}" alt="Logo" style="height: 24px; width: auto; border-radius: 4px; filter: drop-shadow(0px 0px 6px rgba(56, 189, 248, 0.6));">
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

HTML_FEEDBACK = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-comments" style="color:#a855f7;"></i> Zpětná vazba a Žádosti</h2>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning); margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;">Nové žádosti o HWID Reset</h3>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>Uživatel (ID)</th>
                <th>Důvod (Zpráva)</th>
                <th>Datum</th>
                <th>Akce</th>
            </tr>
            {% for f in hwid_pending %}
            <tr>
                <td style="color:white; font-weight:bold;">{{ f.get('nick', 'Neznámý') }} <br><span style="font-size:11px; color:#aaa; font-weight:normal;">{{ f.get('discord_id', '') }}</span></td>
                <td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td>
                <td style="color:#aaa; font-size:12px;">{{ f.get('created_at', '') }}</td>
                <td style="display:flex; gap:5px;">
                    <form action="/dashboard/feedback_reset_hwid" method="POST" style="margin:0;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <input type="hidden" name="discord_id" value="{{ f.get('discord_id', '') }}">
                        <button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;" title="Schválit a Resetovat HWID"><i class="fas fa-check"></i> Resetovat</button>
                    </form>
                    <button type="button" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" title="Zamítnout žádost" onclick="rejectHwid('{{ f.get('id', '') }}', '{{ f.get('nick', '') | replace("'", "\\'") }}')"><i class="fas fa-times"></i> Zamítnout</button>
                    <form id="form_hwid_reject_{{ f.get('id', '') }}" action="/dashboard/feedback_reject" method="POST" style="display:none;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <input type="hidden" name="discord_id" value="{{ f.get('discord_id', '') }}">
                        <input type="hidden" name="reason" id="reject_reason_{{ f.get('id', '') }}">
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Zatím žádné žádosti o HWID reset.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); margin-bottom: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">Nové zprávy od uživatelů (Všeobecné)</h3>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>Uživatel (ID)</th>
                <th>Zpráva / Nápad / Chyba</th>
                <th>Datum</th>
                <th>Akce</th>
            </tr>
            {% for f in general_pending %}
            <tr>
                <td style="color:white; font-weight:bold;">{{ f.get('nick', 'Neznámý') }} <br><span style="font-size:11px; color:#aaa; font-weight:normal;">{{ f.get('discord_id', '') }}</span></td>
                <td style="color:#ddd; font-style:italic;">{{ f.get('message', '') }}</td>
                <td style="color:#aaa; font-size:12px;">{{ f.get('created_at', '') }}</td>
                <td style="display:flex; gap:5px;">
                    <button type="button" class="btn btn-dark" style="padding: 5px 10px; font-size: 12px;" onclick="replyGeneral('{{ f.get('id', '') }}', '{{ f.get('nick', '') | replace("'", "\\'") }}', '{{ f.get('discord_id', '') }}')"><i class="fas fa-reply"></i> Odpovědět</button>
                    <form id="form_general_reply_{{ f.get('id', '') }}" action="/dashboard/feedback_reply" method="POST" style="display:none;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <input type="hidden" name="discord_id" value="{{ f.get('discord_id', '') }}">
                        <input type="hidden" name="message" id="reply_msg_{{ f.get('id', '') }}">
                    </form>
                    
                    <form action="/dashboard/feedback_resolve" method="POST" style="margin:0;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check-circle"></i> Vyřešeno</button>
                    </form>
                    
                    <form action="/dashboard/feedback_delete" method="POST" style="margin:0;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i> Smazat</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Zatím žádná nová zpětná vazba.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <h3 style="color: var(--success); margin-top: 0;">Vyřešeno / Uzavřeno</h3>
    <div style="overflow-x: auto;">
        <table>
            <tr>
                <th>Uživatel</th>
                <th>Typ</th>
                <th>Zpráva uživatele</th>
                <th>Vaše odpověď / Status</th>
                <th>Akce</th>
            </tr>
            {% for f in resolved_all %}
            <tr style="opacity: 0.7;">
                <td style="color:white; font-weight:bold;">{{ f.get('nick', '') }}</td>
                <td>{{ 'HWID Reset' if f.get('type') == 'HWID' else 'Zpětná vazba' }}</td>
                <td style="color:#aaa; font-style:italic;">{{ f.get('message', '') }}</td>
                <td style="color:var(--success); font-weight:bold;">{{ f.get('sys_note', 'Vyřešeno') }}</td>
                <td>
                    <form action="/dashboard/feedback_delete" method="POST" style="margin:0;">
                        <input type="hidden" name="feedback_id" value="{{ f.get('id', '') }}">
                        <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i></button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Žádné uzavřené tickety.</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<script>
    function rejectHwid(id, nick) {
        let reason = prompt("Zadejte důvod zamítnutí pro hráče " + nick + ":", "Reset HWID nyní není možný.");
        if (reason) {
            document.getElementById('reject_reason_' + id).value = reason;
            document.getElementById('form_hwid_reject_' + id).submit();
        }
    }
    function replyGeneral(id, nick, dId) {
        let msg = prompt("Napište zprávu pro hráče " + nick + " (Přijde mu to do DM):");
        if (msg) {
            document.getElementById('reply_msg_' + id).value = msg;
            document.getElementById('form_general_reply_' + id).submit();
        }
    }
</script>
"""
