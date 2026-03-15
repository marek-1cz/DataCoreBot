import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, Response, stream_with_context, jsonify
from threading import Thread
from supabase import create_client
from datetime import datetime, timedelta
import asyncio
import uuid
import urllib.request
import json
import traceback
import re

# IMPORT VŠECH HTML DESIGNŮ Z VEDLEJŠÍHO SOUBORU
from html_templates import *

print("=== START PROJEKTU OIS IDPK ===", flush=True)

app = Flask(__name__)
app.secret_key = "ois_idpk_super_tajny_klic" 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

URL_MALE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20pf-lepsi.png"
URL_VELKE_LOGO = "https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png"

def get_prague_time():
    return datetime.utcnow() + timedelta(hours=1)

DEPLOY_TIME = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")

@app.errorhandler(Exception)
def handle_exception(e):
    error_trace = traceback.format_exc()
    print(error_trace, flush=True)
    return f"<div style='background:#0f172a; color:#ef4444; padding:20px; font-family:monospace; border:2px solid #ef4444;'><h2>CHYBA APLIKACE (500)</h2><p>Pošli tohle vývojáři:</p><pre>{error_trace}</pre></div>", 500

# ==========================================
# DATABÁZE A GLOBÁLNÍ FUNKCE
# ==========================================

def get_db():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        print(f"Chyba připojení k DB: {e}")
    return None

def process_supporters(data_list):
    for s in data_list:
        amt_str = str(s.get('amount', '0'))
        match = re.search(r'([\d\.,]+)', amt_str)
        val = 0.0
        if match:
            try:
                val = float(match.group(1).replace(',', '.'))
            except:
                pass
        
        norm_val = val
        if 'usd' in amt_str.lower() or '$' in amt_str.lower():
            norm_val *= 23
        elif 'eur' in amt_str.lower() or '€' in amt_str.lower():
            norm_val *= 25
        
        s['norm_val'] = norm_val
        if norm_val >= 325:
            s['tier'] = 3
        elif norm_val >= 195:
            s['tier'] = 2
        else:
            s['tier'] = 1

    data_list.sort(key=lambda x: (x.get('norm_val', 0), x.get('id', 0)), reverse=True)
    return data_list

def calculate_roles_for_supporter(amount_str):
    match = re.search(r'([\d\.,]+)', str(amount_str))
    val = 0.0
    if match:
        try:
            val = float(match.group(1).replace(',', '.'))
        except:
            pass
    if 'usd' in str(amount_str).lower() or '$' in str(amount_str).lower():
        val *= 23
    elif 'eur' in str(amount_str).lower() or '€' in str(amount_str).lower():
        val *= 25
    
    if val >= 325:
        tier_role = "⭐| MEGA PODPOROVATEL"
    elif val >= 195:
        tier_role = "⭐| VELKÝ PODPOROVATEL"
    else:
        tier_role = "⭐| PODPOROVATEL"
        
    # Vrací List rolí pro Discord a String pro Databázi
    discord_roles = ["🎖️| Beta tester", tier_role]
    db_role_string = f"BT,{tier_role}"
    
    return discord_roles, db_role_string

def user_exists_sync(identifier):
    try:
        for guild in bot.guilds:
            if identifier.isdigit():
                member = guild.get_member(int(identifier))
                if member:
                    return True
            member = discord.utils.find(
                lambda m: m.name.lower() == identifier.lower() or 
                          (m.global_name and m.global_name.lower() == identifier.lower()), 
                guild.members
            )
            if member:
                return True
    except:
        pass
    return False

async def assign_supporter_role(identifier, role_names_list):
    success = False
    try:
        for guild in bot.guilds:
            member = None
            if identifier.isdigit():
                member = guild.get_member(int(identifier))
            if not member:
                member = discord.utils.find(
                    lambda m: m.name.lower() == identifier.lower() or 
                              (m.global_name and m.global_name.lower() == identifier.lower()), 
                    guild.members
                )

            if member:
                assigned_any = False
                for r_name in role_names_list:
                    role = discord.utils.get(guild.roles, name=r_name)
                    if role:
                        await member.add_roles(role)
                        assigned_any = True
                
                if assigned_any:
                    success = True
                    try:
                        roles_str = "\n".join([f"**{r}**" for r in role_names_list])
                        embed = discord.Embed(
                            title="🎉 Děkujeme za obrovskou podporu!", 
                            description=f"Na našem Discord serveru a v databázi ti byly automaticky přiděleny tyto exkluzivní role:\n\n{roles_str}\n\nMoc si toho vážíme!", 
                            color=0x38bdf8
                        )
                        await member.send(embed=embed)
                    except:
                        pass
                break
    except Exception as e:
        print(f"Chyba pri pridelovani roli: {e}")
    return success

async def announce_new_supporter(discord_nick, amount_str, message, role_names_list):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="⭐・podporovatelé")
        if channel:
            roles_str = ", ".join([f"**{r}**" for r in role_names_list])
            embed = discord.Embed(title="🎉 MÁME NOVÉHO PODPOROVATELE!", description=f"Uživatel **{discord_nick}** právě podpořil náš projekt a získal exkluzivní role {roles_str} na serveru i v aplikaci!", color=0xf59e0b)
            embed.add_field(name="💰 Výše podpory", value=f"**{amount_str}**", inline=False)
            if message and message.strip():
                embed.add_field(name="📝 Vzkaz od podporovatele", value=f"*{message}*", inline=False)
            embed.set_footer(text="Obrovsky děkujeme za Vaši podporu! ❤️ Projekt OIS IDPK")
            try:
                await channel.send(embed=embed)
            except:
                pass
            break

async def async_send_log(title, description, color=0x38bdf8):
    for guild in bot.guilds:
        channel = discord.utils.get(guild.channels, name="🖥️・datacore-logs")
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=get_prague_time())
            try:
                await channel.send(embed=embed)
            except:
                pass
            break

def send_log(title, description, color=0x38bdf8):
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(async_send_log(title, description, color), bot.loop)

def _cors_jsonify(data):
    resp = jsonify(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

def render_public(template_string, **kwargs):
    html = PUBLIC_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

def render_dashboard(template_string, **kwargs):
    html = DASHBOARD_LAYOUT.replace('{% block content %}{% endblock %}', template_string)
    html = html.replace('{{ deploy_time }}', DEPLOY_TIME)
    return render_template_string(BASE_HTML.replace('{% block layout %}{% endblock %}', html), logo_male=URL_MALE_LOGO, logo_velke=URL_VELKE_LOGO, **kwargs)

@app.before_request
def check_session_validity():
    if request.path.startswith('/dashboard/') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize']:
        if not session.get('logged_in'):
            return redirect(url_for('dashboard_main'))
            
    if request.path.startswith('/dashboard') and request.path not in ['/dashboard/wait_auth', '/dashboard/login_finalize'] and session.get('logged_in'):
        discord_id = session.get('discord_id')
        if discord_id:
            try:
                db = get_db()
                if db:
                    users_data = db.table("users").select("dashboard_access, is_banned, is_deleted").eq("discord_id", discord_id).execute().data
                    if users_data:
                        user = users_data[0]
                        if not user.get("dashboard_access") or user.get("is_banned") or user.get("is_deleted"):
                            session.clear()
                            flash('Váš přístup byl zablokován nebo odebrán.', 'error')
                            return redirect(url_for('dashboard_main'))
            except:
                pass

def sync_roles_from_flask(discord_id, role_string):
    async def sync():
        try:
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id))
                if not member:
                    try:
                        member = await guild.fetch_member(int(discord_id))
                    except:
                        pass
                if member:
                    await update_member_roles(member, role_string)
        except:
            pass
    if bot.loop and bot.loop.is_running():
        asyncio.run_coroutine_threadsafe(sync(), bot.loop)

# ==========================================
# VEŘEJNÉ STRÁNKY (PUBLIC ROUTES)
# ==========================================

