import os
import time
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, Response, render_template_string, request, session, redirect
from zoneinfo import ZoneInfo
import math
import re
import http.cookiejar

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    print("[MAPA-WARN] Modul 'supabase' není dostupný! Historie se neuloží.")

mapa_bp = Blueprint('mapa_bp', __name__)

# ─── KONFIGURACE SPZ LOGIKY ──────────────────────────────────────────────────
SPZ_HOLD_MINUTES       = 8
SPZ_STABLE_TICKS       = 2
GHOST_MAX_OFFLINE_MIN  = 20
GHOST_DIST_STRICT      = 0.010
GHOST_DIST_LOOSE       = 0.030
ARRIVA_MATCH_DIST      = 0.008
DUPLICATE_GRACE_SEC    = 120
# ─────────────────────────────────────────────────────────────────────────────

HTML_HISTORIE_INDEX = """
<div style="padding: 20px; max-width: 1500px; margin: auto; font-family: sans-serif;">
  <div style="background-color: #dc2626; color: white; padding: 12px; border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 18px; font-size: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2px solid #991b1b;">
    <i class="fas fa-exclamation-triangle fa-fade"></i> !!! DATA NEMUSÍ SEDĚT - STRÁNKA JE VE VÝVOJI !!!
  </div>

  <details style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:12px 16px; margin-bottom:16px; cursor:pointer;">
    <summary style="color:#f59e0b; font-weight:bold; font-size:13px; user-select:none;">
      <i class="fas fa-info-circle"></i>&nbsp; Proč systém občas vynechá záznamy? (klikni pro více info)
    </summary>
    <div style="color:#94a3b8; font-size:12px; margin-top:10px; line-height:1.7;">
      <p style="margin:0 0 6px 0;"><strong style="color:#fff;">Zaznamenaná SPZ může být:</strong></p>
      <ul style="margin:0 0 10px 0; padding-left:20px;">
        <li><span style="color:#f59e0b;">✓ Ověřená</span> – Arriva i Inflow souhlasily 2× po sobě. Vysoce spolehlivé.</li>
        <li><span style="color:#94a3b8;">~ Odhad</span> – SPZ z ghost matchingu (vozovna, ranní výjezd). Může se lišit.</li>
      </ul>
      <p style="margin:0 0 6px 0;"><strong style="color:#fff;">Proč chybí záznamy:</strong></p>
      <ul style="margin:0; padding-left:20px;">
        <li>Arriva API pomalá nebo nevrátila bus → SPZ se nepáruje</li>
        <li>Restart mapy uprostřed spoje → ztráta kontextu, nový trip_id</li>
        <li>Ranní výjezd z vozovny před spuštěním mapy → první spoj chybí</li>
        <li>Jsou zaznamenávány <strong>pouze linky 490xxx a 496xxx</strong> – ostatní záměrně vynechány</li>
      </ul>
    </div>
  </details>

  <div id="statsBar" style="display:flex; gap:14px; flex-wrap:wrap; margin-bottom:18px;"></div>

  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
    <h2 style="color: #38bdf8; margin: 0; font-size: 22px;"><i class="fas fa-database"></i> Databáze Sledovaných Vozů</h2>
    <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
      <select id="filterLine" style="background:#1e293b; color:white; border:1px solid #334155; border-radius:6px; padding:7px 10px; font-size:13px;">
        <option value="">Všechny linky</option>
        <option value="490">Linka 490</option>
        <option value="496">Linka 496</option>
      </select>
      <select id="filterStatus" style="background:#1e293b; color:white; border:1px solid #334155; border-radius:6px; padding:7px 10px; font-size:13px;">
        <option value="">Všechny stavy</option>
        <option value="Probíhá">Probíhá</option>
        <option value="depo">V depu / Přes noc</option>
        <option value="Ukončeno">Ukončeno</option>
      </select>
      <input id="historySearch" type="text" placeholder="Hledat SPZ, linku..." style="background:#1e293b; color:white; border:1px solid #334155; border-radius:6px; padding:7px 12px; font-size:13px; min-width:200px;">
    </div>
  </div>

  <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
    <table style="width:100%; border-collapse:collapse; color:#cbd5e1; min-width:950px;">
      <thead>
        <tr style="background: #0f172a;">
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:left;">Datum</th>
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:left;">SPZ Vozu</th>
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:left;">Linka</th>
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:left;">Čas (Plán → Reál)</th>
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:left;">Status / Konec</th>
          <th style="color:#38bdf8; padding:11px 14px; border-bottom:1px solid #334155; text-align:center;">Akce</th>
        </tr>
      </thead>
      <tbody id="historyTableBody">
        <tr><td colspan="6" style="text-align:center; padding:30px; color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Načítám...</td></tr>
      </tbody>
    </table>
  </div>
  <p style="color:#64748b; font-size:11px; margin-top:8px;">* Neomezená historie záznamů. Aktualizace každých 10s.</p>

  <script>
  let allData = [];
  function buildFreqMap(data) {
    const freq = {};
    data.forEach(row => {
      const spz = row.spz || 'Neznámá';
      if (spz === 'Neznámá') return;
      const lineBase = (row.linka || '').replace(/[/].*/g, '').trim().replace(/\\D/g, '');
      const key = spz + '_' + lineBase;
      freq[key] = (freq[key] || 0) + 1;
    });
    return freq;
  }
  function renderStats(data) {
    const spzSet = new Set(data.filter(r=>r.spz&&r.spz!=='Neznámá').map(r=>r.spz));
    const total  = data.length;
    const active = data.filter(r=>!r.end_actual&&!r.status?.includes('Timeout')&&!r.status?.includes('depu')).length;
    const depot  = data.filter(r=>r.status?.includes('depu')||r.status?.includes('Vozovn')).length;
    document.getElementById('statsBar').innerHTML = `
      <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;">
        <div style="color:#38bdf8;font-size:22px;font-weight:900;">${total}</div>
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;">Záznamů</div>
      </div>
      <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;">
        <div style="color:#f59e0b;font-size:22px;font-weight:900;">${spzSet.size}</div>
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;">Unikátních SPZ</div>
      </div>
      <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;">
        <div style="color:#10b981;font-size:22px;font-weight:900;">${active}</div>
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;">Probíhá</div>
      </div>
      <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;">
        <div style="color:#64748b;font-size:22px;font-weight:900;">${depot}</div>
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;">V depu</div>
      </div>`;
  }
  function applyFilters() {
    const search     = document.getElementById('historySearch').value.toLowerCase().trim();
    const filterLine = document.getElementById('filterLine').value;
    const filterStat = document.getElementById('filterStatus').value;
    document.querySelectorAll('#historyTableBody tr[data-search]').forEach(row => {
      const txt    = row.getAttribute('data-search') || '';
      const linka  = row.getAttribute('data-linka')  || '';
      const status = row.getAttribute('data-status')  || '';
      let vis = true;
      if (search     && !txt.includes(search))        vis = false;
      if (filterLine && !linka.includes(filterLine))  vis = false;
      if (filterStat === 'Probíhá' && !status.includes('probíhá') && !status.includes('jede') && !status.includes('čeká')) vis = false;
      if (filterStat === 'depo'    && !status.includes('depu') && !status.includes('vozov')) vis = false;
      if (filterStat === 'Ukončeno' && !status.includes('konec') && !status.includes('timeout') && !status.includes('ukončen')) vis = false;
      row.style.display = vis ? '' : 'none';
    });
  }
  async function loadIndex() {
    try {
      const response = await fetch('/api/history_full');
      const result   = await response.json();
      allData        = result.data || [];
      const freq     = buildFreqMap(allData);
      renderStats(allData);
      const tbody = document.getElementById('historyTableBody');
      if (allData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#64748b;">Zatím žádné záznamy pro linky 490/496.</td></tr>';
        return;
      }
      let newHtml = '';
      allData.forEach(row => {
        const d = new Date(row.created_at);
        const dayStr = d.toLocaleDateString('cs-CZ');
        const spz    = row.spz || 'Neznámá';
        const linka  = row.linka || '---';
        const lineBase = linka.replace(/\\/.*/, '').trim().replace(/\\D/g, '');
        const freqKey  = spz + '_' + lineBase;
        const runCnt   = row.run_count || freq[freqKey] || 0;
        let spzBadge = '';
        if (spz === 'Neznámá') {
          spzBadge = `<span style="background:#334155;color:#94a3b8;padding:3px 8px;border-radius:4px;font-size:12px;"><i class="fas fa-question-circle" style="margin-right:4px;"></i>Neznámá</span>`;
        } else if (row.status?.includes('Falešný')) {
          spzBadge = `<span style="background:#ef4444;color:white;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold;">${spz} ✗</span>`;
        } else {
          spzBadge = `<span style="background:#f59e0b;color:#0f172a;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold;">${spz} ✓</span>`;
        }
        let freqBadge = '';
        if (runCnt >= 10) freqBadge = `<br><span style="background:#7c3aed;color:white;padding:1px 6px;border-radius:10px;font-size:10px;margin-top:3px;display:inline-block;"><i class="fas fa-star"></i> Stálý vůz (${runCnt}×)</span>`;
        else if (runCnt >= 5) freqBadge = `<br><span style="background:#0284c7;color:white;padding:1px 6px;border-radius:10px;font-size:10px;margin-top:3px;display:inline-block;"><i class="fas fa-redo"></i> Častá linka (${runCnt}×)</span>`;
        else if (runCnt >= 3) freqBadge = `<br><span style="background:#334155;color:#94a3b8;padding:1px 6px;border-radius:10px;font-size:10px;margin-top:3px;display:inline-block;">${runCnt}× na této lince</span>`;
        let startStr = '<span style="color:#64748b;">---</span>';
        if (row.start_scheduled || row.start_actual) {
          startStr = `<span style="color:#64748b;">${row.start_scheduled || '?'}</span> → <strong style="color:#10b981;">${row.start_actual || 'Čeká'}</strong>`;
        }
        const inDepot = row.status?.includes('depu') || row.status?.includes('Vozovn');
        const isEnd   = row.end_actual || row.status?.includes('Timeout') || row.status?.includes('Ukončen');
        let statusColor = '#eab308';
        let endLabel    = '<i class="fas fa-spinner fa-pulse" style="margin-right:4px;"></i>Probíhá';
        if (inDepot) { statusColor = '#64748b'; endLabel = '<i class="fas fa-warehouse" style="margin-right:4px;"></i>V depu'; }
        else if (isEnd) { statusColor = '#ef4444'; endLabel = row.end_actual || 'Ukončeno'; }
        const statusHtml = `<div style="color:#94a3b8;font-size:11px;margin-bottom:2px;">${row.status||''}</div><div style="color:${statusColor};font-weight:bold;font-size:13px;">${endLabel}</div>`;
        const rowText   = `${spz} ${linka} ${row.status||''}`.toLowerCase();
        const rowStatus = (row.status||'').toLowerCase();
        newHtml += `
          <tr style="border-bottom:1px solid #334155;" data-search="${rowText}" data-linka="${lineBase}" data-status="${rowStatus}">
            <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${dayStr}<br><span style="color:#475569;font-size:10px;">${(row.trip_id||'').substring(0,10)}…</span></td>
            <td style="padding:11px 14px;vertical-align:middle;">${spzBadge}${freqBadge}</td>
            <td style="padding:11px 14px;vertical-align:middle;"><strong style="color:white;">${linka}</strong>${row.jr_link?`<br><a href="${row.jr_link}" target="_blank" style="font-size:11px;color:#38bdf8;">JŘ <i class="fas fa-external-link-alt"></i></a>`:''}</td>
            <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${startStr}</td>
            <td style="padding:11px 14px;vertical-align:middle;">${statusHtml}</td>
            <td style="padding:11px 14px;vertical-align:middle;text-align:center;">
              ${spz !== 'Neznámá' ? `<a href="/historie/${spz}" style="background:#38bdf8;color:#0f172a;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:bold;text-decoration:none;"><i class="fas fa-list"></i> Detail vozu</a>` : `<span style="color:#475569;font-size:11px;">Čeká na SPZ</span>`}
            </td>
          </tr>`;
      });
      tbody.innerHTML = newHtml;
      applyFilters();
    } catch(e) { console.error(e); }
  }
  document.getElementById('historySearch').addEventListener('input', applyFilters);
  document.getElementById('filterLine').addEventListener('change', applyFilters);
  document.getElementById('filterStatus').addEventListener('change', applyFilters);
  loadIndex();
  setInterval(loadIndex, 10000);
  </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
"""

