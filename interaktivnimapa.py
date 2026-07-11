import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse as _uparse
import threading
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
SPZ_HIGH_CONFIDENCE_DIST_M = 300  # jednoznacny + blizky zasah = zamek hned, bez cekani na 2. tik
SPZ_REAUDIT_INTERVAL_SEC = 60      # jak casto preverovat UZ overenou (fajfka) SPZ - nizsi priorita nez hledani neoverenych
GHOST_MAX_OFFLINE_MIN = 20
GHOST_DIST_STRICT     = 0.010
DUPLICATE_GRACE_SEC   = 120

# Cesta k GTFS db relativne k tomuto souboru (spolehlivejsi nez working dir)
GTFS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtfs_stops.db")

# Tolerance pro parovani SPZ v metrech (presnejsi nez stupne)
ARRIVA_MATCH_DIST_M = 750   # max vzdalenost PVVD pozice od Arriva pozice same SPZ
ARRIVA_STOP_MATCH_M = 400   # max vzdalenost k nejblizsi GTFS zastavce pro krizovou kontrolu

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
      <option value="">Vsechny stavy</option><option value="Probiha">Probiha</option><option value="depo">V depu</option><option value="Ukonceno">Ukonceno</option>
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
    <tbody id="historyTableBody"><tr><td colspan="6" style="text-align:center;padding:30px;color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Nacitam...</td></tr></tbody>
  </table>
