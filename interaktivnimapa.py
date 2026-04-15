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
    print("[MAPA-WARN] Modul 'supabase' není dostupný! Mapa poběží, ale historie se neuloží.")

mapa_bp = Blueprint('mapa_bp', __name__)

HTML_HISTORIE_INDEX = """
<div style="padding: 20px; max-width: 1200px; margin: auto; font-family: sans-serif;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 24px;"><i class="fas fa-bus"></i> Seznam sledovaných vozů</h2>
        <div class="field" style="margin-bottom: 0;">
          <p class="control has-icons-left">
            <input class="input" id="historySearch" type="text" placeholder="Filtrovat linku (např. 490, 735) nebo SPZ..." style="background: #1e293b; color: white; border-color: #334155; min-width: 300px;">
            <span class="icon is-small is-left" style="color: #94a3b8;">
              <i class="fas fa-search"></i>
            </span>
          </p>
        </div>
    </div>

    <div style="background: #1e293b; border-radius: 10px; border: 1px solid #334155; overflow-x: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <table class="table is-fullwidth is-hoverable" style="background: transparent; color: #cbd5e1; margin-bottom: 0; min-width: 800px;">
            <thead>
                <tr style="background: #0f172a;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">SPZ</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední známá Linka</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Poslední cíl</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Naposledy viděn</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Akce</th>
                </tr>
            </thead>
            <tbody id="historyTableBody">
                <tr><td colspan="5" style="text-align:center; padding: 30px; color: #38bdf8;"><i class="fas fa-spinner fa-spin"></i> Analyzuji databázi vozů...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        async function loadIndex() {
            try {
                const response = await fetch('/api/history_latest');
                const data = await response.json();
                const tbody = document.getElementById('historyTableBody');
                tbody.innerHTML = '';

                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Žádná data v databázi.</td></tr>';
                    return;
                }

                const uniqueBuses = {};
                data.forEach(row => {
                    if (!uniqueBuses[row.spz] && row.spz !== 'Neznámá') {
                        uniqueBuses[row.spz] = row;
                    }
                });

                Object.values(uniqueBuses).forEach(row => {
                    const date = new Date(row.created_at);
                    const timeStr = date.toLocaleDateString('cs-CZ') + ' ' + date.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                    const linkaClean = row.linka || '---';
                    
                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.setAttribute('data-spz', row.spz);
                    tr.setAttribute('data-linka', linkaClean);
                    
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;"><span class="tag is-warning" style="background:#f59e0b; color:#0f172a; font-weight:bold; font-size:14px;">${row.spz}</span></td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${linkaClean}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${row.destination || '---'}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle;">${timeStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="/historie/${row.spz}" class="button is-small is-primary">
                                <i class="fas fa-list" style="margin-right: 5px;"></i> Detail a Historie
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch(e) { 
                document.getElementById('historyTableBody').innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color:#ef4444;">Chyba připojení k DB.</td></tr>';
            }
        }

        document.getElementById('historySearch').addEventListener('input', function(e) {
            const val = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#historyTableBody tr');
            rows.forEach(row => {
                if(!row.hasAttribute('data-spz')) return;
                const spz = row.getAttribute('data-spz').toLowerCase();
                const linka = row.getAttribute('data-linka').toLowerCase();
                
                const matchSpz = spz.includes(val);
                const matchLinka = linka.includes(val) || linka.startsWith(val);

                row.style.display = (matchSpz || matchLinka) ? '' : 'none';
            });
        });

        loadIndex();
    </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
"""

