import os
import json
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

METRICS_FILE = os.path.join(os.path.dirname(__file__), "daily_metrics.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "daily_reports_history.json")


def get_prague_now():
    try:
        return datetime.now(ZoneInfo("Europe/Prague"))
    except Exception:
        return datetime.now()


class DailyMetricsTracker:
    def __init__(self):
        self.current_date = get_prague_now().strftime("%Y-%m-%d")
        self.data = self._default_data(self.current_date)
        self._load()

    def _default_data(self, date_str):
        return {
            "date": date_str,
            "created_at": get_prague_now().strftime("%Y-%m-%d %H:%M:%S"),
            "web_requests_total": 0,
            "web_requests_ok": 0,
            "web_client_errors": 0,
            "web_server_errors": 0,
            "web_error_samples": [],
            "map_inflow_ticks": 0,
            "map_peak_buses": 0,
            "map_bug_errors": 0,
            "map_spz_conflicts": 0,
            "map_crashes": 0,
            "map_crash_samples": [],
            "notif_evaluated": 0,
            "notif_sent_discord": 0,
            "notif_sent_email": 0,
            "notif_failed": 0,
            "notif_error_samples": [],
            "app_downloads_success": 0,
            "app_downloads_failed": 0,
            "app_crashes_reported": 0,
            "app_crash_samples": [],
            "db_ops_ok": 0,
            "db_ops_failed": 0,
        }

    def _check_day_rollover(self):
        today = get_prague_now().strftime("%Y-%m-%d")
        if self.current_date != today:
            # Uložit do historie
            self._archive_current()
            self.current_date = today
            self.data = self._default_data(today)
            self._save()

    def _load(self):
        try:
            if os.path.exists(METRICS_FILE):
                with open(METRICS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if saved.get("date") == self.current_date:
                        self.data.update(saved)
                    else:
                        self._archive_data(saved)
        except Exception as e:
            print(f"[METRICS] Chyba pri nacitani daily_metrics: {e}", flush=True)

    def _save(self):
        try:
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[METRICS] Chyba pri zapisu daily_metrics: {e}", flush=True)

    def _archive_current(self):
        self._archive_data(self.data)

    def _archive_data(self, old_data):
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            # Zachovat max 30 dnu historie
            history = [h for h in history if h.get("date") != old_data.get("date")]
            history.append(old_data)
            history = history[-30:]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[METRICS] Chyba pri archivaci: {e}", flush=True)

    def record_request(self, status_code, path, error=None):
        self._check_day_rollover()
        self.data["web_requests_total"] += 1
        if 200 <= status_code < 400:
            self.data["web_requests_ok"] += 1
        elif 400 <= status_code < 500:
            self.data["web_client_errors"] += 1
        else:
            self.data["web_server_errors"] += 1
            if error and len(self.data.get("web_error_samples", [])) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data.setdefault("web_error_samples", []).append(f"[{ts}] {path} -> {error}")
        if self.data["web_requests_total"] % 25 == 0:
            self._save()

    def record_client_error(self):
        self._check_day_rollover()
        self.data["web_client_errors"] = self.data.get("web_client_errors", 0) + 1

    def record_map_tick(self, active_count, bug_count=0, spz_conflict=False):
        self._check_day_rollover()
        self.data["map_inflow_ticks"] += 1
        if active_count > self.data.get("map_peak_buses", 0):
            self.data["map_peak_buses"] = active_count
        if bug_count > 0:
            self.data["map_bug_errors"] = self.data.get("map_bug_errors", 0) + bug_count
        if spz_conflict:
            self.data["map_spz_conflicts"] = self.data.get("map_spz_conflicts", 0) + 1
        if self.data["map_inflow_ticks"] % 10 == 0:
            self._save()

    def record_map_crash(self, error_msg):
        self._check_day_rollover()
        self.data["map_crashes"] = self.data.get("map_crashes", 0) + 1
        samples = self.data.setdefault("map_crash_samples", [])
        if len(samples) < 10:
            ts = get_prague_now().strftime("%H:%M:%S")
            samples.append(f"[{ts}] {str(error_msg)[:120]}")
        self._save()

    def record_notification(self, channel, success, error=None):
        self._check_day_rollover()
        self.data["notif_evaluated"] += 1
        if success:
            if channel == "discord":
                self.data["notif_sent_discord"] += 1
            elif channel == "email":
                self.data["notif_sent_email"] += 1
        else:
            self.data["notif_failed"] += 1
            if error and len(self.data.get("notif_error_samples", [])) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data.setdefault("notif_error_samples", []).append(f"[{ts}] {channel}: {error}")
        self._save()

    def record_download(self, success, error=None):
        self._check_day_rollover()
        if success:
            self.data["app_downloads_success"] += 1
        else:
            self.data["app_downloads_failed"] += 1
            if error and len(self.data.get("app_crash_samples", [])) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data.setdefault("app_crash_samples", []).append(f"[{ts}] Download error: {error}")
        self._save()

    def record_app_error(self, nick, error_type, msg):
        self._check_day_rollover()
        self.data["app_crashes_reported"] += 1
        if len(self.data.get("app_crash_samples", [])) < 10:
            ts = get_prague_now().strftime("%H:%M:%S")
            self.data.setdefault("app_crash_samples", []).append(f"[{ts}] {nick} ({error_type}): {msg[:100]}")
        self._save()

    def record_db_op(self, success, error=None):
        self._check_day_rollover()
        if success:
            self.data["db_ops_ok"] += 1
        else:
            self.data["db_ops_failed"] += 1
            if self.data["db_ops_failed"] % 5 == 0:
                self._save()


# Globální instance trackeru
TRACKER = DailyMetricsTracker()


def get_live_database_status():
    """Získá reálný stav obou databází: Turso a Cloudflare D1 (žádné vymyšlené hodnoty)."""
    status = {
        "turso_reads": 0,
        "turso_blocked": False,
        "turso_reason": "",
        "d1_available": False,
        "d1_counts": {}
    }
    # Turso stav z turso_budget.json
    try:
        budget_path = os.path.join(os.path.dirname(__file__), "turso_budget.json")
        if os.path.exists(budget_path):
            with open(budget_path, "r", encoding="utf-8") as f:
                b_data = json.load(f)
                status["turso_reads"] = b_data.get("row_reads", 0)
                status["turso_blocked"] = b_data.get("blocked", False)
                status["turso_reason"] = b_data.get("blocked_reason", "")
    except Exception as e:
        status["turso_reason"] = str(e)
    
    # Cloudflare D1 stav
    try:
        import cloudflare_d1
        if cloudflare_d1.is_d1_available():
            status["d1_available"] = True
            client = cloudflare_d1.get_d1_client()
            r_dep = client.execute("SELECT COUNT(*) as c FROM depot_history")
            r_trip = client.execute("SELECT COUNT(*) as c FROM bus_trips")
            r_spz = client.execute("SELECT COUNT(*) as c FROM spz_registry")
            status["d1_counts"] = {
                "depot_history": r_dep[0].get("c", 0) if r_dep else 0,
                "bus_trips": r_trip[0].get("c", 0) if r_trip else 0,
                "spz_registry": r_spz[0].get("c", 0) if r_spz else 0
            }
    except Exception:
        status["d1_available"] = False
    
    return status


def compute_system_health(metrics_data, db_status=None):
    """Vypočítá procentuální úspěšnost jednotlivých komponent a celkový index zdraví."""
    # 1. Web & API
    web_tot = metrics_data.get("web_requests_total", 0)
    web_err = metrics_data.get("web_server_errors", 0)
    if web_tot > 0:
        web_pct = max(0.0, min(100.0, round(((web_tot - web_err) / web_tot) * 100.0, 1)))
    else:
        web_pct = 100.0

    # 2. Mapa & GPS (zohledňujeme skutečné pády smyčky!)
    map_ticks = metrics_data.get("map_inflow_ticks", 0)
    map_bugs = metrics_data.get("map_bug_errors", 0)
    map_crashes = metrics_data.get("map_crashes", 0)
    peak_buses = max(1, metrics_data.get("map_peak_buses", 1))
    if map_crashes > 0:
        # Každý pád workeru znamená vážný problém s během mapy
        crash_penalty = min(60.0, map_crashes * 10.0)
        map_pct = max(0.0, round(100.0 - crash_penalty - (map_bugs * 0.5), 1))
    elif map_ticks > 0:
        bug_ratio = map_bugs / (map_ticks * peak_buses)
        map_pct = max(50.0, min(100.0, round((1.0 - min(bug_ratio * 10, 0.5)) * 100.0, 1)))
    else:
        map_pct = 0.0 if map_crashes > 0 else 100.0

    # 3. Notifikace
    notif_sent = metrics_data.get("notif_sent_discord", 0) + metrics_data.get("notif_sent_email", 0)
    notif_fail = metrics_data.get("notif_failed", 0)
    notif_tot = notif_sent + notif_fail
    if notif_tot > 0:
        notif_pct = max(0.0, min(100.0, round((notif_sent / notif_tot) * 100.0, 1)))
    else:
        notif_pct = 100.0

    # 4. Aplikace & Stahování
    dl_ok = metrics_data.get("app_downloads_success", 0)
    dl_fail = metrics_data.get("app_downloads_failed", 0)
    app_errs = metrics_data.get("app_crashes_reported", 0)
    app_tot = dl_ok + dl_fail + app_errs
    if app_tot > 0:
        app_pct = max(0.0, min(100.0, round((dl_ok / max(1, app_tot)) * 100.0, 1)))
    else:
        app_pct = 100.0

    # 5. Databáze (reálné zhodnocení včetně Turso quota / D1)
    if db_status is None:
        db_status = get_live_database_status()
    db_ok = metrics_data.get("db_ops_ok", 0)
    db_fail = metrics_data.get("db_ops_failed", 0)
    db_tot = db_ok + db_fail
    if db_status.get("turso_blocked"):
        # Pokud Turso blokuje zápisy, DB zdraví nemůže být 100 %
        db_pct = 70.0 if db_status.get("d1_available") else 40.0
    elif db_tot > 0:
        db_pct = max(0.0, min(100.0, round((db_ok / db_tot) * 100.0, 1)))
    else:
        db_pct = 100.0 if db_status.get("d1_available") else 80.0

    # Celkové skóre (vážený průměr)
    overall_pct = round(
        (web_pct * 0.25) + (map_pct * 0.35) + (notif_pct * 0.15) + (app_pct * 0.10) + (db_pct * 0.15),
        1
    )

    return {
        "overall_pct": overall_pct,
        "web_pct": web_pct,
        "map_pct": map_pct,
        "notif_pct": notif_pct,
        "app_pct": app_pct,
        "db_pct": db_pct,
    }


def call_ai_narrator(summary_prompt):
    """Pokusí se zavolat Google Gemini / AI pokud je nastaven klíč v prostředí."""
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gemini_key:
        return None

    try:
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": summary_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[AI REPORT] Selhalo volání externí AI API: {e}", flush=True)
        return None


def generate_ai_daily_report(metrics_data=None):
    """Sestaví kompletní denní report se statistikami, limity databází a upřímným technickým zhodnocením."""
    if metrics_data is None:
        metrics_data = TRACKER.data

    date_str = metrics_data.get("date", get_prague_now().strftime("%Y-%m-%d"))
    db_status = get_live_database_status()
    health = compute_system_health(metrics_data, db_status=db_status)
    overall = health["overall_pct"]

    # Hodnocení stavu
    if overall >= 95.0 and not db_status.get("turso_blocked") and metrics_data.get("map_crashes", 0) == 0:
        grade_text = "VYNIKAJÍCÍ 🟢"
        color = 0x10b981
    elif overall >= 85.0:
        grade_text = "PROVOZUSCHOPNÝ S OMEZENÍM 🔵"
        color = 0x38bdf8
    elif overall >= 65.0:
        grade_text = "USPOKOJIVÝ / POZORNOST NUTNÁ 🟠"
        color = 0xf59e0b
    else:
        grade_text = "KRITICKÝ / DETEKOVÁNY CHYBY 🔴"
        color = 0xef4444

    good_points = []
    bad_points = []

    # 1. Databáze (reálné hodnoty)
    t_reads = db_status.get("turso_reads", 0)
    if db_status.get("turso_blocked"):
        bad_points.append(f"Turso DB: Zápisy jsou blokovány (vyčerpána kvóta bezplatného plánu). Přečteno: {t_reads:,} řádků.")
    else:
        good_points.append(f"Turso DB: Čtení v pořádku ({t_reads:,} řádků za tento měsíc).")

    if db_status.get("d1_available"):
        d1_c = db_status.get("d1_counts", {})
        good_points.append(f"Cloudflare D1: Plně funkční ({d1_c.get('depot_history', 0)} záznamů vozoven, {d1_c.get('bus_trips', 0)} spojů, {d1_c.get('spz_registry', 0)} SPZ).")
    else:
        bad_points.append("Cloudflare D1: Databáze není dostupná nebo selhalo spojení!")

    # 2. Interaktivní mapa (reálné pády smyčky)
    map_ticks = metrics_data.get("map_inflow_ticks", 0)
    peak_buses = metrics_data.get("map_peak_buses", 0)
    map_bugs = metrics_data.get("map_bug_errors", 0)
    map_crashes = metrics_data.get("map_crashes", 0)
    map_crash_samples = metrics_data.get("map_crash_samples", [])

    if map_crashes > 0:
        sample_txt = f" (např. {map_crash_samples[-1]})" if map_crash_samples else ""
        bad_points.append(f"Mapa: Smyčka workeru spadla {map_crashes}x{sample_txt}.")
    elif map_ticks > 0:
        good_points.append(f"Mapa: Běžela stabilně bez pádů ({map_ticks} cyklů, maximum {peak_buses} vozů online).")
    else:
        bad_points.append("Mapa: Nebyly zaznamenány žádné synchronizační cykly (worker možná stál).")

    if map_bugs > 0:
        bad_points.append(f"Mapa: Zachyceno {map_bugs} autobusů v nevalidním stavu.")

    # 3. Web & API
    web_ok = metrics_data.get("web_requests_ok", 0)
    web_err = metrics_data.get("web_server_errors", 0)
    web_samples = metrics_data.get("web_error_samples", [])
    if web_ok > 0 and web_err == 0:
        good_points.append(f"Web & API: Všech {web_ok} požadavků odbaveno úspěšně.")
    elif web_ok > 0:
        good_points.append(f"Web & API: Odbaveno {web_ok} úspěšných požadavků.")
    if web_err > 0:
        sample_w = f" (např. {web_samples[-1]})" if web_samples else ""
        bad_points.append(f"Web: Zaznamenáno {web_err}x HTTP 500 chyba serveru{sample_w}.")

    # 4. Notifikace
    notif_d = metrics_data.get("notif_sent_discord", 0)
    notif_e = metrics_data.get("notif_sent_email", 0)
    notif_fail = metrics_data.get("notif_failed", 0)
    if (notif_d + notif_e) > 0:
        good_points.append(f"Notifikace: Úspěšně odesláno {notif_d} přes Discord a {notif_e} přes E-mail.")
    if notif_fail > 0:
        bad_points.append(f"Notifikace: {notif_fail} oznámení selhalo při doručení.")

    # 5. Launcher & Aplikace
    dl_ok = metrics_data.get("app_downloads_success", 0)
    dl_fail = metrics_data.get("app_downloads_failed", 0)
    app_crashes = metrics_data.get("app_crashes_reported", 0)
    if dl_ok > 0:
        good_points.append(f"Launcher: Hráči úspěšně stáhli {dl_ok} herních balíčků.")
    if dl_fail > 0:
        bad_points.append(f"Launcher: {dl_fail} stahování selhalo nebo bylo přerušeno.")
    if app_crashes > 0:
        bad_points.append(f"Aplikace: Hlášeno {app_crashes} pádů softwaru od uživatelů.")

    if not good_points:
        good_points.append("Základní procesy serveru jsou spuštěné.")
    if not bad_points:
        bad_points.append("Nebyly zaznamenány žádné kritické výpadky.")

    # Upřímné technické AI shrnutí
    prompt = (
        f"Jsi technický asistent systému OIS IDPK / DataCoreBot. "
        f"Napiš věcné, upřímné a technicky přesné zhodnocení provozu dne {date_str} (2-3 věty). "
        f"Neklam, nic si nevymýšlej. Pokud něco selhalo nebo jsou limity, přímo to uveď. "
        f"Celková spolehlivost: {overall} %. Web: {health['web_pct']} %, Mapa: {health['map_pct']} %, "
        f"Databáze: {health['db_pct']} %. "
        f"Klady: {'; '.join(good_points)}. "
        f"Nedostatky/závady: {'; '.join(bad_points)}."
    )
    ai_text = call_ai_narrator(prompt)
    if not ai_text:
        # Upřímný vestavěný generátor (žádné lži o 100% bezchybnosti pokud jsou problémy)
        if overall >= 95.0 and not db_status.get("turso_blocked") and map_crashes == 0:
            ai_text = (
                f"Systém dnes běžel stabilně se spolehlivostí {overall} %. "
                f"Interaktivní mapa i web fungovaly plynule a bez pádů smyček. Provoz databází je v normě."
            )
        elif db_status.get("turso_blocked") or map_crashes > 0:
            issues = []
            if db_status.get("turso_blocked"):
                issues.append("Turso databáze má zablokované zápisy (přesunuto na Cloudflare D1)")
            if map_crashes > 0:
                issues.append(f"smyčka mapy zaznamenala {map_crashes} pádů")
            if web_err > 0:
                issues.append(f"web měl {web_err} chyb 500")
            issues_str = ", ".join(issues) if issues else "ojedinělé výpadky"
            ai_text = (
                f"Dnešní spolehlivost dosáhla {overall} %. V provozu se projevila technická omezení: {issues_str}. "
                f"Doporučujeme sledovat stabilitu a stav databází."
            )
        else:
            ai_text = (
                f"Systém dnes dosáhl provozní spolehlivosti {overall} %. "
                f"Klíčové služby fungovaly, ale je třeba věnovat pozornost hlášeným chybám v logu."
            )

    # Turso status řádek
    turso_line = f"Čtení: `{t_reads:,}` řádků | Zápisy: " + ("`⛔ ZABLOKOVÁNY`" if db_status.get("turso_blocked") else "`🟢 V NORMĚ`")
    d1_c = db_status.get("d1_counts", {})
    d1_line = f"`🟢 AKTIVNÍ` (Vozovny: {d1_c.get('depot_history', 0)}, Spoje: {d1_c.get('bus_trips', 0)}, SPZ: {d1_c.get('spz_registry', 0)})" if db_status.get("d1_available") else "`🔴 NEDOSTUPNÁ`"

    embed = {
        "title": f"📊 Denní Systémový Report – {date_str}",
        "description": f"🤖 **Diagnostika celkového stavu:** **{overall} %** ({grade_text})\n\n*{ai_text}*",
        "color": color,
        "fields": [
            {
                "name": "💾 Stav Databází & Limity",
                "value": (
                    f"• **Turso DB:** {turso_line}\n"
                    f"• **Cloudflare D1:** {d1_line}"
                ),
                "inline": False,
            },
            {
                "name": "📈 Spolehlivost Subsystémů",
                "value": (
                    f"• 🌐 **Web & API:** `{health['web_pct']} %`\n"
                    f"• 🗺️ **Mapa & GPS data:** `{health['map_pct']} %` (Pády smyčky: `{map_crashes}`)\n"
                    f"• 🔔 **Oznámení & Zvonky:** `{health['notif_pct']} %`\n"
                    f"• 📲 **Aplikace & Stahování:** `{health['app_pct']} %`\n"
                    f"• 🗄️ **Databáze:** `{health['db_pct']} %`"
                ),
                "inline": False,
            },
            {
                "name": "✅ Co fungovalo",
                "value": "\n".join(f"• {pt}" for pt in good_points[:4]),
                "inline": False,
            },
            {
                "name": "⚠️ Nedostatky a chyby",
                "value": "\n".join(f"• {pt}" for pt in bad_points[:4]),
                "inline": False,
            },
            {
                "name": "🔢 Provozní Čísla Dne",
                "value": (
                    f"Max busů: **{peak_buses}** | "
                    f"Cykly mapy: **{map_ticks}** | "
                    f"Pády mapy: **{map_crashes}** | "
                    f"Web dotazy: **{web_ok + web_err}** (500: **{web_err}**)"
                ),
                "inline": False,
            }
        ],
        "footer": {"text": "DataCoreBot • Reálný technický denní audit"},
    }

    text_log = (
        f"=== DENNÍ SYSTÉMOVÝ REPORT ({date_str}) ===\n"
        f"Celková spolehlivost: {overall}% ({grade_text})\n"
        f"Turso: {turso_line} | D1: {d1_line}\n"
        f"Mapa: {map_ticks} cyklů, {map_crashes} pádů, max {peak_buses} busů\n"
        f"Diagnostika: {ai_text}\n"
        f"Klady: {'; '.join(good_points)}\n"
        f"Nedostatky: {'; '.join(bad_points)}\n"
        f"==========================================="
    )

    return {
        "date": date_str,
        "health": health,
        "ai_summary": ai_text,
        "good_points": good_points,
        "bad_points": bad_points,
        "db_status": db_status,
        "embed": embed,
        "text_log": text_log,
        "metrics": metrics_data,
    }
