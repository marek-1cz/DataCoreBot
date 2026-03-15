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
        .btn-warning { background-color: var(--warning); color: #000; }
        .btn-success { background-color: var(--success); color: #fff;}
        .btn-dark { background-color: #334155; color: white; }
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
        .sidebar-link:hover { background-color: rgba(56, 189, 248, 0.1); color: var(--blue-main); border-left-color: var(--blue-main); }
        .dashboard-content { flex-grow: 1; padding: 30px; background-color: var(--bg-dark); overflow-y: auto; }
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
        .alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .alert-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    </style>
</head>
<body>
    {% block layout %}{% endblock %}
</body>
</html>
"""

PUBLIC_LAYOUT = """
<nav class="top-nav">
    <a href="/" class="logo"><img src="{{ logo_male }}" alt="Logo" style="height: 30px; border-radius: 4px;"> OIS IDPK</a>
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
            {% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
"""

DASHBOARD_LAYOUT = """
<div class="dashboard-wrapper">
    <div class="sidebar">
        <div class="sidebar-header">
            <a href="/" class="logo" style="font-size: 20px; justify-content: center;"><img src="{{ logo_male }}" style="height: 24px;"> OIS IDPK</a>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Dashboard</div>
        </div>
        <div class="sidebar-menu">
            <a href="/dashboard" class="sidebar-link"><i class="fas fa-home" style="width:25px;"></i> Přehled</a>
            <a href="/dashboard/stats" class="sidebar-link"><i class="fas fa-chart-bar" style="width:25px;"></i> Statistiky</a>
            <a href="/dashboard/app_settings" class="sidebar-link"><i class="fas fa-cog" style="width:25px;"></i> Aplikace</a>
            <a href="/dashboard/downloads" class="sidebar-link"><i class="fas fa-cloud-download-alt" style="width:25px;"></i> Stahování</a>
            <a href="/dashboard/pending_roles" class="sidebar-link" style="color: #10b981;"><i class="fas fa-ticket-alt" style="width:25px;"></i> Rezervace</a>
            <a href="/dashboard/ids" class="sidebar-link"><i class="fas fa-id-badge" style="width:25px;"></i> Správa ID</a>
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus" style="width:25px;"></i> Tým</a>
            <a href="/dashboard/supporters" class="sidebar-link" style="color: var(--blue-main); text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);"><i class="fas fa-star" style="width:25px;"></i> Podporovatelé</a>
            <a href="/dashboard?filter=banned" class="sidebar-link" style="color: var(--warning);"><i class="fas fa-ban" style="width:25px;"></i> BANy</a>
            <a href="/dashboard?filter=deleted" class="sidebar-link" style="color: var(--danger);"><i class="fas fa-trash-alt" style="width:25px;"></i> Smazaní</a>
        </div>
        <div style="padding: 20px;">
            <div style="font-size: 11px; color: var(--text-muted); text-align: center; margin-bottom: 15px; border-top: 1px solid #334155; padding-top: 15px;">Update:<br><b>{{ deploy_time }}</b></div>
            <a href="/logout" class="btn btn-danger" style="width: 100%; text-align: center;"><i class="fas fa-sign-out-alt"></i> Odhlásit</a>
        </div>
    </div>
    <div class="dashboard-content">
        {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}
        {% block content %}{% endblock %}
    </div>
</div>

<div class="modal-overlay" id="editModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(5px);z-index:1000;align-items:center;justify-content:center;">
    <div class="modal" style="background:var(--bg-panel);padding:30px;border-radius:15px;width:700px;border-top:5px solid var(--blue-main);max-height:90vh;overflow-y:auto;">
        <h2 style="color: var(--blue-main); margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between;">
            <span><i class="fas fa-user"></i> Profil <span id="modalAppId" style="color: var(--text-muted);"></span></span>
            <span id="modalStatusDot" style="font-size: 14px;"></span>
        </h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
            <div style="background:#0f172a;padding:15px;border-radius:8px;border:1px solid #334155;">
                <div style="font-size:12px;color:var(--text-muted);">Členem Discordu od:</div><div style="font-weight:bold;" id="profJoined"><i class="fas fa-spinner fa-spin"></i></div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:10px;">Aktivita v aplikaci:</div><div style="font-weight:bold;" id="profAppStatus"></div>
                <div id="profStats"></div>
            </div>
            <div style="background:#0f172a;padding:15px;border-radius:8px;border:1px solid #334155;max-height:250px;overflow-y:auto;">
                <div style="font-weight:bold;color:var(--blue-main);margin-bottom:10px;">Historie stahování:</div>
                <table style="width:100%;margin:0;background:transparent;"><tbody id="profDownloads"><tr><td colspan="2" style="text-align:center;"><i class="fas fa-spinner fa-spin"></i></td></tr></tbody></table>
            </div>
        </div>
        <form action="/dashboard/edit_user" method="POST" style="border-top: 1px solid #334155; padding-top: 15px;">
            <input type="hidden" name="discord_id" id="modalDiscordId">
            <label>Herní Nick:</label> <input type="text" name="nick" id="modalNick" required>
            <label>Role:</label>
            <div style="display:flex;gap:15px;margin-bottom:15px;">
                <label style="color:#ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label>
                <label style="color:#10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label>
                <label style="color:#3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label>
                <label style="color:#94a3b8;"><input type="checkbox" name="roles" value="User"> User</label>
            </div>
            <label>HWID (Zámek na PC):</label> <input type="text" name="hwid" id="modalHwid">
            <div style="background:rgba(56,189,248,0.1);padding:10px;border-radius:5px;border:1px solid var(--blue-main);margin-bottom:15px;">
                <label style="cursor:pointer;font-weight:bold;color:var(--blue-main);display:flex;align-items:center;gap:10px;"><input type="checkbox" name="dashboard_access" id="modalDashboardAccess" value="True" style="width:auto;margin:0;"> Povolit přístup do Dashboardu</label>
            </div>
            <div id="activeActions">
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button type="submit" name="action" value="save" class="btn" style="flex: 2;">Uložit úpravy</button>
                    <button type="submit" name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;">Dát BAN</button>
                    <button type="submit" name="action" value="unban" id="btnUnban" class="btn btn-success" style="flex: 1; display: none;">Un-BAN</button>
                </div>
                <div style="margin-top: 15px;"><button type="submit" name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Smazat účet?')">Smazat účet (Soft)</button></div>
            </div>
            <div id="deletedActions" style="display: none; margin-top: 20px;">
                <p style="color: var(--danger); font-weight: bold; text-align: center;">Tento účet je smazaný.</p>
                <div style="display: flex; gap: 10px;">
                    <button type="submit" name="action" value="restore" class="btn btn-success" style="flex: 1;">Obnovit účet</button>
                    <button type="submit" name="action" value="hard_delete" class="btn btn-dark" style="flex: 1;" onclick="return confirm('Trvale smazat?')">Smazat permanentně</button>
                </div>
            </div>
        </form>
        <button class="btn" onclick="document.getElementById('editModal').style.display='none'" style="background:transparent;color:var(--text-muted);border:1px solid #334155;width:100%;margin-top:10px;">Zrušit</button>
    </div>
</div>
<script>
    function openModal(app_id, discord_id, nick, roles, hwid, is_banned, is_deleted, dashboard_access) {
        document.getElementById('editModal').style.display = 'flex';
        document.getElementById('modalAppId').innerText = "#" + app_id;
        document.getElementById('modalDiscordId').value = discord_id;
        document.getElementById('modalNick').value = nick;
        document.getElementById('modalHwid').value = hwid === 'None' ? '' : hwid;
        document.getElementById('modalDashboardAccess').checked = (dashboard_access === 'True');
        document.querySelectorAll('input[name="roles"]').forEach(cb => cb.checked = false);
        roles.split(',').forEach(r => { let el = document.querySelector(`input[name="roles"][value="${r.trim()}"]`); if(el) el.checked = true; });
        if (is_deleted === 'True') { document.getElementById('activeActions').style.display = 'none'; document.getElementById('deletedActions').style.display = 'block'; } 
        else { 
            document.getElementById('activeActions').style.display = 'block'; document.getElementById('deletedActions').style.display = 'none'; 
            if (is_banned === 'True') { document.getElementById('btnBan').style.display = 'none'; document.getElementById('btnUnban').style.display = 'block'; } 
            else { document.getElementById('btnBan').style.display = 'block'; document.getElementById('btnUnban').style.display = 'none'; }
        }
        fetch('/api/get_profile_data/' + discord_id).then(r => r.json()).then(data => {
            document.getElementById('profJoined').innerText = data.joined_at;
            document.getElementById('modalStatusDot').innerHTML = data.status;
            document.getElementById('profAppStatus').innerHTML = data.app_status;
            document.getElementById('profStats').innerHTML = data.stats;
            let dlHtml = "";
            if(data.downloads && data.downloads.length > 0) { data.downloads.forEach(d => { dlHtml += `<tr><td style="color:var(--blue-main);font-size:12px;"><b>${d.version_name}</b></td><td style="color:var(--text-muted);font-size:12px;">${d.downloaded_at}</td></tr>`; }); } 
            else { dlHtml = "<tr><td colspan='2' style='color:var(--text-muted);font-size:12px;'>Zatím nic nestáhl.</td></tr>"; }
            document.getElementById('profDownloads').innerHTML = dlHtml;
        });
    }
</script>
"""

HTML_HOME = """
<div style="text-align: center; padding: 60px 20px; max-width: 800px; margin: 0 auto;">
    <h1 style="color: var(--blue-main); font-size: 2.5em; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);">OFICIÁLNÍ STRÁNKA PROJEKTU OIS IDPK</h1>
    <div style="font-size: 1.1em; color: var(--text-main); line-height: 1.6; margin-bottom: 40px; background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 10px; border-left: 4px solid var(--blue-main); text-align: left;">
        <p style="margin-top:0;">Projekt OIS IDPK je fanouškovský software inspirovaný skutečnými vnitřními informačními panely, které se používají v autobusech Plzeňského kraje.</p>
        <p>Software simuluje zobrazování zastávek, průběh celé linky i další informace, které běžně vidí cestující během jízdy.</p>
        <p style="margin-bottom:0;">Jedná se čistě o fanouškovský projekt vytvořený pro zábavu, experimentování a zájem o dopravní technologie. Projekt nespolupracuje s dopravci.</p>
    </div>
    <a href="/download" class="btn" style="font-size: 18px; padding: 15px 40px; border-radius: 30px; box-shadow: 0 5px 15px rgba(56, 189, 248, 0.4);"><i class="fas fa-download"></i> Získat Software</a>
    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 60px 0;">
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; background: var(--bg-panel); padding: 40px; border-radius: 15px; border: 1px solid #334155;">
        <img src="{{ logo_velke }}" alt="DataCoreBot Logo" style="max-width: 250px; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.5)); margin-bottom: 10px;">
        <div style="text-align: center; max-width: 600px;">
            <h3 style="color: var(--warning); margin-top: 0; font-size: 1.6em; text-shadow: 0 0 5px rgba(245, 158, 11, 0.5);">Poháněno systémem DataCoreBot</h3>
            <p style="color: var(--text-muted); line-height: 1.6; margin: 0 0 15px 0;">Celá infrastruktura je bezpečně řízena a chráněna systémem DataCoreBot. Zajišťuje HWID ochranu a běh projektu.</p>
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
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-chart-line" style="color:var(--blue-main);"></i> Statistiky Webu</h2>
</div>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--blue-main); text-align: center;">
        <h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0;">Unikátní zobrazení (Celkem)</h3>
        <div style="font-size: 40px; font-weight: 900; color: var(--text-main);">{{ total_visits }}</div>
    </div>
    <div style="background: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--success); text-align: center;">
        <h3 style="color: var(--text-muted); font-size: 14px; margin-top: 0;">Zobrazení za 7 dní</h3>
        <div style="font-size: 40px; font-weight: 900; color: var(--success);">{{ last_7_days }}</div>
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;"><i class="fas fa-globe"></i> Státy (Souhrn)</h3>
    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
        {% for cc, data in country_totals.items() %}
        <div style="background: rgba(0,0,0,0.3); border: 1px solid #334155; padding: 10px 20px; border-radius: 8px; display: flex; align-items: center; gap: 10px;">
            <img src="{{ data.flag }}" alt="" style="border-radius: 3px; box-shadow: 0 0 5px rgba(0,0,0,0.5);">
            <span style="color: var(--text-main); font-weight: bold;">{{ data.name }}</span>
            <span style="background: var(--blue-main); color: #000; padding: 2px 8px; border-radius: 12px; font-weight: 900; font-size: 12px;">{{ data.count }}</span>
        </div>
        {% else %} <div style="color: var(--text-muted);">Zatím žádná data.</div> {% endfor %}
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <h3 style="color: var(--blue-main); margin-top: 0;"><i class="fas fa-map-marker-alt"></i> Detailní přehled regionů</h3>
    <table style="width: 100%;"><tr><th>Region</th><th>Počet zobrazení</th></tr>
        {% for c_name, data in region_totals.items() %}
        <tr><td style="font-weight: bold; color: var(--text-main); display: flex; align-items: center; gap: 10px;">{% if data.flag %}<img src="{{ data.flag }}" style="border-radius: 3px;">{% endif %} {{ c_name }}</td><td style="color: var(--blue-main); font-weight: bold; font-size: 16px;">{{ data.count }}</td></tr>
        {% endfor %}
    </table>
</div>
"""

HTML_TEAM = """
<h2 style="color: var(--blue-main); border-bottom: 2px solid #334155; padding-bottom: 10px; text-align:center;">Náš Tým</h2>
<div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 20px;">
    {% for member in team %}
    <div style="background-color: var(--bg-panel); border-radius: 10px; padding: 20px; text-align: center; border-top: 4px solid var(--blue-main); width: 300px; transition: 0.3s;">
        <img src="{{ member.get('image_url', '') }}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 15px; border: 3px solid #334155;" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <h3 style="font-size: 20px; font-weight: bold; margin: 0 0 5px 0;">{{ member.get('name', '') }}</h3>
        <div style="color: var(--blue-main); font-size: 14px; margin-bottom: 15px;">@{{ member.get('discord_nick', '') }}</div>
        <p style="color: var(--text-muted); font-size: 14px; line-height: 1.5; margin-bottom: 15px;">{{ member.get('description', '') }}</p>
        <div>
            {% set roles_input = member.get('role_name', '').split(',') if member.get('role_name') else [] %}
            {% for r in roles_input %}
                {% set parts = r.split('|') %}{% set r_name = parts[0].strip() %}{% set r_color = parts[1].strip() if parts|length > 1 else '#38bdf8' %}
                <span class="role-tag" style="background-color: {{ r_color }}33; color: {{ r_color }}; border: 1px solid {{ r_color }};">{{ r_name }}</span>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</div>
"""

HTML_DOWNLOADS_MAIN = """
<div style="text-align: center; padding: 60px 20px; max-width: 700px; margin: 50px auto; background-color: var(--bg-panel); border-radius: 15px; box-shadow: 0 15px 30px rgba(0,0,0,0.5); border-top: 5px solid #5865F2;">
    <h2 style="color: var(--text-main); font-size: 2.2em; margin-top: 0;"><i class="fas fa-shield-alt" style="color: var(--blue-main);"></i> Oficiální distribuce softwaru</h2>
    <p style="color: var(--text-muted); font-size: 1.1em; line-height: 1.6; margin-bottom: 20px;">Z důvodu ochrany projektu jsme se rozhodli přesunout distribuci na náš Discord. Díky tomu máme větší kontrolu.</p>
    <div style="background-color: rgba(88, 101, 242, 0.1); border: 1px solid #5865F2; padding: 30px 20px; border-radius: 10px; margin: 30px 20px;">
        <p style="color: var(--text-main); font-weight: bold; font-size: 1.2em; margin-top: 0;">Jak získat software:</p>
        <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Připojte se na náš Discord a přejděte do kanálu <b>💾・download</b>.</p>
        <a href="https://discord.gg/vmTagbC9mF" target="_blank"><i class="fab fa-discord" style="font-size: 120px; color: #5865F2; filter: drop-shadow(0px 10px 15px rgba(88,101,242,0.4));"></i></a>
    </div>
</div>
"""

HTML_LOGIN = """
<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-top: 4px solid var(--blue-main);">
    <h2 style="text-align: center; color: var(--blue-main); margin-top: 0;"><i class="fas fa-lock"></i> Dashboard 2FA</h2>
    <div style="background-color: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--danger); padding: 12px; margin-bottom: 20px;">
        <p style="color: var(--danger); margin: 0; font-size: 13px; font-weight: 800;">Zabezpečená zóna</p>
        <p style="color: var(--text-muted); margin: 5px 0 0 0; font-size: 12px;">Vyhrazena <b>pouze pro administrátory</b>.</p>
    </div>
    <form method="POST" action="/login_request">
        <label style="font-weight: bold; font-size: 12px; color: var(--text-muted);">VAŠE DISCORD ID</label>
        <input type="text" name="discord_id" required>
        <button type="submit" class="btn" style="width: 100%; margin-top: 10px;">Odeslat žádost</button>
    </form>
</div>
"""

HTML_WAIT_AUTH = """
<div style="max-width: 500px; margin: 50px auto; background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; border-top: 4px solid var(--warning);">
    <h2 style="color: var(--warning); margin-top: 0;"><i class="fas fa-spinner fa-spin"></i> Čekání na ověření</h2>
    <p style="color: var(--text-main); font-size: 16px;">Byla Vám odeslána zpráva na Discord.</p>
</div>
<script>
    setInterval(() => {
        fetch('/api/check_auth/{{ discord_id }}').then(r => r.json()).then(data => {
            if(data.status === 'approved') { window.location.href = '/dashboard/login_finalize?discord_id={{ discord_id }}'; } 
            else if(data.status === 'rejected') { window.location.href = '/dashboard'; }
        });
    }, 2000);
</script>
"""

HTML_APP_SETTINGS = """
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if soft_enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);">Status Softwaru (Kill-Switch)</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if soft_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if soft_enabled else 'fa-ban' }}"></i></div>
        <form action="/dashboard/toggle_software" method="POST"><input type="hidden" name="new_status" value="{{ 'False' if soft_enabled else 'True' }}"><button type="submit" class="btn {{ 'btn-danger' if soft_enabled else 'btn-success' }}" style="width: 100%;">Přepnout Globální Stav Softwaru</button></form>
    </div>
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if dl_enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);">Status Stahování na Discordu</h3>
        <div style="font-size: 50px; margin: 15px 0; color: {{ 'var(--success)' if dl_enabled else 'var(--danger)' }};"><i class="fas {{ 'fa-check-circle' if dl_enabled else 'fa-ban' }}"></i></div>
        <form action="/dashboard/toggle_downloads" method="POST"><input type="hidden" name="new_status" value="{{ 'False' if dl_enabled else 'True' }}"><input type="hidden" name="return_to" value="app_settings"><button type="submit" class="btn {{ 'btn-danger' if dl_enabled else 'btn-success' }}" style="width: 100%;">Přepnout Stahování</button></form>
    </div>
</div>
"""

HTML_DOWNLOADS_MGMT = """
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid {{ 'var(--success)' if enabled else 'var(--danger)' }}; text-align: center;">
        <h3 style="margin-top: 0; color: var(--text-main);">Hlavní vypínač instalací</h3>
        <form action="/dashboard/toggle_downloads" method="POST"><input type="hidden" name="new_status" value="{{ 'False' if enabled else 'True' }}"><input type="hidden" name="return_to" value="downloads"><button type="submit" class="btn {{ 'btn-danger' if enabled else 'btn-success' }}" style="width: 100%;">Přepnout Vypínač</button></form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat Verzi Softwaru</h3>
        <form action="/dashboard/add_version" method="POST"><input type="text" name="version_name" placeholder="Název" required><input type="url" name="file_url" placeholder="Přímý odkaz na stažení" required>
            <select name="target_role" required><option value="User">User (Všichni)</option><option value="BT">BETA TESTER</option><option value="DEV_SA">DEV / SERVER ADMIN</option></select>
            <button type="submit" class="btn" style="width: 100%;">Přidat verzi</button>
        </form>
    </div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">📦 Dostupné soubory</h3>
    <table style="width: 100%;"><tr><th>Název</th><th>Cílová Skupina</th><th>Odkaz</th><th>Akce</th></tr>
        {% for v in versions %}
        <tr>
            <td><strong>{{ v.get('version_name', '') }}</strong></td><td>{{ v.get('target_role', '') }}</td>
            <td><a href="{{ v.get('file_url', '') }}" target="_blank" style="color: var(--blue-main);">Odkaz</a></td>
            <td><form action="/dashboard/delete_version" method="POST"><input type="hidden" name="version_id" value="{{ v.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px;"><i class="fas fa-trash"></i> Smazat</button></form></td>
        </tr>
        {% endfor %}
    </table>
</div>
"""

HTML_PENDING_ROLES = """
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Předpřipravit Roli</h3>
        <form action="/dashboard/add_pending_role" method="POST">
            <input type="text" name="discord_identifier" placeholder="Discord Nick nebo ID" required>
            <div class="checkbox-group"><label style="color: #ef4444;"><input type="checkbox" name="roles" value="SA"> SA</label><label style="color: #10b981;"><input type="checkbox" name="roles" value="DEV"> DEV</label><label style="color: #3b82f6;"><input type="checkbox" name="roles" value="BT"> BT</label><label style="color: #94a3b8;"><input type="checkbox" name="roles" value="User"> User</label></div>
            <button type="submit" class="btn" style="width: 100%;">Vytvořit Rezervaci</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">⏳ Čekající rezervace</h3>
        <table style="width: 100%;"><tr><th>Discord Identifikátor</th><th>Rezervovaná Role</th><th>Akce</th></tr>
            {% for p in pending %}<tr><td><strong>{{ p.get('discord_identifier', '') }}</strong></td><td>{{ p.get('roles', '') }}</td><td><form action="/dashboard/delete_pending_role" method="POST"><input type="hidden" name="pending_id" value="{{ p.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px;"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}
        </table>
    </div>
