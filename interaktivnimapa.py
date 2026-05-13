import os
import time
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, Response, render_template_string
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
SPZ_HOLD_MINUTES       = 8     # Jak dlouho držet SPZ bez nového potvrzení z Arrivy
SPZ_STABLE_TICKS       = 2     # Kolik po sobě jdoucích shod = ověřená SPZ
GHOST_MAX_OFFLINE_MIN  = 20    # Jak starý (minuty) ghost kandidát se ještě vezme v potaz
GHOST_DIST_STRICT      = 0.010 # ~1 km – vzdálenost pro ghost bez shody linky
GHOST_DIST_LOOSE       = 0.030 # ~3 km – vzdálenost pro ghost se shodou linky
ARRIVA_MATCH_DIST      = 0.008 # ~800 m – radius hledání v Arriva API (bylo 0.015!)
DUPLICATE_GRACE_SEC    = 120   # Sekundy grace periody před smazáním duplicitní SPZ
# ─────────────────────────────────────────────────────────────────────────────

# --- HTML ŠABLONY ---
HTML_HISTORIE_INDEX = """
<div style="padding: 20px; max-width: 1400px; margin: auto; font-family: sans-serif;">
  <div style="background-color: #dc2626; color: white; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 20px; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 2px solid #991b1b;">
    <i class="fas fa-exclamation-triangle fa-fade"></i> !!! DATA NEMUSÍ SEDĚT - STRÁNKA JE VE VÝVOJI !!!
  </div>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
    <h2 style="color: #38bdf8; margin: 0; font-size: 24px;"><i class="fas fa-database"></i> Databáze Sledovaných Vozů</h2>
    <div class="field" style="margin-bottom: 0;">
      <p class="control has-icons-left">
        <input class="input" id="historySearch" type="text" placeholder="Hledat linku, SPZ nebo status..." style="background: #1e293b; color: white; border-color: #334155; min-width: 350px;">
        <span class="icon is-small is-left" style="color: #94a3b8;"><i class="fas fa-search"></i></span>
      </p>
    </div>
  </div>
  <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
    <table class="table is-fullwidth is-hoverable" style="background: transparent; color: #cbd5e1; margin-bottom: 0; min-width: 1000px;">
      <thead>
        <tr style="background: #0f172a;">
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Datum &amp; Spoj ID</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka (JŘ)</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">SPZ Vozu</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Start (Plán -&gt; Reál)</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Konec spoje / Status</th>
          <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Akce</th>
        </tr>
      </thead>
      <tbody id="historyTableBody">
        <tr><td colspan="6" style="text-align:center; padding: 30px; color: #38bdf8;"><i class="fas fa-spinner fa-spin"></i> Stahuji historii spojů...</td></tr>
      </tbody>
    </table>
  </div>
  <script>
  async function loadIndex() {
    try {
      const searchVal = document.getElementById('historySearch').value.toLowerCase().trim();
      const response = await fetch('/api/history_full');
      const result = await response.json();
      const data = result.data || [];
      const tbody = document.getElementById('historyTableBody');
      let newHtml = '';
      if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px;">Zatím žádné záznamy pro 490/496.</td></tr>';
        return;
      }
      data.forEach(row => {
        const createdDate = new Date(row.created_at);
        const dayStr = createdDate.toLocaleDateString('cs-CZ');
        let spzBadge = '';
        if (!row.spz || row.spz === 'Neznámá') {
          spzBadge = `<span class="tag is-light" style="background:#334155; color:#94a3b8;"><i class="fas fa-question-circle" style="margin-right:4px;"></i>Neznámá</span>`;
        } else if (row.status && row.status.includes('Falešný záznam')) {
          spzBadge = `<span class="tag is-danger" style="font-weight:bold;">${row.spz} <i class="fas fa-times-circle" style="color:white; margin-left:5px;" title="Neověřený / Falešný záznam"></i></span>`;
        } else {
          spzBadge = `<span class="tag is-warning" style="background:#f59e0b; color:#0f172a; font-weight:bold;">${row.spz} <i class="fas fa-check-circle" style="color:#0f172a; margin-left:5px;" title="Ověřeno"></i></span>`;
        }
        let startStr = "---";
        if (row.start_scheduled || row.start_actual) {
          startStr = `<span style="color:#94a3b8;">${row.start_scheduled || '?'}</span> <i class="fas fa-arrow-right" style="font-size:10px; margin:0 5px;"></i> <strong style="color:#10b981;">${row.start_actual || 'Čeká'}</strong>`;
        }
        let isFinished = row.end_actual || (row.status && row.status.includes('Timeout'));
        let statusColor = isFinished ? "#ef4444" : "#eab308";
        let statusIcon = isFinished ? "" : `<i class="fas fa-spinner fa-pulse" style="margin-right:5px;"></i>`;
        let endInfo = row.end_actual ? row.end_actual : 'Probíhá...';
        if (row.status && row.status.includes('Timeout')) endInfo = 'Ukončeno (Timeout)';
        let statusHtml = `<div style="font-size:12px; color:#cbd5e1;">${row.status}</div><div style="color:${statusColor}; font-weight:bold;">${statusIcon}${endInfo}</div>`;
        const linkaClean = row.linka || '---';
        const spzSafe = row.spz || 'Neznámá';
        const rowText = `${spzSafe} ${linkaClean} ${row.status}`.toLowerCase();
        const isVisible = rowText.includes(searchVal) ? '' : 'display:none;';
        newHtml += `
          <tr style="border-color: #334155; ${isVisible}" data-search="${rowText}">
            <td style="border-color: #334155; padding: 12px; vertical-align: middle;"><strong>${dayStr}</strong><br><span style="font-size:11px; color:#64748b;">ID: ${row.trip_id.substring(0,8)}...</span></td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle;"><strong style="color:white;">${linkaClean}</strong>${row.jr_link ? `<br><a href="${row.jr_link}" target="_blank" style="font-size:11px; color:#38bdf8;">Zdroj JŘ <i class="fas fa-external-link-alt"></i></a>` : ''}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${spzBadge}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${startStr}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${statusHtml}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
              ${spzSafe !== 'Neznámá' ? `<a href="/historie/${spzSafe}" class="button is-small is-primary"><i class="fas fa-list" style="margin-right: 5px;"></i> Detail vozu</a>` : `<span style="font-size:11px; color:#94a3b8;">Čeká na SPZ</span>`}
            </td>
          </tr>`;
      });
      tbody.innerHTML = newHtml;
    } catch(e) { console.error(e); }
  }
  document.getElementById('historySearch').addEventListener('input', function(e) {
    const val = e.target.value.toLowerCase().trim();
    document.querySelectorAll('#historyTableBody tr').forEach(row => {
      if (!row.hasAttribute('data-search')) return;
      row.style.display = row.getAttribute('data-search').includes(val) ? '' : 'none';
    });
  });
  loadIndex();
  setInterval(loadIndex, 10000);
  </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
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
      lastPosDiv.innerHTML = `
        <div style="display:flex; align-items:center; gap: 15px;">
          <div style="flex-grow: 1;">
            <strong style="color: white; font-size:16px;">Stav vozidla:</strong> <span style="font-size:16px;">${topStatus}</span><br>
            <span style="color: #cbd5e1; font-size: 14px;">Zaznamenáno: ${topTime}</span>
            ${liveIndicator}
          </div>
          <a href="/mapa#${currentLat},${currentLng}" class="button is-info is-medium" style="font-weight:bold;">
            <i class="fas fa-crosshairs" style="margin-right: 8px;"></i> Ukázat na mapě
          </a>
        </div>`;
      let newHtml = '';
      data.forEach(trip => {
        const cd = new Date(trip.created_at);
        const dayStr = cd.toLocaleDateString('cs-CZ');
        let startStr = trip.start_actual ? trip.start_actual : (trip.start_scheduled ? `<span style="color:#94a3b8;">${trip.start_scheduled} (Plán)</span>` : "---");
        let isFinished = trip.end_actual || trip.status.includes('Timeout');
        let endStr = "";
        if (isFinished) {
          endStr = `${trip.end_actual || 'Timeout'} <br><span style="font-size:11px; color:#94a3b8;">(${trip.status})</span>`;
        } else {
          endStr = `<span style="color:#eab308; font-weight:bold;"><i class="fas fa-spinner fa-pulse"></i> Probíhá...</span><br><span style="font-size:11px; color:#94a3b8;">${trip.status}</span>`;
        }
        newHtml += `
          <tr style="border-color: #334155;">
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; color:#cbd5e1;">${dayStr}<br><span style="font-size:10px; color:#64748b;">${trip.trip_id.substring(0,8)}...</span></td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${trip.linka}${trip.jr_link ? `<br><a href="${trip.jr_link}" target="_blank" style="font-size:11px; color:#38bdf8;">Aktuální JŘ <i class="fas fa-external-link-alt"></i></a>` : ''}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #10b981;">${startStr}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #ef4444;">${endStr}</td>
            <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
              <a href="/mapa#${trip.last_lat},${trip.last_lng}" class="button is-small is-outlined" style="background: transparent; color: #cbd5e1; border-color: #4b5563;"><i class="fas fa-map-marker-alt"></i> Mapa</a>
            </td>
          </tr>`;
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
/* ─── TOP PANEL ─── */
#panel-zone{position:fixed;top:0;left:0;right:0;height:40px;z-index:3000;pointer-events:auto;}
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
.n-home{background:#38bdf8;color:#0f172a;}
.n-home:hover{background:#0284c7;color:#fff;}
.n-provoz{background:#334155;color:#fff;}
.n-provoz:hover{background:#475569;}
/* ─── MARKERS ─── */
.bus-marker,.train-marker{border:2px solid #fff;text-align:center;color:#fff;font-weight:bold;font-size:10px;line-height:20px;box-shadow:0 0 5px rgba(0,0,0,.5);}
.bus-marker{border-radius:50%;}.train-marker{border-radius:4px;}
.bg-green{background:#10b981;}.bg-red{background:#ef4444;}
.bg-blue{background:#3b82f6;}.bg-darkblue{background:#1e3a8a;}
.bg-gray{background:#64748b;border-color:#475569!important;color:#cbd5e1;}
.bg-purple{background:#a855f7;}
.bg-bug{background:#374151;border-color:#6b7280!important;border-style:dashed!important;color:#9ca3af;opacity:.65;}
/* ─── POPUP ─── */
.dark-popup .leaflet-popup-content-wrapper{background:#1e293b;color:#fff;border:1px solid #334155;padding:0;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.65);}
.dark-popup .leaflet-popup-tip{background:#1e293b;}
.dark-popup .leaflet-popup-content{margin:0;width:286px!important;}
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
#sw{display:none;position:fixed;top:68px;left:50%;transform:translateX(-50%);
  background:linear-gradient(135deg,#991b1b,#ef4444);color:#fff;
  padding:11px 18px;border-radius:10px;font-weight:bold;z-index:5000;
  text-align:center;max-width:92vw;width:410px;
  box-shadow:0 4px 25px rgba(239,68,68,.55);border:1px solid rgba(255,255,255,.15);
  animation:swPulse 2s ease-in-out infinite alternate;}
@keyframes swPulse{0%{box-shadow:0 4px 20px rgba(239,68,68,.4);}100%{box-shadow:0 4px 45px rgba(239,68,68,.9);}}
/* ─── JŘ MODAL ─── */
#ttm{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.72);z-index:6000;align-items:center;justify-content:center;}
#ttm.open{display:flex;}
#ttb{background:#0f172a;border-radius:10px;padding:20px;max-width:700px;width:95%;border:1px solid #38bdf8;max-height:86vh;overflow-y:auto;position:relative;}
#ttc-btn{position:absolute;top:10px;right:10px;background:#ef4444;color:#fff;border:none;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;font-weight:bold;}
/* ─── MOBILE ─── */
@media(max-width:600px){
  #top-nav{gap:6px;padding:0 8px;height:52px;}
  .n-title .a{font-size:13px;}.n-warn{font-size:9px;padding:2px 5px;display:none;}
  .n-btn{font-size:11px;padding:5px 7px;}.n-clock{font-size:11px;padding:4px 7px;}
  #hf{width:210px;}.dark-popup .leaflet-popup-content{width:252px!important;}
}
</style>

<div id="map-wrap">
  <div id="panel-zone"></div>

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
    <div class="n-clock">🕐 <span id="systemTimeClock">--:--:--</span></div>
    <a href="https://datacorebot.koyeb.app/" class="n-btn n-home">🏠 Domů</a>
    <a href="/provoz-idpk" class="n-btn n-provoz">🚌 Provoz IDPK</a>
  </nav>

  <div id="map"></div>

  <!-- Startup warning -->
  <div id="sw">
    <div style="font-size:17px;margin-bottom:3px;">⚠️ Mapa se startuje</div>
    <div style="font-size:12px;font-weight:normal;opacity:.9;">Probíhá načítání dat z Inflow a Arriva — vyčkejte prosím, data se brzy zobrazí.</div>
    <div id="sw-cd" style="margin-top:5px;font-size:11px;opacity:.8;"></div>
  </div>

  <!-- JŘ Modal -->
  <div id="ttm">
    <div id="ttb">
      <button id="ttc-btn" onclick="document.getElementById('ttm').classList.remove('open')">✕</button>
      <div id="ttc" style="color:white;">Načítám...</div>
    </div>
  </div>

  <!-- Follow HUD -->
  <div id="hud">
    <div id="hf">
      <div class="hh">
        <span class="hl">📡 SLEDOVÁNÍ SPOJE</span>
        <button class="hb-mn" onclick="minHud()" title="Minimalizovat">−</button>
      </div>
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

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
// ─── PANEL ────────────────────────────────────────────────────────────────────
const nav = document.getElementById('top-nav');
const pz  = document.getElementById('panel-zone');
let hideT = null;
function showNav(){ clearTimeout(hideT); nav.classList.add('vis'); }
function hideNav(){ hideT = setTimeout(()=>nav.classList.remove('vis'), 450); }
pz.addEventListener('mouseenter', showNav);
nav.addEventListener('mouseenter', showNav);
nav.addEventListener('mouseleave', hideNav);
document.addEventListener('touchstart', e=>{
  if(e.touches[0].clientY < 38){ showNav(); clearTimeout(hideT); hideT=setTimeout(()=>nav.classList.remove('vis'),4500); }
  else if(!nav.contains(e.target)) hideNav();
},{passive:true});

// ─── MAP ──────────────────────────────────────────────────────────────────────
var dLat=49.7384, dLng=13.3736, dZoom=12;
var hp = window.location.hash.replace('#','').split(',');
if(hp.length===2){ dLat=parseFloat(hp[0]); dLng=parseFloat(hp[1]); dZoom=17; }
var map = L.map('map',{zoomControl:false}).setView([dLat,dLng],dZoom);
L.control.zoom({position:'bottomleft'}).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);
var ml = L.layerGroup().addTo(map);
if(hp.length===2) L.circleMarker([dLat,dLng],{radius:28,color:'#ef4444',weight:2,opacity:.8,fillOpacity:.12}).addTo(map);

// ─── HUD ──────────────────────────────────────────────────────────────────────
let lastArr=[], followId=null, hudMin=false, followInflowId=null;

function stopFollow(){
  followId=null; followInflowId=null; hudMin=false;
  document.getElementById('hud').style.display='none';
  document.getElementById('hf').style.display='block';
  document.getElementById('hm').style.display='none';
}
function minHud(){
  hudMin=true;
  document.getElementById('hf').style.display='none';
  document.getElementById('hm').style.display='flex';
}
function maxHud(){
  hudMin=false;
  document.getElementById('hf').style.display='block';
  document.getElementById('hm').style.display='none';
}
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
  if(b.color_class==='bg-blue'){
    let dm=Math.abs(dv),dh=Math.floor(dm/60),dmin=dm%60;
    de.innerHTML=`<span style="color:#3b82f6;">Odjezd za ${dh>0?dh+'h ':''} ${dmin}min</span>`;
  } else if(b.color_class==='bg-darkblue'){
    de.innerHTML=`<span style="color:#60a5fa;">Náskok ${Math.abs(dv)} min</span>`;
  } else if(dv>=5){
    de.innerHTML=`<span style="color:#ef4444;">+${dv} min</span>`;
  } else if(dv<-1){
    de.innerHTML=`<span style="color:#60a5fa;">−${Math.abs(dv)} min</span>`;
  } else { de.innerHTML='<span style="color:#10b981;">V čase</span>'; }
  document.getElementById('h-status').textContent=b.status||'—';
  document.getElementById('hm-line').textContent='L'+(b.line||'?');
  let jrBtn=document.getElementById('h-jr');
  let iid=followInflowId||b.id;
  jrBtn.onclick=()=>showTT(iid);
}

// ─── TIMETABLE MODAL ──────────────────────────────────────────────────────────
async function showTT(busId){
  document.getElementById('ttm').classList.add('open');
  document.getElementById('ttc').innerHTML="<div style='text-align:center;padding:40px;color:#38bdf8;'><i class='fas fa-circle-notch fa-spin fa-2x'></i><p style='margin-top:14px;font-weight:bold;'>Načítám JŘ z PVVD...</p></div>";
  try{
    let r=await fetch('/api/bus_detail/'+busId);
    document.getElementById('ttc').innerHTML=await r.text();
  }catch(e){document.getElementById('ttc').innerHTML="<p style='color:#ef4444;padding:20px;text-align:center;'>Chyba při načítání JŘ.</p>";}
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

// ─── MAIN FETCH ───────────────────────────────────────────────────────────────
async function fetchBuses(){
  try{
    let r=await fetch('/api/live_buses'), data=await r.json();
    if(data.server_time) document.getElementById('systemTimeClock').innerText=data.server_time;
    if(typeof data.worker_uptime_seconds==='number') checkSW(data.worker_uptime_seconds);
    if(data.status!=='success') return;
    lastArr=data.buses;
    if(followId){
      let fb=data.buses.find(b=>b.id===followId);
      if(fb&&fb.lat){ map.setView([fb.lat,fb.lng]); if(!hudMin) updateHud(fb); else document.getElementById('hm-line').textContent='L'+(fb.line||'?'); }
      else document.getElementById('h-status').textContent='⚠ Ztráta signálu';
    }
    ml.clearLayers();
    data.buses.forEach(bus=>{
      if(!bus.lat||!bus.lng) return;
      let mc=bus.color_class, dv=parseInt(bus.delay), dTxt='';
      if(mc==='bg-gray'||mc==='bg-bug') dTxt='<span style="color:#94a3b8;">N/A</span>';
      else if(mc==='bg-purple') dTxt='<span style="color:#a855f7;">Konečná</span>';
      else if(mc==='bg-blue'){
        let dm=Math.abs(dv),dh=Math.floor(dm/60),dmn=dm%60,ts=dh>0?dh+'h '+dmn+'m':dmn+' min';
        dTxt=`<span style="color:#3b82f6;">Za ${ts}</span>`;
      } else if(mc==='bg-darkblue'){
        dTxt=`<span style="color:#60a5fa;">Náskok ${Math.abs(dv)} min</span>`;
      } else if(dv>=5){
        dTxt=`<span style="color:#ef4444;">Zpoždění ${dv} min</span>`;
      } else { dTxt=`<span style="color:#10b981;">+${dv} min</span>`; }

      let shape=bus.is_train?'train-marker':'bus-marker';
      let icon=L.divIcon({className:shape+' '+mc,iconSize:[24,24]});
      let marker=L.marker([bus.lat,bus.lng],{icon});

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
      if(mc==='bg-bug') bugW=`<div style="background:#374151;border:1px dashed #6b7280;border-radius:5px;padding:7px;margin:5px 0;color:#9ca3af;font-size:10px;text-align:center;"><i class="fas fa-exclamation-triangle" style="color:#f59e0b;"></i> <b style="color:#f59e0b;">BUG – NEAKTUÁLNÍ MÍSTO</b><br>SPZ ${bus.spz} jede na jiném místě.</div>`;
      let sc='#10b981';
      if(mc==='bg-bug'||bus.status.includes('příliš')) sc='#6b7280';
      else if(bus.status.includes('Stojí')) sc='#ef4444';
      else if(bus.status.includes('Konečná')||bus.status.includes('Ztráta')) sc='#a855f7';
      else if(bus.status.includes('Čeká')||bus.status.includes('Začátek')) sc='#3b82f6';
      else if(bus.status.includes('Odstaven')||bus.status.includes('signál')) sc='#94a3b8';
      else if(bus.status.includes('Náskok')) sc='#60a5fa';
      let fTxt=(followId===bus.id)?'✕ Zrušit sledování':'📡 Sledovat';
      let fSt=(followId===bus.id)?'background:#ef4444;color:#fff;':'background:#3b82f6;color:#fff;';
      let popH=`
        <div class="ph" style="${mc==='bg-bug'?'background:#1f2937;':''}">
          <h3 class="ph-t" style="${mc==='bg-bug'?'color:#9ca3af;':''}"><i class="${bus.is_train?'fas fa-train':'fas fa-bus'}"></i> Linka ${bus.line}</h3>
        </div>
        <div class="pb">
          ${bugW}
          <div class="pr"><span class="pl">Cíl:</span><span class="pv">${bus.destination||'Neznámý'}</span></div>
          ${spzH}${invTxt}
          <div class="pr"><span class="pl">Status:</span><span class="pv" style="color:${sc};">${bus.status}</span></div>
          <div class="pr" style="border:none;"><span class="pl">JŘ:</span><span class="pv">${dTxt}</span></div>
          <button class="pa" onclick="showTT('${bus.id}')"><i class="fas fa-list-alt"></i> Zobrazit Jízdní řád</button>
          <button class="pa" style="${fSt}margin-top:5px;" onclick="toggleFollow('${bus.id}','${bus.id}')">${fTxt}</button>
          ${histBtn}
        </div>`;
      marker.bindPopup(popH,{className:'dark-popup'});
      ml.addLayer(marker);
    });
  }catch(e){console.error(e);}
}
fetchBuses();
setInterval(fetchBuses,10000);
</script>
"""


