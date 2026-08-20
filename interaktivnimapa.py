import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse as _uparse
import threading
import queue

DEPOT_DISCORD_QUEUE = queue.Queue()
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, Response, request, session, redirect
from zoneinfo import ZoneInfo
import math
import re
import http.cookiejar
import sqlite3
import unicodedata
import concurrent.futures

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    print("[MAPA-WARN] Modul 'supabase' neni dostupny!")

mapa_bp = Blueprint('mapa_bp', __name__)

SPZ_HOLD_MINUTES      = 8
SPZ_STABLE_TICKS      = 2
SPZ_HIGH_CONFIDENCE_DIST_M = 300  # 3-faktor match = okamzita fajfka (zadne cekani na 2. tik)
SPZ_REAUDIT_INTERVAL_SEC = 30      # jak casto preverovat UZ overenou (fajfka) SPZ (snizeno pro rychlejsi korekci)
SPZ_AUTO_REFRESH_MIN     = 8       # kazdych N minut proved plny refresh SPZ u vsech aktivnich busu
                                   # (ekvivalent knofliku "Najit SPZ" ale pro vsechny najednou)
SPZ_BEARING_MAX_DIFF     = 75      # max rozdil smer (deg) pro bearing bonus faktor SPZ
SPZ_MIN_MOVE_MINUTES     = 2       # bus musi jet alespon N minut nez se provede prvni SPZ parovani
SPZ_CACHE_FLUSH_SEC      = 60      # jak casto zapisovat spz_cache do Supabase (sekundy)
# Stavy (color_class), pri kterych se ZAKAZUJE hledani nove SPZ z Arrivy
SPZ_BLOCKED_COLORS = frozenset({'bg-bug', 'bg-blue', 'bg-purple', 'bg-gray'})
GHOST_MAX_OFFLINE_MIN = 20
GHOST_DIST_STRICT     = 0.010
DUPLICATE_GRACE_SEC   = 120
DEPOT_CHECK_INTERVAL_SEC = 20  # jak casto kontrolovat vjezd busu do vozovny
DEPOT_ACTIVE_SESSIONS = {}  # {spz: {"id": uuid, "depot_name": str, "arrived_at": str, "is_imprecise": bool}}
SCRIPT_START_TIME = datetime.now(ZoneInfo("Europe/Prague")).replace(tzinfo=None)

# Cesta k GTFS db relativne k tomuto souboru (spolehlivejsi nez working dir)
GTFS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtfs_stops.db")

# Tolerance pro parovani SPZ v metrech (presnejsi nez stupne)
ARRIVA_MATCH_DIST_M = 750   # max vzdalenost PVVD pozice od Arriva pozice same SPZ
ARRIVA_STOP_MATCH_M = 400   # max vzdalenost k nejblizsi GTFS zastavce pro krizovou kontrolu

# REPORT SITUACE: kruhovy buffer poslednich anomalii (duplicitni SPZ, spatne prirazeni, atd.)
# Kazdy zaznam: {ts, typ, zprava, data}
_REPORT_SITUACE = []
_REPORT_SITUACE_MAX = 200

def _report_situace(typ, zprava, **data):
    """Zapise anomalii do REPORT SITUACE bufferu (viditelny v logu mapy)."""
    import traceback as _tb
    entry = {
        "ts": datetime.now().isoformat(timespec='seconds'),
        "typ": typ,
        "zprava": zprava,
        "data": data,
    }
    _REPORT_SITUACE.append(entry)
    if len(_REPORT_SITUACE) > _REPORT_SITUACE_MAX:
        _REPORT_SITUACE.pop(0)
    sys_log(f"REPORT {typ}: {zprava} | {data}")

import collections
SYSTEM_LOGS = collections.deque(maxlen=300)

def sys_log(msg):
    try:
        ts = datetime.now(ZoneInfo("Europe/Prague")).strftime("%H:%M:%S")
    except Exception:
        ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    SYSTEM_LOGS.append(entry)
    print(entry, flush=True)


def _spz_debug_log(bus_id, event, spz=None, detail=None, **extra):
    """Zapise podrobny SPZ event do debug bufferu. Neloguje se na stdout pri bezne operaci."""
    entry = {
        "ts": datetime.now().isoformat(timespec='seconds'),
        "bus_id": bus_id,
        "spz": spz,
        "event": event,
        "detail": detail,
    }
    entry.update(extra)
    _SPZ_DEBUG_LOG.append(entry)
    if len(_SPZ_DEBUG_LOG) > _SPZ_DEBUG_LOG_MAX:
        _SPZ_DEBUG_LOG.pop(0)

# === HTML SABLONY ===

HTML_HISTORIE_INDEX = """
<div style="padding:20px;max-width:1500px;margin:auto;font-family:sans-serif;">
<div style="background:#dc2626;color:white;padding:12px;border-radius:8px;font-weight:bold;text-align:center;margin-bottom:18px;font-size:15px;border:2px solid #991b1b;">
  <i class="fas fa-exclamation-triangle fa-fade"></i> !!! DATA NEMUSI SEDET - STRANKA JE VE VYVOJI !!!
</div>
<details style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px 16px;margin-bottom:16px;cursor:pointer;">
  <summary style="color:#f59e0b;font-weight:bold;font-size:13px;user-select:none;"><i class="fas fa-info-circle"></i> Proc system obcas vynecha zaznamy?</summary>
  <div style="color:#94a3b8;font-size:12px;margin-top:10px;line-height:1.7;">
    <ul style="margin:0;padding-left:20px;">
      <li>Arriva API pomala nebo nevratila bus - SPZ se neparuje</li>
      <li>Restart mapy uprostred spoje - ztrata kontextu, novy trip_id</li>
      <li>Jsou zaznamenavany <strong>pouze linky 490xxx a 496xxx</strong></li>
    </ul>
  </div>
</details>
<div id="statsBar" style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px;"></div>
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px;">
  <h2 style="color:#38bdf8;margin:0;font-size:22px;"><i class="fas fa-database"></i> 🗄️ Databaze Sledovanych Vozu</h2>
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
    <select id="filterLine" style="background:#1e293b;color:white;border:1px solid #334155;border-radius:6px;padding:7px 10px;font-size:13px;">
      <option value="">Vsechny linky</option><option value="490">Linka 490</option><option value="496">Linka 496</option>
    </select>
    <select id="filterStatus" style="background:#1e293b;color:white;border:1px solid #334155;border-radius:6px;padding:7px 10px;font-size:13px;">
      <option value="">Vsechny stavy</option><option value="Probiha">Probiha</option><option value="depo">V garáži</option><option value="Ukonceno">Ukonceno</option>
    </select>
    <input id="historySearch" type="text" placeholder="🔍 Hledat SPZ, linku..." style="background:#1e293b;color:white;border:1px solid #334155;border-radius:6px;padding:7px 12px;font-size:13px;min-width:200px;">
  </div>
</div>
<div style="background:#1e293b;border-radius:10px;border:1px solid #334155;overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;color:#cbd5e1;min-width:950px;">
    <thead><tr style="background:#0f172a;">
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:left;">Datum</th>
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:left;">SPZ Vozu</th>
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:left;">Linka</th>
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:left;">Cas (Plan -> Real)</th>
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:left;">Status / Konec</th>
      <th style="color:#38bdf8;padding:11px 14px;border-bottom:1px solid #334155;text-align:center;">Akce</th>
    </tr></thead>
    <tbody id="historyTableBody"><tr><td colspan="6" style="text-align:center;padding:30px;color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Načítám…</td></tr></tbody>
  </table>
</div>
<p style="color:#64748b;font-size:11px;margin-top:8px;">* Neomezena historie. Aktualizace kazdych 10s.</p>
<script>
let allData=[];
function buildFreqMap(data){const f={};data.forEach(r=>{const spz=r.spz||'Neznama';if(spz==='Neznama')return;const lb=String(r.linka||'').replace(/\\/.*/g,'').trim().replace(/[^0-9]/g,'');f[spz+'_'+lb]=(f[spz+'_'+lb]||0)+1;});return f;}
function renderStats(data){
  const ss=new Set(data.filter(r=>r.spz&&r.spz!=='Neznama').map(r=>r.spz));
  const total=data.length,active=data.filter(r=>!r.end_actual&&!r.status?.includes('Timeout')&&!r.status?.includes('depu')).length,depot=data.filter(r=>r.status?.includes('depu')||r.status?.includes('Vozovn')).length;
  document.getElementById('statsBar').innerHTML=`
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#38bdf8;font-size:22px;font-weight:900;">${total}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📋 Zaznamu</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#f59e0b;font-size:22px;font-weight:900;">${ss.size}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🚌 Unikatnich SPZ</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#10b981;font-size:22px;font-weight:900;">${active}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📡 Probiha</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#64748b;font-size:22px;font-weight:900;">${depot}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🏢 V garáži</div></div>`;
}
function applyFilters(){
  const s=document.getElementById('historySearch').value.toLowerCase().trim();
  const fl=document.getElementById('filterLine').value,fs=document.getElementById('filterStatus').value;
  document.querySelectorAll('#historyTableBody tr[data-search]').forEach(row=>{
    const txt=row.getAttribute('data-search')||'',linka=row.getAttribute('data-linka')||'',status=row.getAttribute('data-status')||'';
    let vis=true;
    if(s&&!txt.includes(s))vis=false;
    if(fl&&!linka.includes(fl))vis=false;
    if(fs==='Probiha'&&!status.includes('probiha')&&!status.includes('jede')&&!status.includes('ceka'))vis=false;
    if(fs==='depo'&&!status.includes('depu')&&!status.includes('vozov'))vis=false;
    if(fs==='Ukonceno'&&!status.includes('konec')&&!status.includes('timeout')&&!status.includes('ukoncen'))vis=false;
    row.style.display=vis?'':'none';
  });
}
async function loadIndex(){
  try{
    const res=await fetch('/api/history_full');const result=await res.json();allData=result.data||[];
    const freq=buildFreqMap(allData);renderStats(allData);
    const tbody=document.getElementById('historyTableBody');
    if(allData.length===0){tbody.innerHTML='<tr><td colspan="6" style="text-align:center;padding:20px;color:#64748b;">Zatim zadne zaznamy.</td></tr>';return;}
    let html='';
    allData.forEach(row=>{
      const d=new Date(row.created_at),dayStr=d.toLocaleDateString('cs-CZ');
      const spz=row.spz||'Neznama',linka=row.linka||'---';
      const lb=String(linka).replace(/\\/.*/,'').trim().replace(/[^0-9]/g,'');
      const rc=row.run_count||freq[spz+'_'+lb]||0;
      let spzB=spz==='Neznama'?`<span style="background:#334155;color:#94a3b8;padding:3px 8px;border-radius:4px;font-size:12px;">Neznama</span>`:
               row.status?.includes('Falesny')?`<span style="background:#ef4444;color:white;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold;">${spz} X</span>`:
               `<span style="background:#f59e0b;color:#0f172a;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold;">${spz} OK</span>`;
      let fb=rc>=10?`<br><span style="background:#7c3aed;color:white;padding:1px 6px;border-radius:10px;font-size:10px;display:inline-block;margin-top:3px;"><i class="fas fa-star"></i> Staly vuz (${rc}x)</span>`:
             rc>=5?`<br><span style="background:#0284c7;color:white;padding:1px 6px;border-radius:10px;font-size:10px;display:inline-block;margin-top:3px;"><i class="fas fa-redo"></i> Casta linka (${rc}x)</span>`:
             rc>=3?`<br><span style="background:#334155;color:#94a3b8;padding:1px 6px;border-radius:10px;font-size:10px;display:inline-block;margin-top:3px;">${rc}x na teto lince</span>`:'';
      let ss='<span style="color:#64748b;">---</span>';
      if(row.start_scheduled||row.start_actual)ss=`<span style="color:#64748b;">${row.start_scheduled||'?'}</span> -> <strong style="color:#10b981;">${row.start_actual||'Ceka'}</strong>`;
      const iD=row.status?.includes('depu')||row.status?.includes('Vozovn'),isE=row.end_actual||row.status?.includes('Timeout')||row.status?.includes('Ukoncen');
      let sc='#eab308',el='<i class="fas fa-spinner fa-pulse" style="margin-right:4px;"></i>Probiha';
      if(iD){sc='#64748b';el='<i class="fas fa-warehouse" style="margin-right:4px;"></i>V depu';}
      else if(isE){sc='#ef4444';el=row.end_actual||'Ukonceno';}
      const sH=`<div style="color:#94a3b8;font-size:11px;margin-bottom:2px;">${row.status||''}</div><div style="color:${sc};font-weight:bold;font-size:13px;">${el}</div>`;
      const rt=`${spz} ${linka} ${row.status||''}`.toLowerCase(),rs=(row.status||'').toLowerCase();
      html+=`<tr style="border-bottom:1px solid #334155;" data-search="${rt}" data-linka="${lb}" data-status="${rs}">
        <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${dayStr}<br><span style="color:#475569;font-size:10px;">${String(row.trip_id||'').substring(0,10)}...</span></td>
        <td style="padding:11px 14px;vertical-align:middle;">${spzB}${fb}</td>
        <td style="padding:11px 14px;vertical-align:middle;"><strong style="color:white;">${linka}</strong>${row.jr_link?`<br><a href="${row.jr_link}" target="_blank" style="font-size:11px;color:#38bdf8;">JR <i class="fas fa-external-link-alt"></i></a>`:''}</td>
        <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${ss}</td>
        <td style="padding:11px 14px;vertical-align:middle;">${sH}</td>
        <td style="padding:11px 14px;vertical-align:middle;text-align:center;">${spz!=='Neznama'?`<a href="/historie/${spz}" style="background:#38bdf8;color:#0f172a;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:bold;text-decoration:none;"><i class="fas fa-list"></i> Detail vozu</a>`:`<span style="color:#475569;font-size:11px;">Ceka na SPZ</span>`}</td>
      </tr>`;
    });
    tbody.innerHTML=html;applyFilters();
  }catch(e){console.error(e);}
}
document.getElementById('historySearch').addEventListener('input',applyFilters);
document.getElementById('filterLine').addEventListener('change',applyFilters);
document.getElementById('filterStatus').addEventListener('change',applyFilters);
loadIndex();
</script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
"""

HTML_HISTORIE_DETAIL = """
<div style="padding:20px;max-width:1000px;margin:auto;font-family:sans-serif;">
<a href="/historie" style="display:inline-block;margin-bottom:15px;padding:6px 14px;background:#334155;color:white;border-radius:6px;text-decoration:none;font-size:13px;">⬅️ Zpet</a>
<div style="background:#dc2626;color:white;padding:15px;border-radius:8px;font-weight:bold;text-align:center;margin-bottom:20px;font-size:18px;border:2px solid #991b1b;">!!! DATA NEMUSI SEDET - STRANKA JE VE VYVOJI !!!</div>
<div style="background:#1e293b;padding:20px;border-radius:10px;border:1px solid #38bdf8;margin-bottom:25px;">
  <h2 style="color:white;margin:0 0 10px 0;font-size:28px;">🚌 Autobus SPZ: <span style="color:#f59e0b;">__SPZ__</span></h2>
  <div id="absoluteLastPos"><span style="color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Načítám…</span></div>
</div>
<h3 style="color:#38bdf8;margin-bottom:15px;margin-top:20px;"><i class="fas fa-warehouse"></i> 🅿️ Pobyty ve vozovnách</h3>
<div style="background:#0f172a;border-radius:10px;border:1px solid #334155;overflow-x:auto;margin-bottom:20px;">
  <table style="width:100%;border-collapse:collapse;color:#cbd5e1;">
    <thead><tr style="background:#1e293b;">
      <th style="color:#38bdf8;padding:12px;border-color:#334155;text-align:left;">Vozovna</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;text-align:left;">Příjezd</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;text-align:left;">Odjezd</th>
    </tr></thead>
    <tbody id="depotTableBody"><tr><td colspan="3" style="text-align:center;padding:15px;color:#64748b;">Načítám...</td></tr></tbody>
  </table>
</div>

<h3 style="color:#38bdf8;margin-bottom:15px;"><i class="fas fa-route"></i> 🚌 Odjete spoje</h3>
<div style="background:#0f172a;border-radius:10px;border:1px solid #334155;overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;color:#cbd5e1;">
    <thead><tr style="background:#1e293b;">
      <th style="color:#38bdf8;padding:12px;border-color:#334155;">Datum / Spoj ID</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;">Linka</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;">Zacatek</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;">Konec / Status</th>
      <th style="color:#38bdf8;padding:12px;border-color:#334155;text-align:center;">Mapa</th>
    </tr></thead>
    <tbody id="detailTableBody"><tr><td colspan="5" style="text-align:center;padding:30px;color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i></td></tr></tbody>
  </table>
</div>
<script>
const PAGE_SPZ='__SPZ__';
async function loadDetail(){
  try{
    const res=await fetch('/api/history_spz/'+PAGE_SPZ);const result=await res.json();const data=result.data||[];
    const liveRes=await fetch('/api/live_buses');const liveData=await liveRes.json();
    const liveBus=liveData.buses?liveData.buses.find(b=>b.spz===PAGE_SPZ):null;
    const tbody=document.getElementById('detailTableBody'),lastP=document.getElementById('absoluteLastPos');
    if(data.length===0&&!liveBus){tbody.innerHTML='<tr><td colspan="5" style="text-align:center;padding:20px;">Zadna historie.</td></tr>';lastP.innerHTML='<span style="color:#ef4444;">Poloha neznama</span>';return;}
    let lat=0,lng=0,topS="",topT="",liveI="";
    if(liveBus&&liveBus.lat){lat=liveBus.lat;lng=liveBus.lng;topS=liveBus.status+' ('+( liveBus.line||'Bez linky')+')';topT="Nyni (Ziva data)";liveI=`<br><span style="color:#10b981;font-weight:bold;font-size:13px;"><i class="fas fa-satellite-dish"></i> Zive na mape</span>`;}
    else if(data.length>0){const n=data[0];lat=n.last_lat;lng=n.last_lng;topS=n.status+' ('+(n.linka||'Bez linky')+')';const nd=new Date(n.updated_at||n.created_at);topT=nd.toLocaleDateString('cs-CZ')+' '+nd.toLocaleTimeString('cs-CZ');liveI=`<br><span style="color:#94a3b8;font-size:13px;"><i class="fas fa-database"></i> Historie</span>`;}
    lastP.innerHTML=`<div style="display:flex;align-items:center;gap:15px;"><div style="flex-grow:1;"><strong style="color:white;font-size:16px;">Stav:</strong> <span>${topS}</span><br><span style="color:#cbd5e1;font-size:14px;">${topT}</span>${liveI}</div><a href="/mapa#${lat},${lng}" style="background:#38bdf8;color:#0f172a;padding:10px 16px;border-radius:8px;font-weight:bold;text-decoration:none;"><i class="fas fa-crosshairs"></i> Na mape</a></div>`;
    let html='';
    data.forEach(trip=>{
      const cd=new Date(trip.created_at),dayStr=cd.toLocaleDateString('cs-CZ');
      let ss=trip.start_actual?trip.start_actual:(trip.start_scheduled?`<span style="color:#94a3b8;">${trip.start_scheduled} (Plan)</span>`:"---");
      let iF=trip.end_actual||trip.status.includes('Timeout');
      let es=iF?`${trip.end_actual||'Timeout'} <br><span style="font-size:11px;color:#94a3b8;">(${trip.status})</span>`:`<span style="color:#eab308;font-weight:bold;"><i class="fas fa-spinner fa-pulse"></i> Probiha...</span><br><span style="font-size:11px;color:#94a3b8;">${trip.status}</span>`;
      html+=`<tr style="border-color:#334155;"><td style="border-color:#334155;padding:12px;color:#cbd5e1;">${dayStr}<br><span style="font-size:10px;color:#64748b;">${trip.trip_id.substring(0,8)}...</span></td><td style="border-color:#334155;padding:12px;font-weight:bold;color:white;">${trip.linka}${trip.jr_link?`<br><a href="${trip.jr_link}" target="_blank" style="font-size:11px;color:#38bdf8;">JR <i class="fas fa-external-link-alt"></i></a>`:''}</td><td style="border-color:#334155;padding:12px;color:#10b981;">${ss}</td><td style="border-color:#334155;padding:12px;color:#ef4444;">${es}</td><td style="border-color:#334155;padding:12px;text-align:center;"><a href="/mapa#${trip.last_lat},${trip.last_lng}" style="background:transparent;color:#cbd5e1;border:1px solid #4b5563;padding:5px 10px;border-radius:4px;text-decoration:none;font-size:12px;"><i class="fas fa-map-marker-alt"></i></a></td></tr>`;
    });
    tbody.innerHTML=html;

    const depotTbody = document.getElementById('depotTableBody');
    const dVisits = result.depot_visits || [];
    if(dVisits.length === 0) {
      depotTbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:15px;color:#64748b;">Zatím nebyl ve vozovně.</td></tr>';
    } else {
      let dHtml = '';
      dVisits.forEach(v => {
        let arr = new Date(v.arrived_at).toLocaleString('cs-CZ');
        let lft = v.left_at ? new Date(v.left_at).toLocaleString('cs-CZ') : '<span style="color:#10b981;font-weight:bold;">Nyní zaparkován</span>';
        let arrHtml = arr;
        if(v.is_imprecise) arrHtml += ' <span style="font-size:11px;color:#f59e0b;">(RESET MAPY NEPŘESNÝ ČAS)</span>';
        dHtml += `<tr style="border-bottom:1px solid #1e293b;"><td style="padding:10px;color:white;font-weight:bold;">${v.depot_name}</td><td style="padding:10px;color:#94a3b8;">${arrHtml}</td><td style="padding:10px;color:#94a3b8;">${lft}</td></tr>`;
      });
      depotTbody.innerHTML = dHtml;
    }

  }catch(e){console.error(e);}
}
loadDetail();
</script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
"""

HTML_MAPA = """
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100%;height:100%;overflow:hidden;background:#0f172a;}
.dark-map .leaflet-marker-pane, .dark-map .leaflet-overlay-pane { filter: brightness(0.85); }
#map-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;}
#map{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;}
#panel-zone{position:fixed;top:0;left:0;right:0;height:40px;z-index:3000;pointer-events:none;}
#top-nav{position:fixed;top:-72px;left:0;right:0;min-height:58px;background:rgba(8,16,30,0.97);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);z-index:2999;transition:top 0.3s cubic-bezier(.4,0,.2,1);display:flex;align-items:center;justify-content:center;padding:6px 14px;gap:6px;box-shadow:0 4px 24px rgba(0,0,0,0.7);flex-wrap:wrap;}
#top-nav.vis{top:0;}
#nav-handle{position:fixed;top:0;left:50%;transform:translateX(-50%);width:90px;height:7px;background:rgba(56,189,248,.55);border-radius:0 0 8px 8px;z-index:3001;cursor:pointer;transition:opacity .3s,background .2s,width .2s;}
#nav-handle:hover{background:rgba(56,189,248,.95);width:130px;}
#nav-handle.hid{opacity:0;pointer-events:none;}
body.nav-static #nav-handle, body.nav-glass:not(.nav-glass-hide) #nav-handle { display: none !important; }
.n-logo{position:relative;display:block;flex-shrink:0;background:transparent;border:none;padding:0;box-shadow:none;height:34px;width:44px;margin-right:12px;}
.n-logo img{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);height:50px;width:auto;filter:drop-shadow(0 0 10px rgba(56,189,248,0.9)) drop-shadow(0 0 2px rgba(255,255,255,0.4));transition:transform .2s;}
.n-logo:hover img{transform:translate(-50%,-50%) scale(1.05);}
.n-title{flex-shrink:0;line-height:1.2;}.n-title .a{color:#38bdf8;font-size:14px;font-weight:800;}.n-title .b{color:#64748b;font-size:10px;}
.n-warn{background:#f59e0b;color:#0f172a;padding:3px 8px;border-radius:5px;font-size:10px;font-weight:bold;white-space:nowrap;flex-shrink:0;}
.n-sp{width:80px;flex:0 0 auto;}
.n-clock, #admin-mode-badge, #spz-search-inp {
  background: #020617 !important;
  border: 1px solid #1e293b !important;
  color: #94a3b8 !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.8) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}
.n-clock{padding:4px 10px;white-space:nowrap;flex-shrink:0;color:#ffffff !important;}
#spz-search-inp::placeholder { color: #475569 !important; }
#spz-results:empty { display: none !important; }

/* The Gradient Border Buttons */
.n-btn, #nav-pin-btn, #nt-toggle-btn, #nt-add-btn, #le-toggle-btn, #log-toggle-btn, #depot-toggle-btn {
  background: linear-gradient(#08101e, #08101e) padding-box,
              linear-gradient(135deg, rgba(56,189,248,0.6), rgba(2,132,199,0.8)) border-box !important;
  color: #e2e8f0 !important;
  border: 1px solid transparent !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
  padding: 6px 14px !important;
  font-size: 12px !important;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.n-btn:hover, #nav-pin-btn:hover, #nt-toggle-btn:hover, #nt-add-btn:hover, #le-toggle-btn:hover, #log-toggle-btn:hover, #depot-toggle-btn:hover {
  background: linear-gradient(rgba(56,189,248,0.1), rgba(2,132,199,0.15)) padding-box,
              linear-gradient(135deg, #38bdf8, #0284c7) border-box !important;
  color: #ffffff !important;
  box-shadow: 0 0 16px rgba(2,132,199,0.4), 0 4px 12px rgba(0,0,0,0.6) !important;
  transform: translateY(-2px);
}

/* Pinned state */
#nav-pin-btn.pinned {
  background: linear-gradient(#08101e, #08101e) padding-box,
              linear-gradient(135deg, #f59e0b, #ef4444) border-box !important;
  color: #f59e0b !important;
  box-shadow: 0 0 12px rgba(245,158,11,0.2) !important;
}

/* Lines overlay buttons in legend */
#lines-legend>div:hover{background:rgba(56,189,248,.08);}

@keyframes pulseAttention {
  0%, 100% { box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4) !important; }
  50% { box-shadow: 0 0 25px 10px rgba(56, 189, 248, 0.9) !important; }
}

/* Výrazné tlačítko "Zobrazit zastávky" - prominentní pro veřejnost */
#pub-stops-btn {
  background: linear-gradient(135deg, #38bdf8, #0369a1) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
  font-size: 13px !important;
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
  box-shadow: 0 4px 15px rgba(2,132,199,0.3) !important;
  transition: all 0.3s ease;
  padding: 7px 15px !important;
  text-decoration: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  animation: pulseAttention 1s ease-in-out 5s 5;
}

#pub-stops-btn:hover {
  background: linear-gradient(135deg, #0ea5e9, #075985) !important;
  box-shadow: 0 6px 20px rgba(2,132,199,0.5) !important;
  transform: translateY(-2px);
}
#pub-stops-btn.active{background:linear-gradient(135deg, #f59e0b, #ef4444) !important;}
/* Kurzor kříže v NT add mode */
body.nt-add-active{cursor:crosshair !important;}
body.nt-add-active #map{cursor:crosshair !important;}
.dark-popup .leaflet-popup-content-wrapper{background:#1e293b;color:#fff;border:1px solid #334155;padding:0;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.65);}
.dark-popup .leaflet-popup-tip{background:#1e293b;}
.dark-popup .leaflet-popup-content{margin:0;width:292px!important;}
.ph{background:#0f172a;padding:10px 13px;border-bottom:1px solid #334155;}
.ph-t{font-weight:bold;color:#38bdf8;font-size:15px;margin:0;}
.pb{padding:11px 13px;font-size:13px;line-height:1.6;}
.pr{display:flex;justify-content:space-between;margin-bottom:5px;border-bottom:1px dashed #334155;padding-bottom:3px;}
.pr:last-child{border-bottom:none;}
.pl{color:#94a3b8;font-weight:600;}.pv{font-weight:bold;text-align:right;max-width:60%;word-wrap:break-word;}
.spz-b{background:#f59e0b;color:#0f172a;padding:2px 6px;border-radius:4px;font-size:12px;border:1px solid #d97706;}
.pa{background:#38bdf8;color:#0f172a;border:none;padding:8px;width:100%;border-radius:5px;font-weight:bold;cursor:pointer;transition:.2s;margin-top:7px;display:block;text-align:center;font-size:12px;}
.pa:hover{background:#0284c7;color:#fff;}
.pa-d{background:#334155;color:#fff;}.pa-d:hover{background:#475569;}
#hud{display:none;position:fixed;bottom:18px;right:18px;z-index:4000;font-family:'Segoe UI',sans-serif;}
#hf{background:#1e293b;border:2px solid #38bdf8;border-radius:12px;padding:13px;width:248px;box-shadow:0 8px 28px rgba(0,0,0,.75);}
#hm{display:none;background:#1e293b;border:2px solid #38bdf8;border-radius:50px;padding:6px 12px;align-items:center;gap:8px;}
#hm button{background:none;border:none;cursor:pointer;font-size:18px;padding:2px 5px;}
.hh{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;}
.hl{color:#38bdf8;font-size:10px;font-weight:bold;letter-spacing:.5px;}
.ht{color:#94a3b8;font-size:11px;margin-bottom:1px;}
.hd{color:#fff;font-size:16px;font-weight:bold;margin-bottom:6px;line-height:1.2;}
.hr{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:4px;}
.hac{display:flex;gap:5px;margin-top:9px;}
.hb{flex:1;padding:7px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:bold;}
.hb-jr{background:#38bdf8;color:#0f172a;}.hb-st{background:#ef4444;color:#fff;}
.hb-mn{background:none;border:1px solid #334155;color:#94a3b8;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:14px;}
#sw{display:none;position:fixed;top:68px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#991b1b,#ef4444);color:#fff;padding:11px 18px;border-radius:10px;font-weight:bold;z-index:5000;text-align:center;max-width:92vw;width:410px;animation:swPulse 2.4s ease-in-out infinite alternate;}
@keyframes swPulse{0%{box-shadow:0 4px 20px rgba(239,68,68,.4);}100%{box-shadow:0 4px 45px rgba(239,68,68,.9);}}
#ttm{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.72);z-index:6000;align-items:center;justify-content:center;}
#ttm.open{display:flex;}
#ttb{background:#0f172a;border-radius:10px;padding:20px;max-width:700px;width:95%;border:1px solid #38bdf8;max-height:86vh;overflow-y:auto;position:relative;}
#ttc-btn{position:absolute;top:10px;right:10px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;font-weight:bold;}
#spz-results .sr-item{padding:8px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:8px;}
#spz-results .sr-item:hover{background:#334155;}
.route-line-future{stroke-dasharray:14 10;animation:routeFlow 0.96s linear infinite;stroke-linecap:round;filter:drop-shadow(0 0 4px currentColor);}
.route-line-past{stroke-linecap:round;filter:drop-shadow(0 0 1px rgba(0,0,0,.5));}
.route-line-draw{animation:routeDraw 1.44s ease-out forwards;}
@keyframes routeFlow{to{stroke-dashoffset:-24;}}
@keyframes routePulse{0%,100%{box-shadow:0 0 0 0 rgba(56,189,248,.8),0 2px 6px rgba(0,0,0,.5);}50%{box-shadow:0 0 0 10px rgba(56,189,248,0),0 2px 6px rgba(0,0,0,.5);}}
@keyframes routeDrawLoop {
  0% { stroke-dashoffset: var(--r-len); }
  65% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 0; }
}
@keyframes routeDraw{from{stroke-dashoffset:1}to{stroke-dashoffset:0;}}
/* Floating close-route button */
#close-route-btn, #edit-route-btn, #save-route-btn { display:none; position:fixed; z-index:4200; border-radius:24px; padding:8px 22px; font-size:13px; font-weight:700; cursor:pointer; backdrop-filter:blur(8px); transition:all .2s; letter-spacing:.3px; }
#close-route-btn { top: 75px; left: 50%; transform:translateX(-50%); background:rgba(15,23,42,.92); color:#ef4444; border:1.5px solid #ef4444; box-shadow:0 4px 20px rgba(239,68,68,.35); }
#close-route-btn:hover { background:#ef4444; color:#fff; box-shadow:0 4px 28px rgba(239,68,68,.6); }
#edit-route-btn { top: 75px; left: calc(50% + 80px); transform:translateX(-50%); background:rgba(15,23,42,.92); color:#38bdf8; border:1.5px solid #38bdf8; box-shadow:0 4px 20px rgba(56,189,248,.35); }
#edit-route-btn:hover { background:#38bdf8; color:#fff; box-shadow:0 4px 28px rgba(56,189,248,.6); }
#save-route-btn { top: 75px; left: calc(50% + 80px); transform:translateX(-50%); background:rgba(239,68,68,.92); color:white; border:1.5px solid #f87171; box-shadow:0 4px 20px rgba(239,68,68,.35); }
#save-route-btn:hover { background:#ef4444; color:#fff; box-shadow:0 4px 28px rgba(239,68,68,.6); }
/* Leaflet popup fade-in */
.leaflet-popup{animation:popupIn .22s cubic-bezier(.34,1.56,.64,1);}
@keyframes popupIn{from{opacity:0;transform:translateY(10px) scale(.96);}to{opacity:1;transform:translateY(0) scale(1);}}
.route-line-past{stroke-linecap:round;}
.nt-dot{width:14px;height:14px;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.6);cursor:grab;box-sizing:border-box;}
.nt-dot-normal{background:#38bdf8;border:2px solid white;}
.nt-dot-manual{background:#10b981;border:2px solid white;}
.nt-dot-flagged{background:#f59e0b;border:2px solid #fff;animation:ntPulse 1.44s ease-in-out infinite;}
.nt-dot-saving{background:#a855f7;border:2px solid white;opacity:.7;}
@keyframes ntPulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.7);}50%{box-shadow:0 0 0 7px rgba(245,158,11,0);}}
.pub-dot{width:9px;height:9px;border-radius:50%;background:#38bdf8;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.5);}
.pub-dot-train{border-radius:0 !important;background:#f59e0b;}
.pub-dot-approx{background:#f59e0b;border:2px dashed white;}
.pub-dot-substitute{background:#a855f7;border:2px dashed white;}
.nt-dot-train{border-radius:0 !important;}
#stop-info-pop{position:fixed;bottom:18px;left:18px;z-index:4400;background:#1e293b;border:2px solid #38bdf8;border-radius:10px;padding:12px 14px;width:220px;box-shadow:0 8px 24px rgba(0,0,0,.7);display:none;}
#stop-info-pop .sip-name{color:#38bdf8;font-weight:bold;font-size:13px;margin-bottom:8px;}
#stop-info-pop .sip-lines{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;}
#stop-info-pop .sip-line{background:#334155;color:#cbd5e1;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;}
#log-errors-body{max-height:160px;overflow-y:auto;padding:6px 12px;font-family:monospace;font-size:10px;color:#f87171;}
#nt-edit-pop{position:fixed;bottom:18px;left:18px;z-index:4500;background:#1e293b;border:2px solid #f59e0b;border-radius:10px;padding:12px 14px;width:240px;box-shadow:0 8px 24px rgba(0,0,0,.7);display:none;}
#nt-edit-pop .ntp-t{color:#f59e0b;font-weight:bold;font-size:13px;margin-bottom:8px;}
#nt-edit-pop label{display:flex;align-items:center;gap:7px;color:#cbd5e1;font-size:12px;margin-bottom:7px;cursor:pointer;}
#nt-edit-pop input[type=checkbox]{width:15px;height:15px;cursor:pointer;}
#nt-edit-pop button{width:100%;padding:6px;border:none;border-radius:5px;font-size:12px;font-weight:bold;cursor:pointer;margin-top:3px;}
#log-panel{position:fixed;bottom:18px;right:18px;z-index:4500;background:#0f172a;border:2px solid #475569;border-radius:10px;width:380px;max-width:90vw;display:none;box-shadow:0 8px 24px rgba(0,0,0,.7);}
#log-panel .lp-h{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-bottom:1px solid #334155;}
#log-panel .lp-h span{color:#94a3b8;font-size:12px;font-weight:bold;}
#log-panel .lp-h button{background:none;border:1px solid #475569;color:#94a3b8;border-radius:4px;font-size:10px;padding:3px 7px;cursor:pointer;margin-left:5px;}
#log-body{max-height:240px;overflow-y:auto;padding:8px 12px;font-family:monospace;font-size:10.5px;color:#94a3b8;line-height:1.5;user-select:text !important;-webkit-user-select:text !important;}
#log-body .lg-err{color:#f87171;}
#log-body .lg-warn{color:#fbbf24;}
#log-body .lg-ok{color:#34d399;}
@media(max-width:768px){
  #top-nav{gap:4px;padding:4px 5px;height:auto;min-height:50px;flex-wrap:wrap;justify-content:center;}
  .n-title,.n-warn{display:none;}
  .n-clock{font-size:10px;padding:3px 5px;}
  .n-btn{font-size:10px;padding:4px 7px;}
  #pub-stops-btn{font-size:11px;padding:5px 10px;}
  #spz-search-inp{width:80px;font-size:11px;}
  #hf{width:200px;}
  .dark-popup .leaflet-popup-content{width:240px!important;}
  #log-panel{bottom:auto;top:130px;right:4px;left:4px;width:auto;max-width:100vw;}
  #log-body,#log-errors-body,#log-spz-body,#log-missing-body,#log-report-body,#log-approx-body{max-height:160px;user-select:text !important;-webkit-user-select:text !important;}
  #nt-edit-pop{left:4px;right:4px;bottom:10px;width:auto;max-height:80vh;overflow-y:auto;}
  #bus-detail-pop, #stop-info-pop { width: 92% !important; left: 4% !important; bottom: 20px !important; top: auto !important; transform: none !important; }
  .sip-lines{flex-wrap:wrap;gap:3px;}
  .lp-h div{gap:2px;flex-wrap:wrap;}
  .lp-h div button{font-size:10px;padding:2px 5px;}
  #nt-add-bar{left:4px;right:4px;transform:none;flex-wrap:wrap;gap:5px;}
  #idos-modal-box{width:100% !important;height:100% !important;max-width:none !important;border:none !important;border-radius:0 !important;}
  #hud { top: auto !important; left: 10px !important; right: auto !important; bottom: 30px !important; }
  #close-route-btn { top: auto !important; bottom: 140px !important; left: 50% !important; transform: translateX(-50%) !important; }
  #edit-route-btn, #save-route-btn { top: auto !important; bottom: 190px !important; left: 50% !important; transform: translateX(-50%) !important; }
}
@media(max-width:420px){
  .n-provoz{display:none;}
  #spz-search-inp{width:65px;font-size:10px;}
  #nt-toggle-btn,#nt-add-btn,#log-toggle-btn,#depot-toggle-btn{font-size:11px;padding:4px 6px;}
  #pub-stops-btn{font-size:10px;padding:4px 9px;}
}

@keyframes routeDrawLoop {
  0% { stroke-dashoffset: var(--r-len); }
  65% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 0; }
}
/* Low Graphics Mode overrides */
body.low-graphics * {
  box-shadow: none !important;
  text-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  transition: none !important;
  animation: none !important;
  filter: none !important;
}
body.low-graphics .route-line-past,
body.low-graphics path,
body.low-graphics .leaflet-marker-icon div {
  animation: none !important;
}
#settings-toggle-btn{background:rgba(15,23,42,0.85);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid #334155;color:#cbd5e1;border-radius:30px;height:42px;padding:0 14px;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 15px rgba(0,0,0,0.4);transition:all 0.4s cubic-bezier(.34,1.56,.64,1);overflow:hidden;position:relative;}
#settings-toggle-btn:hover{transform:scale(1.05);box-shadow:0 6px 20px rgba(0,0,0,0.6);background:rgba(15,23,42,0.95);color:#38bdf8;border-color:#38bdf8;}
body.dark-map #settings-toggle-btn, body.bw-dark-map #settings-toggle-btn, body.traffic-dark-map #settings-toggle-btn { background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.6); color: #38bdf8; box-shadow: 0 0 20px rgba(56, 189, 248, 0.3), inset 0 0 12px rgba(56, 189, 248, 0.2); }
body.dark-map #settings-toggle-btn:hover, body.bw-dark-map #settings-toggle-btn:hover, body.traffic-dark-map #settings-toggle-btn:hover { background: rgba(56, 189, 248, 0.3); border-color: #38bdf8; color: #38bdf8; box-shadow: 0 0 30px rgba(56, 189, 248, 0.5), inset 0 0 20px rgba(56, 189, 248, 0.4); }
#settings-toggle-btn .st-text{font-size:13px;font-weight:700;width:0px;opacity:0;transition:all 0.4s cubic-bezier(.34,1.56,.64,1);white-space:nowrap;overflow:hidden;margin-left:0px;}
#settings-toggle-btn:hover .st-text{width:75px;opacity:1;margin-left:6px;}

body.nav-static #top-nav { top: 0 !important; }
body.nav-glass #top-nav { top: 15px !important; left: 50% !important; right: auto !important; transform: translateX(-50%) !important; width: max-content !important; max-width: 98vw !important; border-radius: 16px !important; padding: 6px 12px !important; gap: 6px !important; flex-wrap: nowrap !important; background: rgba(15, 23, 42, 0.25) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; backdrop-filter: blur(16px) saturate(180%) !important; -webkit-backdrop-filter: blur(16px) saturate(180%) !important; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35) !important; }
body.nav-glass-hide #top-nav { top: -100px !important; }
body.nav-glass-hide #top-nav.vis { top: 15px !important; }
body.nav-static #nav-pin-btn, body.nav-glass:not(.nav-glass-hide) #nav-pin-btn { display: none !important; }
@media (max-width: 768px) {
  .n-sp { display: none !important; }
  #top-nav { flex-wrap: wrap !important; height: auto; min-height: 50px; padding: 4px 6px; justify-content: center; gap: 4px; width: 100% !important; border-radius: 0; }
  body.nav-glass #top-nav { width: 98% !important; border-radius: 14px !important; flex-wrap: wrap !important; left: 50% !important; transform: translateX(-50%) !important; top: 10px !important; }
  body.nav-glass-hide #top-nav { top: -100px !important; }
  body.nav-glass-hide #top-nav.vis { top: 10px !important; }
  .n-warn, .n-clock, .n-title { display: none !important; }
  #spz-search-inp { width: 90px !important; }
  #settings-btn-wrap { top: auto !important; bottom: 90px !important; right: 10px !important; }
}
</style>

<div id="map-wrap">
  <div id="panel-zone"></div>
  <div id="nav-handle" title="Klikni pro zobrazeni navigace"></div>
  <nav id="top-nav">
    <a href="https://datacorebot.koyeb.app/" class="n-logo">
      <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png" alt="OIS IDPK">
    </a>
    <button id="pub-stops-btn" onclick="togglePubStops()"><i class="fas fa-bus"></i> Zastávky</button>
    <button id="lines-overlay-btn-pub" onclick="toggleLinesPanel()" class="n-btn"><i class="fas fa-route"></i> Linky</button>
    <div class="n-sp"></div>
    <div class="n-clock"><span id="systemTimeClock">--:--:--</span></div>
    <div style="position:relative;flex-shrink:0;" id="spz-search-wrap">
      <input id="spz-search-inp" type="text" placeholder="🔍 SPZ..."
        style="background:#0f172a;color:white;border:1px solid #334155;border-radius:6px;padding:5px 9px;font-size:12px;width:110px;outline:none;"
        oninput="spzSearch(this.value)" onblur="setTimeout(()=>document.getElementById('spz-results').innerHTML='',200)">
      <div id="spz-results" style="position:absolute;top:34px;right:0;background:#1e293b;border:1px solid #334155;border-radius:8px;min-width:220px;z-index:4000;box-shadow:0 8px 20px rgba(0,0,0,.7);max-height:220px;overflow-y:auto;"></div>
    </div>
    <div id="admin-mode-badge" style="display:none;background:rgba(56,189,248,0.15);color:#38bdf8;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;border:1px solid rgba(56,189,248,0.3);flex-shrink:0;">Admin</div>
    <button id="nav-pin-btn" onclick="toggleNavPin()" title="Uzamknout lištu"><i class="fas fa-thumbtack"></i></button>

    <!-- Admin nástroje – skryté pro veřejnost -->
    <button id="nt-toggle-btn" onclick="toggleNT()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #f59e0b;background:transparent;color:#f59e0b;cursor:pointer;">🛠️ NT</button>
    <button id="nt-add-btn" onclick="startNtAdd()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:14px;flex-shrink:0;border:1px solid #10b981;background:transparent;color:#10b981;cursor:pointer;" title="Přidat zastávku">＋</button>
    <button id="le-toggle-btn" onclick="toggleLineEditor()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #a855f7;background:transparent;color:#a855f7;cursor:pointer;" title="Editor linek"><i class="fas fa-edit"></i> Edit</button>
    <button id="depot-toggle-btn" onclick="document.getElementById('depot-admin-panel').style.display=document.getElementById('depot-admin-panel').style.display==='none'?'block':'none'" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #b45309;background:transparent;color:#fcd34d;cursor:pointer;" title="Správa vozoven">🅿️ Vozovny</button>
    <!-- lines-overlay-btn-pub is already in nav for everyone -->
    <button id="log-toggle-btn" onclick="toggleLogPanel()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #475569;background:transparent;color:#94a3b8;cursor:pointer;">📋</button>
    __AD_BTN__
  </nav>
  __ADMIN_BANNER__
  <div id="map"></div>
  <div id="sw">
    <div style="font-size:17px;margin-bottom:3px;display:flex;justify-content:space-between;align-items:center;">
      <span><i class="fas fa-spinner fa-spin"></i> Mapa se startuje</span>
      <button onclick="document.getElementById('sw').style.display='none'" style="background:rgba(255,255,255,0.1);color:#fff;border:none;border-radius:4px;padding:3px 8px;font-size:12px;cursor:pointer;">Vypnout</button>
    </div>
    <div style="font-size:12px;font-weight:normal;opacity:.9;">Probiha nacitani dat - vyckejte prosim.</div>
    <div id="sw-cd" style="margin-top:5px;font-size:11px;opacity:.8;"></div>
  </div>
  <div id="ttm"><div id="ttb">
    <button id="ttc-btn" onclick="document.getElementById('ttm').classList.remove('open')">X</button>
    <div id="ttc" style="color:white;">Načítám…</div>
  </div></div>
  <div id="close-route-btn" onclick="closeActiveRoute()"><i class="fas fa-times"></i> Zavřít trasu</div>
  <div id="edit-route-btn" onclick="startEditRouteRoads()"><i class="fas fa-edit"></i> Silnice</div>
  <div id="save-route-btn" onclick="saveRouteRoads()"><i class="fas fa-save"></i> ULOŽIT TRASU</div>
  <div id="hud">
    <div id="hf">
      <div class="hh" id="hud-drag-handle" style="cursor: move;" title="Táhněte pro přesun"><span class="hl">📡 SLEDOVANI SPOJE (táhni)</span><button class="hb-mn" onclick="minHud()">-</button></div>
      <div id="h-trip" class="ht">Spoj: -</div>
      <div id="h-dest" class="hd">Načítám…</div>
      <div class="hr"><span style="color:#94a3b8;">SPZ:</span><span id="h-spz">-</span></div>
      <div class="hr"><span style="color:#94a3b8;">Zpozdeni:</span><span id="h-delay">-</span></div>
      <div class="hr"><span style="color:#94a3b8;">Status:</span><span id="h-status" style="color:#94a3b8;font-size:11px;">-</span></div>
      <div class="hac"><button class="hb hb-jr" id="h-jr"><i class="fas fa-list"></i> JR</button><button class="hb hb-route" id="h-route" onclick="_hudShowRoute()" style="background:#1e3a8a;color:#93c5fd;" title="Zobrazit trasu"><i class="fas fa-route"></i></button><button class="hb" id="h-pin" onclick="togglePin()" style="background:#f59e0b;color:#0f172a;" title="Připnout kameru"><i class="fas fa-thumbtack"></i></button><button class="hb hb-st" onclick="stopFollow()"><i class="fas fa-times"></i></button></div>
    </div>
    <div id="hm">
      <span style="color:#38bdf8;font-size:12px;font-weight:bold;">●</span>
      <span id="hm-line" style="color:#fff;font-size:12px;font-weight:bold;"></span>
      <button onclick="maxHud()" style="color:#10b981;">+</button>
      <button onclick="stopFollow()" style="color:#ef4444;">X</button>
    </div>
  </div>
  <div id="nt-edit-pop">
    <div class="ntp-t"><span id="ntp-mode-icon">🚏</span> <span id="ntp-name">-</span></div>
    <div style="font-size:10px;color:#64748b;margin-bottom:8px;">Systémový název (pro vyhledávání v JŘ)</div>
    <label style="display:block;margin-bottom:4px;font-size:11px;color:#94a3b8;">Zobrazovaný název (prázdné = použij systémový):</label>
    <input id="ntp-dispname" type="text" placeholder="Zobrazovaný název..." style="width:100%;box-sizing:border-box;background:#0f172a;color:white;border:1px solid #334155;border-radius:4px;padding:5px 8px;font-size:12px;margin-bottom:8px;">
    <label style="display:block;margin-bottom:4px;font-size:11px;color:#94a3b8;">Mód zastávky (Doprava):</label>
    <select id="ntp-mode-select" style="width:100%;box-sizing:border-box;background:#0f172a;color:white;border:1px solid #334155;border-radius:4px;padding:5px 8px;font-size:12px;margin-bottom:8px;">
      <option value="bus">🚌 Autobus</option>
      <option value="train">🚂 Vlak</option>
      <option value="mixed">🚌🚂 Smíšená (Bus + Vlak)</option>
    </select>
    <label style="margin-bottom:6px;"><input type="checkbox" id="ntp-approx"> ⚠️ Přibližná poloha</label>
    <label style="margin-bottom:8px;"><input type="checkbox" id="ntp-substitute"> 🔀 Náhradní zastávka</label>
    <label style="margin-bottom:8px;"><input type="checkbox" id="ntp-notfound"> ❌ Nenalezeno (error)</label>
    <div style="margin-bottom:4px;font-size:11px;color:#94a3b8;">Linky přes zastávku:</div>
    <div id="ntp-lines-chips" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;min-height:22px;"></div>
    <div style="display:flex;gap:4px;margin-bottom:8px;">
      <input id="ntp-line-add" type="text" placeholder="Přidat linku (760 nebo 490760)" style="flex:1;background:#0f172a;color:white;border:1px solid #334155;border-radius:4px;padding:5px 8px;font-size:12px;" onkeydown="if(event.key==='Enter')addLineToNtStop()">
      <button onclick="addLineToNtStop()" style="background:#334155;color:#38bdf8;border:none;border-radius:4px;padding:5px 10px;cursor:pointer;font-size:12px;font-weight:bold;">＋</button>
    </div>
    <button onclick="saveNtFlags()" style="width:100%;background:#10b981;color:white;border:none;border-radius:5px;padding:7px;font-weight:bold;cursor:pointer;font-size:12px;margin-bottom:4px;">💾 Uložit vše</button>
    <button onclick="deleteNtStop()" style="width:100%;background:#7f1d1d;color:#fca5a5;border:none;border-radius:5px;padding:5px;font-size:11px;cursor:pointer;margin-bottom:4px;">🗑️ Odebrat zastávku</button>
    <button onclick="document.getElementById('nt-edit-pop').style.display='none'" style="width:100%;background:transparent;border:1px solid #334155;color:#64748b;border-radius:5px;padding:4px;font-size:11px;cursor:pointer;">Zavřít</button>
  </div>
  <div id="stop-info-pop">
    <div class="sip-name"><span id="sip-mode-icon">🚏</span> <span id="sip-name-txt">-</span></div>
    <div id="sip-dispname" style="font-size:11px;color:#64748b;margin-bottom:4px;"></div>
    <div id="sip-mode" style="font-size:10px;color:#64748b;margin-bottom:6px;"></div>
    <div class="sip-lines" id="sip-lines-wrap"></div>
    <div id="sip-note" style="font-size:10px;color:#f59e0b;margin-top:4px;"></div>
    <button id="sip-idos-btn" style="display:block;background:#38bdf8;color:#0f172a;text-align:center;border:none;border-radius:5px;font-size:12px;font-weight:bold;padding:6px;margin-top:10px;width:100%;box-sizing:border-box;transition:0.2s;cursor:pointer;" onmouseover="this.style.background='#7dd3fc'" onmouseout="this.style.background='#38bdf8'">📅 Odjezdy ze zastávky</button>
    <button onclick="document.getElementById('stop-info-pop').style.display='none'" style="background:transparent;border:1px solid #334155;color:#64748b;border-radius:5px;font-size:11px;padding:3px 8px;cursor:pointer;margin-top:6px;width:100%;">Zavřít</button>
  </div>
  <div id="idos-modal" onclick="if(event.target===this){this.style.display='none';document.getElementById('idos-iframe').src='';}" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(15,23,42,0.85);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);z-index:9000;align-items:center;justify-content:center;">
    <div id="idos-modal-box" style="background:#1e293b;width:95vw;max-width:1400px;height:95vh;border-radius:12px;border:2px solid #38bdf8;box-shadow:0 10px 40px rgba(0,0,0,0.8);display:flex;flex-direction:column;overflow:hidden;">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:#0f172a;border-bottom:1px solid #334155;">
        <span style="color:#38bdf8;font-weight:bold;font-size:15px;">📅 Odjezdy ze zastávky</span>
        <button onclick="document.getElementById('idos-modal').style.display='none';document.getElementById('idos-iframe').src='';" style="background:none;border:none;color:#ef4444;font-size:20px;cursor:pointer;">✕</button>
      </div>
      <iframe id="idos-iframe" src="" style="width:100%;height:100%;border:none;background:white;"></iframe>
    </div>
  </div>
  <div id="lines-overlay-panel" style="display:none;position:fixed;top:64px;right:10px;z-index:4600;background:#0f172a;border:2px solid #38bdf8;border-radius:10px;width:290px;max-width:95vw;box-shadow:0 8px 28px rgba(0,0,0,.8);">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #1e293b;">
      <span style="color:#38bdf8;font-weight:bold;font-size:13px;">🗺️ Zobrazit linky</span>
      <button onclick="toggleLinesPanel()" style="background:none;border:none;color:#64748b;font-size:16px;cursor:pointer;">✕</button>
    </div>
    <div style="padding:10px 14px;">
      <div style="font-size:11px;color:#64748b;margin-bottom:8px;">Zadej prefix nebo číslo linky. Prázdné = vše (pomalé!)</div>
      <div style="display:flex;gap:6px;margin-bottom:8px;">
        <input id="lines-filter-inp" type="text" placeholder="490, 760, 490735..." style="flex:1;background:#1e293b;color:white;border:1px solid #334155;border-radius:5px;padding:6px 9px;font-size:12px;" onkeydown="if(event.key==='Enter')loadLinesOverlay()">
        <button onclick="loadLinesOverlay()" style="background:#38bdf8;color:#0f172a;border:none;border-radius:5px;padding:6px 12px;font-weight:bold;font-size:12px;cursor:pointer;">Zobrazit</button>
      </div>
      <button onclick="clearLinesOverlay()" style="width:100%;background:#334155;color:#94a3b8;border:none;border-radius:5px;padding:5px;font-size:11px;cursor:pointer;margin-bottom:8px;">Skrýt linky</button>
      <div id="lines-status" style="font-size:11px;color:#64748b;margin-bottom:6px;"></div>
      <div id="lines-legend" style="max-height:200px;overflow-y:auto;"></div>
    </div>
  </div>
  <div id="line-editor-panel" style="display:none;position:fixed;top:64px;right:10px;z-index:4700;background:#0f172a;border:2px solid #a855f7;border-radius:10px;width:300px;max-width:95vw;box-shadow:0 8px 28px rgba(168,85,247,.25);">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #1e293b;">
      <span style="color:#a855f7;font-weight:bold;font-size:13px;"><i class="fas fa-edit"></i> Editor linky</span>
      <button onclick="document.getElementById('line-editor-panel').style.display='none';lineEditorOff()" style="background:none;border:none;color:#64748b;font-size:16px;cursor:pointer;">✕</button>
    </div>
    <div style="padding:10px 14px;">
      <div style="font-size:11px;color:#64748b;margin-bottom:8px;">Zadej číslo linky:</div>
      <div style="display:flex;gap:6px;margin-bottom:8px;">
        <input id="le-line-inp" type="text" placeholder="735, 490735..." style="flex:1;background:#1e293b;color:white;border:1px solid #334155;border-radius:5px;padding:6px 9px;font-size:12px;" onkeydown="if(event.key==='Enter')leLoadLine()">
        <button onclick="leLoadLine()" style="background:#a855f7;color:white;border:none;border-radius:5px;padding:6px 12px;font-weight:bold;font-size:12px;cursor:pointer;">Načíst</button>
      </div>
      <div style="font-size:11px;color:#64748b;margin-bottom:6px;"><i class="fas fa-mouse-pointer"></i> Táhni bod · Klikni pro přidání</div>
      <div id="le-status" style="font-size:11px;color:#64748b;margin-bottom:6px;"></div>
      <div id="le-stops" style="max-height:260px;overflow-y:auto;"></div>
      <div style="display:flex;gap:4px;margin-top:8px;">
        <button onclick="leAddMode()" id="le-add-btn" style="flex:1;background:#334155;color:#a855f7;border:1px solid #a855f7;border-radius:5px;padding:5px;font-size:11px;cursor:pointer;"><i class="fas fa-plus"></i> Přidat</button>
        <button onclick="leSave()" style="flex:1;background:#a855f7;color:white;border:none;border-radius:5px;padding:5px;font-size:11px;font-weight:bold;cursor:pointer;"><i class="fas fa-save"></i> Uložit</button>
      </div>
    </div>
  </div>
  <div id="log-panel">
    <div class="lp-h">
      <span>📋 LOG</span>
      <div style="display:flex;gap:3px;flex-wrap:wrap;">
        <button onclick="setLogTab('all')" id="log-tab-all" style="background:#334155;color:white;">Vše</button>
        <button onclick="setLogTab('err')" id="log-tab-err">⚠️ Chyby</button>
        <button onclick="setLogTab('spz')" id="log-tab-spz">🚌 SPZ</button>
        <button onclick="setLogTab('missing')" id="log-tab-missing">📍 Chybí</button>
        <button onclick="setLogTab('conflict')" id="log-tab-conflict">⚔️ Konflikt</button>
        <button onclick="setLogTab('report')" id="log-tab-report">🔴 REPORT</button>
        <button onclick="setLogTab('approx')" id="log-tab-approx">⚠️ Přibliž.</button>
        <button onclick="setLogTab('system')" id="log-tab-system">🛠️ Systém</button>
        <button onclick="copyLog()">Kopír.</button>
        <button onclick="clearLog()">Smaž</button>
        <button onclick="document.getElementById('log-panel').style.display='none'">X</button>
      </div>
    </div>
    <div id="log-body"></div>
    <div id="log-errors-body" style="display:none;"></div>
    <div id="log-spz-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-family:monospace;font-size:10.5px;color:#94a3b8;"></div>
    <div id="log-missing-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-size:11px;"></div>
    <div id="log-conflict-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-size:11px;"></div>
    <div id="log-report-body" style="display:none;max-height:240px;overflow-y:auto;padding:6px 12px;"></div>
    <div id="log-approx-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-size:11px;"></div>
    <div id="log-system-body" style="display:none;max-height:240px;overflow-y:auto;padding:6px 12px;font-family:monospace;font-size:11px;color:#94a3b8;white-space:pre-wrap;"></div>
  </div>
  <div id="nt-add-bar" style="display:none;position:fixed;top:70px;left:50%;transform:translateX(-50%);z-index:5000;background:#1e293b;border:2px solid #f59e0b;border-radius:8px;padding:8px 14px;display:none;align-items:center;gap:8px;box-shadow:0 4px 20px rgba(0,0,0,.7);">
    <span style="color:#f59e0b;font-size:12px;font-weight:bold;">🚏 Klikni na mapu kde je zastávka</span>
    <input id="nt-add-name" type="text" placeholder="Název zastávky" style="background:#0f172a;color:white;border:1px solid #475569;border-radius:4px;padding:4px 8px;font-size:12px;width:160px;">
    <button onclick="confirmNtAdd()" style="background:#10b981;color:white;border:none;border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;">Přidat</button>
    <button onclick="cancelNtAdd()" style="background:#334155;color:#94a3b8;border:none;border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;">Zrušit</button>
  </div>
</div>

<div id="settings-btn-wrap" style="position:fixed;top:75px;right:20px;z-index:5000;display:flex;flex-direction:column;align-items:flex-end;">
  <button id="settings-toggle-btn" onclick="toggleSettingsPanel()">
    <i class="fas fa-cog"></i>
    <span class="st-text">Nastavení</span>
  </button>
  
  <div id="settings-panel" style="display:none;margin-top:15px;background:rgba(15,23,42,0.85);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid rgba(56,189,248,0.4);border-radius:16px;width:280px;box-shadow:0 10px 40px rgba(0,0,0,0.8);padding:20px;transform-origin:top right;transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);">
    <div style="color:#38bdf8;font-weight:800;font-size:15px;margin-bottom:16px;text-align:center;letter-spacing:1px;text-transform:uppercase;">Nastavení</div>
    
    <div style="color:white;font-size:12px;font-weight:bold;margin-bottom:8px;padding-left:4px;">Základní mapa</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:20px;">
      <button id="bm-btn-dark" class="bm-btn" onclick="setBaseMap('dark')" style="background:#1e293b;border:1px solid #38bdf8;color:#38bdf8;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">🌙 Tmavá</button>
      <button id="bm-btn-osm" class="bm-btn" onclick="setBaseMap('osm')" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">🗺️ Výchozí</button>
      <button id="bm-btn-transport_dark" class="bm-btn" onclick="setBaseMap('transport_dark')" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">🌃 Dopravní (tmavá)</button>
      <button id="bm-btn-transport" class="bm-btn" onclick="setBaseMap('transport')" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">🚇 Dopravní</button>
      <button id="bm-btn-satellite" class="bm-btn" onclick="setBaseMap('satellite')" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">🛰️ Satelit</button>
      <button id="bm-btn-bw" class="bm-btn" onclick="setBaseMap('bw')" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;padding:8px;border-radius:8px;font-size:11px;font-weight:bold;cursor:pointer;transition:0.2s;">⚪ Černobílá</button>
    </div>

    <div style="color:white;font-size:12px;font-weight:bold;margin-bottom:8px;padding-left:4px;">Design navigace</div>
    <select id="settings-nav-design" onchange="setNavDesign(this.value)" style="width:100%;background:rgba(255,255,255,0.05);color:white;border:1px solid #334155;border-radius:8px;padding:8px;font-size:12px;outline:none;cursor:pointer;margin-bottom:16px;">
      <option value="classic" style="background:#0f172a;">Klasická (srolovací)</option>
      <option value="static" style="background:#0f172a;">Klasická (stálá)</option>
      <option value="glass" style="background:#0f172a;">Nový design (Glass - stálá)</option>
      <option value="glass-hide" style="background:#0f172a;">Nový design (Glass - srolovací)</option>
    </select>

    <div style="color:white;font-size:12px;font-weight:bold;margin-bottom:8px;padding-left:4px;">Výkon</div>
    <label style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;background:rgba(255,255,255,0.03);padding:12px;border-radius:12px;border:1px solid rgba(255,255,255,0.05);transition:0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.06)'" onmouseout="this.style.background='rgba(255,255,255,0.03)'">
      <div style="flex:1;">
        <div style="color:white;font-size:13px;font-weight:bold;">Nízké detaily</div>
        <div style="color:#94a3b8;font-size:11px;margin-top:4px;line-height:1.4;">Vypne plynulé animace.</div>
      </div>
      <input type="checkbox" id="settings-low-graphics" onchange="toggleLowGraphics(this.checked)" style="transform:scale(1.2);margin-left:12px;accent-color:#38bdf8;">
    </label>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>

<script>
const IS_ADMIN=__IS_ADMIN__;

// === ADMIN ===
let adminInputCache={};
function saveAdminInputs(){
  if(!IS_ADMIN)return;
  document.querySelectorAll('[id^="adm_spz_"]').forEach(el=>{if(el.value!==el.getAttribute('data-orig'))adminInputCache['spz_'+el.id.replace('adm_spz_','')]=el.value;});
  document.querySelectorAll('[id^="adm_st_"]').forEach(el=>{if(el.value!==el.getAttribute('data-orig'))adminInputCache['st_'+el.id.replace('adm_st_','')]=el.value;});
  document.querySelectorAll('[id^="adm_note_"]').forEach(el=>{adminInputCache['note_'+el.id.replace('adm_note_','')]=el.value;});
}
function restoreAdminInput(busId,ft){let v=adminInputCache[ft+'_'+busId];return(v!==undefined&&v!==null)?v:null;}

let _toastT=null;
function showAdminToast(msg,ok=true){
  let t=document.getElementById('admin-toast');
  if(!t){t=document.createElement('div');t.id='admin-toast';t.style.cssText='position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;padding:9px 20px;font-size:12px;font-weight:bold;z-index:9999;border-radius:20px;white-space:nowrap;transition:opacity .4s;pointer-events:none;';document.body.appendChild(t);}
  t.textContent=msg;t.style.color=ok?'#10b981':'#ef4444';t.style.border='1px solid '+(ok?'#10b981':'#ef4444');t.style.opacity='1';
  clearTimeout(_toastT);_toastT=setTimeout(()=>{t.style.opacity='0';},3500);
}
async function adminAction(action,busId,extraData={}){
  saveAdminInputs();showAdminToast('Odesilam...');
  try{
    let res=await fetch('/api/admin/map_action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,bus_id:busId,...extraData})});
    let data=await res.json();
    if(data.status==='success'){showAdminToast('Uloženo - system zpracovava');setTimeout(()=>{if(action==='reset_admin'||action==='recheck_spz')Object.keys(adminInputCache).forEach(k=>{if(k.endsWith('_'+busId))delete adminInputCache[k];});fetchBuses();},800);}
    else showAdminToast('Chyba: '+(data.message||'neznama'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
window.adminDelete=(id)=>{if(confirm('Smazat tecku? Vrati se az pri novem spoji.')){adminAction('delete',id);openPopupBusId=null;}};
window.adminRecheck=(id)=>adminAction('recheck_spz',id);
window.adminSetSPZ=(id)=>{let spz=document.getElementById('adm_spz_'+id)?.value;if(spz)adminAction('edit_spz',id,{spz});};
window.adminSaveAll=(id,permanent)=>{
  let st=document.getElementById('adm_st_'+id)?.value?.trim()||'',col=document.getElementById('adm_col_'+id)?.value?.trim()||'',note=document.getElementById('adm_note_'+id)?.value?.trim()||'';
  if(!st&&!col&&!note){showAdminToast('Nic k ulozeni',false);return;}
  adminAction('edit_all',id,{status:st,color_class:col,note,permanent});
};

window.openSeznamAutobusu = function(rawSpz) {
    let s = rawSpz.replace(/[^a-zA-Z0-9]/g, '');
    let formattedSpz = rawSpz;
    if (s.length > 4) {
        formattedSpz = s.substring(0, s.length - 4) + ' ' + s.substring(s.length - 4);
    }
    
    // Synchronously open a new tab to avoid popup blockers
    let newTab = window.open('about:blank', '_blank');
    
    // Inject a nice loading screen into the new tab
    newTab.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Načítám seznam autobusů...</title>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        </head>
        <body style="background:#0f172a; color:white; font-family:sans-serif; display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh; margin:0;">
            <i class="fas fa-circle-notch fa-spin" style="font-size:3rem; color:#38bdf8; margin-bottom:20px;"></i>
            <h2 style="margin:0;">Otevírám databázi vozidel...</h2>
            <p style="color:#94a3b8; margin-top:15px; text-align:center; max-width: 400px; line-height:1.5;">
                Vyhledávám vůz <b>${formattedSpz}</b> na stránce https://seznam-autobusu.cz/<br>
                Prosím o strpení, navazuji spojení s cílovým serverem (cca 5 sekund)...
            </p>
        </body>
        </html>
    `);
    newTab.document.close();
    
    // Redirect the new tab to the target URL
    newTab.location.href = 'https://seznam-autobusu.cz/seznam?evcspz=' + encodeURIComponent(formattedSpz);
};

// === NAV ===
const nav=document.getElementById('top-nav');
let hideT=null;
let handle=document.getElementById('nav-handle');
function showNav(dur){clearTimeout(hideT);nav.classList.add('vis');if(handle)handle.classList.add('hid');if(dur)hideT=setTimeout(hideNav,dur);}
function hideNav(){nav.classList.remove('vis');if(handle)handle.classList.remove('hid');}
if(handle)handle.addEventListener('click',()=>showNav(5000));
let navPinned=false;
function toggleNavPin(){
  navPinned=!navPinned;
  let btn=document.getElementById('nav-pin-btn');
  if(navPinned){btn.classList.add('pinned');showNav(0);}
  else{btn.classList.remove('pinned');hideT=setTimeout(hideNav,1500);}
}
document.addEventListener('mousemove',e=>{if(e.clientY<6)showNav();},{passive:true});
nav.addEventListener('mouseenter',()=>clearTimeout(hideT));
nav.addEventListener('mouseleave',()=>{if(!navPinned)hideT=setTimeout(hideNav,600);});
document.addEventListener('touchstart',e=>{if(e.touches[0].clientY<35){showNav(4500);}else if(!nav.contains(e.target)&&!navPinned){clearTimeout(hideT);hideT=setTimeout(hideNav,400);}},{passive:true});
showNav(4000);
// Smart pan handlers registered after map init below
if(IS_ADMIN){let ab=document.getElementById('admin-mode-badge');if(ab)ab.style.display='block';let ntb=document.getElementById('nt-toggle-btn');if(ntb)ntb.style.display='inline-block';let nab=document.getElementById('nt-add-btn');if(nab)nab.style.display='inline-block';let leb=document.getElementById('le-toggle-btn');if(leb)leb.style.display='inline-block';let dtb=document.getElementById('depot-toggle-btn');if(dtb)dtb.style.display='inline-block';let lgb=document.getElementById('log-toggle-btn');if(lgb)lgb.style.display='inline-block';}

// === MAP ===
var dLat=49.7384,dLng=13.3736,dZoom=12;
var hp=window.location.hash.replace('#','').split(',');
if(hp.length===2&&!isNaN(hp[0])&&!isNaN(hp[1])&&hp[0]!==""){dLat=parseFloat(hp[0]);dLng=parseFloat(hp[1]);dZoom=17;}
var map=L.map('map',{zoomControl:false}).setView([dLat,dLng],dZoom);
L.control.zoom({position:'bottomleft'}).addTo(map);
window.mapLayers = {
  osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}),
  dark: L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png?api_key=68be98ba-5497-41e4-b14e-0aaa9649aafd',{maxZoom:20,attribution:'&copy; Stadia Maps'}),
  bw: L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{maxZoom:19,attribution:'&copy; CARTO'}),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'&copy; Esri'}),
  transport_dark: L.tileLayer('https://{s}.tile.thunderforest.com/transport-dark/{z}/{x}/{y}.png?apikey=086ca59fb24640be82e5259e96c7a0cb',{maxZoom:22,attribution:'&copy; Thunderforest'}),
  transport: L.tileLayer('https://{s}.tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey=086ca59fb24640be82e5259e96c7a0cb',{maxZoom:22,attribution:'&copy; Thunderforest'})
};
window.currentBaseMap = localStorage.getItem('ois_basemap') || 'osm';
if (!window.mapLayers[window.currentBaseMap]) window.currentBaseMap = 'osm';
window.mapLayers[window.currentBaseMap].addTo(map);

window.setBaseMap = function(type) {
  Object.values(window.mapLayers).forEach(layer => map.removeLayer(layer));
  window.mapLayers[type].addTo(map);
  window.currentBaseMap = type;
  localStorage.setItem('ois_basemap', type);
  document.querySelectorAll('.bm-btn').forEach(b => {
    b.style.borderColor = '#334155';
    b.style.color = '#cbd5e1';
  });
  let activeBtn = document.getElementById('bm-btn-' + type);
  if(activeBtn) {
    activeBtn.style.borderColor = '#38bdf8';
    activeBtn.style.color = '#38bdf8';
  }
  document.body.classList.remove('dark-map', 'bw-dark-map', 'traffic-dark-map');
  if (type === 'dark') {
    document.body.classList.add('dark-map');
  } else if (type === 'bw') {
    document.body.classList.add('bw-dark-map');
  } else if (type === 'transport_dark') {
    document.body.classList.add('traffic-dark-map');
  }
};

// Inicializace aktivního tlačítka při načtení
setTimeout(() => setBaseMap(window.currentBaseMap), 100);

window.setNavDesign = function(type) {
  document.body.classList.remove('nav-static', 'nav-glass', 'nav-glass-hide');
  if(type === 'static') document.body.classList.add('nav-static');
  if(type === 'glass') document.body.classList.add('nav-glass');
  if(type === 'glass-hide') document.body.classList.add('nav-glass', 'nav-glass-hide');
  localStorage.setItem('ois_nav_design', type);
};
setTimeout(() => {
  let savedNav = localStorage.getItem('ois_nav_design') || 'glass';
  let el = document.getElementById('settings-nav-design');
  if(el) el.value = savedNav;
  window.setNavDesign(savedNav);
}, 100);
setTimeout(()=>map.invalidateSize(),300);
var ml = L.markerClusterGroup({
  disableClusteringAtZoom: 16,
  maxClusterRadius: (window.innerWidth < 768) ? 45 : 35,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
  zoomToBoundsOnClick: true
}).addTo(map);

var routeLayer=L.layerGroup().addTo(map);
var ntLayer=L.layerGroup().addTo(map);
var pubStopsLayer=L.layerGroup().addTo(map);

// Auto-detekce mobilu pro usporu baterie a CPU ve spicce (jen poprve, kdyz uzivatel nema nastaveno jinak)
let savedLg = localStorage.getItem('low_graphics_mode');
if(savedLg === null && (window.innerWidth < 768 || /Mobi|Android/i.test(navigator.userAgent))){
    document.body.classList.add('low-graphics');
    localStorage.setItem('low_graphics_mode', 'true');
    setTimeout(() => {
        let lgCb = document.getElementById('settings-low-graphics');
        if(lgCb) lgCb.checked = true;
    }, 500);
}
// Smart pan during tracking: allow user to pan, return to bus 1.5s after release
let _panReturnTimer=null;
map.on('mousedown touchstart',()=>{if(followId&&pinMode)clearTimeout(_panReturnTimer);});
map.on('mouseup touchend',()=>{
  if(followId&&pinMode){
    clearTimeout(_panReturnTimer);
    _panReturnTimer=setTimeout(()=>{
      let b=lastArr.find(x=>x.id===followId);
      if(b&&b.lat&&pinMode)map.panTo([b.lat,b.lng],{animate:true,duration:0.6});
    },1500);
  }
});
if(hp.length===2&&!isNaN(hp[0])&&hp[0]!=="")L.circleMarker([dLat,dLng],{radius:28,color:'#ef4444',weight:2,opacity:.8,fillOpacity:.12}).addTo(map);

// === STATE (MODULE LEVEL) ===
let lastArr=[],followId=null,hudMin=false,followInflowId=null;
let openPopupBusId=null;
let activeRouteId=null;
// KLICOVA OPRAVA: isRefreshing MUSI byt MODULE-LEVEL, ne uvnitr fetchBuses()!
// Pokud by byla lokalni, kazdy 10s refresh by vytvoril novou promennou s
// hodnotou false a closure v popupclose by vzdy videla false -> mazala trasu.
let isRefreshing=false;

// === LOG ===
let logEntries=[],logErrEntries=[],logSpzEntries=[],logMissingStops={};
let logCurrentTab='all';
function appLog(msg,level){
  level=level||'info';
  let t=new Date().toLocaleTimeString('cs-CZ');
  let entry={t,msg,level};
  logEntries.push(entry);if(logEntries.length>500)logEntries.shift();
  if(level==='error'||level==='warn'){
    logErrEntries.push(entry);if(logErrEntries.length>200)logErrEntries.shift();
    let btn=document.getElementById('log-tab-report');
    if(btn&&logCurrentTab!=='report')btn.style.color='#f87171';
  }
  if(logCurrentTab==='all'){
    let body=document.getElementById('log-body');
    if(body){let cls=level==='error'?'lg-err':level==='warn'?'lg-warn':level==='ok'?'lg-ok':'';let line=document.createElement('div');line.className=cls;line.textContent=`[${t}] ${msg}`;body.appendChild(line);body.scrollTop=body.scrollHeight;}
  }
}
function appLogSpz(busId,spz,status,detail){
  let t=new Date().toLocaleTimeString('cs-CZ');
  let entry={t,busId,spz,status,detail};
  logSpzEntries.push(entry);if(logSpzEntries.length>200)logSpzEntries.shift();
  if(logCurrentTab==='spz')renderSpzLog();
}
function logMissingStop(name){
  if(!logMissingStops[name])logMissingStops[name]={count:0,last:''};
  logMissingStops[name].count++;
  logMissingStops[name].last=new Date().toLocaleTimeString('cs-CZ');
  let btn=document.getElementById('log-tab-missing');
  if(btn&&logCurrentTab!=='missing')btn.style.color='#fbbf24';
  if(logCurrentTab==='missing')renderMissingLog();
}
function renderSpzLog(){
  let body=document.getElementById('log-spz-body');
  if(!body)return;
  body.innerHTML='';
  [...logSpzEntries].reverse().forEach(e=>{
    let line=document.createElement('div');
    let cls=e.status==='ok'?'lg-ok':e.status==='err'?'lg-err':'';
    line.className=cls;
    line.textContent=`[${e.t}] Bus ${e.busId}: ${e.spz} — ${e.detail}`;
    body.appendChild(line);
  });
}
function renderMissingLog(){
  let body=document.getElementById('log-missing-body');
  if(!body)return;
  body.innerHTML='';
  let sorted=Object.entries(logMissingStops).sort((a,b)=>b[1].count-a[1].count);
  if(!sorted.length){body.innerHTML='<div style="color:#64748b;padding:8px;">Žádné chybějící zastávky</div>';return;}
  sorted.forEach(([name,info])=>{
    let div=document.createElement('div');
    div.style.cssText='padding:6px 0;border-bottom:1px solid #1e293b;';
    div.innerHTML=`
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="color:#f59e0b;font-size:12px;">📍 ${name}</span>
        <span style="color:#64748b;font-size:10px;">${info.count}× posl. ${info.last}</span>
      </div>
      <div style="display:flex;gap:4px;">
        <button style="flex:1;background:#10b981;color:white;border:none;border-radius:4px;padding:3px 6px;font-size:10px;cursor:pointer;">🆕 Vytvořit novou</button>
        <button style="flex:1;background:#334155;color:#94a3b8;border:none;border-radius:4px;padding:3px 6px;font-size:10px;cursor:pointer;">🔗 Použít existující</button>
      </div>`;
    let [createBtn,useBtn]=div.querySelectorAll('button');
    createBtn.onclick=()=>{
      // Vytvořit novou: přijmi název z JŘ přímo (bez promptu), jen klikni kde to leží
      document.getElementById('log-panel').style.display='none';
      _startMissingFix(name,'new');
    };
    useBtn.onclick=()=>{
      document.getElementById('log-panel').style.display='none';
      _startMissingFix(name,'existing');
    };
    body.appendChild(div);
  });
}

// Vizuální režim opravy chybějící zastávky - žádné prompty, vše klikáním
let _missingFixName='', _missingFixMode='', _missingPickLayer=null;
function _startMissingFix(name, mode){
  _missingFixName=name; _missingFixMode=mode;
  if(_missingPickLayer){_missingPickLayer.clearLayers();}
  _missingPickLayer=_missingPickLayer||L.layerGroup().addTo(map);
  if(mode==='existing'){
    // Zobraz GTFS zastávky v okolí jako žluté kroužky pro výběr
    let b=map.getBounds();
    let pad=0.25;
    fetch(`/api/stops_near?lat=${b.getCenter().lat}&lng=${b.getCenter().lng}&radius_m=5000`)
      .then(r=>r.json()).then(data=>{
        if(data.status!=='success'){showAdminToast(data.message||'Přibliž mapu k oblasti linky',false);return;}
        _missingPickLayer.clearLayers();
        data.stops.forEach(s=>{
          let m=L.circleMarker([s.lat,s.lng],{radius:9,color:'#f59e0b',fillColor:'#fbbf24',fillOpacity:0.7,weight:2});
          m.bindTooltip(`<b>${s.name}</b><br><span style="color:#38bdf8;font-size:10px;">Klikni pro napojení</span>`,{direction:'top',className:'dark-popup'});
          m.on('click',async()=>{
            _missingPickLayer.clearLayers();
            await _saveMissingFix(_missingFixName, s.lat, s.lng, s.name);
          });
          _missingPickLayer.addLayer(m);
        });
        showAdminToast(`🟡 Klikni na správnou zastávku pro "${name}"`,true);
      }).catch(()=>showAdminToast('Chyba načítání zastávek',false));
  } else {
    // Nová zastávka: kříž kurzor, klikni kam patří
    ntAddMode=true; ntPendingPrefill=name;
    document.body.classList.add('nt-add-active');
    showAdminToast(`🚏 Klikni kam patří "${name}"`,true);
  }
}
async function _saveMissingFix(missingName, lat, lng, sourceName){
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:missingName, lat, lng})});
    let rd=await res.json();
    if(rd.status==='success'){
      showAdminToast(`✅ "${missingName}" -> "${sourceName||'nová poloha'}"`,true);
      appLog(`Opravena zastávka: "${missingName}" @ ${lat.toFixed(5)},${lng.toFixed(5)} (${sourceName||'nový bod'})`,'ok');
      delete logMissingStops[missingName];
      if(logCurrentTab==='missing')renderMissingLog();
      if(_missingPickLayer){_missingPickLayer.clearLayers();}
      // Obnov trasu - tohle je klíčové!
      setTimeout(refreshActiveRoute, 300);
    }else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}

function setLogTab(tab){
  logCurrentTab=tab;
  let tabIds=['all','err','spz','missing','report','approx','system'];
  tabIds.forEach(id=>{
    let body=document.getElementById(id==='all'?'log-body':id==='err'?'log-errors-body':id==='spz'?'log-spz-body':id==='missing'?'log-missing-body':id==='report'?'log-report-body':id==='system'?'log-system-body':'log-approx-body');
    if(body)body.style.display=(tab===id?'':'none');
    let btn=document.getElementById(`log-tab-${id}`);
    if(btn){btn.style.background=(tab===id?'#334155':'transparent');btn.style.color='';}
  });
  if(tab==='err'){let b=document.getElementById('log-errors-body');b.innerHTML='';logErrEntries.forEach(e=>{let l=document.createElement('div');l.className='lg-err';l.textContent=`[${e.t}] ${e.msg}`;b.appendChild(l);});b.scrollTop=b.scrollHeight;}
  if(tab==='spz')renderSpzLog();
  if(tab==='missing')renderMissingLog();
  if(tab==='report')loadReportSituace();
  if(tab==='approx')renderApproxLog();
  if(tab==='system')loadSystemLogs();
}
async function loadSystemLogs(){
  let b=document.getElementById('log-system-body');if(!b)return;
  b.innerHTML='<div style="text-align:center;padding:10px;"><i class="fas fa-spinner fa-spin"></i> Načítám...</div>';
  try{
    let r=await fetch('/api/admin/system_logs');let d=await r.json();
    if(d.logs&&d.logs.length>0){
      b.innerHTML=d.logs.map(l=>`<div style="margin-bottom:4px;padding-bottom:4px;border-bottom:1px solid #1e293b;">${l}</div>`).join('');
    }else{b.innerHTML='<div style="text-align:center;padding:10px;">Zatím žádné systémové chyby.</div>';}
    b.scrollTop=b.scrollHeight;
  }catch(e){b.innerHTML='Chyba načítání systémových logů.';}
}
function toggleLogPanel(){let p=document.getElementById('log-panel');if(p)p.style.display=p.style.display==='block'?'none':'block';}
function copyLog(){
  let txt=logEntries.map(e=>`[${e.t}][${e.level}] ${e.msg}`).join('\\n');
  navigator.clipboard.writeText(txt).then(()=>showAdminToast('📋 Zkopírováno',true)).catch(()=>showAdminToast('Chyba kopírování',false));
}
// === Přibližné polohy log ===
let logApproxStops = {};  // name -> {confidence, lat, lng}
function logApproxStop(name, lat, lng, confidence){
  logApproxStops[name] = {name, lat, lng, confidence, ts: new Date().toLocaleTimeString('cs-CZ')};
  let btn = document.getElementById('log-tab-approx');
  if(btn && logCurrentTab !== 'approx') btn.style.color = '#f59e0b';
  if(logCurrentTab === 'approx') renderApproxLog();
}
function renderApproxLog(){
  let body = document.getElementById('log-approx-body');
  if(!body) return;
  body.innerHTML = '';
  let entries = Object.values(logApproxStops).sort((a,b) => a.name.localeCompare(b.name));
  if(!entries.length){body.innerHTML='<div style="color:#64748b;padding:8px;">Žádné přibližné polohy</div>';return;}
  entries.forEach(s=>{
    let div = document.createElement('div');
    div.style.cssText = 'padding:5px 0;border-bottom:1px solid #1e293b;';
    let confLabel = s.confidence==='geocoded'?'Nominatim':'Fuzzy GTFS';
    div.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="color:#f59e0b;font-size:12px;">⚠️ ${s.name}</span>
        <span style="color:#64748b;font-size:10px;">${confLabel} · ${s.ts}</span>
      </div>
      <div style="display:flex;gap:4px;">
        <button style="flex:1;background:#10b981;color:white;border:none;border-radius:4px;padding:3px 6px;font-size:10px;cursor:pointer;">✅ Poloha sedí</button>
        <button style="flex:1;background:#334155;color:#94a3b8;border:none;border-radius:4px;padding:3px 6px;font-size:10px;cursor:pointer;">📍 Přesunout</button>
      </div>`;
    let [okBtn, moveBtn] = div.querySelectorAll('button');
    okBtn.onclick = async () => {
      // Oznac jako overeno - ulozi approx=false
      let res = await fetch('/api/admin/save_stop_override', {method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name: s.name, lat: s.lat, lng: s.lng, approx: false})});
      let rd = await res.json();
      if(rd.status==='success'){
        delete logApproxStops[s.name];
        showAdminToast(`✅ Poloha potvrzena: ${s.name}`, true);
        renderApproxLog();
        setTimeout(refreshActiveRoute, 300);
      }
    };
    moveBtn.onclick = () => {
      document.getElementById('log-panel').style.display = 'none';
      _startMissingFix(s.name, 'new');  // reuse the NT add flow
    };
    body.appendChild(div);
  });
}

async function loadReportSituace(){
  let body=document.getElementById('log-report-body');
  if(!body)return;
  body.innerHTML='<div style="color:#64748b;padding:6px;">Načítám...</div>';
  try{
    let r=await fetch('/api/admin/report_situace?limit=100');
    let data=await r.json();
    body.innerHTML='';
    if(!data.entries||!data.entries.length){body.innerHTML='<div style="color:#64748b;padding:6px;">Žádné záznamy ze serveru</div>';}
    
    // Přidání klientských chyb (logErrEntries) do záložky REPORT, jak uživatel požadoval
    if(logErrEntries.length > 0){
      let head=document.createElement('div');
      head.style.cssText='padding:5px 0;border-bottom:1px solid #1e293b;font-weight:bold;color:#f87171;';
      head.textContent='=== KLIENTSKÉ CHYBY ===';
      body.insertBefore(head, body.firstChild);
      
      logErrEntries.slice().reverse().forEach(e=>{
        let div=document.createElement('div');
        div.style.cssText='padding:3px 0;font-family:monospace;font-size:10px;color:#f87171;';
        div.textContent=`[${e.t}] ${e.msg}`;
        body.insertBefore(div, head.nextSibling);
      });
      
      let sep=document.createElement('div');
      sep.style.cssText='padding:5px 0;border-bottom:1px solid #1e293b;font-weight:bold;color:#60a5fa;margin-top:10px;';
      sep.textContent='=== HLÁŠENÍ SERVERU ===';
      body.appendChild(sep);
    }
    if(data.entries && data.entries.length){
      data.entries.forEach(e=>{
        let div=document.createElement('div');
        div.style.cssText='padding:5px 0;border-bottom:1px solid #1e293b;font-family:monospace;font-size:10px;';
        let clr=e.typ==='DUP_SPZ'?'#f87171':e.typ==='SPZ_RESET'?'#fbbf24':'#94a3b8';
        div.innerHTML=`<span style="color:${clr};font-weight:bold;">[${e.ts}] ${e.typ}</span><br><span style="color:#cbd5e1;">${e.zprava}</span>`;
        body.appendChild(div);
      });
    }
  }catch(err){body.innerHTML='<div style="color:#f87171;padding:6px;">Chyba načítání: '+err+'</div>';}
}
function clearLog(){
  logEntries=[];logErrEntries=[];logSpzEntries=[];logMissingStops={};
  ['log-body','log-errors-body','log-spz-body','log-missing-body','log-report-body','log-approx-body'].forEach(id=>{let el=document.getElementById(id);if(el)el.innerHTML='';});
}
window.addEventListener('error',e=>{appLog('JS chyba: '+(e.message||e)+(e.filename?` (${e.filename}:${e.lineno})`:''),'error');});
window.addEventListener('unhandledrejection',e=>{appLog('Promise chyba: '+(e.reason&&(e.reason.message||e.reason)),'error');});

// === HUD + KAMERA + ŠPENDLÍK ===
let pinMode=false;
function _hudShowRoute(){ if(followId) toggleRoute(followId); }
function stopFollow(){
  followId=null;followInflowId=null;hudMin=false;pinMode=false;
  document.getElementById('hud').style.display='none';
  document.getElementById('hf').style.display='block';
  document.getElementById('hm').style.display='none';
  let pb=document.getElementById('h-pin');if(pb){pb.style.background='#334155';pb.style.color='#94a3b8';}
}
function togglePin(){
  pinMode=!pinMode;
  let btn=document.getElementById('h-pin');
  if(btn){btn.style.background=pinMode?'#f59e0b':'#334155';btn.style.color=pinMode?'#0f172a':'#94a3b8';}
  if(pinMode&&followId){let b=lastArr.find(x=>x.id===followId);if(b&&b.lat)map.setView([b.lat,b.lng]);}
}
function minHud(){hudMin=true;document.getElementById('hf').style.display='none';document.getElementById('hm').style.display='flex';document.getElementById('hud').style.transform='none';}
function maxHud(){hudMin=false;document.getElementById('hf').style.display='block';document.getElementById('hm').style.display='none';document.getElementById('hud').style.transform='translate3d(' + hudX + 'px, ' + hudY + 'px, 0)';}

let hudX=0, hudY=0, isHudDragging=false, hudStartX, hudStartY;
document.addEventListener('DOMContentLoaded', () => {
    let hudHandle = document.getElementById('hud-drag-handle');
    let hudEl = document.getElementById('hud');
    if (hudHandle) {
        hudHandle.addEventListener('mousedown', hudDragStart);
        hudHandle.addEventListener('touchstart', hudDragStart, {passive: false});
        document.addEventListener('mousemove', hudDragMove);
        document.addEventListener('touchmove', hudDragMove, {passive: false});
        document.addEventListener('mouseup', hudDragEnd);
        document.addEventListener('touchend', hudDragEnd);
    }
    function hudDragStart(e) {
        if(e.target.tagName === 'BUTTON' || hudMin) return;
        isHudDragging = true;
        let clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let clientY = e.touches ? e.touches[0].clientY : e.clientY;
        hudStartX = clientX - hudX;
        hudStartY = clientY - hudY;
    }
    function hudDragMove(e) {
        if(!isHudDragging) return;
        e.preventDefault();
        let clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let clientY = e.touches ? e.touches[0].clientY : e.clientY;
        hudX = clientX - hudStartX;
        hudY = clientY - hudStartY;
        hudEl.style.transform = 'translate3d(' + hudX + 'px, ' + hudY + 'px, 0)';
    }
    function hudDragEnd(e) {
        isHudDragging = false;
    }
});
window.toggleFollow=function(busId,inflowId){
  if(followId===busId){stopFollow();return;}
  followId=busId;followInflowId=inflowId||busId;
  // Auto-pin: kamera se okamžitě připne na bus
  pinMode=true;
  let b=lastArr.find(x=>x.id===busId);
  if(b&&b.lat)map.setView([b.lat,b.lng],16);
  document.getElementById('hud').style.display='block';updateHud(b);
  let pb=document.getElementById('h-pin');if(pb){pb.style.background='#f59e0b';pb.style.color='#0f172a';}
  if(hudMin){document.getElementById('hf').style.display='none';document.getElementById('hm').style.display='flex';}
  appLog('Sledování zahájeno (auto-pin): bus '+busId,'info');
};
function updateHud(b){
  if(!b)return;
  document.getElementById('h-trip').textContent='Spoj: '+(b.line||'?')+(b.trip_id?' / '+String(b.trip_id).replace('TRIP-','').substring(0,8):'');
  document.getElementById('h-dest').innerHTML='-> '+(b.destination||'Neznamy cil');
  let se=document.getElementById('h-spz');
  if(b.spz&&b.spz!=='Neznama'){
    if(b.spz_verified){se.innerHTML=`<span style="background:#f59e0b;color:#0f172a;padding:1px 7px;border-radius:4px;font-weight:bold;">${b.spz} <i class="fas fa-check"></i></span>`;}
    else{se.innerHTML=`<span style="background:#f97316;color:#fff;padding:1px 7px;border-radius:4px;font-weight:bold;">${b.spz} <i class="fas fa-clock"></i></span>`;}
  }
  else{se.innerHTML='<span style="color:#64748b;">Ceka...</span>';}
  let de=document.getElementById('h-delay'),dv=parseInt(b.delay);
  if(b.color_class==='bg-blue'){let dm=Math.abs(dv),dh=Math.floor(dm/60),dmin=dm%60;de.innerHTML=`<span style="color:#3b82f6;">Odjezd za ${dh>0?dh+'h ':''} ${dmin}min</span>`;}
  else if(b.color_class==='bg-darkblue')de.innerHTML=`<span style="color:#60a5fa;">Naskok ${Math.abs(dv)} min</span>`;
  else if(b.color_class==='bg-orange')de.innerHTML=`<span style="color:#f59e0b;">Vyzkum</span>`;
  else if(dv>=5)de.innerHTML=`<span style="color:#ef4444;">+${dv} min</span>`;
  else if(dv<-1)de.innerHTML=`<span style="color:#60a5fa;">-${Math.abs(dv)} min</span>`;
  else de.innerHTML='<span style="color:#10b981;">V case</span>';
  document.getElementById('h-status').textContent=b.status||'-';
  document.getElementById('hm-line').textContent='L'+(b.line||'?');
  document.getElementById('h-jr').onclick=()=>showTT(followInflowId||b.id);
}

// === JR MODAL ===
async function showTT(busId){
  document.getElementById('ttm').classList.add('open');
  document.getElementById('ttc').innerHTML="<div style='text-align:center;padding:40px;color:#38bdf8;'><i class='fas fa-circle-notch fa-spin fa-2x'></i><p style='margin-top:14px;font-weight:bold;'>📋 Načítám JízdníŘád…...</p></div>";
  try{let r=await fetch('/api/bus_detail/'+busId);document.getElementById('ttc').innerHTML=await r.text();}
  catch(e){document.getElementById('ttc').innerHTML="<p style='color:#ef4444;padding:20px;text-align:center;'>Chyba pri nacitani JR.</p>";}
}

// === STARTUP WARNING ===
let swShown=false,pageLoad=Date.now();
function checkSW(uptimeSec){
  let sw=document.getElementById('sw');
  if(uptimeSec<600&&(Date.now()-pageLoad)<660000){
    if(!swShown){swShown=true;sw.style.display='block';}
    let rem=Math.max(0,Math.round(600-uptimeSec));
    document.getElementById('sw-cd').textContent=rem>0?'Pribl. '+rem+'s do plneho nacteni':'Dokoncuji...';
  }else{sw.style.display='none';swShown=false;}
}

// === SVG MARKER ===
function buildMarkerSvg(mc,bearing,lineText,isTrain){
  const cM={'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-yellow':'#facc15','bg-bug':'#374151'};
  // Podpora pro bg-depot:HEX format (bus v depu s barvou zony)
  let isDepot=mc&&mc.startsWith('bg-depot:');
  let bgC=isDepot?mc.substring(9):(cM[mc]||'#64748b');
  const tF=(mc==='bg-orange'||mc==='bg-yellow')?'#0f172a':'#fff';
  let lC=String(lineText||'').split('/')[0].trim().replace(/[^0-9]/g,'');
  let lD=lC.length>=4?lC.slice(-3):lC;
  const cx=18,cy=18,r=isTrain?10:12;
  let si='';
  const hB=bearing!==null&&bearing!==undefined&&!['bg-gray','bg-purple','bg-bug'].includes(mc)&&!isTrain&&!isDepot;
  if(hB){
    const rad=(bearing*Math.PI)/180;
    const tX=+(cx+Math.sin(rad)*(r+10)).toFixed(2),tY=+(cy-Math.cos(rad)*(r+10)).toFixed(2);
    const bMX=cx+Math.sin(rad)*(r-1),bMY=cy-Math.cos(rad)*(r-1),pR=rad+Math.PI/2;
    const b1X=+(bMX+Math.sin(pR)*5).toFixed(2),b1Y=+(bMY-Math.cos(pR)*5).toFixed(2);
    const b2X=+(bMX-Math.sin(pR)*5).toFixed(2),b2Y=+(bMY+Math.cos(pR)*5).toFixed(2);
    si+=`<polygon points="${tX},${tY} ${b1X},${b1Y} ${b2X},${b2Y}" fill="${bgC}" stroke="white" stroke-width="1.5" stroke-linejoin="round" opacity="0.95"/>`;
  }
  si+=`<circle cx="${cx+1}" cy="${cy+1}" r="${r}" fill="rgba(0,0,0,0.3)"/>`;
  if(isTrain)si+=`<rect x="${cx-r}" y="${cy-r}" width="${r*2}" height="${r*2}" rx="3" fill="${bgC}" stroke="white" stroke-width="2"/>`;
  else if(isDepot){
    // Bus v depu: plny kruh s barvou zony + tlustsi border
    si+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${bgC}" stroke="white" stroke-width="2.5" opacity="0.9"/>`;
    // Mala ikona garáže uvnitř (H symbol)
    si+=`<text x="${cx}" y="${cy+1}" dominant-baseline="middle" text-anchor="middle" fill="rgba(0,0,0,0.5)" font-size="10" font-family="sans-serif">🅿️</text>`;
  }
  else{const ds=mc==='bg-bug'?'stroke-dasharray="3,2"':'';si+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${bgC}" stroke="white" stroke-width="2" ${ds} opacity="${mc==='bg-bug'?0.7:1}"/>`;}
  if(lD&&!isTrain&&mc!=='bg-bug'&&!isDepot){
    if(lD.length>3){si+=`<text x="${cx}" y="${cy-2.5}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="7" font-family="'Segoe UI',system-ui,sans-serif">${lD.substring(0,3)}</text>`;si+=`<text x="${cx}" y="${cy+5.5}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="6" font-family="'Segoe UI',system-ui,sans-serif">${lD.substring(3)}</text>`;}
    else si+=`<text x="${cx}" y="${cy+1}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="8" font-family="'Segoe UI',system-ui,sans-serif">${lD}</text>`;
  }
  return `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;display:block;">${si}</svg>`;
}


window.onLineClick = function(lat, lng, wpIndex, segId) {
  let isStraight = window.segmentModes && window.segmentModes[segId] === 'straight';
  let content = `
    <div style="font-size:13px; font-weight:bold; color:#0f172a; text-align:center; margin-bottom:8px;">Možnosti úseku</div>
    <button onclick="window.addWaypointAt(${lat}, ${lng}, ${wpIndex + 1})" style="width:100%; margin-bottom:6px; background:#38bdf8; color:#0f172a; border:none; padding:6px; border-radius:4px; font-size:12px; cursor:pointer;"><b>+</b> Vytvořit průjezdní bod</button>
    <button onclick="toggleSegmentMode('${segId}'); map.closePopup();" style="width:100%; background:#10b981; color:white; border:none; padding:6px; border-radius:4px; font-size:12px; cursor:pointer;">${isStraight ? 'Změnit na: Silnice' : 'Změnit na: Vzdušná čára'}</button>
  `;
  L.popup().setLatLng([lat, lng]).setContent(content).openOn(map);
};

window.addWaypointAt = function(lat, lng, spliceIndex) {
  if (window.routeRoutingControl) {
    let wps = window.routeRoutingControl.getWaypoints();
    let newName = 'wp_' + Math.random().toString(36).substr(2, 9);
    let newWp = L.Routing.waypoint(L.latLng(lat, lng), newName);
    if (spliceIndex > 0) {
      let prevName = wps[spliceIndex - 1].name;
      if (window.segmentModes && window.segmentModes[prevName] === 'straight') {
        window.segmentModes[newName] = 'straight';
      }
    }
    wps.splice(spliceIndex, 0, newWp);
    window.routeRoutingControl.setWaypoints(wps);
    map.closePopup();
  }
};

function toggleSegmentMode(stopName) {
  window.segmentModes = window.segmentModes || {};
  window.segmentModes[stopName] = window.segmentModes[stopName] === 'straight' ? 'driving' : 'straight';
  if (window.routeRoutingControl || window.autoRoutingControl) {
    let sBtn = document.getElementById('save-route-btn');
    if (sBtn && sBtn.style.display !== 'none') {
      if (window.routeRoutingControl) window.routeRoutingControl.route();
    } else {
      if (activeRouteId) refreshActiveRoute();
    }
  }
}

function startEditRouteRoads() {
  if(!window.currentRouteData || !window.currentRouteData.stops) return;
  
  if(window.autoRoutingControl) {
    map.removeControl(window.autoRoutingControl);
    window.autoRoutingControl = null;
  }
  if(window.routeRoutingControl) {
    map.removeControl(window.routeRoutingControl);
    window.routeRoutingControl = null;
  }

  let pts = window.currentRouteData.stops.filter(s=>s.lat&&s.lng);
  
  let savedWps = window.currentRouteData.custom_shape_full && window.currentRouteData.custom_shape_full.waypoints;
  let waypoints = [];
  
  if (savedWps && savedWps.length > 0) {
    waypoints = savedWps.map(w => L.Routing.waypoint(L.latLng(w.lat, w.lng), w.name, {isStop: w.isStop}));
    window.segmentModes = window.currentRouteData.custom_shape_full.segmentModes || {};
  } else {
    waypoints = pts.map(s => L.Routing.waypoint(L.latLng(s.lat, s.lng), s.name, {isStop: true}));
    window.segmentModes = {};
  }
  
  if(waypoints.length < 2) return;
  routeLayer.clearLayers();
  document.getElementById('edit-route-btn').style.display = 'none';
  document.getElementById('save-route-btn').style.display = 'block';
  showAdminToast('Přesuňte zastávky pro úpravu jejich pozice na trase. Pro autobusy lze měnit i tvar čáry.', true);
  
  let bus = lastArr.find(b=>b.id===window.currentRouteBusId);
  let isTrain = bus && bus.is_train;

  if (isTrain) {
    let routeCoords = waypoints.map(wp => [wp.lat, wp.lng]);
    let shapePoly = L.polyline(routeCoords, {color: '#f59e0b', weight: 6, opacity: 0.8});
    routeLayer.addLayer(shapePoly);
  } else {
    let osrmRouter = L.Routing.osrmv1({
      serviceUrl: 'https://router.project-osrm.org/route/v1',
      profile: 'driving',
      useHints: false
    });

    let routerObj = {
      route: function(wps, cb, context) {
        window.segmentModes = window.segmentModes || {};
        let hasStraight = false;
        
        for (let i = 0; i < wps.length; i++) {
          if (!wps[i].name) {
            wps[i].name = 'wp_' + Math.random().toString(36).substr(2, 9);
            if (i > 0 && wps[i-1].name && window.segmentModes[wps[i-1].name] === 'straight') {
              window.segmentModes[wps[i].name] = 'straight';
            }
          }
        }
        
        for (let i = 0; i < wps.length - 1; i++) {
          if (window.segmentModes[wps[i].name] === 'straight') hasStraight = true;
        }

        if (!hasStraight) {
          osrmRouter.route(wps, cb, context);
          return;
        }

        osrmRouter.route(wps, function(err, routes) {
          if (err || !routes || !routes.length) {
            cb.call(context, err, routes);
            return;
          }
          let route = routes[0];
          if (route.waypointIndices) {
            let newCoords = [];
            let newIndices = [];
            for (let i = 0; i < wps.length - 1; i++) {
              newIndices.push(newCoords.length);
              let startIdx = route.waypointIndices[i];
              let endIdx = route.waypointIndices[i+1];
              let isStraight = wps[i].name && window.segmentModes[wps[i].name] === 'straight';
              
              if (isStraight) {
                 newCoords.push(wps[i].latLng);
              } else {
                 for (let j = startIdx; j < endIdx; j++) {
                   newCoords.push(route.coordinates[j]);
                 }
              }
            }
            newIndices.push(newCoords.length);
            let lastIdx = route.waypointIndices[wps.length - 1];
            newCoords.push(route.coordinates[lastIdx]);
            
            route.coordinates = newCoords;
            route.waypointIndices = newIndices;
          }
          cb.call(context, err, routes);
        }, context);
      }
    };

    window.routeRoutingControl = L.Routing.control({
      waypoints: waypoints,
      router: routerObj,
      routeWhileDragging: true,
      addWaypoints: false,
      show: false,
      createMarker: function(i, wp, nWps) {
        if (wp.options && wp.options.isStop) return null;
        let m = L.marker(wp.latLng, {
          draggable: true,
          icon: L.divIcon({className: '', html: '<div style="width:14px;height:14px;background:white;border:3px solid #38bdf8;border-radius:50%;cursor:pointer;box-shadow:0 0 3px rgba(0,0,0,0.5);"></div>', iconSize: [14, 14], iconAnchor: [7, 7]})
        });
        m.bindTooltip('Kliknutím odstraníš bod', {direction: 'top'});
        m.on('click', function() {
          let wps = window.routeRoutingControl.getWaypoints();
          let idx = wps.findIndex(w => w.name === wp.name);
          if (idx !== -1) {
            wps.splice(idx, 1);
            window.routeRoutingControl.setWaypoints(wps);
          }
        });
        return m;
      },
      routeLine: function(route, options) {
        let line = L.Routing.line(route, options);
        line.eachLayer(function(l) {
          l.on('click', function(e) {
            let minDist = Infinity;
            let wpIndex = 0;
            for (let i = 0; i < route.waypointIndices.length - 1; i++) {
              let startIdx = route.waypointIndices[i];
              let endIdx = route.waypointIndices[i+1];
              for (let j = startIdx; j < endIdx; j++) {
                let p1 = map.latLngToLayerPoint(route.coordinates[j]);
                let p2 = map.latLngToLayerPoint(route.coordinates[j+1]);
                let p = map.latLngToLayerPoint(e.latlng);
                let d = L.LineUtil.pointToSegmentDistance(p, p1, p2);
                if (d < minDist) {
                  minDist = d;
                  wpIndex = i;
                }
              }
            }
            let wps = window.routeRoutingControl.getWaypoints();
            if (!wps[wpIndex].name) wps[wpIndex].name = 'wp_' + Math.random().toString(36).substr(2, 9);
            window.onLineClick(e.latlng.lat, e.latlng.lng, wpIndex, wps[wpIndex].name);
            L.DomEvent.stop(e);
          });
        });
        return line;
      }
    }).on('routesfound', function(e) {
      window.latestLRMRoute = e.routes[0];
    }).addTo(map);
  }

  // Přidání draggable zastávek pro per-route posun
  pts.forEach((stop, idx) => {
    let baseCls = isTrain ? 'pub-dot pub-dot-train' : 'pub-dot';
    let icon = L.divIcon({className:'',html:`<div class="${baseCls}" style="width:12px;height:12px;border:3px solid red;background:#fff;"></div>`,iconSize:[12,12],iconAnchor:[6,6]});
    let m = L.marker([stop.lat, stop.lng], {icon: icon, draggable: true, zIndexOffset: 2000}).addTo(routeLayer);
    
    let isStraight = window.segmentModes && window.segmentModes[stop.name] === 'straight';
    let pBtn = idx < pts.length - 1 && !isTrain ? `<br><span style="font-size:10px; color:#64748b; font-weight:normal;">Úsek začíná zde</span>` : '';
    m.bindPopup(`<div style="font-size:12px; font-weight:bold; color:#0f172a; text-align:center;">${stop.name}${pBtn}</div>`);
    m.bindTooltip(`Posunout <b>${stop.name}</b> (pro celý směr trasy)`, {direction: 'top'});
    m.on('dragend', async function(e) {
      let pos = e.target.getLatLng();
      let prev_name = idx > 0 ? pts[idx-1].name : "";
      let next_name = idx < pts.length - 1 ? pts[idx+1].name : "";
      try {
        let r = await fetch('/api/admin/save_route_stop_override', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({prev_stop: prev_name, this_stop: stop.name, next_stop: next_name, lat: pos.lat, lng: pos.lng})
        });
        let rd = await r.json();
        if(rd.status === 'success') {
          showAdminToast(`Zastávka ${stop.name} upravena pro tento směr`, true);
          if (window.routeRoutingControl) {
            let wps = window.routeRoutingControl.getWaypoints();
            if (wps[idx]) {
              wps[idx].latLng = pos;
              window.routeRoutingControl.setWaypoints(wps);
            }
          }
        } else {
          showAdminToast('Chyba: ' + rd.message, false);
        }
      } catch(ex) {}
    });
  });
}

async function saveRouteRoads() {
  if(!window.routeRoutingControl || !window.currentRouteData || !window.latestLRMRoute) { 
    showAdminToast('Trasa nenalezena - zkuste pohnout bodem', false); 
    return; 
  }
  let route = window.latestLRMRoute;
  
  let coords = route.coordinates.map(c => [c.lat, c.lng]);
  let wps = window.routeRoutingControl.getWaypoints().map(w => ({
    lat: w.latLng.lat,
    lng: w.latLng.lng,
    name: w.name || '',
    isStop: w.options && w.options.isStop ? true : false
  }));
  let smodes = window.segmentModes || {};
  
  let rk = window.currentRouteData.route_key;
  if(!rk) { showAdminToast('Chybí route_key', false); return; }
  
  document.getElementById('save-route-btn').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ukládám...';
  try {
    let r = await fetch('/api/admin/save_custom_route', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({route_key: rk, points: coords, waypoints: wps, segmentModes: smodes})
    });
    let rd = await r.json();
    if(rd.status === 'success') {
      showAdminToast('Úprava trasy uložena', true);
      closeActiveRoute();
      toggleRoute(window.currentRouteBusId); // reload
    } else {
      showAdminToast('Chyba: ' + rd.message, false);
      document.getElementById('save-route-btn').innerHTML = '<i class="fas fa-save"></i> ULOŽIT (Táhni modrou čáru = trasu, červený bod = zastávku)';
    }
  } catch(e) {
    showAdminToast('Chyba uložení', false);
    document.getElementById('save-route-btn').innerHTML = '<i class="fas fa-save"></i> ULOŽIT (Táhni modrou čáru = trasu, červený bod = zastávku)';
  }
}

function closeActiveRoute(){
  routeLayer.clearLayers();
  if(window.routeRoutingControl) {
    map.removeControl(window.routeRoutingControl);
    window.routeRoutingControl = null;
  }
  if(window.autoRoutingControl) {
    map.removeControl(window.autoRoutingControl);
    window.autoRoutingControl = null;
  }
  if(activeRouteId){let btn=document.getElementById('route-btn-'+activeRouteId);if(btn){btn.textContent='🗺️ Zobrazit trasu';btn.style.background='#334155';}}
  activeRouteId=null;
  let eBtn=document.getElementById('edit-route-btn');if(eBtn)eBtn.style.display='none';
  let sBtn=document.getElementById('save-route-btn');if(sBtn)sBtn.style.display='none';
  let crb=document.getElementById('close-route-btn');if(crb)crb.style.display='none';
}
async function toggleRoute(busId){
  if(activeRouteId===busId){
    routeLayer.clearLayers();activeRouteId=null;
    let btn=document.getElementById('route-btn-'+busId);
    if(btn){btn.textContent='🗺️ Zobrazit trasu';btn.style.background='#334155';}
    let crb=document.getElementById('close-route-btn');if(crb)crb.style.display='none';
    return;
  }
  routeLayer.clearLayers();activeRouteId=busId;
  let btn=document.getElementById('route-btn-'+busId);
  if(btn){btn.innerHTML='<i class="fas fa-spinner fa-spin"></i> Hledám...';btn.style.background='#1e3a8a';}
  showAdminToast('🗺️ Hledám trasu — mapu mezitím můžeš používat',true);
  try{
    let r=await fetch('/api/bus_route/'+busId);
    let data=await r.json();
    if(activeRouteId!==busId)return;
    _renderRoute(busId,data,btn);
  }catch(e){
    if(btn){btn.textContent='Chyba načítání';btn.style.background='#7f1d1d';}
    appLog('Trasa – chyba: '+e,'error');
  }
}

async function refreshActiveRoute(){
  if(!activeRouteId)return;
  let busId=activeRouteId;
  let btn=document.getElementById('route-btn-'+busId);
  routeLayer.clearLayers();
  try{
    let r=await fetch('/api/bus_route/'+busId);
    let data=await r.json();
    if(activeRouteId!==busId)return;
    _renderRoute(busId,data,btn);
    showAdminToast('🗺️ Trasa obnovena',true);
  }catch(e){appLog('Refresh trasy – chyba: '+e,'error');}
}

function _renderRoute(busId,data,btn){
  window.currentRouteData = data;
  window.currentRouteBusId = busId;
  routeLayer.clearLayers();
  if(!data.stops||data.stops.length<2){
    if(btn){btn.textContent=data.error?'Trasa nedostupná ('+data.error+')':'Trasa nedostupná';btn.style.background='#7f1d1d';}
    return;
  }
  let bus=lastArr.find(b=>b.id===busId);
  let delay=bus?parseInt(bus.delay||0):0;
  let status=bus?bus.color_class:'bg-gray';
  let isBug=status==='bg-bug'||status==='bg-gray';
  let isFinished=status==='bg-purple';
  let futColor = isFinished ? '#a855f7' : isBug ? '#64748b' : delay >= 5 ? '#ef4444' : '#3b82f6';
  let pastColor=isBug||isFinished?'#6b7280':'#64748b';
  let pts=data.stops.filter(s=>s.lat&&s.lng);
  let splitIdx=pts.findIndex(s=>!s.passed);
  if(splitIdx===-1)splitIdx=pts.length;
  let isAtStop = false;
  let isWaiting = bus && (bus.status && (bus.status.includes('ceka') || bus.status.includes('zacatek')));
  if (bus && bus.lat && bus.lng && pts.length > 0) {
    let bestDist = Infinity;
    let bestSegmentIdx = 0;

    for (let i = 0; i < pts.length - 1; i++) {
      let v = pts[i];
      let w = pts[i+1];
      let p = bus;
      
      let l2 = (w.lat - v.lat)**2 + (w.lng - v.lng)**2;
      let t = 0;
      if (l2 !== 0) {
        t = ((p.lat - v.lat) * (w.lat - v.lat) + (p.lng - v.lng) * (w.lng - v.lng)) / l2;
        t = Math.max(0, Math.min(1, t));
      }
      
      let projLat = v.lat + t * (w.lat - v.lat);
      let projLng = v.lng + t * (w.lng - v.lng);
      let d2 = (p.lat - projLat)**2 + (p.lng - projLng)**2;
      
      if (d2 < bestDist) {
        bestDist = d2;
        bestSegmentIdx = i;
      }
    }
    
    splitIdx = bestSegmentIdx;

    if (typeof map !== 'undefined' && pts[splitIdx]) {
      let distMeters = map.distance([bus.lat, bus.lng], [pts[splitIdx].lat, pts[splitIdx].lng]);
      if (distMeters < 150) isAtStop = true;
      else if (splitIdx + 1 < pts.length) {
        // Pokud je už blízko k další zastávce (např. na křižovatce těsně před ní)
        let distNext = map.distance([bus.lat, bus.lng], [pts[splitIdx+1].lat, pts[splitIdx+1].lng]);
        if (distNext < 150) {
           isAtStop = true;
           splitIdx = splitIdx + 1;
        }
      }
    }
  }

  // U čekajících autobusů budeme animovat celou trasu od první zastávky
  if (isWaiting) splitIdx = 0;

  let finalIdx=pts.length-1;
  let pastPts=pts.slice(0,Math.min(splitIdx+1,pts.length)).map(s=>[s.lat,s.lng]);
  let futurePts=pts.slice(splitIdx).map(s=>[s.lat,s.lng]);

  let animFn = function(el, speed, ptsArr) {
    if(!el) return;
    let updateLength = () => {
      let len = 0;
      if (typeof map !== 'undefined' && ptsArr && ptsArr.length > 1) {
        for(let i=1; i<ptsArr.length; i++){
          let p1 = map.latLngToLayerPoint(ptsArr[i-1]);
          let p2 = map.latLngToLayerPoint(ptsArr[i]);
          let dx = p1.x - p2.x, dy = p1.y - p2.y;
          len += Math.sqrt(dx*dx + dy*dy);
        }
      } else {
        len = el.getTotalLength ? el.getTotalLength() : 5000;
      }
      if (len === 0) len = 5000;
      
      el.style.setProperty('--r-len', len);
      el.style.strokeDasharray = len + ' ' + (len * 10);
      let drawMs = Math.max(1500, Math.min((len / speed) * 1000, 8000));
      let totalDur = drawMs / 0.65;
      el.style.animation = 'routeDrawLoop ' + totalDur + 'ms ease-in-out infinite';
    };
    
    updateLength();
    
    if (typeof map !== 'undefined') {
      let onZoom = () => {
        if (!el || !el.parentNode) {
          map.off('zoomend', onZoom);
          return;
        }
        updateLength();
      };
      map.on('zoomend', onZoom);
    }
  };

  let bgOp = isBug ? 0.05 : 0.18;
  let fgOp = isBug ? 0.3 : 0.85;
  let futFgOp = isBug ? 0.3 : 0.95;

  if(data.custom_shape && data.custom_shape.length > 0) {
    let shapePoly = L.polyline(data.custom_shape, {color: futColor, weight: 7, opacity: futFgOp, lineCap: 'round', lineJoin: 'round', className: 'route-line-past'});
    if(!isBug && !isFinished) {
      shapePoly.on('add', function() { animFn(this.getElement(), 320, data.custom_shape); });
    }
    routeLayer.addLayer(shapePoly);
  } else {
    let waypoints = pts.filter(s=>s.lat&&s.lng).map(s=>L.latLng(s.lat, s.lng));
    if(waypoints.length >= 2) {
      if (bus && bus.is_train) {
        let routeCoords = waypoints.map(wp => [wp.lat, wp.lng]);
        routeLayer.addLayer(L.polyline(routeCoords,{color:futColor,weight:14,opacity:bgOp,lineCap:'round',lineJoin:'round'}));
        let shapePoly = L.polyline(routeCoords, {color: futColor, weight: 7, opacity: futFgOp, lineCap: 'round', lineJoin: 'round', className: 'route-line-past'});
        if(!isBug && !isFinished) {
          shapePoly.on('add', function() { animFn(this.getElement(), 320, routeCoords); });
        }
        routeLayer.addLayer(shapePoly);
      } else {
        let tempControl = L.Routing.control({
          waypoints: waypoints,
          router: L.Routing.osrmv1({
            serviceUrl: 'https://router.project-osrm.org/route/v1',
            profile: 'driving',
            useHints: false
          }),
          routeWhileDragging: false,
          addWaypoints: false,
          show: false,
          lineOptions: { styles: [{opacity: 0}] },
          createMarker: function() { return null; }
        }).on('routesfound', function(e) {
          let routeCoords = e.routes[0].coordinates.map(c => [c.lat, c.lng]);
          routeLayer.addLayer(L.polyline(routeCoords,{color:futColor,weight:14,opacity:bgOp,lineCap:'round',lineJoin:'round'}));
          let shapePoly = L.polyline(routeCoords, {color: futColor, weight: 7, opacity: futFgOp, lineCap: 'round', lineJoin: 'round', className: 'route-line-past'});
          if(!isBug && !isFinished) {
            shapePoly.on('add', function() { animFn(this.getElement(), 320, routeCoords); });
          }
          routeLayer.addLayer(shapePoly);
        }).addTo(map);
        
        if(window.autoRoutingControl) map.removeControl(window.autoRoutingControl);
        window.autoRoutingControl = tempControl;
      }
    }
  }
  pts.forEach((stop,i)=>{
    let isPast = (i < splitIdx);
    let isFinal = (i === finalIdx);
    let isBusPos = (i === splitIdx && !isFinished && !isWaiting && !isBug);
    let isNext = (i === splitIdx + 1 && i <= finalIdx && !isFinished && !isWaiting && !isBug) || (isWaiting && i === 0 && !isBug);
    let lowConf = stop.confidence==='fuzzy'||stop.confidence==='geocoded';
    let warnHtml = '';
    if(stop.substitute)warnHtml='<br><span style="color:#a855f7;font-size:10px;">🔀 náhradní</span>';
    else if(stop.approx||lowConf)warnHtml='<br><span style="color:#f59e0b;font-size:10px;">⚠️ přibl.</span>';
    
    let icon;
    let br = (bus && bus.is_train) ? '4px' : '50%';
    if(isFinal){
      let fc=isFinished?'#a855f7':futColor;
      icon=L.divIcon({className:'',iconSize:[24,24],iconAnchor:[12,12],html:'<div style="width:22px;height:22px;background:'+fc+';border:3px solid #fff;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:13px;box-shadow:0 0 12px '+fc+',0 2px 8px rgba(0,0,0,.8);">🏁</div>'});
    } else if(isNext){
      icon=L.divIcon({className:'',iconSize:[22,22],iconAnchor:[11,11],html:'<div style="width:18px;height:18px;border-radius:'+br+';background:'+futColor+';border:3px solid #fff;box-shadow:0 0 14px '+futColor+',0 2px 6px rgba(0,0,0,.6);animation:routePulse 1.32s ease-in-out infinite;"></div>'});
    } else if(isBusPos){
      icon=L.divIcon({className:'',iconSize:[16,16],iconAnchor:[8,8],html:'<div style="width:12px;height:12px;border-radius:'+br+';background:#fff;border:3px solid '+futColor+';box-shadow:0 0 10px '+futColor+',0 2px 6px rgba(0,0,0,.5);"></div>'});
    } else if(isPast || isFinished){
      let w = isFinished ? 11 : 9;
      let bg = isFinished ? '#d8b4fe' : '#cbd5e1';
      let brd = isFinished ? '#9333ea' : '#64748b';
      icon=L.divIcon({className:'',iconSize:[w+3,w+3],iconAnchor:[(w+3)/2,(w+3)/2],html:'<div style="width:'+w+'px;height:'+w+'px;border-radius:'+br+';background:'+bg+';border:1.5px solid '+brd+';opacity:1;"></div>'});
    } else {
      let bd=lowConf?'2px dashed #f59e0b':'2px solid rgba(255,255,255,0.9)';
      icon=L.divIcon({className:'',iconSize:[14,14],iconAnchor:[7,7],html:'<div style="width:10px;height:10px;border-radius:'+br+';background:'+futColor+';border:'+bd+';box-shadow:0 0 6px '+futColor+',0 1px 4px rgba(0,0,0,.5);"></div>'});
    }
    
    let zIdx = isFinal?300:isNext?250:isBusPos?200:isPast?-200:-50;
    let m=L.marker([stop.lat,stop.lng],{icon,zIndexOffset:zIdx});
    let timeStr=stop.time?' / <b>'+stop.time+'</b>':'';
    let typeLabel='';
    if (isWaiting && i === 0) typeLabel = ' — ⏳ <b>Počáteční zastávka</b>';
    else typeLabel = isFinal?' — 🏁 <b>Konečná</b>':isNext?' ← <b>Následující zastávka</b>':isBusPos?(isAtStop?' ← <b>Aktuální zastávka</b>':' ← <b>Poslední potvrzená zastávka</b>'):'';
    let emj = (bus && bus.is_train) ? '🚂' : '🚏';
    m.bindTooltip('<span style="font-size:12px;">'+emj+' '+stopDisplayName(stop)+'</span>'+timeStr+typeLabel+warnHtml,{direction:'top',className:'dark-popup'});

    routeLayer.addLayer(m);
  });
  let found=data.stops.filter(s=>s.lat).length;
  let uncertain=data.stops.filter(s=>s.lat&&(s.confidence==='fuzzy'||s.confidence==='geocoded')).length;
  let missing=data.stops.filter(s=>!s.lat);
  missing.forEach(s=>{appLog('Zastávka nenalezena: "'+s.name+'" přidej v NT','warn');logMissingStop(s.name);fetch('/api/admin/report_missing_stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stop_name:s.name,bus_id:busId})}).catch(()=>{});});
  if(IS_ADMIN){data.stops.filter(s=>s.lat&&(s.confidence==='fuzzy'||s.confidence==='geocoded')&&!s.substitute).forEach(s=>logApproxStop(s.name,s.lat,s.lng,s.confidence));}
  appLog('Trasa '+busId+': '+found+'/'+data.stops.length+' (nejisté:'+uncertain+' chybí:'+missing.length+')','info');
  let label='🗺️ Zavřít trasu ('+found+'/'+data.stops.length+' zast.)'+(uncertain?' ⚠️'+uncertain:'')+(missing.length?' ❓'+missing.length:'');
  if(btn){btn.textContent=label;btn.style.background='#1e40af';}
  let crb=document.getElementById('close-route-btn');if(crb)crb.style.display='block';
  if(IS_ADMIN) {
    if(!data.route_key && pts.length > 0 && bus && bus.line) {
      data.route_key = bus.line + '_' + pts[0].name + '_' + pts[pts.length-1].name;
    }
    let erb = document.getElementById('edit-route-btn');
    if(erb) erb.style.display = 'block';
  }
}




// === LINKA EDITOR ===
let leLayer=null,leStops=[],leLineName='',leAddActive=false;
function leInit(){if(!leLayer)leLayer=L.layerGroup().addTo(map);}
function lineEditorOff(){if(leLayer)leLayer.clearLayers();leAddActive=false;document.body.classList.remove('nt-add-active');let b=document.getElementById('le-add-btn');if(b){b.style.background='#334155';b.style.color='#a855f7';}}
function toggleLineEditor(){leInit();let p=document.getElementById('le-editor-panel');if(!p)return;p.style.display=p.style.display==='block'?'none':'block';if(p.style.display==='none')lineEditorOff();}
async function leLoadLine(){
  leInit();leLayer.clearLayers();leStops=[];
  let inp=document.getElementById('le-line-inp');
  let line=(inp&&inp.value||'').trim();if(!line)return;
  leLineName=line;
  let st=document.getElementById('le-status');if(st)st.textContent='Načítám…';
  try{
    let r=await fetch('/api/admin/line_stops?line='+encodeURIComponent(line));
    let data=await r.json();
    if(data.status!=='success'){if(st)st.textContent=data.message||'Chyba';return;}
    leStops=data.stops.map((s,i)=>({...s,_idx:i,_moved:false}));
    if(st)st.textContent=leStops.length+' zastávek pro '+line;
    leRender();
  }catch(e){if(st)st.textContent='Chyba: '+e;}
}
function leRender(){
  leLayer.clearLayers();
  let listEl=document.getElementById('le-stops');if(listEl)listEl.innerHTML='';
  if(leStops.length>=2){
    let coords=leStops.map(s=>[s.lat,s.lng]);
    leLayer.addLayer(L.polyline(coords,{color:'#a855f7',weight:6,opacity:0.85,dashArray:'8,4',lineCap:'round',lineJoin:'round'}));
  }
  leStops.forEach((s,i)=>{
    let col=s._moved?'#f59e0b':'#a855f7';
    let ic=L.divIcon({className:'',iconSize:[18,18],iconAnchor:[9,9],html:'<div style="width:16px;height:16px;border-radius:50%;background:'+col+';border:2px solid white;box-shadow:0 0 8px '+col+';display:flex;align-items:center;justify-content:center;font-size:9px;color:white;font-weight:bold;cursor:grab;">'+(i+1)+'</div>'});
    let m=L.marker([s.lat,s.lng],{icon:ic,draggable:true,zIndexOffset:600});
    m.bindTooltip('<b>'+(s.display_name||s.name)+'</b>',{direction:'top',className:'dark-popup'});
    m.on('dragend',()=>{let pos=m.getLatLng();leStops[i].lat=pos.lat;leStops[i].lng=pos.lng;leStops[i]._moved=true;leRender();});
    leLayer.addLayer(m);
    if(listEl){
      let div=document.createElement('div');
      div.style.cssText='display:flex;align-items:center;gap:6px;padding:4px 2px;border-bottom:1px solid #1e293b;font-size:11px;cursor:pointer;border-radius:4px;';
      div.innerHTML='<span style="color:#64748b;width:18px;text-align:right;">'+(i+1)+'</span><span style="flex:1;color:'+(s._moved?'#f59e0b':'#cbd5e1')+';">'+(s.display_name||s.name)+'</span><button style="background:#3f0000;color:#fca5a5;border:none;border-radius:3px;padding:1px 5px;font-size:10px;cursor:pointer;">✕</button>';
      div.querySelector('button').onclick=e=>{e.stopPropagation();leStops.splice(i,1);leRender();};
      div.onclick=()=>map.setView([s.lat,s.lng],17);
      listEl.appendChild(div);
    }
  });
}
function leAddMode(){
  leAddActive=!leAddActive;
  let btn=document.getElementById('le-add-btn');
  if(leAddActive){document.body.classList.add('nt-add-active');if(btn){btn.style.background='#a855f7';btn.style.color='#fff';}showAdminToast('Klikni na mapu pro přidání zastávky',true);}
  else{document.body.classList.remove('nt-add-active');if(btn){btn.style.background='#334155';btn.style.color='#a855f7';}}
}
async function leSave(){
  if(!leStops.length||!leLineName){showAdminToast('Načti nejprve linku',false);return;}
  let moved=leStops.filter(s=>s._moved);
  if(!moved.length){showAdminToast('Žádné změny k uložení',false);return;}
  let ok=0;
  for(let s of moved){
    try{let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name,lat:s.lat,lng:s.lng})});let rd=await res.json();if(rd.status==='success')ok++;}catch(e){}
  }
  showAdminToast('Uloženo '+ok+'/'+moved.length+' bodů',true);
  leStops.forEach(s=>s._moved=false);leRender();
}

// === NT (Nastaveni tras) - rucni kalibrace poloh zastavek ===
let ntMode=false,ntMoveTimer=null,currentNtEdit=null,ntAddMode=false,ntAddName='';
function stopDisplayName(s){
  // Zobrazovany nazev ma prednost pred systemovym (pouzitym jen pro vyhledavani v JŘ)
  return (s.display_name&&s.display_name.trim())?s.display_name.trim():s.name;
}
function ntDotIcon(cls){return L.divIcon({className:'',html:`<div class="nt-dot ${cls}"></div>`,iconSize:[14,14],iconAnchor:[7,7]});}
function ntDotClass(s){
  let base=s.manual?'nt-dot-manual':(s.flagged?'nt-dot-flagged':'nt-dot-normal');
  let train=s.mode==='train'?' nt-dot-train':'';
  let extra=s.substitute?' nt-dot-substitute':(s.approx?' nt-dot-approx':'');
  return base+train+extra;
}
function ntLabel(s){
  let dn=s.display_name?`<br><span style="color:#38bdf8;">📛 ${s.display_name}</span>`:'';
  let parts=[];
  if(s.manual)parts.push('✅ ručně opraveno');else if(s.flagged)parts.push('⚠️ nejisté');
  if(s.substitute)parts.push('🔀 náhradní');else if(s.approx)parts.push('⚠️ přibl.');
  if(s.lines&&s.lines.length)parts.push('Linky: '+s.lines.join(', '));
  return dn+(parts.length?'<br>'+parts.join(' · '):'');
}
function toggleNT(){
  ntMode=!ntMode;
  let btn=document.getElementById('nt-toggle-btn');
  if(ntMode){btn.style.background='#f59e0b';btn.style.color='#0f172a';showAdminToast('🛠️ NT zapnut – táhni body, klikni pro editaci',true);loadNTStops();}
  else{btn.style.background='transparent';btn.style.color='#f59e0b';ntLayer.clearLayers();document.getElementById('nt-edit-pop').style.display='none';cancelNtAdd();}
}
async function loadNTStops(){
  if(!ntMode)return;
  let b=map.getBounds();
  try{
    let r=await fetch(`/api/admin/route_stops?south=${b.getSouth()}&west=${b.getWest()}&north=${b.getNorth()}&east=${b.getEast()}`);
    let data=await r.json();
    if(!ntMode)return;
    ntLayer.clearLayers();
    if(data.status!=='success'){showAdminToast(data.message||'Chyba načítání',false);return;}
    data.stops.forEach(s=>{
      let m=L.marker([s.lat,s.lng],{icon:ntDotIcon(ntDotClass(s)),draggable:true,zIndexOffset:500});
      m.bindTooltip(`<b>${s.mode==='train'?'🚂':'🚏'} ${s.name}</b>${ntLabel(s)}`,{direction:'top',className:'dark-popup'});
      m.on('click',()=>openNtEdit(s,m));
      m.on('dragend',async()=>{
        let pos=m.getLatLng();m.setIcon(ntDotIcon('nt-dot-saving'));
        let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name,lat:pos.lat,lng:pos.lng})});
        let rd=await res.json();
        if(rd.status==='success'){s.manual=true;m.setIcon(ntDotIcon(ntDotClass(s)));m.setTooltipContent(`<b>${s.mode==='train'?'🚂':'🚏'} ${s.name}</b>${ntLabel(s)}`);showAdminToast(`💾 ${s.name}`,true);}
        else{showAdminToast('Chyba: '+(rd.message||'?'),false);}
      });
      ntLayer.addLayer(m);
    });
  }catch(e){appLog('NT načítání selhalo: '+e,'error');}
}
function renderNtLineChips(lines){
  let wrap=document.getElementById('ntp-lines-chips');
  if(!wrap)return;
  wrap.innerHTML='';
  (lines||[]).forEach(l=>{
    let chip=document.createElement('span');
    chip.style.cssText='background:#334155;color:#cbd5e1;padding:2px 6px 2px 8px;border-radius:10px;font-size:11px;font-weight:bold;display:inline-flex;align-items:center;gap:4px;';
    chip.innerHTML=`${l}<button onclick="removeNtLine('${l}')" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:13px;padding:0;line-height:1;">×</button>`;
    wrap.appendChild(chip);
  });
  if(!lines||!lines.length)wrap.innerHTML='<span style="color:#475569;font-size:10px;">Žádné linky (použije se GTFS)</span>';
}
async function addLineToNtStop(){
  if(!currentNtEdit)return;
  let inp=document.getElementById('ntp-line-add');
  let line=(inp.value||'').trim();
  if(!line){showAdminToast('Zadej číslo linky',false);return;}
  inp.value='';
  let {stop:s}=currentNtEdit;
  try{
    let res=await fetch('/api/admin/assign_line_to_stop',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({stop_name:s.name,line,remove:false,mode:s.mode})});
    let rd=await res.json();
    if(rd.status==='success'){
      s.lines=rd.lines;
      renderNtLineChips(s.lines);
      showAdminToast(`✅ Linka ${line} přidána`,true);
    }else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
async function removeNtLine(line){
  if(!currentNtEdit)return;
  let {stop:s}=currentNtEdit;
  try{
    let res=await fetch('/api/admin/assign_line_to_stop',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({stop_name:s.name,line,remove:true,mode:s.mode})});
    let rd=await res.json();
    if(rd.status==='success'){s.lines=rd.lines;renderNtLineChips(s.lines);showAdminToast(`Linka ${line} odebrána`,true);}
    else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
function openNtEdit(s,m){
  currentNtEdit={stop:s,marker:m};
  let icon=s.mode==='train'?'🚂':'🚏';
  let modeEl=document.getElementById('ntp-mode-icon');if(modeEl)modeEl.textContent=icon;
  document.getElementById('ntp-name').textContent=s.name;
  document.getElementById('ntp-dispname').value=s.display_name||'';
  let ms=document.getElementById('ntp-mode-select');
  if(ms)ms.value=s.mode||'bus';
  document.getElementById('ntp-approx').checked=!!s.approx;
  document.getElementById('ntp-substitute').checked=!!s.substitute;
  let nf=document.getElementById('ntp-notfound');if(nf)nf.checked=!!s.notfound;
  renderNtLineChips(s.lines);
  document.getElementById('nt-edit-pop').style.display='block';
}
async function saveNtFlags(){
  if(!currentNtEdit)return;
  let {stop:s,marker:m}=currentNtEdit;
  let pos=m.getLatLng();
  let approx=document.getElementById('ntp-approx').checked;
  let substitute=document.getElementById('ntp-substitute').checked;
  let notfound=!!(document.getElementById('ntp-notfound')||{}).checked;
  let display_name=document.getElementById('ntp-dispname').value.trim();
  let ms=document.getElementById('ntp-mode-select');
  let mode=ms?ms.value:'bus';
  // Linky jsou uloženy průběžně přes addLineToNtStop/removeNtLine
  // saveNtFlags uloží jen zbývající metadata (approx/substitute/display_name)
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:s.name,lat:pos.lat,lng:pos.lng,approx,substitute,notfound,display_name,mode,custom_lines:s.lines||null})});
    let rd=await res.json();
    if(rd.status==='success'){
      Object.assign(s,{approx,substitute,display_name,mode,manual:true});
      m.setIcon(ntDotIcon(ntDotClass(s)));
      let icon=s.mode==='train'?'🚂':'🚏';
      m.setTooltipContent(`<b>${icon} ${s.name}</b>${ntLabel(s)}`);
      showAdminToast(`💾 Uloženo: ${s.name}`,true);
      document.getElementById('nt-edit-pop').style.display='none';
    }else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
async function deleteNtStop(){
  if(!currentNtEdit)return;
  let {stop:s}=currentNtEdit;
  if(!confirm(`Odebrat zastávku "${s.name}"? Vrátí se na automatickou GTFS polohu.`))return;
  try{
    let res=await fetch('/api/admin/delete_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name, mode:s.mode})});
    let rd=await res.json();
    if(rd.status==='success'){showAdminToast(`🗑️ Odebráno: ${s.name}`,true);document.getElementById('nt-edit-pop').style.display='none';loadNTStops();}
    else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
// NT add mode: + button -> enter name in topbar -> click on map -> saves
// NT add mode: klik + -> kříž -> klik mapu -> prompt pro název -> uloží
let ntPendingPrefill='';
function startNtAdd(prefillName){
  ntAddMode=true;
  ntPendingPrefill=prefillName||'';
  document.body.classList.add('nt-add-active');
  let btn=document.getElementById('nt-add-btn');
  if(btn){btn.style.background='#10b981';btn.style.color='#0f172a';}
  showAdminToast('🚏 Klikni na mapu kde zastávka leží',true);
}
function cancelNtAdd(){
  ntAddMode=false;
  ntPendingPrefill='';
  document.body.classList.remove('nt-add-active');
  let btn=document.getElementById('nt-add-btn');
  if(btn){btn.style.background='transparent';btn.style.color='#10b981';}
}
async function _doAddStop(lat,lng,name){
  if(!name||!name.trim())return;
  name=name.trim();
  let mode=prompt('Zadej mód zastávky (bus / train / mixed):','bus');
  if(!mode)mode='bus';
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,lat,lng,mode})});
    let rd=await res.json();
    if(rd.status==='success'){
      showAdminToast(`✅ Přidána: ${name}`,true);
      appLog(`Přidána zastávka: "${name}" @ ${lat.toFixed(5)},${lng.toFixed(5)}`,'ok');
      delete logMissingStops[name];
      if(logCurrentTab==='missing')renderMissingLog();
      if(!ntMode)toggleNT();else loadNTStops();
      // Po přidání zastávky automaticky obnov aktivní trasu
      setTimeout(refreshActiveRoute, 400);
    }else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
map.on('click',async(e)=>{
  if(leAddActive){let name=prompt('Název zastávky:','');if(name&&name.trim()){leStops.push({name:name.trim(),display_name:'',lat:e.latlng.lat,lng:e.latlng.lng,lines:[leLineName],_moved:true,_idx:leStops.length});leRender();let st=document.getElementById('le-status');if(st)st.textContent=leStops.length+' zastávek';}return;}
  if(!ntAddMode)return;
  let prefill=ntPendingPrefill;
  cancelNtAdd();
  if(prefill){
    // Volano z logu "Chybí" - název z JŘ, žádný prompt, rovnou ulož
    await _saveMissingFix(prefill, e.latlng.lat, e.latlng.lng, null);
  } else {
    // Volano z tlačítka + - zeptej se na název
    let name=prompt('Název nové zastávky:','');
    if(!name||!name.trim())return;
    await _doAddStop(e.latlng.lat,e.latlng.lng,name.trim());
  }
});
map.on('moveend',()=>{
  if(!ntMode)return;
  clearTimeout(ntMoveTimer);ntMoveTimer=setTimeout(loadNTStops,400);
});

// === Zobrazit linky na mapě ===
let linesOverlayLayer=L.layerGroup().addTo(map);
let lineEditorLayer=linesOverlayLayer; // backward compat alias
let _lineColors={};
let _lineColorOrder=[];
// Paleta: první vždy červená, zbytek rotuje přes bezpečné barvy (žádná zelená/žlutozelená)
const _LINE_PALETTE=['#ef4444','#a855f7','#f97316','#38bdf8','#e879f9','#fb923c','#818cf8','#c084fc','#f43f5e','#0ea5e9','#c026d3','#7c3aed'];

function toggleSettingsPanel() {
  let p = document.getElementById('settings-panel');
  if(p) p.style.display = p.style.display === 'none' ? 'block' : 'none';
}
function toggleLowGraphics(enabled) {
  localStorage.setItem('low_graphics_mode', enabled ? '1' : '0');
  if (enabled) document.body.classList.add('low-graphics');
  else document.body.classList.remove('low-graphics');
}
document.addEventListener('DOMContentLoaded', () => {
  let lgm = localStorage.getItem('low_graphics_mode') === '1';
  let cb = document.getElementById('settings-low-graphics');
  if(cb) cb.checked = lgm;
  if(lgm) document.body.classList.add('low-graphics');
});
function _lineColor(line){
  if(!_lineColors[line]){
    if(_lineColorOrder.length===0){
      _lineColors[line]=_LINE_PALETTE[0]; // první linka vždy červená
    } else {
      // Přiřaď deterministicky ale vyhni se zeleným/žlutým odstínům
      let idx=(_lineColorOrder.length % (_LINE_PALETTE.length-1))+1;
      _lineColors[line]=_LINE_PALETTE[idx];
    }
    _lineColorOrder.push(line);
  }
  return _lineColors[line];
}
function _resetLineColors(){_lineColors={};_lineColorOrder=[];}
function toggleLinesPanel(){
  let pan=document.getElementById('lines-overlay-panel');
  if(!pan)return;
  pan.style.display=(pan.style.display==='block'?'none':'block');
}
async function loadLinesOverlay(){
  let q=(document.getElementById('lines-filter-inp')||{}).value||'';
  let status=document.getElementById('lines-status');
  let legend=document.getElementById('lines-legend');
  if(status)status.textContent='Načítám...';
  if(legend)legend.innerHTML='';
  linesOverlayLayer.clearLayers();
  _linePolylines={}; _legendRows={}; _activeLine=null;
  _resetLineColors();
  try{
    let url='/api/lines_map'+(q.trim()?'?q='+encodeURIComponent(q.trim()):'');
    let r=await fetch(url);
    let data=await r.json();
    if(data.status!=='success'){if(status)status.textContent=data.message||'Chyba';return;}
    let lines=data.lines;
    let lineNames=Object.keys(lines).sort();
    if(status)status.textContent=lineNames.length+' linek (Plzeňský kraj)';
    if(legend)legend.innerHTML='';
    lineNames.forEach(l=>{
      let col=_lineColor(l);
      let stops=lines[l];
      if(stops.length<2)return;
      // Linie
      let coords=stops.map(s=>[s.lat,s.lng]);
      let glowL=L.polyline(coords,{color:col,weight:18,opacity:0.12,lineCap:'round',lineJoin:'round'});
      linesOverlayLayer.addLayer(glowL);
      let poly=L.polyline(coords,{color:col,weight:7,opacity:0.85,lineCap:'round',lineJoin:'round'});
      poly.bindTooltip(`<b>Linka ${l}</b><br>${stops.length} zastávek`,{sticky:true,className:'dark-popup'});
      linesOverlayLayer.addLayer(poly);
      _linePolylines[l]=poly;
      // Bod první a poslední zastávky
      [[stops[0],'▶'],[stops[stops.length-1],'■']].forEach(([s,sym])=>{
        let ic=L.divIcon({className:'',iconSize:[14,14],iconAnchor:[7,7],
          html:`<div style="width:12px;height:12px;background:${col};border:2px solid white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:7px;color:white;">${sym}</div>`});
        linesOverlayLayer.addLayer(L.marker([s.lat,s.lng],{icon:ic,zIndexOffset:-10}));
      });
      // Legenda
      if(legend){
        let row=document.createElement('div');
        row.style.cssText='display:flex;align-items:center;gap:6px;padding:2px 0;font-size:11px;cursor:pointer;';
        row.innerHTML=`<div style="width:22px;height:4px;background:${col};border-radius:2px;flex-shrink:0;"></div><span style="color:#cbd5e1;">${l}</span><span style="color:#64748b;font-size:10px;">(${stops.length} zast.)</span>`;
        row.onclick=()=>_highlightLine(l);
        legend.appendChild(row);
        _legendRows[l]=row;
      }
    });
  }catch(e){if(status)status.textContent='Chyba: '+e;appLog('Linky: '+e,'error');}
}
let _activeLine=null;
let _linePolylines={};
let _legendRows={};
function _highlightLine(l){
  if(_activeLine&&_linePolylines[_activeLine]){
    _linePolylines[_activeLine].setStyle({weight:7,opacity:0.85});
    if(_legendRows[_activeLine]){_legendRows[_activeLine].style.background='';_legendRows[_activeLine].style.borderLeft='';}
  }
  if(_activeLine===l){_activeLine=null;return;}
  _activeLine=l;
  let poly=_linePolylines[l];
  if(!poly)return;
  poly.setStyle({weight:10,opacity:1.0});
  poly.bringToFront();
  let col=_lineColor(l);
  map.fitBounds(poly.getBounds(),{padding:[30,30]});
  if(_legendRows[l]){_legendRows[l].style.background='rgba(56,189,248,0.12)';_legendRows[l].style.borderLeft='3px solid '+col;}
}
function clearLinesOverlay(){
  linesOverlayLayer.clearLayers();
  let status=document.getElementById('lines-status');
  let legend=document.getElementById('lines-legend');
  if(status)status.textContent='';
  if(legend)legend.innerHTML='';
}
// Backward compat - loadLineStops still works if called elsewhere
function loadLineStops(){loadLinesOverlay();}
function toggleLineEditor(){toggleLinesPanel();}

// === Veřejné "Zobrazit zastávky" + stop info popup ===
let pubStopsMode=false;
let pubMoveTimer=null;

function showStopInfo(s){
  let icon=s.mode==='train'?'🚂':'🚏';
  document.getElementById('sip-mode-icon').textContent=icon;
  document.getElementById('sip-name-txt').textContent=stopDisplayName(s);
  let dn=document.getElementById('sip-dispname');
  dn.textContent=(s.display_name&&s.display_name.trim())?`Systémový název: ${s.name}`:'';
  let modeEl=document.getElementById('sip-mode');
  modeEl.textContent=s.mode==='train'?'🚂 Vlaková zastávka':s.mode==='bus'?'🚌 Autobusová zastávka':s.mode==='mixed'?'🚌🚂 Bus + vlak':'';
  let linesEl=document.getElementById('sip-lines-wrap');
  linesEl.innerHTML='';
  if(s.lines&&s.lines.length){
    s.lines.forEach(l=>{
      let sp=document.createElement('span');sp.className='sip-line';sp.textContent=l;linesEl.appendChild(sp);
    });
  }else{
    linesEl.innerHTML='<span style="color:#64748b;font-size:11px;">Linky nejsou k dispozici</span>';
  }
  let noteEl=document.getElementById('sip-note');
  noteEl.textContent=s.substitute?'🔀 Náhradní zastávka':s.approx?'⚠️ Přibližná poloha':'';
  
  let depsHtml = '';
  if (window.lastArr && window.lastArr.length) {
    let deps = window.lastArr.filter(b => b.next_stop && stopDisplayName({name: b.next_stop, display_name: ''}) === stopDisplayName({name: s.name, display_name: ''}));
    deps = deps.slice(0, 5);
    if (deps.length > 0) {
      depsHtml = '<div style="margin:10px 0;"><div style="font-size:11px;color:#94a3b8;margin-bottom:4px;">Spoje na cestě sem (odhad dle polohy):</div>';
      deps.forEach(b => {
        let dv = parseInt(b.delay) || 0;
        let dTxt = dv >= 5 ? `<span style="color:#ef4444;">+${dv} min</span>` : (dv > 0 ? `<span style="color:#10b981;">+${dv} min</span>` : (dv < 0 ? `<span style="color:#60a5fa;">${Math.abs(dv)} min napřed</span>` : `<span style="color:#10b981;">Včas</span>`));
        let prev = b.last_stop ? `z ${b.last_stop}` : '';
        depsHtml += `<div style="display:flex;justify-content:space-between;background:rgba(15,23,42,0.5);padding:4px 8px;border-radius:4px;margin-bottom:2px;font-size:12px;">
           <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px;"><b>L${b.line||'?'}</b> ${prev}</span>
           <span>${dTxt}</span>
        </div>`;
      });
      depsHtml += '</div>';
    } else {
      depsHtml = '<div style="color:#64748b;font-size:12px;margin:8px 0;text-align:center;">Žádné aktivní spoje na mapě na cestě sem</div>';
    }
  }
  
  let depsContainer = document.getElementById('sip-live-deps');
  if(!depsContainer) {
    depsContainer = document.createElement('div');
    depsContainer.id = 'sip-live-deps';
    noteEl.parentNode.insertBefore(depsContainer, noteEl.nextSibling);
  }
  depsContainer.innerHTML = depsHtml;

  let idosBtn=document.getElementById('sip-idos-btn');
  if(idosBtn){
    // Rozlišení IDOS URL podle typu zastávky: bus, vlak, nebo smíšená
    let btnIcon, btnText, idosSection;
    if(s.mode === 'train') {
      btnIcon = '🚂'; btnText = ' Odjezdy vlaků'; idosSection = 'vlaky';
    } else if(s.mode === 'mixed') {
      btnIcon = '🚌🚂'; btnText = ' Odjezdy (Bus + Vlak)'; idosSection = 'vlakyautobusymhdvse';
    } else {
      btnIcon = '🚌'; btnText = ' Odjezdy autobusů'; idosSection = 'autobusy';
    }
    idosBtn.textContent = btnIcon + btnText;
    idosBtn.onclick = function() {
      // Použít systémový název (s.name) pro správné vyhledávání v IDOS
      // — display_name je jen pro zobrazení na mapě, v JŘ je evidován systémový
      let searchName = s.name;
      let url = `https://idos.idnes.cz/${idosSection}/odjezdy/vysledky/?f=${encodeURIComponent(searchName)}`;
      document.getElementById('idos-iframe').src = url;
      let modalHeader = document.querySelector('#idos-modal-box span');
      if (modalHeader) modalHeader.textContent = btnIcon + btnText;
      document.getElementById('idos-modal').style.display = 'flex';
      document.getElementById('stop-info-pop').style.display = 'none';
    };
  }
  
  document.getElementById('stop-info-pop').style.display='block';
}

function pubStopIcon(s){
  // Čtverec = vlak, kruh = autobus (i zastávky kopírují tvar markerů vozidel)
  let isTrain=s.mode==='train';
  let isMixed=s.mode==='mixed';
  let base=s.substitute?'pub-dot-substitute':s.approx?'pub-dot-approx':'';
  let trainCls=(isTrain||isMixed)?' pub-dot-train':'';
  let size=isTrain?12:10;
  // Přidej rozlišovací tooltip prefix
  return L.divIcon({className:'',html:`<div class="pub-dot ${base}${trainCls}" style="width:${size}px;height:${size}px;" title="${isTrain?'Vlak':isMixed?'Bus+Vlak':'Bus'}"></div>`,iconSize:[size,size],iconAnchor:[size>>1,size>>1]});
}

async function loadPubStops(){
  if(!pubStopsMode)return;
  let b=map.getBounds();
  let url=`/api/stops_in_view?south=${b.getSouth()}&west=${b.getWest()}&north=${b.getNorth()}&east=${b.getEast()}`;
  try{
    let r=await fetch(url);let data=await r.json();
    if(!pubStopsMode)return;
    pubStopsLayer.clearLayers();
    if(data.status!=='success'){showAdminToast(data.message||'Přibliž mapu pro zobrazení zastávek',false);return;}
    data.stops.forEach(s=>{
      let m=L.marker([s.lat,s.lng],{icon:pubStopIcon(s),zIndexOffset:-50});
      let note=s.substitute?'<br><span style="color:#a855f7;">🔀 náhradní</span>':s.approx?'<br><span style="color:#f59e0b;">⚠️ přibl.</span>':'';
      m.bindTooltip(`<b>${s.mode==='train'?'🚂':'🚏'} ${stopDisplayName(s)}</b>${note}`,{direction:'top',className:'dark-popup'});
      m.on('click',()=>showStopInfo(s));
      pubStopsLayer.addLayer(m);
    });
    appLog(`Zastávky načteny: ${data.stops.length} ve výřezu`,'info');
  }catch(e){console.error('Stops load:',e);appLog('Chyba načítání zastávek: '+e,'error');}
}
function togglePubStops(){
  pubStopsMode=!pubStopsMode;
  let btn=document.getElementById('pub-stops-btn');
  if(pubStopsMode){
    btn.classList.add('active');
    loadPubStops();
  }else{
    btn.classList.remove('active');
    pubStopsLayer.clearLayers();
    document.getElementById('stop-info-pop').style.display='none';
  }
}
map.on('moveend',()=>{
  if(!pubStopsMode)return;
  clearTimeout(pubMoveTimer);
  pubMoveTimer=setTimeout(loadPubStops,400);
});

// === SPZ SEARCH ===
function spzSearch(val){
  let box=document.getElementById('spz-results');val=val.trim().toUpperCase();
  if(val.length<2){box.innerHTML='';return;}
  let matches=lastArr.filter(b=>b.spz&&b.spz!=='Neznama'&&b.spz.toUpperCase().includes(val));
  if(matches.length===0){box.innerHTML='<div style="padding:10px;color:#64748b;font-size:12px;text-align:center;">Zadne vysledky</div>';return;}
  const cM={'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-yellow':'#facc15','bg-bug':'#374151'};
  box.innerHTML=matches.slice(0,8).map(b=>`<div class="sr-item" onclick="zoomToSpz(${b.lat},${b.lng},'${b.id}')"><div style="width:10px;height:10px;border-radius:50%;background:${cM[b.color_class]||'#64748b'};flex-shrink:0;"></div><div><strong style="color:#f59e0b;">${b.spz}</strong><span style="color:#94a3b8;margin-left:5px;">L${b.line||'?'}</span><br><span style="color:#64748b;font-size:10px;">${b.status||''}</span></div></div>`).join('');
}
function zoomToSpz(lat,lng,busId){
  document.getElementById('spz-results').innerHTML='';document.getElementById('spz-search-inp').value='';
  map.setView([lat,lng],16);setTimeout(()=>{ml.eachLayer(l=>{if(l._busId===busId)l.openPopup();});},200);
}

// === MAIN FETCH ===
async function fetchBuses(){
  try{
    let r=await fetch('/api/live_buses'),data=await r.json();
    if(data.server_time)document.getElementById('systemTimeClock').innerText=data.server_time;
    if(typeof data.worker_uptime_seconds==='number')checkSW(data.worker_uptime_seconds);
    if(data.status!=='success')return;
    lastArr=data.buses;
    if(followId){
      let fb=data.buses.find(b=>b.id===followId);
      if(fb&&fb.lat){
        // Pohyb kamery jen kdyz je aktivní ŠPENDLÍK - jinak jen updatuj HUD
        if(pinMode)map.setView([fb.lat,fb.lng]);
        if(!hudMin)updateHud(fb);else document.getElementById('hm-line').textContent='L'+(fb.line||'?');
      } else document.getElementById('h-status').textContent='Ztráta signálu';
    }
    saveAdminInputs();

    // Ochrana pred ztratou fokusu pri psani v popupu
    let isTyping = false;
    let ae = document.activeElement;
    if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'SELECT') && ae.closest('.leaflet-popup')) {
        isTyping = true;
    }

    if (!window.busMarkersMap) window.busMarkersMap = new Map();
    let currentBusIds = new Set();
    isRefreshing=true;

    data.buses.forEach(bus=>{
      if(!bus.lat||!bus.lng)return;
      currentBusIds.add(bus.id);
      let mc=bus.color_class,dv=parseInt(bus.delay),dTxt='';
      if(mc==='bg-gray'||mc==='bg-bug')dTxt='<span style="color:#94a3b8;">N/A</span>';
      else if(mc==='bg-purple')dTxt='<span style="color:#a855f7;">Konečná</span>';
      else if(mc==='bg-orange')dTxt='<span style="color:#f59e0b;">Vyzkum</span>';
      else if(mc==='bg-blue'){let dm=Math.abs(dv),dh=Math.floor(dm/60),dmn=dm%60;dTxt=`<span style="color:#3b82f6;">Za ${dh>0?dh+'h '+dmn+'m':dmn+' min'}</span>`;}
      else if(mc==='bg-darkblue')dTxt=`<span style="color:#60a5fa;">Naskok ${Math.abs(dv)} min</span>`;
      else if(dv>=5)dTxt=`<span style="color:#ef4444;">Zpozdeni ${dv} min</span>`;
      else dTxt=`<span style="color:#10b981;">+${dv} min</span>`;

      // Barveni markeru: depot_color ma prednost pred color_class
      let markerColor=mc;
      if(bus.in_depot&&bus.depot_color){
        // Bus v vozovne: pouzij barvu zony (HEX) pro marker
        // Preved na interni format: ulozi se jako special 'bg-depot-hex'
        markerColor='bg-depot:'+bus.depot_color;
      }
      let icon=L.divIcon({className:'',html:buildMarkerSvg(markerColor,bus.bearing,bus.line,bus.is_train),iconSize:[36,36],iconAnchor:[18,18],popupAnchor:[0,-20]});
      let spzH='',invTxt='',histBtn='';
      if(!bus.is_train){
        if(bus.investigating){spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#ef4444;color:#fff;border-color:#b91c1c;">Vyzkum <i class="fas fa-clock"></i></span></div>`;invTxt=`<div style="color:#ef4444;font-size:10px;font-weight:bold;margin:4px 0;">Zjistuji SPZ (${bus.investigation_spz})</div>`;}
        else if(bus.spz&&bus.spz!=='Neznama'){
          let seznamBtn = '';
          if (bus.spz_verified || bus.admin_flag) {
              seznamBtn = `<a href="javascript:void(0)" onclick="openSeznamAutobusu('${bus.spz}')" class="pa pa-d" style="margin-top:5px; background: #2563eb; color: #fff; border-color: #1d4ed8;">🚌 Fotografie a informace o vozu</a>`;
          }

          if(bus.admin_flag){
            spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#60a5fa;color:#0f172a;border-color:#3b82f6;font-weight:bold;" title="Ověřená SPZ správci systému">${bus.spz} <i class="fas fa-check-double" style="color:#0f172a;"></i></span></div>`;
            histBtn=`<a href="/historie/${bus.spz}" target="_blank" class="pa pa-d" style="margin-top:5px;">📜 Historie vozu</a>${seznamBtn}`;
          } else if(bus.spz_verified){spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" title="SPZ ověřena systémem">${bus.spz} <i class="fas fa-check"></i></span></div>`;histBtn=`<a href="/historie/${bus.spz}" target="_blank" class="pa pa-d" style="margin-top:5px;">📜 Historie vozu</a>${seznamBtn}`;}
          else{spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#f97316;color:#fff;border-color:#c2410c;">${bus.spz} <i class="fas fa-clock"></i></span></div>`;}
        }
        else spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv" style="color:#64748b;">Ceka na overeni</span></div>`;
      }
      let bugW='';
      if(mc==='bg-bug'){let bS=(bus.spz&&bus.spz!=='Neznama')?bus.spz:'Neznama SPZ';bugW=`<div style="background:#3f0000;border:2px solid #ef4444;border-radius:5px;padding:8px;margin:5px 0;font-size:11px;text-align:center;"><b style="color:#ef4444;font-size:13px;letter-spacing:.5px;">\u26d4 NEN\u00cd RE\u00c1LN\u00c1 POLOHA</b><br><span style="color:#fca5a5;font-weight:bold;">PRAVD\u011aPODOBN\u011a BUG NEBO POSLEDN\u00cd ZN\u00c1M\u00c1 POZICE</span><br><span style="color:#94a3b8;font-size:10px;">Pravd\u011bpodobn\u011b SPZ <b style="color:#fbbf24;">${bS}</b> \u2013 pozice nemus\u00ed odpov\u00eddat realit\u011b</span></div>`;}
      let orangeW='';
      if(mc==='bg-orange')orangeW=`<div style="background:rgba(245,158,11,.15);border:1px solid #f59e0b;border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:#f59e0b;"><b>🔍 Vyzkum - bus byl zasekly, nyni jede</b></div>`;
      let depotW='';
      function hexToRgb(hex){let r=0,g=0,b=0;if(hex.length==4){r="0x"+hex[1]+hex[1];g="0x"+hex[2]+hex[2];b="0x"+hex[3]+hex[3];}else if(hex.length==7){r="0x"+hex[1]+hex[2];g="0x"+hex[3]+hex[4];b="0x"+hex[5]+hex[6];}return +r+","+ +g+","+ +b;}
      if(bus.in_depot&&bus.depot_name){let dCol=bus.depot_color||'#facc15';depotW=`<div style="background:rgba(${hexToRgb(dCol)},0.12);border:1px solid ${dCol};border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:${dCol};"><b>🅿️ ${bus.depot_name}</b><br><span style="color:#94a3b8;font-size:10px;">Bus v areálu vozovny</span></div>`;}
      else if(mc==='bg-yellow'||bus.status?.startsWith('Vozovna'))depotW=`<div style="background:rgba(250,204,21,.12);border:1px solid #facc15;border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:#facc15;"><b>🅿️ ${bus.status||'Vozovna'}</b><br><span style="color:#94a3b8;font-size:10px;">Bus v areálu vozovny</span></div>`;
      let sc='#10b981';
      if(mc==='bg-bug')sc='#6b7280';else if(mc==='bg-orange')sc='#f59e0b';
      else if(mc==='bg-yellow')sc='#facc15';
      else if(bus.status?.includes('prilis'))sc='#94a3b8';else if(bus.status?.includes('Stoji'))sc='#ef4444';
      else if(bus.status?.includes('Konečná')||bus.status?.includes('Ztrata'))sc='#a855f7';
      else if(bus.status?.includes('Ceka')||bus.status?.includes('Zacatek'))sc='#3b82f6';
      else if(bus.status?.includes('Odstaven')||bus.status?.includes('signal'))sc='#94a3b8';
      else if(bus.status?.includes('Naskok'))sc='#60a5fa';
      else if(bus.status?.includes('Vozovna'))sc='#facc15';
      let fTxt=(followId===bus.id)?'✖️ Zrusit sledovani':'📡 Sledovat';
      let fSt=(followId===bus.id)?'background:#ef4444;color:#fff;':'background:#3b82f6;color:#fff;';
      let afH=bus.admin_flag?'<span style="background:#1e40af;color:#93c5fd;padding:2px 7px;border-radius:10px;font-size:10px;margin-left:6px;font-weight:bold;">Admin uprava</span>':'';
      let rA=(activeRouteId===bus.id);

      let popH=`
        <div class="ph" style="${mc==='bg-bug'?'background:#1f2937;':''}${mc==='bg-orange'?'background:#1c1400;':''}">
          <h3 class="ph-t" style="${mc==='bg-bug'?'color:#9ca3af;':''}${mc==='bg-orange'?'color:#f59e0b;':''}">Linka ${bus.line}${afH}</h3>
        </div>
        <div class="pb">
          ${bugW}${orangeW}${depotW}
          ${bus.admin_note?`<div style="background:rgba(147,197,253,0.1);border:1px solid #334155;border-radius:5px;padding:5px 8px;margin-bottom:5px;font-size:11px;color:#93c5fd;">${bus.admin_note}</div>`:''}
          <div class="pr"><span class="pl">Cil:</span><span class="pv">${bus.destination||'Neznamy'}</span></div>
          ${spzH}${invTxt}
          <div class="pr"><span class="pl">Status:</span><span class="pv" style="color:${sc};">${bus.status}</span></div>
          <div class="pr" style="border:none;"><span class="pl">JR:</span><span class="pv">${dTxt}</span></div>
          <button class="pa" onclick="showTT('${bus.id}')">📋 Zobrazit jízdní řád</button>
          <button class="pa" style="${fSt}margin-top:5px;" onclick="toggleFollow('${bus.id}','${bus.id}')">${fTxt}</button>
          ${histBtn}
          <button id="route-btn-${bus.id}" class="pa pa-d" style="margin-top:5px;${rA?'background:#1e40af;':''}" onclick="toggleRoute('${bus.id}')">${rA?'🗺️ Skryt trasu':'🗺️ Zobrazit trasu'}</button>
        </div>`;

      if(IS_ADMIN){
        let oSpz=bus.spz==='Neznama'?'':bus.spz;
        let cSpz=restoreAdminInput(bus.id,'spz')??oSpz;
        let cSt=restoreAdminInput(bus.id,'st')??bus.status;
        let cNote=restoreAdminInput(bus.id,'note')??(bus.admin_note||'');
        // Predpocitane promenne pro admin lock tlacitko (reseni 'bus is not defined' pri onclick)
        let adminIsVerified=bus.admin_spz_verified===true;
        let adminVerifyAction=adminIsVerified?'admin_unverify_spz':'admin_verify_spz';
        let adminVerifyBg=adminIsVerified?'#1d4ed8':'#1e293b';
        let adminVerifyColor=adminIsVerified?'#bfdbfe':'#94a3b8';
        let adminVerifyBorder=adminIsVerified?'#3b82f6':'#334155';
        let adminVerifyText=adminIsVerified?'🔒 SPZ UZAMČENA ADMINEM (klikni pro odemčení)':'🔓 Ověřit SPZ adminem (Admin Lock)';
        let hasSPZ=bus.spz&&bus.spz!=='Neznama';
        // Predstav tlacitko jako hotovy HTML string (bez vnorenych backticks - JS to neumi parsovat)
        let adminLockBtn='';
        if(hasSPZ){
          adminLockBtn='<button id="adm_lock_'+bus.id+'" '
            +'onclick="let b=document.getElementById(\\\'adm_lock_'+bus.id+'\\\');'
            +'adminAction(\\\''+adminVerifyAction+'\\\',\\\''+bus.id+'\\\');'
            +'if(\\\''+adminVerifyAction+'\\\'===\\\'admin_verify_spz\\\'){'
            +'b.style.background=\\\'#1d4ed8\\\';b.style.color=\\\'#bfdbfe\\\';b.style.borderColor=\\\'#3b82f6\\\';'
            +'b.textContent=\\\'🔒 SPZ UZAMČENA ADMINEM\\\';'
            +'}else{'
            +'b.style.background=\\\'#1e293b\\\';b.style.color=\\\'#94a3b8\\\';b.style.borderColor=\\\'#334155\\\';'
            +'b.textContent=\\\'🔓 Ověřit SPZ adminem (Admin Lock)\\\';'
            +'}" '
            +'style="width:100%;margin-top:6px;padding:9px;border:1px solid '+adminVerifyBorder+';border-radius:5px;'
            +'font-size:12px;cursor:pointer;font-weight:bold;touch-action:manipulation;'
            +'background:'+adminVerifyBg+';color:'+adminVerifyColor+';transition:all .2s;">'
            +adminVerifyText+'</button>';
        }
        popH+=`<style>.adm-inp{width:100%;box-sizing:border-box;background:#0f172a;color:white;border:1px solid #334155;border-radius:5px;padding:9px;font-size:13px;margin-top:4px;}.adm-inp:focus{outline:none;border-color:#38bdf8;}.adm-btn{width:100%;padding:11px;border:none;border-radius:6px;font-size:13px;font-weight:bold;cursor:pointer;margin-top:4px;touch-action:manipulation;}.adm-toggle-btn{width:100%;padding:9px;background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:5px;font-size:12px;cursor:pointer;margin-top:8px;touch-action:manipulation;}
@keyframes routeDrawLoop {
  0% { stroke-dashoffset: var(--r-len); }
  65% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 0; }
}
</style>
          <div style="border-top:1px solid #334155;margin-top:6px;padding:10px 13px;background:#0a0f1e;border-radius: 0 0 5px 5px;">
            <strong style="color:#38bdf8;font-size:12px;letter-spacing:.5px;">🔧 ADMIN PANEL</strong>
            <div style="color:#94a3b8;font-size:10px;margin-top:2px;font-family:monospace;word-break:break-all;">ID vozu: ${bus.id}</div>
            
            <div style="display:flex;gap:6px;margin-top:8px;">
              <input type="text" id="adm_spz_${bus.id}" value="${cSpz}" data-orig="${oSpz}" placeholder="SPZ" class="adm-inp" style="flex:2;margin-top:0;">
              <button onclick="adminSetSPZ('${bus.id}')" style="flex:1;background:#10b981;color:white;border:none;border-radius:5px;font-size:13px;cursor:pointer;font-weight:bold;padding:9px;touch-action:manipulation;">💾 Uložit</button>
            </div>
            ${adminLockBtn}
            <div style="display:flex;gap:6px;margin-top:6px;">
              <button onclick="adminAction('recheck_spz','${bus.id}')" style="flex:1;background:#f59e0b;color:#0f172a;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:9px;touch-action:manipulation;">🔍 Hledat</button>
              <button onclick="adminDelete('${bus.id}')" style="flex:1;background:#ef4444;color:white;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:9px;touch-action:manipulation;">🗑️ Smazat</button>
            </div>
            
            <button class="adm-toggle-btn" onclick="let el=document.getElementById('adm_grafika_${bus.id}'); if(el.style.display==='none'){el.style.display='block';this.innerText='🔼 Skrýt vzhled a úpravy';}else{el.style.display='none';this.innerText='🎨 Vzhled a další úpravy';}">🎨 Vzhled a další úpravy</button>
            
            <div id="adm_grafika_${bus.id}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
              <input type="text" id="adm_st_${bus.id}" value="${cSt}" data-orig="${bus.status}" placeholder="Status text..." class="adm-inp">
              <select id="adm_col_${bus.id}" class="adm-inp" style="margin-top:6px;">
                <option value="">-- Výchozí barva --</option>
                <option value="bg-gray" ${bus.color_class==='bg-gray'?'selected':''}>Šedá</option>
                <option value="bg-blue" ${bus.color_class==='bg-blue'?'selected':''}>Světle modrá</option>
                <option value="bg-darkblue" ${bus.color_class==='bg-darkblue'?'selected':''}>Tmavě modrá</option>
                <option value="bg-green" ${bus.color_class==='bg-green'?'selected':''}>Zelená</option>
                <option value="bg-red" ${bus.color_class==='bg-red'?'selected':''}>Červená</option>
                <option value="bg-purple" ${bus.color_class==='bg-purple'?'selected':''}>Fialová</option>
                <option value="bg-orange" ${bus.color_class==='bg-orange'?'selected':''}>Oranžová</option>
                <option value="bg-bug" ${bus.color_class==='bg-bug'?'selected':''}>Označeno jako BUG</option>
              </select>
              <input type="text" id="adm_note_${bus.id}" value="${cNote}" data-orig="${bus.admin_note||''}" placeholder="Poznámka..." class="adm-inp" style="margin-top:6px;">
              <div style="display:flex;gap:6px;margin-top:8px;">
                <button onclick="adminSaveAll('${bus.id}',true)" class="adm-btn" style="flex:1;background:#1e40af;color:white;">📌 Uložit natrvalo</button>
                <button onclick="adminSaveAll('${bus.id}',false)" class="adm-btn" style="flex:1;background:#334155;color:#94a3b8;">⏱️ Dočasně</button>
              </div>
              <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:10px;padding-top:8px;border-top:1px solid #1e293b;">
                <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:12px;color:#93c5fd;flex:1;min-width:100px;touch-action:manipulation;">
                  <input type="checkbox" id="adm_flag_${bus.id}" ${bus.admin_flag?'checked':''} onchange="adminAction('set_admin_flag','${bus.id}',{flag:this.checked})" style="width:18px;height:18px;cursor:pointer;">
                  Admin úprava
                </label>
                <button onclick="adminAction('mark_bug','${bus.id}')" style="flex:1;background:#3f0000;color:#fca5a5;border:1px solid #ef4444;border-radius:5px;font-size:11px;cursor:pointer;padding:7px;touch-action:manipulation;font-weight:bold;">⛔ BUG</button>
                <button onclick="adminAction('reset_admin','${bus.id}')" style="flex:1;background:transparent;color:#94a3b8;border:1px solid #334155;border-radius:5px;font-size:11px;cursor:pointer;padding:7px;touch-action:manipulation;">🔄 Reset</button>
              </div>
            </div>
          </div>`;
      }
      
      let existingMarker = window.busMarkersMap.get(bus.id);
      if (existingMarker) {
          existingMarker.setLatLng([bus.lat, bus.lng]);
          existingMarker.setIcon(icon);
          if (!(isTyping && openPopupBusId === bus.id)) {
              existingMarker.setPopupContent(popH);
          }
      } else {
          let m = L.marker([bus.lat, bus.lng], {icon, zIndexOffset: 1000});
          m.bindPopup(popH, {className:'dark-popup', maxWidth:300});
          m._busId = bus.id;
          m.on('popupopen', ()=>{openPopupBusId=bus.id;});
          m.on('popupclose', ()=>{if(openPopupBusId===bus.id)openPopupBusId=null;});
          m.addTo(ml);
          window.busMarkersMap.set(bus.id, m);
      }
    });

    for (let [id, m] of window.busMarkersMap.entries()) {
        if (!currentBusIds.has(id)) {
            ml.removeLayer(m);
            window.busMarkersMap.delete(id);
        }
    }

    setTimeout(()=>{isRefreshing=false;},50);

    // Komplexní logování stavu mapy
    if(IS_ADMIN){
      let total=data.buses.length;
      let noSpz=data.buses.filter(b=>!b.spz||b.spz==='Neznama').length;
      let verified=data.buses.filter(b=>b.spz_verified).length;
      let bug=data.buses.filter(b=>b.color_class==='bg-bug').length;
      appLog(`Mapa: ${total} busů | SPZ: ${verified}✅ ${total-noSpz-verified}⏳ ${noSpz}❓${bug?' '+bug+'🐛':''}`, 'info');
      // SPZ log — loguj jen změny stavu, ne každý tik
      data.buses.forEach(b=>{
        if(b.is_train)return;
        let prev=window._spzPrev&&window._spzPrev[b.id];
        let cur=`${b.spz||'?'}|${b.spz_verified?'ok':'pending'}`;
        if(!prev){window._spzPrev=window._spzPrev||{};window._spzPrev[b.id]=cur;return;}
        if(prev!==cur){
          window._spzPrev[b.id]=cur;
          if(b.spz&&b.spz!=='Neznama'){
            appLogSpz(b.id,b.spz,b.spz_verified?'ok':'pending',b.spz_verified?`✅ Ověřeno (L${b.line})`:`⏳ Čeká na ověření (L${b.line})`);
          }else{
            appLogSpz(b.id,'Neznámá','err',`❓ Bez SPZ (L${b.line}, stav: ${b.status})`);
          }
        }
      });
    }

  }catch(e){
    console.error(e);
    isRefreshing=false;
    appLog('fetchBuses chyba: '+e.message,'error');
  }
}
fetchBuses();
setInterval(fetchBuses,10000);

// ═══════════════════════════════════════════════════════════
// VOZOVNY (DEPOT ZONES) — admin draw + public garage icons
// ═══════════════════════════════════════════════════════════
let depotZones=[], depotLayer=L.layerGroup().addTo(map), depotDrawMode=false, depotPoints=[], depotDrawPolyline=null, depotEditId=null;
const DEPOT_ICON=L.divIcon({className:'',html:`<div style="font-size:22px;line-height:1;filter:drop-shadow(0 1px 3px #000);" title="Vozovna">🅿️</div>`,iconSize:[28,28],iconAnchor:[14,14]});

// Načti a zobraz vozovny (volá se při startu + po každé změně)
async function loadDepotZones(){
  try{
    let r=await fetch('/api/depot_zones'),d=await r.json();
    if(d.status!=='success')return;
    depotZones=d.zones;
    renderDepotZones();
    if(IS_ADMIN)renderDepotList();
  }catch(e){console.error('[DEPOT]',e);}
}

function renderDepotZones(){
    if(!window._depotMarkersMap) { window._depotMarkersMap = new Map(); window._depotPolysMap = new Map(); }
    let currentNames = new Set(depotZones.map(z => z.name));
    
    // Odstranění starých vozoven
    for(let [name, mk] of window._depotMarkersMap.entries()) {
        if(!currentNames.has(name)) {
            depotLayer.removeLayer(mk);
            let poly = window._depotPolysMap.get(name);
            if(poly) depotLayer.removeLayer(poly);
            window._depotMarkersMap.delete(name);
            window._depotPolysMap.delete(name);
        }
    }
    
    depotZones.forEach(z=>{
        if(!z.polygon||z.polygon.length<3)return;
        let zColor=z.color||'#facc15';
        
        let poly = window._depotPolysMap.get(z.name);
        if(!poly) {
            poly=L.polygon(z.polygon,{
                color:zColor,fillColor:zColor,
                fillOpacity:0.13,weight:2,dashArray:'6,4',opacity:0.7,
            });
            window._depotPolysMap.set(z.name, poly);
            depotLayer.addLayer(poly);
        } else {
            poly.setLatLngs(z.polygon);
        }
        
        let center = poly.getBounds().getCenter();
        let mk = window._depotMarkersMap.get(z.name);
        if(!mk) {
            let depotIconHtml=`<div style="font-size:22px;line-height:1;filter:drop-shadow(0 0 4px ${zColor}) drop-shadow(0 1px 3px #000);cursor:pointer;" title="Vozovna: ${z.name}">🅿️</div>`;
            let depotIcon=L.divIcon({className:'',html:depotIconHtml,iconSize:[28,28],iconAnchor:[14,14]});
            mk=L.marker(center,{icon:depotIcon,zIndexOffset:500});
            window._depotMarkersMap.set(z.name, mk);
            
            let popId = 'depot_pop_' + Math.random().toString(36).substr(2,9);
            mk._popId = popId;
            mk._zName = z.name;
            
            let popHtml = `<div id="${popId}" style="background:#0f172a;color:white;padding:15px;width:100%;box-sizing:border-box;font-family:sans-serif;max-height:85vh;overflow-y:auto;overflow-x:hidden;">
                <div style="font-weight:bold;font-size:16px;margin-bottom:12px;color:${zColor};display:flex;align-items:center;gap:6px;">
                    <span>🅿️ Vozovna: ${z.name}</span>
                </div>
                <div style="font-weight:bold;font-size:13px;color:#cbd5e1;margin-bottom:6px;">VOZIDLA VE VOZOVNĚ:</div>
                <div id="${popId}_active" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px;">Načítám...</div>
                <div style="margin-top:16px;border-top:1px dashed #334155;padding-top:12px;">
                    <div style="font-size:13px;color:#cbd5e1;font-weight:bold;margin-bottom:10px;">Historie odjezdů a příjezdů</div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;align-items:center;">
                        <input type="text" id="${popId}_search" placeholder="🔍 SPZ..." autocomplete="off" style="background:#1e293b;border:1px solid #334155;color:white;padding:4px 8px;border-radius:4px;font-size:12px;width:100px;">
                        <select id="${popId}_sort" style="background:#1e293b;border:1px solid #334155;color:white;padding:4px 8px;border-radius:4px;font-size:12px;">
                            <option value="desc">Nejnovější</option>
                            <option value="asc">Nejstarší</option>
                        </select>
                    </div>
                    <div id="${popId}_hist" style="font-size:12px;color:#94a3b8;width:100%;overflow-x:auto;">Načítám historii...</div>
                </div>
            </div>`;
            mk.bindPopup(popHtml,{className:'dark-popup', maxWidth:500, minWidth:460});
            
            mk.on('popupopen', function() {
                window._activeDepotPopId = mk._popId;
                window._activeDepotName = mk._zName;
                if(window.updateActiveDepotPopup) window.updateActiveDepotPopup();
            });
            mk.on('popupclose', function() {
                window._activeDepotPopId = null;
                window._activeDepotName = null;
            });
            
            depotLayer.addLayer(mk);
        }
    });
    
    // Aktualizuj otevřené popup okno bez refreshování celé mapy
    if(window.updateActiveDepotPopup) window.updateActiveDepotPopup();
}

window.updateActiveDepotPopup = function() {
    let zName = window._activeDepotName;
    let popId = window._activeDepotPopId;
    if(!zName || !popId) return;
    
    let z = depotZones.find(dz => dz.name === zName);
    if(!z) return;
    
    let activeDiv = document.getElementById(popId+'_active');
    if(activeDiv) {
        if(z.buses && z.buses.length) {
            let seenSpz = new Set();
            let uniqueBuses = [];
            for(let b of z.buses) {
                let spzKey = b.spz || '?';
                if(!seenSpz.has(spzKey)) { seenSpz.add(spzKey); uniqueBuses.push(b); }
            }
            let zColor = z.color || '#facc15';
            activeDiv.innerHTML = uniqueBuses.map(b=>{
                let adminDel = IS_ADMIN && b.session_id ? `<button onclick="deleteDepotRecord('${b.session_id}','${z.name}')" style="background:transparent;border:none;color:#ef4444;cursor:pointer;font-size:10px;padding:0 2px;margin-left:4px;" title="Smazat">❌</button>` : '';
                return `<span style="background:rgba(255,255,255,0.05);border:1px solid #334155;color:${zColor};padding:4px 8px;border-radius:6px;font-weight:bold;font-size:13px;display:inline-flex;align-items:center;gap:4px;">
                    ${b.spz||'?'}
                    <span style="color:#64748b;font-size:10px;font-weight:normal;">L${b.line||'?'}</span>
                    ${b.spz_verified?'<i class="fas fa-check" style="color:#10b981;font-size:10px;"></i>':''}
                    ${adminDel}
                </span>`;
            }).join('');
        } else {
            activeDiv.innerHTML = '<span style="color:#64748b;font-size:12px;padding:4px;">Žádný bus v depu</span>';
        }
    }
    
    let histDiv = document.getElementById(popId+'_hist');
    if(histDiv && !histDiv._eventsAttached) {
        histDiv._eventsAttached = true;
        let searchInp = document.getElementById(popId+'_search');
        let sortSel = document.getElementById(popId+'_sort');
        
        async function fetchHist() {
            if(!histDiv) return;
            histDiv.innerHTML = '<div style="text-align:center;padding:10px;"><i class="fas fa-spinner fa-spin"></i> Načítám...</div>';
            try {
                let q = searchInp ? searchInp.value : '';
                let sDir = sortSel ? sortSel.value : 'desc';
                let url = '/api/depot_history?depot_name='+encodeURIComponent(z.name)+'&q='+encodeURIComponent(q)+'&sort='+encodeURIComponent(sDir);
                let r = await fetch(url);
                let d = await r.json();
                if(d.status==='success' && d.data && d.data.length>0) {
                    let hMap = new Map();
                    for(let h of d.data) {
                        let k = h.spz; // Sjednotíme podle SPZ - zobrazí se pouze poslední (nejnovější/nejstarší podle řazení) návštěva dané SPZ
                        if(!hMap.has(k)) hMap.set(k, h);
                    }
                    let uniqueHist = Array.from(hMap.values());
                    
                    let tableRows = uniqueHist.map(h=>{
                        let fmtT = (iso) => {
                            if(!iso) return '';
                            let dt = new Date(iso);
                            if(isNaN(dt)) return iso;
                            // Krátký formát, např. "19. 8. 08:06"
                            return dt.toLocaleString('cs-CZ', {day:'numeric', month:'numeric', hour:'2-digit', minute:'2-digit'});
                        };
                        let lTime = h.left_at ? fmtT(h.left_at) : '<span style="color:#10b981;font-weight:bold;">Nyní parkuje</span>';
                        let aTime = h.arrived_at ? fmtT(h.arrived_at) : 'Neznámý';
                        let impr = h.is_imprecise ? ' <span title="Nepřesný čas (Reset mapy)" style="color:#facc15;font-size:10px;">⚠️</span>' : '';
                        let adminDel = IS_ADMIN ? `<button onclick="deleteDepotRecord('${h.id}','${z.name}')" style="background:transparent;border:none;color:#ef4444;cursor:pointer;font-size:10px;padding:2px 4px;" title="Smazat ze záznamu">❌</button>` : '';
                        return `<tr style="border-bottom:1px solid #1e293b;">
                            <td style="padding:4px;color:#f59e0b;font-weight:bold;white-space:nowrap;">${h.spz}</td>
                            <td style="padding:4px;font-size:11px;white-space:nowrap;">${aTime}${impr}</td>
                            <td style="padding:4px;font-size:11px;white-space:nowrap;">${lTime}</td>
                            <td style="padding:4px;text-align:right;">${adminDel}</td>
                        </tr>`;
                    }).join('');
                    histDiv.innerHTML = `<table style="width:100%;border-collapse:collapse;color:#cbd5e1;table-layout:auto;">
                        <thead><tr style="background:#1e293b;text-align:left;">
                            <th style="padding:4px;color:#38bdf8;font-weight:bold;">SPZ</th>
                            <th style="padding:4px;color:#38bdf8;font-weight:bold;">Příjezd</th>
                            <th style="padding:4px;color:#38bdf8;font-weight:bold;">Odjezd</th>
                            <th style="padding:4px;"></th>
                        </tr></thead>
                        <tbody>${tableRows}</tbody>
                    </table>`;
                } else {
                    histDiv.innerHTML = '<div style="text-align:center;padding:10px;">Žádná historie nalezena</div>';
                }
            } catch(e) {
                histDiv.innerHTML = '<div style="color:#ef4444;padding:10px;">Chyba načítání</div>';
            }
        }
        
        fetchHist();
        
        let debounce = null;
        let attachEv = (el, type='input') => {
            if(!el) return;
            el.addEventListener(type, ()=>{
                clearTimeout(debounce);
                debounce = setTimeout(fetchHist, 400);
            });
            if(type==='input') {
                el.addEventListener('keydown', e => e.stopPropagation());
                el.addEventListener('keyup', e => e.stopPropagation());
                el.addEventListener('keypress', e => e.stopPropagation());
            }
        };
        attachEv(searchInp, 'input');
        attachEv(sortSel, 'change');
    }
}

window.deleteDepotRecord = async function(id, depotName) {
    if(!confirm("Opravdu smazat záznam z historie vozovny " + depotName + "? (pokud je vůz aktivní uvnitř, zmizí ihned)")) return;
    try {
        let r = await fetch('/api/admin/delete_depot_history', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
        let d = await r.json();
        if(d.status==='success') {
            appLog('Záznam z depa smazán', 'ok');
            loadDepotZones();
        } else {
            appLog('Chyba mazání: '+d.message, 'error');
        }
    } catch(e) { appLog('Chyba komunikace při mazání z depa', 'error'); }
};

function renderDepotList(){
  let el=document.getElementById('depot-zone-list');
  if(!el)return;
  if(depotZones.length===0){el.innerHTML='<div style="color:#64748b;font-size:12px;text-align:center;padding:8px;">Žádné vozovny</div>';return;}
  el.innerHTML=depotZones.map(z=>`
    <div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid #1e293b;">
      <div style="width:10px;height:10px;border-radius:2px;background:${z.color||'#facc15'};flex-shrink:0;"></div>
      <span style="flex:1;font-size:12px;color:#e2e8f0;">${z.name}</span>
      <button onclick="depotEditZone('${z.id}')" style="background:#1e40af;color:#93c5fd;border:none;border-radius:4px;padding:3px 7px;font-size:10px;cursor:pointer;">✏️ Edit</button>
      <button onclick="depotDeleteZone('${z.id}','${z.name.replace(/'/g,"\\'")}')" style="background:#7f1d1d;color:#fca5a5;border:none;border-radius:4px;padding:3px 7px;font-size:10px;cursor:pointer;">🗑️</button>
    </div>`).join('');
}

async function depotDeleteZone(id,name){
  if(!confirm('Smazat vozovnu "'+name+'"?'))return;
  let r=await fetch('/api/admin/delete_depot_zone',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  let d=await r.json();
  if(d.status==='success'){appLog('Vozovna smazána','ok');await loadDepotZones();}
  else appLog('Chyba: '+d.message,'error');
}

function depotEditZone(id){
  let z=depotZones.find(x=>String(x.id)===String(id));
  if(!z)return;
  document.getElementById('depot-name-inp').value=z.name;
  document.getElementById('depot-color-inp').value=z.color||'#facc15';
  depotEditId=id;
  depotPoints=z.polygon.map(p=>L.latLng(p[0],p[1]));
  depotDrawMode=true;
  updateDepotDrawPreview();
  document.getElementById('depot-draw-panel').style.display='block';
  appLog('Editujete vozovnu "'+z.name+'" — přidejte body nebo uložte','info');
}

function startDepotDraw(){
  depotDrawMode=true;depotPoints=[];depotEditId=null;
  document.getElementById('depot-name-inp').value='';
  document.getElementById('depot-color-inp').value='#facc15';
  if(depotDrawPolyline){depotLayer.removeLayer(depotDrawPolyline);depotDrawPolyline=null;}
  document.getElementById('depot-draw-panel').style.display='block';
  appLog('Klikej na mapu pro přidání bodů vozovny. Double-click = uložit.','info');
}

function updateDepotDrawPreview(){
  if(depotDrawPolyline)depotLayer.removeLayer(depotDrawPolyline);
  if(depotPoints.length<2)return;
  depotDrawPolyline=L.polygon(depotPoints,{color:'#facc15',fillOpacity:0.15,dashArray:'4,3',weight:2}).addTo(depotLayer);
}

map.on('click',function(e){
  if(!depotDrawMode||!IS_ADMIN)return;
  depotPoints.push(e.latlng);
  updateDepotDrawPreview();
  appLog('Bod '+depotPoints.length+' přidán ('+e.latlng.lat.toFixed(5)+','+e.latlng.lng.toFixed(5)+')','info');
});
map.on('dblclick',function(e){
  if(!depotDrawMode||!IS_ADMIN)return;
  L.DomEvent.stop(e);
  depotSaveZone();
});

function depotUndoPoint(){
  if(depotPoints.length===0)return;
  depotPoints.pop();
  updateDepotDrawPreview();
}

async function depotSaveZone(){
  try {
    let name=document.getElementById('depot-name-inp').value.trim();
    let color=document.getElementById('depot-color-inp').value||'#facc15';
    if(!name){alert('Chyba: Zadej název vozovny!');return;}
    if(depotPoints.length<3){
      alert(`Chyba: Polygon musí mít aspoň 3 body!\n\nMusíš nejprve klikat myší do mapy a ohraničit tak areál vozovny. Až naklikáš aspoň 3 body, klikni znovu na Uložit.`);
      return;
    }
    let polygon=depotPoints.map(p=>[p.lat,p.lng]);
    let body={name,polygon,color};
    if(depotEditId)body.id=depotEditId;
    
    let btn=document.querySelector('button[onclick="depotSaveZone()"]');
    if(btn) btn.innerText='Ukládám...';
    
    let r=await fetch('/api/admin/save_depot_zone',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    let text = await r.text();
    let d;
    try {
        d = JSON.parse(text);
    } catch(e) {
        alert(`Kritická chyba serveru: Backend nevrátil JSON data.\nOdpověď: ` + text.substring(0, 150));
        if(btn) btn.innerHTML='💾 Uložit';
        return;
    }
    
    if(d.status==='success'){
      appLog('Vozovna "'+name+'" uložena ✅','ok');
      depotDrawMode=false;depotPoints=[];depotEditId=null;
      if(depotDrawPolyline){depotLayer.removeLayer(depotDrawPolyline);depotDrawPolyline=null;}
      document.getElementById('depot-draw-panel').style.display='none';
      await loadDepotZones();
    }else {
      appLog('Chyba ukládání: '+d.message,'error');
      alert(`Nepodařilo se uložit vozovnu:\n` + d.message);
    }
    if(btn) btn.innerHTML='💾 Uložit';
  } catch(err) {
      alert(`Neočekávaná chyba v prohlížeči:\n` + err.message);
      let btn=document.querySelector('button[onclick="depotSaveZone()"]');
      if(btn) btn.innerHTML='💾 Uložit';
  }
}

function depotCancelDraw(){
  depotDrawMode=false;depotPoints=[];depotEditId=null;
  if(depotDrawPolyline){depotLayer.removeLayer(depotDrawPolyline);depotDrawPolyline=null;}
  document.getElementById('depot-draw-panel').style.display='none';
}

// Admin button pro vozovny - vloží se do admin toolbaru pokud existuje
if(IS_ADMIN){
  // Přidej tlačítko Vozovny do admin nav
  let adminNav=document.getElementById('admin-side-btns');
  if(adminNav){
    let depotBtn=document.createElement('button');
    depotBtn.className='n-btn';depotBtn.style.cssText='background:#78350f;color:#fcd34d;border:1px solid #b45309;';
    depotBtn.innerHTML='🅿️ Vozovny';
    depotBtn.onclick=()=>{
      let p=document.getElementById('depot-admin-panel');
      if(p)p.style.display=p.style.display==='none'?'block':'none';
    };
    adminNav.appendChild(depotBtn);
  }
  // Injektuj admin panel pro vozovny do DOM
  let depotPanel=document.createElement('div');
  depotPanel.id='depot-admin-panel';
  depotPanel.style.cssText='display:none;position:fixed;top:120px;right:10px;width:260px;background:#0f172a;border:1px solid #b45309;border-radius:10px;z-index:2000;box-shadow:0 8px 32px rgba(0,0,0,.7);padding:14px;';
  depotPanel.innerHTML=`
    <div style="color:#facc15;font-weight:bold;font-size:13px;margin-bottom:10px;display:flex;align-items:center;gap:6px;">🏭 Správa Vozoven <button onclick="document.getElementById('depot-admin-panel').style.display='none'" style="margin-left:auto;background:none;border:none;color:#64748b;cursor:pointer;font-size:16px;">✕</button></div>
    <div id="depot-zone-list" style="max-height:180px;overflow-y:auto;margin-bottom:10px;"></div>
    <button onclick="startDepotDraw()" style="width:100%;background:#b45309;color:#fcd34d;border:none;border-radius:6px;padding:9px;font-weight:bold;cursor:pointer;font-size:13px;">➕ Nová vozovna</button>
    <div id="depot-draw-panel" style="display:none;margin-top:10px;border-top:1px solid #1e293b;padding-top:10px;">
      <div style="color:#94a3b8;font-size:11px;margin-bottom:6px;">🖱️ Klikej na mapu pro body, dbl-click = uložit</div>
      <input id="depot-name-inp" type="text" placeholder="Název vozovny..." style="width:100%;box-sizing:border-box;background:#1e293b;color:white;border:1px solid #334155;border-radius:5px;padding:7px;font-size:12px;margin-bottom:6px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <label style="color:#94a3b8;font-size:11px;">Barva:</label>
        <input id="depot-color-inp" type="color" value="#facc15" style="width:40px;height:28px;border:none;cursor:pointer;background:none;">
      </div>
      <div style="display:flex;gap:5px;">
        <button onclick="depotUndoPoint()" style="flex:1;background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:5px;padding:6px;font-size:11px;cursor:pointer;">↩️ Vrátit</button>
        <button onclick="depotSaveZone()" style="flex:2;background:#10b981;color:white;border:none;border-radius:5px;padding:6px;font-weight:bold;font-size:12px;cursor:pointer;">💾 Uložit</button>
        <button onclick="depotCancelDraw()" style="flex:1;background:#7f1d1d;color:#fca5a5;border:none;border-radius:5px;padding:6px;font-size:11px;cursor:pointer;">✕ Zrušit</button>
      </div>
    </div>`;
  document.body.appendChild(depotPanel);
}

// Automaticky načti vozovny při startu
loadDepotZones();
setInterval(loadDepotZones,20000); // refresh kazdych 20 sekund
</script>
"""

# === GLOBALNI STAV ===
GLOBAL_BUS_CACHE    = {}
ADMIN_SPZ_LOCKS     = {}
LIVE_BUSES_DATA     = []
TRACKED_SPZS        = set()
WORKER_START_TIME   = None
ADMIN_DELETED_BUSES = {}
CUSTOM_ROUTES = {}
ROUTE_STOP_OVERRIDES = {}
DEPOT_ZONES = []  # list dict: {id, name, polygon [[lat,lng],...], color}

# === SPZ DEBUG LOG: podrobný rotující buffer pro diagnostiku SPZ matching ===
# Každý záznam: {ts, bus_id, spz, event, detail, gate_3f_cnt, gate_pass_cnt}
_SPZ_DEBUG_LOG = []
_SPZ_DEBUG_LOG_MAX = 500
_arriva_fetch_stats = {"ok": 0, "fail": 0, "empty": 0, "last_fail_reason": None, "last_ok_cnt": 0}

_stop_geo_cache     = {}
_last_spz_auto_refresh = None   # kdy byl naposledy proveden automaticky reset SPZ u vsech busu

# === SPZ MEMORY: Persistentni sledovani SPZ i kdyz bus zmizi z Arrivy ===
# Klic: SPZ (str) -> hodnota: dict s:
#   - last_arriva_lat, last_arriva_lng: posledni zname Arriva pozice
#   - last_arriva_time: kdyz byla pozice z Arriva aktualizovana
#   - last_pvvd_bus_id: ktery PVVD bus_id SPZ nosil naposledy
#   - last_pvvd_time: kdyz byl PVVD bus naposledy viden
#   - line: linka na ktere SPZ byla
#   - destination: cil
#   - trip_id: trip_id vozu (pro spojitost pri zmene linky)
#   - verified: mel 3-faktor match
#   - frozen: SPZ je "zamrazena" (bus v depu/na konecne)
SPZ_MEMORY = {}  # spz -> dict
SPZ_MEMORY_MAX_AGE_HOURS = 24  # jak dlouho pamatovat SPZ bez aktualizace

# ── GTFS zastavky v pameti ───────────────────────────────────────────────────
GTFS_LOADED    = False
GTFS_STOPS     = []          # list of (name, lat, lon)
GTFS_NAME_IDX  = {}          # norm_name -> [indexy]
GTFS_GRID      = {}          # (lat_bucket, lon_bucket) -> [indexy]
GTFS_GRID_SZ   = 0.01        # ~1.1km dlazdice
GTFS_STOP_CNT  = 0
GTFS_TOKENS    = []           # parallel list k GTFS_STOPS: frozenset slov v nazvu
GTFS_TOKEN_IDX = {}           # slovo -> [indexy do GTFS_STOPS] (invertovany index pro rychly fuzzy hledani)
GTFS_MODES     = []           # parallel list k GTFS_STOPS: 'bus'/'train'/'mixed'/None
GTFS_LINES     = []           # parallel list k GTFS_STOPS: list of route short names (napr. ['490','496']) or []

# ── Rezim "Nastaveni tras" (NT) - rucni opravy poloh zastavek ────────────────
# STOP_OVERRIDES ma VZDY prednost pred GTFS - kdyz admin v NT rezimu rucne
# presune bod a ulozi, system uz tu zastavku nikdy znovu nehleda v GTFS/
# Nominatim, jen pouzije ulozenou polohu. Persistuje se do Supabase tabulky
# 'stop_overrides', aby to preziv restart workeru.
STOP_OVERRIDES = {}           # norm_name -> {"lat":, "lng":, "name": puvodni zobrazovany nazev}
# CONFIDENCE_LOG si pamatuje, s jakou jistotou se naposled kazda zastavka
# nasla (exact/fuzzy/geocoded/none/manual) - pri pruchodu trasy v
# api_bus_route. NT rezim podle toho zvyrazni "podezrele" body, at je admin
# vidi rovnou, bez nutnosti proklikavat kazdou trasu zvlast.
CONFIDENCE_LOG = {}           # norm_name -> {"confidence":, "name":}

cj     = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_prague_time():
    try:
        return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)
    except Exception:
        return datetime.now()

def get_internet_prague_time():
    """Ziska presny cas z internetu, fallback na lokalni po 2s timeoutu."""
    try:
        import urllib.request
        import json
        req = urllib.request.Request("http://worldtimeapi.org/api/timezone/Europe/Prague", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2.0) as response:
            data = json.loads(response.read().decode('utf-8'))
            if "datetime" in data:
                return data["datetime"]
    except Exception as e:
        print(f"[TIME API ERROR] Nelze ziskat cas z internetu: {e}")
    return datetime.now(ZoneInfo('Europe/Prague')).isoformat()


def is_same_line(l1, l2):
    if not l1 or not l2 or l1 == "Nezn\u00e1m\u00e1" or l2 == "Nezn\u00e1m\u00e1":
        return False
    b1 = str(l1).split('/')[0]
    b2 = str(l2).split('/')[0]
    cl1 = re.sub(r'\D', '', b1)
    cl2 = re.sub(r'\D', '', b2)
    if not cl1 or not cl2:
        return b1 == b2
    return cl1.endswith(cl2) or cl2.endswith(cl1)


def _arriva_line_matches(local_line, b):
    """Porovna linku z PVVD s linkNumberAlias i linkNumber z Arrivy."""
    if is_same_line(local_line, b.get("linkNumber")):
        return True
    alias = b.get("linkNumberAlias")
    if alias and is_same_line(local_line, str(alias)):
        return True
    return False


def haversine_m(lat1, lon1, lat2, lon2):
    """Vzdalenost mezi dvema GPS body v metrech."""
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return float("inf")
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


# Bezne ceske zkratky pouzivane v nazvech zastavek (PVVD casto zkracuje, GTFS
# obvykle ne) - rozepsano PRED odstranenim teckovani/mezer, aby \b funguje
# spravne a aby se napr. "aut. st." a "zel. st." nepletly (obe obsahuji "st.",
# ale kazda znamena neco jineho - autobusove stanoviste vs zeleznicni stanice).
_ABBREV_PATTERNS = [
    (re.compile(r'\bzel\.?\s*st\.?\b'), 'zeleznicni stanice'),
    (re.compile(r'\bzel\.?\s*zast\.?\b'), 'zeleznicni zastavka'),
    (re.compile(r'\baut\.?\s*st\.?\b'), 'autobusove stanoviste'),
    (re.compile(r'\bnadr\.?\b'), 'nadrazi'),
    (re.compile(r'\bnam\.?\b'), 'namesti'),
    (re.compile(r'\bzast\.?\b'), 'zastavka'),
    (re.compile(r'\brozc\.?\b'), 'rozcesti'),
    (re.compile(r'\bkriz\.?\b'), 'krizovatka'),
    (re.compile(r'\bul\.?\b'), 'ulice'),
]


def _pre_normalize(s):
    """Lowercase + odstraneni diakritiky + rozepsani znamych zkratek.
    Mezery/teckovani se NEodstranuji - to az nasledne v _norm_txt/_tokenize."""
    if not s:
        return ""
    s = str(s).lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    for pattern, repl in _ABBREV_PATTERNS:
        s = pattern.sub(repl, s)
    return s


def _norm_txt(s):
    """Normalizace textu pro porovnani (diakritika, zkratky, mezery, velikost pismen)."""
    if not s:
        return ""
    return re.sub(r'[^a-z0-9]+', '', _pre_normalize(s))


def _tokenize(s):
    """Rozdeli nazev na normalizovana 'slova' (bez diakritiky, zkratky rozepsany,
    min. 3 znaky). Pouziva se pro presnejsi fuzzy parovani nazvu zastavek - misto
    naivniho 'je jeden retezec podretezcem druheho' se pocita prekryv SLOV. Diky
    tomu se napr. 'Bor, Nova Hospoda' uz neplete s 'Novy Bor, Janov, restaurace'
    jen kvuli nahodne spolecnemu slovu, a 'aut. st.' se spravne rozepise na
    'autobusove stanoviste' misto kolize se 'zel. st.' (zelezni stanice)."""
    if not s:
        return frozenset()
    raw = re.split(r'[^a-z0-9]+', _pre_normalize(s))
    return frozenset(t for t in raw if len(t) >= 3)


def _gtfs_grid_key(lat, lon):
    return (round(lat / GTFS_GRID_SZ), round(lon / GTFS_GRID_SZ))


_TRAIN_HINT_WORDS = ('zeleznicni', 'zeleznice', 'nadrazi', 'vlak', 'vlakova')


def _name_suggests_train(name):
    """Naznacuje nazev zastavky, ze jde o VLAKOVOU stanici/zastavku (ne
    autobusovou)? Vyuziva uz rozepsane zkratky (zel.st. -> zeleznicni
    stanice) z _pre_normalize, takze chytne zkratkovou i plnou variantu."""
    if not name:
        return False
    return any(w in _pre_normalize(name) for w in _TRAIN_HINT_WORDS)


def _load_gtfs():
    """Nacte gtfs_stops.db do pameti. Vola se jednou pri startu workeru."""
    global GTFS_LOADED, GTFS_STOPS, GTFS_NAME_IDX, GTFS_GRID, GTFS_STOP_CNT
    global GTFS_TOKENS, GTFS_TOKEN_IDX, GTFS_MODES, GTFS_LINES
    if not os.path.exists(GTFS_DB_PATH):
        print(f"[GTFS] Soubor nenalezen: {GTFS_DB_PATH}", flush=True)
        return False
    try:
        conn = sqlite3.connect(GTFS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(stops)")
        cols = [r[1] for r in cur.fetchall()]
        def pick(cands):
            for c in cands:
                if c in cols: return c
            return None
        nc  = pick(["stop_name","name"])
        lac = pick(["stop_lat","lat","latitude"])
        loc = pick(["stop_lon","stop_lng","lon","lng","longitude"])
        mc  = pick(["mode"])    # volitelny - 'bus'/'train'/'mixed'/NULL
        lc  = pick(["lines"])   # volitelny - JSON pole nazvu linek napr. '["490","733"]'
        if not (nc and lac and loc):
            raise RuntimeError(f"Nerozpoznane schema: {cols}")
        extras = (f", {mc} AS md" if mc else "") + (f", {lc} AS ln" if lc else "")
        cur.execute(f"SELECT {nc} AS n, {lac} AS la, {loc} AS lo{extras} FROM stops")
        stops, name_idx, grid, modes, lines_list = [], {}, {}, [], []
        tokens_list, token_idx = [], {}
        for row in cur.fetchall():
            name = (row["n"] or "").strip()
            try:
                la, lo = float(row["la"]), float(row["lo"])
            except (TypeError, ValueError):
                continue
            if not name or (la == 0 and lo == 0):
                continue
            idx = len(stops)
            stops.append((name, la, lo))
            modes.append(row["md"] if mc else None)
            raw_lines = row["ln"] if lc else None
            try:
                lines_list.append(json.loads(raw_lines) if raw_lines else [])
            except Exception:
                lines_list.append([])
            nk = _norm_txt(name)
            name_idx.setdefault(nk, []).append(idx)
            grid.setdefault(_gtfs_grid_key(la, lo), []).append(idx)
            tk = _tokenize(name)
            tokens_list.append(tk)
            for t in tk:
                token_idx.setdefault(t, []).append(idx)
        conn.close()
        GTFS_STOPS, GTFS_NAME_IDX, GTFS_GRID = stops, name_idx, grid
        GTFS_TOKENS, GTFS_TOKEN_IDX = tokens_list, token_idx
        GTFS_MODES = modes
        GTFS_LINES = lines_list
        GTFS_STOP_CNT = len(stops)
        GTFS_LOADED = True
        has_modes = mc is not None
        print(f"[GTFS] Nacteno {len(stops)} zastavek z {GTFS_DB_PATH} (mode info: {'ano' if has_modes else 'ne - stary format DB'})", flush=True)
        return True
    except Exception as e:
        print(f"[GTFS] Chyba nacitani: {e}", flush=True)
        return False


def _load_stop_overrides(db):
    """Nacte rucni opravy poloh zastavek (NT rezim) ze Supabase do pameti."""
    global STOP_OVERRIDES
    if not db:
        return
    try:
        res = db.table("stop_overrides").select("*").execute()
        loaded = {}
        for row in (res.data or []):
            nm = row.get("stop_name")
            if not nm:
                continue
            try:
                cl = json.loads(row["custom_lines"]) if row.get("custom_lines") else None
            except Exception:
                cl = None
            
            mode = row.get("mode") or "bus"
            loaded[f"{_norm_txt(nm)}|{mode}"] = {
                "lat": row["lat"], "lng": row["lng"], "name": nm,
                "approx": bool(row.get("approx", False)),
                "substitute": bool(row.get("substitute", False)),
                "display_name": row.get("display_name") or "",
                "custom_lines": cl,   # None = pouzij GTFS, list = pouzij toto
                "mode": row.get("mode") or "bus",
            }
        STOP_OVERRIDES = loaded
        print(f"[NT] Nacteno {len(loaded)} rucnich oprav poloh zastavek.", flush=True)
    except Exception as e:
        print(f"[NT] Tabulka stop_overrides nedostupna (OK pokud NT jeste nebyl pouzit): {e}", flush=True)

def _load_depot_zones(db):
    """Nacte vozovny (depot zones) ze Supabase do pameti."""
    global DEPOT_ZONES
    if not db:
        return
    try:
        res = db.table("depot_zones").select("*").execute()
        loaded = []
        for row in (res.data or []):
            poly = row.get("polygon")
            if not poly or len(poly) < 3:
                continue
            loaded.append({
                "id": row.get("id"),
                "name": row.get("name", "Vozovna"),
                "polygon": poly,
                "color": row.get("color") or "#facc15",
            })
        DEPOT_ZONES.clear()
        DEPOT_ZONES.extend(loaded)
        print(f"[DEPOT] Nacteno {len(loaded)} vozoven.", flush=True)
    except Exception as e:
        print(f"[DEPOT] Tabulka depot_zones nedostupna: {e}", flush=True)

def _load_depot_active_sessions(db):
    global DEPOT_ACTIVE_SESSIONS
    if not db:
        return
    try:
        res = db.table("depot_history").select("*").is_("left_at", "null").execute()
        loaded = {}
        for row in (res.data or []):
            bid = row.get("bus_id") or f"unknown_{row['id']}"
            loaded[bid] = {
                "id": row["id"],
                "depot_name": row["depot_name"],
                "arrived_at": row["arrived_at"],
                "is_imprecise": row.get("is_imprecise", False),
                "spz": row.get("spz")
            }
        DEPOT_ACTIVE_SESSIONS = loaded
        print(f"[DEPOT] Nacteno {len(loaded)} aktivnich navstev ve vozovnach.", flush=True)
    except Exception as e:
        print(f"[DEPOT] Tabulka depot_history nedostupna: {e}", flush=True)

def _point_in_polygon(lat, lng, polygon):
    """Ray-casting algoritmus: je bod (lat, lng) uvnitr polygonu?
    polygon = [[lat, lng], [lat, lng], ...]"""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][1], polygon[i][0]  # lng, lat
        xj, yj = polygon[j][1], polygon[j][0]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _check_depot_zones(lat, lng):
    """Zkontroluj zda je bod (lat, lng) uvnitr nektere vozovny.
    Vraci tuple (nazev, barva) nebo (None, None)."""
    for zone in DEPOT_ZONES:
        if _point_in_polygon(lat, lng, zone["polygon"]):
            return zone["name"], zone.get("color", "#facc15")
    return None, None


def _bearing_diff(b1, b2):
    """Kruhovy rozdil dvou smerovych uhlu (0-360 deg). Vzdy vrati 0-180."""
    if b1 is None or b2 is None:
        return 0
    diff = abs(int(b1) - int(b2)) % 360
    return min(diff, 360 - diff)


def _load_route_stop_overrides(db):
    global ROUTE_STOP_OVERRIDES
    if not db:
        return
    try:
        res = db.table("route_stop_overrides").select("*").execute()
        loaded = {}
        for row in (res.data or []):
            loaded[row["segment_key"]] = {"lat": row["lat"], "lng": row["lng"]}
        ROUTE_STOP_OVERRIDES = loaded
        print(f"[NT] Nacteno {len(loaded)} smerovych oprav poloh zastavek.", flush=True)
    except Exception as e:
        print(f"[NT] Tabulka route_stop_overrides nedostupna: {e}", flush=True)

def _load_custom_routes(db):
    global CUSTOM_ROUTES
    if not db:
        return
    try:
        res = db.table("custom_routes").select("*").execute()
        loaded = {}
        for row in (res.data or []):
            try:
                loaded[row["route_key"]] = json.loads(row["points"]) if isinstance(row["points"], str) else row["points"]
            except Exception:
                pass
        CUSTOM_ROUTES = loaded
        print(f"[NT] Nacteno {len(loaded)} vlastnich tvaru silnic.", flush=True)
    except Exception as e:
        print(f"[NT] Tabulka custom_routes nedostupna: {e}", flush=True)


def _nearest_stop_name(lat, lon, max_m=400):
    """Nejblizsi GTFS zastavka k dane pozici (pro krizovou kontrolu lastStopName z Arrivy)."""
    if not GTFS_STOPS:
        return None
    bk = _gtfs_grid_key(lat, lon)
    candidates = []
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            candidates.extend(GTFS_GRID.get((bk[0]+dlat, bk[1]+dlon), []))
    best_name, best_d = None, None
    for idx in candidates:
        name, la, lo = GTFS_STOPS[idx]
        d = haversine_m(lat, lon, la, lo)
        if best_d is None or d < best_d:
            best_d, best_name = d, name
    return best_name if (best_d is not None and best_d <= max_m) else None


def _lookup_stop_coords(name, anchor=None, max_anchor_dist_m=60000, bus_mode=None):
    """GPS souradnice zastavky podle nazvu z GTFS. Vraci (coords, confidence)
    kde confidence je "exact" / "fuzzy" / None (kdyz se nic nenajde).

    DULEZITE: stejny nazev zastavky ('Nova Ves', 'Chrastany', ...) existuje
    v GTFS databazi desitky-kratkrat napric celou CR (databaze pokryva
    cely bounding box, ne jen Plzensky kraj). Bez geograficke kotvy by se
    vzdy vybrala jen prvni shoda v databazi - prakticky nahodne mesto.

    `anchor` = (lat, lon) referencni bod (napr. aktualni poloha busu nebo
    posledni uz vyresena zastavka na trase) - z VSECH kandidatu se stejnym
    nazvem se vybere ten geograficky nejblizsi anchoru. Pokud i ten
    nejblizsi kandidat je dal nez `max_anchor_dist_m`, povazuje se shoda za
    nedukazpodobnou a vrati se None (radsi chybejici tecka nez spatne
    umistena).

    Fuzzy fallback (kdyz presny nazev nesedi) NEPOUZIVA naivni "jeden retezec
    je podretezcem druheho" - to umelo plest napr. 'Bor, Nova Hospoda' s
    uplne jinou zastavkou 'Novy Bor, Janov, restaurace' jen kvuli nahodne
    spolecnemu slovu. Misto toho se pocita PREKRYV SLOV (min. 70 % kratsiho
    nazvu) pres rychly invertovany index (jen kandidati sdileji aspon jedno
    slovo - ne sken vsech 67k zastavek).

    MODE-AWARENESS (vlak vs bus): nektera mista maji vlakovou stanici A
    autobusovou zastavku se STEJNYM nazvem (napr. "Trpisty" - vlakova
    stanice 1.3 km od "Trpisty" - autobusove zastavky uprostred vesnice).
    Tahle appka sleduje BUS linky, takze pokud hledany nazev sam neznaci
    vlak (zel./nadrazi/vlak), preferuji se kandidati oznaceni jako 'bus'
    pred 'train'. Pokud presna/fuzzy shoda vyjde JEN na vlakovou variantu,
    zkusi se jeste "zachranny" krok - hledani blizke (do 3 km) autobusove
    zastavky s aspon castecne podobnym nazvem, presne pro pripad jako
    Trpisty.
    """
    if not GTFS_STOPS and not STOP_OVERRIDES:
        return None, None
    key = _norm_txt(name)
    if not key:
        return None, None

    target_mode = bus_mode
    if not target_mode:
        wants_train = _name_suggests_train(name)
        target_mode = 'train' if wants_train else 'bus'
    # Pokud nazev obsahuje hint na vlak, vzdy preferuj train rezim
    elif bus_mode == 'bus' and _name_suggests_train(name):
        target_mode = 'train'

    # 0) Rucni oprava z NT rezimu ma VZDY prednost - admin uz to jednou
    # rucne overil a ulozil, takze se uz znovu nehleda v GTFS/Nominatim.
    ov = STOP_OVERRIDES.get(f"{key}|{target_mode}")
    if not ov:
        ov = STOP_OVERRIDES.get(f"{key}|mixed")

    if ov:
        return (ov["lat"], ov["lng"]), "manual"

    if not GTFS_STOPS:
        return None, None

    def mode_ok(idx):
        m = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
        return (not m) or (m == 'mixed') or (m == target_mode)

    def pick_best(idxs, strict_mode=True):
        """Vybere nejlepsiho kandidata z idxs.
        strict_mode=True: pokud existuje spravny rezim, NIKDY nepouzij spatny
        (toto zabraňuje prirazeni vlakove stanice k bus zastavce se stejnym nazvem).
        strict_mode=False: povoluje fallback na spatny rezim kdyz spravny neni.
        """
        if not idxs:
            return None
        preferred = [i for i in idxs if mode_ok(i)]
        # KLIC: pokud existuje aspon jeden kandidat spravneho rezimu,
        # IGNORUJ vsechny ostatniho rezimu - nepovoluj fallback na spatny typ.
        # Toto je hlavni oprava: 'Svojšín' (bus) uz nebude pouzit vlakova stanice
        # jen proto, ze je v GTFS jako jedina/prvni shoda.
        if preferred:
            pool = preferred
        elif strict_mode:
            # Spravny rezim vubec neni k dispozici - radsi None nez spatny typ
            return None
        else:
            pool = idxs
        if not anchor:
            # Bez anchoru: vrat prvni preferovany (nelze geograficky vybrat)
            _, la, lo = GTFS_STOPS[pool[0]]
            return (la, lo)
        if len(pool) == 1:
            _, la, lo = GTFS_STOPS[pool[0]]
            d = haversine_m(anchor[0], anchor[1], la, lo)
            if d > max_anchor_dist_m:
                return None
            return (la, lo)
        best_coords, best_d = None, None
        for idx in pool:
            _, la, lo = GTFS_STOPS[idx]
            d = haversine_m(anchor[0], anchor[1], la, lo)
            if best_d is None or d < best_d:
                best_d, best_coords = d, (la, lo)
        if best_d is not None and best_d > max_anchor_dist_m:
            return None
        return best_coords

    def idxs_have_mode_ok(idxs):
        return any(mode_ok(i) for i in idxs)

    # 1) Presna shoda normalizovaneho nazvu
    exact_idxs = GTFS_NAME_IDX.get(key, [])
    if exact_idxs:
        if idxs_have_mode_ok(exact_idxs):
            result = pick_best(exact_idxs, strict_mode=True)
            if result:
                return result, "exact"
        # Mame presnou shodu, ale pouze spatneho rezimu - zkus pridat fuzzy
        # kandidaty spravneho rezimu z okoli pred definitivnim vzdanim se
        # (zpracuje se nize v kroku 3)

    # 2) Fuzzy: Jaccard prekryv slov (prunik/sjednoceni, ne jen prunik/min)
    # >= 70 %, hledano jen mezi kandidaty z invertovaneho indexu (sdileji
    # aspon jedno slovo - ne sken vsech 67k zastavek).
    #
    # DULEZITE proc zrovna Jaccard a ne "prunik / kratsi z obou": kdyby se
    # delilo jen kratsi mnozinou, kratsi nazev jako "Kladruby, Vrbice" by
    # VZDY vysel jako 100% shoda s delsim "Kladruby, Vrbice, rozcesti" -
    # i kdyz jde o dve ruzna, nekolik km vzdalena mista. Jaccard navic
    # penalizuje chybejici/navic slovo (delitel je SJEDNOCENI, ne min),
    # takze "...rozcesti" uz nevyjde stejne jako bez nej.
    search_tokens = _tokenize(name)
    candidate_idxs = set()
    fuzzy_matches = []
    if search_tokens and GTFS_TOKEN_IDX:
        for tok in search_tokens:
            candidate_idxs.update(GTFS_TOKEN_IDX.get(tok, ()))
        best_score = 0.0
        for idx in candidate_idxs:
            cand_tokens = GTFS_TOKENS[idx]
            if not cand_tokens:
                continue
            score = len(search_tokens & cand_tokens) / len(search_tokens | cand_tokens)
            if score < 0.7:
                continue
            if score > best_score:
                best_score, fuzzy_matches = score, [idx]
            elif score == best_score:
                fuzzy_matches.append(idx)
        if fuzzy_matches and idxs_have_mode_ok(fuzzy_matches):
            result = pick_best(fuzzy_matches, strict_mode=True)
            if result:
                return result, "fuzzy"

    # 3) "Zachranny" krok: presna/fuzzy shoda existuje, ale JEN spatneho
    # rezimu (typicky: hledas bus zastavku, ale jedine co se naslo pod
    # timhle jmenem je vlakova stanice). Zkus jeste volnejsi shodu (Jaccard
    # >= 0.4) MEZI KANDIDATY CO MAJI ASPON JEDNO SPOLECNE SLOVO, ale jen
    # pokud jsou opravdu blizko (do 3 km) te spatne-rezimove shody - tim se
    # najde napr. "Trpisty, Hospoda"/"Trpisty, rozcesti" (bus) co lezi
    # kousek od vlakove stanice "Trpisty", i kdyz se presne nazvy neshoduji.
    fallback_idxs = exact_idxs or fuzzy_matches
    if fallback_idxs and not idxs_have_mode_ok(fallback_idxs):
        # Pouzij prvni kandidat spatneho rezimu jako geografickou kotvu pro
        # hledani blizke bus zastavky (spatny-rezimova kotva)
        _, la0, lo0 = GTFS_STOPS[fallback_idxs[0]]
        rescue_anchor = (la0, lo0)
        if search_tokens and candidate_idxs:
            rescue = []
            best_rescue_score = 0.0
            for idx in candidate_idxs:
                if not mode_ok(idx):
                    continue
                cand_tokens = GTFS_TOKENS[idx]
                if not cand_tokens:
                    continue
                score = len(search_tokens & cand_tokens) / len(search_tokens | cand_tokens)
                if score < 0.4:
                    continue
                _, la, lo = GTFS_STOPS[idx]
                if haversine_m(rescue_anchor[0], rescue_anchor[1], la, lo) > 3000:
                    continue
                if score > best_rescue_score:
                    best_rescue_score, rescue = score, [idx]
                elif score == best_rescue_score:
                    rescue.append(idx)
            if rescue:
                result = pick_best(rescue, strict_mode=True)
                if result:
                    return result, "fuzzy"
        # Zachranny krok nic nenasel.
        # DULEZITE: pokud hledame bus a nasli jsme POUZE vlak - vrat None!
        # Je lepsi mit chybejici tecku v trase (cervene ?, NT log) nez
        # spatne umistit autobus na vlakove nadrazi.
        # VYJIMKA: pokud neni zadny anchor (zacatek trasy), radsi akceptuj
        # spatny rezim nez nic - admin to muze opravit v NT.
        if anchor is None:
            if exact_idxs:
                result = pick_best(exact_idxs, strict_mode=False)
                if result:
                    return result, "exact"
            if fuzzy_matches:
                result = pick_best(fuzzy_matches, strict_mode=False)
                if result:
                    return result, "fuzzy"
        # S anchorem: radsi None nez spatny rezim
        return None, None

    return None, None


def get_db_client():
    if not HAS_SUPABASE:
        return None
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None


def new_cache_entry(bus_id, trip_id, lat, lng, line, dest, is_train, delay, now,
                     ghost_spz=None, ghost_verified=False, admin_verified=False):
    return {
        "trip_id": trip_id, "inflow_id": bus_id, "lat": lat, "lng": lng, "bearing": None,
        "line": line, "real_linka_spoj": None, "destination": dest, "is_train": is_train,
        "raw_delay": delay, "spz": ghost_spz, "spz_verified": ghost_verified,
        "spz_locked": False, "manual_spz": False, "spz_stable_ticks": 0,
        "spz_last_verified": None, "investigating": False, "investigation_spz": None,
        "investigation_start": None, "first_seen": now, "last_inflow_seen": now,
        "last_moved": now, "created_at": now, "actual_start_time": None,
        "actual_end_time": None, "first_dep_time": None, "last_dep_time": None,
        "tt_last_fetch": None, "tt_is_fetching": False,
        "status": "Načítání...", "color_class": "bg-gray", "is_offline": False,
        "db_first_upsert": False, "_last_db_status": None, "_last_db_linka": None,
        "_end_written": False, "_was_long_stationary": False, "final_delay_display": 0,
        "admin_color_override": None, "admin_status_override": None, "admin_flag": False,
        "bug_locked": False, "admin_lock_display": False, "admin_lock_permanent": False,
        "admin_note": "",
        # admin_spz_verified: absolutni admin lock - automatikaprestane hledat jinou SPZ.
        # Nastavuje se tlacitkem 'Overit SPZ adminem' v Admin Panelu.
        "admin_spz_verified": admin_verified,
        # _first_move_time: kdy se bus poprve fyzicky pohnul (pro SPZ_MIN_MOVE_MINUTES).
        # SPZ se nezacne hledat dokud bus nejede alespon SPZ_MIN_MOVE_MINUTES minut.
        "_first_move_time": None,
        # spz_frozen: tvrdy zamek SPZ kdyz bus dojede na konecnou / do depa -
        # narozdil od beznych spz_locked/spz_verified (ktere se behem jizdy
        # porad prubezne re-auditujeji kvuli samoopravnosti) tohle uz system
        # vubec nezkousi menit, dokud nezacne genuinly novy spoj (zmena linky).
        "spz_frozen": False,
        # spz_last_audit_check: kdy byla naposledy provedena re-audit kontrola
        # jiz zamknute/overene SPZ - u overenych (fajfka) se kontroluje jen
        # obcas (nizsi priorita), ne kazdy tik jako u jeste neovere
        "spz_last_audit_check": None,
    }


def fetch_tt_bg(bus_id, cached_dict):
    try:
        cb = int(time.time() * 1000)
        hdr = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest',
               'Referer': 'https://pvvd.idpk.cz/', 'Cache-Control': 'no-cache'}
        with opener.open(urllib.request.Request(
                f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb}", headers=hdr), timeout=4) as r:
            ih = r.read().decode('utf-8')
        ml = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', ih, re.IGNORECASE | re.DOTALL)
        ms = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', ih, re.IGNORECASE | re.DOTALL)
        if ml and ms:
            cached_dict["real_linka_spoj"] = f"{ml.group(1).strip()}/{ms.group(1).strip()}"
        with opener.open(urllib.request.Request(
                f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}",
                headers=hdr), timeout=4) as r:
            tt = r.read().decode('utf-8')
        times = re.findall(r'\b\d{2}:\d{2}\b', tt)
        if times:
            cached_dict["first_dep_time"] = times[0]
            cached_dict["last_dep_time"] = times[-1]
    except Exception:
        pass
    finally:
        cached_dict["tt_is_fetching"] = False


def close_previous_trips(db, spz, current_trip_id, end_time_str):
    if not db or not spz or spz == "Neznámá":
        return
    try:
        resp = db.table("bus_history").select("trip_id").eq("spz", spz) \
                 .is_("end_actual", None).neq("trip_id", current_trip_id).execute()
        for row in (resp.data or []):
            try:
                db.table("bus_history").update({
                    "end_actual": end_time_str,
                    "status": "Ukončeno (Nový spoj zahájen)",
                    "updated_at": get_prague_time().isoformat(),
                }).eq("trip_id", row["trip_id"]).execute()
            except Exception:
                pass
    except Exception:
        pass


def _is_tracked_line(linka_str):
    num = re.sub(r'\D', '', re.sub(r'/.*', '', str(linka_str)).strip())
    return num.startswith("490") or num.startswith("496")


def upsert_to_history(db, c):
    global TRACKED_SPZS
    if c.get("is_train") or not db:
        return
    spz = c.get("spz")
    if not spz or spz == "Neznámá":
        return
    final_linka = c.get("real_linka_spoj") or c.get("line", "")
    if not _is_tracked_line(final_linka):
        return
    if not c.get("actual_start_time") and not c.get("actual_end_time"):
        return
    TRACKED_SPZS.add(spz)
    jr_l = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={c['inflow_id']}&currentStopId=0"
    payload_full = {
        "trip_id": c["trip_id"], "spz": spz, "spz_verified": c.get("spz_verified", False),
        "spz_3factor": c.get("spz_3factor", False), "spz_conflict_warn": c.get("spz_conflict_warn", False),
        "linka": final_linka, "jr_link": jr_l, "start_scheduled": c.get("first_dep_time"),
        "start_actual": c.get("actual_start_time"), "end_actual": c.get("actual_end_time"),
        "last_lat": c.get("lat"), "last_lng": c.get("lng"), "status": c.get("status"),
        "created_at": c["created_at"].isoformat(), "updated_at": get_prague_time().isoformat(),
    }
    try:
        db.table("bus_history").upsert(payload_full).execute()
    except Exception as e:
        err_str = str(e)
        # Graceful fallback: pokud DB nema sloupec spz_3factor nebo spz_conflict_warn
        # (PGRST204 = neznamy sloupec v schema cache), zkus bez tech sloupcu
        if "PGRST204" in err_str or "spz_3factor" in err_str or "spz_conflict_warn" in err_str:
            payload_fallback = {k: v for k, v in payload_full.items()
                                if k not in ("spz_3factor", "spz_conflict_warn")}
            try:
                db.table("bus_history").upsert(payload_fallback).execute()
                # Jen jednou za cas upozornit ze fallback je aktivni
                print(f"[MAPA-DB WARN] {spz}: spz_3factor/spz_conflict_warn sloupec chybi v DB "
                      f"- pridat SQL: ALTER TABLE bus_history ADD COLUMN spz_3factor BOOLEAN DEFAULT FALSE; "
                      f"ADD COLUMN spz_conflict_warn BOOLEAN DEFAULT FALSE;", flush=True)
            except Exception as e2:
                print(f"[MAPA-DB CHYBA] {spz}: {e2}", flush=True)
        else:
            print(f"[MAPA-DB CHYBA] {spz}: {e}", flush=True)


def background_map_worker():
    global TRACKED_SPZS, WORKER_START_TIME
    print("[MAPA] Worker startuje...", flush=True)
    WORKER_START_TIME = get_prague_time()

    # Nacti GTFS zastavky do pameti (soubor je soucasti repa, neni potreba stahovat)
    _load_gtfs()

    db_client = get_db_client()
    if db_client:
        try:
            res = db_client.table("bus_history").select("spz").execute()
            for r in res.data:
                if r.get("spz") and r["spz"] != "Nezn\u00e1m\u00e1":
                    TRACKED_SPZS.add(r["spz"])
            print(f"[MAPA] Na\u010dteno {len(TRACKED_SPZS)} sledovan\u00fdch SPZ.")
        except Exception:
            pass
        _load_stop_overrides(db_client)
        _load_route_stop_overrides(db_client)
        _load_custom_routes(db_client)
        _load_depot_zones(db_client)
        _load_depot_active_sessions(db_client)

        # === SPZ CACHE RESTORE: Obnov SPZ z predchoziho behu (zachrani data po restartu/deployi) ===
        try:
            _now_restore = get_prague_time()
            cache_res = db_client.table("spz_cache").select("*").execute()
            restored = 0
            for row in (cache_res.data or []):
                bid = row.get("bus_id")
                spz = row.get("spz")
                
                # Uloz admin verified do pameti natrvalo
                if row.get("admin_verified") and bid and spz:
                    ADMIN_SPZ_LOCKS[bid] = {
                        "spz": spz,
                        "admin_note": row.get("admin_note", ""),
                        "color_class": row.get("color_class", "bg-darkblue")
                    }
                    
                if not bid or not spz or spz == "Nezn\u00e1m\u00e1":
                    continue
                if bid in GLOBAL_BUS_CACHE:
                    continue  # bus uz je zivý, cache ho neprepis
                # Vytvor ghost zaznam s SPZ z predchoziho behu
                ghost_entry = new_cache_entry(
                    bid, row.get("trip_id") or f"RESTORED-{bid}",
                    row.get("lat") or 0, row.get("lng") or 0,
                    row.get("linka") or "", "", False, 0, _now_restore,
                    ghost_spz=spz, ghost_verified=row.get("spz_verified", False),
                    admin_verified=row.get("admin_verified", False)
                )
                ghost_entry["is_offline"] = True
                ghost_entry["color_class"] = row.get("color_class") or "bg-gray"
                ghost_entry["status"] = row.get("status_text") or "Obnoven po restartu"
                ghost_entry["admin_note"] = row.get("admin_note") or ""
                ghost_entry["admin_flag"] = row.get("admin_flag", False)
                if row.get("manual_spz"):
                    ghost_entry["manual_spz"] = True
                ghost_entry["spz_frozen"] = True  # zamkni - je z cache, nechceme okamzite prepsat
                ghost_entry["_is_restored"] = True
                ghost_entry["spz_locked"] = True
                if ghost_entry["admin_spz_verified"]:
                    ghost_entry["manual_spz"] = True
                GLOBAL_BUS_CACHE[bid] = ghost_entry
                SPZ_MEMORY[spz] = {
                    "last_arriva_lat": row.get("lat") or 0,
                    "last_arriva_lng": row.get("lng") or 0,
                    "last_arriva_time": _now_restore,
                    "line": row.get("linka") or "",
                    "destination": "",
                    "verified": row.get("spz_verified", False),
                }
                restored += 1
            print(f"[SPZ CACHE] Obnoveno {restored} zaznamu z predchoziho behu.", flush=True)
        except Exception as e_cache:
            print(f"[SPZ CACHE] Chyba pri obnove: {e_cache}", flush=True)

    url_inflow_base = "https://pvvd.idpk.cz/Ajax/GetPoints"
    url_arriva = "https://www.arriva.cz/api/graphql"
    inflow_headers = {
        'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://pvvd.idpk.cz/',
        'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
    }
    try:
        opener.open(urllib.request.Request("https://pvvd.idpk.cz/", headers={'User-Agent': 'Mozilla/5.0'}))
    except Exception:
        pass

    last_db_cleanup = get_prague_time()
    last_spz_memory_cleanup = get_prague_time()
    last_spz_cache_flush = get_prague_time()
    TRIP_COUNTER = int(time.time())

    while True:
        try:
            now = get_prague_time()
            if db_client and (now - last_db_cleanup).total_seconds() > 86400:
                last_db_cleanup = now

            # === SPZ MEMORY CLEANUP: smaz stare zaznamy (max 24h) ===
            if (now - last_spz_memory_cleanup).total_seconds() > 3600:
                last_spz_memory_cleanup = now
                max_age = SPZ_MEMORY_MAX_AGE_HOURS * 3600
                to_delete = []
                for spz, mem in SPZ_MEMORY.items():
                    last_time = mem.get("last_arriva_time") or mem.get("last_pvvd_time") or now
                    if (now - last_time).total_seconds() > max_age:
                        to_delete.append(spz)
                for spz in to_delete:
                    del SPZ_MEMORY[spz]
                if to_delete:
                    print(f"[SPZ MEMORY] Vymazano {len(to_delete)} starych zaznamu", flush=True)

            data_inflow, data_arriva = [], []
            url_inflow = f"{url_inflow_base}?_={int(time.time() * 1000)}"
            try:
                with urllib.request.urlopen(urllib.request.Request(url_inflow, headers=inflow_headers), timeout=5) as r:
                    data_inflow = json.loads(r.read().decode())
            except Exception:
                try:
                    req1p = urllib.request.Request(url_inflow, data=b"{}", headers=inflow_headers, method='POST')
                    with urllib.request.urlopen(req1p, timeout=5) as r:
                        data_inflow = json.loads(r.read().decode())
                except Exception:
                    pass

            try:
                ap = {
                    "operationName": "busesCurrentLocation", "variables": {},
                    "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle delay destinationName lastStopName\n    latitude longitude linkNumber state type\n    mainType spz updated linkNumberAlias __typename\n  }\n}"
                }
                req2 = urllib.request.Request(
                    url_arriva, data=json.dumps(ap).encode('utf-8'),
                    headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json',
                             'Origin': 'https://www.arriva.cz', 'Referer': 'https://www.arriva.cz/'},
                    method='POST')
                with urllib.request.urlopen(req2, timeout=5) as r2:
                    resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and resp2:
                    data_arriva = resp2[0].get("data", {}).get("busesCurrentLocations", [])
                elif isinstance(resp2, dict):
                    data_arriva = resp2.get("data", {}).get("busesCurrentLocations", [])
                # Arriva fetch stats
                if data_arriva:
                    _arriva_fetch_stats["ok"] += 1
                    _arriva_fetch_stats["last_ok_cnt"] = len(data_arriva)
                else:
                    _arriva_fetch_stats["empty"] += 1
                    print(f"[ARRIVA-WARN] Prazdna odpoved z Arriva API (resp keys: {list(resp2.keys()) if isinstance(resp2, dict) else type(resp2).__name__})", flush=True)
            except urllib.error.HTTPError as e_http:
                _arriva_fetch_stats["fail"] += 1
                _arriva_fetch_stats["last_fail_reason"] = f"HTTP {e_http.code}: {e_http.reason}"
                print(f"[ARRIVA-ERR] HTTP chyba: {e_http.code} {e_http.reason} - Arriva API blokuje?", flush=True)
            except urllib.error.URLError as e_url:
                _arriva_fetch_stats["fail"] += 1
                _arriva_fetch_stats["last_fail_reason"] = str(e_url.reason)
                print(f"[ARRIVA-ERR] URL chyba: {e_url.reason}", flush=True)
            except Exception as e_gen:
                _arriva_fetch_stats["fail"] += 1
                _arriva_fetch_stats["last_fail_reason"] = str(e_gen)
                print(f"[ARRIVA-ERR] Neocekavana chyba: {e_gen}", flush=True)

            # === SPZ MEMORY UPDATE: uloz pozice z Arriva pro kazdou SPZ ===
            # To nam umozni matchovat SPZ i kdyz Arriva bus momentalne nevidí
            for b_a in data_arriva:
                b_spz = (b_a.get("spz") or "").strip()
                if not b_spz or b_spz == "Neznámá":
                    continue
                b_lat = b_a.get("latitude") or 0
                b_lon = b_a.get("longitude") or 0
                b_line = str(b_a.get("linkNumber") or b_a.get("linkNumberAlias") or "").strip()
                b_dest = str(b_a.get("destinationName") or "").strip()
                # aktualizuj/pridej do pameti
                SPZ_MEMORY[b_spz] = {
                    "last_arriva_lat": b_lat,
                    "last_arriva_lng": b_lon,
                    "last_arriva_time": now,
                    "line": b_line,
                    "destination": b_dest,
                    "verified": False,  # bude nastaveno pri 3-faktor match
                }

            current_inflow_ids = set()
            new_live_data = []


            if isinstance(data_inflow, list):
                for bus1 in data_inflow:
                    try:
                        bus_id = str(bus1.get("id", "0"))
                        line = str(bus1.get("text", "")).strip()
                        lat1 = bus1.get("lat", 0)
                        lng1 = bus1.get("lng", 0)
                        delay = int(bus1.get("delay", 0)) if bus1.get("delay") is not None else 0
                        dest1 = str(bus1.get("finalStopName", "")).strip()
                        traction = str(bus1.get("traction", "BUS")).upper()
                        is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]

                        if bus_id in ADMIN_DELETED_BUSES:
                            if not is_same_line(line, ADMIN_DELETED_BUSES[bus_id]):
                                del ADMIN_DELETED_BUSES[bus_id]
                            else:
                                current_inflow_ids.add(bus_id)
                                continue

                        current_inflow_ids.add(bus_id)

                        if bus_id not in GLOBAL_BUS_CACHE:
                            TRIP_COUNTER += 1
                            ghost_spz = None
                            ghost_verified = False
                            ghost_trip_id = f"TRIP-{TRIP_COUNTER}"
                            gc_list = []
                            for gid, gc in list(GLOBAL_BUS_CACHE.items()):
                                if not (gc.get("is_offline") and gc.get("spz") and gc["spz"] != "Nezn\u00e1m\u00e1"):
                                    continue
                                oa_min = (now - gc["last_inflow_seen"]).total_seconds() / 60.0
                                if oa_min > 1080:
                                    continue
                                gd = math.hypot(lat1 - gc["lat"], lng1 - gc["lng"])
                                lm = is_same_line(line, gc["line"])
                                if lm and gd < 0.08:
                                    gc_list.append((gid, gc, gd, gd + oa_min * 0.0001 - 0.05))
                                elif gd < GHOST_DIST_STRICT and oa_min <= GHOST_MAX_OFFLINE_MIN:
                                    gc_list.append((gid, gc, gd, gd + oa_min * 0.0005))
                            if gc_list:
                                gc_list.sort(key=lambda x: x[3])
                                best_gid, best_gc, _, _ = gc_list[0]
                                ghost_spz = best_gc["spz"]
                                if is_same_line(line, best_gc["line"]):
                                    ghost_trip_id = best_gc["trip_id"]
                                    ghost_verified = best_gc.get("spz_verified", False)
                                    ghost_admin_verified = best_gc.get("admin_spz_verified", False)
                                    ghost_admin_note = best_gc.get("admin_note", "")
                                    ghost_admin_flag = best_gc.get("admin_flag", False)
                                    ghost_color_class = best_gc.get("color_class")
                                    ghost_status = best_gc.get("status")
                                    ghost_manual_spz = best_gc.get("manual_spz", False)
                                del GLOBAL_BUS_CACHE[best_gid]
                                if db_client and ghost_spz and ghost_spz != "Neznámá":
                                    close_previous_trips(db_client, ghost_spz, ghost_trip_id, now.strftime('%H:%M'))
                            
                            nb = new_cache_entry(
                                bus_id, ghost_trip_id, lat1, lng1, line, dest1, is_train, delay, now,
                                ghost_spz, ghost_verified, ghost_admin_verified if 'ghost_admin_verified' in locals() else False)
                            
                            if 'ghost_admin_note' in locals():
                                nb["admin_note"] = ghost_admin_note
                                nb["admin_flag"] = ghost_admin_flag
                                nb["manual_spz"] = ghost_manual_spz
                                if ghost_color_class and ghost_color_class != "bg-gray":
                                    nb["color_class"] = ghost_color_class
                                if ghost_status and ghost_status != "Načítání...":
                                    nb["status"] = ghost_status
                            
                            if bus_id in ADMIN_SPZ_LOCKS:
                                lock = ADMIN_SPZ_LOCKS[bus_id]
                                nb["spz"] = lock["spz"]
                                nb["admin_spz_verified"] = True
                                nb["admin_flag"] = True
                                nb["spz_verified"] = True
                                nb["manual_spz"] = True
                                nb["spz_locked"] = True
                                nb["spz_frozen"] = True
                                nb["color_class"] = lock.get("color_class", "bg-darkblue")
                                if lock.get("admin_note"):
                                    nb["admin_note"] = lock["admin_note"]
                            
                            GLOBAL_BUS_CACHE[bus_id] = nb

                        else:
                            c = GLOBAL_BUS_CACHE[bus_id]
                            c["last_inflow_seen"] = now
                            c["is_offline"] = False
                            c["raw_delay"] = delay
                            c["is_train"] = is_train
                            dm = math.hypot(lat1 - c["lat"], lng1 - c["lng"])
                            
                            is_restored = c.pop("_is_restored", False)
                            if is_restored:
                                c["line"] = line
                                # Ignoruj prni nesoulad linky pri nacteni z db

                            if bus_id in ADMIN_SPZ_LOCKS:
                                lock = ADMIN_SPZ_LOCKS[bus_id]
                                c["spz"] = lock["spz"]
                                c["admin_spz_verified"] = True
                                c["admin_flag"] = True
                                c["spz_verified"] = True
                                c["manual_spz"] = True
                                c["spz_locked"] = True
                                c["spz_frozen"] = True
                                c["color_class"] = lock.get("color_class", "bg-darkblue")
                                if lock.get("admin_note"):
                                    c["admin_note"] = lock["admin_note"]

                            if not is_same_line(c["line"], line) and line and c["line"] != "Nezn\u00e1m\u00e1":
                                if not c["actual_end_time"]:
                                    c["actual_end_time"] = now.strftime('%H:%M')
                                    c["status"] = "Ukon\u010deno (Za\u010d\u00e1tek nov\u00e9ho spoje)"
                                    upsert_to_history(db_client, c)
                                TRIP_COUNTER += 1
                                nti = f"TRIP-{TRIP_COUNTER}"
                                if c.get("spz") and c["spz"] != "Nezn\u00e1m\u00e1" and db_client:
                                    close_previous_trips(db_client, c["spz"], nti, now.strftime('%H:%M'))
                                c["trip_id"] = nti
                                c["line"] = line
                                c["real_linka_spoj"] = None
                                c["destination"] = dest1
                                c["first_dep_time"] = None
                                c["last_dep_time"] = None
                                c["actual_start_time"] = None
                                c["actual_end_time"] = None
                                c["created_at"] = now
                                c["status"] = "Na\u010d\u00edt\u00e1n\u00ed..."
                                c["bearing"] = None
                                # BUG-zamknute SPZ se NIKDY automaticky neresetuje (ani pri zmene linky)
                                if not c.get("manual_spz") and not c.get("bug_locked"):
                                    c["spz_locked"] = False
                                    c["spz_verified"] = False
                                    # spz_frozen se UVOLNI presne tady - novy spoj na nove
                                    # lince je legitimni duvod zacit hledat SPZ od znovu,
                                    # i kdyz byl bus driv "Kone\u010dn\u00e1 zast\u00e1vka"/v depu.
                                    c["spz_frozen"] = False
                                    c["spz_last_audit_check"] = None
                                if not c.get("admin_lock_permanent"):
                                    c["admin_lock_display"] = False
                                    c["admin_color_override"] = None
                                    c["admin_status_override"] = None
                                c["investigating"] = False
                                c["db_first_upsert"] = False
                                c["_last_db_status"] = None
                                c["_last_db_linka"] = None
                                c["_end_written"] = False
                            else:
                                if dest1:
                                    c["destination"] = dest1
                                if line and len(line) > len(c.get("line", "")):
                                    c["line"] = line

                            if dm > 0.0001:
                                l1r = math.radians(c["lat"])
                                l2r = math.radians(lat1)
                                ld = math.radians(lng1 - c["lng"])
                                y = math.sin(ld) * math.cos(l2r)
                                x = math.cos(l1r) * math.sin(l2r) - math.sin(l1r) * math.cos(l2r) * math.cos(ld)
                                c["bearing"] = int((math.degrees(math.atan2(y, x)) + 360) % 360)
                                c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1
                    except Exception:
                        continue

            # ── Duplikaty (bug-locked vozy vynechej – jejich SPZ je navzdy zamknuta) ─────
            spz_tracker = {}
            for bid, bc in GLOBAL_BUS_CACHE.items():
                sv = bc.get("spz")
                if sv and sv != "Nezn\u00e1m\u00e1" and not bc.get("is_offline") and not bc.get("bug_locked"):
                    spz_tracker.setdefault(sv, []).append(bid)
            for sv, bus_ids in spz_tracker.items():
                if len(bus_ids) <= 1:
                    bc0 = GLOBAL_BUS_CACHE[bus_ids[0]]
                    bc0["investigating"] = False
                    bc0["investigation_start"] = None
                    if bc0.get("color_class") == "bg-bug":
                        bc0["color_class"] = "bg-gray"
                        bc0["status"] = "Stoj\u00ed"
                    continue
                mb = [bid for bid in bus_ids if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() < 60]
                sb = [bid for bid in bus_ids if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() > 180]
                if mb and sb:
                    for bid in sb:
                        bc = GLOBAL_BUS_CACHE[bid]
                        if (now - bc["last_moved"]).total_seconds() / 60.0 < 2:
                            bc["color_class"] = "bg-orange"
                            bc["status"] = "V\u00fdzkum – Duplitn\u00ed SPZ"
                        else:
                            # Tecka se zasekla, SPZ jede jinde -> BUG lock NAVZDY
                            if bc.get("admin_spz_verified"):
                                print(f"[ADMIN-VERIFY] status odebrán admin potvrzením a přesunut", flush=True)
                                bc["admin_spz_verified"] = False
                                bc["admin_spz_bug"] = True
                                for mb_id in mb:
                                    GLOBAL_BUS_CACHE[mb_id]["admin_spz_conflict"] = True
                                    GLOBAL_BUS_CACHE[mb_id]["spz_verified"] = True

                            bc["status"] = "BUG - NEAKTU\u00c1LN\u00cd M\u00cdSTO"
                            bc["color_class"] = "bg-bug"
                            bc["spz_locked"] = True
                            bc["bug_locked"] = True
                        bc["investigating"] = False
                        bc["investigation_start"] = None
                    for bid in mb:
                        GLOBAL_BUS_CACHE[bid]["investigating"] = False
                        GLOBAL_BUS_CACHE[bid]["investigation_start"] = None
                    continue

                def sc_fn(bid):
                    bc = GLOBAL_BUS_CACHE[bid]
                    return (bc.get("spz_stable_ticks", 0), bc.get("spz_last_verified") or datetime.min)
                best_bid = max(bus_ids, key=sc_fn)
                for bid in bus_ids:
                    bc = GLOBAL_BUS_CACHE[bid]
                    if bid == best_bid:
                        bc["investigating"] = False
                        bc["investigation_start"] = None
                    else:
                        if not bc.get("manual_spz") and not bc.get("bug_locked"):
                            bc["spz_verified"] = False
                            bc["spz_locked"] = False
                        bc["investigating"] = True
                        bc["investigation_spz"] = sv
                        if bc.get("investigation_start") is None:
                            bc["investigation_start"] = now
                        elif (now - bc["investigation_start"]).total_seconds() > DUPLICATE_GRACE_SEC and not bc.get("manual_spz") and not bc.get("bug_locked"):
                            bc["spz_verified"] = False
                            bc["spz_locked"] = False
                            bc["investigating"] = False
                            bc["investigation_start"] = None
                            bc["spz_stable_ticks"] = 0

            # ── Offline + timeouty ────────────────────────────────────────────────────────
            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                om = (now - c["last_inflow_seen"]).total_seconds() / 60.0
                tm = (now - c["first_seen"]).total_seconds() / 60.0
                if tm > 1200 and not c["actual_end_time"] and not c.get("is_offline"):
                    c["actual_end_time"] = now.strftime('%H:%M')
                    c["status"] = "Timeout"
                    c["color_class"] = "bg-gray"
                    upsert_to_history(db_client, c)
                    if bus_id in DEPOT_ACTIVE_SESSIONS:
                        try:
                            db_client.table("depot_history").update({"left_at": datetime.now(ZoneInfo('Europe/Prague')).isoformat()}).eq("id", DEPOT_ACTIVE_SESSIONS[bus_id]["id"]).execute()
                        except: pass
                        del DEPOT_ACTIVE_SESSIONS[bus_id]
                        DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                if bus_id not in current_inflow_ids:
                    if om > 1080:
                        upsert_to_history(db_client, c)
                        if bus_id in DEPOT_ACTIVE_SESSIONS:
                            try:
                                db_client.table("depot_history").update({"left_at": datetime.now(ZoneInfo('Europe/Prague')).isoformat()}).eq("id", DEPOT_ACTIVE_SESSIONS[bus_id]["id"]).execute()
                            except: pass
                            del DEPOT_ACTIVE_SESSIONS[bus_id]
                            DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                        del GLOBAL_BUS_CACHE[bus_id]
                        continue
                    c["is_offline"] = True
                    spz_ok = bool(c.get("spz") and c.get("spz") != "Nezn\u00e1m\u00e1")
                    # === SPZ MEMORY: uloz posledni PVVD pozici pro offline bus ===
                    if spz_ok and c.get("spz") in SPZ_MEMORY:
                        SPZ_MEMORY[c["spz"]]["last_pvvd_lat"] = c["lat"]
                        SPZ_MEMORY[c["spz"]]["last_pvvd_lng"] = c["lng"]
                        SPZ_MEMORY[c["spz"]]["last_pvvd_time"] = now
                        SPZ_MEMORY[c["spz"]]["last_pvvd_bus_id"] = bus_id
                    if om >= 120:
                        c["status"] = "Stoj\u00ed v depu / Vozovn\u011b"
                        c["color_class"] = "bg-gray"
                        c["raw_delay"] = 0
                        c["spz_locked"] = True
                        if spz_ok:
                            c["spz_frozen"] = True   # máme SPZ - zamraž ji, bude vidět i v depu
                    elif om >= 15:
                        c["status"] = "Odstaven (Bez sign\u00e1lu)"
                        c["color_class"] = "bg-gray"
                        c["raw_delay"] = 0
                        c["spz_locked"] = True
                        if spz_ok:
                            c["spz_frozen"] = True
                    elif om > 2:
                        if not c["actual_end_time"]:
                            c["actual_end_time"] = now.strftime('%H:%M')
                        c["status"] = "Ztr\u00e1ta polohy (Kone\u010dn\u00e1)"
                        c["color_class"] = "bg-purple"
                        c["raw_delay"] = 0
                        c["spz_locked"] = True
                        if spz_ok:
                            c["spz_frozen"] = True
                        if om < 4:
                            upsert_to_history(db_client, c)

            # ── Statusy, barvy, SPZ parovani ─────────────────────────────────────────────
            new_live_data = []
            tt_ftick = 0
            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                inact = (now - c["last_moved"]).total_seconds() / 60.0
                
                # ── Retroaktivni uprava SPZ vozovny ──────────────────────────────────────
                if c.get("spz") and c["spz"] not in ("Nezn\u00e1m\u00e1", "Neznámá") and not c.get("_depot_retro_updated"):
                    if db_client:
                        try:
                            # Prepis ID na SPZ zpetne
                            db_client.table("depot_history").update({"spz": c["spz"]}).eq("bus_id", bus_id).like("spz", "[ID:%").execute()
                            c["_depot_retro_updated"] = True
                            DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                        except Exception: pass
                        
                # ── Vozovna check ────────────────────────────────────────────────────────
                # Zkontroluj zda je bus uvnitr nejake vozovny (depot zone).
                # Kontrola probiha jen kazdych DEPOT_CHECK_INTERVAL_SEC sekund
                # aby se neskenoval polygon pri kazdem tiku (10s).
                if DEPOT_ZONES and not c.get("is_train") and not c.get("admin_lock_display"):
                    last_depot_check = c.get("_last_depot_check")
                    depot_due = (not last_depot_check or
                                 (now - last_depot_check).total_seconds() >= DEPOT_CHECK_INTERVAL_SEC)
                    if depot_due:
                        c["_last_depot_check"] = now
                        depot_name, depot_color = _check_depot_zones(c.get("lat"), c.get("lng"))
                        if c.get("color_class") == "bg-bug":
                            depot_name = None
                        
                        if depot_name:
                            if not c.get("_in_depot"):
                                c["_in_depot"] = True
                                c["_depot_name"] = depot_name
                                c["_depot_color"] = depot_color or "#facc15"
                                # Zamraz SPZ - bus parkuje, nema smysl re-auditovat
                                spz_val = c.get("spz")
                                if spz_val and spz_val not in ("Nezn\u00e1m\u00e1", "Neznámá"):
                                    c["spz_frozen"] = True
                                    c["spz_locked"] = True

                                # === DETEKCE DUPLICITY VOZOVNA vs. AKTIVNI MAPA ===
                                # Pokud stejná SPZ jede zároveň na aktivní mapě (jiný bus_id),
                                # vozovnový záznam označíme jako BUG a zapíšeme do logu.
                                if spz_val and spz_val not in ("Nezn\u00e1m\u00e1", "Neznámá"):
                                    for oth_id, oth_c in list(GLOBAL_BUS_CACHE.items()):
                                        if oth_id == bus_id:
                                            continue
                                        if (oth_c.get("spz") == spz_val
                                                and not oth_c.get("is_offline")
                                                and not oth_c.get("bug_locked")):
                                            # Duplicita! Vozovnový bus dostane BUG.
                                            if c.get("admin_spz_verified"):
                                                print(f"[ADMIN-VERIFY] status odebrán admin potvrzením a přesunut", flush=True)
                                                c["admin_spz_verified"] = False
                                                c["admin_spz_bug"] = True
                                                oth_c["admin_spz_conflict"] = True
                                                oth_c["spz_verified"] = True
                                                
                                            c["color_class"] = "bg-bug"
                                            c["status"] = "BUG \u2013 Syst\u00e9m rozpoznal duplicitu SPZ"
                                            c["bug_locked"] = True
                                            c["spz_frozen"] = True
                                            dup_msg = (f"Syst\u00e9m rozpoznal duplicitu v {now.strftime('%H:%M %d.%m.%Y')}: "
                                                       f"SPZ {spz_val} v\u00edz\u00ed tak\u00e9 aktivn\u011b bus_id={oth_id} "
                                                       f"(L{oth_c.get('line','?')})")
                                            _report_situace("DUP_DEPOT", dup_msg,
                                                            spz=spz_val, depot_bus=bus_id, active_bus=oth_id)
                                            # Zapis do depot_history jako poznamka
                                            if db_client and bus_id in DEPOT_ACTIVE_SESSIONS:
                                                try:
                                                    db_client.table("depot_history").update({
                                                        "spz": f"[BUG-DUP] {spz_val}",
                                                    }).eq("id", DEPOT_ACTIVE_SESSIONS[bus_id]["id"]).execute()
                                                except Exception:
                                                    pass
                                            print(f"[DEPOT-DUP] SPZ {spz_val}: bus {bus_id} ve vozovne "
                                                  f"+ bus {oth_id} aktivni na mape -> BUG", flush=True)
                                            break

                                if bus_id not in DEPOT_ACTIVE_SESSIONS:
                                    is_imprecise = (now - SCRIPT_START_TIME).total_seconds() < 120
                                    try:
                                        eff_spz = spz_val if spz_val and spz_val not in ("Nezn\u00e1m\u00e1", "Neznámá") else f"[ID: {bus_id}]"
                                        resp = db_client.table("depot_history").insert({
                                            "spz": eff_spz,
                                            "bus_id": bus_id,
                                            "depot_name": depot_name,
                                            "arrived_at": get_internet_prague_time(),
                                            "is_imprecise": is_imprecise
                                        }).execute()
                                        if resp.data:
                                            DEPOT_ACTIVE_SESSIONS[bus_id] = {
                                                "id": resp.data[0]["id"],
                                                "depot_name": depot_name,
                                                "arrived_at": get_internet_prague_time(),
                                                "is_imprecise": is_imprecise,
                                                "spz": eff_spz
                                            }
                                            DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                                    except Exception as e:
                                        print(f"[DEPOT] Chyba zapisu DB prijezdu pro bus_id={bus_id}: {e}")
                                print(f"[DEPOT] Bus {bus_id} ({c.get('spz','?')}) vjel do vozovny '{depot_name}'", flush=True)
                            else:
                                # Aktualizuj barvu i kdyz uz je v depu (mohla se zmenit)
                                c["_depot_color"] = depot_color or "#facc15"
                                # Update zpetne SPZ pokud ji najdeme
                                if bus_id in DEPOT_ACTIVE_SESSIONS:
                                    sess_spz = DEPOT_ACTIVE_SESSIONS[bus_id].get("spz")
                                    curr_spz = c.get("spz")
                                    if curr_spz and curr_spz not in ("Nezn\u00e1m\u00e1", "Neznámá") and curr_spz != sess_spz:
                                        DEPOT_ACTIVE_SESSIONS[bus_id]["spz"] = curr_spz
                                        try:
                                            db_client.table("depot_history").update({"spz": curr_spz}).eq("id", DEPOT_ACTIVE_SESSIONS[bus_id]["id"]).execute()
                                            DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                                        except Exception:
                                            pass
                        else:
                            if c.get("_in_depot"):
                                old_depot_name = c.get("_depot_name")
                                if bus_id in DEPOT_ACTIVE_SESSIONS:
                                    session_id = DEPOT_ACTIVE_SESSIONS[bus_id]["id"]
                                    try:
                                        db_client.table("depot_history").update({
                                            "left_at": get_internet_prague_time()
                                        }).eq("id", session_id).execute()
                                    except Exception as e:
                                        print(f"[DEPOT] Chyba zapisu DB odjezdu: {e}")
                                    del DEPOT_ACTIVE_SESSIONS[bus_id]
                                    DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
                                c["_in_depot"] = False
                                c["_depot_name"] = None
                                c["_depot_color"] = None
                                # Odemkni SPZ - bus opustil vozovnu, muzeme hledat znovu
                                if not c.get("manual_spz") and not c.get("bug_locked"):
                                    c["spz_frozen"] = False
                                    c["spz_locked"] = False
                                    c["spz_verified"] = False
                                    c["spz_stable_ticks"] = 0
                                print(f"[DEPOT] Bus {bus_id} opustil vozovnu", flush=True)

                if c.get("is_offline"):
                    fld = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c.get("is_train") else "Nezn\u00e1m\u00e1")
                    new_live_data.append({
                        "id": bus_id, "trip_id": c.get("trip_id"), "lat": c.get("lat"), "lng": c.get("lng"),
                        "bearing": c.get("bearing"), "line": fld, "delay": 0,
                        "destination": c.get("destination"), "spz": c.get("spz") or "Nezn\u00e1m\u00e1",
                        "spz_verified": c.get("spz_verified", False), "is_train": c.get("is_train"),
                        "status": c.get("status"), "color_class": c.get("color_class"),
                        "inactive_minutes": inact,
                        "last_updated": c["last_moved"].strftime("%H:%M:%S") if c.get("last_moved") else "N/A",
                        "investigating": False, "investigation_spz": "",
                        "admin_flag": c.get("admin_flag", False), "admin_note": c.get("admin_note", ""),
                        "in_depot": c.get("_in_depot", False),
                        "depot_name": c.get("_depot_name"),
                        "depot_color": c.get("_depot_color")
                    })
                    continue

                lat1 = c["lat"]; lng1 = c["lng"]; line = c["line"]
                dest1 = c["destination"]; is_train = c["is_train"]
                is_moving = inact < 1
                delay_val = c["raw_delay"]

                # ══════════════════════════════════════════════════════════════════
                # SPZ PAROVANI – kontinualni, samoopravne
                # ──────────────────────────────────────────────────────────────────
                # Klicove opravy oproti puvodni verzi:
                # 1) Blok bezi VZDY (ne jen kdyz spz_locked==False) -> i zamknuta SPZ
                #    se kazdy tik overi, ze stale sedi. Pokud nesedi, uvolni se a hleda znovu.
                # 2) best_match_dest se ted pouziva jako TVRDA PODMINKA (kandidat s nesedici
                #    destinaci se rovnou zahodí, misto toho aby jen nezaktualizoval timestamp).
                # 3) lastStopName z Arrivy se pouziva jako dalsi krizova kontrola (pokud GTFS data dostupna).
                # 4) Kdyz bus dlouho nestoji v pohybu (inact > 10 min - stejny prah jako
                #    "Stoji prilis dlouho" status nize), SPZ se NEPARUJE ANI NEKONTROLUJE.
                #    Stojici bus (depo, zaseknuty, cekajici dlouho) ma nespolehlivou polohu
                #    vuci zive Arriva mape - hledani/re-audit SPZ za techto podminek casteji
                #    vede ke spatnemu prirazeni nez k uzitku. SPZ zustava zamrazena na
                #    poslednim znamem stavu, dokud se bus znovu nerozjede.
                # 5) spz_frozen: jakmile bus opravdu DOJEL (konecna zastavka / depo /
                #    odstaven), SPZ se TVRDE zamkne a uz se vubec nezkousi menit - ani
                #    pri pripadnem znovu-pripojeni k Arrive. To je schvalne JINE nez
                #    behem jizdy (kde SPZ zustava soft-zamcena a porad prubezne
                #    samoopravna) - po dojeti uz nehrozi false-positive prebehnuti na
                #    jinou SPZ, ale hrozi ze by re-audit kvuli ridke Arriva poloze na
                #    parkovisti/v depu omylem SPZ odemkl a system by ji ztratil z dohledu.
                # ══════════════════════════════════════════════════════════════════
                # SPZ PAROVÁNÍ: spustí se pokud:
                # - Bus nemá SPZ vůbec (vždy hledej bez ohledu na inact)
                # - Bus má SPZ ale není frozen (hledej/reaudituj při jízdě)
                # Přeskočí jen: manual_spz, bug_locked, investigating, vlak,
                #               admin_spz_verified (absolutni admin lock),
                #               blokované barvy (bg-bug/blue/purple/gray) bez admin_verified,
                #               nebo spz_frozen s platnou SPZ (po dojeti na konečnou)

                # Sleduj první pohyb (pro SPZ_MIN_MOVE_MINUTES)
                if is_moving and not c.get("_first_move_time"):
                    c["_first_move_time"] = now

                has_valid_spz = bool(c.get("spz") and c.get("spz") != "Nezn\u00e1m\u00e1")
                if c.get("spz_frozen") and not has_valid_spz:
                    c["spz_frozen"] = False

                # Pokud ma admin_spz_verified, SPZ je absolutne zamcena - skip vse
                if c.get("admin_spz_verified") and has_valid_spz:
                    skip_spz = True
                else:
                    force_search = (not has_valid_spz and not c.get("spz_frozen")
                                    and not c.get("manual_spz") and not c.get("bug_locked")
                                    and not is_train and inact <= 120)
                    skip_spz = (is_train or c.get("investigating") or c.get("manual_spz")
                                or c.get("bug_locked")
                                or (c.get("spz_frozen") and has_valid_spz and inact > 2))

                    # Blokuj SPZ parovani pri blokovanych stavech (nematchuj kdyz bus neni fyzicky na trase)
                    if not c.get("admin_spz_verified"):
                        if c.get("color_class") in SPZ_BLOCKED_COLORS and has_valid_spz:
                            skip_spz = True  # Ma SPZ - nech ji zamrzenou, ale nehledej novou
                        elif c.get("color_class") in SPZ_BLOCKED_COLORS and not has_valid_spz:
                            # Nema SPZ + je v blokovane barve = nehledej (nema smysl, Arriva ho nevidí)
                            skip_spz = True

                    # Minimalni pohyb pred prvnim SPZ parovanim
                    if not has_valid_spz and not skip_spz:
                        first_move = c.get("_first_move_time")
                        if not first_move or (now - first_move).total_seconds() < SPZ_MIN_MOVE_MINUTES * 60:
                            skip_spz = True  # Bus jede prilis kratce, pockat na potvrzeni pohybu

                    if force_search and not c.get("color_class") in SPZ_BLOCKED_COLORS:
                        skip_spz = False

                if not skip_spz:
                    d1_norm = _norm_txt(dest1)
                    near_stop = _nearest_stop_name(lat1, lng1, ARRIVA_STOP_MATCH_M) if GTFS_LOADED else None
                    near_stop_norm = _norm_txt(near_stop) if near_stop else ""

                    # 3-FAKTOROVY SPZ ALGORITMUS
                    gate_pass    = {}   # spz -> dist_m (linka+pozice+cil = full match)
                    gate_3f      = set()  # spz ktere prosly vsemi 3 faktory => prima fajfka
                    gate_partial = {}   # spz -> dist_m (jen linka+pozice <= 500m, fallback)

                    for b_a in data_arriva:
                        b_spz = (b_a.get("spz") or "").strip()
                        if not b_spz or b_spz == "Nezn\u00e1m\u00e1":
                            continue
                        if not _arriva_line_matches(line, b_a):
                            continue
                        b_lat = b_a.get("latitude") or 0
                        b_lon = b_a.get("longitude") or 0
                        dist_m = haversine_m(lat1, lng1, b_lat, b_lon)
                        if dist_m <= 500:
                            if b_spz not in gate_partial or dist_m < gate_partial[b_spz]:
                                gate_partial[b_spz] = dist_m
                        if dist_m > ARRIVA_MATCH_DIST_M:
                            continue
                        if b_spz not in gate_pass or dist_m < gate_pass[b_spz]:
                            gate_pass[b_spz] = dist_m
                        # Faktor 3: cil + posledni zastavka + bonus: smer (bearing)
                        ok_dir = True
                        a_dest_norm = _norm_txt(b_a.get("destinationName", ""))
                        if d1_norm and a_dest_norm:
                            ok_dir = (d1_norm in a_dest_norm or a_dest_norm in d1_norm)
                        ok_stop = True
                        if near_stop_norm:
                            a_stop_norm = _norm_txt(b_a.get("lastStopName", ""))
                            if a_stop_norm:
                                ok_stop = (near_stop_norm in a_stop_norm or a_stop_norm in near_stop_norm)
                        # Bonus faktor: bearing (smer jizdy) - pokud mame oba szmery,
                        # kandidat jedouci OPACNYM smerem dostane penalizaci (ne plnou zamitnutí,
                        # protoze PVVD a Arriva nemaji vzdy sync bearing)
                        ok_bearing = True
                        a_angle = b_a.get("angle")
                        if c.get("bearing") is not None and a_angle is not None:
                            bdiff = _bearing_diff(c["bearing"], a_angle)
                            ok_bearing = (bdiff <= SPZ_BEARING_MAX_DIFF)
                        if ok_dir and ok_stop and ok_bearing:
                            gate_3f.add(b_spz)

                    if gate_3f:
                        best_spz = min(gate_3f, key=lambda s: gate_pass.get(s, 9999))
                    elif gate_pass:
                        best_spz = min(gate_pass, key=gate_pass.get)
                    elif not has_valid_spz and gate_partial:
                        best_spz = min(gate_partial, key=gate_partial.get)
                    else:
                        best_spz = None

                    # === SPZ MEMORY FALLBACK: kdyz Arriva nevidí bus, pouzij pamet ===
                    # Pokud nemame best_spz z aktualnich Arriva dat, ale bus ma trip_id
                    # a v pameti je SPZ stejne linky blizko, pouzij tu.
                    if not best_spz and not has_valid_spz and not c.get("spz_frozen"):
                        trip_id = c.get("trip_id")
                        # Hledej v SPZ_MEMORY SPZ na stejne lince blizko PVVD pozice
                        mem_candidates = []
                        for spz, mem in SPZ_MEMORY.items():
                            if not is_same_line(mem.get("line", ""), line):
                                continue
                            mem_lat = mem.get("last_arriva_lat", 0)
                            mem_lng = mem.get("last_arriva_lng", 0)
                            if mem_lat == 0 or mem_lng == 0:
                                continue
                            dist_m = haversine_m(lat1, lng1, mem_lat, mem_lng)
                            # Pripustna vzdalenost: 1.5km (vetsi nez ARRIVA_MATCH_DIST_M=750)
                            # protoze pamet muze byt starsi a bus se mohl pohnout
                            if dist_m <= 1500:
                                age_sec = (now - mem.get("last_arriva_time", now)).total_seconds()
                                if age_sec <= SPZ_MEMORY_MAX_AGE_HOURS * 3600:
                                    mem_candidates.append((spz, dist_m, age_sec, mem.get("verified", False)))
                        if mem_candidates:
                            # Preferuj: mensi vzdalenost, novejsi data, verified
                            mem_candidates.sort(key=lambda x: (x[1], x[2], not x[3]))
                            best_spz = mem_candidates[0][0]
                            # Označ jako z paměti (ne 3-faktor)
                            c["spz_from_memory"] = True
                            print(f"[MAPA] SPZ MEMORY MATCH: bus {bus_id} (L{line}) -> {best_spz} (dist={mem_candidates[0][1]:.0f}m, age={mem_candidates[0][2]:.0f}s)")

                    # REPORT SITUACE: duplicitni SPZ
                    if best_spz:
                        for oth_id, oth_c in list(GLOBAL_BUS_CACHE.items()):
                            if oth_id == bus_id:
                                continue
                            if (oth_c.get("spz") == best_spz
                                    and oth_c.get("spz_verified")
                                    and not oth_c.get("is_offline")):
                                oth_line = oth_c.get("line", "")
                                oth_lat = oth_c.get("lat") or 0
                                oth_lng = oth_c.get("lng") or 0
                                dist_between = round(haversine_m(lat1, lng1, oth_lat, oth_lng))
                                lines_differ = not is_same_line(line, oth_line)
                                is_3f_winner = (best_spz in gate_3f)
                                _report_situace(
                                    "DUP_SPZ",
                                    f"SPZ {best_spz} pouziva aktivni bus {oth_id} (L{oth_line})"
                                    f" a take bus {bus_id} (L{line})",
                                    spz=best_spz,
                                    bus_a=bus_id, line_a=line, lat_a=lat1, lon_a=lng1,
                                    bus_b=oth_id, line_b=oth_line,
                                    lat_b=oth_lat, lon_b=oth_lng,
                                    dist_between=dist_between,
                                    is_3factor=is_3f_winner,
                                    lines_differ=lines_differ,
                                )
                                _spz_debug_log(
                                    bus_id, "DUP_SPZ_DETECTED",
                                    spz=best_spz,
                                    detail=f"Konflikt s busem {oth_id} (L{oth_line}), dist={dist_between}m, ruzne_linky={lines_differ}",
                                    is_3f=is_3f_winner,
                                )
                                # STREDNI AGRESIVITA: pokud maji ruzne linky -> jasna chyba
                                # Okamzite odebrat SPZ starsimu (mene verifikovanimu) busu
                                if lines_differ and not oth_c.get("manual_spz") and not oth_c.get("bug_locked"):
                                    print(f"[SPZ-CONFLICT] SPZ {best_spz}: bus {bus_id} (L{line}) vs "
                                          f"bus {oth_id} (L{oth_line}) - RUZNE LINKY, dist={dist_between}m "
                                          f"-> uvolnuji SPZ u busu {oth_id}", flush=True)
                                    _spz_debug_log(
                                        oth_id, "SPZ_REMOVED_DIFF_LINE",
                                        spz=best_spz,
                                        detail=f"Odebrana SPZ kvuli konfliktu s busem {bus_id} (L{line}), ruzne linky",
                                    )
                                    if oth_c.get("spz_verified") and db_client:
                                        try:
                                            db_client.table("bus_history").update({
                                                "status": "Falešný záznam (SPZ odebrána - konflikt různé linky)",
                                                "spz_verified": False,
                                            }).eq("trip_id", oth_c["trip_id"]).execute()
                                        except Exception:
                                            pass
                                    oth_c["spz_verified"] = False
                                    oth_c["spz_locked"] = False
                                    oth_c["spz_3factor"] = False
                                    oth_c["spz_stable_ticks"] = 0
                                    oth_c["spz_conflict_warn"] = True
                                elif is_3f_winner and not oth_c.get("spz_3factor"):
                                    # Nas kandidat je 3-faktor, ostatni neni -> jen conflict_warn
                                    oth_c["spz_conflict_warn"] = True

                    # SPZ DEBUG LOG: zaznamenej matching decision pro kazdy bus
                    if best_spz:
                        _dist_raw = gate_pass.get(best_spz) or gate_partial.get(best_spz)
                        _dist_str = f"{_dist_raw:.0f}m" if isinstance(_dist_raw, (int, float)) else "?m"
                        _spz_debug_log(
                            bus_id, "SPZ_MATCH",
                            spz=best_spz,
                            detail=f"gate_3f={len(gate_3f)}, gate_pass={len(gate_pass)}, "
                                   f"gate_partial={len(gate_partial)}, "
                                   f"is_3f={best_spz in gate_3f}, "
                                   f"dist={_dist_str} inact={inact:.1f}min",
                            line=line, dest=dest1,
                            gate_3f_cnt=len(gate_3f),
                            gate_pass_cnt=len(gate_pass),
                        )
                    elif not has_valid_spz and not c.get("spz_frozen"):
                        _spz_debug_log(
                            bus_id, "SPZ_NO_MATCH",
                            detail=f"Zadny kandidat: gate_3f={len(gate_3f)}, gate_pass={len(gate_pass)}, "
                                   f"gate_partial={len(gate_partial)}, arriva_total={len(data_arriva)}, "
                                   f"inact={inact:.1f}min",
                            line=line,
                        )

                    # Re-audit: spust cely match algoritmus, ne jen listingovou kontrolu.
                    # Pokud best_spz z re-auditu je JINA nez aktualni SPZ (nebo zadna),
                    # okamzite uvolni lock - bus byl spatne pripojen.
                    current_spz = c.get("spz")
                    was_locked = bool(c.get("spz_locked"))
                    if was_locked and current_spz and current_spz != "Nezn\u00e1m\u00e1":
                        last_audit = c.get("spz_last_audit_check")
                        due = (not last_audit) or (now - last_audit).total_seconds() >= SPZ_REAUDIT_INTERVAL_SEC
                        if due:
                            c["spz_last_audit_check"] = now
                            # Audit: je aktualni SPZ stale nejlepsi kandidat?
                            if current_spz in gate_3f:
                                # Stale nejlepsi (3-faktor) - potvrd a pokracuj
                                c["spz_last_verified"] = now
                                c["spz_verified"] = True
                                c["spz_3factor"] = True
                            elif current_spz in gate_pass:
                                # Stale v dosahu (1-2 faktor) - potvrd bez 3f
                                c["spz_last_verified"] = now
                            else:
                                # Aktualni SPZ neni v arriva datech VUBEC
                                still_listed = any((ba.get("spz") or "").strip() == current_spz for ba in data_arriva)
                                last_v = c.get("spz_last_verified")
                                stale = (not last_v) or (now - last_v).total_seconds() >= SPZ_HOLD_MINUTES * 60
                                if not still_listed or stale:
                                    # SPZ zmizela z Arrivy a ceka prilis dlouho -
                                    # zkontroluj zda existuje lepsi kandidat na trase
                                    new_candidate = None
                                    if gate_3f:
                                        new_candidate = min(gate_3f, key=lambda s: gate_pass.get(s, 9999))
                                    elif gate_pass:
                                        new_candidate = min(gate_pass, key=gate_pass.get)
                                    if new_candidate and new_candidate != current_spz:
                                        # Existuje jiny kandidat na trase - uvolni lock
                                        _report_situace("SPZ_RESET",
                                            f"SPZ {current_spz} nahrazena {new_candidate} u busu {bus_id}",
                                            bus=bus_id, old_spz=current_spz, new_spz=new_candidate,
                                            reason="better_candidate_found")
                                        print(f"[SPZ] REAUDIT: {current_spz} -> {new_candidate} u busu {bus_id}", flush=True)
                                        if c.get("spz_verified") and db_client:
                                            try:
                                                db_client.table("bus_history").update({
                                                    "status": "Fale\u0161n\u00fd z\u00e1znam (SPZ opravena re-auditem)",
                                                    "spz_verified": False
                                                }).eq("trip_id", c["trip_id"]).execute()
                                            except Exception:
                                                pass
                                        c["spz_verified"] = False
                                        c["spz_locked"] = False
                                        c["spz_3factor"] = False
                                        c["spz_stable_ticks"] = 0
                                        was_locked = False
                                    elif stale:
                                        # Zadny lepsi kandidat, ale SPZ je davno neoverena
                                        _report_situace("SPZ_RESET",
                                            f"SPZ {current_spz} uvolnena (stale) u busu {bus_id}",
                                            bus=bus_id, spz=current_spz, reason="stale")
                                        print(f"[SPZ] Uvolnuji {current_spz} u busu {bus_id} (stale)", flush=True)
                                        if c.get("spz_verified") and db_client:
                                            try:
                                                db_client.table("bus_history").update({
                                                    "status": "Fale\u0161n\u00fd z\u00e1znam (SPZ opravena)",
                                                    "spz_verified": False
                                                }).eq("trip_id", c["trip_id"]).execute()
                                            except Exception:
                                                pass
                                        c["spz_verified"] = False
                                        c["spz_locked"] = False
                                        c["spz_3factor"] = False
                                        c["spz_stable_ticks"] = 0
                                        was_locked = False

                    if was_locked and (not current_spz or current_spz == "Nezn\u00e1m\u00e1"):
                        was_locked = False
                        c["spz_locked"] = False

                    # Prirazeni noveho kandidata
                    if not was_locked:
                        if best_spz:
                            is_3f = best_spz in gate_3f
                            if best_spz != current_spz:
                                if c.get("spz_verified") and current_spz and db_client:
                                    try:
                                        db_client.table("bus_history").update({
                                            "status": "Fale\u0161n\u00fd z\u00e1znam (SPZ opravena)",
                                            "spz_verified": False
                                        }).eq("trip_id", c["trip_id"]).execute()
                                    except Exception:
                                        pass
                                TRIP_COUNTER += 1
                                c["trip_id"] = f"TRIP-{TRIP_COUNTER}"
                                c["spz"] = best_spz
                                c["spz_stable_ticks"] = 1
                                c["spz_verified"] = False
                                c["spz_locked"] = False
                                c["spz_3factor"] = False
                            else:
                                c["spz_stable_ticks"] = c.get("spz_stable_ticks", 0) + 1
                            c["spz_last_verified"] = now
                            if is_3f or c.get("spz_stable_ticks", 0) >= SPZ_STABLE_TICKS:
                                c["spz_verified"] = True
                                c["spz_locked"] = True
                                c["spz_3factor"] = is_3f
                                # === SPZ MEMORY UPDATE: oznac jako verified v pameti ===
                                if best_spz in SPZ_MEMORY:
                                    SPZ_MEMORY[best_spz]["verified"] = True
                                    SPZ_MEMORY[best_spz]["last_pvvd_bus_id"] = bus_id
                                    SPZ_MEMORY[best_spz]["last_pvvd_time"] = now
                                    SPZ_MEMORY[best_spz]["trip_id"] = c.get("trip_id")
                                    if is_3f:
                                        SPZ_MEMORY[best_spz]["verified"] = True
                        else:
                            last_v = c.get("spz_last_verified")
                            if not last_v or (now - last_v).total_seconds() >= SPZ_HOLD_MINUTES * 60:
                                c["spz_verified"] = False
                                c["spz_locked"] = False
                                c["spz_3factor"] = False


                # ── JR fetch ──────────────────────────────────────────────────────────────
                if not is_train:
                    tt_age = (now - c["tt_last_fetch"]).total_seconds() if c.get("tt_last_fetch") else 9999
                    if tt_age > 300 and not c.get("tt_is_fetching") and tt_ftick < 5:
                        tt_ftick += 1
                        c["tt_last_fetch"] = now
                        c["tt_is_fetching"] = True
                        threading.Thread(target=fetch_tt_bg, args=(bus_id, c), daemon=True).start()

                # ── Barvy + status ────────────────────────────────────────────────────────
                old_status = c.get("status", "")

                if c.get("admin_lock_display"):
                    if c.get("admin_color_override"):
                        c["color_class"] = c["admin_color_override"]
                    if c.get("admin_status_override"):
                        c["status"] = c["admin_status_override"]

                elif c.get("color_class") == "bg-bug":
                    if is_moving:
                        c["color_class"] = "bg-orange"
                        c["status"] = "V\u00fdzkum \u2013 Reaktivace (byl zaseknut\u00fd)"
                elif c.get("_in_depot"):
                    # Vozovna: pevna barva + status, prepise vsechny ostatni
                    depot_name = c.get("_depot_name", "Vozovna")
                    c["color_class"] = "bg-yellow"
                    c["status"] = f"Vozovna: {depot_name}"
                else:
                    is_before_departure = False
                    time_to_dep = 0
                    if c["first_dep_time"]:
                        try:
                            dh, dm_ = map(int, c["first_dep_time"].split(':'))
                            dep_total = dh * 60 + dm_
                            cur_total = now.hour * 60 + now.minute
                            diff = dep_total - cur_total
                            if diff < -720: diff += 1440
                            elif diff > 720: diff -= 1440
                            if diff > 1:
                                is_before_departure = True
                                time_to_dep = int(diff)
                        except Exception:
                            pass

                    if is_before_departure:
                        c["actual_end_time"] = None
                        if time_to_dep <= 240:
                            c["status"] = f"\u010cek\u00e1 na odjezd ({time_to_dep} min)"
                            c["color_class"] = "bg-blue"
                        else:
                            c["status"] = "\u010cek\u00e1 na spoj (>4h)"
                            c["color_class"] = "bg-gray"
                        delay_val = -time_to_dep

                    elif delay_val <= -10000:
                        if inact > 10:
                            c["status"] = "Odstaven"
                            c["color_class"] = "bg-gray"
                            c["spz_locked"] = True
                            c["spz_frozen"] = True
                        else:
                            c["status"] = "Kone\u010dn\u00e1 zast\u00e1vka"
                            c["color_class"] = "bg-purple"
                            c["spz_locked"] = True
                            c["spz_frozen"] = True
                            if not c["actual_end_time"]:
                                c["actual_end_time"] = now.strftime('%H:%M')
                                c["_end_written"] = False
                            if c.get("admin_lock_display") and not c.get("admin_lock_permanent"):
                                c["admin_lock_display"] = False
                                c["admin_color_override"] = None
                                c["admin_status_override"] = None

                    elif delay_val < -1 and c.get("actual_start_time"):
                        c["status"] = "J\u00edzda (N\u00e1skok)" if is_moving else "Stoj\u00ed (N\u00e1skok)"
                        c["color_class"] = "bg-darkblue"

                    else:
                        c["status"] = "J\u00edzda" if is_moving else "Stoj\u00ed"
                        c["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                    if (not is_moving and inact > 10 and c.get("actual_start_time")
                            and c["color_class"] not in ("bg-purple", "bg-gray", "bg-bug", "bg-blue", "bg-orange")):
                        c["status"] = f"Stoj\u00ed p\u0159\u00edli\u0161 dlouho ({int(inact)} min)"
                        c["color_class"] = "bg-gray"
                        c["_was_long_stationary"] = True
                        # Zamkni SPZ POUZE pokud uz ji mame - nema smysl zamykat "Neznama".
                        # Kdyz SPZ jeste neni, necháme ji odemcenou at ji muzeme najit pozdeji.
                        if c.get("spz") and c["spz"] != "Nezn\u00e1m\u00e1":
                            c["spz_locked"] = True
                    elif is_moving and c.get("_was_long_stationary") and c["color_class"] not in ("bg-bug", "bg-blue"):
                        c["color_class"] = "bg-orange"
                        c["status"] = "V\u00fdzkum \u2013 Reaktivace po dlouh\u00e9m st\u00e1n\u00ed"
                        c["_was_long_stationary"] = False

                if is_moving and not c["actual_start_time"] and not is_train:
                    c["actual_start_time"] = now.strftime('%H:%M')
                    c["_end_written"] = False

                c["final_delay_display"] = delay_val

                if c.get("admin_color_override"):
                    c["color_class"] = c["admin_color_override"]
                if c.get("admin_status_override"):
                    c["status"] = c["admin_status_override"]

                # ── DB upsert ─────────────────────────────────────────────────────────────
                has_spz = c.get("spz") and c["spz"] != "Nezn\u00e1m\u00e1"
                tracked_line = _is_tracked_line(c.get("real_linka_spoj") or c.get("line", ""))
                just_ended = c.get("actual_end_time") and not c.get("_end_written")

                if has_spz and tracked_line:
                    if (not c.get("db_first_upsert") or (old_status != c["status"]) or just_ended
                            or (is_moving and c.get("actual_start_time") and int(time.time()) % 30 < 10)):
                        upsert_to_history(db_client, c)
                        c["db_first_upsert"] = True
                        c["_last_db_status"] = c["status"]
                        c["_last_db_linka"] = c.get("real_linka_spoj") or c.get("line")
                        if just_ended:
                            c["_end_written"] = True
                            close_previous_trips(db_client, c.get("spz"), c["trip_id"], c["actual_end_time"])

                fld = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c["is_train"] else "Nezn\u00e1m\u00e1")
                new_live_data.append({
                    "id": bus_id, "trip_id": c["trip_id"], "lat": c["lat"], "lng": c["lng"],
                    "bearing": c.get("bearing"), "line": fld, "delay": c.get("final_delay_display", 0),
                    "destination": c["destination"], "spz": c["spz"] or "Nezn\u00e1m\u00e1",
                    "spz_verified": c.get("spz_verified", False), "is_train": c["is_train"],
                    "status": c["status"], "color_class": c["color_class"], "inactive_minutes": inact,
                    "last_updated": c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A",
                    "investigating": c.get("investigating", False),
                    "investigation_spz": c.get("investigation_spz", ""),
                    "admin_flag": c.get("admin_flag", False), "admin_note": c.get("admin_note", ""),
                    "admin_spz_verified": c.get("admin_spz_verified", False),
                    "admin_spz_bug": c.get("admin_spz_bug", False),
                    "admin_spz_conflict": c.get("admin_spz_conflict", False)
                })

            global LIVE_BUSES_DATA, _last_spz_auto_refresh
            LIVE_BUSES_DATA = new_live_data

            # ── Auto-refresh SPZ (kazdych SPZ_AUTO_REFRESH_MIN minut) ─────────
            # Ekvivalent knofliku "Najit SPZ" pro vsechny aktivni busy najednou.
            # Klicove: ZACHOVA aktualni SPZ hodnotu pro zobrazeni, jen uvolni zamek.
            # Dalsi tik (10s) provede cerstve parovani - pokud najde STEJNOU SPZ
            # = automaticky ji znovu overi (fajfka zustane). Pokud jinou = nahradi.
            if (not _last_spz_auto_refresh or
                    (now - _last_spz_auto_refresh).total_seconds() >= SPZ_AUTO_REFRESH_MIN * 60):
                _last_spz_auto_refresh = now
                refreshed = 0
                for bid, bc in GLOBAL_BUS_CACHE.items():
                    if (bc.get("is_offline") or bc.get("manual_spz") or
                            bc.get("spz_frozen") or bc.get("bug_locked") or bc.get("is_train")
                            or bc.get("admin_spz_verified")):
                        continue
                    if bc.get("spz_locked"):
                        bc["spz_locked"] = False
                        bc["spz_verified"] = False
                        bc["spz_3factor"] = False
                        bc["spz_stable_ticks"] = 0
                        bc["spz_last_audit_check"] = None
                        refreshed += 1
                if refreshed:
                    print(f"[SPZ AUTO-REFRESH] Reset SPZ zamku u {refreshed} busu -> dalsi tik opatri cerstve parovani", flush=True)

            # ── SPZ CACHE FLUSH do Supabase (kazdych SPZ_CACHE_FLUSH_SEC sekund) ─────────
            if db_client and (now - last_spz_cache_flush).total_seconds() >= SPZ_CACHE_FLUSH_SEC:
                last_spz_cache_flush = now
                cache_rows = []
                for bid, bc in list(GLOBAL_BUS_CACHE.items()):
                    spz_v = bc.get("spz")
                    if not spz_v or spz_v in ("Nezn\u00e1m\u00e1", "Neznámá"):
                        continue
                    cache_rows.append({
                        "bus_id": bid,
                        "spz": spz_v,
                        "linka": bc.get("line") or "",
                        "lat": bc.get("lat"),
                        "lng": bc.get("lng"),
                        "spz_verified": bc.get("spz_verified", False),
                        "admin_verified": bc.get("admin_spz_verified", False),
                        "trip_id": bc.get("trip_id"),
                        "color_class": bc.get("color_class"),
                        "status_text": bc.get("status"),
                        "admin_note": bc.get("admin_note", ""),
                        "admin_flag": bc.get("admin_flag", False),
                        "manual_spz": bc.get("manual_spz", False),
                        "updated_at": datetime.now(ZoneInfo("Europe/Prague")).isoformat(),
                    })
                if cache_rows:
                    try:
                        db_client.table("spz_cache").upsert(cache_rows).execute()
                    except Exception as e_flush:
                        print(f"[SPZ CACHE] Chyba pri zapisu: {e_flush}", flush=True)
                # Smaz zaznamy ktere uz nejsou aktivni
                active_ids = list(GLOBAL_BUS_CACHE.keys())
                if active_ids:
                    try:
                        db_client.table("spz_cache").delete().not_.in_("bus_id", active_ids).eq("admin_verified", False).execute()
                    except Exception:
                        pass

            time.sleep(10)

        except Exception as crash_error:
            import traceback
            err_str = f"Hlavni smycka selhala: {crash_error}\n{traceback.format_exc()}"
            try:
                sys_log(err_str)
            except Exception:
                print(f"[MAPA CRITICAL] {err_str}", flush=True)
            time.sleep(10)


def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()

# === FLASK ROUTES ===

def _full_page(title, body_html, is_map=False):
    extra = 'overflow:hidden;' if is_map else ''
    map_head = ""
    if is_map:
        map_head = """
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
  <style>
    *{margin:0;padding:0;box-sizing:border-box;}
    html,body{width:100%;height:100%;overflow:hidden;background:#0f172a;color:white;}
    #map-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;}
    #map{position:absolute;top:0;left:0;width:100%;height:100%!important;min-height:100vh;z-index:1;}
  
@keyframes routeDrawLoop {
  0% { stroke-dashoffset: var(--r-len); }
  65% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 0; }
}
</style>"""
    return Response(
        f"""<!DOCTYPE html>
<html style="background:#0f172a;">
<head>
<title>{title} | OIS IDPK</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{map_head}
</head>
<body style="background:#0f172a;color:white;{extra}margin:0;padding:0;">{body_html}</body>
</html>""", mimetype='text/html')


_AD_BTN_NORMAL = '<a href="/mapa_admin" class="n-btn n-ad">🔧 AD</a>'
_AD_BTN_ADMIN  = '<a href="/mapa" class="n-btn n-back">⬅️ Zp\u011bt</a>'


@mapa_bp.route('/mapa')
def stranka_mapa():
    html = HTML_MAPA.replace('__ADMIN_BANNER__', '').replace('__IS_ADMIN__', 'false').replace('__AD_BTN__', _AD_BTN_NORMAL)
    return _full_page("Mapa", html, is_map=True)


@mapa_bp.route('/mapa_admin')
def stranka_mapa_admin():
    if not session.get('logged_in'):
        return redirect('/dashboard')
    admin_banner = (
        '<div style="position:relative;margin-top:58px;padding:4px;text-align:center;">'
        '<span style="display:inline-block;background:rgba(56,189,248,0.1);color:#38bdf8;'
        'padding:3px 14px;border-radius:20px;font-size:11px;font-weight:bold;'
        'border:1px solid rgba(56,189,248,0.3);">Admin mapa \u2014 moderace zapnut\u00e1</span></div>'
    )
    html = HTML_MAPA.replace('__ADMIN_BANNER__', admin_banner).replace('__IS_ADMIN__', 'true').replace('__AD_BTN__', _AD_BTN_ADMIN)
    return _full_page("Admin Mapa", html, is_map=True)


@mapa_bp.route('/api/admin/map_action', methods=['POST'])
def api_admin_map_action():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    bus_id = str(data.get("bus_id", ""))

    if bus_id not in GLOBAL_BUS_CACHE:
        if action == "delete":
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Bus nenalezen v cache"})

    c = GLOBAL_BUS_CACHE[bus_id]

    if action == "delete":
        ADMIN_DELETED_BUSES[bus_id] = c.get("line", "")
        if bus_id in DEPOT_ACTIVE_SESSIONS:
            try:
                get_db_client().table("depot_history").update({"left_at": datetime.now(ZoneInfo("Europe/Prague")).isoformat()}).eq("id", DEPOT_ACTIVE_SESSIONS[bus_id]["id"]).execute()
            except: pass
            del DEPOT_ACTIVE_SESSIONS[bus_id]
            DEPOT_DISCORD_QUEUE.put({"type": "update_all"})
        del GLOBAL_BUS_CACHE[bus_id]

    elif action == "edit_spz":
        new_spz = str(data.get("spz", "")).strip()
        if new_spz:
            c["spz"] = new_spz
            c["spz_locked"] = True
            c["spz_verified"] = True
            c["manual_spz"] = True
            c["investigating"] = False

    elif action == "recheck_spz":
        c["spz_locked"] = False
        c["spz_verified"] = False
        c["spz"] = None
        c["manual_spz"] = False
        c["bug_locked"] = False   # Admin explicitne odemkl BUG-zamek
        c["spz_frozen"] = False   # Admin explicitne odemkl i tvrdy zamek po dojeti
        c["spz_last_audit_check"] = None
        c["investigating"] = False
        c["spz_stable_ticks"] = 0

    elif action == "edit_status":
        new_st = str(data.get("status", "")).strip()
        new_col = str(data.get("color_class", "")).strip()
        if new_st:
            c["status"] = new_st
            c["admin_status_override"] = new_st
            c["admin_lock_display"] = True
        if new_col and new_col not in ("", "\u2500\u2500"):
            c["color_class"] = new_col
            c["admin_color_override"] = new_col
            c["admin_lock_display"] = True

    elif action == "set_admin_flag":
        c["admin_flag"] = bool(data.get("flag", False))

    elif action == "edit_all":
        new_st = str(data.get("status", "")).strip()
        new_col = str(data.get("color_class", "")).strip()
        new_note = str(data.get("note", "")).strip()
        permanent = bool(data.get("permanent", False))
        if new_st:
            c["status"] = new_st
            c["admin_status_override"] = new_st
            c["admin_lock_display"] = True
        if new_col and new_col not in ("", "\u2500\u2500"):
            c["color_class"] = new_col
            c["admin_color_override"] = new_col
            c["admin_lock_display"] = True
        if new_note is not None:
            c["admin_note"] = new_note
        c["admin_lock_permanent"] = permanent

    elif action == "mark_bug":
        # Admin rucne oznaci bus jako "BUG / nestoji tu" - bude mit cerveny alert
        # ale SPZ se mu nesmazava (zustavaji videt kde byl naposledy)
        c["bug_locked"] = True
        c["color_class"] = "bg-bug"
        c["status"] = "BUG / Nerealna poloha (oznaceno adminem)"
        c["spz_frozen"] = True  # zamraz SPZ aby se nesmazala
        c["spz_conflict_warn"] = False  # admin to vedome oznacil, uz neni potreba duplikat alert
        if c.get("admin_spz_verified") or bus_id in ADMIN_SPZ_LOCKS:
            c["admin_spz_verified"] = False
            c["admin_spz_bug"] = True
            ADMIN_SPZ_LOCKS.pop(bus_id, None)

    elif action == "admin_verify_spz":
        # Absolutni admin lock - SPZ je overena adminem, automatikata prestane hledat
        if c.get("spz") and c["spz"] not in ("Nezn\u00e1m\u00e1", "Neznámá"):
            c["admin_spz_verified"] = True
            c["admin_flag"] = True
            c["spz_locked"] = True
            c["spz_frozen"] = True
            c["manual_spz"] = True
            c["spz_verified"] = True
            c["investigating"] = False
            c["bug_locked"] = False
            ADMIN_SPZ_LOCKS[bus_id] = {
                "spz": c["spz"],
                "admin_note": c.get("admin_note", ""),
                "color_class": c.get("color_class", "bg-darkblue")
            }
            # Okamzite zapsat do spz_cache s admin_verified=True
            try:
                _db_av = get_db_client()
                if _db_av:
                    _db_av.table("spz_cache").upsert({
                        "bus_id": bus_id,
                        "spz": c["spz"],
                        "linka": c.get("line") or "",
                        "lat": c.get("lat"),
                        "lng": c.get("lng"),
                        "spz_verified": True,
                        "admin_verified": True,
                        "trip_id": c.get("trip_id"),
                        "color_class": c.get("color_class"),
                        "status_text": c.get("status"),
                        "updated_at": datetime.now(ZoneInfo("Europe/Prague")).isoformat(),
                    }).execute()
            except Exception as e_av:
                print(f"[ADMIN-VERIFY] Chyba zapisu spz_cache: {e_av}", flush=True)
            print(f"[ADMIN-VERIFY] Bus {bus_id}: SPZ {c['spz']} overena adminem (absolutni lock)", flush=True)
        else:
            return jsonify({"status": "error", "message": "Nejdrive prirad SPZ, pak ji lze overit"})

    elif action == "admin_unverify_spz":
        # Odebrani admin locku - automatikata muze opet hledat
        c["admin_spz_verified"] = False
        c["manual_spz"] = False
        c["spz_frozen"] = False
        c["spz_locked"] = False
        c["spz_verified"] = False
        c["spz_3factor"] = False
        c["admin_flag"] = False
        c["spz_stable_ticks"] = 0
        
        ADMIN_SPZ_LOCKS.pop(bus_id, None)
        try:
            ADMIN_SPZ_LOCKS.pop(int(bus_id), None)
        except ValueError:
            pass
        try:
            _db_av = get_db_client()
            if _db_av:
                _db_av.table("spz_cache").update({"admin_verified": False}).eq("bus_id", bus_id).execute()
        except Exception as e_av:
            pass
        print(f"[ADMIN-VERIFY] Bus {bus_id}: Admin lock SPZ odebran", flush=True)

    elif action == "reset_admin":
        c["manual_spz"] = False
        c["admin_spz_verified"] = False
        c["spz_locked"] = False
        c["spz_verified"] = False
        c["spz_stable_ticks"] = 0
        c["spz_frozen"] = False
        c["spz_3factor"] = False
        c["spz_conflict_warn"] = False
        c["spz_last_audit_check"] = None
        c["investigating"] = False
        c["admin_color_override"] = None
        c["admin_status_override"] = None
        c["admin_flag"] = False
        c["bug_locked"] = False
        c["admin_lock_display"] = False
        c["admin_lock_permanent"] = False
        c["admin_note"] = ""
        c["color_class"] = "bg-gray"
        c["status"] = "Na\u010d\u00edt\u00e1n\u00ed..."
        c["admin_spz_bug"] = False
        c["admin_spz_conflict"] = False
        ADMIN_SPZ_LOCKS.pop(bus_id, None)
        try:
            _db_av = get_db_client()
            if _db_av:
                _db_av.table("spz_cache").update({"admin_verified": False}).eq("bus_id", bus_id).execute()
        except Exception as e_av:
            pass

    return jsonify({"status": "success"})


@mapa_bp.route('/api/admin/approve_conflict_spz', methods=['POST'])
def api_admin_approve_conflict_spz():
    if not current_user.is_authenticated:
        return jsonify({"status": "error", "message": "Neopravneny pristup"}), 401
        
    data = request.json or {}
    bus_id = data.get("bus_id")
    if not bus_id or bus_id not in GLOBAL_BUS_CACHE:
        return jsonify({"status": "error", "message": "Bus nenalezen"})
        
    c = GLOBAL_BUS_CACHE[bus_id]
    
    c["admin_spz_conflict"] = False
    c["admin_spz_verified"] = True
    c["manual_spz"] = True
    c["spz_locked"] = True
    c["spz_frozen"] = True
    c["admin_flag"] = True
    c["spz_verified"] = True
    
    # Save lock persistently
    spz = c.get("spz")
    ADMIN_SPZ_LOCKS[bus_id] = {
        "spz": spz,
        "color_class": c.get("color_class", "bg-darkblue"),
        "timestamp": get_prague_time(),
        "admin_note": c.get("admin_note", "")
    }
    
    # Okamzite zapsat do spz_cache s admin_verified=True
    try:
        _db_av = get_db_client()
        if _db_av:
            _db_av.table("spz_cache").upsert({
                "bus_id": bus_id,
                "spz": c.get("spz"),
                "linka": c.get("line") or "",
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "spz_verified": True,
                "admin_verified": True,
                "trip_id": c.get("trip_id"),
                "color_class": c.get("color_class"),
                "status_text": c.get("status"),
                "updated_at": datetime.now(ZoneInfo("Europe/Prague")).isoformat(),
            }).execute()
    except Exception as e_av:
        print(f"[ADMIN-VERIFY] Chyba zapisu spz_cache: {e_av}", flush=True)

    print(f"[ADMIN-VERIFY] Konflikt vyresen, Bus {bus_id} dostal SPZ lock", flush=True)
    return jsonify({"status": "success"})



@mapa_bp.route('/historie')
def stranka_historie_index():
    return _full_page("Historie", HTML_HISTORIE_INDEX)


@mapa_bp.route('/historie/<spz>')
def stranka_historie_detail(spz):
    return _full_page(f"V\u016fz {spz}", HTML_HISTORIE_DETAIL.replace('__SPZ__', spz))


@mapa_bp.route('/api/live_buses')
def api_live_buses():
    now = get_prague_time()
    uptime = (now - WORKER_START_TIME).total_seconds() if WORKER_START_TIME else 9999
    return jsonify({
        "status": "success", "server_time": now.strftime('%H:%M:%S'),
        "worker_uptime_seconds": round(uptime), "buses": LIVE_BUSES_DATA,
    })


@mapa_bp.route('/api/debug/gtfs')
def api_debug_gtfs():
    """Diagnosticky endpoint – zkontroluj po deployi ze GTFS funguje."""
    db_exists = os.path.exists(GTFS_DB_PATH)
    db_size = os.path.getsize(GTFS_DB_PATH) if db_exists else 0
    return jsonify({
        "gtfs_loaded": GTFS_LOADED,
        "stop_count": GTFS_STOP_CNT,
        "db_path": GTFS_DB_PATH,
        "db_exists": db_exists,
        "db_size_mb": round(db_size / 1024 / 1024, 2),
        "manual_overrides": len(STOP_OVERRIDES),
        "flagged_stops": len(CONFIDENCE_LOG),
    })


def _bbox_stops(south, west, north, east, max_cells=20000, max_stops=1500):
    """Spolecny pomocnik pro NT i verejny 'Zobrazit zastavky': vrati (list, None)
    s polozkami {key, name, lat, lon, mode, lines} pro zastavky uvnitr bboxu,
    nebo (None, chybova_zprava) pri prilis velkem vyrezu/poctu bodu.
    Zastavky se stejnym nazvem ALE RUZNYM MODEM (napr. Trpisty bus vs Trpisty vlak)
    se vracejí jako dva separatni zaznamy, protoze jsou fyzicky ruzna mista.

    DULEZITE: zahrnuje i RYZE RUCNE pridane zastavky z STOP_OVERRIDES, ktere
    v GTFS vubec nemaji zaznam (admin je vytvoril v NT rezimu pres tlacitko +).
    Bez tohohle by se takova zastavka nikdy nezobrazila na mape, protoze
    GTFS_GRID o ni neví - hledalo by se jen v GTFS datech."""
    if not GTFS_STOPS and not STOP_OVERRIDES:
        return None, "GTFS data nejsou na\u010dtena"
    lat_b0, lat_b1 = round(south / GTFS_GRID_SZ), round(north / GTFS_GRID_SZ)
    lon_b0, lon_b1 = round(west / GTFS_GRID_SZ), round(east / GTFS_GRID_SZ)
    if (lat_b1 - lat_b0 + 1) * (lon_b1 - lon_b0 + 1) > max_cells:
        return None, "V\u00fdb\u011br na map\u011b je moc velk\u00fd - p\u0159ibli\u017e si konkr\u00e9tn\u011bj\u0161\u00ed oblast"
    idxs = set()
    for la_b in range(lat_b0, lat_b1 + 1):
        for lo_b in range(lon_b0, lon_b1 + 1):
            idxs.update(GTFS_GRID.get((la_b, lo_b), ()))
    # Dedup: same name+mode at same coords -> one entry; same name+different mode -> two entries
    seen = {}  # (norm_name, mode_or_none) -> first seen entry
    results = []
    for idx in sorted(idxs):
        name, la, lo = GTFS_STOPS[idx]
        if not (south <= la <= north and west <= lo <= east):
            continue
        key = _norm_txt(name)
        md = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
        ln = GTFS_LINES[idx] if idx < len(GTFS_LINES) else []
        dedup_key = (key, md)
        if dedup_key not in seen:
            seen[dedup_key] = len(results)
            results.append({"key": key, "name": name, "lat": la, "lng": lo,
                            "mode": md, "lines": ln or []})
        else:
            # Merge lines for duplicate coords with same mode
            existing = results[seen[dedup_key]]
            merged = sorted(set(existing["lines"]) | set(ln or []))
            existing["lines"] = merged

    # Pridej rucne vytvorene zastavky bez GTFS protejsku (nove pres NT +)
    gtfs_dedup_keys = {(r["key"], r["mode"] or "bus") for r in results}
    for comp_key, ov in STOP_OVERRIDES.items():
        parts = comp_key.split('|', 1)
        base_key = parts[0]
        mode = parts[1] if len(parts) > 1 else ov.get("mode", "bus")
        if (base_key, mode) in gtfs_dedup_keys:
            continue  # uz pokryto pres GTFS zaznam vyse (override se aplikuje pozdeji v endpointu)
        la, lo = ov.get("lat"), ov.get("lng")
        if la is None or lo is None:
            continue
        if not (south <= la <= north and west <= lo <= east):
            continue
        results.append({
            "key": base_key, "name": ov.get("name") or base_key, "lat": la, "lng": lo,
            "mode": mode, "lines": ov.get("custom_lines") or [],
        })

    if len(results) > max_stops:
        return None, f"P\u0159\u00edli\u0161 mnoho zast\u00e1vek ve v\u00fdezu ({len(results)}) - p\u0159ibli\u017e si v\u00edc"
    return results, None


def _parse_bbox_args():
    try:
        return (float(request.args.get('south')), float(request.args.get('west')),
                float(request.args.get('north')), float(request.args.get('east')))
    except (TypeError, ValueError):
        return None


@mapa_bp.route('/api/admin/route_stops')
def api_admin_route_stops():
    """NT rezim: vrati zastavky v aktualnim vyrezu, kazda s efektivni
    polohou, mode (bus/train/mixed), lines, manual/flagged/approx/substitute."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    bbox = _parse_bbox_args()
    if not bbox:
        return jsonify({"status": "error", "message": "Chyb\u00ed/\u0161patn\u00e9 sou\u0159adnice v\u00fdezu"}), 400
    items, err = _bbox_stops(*bbox)
    if err:
        return jsonify({"status": "error", "message": err})

    stops_out = []
    for s in items:
        key = s["key"]
        gtfs_mode = s.get("mode")
        m_str = gtfs_mode or "bus"
        # OPRAVA: pouzij composite key s modem pro spravne rozliseni
        # bus vs train zastavky se stejnym nazvem
        ov = STOP_OVERRIDES.get(f"{key}|{m_str}")
        if not ov and m_str != "mixed":
            ov = STOP_OVERRIDES.get(f"{key}|mixed")
        eff_lat = ov["lat"] if ov else s["lat"]
        eff_lng = ov["lng"] if ov else s["lng"]
        # Linky: custom_lines (rucne nastavene) maji prednost pred GTFS
        eff_lines = ov["custom_lines"] if (ov and ov.get("custom_lines") is not None) else s.get("lines", [])
        eff_mode = (ov.get("mode") if ov else None) or gtfs_mode
        flag = CONFIDENCE_LOG.get(key)
        flagged = bool(flag and flag.get("confidence") in ("fuzzy", "geocoded", "none"))
        stops_out.append({
            "name": s["name"],
            "display_name": (ov.get("display_name") or "") if ov else "",
            "lat": eff_lat, "lng": eff_lng,
            "mode": eff_mode, "lines": eff_lines,
            "manual": bool(ov), "flagged": flagged,
            "approx": bool(ov and ov.get("approx")),
            "substitute": bool(ov and ov.get("substitute")),
        })

    return jsonify({"status": "success", "stops": stops_out, "count": len(stops_out)})


@mapa_bp.route('/api/stops_near')
def api_stops_near():
    """Vraci zastavky do dane vzdalenosti od bodu (v metrech).
    Zadny limit na pocet - nikdy nehazi 'oblast je prilis velka'."""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        radius_m = min(float(request.args.get('radius_m', 3000)), 10000)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Chybí lat/lng"}), 400

    if not GTFS_STOPS:
        return jsonify({"status": "error", "message": "GTFS data nejsou načtena"}), 503

    # Hledej pres GTFS_GRID - rychle, bez skenování vsech 67k zastavek
    pad_deg = radius_m / 100000  # hruba konverze: ~1.1 km/0.01 deg
    lat_b0 = round((lat - pad_deg) / GTFS_GRID_SZ)
    lat_b1 = round((lat + pad_deg) / GTFS_GRID_SZ)
    lon_b0 = round((lng - pad_deg) / GTFS_GRID_SZ)
    lon_b1 = round((lng + pad_deg) / GTFS_GRID_SZ)

    seen = {}
    for la_b in range(lat_b0, lat_b1 + 1):
        for lo_b in range(lon_b0, lon_b1 + 1):
            for idx in GTFS_GRID.get((la_b, lo_b), ()):
                name, la, lo = GTFS_STOPS[idx]
                d = haversine_m(lat, lng, la, lo)
                if d > radius_m:
                    continue
                key = _norm_txt(name)
                m = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
                m_str = m or "bus"
                ov = STOP_OVERRIDES.get(f"{key}|{m_str}") or STOP_OVERRIDES.get(f"{key}|mixed")
                eff_lat = ov["lat"] if ov else la
                eff_lng = ov["lng"] if ov else lo
                if key not in seen or d < seen[key]["_d"]:
                    seen[key] = {
                        "name": name,
                        "display_name": (ov.get("display_name") or "") if ov else "",
                        "lat": eff_lat, "lng": eff_lng,
                        "approx": bool(ov and ov.get("approx")),
                        "substitute": bool(ov and ov.get("substitute")),
                        "mode": GTFS_MODES[idx] if idx < len(GTFS_MODES) else None,
                        "lines": (ov.get("custom_lines") if ov and ov.get("custom_lines") is not None
                                  else (GTFS_LINES[idx] if idx < len(GTFS_LINES) else [])) or [],
                        "_d": d,
                    }

    stops = [{k: v for k, v in s.items() if k != "_d"} for s in
             sorted(seen.values(), key=lambda x: x["_d"])]
    return jsonify({"status": "success", "stops": stops, "count": len(stops)})


@mapa_bp.route('/api/stops_in_view')
def api_stops_in_view():
    """Verejny endpoint pro 'Zobrazit zastavky' + klik na zastávku = linky.
    DULEZITE: bus a vlak zastavky se stejnym nazvem jsou vráceny jako DVA
    separatni zaznamy (ruzna mista, ruzny mode) - nesmejí se mergeovat."""
    bbox = _parse_bbox_args()
    if not bbox:
        return jsonify({"status": "error", "message": "Chyb\u00ed/\u0161patn\u00e9 sou\u0159adnice v\u00fdezu"}), 400
    items, err = _bbox_stops(*bbox)
    if err:
        return jsonify({"status": "error", "message": err})

    stops_out = []
    for s in items:
        key = s["key"]
        # OPRAVA: pouzit mode z konkretniho zaznamu (bus NEBO train), ne fallback
        # na "bus" - jinak se bus a train zastavka se stejnym nazvem slouci do jedne
        gtfs_mode = s.get("mode")  # muze byt None, 'bus', 'train', 'mixed'
        m_str = gtfs_mode or "bus"
        # Hledej NT override pro TENTO konkretni rezim dopravy:
        ov = STOP_OVERRIDES.get(f"{key}|{m_str}")
        if not ov and m_str != "mixed":
            ov = STOP_OVERRIDES.get(f"{key}|mixed")
        eff_lat = ov["lat"] if ov else s["lat"]
        eff_lng = ov["lng"] if ov else s["lng"]
        eff_lines = ov["custom_lines"] if (ov and ov.get("custom_lines") is not None) else s.get("lines", [])
        # Efektivni mode: override muze menit mode (napr. bylo 'bus', admin
        # opravil na 'train') - pouzij override mode pokud existuje
        eff_mode = (ov.get("mode") if ov else None) or gtfs_mode
        stops_out.append({
            "name": s["name"],
            "display_name": (ov.get("display_name") or "") if ov else "",
            "lat": eff_lat, "lng": eff_lng,
            "mode": eff_mode, "lines": eff_lines,
            "approx": bool(ov and ov.get("approx")),
            "substitute": bool(ov and ov.get("substitute")),
        })

    return jsonify({"status": "success", "stops": stops_out, "count": len(stops_out)})

@mapa_bp.route('/api/admin/save_custom_route', methods=['POST'])
def api_admin_save_custom_route():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    data = request.get_json(silent=True) or {}
    route_key = str(data.get("route_key", "")).strip()
    points = data.get("points")
    if not route_key or not isinstance(points, list):
        return jsonify({"status": "error", "message": "Chybná data"}), 400
    CUSTOM_ROUTES[route_key] = {"coords": points, "waypoints": data.get("waypoints"), "segmentModes": data.get("segmentModes")} if data.get("waypoints") else points
    
    db = get_db_client()
    if db:
        try:
            db.table("custom_routes").upsert({
                "route_key": route_key,
                "points": json.dumps(CUSTOM_ROUTES[route_key], ensure_ascii=False),
                "updated_at": get_prague_time().isoformat(),
            }, on_conflict="route_key").execute()
            return jsonify({"status": "success", "message": "Trasa uložena do Supabase"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "DB nedostupná"}), 500

@mapa_bp.route('/api/admin/save_route_stop_override', methods=['POST'])
def api_admin_save_route_stop_override():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    data = request.get_json(silent=True) or {}
    prev_stop = str(data.get("prev_stop", "")).strip()
    this_stop = str(data.get("this_stop", "")).strip()
    next_stop = str(data.get("next_stop", "")).strip()
    lat = data.get("lat")
    lng = data.get("lng")
    if not this_stop or lat is None or lng is None:
        return jsonify({"status": "error", "message": "Chybná data"}), 400
    
    route_key = f"{_norm_txt(prev_stop)}|{_norm_txt(this_stop)}|{_norm_txt(next_stop)}"
    ROUTE_STOP_OVERRIDES[route_key] = {"lat": float(lat), "lng": float(lng)}
    
    db = get_db_client()
    if db:
        try:
            db.table("route_stop_overrides").upsert({
                "segment_key": route_key,
                "lat": float(lat), "lng": float(lng),
                "updated_at": get_prague_time().isoformat(),
            }, on_conflict="segment_key").execute()
            return jsonify({"status": "success", "message": "Zastávka upravena pro tento směr"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "DB nedostupná"}), 500

@mapa_bp.route('/api/admin/save_stop_override', methods=['POST'])
def api_admin_save_stop_override():
    """NT rezim: ulozi rucne opravenou zastavku natrvalo i do pameti.
    lat/lng jsou povinne jen pro novou zastavku (existujici lze updatovat
    jen flags/display_name/lines bez zmeny polohy)."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"status": "error", "message": "Chyb\u00ed n\u00e1zev zast\u00e1vky"}), 400

    mode = str(data.get("mode", "bus")).strip()
    key = f"{_norm_txt(name)}|{mode}"
    existing = STOP_OVERRIDES.get(key, {})

    # Souradnice - povinne jen pokud zaznam jeste neexistuje
    try:
        lat = float(data["lat"])
        lng = float(data["lng"])
    except (TypeError, ValueError, KeyError):
        if not existing:
            return jsonify({"status": "error", "message": "\u0160patn\u00e9 nebo chyb\u011bj\u00edc\u00ed sou\u0159adnice"}), 400
        lat = existing["lat"]
        lng = existing["lng"]

    approx = bool(data["approx"]) if "approx" in data else existing.get("approx", False)
    substitute = bool(data["substitute"]) if "substitute" in data else existing.get("substitute", False)
    display_name = str(data["display_name"]).strip() if "display_name" in data else existing.get("display_name", "")
    # custom_lines: None = zachovej GTFS, [] = zadne linky, [...] = konkretni linky
    if "custom_lines" in data:
        cl = data["custom_lines"]
        if cl is None or (isinstance(cl, list) and all(isinstance(x, str) for x in cl)):
            custom_lines = cl
        else:
            custom_lines = existing.get("custom_lines")
    else:
        custom_lines = existing.get("custom_lines")
        
    # mode uz mame vyse

    STOP_OVERRIDES[key] = {
        "lat": lat, "lng": lng, "name": name,
        "approx": approx, "substitute": substitute,
        "display_name": display_name,
        "custom_lines": custom_lines,
        "mode": mode
    }
    CONFIDENCE_LOG.pop(key, None)

    db = get_db_client()
    if db:
        try:
            db.table("stop_overrides").upsert({
                "stop_name": name, "lat": lat, "lng": lng,
                "approx": approx, "substitute": substitute,
                "display_name": display_name,
                "custom_lines": json.dumps(custom_lines, ensure_ascii=False) if custom_lines is not None else None,
                "mode": mode,
                "updated_at": get_prague_time().isoformat(),
            }).execute()
        except Exception as e:
            print(f"[NT] Chyba ukl\u00e1d\u00e1n\u00ed do DB: {e}", flush=True)

    return jsonify({"status": "success"})


@mapa_bp.route('/api/admin/delete_stop_override', methods=['POST'])
def api_admin_delete_stop_override():
    """NT rezim: vrati zastavku zpet na automaticky urcenou polohu (GTFS/Nominatim)."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    mode = str(data.get("mode", "bus")).strip()
    if not name:
        return jsonify({"status": "error", "message": "Chyb\u00ed n\u00e1zev zast\u00e1vky"}), 400
    key = f"{_norm_txt(name)}|{mode}"
    STOP_OVERRIDES.pop(key, None)
    db = get_db_client()
    if db:
        try:
            db.table("stop_overrides").delete().eq("stop_name", name).eq("mode", mode).execute()
        except Exception as e:
            print(f"[NT] Chyba maz\u00e1n\u00ed z DB: {e}", flush=True)
    return jsonify({"status": "success"})


@mapa_bp.route('/api/admin/assign_line_to_stop', methods=['POST'])
def api_admin_assign_line_to_stop():
    """NT: priradi linku k zastavce. Linka muze byt zadana jako kratky kod
    ('760') nebo plny ('490760') - ulozi se jako custom_lines.
    Pokud zastavka jeste nema override zaznam, vytvori se s aktualnimi
    GTFS souradnicemi (nebo chyba pokud zastavka v GTFS neni)."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    data = request.get_json(silent=True) or {}
    stop_name = str(data.get("stop_name", "")).strip()
    line_str = str(data.get("line", "")).strip()
    remove = bool(data.get("remove", False))
    mode = str(data.get("mode", "bus")).strip()
    if not stop_name or not line_str:
        return jsonify({"status": "error", "message": "Chyb\u00ed n\u00e1zev zast\u00e1vky nebo linky"}), 400

    key = f"{_norm_txt(stop_name)}|{mode}"
    ov = STOP_OVERRIDES.get(key)

    # Ziskej souradnice - z override nebo z GTFS
    if ov:
        lat, lng = ov["lat"], ov["lng"]
    else:
        coords, _ = _lookup_stop_coords(stop_name)
        if not coords:
            return jsonify({"status": "error", "message": f"Zast\u00e1vka '{stop_name}' nebyla nalezena v GTFS ani v NT. Nejprve ji p\u0159idej p\u0159es + tla\u010d\u00edtko."}), 404
        lat, lng = coords

    # Existujici linky
    custom_lines_exist = "custom_lines" in ov if ov else False
    if custom_lines_exist and ov["custom_lines"] is not None:
        cur_lines = list(ov["custom_lines"])
    else:
        # Zacni s GTFS linkami jako zakladem, pokud override vlastnich linek neni vubec definovan
        cur_lines = []
        idxs = GTFS_NAME_IDX.get(key, [])
        for idx in idxs:
            if idx < len(GTFS_LINES):
                cur_lines.extend(GTFS_LINES[idx] or [])
        cur_lines = list(dict.fromkeys(cur_lines))  # dedup

    if remove:
        cur_lines = [l for l in cur_lines if l != line_str and not l.endswith(line_str)]
    else:
        # Pridej linku pokud jeste neni (porovnej suffix i plny retezec)
        already = any(l == line_str or l.endswith(line_str) or line_str.endswith(l) for l in cur_lines)
        if not already:
            cur_lines.append(line_str)
        cur_lines = sorted(set(cur_lines))

    existing = ov or {}
    mode = existing.get("mode", "bus")
    
    STOP_OVERRIDES[key] = {
        "lat": lat, "lng": lng, "name": stop_name,
        "approx": existing.get("approx", False),
        "substitute": existing.get("substitute", False),
        "display_name": existing.get("display_name", ""),
        "custom_lines": cur_lines,
        "mode": mode
    }

    db = get_db_client()
    if db:
        try:
            db.table("stop_overrides").upsert({
                "stop_name": stop_name, "lat": lat, "lng": lng,
                "approx": STOP_OVERRIDES[key]["approx"],
                "substitute": STOP_OVERRIDES[key]["substitute"],
                "display_name": STOP_OVERRIDES[key]["display_name"],
                "custom_lines": json.dumps(cur_lines, ensure_ascii=False),
                "mode": mode,
                "updated_at": get_prague_time().isoformat(),
            }).execute()
        except Exception as e:
            print(f"[NT] Chyba ukl\u00e1d\u00e1n\u00ed linky: {e}", flush=True)

    action = "odebr\u00e1na" if remove else "p\u0159id\u00e1na"
    print(f"[NT] Linka {line_str} {action} k zast\u00e1vce '{stop_name}'. Linky: {cur_lines}", flush=True)
    return jsonify({"status": "success", "lines": cur_lines})


@mapa_bp.route('/api/admin/report_missing_stop', methods=['POST'])
def api_admin_report_missing_stop():
    """Backend-side logging of stops that route-builder couldn't locate.
    Frontend also logs these; this endpoint allows the worker to report them
    server-side so they persist across page reloads."""
    if not session.get('logged_in'):
        return jsonify({"status": "ok"})  # ticha chyba - neni kriticke
    data = request.get_json(silent=True) or {}
    stop_name = str(data.get("stop_name", "")).strip()
    bus_id = str(data.get("bus_id", "")).strip()
    if stop_name:
        print(f"[ROUTE-MISS] Zast\u00e1vka nenalezena: '{stop_name}' (bus {bus_id})", flush=True)
    return jsonify({"status": "ok"})


@mapa_bp.route('/api/admin/report_situace')
@mapa_bp.route('/api/lines_map')
def api_lines_map():
    """Verejny endpoint: vrati zastávky (s pořadím) pro filtrovane linky.
    Parametr q: prefix nebo cele cislo linky (napr. '490', '760', '490735').
    Vraci: {lines: {linka: [stops]}} kde kazdy stop ma name/lat/lng.
    Poradi zastávek je urceno sekvenci z JR (jizda po trase ze zapad na vychod
    nebo sever-jih, na zaklade heuristiky).
    POZNAMKA: pro kazde unikatni cislo linky se zastávky RADI metodou
    nejblizsiho souseda (nearest-neighbor) od prvniho bodu, cimz se ziskava
    priblizna ale vizualne smysluplna trasa bez nutnosti mit ulozene stop_times."""
    q = (request.args.get('q') or '').strip()
    if not GTFS_LOADED:
        return jsonify({'status': 'error', 'message': 'GTFS data nejsou načtena'}), 503

    # Normalizuj dotaz: "490735" -> hledej taky "735", "490735", "735" a "490" (zkraceni)
    # Cesty jake uzivatel zadava v PVVD (490735) vs jak jsou v GTFS (735)
    q_raw = q
    q_digits = re.sub(r'\D', '', q) if q else ''
    # Pokud uzivatel zadal dlouhe cislo (>=6 cifer), zkus taky posledni 3
    q_variants = set([q_digits])
    if len(q_digits) >= 6:
        q_variants.add(q_digits[-3:])  # 490735 -> 735
        q_variants.add(q_digits[-4:])  # 490735 -> 0735
    # Pokud zadal kratke cislo, zkus taky s prefixem (735 -> 490735) - matchuje oba
    q_variants = {v for v in q_variants if v}

    LAT_MIN, LAT_MAX = 49.2, 50.2
    LON_MIN, LON_MAX = 12.4, 13.8
    line_stops = {}
    for idx, ln_list in enumerate(GTFS_LINES):
        if not ln_list:
            continue
        name, la, lo = GTFS_STOPS[idx]
        key = _norm_txt(name)
        m = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
        m_str = m or "bus"
        ov = STOP_OVERRIDES.get(f"{key}|{m_str}") or STOP_OVERRIDES.get(f"{key}|mixed")
        eff_lat = ov['lat'] if ov else la
        eff_lng = ov['lng'] if ov else lo
        disp = (ov.get('display_name') or '') if ov else ''
        for l in ln_list:
            l_digits = re.sub(r'\D', '', l)
            # Filtruj: pokud q zadano, shoda prefixu ci sufixu
            if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
                continue
            if q_variants:
                # Match: linka odpovida kterekoliv varianté dotazu
                matched = any(
                    l_digits == v or l_digits.startswith(v) or v == l_digits or
                    (len(v) >= 3 and l_digits == v)
                    for v in q_variants
                )
                if not matched:
                    continue
            if l not in line_stops:
                line_stops[l] = []
            line_stops[l].append({'name': disp or name, 'lat': eff_lat, 'lng': eff_lng})

    line_stops = {l: s for l, s in line_stops.items() if len(s) >= 3}
    if len(line_stops) > 200:
        return jsonify({'status': 'error',
                        'message': f'Nalezeno {len(line_stops)} linek — zadej přesnější číslo (např. 490)'}), 400

    # Seřaď zastávky každé linky metodou nejbližšího souseda
    def sort_stops_nn(stops):
        if len(stops) <= 2:
            return stops
        # Začni od nejzápadnějšího bodu
        remaining = list(stops)
        remaining.sort(key=lambda s: s['lng'])
        ordered = [remaining.pop(0)]
        while remaining:
            last = ordered[-1]
            best = min(remaining, key=lambda s: (s['lat']-last['lat'])**2 + (s['lng']-last['lng'])**2)
            ordered.append(best)
            remaining.remove(best)
        return ordered

    result = {}
    for l, stops in line_stops.items():
        # Deduplikuj (stejný bod z více stop_id)
        seen = set()
        unique = []
        for s in stops:
            k = (round(s['lat'],4), round(s['lng'],4))
            if k not in seen:
                seen.add(k)
                unique.append(s)
        result[l] = sort_stops_nn(unique)

    return jsonify({'status': 'success', 'lines': result, 'count': len(result)})


def api_admin_report_situace():
    """Vrati posledni zaznamy z REPORT SITUACE bufferu (anomalie, duplikaty SPZ atd.)
    Volano frontendem pro zobrazeni v logu — založka REPORT SITUACE."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    limit = min(int(request.args.get("limit", 100)), 200)
    return jsonify({
        "status": "success",
        "entries": list(reversed(_REPORT_SITUACE[-limit:])),
        "total": len(_REPORT_SITUACE),
    })


@mapa_bp.route('/api/admin/system_logs')
def api_admin_system_logs():
    """Vrati zaznamy o kritickych chybach a padech ze systemu."""
    return jsonify({"status": "success", "logs": list(SYSTEM_LOGS)})

@mapa_bp.route('/api/admin/spz_debug')
def api_admin_spz_debug():
    """Vrati podrobny SPZ matching log (posledni zaznamy z _SPZ_DEBUG_LOG).
    Parametry:
      ?limit=N   - max pocet zaznamu (default 200, max 500)
      ?bus_id=X  - filtr na konkretni bus_id
      ?event=X   - filtr na typ eventu (napr. DUP_SPZ_DETECTED, SPZ_NO_MATCH, ...)
      ?spz=X     - filtr na konkretni SPZ
    """
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    limit = min(int(request.args.get("limit", 200)), 500)
    bus_id_filter = request.args.get("bus_id", "").strip()
    event_filter = request.args.get("event", "").strip().upper()
    spz_filter = request.args.get("spz", "").strip().upper()
    entries = list(reversed(_SPZ_DEBUG_LOG))
    if bus_id_filter:
        entries = [e for e in entries if str(e.get("bus_id", "")) == bus_id_filter]
    if event_filter:
        entries = [e for e in entries if event_filter in (e.get("event") or "").upper()]
    if spz_filter:
        entries = [e for e in entries if spz_filter in (e.get("spz") or "").upper()]
    return jsonify({
        "status": "success",
        "entries": entries[:limit],
        "total_in_buffer": len(_SPZ_DEBUG_LOG),
        "filters_applied": {
            "bus_id": bus_id_filter or None,
            "event": event_filter or None,
            "spz": spz_filter or None,
        },
    })


@mapa_bp.route('/api/admin/arriva_stats')
def api_admin_arriva_stats():
    """Vrati statistiky Arriva API fetche (OK/fail/empty pocty, posledni chyba).
    Pomaha zjistit zda Arriva API blokuje nebo vraci prazdne odpovedi."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    total = _arriva_fetch_stats["ok"] + _arriva_fetch_stats["fail"] + _arriva_fetch_stats["empty"]
    ok_pct = round(_arriva_fetch_stats["ok"] / total * 100, 1) if total > 0 else 0
    return jsonify({
        "status": "success",
        "stats": {
            "ok": _arriva_fetch_stats["ok"],
            "fail": _arriva_fetch_stats["fail"],
            "empty": _arriva_fetch_stats["empty"],
            "total": total,
            "ok_percent": ok_pct,
            "last_fail_reason": _arriva_fetch_stats.get("last_fail_reason"),
            "last_ok_bus_count": _arriva_fetch_stats.get("last_ok_cnt", 0),
        },
        "spz_debug_buffer_size": len(_SPZ_DEBUG_LOG),
        "active_buses": len(GLOBAL_BUS_CACHE),
    })


@mapa_bp.route('/api/admin/line_stops')
def api_admin_line_stops():
    """NT linka-editor: vrati vsechny zastavky pro dané číslo linky Z CELE GTFS DB,
    BEZ JAKEHOKOLI BBOXU. Pouziva GTFS_LINES pole (nacitane z DB), takze staci
    zadne sitove pozadavky, vsechno je v pameti.

    Hledani je flexibilni: '722' najde zastavky kde je linka '722', '490722'
    i '722' se berou jako ekvivalentni — porovna se suffix i cele cislo."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizov\u00e1no"}), 401
    line_q = (request.args.get("line") or "").strip()
    if not line_q:
        return jsonify({"status": "error", "message": "Chybi cislo linky"}), 400
    if not GTFS_LOADED:
        return jsonify({"status": "error", "message": "GTFS data nejsou nactena"}), 503

    # Normalizuj dotaz pro flexibilni porovnani
    q_norm = re.sub(r'\D', '', line_q)  # jen cislice

    matches = []
    seen_key = {}  # norm_name -> index do matches (pro deduplikaci)
    for idx, ln_list in enumerate(GTFS_LINES):
        if not ln_list:
            continue
        found = False
        for l in ln_list:
            l_norm = re.sub(r'\D', '', l)
            if l_norm == q_norm or l_norm.endswith(q_norm) or q_norm.endswith(l_norm):
                found = True
                break
        if not found:
            continue
        name, la, lo = GTFS_STOPS[idx]
        key = _norm_txt(name)
        m = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
        m_str = m or "bus"
        ov = STOP_OVERRIDES.get(f"{key}|{m_str}") or STOP_OVERRIDES.get(f"{key}|mixed")
        eff_lat = ov["lat"] if ov else la
        eff_lng = ov["lng"] if ov else lo
        eff_lines = (ov.get("custom_lines") if ov and ov.get("custom_lines") is not None else ln_list) or []
        md = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None

        if key in seen_key:
            # Stejna zastavka na jine nastupisté — jen sluc linky
            matches[seen_key[key]]["lines"] = sorted(set(matches[seen_key[key]]["lines"]) | set(eff_lines))
            continue
        seen_key[key] = len(matches)
        matches.append({
            "name": name,
            "display_name": (ov.get("display_name") or "") if ov else "",
            "lat": eff_lat, "lng": eff_lng,
            "mode": md, "lines": eff_lines,
            "manual": bool(ov),
            "approx": bool(ov and ov.get("approx")),
        })

    return jsonify({
        "status": "success",
        "stops": matches,
        "count": len(matches),
        "line_query": line_q,
    })


@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    try:
        cb = int(time.time() * 1000)
        hdr = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://pvvd.idpk.cz/'}
        info_html = ""
        try:
            with opener.open(urllib.request.Request(
                    f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb}", headers=hdr), timeout=4) as r:
                info_html = r.read().decode('utf-8')
        except Exception:
            pass
        tt_html = ""
        try:
            with opener.open(urllib.request.Request(
                    f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}",
                    headers=hdr), timeout=4) as r:
                tt_html = r.read().decode('utf-8')
        except Exception:
            tt_html = "<p style='color:#94a3b8;'>J\u0158 nen\u00ed dostupn\u00fd.</p>"
        return f"""<div style="background:#0f172a;color:white;font-family:sans-serif;">
<div style="background:#1e293b;padding:12px;border-radius:6px;margin-bottom:12px;">{info_html}</div>
<div style="overflow-x:auto;"><style>table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:6px 10px;text-align:left}}th{{background:#0f172a;color:#38bdf8}}tr:hover td{{background:#1e293b}}.current{{background:#166534!important;font-weight:bold}}
</style>{tt_html}</div></div>"""
    except Exception as e:
        return f"<p style='color:#ef4444;padding:20px;'>Chyba: {e}</p>"


@mapa_bp.route('/api/history_full')
def api_history_full():
    db = get_db_client()
    if not db:
        return jsonify({"data": [], "error": "DB nedostupn\u00e1"})
    try:
        res = db.table("bus_history").select("*").order("created_at", desc=True).limit(200).execute()
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)})


@mapa_bp.route('/api/history_spz/<spz>')
def api_history_spz(spz):
    db = get_db_client()
    if not db:
        return jsonify({"data": [], "depot_visits": [], "error": "DB nedostupna"})
    try:
        res = db.table("bus_history").select("*").eq("spz", spz).order("created_at", desc=True).limit(100).execute()
        depot_res = db.table("depot_history").select("*").eq("spz", spz).order("arrived_at", desc=True).limit(50).execute()
        return jsonify({"data": res.data, "depot_visits": depot_res.data or []})
    except Exception as e:
        return jsonify({"data": [], "depot_visits": [], "error": str(e)})

# === ROUTE BACKEND (GTFS in-memory + Nominatim fallback per zastavku) ===

def _geocode_stop(stop_name, anchor=None, max_anchor_dist_m=20000):
    """Nominatim geocoding - fallback pro zastavky ktere GTFS nema.
    `anchor` (lat, lon) - pokud zadan, preferuje vysledek nejblizsi anchoru
    misto pevneho stredu Plzne (presnejsi pro trasy mimo Plzensky kraj).
    Pokud i nejblizsi vysledek je dal nez `max_anchor_dist_m`, povazuje se
    za nedukazpodobnou shodu a vrati se None - radsi chybejici tecka nez
    spatne umistena (napr. uplne jine mesto se shodnym nazvem ulice/objektu)."""
    key = (stop_name.strip().lower(), anchor)
    if key in _stop_geo_cache:
        return _stop_geo_cache[key]
    ref_lat, ref_lon = anchor if anchor else (49.74, 13.37)
    try:
        bbox = "viewbox=11.8%2C50.5%2C14.1%2C49.1&bounded=1"
        q = _uparse.quote(stop_name)
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=3&countrycodes=cz&{bbox}"
        req = urllib.request.Request(url, headers={"User-Agent": "OIS-IDPK/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as r:
            res = json.loads(r.read().decode())
        if res:
            best = min(res, key=lambda x: haversine_m(ref_lat, ref_lon, float(x["lat"]), float(x["lon"])))
            d = haversine_m(ref_lat, ref_lon, float(best["lat"]), float(best["lon"]))
            if d > max_anchor_dist_m:
                _stop_geo_cache[key] = None
                return None
            coords = (float(best["lat"]), float(best["lon"]))
            _stop_geo_cache[key] = coords
            return coords
    except Exception:
        pass
    _stop_geo_cache[key] = None
    return None


def _fetch_tt_stops(bus_id):
    stop_names, stop_times, current_idx = [], [], 0
    try:
        cb = int(time.time() * 1000)
        hdr = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://pvvd.idpk.cz/'}
        url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}"
        with opener.open(urllib.request.Request(url, headers=hdr), timeout=5) as r:
            tt = r.read().decode("utf-8")
        import html as _html
        for row_m in re.finditer(r'<tr[^>]*>(.*?)</tr>', tt, re.DOTALL | re.IGNORECASE):
            cells = [re.sub(r'<[^>]+>', '', x).strip()
                     for x in re.findall(r'<td[^>]*>(.*?)</td>', row_m.group(1), re.DOTALL | re.IGNORECASE)]
            if cells and cells[0] and len(cells[0]) > 1:
                stop_names.append(_html.unescape(cells[0]))
                stop_times.append(cells[1] if len(cells) > 1 else "")
        cur_matches = re.findall(r"""class=["'"]current["'"][^>]*>.*?<td[^>]*>(.*?)</td>""", tt, re.DOTALL | re.IGNORECASE)
        if cur_matches:
            cur = re.sub(r'<[^>]+>', '', cur_matches[0]).strip()
            for i, s in enumerate(stop_names):
                if s.lower() == cur.lower():
                    current_idx = i
                    break
    except Exception as e:
        print(f"[ROUTE] JR fetch chyba: {e}")
    return stop_names, stop_times, current_idx


@mapa_bp.route('/api/bus_route/<bus_id>')
def api_bus_route(bus_id):
    """Vrati seznam zastavek s GPS pro vykresleni trasy na mape.

    Opravena verze: pouziva GTFS in-memory index (nacten pri startu) pro kazdou
    zastavku, s fallbackem na Nominatim jen pro zastavky ktere GTFS nema.

    DULEZITA OPRAVA presnosti: stejny nazev zastavky existuje v GTFS databazi
    casto vicekrat napric celou CR (napr. "Nova Ves" 24x v ruznych mestech).
    Aby se vzdy vybrala ta spravna (na trase tohoto busu, ne nahodne nekde
    jinde v republice), se pouziva geograficka "kotva" (anchor), ktera se
    postupne posouva podel trasy: zacina na aktualni poloze busu a po kazde
    uspesne najdene zastavce se presune na jeji souradnice. Diky tomu zustava
    vyber zastavek geograficky souvisly misto skakani po cele CR.

    DVOUFAZOVE RESENI KVULI RYCHLOSTI:
    1) Sekvencni GTFS pruchod (rychly, bez site) - drzi spravne navazujici
       anchor retezeni pro presnost.
    2) Zastavky, ktere GTFS nenasel, se hledaji pres Nominatim VSECHNY
       NAJEDNOU paralelne (thread pool) - misto jedna po druhe. Tohle byl
       hlavni duvod proc hledani trasy trvalo dlouho (kazdy Nominatim dotaz
       az 2.5s, sekvencne se to scitalo).

    Kazda zastavka v odpovedi nese "confidence": "manual" (rucne opraveno v NT
    rezimu - nejjistejsi), "exact" (presna shoda nazvu), "fuzzy" (shoda podle
    prekryvu slov - o neco mene jista), "geocoded" (dohledano pres Nominatim -
    nejmene presne) nebo "none" (nenalezeno). Frontend muze "fuzzy"/"geocoded"
    zvyraznit jinak, at je videt, ktere body trasy jsou jistejsi a ktere je
    radno brat s rezervou.
    """
    c = GLOBAL_BUS_CACHE.get(bus_id)
    if not c:
        return jsonify({"stops": [], "error": "Bus nenalezen"})

    stop_names, stop_times, current_idx = _fetch_tt_stops(bus_id)
    if not stop_names:
        return jsonify({"stops": [], "error": "Zastavky nenalezeny v JR PVVD"})

    result = [None] * len(stop_names)
    seen = {}
    pending = []  # (index, name_c, anchor_v_danou_chvili) - pro Nominatim fallback
    anchor = (c.get("lat"), c.get("lng")) if c.get("lat") and c.get("lng") else None
    bus_mode = "train" if c.get("is_train") else "bus"

    # ── PASS 1: sekvencni GTFS pruchod s anchor retezenim ───────────────────
    for i, (name, t) in enumerate(zip(stop_names, stop_times)):
        name_c = name.strip()

        if name_c in seen:
            prev_lat, prev_lng = seen[name_c]
            result[i] = {
                "name": name_c, "time": t,
                "lat": (prev_lat + 0.00002 * (i % 4 + 1)) if prev_lat else None,
                "lng": prev_lng,
                "passed": i < current_idx,
                "confidence": "dup",
            }
            continue

        coords, conf = (None, None)
        if GTFS_LOADED or STOP_OVERRIDES:
            coords, conf = _lookup_stop_coords(name_c, anchor=anchor, bus_mode=bus_mode)

        if coords:
            seen[name_c] = coords
            anchor = coords
            ov = STOP_OVERRIDES.get(f"{_norm_txt(name_c)}|{bus_mode}") or STOP_OVERRIDES.get(f"{_norm_txt(name_c)}|mixed")
            result[i] = {"name": name_c, "time": t, "lat": coords[0], "lng": coords[1],
                         "passed": i < current_idx, "confidence": conf,
                         "display_name": (ov.get("display_name") if ov else "") or ""}
        else:
            pending.append((i, name_c, anchor, t))

    # ── PASS 2: zbyle zastavky pres Nominatim - VSECHNY NAJEDNOU paralelne ──
    if pending:
        def resolve(item):
            idx, name_c, anch, t = item
            coords = _geocode_stop(name_c, anchor=anch)
            return idx, name_c, t, coords

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for idx, name_c, t, coords in pool.map(resolve, pending):
                if coords:
                    seen[name_c] = coords
                result[idx] = {
                    "name": name_c, "time": t,
                    "lat": coords[0] if coords else None,
                    "lng": coords[1] if coords else None,
                    "passed": idx < current_idx,
                    "confidence": "geocoded" if coords else "none",
                }

    # Zaznamenej jistotu kazde zastavky - NT rezim podle tohoto zvyrazni
    # "podezrele" body (fuzzy/geocoded/none), at je admin nemusi hledat
    # proklikavanim kazde trasy zvlast. Zaroven pripoj approx/substitute
    # priznaky (pokud byly v NT rezimu rucne nastaveny), at je videt i
    # primo v zobrazene trase, ne jen v samostatnem "Zobrazit zastavky".
    for s in result:
        if not (s and s.get("name")):
            continue
        key = _norm_txt(s["name"])
        ov = STOP_OVERRIDES.get(f"{key}|{bus_mode}") or STOP_OVERRIDES.get(f"{key}|mixed")
        s["approx"] = bool(ov and ov.get("approx"))
        s["substitute"] = bool(ov and ov.get("substitute"))
        if s.get("confidence") not in (None, "dup"):
            CONFIDENCE_LOG[key] = {"confidence": s["confidence"], "name": s["name"]}

    gtfs_hits = sum(1 for s in result if s["confidence"] == "exact")
    fuzzy_hits = sum(1 for s in result if s["confidence"] == "fuzzy")
    nominatim_hits = sum(1 for s in result if s["confidence"] == "geocoded")
    found = sum(1 for s in result if s["lat"])
    print(f"[ROUTE] Bus {bus_id}: {found}/{len(result)} zastavek "
          f"(presne:{gtfs_hits} fuzzy:{fuzzy_hits} nominatim:{nominatim_hits})", flush=True)

    custom_shape = None
    custom_shape_full = None
    route_key = None
    if result and c.get('line'):
        route_key = f"{c.get('line')}_{result[0]['name']}_{result[-1]['name']}"
        if route_key in CUSTOM_ROUTES:
            raw_shape = CUSTOM_ROUTES[route_key]
            if isinstance(raw_shape, dict):
                custom_shape_full = raw_shape
                custom_shape = raw_shape.get("coords", [])
            else:
                custom_shape = raw_shape
                custom_shape_full = {"coords": raw_shape, "waypoints": [], "segmentModes": {}}
        for i, s in enumerate(result):
            if not (s and s.get("name")):
                continue
            prev_s = result[i-1]["name"] if i > 0 and result[i-1] else ""
            next_s = result[i+1]["name"] if i < len(result)-1 and result[i+1] else ""
            segment_key = f"{_norm_txt(prev_s)}|{_norm_txt(s['name'])}|{_norm_txt(next_s)}"
            if segment_key in ROUTE_STOP_OVERRIDES:
                ovr = ROUTE_STOP_OVERRIDES[segment_key]
                s["lat"] = ovr["lat"]
                s["lng"] = ovr["lng"]

    return jsonify({
        "stops": result,
        "bus_id": bus_id,
        "found": found,
        "total": len(result),
        "gtfs_hits": gtfs_hits,
        "fuzzy_hits": fuzzy_hits,
        "nominatim_hits": nominatim_hits,
        "custom_shape": custom_shape,
        "custom_shape_full": custom_shape_full,
        "route_key": route_key if result and c.get('line') else None
    })



# === VOZOVNY (DEPOT ZONES) ===

@mapa_bp.route('/api/depot_zones')
def api_depot_zones():
    """Verejny endpoint: vrati vsechny vozovny (polygon, nazev, barva)
    + aktualni pocet busu v kazde vozovne."""
    zones_out = []
    for zone in DEPOT_ZONES:
        # Spocitej busy v teto vozovne
        buses_in_dict = {}
        for bid, bc in GLOBAL_BUS_CACHE.items():
            if bc.get("_in_depot") and bc.get("_depot_name") == zone["name"]:
                spz = bc.get("spz") or "Neznámá"
                if bc.get("color_class") == "bg-bug":
                    continue
                dict_key = bid if spz in ("Nezn\u00e1m\u00e1", "Neznámá") else spz
                if dict_key not in buses_in_dict:
                    arrived_at = None
                    is_imprecise = False
                    session_id = None
                    if bid in DEPOT_ACTIVE_SESSIONS:
                        arrived_at = DEPOT_ACTIVE_SESSIONS[bid]["arrived_at"]
                        is_imprecise = DEPOT_ACTIVE_SESSIONS[bid]["is_imprecise"]
                        session_id = DEPOT_ACTIVE_SESSIONS[bid]["id"]
                        
                    buses_in_dict[dict_key] = {
                        "id": bid,
                        "session_id": session_id,
                        "spz": spz,
                        "line": bc.get("line") or "",
                        "spz_verified": bc.get("spz_verified", False),
                        "arrived_at": arrived_at,
                        "is_imprecise": is_imprecise
                    }
        
        buses_in = list(buses_in_dict.values())
        zones_out.append({
            "id": zone["id"],
            "name": zone["name"],
            "polygon": zone["polygon"],
            "color": zone.get("color", "#facc15"),
            "bus_count": len(buses_in),
            "buses": buses_in,
        })
    return jsonify({"status": "success", "zones": zones_out, "count": len(zones_out)})

@mapa_bp.route('/api/depot_history')
def api_depot_history():
    """Vrati historii odjetych busu z vozovny."""
    depot_name = request.args.get('depot_name')
    search_q = request.args.get('q', '').strip().lower()
    sort_dir = request.args.get('sort', 'desc').strip()
    
    db = get_db_client()
    if not db:
        return jsonify({"status": "error", "message": "DB nedostupna"})
        
    query = db.table("depot_history").select("*").eq("depot_name", depot_name)
    if search_q:
        query = query.ilike("spz", f"%{search_q}%")
        
    is_desc = sort_dir == 'desc'
    res = query.order("arrived_at", desc=is_desc).limit(500).execute()
    return jsonify({"status": "success", "data": res.data or []})

@mapa_bp.route('/api/admin/delete_depot_history', methods=['POST'])
def api_admin_delete_depot_history():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizovano"}), 401
    
    data = request.get_json(silent=True) or {}
    record_id = data.get("id")
    if not record_id:
        return jsonify({"status": "error", "message": "Chybi ID"}), 400
        
    db = get_db_client()
    if not db:
        return jsonify({"status": "error", "message": "DB nedostupna"}), 500
        
    try:
        db.table("depot_history").delete().eq("id", record_id).execute()
        # Take to zmaz z pameti pokud je to aktivni
        for s_spz, s_data in list(DEPOT_ACTIVE_SESSIONS.items()):
            if s_data["id"] == record_id:
                del DEPOT_ACTIVE_SESSIONS[s_spz]
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@mapa_bp.route('/api/admin/save_depot_zone', methods=['POST'])
def api_admin_save_depot_zone():
    """Admin: ulozi nebo aktualizuje vozovnu (depot zone)."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    polygon = data.get("polygon")
    color = str(data.get("color", "#facc15")).strip()
    zone_id = data.get("id")

    if not name:
        return jsonify({"status": "error", "message": "Chybí název vozovny"}), 400
    if not polygon or not isinstance(polygon, list) or len(polygon) < 3:
        return jsonify({"status": "error", "message": "Polygon musí mít aspoň 3 body"}), 400

    db = get_db_client()
    if not db:
        return jsonify({"status": "error", "message": "DB nedostupná"}), 500
    try:
        row = {
            "name": name,
            "polygon": polygon,
            "color": color,
            "updated_at": get_prague_time().isoformat(),
        }
        try:
            if zone_id:
                row["id"] = zone_id
                db.table("depot_zones").upsert(row, on_conflict="id").execute()
            else:
                res = db.table("depot_zones").insert(row).execute()
                zone_id = res.data[0]["id"] if res.data else None
        except Exception as e:
            err_str = str(e)
            if "color" in err_str or "PGRST204" in err_str:
                print(f"[DEPOT WARN] Sloupec 'color' asi chybí v DB. Přidej: ALTER TABLE depot_zones ADD COLUMN color TEXT DEFAULT '#facc15'; Ukladam bez barvy.", flush=True)
                row_fallback = {k: v for k, v in row.items() if k != "color"}
                if zone_id:
                    db.table("depot_zones").upsert(row_fallback, on_conflict="id").execute()
                else:
                    res = db.table("depot_zones").insert(row_fallback).execute()
                    zone_id = res.data[0]["id"] if res.data else None
            else:
                raise e

        # Aktualizuj v pameti
        for z in DEPOT_ZONES:
            if str(z["id"]) == str(zone_id):
                z["name"] = name
                z["polygon"] = polygon
                z["color"] = color
                break
        else:
            DEPOT_ZONES.append({"id": zone_id, "name": name, "polygon": polygon, "color": color})

        print(f"[DEPOT] Ulozena vozovna '{name}' ({len(polygon)} bodu)", flush=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@mapa_bp.route('/api/admin/delete_depot_zone', methods=['POST'])
def api_admin_delete_depot_zone():
    """Admin: smaze vozovnu podle id."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    data = request.get_json(silent=True) or {}
    zone_id = data.get("id")
    if not zone_id:
        return jsonify({"status": "error", "message": "Chybí id vozovny"}), 400
    db = get_db_client()
    if db:
        try:
            db.table("depot_zones").delete().eq("id", zone_id).execute()
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    global DEPOT_ZONES
    DEPOT_ZONES[:] = [z for z in DEPOT_ZONES if str(z["id"]) != str(zone_id)]
    print(f"[DEPOT] Smazana vozovna id={zone_id}", flush=True)
    return jsonify({"status": "success"})
