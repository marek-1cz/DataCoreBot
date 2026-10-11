import json
import uuid
import time
from datetime import datetime
from zoneinfo import ZoneInfo

def get_prague_now_str():
    return datetime.now(ZoneInfo("Europe/Prague")).strftime("%d.%m.%Y %H:%M")

def parse_device_info(ua_string: str) -> dict:
    ua = (ua_string or "").strip()
    if not ua:
        return {"name": "Neznámé zařízení", "icon": "fa-desktop"}
    
    # OS
    os_name = "Neznámý OS"
    if "iPhone" in ua:
        os_name = "iPhone"
    elif "iPad" in ua:
        os_name = "iPad"
    elif "Android" in ua:
        os_name = "Android"
    elif "Windows NT 10.0" in ua or "Windows NT 11.0" in ua:
        os_name = "Windows"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Macintosh" in ua or "Mac OS" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"

    # Browser
    browser = "Web"
    if "Edg/" in ua or "Edge/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "Chrome/" in ua and "Android" not in ua and "Mobile" not in ua:
        browser = "Chrome"
    elif "Chrome/" in ua:
        browser = "Chrome"
    elif "Safari/" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Firefox/" in ua:
        browser = "Firefox"

    # Device type & icon
    if "iPhone" in ua or ("Android" in ua and "Mobile" in ua):
        dev_type = "Mobil"
        icon = "fa-mobile-alt"
    elif "iPad" in ua or ("Android" in ua and "Mobile" not in ua):
        dev_type = "Tablet"
        icon = "fa-tablet-alt"
    elif os_name in ("Windows", "macOS", "Linux"):
        dev_type = "Počítač"
        icon = "fa-laptop"
    else:
        dev_type = "Zařízení"
        icon = "fa-desktop"

    name = f"{dev_type} ({os_name} • {browser})"
    return {"name": name, "icon": icon}


def get_user_sessions(user_or_token) -> list:
    """Vrátí seznam aktivních relací pro daného uživatele (přijímá user dict nebo surový string)."""
    if not user_or_token:
        return []
    if isinstance(user_or_token, str):
        raw = user_or_token.strip()
        user_dict = {}
    elif isinstance(user_or_token, dict):
        user_dict = user_or_token
        raw = str(user_dict.get("web_session_token") or "").strip()
    else:
        return []

    if not raw:
        return []
    
    if raw.startswith("[") and raw.endswith("]"):
        try:
            sessions = json.loads(raw)
            if isinstance(sessions, list):
                valid = []
                for s in sessions:
                    if isinstance(s, dict) and s.get("token"):
                        if not s.get("id"):
                            s["id"] = str(uuid.uuid4())[:8]
                        if not s.get("icon"):
                            s["icon"] = "fa-desktop"
                        valid.append(s)
                return valid
        except Exception:
            pass

    # Legacy fallback (jeden řetězec v web_session_token)
    login_time = user_dict.get("web_login_at") or "Dříve"
    return [{
        "id": "legacy",
        "token": raw,
        "device": "Předchozí přihlášení",
        "icon": "fa-desktop",
        "ip": user_dict.get("ip_address") or "Neznámá",
        "user_agent": "",
        "created_at": login_time,
        "last_active": login_time
    }]


def user_has_session_token(user_or_token, token: str) -> bool:
    """Ověří, zda uživatel má aktivní relaci s daným tokenem."""
    if not user_or_token or not token:
        return False
    if isinstance(user_or_token, str):
        raw = user_or_token.strip()
    elif isinstance(user_or_token, dict):
        raw = str(user_or_token.get("web_session_token") or "").strip()
    else:
        return False

    if raw == token:
        return True
    sessions = get_user_sessions(user_or_token)
    return any(s.get("token") == token for s in sessions)


def add_user_session(db, user_or_id, token: str, req=None) -> list:
    """Přidá novou relaci k uživateli (zachová stávající relace na ostatních zařízeních)."""
    if not db or not token:
        return []
    
    if isinstance(user_or_id, dict):
        user_id = user_or_id.get("id")
        user = user_or_id
    else:
        user_id = user_or_id
        res = db.table("users").select("*").eq("id", user_id).execute()
        user = res.data[0] if res.data else None

    if not user:
        return []

    sessions = get_user_sessions(user)
    # Odstranit případnou existující relaci se stejným tokenem
    sessions = [s for s in sessions if s.get("token") != token]

    ua = req.headers.get('User-Agent', '') if req else ''
    ip = ''
    if req:
        xf = req.headers.get('X-Forwarded-For', '')
        ip = xf.split(',')[0].strip() if xf else (req.remote_addr or '')

    dev_info = parse_device_info(ua)
    now_str = get_prague_now_str()

    new_sess = {
        "id": str(uuid.uuid4())[:8],
        "token": token,
        "device": dev_info["name"],
        "icon": dev_info["icon"],
        "ip": ip or "Neznámá",
        "user_agent": ua[:120],
        "created_at": now_str,
        "last_active": now_str
    }
    # Vložit na začátek (nejnovější nahoře)
    sessions.insert(0, new_sess)
    # Omezit na max 20 relací
    sessions = sessions[:20]

    json_str = json.dumps(sessions, ensure_ascii=False)
    try:
        db.table("users").update({
            "web_session_token": json_str,
            "web_login_at": now_str,
            "login_token": ""
        }).eq("id", user["id"]).execute()
    except Exception as e:
        print(f"[SESSION] Chyba při ukládání relací: {e}", flush=True)

    return sessions