</div>
<p style="color:#64748b;font-size:11px;margin-top:8px;">* Neomezena historie. Aktualizace kazdych 10s.</p>
<script>
let allData=[];
function buildFreqMap(data){const f={};data.forEach(r=>{const spz=r.spz||'Neznama';if(spz==='Neznama')return;const lb=(r.linka||'').replace(/[/].*/g,'').trim().replace(/[^0-9]/g,'');f[spz+'_'+lb]=(f[spz+'_'+lb]||0)+1;});return f;}
function renderStats(data){
  const ss=new Set(data.filter(r=>r.spz&&r.spz!=='Neznama').map(r=>r.spz));
  const total=data.length,active=data.filter(r=>!r.end_actual&&!r.status?.includes('Timeout')&&!r.status?.includes('depu')).length,depot=data.filter(r=>r.status?.includes('depu')||r.status?.includes('Vozovn')).length;
  document.getElementById('statsBar').innerHTML=`
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#38bdf8;font-size:22px;font-weight:900;">${total}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📋 Zaznamu</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#f59e0b;font-size:22px;font-weight:900;">${ss.size}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🚌 Unikatnich SPZ</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#10b981;font-size:22px;font-weight:900;">${active}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📡 Probiha</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#64748b;font-size:22px;font-weight:900;">${depot}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🏢 V depu</div></div>`;
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
      const lb=linka.replace(/[/].*/,'').trim().replace(/[^0-9]/g,'');
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
        <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${dayStr}<br><span style="color:#475569;font-size:10px;">${(row.trip_id||'').substring(0,10)}...</span></td>
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
loadIndex();setInterval(loadIndex,10000);
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
  <div id="absoluteLastPos"><span style="color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Nacitam...</span></div>
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
  }catch(e){console.error(e);}
}
loadDetail();setInterval(loadDetail,10000);
</script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
"""

HTML_MAPA = """
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100%;height:100%;overflow:hidden;background:#0f172a;}
#map-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;}
#map{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;}
#panel-zone{position:fixed;top:0;left:0;right:0;height:40px;z-index:3000;pointer-events:none;}
#top-nav{position:fixed;top:-72px;left:0;right:0;height:58px;background:rgba(8,16,30,0.97);border-bottom:1px solid #334155;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);z-index:2999;transition:top 0.3s cubic-bezier(.4,0,.2,1);display:flex;align-items:center;padding:0 14px;gap:10px;box-shadow:0 4px 24px rgba(0,0,0,0.7);}
#top-nav.vis{top:0;}
.n-logo{display:flex;align-items:center;text-decoration:none;flex-shrink:0;}
.n-logo img{height:32px;width:auto;filter:drop-shadow(0 0 7px rgba(56,189,248,.55));}
.n-title{flex-shrink:0;line-height:1.2;}.n-title .a{color:#38bdf8;font-size:14px;font-weight:800;}.n-title .b{color:#64748b;font-size:10px;}
.n-warn{background:#f59e0b;color:#0f172a;padding:3px 8px;border-radius:5px;font-size:10px;font-weight:bold;white-space:nowrap;flex-shrink:0;}
.n-sp{flex:1;}
.n-clock{color:#38bdf8;font-size:12px;font-weight:bold;background:rgba(56,189,248,.08);padding:4px 8px;border-radius:6px;border:1px solid #334155;white-space:nowrap;flex-shrink:0;}
.n-btn{padding:5px 10px;border-radius:6px;font-weight:bold;text-decoration:none;font-size:12px;flex-shrink:0;white-space:nowrap;transition:.2s;}
.n-home{background:#38bdf8;color:#0f172a;}.n-home:hover{background:#0284c7;color:#fff;}
.n-provoz{background:#334155;color:#fff;}.n-provoz:hover{background:#475569;}
.n-ad{background:#1e3a5f;color:#38bdf8;border:1px solid #334155;font-size:11px;padding:4px 8px;}.n-ad:hover{background:#1e40af;color:#fff;}
.n-back{background:#ef4444;color:#fff;font-size:11px;padding:4px 8px;}.n-back:hover{background:#dc2626;}
/* Výrazné tlačítko "Zobrazit zastávky" - prominentní pro veřejnost */
#pub-stops-btn{background:linear-gradient(135deg,#0ea5e9,#38bdf8);color:#0f172a;border:none;padding:7px 14px;border-radius:8px;font-weight:800;font-size:13px;cursor:pointer;flex-shrink:0;white-space:nowrap;box-shadow:0 2px 8px rgba(56,189,248,.4);transition:.2s;}
#pub-stops-btn:hover{background:linear-gradient(135deg,#0284c7,#0ea5e9);box-shadow:0 3px 14px rgba(56,189,248,.6);}
#pub-stops-btn.active{background:#f59e0b;color:#0f172a;box-shadow:0 2px 8px rgba(245,158,11,.5);}
#nav-handle{position:fixed;top:0;left:50%;transform:translateX(-50%);width:90px;height:7px;background:rgba(56,189,248,.55);border-radius:0 0 8px 8px;z-index:3001;cursor:pointer;transition:opacity .3s,background .2s,width .2s;}
#nav-handle:hover{background:rgba(56,189,248,.95);width:130px;}
#nav-handle.hid{opacity:0;pointer-events:none;}
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
#sw{display:none;position:fixed;top:68px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#991b1b,#ef4444);color:#fff;padding:11px 18px;border-radius:10px;font-weight:bold;z-index:5000;text-align:center;max-width:92vw;width:410px;animation:swPulse 2s ease-in-out infinite alternate;}
@keyframes swPulse{0%{box-shadow:0 4px 20px rgba(239,68,68,.4);}100%{box-shadow:0 4px 45px rgba(239,68,68,.9);}}
#ttm{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.72);z-index:6000;align-items:center;justify-content:center;}
#ttm.open{display:flex;}
#ttb{background:#0f172a;border-radius:10px;padding:20px;max-width:700px;width:95%;border:1px solid #38bdf8;max-height:86vh;overflow-y:auto;position:relative;}
#ttc-btn{position:absolute;top:10px;right:10px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;font-weight:bold;}
#spz-results .sr-item{padding:8px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:8px;}
#spz-results .sr-item:hover{background:#334155;}
.route-line-future{stroke-dasharray:14 10;animation:routeFlow 0.9s linear infinite;stroke-linecap:round;}
@keyframes routeFlow{to{stroke-dashoffset:-24;}}
@keyframes routePulse{0%,100%{box-shadow:0 0 0 0 rgba(56,189,248,.8),0 2px 6px rgba(0,0,0,.5);}50%{box-shadow:0 0 0 8px rgba(56,189,248,0),0 2px 6px rgba(0,0,0,.5);}}
.route-line-past{stroke-linecap:round;}
.nt-dot{width:14px;height:14px;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.6);cursor:grab;box-sizing:border-box;}
.nt-dot-normal{background:#38bdf8;border:2px solid white;}
.nt-dot-manual{background:#10b981;border:2px solid white;}
.nt-dot-flagged{background:#f59e0b;border:2px solid #fff;animation:ntPulse 1.2s ease-in-out infinite;}
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
#log-body{max-height:240px;overflow-y:auto;padding:8px 12px;font-family:monospace;font-size:10.5px;color:#94a3b8;line-height:1.5;}
#log-body .lg-err{color:#f87171;}
#log-body .lg-warn{color:#fbbf24;}
#log-body .lg-ok{color:#34d399;}
@media(max-width:768px){
  #top-nav{gap:4px;padding:0 5px;height:auto;min-height:50px;flex-wrap:wrap;padding-bottom:5px;padding-top:5px;}
  .n-title,.n-warn{display:none;}
  .n-clock{font-size:10px;padding:3px 5px;}
  .n-btn{font-size:10px;padding:4px 7px;}
  #pub-stops-btn{font-size:11px;padding:5px 10px;}
  #spz-search-inp{width:80px;font-size:11px;}
  #hf{width:200px;}
  .dark-popup .leaflet-popup-content{width:240px!important;}
  #log-panel{bottom:auto;top:56px;right:4px;left:4px;width:auto;max-width:100vw;}
  #log-body,#log-errors-body,#log-spz-body,#log-missing-body{max-height:160px;}
  #nt-edit-pop{left:4px;right:4px;bottom:10px;width:auto;max-height:80vh;overflow-y:auto;}
  #stop-info-pop{left:4px;right:4px;bottom:10px;width:auto;}
  .sip-lines{flex-wrap:wrap;gap:3px;}
  .lp-h div{gap:2px;flex-wrap:wrap;}
  .lp-h div button{font-size:10px;padding:2px 5px;}
  #nt-add-bar{left:4px;right:4px;transform:none;flex-wrap:wrap;gap:5px;}
}
@media(max-width:420px){
  .n-provoz{display:none;}
  #spz-search-inp{width:65px;font-size:10px;}
  #nt-toggle-btn,#nt-add-btn,#log-toggle-btn{font-size:11px;padding:4px 6px;}
  #pub-stops-btn{font-size:10px;padding:4px 9px;}
}
</style>

<div id="map-wrap">
  <div id="panel-zone"></div>
  <div id="nav-handle" title="Klikni pro zobrazeni navigace"></div>
  <nav id="top-nav">
    <a href="https://datacorebot.koyeb.app/" class="n-logo">
      <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png" alt="OIS IDPK">
    </a>
    <!-- Výrazné tlačítko Zobrazit zastávky - první, pro veřejnost -->
    <button id="pub-stops-btn" onclick="togglePubStops()">🚏 Zastávky</button>
    <a href="/provoz-idpk" class="n-btn n-provoz">IDPK</a>
    <a href="https://datacorebot.koyeb.app/" class="n-btn n-home">🏠</a>
    <div class="n-sp"></div>
    <div id="admin-mode-badge" style="display:none;background:rgba(56,189,248,0.15);color:#38bdf8;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;border:1px solid rgba(56,189,248,0.3);flex-shrink:0;">Admin</div>
    <div class="n-clock"><span id="systemTimeClock">--:--:--</span></div>
    <div style="position:relative;flex-shrink:0;" id="spz-search-wrap">
      <input id="spz-search-inp" type="text" placeholder="🔍 SPZ..."
        style="background:#0f172a;color:white;border:1px solid #334155;border-radius:6px;padding:5px 9px;font-size:12px;width:110px;outline:none;"
        oninput="spzSearch(this.value)" onblur="setTimeout(()=>document.getElementById('spz-results').innerHTML='',200)">
      <div id="spz-results" style="position:absolute;top:34px;right:0;background:#1e293b;border:1px solid #334155;border-radius:8px;min-width:220px;z-index:4000;box-shadow:0 8px 20px rgba(0,0,0,.7);max-height:220px;overflow-y:auto;"></div>
    </div>
    <!-- Admin nástroje – skryté pro veřejnost -->
    <button id="nt-toggle-btn" onclick="toggleNT()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #f59e0b;background:transparent;color:#f59e0b;cursor:pointer;">🛠️ NT</button>
    <button id="nt-add-btn" onclick="startNtAdd()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:14px;flex-shrink:0;border:1px solid #10b981;background:transparent;color:#10b981;cursor:pointer;" title="Přidat zastávku">＋</button>
    <button id="nt-line-btn" onclick="toggleLineEditor()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #38bdf8;background:transparent;color:#38bdf8;cursor:pointer;" title="Editor linky">🛤️</button>
    <button id="log-toggle-btn" onclick="toggleLogPanel()" style="display:none;padding:5px 9px;border-radius:6px;font-weight:bold;font-size:11px;flex-shrink:0;border:1px solid #475569;background:transparent;color:#94a3b8;cursor:pointer;">📋</button>
    __AD_BTN__
  </nav>
  __ADMIN_BANNER__
  <div id="map"></div>
  <div id="sw">
    <div style="font-size:17px;margin-bottom:3px;">🚍 Mapa se startuje</div>
    <div style="font-size:12px;font-weight:normal;opacity:.9;">Probiha nacitani dat - vyckejte prosim.</div>
    <div id="sw-cd" style="margin-top:5px;font-size:11px;opacity:.8;"></div>
  </div>
  <div id="ttm"><div id="ttb">
    <button id="ttc-btn" onclick="document.getElementById('ttm').classList.remove('open')">X</button>
    <div id="ttc" style="color:white;">Nacitam...</div>
  </div></div>
  <div id="hud">
    <div id="hf">
      <div class="hh"><span class="hl">📡 SLEDOVANI SPOJE</span><button class="hb-mn" onclick="minHud()">-</button></div>
      <div id="h-trip" class="ht">Spoj: -</div>
      <div id="h-dest" class="hd">Nacitam...</div>
      <div class="hr"><span style="color:#94a3b8;">SPZ:</span><span id="h-spz">-</span></div>
      <div class="hr"><span style="color:#94a3b8;">Zpozdeni:</span><span id="h-delay">-</span></div>
      <div class="hr"><span style="color:#94a3b8;">Status:</span><span id="h-status" style="color:#94a3b8;font-size:11px;">-</span></div>
      <div class="hac"><button class="hb hb-jr" id="h-jr">📋 JR</button><button class="hb" id="h-pin" onclick="togglePin()" style="background:#334155;color:#94a3b8;" title="Prilenout kameru k busu">📍</button><button class="hb hb-st" onclick="stopFollow()">✖️ Konec</button></div>
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
    <label style="margin-bottom:6px;"><input type="checkbox" id="ntp-approx"> ⚠️ Přibližná poloha</label>
    <label style="margin-bottom:8px;"><input type="checkbox" id="ntp-substitute"> 🔀 Náhradní zastávka</label>
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
    <button onclick="document.getElementById('stop-info-pop').style.display='none'" style="background:transparent;border:1px solid #334155;color:#64748b;border-radius:5px;font-size:11px;padding:3px 8px;cursor:pointer;margin-top:6px;width:100%;">Zavřít</button>
  </div>
  <div id="nt-line-editor" style="display:none;position:fixed;top:64px;right:10px;z-index:4600;background:#0f172a;border:2px solid #38bdf8;border-radius:10px;width:300px;max-width:95vw;box-shadow:0 8px 28px rgba(0,0,0,.8);">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #1e293b;">
      <span style="color:#38bdf8;font-weight:bold;font-size:13px;">🛤️ Editor linky</span>
      <button onclick="document.getElementById('nt-line-editor').style.display='none'" style="background:none;border:none;color:#64748b;font-size:16px;cursor:pointer;">✕</button>
    </div>
    <div style="padding:10px 14px;">
      <div style="display:flex;gap:6px;margin-bottom:10px;">
        <input id="nt-line-inp" type="text" placeholder="Číslo linky (490735, 760...)" style="flex:1;background:#1e293b;color:white;border:1px solid #334155;border-radius:5px;padding:6px 9px;font-size:12px;" onkeydown="if(event.key==='Enter')loadLineStops()">
        <button onclick="loadLineStops()" style="background:#38bdf8;color:#0f172a;border:none;border-radius:5px;padding:6px 12px;font-weight:bold;font-size:12px;cursor:pointer;">Načíst</button>
      </div>
      <div id="nt-line-status" style="font-size:11px;color:#64748b;margin-bottom:8px;"></div>
      <div id="nt-line-stops" style="max-height:350px;overflow-y:auto;"></div>
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
        <button onclick="copyLog()">Kopír.</button>
        <button onclick="clearLog()">Smaž</button>
        <button onclick="document.getElementById('log-panel').style.display='none'">X</button>
      </div>
    </div>
    <div id="log-body"></div>
    <div id="log-errors-body" style="display:none;"></div>
    <div id="log-spz-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-family:monospace;font-size:10.5px;color:#94a3b8;"></div>
    <div id="log-missing-body" style="display:none;max-height:200px;overflow-y:auto;padding:6px 12px;font-size:11px;"></div>
  </div>
  <div id="nt-add-bar" style="display:none;position:fixed;top:70px;left:50%;transform:translateX(-50%);z-index:5000;background:#1e293b;border:2px solid #f59e0b;border-radius:8px;padding:8px 14px;display:none;align-items:center;gap:8px;box-shadow:0 4px 20px rgba(0,0,0,.7);">
    <span style="color:#f59e0b;font-size:12px;font-weight:bold;">🚏 Klikni na mapu kde je zastávka</span>
    <input id="nt-add-name" type="text" placeholder="Název zastávky" style="background:#0f172a;color:white;border:1px solid #475569;border-radius:4px;padding:4px 8px;font-size:12px;width:160px;">
    <button onclick="confirmNtAdd()" style="background:#10b981;color:white;border:none;border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;">Přidat</button>
    <button onclick="cancelNtAdd()" style="background:#334155;color:#94a3b8;border:none;border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;">Zrušit</button>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

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
    if(data.status==='success'){showAdminToast('Ulozeno - system zpracovava');setTimeout(()=>{if(action==='reset_admin'||action==='recheck_spz')Object.keys(adminInputCache).forEach(k=>{if(k.endsWith('_'+busId))delete adminInputCache[k];});fetchBuses();},800);}
    else showAdminToast('Chyba: '+(data.message||'neznama'),false);
  }catch(e){showAdminToast('Chyba spojeni',false);}
}
window.adminDelete=(id)=>{if(confirm('Smazat tecku? Vrati se az pri novem spoji.')){adminAction('delete',id);openPopupBusId=null;}};
window.adminRecheck=(id)=>adminAction('recheck_spz',id);
window.adminSetSPZ=(id)=>{let spz=document.getElementById('adm_spz_'+id)?.value;if(spz)adminAction('edit_spz',id,{spz});};
window.adminSaveAll=(id,permanent)=>{
  let st=document.getElementById('adm_st_'+id)?.value?.trim()||'',col=document.getElementById('adm_col_'+id)?.value?.trim()||'',note=document.getElementById('adm_note_'+id)?.value?.trim()||'';
  if(!st&&!col&&!note){showAdminToast('Nic k ulozeni',false);return;}
  adminAction('edit_all',id,{status:st,color_class:col,note,permanent});
};

// === NAV ===
const nav=document.getElementById('top-nav'),handle=document.getElementById('nav-handle');
let hideT=null;
function showNav(dur){clearTimeout(hideT);nav.classList.add('vis');handle.classList.add('hid');if(dur)hideT=setTimeout(hideNav,dur);}
function hideNav(){nav.classList.remove('vis');handle.classList.remove('hid');}
handle.addEventListener('click',()=>showNav(5000));
document.addEventListener('mousemove',e=>{if(e.clientY<6)showNav();},{passive:true});
nav.addEventListener('mouseenter',()=>clearTimeout(hideT));
nav.addEventListener('mouseleave',()=>{hideT=setTimeout(hideNav,600);});
document.addEventListener('touchstart',e=>{if(e.touches[0].clientY<35){showNav(4500);}else if(!nav.contains(e.target)){clearTimeout(hideT);hideT=setTimeout(hideNav,400);}},{passive:true});
showNav(4000);
if(IS_ADMIN){let ab=document.getElementById('admin-mode-badge');if(ab)ab.style.display='block';let ntb=document.getElementById('nt-toggle-btn');if(ntb)ntb.style.display='inline-block';let nab=document.getElementById('nt-add-btn');if(nab)nab.style.display='inline-block';let nlb=document.getElementById('nt-line-btn');if(nlb)nlb.style.display='inline-block';let lgb=document.getElementById('log-toggle-btn');if(lgb)lgb.style.display='inline-block';}

// === MAP ===
var dLat=49.7384,dLng=13.3736,dZoom=12;
var hp=window.location.hash.replace('#','').split(',');
if(hp.length===2&&!isNaN(hp[0])&&!isNaN(hp[1])&&hp[0]!==""){dLat=parseFloat(hp[0]);dLng=parseFloat(hp[1]);dZoom=17;}
var map=L.map('map',{zoomControl:false}).setView([dLat,dLng],dZoom);
L.control.zoom({position:'bottomleft'}).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'(c) OpenStreetMap'}).addTo(map);
setTimeout(()=>map.invalidateSize(),300);
var ml=L.layerGroup().addTo(map);
var routeLayer=L.layerGroup().addTo(map);
var ntLayer=L.layerGroup().addTo(map);
var pubStopsLayer=L.layerGroup().addTo(map);
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
    let btn=document.getElementById('log-tab-err');
    if(btn&&logCurrentTab!=='err')btn.style.color='#f87171';
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
      if(!ntMode)toggleNT();
      document.getElementById('log-panel').style.display='none';
      startNtAdd(name);
    };
    useBtn.onclick=()=>{
      document.getElementById('log-panel').style.display='none';
      openUseExistingStopDialog(name);
    };
    body.appendChild(div);
  });
}

// "Použít existující" - propoj chybějící jméno z JŘ s už existující zastávkou
// (typicky: PVVD používá jiný zápis názvu než GTFS, ale fyzicky je to stejné
// místo). Vytvoří alias - STOP_OVERRIDES záznam pod hledaným jménem, který
// ukazuje na souřadnice té vybrané existující zastávky.
async function openUseExistingStopDialog(missingName){
  let query=prompt(`Zastávka "${missingName}" nenalezena.\nNapiš část názvu existující zastávky, na kterou se má napojit:`,missingName);
  if(!query||!query.trim())return;
  query=query.trim();
  try{
    let b=map.getBounds();
    // Hledej v aktuálním výřezu i širším okolí (zvětšený bbox) - zastávka
    // co hledáme nemusí být přesně tam kde je teď mapa
    let pad=0.3;
    let r=await fetch(`/api/stops_in_view?south=${b.getSouth()-pad}&west=${b.getWest()-pad}&north=${b.getNorth()+pad}&east=${b.getEast()+pad}`);
    let data=await r.json();
    if(data.status!=='success'){showAdminToast(data.message||'Nelze hledat - přibliž mapu na danou oblast a zkus znovu',false);return;}
    let qn=query.toLowerCase();
    let matches=data.stops.filter(s=>(s.name||'').toLowerCase().includes(qn)||(s.display_name||'').toLowerCase().includes(qn));
    if(!matches.length){showAdminToast('Nic nenalezeno - zkus jiný text nebo přibliž mapu k té oblasti',false);return;}
    let list=matches.slice(0,15).map((s,i)=>`${i+1}. ${s.name}${s.display_name?' ('+s.display_name+')':''}`).join('\\n');
    let choice=prompt(`Vyber číslo zastávky pro napojení "${missingName}":\\n${list}`,'1');
    if(!choice)return;
    let idx=parseInt(choice.trim())-1;
    if(isNaN(idx)||idx<0||idx>=matches.length){showAdminToast('Neplatná volba',false);return;}
    let target=matches[idx];
    // Ulož jako override pod HLEDANÝM jménem (z JŘ), souřadnice = vybraná existující zastávka
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:missingName,lat:target.lat,lng:target.lng})});
    let rd=await res.json();
    if(rd.status==='success'){
      showAdminToast(`✅ "${missingName}" napojeno na "${target.name}"`,true);
      appLog(`Propojeno: "${missingName}" → existující "${target.name}"`,'ok');
      delete logMissingStops[missingName];
      if(logCurrentTab==='missing')renderMissingLog();
    }else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