HTML_HISTORIE_DETAIL = """
<div style="padding: 20px; max-width: 1000px; margin: auto; font-family: sans-serif;">
  <a href="/historie" class="button is-small is-dark" style="margin-bottom: 15px;"><i class="fas fa-arrow-left"></i> Zpět na seznam</a>
  <div style="background-color: #dc2626; color: white; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 20px; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2px solid #991b1b;">
    <i class="fas fa-exclamation-triangle fa-fade"></i> !!! DATA NEMUSÍ SEDĚT - STRÁNKA JE VE VÝVOJI !!!
  </div>
  <div style="background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #38bdf8; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
    <h2 style="color: white; margin: 0 0 10px 0; font-size: 28px;">Autobus SPZ: <span style="color:#f59e0b;">__SPZ__</span></h2>
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 15px;">Historie odjetých linek (Sledováno od přidělení 490/496).</p>
    <div id="absoluteLastPos"><span style="color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Načítám polohu...</span></div>
  </div>
  <h3 style="color: #38bdf8; margin-bottom: 15px; font-size: 20px;"><i class="fas fa-route"></i> Odjeté spoje</h3>
  <div style="background: #0f172a; border-radius: 10px; border: 1px solid #334155; overflow-x: auto;">
    <table class="table is-fullwidth" style="background: transparent; color: #cbd5e1; margin-bottom: 0;">
      <thead>
        <tr style="background: #1e293b;">
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Datum / Spoj ID</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Začátek trasy</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Konec / Poslední status</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Mapa</th>
        </tr>
      </thead>
      <tbody id="detailTableBody">
        <tr><td colspan="5" style="text-align:center; padding: 30px; color: #38bdf8;"><i class="fas fa-spinner fa-spin"></i> Stahuji data...</td></tr>
      </tbody>
    </table>
  </div>
  <script>
  const PAGE_SPZ = '__SPZ__';
  async function loadDetail() {
    try {
      const response = await fetch('/api/history_spz/' + PAGE_SPZ);
      const result = await response.json();
      const data = result.data || [];
      const liveRes = await fetch('/api/live_buses');
      const liveData = await liveRes.json();
      const liveBus = liveData.buses ? liveData.buses.find(b => b.spz === PAGE_SPZ) : null;
      const tbody = document.getElementById('detailTableBody');
      const lastPosDiv = document.getElementById('absoluteLastPos');
      if (data.length === 0 && !liveBus) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Žádná historie nebyla nalezena.</td></tr>';
        lastPosDiv.innerHTML = '<span style="color:#ef4444;">Poloha neznámá</span>';
        return;
      }
      let currentLat = 0, currentLng = 0, topStatus = "", topTime = "", liveIndicator = "";
      if (liveBus && liveBus.lat) {
        currentLat = liveBus.lat; currentLng = liveBus.lng;
        topStatus = liveBus.status + ' (' + (liveBus.line || 'Bez linky') + ')';
        topTime = "Nyní (Živá data z mapy)";
        liveIndicator = `<br><span style="color:#10b981; font-weight:bold; font-size:13px;"><i class="fas fa-satellite-dish"></i> Živě na mapě</span>`;
      } else if (data.length > 0) {
        const newest = data[0];
        currentLat = newest.last_lat; currentLng = newest.last_lng;
        topStatus = newest.status + ' (' + (newest.linka || 'Bez linky') + ')';
        const nd = new Date(newest.updated_at || newest.created_at);
        topTime = nd.toLocaleDateString('cs-CZ') + ' ' + nd.toLocaleTimeString('cs-CZ');
        liveIndicator = `<br><span style="color:#94a3b8; font-size:13px;"><i class="fas fa-database"></i> Historie</span>`;
      }
      lastPosDiv.innerHTML = `<div style="display:flex; align-items:center; gap: 15px;"><div style="flex-grow: 1;"><strong style="color: white; font-size:16px;">Stav vozidla:</strong> <span style="font-size:16px;">${topStatus}</span><br><span style="color: #cbd5e1; font-size: 14px;">Zaznamenáno: ${topTime}</span>${liveIndicator}</div><a href="/mapa#${currentLat},${currentLng}" class="button is-info is-medium" style="font-weight:bold;"><i class="fas fa-crosshairs" style="margin-right: 8px;"></i> Ukázat na mapě</a></div>`;
      let newHtml = '';
      data.forEach(trip => {
        const cd = new Date(trip.created_at);
        const dayStr = cd.toLocaleDateString('cs-CZ');
        let startStr = trip.start_actual ? trip.start_actual : (trip.start_scheduled ? `<span style="color:#94a3b8;">${trip.start_scheduled} (Plán)</span>` : "---");
        let isFinished = trip.end_actual || trip.status.includes('Timeout');
        let endStr = isFinished
          ? `${trip.end_actual || 'Timeout'} <br><span style="font-size:11px; color:#94a3b8;">(${trip.status})</span>`
          : `<span style="color:#eab308; font-weight:bold;"><i class="fas fa-spinner fa-pulse"></i> Probíhá...</span><br><span style="font-size:11px; color:#94a3b8;">${trip.status}</span>`;
        newHtml += `<tr style="border-color: #334155;"><td style="border-color: #334155; padding: 12px; vertical-align: middle; color:#cbd5e1;">${dayStr}<br><span style="font-size:10px; color:#64748b;">${trip.trip_id.substring(0,8)}...</span></td><td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${trip.linka}${trip.jr_link ? `<br><a href="${trip.jr_link}" target="_blank" style="font-size:11px; color:#38bdf8;">Aktuální JŘ <i class="fas fa-external-link-alt"></i></a>` : ''}</td><td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #10b981;">${startStr}</td><td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #ef4444;">${endStr}</td><td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;"><a href="/mapa#${trip.last_lat},${trip.last_lng}" class="button is-small is-outlined" style="background: transparent; color: #cbd5e1; border-color: #4b5563;"><i class="fas fa-map-marker-alt"></i> Mapa</a></td></tr>`;
      });
      tbody.innerHTML = newHtml;
    } catch(e) { console.error(e); }
  }
  loadDetail();
  setInterval(loadDetail, 10000);
  </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
"""

