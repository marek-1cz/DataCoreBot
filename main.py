import os
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, url_for, session
from threading import Thread
from supabase import create_client, Client

print("=== START BOTA ===", flush=True)

app = Flask(__name__)
app.secret_key = "mrweb_tajny_klic_pro_session" # Nutné pro fungování přihlášení

# ==========================================
# DESIGN STRÁNEK (HTML)
# ==========================================

# 1. Veřejná domovská stránka
HTML_HOME = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>MRWEB Project</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { text-align: center; background: #1e1e1e; padding: 50px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-top: 5px solid #bb86fc; }
        h1 { color: #bb86fc; font-size: 3em; margin-bottom: 10px; }
        p { font-size: 1.2em; color: #aaa; }
        .status { color: #03dac6; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        <h1>MRWEB PROJECT</h1>
        <p>Status: <span class="status">ONLINE & OPERATIONAL</span></p>
        <p>Všechny systémy běží na pozadí.</p>
    </div>
</body>
</html>
"""

# 2. Přihlašovací stránka
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Admin Login</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #1e1e1e; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); width: 300px; text-align: center; }
        input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #333; background: #2c2c2c; color: white; }
        button { width: 100%; padding: 10px; background: #bb86fc; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .error { color: #cf6679; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Admin Přihlášení</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Zadejte admin heslo" required>
            <button type="submit">Vstoupit</button>
        </form>
    </div>
</body>
</html>
"""

# 3. Admin Panel
HTML_ADMIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>MRWEB - Admin Panel</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 40px; }
        .container { max-width: 1100px; margin: 0 auto; background-color: #1e1e1e; padding: 30px; border-radius: 10px; }
        h1 { color: #bb86fc; display: flex; justify-content: space-between; align-items: center; }
        .logout { font-size: 14px; color: #cf6679; text-decoration: none; border: 1px solid #cf6679; padding: 5px 10px; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #333; }
        th { background-color: #2c2c2c; color: #bb86fc; }
        .role-SA { color: #cf6679; font-weight: bold; }
        .role-User { color: #03dac6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            👑 MRWEB - Správa Uživatelů
            <a href="/logout" class="logout">Odhlásit se</a>
        </h1>
        <table>
            <tr>
                <th>Discord ID</th>
                <th>Nick</th>
                <th>Role</th>
                <th>HWID</th>
            </tr>
            {% for user in users %}
            <tr>
                <td>{{ user.discord_id }}</td>
                <td><strong>{{ user.nick }}</strong></td>
                <td class="role-{{ user.role }}">{{ user.role }}</td>
                <td>{{ user.hwid if user.hwid else '---' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# ==========================================
# WEB LOGIKA (FLASK)
# ==========================================

@app.route('/')
def home():
    return render_template_string(HTML_HOME)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        typed_password = request.form.get('password')
        admin_password = os.environ.get("ADMIN_PASSWORD", "default_heslo") # Načte heslo z Renderu
        
        if typed_password == admin_password:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = "Špatné heslo! Zkuste to znovu."
            
    return render_template_string(HTML_LOGIN, error=error)

@app.route('/admin')
def admin_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        supabase = create_client(url, key)
        response = supabase.table("users").select("*").execute()
        return render_template_string(HTML_ADMIN, users=response.data)
    except Exception as e:
        return f"Chyba databáze: {e}"

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# DISCORD BOT
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
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
        supabase = create_client(url, key)
        discord_id = str(ctx.author.id)
        
        check = supabase.table("users").select("*").eq("discord_id", discord_id).execute()
        if len(check.data) > 0:
            await ctx.send("Už jsi zaregistrovaný! 🛑")
        else:
            supabase.table("users").insert({"discord_id": discord_id, "nick": nick, "role": "User", "hwid": ""}).execute()
            await ctx.send(f"Registrace hotova! Vítej, **{nick}**! ✅")
    except Exception as e:
        await ctx.send(f"Chyba: {e}")

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
