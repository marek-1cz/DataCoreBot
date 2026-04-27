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

# Globální proměnná pro start systému
SYSTEM_START_TIME = datetime.now()

def is_system_starting():
    return (datetime.now() - SYSTEM_START_TIME).total_seconds() < 45

HTML_HISTORIE_INDEX = """
<div style="padding: 20px; max-width: 1400px; margin: auto; font-family: sans-serif;">
    <div id="startupBanner" style="display:none; background: #ef4444; color: white; padding: 15px; text-align: center; font-weight: bold; border-radius: 8px; margin-bottom: 20px; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.5);">
        <i class="fas fa-exclamation-triangle"></i> PROBÍHÁ RESTART SYSTÉMU A POSTUPNÉ NAČÍTÁNÍ DAT...
    </div>

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 24px;"><i class="fas fa-database"></i> Databáze Vozů</h2>
        <div class="field" style="margin-bottom: 0;">
          <p class="control has-icons-left">
            <input class="input" id="historySearch" type="text" placeholder="Hledat linku nebo SPZ..." style="background: #1e293b; color: white; border-color: #334155; min-width: 350px;">
            <span class="icon is-small is-left" style="color: #94a3b8;"><i class="fas fa-search"></i></span>
          </p>
        </div>
    </div>

    <h3 style="color: #10b981; margin-bottom: 10px;"><i class="fas fa-check-circle"></i> Přiřazené vozy</h3>
    <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 30px;">
        <table class="table is-fullwidth is-hoverable" style="background: transparent; color: #cbd5e1; margin-bottom: 0; min-width: 1000px;" id="tableAssigned">
            <thead>
                <tr style="background: #0f172a;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední aktivita</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">SPZ Vozu</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední známá Linka</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední Status</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Akce</th>
                </tr>
            </thead>
            <tbody id="historyTableBodyAssigned">
                <tr><td colspan="5" style="text-align:center; padding: 30px; color: #38bdf8;"><i class="fas fa-spinner fa-spin"></i> Stahuji historii...</td></tr>
            </tbody>
        </table>
    </div>

    <h3 style="color: #ef4444; margin-bottom: 10px;"><i class="fas fa-question-circle"></i> Nezařazeno (Čeká na spárování SPZ)</h3>
    <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <table class="table is-fullwidth is-hoverable" style="background: transparent; color: #cbd5e1; margin-bottom: 0; min-width: 1000px;" id="tableUnassigned">
            <thead>
                <tr style="background: #0f172a;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Čas startu / pohybu</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka (JŘ)</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Status</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Poloha</th>
                </tr>
            </thead>
            <tbody id="historyTableBodyUnassigned">
            </tbody>
        </table>
    </div>

    <script>
        async function loadIndex() {
            try {
                const response = await fetch('/api/history_full');
                const result = await response.json();
                const data = result.data;
                
                if (result.system_starting) {
                    document.getElementById('startupBanner').style.display = 'block';
                } else {
                    document.getElementById('startupBanner').style.display = 'none';
                }

                const tbodyAssigned = document.getElementById('historyTableBodyAssigned');
                const tbodyUnassigned = document.getElementById('historyTableBodyUnassigned');
                tbodyAssigned.innerHTML = '';
                tbodyUnassigned.innerHTML = '';

                if (data.length === 0) {
                    tbodyAssigned.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Zatím žádné záznamy.</td></tr>';
                    return;
                }

                const uniqueBuses = {};
                const uniqueUnassigned = {};

                data.forEach(row => {
                    if (row.spz && row.spz !== 'Neznámá') {
                        if (!uniqueBuses[row.spz]) uniqueBuses[row.spz] = row;
                    } else {
                        if (!uniqueUnassigned[row.trip_id]) uniqueUnassigned[row.trip_id] = row;
                    }
                });

                Object.values(uniqueBuses).forEach(row => {
                    const createdDate = new Date(row.created_at);
                    const dayStr = createdDate.toLocaleDateString('cs-CZ') + ' ' + createdDate.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                    
                    let spzBadge = `<span class="tag is-warning" style="background:#f59e0b; color:#0f172a; font-weight:bold; font-size:14px;">${row.spz}</span>`;
                    if (!row.spz_verified) spzBadge += ` <i class="fas fa-exclamation-triangle" style="color:#ef4444;" title="Neověřeno"></i>`;

                    let statusColor = row.end_actual ? "#ef4444" : "#eab308";
                    let statusHtml = `<span style="color:${statusColor};">${row.status}</span>`;

                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.setAttribute('data-spz', row.spz);
                    tr.setAttribute('data-linka', row.linka);
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${dayStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${spzBadge}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${row.linka}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${statusHtml}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="/historie/${row.spz}" class="button is-small is-primary">
                                <i class="fas fa-folder-open" style="margin-right: 5px;"></i> Detail vozu
                            </a>
                        </td>
                    `;
                    tbodyAssigned.appendChild(tr);
                });

                let unassignedCount = 0;
                Object.values(uniqueUnassigned).forEach(row => {
                    // Skryjeme staré timeoutlé nezařazené
                    if (row.status.includes("Timeout") || row.end_actual) return;
                    unassignedCount++;
                    
                    const createdDate = new Date(row.created_at);
                    const dayStr = createdDate.toLocaleDateString('cs-CZ') + ' ' + createdDate.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                    
                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${dayStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${row.linka}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color:#eab308;">${row.status}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="/mapa#${row.last_lat},${row.last_lng}" target="_blank" class="button is-small is-outlined" style="background:transparent; color:#cbd5e1; border-color:#4b5563;">
                                <i class="fas fa-map-marker-alt"></i>
                            </a>
                        </td>
                    `;
                    tbodyUnassigned.appendChild(tr);
                });

                if (unassignedCount === 0) {
                    tbodyUnassigned.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px; color:#94a3b8;">Všechny aktivní spoje jsou úspěšně spárovány s SPZ.</td></tr>';
                }

            } catch(e) { 
                document.getElementById('historyTableBodyAssigned').innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color:#ef4444;">Chyba připojení.</td></tr>';
            }
        }

        document.getElementById('historySearch').addEventListener('input', function(e) {
            const val = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#tableAssigned tbody tr');
            rows.forEach(row => {
                if(!row.hasAttribute('data-spz')) return;
                const spz = row.getAttribute('data-spz').toLowerCase();
                const linka = row.getAttribute('data-linka').toLowerCase();
                row.style.display = (spz.includes(val) || linka.includes(val)) ? '' : 'none';
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
    
    <div id="startupBanner" style="display:none; background: #ef4444; color: white; padding: 15px; text-align: center; font-weight: bold; border-radius: 8px; margin-bottom: 20px; font-size: 18px;">
        <i class="fas fa-exclamation-triangle"></i> PROBÍHÁ RESTART SYSTÉMU...
    </div>

    <div style="background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #38bdf8; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
        <h2 style="color: white; margin: 0 0 10px 0; font-size: 28px;">Autobus SPZ: <span style="color:#f59e0b;">{{SPZ}}</span></h2>
        <div id="absoluteLastPos"></div>
    </div>

    <h3 style="color: #38bdf8; margin-bottom: 15px; font-size: 20px;"><i class="fas fa-route"></i> Všechny odjeté spoje (Data z Trip ID)</h3>
    <div style="background: #0f172a; border-radius: 10px; border: 1px solid #334155; overflow-x: auto;">
        <table class="table is-fullwidth" style="background: transparent; color: #cbd5e1; margin-bottom: 0;">
            <thead>
                <tr style="background: #1e293b;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Datum</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka / Spoj</th>
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
        async function loadDetail() {
            try {
                const response = await fetch('/api/history_spz/{{SPZ}}');
                const result = await response.json();
                const data = result.data;

                if (result.system_starting) {
                    document.getElementById('startupBanner').style.display = 'block';
                } else {
                    document.getElementById('startupBanner').style.display = 'none';
                }
                
                const liveRes = await fetch('/api/live_buses');
                const liveData = await liveRes.json();
                const liveBus = liveData.buses ? liveData.buses.find(b => b.spz === '{{SPZ}}') : null;

                const tbody = document.getElementById('detailTableBody');
                const lastPosDiv = document.getElementById('absoluteLastPos');
                tbody.innerHTML = '';

                if (data.length === 0 && !liveBus) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Žádná historie.</td></tr>';
                    lastPosDiv.innerHTML = '<span style="color:#ef4444;">Poloha neznámá</span>';
                    return;
                }

                let currentLat = 0, currentLng = 0, topStatus = "", topTime = "", liveIndicator = "";

                if (liveBus && liveBus.lat) {
                    currentLat = liveBus.lat; currentLng = liveBus.lng;
                    topStatus = `${liveBus.status} (${liveBus.line || 'Bez linky'})`;
                    topTime = "Nyní (Živá data z mapy)";
                    liveIndicator = `<br><span style="color:#10b981; font-weight:bold; font-size:13px;"><i class="fas fa-satellite-dish"></i> Živě</span>`;
                } else if (data.length > 0) {
                    const newest = data[0];
                    currentLat = newest.last_lat; currentLng = newest.last_lng;
                    topStatus = `${newest.status} (${newest.linka || 'Bez linky'})`;
                    const nd = new Date(newest.updated_at || newest.created_at);
                    topTime = `${nd.toLocaleDateString('cs-CZ')} ${nd.toLocaleTimeString('cs-CZ')}`;
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
                    </div>
                `;

                data.forEach(trip => {
                    const cd = new Date(trip.created_at);
                    const dayStr = cd.toLocaleDateString('cs-CZ');
                    
                    let startStr = trip.start_actual ? trip.start_actual : (trip.start_scheduled ? `<span style="color:#94a3b8;">${trip.start_scheduled} (Plán)</span>` : "---");
                    
                    let endStr = "";
                    if (trip.end_actual) {
                        endStr = `${trip.end_actual} <br><span style="font-size:11px; color:#94a3b8;">(${trip.status})</span>`;
                    } else {
                        endStr = `<span style="color:#eab308; font-weight:bold;"><i class="fas fa-spinner fa-pulse"></i> Probíhá...</span><br><span style="font-size:11px; color:#94a3b8;">${trip.status}</span>`;
                    }
                    
                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color:#cbd5e1;">${dayStr}<br><span style="font-size:10px; color:#64748b;">${trip.trip_id.substring(0,8)}</span></td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">
                            ${trip.linka}
                            ${trip.jr_link ? `<br><a href="${trip.jr_link}" target="_blank" style="font-size:11px; color:#38bdf8;">Jízdní řád <i class="fas fa-external-link-alt"></i></a>` : ''}
                        </td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #10b981;">${startStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #ef4444;">${endStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="/mapa#${trip.last_lat},${trip.last_lng}" class="button is-small is-outlined" style="background: transparent; color: #cbd5e1; border-color: #4b5563;">
                                <i class="fas fa-map-marker-alt"></i>
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
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
<div style="padding: 20px; position: relative;">
    <h2 style="color: var(--blue-main); margin-bottom: 20px;"><i class="fas fa-map-marked-alt"></i> Interaktivní Mapa Spojů</h2>
    
    <div id="startupBanner" style="display:none; background: #ef4444; color: white; padding: 15px; text-align: center; font-weight: bold; border-radius: 8px; margin-bottom: 20px; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.5);">
        <i class="fas fa-exclamation-triangle"></i> PROBÍHÁ RESTART SYSTÉMU A POSTUPNÉ NAČÍTÁNÍ DAT...
    </div>

    <div style="position: absolute; top: 20px; right: 20px; z-index: 1000; background: rgba(15, 23, 42, 0.9); color: #38bdf8; padding: 10px 15px; border-radius: 8px; border: 1px solid #38bdf8; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 8px;">
        <i class="far fa-clock"></i> <span id="systemTimeClock" style="font-size: 18px;">--:--:--</span>
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
        .bg-darkblue { background-color: #1e3a8a; } .bg-gray { background-color: #64748b; border-color: #475569; color: #cbd5e1;} 
        .bg-purple { background-color: #a855f7; } .bg-yellow { background-color: #eab308; color: #1e293b; }
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
        .badge-spz { background: #f59e0b; color: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 12px; border: 1px solid #d97706;}
        .btn-timetable { background: #38bdf8; color: #0f172a; border: none; padding: 10px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; margin-top: 10px; display: block; text-align: center; }
        .btn-timetable:hover { background: #0284c7; color: white; }
    </style>

    <script>
        var defaultLat = 49.7384;
        var defaultLng = 13.3736;
        var defaultZoom = 12;

        if(window.location.hash) {
            var hashParts = window.location.hash.replace('#', '').split(',');
            if(hashParts.length === 2) {
                defaultLat = parseFloat(hashParts[0]);
                defaultLng = parseFloat(hashParts[1]);
                defaultZoom = 17; 
            }
        }

        var map = L.map('map').setView([defaultLat, defaultLng], defaultZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        var markersLayer = L.layerGroup().addTo(map);

        if(window.location.hash && hashParts.length === 2) {
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

        async function fetchBuses() {
            try {
                let response = await fetch('/api/live_buses');
                let data = await response.json();
                
                if(data.server_time) {
                    document.getElementById('systemTimeClock').innerText = data.server_time;
                }
                if (data.system_starting) {
                    document.getElementById('startupBanner').style.display = 'block';
                } else {
                    document.getElementById('startupBanner').style.display = 'none';
                }

                if(data.status === "success") {
                    markersLayer.clearLayers();
                    data.buses.forEach(bus => {
                        if(bus.lat && bus.lng) {
                            let markerColor = bus.color_class; 
                            let delayText = ""; let delayVal = parseInt(bus.delay); 

                            if (markerColor === "bg-gray") {
                                if (bus.status.includes(">4h")) {
                                    let aheadMin = Math.abs(delayVal);
                                    let aheadH = Math.floor(aheadMin / 60); let aheadM = aheadMin % 60;
                                    delayText = `<span style="color:#94a3b8;">Odjezd za ${aheadH}h ${aheadM}m</span>`;
                                } else delayText = `<span style="color:#94a3b8;">N/A</span>`;
                            } else if (markerColor === "bg-yellow") {
                                delayText = `<span style="color:#eab308;">Mimo linku / Po JŘ</span>`;
                            } else if (markerColor === "bg-purple") {
                                delayText = `<span style="color:#a855f7;">Konečná zastávka</span>`;
                            } else if (markerColor === "bg-blue") {
                                let aheadMin = Math.abs(delayVal);
                                let aheadH = Math.floor(aheadMin / 60); let aheadM = aheadMin % 60;
                                let timeStr = aheadH > 0 ? `${aheadH}h ${aheadM}min` : `${aheadM} min`;
                                delayText = `<span style="color:#3b82f6;">Odjezd za ${timeStr}</span>`;
                            } else if (markerColor === "bg-darkblue") {
                                let aheadMin = Math.abs(delayVal);
                                delayText = `<span style="color:#60a5fa;">Náskok ${aheadMin} min</span>`; 
                            } else if (delayVal >= 5) {
                                delayText = `<span style="color:#ef4444;">Zpoždění ${delayVal} min</span>`;
                            } else {
                                delayText = `<span style="color:#10b981;">+${delayVal} min</span>`;
                            }

                            let shape = bus.is_train ? 'train-marker' : 'bus-marker';
                            let icon = L.divIcon({ className: shape + ' ' + markerColor, iconSize: [24, 24] });
                            let marker = L.marker([bus.lat, bus.lng], {icon: icon});
                            
                            let spzHtml = "";
                            if (!bus.is_train) {
                                let badgeIcon = bus.spz_verified ? '<i class="fas fa-check-circle" style="color:#0f172a;margin-left:3px;" title="Ověřeno"></i>' : '<i class="fas fa-times-circle" style="color:white;margin-left:3px;" title="Neověřeno"></i>';
                                let spzClass = bus.spz_verified ? 'badge-spz' : 'badge-spz" style="background:#ef4444; color:white; border-color:#b91c1c;';
                                spzHtml = `<div class="popup-row"><span class="popup-label">SPZ:</span><span class="popup-value ${spzClass}">${bus.spz || 'Neznámá'} ${bus.spz !== 'Neznámá' ? badgeIcon : ''}</span></div>`;
                            }
                            
                            let statusColor = "#10b981"; 
                            if (bus.status.includes("Stojí")) statusColor = "#ef4444"; 
                            else if (bus.status.includes("Koneč")) statusColor = "#a855f7"; 
                            else if (bus.status.includes("Začátek") || bus.status.includes("Čeká")) statusColor = "#3b82f6"; 
                            else if (bus.status.includes("Odstaven") || bus.status.includes("N/A") || bus.status.includes("signál") || bus.status.includes("Zmizel")) statusColor = "#94a3b8"; 
                            else if (bus.status.includes("Manipulační")) statusColor = "#eab308"; 
                            else if (bus.status.includes("Náskok") || bus.status.includes("Vyčkává")) statusColor = "#60a5fa"; 
                            else if (bus.status.includes("Timeout")) statusColor = "#ef4444"; 
                            
                            let statusHtml = `<div class="popup-row"><span class="popup-label">Status:</span><span class="popup-value" style="color:${statusColor};">${bus.status}</span></div>`;
                            let idHtml = `<div class="popup-row"><span class="popup-label">Trip ID:</span><span class="popup-value" style="color:#94a3b8; font-size:11px;">${bus.trip_id}</span></div>`;
                            
                            let popupHTML = `
                                <div class="popup-header">
                                    <h3 class="popup-header-title"><i class="${bus.is_train ? 'fas fa-train' : 'fas fa-bus'}"></i> Linka ${bus.line}</h3>
                                </div>
                                <div class="popup-body">
                                    <div class="popup-row"><span class="popup-label">Cíl:</span><span class="popup-value" style="color:white;">${bus.destination || "Neznámý"}</span></div>
                                    ${spzHtml}
                                    ${statusHtml}
                                    ${idHtml}
                                    <div class="popup-row" style="border:none; margin-top:5px;"><span class="popup-label">JŘ:</span><span class="popup-value">${delayText}</span></div>
                                    
                                    <button class="btn-timetable" onclick="showTimetable('${bus.id}')">
                                        <i class="fas fa-list-alt"></i> Zobrazit Jízdní řád
                                    </button>
                                </div>
                            `;
                            
                            marker.bindPopup(popupHTML, {className: 'dark-popup'});
                            markersLayer.addLayer(marker);
                        }
                    });
                }
            } catch(e) { console.error(e); }
        }
        
        fetchBuses();
        setInterval(fetchBuses, 10000);
    </script>
</div>
"""