@app.route('/')
def home(): 
    def log_visit(ip, cf_country):
        try:
            if not ip or ip in ["127.0.0.1", "::1", "0.0.0.0"]:
                return
            clean_ip = ip.split(',')[0].strip()
            
            db = get_db()
            if not db:
                return
            
            today_str = get_prague_time().strftime("%d.%m.%Y")
            now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
            
            existing = db.table("page_visits").select("visited_at").eq("ip", clean_ip).execute().data or []
            for record in existing:
                if record.get("visited_at", "").startswith(today_str):
                    return
            
            country_name = cf_country
            region = ""
            country_code = ""
            
            try:
                url = f"http://ip-api.com/json/{clean_ip}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    geo_data = json.loads(response.read().decode())
                    if geo_data.get("status") == "success":
                        country_name = geo_data.get("country", country_name)
                        region = geo_data.get("regionName", "")
                        country_code = geo_data.get("countryCode", "").lower()
            except:
                pass
            
            if not country_code or country_code.lower() == 'us' or country_name.lower() in ["neznámá", "unknown", "neznámá (nepodporováno)", "none", "united states", "us"]:
                return 
            
            combined_location = f"{country_code}|{country_name}|{region}"
            db.table("page_visits").insert({"ip": clean_ip, "country": combined_location, "visited_at": now_str}).execute()
        except:
            pass

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    country = request.headers.get('CF-IPCountry', 'Neznámá')
    Thread(target=log_visit, args=(ip, country)).start()
    
    return render_public(HTML_HOME)

@app.route('/download')
def download_home():
    return render_public(HTML_DOWNLOADS_MAIN)

@app.route('/team')
def team(): 
    try:
        team_members = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except:
        team_members = []
    return render_public(HTML_TEAM, team=team_members)

@app.route('/supporters')
def supporters():
    support_data = []
    try: 
        db = get_db()
        if db:
            data = db.table("supporters").select("*").eq("status", "completed").execute().data or []
            support_data = process_supporters(data)
    except:
        pass
    return render_public(HTML_SUPPORTERS, supporters=support_data)

@app.route('/api/supporters', methods=['GET', 'OPTIONS'])
def api_supporters():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        if not db:
            return _cors_jsonify({"error": "DB not ready"}), 500
        data = db.table("supporters").select("name, amount, message, created_at").eq("status", "completed").execute().data or []
        support_data = process_supporters(data)
        return _cors_jsonify({"supporters": support_data})
    except Exception as e:
        return _cors_jsonify({"error": str(e)}), 500

@app.route('/claim', methods=['GET', 'POST'])
def claim_role():
    if request.method == 'POST':
        bmac_name = request.form.get('bmac_name', '').strip()
        discord_nick = request.form.get('discord_nick', '').strip()
        
        db = get_db()
        if not db: 
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('claim_role'))

        all_records = db.table("supporters").select("*").eq("name", bmac_name).execute().data
        
        # OCHRANA PROTI ZNEUŽITÍ: Pokud je platba už dokončená, zablokujeme to.
        if any(r['status'] == 'completed' for r in all_records):
            send_log("⚠️ Pokus o zneužití (Double Claim)", f"Uživatel **{discord_nick}** se pokusil na webu znovu použít BMAC jméno **{bmac_name}**, které už bylo dříve spárováno s jiným účtem!", 0xef4444)
            flash('Chyba: Platba pod tímto jménem již byla spárována s jiným Discord účtem a nelze ji použít znovu!', 'error')
            return redirect(url_for('claim_role'))

        pending_records = [r for r in all_records if r['status'] == 'pending']

        if pending_records:
            record = pending_records[0] 
            discord_roles, db_role_string = calculate_roles_for_supporter(record.get('amount', '0'))
            
            if user_exists_sync(discord_nick):
                if bot.loop and bot.loop.is_running():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
                    asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_nick, record.get('amount', '0'), record.get('message', ''), discord_roles), bot.loop)

                db.table("supporters").update({"status": "completed", "discord_nick": discord_nick}).eq("id", record['id']).execute()
                send_log("✅ Role úspěšně vyzvednuta", f"Uživatel **{discord_nick}** si přes web úspěšně spároval BMAC platbu od jména **{bmac_name}**.", 0x10b981)
                
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_nick},nick.ilike.{discord_nick}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                    
                    # Přidáme nové role do seznamu, pokud tam ještě nejsou
                    for new_r in db_role_string.split(','):
                        if new_r.strip() not in roles_list:
                            roles_list.append(new_r.strip())
                            
                    new_roles = ",".join(roles_list)
                    db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
                else:
                    db.table("pending_roles").insert({"discord_identifier": discord_nick, "roles": db_role_string}).execute()

                flash('Úspěch! Role ti byla právě přidělena na Discordu a tvoje jméno bude zveřejněno v síni slávy!', 'success')
            else:
                db.table("supporters").update({"status": "manual_review", "discord_nick": discord_nick}).eq("id", record['id']).execute()
                send_log("⚠️ Žádost o kontrolu", f"Uživatel **{discord_nick}** se pokusil spárovat platbu od **{bmac_name}**, ale bot ho nenašel na Discord serveru.\nPřesunuto do manuální kontroly.", 0xf59e0b)
                flash('Tvůj Discord účet nebyl na serveru nalezen! Požadavek byl odeslán ke schválení administrátorovi.', 'warning')
        else:
            # Kontrola, jestli už to náhodou nečeká na manuální kontrolu
            manual_records = [r for r in all_records if r['status'] == 'manual_review']
            if manual_records:
                flash('Tato platba již čeká na manuální schválení administrátorem. Prosím vyčkejte.', 'warning')
            else:
                db.table("supporters").insert({
                    "name": bmac_name,
                    "discord_nick": discord_nick,
                    "amount": "Neznámá (Z webu)",
                    "message": "Uživatel zadal na webu jméno BMAC, které nebylo nalezeno webhookem.",
                    "status": "manual_review",
                    "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")
                }).execute()
                send_log("📝 Nová neznámá žádost", f"Uživatel **{discord_nick}** žádá o spárování jména **{bmac_name}**, ale webhookem neprošla žádná taková platba.\nPřidáno k manuální kontrole.", 0x3b82f6)
                flash('Platba s tímto jménem nebyla v našem systému nalezena. Váš požadavek byl odeslán administrátorovi k ruční kontrole.', 'warning')

        return redirect(url_for('claim_role'))

    return render_public(HTML_CLAIM)

@app.route('/webhook/bmac', methods=['GET', 'POST'])
def bmac_webhook():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            data = payload.get('data', payload) if isinstance(payload, dict) else {}
        else:
            data = request.args
            
        name = data.get('supporter_name') or data.get('payer_name') or data.get('name') or 'Anonymní dárce'
        message = data.get('support_note') or data.get('message') or ''
        amount_val = data.get('amount') or data.get('support_coffees') or 1
        currency = data.get('currency') or 'CZK'
        amount_str = f"{amount_val} {currency}"
        
        discord_roles, db_role_string = calculate_roles_for_supporter(amount_str)
        discord_identifier = None
        
        id_match = re.search(r'\b\d{17,19}\b', message)
        if id_match:
            discord_identifier = id_match.group(0)
        else:
            nick_match = re.search(r'(?i)(?:discord|dc|nick)[\s:]+([a-zA-Z0-9_.-]+)', message)
            if nick_match:
                discord_identifier = nick_match.group(1).strip()

        db = get_db()
        if db:
            status = 'pending'
            if discord_identifier and user_exists_sync(discord_identifier):
                status = 'completed'

            db.table("supporters").insert({
                "name": str(name), 
                "message": str(message), 
                "amount": str(amount_str), 
                "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M"),
                "status": status,
                "discord_nick": discord_identifier or ""
            }).execute()
            
            send_log("🍕 Nová platba zaznamenána!", f"Uživatel **{name}** právě poslal **{amount_str}**.\nZpráva: *{message}*\n\nPlatba zapsána do databáze jako: `{status}`", 0xF4CC17)

            if status == 'completed':
                db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_identifier},nick.ilike.{discord_identifier}").execute().data
                if db_user:
                    current_roles = db_user[0].get('role', '')
                    roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                    
                    for new_r in db_role_string.split(','):
                        if new_r.strip() not in roles_list:
                            roles_list.append(new_r.strip())
                            
                    new_roles = ",".join(roles_list)
                    db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
                else:
                    db.table("pending_roles").insert({"discord_identifier": discord_identifier, "roles": db_role_string}).execute()

                if bot.loop and bot.loop.is_running():
                    asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_identifier, discord_roles), bot.loop)
                    asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_identifier, amount_str, message, discord_roles), bot.loop)

        if request.method == 'GET':
            return f"<h1>ÚSPĚCH! 🎉</h1><p>Testovací podpora zapsána!</p><a href='/supporters'>Zpět</a>"
        return jsonify({"status": "success"}), 200
    except Exception as e:
        if request.method == 'GET':
            return f"<h1>❌ CHYBA DATABÁZE</h1><p><b>Důvod:</b> {str(e)}</p>"
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/download/<token>')
def secure_download(token):
    db = get_db()
    if not db:
        return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if not resp.data:
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Neplatný odkaz!</h2></div>")
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"):
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--danger);'>Přístup zamítnut</h2></div>")
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data:
            return render_public("<div style='text-align: center; padding: 50px;'><h2 style='color: var(--warning);'>Chyba verze</h2></div>")
            
        v_data = v_resp.data[0]
        html = f"""<div style="background-color: var(--bg-panel); padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; border-top: 4px solid var(--success);"><h2 style="color: var(--success); margin-top: 0;"><i class="fas fa-check-circle"></i> Ověření úspěšné</h2><p style="color: var(--text-muted); font-size: 14px; margin-bottom: 30px;">Přihlášen jako: <strong>{user.get('nick', '')}</strong></p><div style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #334155;"><h3 style="margin: 0 0 10px 0; color: var(--blue-main);">Projekt OIS IDPK</h3><p style="margin: 0; color: var(--text-main);">Instalátor: <strong>{v_data.get('version_name', '')}</strong></p></div><a href="/api/get_file/{token}?v={version_id}" class="btn btn-success" style="font-size: 18px; padding: 15px 30px;"><i class="fas fa-download"></i> Stáhnout Soubor</a></div>"""
        return render_public(html)
    except:
        return "Systémová chyba."

