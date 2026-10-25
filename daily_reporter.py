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
            if error and len(self.data["web_error_samples"]) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data["web_error_samples"].append(f"[{ts}] {path} -> {error}")
        # Uložit periodicky každých 25 požadavků
        if self.data["web_requests_total"] % 25 == 0:
            self._save()

    def record_map_tick(self, active_count, bug_count=0, spz_conflict=False):
        self._check_day_rollover()
        self.data["map_inflow_ticks"] += 1
        if active_count > self.data["map_peak_buses"]:
            self.data["map_peak_buses"] = active_count
        if bug_count > 0:
            self.data["map_bug_errors"] += bug_count
        if spz_conflict:
            self.data["map_spz_conflicts"] += 1
        if self.data["map_inflow_ticks"] % 10 == 0:
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
            if error and len(self.data["notif_error_samples"]) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data["notif_error_samples"].append(f"[{ts}] {channel}: {error}")
        self._save()

    def record_download(self, success, error=None):
        self._check_day_rollover()
        if success:
            self.data["app_downloads_success"] += 1
        else:
            self.data["app_downloads_failed"] += 1
            if error and len(self.data["app_crash_samples"]) < 10:
                ts = get_prague_now().strftime("%H:%M:%S")
                self.data["app_crash_samples"].append(f"[{ts}] Download error: {error}")
        self._save()

    def record_app_error(self, nick, error_type, msg):
        self._check_day_rollover()
        self.data["app_crashes_reported"] += 1
        if len(self.data["app_crash_samples"]) < 10:
            ts = get_prague_now().strftime("%H:%M:%S")
            self.data["app_crash_samples"].append(f"[{ts}] {nick} ({error_type}): {msg[:100]}")
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


