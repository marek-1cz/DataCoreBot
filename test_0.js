
window.swPreviewMap = null;
window.swPreviewLayer = null;
window.busMarkersMap = new Map();

const IS_ADMIN=__IS_ADMIN__;

// === GRAFIKA A PRŮVODCE ===
function updateGfxDesc(val, descEl) {
  let txt = "";
  if(val==1) txt="Nízké – Doporučeno pro slabší zařízení (např. běžné mobilní telefony)";
  else if(val==2) txt="Střední – Doporučeno pro méně výkonné počítače a výkonnější mobily";
  else if(val==3) txt="Vysoké – Doporučeno pro standardně výkonné počítače";
  else if(val==4) txt="Ultra – Doporučeno pro výkonné počítače";
  if(descEl) descEl.textContent = txt;
}

function selectSwTheme(type) {
  setBaseMap(type);
  document.querySelectorAll('[id^="sw-bm-"]').forEach(b => {
    b.style.borderColor = '#334155';
    b.style.color = '#cbd5e1';
    b.style.boxShadow = '0 4px 10px rgba(0,0,0,0.5)';
  });
  let activeBtn = document.getElementById('sw-bm-' + type);
  if(activeBtn) {
    activeBtn.style.borderColor = '#38bdf8';
    activeBtn.style.color = 'white';
    activeBtn.style.boxShadow = '0 4px 15px rgba(56,189,248,0.3)';
  }
  
  if (!window.swPreviewMap) return;
  if (window.swPreviewLayer) { window.swPreviewMap.removeLayer(window.swPreviewLayer); }
  
  let urls = {
    dark: 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png?api_key=68be98ba-5497-41e4-b14e-0aaa9649aafd',
    osm: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    transport_dark: 'https://{s}.tile.thunderforest.com/transport-dark/{z}/{x}/{y}.png?apikey=086ca59fb24640be82e5259e96c7a0cb',
    bw: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    satellite: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
  };
  if(urls[type]) {
    window.swPreviewLayer = L.tileLayer(urls[type]).addTo(window.swPreviewMap);
  }
}

let sliderAnimId = null;

function animateSliderTo(el, targetValue, descId) {
  if (sliderAnimId) { cancelAnimationFrame(sliderAnimId); sliderAnimId = null; }
  let startVal = parseFloat(el.value);
  let endVal = targetValue;
  let duration = 600; // 0.6 seconds
  let startTime = null;
  
  function step(timestamp) {
    if (!startTime) startTime = timestamp;
    let progress = (timestamp - startTime) / duration;
    if (progress > 1) progress = 1;
    let ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    let currentVal = startVal + (endVal - startVal) * ease;
    
    el.value = currentVal.toFixed(2);
    gfxSliderInput(el, descId, true);
    
    if (progress < 1) {
      sliderAnimId = requestAnimationFrame(step);
    } else {
      sliderAnimId = null;
      el.value = endVal;
      gfxSliderInput(el, descId, true);
      setGraphicsLevel(endVal);
    }
  }
  sliderAnimId = requestAnimationFrame(step);
}

function gfxSliderInput(el, descId, isAnim=false) {
  if (!isAnim && sliderAnimId) { cancelAnimationFrame(sliderAnimId); sliderAnimId = null; }
  let val = parseFloat(el.value);
  let rVal = Math.round(val);
  let pct = (val - 1) / 3 * 100;
  let c = "#38bdf8";
  if(rVal === 1) c = "#10b981";
  else if(rVal === 2) c = "#fbbf24";
  else if(rVal === 3) c = "#ef4444";
  else if(rVal === 4) c = "#a855f7";
  el.style.background = `linear-gradient(to right, ${c} ${pct}%, #334155 ${pct}%)`;
  updateGfxDesc(rVal, document.getElementById(descId));
}

function gfxSliderChange(el) {
  let rVal = Math.round(parseFloat(el.value));
  let descId = (el.id === 'sw-gfx-slider') ? 'sw-gfx-desc' : 'settings-gfx-desc';
  animateSliderTo(el, rVal, descId);
}