# --- GLOBÁLNÍ STAV ---
GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA  = []
TRACKED_SPZS     = set()
WORKER_START_TIME = None   # nastavuje se při startu workeru

cj     = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


# --- POMOCNÉ FUNKCE ---

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)


def is_same_line(l1, l2):
    """Porovnání čísel linek - číselná část musí souhlasit."""
    if not l1 or not l2 or l1 == "Neznámá" or l2 == "Neznámá":
        return False
    cl1 = re.sub(r'\D', '', l1)
    cl2 = re.sub(r'\D', '', l2)
    if not cl1 or not cl2:
        return l1 == l2
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


def new_cache_entry(bus_id, trip_id, lat, lng, line, dest, is_train, delay, now, ghost_spz=None):
    """Vytvoří nový prázdný záznam do cache."""
    return {
        "trip_id":            trip_id,
        "inflow_id":          bus_id,
        "lat":                lat,
        "lng":                lng,
        "line":               line,
        "real_linka_spoj":    None,
        "destination":        dest,
        "is_train":           is_train,
        "raw_delay":          delay,
        # SPZ
        "spz":                ghost_spz,
        "spz_verified":       False,
        "spz_locked":         False,
        "spz_stable_ticks":   0,
        "spz_last_verified":  None,
        "investigating":      False,
        "investigation_spz":  None,
        "investigation_start": None,
        # Časy
        "first_seen":         now,
        "last_inflow_seen":   now,
        "last_moved":         now,
        "created_at":         now,
        "actual_start_time":  None,
        "actual_end_time":    None,
        # JŘ
        "first_dep_time":     None,
        "last_dep_time":      None,
        "tt_last_fetch":      None,
        "tt_is_fetching":     False,
        # Status
        "status":             "Načítání...",
        "color_class":        "bg-gray",
        "is_offline":         False,
        "db_first_upsert":    False,
        "final_delay_display": 0,
    }