HTML_HISTORIE_DETAIL = """
<div style="padding: 20px; max-width: 1000px; margin: auto; font-family: sans-serif;">
    <a href="/historie" class="button is-small is-dark" style="margin-bottom: 15px;"><i class="fas fa-arrow-left"></i> Zpět na seznam</a>
    
    <div style="background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #38bdf8; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
        <h2 style="color: white; margin: 0 0 10px 0; font-size: 28px;">Autobus SPZ: <span style="color:#f59e0b;">{{SPZ}}</span></h2>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 15px;">Tato karta obsahuje historii jízd a poloh za posledních 30 dní.</p>
        <div id="absoluteLastPos">
            <span style="color:#38bdf8;"><i class="fas fa-spinner fa-spin"></i> Hledám aktuální polohu...</span>
        </div>
    </div>

    <h3 style="color: #38bdf8; margin-bottom: 15px; font-size: 20px;"><i class="fas fa-route"></i> Historie odjetých spojů</h3>
    <div style="background: #0f172a; border-radius: 10px; border: 1px solid #334155; overflow-x: auto;">
        <table class="table is-fullwidth" style="background: transparent; color: #cbd5e1; margin-bottom: 0;">
            <thead>
                <tr style="background: #1e293b;">
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Datum</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Linka / Spoj</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Začátek trasy</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px;">Konec / Poslední status</th>
                    <th style="color: #38bdf8; border-color: #334155; padding: 12px; text-align: center;">Odkaz na Mapu</th>
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
                const data = await response.json();
                
                const liveRes = await fetch('/api/live_buses');
                const liveData = await liveRes.json();
                const liveBus = liveData.buses ? liveData.buses.find(b => b.spz === '{{SPZ}}') : null;

                const tbody = document.getElementById('detailTableBody');
                const lastPosDiv = document.getElementById('absoluteLastPos');
                tbody.innerHTML = '';

                if (data.length === 0 && !liveBus) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Žádná historie nebyla nalezena.</td></tr>';
                    lastPosDiv.innerHTML = '<span style="color:#ef4444;">Poloha neznámá</span>';
                    return;
                }

                // TOP KARTA - ŽIVÁ NEBO POSLEDNÍ HISTORICKÁ DATA
                let currentLat = 0;
                let currentLng = 0;
                let topStatus = "";
                let topTime = "";
                let liveIndicator = "";

                if (liveBus && liveBus.lat) {
                    currentLat = liveBus.lat;
                    currentLng = liveBus.lng;
                    topStatus = `${liveBus.status} (${liveBus.line || 'Bez linky'})`;
                    topTime = "Nyní (Živá data)";
                    liveIndicator = `<br><span style="color:#10b981; font-weight:bold; font-size:13px;"><i class="fas fa-satellite-dish"></i> Získáno z živé mapy</span>`;
                } else if (data.length > 0) {
                    const newest = data[0];
                    currentLat = newest.last_lat;
                    currentLng = newest.last_lng;
                    topStatus = `${newest.status} (${newest.linka || 'Bez linky'})`;
                    const nd = new Date(newest.created_at);
                    topTime = `${nd.toLocaleDateString('cs-CZ')} ${nd.toLocaleTimeString('cs-CZ')}`;
                    liveIndicator = `<br><span style="color:#94a3b8; font-size:13px;"><i class="fas fa-database"></i> Získáno z historie</span>`;
                }

                lastPosDiv.innerHTML = `
                    <div style="display:flex; align-items:center; gap: 15px;">
                        <div style="flex-grow: 1;">
                            <strong style="color: white; font-size:16px;">Stav vozidla:</strong> <span style="font-size:16px;">${topStatus}</span><br>
                            <span style="color: #cbd5e1; font-size: 14px;">Zaznamenáno: ${topTime}</span>
                            ${liveIndicator}
                        </div>
                        <a href="/mapa#${currentLat},${currentLng}" class="button is-info is-medium" style="font-weight:bold;">
                            <i class="fas fa-crosshairs" style="margin-right: 8px;"></i> Aktuální Poloha
                        </a>
                    </div>
                `;

                // SESKUPOVÁNÍ DO TRAS A JÍZD
                const chronoData = data.reverse();
                const trips = [];
                let currentTrip = null;

                chronoData.forEach(row => {
                    if (!row.linka || row.linka === 'Neznámá') return;
                    
                    const rowDate = new Date(row.created_at);
                    const dateString = rowDate.toLocaleDateString('cs-CZ');

                    let isNewTrip = false;
                    if (!currentTrip) {
                        isNewTrip = true;
                    } else {
                        if (currentTrip.linka !== row.linka) isNewTrip = true;
                        const diffHours = (rowDate - currentTrip.endTime) / (1000 * 60 * 60);
                        if (diffHours > 3) isNewTrip = true;
                    }

                    if (isNewTrip) {
                        if (currentTrip) trips.push(currentTrip);
                        currentTrip = {
                            linka: row.linka,
                            day: dateString,
                            startTime: rowDate,
                            endTime: rowDate,
                            last_lat: row.last_lat,
                            last_lng: row.last_lng,
                            last_status: row.status
                        };
                    } else {
                        currentTrip.endTime = rowDate;
                        currentTrip.last_lat = row.last_lat;
                        currentTrip.last_lng = row.last_lng;
                        currentTrip.last_status = row.status;
                    }
                });
                if (currentTrip) trips.push(currentTrip);

                trips.reverse(); 

                trips.forEach(trip => {
                    const startStr = trip.startTime.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                    
                    const isCompleted = trip.last_status.includes('Konečná') || trip.last_status.includes('Odstaven') || trip.last_status.includes('Ztráta') || trip.last_status.includes('Zmizel');
                    
                    let endStr = "";
                    if (isCompleted) {
                        const endDay = trip.endTime.toLocaleDateString('cs-CZ');
                        if (endDay !== trip.day) {
                            endStr = `<span style="font-size:12px; color:#cbd5e1;">${endDay}</span><br>${trip.endTime.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'})} (${trip.last_status})`;
                        } else {
                            endStr = `${trip.endTime.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'})} <span style="font-size:12px; color:#94a3b8;">(${trip.last_status})</span>`;
                        }
                    } else {
                        endStr = `<span style="color:#eab308; font-weight:bold;"><i class="fas fa-spinner fa-pulse"></i> Aktivní (Nedokončena)</span><br><span style="font-size:12px; color:#94a3b8;">Poslední log: ${trip.last_status}</span>`;
                    }
                    
                    const tr = document.createElement('tr');
                    tr.style.borderColor = '#334155';
                    tr.innerHTML = `
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color:#cbd5e1;">${trip.day}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; font-weight: bold; color: white;">${trip.linka}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #10b981;">${startStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; color: #ef4444;">${endStr}</td>
                        <td style="border-color: #334155; padding: 12px; vertical-align: middle; text-align: center;">
                            <a href="/mapa#${trip.last_lat},${trip.last_lng}" class="button is-small is-outlined" style="background: transparent; color: #cbd5e1; border-color: #4b5563;">
                                <i class="fas fa-map" style="margin-right: 5px;"></i> Lokace
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch(e) { console.error(e); }
        }

        loadDetail();
    </script>
</div>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
"""