function setLogTab(tab){
  logCurrentTab=tab;
  ['all','err','spz','missing'].forEach(id=>{
    let body=document.getElementById(`log-${id==='all'?'body':id==='err'?'errors-body':id+'-body'}`);
    if(body)body.style.display=tab===id?'':'none';
    let btn=document.getElementById(`log-tab-${id}`);
    if(btn){btn.style.background=tab===id?'#334155':'transparent';btn.style.color='';}
  });
  if(tab==='err'){let b=document.getElementById('log-errors-body');b.innerHTML='';logErrEntries.forEach(e=>{let l=document.createElement('div');l.className='lg-err';l.textContent=`[${e.t}] ${e.msg}`;b.appendChild(l);});b.scrollTop=b.scrollHeight;}
  if(tab==='spz')renderSpzLog();
  if(tab==='missing')renderMissingLog();
}
function toggleLogPanel(){let p=document.getElementById('log-panel');if(p)p.style.display=p.style.display==='block'?'none':'block';}
function copyLog(){
  let txt=logEntries.map(e=>`[${e.t}][${e.level}] ${e.msg}`).join('\\n');
  navigator.clipboard.writeText(txt).then(()=>showAdminToast('📋 Zkopírováno',true)).catch(()=>showAdminToast('Chyba kopírování',false));
}
function clearLog(){
  logEntries=[];logErrEntries=[];logSpzEntries=[];logMissingStops={};
  ['log-body','log-errors-body','log-spz-body','log-missing-body'].forEach(id=>{let el=document.getElementById(id);if(el)el.innerHTML='';});
}
window.addEventListener('error',e=>{appLog('JS chyba: '+(e.message||e)+(e.filename?` (${e.filename}:${e.lineno})`:''),'error');});
window.addEventListener('unhandledrejection',e=>{appLog('Promise chyba: '+(e.reason&&(e.reason.message||e.reason)),'error');});