function setGraphicsLevel(level, isInit=false) {
  level = parseInt(level);
  localStorage.setItem('graphics_level', level);
  document.body.classList.remove('low-graphics', 'medium-graphics', 'high-graphics', 'ultra-graphics');
  
  if(level===1) document.body.classList.add('low-graphics');
  else if(level===2) document.body.classList.add('medium-graphics');
  else if(level===3) document.body.classList.add('high-graphics');
  else if(level===4) document.body.classList.add('ultra-graphics');
  
  let sld1 = document.getElementById('settings-gfx-slider');
  let sld2 = document.getElementById('sw-gfx-slider');
  if(sld1 && Math.round(parseFloat(sld1.value)) !== level) { sld1.value = level; gfxSliderInput(sld1, 'settings-gfx-desc'); }
  if(sld2 && Math.round(parseFloat(sld2.value)) !== level) { sld2.value = level; gfxSliderInput(sld2, 'sw-gfx-desc'); }
  
  updateGfxDesc(level, document.getElementById('settings-gfx-desc'));
  updateGfxDesc(level, document.getElementById('sw-gfx-desc'));

  if(window.map && window.busMarkersMap) {
    let needsCluster = (level === 1);
    let hasCluster = !!(window.ml && window.ml.refreshClusters);
    
    if (needsCluster !== hasCluster || isInit) {
      if(window.ml && map.hasLayer(window.ml)) map.removeLayer(window.ml);
      if (needsCluster) {
        window.ml = L.markerClusterGroup({ disableClusteringAtZoom: 16, maxClusterRadius: (window.innerWidth < 768) ? 45 : 35, spiderfyOnMaxZoom: true, showCoverageOnHover: false, zoomToBoundsOnClick: true });
      } else {
        window.ml = L.layerGroup();
      }
      window.ml.addTo(map);
      
      for (const marker of window.busMarkersMap.values()) {
        window.ml.addLayer(marker);
      }
      
      if(!isInit && typeof fetchBuses === 'function') fetchBuses();
    }
  }
}

function swNext(step) {
  document.querySelectorAll('.sw-step').forEach(e=>e.style.display='none');
  let s = document.getElementById('sw-step-'+step);
  if(s) s.style.display='block';
  
  if(step === 2) {
    if(!window.swPreviewMap) {
      window.swPreviewMap = L.map('sw-theme-preview', {
        zoomControl: false, dragging: false, scrollWheelZoom: false,
        doubleClickZoom: false, keyboard: false, touchZoom: false, attributionControl: false
      }).setView([49.7535, 13.3050], 14);
    }
    setTimeout(() => {
      window.swPreviewMap.invalidateSize();
      let current = window.currentBaseMap || 'osm';
      selectSwTheme(current);
    }, 150);
  }
}

function swFinish() {
  localStorage.setItem('setup_wizard_done', 'true');
  document.getElementById('setup-wizard-modal').style.display='none';
  let gfx = document.getElementById('sw-gfx-slider').value;
  setGraphicsLevel(gfx);
}

function startTutorial() {
  document.getElementById('setup-wizard-modal').style.display='none';
  let gfx = document.getElementById('sw-gfx-slider').value;
  setGraphicsLevel(gfx);
  document.getElementById('tutorial-overlay').style.display='block';
  tutNext(1);
}