@app.route('/api/get_file/<token>')
def api_get_file(token):
    db = get_db()
    if not db:
        return "Chyba databáze."
    try:
        resp = db.table("users").select("*").eq("download_token", token).execute()
        if not resp.data:
            return "Neplatný token."
        user = resp.data[0]
        if user.get("is_banned") or user.get("is_deleted"):
            return "Přístup zamítnut."
            
        version_id = request.args.get('v')
        v_resp = db.table("software_versions").select("*").eq("id", version_id).execute()
        if not v_resp.data:
            return "Verze nenalezena."
            
        file_url = v_resp.data[0]['file_url']
        version_name = v_resp.data[0]['version_name']
        
        try:
            db.table("download_logs").insert({"discord_id": user['discord_id'], "version_name": version_name, "downloaded_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
            send_log("📥 Stahování", f"Uživatel `{user.get('nick')}` zahájil stahování: **{version_name}**.", 0x38bdf8)
        except:
            pass
        
        file_ext = "zip" 
        if "pixeldrain.com/u/" in file_url:
            file_url = file_url.replace("/u/", "/api/file/")
        if "1drv.ms" in file_url or "onedrive.live.com" in file_url or "1drv.com" in file_url:
            file_url = file_url.split("?")[0] + "?download=1"
        if "dropbox.com" in file_url:
            file_url = file_url.replace("dl=0", "dl=1")
            if "dl=1" not in file_url:
                file_url += "?dl=1" if "?" not in file_url else "&dl=1"

        req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        remote_response = urllib.request.urlopen(req)
        def generate():
            while True:
                chunk = remote_response.read(8192)
                if not chunk:
                    break
                yield chunk
        content_type = remote_response.headers.get('Content-Type', 'application/octet-stream')
        return Response(stream_with_context(generate()), headers={'Content-Disposition': f'attachment; filename="OIS_IDPK_{version_name.replace(" ", "_")}.{file_ext}"', 'Content-Type': content_type})
    except Exception as e:
        return f"Chyba odkazu: {e}"

# ==========================================
# API PRO SOFTWARE A KLIENTA
# ==========================================

@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def api_status():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    try:
        db = get_db()
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "disabled", "message": "OMLOUVÁME SE, SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA)."})
    except:
        pass
    return _cors_jsonify({"status": "enabled"})

@app.route('/api/app_login', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_login():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
    if not data:
        return _cors_jsonify({"status": "error", "message": "Chybí data."})
    
    identifier = str(data.get("identifier", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})

        user_resp = db.table("users").select("*").or_(f"discord_id.eq.{identifier},nick.ilike.{identifier}").execute()
        if not user_resp.data and identifier.isdigit():
            user_resp = db.table("users").select("*").eq("app_id", int(identifier)).execute()
            
        if not user_resp.data:
            return _cors_jsonify({"status": "error", "message": "Uživatel nenalezen."})
        user = user_resp.data[0]
        
        if user.get("is_banned"):
            send_log("⛔ Pokus o přihlášení (BAN)", f"Zabanovaný uživatel `{user.get('nick')}` se pokusil zapnout software.", 0xef4444)
            return _cors_jsonify({"status": "banned", "message": "Tento účet má BAN."})
        
        db_hwid = user.get("hwid")
        if db_hwid and str(db_hwid) != "None" and str(db_hwid).strip() != "":
            if str(db_hwid) != req_hwid:
                send_log("🔒 HWID Neshoda", f"Uživatel `{user.get('nick')}` se hlásí z jiného PC!\nUloženo: `{db_hwid}`\nNové: `{req_hwid}`", 0xf59e0b)
                return _cors_jsonify({"status": "hwid_error", "message": "Tento účet je vázán na jiný počítač."})
            
        token = str(uuid.uuid4())
        db.table("users").update({"login_token": token}).eq("discord_id", user.get("discord_id")).execute()
        
        async def send():
            try:
                u = bot.get_user(int(user.get("discord_id"))) or await bot.fetch_user(int(user.get("discord_id")))
                if u:
                    embed = discord.Embed(title="🛡️ Ověření přihlášení", description=f"Byl zaznamenán pokus o spuštění softwaru.\n**Uživatel:** {user.get('nick')}\nPotvrďte přístup tlačítkem níže.", color=0x38bdf8)
                    await u.send(embed=embed, view=AppAuthView(token, user.get("discord_id"), is_dm=True))
            except:
                pass
        if bot.loop and bot.loop.is_running():
            asyncio.run_coroutine_threadsafe(send(), bot.loop)
        
        return _cors_jsonify({"status": "waiting", "discord_id": user.get("discord_id")})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_check():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    
    try:
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data:
            return _cors_jsonify({"status": "error"})
        user = user_resp.data[0]
        
        if user.get("login_token") == "approved":
            db_hwid = user.get("hwid")
            if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
                if req_hwid and req_hwid.startswith("PC-"):
                    db.table("users").update({"hwid": req_hwid, "login_token": ""}).eq("discord_id", discord_id).execute()
                else:
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            else:
                db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "success", "display_name": user.get("nick")})
            
        elif user.get("login_token") == "rejected":
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return _cors_jsonify({"status": "error", "message": "Přístup zamítnut uživatelem."})
            
        return _cors_jsonify({"status": "pending"})
    except:
        return _cors_jsonify({"status": "error"})