// === HUD + KAMERA + ŠPENDLÍK ===
let pinMode=false;
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
function minHud(){hudMin=true;document.getElementById('hf').style.display='none';document.getElementById('hm').style.display='flex';}
function maxHud(){hudMin=false;document.getElementById('hf').style.display='block';document.getElementById('hm').style.display='none';}
window.toggleFollow=function(busId,inflowId){
  if(followId===busId){stopFollow();return;}
  followId=busId;followInflowId=inflowId||busId;
  pinMode=false; // default: sledovat ale NEpřilepovat - uživatel může volně chodit po mapě
  let b=lastArr.find(x=>x.id===busId);
  if(b&&b.lat)map.setView([b.lat,b.lng],16); // jednorázový zoom při zahájení sledování
  document.getElementById('hud').style.display='block';updateHud(b);
  let pb=document.getElementById('h-pin');if(pb){pb.style.background='#334155';pb.style.color='#94a3b8';}
  if(hudMin){document.getElementById('hf').style.display='none';document.getElementById('hm').style.display='flex';}
  appLog(`Sledování zahájeno: bus ${busId}`,'info');
};
function updateHud(b){
  if(!b)return;
  document.getElementById('h-trip').textContent='Spoj: '+(b.line||'?')+(b.trip_id?' / '+b.trip_id.replace('TRIP-','').substring(0,8):'');
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
  document.getElementById('ttc').innerHTML="<div style='text-align:center;padding:40px;color:#38bdf8;'><i class='fas fa-circle-notch fa-spin fa-2x'></i><p style='margin-top:14px;font-weight:bold;'>📋 Nacitam JR z PVVD...</p></div>";
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
  const cM={'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-bug':'#374151'};
  const bgC=cM[mc]||'#64748b',tF=(mc==='bg-orange')?'#0f172a':'#fff';
  let lC=(lineText||'').split('/')[0].trim().replace(/[^0-9]/g,'');
  let lD=lC.length>=4?lC.slice(-3):lC;
  const cx=18,cy=18,r=isTrain?10:12;
  let si='';
  const hB=bearing!==null&&bearing!==undefined&&!['bg-gray','bg-purple','bg-bug'].includes(mc)&&!isTrain;
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
  else{const ds=mc==='bg-bug'?'stroke-dasharray="3,2"':'';si+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${bgC}" stroke="white" stroke-width="2" ${ds} opacity="${mc==='bg-bug'?0.7:1}"/>`;}
  if(lD&&!isTrain&&mc!=='bg-bug'){
    if(lD.length>3){si+=`<text x="${cx}" y="${cy-2.5}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="7" font-family="'Segoe UI',system-ui,sans-serif">${lD.substring(0,3)}</text>`;si+=`<text x="${cx}" y="${cy+5.5}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="6" font-family="'Segoe UI',system-ui,sans-serif">${lD.substring(3)}</text>`;}
    else si+=`<text x="${cx}" y="${cy+1}" dominant-baseline="middle" text-anchor="middle" fill="${tF}" font-weight="bold" font-size="8" font-family="'Segoe UI',system-ui,sans-serif">${lD}</text>`;
  }
  return `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;display:block;">${si}</svg>`;
}

// === ROUTE DISPLAY ===
async function toggleRoute(busId){
  if(activeRouteId===busId){
    routeLayer.clearLayers();activeRouteId=null;
    let btn=document.getElementById('route-btn-'+busId);
    if(btn){btn.textContent='🗺️ Zobrazit trasu';btn.style.background='#334155';}
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
  routeLayer.clearLayers();
  if(!data.stops||data.stops.length<2){
    if(btn){btn.textContent=data.error?'Trasa nedostupna ('+data.error+')':'Trasa nedostupna';btn.style.background='#7f1d1d';}
    return;
  }
  const cM={'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-bug':'#374151'};
  let bus=lastArr.find(b=>b.id===busId);
  let lC=bus?(cM[bus.color_class]||'#38bdf8'):'#38bdf8';
  let pts=data.stops.filter(s=>s.lat&&s.lng);
  let splitIdx=pts.findIndex(s=>!s.passed);
  if(splitIdx===-1)splitIdx=pts.length;
  let finalIdx=pts.length-1;

  // Cary
  let pastPts=pts.slice(0,Math.min(splitIdx+1,pts.length)).map(s=>[s.lat,s.lng]);
  let futurePts=pts.slice(splitIdx).map(s=>[s.lat,s.lng]);
  if(pastPts.length>=2)
    routeLayer.addLayer(L.polyline(pastPts,{color:'#374151',weight:3,opacity:0.45,dashArray:'5,5',className:'route-line-past'}));
  if(futurePts.length>=2)
    routeLayer.addLayer(L.polyline(futurePts,{color:lC,weight:5,opacity:0.92,className:'route-line-future'}));

  // Zastavky - kazda ma jiny vizualni styl podle stavu
  pts.forEach((stop,i)=>{
    let isPast=stop.passed;
    let isFinal=(i===finalIdx);
    let isCurrent=(i===splitIdx&&splitIdx>0&&splitIdx<pts.length);
    let lowConf=stop.confidence==='fuzzy'||stop.confidence==='geocoded';
    let warnHtml='';
    if(stop.substitute)warnHtml='<br><span style="color:#a855f7;font-size:10px;">🔀 nahradni</span>';
    else if(stop.approx||lowConf)warnHtml='<br><span style="color:#f59e0b;font-size:10px;">⚠️ pribl.</span>';
    let icon;
    if(isFinal){
      // Koncova: velky ctverec s vlajkou
      icon=L.divIcon({className:'',iconSize:[22,22],iconAnchor:[11,11],html:
        '<div style="width:20px;height:20px;background:'+lC+';border:3px solid #fff;border-radius:4px;'+
        'display:flex;align-items:center;justify-content:center;font-size:12px;'+
        'box-shadow:0 0 10px '+lC+',0 2px 8px rgba(0,0,0,.7);">🏁</div>'});
    } else if(isCurrent){
      // Aktualni: pulsujici kolecko
      icon=L.divIcon({className:'',iconSize:[20,20],iconAnchor:[10,10],html:
        '<div style="width:16px;height:16px;border-radius:50%;background:'+lC+';border:3px solid #fff;'+
        'box-shadow:0 0 12px '+lC+',0 2px 6px rgba(0,0,0,.5);'+
        'animation:routePulse 1.1s ease-in-out infinite;"></div>'});
    } else if(isPast){
      // Minula: mala seda tecka
      icon=L.divIcon({className:'',iconSize:[8,8],iconAnchor:[4,4],html:
        '<div style="width:5px;height:5px;border-radius:50%;background:#374151;border:1.5px solid #4b5563;opacity:0.6;"></div>'});
    } else {
      // Budouci: stredni barevne kolecko
      let bd=lowConf?'2px dashed #f59e0b':'2px solid rgba(255,255,255,0.85)';
      icon=L.divIcon({className:'',iconSize:[12,12],iconAnchor:[6,6],html:
        '<div style="width:9px;height:9px;border-radius:50%;background:'+lC+';border:'+bd+';'+
        'box-shadow:0 1px 4px rgba(0,0,0,.6);"></div>'});
    }
    let m=L.marker([stop.lat,stop.lng],{icon,zIndexOffset:isFinal?300:isCurrent?200:isPast?-200:-50});
    let timeStr=stop.time?' / <b>'+stop.time+'</b>':'';
    let typeLabel=isFinal?' — 🏁 <b>Konecna</b>':isCurrent?' ← <b>Zde</b>':'';
    m.bindTooltip(
      '<span style="font-size:12px;">🚏 '+stopDisplayName(stop)+'</span>'+timeStr+typeLabel+warnHtml,
      {direction:'top',className:'dark-popup'});
    routeLayer.addLayer(m);
  });

  let found=data.stops.filter(s=>s.lat).length;
  let uncertain=data.stops.filter(s=>s.lat&&(s.confidence==='fuzzy'||s.confidence==='geocoded')).length;
  let missing=data.stops.filter(s=>!s.lat);
  missing.forEach(s=>{
    appLog('Zastavka nenalezena: "'+s.name+'" pridej v NT','warn');
    logMissingStop(s.name);
    fetch('/api/admin/report_missing_stop',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({stop_name:s.name,bus_id:busId})}).catch(()=>{});
  });
  appLog('Trasa '+busId+': '+found+'/'+data.stops.length+' (nejiste:'+uncertain+' chybi:'+missing.length+')','info');
  let label='🗺️ Skryt trasu ('+found+'/'+data.stops.length+' zast.)'+(uncertain?' ⚠️'+uncertain:'')+(missing.length?' ❓'+missing.length:'');
  if(btn){btn.textContent=label;btn.style.background='#1e40af';}
}


// === NT (Nastaveni tras) - rucni kalibrace poloh zastavek ===
let ntMode=false,ntMoveTimer=null,currentNtEdit=null,ntAddMode=false,ntAddName='';
function stopDisplayName(s){
  // Zobrazovany nazev ma prednost pred systemovym (pouzitym jen pro vyhledavani v JR)
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
      body:JSON.stringify({stop_name:s.name,line,remove:false})});
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
      body:JSON.stringify({stop_name:s.name,line,remove:true})});
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
  document.getElementById('ntp-approx').checked=!!s.approx;
  document.getElementById('ntp-substitute').checked=!!s.substitute;
  renderNtLineChips(s.lines);
  document.getElementById('nt-edit-pop').style.display='block';
}
async function saveNtFlags(){
  if(!currentNtEdit)return;
  let {stop:s,marker:m}=currentNtEdit;
  let pos=m.getLatLng();
  let approx=document.getElementById('ntp-approx').checked;
  let substitute=document.getElementById('ntp-substitute').checked;
  let display_name=document.getElementById('ntp-dispname').value.trim();
  // Linky jsou uloženy průběžně přes addLineToNtStop/removeNtLine
  // saveNtFlags uloží jen zbývající metadata (approx/substitute/display_name)
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:s.name,lat:pos.lat,lng:pos.lng,approx,substitute,display_name,custom_lines:s.lines||null})});
    let rd=await res.json();
    if(rd.status==='success'){
      Object.assign(s,{approx,substitute,display_name,manual:true});
      m.setIcon(ntDotIcon(ntDotClass(s)));
      m.setTooltipContent(`<b>${s.mode==='train'?'🚂':'🚏'} ${s.name}</b>${ntLabel(s)}`);
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
    let res=await fetch('/api/admin/delete_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name})});
    let rd=await res.json();
    if(rd.status==='success'){showAdminToast(`🗑️ Odebráno: ${s.name}`,true);document.getElementById('nt-edit-pop').style.display='none';loadNTStops();}
    else showAdminToast('Chyba: '+(rd.message||'?'),false);
  }catch(e){showAdminToast('Chyba spojení',false);}
}
// NT add mode: + button → enter name in topbar → click on map → saves
// NT add mode: klik + → kříž → klik mapu → prompt pro název → uloží
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
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,lat,lng})});
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
  if(!ntAddMode)return;
  cancelNtAdd(); // odeber kříž hned
  let prefill=ntPendingPrefill;
  let name=prompt(
    prefill
      ? `Název zastávky (navrhovaný: ${prefill}):\nPonech prázdné pro použití navrhovaného.`
      : 'Název zastávky:',
    prefill
  );
  if(name===null)return; // zrušit
  if(!name.trim()&&prefill)name=prefill; // enter = přijmi navrhovaný
  if(!name.trim()){showAdminToast('Název je prázdný',false);return;}
  await _doAddStop(e.latlng.lat,e.latlng.lng,name);
});
map.on('moveend',()=>{
  if(!ntMode)return;
  clearTimeout(ntMoveTimer);ntMoveTimer=setTimeout(loadNTStops,400);
});