function tutNext(step) {
  document.querySelectorAll('.tut-box').forEach(e => e.style.display='none');
  
  let nav = document.getElementById('top-nav');
  if (nav) { nav.style.zIndex = ''; nav.style.position = ''; nav.style.pointerEvents = ''; }
  let setBtn = document.getElementById('settings-btn-wrap');
  if (setBtn) { setBtn.style.zIndex = ''; setBtn.style.pointerEvents = ''; }
  let setPan = document.getElementById('settings-panel');
  if (setPan) { setPan.style.zIndex = ''; setPan.classList.remove('open'); setPan.style.display='none'; }

  let s = document.getElementById('tut-step-'+step);
  if(s) s.style.display='block';
  
  if (step === 2) {
    if (nav) {
      nav.style.zIndex = '10001';
      if (window.getComputedStyle(nav).position === 'static') nav.style.position = 'relative';
      nav.style.pointerEvents = 'none';
    }
  } else if (step === 3) {
    if (setBtn) { setBtn.style.zIndex = '10001'; setBtn.style.pointerEvents = 'none'; }
    if (setPan) {
      setPan.style.zIndex = '10001';
      setPan.style.display = 'block';
      setTimeout(() => setPan.classList.add('open'), 10);
    }
  }
}

function tutFinish() {
  localStorage.setItem('setup_wizard_done', 'true');
  document.getElementById('tutorial-overlay').style.display='none';
  tutNext(-1); // Cleanup highlights
}