GLOBAL_BUS_CACHE = {}
LIVE_BUSES_DATA = []

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get_db_client():
    if not HAS_SUPABASE: return None
    supa_url = os.environ.get("SUPABASE_URL")
    supa_key = os.environ.get("SUPABASE_KEY")
    if supa_url and supa_key:
        try: return create_client(supa_url, supa_key)
        except: return None
    return None

def fetch_tt_bg(bus_id, cached_dict):
    try:
        cb_time = int(time.time() * 1000)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://pvvd.idpk.cz/',
            'Cache-Control': 'no-cache'
        }
        
        info_url = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb_time}"
        req_info = urllib.request.Request(info_url, headers=headers)
        with opener.open(req_info, timeout=4) as r_info:
            info_html = r_info.read().decode('utf-8')
            m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
            m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
            linka_txt = m_linka.group(1).strip() if m_linka else ""
            spoj_txt = m_spoj.group(1).strip() if m_spoj else ""
            if linka_txt and spoj_txt:
                cached_dict["real_linka_spoj"] = f"{linka_txt}/{spoj_txt}"

        tt_url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}"
        req_tt = urllib.request.Request(tt_url, headers=headers)
        with opener.open(req_tt, timeout=4) as r_tt:
            tt_html = r_tt.read().decode('utf-8')
            times = re.findall(r'\b\d{2}:\d{2}\b', tt_html)
            if times:
                cached_dict["first_dep_time"] = times[0]
                cached_dict["last_dep_time"] = times[-1] 
    except Exception: pass
    finally: cached_dict["tt_is_fetching"] = False