# --- STAHOVÁNÍ JÍZDNÍHO ŘÁDU (vlákno na pozadí) ---

def fetch_tt_bg(bus_id, cached_dict):
    """Stáhne jízdní řád z Inflow a uloží časy do cache."""
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


# --- ZÁPIS DO DATABÁZE ---

def upsert_to_history(db, c):
    """Zapíše / aktualizuje záznam spoje do Supabase.
    Zapisuje POUZE ověřené záznamy se stabilní SPZ."""
    global TRACKED_SPZS
    if c.get("is_train"):
        return
    if not db:
        return
    if not c.get("spz_verified"):
        return
    if c.get("spz_stable_ticks", 0) < SPZ_STABLE_TICKS:
        return  # Příliš brzy – SPZ ještě není stabilní

    spz = c.get("spz")
    if not spz or spz == "Neznámá":
        return

    final_linka = c.get("real_linka_spoj") or c.get("line", "")
    clean_line  = re.sub(r'\D', '', final_linka)

    # Sledujeme jen linky 490 a 496
    if clean_line.startswith("490") or clean_line.startswith("496"):
        TRACKED_SPZS.add(spz)

    if spz not in TRACKED_SPZS:
        return

    try:
        jr_l = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={c['inflow_id']}&currentStopId=0"
        data = {
            "trip_id":        c["trip_id"],
            "spz":            spz,
            "spz_verified":   True,
            "linka":          final_linka,
            "jr_link":        jr_l,
            "start_scheduled": c.get("first_dep_time"),
            "start_actual":   c.get("actual_start_time"),
            "end_actual":     c.get("actual_end_time"),
            "last_lat":       c.get("lat"),
            "last_lng":       c.get("lng"),
            "status":         c.get("status"),
            "created_at":     c["created_at"].isoformat(),
            "updated_at":     get_prague_time().isoformat(),
        }
        db.table("bus_history").upsert(data).execute()
    except Exception:
        pass