def remove_user_session_by_token(db, token: str) -> bool:
    """Odstraní relaci s daným tokenem (např. při odhlášení z aktuálního zařízení)."""
    if not db or not token:
        return False
    user = find_user_by_session_token(db, token)
    if not user:
        return False

    sessions = get_user_sessions(user)
    updated = [s for s in sessions if s.get("token") != token]
    json_val = json.dumps(updated, ensure_ascii=False) if updated else ""
    try:
        db.table("users").update({"web_session_token": json_val}).eq("id", user["id"]).execute()
        return True
    except Exception as e:
        print(f"[SESSION] Chyba při odebírání relace tokenem: {e}", flush=True)
        return False


def remove_user_session_by_id(db, user_id, session_id: str) -> tuple:
    """Odstraní relaci podle jejího session_id. Vrátí (success, token_removed)."""
    if not db or not user_id or not session_id:
        return False, ""
    try:
        res = db.table("users").select("*").eq("id", user_id).execute()
        if not res.data:
            return False, ""
        user = res.data[0]
        sessions = get_user_sessions(user)
        removed_token = ""
        for s in sessions:
            if s.get("id") == session_id:
                removed_token = s.get("token", "")
                break
        
        updated = [s for s in sessions if s.get("id") != session_id]
        json_val = json.dumps(updated, ensure_ascii=False) if updated else ""
        db.table("users").update({"web_session_token": json_val}).eq("id", user_id).execute()
        return True, removed_token
    except Exception as e:
        print(f"[SESSION] Chyba při odebírání relace id={session_id}: {e}", flush=True)
        return False, ""


def revoke_all_other_sessions(db, user_id, keep_token: str) -> bool:
    """Ponechá pouze aktuální relaci s keep_token a odhlásí všechna ostatní zařízení."""
    if not db or not user_id or not keep_token:
        return False
    try:
        res = db.table("users").select("*").eq("id", user_id).execute()
        if not res.data:
            return False
        user = res.data[0]
        sessions = get_user_sessions(user)
        keep = [s for s in sessions if s.get("token") == keep_token]
        if not keep:
            keep = [{
                "id": str(uuid.uuid4())[:8],
                "token": keep_token,
                "device": "Aktuální zařízení",
                "icon": "fa-desktop",
                "ip": "Neznámá",
                "user_agent": "",
                "created_at": get_prague_now_str(),
                "last_active": get_prague_now_str()
            }]
        json_val = json.dumps(keep, ensure_ascii=False)
        db.table("users").update({"web_session_token": json_val}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"[SESSION] Chyba při revoke_all_other_sessions: {e}", flush=True)
        return False


def touch_session_activity(db, user_dict: dict, token: str) -> None:
    """Aktualizuje last_active timestamp relace (max 1x za 5 minut)."""
    if not db or not user_dict or not token:
        return
    sessions = get_user_sessions(user_dict)
    matched = None
    for s in sessions:
        if s.get("token") == token:
            matched = s
            break
    if not matched:
        return

    now_str = get_prague_now_str()
    if matched.get("last_active") == now_str:
        return

    matched["last_active"] = now_str
    json_val = json.dumps(sessions, ensure_ascii=False)
    try:
        db.table("users").update({"web_session_token": json_val}).eq("id", user_dict["id"]).execute()
        user_dict["web_session_token"] = json_val
    except Exception:
        pass


def find_user_by_session_token(db, token: str):
    """Najde uživatele podle cookie session tokenu (podporuje single token i multi-session JSON)."""
    if not db or not token:
        return None
    try:
        res = db.table("users").select("*").or_(f"web_session_token.eq.{token},web_session_token.like.%{token}%").execute()
        for u in (res.data or []):
            if user_has_session_token(u, token):
                return u
    except Exception as e:
        print(f"[SESSION] Chyba při vyhledávání uživatele: {e}", flush=True)
    return None