</div>
"""

HTML_TEAM_ADD = """
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat člena týmu</h3>
        <form action="/dashboard/add_team" method="POST">
            <input type="text" name="name" placeholder="Jméno" required><input type="text" name="discord_nick" placeholder="Discord Nick" required><input type="url" name="image_url" placeholder="URL obrázku" required><textarea name="description" placeholder="Něco o něm..." required></textarea>
            <div id="roles-container"><div style="display: flex; gap: 10px; margin-bottom: 5px;"><input type="text" name="role_name[]" placeholder="Role (např. SA)" style="flex: 2; margin: 0;"><input type="color" name="role_color[]" value="#ef4444" style="flex: 1; margin: 0;"></div></div>
            <button type="submit" class="btn" style="width: 100%; margin-top: 15px;">Přidat do týmu</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">👥 Aktuální členové týmu</h3>
        <table style="width: 100%;"><tr><th>Jméno</th><th>Discord Nick</th><th>Akce</th></tr>
            {% for member in team %}<tr><td><strong>{{ member.get('name', '') }}</strong></td><td>{{ member.get('discord_nick', '') }}</td><td><form action="/dashboard/delete_team" method="POST"><input type="hidden" name="discord_nick" value="{{ member.get('discord_nick', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px;"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}
        </table>
    </div>
