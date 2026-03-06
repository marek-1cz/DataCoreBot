import os
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from threading import Thread
from supabase import create_client

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
        }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-dark); color: var(--text-main); margin: 0; padding: 0; }
        
        nav { background-color: rgba(15, 23, 42, 0.9); padding: 15px 40px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 100; }
        .logo { font-size: 24px; font-weight: 800; color: var(--blue-main); text-decoration: none; letter-spacing: 1px; }
        .nav-links a { color: var(--text-main); text-decoration: none; margin-left: 20px; font-weight: 500; transition: color 0.3s; }
        .nav-links a:hover { color: var(--blue-main); }
        .nav-links .admin-link { color: var(--text-muted); font-size: 12px; margin-left: 40px; }

        .container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
        
        .btn { display: inline-block; background-color: var(--blue-main); color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; transition: 0.3s; }
        .btn:hover { background-color: var(--blue-hover); }
        .btn-danger { background-color: var(--danger); }
        .btn-danger:hover { background-color: #dc2626; }
        
        input, select, textarea { width: 100%; padding: 10px; margin: 8px 0 15px 0; background-color: #0f172a; border: 1px solid #334155; color: white; border-radius: 5px; box-sizing: border-box; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: var(--bg-panel); border-radius: 10px; overflow: hidden; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background-color: #0f172a; color: var(--blue-main); font-weight: 600; text-transform: uppercase; font-size: 13px; }
        tr:hover { background-color: #334155; }
        
        .team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .team-card { background-color: var(--bg-panel); border-radius: 10px; padding: 20px; text-align: center; border-top: 4px solid var(--blue-main); transition: transform 0.3s; }
        .team-card:hover { transform: translateY(-5px); }
        .team-img { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 15px; border: 3px solid #334155; }
        .team-name { font-size: 20px; font-weight: bold; margin: 0 0 5px 0; }
        .team-discord { color: var(--blue-main); font-size: 14px; margin-bottom: 15px; }
        .team-desc { color: var(--text-muted); font-size: 14px; line-height: 1.5; margin-bottom: 15px; }
        .team-role { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; }
        .alert-success { background-color: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .alert-error { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
    </style>
</head>
<body>
    <nav>
        <a href="/" class="logo">OIS IDPK</a>
        <div class="nav-links">
            <a href="/">Domů</a>
            <a href="/download">Download</a>
            <a href="/team">Náš Tým</a>
            <a href="/admin" class="admin-link">Dashboard 🔒</a>
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
</body>
</html>
"""

HTML_HOME = """
<div style="text-align: center; padding: 50px 0;">
    <h1 style="font-size: 3em; color: var(--blue-main); margin-bottom: 10px;">Projekt OIS IDPK</h1>
    <p style="font-size: 1.2em; color: var(--text-muted); max-width: 600px; margin: 0 auto 30px auto;">
        Moderní, rychlý a bezpečný software. Připravujeme pro vás nástroj, který změní pravidla hry.
    </p>
    <a href="/download" class="btn" style="font-size: 18px; padding: 15px 30px;">Získat Software</a>
</div>
"""

HTML_DOWNLOAD = """
<div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center;">
    <h2>Stažení Softwaru</h2>
    <p style="color: var(--text-muted); margin-bottom: 30px;">
        Pro stažení aplikace se prosím připojte na náš oficiální Discord server a požádejte o vygenerování jednorázového odkazu.
    </p>
    <a href="#" class="btn" style="background-color: #5865F2;">Připojit se na Discord</a>
</div>
"""

HTML_TEAM = """
<h2 style="color: var(--blue-main); border-bottom: 2px solid #334155; padding-bottom: 10px;">Náš Tým</h2>
<div class="team-grid">
    {% for member in team %}
    <div class="team-card">
        <img src="{{ member.image_url }}" alt="Fotka" class="team-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <h3 class="team-name">{{ member.name }}</h3>
        <div class="team-discord">@{{ member.discord_nick }}</div>
        <p class="team-desc">{{ member.description }}</p>
        <div class="team-role" style="background-color: {{ member.role_color }}33; color: {{ member.role_color }}; border: 1px solid {{ member.role_color }};">
            {{ member.role_name }}
        </div>
    </div>
    {% else %}
    <p style="color: var(--text-muted);">Zatím nebyli přidáni žádní členové týmu.</p>
    {% endfor %}
</div>
"""

HTML_LOGIN = """
<div style="max-width: 400px; margin: 50px auto; background-color: var(--bg-panel); padding: 30px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
    <h2 style="text-align: center; color: var(--blue-main);">Admin Login</h2>
    <form method="POST">
        <label>Bezpečnostní heslo</label>
        <input type="password" name="password" required>
        <button type="submit" class="btn" style="width: 100%;">Přihlásit se do Dashboardu</button>
    </form>
</div>
"""

HTML_ADMIN = """
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; padding-bottom: 10px; margin-bottom: 20px;">
    <h2>⚙️ Dashboard - Projekt OIS IDPK</h2>
    <a href="/logout" class="btn btn-danger" style="padding: 5px 10px; font-size: 14px;">Odhlásit</a>
</div>

<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">➕ Přidat člena týmu</h3>
        <form action="/admin/add_team" method="POST">
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

    <div style="flex: 2; min-width: 300px; background-color: var(--bg-panel); padding: 20px; border-radius: 10px;">
        <h3 style="color: var(--blue-main); margin-top: 0;">👥 Registrovaní uživatelé</h3>
        <div style="overflow-x: auto;">
            <table>
                <tr>
                    <th>Discord ID</th>
                    <th>Nick</th>
                    <th>Role</th>
                    <th>HWID</th>
                    <th>Akce</th>
                </tr>
                {% for user in users %}
                <tr>
                    <td>{{ user.discord_id }}</td>
                    <td><strong>{{ user.nick }}</strong></td>
                    <td>{{ user.role }}</td>
                    <td>{{ user.hwid if user.hwid else '-' }}</td>
                    <td>
                        <button class="btn" style="padding: 5px 10px; font-size: 12px; margin-right: 5px;" onclick="alert('Úprava uživatele {{ user.nick }} se připravuje!')">Upravit</button>
                        <form action="/admin/delete_user" method="POST" style="display: inline;">
                            <input type="hidden" name="discord_id" value="{{ user.discord_id }}">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Opravdu smazat?')">Smazat</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</div>
"""

# ==========================================
# 2. FLASK ROUTES (LOGIKA WEBU)
# ==========================================

def render_page(template_string, **kwargs):
    full_html = BASE_HTML.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(full_html, **kwargs)

def get_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

@app.route('/')
def home():
    return render_page(HTML_HOME)

@app.route('/download')
def download():
    return render_page(HTML_DOWNLOAD)

@app.route('/team')
def team():
    db = get_db()
    team_members = []
    if db:
        try:
            response = db.table("team").select("*").execute()
            team_members = response.data
        except:
            pass 
            
    return render_page(HTML_TEAM, team=team_members)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == os.environ.get("ADMIN_PASSWORD", "admin"):
            session['logged_in'] = True
            flash('Úspěšně přihlášeno!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Špatné heslo!', 'error')
            
    if not session.get('logged_in'):
        return render_page(HTML_LOGIN)
        
    db = get_db()
    users_data = []
    if db:
        try:
            resp = db.table("users").select("*").execute()
            users_data = resp.data
        except Exception as e:
            flash(f'Chyba načítání uživatelů: {e}', 'error')

    return render_page(HTML_ADMIN, users=users_data)

@app.route('/admin/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'): return redirect(url_for('admin'))
    
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
            flash(f'Chyba při přidávání do týmu (Máš vytvořenou tabulku "team"?): {e}', 'error')
            
    return redirect(url_for('admin'))

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if not session.get('logged_in'): return redirect(url_for('admin'))
    
    discord_id = request.form.get("discord_id")
    db = get_db()
    if db and discord_id:
        try:
            db.table("users").delete().eq("discord_id", discord_id).execute()
            flash('Uživatel byl smazán.', 'success')
        except Exception as e:
            flash(f'Chyba mazání: {e}', 'error')
            
    return redirect(url_for('admin'))

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
            await ctx.send("Už jsi zaregistrovaný! 🛑")
        else:
            db.table("users").insert({"discord_id": discord_id, "nick": nick, "role": "User", "hwid": ""}).execute()
            await ctx.send(f"Registrace do Projektu OIS IDPK hotova! Vítej, **{nick}**! ✅")
    except Exception as e:
        await ctx.send(f"Chyba: {e}")

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("[CHYBA] Chybí DISCORD_TOKEN!")