// === NT linka-editor ===
let lineEditorLayer=L.layerGroup().addTo(map);
let lineEditorActive=false;
function toggleLineEditor(){
  let pan=document.getElementById('nt-line-editor');
  if(!pan)return;
  lineEditorActive=pan.style.display==='block';
  pan.style.display=lineEditorActive?'none':'block';
  if(lineEditorActive){lineEditorLayer.clearLayers();}
  else{let inp=document.getElementById('nt-line-inp');if(inp)inp.focus();}
}
async function loadLineStops(){
  let inp=document.getElementById('nt-line-inp');
  let line=(inp&&inp.value||'').trim();
  if(!line){document.getElementById('nt-line-status').textContent='Zadej číslo linky';return;}
  let status=document.getElementById('nt-line-status');
  let stopsEl=document.getElementById('nt-line-stops');
  status.textContent='Načítám...';stopsEl.innerHTML='';
  lineEditorLayer.clearLayers();
  // Ziskat zastavky pro linku z GTFS pres bbox (velky region pokryva cely kraj)
  let b=map.getBounds();
  // Rozsireny bbox pro pokryti celeho mozneho rozsahu linky
  let pad=1.5;
  try{
    let r=await fetch(`/api/stops_in_view?south=${b.getSouth()-pad}&west=${b.getWest()-pad}&north=${b.getNorth()+pad}&east=${b.getEast()+pad}`);
    let data=await r.json();
    if(data.status!=='success'){status.textContent=data.message||'Chyba';return;}
    // Filtruj zastavky kde je tato linka
    let lineNorm=line.trim();
    let matches=data.stops.filter(s=>(s.lines||[]).some(l=>l===lineNorm||l.endsWith(lineNorm)||lineNorm.endsWith(l)));
    status.textContent=`${matches.length} zastávek pro linku ${line}`;
    if(!matches.length){stopsEl.innerHTML='<div style="color:#64748b;padding:8px;font-size:11px;">Žádné zastávky nenalezeny. Zkus broader bbox – přibliž mapu k trase linky.</div>';return;}
    matches.forEach((s,i)=>{
      let div=document.createElement('div');
      div.style.cssText='padding:5px 0;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:6px;';
      let dn=stopDisplayName(s);
      div.innerHTML=`
        <span style="color:#64748b;font-size:10px;width:18px;text-align:right;">${i+1}</span>
        <div style="flex:1;">
          <div style="font-size:12px;color:${s.approx?'#f59e0b':'#cbd5e1'};">${dn}</div>
          ${s.display_name?'<div style="font-size:9px;color:#475569;">sys: '+s.name+'</div>':''}
        </div>
        <button style="background:#334155;color:#38bdf8;border:none;border-radius:4px;padding:3px 7px;font-size:10px;cursor:pointer;">Na mapě</button>
        <button style="background:#1e3a5f;color:#94a3b8;border:none;border-radius:4px;padding:3px 7px;font-size:10px;cursor:pointer;">NT</button>`;
      let [mapBtn,ntBtn]=div.querySelectorAll('button');
      // Ukaz zastavku na mape
      let m=L.circleMarker([s.lat,s.lng],{radius:6,color:'#38bdf8',fillColor:'#38bdf8',fillOpacity:0.8,weight:2});
      m.bindTooltip(`<b>${dn}</b><br>Linka: ${line}`,{direction:'top',className:'dark-popup'});
      lineEditorLayer.addLayer(m);
      mapBtn.onclick=()=>{map.setView([s.lat,s.lng],17);m.openTooltip();};
      // Otevri NT editor pro tuto zastavku
      ntBtn.onclick=()=>{
        if(!ntMode)toggleNT();
        map.setView([s.lat,s.lng],17);
        setTimeout(()=>{
          ntLayer.eachLayer(layer=>{
            if(layer.getLatLng&&Math.abs(layer.getLatLng().lat-s.lat)<0.0001&&Math.abs(layer.getLatLng().lng-s.lng)<0.0001){
              layer.fire('click');
            }
          });
        },600);
      };
      stopsEl.appendChild(div);
    });
  }catch(e){status.textContent='Chyba: '+e;appLog('Linka-editor chyba: '+e,'error');}
}

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
  document.getElementById('stop-info-pop').style.display='block';
}

