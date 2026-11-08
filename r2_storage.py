# r2_storage.py
# Modul pro ukládání a správu komunitních zvukových souborů a balíčků linek
# Podporuje Cloudflare R2 (S3 kompatibilní API) a automatický lokální fallback.

import os
import io
import time
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Načtení konfigurace Cloudflare R2 z prostředí
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID") or "0752a840edd6e7f0c989d1b83b8f96a9"
R2_ACCESS_KEY_ID = os.environ.get("CF_R2_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID") or ""
R2_SECRET_ACCESS_KEY = os.environ.get("CF_R2_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY") or ""
R2_BUCKET_NAME = os.environ.get("CF_R2_BUCKET_NAME") or os.environ.get("R2_BUCKET_NAME") or "idpk-community-audio"
R2_PUBLIC_URL = os.environ.get("CF_R2_PUBLIC_URL") or os.environ.get("R2_PUBLIC_URL") or ""

LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "community_audio")
if not os.path.exists(LOCAL_STORAGE_DIR):
    try:
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    except Exception as e:
        print(f"[R2_STORAGE] Nelze vytvořit lokální složku pro audio: {e}")

def is_r2_configured() -> bool:
    """Ověří, zda jsou nastaveny autentizační údaje pro Cloudflare R2."""
    return bool(R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME)

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    k_signing = _sign(k_service, 'aws4_request')
    return k_signing

def upload_file_to_r2(file_bytes: bytes, object_key: str, content_type: str = "audio/mpeg") -> str:
    """
    Nahraje soubor přímo do Cloudflare R2 pomocí AWS Signature Version 4.
    Vrací veřejnou nebo přístupovou URL souboru.
    """
    if not is_r2_configured():
        return save_file_locally(file_bytes, object_key)

    region = "auto"
    service = "s3"
    host = f"{CF_ACCOUNT_ID}.r2.cloudflarestorage.com"
    endpoint = f"https://{host}/{R2_BUCKET_NAME}/{object_key}"

    now = datetime.now(timezone.utc)
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')

    payload_hash = hashlib.sha256(file_bytes).hexdigest()

    canonical_uri = f"/{R2_BUCKET_NAME}/{object_key}"
    canonical_querystring = ""
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"PUT\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} "
        f"Credential={R2_ACCESS_KEY_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    req = urllib.request.Request(endpoint, data=file_bytes, method="PUT")
    req.add_header("Content-Type", content_type)
    req.add_header("Host", host)
    req.add_header("x-amz-date", amz_date)
    req.add_header("x-amz-content-sha256", payload_hash)
    req.add_header("Authorization", authorization_header)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status in (200, 201, 204):
                if R2_PUBLIC_URL:
                    base = R2_PUBLIC_URL.rstrip('/')
                    return f"{base}/{object_key}"
                return f"/api/community-audio/{object_key}"
    except urllib.error.HTTPError as e:
        print(f"[R2_STORAGE] Chyba nahrávání do R2 ({e.code}): {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[R2_STORAGE] Výjimka při nahrávání do R2: {e}")

    # Fallback lokálně
    return save_file_locally(file_bytes, object_key)

def save_file_locally(file_bytes: bytes, object_key: str) -> str:
    """Uloží soubor lokálně v static/community_audio/ jako spolehlivý fallback."""
    dest_path = os.path.join(LOCAL_STORAGE_DIR, object_key)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return f"/static/community_audio/{object_key}"

def delete_file_from_storage(object_key: str) -> bool:
    """Smaže soubor z úložiště (R2 i lokálně)."""
    # Lokální smazání
    local_path = os.path.join(LOCAL_STORAGE_DIR, object_key)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except:
            pass

    # R2 smazání pokud je nastaveno
    if is_r2_configured():
        try:
            region = "auto"
            service = "s3"
            host = f"{CF_ACCOUNT_ID}.r2.cloudflarestorage.com"
            endpoint = f"https://{host}/{R2_BUCKET_NAME}/{object_key}"
            now = datetime.now(timezone.utc)
            amz_date = now.strftime('%Y%m%dT%H%M%SZ')
            date_stamp = now.strftime('%Y%m%d')
            payload_hash = hashlib.sha256(b"").hexdigest()
            canonical_uri = f"/{R2_BUCKET_NAME}/{object_key}"
            canonical_headers = (
                f"host:{host}\n"
                f"x-amz-content-sha256:{payload_hash}\n"
                f"x-amz-date:{amz_date}\n"
            )
            signed_headers = "host;x-amz-content-sha256;x-amz-date"
            canonical_request = f"DELETE\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
            algorithm = "AWS4-HMAC-SHA256"
            credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
            string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
            signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, date_stamp, region, service)
            signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            authorization_header = f"{algorithm} Credential={R2_ACCESS_KEY_ID}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
            req = urllib.request.Request(endpoint, method="DELETE")
            req.add_header("Host", host)
            req.add_header("x-amz-date", amz_date)
            req.add_header("x-amz-content-sha256", payload_hash)
            req.add_header("Authorization", authorization_header)
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status in (200, 204)
        except Exception as e:
            print(f"[R2_STORAGE] Chyba při mazání z R2: {e}")
    return True