def compute_system_health(metrics_data):
    """Vypočítá procentuální úspěšnost jednotlivých komponent a celkový index zdraví."""
    # 1. Web & API
    web_tot = metrics_data.get("web_requests_total", 0)
    web_err = metrics_data.get("web_server_errors", 0)
    if web_tot > 0:
        web_pct = max(0.0, min(100.0, round(((web_tot - web_err) / web_tot) * 100.0, 1)))
    else:
        web_pct = 100.0

    # 2. Mapa & GPS
    map_ticks = metrics_data.get("map_inflow_ticks", 0)
    map_bugs = metrics_data.get("map_bug_errors", 0)
    peak_buses = max(1, metrics_data.get("map_peak_buses", 1))
    if map_ticks > 0:
        # Penalizace za BUG autobusy poměrně k provozu
        bug_ratio = map_bugs / (map_ticks * peak_buses)
        map_pct = max(0.0, min(100.0, round((1.0 - min(bug_ratio * 10, 0.5)) * 100.0, 1)))
    else:
        map_pct = 100.0

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

    # 5. Databáze & Supabase
    db_ok = metrics_data.get("db_ops_ok", 0)
    db_fail = metrics_data.get("db_ops_failed", 0)
    db_tot = db_ok + db_fail
    if db_tot > 0:
        db_pct = max(0.0, min(100.0, round((db_ok / db_tot) * 100.0, 1)))
    else:
        db_pct = 100.0

    # Celkové skóre (vážený průměr)
    overall_pct = round(
        (web_pct * 0.30) + (map_pct * 0.30) + (notif_pct * 0.15) + (app_pct * 0.15) + (db_pct * 0.10),
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
    """Sestaví kompletní denní report se statistikami, procenty a AI textovým zhodnocením."""
    if metrics_data is None:
        metrics_data = TRACKER.data

    date_str = metrics_data.get("date", get_prague_now().strftime("%Y-%m-%d"))
    health = compute_system_health(metrics_data)
    overall = health["overall_pct"]

    # Hodnocení stavu
    if overall >= 98.0:
        grade_text = "VYNIKAJÍCÍ 🟢"
        color = 0x10b981  # Emerald green
    elif overall >= 90.0:
        grade_text = "VELMI DOBRÝ 🔵"
        color = 0x38bdf8  # Sky blue
    elif overall >= 75.0:
        grade_text = "USPOKOJIVÝ S VÝHRADAMI 🟠"
        color = 0xf59e0b  # Amber
    else:
        grade_text = "KRITICKÝ / VYŽADUJE POZORNOST 🔴"
        color = 0xef4444  # Red

    # Sestavení bodů co fungovalo a co selhalo
    good_points = []
    bad_points = []

    # Web
    web_ok = metrics_data.get("web_requests_ok", 0)
    web_err = metrics_data.get("web_server_errors", 0)
    if health["web_pct"] >= 99.0:
        good_points.append(f"Webové rozhraní a API běžely bez zaváhání ({web_ok} úspěšných požadavků).")
    elif health["web_pct"] >= 90.0:
        good_points.append(f"Většina webových požadavků proběhla v pořádku ({web_ok} OK).")
    if web_err > 0:
        bad_points.append(f"Web zaznamenal {web_err}x interní chybu serveru (HTTP 500).")

    # Mapa
    map_ticks = metrics_data.get("map_inflow_ticks", 0)
    peak_buses = metrics_data.get("map_peak_buses", 0)
    map_bugs = metrics_data.get("map_bug_errors", 0)
    if map_ticks > 0 and map_bugs == 0:
        good_points.append(f"Interaktivní mapa měla bezchybný provoz (špička {peak_buses} vozů, 0 BUG stavů).")
    elif map_ticks > 0:
        good_points.append(f"Live sledování aktivní s {map_ticks} synchronizačními cykly (špička {peak_buses} vozů).")
    if map_bugs > 0:
        bad_points.append(f"Na mapě bylo zachyceno {map_bugs} vozů v nevalidním/BUG stavu (ztráta GPS či duplicitní SPZ).")

    # Notifikace
    notif_d = metrics_data.get("notif_sent_discord", 0)
    notif_e = metrics_data.get("notif_sent_email", 0)
    notif_fail = metrics_data.get("notif_failed", 0)
    if (notif_d + notif_e) > 0 and notif_fail == 0:
        good_points.append(f"Odesílání oznámení fungovalo na 100 % ({notif_d} přes Discord DM, {notif_e} přes E-mail).")
    elif (notif_d + notif_e) > 0:
        good_points.append(f"Doručeno {notif_d + notif_e} upozornění uživatelům.")
    if notif_fail > 0:
        bad_points.append(f"{notif_fail} notifikací se nepodařilo doručit (chyba Discord API nebo SMTP).")

    # Aplikace / Stahování
    dl_ok = metrics_data.get("app_downloads_success", 0)
    dl_fail = metrics_data.get("app_downloads_failed", 0)
    app_crashes = metrics_data.get("app_crashes_reported", 0)
    if dl_ok > 0 and dl_fail == 0 and app_crashes == 0:
        good_points.append(f"Klient a launcher běžely spolehlivě ({dl_ok} bezchybných stažení, 0 chyb).")
    elif dl_ok > 0:
        good_points.append(f"Úspěšně staženo {dl_ok} instalačních balíčků.")
    if dl_fail > 0:
        bad_points.append(f"Došlo k {dl_fail} přerušeným nebo selhaným stahováním launcheru.")
    if app_crashes > 0:
        bad_points.append(f"Aplikace nahlásila {app_crashes} pádů či výjimek.")

    # Databáze
    db_fail = metrics_data.get("db_ops_failed", 0)
    if db_fail == 0:
        good_points.append("Spojení s cloudovou databází Turso a synchronizace GTFS probíhaly bez přerušení.")
    else:
        bad_points.append(f"Zaznamenáno {db_fail} chyb spojení s databází Turso.")

    if not good_points:
        good_points.append("Základní procesy běžely bez zaznamenaných havárií.")
    if not bad_points:
        bad_points.append("Nebyly nalezeny žádné kritické chyby.")

    # AI textové shrnutí
    prompt = (
        f"Jsi technický asistent systému OIS IDPK / DataCoreBot. "
        f"Napiš stručné (2-3 věty) srozumitelné české hodnocení denního provozu dne {date_str}. "
        f"Celková spolehlivost: {overall} %. Web: {health['web_pct']} %, Mapa: {health['map_pct']} %, "
        f"Notifikace: {health['notif_pct']} %, Aplikace/Stahování: {health['app_pct']} %. "
        f"Klady: {'; '.join(good_points)}. Závady: {'; '.join(bad_points)}. "
        f"Napiš to věcně, přátelsky a přímočaře."
    )
    ai_text = call_ai_narrator(prompt)
    if not ai_text:
        # Vestavěný inteligentní generátor
        if overall >= 95.0:
            ai_text = (
                f"Systém dnes pracoval ve výtečné kondici se spolehlivostí {overall} %. "
                f"Interaktivní mapa i doručování oznámení běžely hladce a uživatelé nezaznamenali žádné podstatné výpadky. "
                f"Provoz všech klíčových služeb byl stabilní."
            )
        elif overall >= 85.0:
            ai_text = (
                f"Systém dnes dosáhl solidní spolehlivosti {overall} %. "
                f"Většina subsystémů fungovala korektně, avšak objevily se drobné komplikace "
                f"({bad_points[0] if bad_points else 'ojedinělé chyby'}). Doporučujeme sledovat stabilitu."
            )
        else:
            ai_text = (
                f"Dnešní spolehlivost systému klesla na {overall} %. "
                f"Během dne došlo k několika vážnějším chybám, zejména: {bad_points[0] if bad_points else 'výpadky služeb'}. "
                f"Doporučujeme kontrolu logů a restart zasažených komponent."
            )

    # Discord Embed struktura
    embed = {
        "title": f"📊 Denní Systémový Report – {date_str}",
        "description": f"🤖 **AI Diagnostika celkového stavu:** **{overall} %** ({grade_text})\n\n*{ai_text}*",
        "color": color,
        "fields": [
            {
                "name": "📈 Spolehlivost Subsystémů",
                "value": (
                    f"• 🌐 **Web & API:** `{health['web_pct']} %`\n"
                    f"• 🗺️ **Mapa & GPS data:** `{health['map_pct']} %`\n"
                    f"• 🔔 **Oznámení & Zvonky:** `{health['notif_pct']} %`\n"
                    f"• 📲 **Aplikace & Stahování:** `{health['app_pct']} %`\n"
                    f"• 🗄️ **Databáze & Synchronizace:** `{health['db_pct']} %`"
                ),
                "inline": False,
            },
            {
                "name": "✅ Co fungovalo",
                "value": "\n".join(f"• {pt}" for pt in good_points[:4]),
                "inline": False,
            },
            {
                "name": "⚠️ Kde byly chyby",
                "value": "\n".join(f"• {pt}" for pt in bad_points[:4]),
                "inline": False,
            },
            {
                "name": "🔢 Provozní Čísla Dne",
                "value": (
                    f"Požadavky: **{web_ok + web_err}** (chyby 500: {web_err}) | "
                    f"Max vozů: **{peak_buses}** | "
                    f"Notifikace: **{notif_d + notif_e}** | "
                    f"Stažení: **{dl_ok}**"
                ),
                "inline": False,
            }
        ],
        "footer": {"text": "DataCoreBot • Automatický denní AI audit"},
    }

    # Plain text verze pro terminál / logger
    text_log = (
        f"=== DENNÍ SYSTÉMOVÝ REPORT ({date_str}) ===\n"
        f"Celková spolehlivost: {overall}% ({grade_text})\n"
        f"Web/API: {health['web_pct']}% | Mapa: {health['map_pct']}% | Notifikace: {health['notif_pct']}% | App: {health['app_pct']}%\n"
        f"AI Hodnocení: {ai_text}\n"
        f"Co fungovalo: {'; '.join(good_points)}\n"
        f"Kde byly chyby: {'; '.join(bad_points)}\n"
        f"==========================================="
    )

    return {
        "date": date_str,
        "health": health,
        "ai_summary": ai_text,
        "good_points": good_points,
        "bad_points": bad_points,
        "embed": embed,
        "text_log": text_log,
        "metrics": metrics_data,
    }