HTML_MAPA = """
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100%;height:100%;overflow:hidden;background:#0f172a;}
#map-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;}
#map{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;}
#panel-zone{position:fixed;top:0;left:0;right:0;height:40px;z-index:3000;pointer-events:none;}
#top-nav{
  position:fixed;top:-72px;left:0;right:0;height:58px;
  background:rgba(8,16,30,0.97);border-bottom:1px solid #334155;
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  z-index:2999;transition:top 0.3s cubic-bezier(.4,0,.2,1);
  display:flex;align-items:center;padding:0 14px;gap:10px;
  box-shadow:0 4px 24px rgba(0,0,0,0.7);
}
#top-nav.vis{top:0;}
.n-logo{display:flex;align-items:center;text-decoration:none;flex-shrink:0;}
.n-logo img{height:34px;width:auto;filter:drop-shadow(0 0 7px rgba(56,189,248,.55));}
.n-title{flex-shrink:0;line-height:1.2;}
.n-title .a{color:#38bdf8;font-size:15px;font-weight:800;letter-spacing:.4px;}
.n-title .b{color:#64748b;font-size:10px;}
.n-warn{background:#f59e0b;color:#0f172a;padding:3px 8px;border-radius:5px;font-size:11px;font-weight:bold;white-space:nowrap;flex-shrink:0;}
.n-sp{flex:1;}
.n-clock{color:#38bdf8;font-size:13px;font-weight:bold;background:rgba(56,189,248,.08);padding:5px 10px;border-radius:6px;border:1px solid #334155;white-space:nowrap;flex-shrink:0;}
.n-btn{padding:6px 11px;border-radius:6px;font-weight:bold;text-decoration:none;font-size:12px;flex-shrink:0;white-space:nowrap;transition:.2s;}
.n-home{background:#38bdf8;color:#0f172a;}.n-home:hover{background:#0284c7;color:#fff;}
.n-provoz{background:#334155;color:#fff;}.n-provoz:hover{background:#475569;}
.n-ad{background:#1e3a5f;color:#38bdf8;border:1px solid #334155;}.n-ad:hover{background:#1e40af;color:#fff;}
.n-back{background:#ef4444;color:#fff;}.n-back:hover{background:#dc2626;}
#nav-handle{position:fixed;top:0;left:50%;transform:translateX(-50%);
  width:90px;height:7px;background:rgba(56,189,248,.55);border-radius:0 0 8px 8px;
  z-index:3001;cursor:pointer;transition:opacity .3s,background .2s,width .2s;}
#nav-handle:hover{background:rgba(56,189,248,.95);width:130px;}
#nav-handle.hid{opacity:0;pointer-events:none;}
/* ─── POPUP ─── */
.dark-popup .leaflet-popup-content-wrapper{background:#1e293b;color:#fff;border:1px solid #334155;padding:0;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.65);}
.dark-popup .leaflet-popup-tip{background:#1e293b;}
.dark-popup .leaflet-popup-content{margin:0;width:292px!important;}
.ph{background:#0f172a;padding:10px 13px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center;}
.ph-t{font-weight:bold;color:#38bdf8;font-size:15px;margin:0;}
.pb{padding:11px 13px;font-size:13px;line-height:1.6;}
.pr{display:flex;justify-content:space-between;margin-bottom:5px;border-bottom:1px dashed #334155;padding-bottom:3px;}
.pr:last-child{border-bottom:none;}
.pl{color:#94a3b8;font-weight:600;}.pv{font-weight:bold;text-align:right;max-width:60%;word-wrap:break-word;}
.spz-b{background:#f59e0b;color:#0f172a;padding:2px 6px;border-radius:4px;font-size:12px;border:1px solid #d97706;}
.pa{background:#38bdf8;color:#0f172a;border:none;padding:8px;width:100%;border-radius:5px;font-weight:bold;cursor:pointer;transition:.2s;margin-top:7px;display:block;text-align:center;font-size:12px;}
.pa:hover{background:#0284c7;color:#fff;}
.pa-d{background:#334155;color:#fff;}.pa-d:hover{background:#475569;}
/* ─── FOLLOW HUD ─── */
#hud{display:none;position:fixed;bottom:18px;right:18px;z-index:4000;font-family:'Segoe UI',sans-serif;}
#hf{background:#1e293b;border:2px solid #38bdf8;border-radius:12px;padding:13px;width:248px;box-shadow:0 8px 28px rgba(0,0,0,.75);}
#hm{display:none;background:#1e293b;border:2px solid #38bdf8;border-radius:50px;padding:6px 12px;align-items:center;gap:8px;box-shadow:0 4px 15px rgba(0,0,0,.5);}
#hm button{background:none;border:none;cursor:pointer;font-size:18px;padding:2px 5px;border-radius:4px;transition:.2s;}
.hh{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;}
.hl{color:#38bdf8;font-size:10px;font-weight:bold;letter-spacing:.5px;}
.ht{color:#94a3b8;font-size:11px;margin-bottom:1px;}
.hd{color:#fff;font-size:16px;font-weight:bold;margin-bottom:6px;line-height:1.2;}
.hr{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:4px;}
.hac{display:flex;gap:5px;margin-top:9px;}
.hb{flex:1;padding:7px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:bold;transition:.2s;}
.hb-jr{background:#38bdf8;color:#0f172a;}.hb-jr:hover{background:#0284c7;color:#fff;}
.hb-st{background:#ef4444;color:#fff;}.hb-st:hover{background:#dc2626;}
.hb-mn{background:none;border:1px solid #334155;color:#94a3b8;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:14px;transition:.2s;}
.hb-mn:hover{border-color:#38bdf8;color:#38bdf8;}
/* ─── STARTUP WARNING ─── */
#sw{display:none;position:fixed;top:68px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#991b1b,#ef4444);color:#fff;padding:11px 18px;border-radius:10px;font-weight:bold;z-index:5000;text-align:center;max-width:92vw;width:410px;box-shadow:0 4px 25px rgba(239,68,68,.55);animation:swPulse 2s ease-in-out infinite alternate;}
@keyframes swPulse{0%{box-shadow:0 4px 20px rgba(239,68,68,.4);}100%{box-shadow:0 4px 45px rgba(239,68,68,.9);}}
/* ─── JŘ MODAL ─── */
#ttm{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.72);z-index:6000;align-items:center;justify-content:center;}
#ttm.open{display:flex;}
#ttb{background:#0f172a;border-radius:10px;padding:20px;max-width:700px;width:95%;border:1px solid #38bdf8;max-height:86vh;overflow-y:auto;position:relative;}
#ttc-btn{position:absolute;top:10px;right:10px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;font-weight:bold;}
#spz-results .sr-item{padding:8px 12px;cursor:pointer;font-size:12px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:8px;}
#spz-results .sr-item:hover{background:#334155;}
#spz-results .sr-item:last-child{border-bottom:none;}
@media(max-width:768px){
  #top-nav{gap:5px;padding:0 6px;height:auto;min-height:52px;flex-wrap:wrap;padding-bottom:5px;padding-top:5px;}
  .n-title{display:none;}
  .n-warn{display:none;}
  .n-clock{font-size:10px;padding:4px 6px;}
  .n-btn{font-size:10px;padding:4px 6px;}
  #spz-search-inp{width:100px;font-size:11px;}
  #hf{width:210px;}
  .dark-popup .leaflet-popup-content{width:252px!important;}
}
@media(max-width:420px){
  .n-provoz{display:none;}
  #spz-search-inp{width:85px;}
}
</style>

<div id="map-wrap">
  <div id="panel-zone"></div>
  <div id="nav-handle" title="Klikni pro zobrazení navigace"></div>

  <nav id="top-nav">
    <a href="https://datacorebot.koyeb.app/" class="n-logo">
      <img src="https://tdonrppusbwhoftdontz.supabase.co/storage/v1/object/public/logo/datacorebot%20n.png" alt="OIS IDPK">
    </a>
    <div class="n-title">
      <div class="a"><i class="fas fa-map-marked-alt"></i> Interaktivní mapa</div>
      <div class="b">Projekt OIS IDPK &nbsp;·&nbsp; Neoficiální</div>
    </div>
    <div class="n-warn">⚠ Není garantována 100% přesnost dat</div>
    <div class="n-sp"></div>
    <div id="admin-mode-badge" style="display:none;background:rgba(56,189,248,0.15);color:#38bdf8;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold;border:1px solid rgba(56,189,248,0.35);white-space:nowrap;flex-shrink:0;">⚙ Admin</div>
    <div class="n-clock">🕐 <span id="systemTimeClock">--:--:--</span></div>
    <a href="https://datacorebot.koyeb.app/" class="n-btn n-home">🏠 Domů</a>
    <a href="/provoz-idpk" class="n-btn n-provoz">🚌 IDPK</a>
    __AD_BTN__
    <div style="position:relative;flex-shrink:0;" id="spz-search-wrap">
      <input id="spz-search-inp" type="text" placeholder="🔍 Hledat SPZ…"
        style="background:#0f172a;color:white;border:1px solid #334155;border-radius:6px;padding:5px 10px;font-size:12px;width:130px;outline:none;"
        oninput="spzSearch(this.value)" onblur="setTimeout(()=>document.getElementById('spz-results').innerHTML='',200)">
      <div id="spz-results" style="position:absolute;top:34px;right:0;background:#1e293b;border:1px solid #334155;border-radius:8px;min-width:230px;z-index:4000;box-shadow:0 8px 20px rgba(0,0,0,.7);max-height:220px;overflow-y:auto;"></div>
    </div>
  </nav>

  __ADMIN_BANNER__

  <div id="map"></div>

  <div id="sw">
    <div style="font-size:17px;margin-bottom:3px;">⚠️ Mapa se startuje</div>
    <div style="font-size:12px;font-weight:normal;opacity:.9;">Probíhá načítání dat — vyčkejte prosím.</div>
    <div id="sw-cd" style="margin-top:5px;font-size:11px;opacity:.8;"></div>
  </div>

  <div id="ttm">
    <div id="ttb">
      <button id="ttc-btn" onclick="document.getElementById('ttm').classList.remove('open')">✕</button>
      <div id="ttc" style="color:white;">Načítám...</div>
    </div>
  </div>

  <div id="hud">
    <div id="hf">
      <div class="hh"><span class="hl">📡 SLEDOVÁNÍ SPOJE</span><button class="hb-mn" onclick="minHud()" title="Minimalizovat">−</button></div>
      <div id="h-trip" class="ht">Spoj: —</div>
      <div id="h-dest" class="hd">Načítám...</div>
      <div class="hr"><span style="color:#94a3b8;">SPZ:</span><span id="h-spz">—</span></div>
      <div class="hr"><span style="color:#94a3b8;">Zpoždění:</span><span id="h-delay">—</span></div>
      <div class="hr"><span style="color:#94a3b8;">Status:</span><span id="h-status" style="color:#94a3b8;font-size:11px;">—</span></div>
      <div class="hac">
        <button class="hb hb-jr" id="h-jr">📋 JŘ</button>
        <button class="hb hb-st" onclick="stopFollow()">✕ Konec</button>
      </div>
    </div>
    <div id="hm">
      <span style="color:#38bdf8;font-size:12px;font-weight:bold;">📡</span>
      <span id="hm-line" style="color:#fff;font-size:12px;font-weight:bold;"></span>
      <button onclick="maxHud()" style="color:#10b981;" title="Rozbalit">＋</button>
      <button onclick="stopFollow()" style="color:#ef4444;" title="Zastavit">✕</button>
    </div>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const IS_ADMIN = __IS_ADMIN__;

// ─── ADMIN ACTIONS ────────────────────────────────────────────────────────────
async function adminAction(action, busId, extraData = {}) {
    saveAdminInputs();  // Ulož hodnoty inputů před odesláním
    showAdminToast('⏳ Odesílám…', true);
    try {
        let res = await fetch('/api/admin/map_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, bus_id: busId, ...extraData })
        });
        let data = await res.json();
        if (data.status === 'success') {
            showAdminToast('✅ Uloženo — systém zpracovává', true);
            setTimeout(() => {
                // Smaž cache pro tento bus po aplikaci
                if (action === 'reset_admin' || action === 'recheck_spz') {
                    Object.keys(adminInputCache).forEach(k => { if(k.endsWith('_'+busId)) delete adminInputCache[k]; });
                }
                fetchBuses();
            }, 800);
        } else {
            showAdminToast('❌ Chyba: ' + (data.message || 'neznámá'), false);
        }
    } catch(e) { showAdminToast('❌ Chyba spojení', false); }
}
window.adminDelete   = (id) => { if(confirm('Smazat tečku z mapy? Znovu se zobrazí až při novém spoji.')) { adminAction('delete', id); openPopupBusId = null; } };
window.adminRecheck  = (id) => adminAction('recheck_spz', id);
window.adminSetSPZ   = (id) => { let spz = document.getElementById('adm_spz_' + id)?.value; if(spz) adminAction('edit_spz', id, {spz}); };
window.adminSetStatus = (id) => {
    let st  = document.getElementById('adm_st_'  + id)?.value?.trim() || '';
    let col = document.getElementById('adm_col_' + id)?.value?.trim() || '';
    if (!st && !col) { showAdminToast('⚠ Zadej status nebo vyber barvu', false); return; }
    adminAction('edit_status', id, {status: st, color_class: col});
};
window.adminSaveAll = (id, permanent) => {
    let st   = document.getElementById('adm_st_'   + id)?.value?.trim() || '';
    let col  = document.getElementById('adm_col_'  + id)?.value?.trim() || '';
    let note = document.getElementById('adm_note_' + id)?.value?.trim() || '';
    if (!st && !col && !note) { showAdminToast('⚠ Nic k uložení', false); return; }
    let typ = permanent ? 'trvalá 🔒' : 'dočasná ⏵';
    adminAction('edit_all', id, {status: st, color_class: col, note: note, permanent: permanent});
    showAdminToast('⏳ Ukládám (' + typ + ')…');
};

// ─── PANEL ────────────────────────────────────────────────────────────────────
const nav    = document.getElementById('top-nav');
const handle = document.getElementById('nav-handle');
let hideT = null;
function showNav(dur){ clearTimeout(hideT); nav.classList.add('vis'); handle.classList.add('hid'); if(dur) hideT=setTimeout(hideNav,dur); }
function hideNav(){ nav.classList.remove('vis'); handle.classList.remove('hid'); }
handle.addEventListener('click', () => showNav(5000));
document.addEventListener('mousemove', e=>{ if(e.clientY < 6) showNav(); },{passive:true});
nav.addEventListener('mouseenter', ()=> clearTimeout(hideT));
nav.addEventListener('mouseleave', ()=>{ hideT=setTimeout(hideNav,600); });
document.addEventListener('touchstart', e=>{
  if(e.touches[0].clientY < 35){ showNav(4500); }
  else if(!nav.contains(e.target)){ clearTimeout(hideT); hideT=setTimeout(hideNav,400); }
},{passive:true});
showNav(4000);
if (IS_ADMIN) {
  let ab = document.getElementById('admin-mode-badge');
  if (ab) ab.style.display = 'block';
}

// ─── MAP ──────────────────────────────────────────────────────────────────────
var dLat=49.7384, dLng=13.3736, dZoom=12;
var hp = window.location.hash.replace('#','').split(',');
if(hp.length===2 && !isNaN(hp[0]) && !isNaN(hp[1]) && hp[0] !== "" && hp[1] !== ""){ dLat=parseFloat(hp[0]); dLng=parseFloat(hp[1]); dZoom=17; }
var map = L.map('map',{zoomControl:false}).setView([dLat,dLng],dZoom);
L.control.zoom({position:'bottomleft'}).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
setTimeout(()=>map.invalidateSize(),300); // Oprava případného tmavého ekranu
var ml = L.layerGroup().addTo(map);
if(hp.length===2 && !isNaN(hp[0]) && !isNaN(hp[1]) && hp[0] !== "" && hp[1] !== "") L.circleMarker([dLat,dLng],{radius:28,color:'#ef4444',weight:2,opacity:.8,fillOpacity:.12}).addTo(map);

// ─── HUD + FOLLOW ─────────────────────────────────────────────────────────────
let lastArr=[], followId=null, hudMin=false, followInflowId=null;
let openPopupBusId = null;  // Sleduje který popup je otevřený

function stopFollow(){ followId=null; followInflowId=null; hudMin=false; document.getElementById('hud').style.display='none'; document.getElementById('hf').style.display='block'; document.getElementById('hm').style.display='none'; }
function minHud(){ hudMin=true; document.getElementById('hf').style.display='none'; document.getElementById('hm').style.display='flex'; }
function maxHud(){ hudMin=false; document.getElementById('hf').style.display='block'; document.getElementById('hm').style.display='none'; }

window.toggleFollow = function(busId, inflowId){
  if(followId===busId){ stopFollow(); return; }
  followId=busId; followInflowId=inflowId||busId;
  let b=lastArr.find(x=>x.id===busId);
  if(b&&b.lat) map.setView([b.lat,b.lng],16);
  document.getElementById('hud').style.display='block';
  updateHud(b);
  if(hudMin){ document.getElementById('hf').style.display='none'; document.getElementById('hm').style.display='flex'; }
}

function updateHud(b){
  if(!b) return;
  let trip = (b.line||'?') + (b.trip_id ? ' · '+b.trip_id.replace('TRIP-','').substring(0,8) : '');
  document.getElementById('h-trip').textContent = 'Spoj: '+trip;
  document.getElementById('h-dest').innerHTML = '→&nbsp;'+(b.destination||'Neznámý cíl');
  let se=document.getElementById('h-spz');
  if(b.spz&&b.spz!=='Neznámá'){
    let icon=b.spz_verified?'✔':'⏳', bg=b.spz_verified?'#f59e0b':'#f97316';
    se.innerHTML=`<span style="background:${bg};color:#0f172a;padding:1px 6px;border-radius:4px;font-weight:bold;">${b.spz} ${icon}</span>`;
  } else { se.innerHTML='<span style="color:#64748b;">Čeká...</span>'; }
  let de=document.getElementById('h-delay'), dv=parseInt(b.delay);
  if(b.color_class==='bg-blue'){ let dm=Math.abs(dv),dh=Math.floor(dm/60),dmin=dm%60; de.innerHTML=`<span style="color:#3b82f6;">Odjezd za ${dh>0?dh+'h ':''} ${dmin}min</span>`; }
  else if(b.color_class==='bg-darkblue'){ de.innerHTML=`<span style="color:#60a5fa;">Náskok ${Math.abs(dv)} min</span>`; }
  else if(b.color_class==='bg-orange'){ de.innerHTML=`<span style="color:#f59e0b;"><i class="fas fa-search"></i> Výzkum</span>`; }
  else if(dv>=5){ de.innerHTML=`<span style="color:#ef4444;">+${dv} min</span>`; }
  else if(dv<-1){ de.innerHTML=`<span style="color:#60a5fa;">−${Math.abs(dv)} min</span>`; }
  else { de.innerHTML='<span style="color:#10b981;">V čase</span>'; }
  document.getElementById('h-status').textContent=b.status||'—';
  document.getElementById('hm-line').textContent='L'+(b.line||'?');
  let jrBtn=document.getElementById('h-jr');
  jrBtn.onclick=()=>showTT(followInflowId||b.id);
}

// ─── JŘ MODAL ─────────────────────────────────────────────────────────────────
async function showTT(busId){
  document.getElementById('ttm').classList.add('open');
  document.getElementById('ttc').innerHTML="<div style='text-align:center;padding:40px;color:#38bdf8;'><i class='fas fa-circle-notch fa-spin fa-2x'></i><p style='margin-top:14px;font-weight:bold;'>Načítám JŘ z PVVD...</p></div>";
  try{ let r=await fetch('/api/bus_detail/'+busId); document.getElementById('ttc').innerHTML=await r.text(); }
  catch(e){ document.getElementById('ttc').innerHTML="<p style='color:#ef4444;padding:20px;text-align:center;'>Chyba při načítání JŘ.</p>"; }
}

// ─── STARTUP WARNING ──────────────────────────────────────────────────────────
let swShown=false, pageLoad=Date.now();
function checkSW(uptimeSec){
  let sw=document.getElementById('sw');
  if(uptimeSec<600&&(Date.now()-pageLoad)<660000){
    if(!swShown){ swShown=true; sw.style.display='block'; }
    let rem=Math.max(0,Math.round(600-uptimeSec));
    document.getElementById('sw-cd').textContent=rem>0?'Přibližně '+rem+'s do plného načtení':'Dokončuji...';
  } else { sw.style.display='none'; swShown=false; }
}

// ─── MARKER SVG BUILDER ───────────────────────────────────────────────────────
function buildMarkerSvg(mc, bearing, lineText, isTrain) {
  const colorMap = {
    'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6',
    'bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7',
    'bg-orange':'#f59e0b','bg-bug':'#374151'
  };
  const bgColor  = colorMap[mc] || '#64748b';
  const textFill = (mc === 'bg-orange') ? '#0f172a' : '#ffffff';

  // Číslo linky: číselná část, max 4 znaky
  // Vezmi část před '/', pak poslední 3 číslice (490735/15 → 490735 → 735)
  let lineClean = (lineText || '').split('/')[0].trim();
  let lineNum = lineClean.replace(/[^0-9]/g, '');
  let lineDisplay = lineNum.length >= 4 ? lineNum.slice(-3) : lineNum;

  const cx = 18, cy = 18, r = isTrain ? 10 : 12;
  let svgInner = '';

  // ── Šipka VNĚ kolečka ────────────────────────────────────────────────────
  const hasBearing = bearing !== null && bearing !== undefined
                  && !['bg-gray','bg-purple','bg-bug'].includes(mc)
                  && !isTrain;
  if (hasBearing) {
    const rad = (bearing * Math.PI) / 180;
    const arrowTipDist  = r + 10;  // špička šipky – vzdálenost od středu
    const arrowBaseDist = r - 1;   // základna šipky – u okraje kolečka
    const bHalf = 5;               // polovina šířky základny

    const tipX = +(cx + Math.sin(rad) * arrowTipDist).toFixed(2);
    const tipY = +(cy - Math.cos(rad) * arrowTipDist).toFixed(2);

    const bMidX = cx + Math.sin(rad) * arrowBaseDist;
    const bMidY = cy - Math.cos(rad) * arrowBaseDist;
    const pRad  = rad + Math.PI / 2;

    const b1X = +(bMidX + Math.sin(pRad) * bHalf).toFixed(2);
    const b1Y = +(bMidY - Math.cos(pRad) * bHalf).toFixed(2);
    const b2X = +(bMidX - Math.sin(pRad) * bHalf).toFixed(2);
    const b2Y = +(bMidY + Math.cos(pRad) * bHalf).toFixed(2);

    svgInner += `<polygon points="${tipX},${tipY} ${b1X},${b1Y} ${b2X},${b2Y}" fill="${bgColor}" stroke="white" stroke-width="1.5" stroke-linejoin="round" opacity="0.95"/>`;
  }

  // ── Stín ─────────────────────────────────────────────────────────────────
  svgInner += `<circle cx="${cx+1}" cy="${cy+1}" r="${r}" fill="rgba(0,0,0,0.3)"/>`;

  // ── Hlavní kolečko / čtverec ──────────────────────────────────────────────
  if (isTrain) {
    svgInner += `<rect x="${cx-r}" y="${cy-r}" width="${r*2}" height="${r*2}" rx="3" fill="${bgColor}" stroke="white" stroke-width="2"/>`;
  } else {
    // Bug: přerušovaný okraj
    const dashStyle = mc === 'bg-bug' ? 'stroke-dasharray="3,2"' : '';
    svgInner += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${bgColor}" stroke="white" stroke-width="2" ${dashStyle} opacity="${mc==='bg-bug'?0.7:1}"/>`;
  }

  // ── Číslo linky ───────────────────────────────────────────────────────────
  if (lineDisplay && !isTrain && mc !== 'bg-bug') {
    if (lineDisplay.length > 3) {
      // dvouřádkové
      svgInner += `<text x="${cx}" y="${cy-2.5}" dominant-baseline="middle" text-anchor="middle" fill="${textFill}" font-weight="bold" font-size="7" font-family="'Segoe UI',system-ui,sans-serif">${lineDisplay.substring(0,3)}</text>`;
      svgInner += `<text x="${cx}" y="${cy+5.5}" dominant-baseline="middle" text-anchor="middle" fill="${textFill}" font-weight="bold" font-size="6" font-family="'Segoe UI',system-ui,sans-serif">${lineDisplay.substring(3)}</text>`;
    } else {
      svgInner += `<text x="${cx}" y="${cy+1}" dominant-baseline="middle" text-anchor="middle" fill="${textFill}" font-weight="bold" font-size="8" font-family="'Segoe UI',system-ui,sans-serif">${lineDisplay}</text>`;
    }
  }

  return `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;display:block;">${svgInner}</svg>`;
}

// ─── ADMIN INPUT CACHE ───────────────────────────────────────────────────────
// Zachová hodnoty admin inputů přes 10s refresh
let adminInputCache = {};
function saveAdminInputs() {
  if (!IS_ADMIN) return;
  document.querySelectorAll('[id^="adm_spz_"]').forEach(el => {
    if (el.value !== el.getAttribute('data-orig')) adminInputCache['spz_' + el.id.replace('adm_spz_','')] = el.value;
  });
  document.querySelectorAll('[id^="adm_st_"]').forEach(el => {
    if (el.value !== el.getAttribute('data-orig')) adminInputCache['st_' + el.id.replace('adm_st_','')] = el.value;
  });
  document.querySelectorAll('[id^="adm_note_"]').forEach(el => {
    adminInputCache['note_' + el.id.replace('adm_note_','')] = el.value;
  });
}
function restoreAdminInput(busId, fieldType) {
  let key = fieldType + '_' + busId;
  let v = adminInputCache[key];
  return (v !== undefined && v !== null) ? v : null;
}

// ─── ADMIN TOAST ──────────────────────────────────────────────────────────────
let _toastTimer = null;
function showAdminToast(msg, ok = true) {
  let t = document.getElementById('admin-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'admin-toast';
    t.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;padding:9px 20px;font-size:12px;font-weight:bold;z-index:9999;border-radius:20px;white-space:nowrap;transition:opacity .4s;pointer-events:none;';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.color = ok ? '#10b981' : '#ef4444';
  t.style.borderColor = ok ? '#10b981' : '#ef4444';
  t.style.border = '1px solid ' + (ok ? '#10b981' : '#ef4444');
  t.style.opacity = '1';
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { t.style.opacity = '0'; }, 3500);
}

// ─── ROUTE DISPLAY ───────────────────────────────────────────────────────────
var routeLayer = L.layerGroup().addTo(map);
let activeRouteId = null;

async function toggleRoute(busId) {
  if (activeRouteId === busId) {
    routeLayer.clearLayers();
    activeRouteId = null;
    let btn = document.getElementById('route-btn-' + busId);
    if (btn) { btn.textContent = '🛤 Zobrazit trasu'; btn.style.background = '#334155'; }
    return;
  }
  routeLayer.clearLayers();
  activeRouteId = busId;
  let btn = document.getElementById('route-btn-' + busId);
  if (btn) { btn.textContent = '⏳ Načítám trasu…'; btn.style.background = '#1e3a8a'; }
  try {
    let r = await fetch('/api/bus_route/' + busId);
    let data = await r.json();
    if (!data.stops || data.stops.length < 2) {
      if (btn) { btn.textContent = '⚠ Trasa nedostupná'; btn.style.background = '#7f1d1d'; }
      return;
    }
    const colorMap = {'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-bug':'#374151'};
    let bus = lastArr.find(b => b.id === busId);
    let lineColor = bus ? (colorMap[bus.color_class] || '#38bdf8') : '#38bdf8';

    // Zastávky jako markery
    data.stops.forEach((stop, i) => {
      if (!stop.lat || !stop.lng) return;
      let isPassed = stop.passed;
      let dotColor = isPassed ? '#475569' : lineColor;
      let stopIcon = L.divIcon({
        className: '',
        html: `<div style="width:8px;height:8px;border-radius:50%;background:${dotColor};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.5);"></div>`,
        iconSize: [8,8], iconAnchor: [4,4]
      });
      let marker = L.marker([stop.lat, stop.lng], {icon: stopIcon, zIndexOffset: -100});
      marker.bindTooltip(`<b>${stop.name}</b>${stop.time ? ' · ' + stop.time : ''}`, {direction:'top', className:'dark-popup'});
      routeLayer.addLayer(marker);
    });

    // Linie mezi zastávkami
    let coords = data.stops.filter(s => s.lat && s.lng).map(s => [s.lat, s.lng]);
    if (coords.length >= 2) {
      let polyline = L.polyline(coords, {color: lineColor, weight: 3, opacity: 0.75, dashArray: '6,4'});
      routeLayer.addLayer(polyline);
      // Zvýrazni absolvovanou část
      let passedCoords = data.stops.filter(s => s.lat && s.lng && s.passed).map(s => [s.lat, s.lng]);
      if (passedCoords.length >= 2) {
        L.polyline(passedCoords, {color: '#475569', weight: 3, opacity: 0.5}).addTo(routeLayer);
      }
    }

    if (btn) { btn.textContent = '🛤 Skrýt trasu'; btn.style.background = '#1e40af'; }
    // Fit map to route
    if (btn) { btn.textContent = '🛤 Skrýt trasu (' + data.stops.filter(s=>s.lat).length + ' zast.)'; btn.style.background = '#1e40af'; }
  } catch(e) {
    if (btn) { btn.textContent = '⚠ Chyba načítání'; btn.style.background = '#7f1d1d'; }
    console.error('Route error:', e);
  }
}

// ─── SPZ SEARCH ──────────────────────────────────────────────────────────────
function spzSearch(val) {
  let box = document.getElementById('spz-results');
  val = val.trim().toUpperCase();
  if (val.length < 2) { box.innerHTML = ''; return; }
  let matches = lastArr.filter(b => b.spz && b.spz !== 'Neznámá' && b.spz.toUpperCase().includes(val));
  if (matches.length === 0) {
    box.innerHTML = '<div style="padding:10px;color:#64748b;font-size:12px;text-align:center;">Žádné výsledky</div>';
    return;
  }
  const colorMap = {'bg-green':'#10b981','bg-red':'#ef4444','bg-blue':'#3b82f6','bg-darkblue':'#1e3a8a','bg-gray':'#64748b','bg-purple':'#a855f7','bg-orange':'#f59e0b','bg-bug':'#374151'};
  box.innerHTML = matches.slice(0,8).map(b => {
    let clr = colorMap[b.color_class] || '#64748b';
    return `<div class="sr-item" onclick="zoomToSpz(${b.lat},${b.lng},'${b.id}')">
      <div style="width:10px;height:10px;border-radius:50%;background:${clr};flex-shrink:0;"></div>
      <div>
        <strong style="color:#f59e0b;">${b.spz}</strong>
        <span style="color:#94a3b8;margin-left:5px;">L${b.line||'?'}</span>
        <br><span style="color:#64748b;font-size:10px;">${b.status||''}</span>
      </div>
    </div>`;
  }).join('');
}
function zoomToSpz(lat, lng, busId) {
  document.getElementById('spz-results').innerHTML = '';
  document.getElementById('spz-search-inp').value = '';
  map.setView([lat, lng], 16);
  // Otevři popup tohoto busu
  setTimeout(() => {
    ml.eachLayer(layer => { if (layer._busId === busId) layer.openPopup(); });
  }, 200);
}

// ─── MAIN FETCH ───────────────────────────────────────────────────────────────
async function fetchBuses(){
  try{
    let r=await fetch('/api/live_buses'), data=await r.json();
    if(data.server_time) document.getElementById('systemTimeClock').innerText=data.server_time;
    if(typeof data.worker_uptime_seconds==='number') checkSW(data.worker_uptime_seconds);
    if(data.status!=='success') return;
    lastArr=data.buses;

    // Sleduj pozici následovaného busu
    if(followId){
      let fb=data.buses.find(b=>b.id===followId);
      if(fb&&fb.lat){ map.setView([fb.lat,fb.lng]); if(!hudMin) updateHud(fb); else document.getElementById('hm-line').textContent='L'+(fb.line||'?'); }
      else document.getElementById('h-status').textContent='⚠ Ztráta signálu';
    }

    // Ulož admin inputs + bus_id otevřeného popupu před clearLayers
    saveAdminInputs();
    let savedOpenId = openPopupBusId;
    let isRefreshing = true;
    ml.clearLayers();

    data.buses.forEach(bus=>{
      if(!bus.lat||!bus.lng) return;
      let mc=bus.color_class, dv=parseInt(bus.delay), dTxt='';
      if(mc==='bg-gray'||mc==='bg-bug') dTxt='<span style="color:#94a3b8;">N/A</span>';
      else if(mc==='bg-purple') dTxt='<span style="color:#a855f7;">Konečná</span>';
      else if(mc==='bg-orange') dTxt='<span style="color:#f59e0b;"><i class="fas fa-search"></i> Výzkum</span>';
      else if(mc==='bg-blue'){ let dm=Math.abs(dv),dh=Math.floor(dm/60),dmn=dm%60,ts=dh>0?dh+'h '+dmn+'m':dmn+' min'; dTxt=`<span style="color:#3b82f6;">Za ${ts}</span>`; }
      else if(mc==='bg-darkblue'){ dTxt=`<span style="color:#60a5fa;">Náskok ${Math.abs(dv)} min</span>`; }
      else if(dv>=5){ dTxt=`<span style="color:#ef4444;">Zpoždění ${dv} min</span>`; }
      else { dTxt=`<span style="color:#10b981;">+${dv} min</span>`; }

      // ── SVG marker: šipka vně + číslo linky ──
      let svgHtml = buildMarkerSvg(mc, bus.bearing, bus.line, bus.is_train);
      let icon = L.divIcon({ className: '', html: svgHtml, iconSize:[36,36], iconAnchor:[18,18], popupAnchor:[0,-20] });
      let marker = L.marker([bus.lat, bus.lng], {icon});

      // Sledování otevřeného popupu
      marker._busId = bus.id;
      marker.on('popupopen',  () => { openPopupBusId = bus.id; });
      marker.on('popupclose', () => {
        if(openPopupBusId===bus.id) openPopupBusId=null;
        // Skryj trasu jen kdyz NENI zpusobeno 10s refreshem
        if(!isRefreshing && activeRouteId===bus.id){ routeLayer.clearLayers(); activeRouteId=null; }
      }); // Opravená závorka pro popupclose

      // ── Popup obsah ──────────────────────────────────────────────────────
      let spzH='', invTxt='', histBtn='';
      if(!bus.is_train){
        if(bus.investigating){
          spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv spz-b" style="background:#ef4444;color:#fff;border-color:#b91c1c;"><i class="fas fa-search"></i> Výzkum</span></div>`;
          invTxt=`<div style="color:#ef4444;font-size:10px;font-weight:bold;margin:4px 0;">⚠ Zjišťuji SPZ (${bus.investigation_spz})</div>`;
        } else if(bus.spz&&bus.spz!=='Neznámá'){
          let vi=bus.spz_verified?'✔':'⏳', vs=bus.spz_verified?'spz-b':'spz-b" style="background:#f97316;color:#fff;border-color:#c2410c;';
          spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv ${vs}">${bus.spz} ${vi}</span></div>`;
          if(bus.spz_verified) histBtn=`<a href="/historie/${bus.spz}" target="_blank" class="pa pa-d" style="margin-top:5px;"><i class="fas fa-history"></i> Historie vozu</a>`;
        } else { spzH=`<div class="pr"><span class="pl">SPZ:</span><span class="pv" style="color:#64748b;">Čeká na ověření</span></div>`; }
      }
      let bugW='';
      if(mc==='bg-bug'){
        let bugSpz=(bus.spz_verified&&bus.spz&&bus.spz!=='Neznámá')?bus.spz:'Neznámá SPZ';
        bugW=`<div style="background:#374151;border:1px dashed #6b7280;border-radius:5px;padding:7px;margin:5px 0;color:#9ca3af;font-size:10px;text-align:center;"><i class="fas fa-exclamation-triangle" style="color:#f59e0b;"></i> <b style="color:#f59e0b;">BUG – NEAKTUÁLNÍ MÍSTO</b><br>SPZ <b>${bugSpz}</b> jede na jiném místě.</div>`;
      }
      let orangeW='';
      if(mc==='bg-orange') orangeW=`<div style="background:rgba(245,158,11,.15);border:1px solid #f59e0b;border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:#f59e0b;"><i class="fas fa-search"></i> <b>Výzkum – bus byl zaseknutý, nyní jede</b></div>`;
      let sc='#10b981';
      if(mc==='bg-bug') sc='#6b7280'; else if(mc==='bg-orange') sc='#f59e0b';
      else if(bus.status.includes('příliš')) sc='#94a3b8';
      else if(bus.status.includes('Stojí')) sc='#ef4444';
      else if(bus.status.includes('Konečná')||bus.status.includes('Ztráta')) sc='#a855f7';
      else if(bus.status.includes('Čeká')||bus.status.includes('Začátek')) sc='#3b82f6';
      else if(bus.status.includes('Odstaven')||bus.status.includes('signál')) sc='#94a3b8';
      else if(bus.status.includes('Náskok')) sc='#60a5fa';
      let fTxt=(followId===bus.id)?'✕ Zrušit sledování':'📡 Sledovat';
      let fSt=(followId===bus.id)?'background:#ef4444;color:#fff;':'background:#3b82f6;color:#fff;';

      let adminFlagHtml = bus.admin_flag ? '<span style="background:#1e40af;color:#93c5fd;padding:2px 7px;border-radius:10px;font-size:10px;margin-left:6px;font-weight:bold;"><i class="fas fa-shield-alt"></i> Admin úprava</span>' : '';
      let popH=`
        <div class="ph" style="${mc==='bg-bug'?'background:#1f2937;':''}${mc==='bg-orange'?'background:#1c1400;':''}">
          <h3 class="ph-t" style="${mc==='bg-bug'?'color:#9ca3af;':''}${mc==='bg-orange'?'color:#f59e0b;':''}"><i class="${bus.is_train?'fas fa-train':'fas fa-bus'}"></i> Linka ${bus.line}${adminFlagHtml}</h3>
        </div>
        <div class="pb">
          ${bugW}${orangeW}
          ${bus.admin_note ? `<div style="background:rgba(147,197,253,0.1);border:1px solid #334155;border-radius:5px;padding:5px 8px;margin-bottom:5px;font-size:11px;color:#93c5fd;"><i class='fas fa-sticky-note' style='margin-right:4px;'></i>${bus.admin_note}</div>` : ''}
          <div class="pr"><span class="pl">Cíl:</span><span class="pv">${bus.destination||'Neznámý'}</span></div>
          ${spzH}${invTxt}
          <div class="pr"><span class="pl">Status:</span><span class="pv" style="color:${sc};">${bus.status}</span></div>
          <div class="pr" style="border:none;"><span class="pl">JŘ:</span><span class="pv">${dTxt}</span></div>
          <button class="pa" onclick="showTT('${bus.id}')"><i class="fas fa-list-alt"></i> Zobrazit Jízdní řád</button>
          <button class="pa" style="${fSt}margin-top:5px;" onclick="toggleFollow('${bus.id}','${bus.id}')">${fTxt}</button>
          ${histBtn}
          <button id="route-btn-${bus.id}" class="pa pa-d" style="margin-top:5px;${activeRouteId===bus.id?'background:#1e40af;':'background:#334155;'}" onclick="toggleRoute('${bus.id}')">${activeRouteId===bus.id?'🛤 Skrýt trasu':'🛤 Zobrazit trasu (exp.)'}</button>
        </div>`;

      // ── Admin overlay ─────────────────────────────────────────────────────
      if(IS_ADMIN){
        let _origSpz  = bus.spz === 'Neznámá' ? '' : bus.spz;
        let _cachedSpz = restoreAdminInput(bus.id, 'spz') ?? _origSpz;
        let _cachedSt  = restoreAdminInput(bus.id, 'st')  ?? bus.status;
        let _cachedNote= restoreAdminInput(bus.id, 'note') ?? (bus.admin_note || '');
        let inputSt = `<style>
          .adm-inp{width:100%;box-sizing:border-box;background:#0f172a;color:white;border:1px solid #334155;border-radius:5px;padding:7px 8px;font-size:12px;margin-top:4px;}
          .adm-inp:focus{outline:none;border-color:#38bdf8;}
          .adm-btn{width:100%;padding:11px;border:none;border-radius:6px;font-size:13px;font-weight:bold;cursor:pointer;margin-top:4px;touch-action:manipulation;}
        </style>`;
        popH += inputSt + `
          <div style="border-top:1px solid #334155;margin-top:6px;padding:10px 13px;background:#0a0f1e;">
            <strong style="color:#38bdf8;font-size:11px;letter-spacing:.5px;">⚙ ADMIN PANEL</strong>
            <div style="display:flex;gap:5px;margin-top:8px;">
              <input type="text" id="adm_spz_${bus.id}" value="${_cachedSpz}" data-orig="${_origSpz}" placeholder="SPZ" class="adm-inp" style="width:55%;margin-top:0;">
              <button onclick="adminSetSPZ('${bus.id}')" style="width:45%;background:#10b981;color:white;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">💾 Uložit</button>
            </div>
            <div style="display:flex;gap:5px;margin-top:5px;">
              <button onclick="adminRecheck('${bus.id}')" style="flex:1;background:#f59e0b;color:#0f172a;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">🔍 Hledat SPZ</button>
              <button onclick="adminDelete('${bus.id}')" style="flex:1;background:#ef4444;color:white;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:7px;touch-action:manipulation;">🗑 Smazat</button>
            </div>
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
              <input type="text" id="adm_st_${bus.id}" value="${_cachedSt}" data-orig="${bus.status}" placeholder="Status text…" class="adm-inp">
              <select id="adm_col_${bus.id}" class="adm-inp" style="margin-top:4px;">
                <option value="">── barva ──</option>
                <option value="bg-gray"     ${bus.color_class==='bg-gray'?'selected':''}>Šedá</option>
                <option value="bg-blue"     ${bus.color_class==='bg-blue'?'selected':''}>Světle modrá</option>
                <option value="bg-darkblue" ${bus.color_class==='bg-darkblue'?'selected':''}>Tmavě modrá</option>
                <option value="bg-green"    ${bus.color_class==='bg-green'?'selected':''}>Zelená</option>
                <option value="bg-red"      ${bus.color_class==='bg-red'?'selected':''}>Červená</option>
                <option value="bg-purple"   ${bus.color_class==='bg-purple'?'selected':''}>Fialová</option>
                <option value="bg-orange"   ${bus.color_class==='bg-orange'?'selected':''}>Oranžová</option>
                <option value="bg-bug"      ${bus.color_class==='bg-bug'?'selected':''}>Bug</option>
              </select>
              <input type="text" id="adm_note_${bus.id}" value="${_cachedNote}" data-orig="${bus.admin_note||''}" placeholder="📝 Poznámka (volitelně)…" class="adm-inp" style="margin-top:4px;">
              <div style="display:flex;gap:5px;margin-top:6px;">
                <button onclick="adminSaveAll('${bus.id}',true)"  class="adm-btn" style="flex:1;background:#1e40af;color:white;">🔒 Trvalá</button>
                <button onclick="adminSaveAll('${bus.id}',false)" class="adm-btn" style="flex:1;background:#334155;color:#94a3b8;">⏵ Dočasná</button>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:7px;padding-top:6px;border-top:1px solid #1e293b;">
              <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:11px;color:#93c5fd;flex:1;touch-action:manipulation;">
                <input type="checkbox" id="adm_flag_${bus.id}" ${bus.admin_flag?'checked':''} onchange="adminAction('set_admin_flag','${bus.id}',{flag:this.checked})" style="width:16px;height:16px;cursor:pointer;">
                <i class="fas fa-shield-alt"></i> Admin úprava
              </label>
              <button onclick="adminAction('reset_admin','${bus.id}')" style="background:transparent;color:#64748b;border:1px solid #334155;border-radius:5px;font-size:11px;cursor:pointer;padding:5px 10px;touch-action:manipulation;">↺ Reset</button>
            </div>
          </div>`;
      }

      marker.bindPopup(popH, {className:'dark-popup', maxWidth:300});
      ml.addLayer(marker);
    });

    // ── Obnoví otevřený popup po refreshi ────────────────────────────────────
    if(savedOpenId){
      ml.eachLayer(layer => {
        if(layer._busId === savedOpenId){
          setTimeout(() => { layer.openPopup(); isRefreshing = false; }, 30);
        }
      });
    } else { isRefreshing = false; }
  }catch(e){console.error(e);}
}
fetchBuses();
setInterval(fetchBuses,10000);
</script>
"""