</div>
"""

HTML_IDS = """
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">Správa Aplikačních ID</h3>
    <table style="width: 100%;"><tr><th>App ID</th><th>Nick</th><th>Discord ID</th><th>Status</th><th>Změnit na:</th></tr>
        {% for user in users %}
        <tr><td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td><td><strong>{{ user.get('nick', '') }}</strong></td><td style="font-size: 12px; color: var(--text-muted);">{{ user.get('discord_id', '') }}</td><td>{% if user.get('is_deleted') %}<span style="color: var(--danger);">Smazán</span>{% else %}<span style="color: var(--success);">Aktivní</span>{% endif %}</td><td><form action="/dashboard/change_id" method="POST" style="display: flex; gap: 5px;"><input type="hidden" name="discord_id" value="{{ user.get('discord_id', '') }}"><input type="number" name="new_app_id" placeholder="Nové ID" required style="width: 80px; margin: 0; padding: 5px;"><button type="submit" class="btn" style="padding: 5px;">Změnit</button></form></td></tr>
        {% endfor %}
    </table>
</div>
"""

HTML_DASHBOARD_MAIN = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);">{{ title }}</h2>
    <div style="color: var(--text-muted); font-size: 13px; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-weight: bold;"><i class="fas fa-sync-alt" style="color: var(--blue-main);"></i> <span id="timer-sec" style="color: white;">60</span>s do aktualizace</div>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; overflow-x: auto;">
    <table id="usersTable" style="width: 100%;">
        <thead><tr><th>App ID</th><th>Nick</th><th>Stav</th><th>Role</th><th>Poslední Aktivita</th><th>Akce</th></tr></thead>
        <tbody>
        {% for user in users %}
        <tr>
            <td style="font-weight: bold; color: var(--blue-main);">#{{ user.get('app_id', '') }}</td>
            <td><strong>{{ user.get('nick', '') }}</strong></td>
            <td>{% if user.get('is_banned') %}<span style="color: var(--danger); font-size: 11px; font-weight:bold; border:1px solid var(--danger); padding:2px 5px; border-radius:4px;">BANNED</span>{% elif user.get('is_deleted') %}<span style="color: var(--text-muted); font-size: 11px; font-weight:bold; border:1px solid var(--text-muted); padding:2px 5px; border-radius:4px;">DELETED</span>{% elif not user.get('hwid') or user.get('hwid') == 'None' or user.get('hwid') == '' %}<span style="color: var(--warning); font-size: 11px; font-weight:bold; border:1px solid var(--warning); padding:2px 5px; border-radius:4px;">NOT ACTIVATED</span>{% else %}<span style="color: var(--success); font-size: 11px; font-weight:bold; border:1px solid var(--success); padding:2px 5px; border-radius:4px;">ACTIVATED</span>{% endif %}</td>
            <td>
                {% set role_list = user.get('role', '').split(',') %}
                {% for r in role_list %}{% set r_clean = r.strip() %}{% if r_clean == 'SA' %}<span class="role-tag" style="background-color: #ef4444; color: white;">SA</span>{% elif r_clean == 'DEV' %}<span class="role-tag" style="background-color: #10b981; color: white;">DEV</span>{% elif r_clean == 'BT' %}<span class="role-tag" style="background-color: #3b82f6; color: white;">BT</span>{% elif r_clean == 'User' %}<span class="role-tag" style="background-color: #64748b; color: white;">User</span>{% endif %}{% endfor %}
                {% if user.get('dashboard_access') %}<i class="fas fa-shield-alt" style="color:var(--blue-main); font-size:12px; margin-left:5px;" title="Má přístup do DB"></i>{% endif %}
            </td>
            <td style="color: var(--text-muted); font-size: 13px;">{% if user.get('is_online') %}<span style="color: var(--success); font-weight: bold;">🟢 AKTIVNÍ</span>{% else %}{{ user.get('last_active', 'Nikdy nehrál') }}{% endif %}</td>
            <td><button class="btn btn-dark" style="padding: 5px 10px; font-size: 12px;" onclick="openModal('{{ user.get('app_id', '') }}', '{{ user.get('discord_id', '') }}', '{{ user.get('nick', '') }}', '{{ user.get('role', '') }}', '{{ user.get('hwid', '') }}', '{{ user.get('is_banned', False) }}', '{{ user.get('is_deleted', False) }}', '{{ user.get('dashboard_access', False) }}')"><i class="fas fa-edit"></i> Edit</button></td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
<script>
    let timeLeft = 60;
    setInterval(() => { timeLeft--; let secEl = document.getElementById('timer-sec'); if(secEl) secEl.innerText = timeLeft; if(timeLeft <= 0) location.reload(); }, 1000);
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
    <div style="display: flex; flex-direction: column; gap: 40px; padding-bottom: 50px; align-items: center;">
        {% for s in supporters %}
        <div class="tier-{{ s.get('tier', 1) }} supporter-wrapper">
            <div style="width: 100%;">
                {% if s.get('tier') == 3 %} <div class="title-badge">MEGA PODPOROVATEL</div>{% elif s.get('tier') == 2 %} <div class="title-badge">VELKÝ PODPOROVATEL</div>{% else %} <div class="title-badge">PODPOROVATEL</div> {% endif %}
                <h3 class="name-title">{{ s.get('name', 'Neznámý dárce') }}</h3>
                <div class="amt-badge">{{ s.get('amount', '') }}</div>
            </div>
            <div style="width: 100%; margin-top: auto;">
                {% if s.get('message') %}<p style="color: var(--text-main); font-size: 16px; font-style: italic; margin: 0 auto 15px auto; line-height: 1.5; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border-left: 2px solid rgba(255,255,255,0.2); max-width: 90%;">"{{ s.get('message') }}"</p>{% endif %}
                <div style="font-size: 11px; color: #64748b; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; text-align: center;">Datum podpory: {{ s.get('created_at', '') }}</div>
            </div>
        </div>
        {% else %}
        <div style="text-align: center; color: var(--text-muted); padding: 40px; background: rgba(0,0,0,0.2); border-radius: 10px; border: 1px dashed rgba(255,255,255,0.1); width: 100%;">Zatím zde nikdo není. Buďte první!</div>
        {% endfor %}
    </div>
</div>
"""

