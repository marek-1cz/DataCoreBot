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
<div style="padding: 10px; max-width: 1600px; margin: auto;">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 15px; gap: 10px;">
    <h2 style="color: var(--blue-main, #38bdf8); margin: 0; display:flex; align-items:center; gap: 10px;">
      <i class="fas fa-map-marked-alt"></i> Interaktivní Mapa Spojů
      <span class="tag is-warning is-light" style="font-size:12px; font-weight:bold;">Neoficiální mapa (Není garantována 100% přesnost)</span>
    </h2>
    <div class="tag is-dark is-large" style="border: 1px solid #38bdf8; font-weight: bold; color: #38bdf8; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">
      <i class="far fa-clock" style="margin-right:8px;"></i> <span id="systemTimeClock">--:--:--</span>
    </div>
  </div>
  <div id="map" style="width: 100%; height: 75vh; border-radius: 10px; border: 2px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 1;"></div>
  <div id="timetable-modal" class="modal" style="z-index: 9999;">
    <div class="modal-background" onclick="document.getElementById('timetable-modal').classList.remove('is-active')"></div>
    <div class="modal-content" style="background: #0f172a; border-radius: 8px; padding: 20px; max-width: 700px; width: 95%; border: 1px solid #38bdf8;">
      <div id="timetable-content" style="color: white; overflow-x: auto;">Načítám detail spoje...</div>
    </div>
    <button class="modal-close is-large" aria-label="close" onclick="document.getElementById('timetable-modal').classList.remove('is-active')"></button>
  </div>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    .bus-marker { border-radius: 50%; border: 2px solid white; text-align: center; color: white; font-weight: bold; font-size: 10px; line-height: 20px; box-shadow: 0 0 5px rgba(0,0,0,0.5); }
    .train-marker { border-radius: 4px; border: 2px solid white; text-align: center; color: white; font-weight: bold; font-size: 10px; line-height: 20px; box-shadow: 0 0 5px rgba(0,0,0,0.5); }
    .bg-green { background-color: #10b981; } .bg-red { background-color: #ef4444; } .bg-blue { background-color: #3b82f6; }
    .bg-darkblue { background-color: #1e3a8a; } .bg-gray { background-color: #64748b; border-color: #475569; color: #cbd5e1; }
    .bg-purple { background-color: #a855f7; }
    .dark-popup .leaflet-popup-content-wrapper { background: #1e293b; color: white; border: 1px solid #334155; padding: 0; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }
    .dark-popup .leaflet-popup-tip { background: #1e293b; border-bottom: 1px solid #334155; border-right: 1px solid #334155; }
    .dark-popup .leaflet-popup-content { margin: 0; width: 280px !important; }
    .popup-header { background: #0f172a; padding: 12px 15px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
    .popup-header-title { font-weight: bold; color: #38bdf8; font-size: 16px; margin: 0; }
    .popup-body { padding: 15px; font-size: 13px; line-height: 1.6; }
    .popup-row { display: flex; justify-content: space-between; margin-bottom: 6px; border-bottom: 1px dashed #334155; padding-bottom: 4px; }
    .popup-row:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
    .popup-label { color: #94a3b8; font-weight: 600; }
    .popup-value { font-weight: bold; text-align: right; max-width: 60%; word-wrap: break-word; }
    .badge-spz { background: #f59e0b; color: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 12px; border: 1px solid #d97706; }
    .btn-timetable { background: #38bdf8; color: #0f172a; border: none; padding: 10px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; margin-top: 10px; display: block; text-align: center; }
    .btn-timetable:hover { background: #0284c7; color: white; }
  </style>
  <script>
    var defaultLat = 49.7384, defaultLng = 13.3736, defaultZoom = 12;
    var hashParts = [];
    if (window.location.hash) {
      hashParts = window.location.hash.replace('#', '').split(',');
      if (hashParts.length === 2) { defaultLat = parseFloat(hashParts[0]); defaultLng = parseFloat(hashParts[1]); defaultZoom = 17; }
    }
    var map = L.map('map').setView([defaultLat, defaultLng], defaultZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
    var markersLayer = L.layerGroup().addTo(map);
    let lastDataArray = [];
    let followedBusId = null;
    map.on('dragstart', function() { followedBusId = null; });
    if (hashParts.length === 2) {
      L.circleMarker([defaultLat, defaultLng], {radius: 35, color: '#ef4444', weight: 3, opacity: 0.8, fillOpacity: 0.2}).addTo(map);
      L.circleMarker([defaultLat, defaultLng], {radius: 5, color: '#ef4444', weight: 5, opacity: 1, fillOpacity: 1}).addTo(map);
    }
    async function showTimetable(busId) {
      let modal = document.getElementById('timetable-modal');
      let content = document.getElementById('timetable-content');
      modal.classList.add('is-active');
      content.innerHTML = "<div class='has-text-centered' style='padding:40px;'><i class='fas fa-circle-notch fa-spin fa-2x' style='color:#38bdf8; margin-bottom: 15px;'></i><p style='color:#38bdf8; font-weight:bold;'>Stahuji Jízdní řád z Inflow...</p></div>";
      try {
        let response = await fetch('/api/bus_detail/' + busId);
        content.innerHTML = await response.text();
      } catch(e) { content.innerHTML = "<p style='color:#ef4444;padding:20px;text-align:center;'>Chyba spojení.</p>"; }
    }
    window.toggleFollow = function(busId) {
      if (followedBusId === busId) { followedBusId = null; }
      else {
        followedBusId = busId;
        let bus = lastDataArray.find(b => b.id === busId);
        if (bus) map.setView([bus.lat, bus.lng], 16);
      }
    }
    async function fetchBuses() {
      try {
        let response = await fetch('/api/live_buses');
        let data = await response.json();
        if (data.server_time) document.getElementById('systemTimeClock').innerText = data.server_time;
        if (data.status === "success") {
          lastDataArray = data.buses;
          markersLayer.clearLayers();
          data.buses.forEach(bus => {
            if (!bus.lat || !bus.lng) return;
            if (followedBusId === bus.id) map.setView([bus.lat, bus.lng]);
            let markerColor = bus.color_class;
            let delayText = "";
            let delayVal = parseInt(bus.delay);
            if (markerColor === "bg-gray") {
              if (bus.status.includes(">4h")) {
                let aheadMin = Math.abs(delayVal), aheadH = Math.floor(aheadMin / 60), aheadM = aheadMin % 60;
                delayText = `<span style="color:#94a3b8;">Odjezd za ${aheadH}h ${aheadM}m</span>`;
              } else delayText = `<span style="color:#94a3b8;">N/A</span>`;
            } else if (markerColor === "bg-purple") {
              delayText = `<span style="color:#a855f7;">Konečná zastávka</span>`;
            } else if (markerColor === "bg-blue") {
              let aheadMin = Math.abs(delayVal), aheadH = Math.floor(aheadMin / 60), aheadM = aheadMin % 60;
              delayText = `<span style="color:#3b82f6;">Odjezd za ${aheadH > 0 ? aheadH + 'h ' : ''}${aheadM} min</span>`;
            } else if (markerColor === "bg-darkblue") {
              delayText = `<span style="color:#60a5fa;">Náskok ${Math.abs(delayVal)} min</span>`;
            } else if (delayVal >= 5) {
              delayText = `<span style="color:#ef4444;">Zpoždění ${delayVal} min</span>`;
            } else {
              delayText = `<span style="color:#10b981;">+${delayVal} min</span>`;
            }
            let shape = bus.is_train ? 'train-marker' : 'bus-marker';
            let icon = L.divIcon({ className: shape + ' ' + markerColor, iconSize: [24, 24] });
            let marker = L.marker([bus.lat, bus.lng], {icon: icon});
            let spzHtml = "", historyBtn = "", investigateText = "";
            if (!bus.is_train) {
              if (bus.investigating) {
                spzHtml = `<div class="popup-row"><span class="popup-label">SPZ:</span><span class="popup-value badge-spz" style="background:#ef4444; color:white; border-color:#b91c1c;"><i class="fas fa-search"></i> Výzkum duplikace</span></div>`;
                investigateText = `<div style="color:#ef4444; font-size:11px; margin-top:5px; font-weight:bold;"><i class="fas fa-exclamation-circle"></i> Probíhá zjišťování správné SPZ (${bus.investigation_spz})</div>`;
              } else if (bus.spz && bus.spz !== 'Neznámá') {
                let badgeIcon = bus.spz_verified ? '<i class="fas fa-check-circle" style="color:#0f172a;margin-left:3px;" title="Ověřeno"></i>' : '<i class="fas fa-question-circle" style="color:white;margin-left:3px;" title="Odhad (drží se)"></i>';
                let spzStyle = bus.spz_verified ? 'badge-spz' : 'badge-spz" style="background:#f97316; color:white; border-color:#c2410c;';
                let spzDisplay = bus.spz_verified ? bus.spz : `${bus.spz} ⏳`;
                spzHtml = `<div class="popup-row"><span class="popup-label">SPZ:</span><span class="popup-value ${spzStyle}">${spzDisplay} ${badgeIcon}</span></div>`;
                if (bus.spz_verified) {
                  historyBtn = `<a href="/historie/${bus.spz}" target="_blank" class="btn-timetable" style="background:#f59e0b; margin-top:5px;"><i class="fas fa-history"></i> Historie vozu</a>`;
                }
              } else {
                spzHtml = `<div class="popup-row"><span class="popup-label">SPZ:</span><span class="popup-value" style="color:#94a3b8;">Čeká na ověření...</span></div>`;
              }
            }
            let statusColor = "#10b981";
            if (bus.status.includes("Stojí") || bus.status.includes("Odstaven")) statusColor = "#ef4444";
            else if (bus.status.includes("Koneč") || bus.status.includes("Ztráta")) statusColor = "#a855f7";
            else if (bus.status.includes("Začátek") || bus.status.includes("Čeká")) statusColor = "#3b82f6";
            else if (bus.status.includes("N/A") || bus.status.includes("signál") || bus.status.includes("Zmizel") || bus.status.includes("Výzkum")) statusColor = "#94a3b8";
            else if (bus.status.includes("Náskok") || bus.status.includes("Vyčkává")) statusColor = "#60a5fa";
            else if (bus.status.includes("Timeout") || bus.status.includes("Falešný")) statusColor = "#ef4444";
            let followText = (followedBusId === bus.id) ? '<i class="fas fa-stop-circle"></i> Zrušit sledování' : '<i class="fas fa-crosshairs"></i> Sledovat kamerou';
            let followStyle = (followedBusId === bus.id) ? 'background:#ef4444; color:white;' : 'background:#3b82f6; color:white;';
            let popupHTML = `
              <div class="popup-header"><h3 class="popup-header-title"><i class="${bus.is_train ? 'fas fa-train' : 'fas fa-bus'}"></i> Linka ${bus.line}</h3></div>
              <div class="popup-body">
                <div class="popup-row"><span class="popup-label">Cíl:</span><span class="popup-value" style="color:white;">${bus.destination || "Neznámý"}</span></div>
                ${spzHtml}${investigateText}
                <div class="popup-row"><span class="popup-label">Status:</span><span class="popup-value" style="color:${statusColor};">${bus.status}</span></div>
                <div class="popup-row"><span class="popup-label">Trip ID:</span><span class="popup-value" style="color:#94a3b8; font-size:11px;">${bus.trip_id}</span></div>
                <div class="popup-row" style="border:none; margin-top:5px;"><span class="popup-label">JŘ:</span><span class="popup-value">${delayText}</span></div>
                <button class="btn-timetable" onclick="showTimetable('${bus.id}')"><i class="fas fa-list-alt"></i> Zobrazit Jízdní řád</button>
                <button onclick="toggleFollow('${bus.id}')" class="btn-timetable" style="${followStyle} margin-top:5px;">${followText}</button>
                ${historyBtn}
              </div>`;
            marker.bindPopup(popupHTML, {className: 'dark-popup'});
            markersLayer.addLayer(marker);
          });
        }
      } catch(e) { console.error(e); }
    }
    fetchBuses();
    setInterval(fetchBuses, 10000);
  </script>
</div>
"""

# --- GLOBÁLNÍ STAV ---
GLOBAL_BUS_CACHE = {}   # bus_id -> dict s daty autobusu
LIVE_BUSES_DATA  = []   # Seznam pro frontend
TRACKED_SPZS     = set()

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
    global TRACKED_SPZS
    print("[MAPA] Worker startuje (vylepšená SPZ logika v2)...", flush=True)

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
            # SEKCE 3: Detekce duplikátních SPZ s grace periodou
            # ═══════════════════════════════════════════════════════
            spz_tracker = {}
            for bid, bc in GLOBAL_BUS_CACHE.items():
                spz_val = bc.get("spz")
                if spz_val and spz_val != "Neznámá" and not bc.get("is_offline"):
                    spz_tracker.setdefault(spz_val, []).append(bid)

            for spz_val, bus_ids in spz_tracker.items():
                if len(bus_ids) <= 1:
                    # Jen 1 bus – výzkum zrušen
                    GLOBAL_BUS_CACHE[bus_ids[0]]["investigating"]     = False
                    GLOBAL_BUS_CACHE[bus_ids[0]]["investigation_start"] = None
                    continue

                # Více busů se stejnou SPZ – najdeme "vítěze"
                # Kritéria: nejvíce stable_ticks, pak nejnovější spz_last_verified
                def score_candidate(bid):
                    bc = GLOBAL_BUS_CACHE[bid]
                    ticks   = bc.get("spz_stable_ticks", 0)
                    last_v  = bc.get("spz_last_verified") or datetime.min
                    return (ticks, last_v)

                best_bid = max(bus_ids, key=score_candidate)

                for bid in bus_ids:
                    bc = GLOBAL_BUS_CACHE[bid]
                    if bid == best_bid:
                        # Vítěz – zrušíme výzkum
                        bc["investigating"]      = False
                        bc["investigation_start"] = None
                    else:
                        # Poražený – grace perioda, pak smazání SPZ
                        bc["spz_verified"]   = False
                        bc["spz_locked"]     = False
                        bc["investigating"]  = True
                        bc["investigation_spz"] = spz_val
                        if bc.get("investigation_start") is None:
                            bc["investigation_start"] = now
                        elif (now - bc["investigation_start"]).total_seconds() > DUPLICATE_GRACE_SEC:
                            bc["spz"]                 = None
                            bc["investigating"]        = False
                            bc["investigation_start"]  = None
                            bc["spz_stable_ticks"]     = 0

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
                        if diff > 0 or (diff > -10 and not c.get("actual_start_time")
                                        and not is_moving and delay_val > -100):
                            is_before_departure = True
                            time_to_dep = max(diff, 0)
                    except Exception:
                        pass

                old_status = c["status"]

                if is_before_departure:
                    c["actual_end_time"] = None
                    if time_to_dep <= 240:
                        c["status"]      = "Začátek linky (Čeká)"
                        c["color_class"] = "bg-blue"
                        delay_val        = -time_to_dep
                    else:
                        c["status"]      = "Čeká na spoj (>4h)"
                        c["color_class"] = "bg-gray"
                        delay_val        = -time_to_dep

                else:
                    if delay_val <= -10000:
                        if inactive_mins > 10:
                            c["status"]      = "Odstaven"
                            c["color_class"] = "bg-gray"
                        else:
                            c["status"]      = "Konečná zastávka"
                            c["color_class"] = "bg-purple"
                            if not c["actual_end_time"]:
                                c["actual_end_time"] = now.strftime('%H:%M')
                    else:
                        if delay_val < -1:
                            if c.get("actual_start_time"):
                                c["status"]      = "Jízda (Náskok)" if is_moving else "Stojí (Náskok)"
                                c["color_class"] = "bg-darkblue"
                            else:
                                c["status"]      = "Začátek linky (Čeká)"
                                c["color_class"] = "bg-blue"
                        else:
                            c["status"]      = "Jízda" if is_moving else "Stojí"
                            c["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"

                if is_moving and not c["actual_start_time"] and not is_train:
                    c["actual_start_time"] = now.strftime('%H:%M')

                c["final_delay_display"] = delay_val

                # ── DB UPSERT (jen ověřené SPZ) ───────────────────────────
                if c.get("spz_verified") and (old_status != c["status"] or is_moving or not c.get("db_first_upsert")):
                    upsert_to_history(db_client, c)
                    c["db_first_upsert"] = True

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

def _full_page(title, body_html):
    """Obalí HTML do kompletní stránky."""
    return Response(
        f"""<!DOCTYPE html>
<html style="background:#0f172a;">
<head>
  <title>{title} | OIS IDPK</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="background:#0f172a; color:white;">
{body_html}
</body>
</html>""",
        mimetype='text/html'
    )


@mapa_bp.route('/mapa')
def stranka_mapa():
    return _full_page("Mapa", HTML_MAPA)


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
    return jsonify({
        "status":      "success",
        "server_time": now.strftime('%H:%M:%S'),
        "buses":       LIVE_BUSES_DATA,
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