# --- HLAVNÍ SMYČKA NA POZADÍ ---

def background_map_worker():
    global TRACKED_SPZS, WORKER_START_TIME
    print("[MAPA] Worker startuje (vylepšená SPZ logika v2)...", flush=True)
    WORKER_START_TIME = get_prague_time()

    db_client = get_db_client()
    if db_client:
        try:
            res = db_client.table("bus_history").select("spz").execute()
            for r in res.data:
                if r.get("spz") and r["spz"] != "Neznámá":
                    TRACKED_SPZS.add(r["spz"])
            print(f"[MAPA] Načteno {len(TRACKED_SPZS)} sledovaných SPZ z databáze.")
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

            # --- Denní čištění DB ---
            if db_client and (now - last_db_cleanup).total_seconds() > 86400:
                try:
                    thirty_days_ago = (now - timedelta(days=30)).isoformat()
                    db_client.table("bus_history").delete().lt("created_at", thirty_days_ago).execute()
                except Exception:
                    pass
                last_db_cleanup = now

            # ═══════════════════════════════════════════════════════
            # SEKCE 1: Stažení dat z obou API
            # ═══════════════════════════════════════════════════════
            data_inflow = []
            data_arriva = []

            url_inflow = f"{url_inflow_base}?_={int(time.time() * 1000)}"
            try:
                req1 = urllib.request.Request(url_inflow, headers=inflow_headers)
                with urllib.request.urlopen(req1, timeout=5) as r1:
                    data_inflow = json.loads(r1.read().decode())
            except Exception:
                try:
                    req1_post = urllib.request.Request(
                        url_inflow, data=b"{}", headers=inflow_headers, method='POST')
                    with urllib.request.urlopen(req1_post, timeout=5) as r1_post:
                        data_inflow = json.loads(r1_post.read().decode())
                except Exception:
                    pass

            try:
                arriva_payload = {
                    "operationName": "busesCurrentLocation",
                    "variables": {},
                    "query": (
                        "query busesCurrentLocation {\n"
                        "  busesCurrentLocations {\n"
                        "    angle delay destinationName lastStopName\n"
                        "    latitude longitude linkNumber state type\n"
                        "    mainType spz updated linkNumberAlias __typename\n"
                        "  }\n}"
                    )
                }
                req2 = urllib.request.Request(
                    url_arriva,
                    data=json.dumps(arriva_payload).encode('utf-8'),
                    headers={
                        'User-Agent':   'Mozilla/5.0',
                        'Content-Type': 'application/json',
                        'Origin':       'https://www.arriva.cz',
                        'Referer':      'https://www.arriva.cz/',
                    },
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

            # ═══════════════════════════════════════════════════════
            # SEKCE 2: Zpracování Inflow dat – nové a stávající busy
            # ═══════════════════════════════════════════════════════
            current_inflow_ids = set()

            if isinstance(data_inflow, list):
                for bus1 in data_inflow:
                    try:
                        bus_id  = str(bus1.get("id", "0"))
                        current_inflow_ids.add(bus_id)
                        line    = str(bus1.get("text", "")).strip()
                        lat1    = bus1.get("lat", 0)
                        lng1    = bus1.get("lng", 0)
                        delay   = int(bus1.get("delay", 0)) if bus1.get("delay") is not None else 0
                        dest1   = str(bus1.get("finalStopName", "")).strip()
                        traction = str(bus1.get("traction", "BUS")).upper()
                        is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]

                        if bus_id not in GLOBAL_BUS_CACHE:
                            # ─── NOVÝ BUS: ghost matching ───────────────────
                            TRIP_COUNTER += 1
                            ghost_spz      = None
                            ghost_trip_id  = f"TRIP-{TRIP_COUNTER}"
                            ghost_candidates = []

                            for gid, gc in list(GLOBAL_BUS_CACHE.items()):
                                # Kandidát musí být offline a mít SPZ
                                if not (gc.get("is_offline") and gc.get("spz") and gc["spz"] != "Neznámá"):
                                    continue
                                # Kandidát nesmí být příliš starý
                                offline_age_min = (now - gc["last_inflow_seen"]).total_seconds() / 60.0
                                if offline_age_min > GHOST_MAX_OFFLINE_MIN:
                                    continue

                                g_dist     = math.hypot(lat1 - gc["lat"], lng1 - gc["lng"])
                                line_match = is_same_line(line, gc["line"])

                                # Přísná vzdálenost NEBO volná vzdálenost se shodou linky
                                if g_dist < GHOST_DIST_STRICT or (g_dist < GHOST_DIST_LOOSE and line_match):
                                    # Nižší skóre = lepší kandidát
                                    score = g_dist \
                                          - (0.005 if line_match else 0) \
                                          + (offline_age_min * 0.0005)
                                    ghost_candidates.append((gid, gc, g_dist, score))

                            if ghost_candidates:
                                ghost_candidates.sort(key=lambda x: x[3])
                                best_gid, best_gc, _, _ = ghost_candidates[0]
                                ghost_spz = best_gc["spz"]
                                # Zdědíme trip_id pokud se shoduje linka (pokračování spoje)
                                if is_same_line(line, best_gc["line"]):
                                    ghost_trip_id = best_gc["trip_id"]
                                del GLOBAL_BUS_CACHE[best_gid]
                                print(f"[MAPA-GHOST] Bus {bus_id} ({line}) zdědil SPZ {ghost_spz} od {best_gid}")

                            GLOBAL_BUS_CACHE[bus_id] = new_cache_entry(
                                bus_id, ghost_trip_id, lat1, lng1,
                                line, dest1, is_train, delay, now, ghost_spz
                            )

                        else:
                            # ─── EXISTUJÍCÍ BUS: aktualizace ─────────────────
                            c = GLOBAL_BUS_CACHE[bus_id]
                            c["last_inflow_seen"] = now
                            c["is_offline"]       = False
                            c["raw_delay"]        = delay
                            c["is_train"]         = is_train

                            dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])

                            # Detekce změny linky (nový spoj stejného vozidla)
                            if not is_same_line(c["line"], line) and line and c["line"] != "Neznámá":
                                if not c["actual_end_time"]:
                                    c["actual_end_time"] = now.strftime('%H:%M')
                                    c["status"] = "Ukončeno (Začátek nového spoje)"
                                    if c.get("spz_verified"):
                                        upsert_to_history(db_client, c)
                                TRIP_COUNTER += 1
                                c["trip_id"]          = f"TRIP-{TRIP_COUNTER}"
                                c["line"]             = line
                                c["real_linka_spoj"]  = None
                                c["destination"]      = dest1
                                c["first_dep_time"]   = None
                                c["last_dep_time"]    = None
                                c["actual_start_time"] = None
                                c["actual_end_time"]  = None
                                c["created_at"]       = now
                                c["status"]           = "Načítání..."
                                c["spz_locked"]       = False
                                c["spz_verified"]     = False
                                c["spz_stable_ticks"] = 0
                                c["investigating"]    = False
                            else:
                                # Aktualizace destinace jen pokud je delší (přesnější)
                                if dest1 and len(dest1) > len(c.get("destination", "")):
                                    c["destination"] = dest1
                                if line and len(line) > len(c.get("line", "")):
                                    c["line"] = line

                            if dist_moved > 0.0001:
                                c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                    except Exception:
                        continue

            # ═══════════════════════════════════════════════════════
            # SEKCE 3: Detekce duplikátních SPZ s grace periodou + BUG detekce
            # ═══════════════════════════════════════════════════════
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
                        # BUG tag se zrušil – bus je sám se svou SPZ
                        GLOBAL_BUS_CACHE[bus_ids[0]]["color_class"] = "bg-gray"
                        GLOBAL_BUS_CACHE[bus_ids[0]]["status"]      = "Stojí"
                    continue

                # ── Detekce BUG: jeden se hýbe, druhý stojí se stejnou SPZ ──
                moving_bids     = [bid for bid in bus_ids
                                   if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() < 60]
                stationary_bids = [bid for bid in bus_ids
                                   if (now - GLOBAL_BUS_CACHE[bid]["last_moved"]).total_seconds() > 180]

                if moving_bids and stationary_bids:
                    # Jasný případ: jede nový bus, starý nezmizel = MAP BUG
                    for bid in stationary_bids:
                        bc = GLOBAL_BUS_CACHE[bid]
                        bc["status"]             = "BUG - NEAKTUÁLNÍ MÍSTO"
                        bc["color_class"]        = "bg-bug"
                        bc["investigating"]      = False
                        bc["investigation_start"] = None
                    for bid in moving_bids:
                        bc = GLOBAL_BUS_CACHE[bid]
                        bc["investigating"]      = False
                        bc["investigation_start"] = None
                    continue  # Přeskočíme standardní duplikát logiku

                # ── Standardní duplikát – výběr vítěze skórem ──
                def score_candidate(bid):
                    bc = GLOBAL_BUS_CACHE[bid]
                    return (bc.get("spz_stable_ticks", 0),
                            bc.get("spz_last_verified") or datetime.min)

                best_bid = max(bus_ids, key=score_candidate)

                for bid in bus_ids:
                    bc = GLOBAL_BUS_CACHE[bid]
                    if bid == best_bid:
                        bc["investigating"]       = False
                        bc["investigation_start"] = None
                    else:
                        bc["spz_verified"]      = False
                        bc["spz_locked"]        = False
                        bc["investigating"]     = True
                        bc["investigation_spz"] = spz_val
                        if bc.get("investigation_start") is None:
                            bc["investigation_start"] = now
                        elif (now - bc["investigation_start"]).total_seconds() > DUPLICATE_GRACE_SEC:
                            bc["spz"]                 = None
                            bc["investigating"]       = False
                            bc["investigation_start"] = None
                            bc["spz_stable_ticks"]    = 0

            # ═══════════════════════════════════════════════════════
            # SEKCE 4: Offline busy a timeouty
            # ═══════════════════════════════════════════════════════
            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                offline_mins = (now - c["last_inflow_seen"]).total_seconds() / 60.0
                total_mins   = (now - c["first_seen"]).total_seconds()       / 60.0

                # Timeout: nový den nebo příliš dlouhý spoj
                if (c["created_at"].date() != now.date() or total_mins > 300) and not c["actual_end_time"]:
                    c["actual_end_time"] = now.strftime('%H:%M')
                    c["status"]          = "Timeout (Příliš dlouho / Nový den)"
                    c["color_class"]     = "bg-gray"
                    if c.get("spz_verified"):
                        upsert_to_history(db_client, c)
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue

                if bus_id not in current_inflow_ids:
                    if offline_mins > 720:
                        del GLOBAL_BUS_CACHE[bus_id]
                        continue
                    c["is_offline"] = True
                    if offline_mins >= 15:
                        c["status"]      = "Odstaven (Bez signálu)"
                        c["color_class"] = "bg-gray"
                        c["raw_delay"]   = 0
                        if c.get("spz_verified"):
                            upsert_to_history(db_client, c)
                    elif offline_mins > 2:
                        if not c["actual_end_time"]:
                            c["actual_end_time"] = now.strftime('%H:%M')
                        c["status"]      = "Ztráta polohy (Konečná)"
                        c["color_class"] = "bg-purple"
                        c["raw_delay"]   = 0
                        if c.get("spz_verified"):
                            upsert_to_history(db_client, c)

            # ═══════════════════════════════════════════════════════
            # SEKCE 5: Výpočet statusů, barev a SPZ párování
            # ═══════════════════════════════════════════════════════
            new_live_data       = []
            tt_fetches_this_tick = 0

            for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
                inactive_mins = (now - c["last_moved"]).total_seconds() / 60.0

                # ── Offline busy: jen zobrazíme, neparujeme SPZ ────────────
                if c.get("is_offline"):
                    last_up = c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A"
                    final_line_disp = (
                        c.get("real_linka_spoj") or c["line"]
                        if c["line"] else ("Vlak" if c["is_train"] else "Neznámá")
                    )
                    new_live_data.append({
                        "id": bus_id, "trip_id": c["trip_id"],
                        "lat": c["lat"], "lng": c["lng"],
                        "line": final_line_disp, "delay": 0,
                        "destination": c["destination"],
                        "spz": c["spz"] or "Neznámá",
                        "spz_verified": c.get("spz_verified", False),
                        "is_train": c["is_train"],
                        "status": c["status"], "color_class": c["color_class"],
                        "inactive_minutes": inactive_mins, "last_updated": last_up,
                        "investigating": False, "investigation_spz": "",
                    })
                    continue

                lat1  = c["lat"]
                lng1  = c["lng"]
                line  = c["line"]
                dest1 = c["destination"]
                is_train = c["is_train"]
                is_moving = inactive_mins < 1
                delay_val = c["raw_delay"]

                # ── SPZ PÁROVÁNÍ S ARRIVA ──────────────────────────────────
                if not is_train and not c.get("investigating"):
                    i_clean  = re.sub(r'\D', '', line)
                    d1_clean = re.sub(r'\W+', '', dest1.lower())

                    best_spz       = None
                    best_match_dest = False
                    best_dist      = 999.0

                    for b in data_arriva:
                        a_line  = str(b.get("linkNumber", "")).strip()
                        a_clean = re.sub(r'\D', '', a_line)
                        if not (i_clean and a_clean and
                                (i_clean.endswith(a_clean) or a_clean.endswith(i_clean))):
                            continue
                        dist = math.hypot(lat1 - b.get("latitude", 0),
                                          lng1 - b.get("longitude", 0))
                        if dist < ARRIVA_MATCH_DIST and dist < best_dist:
                            best_dist = dist
                            a_dest    = str(b.get("destinationName", "")).lower()
                            d2_clean  = re.sub(r'\W+', '', a_dest)
                            best_match_dest = bool(
                                d1_clean in d2_clean or d2_clean in d1_clean
                                or not d1_clean or not d2_clean
                            )
                            best_spz = b.get("spz", "").strip() or None

                    if best_spz and best_spz != "Neznámá":
                        current_spz = c.get("spz")

                        if best_spz == current_spz:
                            # ✓ Potvrzení stejné SPZ
                            c["spz_stable_ticks"] = c.get("spz_stable_ticks", 0) + 1
                            if best_match_dest:
                                c["spz_last_verified"] = now
                        else:
                            # ≠ Jiná SPZ nalezena
                            last_v = c.get("spz_last_verified")
                            recently_verified = (
                                last_v is not None
                                and (now - last_v).total_seconds() < SPZ_HOLD_MINUTES * 60
                                and c.get("spz_verified")
                            )
                            if recently_verified:
                                # Nedávno ověřená SPZ – nedáme se přepsat, jen sledujeme
                                pass
                            else:
                                # Přepíšeme SPZ
                                if c.get("spz_verified") and current_spz and db_client:
                                    try:
                                        db_client.table("bus_history").update({
                                            "status":       "Falešný záznam (SPZ opravena)",
                                            "spz_verified": False,
                                        }).eq("trip_id", c["trip_id"]).execute()
                                    except Exception:
                                        pass
                                    TRIP_COUNTER   += 1
                                    c["trip_id"]    = f"TRIP-{TRIP_COUNTER}"
                                c["spz"]             = best_spz
                                c["spz_stable_ticks"] = 1
                                c["spz_verified"]    = False
                                c["spz_locked"]      = False
                                if best_match_dest:
                                    c["spz_last_verified"] = now

                        # Verifikace po dosažení stability (pohyb NENÍ podmínkou)
                        if c.get("spz_stable_ticks", 0) >= SPZ_STABLE_TICKS and best_match_dest:
                            c["spz_verified"]    = True
                            c["spz_locked"]      = True   # ← zamkne i při stání
                            c["spz_last_verified"] = now

                    else:
                        # Arriva nic nevrátila – držíme SPZ podle stáří posledního ověření
                        last_v = c.get("spz_last_verified")
                        if last_v is None or (now - last_v).total_seconds() >= SPZ_HOLD_MINUTES * 60:
                            # Příliš staré – zrušíme verifikaci, ale SPZ zobrazíme dál jako "odhad"
                            c["spz_verified"] = False
                            c["spz_locked"]   = False
                        # else: SPZ je čerstvá, nic neděláme

                # ── STAHOVÁNÍ JÍZDNÍHO ŘÁDU ───────────────────────────────
                if not is_train:
                    tt_age = (now - c["tt_last_fetch"]).total_seconds() if c.get("tt_last_fetch") else 9999
                    if tt_age > 300 and not c.get("tt_is_fetching") and tt_fetches_this_tick < 5:
                        tt_fetches_this_tick  += 1
                        c["tt_last_fetch"]     = now
                        c["tt_is_fetching"]    = True
                        threading.Thread(
                            target=fetch_tt_bg, args=(bus_id, c), daemon=True
                        ).start()

                # ── BAREVNÁ LOGIKA A STATUS ────────────────────────────────
                # BUG marker se nemění
                if c.get("color_class") == "bg-bug":
                    pass  # Zachováme BUG status dokud se bus nerozjede

                else:
                    is_before_departure = False
                    time_to_dep         = 0

                    if c["first_dep_time"]:
                        try:
                            dh, dm    = map(int, c["first_dep_time"].split(':'))
                            dep_total = dh * 60 + dm
                            cur_total = now.hour * 60 + now.minute
                            diff      = dep_total - cur_total
                            if diff < -720: diff += 1440
                            elif diff > 720: diff -= 1440
                            # Světle modrá: víc než 1 minuta do odjezdu (i při pohybu)
                            if diff > 1 and not c.get("actual_start_time"):
                                is_before_departure = True
                                time_to_dep = int(diff)
                        except Exception:
                            pass

                    old_status = c["status"]

                    if is_before_departure:
                        # ── Světle modrá: čeká na odjezd (> 1 min, i v pohybu) ──
                        c["actual_end_time"] = None
                        if time_to_dep <= 240:
                            c["status"]      = f"Čeká na odjezd ({time_to_dep} min)"
                            c["color_class"] = "bg-blue"
                        else:
                            c["status"]      = "Čeká na spoj (>4h)"
                            c["color_class"] = "bg-gray"
                        delay_val = -time_to_dep

                    elif delay_val <= -10000:
                        # ── Konečná zastávka nebo odstaven ──
                        if inactive_mins > 10:
                            c["status"]      = "Odstaven"
                            c["color_class"] = "bg-gray"
                        else:
                            c["status"]      = "Konečná zastávka"
                            c["color_class"] = "bg-purple"
                            if not c["actual_end_time"]:
                                c["actual_end_time"] = now.strftime('%H:%M')

                    elif delay_val < -1 and c.get("actual_start_time"):
                        # ── Tmavě modrá: uprostřed linky, jede před časem ──
                        c["status"]      = "Jízda (Náskok)" if is_moving else "Stojí (Náskok)"
                        c["color_class"] = "bg-darkblue"

                    else:
                        # ── Normální jízda ──
                        c["status"]      = "Jízda" if is_moving else "Stojí"
                        c["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                    # ── Šedá pro autobusy stojící příliš dlouho ──────────────
                    # (jen pokud already started, není konečná/BUG/gray)
                    if (not is_moving
                            and inactive_mins > 30
                            and c.get("actual_start_time")
                            and c["color_class"] not in ("bg-purple", "bg-gray", "bg-bug", "bg-blue")):
                        c["status"]      = f"Stojí příliš dlouho ({int(inactive_mins)} min)"
                        c["color_class"] = "bg-gray"

                if is_moving and not c["actual_start_time"] and not is_train:
                    c["actual_start_time"] = now.strftime('%H:%M')

                c["final_delay_display"] = delay_val

                # ── DB UPSERT (jen ověřené SPZ) ───────────────────────────
                old_status = c.get("_last_db_status")
                if c.get("spz_verified") and (old_status != c["status"] or is_moving or not c.get("db_first_upsert")):
                    upsert_to_history(db_client, c)
                    c["db_first_upsert"]    = True
                    c["_last_db_status"]    = c["status"]

                # ── Přidáme do live dat ────────────────────────────────────
                last_up = c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A"
                final_line_disp = (
                    c.get("real_linka_spoj") or c["line"]
                    if c["line"] else ("Vlak" if c["is_train"] else "Neznámá")
                )
                new_live_data.append({
                    "id":               bus_id,
                    "trip_id":          c["trip_id"],
                    "lat":              c["lat"],
                    "lng":              c["lng"],
                    "line":             final_line_disp,
                    "delay":            c.get("final_delay_display", 0),
                    "destination":      c["destination"],
                    "spz":              c["spz"] or "Neznámá",
                    "spz_verified":     c.get("spz_verified", False),
                    "is_train":         c["is_train"],
                    "status":           c["status"],
                    "color_class":      c["color_class"],
                    "inactive_minutes": inactive_mins,
                    "last_updated":     last_up,
                    "investigating":    c.get("investigating", False),
                    "investigation_spz": c.get("investigation_spz", ""),
                })

            global LIVE_BUSES_DATA
            LIVE_BUSES_DATA = new_live_data

            time.sleep(10)

        except Exception as crash_error:
            print(f"[MAPA CRITICAL] Worker smyčka selhala, restart za 10s! Chyba: {crash_error}",
                  flush=True)
            time.sleep(10)


def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()


# ─── FLASK ROUTES ─────────────────────────────────────────────────────────────

def _full_page(title, body_html, is_map=False):
    """Obalí HTML do kompletní stránky."""
    extra = 'overflow:hidden;' if is_map else ''
    return Response(
        f"""<!DOCTYPE html>
<html style="background:#0f172a;{extra}">
<head>
  <title>{title} | OIS IDPK</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
</head>
<body style="background:#0f172a;color:white;{extra}margin:0;padding:0;">
{body_html}
</body>
</html>""",
        mimetype='text/html'
    )


@mapa_bp.route('/mapa')
def stranka_mapa():
    return _full_page("Mapa", HTML_MAPA, is_map=True)


@mapa_bp.route('/historie')
def stranka_historie_index():
    return _full_page("Historie", HTML_HISTORIE_INDEX)


@mapa_bp.route('/historie/<spz>')
def stranka_historie_detail(spz):
    # Bezpečné nahrazení placeholderu (bez Jinja2 konfliktů)
    html = HTML_HISTORIE_DETAIL.replace('__SPZ__', spz)
    return _full_page(f"Vůz {spz}", html)


@mapa_bp.route('/api/live_buses')
def api_live_buses():
    now = get_prague_time()
    uptime = (now - WORKER_START_TIME).total_seconds() if WORKER_START_TIME else 9999
    return jsonify({
        "status":               "success",
        "server_time":          now.strftime('%H:%M:%S'),
        "worker_uptime_seconds": round(uptime),
        "buses":                LIVE_BUSES_DATA,
    })


@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    """Vrátí HTML jízdního řádu pro popup."""
    try:
        cb_time = int(time.time() * 1000)
        headers = {
            'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':          'https://pvvd.idpk.cz/',
        }
        # Info okno (linka, spoj)
        info_html = ""
        try:
            req_info = urllib.request.Request(
                f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb_time}",
                headers=headers
            )
            with opener.open(req_info, timeout=4) as r:
                info_html = r.read().decode('utf-8')
        except Exception:
            pass

        # Jízdní řád
        tt_html = ""
        try:
            req_tt = urllib.request.Request(
                f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}",
                headers=headers
            )
            with opener.open(req_tt, timeout=4) as r:
                tt_html = r.read().decode('utf-8')
        except Exception:
            tt_html = "<p style='color:#94a3b8;'>Jízdní řád není dostupný.</p>"

        html_out = f"""
        <div style="background:#0f172a; color:white; font-family:sans-serif;">
          <div style="background:#1e293b; padding:12px; border-radius:6px; margin-bottom:12px;">
            {info_html}
          </div>
          <div style="overflow-x:auto;">
            <style>
              table {{ border-collapse: collapse; width: 100%; }}
              th, td {{ border: 1px solid #334155; padding: 6px 10px; text-align: left; }}
              th {{ background: #0f172a; color: #38bdf8; }}
              tr:hover td {{ background: #1e293b; }}
              .current {{ background: #166534 !important; font-weight: bold; }}
            </style>
            {tt_html}
          </div>
        </div>"""
        return html_out
    except Exception as e:
        return f"<p style='color:#ef4444; padding:20px;'>Chyba při načítání JŘ: {e}</p>"


@mapa_bp.route('/api/history_full')
def api_history_full():
    db = get_db_client()
    if not db:
        return jsonify({"data": [], "error": "DB nedostupná"})
    try:
        res = (
            db.table("bus_history")
              .select("*")
              .order("created_at", desc=True)
              .limit(200)
              .execute()
        )
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)})


@mapa_bp.route('/api/history_spz/<spz>')
def api_history_spz(spz):
    db = get_db_client()
    if not db:
        return jsonify({"data": [], "error": "DB nedostupná"})
    try:
        res = (
            db.table("bus_history")
              .select("*")
              .eq("spz", spz)
              .order("created_at", desc=True)
              .limit(100)
              .execute()
        )
        return jsonify({"data": res.data})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)})