# --- GLOBÁLNÍ STAV ---
GLOBAL_BUS_CACHE    = {}
LIVE_BUSES_DATA     = []
TRACKED_SPZS        = set()
WORKER_START_TIME   = None
ADMIN_DELETED_BUSES = {}   # bus_id → line při smazání adminem

cj     = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)


def is_same_line(l1, l2):
    if not l1 or not l2 or l1 == "Neznámá" or l2 == "Neznámá":
        return False
    b1 = str(l1).split('/')[0]
    b2 = str(l2).split('/')[0]
    cl1 = re.sub(r'\D', '', b1)
    cl2 = re.sub(r'\D', '', b2)
    if not cl1 or not cl2:
        return b1 == b2
    return cl1.endswith(cl2) or cl2.endswith(cl1)


def get_db_client():
    if not HAS_SUPABASE:
        return None
    supa_url = os.environ.get("SUPABASE_URL")
    supa_key = os.environ.get("SUPABASE_KEY")
    if supa_url and supa_key:
        try:
            return create_client(supa_url, supa_key)
        except Exception:
            return None
    return None


def new_cache_entry(bus_id, trip_id, lat, lng, line, dest, is_train, delay, now,
                    ghost_spz=None, ghost_verified=False):
    return {
        "trip_id":            trip_id,
        "inflow_id":          bus_id,
        "lat":                lat,
        "lng":                lng,
        "bearing":            None,
        "line":               line,
        "real_linka_spoj":    None,
        "destination":        dest,
        "is_train":           is_train,
        "raw_delay":          delay,
        "spz":                ghost_spz,
        "spz_verified":       ghost_verified,
        "spz_locked":         False,
        "manual_spz":         False,
        "spz_stable_ticks":   0,
        "spz_last_verified":  None,
        "investigating":      False,
        "investigation_spz":  None,
        "investigation_start": None,
        "first_seen":         now,
        "last_inflow_seen":   now,
        "last_moved":         now,
        "created_at":         now,
        "actual_start_time":  None,
        "actual_end_time":    None,
        "first_dep_time":     None,
        "last_dep_time":      None,
        "tt_last_fetch":      None,
        "tt_is_fetching":     False,
        "status":             "Načítání...",
        "color_class":        "bg-gray",
        "is_offline":         False,
        "db_first_upsert":    False,
        "_last_db_status":    None,
        "_last_db_linka":     None,
        "_end_written":       False,
        "_was_long_stationary": False,
        "final_delay_display": 0,
        "admin_color_override": None,
        "admin_status_override": None,
        "admin_flag": False,
        "bug_locked": False,
        "admin_lock_display": False,
        "admin_lock_permanent": False,
        "admin_note": "",
    }


