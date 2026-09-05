HTML_JIZDNI_RAD = """<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jizdni rad IDPK | OIS IDPK</title>
    <meta name="description" content="Vyhledejte jizdni rad linek IDPK z aktualnich GTFS dat.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0a0f1e; --bg2: #0f172a; --bg3: #1e293b;
            --blue: #38bdf8; --yellow: #f59e0b; --green: #22c55e;
            --red: #ef4444; --text: #e2e8f0; --muted: #94a3b8; --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }
        .header { background: linear-gradient(180deg,#0a0f1e,#0f172a); border-bottom: 1px solid var(--border); padding: 16px 24px; display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 100; }
        .header a { color: var(--muted); text-decoration: none; font-size: 14px; }
        .header a:hover { color: var(--blue); }
        .logo { color: var(--blue); font-weight: 700; font-size: 18px; text-shadow: 0 0 15px rgba(56,189,248,0.5); }
        .sep { color: var(--border); }
        .main { max-width: 1100px; margin: 0 auto; padding: 32px 20px; }
        .hero { text-align: center; margin-bottom: 40px; }
        .hero h1 { font-size: 2.4em; font-weight: 700; color: var(--blue); text-shadow: 0 0 20px rgba(56,189,248,0.4); margin-bottom: 10px; }
        .hero p { color: var(--muted); font-size: 1.05em; }
        .gtfs-bar { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 14px 20px; margin-bottom: 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
        .badge { background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.3); color: var(--blue); padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .search-box { background: var(--bg2); border: 1px solid var(--border); border-radius: 14px; padding: 24px; margin-bottom: 28px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
        .search-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
        .field { flex: 1; min-width: 160px; position: relative; }
        .field label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .field input { width: 100%; background: var(--bg3); border: 1px solid var(--border); color: var(--text); padding: 10px 14px; border-radius: 8px; font-size: 15px; font-family: inherit; transition: border-color 0.2s; }
        .field input:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(56,189,248,0.1); }
        .btn-search { background: linear-gradient(135deg,#0ea5e9,#38bdf8); color: #0a0f1e; font-weight: 700; border: none; padding: 11px 28px; border-radius: 8px; font-size: 15px; cursor: pointer; font-family: inherit; transition: transform 0.15s,box-shadow 0.15s; white-space: nowrap; }
        .btn-search:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(56,189,248,0.4); }
        .btn-search:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        #suggestions { background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; margin-top: 6px; max-height: 220px; overflow-y: auto; display: none; position: absolute; left: 0; right: 0; z-index: 50; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
        .sug-item { padding: 10px 14px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 14px; transition: background 0.15s; }
        .sug-item:hover { background: rgba(56,189,248,0.08); }
        .sug-badge { background: rgba(56,189,248,0.15); color: var(--blue); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .route-header { background: linear-gradient(135deg,var(--bg2),var(--bg3)); border: 1px solid var(--border); border-left: 4px solid var(--blue); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px; }
        .route-header h2 { color: var(--blue); font-size: 1.4em; margin-bottom: 6px; }
        .route-meta { color: var(--muted); font-size: 13px; display: flex; gap: 16px; flex-wrap: wrap; }
        .route-meta span { display: flex; align-items: center; gap: 5px; }
        .trips-title { color: var(--text); font-size: 1em; margin-bottom: 12px; font-weight: 600; }
        .trip-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-bottom: 12px; transition: border-color 0.2s; }
        .trip-card:hover { border-color: rgba(56,189,248,0.4); }
        .trip-hdr { padding: 12px 18px; display: flex; align-items: center; gap: 12px; cursor: pointer; user-select: none; background: var(--bg3); }
        .trip-hdr:hover { background: rgba(56,189,248,0.05); }
        .trip-num { background: var(--blue); color: #0a0f1e; font-weight: 700; padding: 3px 10px; border-radius: 6px; font-size: 13px; }
        .trip-time { font-size: 1.2em; font-weight: 600; color: var(--text); }
        .trip-dest { color: var(--muted); font-size: 14px; flex: 1; }
        .trip-toggle { color: var(--muted); font-size: 12px; margin-left: auto; transition: transform 0.2s; }
        .trip-card.open .trip-toggle { transform: rotate(180deg); }
        .stop-list { padding: 0 18px 14px; display: none; }
        .trip-card.open .stop-list { display: block; }
        .stop-row { display: flex; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(51,65,85,0.5); gap: 12px; font-size: 13px; }
        .stop-row:last-child { border-bottom: none; }
        .stop-time { color: var(--blue); font-weight: 600; min-width: 50px; }
        .stop-name { flex: 1; color: var(--text); }
        .stop-first { color: var(--green); font-weight: 600; }
        .stop-last { color: var(--yellow); font-weight: 600; }
        .stop-zone { background: rgba(148,163,184,0.1); color: var(--muted); padding: 1px 6px; border-radius: 4px; font-size: 11px; }
        .loading, .empty { text-align: center; padding: 60px 20px; color: var(--muted); }
        .loading i { font-size: 2em; margin-bottom: 10px; color: var(--blue); animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .empty i { font-size: 2.5em; margin-bottom: 14px; color: var(--border); }
        @media (max-width:600px) { .hero h1 { font-size: 1.6em; } .search-row { flex-direction: column; } .btn-search { width: 100%; } }
    </style>
</head>
<body>
<div class="header">
    <a href="/" class="logo"><i class="fas fa-bus-alt"></i> OIS IDPK</a>
    <span class="sep">/</span>
    <span style="color:var(--text)">Jizdni rad IDPK</span>
    <a href="/" style="margin-left:auto"><i class="fas fa-home"></i> Domu</a>
</div>

<div class="main">
    <div class="hero">
        <h1><i class="fas fa-table" style="font-size:0.8em"></i> Jizdni rad IDPK</h1>
        <p>Vyhledejte linky a spoje IDPK z aktualnich GTFS dat</p>
    </div>

    <div class="gtfs-bar" id="gtfsBar">
        <i class="fas fa-database" style="color:var(--blue)"></i>
        <span>Nacitam informace o datech...</span>
    </div>

    <div class="search-box">
        <div class="search-row">
            <div class="field" style="flex:2">
                <label><i class="fas fa-bus"></i> Cislo linky IDPK</label>
                <input type="text" id="lineInput" placeholder="napr. 400621, 490722..." autocomplete="off">
                <div id="suggestions"></div>
            </div>
            <div class="field" id="odkudField" style="flex:2; display:none">
                <label><i class="fas fa-map-marker-alt"></i> Odkud</label>
                <select id="odkudSelect" onchange="renderFilteredTrips()"><option value="">-- Všechny --</option></select>
            </div>
            <div class="field" id="kamField" style="flex:2; display:none">
                <label><i class="fas fa-map-marker-alt"></i> Kam</label>
                <select id="kamSelect" onchange="renderFilteredTrips()"><option value="">-- Všechny --</option></select>
            </div>
            <div class="field" style="flex:0 0 auto">
                <label>&nbsp;</label>
                <button class="btn-search" id="searchBtn" onclick="searchLine()">
                    <i class="fas fa-search"></i> Vyhledat
                </button>
            </div>
        </div>
        <div id="loadingStatus" style="margin-top:12px;font-size:13px;color:var(--muted);display:none">
            <i class="fas fa-spinner fa-spin"></i> Nacitam GTFS databazi... (muze trvat 10-30 sekund)
        </div>
    </div>

    <div id="results"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.js"></script>
<script>
const GH_API = 'https://api.github.com/repos/marek-1cz/DataCoreBot/releases/latest';
const RANGES = [[400621,405611],[430432,440649],[450411,475211],[490722,496711]];
let db = null, allRoutes = [], dbLoading = false, dbLoaded = false;
let currentTrips = []; 
let currentShortName = '';

fetch('/api/gtfs-info').then(r=>r.json()).then(d=>{
    const bar = document.getElementById('gtfsBar');
    if(d.error){bar.innerHTML='<i class="fas fa-exclamation-triangle" style="color:var(--yellow)"></i> Info o datech nedostupne';return;}
    bar.innerHTML = `<i class="fas fa-database" style="color:var(--blue)"></i><span class="badge">${d.version_tag||'?'}</span><span>Zastavek: <b style="color:var(--text)">${(d.stop_count||0).toLocaleString()}</b></span><span>Linek: <b style="color:var(--text)">${(d.route_count||0).toLocaleString()}</b></span><span>Spoju: <b style="color:var(--text)">${(d.trip_count||0).toLocaleString()}</b></span><span style="margin-left:auto;font-size:11px;color:var(--muted)">Automaticka aktualizace denne</span>`;
}).catch(()=>{});

const inp = document.getElementById('lineInput');
inp.addEventListener('input', onInput);
inp.addEventListener('keydown', e=>{ if(e.key==='Enter') searchLine(); });

function onInput(){
    const v = inp.value.trim();
    hideSug();
    if(!db||v.length<2) return;
    const m = allRoutes.filter(r=>r.s.includes(v)||r.l.toLowerCase().includes(v.toLowerCase())).slice(0,8);
    if(!m.length) return;
    const sug = document.getElementById('suggestions');
    sug.innerHTML = m.map(r=>`<div class="sug-item" onclick="sel('${r.s}')"><span class="sug-badge">${r.s}</span><span style="color:var(--muted);font-size:13px">${r.l}</span></div>`).join('');
    sug.style.display='block';
}
function hideSug(){ document.getElementById('suggestions').style.display='none'; }
document.addEventListener('click', e=>{ if(!e.target.closest('.field')) hideSug(); });
function sel(s){ inp.value=s; hideSug(); searchLine(); }

async function ensureDb(){
    if(dbLoaded) return true;
    if(dbLoading){
        await new Promise(r=>{ const i=setInterval(()=>{if(!dbLoading){clearInterval(i);r();}},200); });
        return dbLoaded;
    }
    dbLoading=true;
    document.getElementById('loadingStatus').style.display='block';
    document.getElementById('searchBtn').disabled=true;
    try{
        const resp = await fetch('/api/gtfs-db-url');
        if(!resp.ok) throw new Error('Chyba stahovani DB: '+resp.status);
        const buf = await resp.arrayBuffer();
        const SQL = await initSqlJs({locateFile:f=>`https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/${f}`});
        db = new SQL.Database(new Uint8Array(buf));
        const res = db.exec('SELECT route_short_name, route_long_name FROM routes');
        if(res.length){
            const seen=new Set();
            res[0].values.forEach(([s,l])=>{
                const n=parseInt(s);
                if(RANGES.some(([a,b])=>n>=a&&n<=b)&&!seen.has(s)){seen.add(s);allRoutes.push({s,l:l||''});}
            });
            allRoutes.sort((a,b)=>a.s.localeCompare(b.s));
        }
        dbLoaded=true;
    }catch(e){
        console.error(e);
        document.getElementById('results').innerHTML=`<div class="empty"><i class="fas fa-exclamation-circle" style="color:var(--red)"></i><br><b style="color:var(--red)">Chyba nacteni dat</b><p style="margin-top:8px">${e.message}</p></div>`;
        dbLoaded=false;
    }finally{
        dbLoading=false;
        document.getElementById('loadingStatus').style.display='none';
        document.getElementById('searchBtn').disabled=false;
    }
    return dbLoaded;
}

async function searchLine(){
    const v = inp.value.trim();
    if(!v) return;
    hideSug();
    const res = document.getElementById('results');
    res.innerHTML='<div class="loading"><i class="fas fa-spinner"></i><br>Nacitam...</div>';
    
    document.getElementById('odkudField').style.display = 'none';
    document.getElementById('kamField').style.display = 'none';
    
    const ok = await ensureDb();
    if(!ok) return;

    const eq = v.replace(/'/g,"''");
    let rows = db.exec(`SELECT route_id,route_short_name,route_long_name FROM routes WHERE route_short_name='${eq}' LIMIT 10`);
    let shortName = v;
    if(!rows.length||!rows[0].values.length){
        const part = db.exec(`SELECT route_id,route_short_name,route_long_name FROM routes WHERE route_short_name LIKE '%${eq}%' LIMIT 5`);
        if(!part.length||!part[0].values.length){
            res.innerHTML=`<div class="empty"><i class="fas fa-search"></i><br>Linka <b style="color:var(--yellow)">${v}</b> nebyla nalezena</div>`;
            return;
        }
        shortName=part[0].values[0][1];
    } else { shortName=rows[0].values[0][1]; }

    currentShortName = shortName;
    const sn=shortName.replace(/'/g,"''");
    const idRows=db.exec(`SELECT DISTINCT route_id FROM routes WHERE route_short_name='${sn}'`);
    if(!idRows.length){ res.innerHTML='<div class="empty"><i class="fas fa-ban"></i><br>Zadne vysledky</div>'; return; }
    const ids=idRows[0].values.map(r=>`'${r[0]}'`).join(',');
    
    const longRow=db.exec(`SELECT route_long_name FROM routes WHERE route_short_name='${sn}' LIMIT 1`);
    const longName=(longRow[0]&&longRow[0].values[0]&&longRow[0].values[0][0])||'';

    let validity='';
    try {
        const cal=db.exec(`SELECT MIN(start_date),MAX(end_date) FROM calendar c JOIN trips t ON c.service_id=t.service_id WHERE t.route_id IN (${ids})`);
        if(cal.length&&cal[0].values[0][0]){
            const fmt=d=>d?d.slice(6,8)+'.'+d.slice(4,6)+'.'+d.slice(0,4):'?';
            validity=fmt(cal[0].values[0][0])+' - '+fmt(cal[0].values[0][1]);
        }
    }catch(e){}

    const dt = new Date();
    const todayStr = dt.getFullYear() + String(dt.getMonth()+1).padStart(2,'0') + String(dt.getDate()).padStart(2,'0');
    const dowCols = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday'];
    const todayDowCol = dowCols[dt.getDay()];

    const query = `
        SELECT t.trip_id, t.trip_headsign, t.spoj_cislo, 
        (SELECT arrival_time FROM stop_times WHERE trip_id=t.trip_id AND arrival_time IS NOT NULL AND arrival_time != '' ORDER BY stop_sequence ASC LIMIT 1) as dep,
        (SELECT s.name FROM stop_times st JOIN stops s ON st.stop_id=s.stop_id WHERE st.trip_id=t.trip_id ORDER BY st.stop_sequence ASC LIMIT 1) as start_stop,
        (SELECT s.name FROM stop_times st JOIN stops s ON st.stop_id=s.stop_id WHERE st.trip_id=t.trip_id ORDER BY st.stop_sequence DESC LIMIT 1) as end_stop,
        cal.start_date, cal.end_date, cal.monday, cal.tuesday, cal.wednesday, cal.thursday, cal.friday, cal.saturday, cal.sunday,
        (
            (cal.start_date <= '${todayStr}' AND cal.end_date >= '${todayStr}' AND cal.${todayDowCol} = 1 
            AND t.service_id NOT IN (SELECT service_id FROM calendar_dates WHERE date='${todayStr}' AND exception_type=2))
            OR t.service_id IN (SELECT service_id FROM calendar_dates WHERE date='${todayStr}' AND exception_type=1)
        ) as is_running_today
        FROM trips t
        LEFT JOIN calendar cal ON t.service_id = cal.service_id
        WHERE t.route_id IN (${ids})
        ORDER BY dep
    `;
    
    let tripRows;
    try { tripRows = db.exec(query); } catch(e) { console.error(e); tripRows = []; }
    
    if(!tripRows.length||!tripRows[0].values.length){
        res.innerHTML=`<div class="empty"><i class="fas fa-calendar-times"></i><br>Zadne spoje pro linku <b style="color:var(--yellow)">${shortName}</b></div>`;
        return;
    }
    
    currentTrips = tripRows[0].values.map(r => ({
        tid: r[0],
        headsign: r[1],
        spoj: r[2],
        dep: r[3],
        startStop: r[4],
        endStop: r[5],
        startDate: r[6],
        endDate: r[7],
        dow: [r[8],r[9],r[10],r[11],r[12],r[13],r[14]],
        isRunningToday: r[15] == 1,
        longName: longName,
        validity: validity
    }));
    
    const starts = [...new Set(currentTrips.map(t=>t.startStop).filter(Boolean))].sort();
    const ends = [...new Set(currentTrips.map(t=>t.endStop).filter(Boolean))].sort();
    
    let odHtml = '<option value="">-- Všechny --</option>' + starts.map(s=>`<option value="${s.replace(/"/g,'&quot;')}">${s}</option>`).join('');
    let kamHtml = '<option value="">-- Všechny --</option>' + ends.map(s=>`<option value="${s.replace(/"/g,'&quot;')}">${s}</option>`).join('');
    
    document.getElementById('odkudSelect').innerHTML = odHtml;
    document.getElementById('kamSelect').innerHTML = kamHtml;
    document.getElementById('odkudField').style.display = 'block';
    document.getElementById('kamField').style.display = 'block';
    
    renderFilteredTrips();
}

function renderFilteredTrips() {
    const res = document.getElementById('results');
    const odVal = document.getElementById('odkudSelect').value;
    const kamVal = document.getElementById('kamSelect').value;
    
    let filtered = currentTrips;
    if (odVal) filtered = filtered.filter(t => t.startStop === odVal);
    if (kamVal) filtered = filtered.filter(t => t.endStop === kamVal);
    
    if(filtered.length === 0) {
        res.innerHTML = `<div class="empty"><i class="fas fa-filter"></i><br>Zadné spoje neodpovídají filtru</div>`;
        return;
    }
    
    const t0 = filtered[0];
    let html=`<div class="route-header"><h2><i class="fas fa-bus" style="font-size:0.85em"></i> Linka ${currentShortName}</h2><div class="route-meta"><span><i class="fas fa-route"></i> ${t0.longName||'Trasa nedostupna'}</span>${t0.validity?`<span><i class="fas fa-calendar-alt"></i> Platnost JR: ${t0.validity}</span>`:''}<span><i class="fas fa-list-ol"></i> Nalezenych spoju: ${filtered.length}</span></div></div><p class="trips-title">Spoje (${filtered.length})</p>`;
    
    const dt = new Date();
    const todayStr = dt.getFullYear() + String(dt.getMonth()+1).padStart(2,'0') + String(dt.getDate()).padStart(2,'0');

    filtered.forEach(t=>{
        const depStr = t.dep ? t.dep.substring(0,5) : '--:--';
        const sid = 't_' + String(t.tid).replace(/[^a-z0-9]/gi,'_');
        
        let hs = t.headsign;
        if (!hs || hs.trim() === '') hs = t.endStop || 'Neznámý cíl';
        
        let isInactive = false;
        let inactiveReason = "";
        let dowReason = "";
        
        if (t.startDate && t.endDate) {
            if (t.endDate < todayStr) { isInactive = true; inactiveReason = "❌ ZASTARALÝ SPOJ"; }
            else if (t.startDate > todayStr) { isInactive = true; inactiveReason = "📅 BUDOUCÍ SPOJ"; }
        }
        
        if (t.dow) {
            const [mo, tu, we, th, fr, sa, su] = t.dow;
            const isWork = (mo && tu && we && th && fr && !sa && !su);
            const isWkend = (!mo && !tu && !we && !th && !fr && sa && su);
            if (isWkend) dowReason = "JEDE POUZE O VÍKENDU";
            else if (!mo && !tu && !we && !th && !fr && !sa && su) dowReason = "JEDE POUZE V NEDĚLI";
            else if (!mo && !tu && !we && !th && !fr && sa && !su) dowReason = "JEDE POUZE V SOBOTU";
            else if (isWork) dowReason = "JEDE POUZE V PRACOVNÍ DNY";
        }
        
        let bgStyle = 'background:rgba(255,255,255,0.04); border-color:rgba(255,255,255,0.06);';
        let extraLabel = '';
        
        if (isInactive) {
            bgStyle = 'background:rgba(0,0,0,0.3); border-color:rgba(255,255,255,0.1); opacity:0.65; filter: grayscale(60%);';
            extraLabel = `<span style="background:rgba(255,255,255,0.15); color:white; font-size:9px; font-weight:bold; padding:2px 4px; border-radius:3px; margin-left:5px;">${inactiveReason || '⏳ SEZÓNNÍ'}</span>`;
        } else if (!t.isRunningToday) {
            if (dowReason) extraLabel = `<span style="background:rgba(255,255,255,0.1); color:#ccc; font-size:9px; font-weight:bold; padding:2px 4px; border-radius:3px; margin-left:5px;">ℹ️ ${dowReason}</span>`;
            else extraLabel = `<span style="background:rgba(255,255,255,0.1); color:#ccc; font-size:9px; font-weight:bold; padding:2px 4px; border-radius:3px; margin-left:5px;">ℹ️ NEJEDE DNES</span>`;
        }
        
        html+=`<div class="trip-card" id="card_${sid}" style="${bgStyle}">
            <div class="trip-hdr" onclick="toggleTrip('${String(t.tid).replace(/'/g,"\\'")}','${sid}')">
                <span class="trip-time">${depStr}</span>
                <span class="trip-num">spoj ${t.spoj||'?'}</span>
                <span class="trip-dest">${hs}</span>
                ${extraLabel}
                <i class="fas fa-chevron-down trip-toggle"></i>
            </div>
            <div class="stop-list" id="${sid}">
                <div style="color:var(--muted);font-size:13px;padding:10px 0"><i class="fas fa-spinner fa-spin"></i> Nacitam zastavky...</div>
            </div>
        </div>`;
    });
    res.innerHTML=html;
}

function toggleTrip(tripId, sid){
    const card = document.getElementById('card_'+sid);
    if(card.classList.contains('open')){ card.classList.remove('open'); return; }
    card.classList.add('open');
    const div = document.getElementById(sid);
    if(div.dataset.loaded) return;
    div.dataset.loaded = '1';
    try {
        const r = db.exec(`SELECT st.arrival_time, s.name, s.zone_id, st.pickup_type, st.drop_off_type FROM stop_times st JOIN stops s ON st.stop_id=s.stop_id WHERE st.trip_id='${tripId.replace(/'/g,"''")}' ORDER BY st.stop_sequence`);
        if(!r.length||!r[0].values.length){ div.innerHTML='<div style="color:var(--muted);font-size:13px;padding:10px 0">Zadne zastavky</div>'; return; }
        const stops = r[0].values;
        div.innerHTML = stops.map(([time,name,zone,pickup,dropoff], i) => {
            const t = time ? time.substring(0,5) : '--:--';
            const nc = i===0 ? 'stop-name stop-first' : i===stops.length-1 ? 'stop-name stop-last' : 'stop-name';
            
            let pIcon = '';
            if (pickup === '1' && dropoff === '1') {
                pIcon = '<span style="color:var(--muted);font-weight:bold;margin-right:6px;" title="Projizdi">|</span>';
            } else if (pickup === '2' || pickup === '3') {
                pIcon = '<span style="color:var(--yellow);font-weight:bold;margin-right:6px;" title="Na znameni">x</span>';
            } else if (pickup === '1') {
                pIcon = '<span style="color:var(--red);font-size:11px;margin-right:6px;" title="Pouze vystup">&#x1F6AB;</span>';
            }
            
            let cleanZone = zone ? zone.replace(/^P/i, '') : '';
            return `<div class="stop-row"><span class="stop-time">${t}</span><span class="${nc}">${pIcon}${name}</span>${cleanZone?`<span class="stop-zone">${cleanZone}</span>`:''}</div>`;
        }).join('');
    }catch(e){ div.innerHTML=`<div style="color:var(--red);font-size:13px;padding:10px 0">Chyba: ${e.message}</div>`; }
}
</script>
</body>
</html>"""