HTML_MAPA = """
<div style="padding: 20px;">
    <h2 style="color: var(--blue-main); margin-bottom: 20px;"><i class="fas fa-map-marked-alt"></i> Interaktivní Mapa Spojů</h2>
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
        
        .bg-green { background-color: #10b981; } 
        .bg-red { background-color: #ef4444; }   
        .bg-blue { background-color: #3b82f6; } 
        .bg-darkblue { background-color: #1e3a8a; }
        .bg-gray { background-color: #64748b; border-color: #475569; color: #cbd5e1;} 
        .bg-purple { background-color: #a855f7; }
        .bg-yellow { background-color: #eab308; color: #1e293b; }
        
        .dark-popup .leaflet-popup-content-wrapper { background: #1e293b; color: white; border: 1px solid #334155; padding: 0; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); }
        .dark-popup .leaflet-popup-tip { background: #1e293b; border-bottom: 1px solid #334155; border-right: 1px solid #334155; }
        .dark-popup .leaflet-popup-content { margin: 0; width: 270px !important; }
        
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
                if(data.status === "success") {
                    markersLayer.clearLayers();
                    data.buses.forEach(bus => {
                        if(bus.lat && bus.lng) {
                            let markerColor = bus.color_class; 
                            let delayText = "";
                            let delayVal = parseInt(bus.delay); 

                            if (markerColor === "bg-gray") {
                                if (bus.status.includes(">4h")) {
                                    let aheadMin = Math.abs(delayVal);
                                    let aheadH = Math.floor(aheadMin / 60);
                                    let aheadM = aheadMin % 60;
                                    delayText = `<span style="color:#94a3b8;">Odjezd za ${aheadH}h ${aheadM}m</span>`;
                                } else {
                                    delayText = `<span style="color:#94a3b8;">N/A</span>`;
                                }
                            } else if (markerColor === "bg-yellow") {
                                delayText = `<span style="color:#eab308;">Mimo linku</span>`;
                            } else if (markerColor === "bg-purple") {
                                delayText = `<span style="color:#a855f7;">Konečná zastávka</span>`;
                            } else if (markerColor === "bg-blue") {
                                let aheadMin = Math.abs(delayVal);
                                let aheadH = Math.floor(aheadMin / 60);
                                let aheadM = aheadMin % 60;
                                let timeStr = aheadH > 0 ? `${aheadH}h ${aheadM}min` : `${aheadM} min`;
                                
                                let depDate = new Date(Date.now() + aheadMin * 60000); 
                                let depTime = depDate.toLocaleTimeString('cs-CZ', {hour: '2-digit', minute:'2-digit'});
                                delayText = `<span style="color:#3b82f6;">Odjezd za ${timeStr}<br><small style="color:#94a3b8;">(${depTime})</small></span>`;
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
                                let spzDisplay = bus.spz;
                                if (bus.estimated_spz && bus.spz !== "Neznámá") spzDisplay = `Odhad (${bus.spz})`;
                                spzHtml = `<div class="popup-row"><span class="popup-label">SPZ:</span><span class="popup-value badge-spz">${spzDisplay}</span></div>`;
                            }
                            
                            let statusColor = "#10b981"; 
                            if (bus.status.includes("Stojí")) statusColor = "#ef4444"; 
                            else if (bus.status.includes("Koneč")) statusColor = "#a855f7"; 
                            else if (bus.status.includes("Začátek") || bus.status.includes("Čeká")) statusColor = "#3b82f6"; 
                            else if (bus.status.includes("Odstaven") || bus.status.includes("N/A") || bus.status.includes("signál") || bus.status.includes("Zmizel")) statusColor = "#94a3b8"; 
                            else if (bus.status.includes("Manipulační")) statusColor = "#eab308"; 
                            else if (bus.status.includes("Náskok") || bus.status.includes("Vyčkává")) statusColor = "#60a5fa"; 
                            
                            let statusHtml = `<div class="popup-row"><span class="popup-label">Status:</span><span class="popup-value" style="color:${statusColor};">${bus.status}</span></div>`;
                            let updatedHtml = `<div class="popup-row"><span class="popup-label">Poslední pohyb:</span><span class="popup-value" style="color:#94a3b8;">${bus.last_updated}</span></div>`;
                            
                            let popupHTML = `
                                <div class="popup-header">
                                    <h3 class="popup-header-title"><i class="${bus.is_train ? 'fas fa-train' : 'fas fa-bus'}"></i> Linka ${bus.line}</h3>
                                </div>
                                <div class="popup-body">
                                    <div class="popup-row"><span class="popup-label">Cíl:</span><span class="popup-value" style="color:white;">${bus.destination || "Neznámý"}</span></div>
                                    ${spzHtml}
                                    ${statusHtml}
                                    ${updatedHtml}
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

def get_prague_time():
    return datetime.now(ZoneInfo('Europe/Prague')).replace(tzinfo=None)

def calc_mins_to_departure(dep_time_str, current_time):
    try:
        dh, dm = map(int, dep_time_str.split(':'))
        ch, cm = current_time.hour, current_time.minute
        dep_total = dh * 60 + dm
        cur_total = ch * 60 + cm
        diff = dep_total - cur_total
        if diff < -720: diff += 1440
        elif diff > 720: diff -= 1440
        return diff
    except:
        return None

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
        tt_url = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb_time}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://pvvd.idpk.cz/',
            'Cache-Control': 'no-cache'
        }
        req_tt = urllib.request.Request(tt_url, headers=headers)
        with opener.open(req_tt, timeout=4) as r_tt:
            tt_html = r_tt.read().decode('utf-8')
            times = re.findall(r'\b\d{2}:\d{2}\b', tt_html)
            if times:
                cached_dict["first_dep_time"] = times[0]
                cached_dict["last_dep_time"] = times[-1] # Novinka! Stahujeme i přesný konec linky podle JŘ
    except Exception: pass
    finally: cached_dict["tt_is_fetching"] = False

def log_to_history(db, cached_dict, status_text):
    if cached_dict.get("is_train"): return
    if not db or not cached_dict.get("spz") or cached_dict["spz"] == "Neznámá": return
    
    try:
        now_prague = get_prague_time()
        data = {
            "spz": cached_dict["spz"],
            "linka": cached_dict.get("line", "Neznámá"),
            "destination": cached_dict.get("destination", "Neznámý cíl"),
            "last_lat": cached_dict.get("lat"),
            "last_lng": cached_dict.get("lng"),
            "status": status_text,
            "created_at": now_prague.isoformat()
        }
        db.table("bus_history").insert(data).execute()
        print(f"[MAPA-DB] Zapsáno do DB: {cached_dict['spz']} ({status_text})")
    except Exception: pass

def background_map_worker():
    print("[MAPA] Inteligentní mozek (JŘ End Fix + DB Historie) startuje...", flush=True)
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
    last_db_cleanup = get_prague_time()

    while True:
        now = get_prague_time()
        
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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Content-Type': 'application/json',
                    'Origin': 'https://www.arriva.cz',
                    'Referer': 'https://www.arriva.cz/',
                    'Cache-Control': 'no-cache'
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
                        ghost_spz = None
                        ghost_locked = False
                        for gid, g_cached in list(GLOBAL_BUS_CACHE.items()):
                            if g_cached.get("is_offline") and g_cached.get("spz"):
                                g_dist = math.hypot(lat1 - g_cached["lat"], lng1 - g_cached["lng"])
                                if g_dist < 0.001:  
                                    ghost_spz = g_cached["spz"]
                                    ghost_locked = True
                                    del GLOBAL_BUS_CACHE[gid] 
                                    break

                        GLOBAL_BUS_CACHE[bus_id] = {
                            "lat": lat1, "lng": lng1, "line": line, 
                            "spz": ghost_spz, "spz_locked": ghost_locked, "estimated": bool(ghost_spz),
                            "last_moved": now, "first_seen": now, "last_inflow_seen": now,
                            "status": "Načítání...", "color_class": "bg-gray", "destination": dest1_original, 
                            "is_train": is_train, "raw_delay": delay, 
                            "first_dep_time": None, "last_dep_time": None, "tt_last_fetch": None,
                            "tt_is_fetching": False, "is_offline": False,
                            "db_trip_logged": False, "db_offline_logged": False, "db_start_logged": False,
                            "db_manipulacni_logged": False
                        }
                    else:
                        c = GLOBAL_BUS_CACHE[bus_id]
                        c["last_inflow_seen"] = now
                        c["is_offline"] = False
                        c["raw_delay"] = delay
                        c["is_train"] = is_train
                        
                        dist_moved = math.hypot(lat1 - c["lat"], lng1 - c["lng"])
                        
                        if c["line"] != line:
                            c["line"] = line
                            c["destination"] = dest1_original
                            c["first_dep_time"] = None 
                            c["last_dep_time"] = None
                            c["db_trip_logged"] = False 
                            c["db_start_logged"] = False 
                            c["db_manipulacni_logged"] = False
                            if dist_moved < 0.005: 
                                c["estimated"] = True
                                c["last_moved"] = now
                        elif c["destination"] != dest1_original:
                            c["destination"] = dest1_original
                        
                        if dist_moved > 0.0001:
                            c["last_moved"] = now
                            c["lat"] = lat1
                            c["lng"] = lng1

                except: continue

        for bus_id, cached in list(GLOBAL_BUS_CACHE.items()):
            if cached.get("spz") and cached.get("spz_locked") and not cached.get("is_train"):
                arriva_match = next((b for b in data_arriva if str(b.get("spz", "")).strip() == cached["spz"]), None)
                if arriva_match:
                    a_lat, a_lng = arriva_match.get("latitude", 0), arriva_match.get("longitude", 0)
                    dist_check = math.hypot(cached.get("lat", 0) - a_lat, cached.get("lng", 0) - a_lng)
                    if dist_check > 0.015:
                        cached["spz"] = None
                        cached["spz_locked"] = False
                        cached["estimated"] = False

        assigned_spzs = set()
        for bus_id, cached in GLOBAL_BUS_CACHE.items():
            if cached.get("spz") and cached.get("spz_locked"):
                assigned_spzs.add(cached["spz"])

        new_live_data = []
        tt_fetches_this_tick = 0 

        for bus_id, cached in list(GLOBAL_BUS_CACHE.items()):
            if bus_id not in current_inflow_ids:
                offline_mins = (now - cached["last_inflow_seen"]).total_seconds() / 60.0
                
                if offline_mins > 720: 
                    del GLOBAL_BUS_CACHE[bus_id]
                    continue
                
                cached["is_offline"] = True
                
                if offline_mins > 2 and not cached.get("db_trip_logged"):
                    log_to_history(db_client, cached, "Konečná / Zmizel z mapy")
                    cached["db_trip_logged"] = True

                if offline_mins < 20:
                    cached["status"] = "Konečná / Bez dat"
                    cached["color_class"] = "bg-purple"
                else:
                    cached["status"] = "Odstaven (Bez signálu)"
                    cached["color_class"] = "bg-gray"
                    if offline_mins > 60: cached["spz_locked"] = False
                    
            else:
                lat1, lng1 = cached["lat"], cached["lng"]
                line, dest1_original = cached["line"], cached["destination"]
                dest1_lower = dest1_original.lower()
                is_train = cached["is_train"]
                
                time_ref = cached["last_moved"] if cached["last_moved"] else cached["first_seen"]
                inactive_mins = (now - time_ref).total_seconds() / 60.0
                is_moving = inactive_mins < 1 
                
                delay_val = cached["raw_delay"]

                # PÁROVÁNÍ SPZ
                found_in_arriva = False
                if not is_train and not cached["spz_locked"]:
                    buses_on_line = [b for b in data_arriva if str(b.get("linkNumber","")).strip() == line or str(b.get("linkNumberAlias","")).strip() == line]
                    close_buses = [b for b in buses_on_line if math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0)) < 0.015]
                    
                    best_spz = None
                    if len(close_buses) == 1:
                        best_spz = close_buses[0].get("spz", "").strip()
                        found_in_arriva = True
                    elif len(close_buses) > 1:
                        d1_clean = re.sub(r'\W+', '', dest1_lower)
                        for cb in close_buses:
                            d2_clean = re.sub(r'\W+', '', str(cb.get("destinationName", "")).lower())
                            if d1_clean in d2_clean or d2_clean in d1_clean or d1_clean == "" or d2_clean == "":
                                best_spz = cb.get("spz", "").strip()
                                found_in_arriva = True
                                break

                    if not best_spz:
                        ultra_close = [b for b in data_arriva if math.hypot(lat1 - b.get("latitude",0), lng1 - b.get("longitude",0)) < 0.001]
                        valid_ultra = [b for b in ultra_close if b.get("spz", "").strip() not in assigned_spzs and b.get("spz", "").strip() != "Neznámá"]
                        if len(valid_ultra) == 1:
                            best_spz = valid_ultra[0].get("spz", "").strip()
                            found_in_arriva = True
                            cached["estimated"] = True 

                    if best_spz and best_spz != "Neznámá" and best_spz not in assigned_spzs:
                        cached["spz"] = best_spz
                        cached["spz_locked"] = True
                        assigned_spzs.add(best_spz) 
                
                if not is_train and cached["spz"]:
                    for b2 in data_arriva:
                        if b2.get("spz", "").strip() == cached["spz"]:
                            found_in_arriva = True
                            break

                needs_tt = not is_train and not cached.get("first_dep_time") and not cached.get("is_offline")
                if needs_tt and not cached.get("tt_is_fetching"):
                    if not cached.get("tt_last_fetch") or (now - cached["tt_last_fetch"]).total_seconds() > 300:
                        if tt_fetches_this_tick < 5: 
                            tt_fetches_this_tick += 1
                            cached["tt_last_fetch"] = now
                            cached["tt_is_fetching"] = True
                            threading.Thread(target=fetch_tt_bg, args=(bus_id, cached), daemon=True).start()

                # VÝPOČTY Z JŘ A ZPOŽDĚNÍ
                is_before_departure = False
                time_to_dep = 0
                is_route_finished = False
                is_bugged_delay = (delay_val >= 100) # Ochrana proti chybě Inflow (+100min)

                if cached.get("first_dep_time"):
                    diff = calc_mins_to_departure(cached["first_dep_time"], now)
                    if diff is not None and diff > 0:
                        is_before_departure = True
                        time_to_dep = diff

                # Tady je ten trik na opravení manipulační jízdy! 
                # Musí projít čas POSLEDNÍ zastávky v JŘ (+ započítané zpoždění).
                if cached.get("last_dep_time"):
                    mins_to_last = calc_mins_to_departure(cached["last_dep_time"], now)
                    if mins_to_last is not None:
                        expected_mins_to_end = mins_to_last + delay_val
                        if expected_mins_to_end < 0:
                            is_route_finished = True

                # --- ROZHODOVÁNÍ BAREV A STATUSŮ ---
                if is_before_departure:
                    if time_to_dep <= 240:
                        cached["status"] = "Začátek linky (Čeká)"
                        cached["color_class"] = "bg-blue"
                        delay_val = -time_to_dep 
                    else: 
                        cached["status"] = "Čeká na spoj (>4h)"
                        cached["color_class"] = "bg-gray"
                        delay_val = -time_to_dep
                        if inactive_mins > 60: cached["spz_locked"] = False
                
                elif is_route_finished or is_bugged_delay:
                    # Linka je podle JŘ dojetá (nebo je to Inflow bug). Hýbe se?
                    if is_moving:
                        cached["status"] = "Manipulační jízda"
                        cached["color_class"] = "bg-yellow"
                        if not cached.get("db_manipulacni_logged"):
                            log_to_history(db_client, cached, "Manipulační jízda")
                            cached["db_manipulacni_logged"] = True
                    else:
                        if inactive_mins > 5:
                            cached["status"] = "Odstaven"
                            cached["color_class"] = "bg-gray"
                        else:
                            cached["status"] = "Konečná zastávka"
                            cached["color_class"] = "bg-purple"
                            if not cached.get("db_trip_logged"):
                                log_to_history(db_client, cached, "Konečná zastávka")
                                cached["db_trip_logged"] = True
                else:
                    # NORMÁLNÍ JÍZDA - jezdí přesně podle JŘ
                    if delay_val < -1: 
                        if is_moving:
                            cached["status"] = "Jízda (Náskok)"
                            cached["color_class"] = "bg-darkblue"
                        else:
                            cached["status"] = "Stojí (Vyčkává)"
                            cached["color_class"] = "bg-darkblue"
                    else: 
                        if is_moving: cached["status"] = "Jízda"
                        else: cached["status"] = "Stojí"
                        cached["color_class"] = "bg-red" if delay_val >= 5 else "bg-green"
                        
                    # Zapíše Start Linky, jakmile poprvé vyrazí
                    if is_moving and not cached.get("db_start_logged") and not is_train:
                        log_to_history(db_client, cached, "Začátek trasy")
                        cached["db_start_logged"] = True

                cached["final_delay_display"] = delay_val

            last_up_str = cached["last_moved"].strftime("%H:%M:%S") if cached["last_moved"] else "N/A"
            new_live_data.append({
                "id": bus_id, "lat": cached["lat"], "lng": cached["lng"], 
                "line": cached["line"] if cached["line"] else ("Vlak" if cached["is_train"] else "Neznámá"),
                "delay": cached.get("final_delay_display", 0), "destination": cached["destination"], 
                "spz": cached["spz"] or "Neznámá", "is_train": cached["is_train"], 
                "status": cached["status"], "color_class": cached["color_class"],
                "inactive_minutes": inactive_mins if not cached.get("is_offline") else 999, 
                "last_updated": last_up_str, "estimated_spz": cached["estimated"]
            })

        global LIVE_BUSES_DATA
        LIVE_BUSES_DATA = new_live_data
        time.sleep(10)

def start_map_background_task():
    threading.Thread(target=background_map_worker, daemon=True).start()

@mapa_bp.route('/historie')
def stranka_historie_index():
    return render_template_string(f"""
    <!DOCTYPE html>
    <html style="background: #0f172a;">
    <head>
        <title>Historie Spojů | OIS IDPK</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="background: #0f172a; color: white;">
        {HTML_HISTORIE_INDEX}
    </body>
    </html>
    """)

@mapa_bp.route('/historie/<spz>')
def stranka_historie_detail(spz):
    html_filled = HTML_HISTORIE_DETAIL.replace("{{SPZ}}", spz)
    return render_template_string(f"""
    <!DOCTYPE html>
    <html style="background: #0f172a;">
    <head>
        <title>Detail Vozu {spz} | OIS IDPK</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="background: #0f172a; color: white;">
        {html_filled}
    </body>
    </html>
    """)

@mapa_bp.route('/api/history_latest')
def api_history_latest():
    db = get_db_client()
    if not db: return jsonify([])
    try:
        res = db.table("bus_history").select("*").order("created_at", desc=True).limit(3000).execute()
        return jsonify(res.data)
    except: return jsonify([])

@mapa_bp.route('/api/history_spz/<spz>')
def api_history_spz(spz):
    db = get_db_client()
    if not db: return jsonify([])
    try:
        res = db.table("bus_history").select("*").eq("spz", spz).order("created_at", desc=True).limit(2000).execute()
        return jsonify(res.data)
    except: return jsonify([])

@mapa_bp.route('/api/live_buses', methods=['GET'])
def api_live_buses():
    return jsonify({"status": "success", "buses": LIVE_BUSES_DATA})

@mapa_bp.route('/mapa')
def mapa_stranka():
    return render_template_string(f"""
    <!DOCTYPE html>
    <html style="background: #0f172a;">
    <head>
        <title>Mapa | OIS IDPK</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="background: #0f172a; color: white;">
        {HTML_MAPA}
    </body>
    </html>
    """)

@mapa_bp.route('/api/bus_detail/<bus_id>')
def api_bus_detail(bus_id):
    cb = int(time.time() * 1000)
    url_info = f"https://pvvd.idpk.cz/Ajax/OpenInfoWindow?id={bus_id}&_={cb}"
    url_tt = f"https://pvvd.idpk.cz/Ajax/GetTimetable?vehicleNumber={bus_id}&currentStopId=0&_={cb}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://pvvd.idpk.cz/',
        'Cache-Control': 'no-cache'
    }
    
    try:
        info_html = ""
        req1 = urllib.request.Request(url_info, headers=headers)
        with urllib.request.urlopen(req1, timeout=5) as r1: info_html = r1.read().decode('utf-8')
            
        tt_html = ""
        req2 = urllib.request.Request(url_tt, headers=headers)
        with urllib.request.urlopen(req2, timeout=5) as r2: tt_html = r2.read().decode('utf-8')

        linkospoj, spoj_num = "N/A", "N/A"

        m_linka = re.search(r'<th>Linka</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_linka: linkospoj = m_linka.group(1).strip()
        m_spoj = re.search(r'<th>Spoj</th>\s*<td>(.*?)</td>', info_html, re.IGNORECASE | re.DOTALL)
        if m_spoj: spoj_num = m_spoj.group(1).strip()

        tables = re.findall(r'(<table[^>]*>.*?</table>)', tt_html, re.IGNORECASE | re.DOTALL)
        tt_table_only = "".join(tables) if tables else "<p style='color:#ef4444;text-align:center;padding:10px;'>Jízdní řád není momentálně k dispozici.</p>"

        custom_html = f"""
        <style>
            .ois-detail {{ background: #0f172a; color: white; font-family: sans-serif; padding: 15px; border-radius: 8px; }}
            .ois-header {{ color: #38bdf8; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 15px; padding-bottom: 10px; font-size: 18px; }}
            .ois-table-wrapper {{ margin-top: 10px; border: 1px solid #555; border-radius: 5px; overflow-x: auto; background: #2a2a2a; }}
            .ois-table-wrapper table {{ width: 100%; border-collapse: collapse; font-size: 13px; color: #f8fafc; margin-bottom: 0; }}
            .ois-table-wrapper th {{ background: #222; color: #38bdf8; text-align: left; padding: 10px; border-bottom: 2px solid #555; white-space: nowrap; }}
            .ois-table-wrapper td {{ padding: 10px; border-bottom: 1px solid #444; white-space: nowrap; }}
            .ois-table-wrapper tr:nth-child(even) td {{ background-color: #2a2a2a; }}
            .ois-table-wrapper tr:nth-child(odd) td {{ background-color: #333333; }}
            .ois-table-wrapper tr:hover td {{ background-color: #555555; transition: 0.2s; }}
        </style>
        <div class="ois-detail">
            <div class="ois-header"><i class="fas fa-bus"></i> Spoj: {linkospoj} / {spoj_num}</div>
            <div class="ois-table-wrapper">
                {tt_table_only}
            </div>
        </div>
        """
        return Response(custom_html, mimetype='text/html')
    except Exception as e:
        return f"<div style='color:#ef4444; padding:20px; background:#1a1a1a;'>Chyba při stahování JŘ z Inflow: {e}</div>"