def fetch_tt_bg(bus_id, cached_dict):
    try:
        cb_time = int(time.time() * 1000)
        headers = {
            'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':          'https://pvvd.idpk.cz/',
            'Cache-Control':    'no-cache',
        }
        info_url = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb_time}"
        req_info = urllib.request.Request(info_url, headers=headers)
        with opener.open(req_info, timeout=4) as r_info:
            info_html = r_info.read().decode('utf-8')
        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        m_spoj  = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>',  info_html, re.IGNORECASE | re.DOTALL)
        linka_txt = m_linka.group(1).strip() if m_linka else ""
        spoj_txt  = m_spoj.group(1).strip()  if m_spoj  else ""
        if linka_txt and spoj_txt:
            cached_dict["real_linka_spoj"] = f"{linka_txt}/{spoj_txt}"
        tt_url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}"
        req_tt = urllib.request.Request(tt_url, headers=headers)
        with opener.open(req_tt, timeout=4) as r_tt:
            tt_html = r_tt.read().decode('utf-8')
        times = re.findall(r'\b\d{2}:\d{2}\b', tt_html)
        if times:
            cached_dict["first_dep_time"] = times[0]
            cached_dict["last_dep_time"]  = times[-1]
    except Exception:
        pass
    finally:
        cached_dict["tt_is_fetching"] = False