def upsert_to_history(db, c):
    if c.get("is_train"): return
    if not db: return
    
    try:
        final_linka = c.get("real_linka_spoj") or c.get("line", "Neznámá")
        jr_l = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={c['inflow_id']}&currentStopId=0"
        
        data = {
            "trip_id": c["trip_id"],
            "spz": c.get("spz"),
            "spz_verified": c.get("spz_verified", False),
            "linka": final_linka,
            "jr_link": jr_l,
            "start_scheduled": c.get("first_dep_time"),
            "start_actual": c.get("actual_start_time"),
            "end_actual": c.get("actual_end_time"),
            "last_lat": c.get("lat"),
            "last_lng": c.get("lng"),
            "status": c.get("status"),
            "created_at": c["created_at"].isoformat(),
            "updated_at": datetime.now(ZoneInfo('Europe/Prague')).isoformat()
        }
        db.table("bus_history").upsert(data).execute()
    except Exception: pass

def background_map_worker():
    print("[MAPA] Inteligentní mozek v2 (Striktní JŘ, Trip ID, Anti-Spz-Theft, Oznámení restartu) startuje...", flush=True)
    url_inflow_base = "https://pvvd.idpk.cz/Ajax/GetPoints" 
    url_arriva = "https://www.arriva.cz/api/graphql" 
    
    inflow_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://pvvd.idpk.cz/',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    try: opener.open(urllib.request.Request("https://pvvd.idpk.cz/", headers={'User-Agent': 'Mozilla/5.0'}))
    except: pass

    db_client = get_db_client()
    last_db_cleanup = datetime.now(ZoneInfo('Europe/Prague'))
    TRIP_COUNTER = int(time.time()) 

    while True:
        now = datetime.now(ZoneInfo('Europe/Prague'))
        
        if db_client and (now - last_db_cleanup).total_seconds() > 86400:
            try:
                thirty_days_ago = (now - timedelta(days=30)).isoformat()
                db_client.table("bus_history").delete().lt("created_at", thirty_days_ago).execute()
            except Exception: pass
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
            except Exception: pass

        try:
            arriva_payload = {
                "operationName": "busesCurrentLocation",
                "variables": {},
                "query": "query busesCurrentLocation {\n  busesCurrentLocations {\n    angle\n    delay\n    destinationName\n    lastStopName\n    latitude\n    longitude\n    linkNumber\n    state\n    type\n    mainType\n    spz\n    updated\n    linkNumberAlias\n    __typename\n  }\n}"
            }
            req2 = urllib.request.Request(url_arriva, data=json.dumps(arriva_payload).encode('utf-8'),
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/'
                }, method='POST')
            with urllib.request.urlopen(req2, timeout=5) as r2:
                resp2 = json.loads(r2.read().decode())
                if isinstance(resp2, list) and len(resp2) > 0:
                    data_arriva = resp2[0].get("data", {}).get("busesCurrentLocations", [])
                elif isinstance(resp2, dict):
                    data_arriva = resp2.get("data", {}).get("busesCurrentLocations", [])
        except Exception: pass

        current_inflow_ids = set()

        if isinstance(data_inflow, list):
            for bus1 in data_inflow:
                try:
                    bus_id = str(bus1.get("id", "0"))
                    current_inflow_ids.add(bus_id)
                    
                    line = str(bus1.get("text", "")).strip()
                    lat1 = bus1.get("lat", 0)
                    lng1 = bus1.get("lng", 0)
                    delay = int(bus1.get("delay", 0)) if bus1.get("delay") is not None else 0
                    dest1_original = str(bus1.get("finalStopName", "")).strip()
                    traction = str(bus1.get("traction", "BUS")).upper()
                    is_train = int(bus_id) < 0 or traction in ["TRAIN", "UNKNOWN"]

                    if bus_id not in GLOBAL_BUS_CACHE:
                        TRIP_COUNTER += 1
                        GLOBAL_BUS_CACHE[bus_id] = {
                            "trip_id": f"TRIP-{TRIP_COUNTER}",
                            "inflow_id": bus_id,
                            "lat": lat1, "lng": lng1, "line": line, "real_linka_spoj": None,
                            "spz": None, "spz_verified": False,
                            "spz_locked": False, "estimated": False,
                            "last_moved": now, "first_seen": now, "last_inflow_seen": now,
                            "status": "Načítání...", "color_class": "bg-gray", "destination": dest1_original, 
                            "is_train": is_train, "raw_delay": delay, 
                            "first_dep_time": None, "last_dep_time": None, "tt_last_fetch": None,
                            "tt_is_fetching": False, "is_offline": False,
                            "actual_start_time": None, "actual_end_time": None,
                            "created_at": now
                        }
                        upsert_to_history(db_client, GLOBAL_BUS_CACHE[bus_id])
                    else:
                        c = GLOBAL_BUS_CACHE[bus_id]
                        c["last_inflow_seen"] = now
                        c["is_offline"] = False
                        c["raw_delay"] = delay
                        c["is_train"] = is_train
                        
                        dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])
                        
                        if c["line"] != line:
                            if c["line"] != "Neznámá" and not c["actual_end_time"]:
                                c["actual_end_time"] = now.strftime('%H:%M')
                                c["status"] = "Ukončeno začátkem druhé linky"
                                upsert_to_history(db_client, c)

                            TRIP_COUNTER += 1
                            c["trip_id"] = f"TRIP-{TRIP_COUNTER}"
                            c["line"] = line
                            c["real_linka_spoj"] = None
                            c["destination"] = dest1_original
                            c["first_dep_time"] = None 
                            c["last_dep_time"] = None
                            c["actual_start_time"] = None
                            c["actual_end_time"] = None
                            c["created_at"] = now
                            c["status"] = "Načítání..."
                            upsert_to_history(db_client, c)
                            
                            if dist_moved < 0.005: 
                                c["last_moved"] = now
                        elif c["destination"] != dest1_original:
                            c["destination"] = dest1_original
                        
                        if dist_moved > 0.0001:
                            c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                except: continue

        for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
            offline_mins = (now - c["last_inflow_seen"]).total_seconds() / 60.0
            total_mins = (now - c["first_seen"]).total_seconds() / 60.0
            
            if total_mins > 300 and not c["actual_end_time"]:
                c["actual_end_time"] = now.strftime('%H:%M')
                c["status"] = "Timeout (300m+ probíhá)"
                c["color_class"] = "bg-gray"
                upsert_to_history(db_client, c)
                del GLOBAL_BUS_CACHE[bus_id]
                continue

            if bus_id not in current_inflow_ids:
                if offline_mins > 720: 
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                
                c["is_offline"] = True
                if not c["actual_end_time"]:
                    c["actual_end_time"] = now.strftime('%H:%M')
                    c["status"] = "Konečná / Zmizel z mapy"
                    c["color_class"] = "bg-purple"
                    upsert_to_history(db_client, c)
                elif offline_mins > 20:
                    c["status"] = "Odstaven (Bez signálu)"
                    c["color_class"] = "bg-gray"
                    upsert_to_history(db_client, c)

        new_live_data = []
        tt_fetches_this_tick = 0 

        for bus_id, c in list(GLOBAL_BUS_CACHE.items()):
            if c.get("is_offline"):
                continue 

            lat1, lng1 = c["lat"], c["lng"]
            line, dest1_original = c["line"], c["destination"]
            is_train = c["is_train"]
            
            inactive_mins = (now - c["last_moved"]).total_seconds() / 60.0
            is_moving = inactive_mins < 1 
            delay_val = c["raw_delay"]

            if not is_train:
                buses_on_line = [b for b in data_arriva if str(b.get("linkNumber","")).strip() == line]
                close_buses = [b for b in buses_on_line if math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0)) < 0.015]
                
                best_spz = None
                if len(close_buses) == 1:
                    best_spz = close_buses[0].get("spz", "").strip()

                if best_spz and best_spz != "Neznámá":
                    c["spz"] = best_spz
                    c["spz_verified"] = True
                elif c["spz"]:
                    arriva_match = next((b for b in data_arriva if str(b.get("spz", "")).strip() == c["spz"]), None)
                    if arriva_match:
                        a_lat, a_lng = arriva_match.get("latitude", 0), arriva_match.get("longitude", 0)
                        if math.hypot(lat1 - a_lat, lng1 - a_lng) > 0.015:
                            c["spz_verified"] = False 

            if not is_train and not c["first_dep_time"]:
                if not c["tt_last_fetch"] or (now - c["tt_last_fetch"]).total_seconds() > 300:
                    if tt_fetches_this_tick < 5: 
                        tt_fetches_this_tick += 1
                        c["tt_last_fetch"] = now
                        c["tt_is_fetching"] = True
                        threading.Thread(target=fetch_tt_bg, args=(bus_id, c), daemon=True).start()

            is_before_departure = False
            time_to_dep = 0
            mins_to_last = None
            
            if c["first_dep_time"]:
                try:
                    dh, dm = map(int, c["first_dep_time"].split(':'))
                    dep_total = dh * 60 + dm
                    cur_total = now.hour * 60 + now.minute
                    diff = dep_total - cur_total
                    if diff < -720: diff += 1440
                    elif diff > 720: diff -= 1440
                    if diff > 0:
                        is_before_departure = True
                        time_to_dep = diff
                except: pass

            if c["last_dep_time"]:
                try:
                    dh, dm = map(int, c["last_dep_time"].split(':'))
                    dep_total = dh * 60 + dm
                    cur_total = now.hour * 60 + now.minute
                    diff = dep_total - cur_total
                    if diff < -720: diff += 1440
                    elif diff > 720: diff -= 1440
                    mins_to_last = diff
                except: pass

            is_huge_delay = (delay_val >= 100)
            old_status = c["status"]

            if is_before_departure:
                c["actual_end_time"] = None 
                if time_to_dep <= 240:
                    c["status"] = "Začátek linky (Čeká)"
                    c["color_class"] = "bg-blue"
                    delay_val = -time_to_dep 
                else: 
                    c["status"] = "Čeká na spoj (>4h)"
                    c["color_class"] = "bg-gray"
                    delay_val = -time_to_dep
            
            elif (mins_to_last is not None and mins_to_last <= -20) or is_huge_delay:
                if is_moving:
                    c["status"] = "Manipulační jízda"
                    c["color_class"] = "bg-yellow"
                    c["actual_end_time"] = None 
                else:
                    if inactive_mins > 10:
                        c["status"] = "Odstaven"
                        c["color_class"] = "bg-gray"
                        if not c["actual_end_time"]: c["actual_end_time"] = now.strftime('%H:%M')
                    else:
                        c["status"] = "Konečná zastávka"
                        c["color_class"] = "bg-purple"
                        if not c["actual_end_time"]: c["actual_end_time"] = now.strftime('%H:%M')
            else:
                if delay_val <= -10000:
                    c["status"] = "Konečná zastávka"
                    c["color_class"] = "bg-purple"
                    if not c["actual_end_time"]: c["actual_end_time"] = now.strftime('%H:%M')
                elif delay_val < -1: 
                    c["status"] = "Jízda (Náskok)" if is_moving else "Stojí (Vyčkává)"
                    c["color_class"] = "bg-darkblue"
                else: 
                    c["status"] = "Jízda" if is_moving else "Stojí"
                    c["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"
                    
                if is_moving and not c["actual_start_time"] and not is_train:
                    c["actual_start_time"] = now.strftime('%H:%M')

            c["final_delay_display"] = delay_val

            if old_status != c["status"] or is_moving or not c.get("db_first_upsert"):
                upsert_to_history(db_client, c)
                c["db_first_upsert"] = True

            last_up_str = c["last_moved"].strftime("%H:%M:%S") if c["last_moved"] else "N/A"
            final_line_display = c.get("real_linka_spoj") or c["line"] if c["line"] else ("Vlak" if c["is_train"] else "Neznámá")
            
            new_live_data.append({
                "id": bus_id, "trip_id": c["trip_id"], "lat": c["lat"], "lng": c["lng"], 
                "line": final_line_display,
                "delay": c.get("final_delay_display", 0), "destination": c["destination"], 
                "spz": c["spz"] or "Neznámá", "spz_verified": c["spz_verified"], "is_train": c["is_train"], 
                "status": c["status"], "color_class": c["color_class"],
                "inactive_minutes": inactive_mins, 
                "last_updated": last_up_str, "estimated_spz": c["estimated"]
            })

        global LIVE_BUSES_DATA
        LIVE_BUSES_DATA = new_live_data
        time.sleep(10)

def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()

@mapa_bp.route('/historie')
def stranka_historie_index():
    return render_template_string(f"""<!DOCTYPE html><html style="background:#0f172a;"><head><title>Historie | OIS IDPK</title><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="background:#0f172a; color:white;">{HTML_HISTORIE_INDEX}</body></html>""")

@mapa_bp.route('/historie/<spz>')
def stranka_historie_detail(spz):
    html_filled = HTML_HISTORIE_DETAIL.replace("{{SPZ}}", spz)
    return render_template_string(f"""<!DOCTYPE html><html style="background:#0f172a;"><head><title>Detail Vozu {spz}</title><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="background:#0f172a; color:white;">{html_filled}</body></html>""")

@mapa_bp.route('/api/history_full')
def api_history_full():
    db = get_db_client()
    if not db: return jsonify({"system_starting": is_system_starting(), "data": []})
    try:
        res = db.table("bus_history").select("*").order("created_at", desc=True).limit(2000).execute()
        return jsonify({"system_starting": is_system_starting(), "data": res.data})
    except: return jsonify({"system_starting": is_system_starting(), "data": []})

@mapa_bp.route('/api/history_latest')
def api_history_latest():
    db = get_db_client()
    if not db: return jsonify([])
    try:
        res = db.table("bus_history").select("*").order("created_at", desc=True).limit(2000).execute()
        return jsonify(res.data)
    except: return jsonify([])

@mapa_bp.route('/api/history_spz/<spz>')
def api_history_spz(spz):
    db = get_db_client()
    if not db: return jsonify({"system_starting": is_system_starting(), "data": []})
    try:
        res = db.table("bus_history").select("*").eq("spz", spz).order("created_at", desc=True).limit(500).execute()
        return jsonify({"system_starting": is_system_starting(), "data": res.data})
    except: return jsonify({"system_starting": is_system_starting(), "data": []})

@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({
        "status": "success", 
        "system_starting": is_system_starting(),
        "server_time": datetime.now(ZoneInfo('Europe/Prague')).strftime("%H:%M:%S"),
        "buses": LIVE_BUSES_DATA
    })

@mapa_bp.route('/mapa')
def mapa_stranka():
    return render_template_string(f"""<!DOCTYPE html><html style="background:#0f172a;"><head><title>Mapa | OIS IDPK</title><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="background:#0f172a; color:white;">{HTML_MAPA}</body></html>""")

@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    cb = int(time.time() * 1000)
    headers = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'}
    try:
        info_html = ""
        with urllib.request.urlopen(urllib.request.Request(f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb}", headers=headers), timeout=5) as r1: info_html = r1.read().decode('utf-8')
        tt_html = ""
        with urllib.request.urlopen(urllib.request.Request(f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}", headers=headers), timeout=5) as r2: tt_html = r2.read().decode('utf-8')

        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        linkospoj = m_linka.group(1).strip() if m_linka else "N/A"
        spoj_num = m_spoj.group(1).strip() if m_spoj else "N/A"
        tables = re.findall(r'(<table[^>]*>.*?</table>)', tt_html, re.IGNORECASE | re.DOTALL)
        tt_table_only = "".join(tables) if tables else "<p style='color:#ef4444;text-align:center;'>JŘ není k dispozici.</p>"

        return Response(f"""
        <style>.ois-detail{{background:#0f172a;color:white;font-family:sans-serif;padding:15px;border-radius:8px;}}
        .ois-header{{color:#38bdf8;font-weight:bold;border-bottom:1px solid #444;margin-bottom:15px;padding-bottom:10px;font-size:18px;}}
        .ois-table-wrapper{{margin-top:10px;border:1px solid #555;border-radius:5px;overflow-x:auto;background:#2a2a2a;}}
        .ois-table-wrapper table{{width:100%;border-collapse:collapse;font-size:13px;color:#f8fafc;}}
        .ois-table-wrapper th{{background:#222;color:#38bdf8;text-align:left;padding:10px;border-bottom:2px solid #555;}}
        .ois-table-wrapper td{{padding:10px;border-bottom:1px solid #444;}}
        .ois-table-wrapper tr:nth-child(even) td{{background-color:#2a2a2a;}} .ois-table-wrapper tr:nth-child(odd) td{{background-color:#333333;}}
        </style>
        <div class="ois-detail"><div class="ois-header"><i class="fas fa-bus"></i> Spoj: {linkospoj} / {spoj_num}</div>
        <div class="ois-table-wrapper">{tt_table_only}</div></div>
        """, mimetype='text/html')
    except Exception as e: return f"<div style='color:#ef4444;padding:20px;'>Chyba JŘ</div>"