HTML_SUPPORTERS_MGMT = """
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2 style="margin: 0; color: var(--text-main);"><i class="fas fa-star" style="color:var(--warning);"></i> Správa Podporovatelů</h2>
</div>
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; border-top: 4px solid var(--warning); margin-bottom: 20px;">
    <h3 style="color: var(--warning); margin-top: 0;"><i class="fas fa-exclamation-triangle"></i> Ke schválení (Manuální kontrola)</h3>
    <p style="color: var(--text-muted); font-size: 13px;">Zde se zobrazují lidé, kteří si zažádali o roli na webu, ale systém nenašel shodu nebo jejich účet na Discordu.</p>
    <div style="overflow-x: auto;">
        <table style="width: 100%;">
            <tr><th>BMAC Jméno</th><th>Požadovaný Discord Nick</th><th>Částka (Odhad Role)</th><th>Akce</th></tr>
            {% for p in pending_claims %}
            <tr>
                <td style="color:var(--blue-main); font-weight:bold;">{{ p.get('name', 'Neznámý') }}</td>
                <td style="color:white; font-weight:bold;">{{ p.get('discord_nick', 'Nevyplněno') }}</td>
                <td><span class="role-tag" style="background-color: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning);">{{ p.get('amount', '?') }}</span></td>
                <td>
                    <form action="/dashboard/approve_claim" method="POST" style="display:inline;"><input type="hidden" name="claim_id" value="{{ p.get('id', '') }}"><input type="hidden" name="discord_nick" value="{{ p.get('discord_nick', '') }}"><input type="hidden" name="amount" value="{{ p.get('amount', '0') }}"><button type="submit" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-check"></i> Schválit</button></form>
                    <form action="/dashboard/reject_claim" method="POST" style="display:inline;"><input type="hidden" name="claim_id" value="{{ p.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Opravdu zamítnout?')"><i class="fas fa-times"></i></button></form>
                </td>
            </tr>
            {% else %}<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Vše je vyřízeno, žádné čekající požadavky.</td></tr>{% endfor %}
        </table>
    </div>
</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Ruční přidání podporovatele</h3>
        <form action="/dashboard/add_supporter" method="POST">
            <input type="text" name="name" placeholder="Jméno podporovatele" required><input type="text" name="amount" placeholder="Částka (např. 150 CZK nebo 10 USD)" required><textarea name="message" placeholder="Zpráva od podporovatele (volitelně)..." rows="3"></textarea>
            <button type="submit" class="btn" style="width: 100%; margin-top: 15px;">Přidat do databáze</button>
        </form>
    </div>
    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">☕ Historie podporovatelů</h3>
        <div style="overflow-x: auto;">
            <table style="width: 100%;">
                <tr><th>Jméno</th><th>Discord</th><th>Částka</th><th>Datum</th><th>Akce</th></tr>
                {% for s in supporters %}
                <tr>
                    <td style="color:var(--blue-main); font-weight:bold;">{{ s.get('name', 'Neznámý') }}</td><td style="color:#aaa; font-size:12px;">{{ s.get('discord_nick', '') }}</td><td style="color:var(--success); font-weight:bold;">{{ s.get('amount', '') }}</td><td style="color:var(--text-muted); font-size:12px;">{{ s.get('created_at', '') }}</td>
                    <td><form action="/dashboard/delete_supporter" method="POST" style="display:inline;"><input type="hidden" name="supporter_id" value="{{ s.get('id', '') }}"><button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;"><i class="fas fa-trash"></i></button></form></td>
                </tr>
                {% else %}<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Zatím žádné platby.</td></tr>{% endfor %}
            </table>
        </div>
    </div>
</div>
"""