def close_previous_trips(db, spz, current_trip_id, end_time_str):
    if not db or not spz or spz == "Neznámá":
        return
    try:
        open_resp = db.table("bus_history").select("trip_id")\
                      .eq("spz", spz).is_("end_actual", None)\
                      .neq("trip_id", current_trip_id).execute()
        for row in (open_resp.data or []):
            try:
                db.table("bus_history").update({
                    "end_actual":  end_time_str,
                    "status":      "Ukončeno (Nový spoj zahájen)",
                    "updated_at":  get_prague_time().isoformat(),
                }).eq("trip_id", row["trip_id"]).execute()
            except Exception:
                pass
    except Exception:
        pass


def _is_tracked_line(linka_str):
    base = re.sub(r'/.*', '', str(linka_str)).strip()
    num  = re.sub(r'\D', '', base)
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
    spz_verified = c.get("spz_verified", False)
    jr_l = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={c['inflow_id']}&currentStopId=0"
    
    try:
        data = {
            "trip_id":         c["trip_id"],
            "spz":             spz,
            "spz_verified":    spz_verified,
            "linka":           final_linka,
            "jr_link":         jr_l,
            "start_scheduled": c.get("first_dep_time"),
            "start_actual":    c.get("actual_start_time"),
            "end_actual":      c.get("actual_end_time"),
            "last_lat":        c.get("lat"),
            "last_lng":        c.get("lng"),
            "status":          c.get("status"),
            "created_at":      c["created_at"].isoformat(),
            "updated_at":      get_prague_time().isoformat(),
        }
        db.table("bus_history").upsert(data).execute()
    except Exception as e:
        print(f"[MAPA-DB CHYBA] {spz}: {e}")