// === ADMIN ===
let adminInputCache={};
function saveAdminInputs(){
  if(!IS_ADMIN)return;
  document.querySelectorAll('[id^="adm_spz_"]').forEach(el=>{if(el.value!==el.getAttribute('data-orig'))adminInputCache['spz_'+el.id.replace('adm_spz_','')]=el.value;});
  document.querySelectorAll('[id^="adm_st_"]').forEach(el=>{if(el.value!==el.getAttribute('data-orig'))adminInputCache['st_'+el.id.replace('adm_st_','')]=el.value;});
  document.querySelectorAll('[id^="adm_note_"]').forEach(el=>{adminInputCache['note_'+el.id.replace('adm_note_','')]=el.value;});
  document.querySelectorAll('[id^="adm_driver_"]').forEach(el=>{adminInputCache['driver_'+el.id.replace('adm_driver_','')]=el.value;});
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
  let st=document.getElementById('adm_st_'+id)?.value?.trim()||'',col=document.getElementById('adm_col_'+id)?.value?.trim()||'',note=document.getElementById('adm_note_'+id)?.value?.trim()||'',driver=document.getElementById('adm_driver_'+id)?.value?.trim()||'';
  if(!st&&!col&&!note&&!driver){showAdminToast('Nic k ulozeni',false);return;}
  adminAction('edit_all',id,{status:st,color_class:col,note,driver,permanent});
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
  satellite: L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',{maxZoom:21,attribution:'&copy; Google Maps'}),
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
var ml;
var routeLayer=L.layerGroup().addTo(map);
var ntLayer=L.layerGroup().addTo(map);
var pubStopsLayer=L.layerGroup().addTo(map);

// Inicializace grafiky a průvodce
let setupWizardDone = localStorage.getItem('setup_wizard_done');
let savedGfx = localStorage.getItem('graphics_level');

if (setupWizardDone !== 'true') {
  let sw = document.getElementById('setup-wizard-modal');
  if(sw) sw.style.display = 'flex';
  savedGfx = (window.innerWidth < 768 || /Mobi|Android/i.test(navigator.userAgent)) ? "1" : "3";
} else if (!savedGfx) {
  savedGfx = "3";
}

setGraphicsLevel(savedGfx, true);

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

// === NOTIFIKACE JS ===
let _notifCurrentBusId = null, _notifCurrentSpz = null;

window.openNotifModal = function(busId) {
  let bus = (typeof lastArr !== 'undefined') ? lastArr.find(b => b.id === busId) : null;
  if (!bus) { showMapToast('Autobus nenalezen.'); return; }
  
  let spz = bus.spz;
  let line = bus.line;
  let destination = bus.destination;

  _notifCurrentBusId = busId;
  _notifCurrentSpz = spz;
  let info = document.getElementById('notif-bus-info');
  if(info) info.innerHTML = `<b>Linka ${line}</b> → ${destination}${spz&&spz!=='Neznama'?' &nbsp;|&nbsp; SPZ: <b>'+spz+'</b>':''}`;
  // Předvyplň identifikátor
  let inp = document.getElementById('notif-identifier');
  if(inp) {
    if(spz && spz !== 'Neznama') {
      inp.value = spz;
      let r = document.getElementById('notif-type-spz'); if(r) r.checked = true;
    } else {
      inp.value = busId;
      let r = document.getElementById('notif-type-busid'); if(r) r.checked = true;
    }
  }
  document.getElementById('notif-modal').style.display = 'block';
  document.getElementById('notif-modal-msg').textContent = '';
  
  // Načti zastávky spoje
  fetch('/api/bus_route/' + busId).then(r=>r.json()).then(d=>{
    let sel = document.getElementById('nt-stop-route-select');
    if(sel && d.stops) {
      let opts = '<option value="">-- Vyber zastávku na trase --</option>';
      d.stops.filter(s => !s.passed).forEach(s => {
        opts += `<option value="${s.name}">${s.name}</option>`;
      });
      if (opts === '<option value="">-- Vyber zastávku na trase --</option>') {
         opts = '<option value="">Žádné budoucí zastávky (konečná?)</option>';
      }
      sel.innerHTML = opts;
    }
  }).catch(()=>{});
  
  // Zobraz zastávkové pole pokud zaškrtnuto
  let stopCb = document.getElementById('nt-stop-near');
  if(stopCb) stopCb.onchange = () => {
    let sn = document.getElementById('nt-stop-container');
    if(sn) sn.style.display = stopCb.checked ? 'block' : 'none';
  };
  
  // Autocomplete logika
  let stopInp = document.getElementById('nt-stop-name');
  let stopAc = document.getElementById('nt-stop-autocomplete');
  if (stopInp && stopAc) {
    let to = null;
    stopInp.oninput = () => {
      clearTimeout(to);
      let v = stopInp.value.trim();
      if (v.length < 2) { stopAc.style.display = 'none'; return; }
      to = setTimeout(async () => {
        try {
          let r = await fetch('/api/stops_search?q=' + encodeURIComponent(v));
          let d = await r.json();
          if (d.status === 'success' && d.results.length > 0) {
            stopAc.innerHTML = d.results.map(n => `<div style="padding:6px 10px;cursor:pointer;border-bottom:1px solid #334155;font-size:13px;color:#e2e8f0;" onmouseover="this.style.background='#334155'" onmouseout="this.style.background='transparent'" onmousedown="document.getElementById('nt-stop-name').value='${n.replace(/'/g, "\\'")}'; document.getElementById('nt-stop-autocomplete').style.display='none';">${n}</div>`).join('');
            stopAc.style.display = 'block';
          } else {
            stopAc.style.display = 'none';
          }
        } catch(e) {}
      }, 300);
    };
    stopInp.onblur = () => { setTimeout(() => { stopAc.style.display = 'none'; }, 200); };
  }
  // Načti info o doručení (discord/email) z API
  fetch('/api/notifications/delivery_info').then(r=>r.json()).then(d=>{
    let dd = document.getElementById('notif-delivery-discord');
    let de = document.getElementById('notif-delivery-email');
    let dn = document.getElementById('notif-delivery-none');
    
    let cbDiscord = document.getElementById('nt-deliv-discord');
    let cbEmail = document.getElementById('nt-deliv-email');
    
    if(dd) { 
      dd.style.display = d.has_discord ? 'flex' : 'none'; 
      if (!d.has_discord && cbDiscord) cbDiscord.checked = false;
    }
    if(de) { 
      de.style.display = d.has_email ? 'flex' : 'none'; 
      if (!d.has_email && cbEmail) cbEmail.checked = false;
    }
    if(dn) dn.style.display = (!d.has_discord && !d.has_email) ? 'inline-block' : 'none';
    let adm = document.getElementById('notif-admin-target-container');
    if(adm) adm.style.display = d.is_admin ? 'block' : 'none';
  }).catch(()=>{});
  // Načti vozovny do selectboxů
  fetch('/api/depot_zones').then(r=>r.json()).then(d=>{
    if(d.zones) {
      let opts = '<option value="all">Jakákoliv vozovna</option>';
      d.zones.forEach(z => { opts += `<option value="${z.name}">${z.name}</option>`; });
      document.querySelectorAll('.depot-dynamic-select').forEach(el => el.innerHTML = opts);
    }
  }).catch(e=>{});

  // Načti existující pravidla
  loadNotifRules();
};


window.closeNotifModal = function() {
  document.getElementById('notif-modal').style.display = 'none';
};

async function loadNotifRules() {
  try {
    let r = await fetch('/api/notifications/list');
    let d = await r.json();
    let sec = document.getElementById('notif-rules-section');
    let list = document.getElementById('notif-rules-list');
    if(!d.rules || !d.rules.length) { if(sec) sec.style.display='none'; return; }
    if(sec) sec.style.display = 'block';
    if(!list) return;
    list.innerHTML = '';
    d.rules.forEach(rule => {
      let row = document.createElement('div');
      row.style.cssText = 'background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;font-size:12px;';
      let fired = rule.fired_count || 0;
      let t_list = [];
      let t = rule.triggers || {};
      if(t.terminal) t_list.push("Konečná");
      if(t.new_line) t_list.push("Nová linka");
      if(t.depot_in) t_list.push("Do vozovny");
      if(t.depot_out) t_list.push("Z vozovny");
      if(t.trip_change) t_list.push("Změna spoje");
      if(t.started_moving) t_list.push("Rozjezd");
      if(t.stop_near) t_list.push("Zastávka");
      if(t.delay_threshold) t_list.push("Zpoždění > " + t.delay_threshold + " min");
      if(t.delay_change) t_list.push("Změna zpoždění");
      let t_str = t_list.join(", ") || "Žádné";

      row.innerHTML = `<div style="display:flex;flex-direction:column;gap:4px;">
        <span style="color:#e2e8f0;"><b>${rule.label||rule.identifier}</b> <span style="color:#64748b;">(${rule.identifier})</span> <span style="color:#38bdf8;margin-left:6px;">🔔 ${fired}x</span></span>
        <span style="color:#94a3b8;font-size:11px;">Události: ${t_str}</span>
        </div>
        <button onclick="deleteNotifRule('${rule.id}')" style="background:rgba(239,68,68,0.2);color:#ef4444;border:1px solid #ef4444;border-radius:5px;padding:3px 8px;font-size:11px;cursor:pointer;align-self:flex-start;">✕</button>`;
      list.appendChild(row);
    });
  } catch(e) {}
}

async function deleteNotifRule(ruleId) {
  try {
    let r = await fetch('/api/notifications/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: ruleId})});
    let d = await r.json();
    if(d.status==='success') loadNotifRules();
    else showNotifMsg('Chyba: ' + (d.message||'?'), false);
  } catch(e) { showNotifMsg('Chyba spojení', false); }
}

function showNotifMsg(msg, ok) {
  let el = document.getElementById('notif-modal-msg');
  if(!el) return;
  el.textContent = msg;
  el.style.color = ok ? '#10b981' : '#ef4444';
}

async function saveNotifRule(isOneTime = true) {
  let identifier = document.getElementById('notif-identifier').value.trim();
  let idType = document.querySelector('input[name="notif-id-type"]:checked')?.value || 'spz';
  let label = document.getElementById('notif-label').value.trim();
  let stopName = '';
  if (document.getElementById('nt-stop-near')?.checked) {
    let stopType = document.querySelector('input[name="nt_stop_type"]:checked')?.value;
    if (stopType === 'route') {
      stopName = document.getElementById('nt-stop-route-select')?.value.trim() || '';
    } else {
      stopName = document.getElementById('nt-stop-name')?.value.trim() || '';
    }
  }
  let triggers = {
    terminal: document.getElementById('nt-terminal')?.checked || false,
    new_line: document.getElementById('nt-new-line')?.checked || false,
    depot_in: document.getElementById('nt-depot-in')?.checked ? (document.getElementById('nt-depot-name-in')?.value || 'all') : false,
    depot_out: document.getElementById('nt-depot-out')?.checked ? (document.getElementById('nt-depot-name-out')?.value || 'all') : false,
    trip_change: document.getElementById('nt-trip-change')?.checked || false,
    started_moving: document.getElementById('nt-started-moving')?.checked || false,
    stop_near: stopName || '',
    delay_threshold: document.getElementById('nt-delay-thresh')?.checked ? parseInt(document.getElementById('nt-delay-val')?.value || '0') : false,
    delay_change: document.getElementById('nt-delay-change')?.checked || false,
  };
  let deliveryChannels = [];
  if (document.getElementById('nt-deliv-discord')?.checked) deliveryChannels.push('discord');
  if (document.getElementById('nt-deliv-email')?.checked) deliveryChannels.push('email');
  
  let targetUser = document.getElementById('notif-admin-target') ? document.getElementById('notif-admin-target').value.trim() : "";

  if(!identifier) { showNotifMsg('Zadej SPZ nebo Bus ID', false); return; }
  if(!Object.values(triggers).some(v => v && v !== '')) { showNotifMsg('Vyber alespoň jeden trigger', false); return; }
  if(deliveryChannels.length === 0) { showNotifMsg('Vyber alespoň jeden kanál pro doručení', false); return; }
  
  showNotifMsg('⏳ Ukládám...', true);
  try {
    let r = await fetch('/api/notifications/create', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({identifier, identifier_type: idType, triggers, label, delivery_channels: deliveryChannels, is_one_time: isOneTime, target_user: targetUser})});
    let d = await r.json();
    if(d.status==='success') {
      showNotifMsg(d.message || '✅ Pravidlo uloženo!', true);
      loadNotifRules();
      // Reset checkboxů
      ['nt-terminal','nt-new-line','nt-depot-in','nt-depot-out','nt-trip-change','nt-started-moving','nt-stop-near','nt-delay-thresh','nt-delay-change'].forEach(id => { let el=document.getElementById(id); if(el) el.checked=false; }); if(document.getElementById('nt-deliv-email')) document.getElementById('nt-deliv-email').disabled=false;
      let sn=document.getElementById('nt-stop-name'); if(sn) sn.value='';
      let sc=document.getElementById('nt-stop-container'); if(sc) sc.style.display='none';
      let tu=document.getElementById('notif-admin-target'); if(tu) tu.value='';
    } else {
      showNotifMsg('❌ ' + (d.message||'Chyba'), false);
    }
  } catch(e) { showNotifMsg('❌ Chyba spojení', false); }
}

// === SDÍLENÍ AUTOBUSU ===
window.shareBus = function(busId) {
  let trackUrl = location.origin + '/mapa?track=' + busId;
  let bus = (typeof lastArr !== 'undefined') ? lastArr.find(b => b.id === busId) : null;
  if (!bus) { showMapToast('Autobus nenalezen.'); return; }
  
  let now = new Date();
  let timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
  
  let delay = (typeof bus.delay !== 'undefined') ? bus.delay : '?';
  let stopName = (bus.status && bus.status.includes('(')) ? bus.status.split('(').pop().replace(')','') : bus.status;
  
  let real_spoj = bus.real_linka_spoj ? bus.real_linka_spoj.split('/').pop() : "Neznámý";
  let shareText = `Autobus: ${bus.spz !== 'Neznama' && bus.spz ? bus.spz : bus.id}\nLinka: ${bus.line}\nSpoj: ${real_spoj}\nMAP ID: ${bus.id}\nSměr: ${bus.destination}\nAktuální poloha blízko: ${stopName} v ${timeStr}\nZpoždění: ${delay} min\nSledovat na mapě: ${trackUrl}`;
  
  let modal = document.createElement('div');
  modal.style.position = 'fixed';
  modal.style.top = '0'; modal.style.left = '0'; modal.style.width = '100%'; modal.style.height = '100%';
  modal.style.background = 'rgba(0,0,0,0.7)';
  modal.style.display = 'flex'; modal.style.justifyContent = 'center'; modal.style.alignItems = 'center';
  modal.style.zIndex = '10001';
  modal.style.backdropFilter = 'blur(4px)';
  
  let box = document.createElement('div');
  box.style.background = '#1e293b'; box.style.padding = '20px'; box.style.borderRadius = '12px';
  box.style.width = '90%'; box.style.maxWidth = '360px'; box.style.color = '#fff';
  box.style.border = '1px solid #334155';
  box.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
  
  box.innerHTML = `
    <h3 style="margin-top:0;margin-bottom:15px;text-align:center;color:#38bdf8;">📤 Sdílet spoj</h3>
    <textarea id="share-ta" readonly style="width:100%;height:140px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:12px;font-size:13px;resize:none;margin-bottom:15px;box-sizing:border-box;outline:none;">${shareText}</textarea>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <button onclick="navigator.clipboard.writeText(document.getElementById('share-ta').value).then(()=>showMapToast('📋 Text zkopírován!'));this.parentElement.parentElement.parentElement.remove()" style="background:#0284c7;color:white;border:none;padding:12px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%;font-size:14px;box-shadow:0 4px 6px rgba(0,0,0,0.2);">📋 Zkopírovat text a odkaz</button>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:5px;">
        <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(trackUrl)}" target="_blank" style="flex:1;text-align:center;background:#1877f2;color:white;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">Facebook</a>
        <a href="fb-messenger://share/?link=${encodeURIComponent(trackUrl)}" target="_blank" style="flex:1;text-align:center;background:#00B2FF;color:white;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">Messenger</a>
        <a href="https://wa.me/?text=${encodeURIComponent(shareText)}" target="_blank" style="flex:1;text-align:center;background:#25D366;color:white;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">WhatsApp</a>
      </div>
      <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background:#475569;color:white;border:none;padding:10px;border-radius:8px;cursor:pointer;width:100%;margin-top:5px;font-size:13px;">Zavřít</button>
    </div>
  `;
  
  modal.appendChild(box);
  document.body.appendChild(modal);
};

function showMapToast(msg) {
  let t = document.getElementById('map-toast');
  if(!t) {
    t = document.createElement('div');
    t.id = 'map-toast';
    t.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:rgba(16,185,129,0.95);color:white;padding:10px 20px;border-radius:20px;font-size:13px;font-weight:bold;z-index:9999;pointer-events:none;transition:opacity 0.3s;';
    document.body.appendChild(t);
  }
  t.textContent = msg; t.style.opacity = '1';
  clearTimeout(t._to);
  t._to = setTimeout(() => { t.style.opacity = '0'; }, 3000);
}

// === URL TRACKING (?track=BUS_ID) ===
(function() {
  let trackId = new URLSearchParams(location.search).get('track');
  if(!trackId) return;
  window._pendingTrackId = String(trackId);
  // Pokus se otevřít popup při každém refreshi dat po načtení
  window._trackAttempts = 0;
})();

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
  if(!lines||!lines.length)wrap.innerHTML='<span style="color:#475469;font-size:10px;">Žádné linky (použije se GTFS)</span>';
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
          <h3 class="ph-t" style="${mc==='bg-bug'?'color:#9ca3af;':''}${mc==='bg-orange'?'color:#f59e0b;':''}; display:flex; justify-content:space-between; align-items:center;">
            <span>Linka ${bus.line}${afH}</span>
            <span style="font-size:10px; color:#64748b; font-weight:normal; letter-spacing:0.5px;">#${bus.id}</span>
          </h3>
        </div>
        <div class="pb">
          ${bugW}${orangeW}${depotW}
          ${(bus.admin_note && typeof bus.admin_note === 'string' && bus.admin_note.trim() !== '')?`<div style="background:rgba(147,197,253,0.1);border:1px solid #334155;border-radius:5px;padding:5px 8px;margin-bottom:5px;font-size:11px;color:#93c5fd;">${bus.admin_note}</div>`:''}
          ${(bus.admin_driver && typeof bus.admin_driver === 'string' && bus.admin_driver.trim() !== '')?`<div style="background:rgba(251,146,60,0.1);border:1px solid #ea580c;border-radius:5px;padding:5px 8px;margin-bottom:5px;font-size:11px;color:#fb923c;"><b>ŘIDIČ:</b> ${bus.admin_driver}</div>`:''}
          <div class="pr"><span class="pl">Cil:</span><span class="pv">${bus.destination||'Neznamy'}</span></div>
          ${spzH}${invTxt}
          <div class="pr"><span class="pl">Status:</span><span class="pv" style="color:${sc};">${bus.status}</span></div>
          <div class="pr" style="border:none;"><span class="pl">JR:</span><span class="pv">${dTxt}</span></div>
          <button class="pa" onclick="showTT('${bus.id}')">📋 Zobrazit jízdní řád</button>
          <button class="pa" style="${fSt}margin-top:5px;" onclick="toggleFollow('${bus.id}','${bus.id}')">${fTxt}</button>
          ${histBtn}
          <button id="route-btn-${bus.id}" class="pa pa-d" style="margin-top:5px;${rA?'background:#1e40af;':''}" onclick="toggleRoute('${bus.id}')">${rA?'🗺️ Skryt trasu':'🗺️ Zobrazit trasu'}</button>
          <div style="display:flex;gap:5px;margin-top:5px;">
            <button class="pa" style="flex:1;background:#7c3aed;color:#fff;border-color:#6d28d9;" onclick="openNotifModal('${bus.id}')">🔔 Notifikace</button>
            <button class="pa" style="flex:1;background:#0369a1;color:#fff;border-color:#075985;" onclick="shareBus('${bus.id}')">📤 Sdílet</button>
          </div>
        </div>`;


      if(IS_ADMIN){
        let oSpz=bus.spz==='Neznama'?'':bus.spz;
        let cSpz=restoreAdminInput(bus.id,'spz')??oSpz;
        let cSt=restoreAdminInput(bus.id,'st')??bus.status;
        let cNote=restoreAdminInput(bus.id,'note')??(bus.admin_note||'');
        let cDriver=restoreAdminInput(bus.id,'driver')??(bus.admin_driver||'');
        let cCol=bus.color_class||'';
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
              <button onclick="adminAction('force_refresh','${bus.id}')" style="flex:1;background:#7c3aed;color:#fff;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:bold;padding:9px;touch-action:manipulation;">🔄 T. Refresh</button>
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
              <input type="text" id="adm_driver_${bus.id}" value="${cDriver}" data-orig="${bus.admin_driver||''}" placeholder="Jméno řidiče..." class="adm-inp" style="margin-top:6px;">
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

    // URL ?track=BUS_ID: automaticky otevřít popup sledovaného autobusu
    if(window._pendingTrackId && window._trackAttempts < 15) {
      window._trackAttempts++;
      let tId = window._pendingTrackId;
      let tMarker = window.busMarkersMap && window.busMarkersMap.get(tId);
      if(!tMarker) {
        // Zkus najít podle SPZ
        let tBus = lastArr.find(b => String(b.id)===tId || b.spz===tId);
        if(tBus) tMarker = window.busMarkersMap.get(tBus.id);
      }
      if(tMarker) {
        window._pendingTrackId = null;
        let tBus2 = lastArr.find(b => window.busMarkersMap && window.busMarkersMap.get(b.id) === tMarker);
        if(tBus2) { map.setView([tBus2.lat, tBus2.lng], 16); }
        setTimeout(() => { try { tMarker.openPopup(); } catch(e){} }, 400);
      }
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
