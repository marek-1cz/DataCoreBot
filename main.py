import os
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from threading import Thread
from supabase import create_client
from datetime import datetime

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 

# ==========================================
# 1. HTML ŠABLONY (MODERNÍ TECH-BLUE DESIGN)
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
        
        input, select, textarea { width: 100%; padding: 10px; margin: 8px 0 15px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; box-sizing: border-box; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background-color: var(--bg-panel); border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background-color: #0f172a; color: var(--blue-main); font-weight: 600; text-transform: uppercase; font-size: 13px; }
        tr:hover { background-color: #334155; }
        
        .role-tag { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background-color: rgba(56, 189, 248, 0.1); color: var(--blue-main); border: 1px solid var(--blue-main); margin: 2px; }
        
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
            <a href="/dashboard/team" class="sidebar-link"><i class="fas fa-user-plus"></i> Přidat člena týmu</a>
            <a href="/dashboard?filter=banned" class="sidebar-link" style="color: var(--warning);"><i class="fas fa-ban"></i> Seznam BANů</a>
            <a href="/dashboard?filter=deleted" class="sidebar-link" style="color: var(--danger);"><i class="fas fa-trash-alt"></i> Smazaní (Záloha)</a>
            <div style="padding: 15px 20px 5px 20px; font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold;">Hledat roli</div>
            <a href="/dashboard?filter=SA" class="sidebar-link"><i class="fas fa-crown"></i> SA (Super Admini)</a>
            <a href="/dashboard?filter=DEV" class="sidebar-link"><i class="fas fa-code"></i> DEV (Vývojáři)</a>
            <a href="/dashboard?filter=BT" class="sidebar-link"><i class="fas fa-bug"></i> BT (Beta Testeři)</a>
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
                
                <label>Role (lze psát více rolí oddělených čárkou, např: SA, DEV, VIP):</label>
                <input type="text" name="roles" id="modalRoles" placeholder="User">
                
                <label>HWID (Zámek na PC):</label>
                <input type="text" name="hwid" id="modalHwid" placeholder="Pro odblokování smažte text zde">
                
                <div style="display: flex; gap: 10px; margin-top: 20px;">
                    <button type="submit" name="action" value="save" class="btn" style="flex: 2;"><i class="fas fa-save"></i> Uložit</button>
                    <button type="submit" name="action" value="ban" id="btnBan" class="btn btn-warning" style="flex: 1;"><i class="fas fa-ban"></i> BAN</button>
                    <button type="submit" name="action" value="unban" id="btnUnban" class="btn" style="flex: 1; background-color: var(--success); display: none;"><i class="fas fa-check"></i> Un-BAN</button>
                </div>
                
                <div style="margin-top: 15px; border-top: 1px solid #334155; padding-top: 15px;">
                    <button type="submit" name="action" value="delete" class="btn btn-danger" style="width: 100%;" onclick="return confirm('Opravdu smazat účet? (ID zůstane blokované)')"><i class="fas fa-trash"></i> Smazat účet (Soft Delete)</button>
                </div>
            </form>
            <button class="btn" onclick="closeModal()" style="background: transparent; color: var(--text-muted); width: 100%; margin-top: 10px; border: 1px solid #334155;">Zrušit</button>
        </div>
    </div>
</div>

<script>
    function openModal(app_id, discord_id, nick, roles, hwid, is_banned) {
        document.getElementById('editModal').style.display = 'flex';
        document.getElementById('modalAppId').innerText = "#" + app_id;
        document.getElementById('modalDiscordId').value = discord_id;
        document.getElementById('modalNick').value = nick;
        document.getElementById('modalRoles').value = roles;
        document.getElementById('modalHwid').value = hwid === 'None' ? '' : hwid;
        
        if (is_banned === 'True') {
            document.getElementById('btnBan').style.display = 'none';
            document.getElementById('btnUnban').style.display = 'block';
        } else {
            document.getElementById('btnBan').style.display = 'block';
            document.getElementById('btnUnban').style.display = 'none';
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

HTML_TEAM_ADD = """
<div style="background-color: var(--bg-panel); padding: 20px; border-radius: 10px; max-width: 600px;">
    <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat člena týmu</h3>
    <form action="/dashboard/add_team" method="POST">
        <input type="text" name="name" placeholder="Jméno / Přezdívka" required>
        <input type="text" name="discord_nick" placeholder="Discord Nick (bez @)" required>
        <input type="url" name="image_url" placeholder="URL obrázku (odkaz na fotku)" required>
        <textarea name="description" placeholder="Něco o něm..." rows="3" required></textarea>
        
        <div style="display: flex; gap: 10px;">
            <input type="text" name="role_name" placeholder="Název Role (např. Developer)" required style="flex: 2;">
            <input type="color" name="role_color" value="#38bdf8" style="flex: 1; padding: 2px; height: 40px;">
        </div>
        
        <button type="submit" class="btn" style="width: 100%;">Přidat do týmu</button>
    </form>
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
                    <span class="role-tag">{{ r.strip() }}</span>
                {% endfor %}
            </td>
            <td>
                {% if user.is_deleted %}
                    <span style="color: var(--danger); font-weight: bold;"><i class="fas fa-skull"></i> Smazán ({{ user.deleted_at }})</span>
                {% elif user.is_banned %}
                    <span style="color: var(--warning); font-weight: bold;"><i class="fas fa-ban"></i> BANNED</span>
                {% else %}
                    <span style="color: var(--success);"><i class="fas fa-check-circle"></i> Aktivní</span>
                {% endif %}
            </td>
            <td>
                {% if not user.is_deleted %}
                    <button class="btn" style="padding: 6px 12px; font-size: 12px;" onclick="openModal('{{ user.app_id }}', '{{ user.discord_id }}', '{{ user.nick }}', '{{ user.role }}', '{{ user.hwid }}', '{{ user.is_banned }}')"><i class="fas fa-cog"></i> Spravovat</button>
                {% else %}
                    <span style="font-size: 12px; color: var(--text-muted);">Zablokováno</span>
                {% endif %}
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

@app.route('/')
def home():
    return render_public(HTML_HOME)

@app.route('/download')
def download():
    return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--blue-main);'>Stažení</h2><p>Připojte se na Discord pro získání přístupu.</p></div>")

@app.route('/team')
def team():
    # Tady by byla stránka Náš tým (prozatím public placeholder)
    return render_public("<h2 style='color: var(--blue-main); text-align: center;'>Náš Tým</h2><p style='text-align: center;'>Zatím prázdné.</p>")

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if request.method == 'POST':
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
                title = "Smazané účty (Historie)"
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

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    return render_dashboard(HTML_TEAM_ADD)

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    if db:
        try:
            new_member = {
                "name": request.form.get("name"),
                "discord_nick": request.form.get("discord_nick"),
                "image_url": request.form.get("image_url"),
                "description": request.form.get("description"),
                "role_name": request.form.get("role_name"),
                "role_color": request.form.get("role_color")
            }
            db.table("team").insert(new_member).execute()
            flash('Člen týmu byl úspěšně přidán!', 'success')
        except Exception as e:
            flash(f'Chyba při přidávání do týmu: {e}', 'error')
            
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'): return redirect(url_for('dashboard_main'))
    
    db = get_db()
    discord_id = request.form.get("discord_id")
    action = request.form.get("action")
    
    if db and discord_id:
        try:
            if action == 'save':
                updates = {
                    "nick": request.form.get("nick"),
                    "role": request.form.get("roles"),
                    "hwid": request.form.get("hwid")
                }
                db.table("users").update(updates).eq("discord_id", discord_id).execute()
                flash('Uživatel úspěšně upraven!', 'success')
                
            elif action == 'ban':
                db.table("users").update({"is_banned": True}).eq("discord_id", discord_id).execute()
                flash('Uživatel dostal BAN!', 'warning')
                
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                flash('BAN byl zrušen.', 'success')
                
            elif action == 'delete':
                now = datetime.now().strftime("%d.%m.%Y %H:%M")
                db.table("users").update({"is_deleted": True, "deleted_at": now}).eq("discord_id", discord_id).execute()
                flash('Uživatel byl smazán (Soft Delete) - jeho ID bylo trvale zablokováno.', 'danger')
                
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
# 3. DISCORD BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)

@bot.command()
async def register(ctx, nick: str = None):
    if not nick:
        await ctx.send("Použití: `!register HerniNick`")
        return
    try:
        db = get_db()
        if not db:
            await ctx.send("Chybí klíče k databázi!")
            return
            
        discord_id = str(ctx.author.id)
        check = db.table("users").select("*").eq("discord_id", discord_id).execute()
        
        if len(check.data) > 0:
            user_data = check.data[0]
            if user_data.get('is_banned'):
                await ctx.send("Máš udělený BAN na tomto projektu! 🛑")
            elif user_data.get('is_deleted'):
                await ctx.send("Tvůj účet byl smazán administrátorem. 🛑")
            else:
                await ctx.send(f"Už jsi zaregistrovaný s ID #{user_data.get('app_id')}! ✅")
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
                "is_deleted": False
            }
            db.table("users").insert(novy).execute()
            await ctx.send(f"Registrace do Projektu OIS IDPK hotova! Tvé Aplikační ID je **#{new_app_id}**. Vítej, **{nick}**! ✅")
    except Exception as e:
        await ctx.send(f"Chyba při registraci (Máš v Supabase přidané nové sloupce?): {e}")

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