def background_map_worker():
    global TRACKED_SPZS, WORKER_START_TIME
    print("[MAPA] Worker startuje...", flush=True)
    WORKER_START_TIME = get_prague_time()

    # ── Auto-download GTFS DB z GitHub releases (pokud chybí) ────────────────
    if not os.path.exists(GTFS_DB_PATH):
        try:
            print(f"[GTFS] DB nenalezena, stahuji z {GTFS_RELEASE_URL} ...", flush=True)
            tmp = GTFS_DB_PATH + ".tmp"
            headers = {"User-Agent": "OIS-IDPK/1.0"}
            req = urllib.request.Request(GTFS_RELEASE_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                downloaded = 0
                while True:
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
            os.rename(tmp, GTFS_DB_PATH)
            print(f"[GTFS] Stazeno: {os.path.getsize(GTFS_DB_PATH)//1024//1024} MB", flush=True)
        except Exception as e:
            print(f"[GTFS] Chyba stazování: {e}", flush=True)
            if os.path.exists(GTFS_DB_PATH + ".tmp"):
                os.remove(GTFS_DB_PATH + ".tmp")
    else:
        print(f"[GTFS] DB nalezena: {os.path.getsize(GTFS_DB_PATH)//1024//1024} MB", flush=True)

    db_client = get_db_client()
    if db_client:
        try:
            res = db_client.table("bus_history").select("spz").execute()
            for r in res.data:
                if r.get("spz") and r["spz"] != "Neznámá":
                    TRACKED_SPZS.add(r["spz"])
            print(f"[MAPA] Načteno {len(TRACKED_SPZS)} sledovaných SPZ.")
        except Exception:
            pass

    url_inflow_base = "https://pvvd.idpk.cz/Ajax/GetPoints"
    url_arriva      = "https://www.arriva.cz/api/graphql"
    inflow_headers  = {
        'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept':           'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer':          'https://pvvd.idpk.cz/',
        'Cache-Control':    'no-cache',
        'Pragma':           'no-cache',
    }
    try:
        opener.open(urllib.request.Request("https://pvvd.idpk.cz/", headers={'User-Agent': 'Mozilla/5.0'}))
    except Exception:
        pass

    last_db_cleanup = get_prague_time()
    TRIP_COUNTER    = int(time.time())

    while True:
        try:
            now = get_prague_time()

            if db_client and (now - last_db_cleanup).total_seconds() > 86400:
                try:
                    thirty_days_ago = (now - timedelta(days=30)).isoformat()
                    # ZAKOMENTOVÁNO: aby se staré záznamy nemazaly
                    # db_client.table("bus_history").delete().lt("created_at", thirty_days_ago).execute()
                    pass
                except Exception:
                    pass
                last_db_cleanup = now

            data_inflow = []
            data_arriva = []

            url_inflow = f"{url_inflow_base}?_={int(time.time() * 1000)}"
            try:
                req1 = urllib.request.Request(url_inflow, headers=inflow_headers)
                with urllib.request.urlopen(req1, timeout=5) as r1:
                    data_inflow = json.loads(r1.read().decode())
            except Exception:
                try:
                    req1_post = urllib.request.Request(url_inflow, data=b"{}", headers=inflow_headers, method='POST')
                    with urllib.request.urlopen(req1_post, timeout=5) as r1_post:
                        data_inflow = json.loads(r1_post.read().decode())
                except Exception:
                    pass

            try:
                arriva_payload = {
                    "operationName": "busesCurrentLocation",
                    "variables": {},
                    "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle delay destinationName lastStopName\n    latitude longitude linkNumber state type\n    mainType spz updated linkNumberAlias __typename\n  }\n}"
                }
                req2 = urllib.request.Request(
                    url_arriva,
                    data=json.dumps(arriva_payload).encode('utf-8'),
                    headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json','Origin':'https://www.arriva.cz','Referer':'https://www.arriva.cz/'},
                    method='POST'
                )
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
                        bus_id   = str(bus1.get("id", "0"))
                        line     = str(bus1.get("text", "")).strip()
                        lat1     = bus1.get("lat", 0)
                        lng1     = bus1.get("lng", 0)
                        delay    = int(bus1.get("delay", 0)) if bus1.get("delay") is not None else 0
                        dest1    = str(bus1.get("finalStopName", "")).strip()
                        traction = str(bus1.get("traction", "BUS")).upper()
                        is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]

                        # ── Admin delete: přeskočit pokud smazaný a stejná linka ──
                        if bus_id in ADMIN_DELETED_BUSES:
                            deleted_line = ADMIN_DELETED_BUSES[bus_id]
                            if not is_same_line(line, deleted_line):
                                del ADMIN_DELETED_BUSES[bus_id]  # nová linka = odblokovat
                            else:
                                current_inflow_ids.add(bus_id)   # počítej jako "viděný"
                                continue

                        current_inflow_ids.add(bus_id)

                        if bus_id not in GLOBAL_BUS_CACHE:
                            TRIP_COUNTER += 1
                            ghost_spz      = None
                            ghost_verified = False
                            ghost_trip_id  = f"TRIP-{TRIP_COUNTER}"
                            ghost_candidates = []

                            for gid, gc in list(GLOBAL_BUS_CACHE.items()):
                                if not (gc.get("is_offline") and gc.get("spz") and gc["spz"] != "Neznámá"):
                                    continue
                                oa_min = (now - gc["last_inflow_seen"]).total_seconds() / 60.0
                                if oa_min > 1080:
                                    continue
                                g_dist     = math.hypot(lat1 - gc["lat"], lng1 - gc["lng"])
                                line_match = is_same_line(line, gc["line"])
                                if line_match and g_dist < 0.08:
                                    score = g_dist + (oa_min * 0.0001) - 0.05
                                    ghost_candidates.append((gid, gc, g_dist, score))
                                elif g_dist < GHOST_DIST_STRICT and oa_min <= GHOST_MAX_OFFLINE_MIN:
                                    score = g_dist + (oa_min * 0.0005)
                                    ghost_candidates.append((gid, gc, g_dist, score))

                            if ghost_candidates:
                                ghost_candidates.sort(key=lambda x: x[3])
                                best_gid, best_gc, _, _ = ghost_candidates[0]
                                ghost_spz = best_gc["spz"]
                                if is_same_line(line, best_gc["line"]):
                                    ghost_trip_id  = best_gc["trip_id"]
                                    ghost_verified = best_gc.get("spz_verified", False)
                                del GLOBAL_BUS_CACHE[best_gid]
                                if db_client and ghost_spz and ghost_spz != "Neznámá":
                                    close_previous_trips(db_client, ghost_spz, ghost_trip_id, now.strftime('%H:%M'))

                            GLOBAL_BUS_CACHE[bus_id] = new_cache_entry(
                                bus_id, ghost_trip_id, lat1, lng1,
                                line, dest1, is_train, delay, now, ghost_spz, ghost_verified
                            )

                        else:
                            c = GLOBAL_BUS_CACHE[bus_id]
                            c["last_inflow_seen"] = now
                            c["is_offline"]       = False
                            c["raw_delay"]        = delay
                            c["is_train"]         = is_train
                            dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])

                            if not is_same_line(c["line"], line) and line and c["line"] != "Neznámá":
                                if not c["actual_end_time"]:
                                    c["actual_end_time"] = now.strftime('%H:%M')
                                    c["status"] = "Ukončeno (Začátek nového spoje)"
                                    upsert_to_history(db_client, c)
                                TRIP_COUNTER += 1
                                new_trip_id   = f"TRIP-{TRIP_COUNTER}"
                                if c.get("spz") and c["spz"] != "Neznámá" and db_client:
                                    close_previous_trips(db_client, c["spz"], new_trip_id, now.strftime('%H:%M'))
                                c["trip_id"]          = new_trip_id
                                c["line"]             = line
                                c["real_linka_spoj"]  = None
                                c["destination"]      = dest1
                                c["first_dep_time"]   = None
                                c["last_dep_time"]    = None
                                c["actual_start_time"] = None
                                c["actual_end_time"]  = None
                                c["created_at"]       = now
                                c["status"]           = "Načítání..."
                                c["bearing"]          = None
                                # manual_spz: drz SPZ pres cely zivot kolecka na mape
                                if not c.get("manual_spz"):
                                    c["spz_locked"]       = False
                                    c["spz_verified"]     = False
                                    c["spz"]              = c.get("spz")  # zachova ale unverified
                                # admin_lock_display: barva/status se resetuji pri novem spoji
                                # (uzivatele to netrapi, novy spoj = nove auto-vypocty)
                                if not c.get("admin_lock_permanent"):
                                    c["admin_lock_display"]   = False
                                    c["admin_color_override"] = None
                                    c["admin_status_override"]= None
                                    c["admin_lock_permanent"] = False
                                    c["admin_note"]           = ""
                                c["investigating"]    = False
                                c["db_first_upsert"]  = False
                                c["_last_db_status"]  = None
                                c["_last_db_linka"]   = None
                                c["_end_written"]     = False
                            else:
                                if dest1:
                                    c["destination"] = dest1
                                if line and len(line) > len(c.get("line", "")):
                                    c["line"] = line

                            if dist_moved > 0.0001:
                                # Výpočet bearing
                                lat1_rad = math.radians(c["lat"])
                                lat2_rad = math.radians(lat1)
                                lng_diff_rad = math.radians(lng1 - c["lng"])
                                y = math.sin(lng_diff_rad) * math.cos(lat2_rad)
                                x = math.cos(lat1_rad)*math.sin(lat2_rad) - math.sin(lat1_rad)*math.cos(lat2_rad)*math.cos(lng_diff_rad)
                                bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
                                c["bearing"] = int(bearing)
                                c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                    except Exception:
                        continue

            # ═══ SEKCE 3: Duplikáty + BUG detekce ═══════════════════════════
            spz_tracker = {}
            for bid, bc in GLOBAL_BUS_CACHE.items():
                spz_val = bc.get("spz")
                if spz_val and spz_val != "Neznámá" and not bc.get("is_offline"):
                    spz_tracker.setdefault(spz_val, []).append(bid)

            for spz_val, bus_ids in spz_tracker.items():
                if len(bus_ids) <= 1:
                    GLOBAL_BUS_CACHE[bus_ids[0]]["investigating"]      = False
                    GLOBAL_BUS_CACHE[bus_ids[0]]["investigation_start"] = None
                    if GLOBAL_BUS_CACHE[bus_ids[0]].get("color_class") == "bg-bug":
                        GLOBAL_BUS_CACHE[bus_ids[0]]["color_class"] = "bg-gray"
                        GLOBAL_BUS_CACHE[bus_ids[0]]["status"]      = "Stojí"
                    continue

                moving_bids     = [bid for bid in bus_ids if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() < 60]
                stationary_bids = [bid for bid in bus_ids if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() > 180]

                if moving_bids and stationary_bids:
                    for bid in stationary_bids:
                        bc = GLOBAL_BUS_CACHE[bid]
                        if (now - bc["last_moved"]).total_seconds() / 60.0 < 2:
                            bc["color_class"] = "bg-orange"
                            bc["status"]      = "Výzkum – Duplicitní SPZ, bus se hýbe"
                        else:
                            bc["status"]      = "BUG - NEAKTUÁLNÍ MÍSTO"
                            bc["color_class"] = "bg-bug"
                            bc["spz_locked"]  = True
                            bc["bug_locked"]   = True   # Permanentni lock – nikdy neodemykat
                        bc["investigating"]       = False
                        bc["investigation_start"] = None
                    for bid in moving_bids:
                        GLOBAL_BUS_CACHE[bid]["investigating"]       = False
                        GLOBAL_BUS_CACHE[bid]["investigation_start"] = None
                    continue

                def score_candidate(bid):
                    bc = GLOBAL_BUS_CACHE[bid]
                    return (bc.get("spz_stable_ticks", 0), bc.get("spz_last_verified") or datetime.min)
                best_bid = max(bus_ids, key=score_candidate)

                for bid in bus_ids:
                    bc = GLOBAL_BUS_CACHE[bid]
                    if bid == best_bid:
                        bc["investigating"] = False; bc["investigation_start"] = None
                    else:
                        if not bc.get("manual_spz"):
                            bc["spz_verified"] = False; bc["spz_locked"] = False
                        bc["investigating"] = True; bc["investigation_spz"] = spz_val
                        if bc.get("investigation_start") is None:
                            bc["investigation_start"] = now
                        elif (now - bc["investigation_start"]).total_seconds() > DUPLICATE_GRACE_SEC and not bc.get("manual_spz"):
                            bc["spz_verified"] = False; bc["spz_locked"] = False
                            bc["investigating"] = False; bc["investigation_start"] = None; bc["spz_stable_ticks"] = 0

            # ═══ SEKCE 4: Offline + timeouty ═════════════════════════════════
            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                offline_mins = (now - c["last_inflow_seen"]).total_seconds() / 60.0
                total_mins   = (now - c["first_seen"]).total_seconds()       / 60.0

                if total_mins > 1200 and not c["actual_end_time"] and not c.get("is_offline"):
                    c["actual_end_time"] = now.strftime('%H:%M')
                    c["status"]          = "Timeout (Příliš dlouhý spoj)"
                    c["color_class"]     = "bg-gray"
                    upsert_to_history(db_client, c)
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue

                if bus_id not in current_inflow_ids:
                    if offline_mins > 1080:
                        upsert_to_history(db_client, c)
                        del GLOBAL_BUS_CACHE[bus_id]
                        continue
                    c["is_offline"] = True
                    if offline_mins >= 120:
                        c["status"] = "Stojí v depu / Vozovně"; c["color_class"] = "bg-gray"; c["raw_delay"] = 0; c["spz_locked"] = True
                        if offline_mins < 125: upsert_to_history(db_client, c)
                    elif offline_mins >= 15:
                        c["status"] = "Odstaven (Bez signálu)"; c["color_class"] = "bg-gray"; c["raw_delay"] = 0; c["spz_locked"] = True
                        if offline_mins < 20: upsert_to_history(db_client, c)
                    elif offline_mins > 2:
                        if not c["actual_end_time"]: c["actual_end_time"] = now.strftime('%H:%M')
                        c["status"] = "Ztráta polohy (Konečná)"; c["color_class"] = "bg-purple"; c["raw_delay"] = 0; c["spz_locked"] = True
                        if offline_mins < 4: upsert_to_history(db_client, c)

            # ═══ SEKCE 5: Statusy, barvy, SPZ párování ═══════════════════════
            new_live_data        = []
            tt_fetches_this_tick = 0

            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                inactive_mins = (now - c["last_moved"]).total_seconds() / 60.0

                if c.get("is_offline"):
                    final_line_disp = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c["is_train"] else "Neznámá")
                    new_live_data.append({
                        "id":bus_id,"trip_id":c["trip_id"],"lat":c["lat"],"lng":c["lng"],"bearing":c.get("bearing"),
                        "line":final_line_disp,"delay":0,"destination":c["destination"],
                        "spz":c["spz"] or "Neznámá","spz_verified":c.get("spz_verified",False),
                        "is_train":c["is_train"],"status":c["status"],"color_class":c["color_class"],
                        "inactive_minutes":inactive_mins,"last_updated":c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A",
                        "investigating":False,"investigation_spz":"",
                        "admin_flag": c.get("admin_flag", False),
                        "admin_note": c.get("admin_note", ""),
                    })
                    continue

                lat1  = c["lat"]; lng1 = c["lng"]; line = c["line"]
                dest1 = c["destination"]; is_train = c["is_train"]
                is_moving = inactive_mins < 1; delay_val = c["raw_delay"]

                # ── SPZ párování ──────────────────────────────────────────────
                if not is_train and not c.get("investigating") and not c.get("spz_locked") and not c.get("bug_locked"):
                    i_clean = re.sub(r'\D','', line); d1_clean = re.sub(r'\W+','', dest1.lower())
                    best_spz = None; best_match_dest = False; best_dist = 999.0
                    for b in data_arriva:
                        a_line  = str(b.get("linkNumber","")).strip()
                        a_clean = re.sub(r'\D','', a_line)
                        if not (i_clean and a_clean and (i_clean.endswith(a_clean) or a_clean.endswith(i_clean))): continue
                        dist = math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0))
                        if dist < ARRIVA_MATCH_DIST and dist < best_dist:
                            best_dist = dist
                            a_dest = str(b.get("destinationName","")).lower()
                            d2_clean = re.sub(r'\W+','', a_dest)
                            best_match_dest = bool(d1_clean in d2_clean or d2_clean in d1_clean or not d1_clean or not d2_clean)
                            best_spz = b.get("spz","").strip() or None

                    if best_spz and best_spz != "Neznámá":
                        current_spz = c.get("spz")
                        if best_spz == current_spz:
                            c["spz_stable_ticks"] = c.get("spz_stable_ticks",0) + 1
                            if best_match_dest: c["spz_last_verified"] = now
                        else:
                            last_v = c.get("spz_last_verified")
                            recently = last_v and (now-last_v).total_seconds() < SPZ_HOLD_MINUTES*60 and c.get("spz_verified")
                            if not recently:
                                if c.get("spz_verified") and current_spz and db_client:
                                    try:
                                        db_client.table("bus_history").update({"status":"Falešný záznam (SPZ opravena)","spz_verified":False}).eq("trip_id",c["trip_id"]).execute()
                                    except Exception: pass
                                TRIP_COUNTER += 1; c["trip_id"] = f"TRIP-{TRIP_COUNTER}"
                                c["spz"] = best_spz; c["spz_stable_ticks"] = 1; c["spz_verified"] = False; c["spz_locked"] = False
                                if best_match_dest: c["spz_last_verified"] = now
                        # Lock po 2 shodách polohy – bez požadavku na shodu cíle
                        if c.get("spz_stable_ticks",0) >= SPZ_STABLE_TICKS:
                            c["spz_verified"] = True; c["spz_locked"] = True; c["spz_last_verified"] = now
                    else:
                        last_v = c.get("spz_last_verified")
                        if not last_v or (now-last_v).total_seconds() >= SPZ_HOLD_MINUTES*60:
                            if not c.get("manual_spz") and not c.get("bug_locked"):
                                c["spz_verified"] = False; c["spz_locked"] = False

                # ── JŘ fetch ──────────────────────────────────────────────────
                if not is_train:
                    tt_age = (now - c["tt_last_fetch"]).total_seconds() if c.get("tt_last_fetch") else 9999
                    if tt_age > 300 and not c.get("tt_is_fetching") and tt_fetches_this_tick < 5:
                        tt_fetches_this_tick += 1; c["tt_last_fetch"] = now; c["tt_is_fetching"] = True
                        threading.Thread(target=fetch_tt_bg, args=(bus_id, c), daemon=True).start()

                # ── Barvy + status ────────────────────────────────────────────
                old_status = c.get("status", "")  # PŘED if/else – oprava scope bugu

                # Pokud admin zamknul zobrazení, přeskoč automatiku
                if c.get("admin_lock_display"):
                    # Jen aplikuj override a přeskoč přepočet barev
                    if c.get("admin_color_override"):
                        c["color_class"] = c["admin_color_override"]
                    if c.get("admin_status_override"):
                        c["status"]      = c["admin_status_override"]

                elif c.get("color_class") == "bg-bug":
                    if is_moving:
                        c["color_class"] = "bg-orange"; c["status"] = "Výzkum – Reaktivace (byl zaseknutý)"
                else:
                    is_before_departure = False; time_to_dep = 0
                    if c["first_dep_time"]:
                        try:
                            dh, dm = map(int, c["first_dep_time"].split(':'))
                            dep_total = dh*60 + dm; cur_total = now.hour*60 + now.minute
                            diff = dep_total - cur_total
                            if diff < -720: diff += 1440
                            elif diff > 720: diff -= 1440
                            if diff > 1: is_before_departure = True; time_to_dep = int(diff)
                        except Exception: pass

                    if is_before_departure:
                        c["actual_end_time"] = None
                        if time_to_dep <= 240:
                            c["status"] = f"Čeká na odjezd ({time_to_dep} min)"; c["color_class"] = "bg-blue"
                        else:
                            c["status"] = "Čeká na spoj (>4h)"; c["color_class"] = "bg-gray"
                        delay_val = -time_to_dep

                    elif delay_val <= -10000:
                        if inactive_mins > 10:
                            c["status"] = "Odstaven"; c["color_class"] = "bg-gray"; c["spz_locked"] = True
                        else:
                            c["status"] = "Konečná zastávka"; c["color_class"] = "bg-purple"; c["spz_locked"] = True
                            if not c["actual_end_time"]:
                                c["actual_end_time"] = now.strftime('%H:%M'); c["_end_written"] = False
                            # Dočasný admin override reset při konečné
                            if c.get("admin_lock_display") and not c.get("admin_lock_permanent"):
                                c["admin_lock_display"] = False
                                c["admin_color_override"] = None
                                c["admin_status_override"] = None

                    elif delay_val < -1 and c.get("actual_start_time"):
                        c["status"] = "Jízda (Náskok)" if is_moving else "Stojí (Náskok)"; c["color_class"] = "bg-darkblue"

                    else:
                        c["status"] = "Jízda" if is_moving else "Stojí"
                        c["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                    if (not is_moving and inactive_mins > 10 and c.get("actual_start_time")
                            and c["color_class"] not in ("bg-purple","bg-gray","bg-bug","bg-blue","bg-orange")):
                        c["status"] = f"Stojí příliš dlouho ({int(inactive_mins)} min)"
                        c["color_class"] = "bg-gray"; c["_was_long_stationary"] = True; c["spz_locked"] = True
                    elif is_moving and c.get("_was_long_stationary") and c["color_class"] not in ("bg-bug","bg-blue"):
                        c["color_class"] = "bg-orange"; c["status"] = "Výzkum – Reaktivace po dlouhém stání"; c["_was_long_stationary"] = False

                if is_moving and not c["actual_start_time"] and not is_train:
                    c["actual_start_time"] = now.strftime('%H:%M'); c["_end_written"] = False

                c["final_delay_display"] = delay_val

                # ── Admin overrides (přepíší výsledek automatické logiky) ─────
                if c.get("admin_color_override"):
                    c["color_class"] = c["admin_color_override"]
                if c.get("admin_status_override"):
                    c["status"]      = c["admin_status_override"]

                # ── DB upsert ─────────────────────────────────────────────────
                has_spz      = c.get("spz") and c["spz"] != "Neznámá"
                tracked_line = _is_tracked_line(c.get("real_linka_spoj") or c.get("line",""))
                status_chg   = (old_status != c["status"])
                linka_chg    = (c.get("_last_db_linka") != (c.get("real_linka_spoj") or c.get("line")))
                just_ended   = (c.get("actual_end_time") and not c.get("_end_written"))

                if has_spz and tracked_line:
                    if not c.get("db_first_upsert") or status_chg or linka_chg or \
                       (is_moving and c.get("actual_start_time") and int(time.time()) % 30 < 10) or just_ended:
                        upsert_to_history(db_client, c)
                        c["db_first_upsert"] = True; c["_last_db_status"] = c["status"]
                        c["_last_db_linka"]  = c.get("real_linka_spoj") or c.get("line")
                        if just_ended:
                            c["_end_written"] = True
                            close_previous_trips(db_client, c.get("spz"), c["trip_id"], c["actual_end_time"])

                final_line_disp = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c["is_train"] else "Neznámá")
                new_live_data.append({
                    "id":               bus_id,
                    "trip_id":          c["trip_id"],
                    "lat":              c["lat"],
                    "lng":              c["lng"],
                    "bearing":          c.get("bearing"),
                    "line":             final_line_disp,
                    "delay":            c.get("final_delay_display", 0),
                    "destination":      c["destination"],
                    "spz":              c["spz"] or "Neznámá",
                    "spz_verified":     c.get("spz_verified", False),
                    "is_train":         c["is_train"],
                    "status":           c["status"],
                    "color_class":      c["color_class"],
                    "inactive_minutes": inactive_mins,
                    "last_updated":     c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A",
                    "investigating":    c.get("investigating", False),
                    "investigation_spz": c.get("investigation_spz", ""),
                    "admin_flag":        c.get("admin_flag", False),
                    "admin_note":        c.get("admin_note", ""),
                })

            global LIVE_BUSES_DATA
            LIVE_BUSES_DATA = new_live_data
            time.sleep(10)

        except Exception as crash_error:
            print(f"[MAPA CRITICAL] Worker selhala, restart za 10s! Chyba: {crash_error}", flush=True)
            time.sleep(10)