@app.route('/api/silent_check', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_silent_check():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    req_hwid = str(data.get("hwid", ""))
    db = get_db()
    try:
        set_resp = db.table("settings").select("setting_value").eq("setting_key", "software_enabled").execute()
        if set_resp.data and str(set_resp.data[0].get('setting_value', 'True')).lower() == 'false':
            return _cors_jsonify({"status": "error", "message": "SOFTWARE JE NYNÍ VYPNUT."})
        user_resp = db.table("users").select("*").eq("discord_id", discord_id).execute()
        if not user_resp.data:
            return _cors_jsonify({"status": "error", "message": "Tento účet neexistuje."})
        user = user_resp.data[0]
        if user.get("is_banned"):
            return _cors_jsonify({"status": "error", "message": "Tento účet má BAN."})
        if user.get("is_deleted"):
            return _cors_jsonify({"status": "error", "message": "Tento účet byl smazán."})
        
        db_hwid = user.get("hwid")
        if not db_hwid or str(db_hwid) == "None" or str(db_hwid).strip() == "":
            if req_hwid and req_hwid.startswith("PC-"):
                db.table("users").update({"hwid": req_hwid}).eq("discord_id", discord_id).execute()
                return _cors_jsonify({"status": "success"})
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Chyba čtení PC."})

        if str(db_hwid) != req_hwid:
            return _cors_jsonify({"status": "error", "message": "ZÁMEK HWID: Váš počítač nesouhlasí."})
            
        return _cors_jsonify({"status": "success"})
    except Exception as e:
        return _cors_jsonify({"status": "error", "message": str(e)})

@app.route('/api/app_ping', methods=['POST', 'OPTIONS'], strict_slashes=False)
def api_app_ping():
    if request.method == 'OPTIONS':
        return Response(status=200, headers={'Access-Control-Allow-Origin': '*'})
    data = request.get_json(silent=True) or {}
    discord_id = str(data.get("discord_id", ""))
    action = data.get("action", "ping")
    db = get_db()
    try:
        now_str = get_prague_time().strftime("%d.%m.%Y %H:%M:%S")
        user_resp = db.table("users").select("launch_count, total_time").eq("discord_id", discord_id).execute()
        if not user_resp.data:
            return _cors_jsonify({"status": "error"})
        
        updates = {"last_active": now_str, "is_online": True}
        if action == "start":
            count = user_resp.data[0].get("launch_count") or 0
            updates["launch_count"] = count + 1
        elif action == "stop":
            updates["is_online"] = False
        elif action == "ping":
            time_val = user_resp.data[0].get("total_time") or 0
            updates["total_time"] = time_val + 60
            
        db.table("users").update(updates).eq("discord_id", discord_id).execute()
        return _cors_jsonify({"status": "ok"})
    except:
        return _cors_jsonify({"status": "error"})

# ==========================================
# DASHBOARD A ADMIN ROUTES
# ==========================================

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
                async def send():
                    try:
                        u = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                        if u:
                            await u.send(embed=discord.Embed(title="🔐 Bezpečnostní ověření", description="Byl zaznamenán pokus o přihlášení do administračního panelu.\n\nPokud jste to Vy, potvrďte přístup kliknutím na tlačítko níže.", color=0x38bdf8), view=DashboardAuthView(token, discord_id))
                    except:
                        pass
                if bot.loop and bot.loop.is_running():
                    asyncio.run_coroutine_threadsafe(send(), bot.loop)
                return redirect(url_for('wait_auth', discord_id=discord_id))
            else:
                flash('Účet neexistuje, nemá povolený přístup, nebo byl zablokován.', 'error')
        except Exception as e:
            flash(f'Chyba: {e}', 'error')
    return redirect(url_for('dashboard_main'))

@app.route('/dashboard/wait_auth')
def wait_auth(): 
    return render_public(HTML_WAIT_AUTH, discord_id=request.args.get("discord_id"))

@app.route('/api/check_auth/<discord_id>')
def check_auth(discord_id):
    try:
        db = get_db()
        if db:
            user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
            if user:
                t = user[0].get("login_token")
                if t == "approved":
                    return {"status": "approved"}
                elif t == "rejected":
                    db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
                    return {"status": "rejected"}
    except:
        pass
    return {"status": "waiting"}

@app.route('/dashboard/login_finalize')
def login_finalize():
    discord_id = request.args.get('discord_id')
    db = get_db()
    if db and discord_id:
        user = db.table("users").select("login_token").eq("discord_id", discord_id).execute().data
        if user and user[0].get("login_token") == "approved":
            session.permanent = True
            session['logged_in'] = True
            session['discord_id'] = discord_id
            db.table("users").update({"login_token": ""}).eq("discord_id", discord_id).execute()
            return redirect(url_for('dashboard_main'))
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard/stats')
def dashboard_stats():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    
    total_visits = 0
    last_7_days = 0
    country_totals = {}
    region_totals = {}
    
    dates_7_days = [(get_prague_time().replace(tzinfo=None) - timedelta(days=i)).strftime("%d.%m.") for i in range(6, -1, -1)]
    chart_data_7d = {d: 0 for d in dates_7_days}
    chart_data_24h = {f"{i:02d}:00": 0 for i in range(24)}
    
    try:
        db = get_db()
        if db:
            # Ochrana paměti - Načte pouze nejnovějších 5000 záznamů, aby nepadla RAMka
            visits = db.table("page_visits").select("*").order("id", desc=True).limit(5000).execute().data or []
            total_visits = len(visits)
            now = get_prague_time().replace(tzinfo=None)
            
            for v in visits:
                c_raw = v.get('country', '')
                if not c_raw or 'neznámá' in c_raw.lower() or 'unknown' in c_raw.lower() or 'none' in c_raw.lower() or 'us' in c_raw.lower():
                    continue
                
                parts = c_raw.split('|')
                cc = parts[0] if len(parts) > 0 else ""
                c_name = parts[1] if len(parts) > 1 else c_raw
                reg = parts[2] if len(parts) > 2 else ""
                
                if not cc or cc == 'us':
                    continue
                
                flag_url = f"https://flagcdn.com/24x18/{cc}.png"
                
                if cc not in country_totals:
                    country_totals[cc] = {"name": c_name, "count": 0, "flag": flag_url}
                country_totals[cc]["count"] += 1
                
                display_name = f"{c_name} - {reg}" if reg else c_name
                if display_name not in region_totals:
                    region_totals[display_name] = {"count": 0, "flag": flag_url}
                region_totals[display_name]["count"] += 1
                
                try:
                    v_time = datetime.strptime(v['visited_at'], "%d.%m.%Y %H:%M")
                    if (now - v_time).days <= 7:
                        last_7_days += 1
                        
                    day_str = v_time.strftime("%d.%m.")
                    hour_str = v_time.strftime("%H:00")
                    if day_str in chart_data_7d:
                        chart_data_7d[day_str] += 1
                    if v_time.date() == now.date():
                        if hour_str in chart_data_24h:
                            chart_data_24h[hour_str] += 1
                except:
                    pass
                
    except Exception as e:
        flash(f"Chyba při načítání statistik: {e}", "error")
    
    return render_dashboard(HTML_STATS, total_visits=total_visits, last_7_days=last_7_days, country_totals=country_totals, region_totals=region_totals, labels_7d=json.dumps(list(chart_data_7d.keys())), data_7d=json.dumps(list(chart_data_7d.values())), labels_24h=json.dumps(list(chart_data_24h.keys())), data_24h=json.dumps(list(chart_data_24h.values())), deploy_time=DEPLOY_TIME)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard_main():
    if not session.get('logged_in'):
        return render_public(HTML_LOGIN)
    users_data = []
    try:
        db = get_db()
        if db:
            query = db.table("users").select("*")
            f = request.args.get('filter')
            if f == 'banned':
                query = query.eq("is_banned", True).eq("is_deleted", False)
            elif f == 'deleted':
                query = query.eq("is_deleted", True)
            elif f:
                query = query.ilike("role", f"%{f}%").eq("is_deleted", False)
            else:
                query = query.eq("is_deleted", False).order("app_id")
            
            users_data = query.execute().data or []
            now = get_prague_time().replace(tzinfo=None)
            
            for u in users_data:
                if u.get("is_online"):
                    la_str = u.get("last_active")
                    if la_str:
                        try:
                            last_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S")
                            if (now - last_dt).total_seconds() > 120:
                                u["is_online"] = False
                                db.table("users").update({"is_online": False}).eq("discord_id", u["discord_id"]).execute()
                        except:
                            pass
    except Exception as e:
        flash(f"Chyba při načítání dat: {e}", "error")
    return render_dashboard(HTML_DASHBOARD_MAIN, users=users_data, title="Přehled uživatelů", deploy_time=DEPLOY_TIME)

@app.route('/dashboard/supporters', methods=['GET'])
def dashboard_supporters():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main')) 
    pending_claims = []
    support_data = []
    try: 
        db = get_db()
        if db:
            p_data = db.table("supporters").select("*").eq("status", "manual_review").execute().data or []
            pending_claims = p_data
            
            s_data = db.table("supporters").select("*").eq("status", "completed").execute().data or []
            support_data = process_supporters(s_data)
    except Exception as e: 
        flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_SUPPORTERS_MGMT, pending_claims=pending_claims, supporters=support_data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/approve_claim', methods=['POST'])
def approve_claim():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    claim_id = request.form.get("claim_id")
    discord_nick = request.form.get("discord_nick")
    amount = request.form.get("amount", "0")
    db = get_db()
    if db and claim_id and discord_nick:
        discord_roles, db_role_string = calculate_roles_for_supporter(amount)
        
        if bot.loop and bot.loop.is_running():
            asyncio.run_coroutine_threadsafe(assign_supporter_role(discord_nick, discord_roles), bot.loop)
            
            rec = db.table("supporters").select("*").eq("id", claim_id).execute().data
            if rec:
                asyncio.run_coroutine_threadsafe(announce_new_supporter(discord_nick, amount, rec[0].get('message', ''), discord_roles), bot.loop)
        
        db.table("supporters").update({"status": "completed", "discord_nick": discord_nick}).eq("id", claim_id).execute()
        send_log("✅ Manuální schválení", f"Administrátor právě schválil roli pro uživatele **{discord_nick}**.", 0x10b981)
        
        db_user = db.table("users").select("*").or_(f"discord_id.eq.{discord_nick},nick.ilike.{discord_nick}").execute().data
        if db_user:
            current_roles = db_user[0].get('role', '')
            roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
            for new_r in db_role_string.split(','):
                if new_r.strip() not in roles_list:
                    roles_list.append(new_r.strip())
            new_roles = ",".join(roles_list)
            db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
        else:
            db.table("pending_roles").insert({"discord_identifier": discord_nick, "roles": db_role_string}).execute()
            
        flash(f'Požadavek schválen a role udělena pro: {discord_nick}', 'success')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/reject_claim', methods=['POST'])
def reject_claim():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    claim_id = request.form.get("claim_id")
    db = get_db()
    if db and claim_id:
        db.table("supporters").delete().eq("id", claim_id).execute()
        send_log("❌ Manuální zamítnutí", f"Administrátor zamítl a smazal platbu s ID: {claim_id}.", 0xef4444)
        flash('Požadavek byl zamítnut a smazán.', 'success')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/edit_supporter', methods=['POST'])
def edit_supporter():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    supporter_id = request.form.get("supporter_id")
    db = get_db()
    if db and supporter_id:
        try:
            db.table("supporters").update({
                "name": request.form.get("name"),
                "discord_nick": request.form.get("discord_nick", ""),
                "amount": request.form.get("amount"),
                "message": request.form.get("message", "")
            }).eq("id", supporter_id).execute()
            flash('Údaje podporovatele byly úspěšně upraveny!', 'success')
        except Exception as e:
            flash(f'Chyba při úpravě: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/add_supporter', methods=['POST'])
def add_supporter():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try: 
        db = get_db()
        d_nick = request.form.get("discord_nick", "").strip()
        amt = request.form.get("amount", "0 CZK")
        msg = request.form.get("message", "")
        
        db.table("supporters").insert({
            "name": request.form.get("name"), 
            "discord_nick": d_nick,
            "amount": amt, 
            "message": msg, 
            "status": "completed",
            "created_at": get_prague_time().strftime("%d.%m.%Y %H:%M")
        }).execute()
        
        if d_nick:
            discord_roles, db_role_string = calculate_roles_for_supporter(amt)
            if bot.loop and bot.loop.is_running():
                asyncio.run_coroutine_threadsafe(assign_supporter_role(d_nick, discord_roles), bot.loop)
                asyncio.run_coroutine_threadsafe(announce_new_supporter(d_nick, amt, msg, discord_roles), bot.loop)
                
            db_user = db.table("users").select("*").or_(f"discord_id.eq.{d_nick},nick.ilike.{d_nick}").execute().data
            if db_user:
                current_roles = db_user[0].get('role', '')
                roles_list = [r.strip() for r in current_roles.split(',')] if current_roles else []
                for new_r in db_role_string.split(','):
                    if new_r.strip() not in roles_list:
                        roles_list.append(new_r.strip())
                new_roles = ",".join(roles_list)
                db.table("users").update({"role": new_roles}).eq("discord_id", db_user[0]['discord_id']).execute()
            else:
                db.table("pending_roles").insert({"discord_identifier": d_nick, "roles": db_role_string}).execute()
        
        flash('Podporovatel byl úspěšně přidán!', 'success')
    except Exception as e:
        flash(f'Chyba při přidávání: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/dashboard/delete_supporter', methods=['POST'])
def delete_supporter():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("supporters").delete().eq("id", request.form.get("supporter_id")).execute()
        flash('Podporovatel smazán.', 'success')
    except Exception as e:
        flash(f'Chyba při mazání: {e}', 'error')
    return redirect(url_for('dashboard_supporters'))

@app.route('/api/get_profile_data/<discord_id>')
def get_profile_data(discord_id):
    if not session.get('logged_in'):
        return jsonify({"joined_at": "Neznámé", "status": "Neznámý", "downloads": []})
    
    joined_at = "Neznámé"
    app_status_html = "<span style='color: #64748b;'><i>Neaktivní</i></span>"
    stats_html = ""
    dls = []
    status_map = { 
        "online": "<span style='color:#10b981; font-weight:bold;'><i class='fas fa-circle'></i> Online</span>", 
        "idle": "<span style='color:#f59e0b; font-weight:bold;'><i class='fas fa-moon'></i> Nečinný</span>", 
        "dnd": "<span style='color:#ef4444; font-weight:bold;'><i class='fas fa-minus-circle'></i> Nerušit</span>", 
        "offline": "<span style='color:#64748b; font-weight:bold;'><i class='fas fa-circle'></i> Offline</span>" 
    }
    status_html = status_map["offline"]
    
    try:
        if bot.guilds:
            for g in bot.guilds:
                m = g.get_member(int(discord_id))
                if m:
                    joined_at = m.joined_at.strftime("%d.%m.%Y") if m.joined_at else "Neznámé"
                    status_html = status_map.get(str(m.status), status_map["offline"])
                    break
        db = get_db()
        if db:
            dls = db.table("download_logs").select("*").eq("discord_id", discord_id).order("id", desc=True).limit(15).execute().data or []
            db_user = db.table("users").select("last_active, is_online, launch_count, total_time").eq("discord_id", discord_id).execute().data
            if db_user:
                u = db_user[0]
                is_on = u.get("is_online", False)
                la_str = u.get("last_active") or ""
                if is_on and la_str:
                    try:
                        last_dt = datetime.strptime(la_str, "%d.%m.%Y %H:%M:%S")
                        if (get_prague_time().replace(tzinfo=None) - last_dt).total_seconds() > 120:
                            is_on = False
                            db.table("users").update({"is_online": False}).eq("discord_id", discord_id).execute()
                    except:
                        pass
                
                m, s = divmod(u.get("total_time") or 0, 60)
                h, m = divmod(m, 60)
                
                if is_on:
                    app_status_html = '<span style="color: var(--success); font-weight:bold;">🟢 AKTIVNÍ</span>'
                else:
                    app_status_html = f'<span style="color: var(--danger);">🔴 Offline</span> (Naposledy: {la_str or "Nikdy"})'
                stats_html = f"<div style='margin-top:10px; font-size:12px; color:var(--text-muted); border-top: 1px solid #334155; padding-top: 10px;'><div><b>Spuštění:</b> {u.get('launch_count') or 0}x</div><div style='margin-top:5px;'><b>Čas:</b> {h}h {m}m {s}s</div></div>"
    except:
        pass
    
    return jsonify({"joined_at": joined_at, "status": status_html, "app_status": app_status_html, "stats": stats_html, "downloads": dls})

@app.route('/dashboard/app_settings', methods=['GET'])
def dashboard_app_settings():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    soft_enabled = True
    dl_enabled = True
    try:
        db = get_db()
        if db:
            res = db.table("settings").select("*").in_("setting_key", ["software_enabled", "downloads_enabled"]).execute().data or []
            for r in res:
                if r.get('setting_key') == 'software_enabled' and str(r.get('setting_value')).lower() == 'false':
                    soft_enabled = False
                if r.get('setting_key') == 'downloads_enabled' and str(r.get('setting_value')).lower() == 'false':
                    dl_enabled = False
    except:
        pass
    return render_dashboard(HTML_APP_SETTINGS, soft_enabled=soft_enabled, dl_enabled=dl_enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/downloads', methods=['GET'])
def dashboard_downloads():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main')) 
    versions = []
    enabled = True
    try:
        db = get_db()
        if db:
            set_resp = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if set_resp and str(set_resp[0].get('setting_value')).lower() == 'false':
                enabled = False
            versions = db.table("software_versions").select("*").order("id").execute().data or []
    except Exception as e:
        flash(f"Chyba DB: {e}", "error")
    return render_dashboard(HTML_DOWNLOADS_MGMT, versions=versions, enabled=enabled, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/toggle_software', methods=['POST'])
def toggle_software():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    new_status = request.form.get("new_status")
    if db:
        try:
            check = db.table("settings").select("*").eq("setting_key", "software_enabled").execute().data or []
            if not check:
                db.table("settings").insert({"setting_key": "software_enabled", "setting_value": new_status}).execute()
            else:
                db.table("settings").update({"setting_value": new_status}).eq("setting_key", "software_enabled").execute()
            flash('Globální stav softwaru byl změněn!', 'success')
            send_log("🚨 Kill-Switch", f"Software byl přes administraci **{'ZAPNUT' if new_status == 'True' else 'VYPNUT'}**.", 0xef4444 if new_status == 'False' else 0x10b981)
        except Exception as e:
            flash(f"Chyba: Zkontrolujte DB. ({e})", "error")
    return redirect(url_for('dashboard_app_settings'))

@app.route('/dashboard/toggle_downloads', methods=['POST'])
def toggle_downloads():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    new_status = request.form.get("new_status")
    return_to = request.form.get("return_to", "downloads")
    if db:
        try: 
            check = db.table("settings").select("*").eq("setting_key", "downloads_enabled").execute().data or []
            if not check:
                db.table("settings").insert({"setting_key": "downloads_enabled", "setting_value": new_status}).execute()
            else:
                db.table("settings").update({"setting_value": new_status}).eq("setting_key", "downloads_enabled").execute()
            flash('Status stahování byl změněn.', 'success')
        except Exception as e:
            flash(f"Chyba: {e}", "error")
    if return_to == 'app_settings':
        return redirect(url_for('dashboard_app_settings'))
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/add_version', methods=['POST'])
def add_version():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try:
        get_db().table("software_versions").insert({"version_name": request.form.get("version_name"), "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}).execute()
    except:
        pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/edit_version', methods=['POST'])
def edit_version():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try: 
        get_db().table("software_versions").update({"version_name": request.form.get("version_name"), "file_url": request.form.get("file_url"), "target_role": request.form.get("target_role")}).eq("id", request.form.get("version_id")).execute()
        flash('Verze byla úspěšně upravena.', 'success')
    except Exception as e:
        flash(f'Chyba při úpravě verze: {e}', 'error')
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/delete_version', methods=['POST'])
def delete_version():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    try:
        get_db().table("software_versions").delete().eq("id", request.form.get("version_id")).execute()
    except:
        pass
    return redirect(url_for('dashboard_downloads'))

@app.route('/dashboard/pending_roles', methods=['GET'])
def pending_roles(): 
    try:
        data = get_db().table("pending_roles").select("*").order("id").execute().data or [] if get_db() else []
    except:
        data = []
    return render_dashboard(HTML_PENDING_ROLES, pending=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/ids', methods=['GET'])
def dashboard_ids(): 
    try:
        data = get_db().table("users").select("*").order("app_id").execute().data or [] if get_db() else []
    except:
        data = []
    return render_dashboard(HTML_IDS, users=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/team', methods=['GET'])
def dashboard_team_page(): 
    try:
        data = get_db().table("team").select("*").execute().data or [] if get_db() else []
    except:
        data = []
    return render_dashboard(HTML_TEAM_ADD, team=data, deploy_time=DEPLOY_TIME)

@app.route('/dashboard/add_pending_role', methods=['POST'])
def add_pending_role():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            roles_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
            db.table("pending_roles").insert({"discord_identifier": request.form.get("discord_identifier"), "roles": roles_str}).execute()
            flash('Rezervace vytvořena.', 'success')
        except Exception as e:
            flash(f"Chyba: {e}", "error")
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/delete_pending_role', methods=['POST'])
def delete_pending_role():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    p_id = request.form.get("pending_id")
    if db and p_id: 
        try:
            db.table("pending_roles").delete().eq("id", p_id).execute()
        except:
            pass
    return redirect(url_for('pending_roles'))

@app.route('/dashboard/change_id', methods=['POST'])
def change_id():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            db.table("users").update({"app_id": int(request.form.get("new_app_id"))}).eq("discord_id", request.form.get("discord_id")).execute()
        except:
            pass
    return redirect(url_for('dashboard_ids'))

@app.route('/dashboard/add_team', methods=['POST'])
def add_team():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    if db:
        try:
            combined_roles = [f"{n.strip()}|{c.strip()}" for n, c in zip(request.form.getlist("role_name[]"), request.form.getlist("role_color[]")) if n.strip()]
            db.table("team").insert({"name": request.form.get("name"), "discord_nick": request.form.get("discord_nick"), "image_url": request.form.get("image_url"), "description": request.form.get("description"), "role_name": ",".join(combined_roles)}).execute()
        except:
            pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/delete_team', methods=['POST'])
def delete_team():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    db = get_db()
    if db: 
        try:
            db.table("team").delete().eq("discord_nick", request.form.get("discord_nick")).execute()
        except:
            pass
    return redirect(url_for('dashboard_team_page'))

@app.route('/dashboard/edit_user', methods=['POST'])
def edit_user():
    if not session.get('logged_in'):
        return redirect(url_for('dashboard_main'))
    
    db = get_db()
    discord_id = request.form.get("discord_id")
    action = request.form.get("action")
    nick = request.form.get("nick")
    
    if db and discord_id:
        try:
            if action == 'save':
                r_str = ",".join(request.form.getlist("roles")) if request.form.getlist("roles") else "User"
                db.table("users").update({"nick": nick, "role": r_str, "hwid": request.form.get("hwid"), "dashboard_access": True if request.form.get("dashboard_access") else False}).eq("discord_id", discord_id).execute()
                sync_roles_from_flask(discord_id, r_str)
                send_log("✏️ Úprava uživatele", f"Administrátor upravil uživatele **{nick}** (ID: `{discord_id}`).\nNové role: `{r_str}`", 0xf59e0b)
                flash('Údaje upraveny!', 'success')
            elif action == 'ban':
                db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
                send_log("🔨 BAN", f"Administrátor udělil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0xef4444)
                flash('BAN udělen.', 'warning')
                if str(session.get('discord_id')) == str(discord_id):
                    session.clear()
            elif action == 'unban':
                db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
                send_log("🕊️ UN-BAN", f"Administrátor zrušil BAN uživateli **{nick}** (ID: `{discord_id}`).", 0x10b981)
                flash('BAN zrušen.', 'success')
            elif action == 'delete':
                db.table("users").update({"is_deleted": True, "deleted_at": get_prague_time().strftime("%d.%m.%Y %H:%M"), "dashboard_access": False}).eq("discord_id", discord_id).execute()
                flash('Účet smazán (Soft Delete).', 'danger')
                if str(session.get('discord_id')) == str(discord_id):
                    session.clear()
            elif action == 'restore':
                db.table("users").update({"is_deleted": False, "deleted_at": ""}).eq("discord_id", discord_id).execute()
                flash('Účet obnoven!', 'success')
            elif action == 'hard_delete':
                db.table("users").delete().eq("discord_id", discord_id).execute()
                flash('Účet trvale smazán.', 'dark')
                if str(session.get('discord_id')) == str(discord_id):
                    session.clear()
        except:
            pass
    return redirect(url_for('dashboard_main'))

# ==========================================
# DISCORD BOT A TLAČÍTKA
# ==========================================
class DashboardAuthView(discord.ui.View):
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
                await interaction.edit_original_response(content="✅ **Přístup do administrace byl úspěšně schválen!**", view=None)
            else:
                await interaction.edit_original_response(content="❌ **Platnost vypršela.**", view=None)
                
    @discord.ui.button(label="Zamítnout", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db = get_db()
        if db:
            db.table("users").update({"login_token": "rejected"}).eq("discord_id", self.discord_id).execute()
        await interaction.edit_original_response(content="⛔ **Zamítnuto.**", view=None)

class AppAuthView(discord.ui.View):
    def __init__(self, token, discord_id, is_dm=True):
        super().__init__(timeout=180)
        self.token = token
        self.discord_id = discord_id
        self.is_dm = is_dm
        
    @discord.ui.button(label="Ano, ověřit", style=discord.ButtonStyle.success)
    async def ok(self, interaction, button):
        if str(interaction.user.id) != str(self.discord_id):
            return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        db = get_db()
        if db:
            db.table("users").update({"login_token": "approved"}).eq("discord_id", self.discord_id).execute()
        await interaction.response.edit_message(content="✅ **Ověřeno! Můžete se vrátit do aplikace.**", view=None)
        send_log("🖥️ Přihlášení do Aplikace", f"Uživatel s ID `{self.discord_id}` se úspěšně ověřil a vstoupil do softwaru.", 0x10b981)
        if not self.is_dm:
            await asyncio.sleep(2)
            await interaction.message.delete()

class PerDeleteConfirm(discord.ui.View):
    def __init__(self, target_id, author_id):
        super().__init__(timeout=60)
        self.target_id = target_id
        self.author_id = author_id

    @discord.ui.button(label="Ano, trvale smazat", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.defer()
        db = get_db()
        if db:
            db.table("users").delete().eq("discord_id", self.target_id).execute()
            await interaction.edit_original_response(content=f"✅ Účet `{self.target_id}` byl z databáze PERMANENTNĚ smazán.", view=None, embed=None)

    @discord.ui.button(label="Zrušit", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Toto není tvé tlačítko!", ephemeral=True)
        await interaction.response.edit_message(content="❌ Akce zrušena.", view=None, embed=None)

class DynamicDownloadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Zahájit instalaci softwaru", style=discord.ButtonStyle.primary, emoji="📥", custom_id="persistent_install_main_btn")
    async def dl_btn(self, interaction, button):
        class DynamicRulesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Souhlasím s pravidly", style=discord.ButtonStyle.success, emoji="✅")
            async def agree(self, i2, b2):
                await i2.response.edit_message(content="<a:loading:123> Ověřuji profil...", view=None)
                try:
                    db = get_db()
                    d_id = str(i2.user.id)
                    n = i2.user.display_name
                    u_role = "User"
                    
                    settings_resp = db.table("settings").select("setting_value").eq("setting_key", "downloads_enabled").execute().data or [{}]
                    if str(settings_resp[0].get('setting_value', '')).lower() == 'false':
                        return await i2.edit_original_response(content="**Stahování je globálně vypnuto.**")
                        
                    chk = db.table("users").select("*").eq("discord_id", d_id).execute()
                    pend_data = db.table("pending_roles").select("*").execute().data or []
                    pend = next((p for p in pend_data if p['discord_identifier'] in [d_id, n]), None)
                    
                    if chk.data:
                        if chk.data[0].get('is_banned'):
                            return await i2.edit_original_response(content="**Přístup zamítnut:** Máte BAN.")
                        if chk.data[0].get('is_deleted'):
                            hid = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                            nid = hid.data[0]["app_id"] + 1 if hid.data else 1000
                            r = pend['roles'] if pend else "User"
                            db.table("users").update({"app_id": nid, "nick": n, "is_deleted": False, "role": r}).eq("discord_id", d_id).execute()
                            u_role = r
                            if pend:
                                db.table("pending_roles").delete().eq("id", pend['id']).execute()
                        else:
                            u_role = chk.data[0].get('role', 'User')
                    else:
                        hid = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute()
                        nid = hid.data[0]["app_id"] + 1 if hid.data else 1000
                        r = pend['roles'] if pend else "User"
                        db.table("users").insert({"app_id": nid, "discord_id": d_id, "nick": n, "role": r, "hwid": "", "is_banned": False, "is_deleted": False, "dashboard_access": False, "login_token": "", "registered_at": get_prague_time().strftime("%d.%m.%Y %H:%M")}).execute()
                        u_role = r
                        if pend:
                            db.table("pending_roles").delete().eq("id", pend['id']).execute()
                            
                    if isinstance(i2.user, discord.Member): 
                        try:
                            await update_member_roles(i2.user, u_role)
                        except:
                            pass
                            
                    class DynamicVersionSelect(discord.ui.Select):
                        def __init__(self, u_lvl):
                            opts = []
                            vers_data = get_db().table("software_versions").select("*").order("id").execute().data or []
                            for v in vers_data:
                                req = 2 if v['target_role'] == 'BT' else (3 if v['target_role'] == 'DEV_SA' else 1)
                                if u_lvl >= req:
                                    opts.append(discord.SelectOption(label=v['version_name'], value=str(v['id']), emoji="📦"))
                            if not opts:
                                opts.append(discord.SelectOption(label="Nic není k dispozici", value="none"))
                            super().__init__(placeholder="Vyber verzi k instalaci...", options=opts)
                            
                        async def callback(self, i3):
                            if self.values[0] == "none":
                                return await i3.response.send_message("Nic tu není.", ephemeral=True)
                            await i3.response.send_message("<a:loading:123> Generuji odkaz...", ephemeral=True)
                            t = str(uuid.uuid4())
                            get_db().table("users").update({"download_token": t}).eq("discord_id", str(i3.user.id)).execute()
                            await i3.edit_original_response(content=f"**Odkaz připraven:**\n🔗 {os.environ.get('RENDER_EXTERNAL_URL', 'https://datacorebot.onrender.com')}/download/{t}?v={self.values[0]}\n*Platí jen pro Vás.*")
                            
                    v_view = discord.ui.View()
                    v_view.add_item(DynamicVersionSelect(3 if 'SA' in u_role or 'DEV' in u_role else (2 if 'BT' in u_role else 1)))
                    await i2.edit_original_response(content="**Ověření úspěšné.** Vyberte soubor:", view=v_view)
                except Exception as e:
                    await i2.edit_original_response(content=f"Chyba DB: {e}")
                    
            @discord.ui.button(label="Nesouhlasím", style=discord.ButtonStyle.danger, emoji="❌")
            async def disagree(self, i2, b2):
                await i2.response.edit_message(content="**Akce zrušena.**", view=None)
                
        await interaction.response.send_message("**Podmínky užití:**\n1. Zákaz úprav a šíření.\n2. Zámek na Váš PC (HWID).\n\nSouhlasíte?", view=DynamicRulesView(), ephemeral=True)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.invites_cache = {}

def check_web_sa():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="web-sa") or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění k tomuto příkazu.", delete_after=10)
        return False
    return commands.check(predicate)

def check_sm_role():
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send(f"❌ {ctx.author.mention}, nemáš oprávnění k tomuto příkazu.", delete_after=10)
        return False
    return commands.check(predicate)

@tasks.loop(hours=24)
async def pixeldrain_keepalive():
    db = get_db()
    if not db:
        return
    try:
        resp = db.table("software_versions").select("version_name, file_url").execute()
        versions = getattr(resp, "data", []) or []
        refreshed = []
        for v in versions:
            url = v.get("file_url", "")
            name = v.get("version_name", "Neznámá verze")
            if "pixeldrain.com/u/" in url:
                api_url = url.replace("/u/", "/api/file/")
                try:
                    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-10'})
                    await asyncio.to_thread(urllib.request.urlopen, req, timeout=15)
                    refreshed.append(name)
                except:
                    pass
        if refreshed:
            files_str = "\n• ".join(refreshed)
            await async_send_log("🔄 Anti-Delete Ochrana", f"Systém právě úspěšně nasimuloval stažení.\n**Ochráněné soubory:**\n• {files_str}", 0x3b82f6)
    except:
        pass

@tasks.loop(minutes=1)
async def check_pending_supporters():
    db = get_db()
    if not db:
        return
    try:
        pending = db.table("supporters").select("*").eq("status", "pending").execute().data or []
        now = get_prague_time()
        for p in pending:
            try:
                created_time = datetime.strptime(p['created_at'], "%d.%m.%Y %H:%M")
                if (now - created_time).total_seconds() > 300: # 5 MINUT
                    db.table("supporters").update({"status": "manual_review"}).eq("id", p['id']).execute()
                    send_log("⏳ Platba propadla do kontroly", f"Uživatel si do 5 minut na webu nevyzvedl roli za jméno BMAC: **{p.get('name')}**.\nPřesunuto do manuálního schvalování v Dashboardu.", 0xf59e0b)
            except:
                pass
    except:
        pass

@bot.event
async def on_ready():
    print(f'[OK] Discord bot připraven: {bot.user}', flush=True)
    try:
        bot.add_view(DynamicDownloadView())
    except:
        pass
    try:
        for guild in bot.guilds:
            bot.invites_cache[guild.id] = await guild.invites()
    except:
        pass
    if not pixeldrain_keepalive.is_running():
        pixeldrain_keepalive.start()
    if not check_pending_supporters.is_running():
        check_pending_supporters.start()

@bot.event
async def on_member_join(member):
    used_invite = None
    try:
        new_invites = await member.guild.invites()
        old_invites = bot.invites_cache.get(member.guild.id, [])
        for invite in new_invites:
            for old_invite in old_invites:
                if invite.code == old_invite.code and invite.uses > old_invite.uses:
                    used_invite = invite
                    break
            if used_invite:
                break
        bot.invites_cache[member.guild.id] = new_invites
    except:
        pass
    link_info = "\n\n**🌐 Zdroj:** Uživatel se připojil z odkazu na webové stránce!" if used_invite and used_invite.code == "vmTagbC9mF" else ""
    await async_send_log("👋 Nový člen na serveru", f"**Uživatel:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Datum připojení:** {get_prague_time().strftime('%d.%m.%Y %H:%M')}{link_info}", 0x10b981)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"{ctx.author.mention} ❌ **Špatný formát!** Zkontroluj si `!help`.", delete_after=15)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention} ❌ **Cíl nenalezen!**", delete_after=15)
    elif isinstance(error, commands.CheckFailure):
        pass 

@bot.command()
@check_web_sa()
async def setup_download(ctx):
    embed = discord.Embed(title="📥 Projekt OIS IDPK - Instalace", description="Vítejte v oficiálním instalačním průvodci.\n\nKliknutím na tlačítko níže zahájíte ověření účtu a generování osobního odkazu ke stažení.", color=0x38bdf8)
    await ctx.send(embed=embed, view=DynamicDownloadView())
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def auth(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
    db = get_db()
    if db:
        u = db.table("users").select("login_token").eq("discord_id", str(ctx.author.id)).execute().data
        if u and u[0].get('login_token'):
            await ctx.send(f"🛡️ {ctx.author.mention}, potvrďte přihlášení do aplikace:", view=AppAuthView(u[0]['login_token'], str(ctx.author.id), False), delete_after=60)
        else:
            msg = await ctx.send(f"❌ {ctx.author.mention} Nemáš čekající požadavek na přihlášení.")
            await asyncio.sleep(5)
            await msg.delete()

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Nápověda - Projekt OIS IDPK", description="Seznam dostupných příkazů rozdělený podle oprávnění.", color=0x38bdf8)
    embed.add_field(name="🌍 Veřejné příkazy", value="`!auth` - Potvrzení přihlášení do aplikace.\n`!ping` - Odezva bota.\n`!help` - Tato nápověda.", inline=False)
    embed.add_field(name="🛡️ Správa (SM)", value="`!info [ID]` - Profil.\n`!db [ID]` - 2FA do webu.\n`!ban`/`!unban [ID]` - BANY.\n`!delete [ID]` - Blokace.\n`!perdelete [ID]` - Úplné smazání.\n`!register [ID]` - Vytvoří účet cizímu.\n`!message #kanál [text]` - Zpráva přes bota.\n`!dm @uzivatel [text]` - Soukromá zpráva.", inline=False)
    embed.add_field(name="⚙️ Administrace (web-sa)", value="`!setup_download` - Generuje instalátor.\n`!sm @uživatel` - Přidá/odebere roli SM.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx): 
    await ctx.send(f"🏓 Pong! Odezva: **{round(bot.latency * 1000)}ms**.")

@bot.command()
async def info(ctx, discord_id: str = None):
    if not discord_id:
        return await ctx.send(f"❌ Zadejte ID.")
    db = get_db()
    if not db: return
    u = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not u:
        return await ctx.send(f"❌ Nenalezen.")
    embed = discord.Embed(title=f"Uživatel: {u[0].get('nick')}", color=0x38bdf8)
    embed.add_field(name="App ID", value=f"#{u[0].get('app_id')}", inline=True)
    embed.add_field(name="Discord ID", value=u[0].get('discord_id'), inline=True)
    embed.add_field(name="Role", value=u[0].get('role'), inline=True)
    embed.add_field(name="Banned", value="Ano" if u[0].get('is_banned') else "Ne", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@check_sm_role()
async def ban(ctx, discord_id: str):
    db = get_db()
    if not db:
        return
    user_data = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if not user_data:
        return await ctx.send("❌ Uživatel nenalezen.")
    db.table("users").update({"is_banned": True, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"🔨 Uživateli `{discord_id}` byl udělen BAN.")

@bot.command()
@check_sm_role()
async def unban(ctx, discord_id: str):
    db = get_db()
    if not db:
        return
    db.table("users").update({"is_banned": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"🕊️ Uživateli `{discord_id}` byl zrušen BAN.")

@bot.command()
@check_sm_role()
async def db(ctx, discord_id: str):
    db_conn = get_db()
    if not db_conn:
        return
    user_data = db_conn.table("users").select("dashboard_access").eq("discord_id", discord_id).execute().data
    if not user_data:
        return await ctx.send("❌ Uživatel nenalezen.")
    new_status = not user_data[0].get("dashboard_access", False)
    db_conn.table("users").update({"dashboard_access": new_status}).eq("discord_id", discord_id).execute()
    await ctx.send(f"⚙️ Přístup do DB pro ID `{discord_id}`: **{'POVOLEN ✅' if new_status else 'ODEBRÁN ❌'}**.")

@bot.command()
@check_sm_role()
async def delete(ctx, discord_id: str):
    db = get_db()
    if not db:
        return
    now = get_prague_time().strftime("%d.%m.%Y %H:%M")
    db.table("users").update({"is_deleted": True, "deleted_at": now, "dashboard_access": False}).eq("discord_id", discord_id).execute()
    await ctx.send(f"☠️ Účet `{discord_id}` byl smazán (Soft Delete).")

@bot.command()
@check_sm_role()
async def perdelete(ctx, discord_id: str):
    embed = discord.Embed(title="⚠️ Varování: Permanentní smazání", description=f"Opravdu chceš nevratně smazat účet `{discord_id}` z databáze?", color=0xef4444)
    await ctx.send(embed=embed, view=PerDeleteConfirm(discord_id, ctx.author.id))

@bot.command()
async def register(ctx, target_id: str = None):
    db = get_db()
    if not db:
        return await ctx.send("❌ Databáze nedostupná.")
    if target_id:
        is_admin = discord.utils.get(ctx.author.roles, name="web-sa") or discord.utils.get(ctx.author.roles, name="SM") or ctx.author.guild_permissions.administrator
        if not is_admin:
            return await ctx.send(f"❌ {ctx.author.mention} Nemáš oprávnění.")
        discord_id = target_id
        target_member = ctx.guild.get_member(int(discord_id)) if discord_id.isdigit() else None
        nick = target_member.display_name if target_member else f"Uživatel {discord_id}"
    else:
        discord_id = str(ctx.author.id)
        nick = ctx.author.display_name
        target_member = ctx.author
        
    now_str = get_prague_time().strftime("%d.%m.%Y %H:%M")
    check = db.table("users").select("*").eq("discord_id", discord_id).execute().data
    if check:
        if check[0].get('is_banned'):
            return await ctx.send("❌ Tento účet má BAN.")
        elif check[0].get('is_deleted'):
            highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
            new_app_id = highest[0]["app_id"] + 1 if highest else 1000
            db.table("users").update({"app_id": new_app_id, "nick": nick, "is_deleted": False, "deleted_at": "", "registered_at": now_str}).eq("discord_id", discord_id).execute()
            await ctx.send(f"✅ Smazaný účet byl úspěšně obnoven! Nové App ID je **#{new_app_id}**.")
            if target_member:
                await update_member_roles(target_member, check[0].get('role', 'User'))
        else:
            await ctx.send(f"ℹ️ Tento uživatel již je zaregistrován!")
    else:
        highest = db.table("users").select("app_id").order("app_id", desc=True).limit(1).execute().data
        new_app_id = highest[0]["app_id"] + 1 if highest else 1000
        db.table("users").insert({ "app_id": new_app_id, "discord_id": discord_id, "nick": nick, "role": "User", "hwid": "", "is_banned": False, "is_deleted": False, "deleted_at": "", "dashboard_access": False, "login_token": "", "registered_at": now_str }).execute()
        await ctx.send(f"✅ Úspěšně zaregistrován! App ID: **#{new_app_id}**.")

@bot.command()
@check_web_sa()
async def sm(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="SM")
    if not role:
        return await ctx.send("❌ Role `SM` neexistuje.")
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"➖ Role **SM** odebrána.")
    else:
        await member.add_roles(role)
        await ctx.send(f"➕ Role **SM** přidělena.")

@bot.command()
@check_sm_role()
async def message(ctx, channel: discord.TextChannel, *, text: str):
    try:
        await channel.send(text)
        await ctx.send(f"✅ Odesláno.")
    except:
        await ctx.send("❌ Nemám oprávnění.")

@bot.command()
@check_sm_role()
async def dm(ctx, member: discord.Member, *, text: str):
    try:
        await member.send(embed=discord.Embed(title="Zpráva od administrace", description=text, color=0x38bdf8))
        await ctx.send(f"✅ Odesláno.")
    except:
        await ctx.send("❌ Zablokované SZ.")

def run_web():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    Thread(target=run_web).start()
    if token:
        bot.run(token)
    else:
        print("KRITICKÁ CHYBA: DISCORD_TOKEN není nastaven v environment variables! (Web běží dál bez Bota)")