function pubStopIcon(s){
  let isTrain=s.mode==='train';
  let base=s.substitute?'pub-dot-substitute':s.approx?'pub-dot-approx':'';
  let trainCls=isTrain?' pub-dot-train':'';
  let size=isTrain?12:10; // trochu větší pro lepší touch
  return L.divIcon({className:'',html:`<div class="pub-dot ${base}${trainCls}" style="width:${size}px;height:${size}px;"></div>`,iconSize:[size,size],iconAnchor:[size>>1,size>>1]});
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
  const cM={'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-bug':'#374151'};
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
    let savedOpenId=openPopupBusId;
    isRefreshing=true;
    ml.clearLayers();

    data.buses.forEach(bus=>{
      if(!bus.lat||!bus.lng)return;
      let mc=bus.color_class,dv=parseInt(bus.delay),dTxt='';
      if(mc==='bg-gray'||mc==='bg-bug')dTxt='<span style="color:#94a3b8;">N/A</span>';
      else if(mc==='bg-purple')dTxt='<span style="color:#a855f7;">Konecna</span>';
      else if(mc==='bg-orange')dTxt='<span style="color:#f59e0b;">Vyzkum</span>';
      else if(mc==='bg-blue'){let dm=Math.abs(dv),dh=Math.floor(dm/60),dmn=dm%60;dTxt=`<span style="color:#3b82f6;">Za ${dh>0?dh+'h '+dmn+'m':dmn+' min'}</span>`;}
      else if(mc==='bg-darkblue')dTxt=`<span style="color:#60a5fa;">Naskok ${Math.abs(dv)} min</span>`;
      else if(dv>=5)dTxt=`<span style="color:#ef4444;">Zpozdeni ${dv} min</span>`;
      else dTxt=`<span style="color:#10b981;">+${dv} min</span>`;

      let icon=L.divIcon({className:'',html:buildMarkerSvg(mc,bus.bearing,bus.line,bus.is_train),iconSize:[36,36],iconAnchor:[18,18],popupAnchor:[0,-20]});
      let marker=L.marker([bus.lat,bus.lng],{icon});
      marker._busId=bus.id;
      marker.on('popupopen',()=>{openPopupBusId=bus.id;});
      marker.on('popupclose',()=>{
        if(openPopupBusId===bus.id)openPopupBusId=null;
        if(!isRefreshing&&activeRouteId===bus.id){routeLayer.clearLayers();activeRouteId=null;}
      });

      let spzH='',invTxt='',histBtn='';
      if(!bus.is_train){
        if(bus.investigating){spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#ef4444;color:#fff;border-color:#b91c1c;">Vyzkum <i class="fas fa-clock"></i></span></div>`;invTxt=`<div style="color:#ef4444;font-size:10px;font-weight:bold;margin:4px 0;">Zjistuji SPZ (${bus.investigation_spz})</div>`;}
        else if(bus.spz&&bus.spz!=='Neznama'){
          if(bus.spz_verified){spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b">${bus.spz} <i class="fas fa-check"></i></span></div>`;histBtn=`<a href="/historie/${bus.spz}" target="_blank" class="pa pa-d" style="margin-top:5px;">📜 Historie vozu</a>`;}
          else{spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#f97316;color:#fff;border-color:#c2410c;">${bus.spz} <i class="fas fa-clock"></i></span></div>`;}
        }
        else spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv" style="color:#64748b;">Ceka na overeni</span></div>`;
      }
      let bugW='';
      if(mc==='bg-bug'){let bS=(bus.spz&&bus.spz!=='Neznama')?bus.spz:'Neznama SPZ';bugW=`<div style="background:#374151;border:1px dashed #6b7280;border-radius:5px;padding:7px;margin:5px 0;color:#9ca3af;font-size:10px;text-align:center;"><b style="color:#f59e0b;">🐛 BUG - NEAKTUALNI MISTO</b><br>SPZ <b>${bS}</b> zamknuta (posledni znama pred zaseknutim), jede na jinem miste.</div>`;}
      let orangeW='';
      if(mc==='bg-orange')orangeW=`<div style="background:rgba(245,158,11,.15);border:1px solid #f59e0b;border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:#f59e0b;"><b>🔍 Vyzkum - bus byl zasekly, nyni jede</b></div>`;
      let sc='#10b981';
      if(mc==='bg-bug')sc='#6b7280';else if(mc==='bg-orange')sc='#f59e0b';
      else if(bus.status.includes('prilis'))sc='#94a3b8';else if(bus.status.includes('Stoji'))sc='#ef4444';
      else if(bus.status.includes('Konecna')||bus.status.includes('Ztrata'))sc='#a855f7';
      else if(bus.status.includes('Ceka')||bus.status.includes('Zacatek'))sc='#3b82f6';
      else if(bus.status.includes('Odstaven')||bus.status.includes('signal'))sc='#94a3b8';
      else if(bus.status.includes('Naskok'))sc='#60a5fa';
      let fTxt=(followId===bus.id)?'✖️ Zrusit sledovani':'📡 Sledovat';
      let fSt=(followId===bus.id)?'background:#ef4444;color:#fff;':'background:#3b82f6;color:#fff;';
      let afH=bus.admin_flag?'<span style="background:#1e40af;color:#93c5fd;padding:2px 7px;border-radius:10px;font-size:10px;margin-left:6px;font-weight:bold;">Admin uprava</span>':'';
      let rA=(activeRouteId===bus.id);

      let popH=`
        <div class="ph" style="${mc==='bg-bug'?'background:#1f2937;':''}${mc==='bg-orange'?'background:#1c1400;':''}">
          <h3 class="ph-t" style="${mc==='bg-bug'?'color:#9ca3af;':''}${mc==='bg-orange'?'color:#f59e0b;':''}">Linka ${bus.line}${afH}</h3>
        </div>
        <div class="pb">
          ${bugW}${orangeW}
          ${bus.admin_note?`<div style="background:rgba(147,197,253,0.1);border:1px solid #334155;border-radius:5px;padding:5px 8px;margin-bottom:5px;font-size:11px;color:#93c5fd;">${bus.admin_note}</div>`:''}
          <div class="pr"><span class="pl">Cil:</span><span class="pv">${bus.destination||'Neznamy'}</span></div>
          ${spzH}${invTxt}
          <div class="pr"><span class="pl">Status:</span><span class="pv" style="color:${sc};">${bus.status}</span></div>
          <div class="pr" style="border:none;"><span class="pl">JR:</span><span class="pv">${dTxt}</span></div>
          <button class="pa" onclick="showTT('${bus.id}')">📋 Zobrazit Jizdni rad</button>
          <button class="pa" style="${fSt}margin-top:5px;" onclick="toggleFollow('${bus.id}','${bus.id}')">${fTxt}</button>
          ${histBtn}
          <button id="route-btn-${bus.id}" class="pa pa-d" style="margin-top:5px;${rA?'background:#1e40af;':''}" onclick="toggleRoute('${bus.id}')">${rA?'🗺️ Skryt trasu':'🗺️ Zobrazit trasu'}</button>
        </div>`;

      if(IS_ADMIN){
        let oSpz=bus.spz==='Neznama'?'':bus.spz;
        let cSpz=restoreAdminInput(bus.id,'spz')??oSpz;
        let cSt=restoreAdminInput(bus.id,'st')??bus.status;
        let cNote=restoreAdminInput(bus.id,'note')??(bus.admin_note||'');
        popH+=`<style>.adm-inp{width:100%;box-sizing:border-box;background:#0f172a;color:white;border:1px solid #334155;border-radius:5px;padding:7px 8px;font-size:12px;margin-top:4px;}.adm-inp:focus{outline:none;border-color:#38bdf8;}.adm-btn{width:100%;padding:11px;border:none;border-radius:6px;font-size:13px;font-weight:bold;cursor:pointer;margin-top:4px;touch-action:manipulation;}</style>
          <div style="border-top:1px solid #334155;margin-top:6px;padding:10px 13px;background:#0a0f1e;">
            <strong style="color:#38bdf8;font-size:11px;letter-spacing:.5px;">🔧 ADMIN PANEL</strong>
            <div style="display:flex;gap:5px;margin-top:8px;">
              <input type="text" id="adm_spz_${bus.id}" value="${cSpz}" data-orig="${oSpz}" placeholder="SPZ" class="adm-inp" style="width:55%;margin-top:0;">
              <button onclick="adminSetSPZ('${bus.id}')" style="width:45%;background:#10b981;color:white;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">💾 Ulozit</button>
            </div>
            <div style="display:flex;gap:5px;margin-top:5px;">
              <button onclick="adminAction('recheck_spz','${bus.id}')" style="flex:1;background:#f59e0b;color:#0f172a;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">🔍 Hledat SPZ</button>
              <button onclick="adminDelete('${bus.id}')" style="flex:1;background:#ef4444;color:white;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">🗑️ Smazat</button>
            </div>
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
              <input type="text" id="adm_st_${bus.id}" value="${cSt}" data-orig="${bus.status}" placeholder="Status text..." class="adm-inp">
              <select id="adm_col_${bus.id}" class="adm-inp" style="margin-top:4px;">
                <option value="">-- barva --</option>
                <option value="bg-gray" ${bus.color_class==='bg-gray'?'selected':''}>Seda</option>
                <option value="bg-blue" ${bus.color_class==='bg-blue'?'selected':''}>Svetle modra</option>
                <option value="bg-darkblue" ${bus.color_class==='bg-darkblue'?'selected':''}>Tmave modra</option>
                <option value="bg-green" ${bus.color_class==='bg-green'?'selected':''}>Zelena</option>
                <option value="bg-red" ${bus.color_class==='bg-red'?'selected':''}>Cervena</option>
                <option value="bg-purple" ${bus.color_class==='bg-purple'?'selected':''}>Fialova</option>
                <option value="bg-orange" ${bus.color_class==='bg-orange'?'selected':''}>Oranzova</option>
                <option value="bg-bug" ${bus.color_class==='bg-bug'?'selected':''}>Bug</option>
              </select>
              <input type="text" id="adm_note_${bus.id}" value="${cNote}" data-orig="${bus.admin_note||''}" placeholder="Poznamka..." class="adm-inp" style="margin-top:4px;">
              <div style="display:flex;gap:5px;margin-top:6px;">
                <button onclick="adminSaveAll('${bus.id}',true)" class="adm-btn" style="flex:1;background:#1e40af;color:white;">📌 Trvala</button>
                <button onclick="adminSaveAll('${bus.id}',false)" class="adm-btn" style="flex:1;background:#334155;color:#94a3b8;">⏱️ Docasna</button>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:7px;padding-top:6px;border-top:1px solid #1e293b;">
              <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:11px;color:#93c5fd;flex:1;touch-action:manipulation;">
                <input type="checkbox" id="adm_flag_${bus.id}" ${bus.admin_flag?'checked':''} onchange="adminAction('set_admin_flag','${bus.id}',{flag:this.checked})" style="width:16px;height:16px;cursor:pointer;">
                Admin uprava
              </label>
              <button onclick="adminAction('reset_admin','${bus.id}')" style="background:transparent;color:#64748b;border:1px solid #334155;border-radius:5px;font-size:11px;cursor:pointer;padding:5px 10px;touch-action:manipulation;">🔄 Reset</button>
            </div>
          </div>`;
      }
      marker.bindPopup(popH,{className:'dark-popup',maxWidth:300});
      ml.addLayer(marker);
    });

    if(savedOpenId){
      ml.eachLayer(layer=>{
        if(layer._busId===savedOpenId){
          setTimeout(()=>{layer.openPopup();isRefreshing=false;},30);
        }
      });
    }else{
      setTimeout(()=>{isRefreshing=false;},50);
    }

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
</script>
"""

# === GLOBALNI STAV ===
GLOBAL_BUS_CACHE    = {}
LIVE_BUSES_DATA     = []
TRACKED_SPZS        = set()
WORKER_START_TIME   = None
ADMIN_DELETED_BUSES = {}
_stop_geo_cache     = {}

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
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)


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
            loaded[_norm_txt(nm)] = {
                "lat": row["lat"], "lng": row["lng"], "name": nm,
                "approx": bool(row.get("approx", False)),
                "substitute": bool(row.get("substitute", False)),
                "display_name": row.get("display_name") or "",
                "custom_lines": cl,   # None = pouzij GTFS, list = pouzij toto
            }
        STOP_OVERRIDES = loaded
        print(f"[NT] Nacteno {len(loaded)} rucnich oprav poloh zastavek.", flush=True)
    except Exception as e:
        print(f"[NT] Tabulka stop_overrides nedostupna (OK pokud NT jeste nebyl pouzit): {e}", flush=True)


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


def _lookup_stop_coords(name, anchor=None, max_anchor_dist_m=60000):
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

    # 0) Rucni oprava z NT rezimu ma VZDY prednost - admin uz to jednou
    # rucne overil a ulozil, takze se uz znovu nehleda v GTFS/Nominatim.
    ov = STOP_OVERRIDES.get(key)
    if ov:
        return (ov["lat"], ov["lng"]), "manual"

    if not GTFS_STOPS:
        return None, None

    wants_train = _name_suggests_train(name)
    target_mode = 'train' if wants_train else 'bus'

    def mode_ok(idx):
        m = GTFS_MODES[idx] if idx < len(GTFS_MODES) else None
        return (not m) or (m == 'mixed') or (m == target_mode)

    def pick_best(idxs):
        if not idxs:
            return None
        # Mezi kandidaty preferuj spravny rezim dopravy (bus/train) - pokud
        # aspon jeden vyhovuje, omez se na ne; jinak pouzij vsechny (radsi
        # nepresny rezim nez nic).
        preferred = [i for i in idxs if mode_ok(i)]
        pool = preferred if preferred else idxs
        if not anchor or len(pool) == 1:
            _, la, lo = GTFS_STOPS[pool[0]]
            if anchor:
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
    if exact_idxs and idxs_have_mode_ok(exact_idxs):
        result = pick_best(exact_idxs)
        if result:
            return result, "exact"

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
            result = pick_best(fuzzy_matches)
            if result:
                return result, "fuzzy"

    # 3) "Zachranny" krok: presna/fuzzy shoda existuje, ale JEN spatneho
    # rezimu (typicky: hledas bus zastavku, ale jedine co se nase\u0161lo pod
    # timhle jmenem je vlakova stanice). Zkus jeste volnejsi shodu (Jaccard
    # >= 0.4) MEZI KANDIDATY CO MAJI ASPON JEDNO SPOLECNE SLOVO, ale jen
    # pokud jsou opravdu blizko (do 3 km) te spatne-rezimove shody - tim se
    # najde napr. "Trpisty, Hospoda"/"Trpisty, rozcesti" (bus) co lezi
    # kousek od vlakove stanice "Trpisty", i kdyz se presne nazvy neshoduji.
    fallback_idxs = exact_idxs or fuzzy_matches
    if fallback_idxs and not idxs_have_mode_ok(fallback_idxs):
        wrong_mode_coords = pick_best(fallback_idxs)  # bez mode filtru by tohle vratilo spatny rezim, ale souradnice potrebujeme jako kotvu
        # pick_best uz mode-preferuje, takze pro ziskani SAMOTNE spatne-rezimove
        # kotvy pouzijeme primy vypocet bez filtru:
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
                result = pick_best(rescue)
                if result:
                    return result, "fuzzy"
        # Zachranny krok nic nenasel - radsi puvodni (spatneho rezimu) shoda nez nic
        if exact_idxs:
            result = pick_best(exact_idxs)
            if result:
                return result, "exact"
        if fuzzy_matches:
            result = pick_best(fuzzy_matches)
            if result:
                return result, "fuzzy"

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
                     ghost_spz=None, ghost_verified=False):
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
    try:
        db.table("bus_history").upsert({
            "trip_id": c["trip_id"], "spz": spz, "spz_verified": c.get("spz_verified", False),
            "linka": final_linka, "jr_link": jr_l, "start_scheduled": c.get("first_dep_time"),
            "start_actual": c.get("actual_start_time"), "end_actual": c.get("actual_end_time"),
            "last_lat": c.get("lat"), "last_lng": c.get("lng"), "status": c.get("status"),
            "created_at": c["created_at"].isoformat(), "updated_at": get_prague_time().isoformat(),
        }).execute()
    except Exception as e:
        print(f"[MAPA-DB CHYBA] {spz}: {e}")


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
    TRIP_COUNTER = int(time.time())

    while True:
        try:
            now = get_prague_time()
            if db_client and (now - last_db_cleanup).total_seconds() > 86400:
                last_db_cleanup = now

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
            except Exception:
                pass

            current_inflow_ids = set()

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
                                del GLOBAL_BUS_CACHE[best_gid]
                                if db_client and ghost_spz and ghost_spz != "Nezn\u00e1m\u00e1":
                                    close_previous_trips(db_client, ghost_spz, ghost_trip_id, now.strftime('%H:%M'))
                            GLOBAL_BUS_CACHE[bus_id] = new_cache_entry(
                                bus_id, ghost_trip_id, lat1, lng1, line, dest1, is_train, delay, now,
                                ghost_spz, ghost_verified)

                        else:
                            c = GLOBAL_BUS_CACHE[bus_id]
                            c["last_inflow_seen"] = now
                            c["is_offline"] = False
                            c["raw_delay"] = delay
                            c["is_train"] = is_train
                            dm = math.hypot(lat1 - c["lat"], lng1 - c["lng"])

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
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                if bus_id not in current_inflow_ids:
                    if om > 1080:
                        upsert_to_history(db_client, c)
                        del GLOBAL_BUS_CACHE[bus_id]
                        continue
                    c["is_offline"] = True
                    spz_ok = bool(c.get("spz") and c.get("spz") != "Nezn\u00e1m\u00e1")
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
                if c.get("is_offline"):
                    fld = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c["is_train"] else "Nezn\u00e1m\u00e1")
                    new_live_data.append({
                        "id": bus_id, "trip_id": c["trip_id"], "lat": c["lat"], "lng": c["lng"],
                        "bearing": c.get("bearing"), "line": fld, "delay": 0,
                        "destination": c["destination"], "spz": c["spz"] or "Nezn\u00e1m\u00e1",
                        "spz_verified": c.get("spz_verified", False), "is_train": c["is_train"],
                        "status": c["status"], "color_class": c["color_class"],
                        "inactive_minutes": inact,
                        "last_updated": c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A",
                        "investigating": False, "investigation_spz": "",
                        "admin_flag": c.get("admin_flag", False), "admin_note": c.get("admin_note", ""),
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
                #               nebo spz_frozen s platnou SPZ (po dojeti na konečnou)
                has_valid_spz = bool(c.get("spz") and c.get("spz") != "Nezn\u00e1m\u00e1")
                # Nikdy nezamrazuj bus bez SPZ - vozovna/konečná si má SPZ pamatovat
                # ale bus který odjel a stále nemá SPZ musí hledat dál
                if c.get("spz_frozen") and not has_valid_spz:
                    c["spz_frozen"] = False
                skip_spz = (is_train or c.get("investigating") or c.get("manual_spz")
                            or c.get("bug_locked")
                            or (c.get("spz_frozen") and has_valid_spz and inact > 2))
                if not skip_spz:
                    d1_norm = _norm_txt(dest1)
                    near_stop = _nearest_stop_name(lat1, lng1, ARRIVA_STOP_MATCH_M) if GTFS_LOADED else None
                    near_stop_norm = _norm_txt(near_stop) if near_stop else ""

                    # Sestav gate_pass (přísné brány: linka+pozice+cíl+zastávka)
                    gate_pass = {}
                    for b in data_arriva:
                        if not _arriva_line_matches(line, b):
                            continue
                        b_spz = (b.get("spz") or "").strip()
                        if not b_spz or b_spz == "Nezn\u00e1m\u00e1":
                            continue
                        dist_m = haversine_m(lat1, lng1, b.get("latitude") or 0, b.get("longitude") or 0)
                        if dist_m > ARRIVA_MATCH_DIST_M:
                            continue
                        a_dest_norm = _norm_txt(b.get("destinationName", ""))
                        if d1_norm and a_dest_norm:
                            if d1_norm not in a_dest_norm and a_dest_norm not in d1_norm:
                                continue
                        if near_stop_norm:
                            a_stop_norm = _norm_txt(b.get("lastStopName", ""))
                            if a_stop_norm and near_stop_norm not in a_stop_norm and a_stop_norm not in near_stop_norm:
                                continue
                        if b_spz not in gate_pass or dist_m < gate_pass[b_spz]:
                            gate_pass[b_spz] = dist_m

                    # FALLBACK pro bus ZCELA BEZ SPZ: pokud přísné brány nic nenašly,
                    # zkus jen linka+pozice (bez cíle a zastávky) - na začátku jízdy
                    # nebo po výjezdu z vozovny jsou tato data nespolehlivá.
                    # Bezpečná protože: jen pro bus bez SPZ (nepřepíše dobrou SPZ)
                    # a distanční filtr je přísnější (500m místo 750m).
                    if not gate_pass and not has_valid_spz:
                        for b in data_arriva:
                            if not _arriva_line_matches(line, b):
                                continue
                            b_spz = (b.get("spz") or "").strip()
                            if not b_spz or b_spz == "Nezn\u00e1m\u00e1":
                                continue
                            dist_m = haversine_m(lat1, lng1, b.get("latitude") or 0, b.get("longitude") or 0)
                            if dist_m > 500:
                                continue
                            if b_spz not in gate_pass or dist_m < gate_pass[b_spz]:
                                gate_pass[b_spz] = dist_m

                    current_spz = c.get("spz")
                    was_locked = bool(c.get("spz_locked"))
                    # Nekonzistentni stav: spz_locked=True ale SPZ je None/Neznama.
                    # Stava se kdyz "Stoji prilis dlouho" zamkne zamek driv nez
                    # SPZ vubec stihne dojit (bus cekal na prvnim zastaveni).
                    # -> Povaz za NEzamcene, at search step muze SPZ nalezt.
                    if was_locked and (not current_spz or current_spz == "Nezn\u00e1m\u00e1"):
                        was_locked = False
                        c["spz_locked"] = False

                    # ── 1) Re-audit jiz zamknute SPZ - ALE jen obcas (nizsi priorita) ──
                    # Jakmile uz SPZ ma fajfku (overeno), nehrozi tolik a nema smysl ji
                    # kontrolovat porad - staci obcas (SPZ_REAUDIT_INTERVAL_SEC), at se
                    # vykon vetsinou venuje hledani u jeste NEoverenych busu. Presto se
                    # i overene SPZ jednou za cas znovu prubehnou (bezpecnostni sitko proti
                    # tomu, aby se nahodou nezasekla spatna SPZ navzdy - presne to, co se
                    # delo pred touto opravou).
                    if was_locked and current_spz and current_spz != "Nezn\u00e1m\u00e1":
                        last_audit = c.get("spz_last_audit_check")
                        due_for_audit = (not last_audit) or (now - last_audit).total_seconds() >= SPZ_REAUDIT_INTERVAL_SEC
                        if due_for_audit:
                            c["spz_last_audit_check"] = now
                            if current_spz in gate_pass:
                                c["spz_last_verified"] = now  # stale sedi -> refresh
                            else:
                                still_listed = any((b.get("spz") or "").strip() == current_spz for b in data_arriva)
                                last_v = c.get("spz_last_verified")
                                stale = (not last_v) or (now - last_v).total_seconds() >= SPZ_HOLD_MINUTES * 60
                                if still_listed or stale:
                                    # SPZ uz nesedi (jede jinym smerem/jinym cilem) nebo dlouho nepotvrzena
                                    # -> uvolni zamek, system hleda spravnou SPZ znovu
                                    print(f"[SPZ] Uvolnuji spatnou SPZ {current_spz} u busu {bus_id}", flush=True)
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
                                    c["spz_stable_ticks"] = 0
                                    was_locked = False
                        # else: throttled - tenhle tik se uz overena SPZ vubec neresi

                    # ── 2) Hledani (noveho) kandidata (jen kdyz neni platny zamek) ──
                    if not was_locked:
                        best_spz = min(gate_pass, key=gate_pass.get) if gate_pass else None
                        if best_spz:
                            # Jednoznacny + blizky zasah (jediny kandidat presel vsemi branami
                            # A je opravdu blizko) = okamzity zamek hned napoprve - rychlejsi.
                            # Vicero kandidatu nebo jen hranicni vzdalenost = pojistka 2 tiky
                            # (SPZ_STABLE_TICKS), aby se nezamykalo nahodou spatne.
                            ambiguous = len(gate_pass) > 1
                            high_confidence = (not ambiguous) and gate_pass[best_spz] <= SPZ_HIGH_CONFIDENCE_DIST_M
                            if best_spz == current_spz:
                                c["spz_stable_ticks"] = c.get("spz_stable_ticks", 0) + 1
                            else:
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
                            c["spz_last_verified"] = now
                            if high_confidence or c.get("spz_stable_ticks", 0) >= SPZ_STABLE_TICKS:
                                c["spz_verified"] = True
                                c["spz_locked"] = True
                        else:
                            # Zadny kandidat nesplnil vsechny podminky
                            last_v = c.get("spz_last_verified")
                            if not last_v or (now - last_v).total_seconds() >= SPZ_HOLD_MINUTES * 60:
                                c["spz_verified"] = False
                                c["spz_locked"] = False

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
                })

            global LIVE_BUSES_DATA
            LIVE_BUSES_DATA = new_live_data
            time.sleep(10)

        except Exception as crash_error:
            print(f"[MAPA CRITICAL] {crash_error}", flush=True)
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
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
  <style>
    *{margin:0;padding:0;box-sizing:border-box;}
    html,body{width:100%;height:100%;overflow:hidden;background:#0f172a;color:white;}
    #map-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;}
    #map{position:absolute;top:0;left:0;width:100%;height:100%!important;min-height:100vh;z-index:1;}
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

    elif action == "reset_admin":
        c["manual_spz"] = False
        c["spz_locked"] = False
        c["spz_verified"] = False
        c["spz_stable_ticks"] = 0
        c["spz_frozen"] = False
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
    gtfs_keys = {r["key"] for r in results}
    for key, ov in STOP_OVERRIDES.items():
        if key in gtfs_keys:
            continue  # uz pokryto pres GTFS zaznam vyse (override se aplikuje pozdeji v endpointu)
        la, lo = ov.get("lat"), ov.get("lng")
        if la is None or lo is None:
            continue
        if not (south <= la <= north and west <= lo <= east):
            continue
        results.append({
            "key": key, "name": ov.get("name") or key, "lat": la, "lng": lo,
            "mode": None, "lines": ov.get("custom_lines") or [],
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
        ov = STOP_OVERRIDES.get(key)
        eff_lat = ov["lat"] if ov else s["lat"]
        eff_lng = ov["lng"] if ov else s["lng"]
        # Linky: custom_lines (rucne nastavene) maji prednost pred GTFS
        eff_lines = ov["custom_lines"] if (ov and ov.get("custom_lines") is not None) else s.get("lines", [])
        flag = CONFIDENCE_LOG.get(key)
        flagged = bool(flag and flag.get("confidence") in ("fuzzy", "geocoded", "none"))
        stops_out.append({
            "name": s["name"],
            "display_name": (ov.get("display_name") or "") if ov else "",
            "lat": eff_lat, "lng": eff_lng,
            "mode": s.get("mode"), "lines": eff_lines,
            "manual": bool(ov), "flagged": flagged,
            "approx": bool(ov and ov.get("approx")),
            "substitute": bool(ov and ov.get("substitute")),
        })

    return jsonify({"status": "success", "stops": stops_out, "count": len(stops_out)})


@mapa_bp.route('/api/stops_in_view')
def api_stops_in_view():
    """Verejny endpoint pro 'Zobrazit zastavky' + klik na zastávku = linky."""
    bbox = _parse_bbox_args()
    if not bbox:
        return jsonify({"status": "error", "message": "Chyb\u00ed/\u0161patn\u00e9 sou\u0159adnice v\u00fdezu"}), 400
    items, err = _bbox_stops(*bbox)
    if err:
        return jsonify({"status": "error", "message": err})

    stops_out = []
    for s in items:
        key = s["key"]
        ov = STOP_OVERRIDES.get(key)
        eff_lat = ov["lat"] if ov else s["lat"]
        eff_lng = ov["lng"] if ov else s["lng"]
        eff_lines = ov["custom_lines"] if (ov and ov.get("custom_lines") is not None) else s.get("lines", [])
        stops_out.append({
            "name": s["name"],
            "display_name": (ov.get("display_name") or "") if ov else "",
            "lat": eff_lat, "lng": eff_lng,
            "mode": s.get("mode"), "lines": eff_lines,
            "approx": bool(ov and ov.get("approx")),
            "substitute": bool(ov and ov.get("substitute")),
        })

    return jsonify({"status": "success", "stops": stops_out, "count": len(stops_out)})


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

    key = _norm_txt(name)
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

    STOP_OVERRIDES[key] = {
        "lat": lat, "lng": lng, "name": name,
        "approx": approx, "substitute": substitute,
        "display_name": display_name,
        "custom_lines": custom_lines,
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
                "updated_at": get_prague_time().isoformat(),
            }, on_conflict="stop_name").execute()
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
    if not name:
        return jsonify({"status": "error", "message": "Chyb\u00ed n\u00e1zev zast\u00e1vky"}), 400
    key = _norm_txt(name)
    STOP_OVERRIDES.pop(key, None)
    db = get_db_client()
    if db:
        try:
            db.table("stop_overrides").delete().eq("stop_name", name).execute()
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
    if not stop_name or not line_str:
        return jsonify({"status": "error", "message": "Chyb\u00ed n\u00e1zev zast\u00e1vky nebo linky"}), 400

    key = _norm_txt(stop_name)
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
    cur_lines = list(ov.get("custom_lines") or []) if ov else []
    if not cur_lines:
        # Zacni s GTFS linkami jako zakladem
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
    STOP_OVERRIDES[key] = {
        "lat": lat, "lng": lng, "name": stop_name,
        "approx": existing.get("approx", False),
        "substitute": existing.get("substitute", False),
        "display_name": existing.get("display_name", ""),
        "custom_lines": cur_lines,
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
                "updated_at": get_prague_time().isoformat(),
            }, on_conflict="stop_name").execute()
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
<div style="overflow-x:auto;"><style>table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:6px 10px;text-align:left}}th{{background:#0f172a;color:#38bdf8}}tr:hover td{{background:#1e293b}}.current{{background:#166534!important;font-weight:bold}}</style>{tt_html}</div></div>"""
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
        return jsonify({"data": [], "error": "DB nedostupn\u00e1"})
    try:
        res = db.table("bus_history").select("*").eq("spz", spz).order("created_at", desc=True).limit(100).execute()
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)})

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
            coords, conf = _lookup_stop_coords(name_c, anchor=anchor)

        if coords:
            seen[name_c] = coords
            anchor = coords
            ov = STOP_OVERRIDES.get(_norm_txt(name_c))
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
        ov = STOP_OVERRIDES.get(key)
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
    return jsonify({
        "stops": result,
        "bus_id": bus_id,
        "found": found,
        "total": len(result),
        "gtfs_hits": gtfs_hits,
        "fuzzy_hits": fuzzy_hits,
        "nominatim_hits": nominatim_hits,
    })