def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()


# ─── FLASK ROUTES ─────────────────────────────────────────────────────────────

GTFS_DB_PATH     = "gtfs_stops.db"
GTFS_RELEASE_URL = "https://github.com/marek-1cz/DataCoreBot/releases/download/V.2/gtfs_stops.db"

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
    #map{position:absolute;top:0;left:0;width:100%;height:100% !important;min-height:100vh;z-index:1;}
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
</html>""",
        mimetype='text/html'
    )

_AD_BTN_NORMAL = '<a href="/mapa_admin" class="n-btn n-ad"><i class="fas fa-lock"></i> AD</a>'
_AD_BTN_ADMIN  = '<a href="/mapa" class="n-btn n-back"><i class="fas fa-arrow-left"></i> Zpět</a>'

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
        'border:1px solid rgba(56,189,248,0.3);letter-spacing:.3px;">'
        '⚙️ Admin mapa — moderace zapnutá'
        '</span></div>'
    )
    html = HTML_MAPA.replace('__ADMIN_BANNER__', admin_banner).replace('__IS_ADMIN__', 'true').replace('__AD_BTN__', _AD_BTN_ADMIN)
    return _full_page("Admin Mapa", html, is_map=True)


@mapa_bp.route('/api/admin/map_action', methods=['POST'])
def api_admin_map_action():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Neautorizováno"}), 401
    data   = request.get_json(silent=True) or {}
    action = data.get("action")
    bus_id = str(data.get("bus_id", ""))

    if bus_id not in GLOBAL_BUS_CACHE:
        if action == "delete":
            # Bus může být v admin_deleted nebo dočasně offline
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Bus nenalezen v cache"})

    c = GLOBAL_BUS_CACHE[bus_id]

    if action == "delete":
        line = c.get("line", "")
        ADMIN_DELETED_BUSES[bus_id] = line   # Uchovej linku pro detekci nového spoje
        del GLOBAL_BUS_CACHE[bus_id]

    elif action == "edit_spz":
        new_spz = str(data.get("spz", "")).strip()
        if new_spz:
            c["spz"]          = new_spz
            c["spz_locked"]   = True
            c["spz_verified"] = True
            c["manual_spz"]   = True
            c["investigating"] = False

    elif action == "recheck_spz":
        c["spz_locked"]       = False
        c["spz_verified"]     = False
        c["spz"]              = None
        c["manual_spz"]       = False
        c["investigating"]    = False
        c["spz_stable_ticks"] = 0

    elif action == "edit_status":
        new_st  = str(data.get("status",      "")).strip()
        new_col = str(data.get("color_class", "")).strip()
        if new_st:
            c["status"]                = new_st
            c["admin_status_override"] = new_st
            c["admin_lock_display"]    = True
        if new_col and new_col not in ("", "──"):
            c["color_class"]           = new_col
            c["admin_color_override"]  = new_col
            c["admin_lock_display"]    = True

    elif action == "set_admin_flag":
        c["admin_flag"] = bool(data.get("flag", False))

    elif action == "edit_all":
        new_st   = str(data.get("status",      "")).strip()
        new_col  = str(data.get("color_class", "")).strip()
        new_note = str(data.get("note",        "")).strip()
        permanent = bool(data.get("permanent", False))
        if new_st:
            c["status"]                = new_st
            c["admin_status_override"] = new_st
            c["admin_lock_display"]    = True
        if new_col and new_col not in ("", "──"):
            c["color_class"]           = new_col
            c["admin_color_override"]  = new_col
            c["admin_lock_display"]    = True
        if new_note is not None:
            c["admin_note"] = new_note
        c["admin_lock_permanent"] = permanent

    elif action == "reset_admin":
        c["manual_spz"]           = False
        c["spz_locked"]           = False
        c["spz_verified"]         = False
        c["spz_stable_ticks"]     = 0
        c["investigating"]        = False
        c["admin_color_override"] = None
        c["admin_status_override"]= None
        c["admin_flag"]           = False
        c["bug_locked"]           = False
        c["admin_lock_display"]   = False
        c["admin_lock_permanent"] = False
        c["admin_note"]           = ""
        c["color_class"]          = "bg-gray"
        c["status"]               = "Načítání..."

    return jsonify({"status": "success"})


@mapa_bp.route('/historie')
def stranka_historie_index():
    return _full_page("Historie", HTML_HISTORIE_INDEX)


@mapa_bp.route('/historie/<spz>')
def stranka_historie_detail(spz):
    html = HTML_HISTORIE_DETAIL.replace('__SPZ__', spz)
    return _full_page(f"Vůz {spz}", html)


@mapa_bp.route('/api/live_buses')
def api_live_buses():
    now = get_prague_time()
    uptime = (now - WORKER_START_TIME).total_seconds() if WORKER_START_TIME else 9999
    return jsonify({
        "status":                "success",
        "server_time":           now.strftime('%H:%M:%S'),
        "worker_uptime_seconds": round(uptime),
        "buses":                 LIVE_BUSES_DATA,
    })


@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    try:
        cb_time = int(time.time() * 1000)
        headers = {'User-Agent':'Mozilla/5.0','X-Requested-With':'XMLHttpRequest','Referer':'https://pvvd.idpk.cz/'}
        info_html = ""
        try:
            req_info = urllib.request.Request(f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb_time}", headers=headers)
            with opener.open(req_info, timeout=4) as r: info_html = r.read().decode('utf-8')
        except Exception: pass
        tt_html = ""
        try:
            req_tt = urllib.request.Request(f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}", headers=headers)
            with opener.open(req_tt, timeout=4) as r: tt_html = r.read().decode('utf-8')
        except Exception: tt_html = "<p style='color:#94a3b8;'>JŘ není dostupný.</p>"
        return f"""<div style="background:#0f172a;color:white;font-family:sans-serif;">
          <div style="background:#1e293b;padding:12px;border-radius:6px;margin-bottom:12px;">{info_html}</div>
          <div style="overflow-x:auto;"><style>table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:6px 10px;text-align:left}}th{{background:#0f172a;color:#38bdf8}}tr:hover td{{background:#1e293b}}.current{{background:#166534!important;font-weight:bold}}</style>{tt_html}</div></div>"""
    except Exception as e:
        return f"<p style='color:#ef4444;padding:20px;'>Chyba: {e}</p>"


@mapa_bp.route('/api/history_full')
def api_history_full():
    db = get_db_client()
    if not db: return jsonify({"data":[],"error":"DB nedostupná"})
    try:
        res = db.table("bus_history").select("*").order("created_at", desc=True).limit(200).execute()
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data":[],"error":str(e)})


@mapa_bp.route('/api/history_spz/<spz>')
def api_history_spz(spz):
    db = get_db_client()
    if not db: return jsonify({"data":[],"error":"DB nedostupná"})
    try:
        res = db.table("bus_history").select("*").eq("spz", spz).order("created_at", desc=True).limit(100).execute()
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data":[],"error":str(e)})


# --- EXPERIMENTALNI: Trasa busu ---
import urllib.parse as _uparse

_stop_geo_cache = {}

def _geocode_stop(stop_name):
    key = stop_name.strip().lower()
    if key in _stop_geo_cache:
        return _stop_geo_cache[key]
    try:
        # Bounding box pro Plzensky kraj + okolni regiony (rychlejsi a presnejsi)
        bbox = "viewbox=11.8%2C50.5%2C14.1%2C49.1&bounded=1"
        q    = _uparse.quote(stop_name)
        url  = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=2&countrycodes=cz&{bbox}"
        req  = urllib.request.Request(url, headers={"User-Agent": "OIS-IDPK/1.0 (mapa.idpk.cz)"})
        with urllib.request.urlopen(req, timeout=3) as r:
            res = json.loads(r.read().decode())
        if res:
            # Vyber nejblizsi k centru Plzne (49.74, 13.37)
            def dist_plzen(r):
                return abs(float(r["lat"]) - 49.74) + abs(float(r["lon"]) - 13.37)
            best = min(res, key=dist_plzen)
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
        cb   = int(time.time() * 1000)
        hdrs = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": "https://pvvd.idpk.cz/"}
        url  = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}"
        with opener.open(urllib.request.Request(url, headers=hdrs), timeout=5) as r:
            tt = r.read().decode("utf-8")
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', tt, re.DOTALL | re.IGNORECASE):
            cells = [re.sub(r'<[^>]+>', '', x).strip()
                     for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)]
            if len(cells) >= 1 and cells[0] and len(cells[0]) > 1:
                stop_names.append(cells[0])
                stop_times.append(cells[1] if len(cells) > 1 else "")
        cur_m = re.findall(r"""class=["']current["'][^>]*>.*?<td[^>]*>(.*?)</td>""", tt, re.DOTALL | re.IGNORECASE)
        if cur_m:
            cur = re.sub(r'<[^>]+>', '', cur_m[0]).strip()
            for i, s in enumerate(stop_names):
                if s.lower() == cur.lower():
                    current_idx = i; break
    except Exception as e:
        print(f"[ROUTE] JR fetch chyba: {e}")
    return stop_names, stop_times, current_idx


@mapa_bp.route('/api/bus_route/<bus_id>')
def api_bus_route(bus_id):
    c = GLOBAL_BUS_CACHE.get(bus_id)
    if not c:
        return jsonify({"stops": [], "error": "Bus nenalezen"})

    stop_names, stop_times, current_idx = _fetch_tt_stops(bus_id)
    if not stop_names:
        return jsonify({"stops": [], "error": "Zastávky nenalezeny v JR"})

    if os.path.exists(GTFS_DB_PATH):
        try:
            import sqlite3 as _sq
            conn = _sq.connect(GTFS_DB_PATH)
            conn.row_factory = _sq.Row
            cur  = conn.cursor()
            result = []
            seen   = set()
            for i, (name, t) in enumerate(zip(stop_names, stop_times)):
                name_c = name.strip()
                if name_c in seen:
                    prev = result[-1] if result else None
                    if prev and prev["lat"]:
                        result.append({"name": name_c, "time": t,
                                       "lat": prev["lat"] + 0.00001,
                                       "lng": prev["lng"],
                                       "passed": i < current_idx})
                    continue
                seen.add(name_c)
                cur.execute("SELECT stop_lat, stop_lon FROM stops WHERE stop_name = ? LIMIT 1", (name_c,))
                row = cur.fetchone()
                if not row:
                    word = name_c.split()[0] if name_c else name_c
                    cur.execute("SELECT stop_lat, stop_lon FROM stops WHERE stop_name LIKE ? LIMIT 1", (f"{word}%",))
                    row = cur.fetchone()
                result.append({"name": name_c, "time": t,
                               "lat":  row["stop_lat"] if row else None,
                               "lng":  row["stop_lon"] if row else None,
                               "passed": i < current_idx})
            conn.close()
            return jsonify({"stops": result, "bus_id": bus_id, "source": "gtfs",
                            "found": sum(1 for s in result if s["lat"]), "total": len(result)})
        except Exception as e:
            print(f"[ROUTE] GTFS chyba: {e}")

    result = []
    for i, (name, t) in enumerate(zip(stop_names[:20], stop_times[:20])):
        coords = _geocode_stop(name)
        result.append({"name": name, "time": t,
                       "lat":  coords[0] if coords else None,
                       "lng":  coords[1] if coords else None,
                       "passed": i < current_idx})
    return jsonify({"stops": result, "bus_id": bus_id, "source": "nominatim"})
