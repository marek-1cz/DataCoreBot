
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

// === NAV ===
const nav=document.getElementById('top-nav'),handle=document.getElementById('nav-handle');
let hideT=null;
function showNav(dur){clearTimeout(hideT);nav.classList.add('vis');handle.classList.add('hid');if(dur)hideT=setTimeout(hideNav,dur);}
function hideNav(){nav.classList.remove('vis');handle.classList.remove('hid');}
let navPinned=false;
function toggleNavPin(){
  navPinned=!navPinned;
  let btn=document.getElementById('nav-pin-btn');
  if(navPinned){btn.classList.add('pinned');showNav(0);}
  else{btn.classList.remove('pinned');hideT=setTimeout(hideNav,1500);}
}
handle.addEventListener('click',()=>showNav(5000));
document.addEventListener('mousemove',e=>{if(e.clientY<6)showNav();},{passive:true});
nav.addEventListener('mouseenter',()=>clearTimeout(hideT));
nav.addEventListener('mouseleave',()=>{if(!navPinned)hideT=setTimeout(hideNav,600);});
document.addEventListener('touchstart',e=>{if(e.touches[0].clientY<35){showNav(4500);}else if(!nav.contains(e.target)&&!navPinned){clearTimeout(hideT);hideT=setTimeout(hideNav,400);}},{passive:true});
showNav(4000);
// Smart pan handlers registered after map init below
if(IS_ADMIN){let ab=document.getElementById('admin-mode-badge');if(ab)ab.style.display='block';let ntb=document.getElementById('nt-toggle-btn');if(ntb)ntb.style.display='inline-block';let nab=document.getElementById('nt-add-btn');if(nab)nab.style.display='inline-block';let leb=document.getElementById('le-toggle-btn');if(leb)leb.style.display='inline-block';let lgb=document.getElementById('log-toggle-btn');if(lgb)lgb.style.display='inline-block';}

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
      showAdminToast(`✅ "${missingName}" → "${sourceName||'nová poloha'}"`,true);
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
  let tabIds=['all','err','spz','missing','report','approx'];
  tabIds.forEach(id=>{
    let body=document.getElementById(id==='all'?'log-body':id==='err'?'log-errors-body':id==='spz'?'log-spz-body':id==='missing'?'log-missing-body':id==='report'?'log-report-body':'log-approx-body');
    if(body)body.style.display=(tab===id?'':'none');
    let btn=document.getElementById(`log-tab-${id}`);
    if(btn){btn.style.background=(tab===id?'#334155':'transparent');btn.style.color='';}
  });
  if(tab==='err'){let b=document.getElementById('log-errors-body');b.innerHTML='';logErrEntries.forEach(e=>{let l=document.createElement('div');l.className='lg-err';l.textContent=`[${e.t}] ${e.msg}`;b.appendChild(l);});b.scrollTop=b.scrollHeight;}
  if(tab==='spz')renderSpzLog();
  if(tab==='missing')renderMissingLog();
  if(tab==='report')loadReportSituace();
  if(tab==='approx')renderApproxLog();
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
    if(!data.entries||!data.entries.length){body.innerHTML='<div style="color:#64748b;padding:6px;">Žádné záznamy</div>';return;}
    data.entries.forEach(e=>{
      let div=document.createElement('div');
      div.style.cssText='padding:5px 0;border-bottom:1px solid #1e293b;font-family:monospace;font-size:10px;';
      let clr=e.typ==='DUP_SPZ'?'#f87171':e.typ==='SPZ_RESET'?'#fbbf24':'#94a3b8';
      div.innerHTML=`<span style="color:${clr};font-weight:bold;">[${e.ts}] ${e.typ}</span><br><span style="color:#cbd5e1;">${e.zprava}</span>`;
      body.appendChild(div);
    });
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
function _hudShowRoute(){if(followId)toggleRoute(followId);}
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
function closeActiveRoute(){
  routeLayer.clearLayers();
  if(activeRouteId){let btn=document.getElementById('route-btn-'+activeRouteId);if(btn){btn.textContent='🗺️ Zobrazit trasu';btn.style.background='#334155';}}
  activeRouteId=null;
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
  let futColor=isBug||isFinished?'#a855f7':delay>300?'#ef4444':'#3b82f6';
  let pastColor=isBug||isFinished?'#6b7280':'#475569';
  let pts=data.stops.filter(s=>s.lat&&s.lng);
  let splitIdx=pts.findIndex(s=>!s.passed);
  if(splitIdx===-1)splitIdx=pts.length;
  let finalIdx=pts.length-1;
  let pastPts=pts.slice(0,Math.min(splitIdx+1,pts.length)).map(s=>[s.lat,s.lng]);
  let futurePts=pts.slice(splitIdx).map(s=>[s.lat,s.lng]);
  if(pastPts.length>=2)
    routeLayer.addLayer(L.polyline(pastPts,{color:isFinished?'#a855f7':pastColor,weight:5,opacity:0.55,dashArray:'5,5',className:'route-line-past'}));
  if(futurePts.length>=2){
    routeLayer.addLayer(L.polyline(futurePts,{color:futColor,weight:14,opacity:0.18,lineCap:'round',lineJoin:'round'}));
    let futPoly=L.polyline(futurePts,{color:futColor,weight:7,opacity:0.95,lineCap:'round',lineJoin:'round',className:isBug?'route-line-past':'route-line-future'});
    futPoly.on('add',function(){
      let el=this.getElement();
      if(!el)return;
      el.style.strokeDasharray='8000';el.style.strokeDashoffset='8000';
      el.style.transition='stroke-dashoffset 1.6s cubic-bezier(.4,0,.2,1)';
      setTimeout(()=>{el.style.strokeDashoffset='0';},30);
    });
    routeLayer.addLayer(futPoly);
  }
  pts.forEach((stop,i)=>{
    let isPast=stop.passed,isFinal=(i===finalIdx),isCurrent=(i===splitIdx&&splitIdx>0&&splitIdx<pts.length);
    let lowConf=stop.confidence==='fuzzy'||stop.confidence==='geocoded';
    let warnHtml='';
    if(stop.substitute)warnHtml='<br><span style="color:#a855f7;font-size:10px;">🔀 náhradní</span>';
    else if(stop.approx||lowConf)warnHtml='<br><span style="color:#f59e0b;font-size:10px;">⚠️ přibl.</span>';
    let icon;
    if(isFinal){
      let fc=isFinished?'#a855f7':futColor;
      icon=L.divIcon({className:'',iconSize:[24,24],iconAnchor:[12,12],html:'<div style="width:22px;height:22px;background:'+fc+';border:3px solid #fff;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:13px;box-shadow:0 0 12px '+fc+',0 2px 8px rgba(0,0,0,.8);">🏁</div>'});
    } else if(isCurrent){
      icon=L.divIcon({className:'',iconSize:[22,22],iconAnchor:[11,11],html:'<div style="width:18px;height:18px;border-radius:50%;background:'+futColor+';border:3px solid #fff;box-shadow:0 0 14px '+futColor+',0 2px 6px rgba(0,0,0,.6);animation:routePulse 1.1s ease-in-out infinite;"></div>'});
    } else if(isPast){
      icon=L.divIcon({className:'',iconSize:[8,8],iconAnchor:[4,4],html:'<div style="width:5px;height:5px;border-radius:50%;background:'+(isFinished?'#a855f7':'#4b5563')+';border:1px solid '+(isFinished?'#c084fc':'#6b7280')+';opacity:0.7;"></div>'});
    } else {
      let bd=lowConf?'2px dashed #f59e0b':'2px solid rgba(255,255,255,0.9)';
      icon=L.divIcon({className:'',iconSize:[14,14],iconAnchor:[7,7],html:'<div style="width:10px;height:10px;border-radius:50%;background:'+futColor+';border:'+bd+';box-shadow:0 0 6px '+futColor+',0 1px 4px rgba(0,0,0,.5);"></div>'});
    }
    let m=L.marker([stop.lat,stop.lng],{icon,zIndexOffset:isFinal?300:isCurrent?200:isPast?-200:-50});
    let timeStr=stop.time?' / <b>'+stop.time+'</b>':'';
    let typeLabel=isFinal?' — 🏁 <b>Konečná</b>':isCurrent?' ← <b>Zde</b>':'';
    m.bindTooltip('<span style="font-size:12px;">🚏 '+stopDisplayName(stop)+'</span>'+timeStr+typeLabel+warnHtml,{direction:'top',className:'dark-popup'});
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
}




// === LINKA EDITOR ===
let leLayer=null,leStops=[],leLineName='',leAddActive=false;
function leInit(){if(!leLayer)leLayer=L.layerGroup().addTo(map);}
function lineEditorOff(){if(leLayer)leLayer.clearLayers();leAddActive=false;document.body.classList.remove('nt-add-active');let b=document.getElementById('le-add-btn');if(b){b.style.background='#334155';b.style.color='#a855f7';}}
function toggleLineEditor(){leInit();let p=document.getElementById('line-editor-panel');if(!p)return;p.style.display=p.style.display==='block'?'none':'block';if(p.style.display==='none')lineEditorOff();}
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
    leLayer.addLayer(L.polyline(coords,{color:'#a855f7',weight:6,opacity:0.85,dashArray:'8,4',lineCap:'round'}));
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
  // Linky jsou uloženy průběžně přes addLineToNtStop/removeNtLine
  // saveNtFlags uloží jen zbývající metadata (approx/substitute/display_name)
  try{
    let res=await fetch('/api/admin/save_stop_override',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:s.name,lat:pos.lat,lng:pos.lng,approx,substitute,notfound,display_name,custom_lines:s.lines||null})});
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
      else if(mc==='bg-purple')dTxt='<span style="color:#a855f7;">Konečná</span>';
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
        // Trasa NEZNIKNE po zavření popupu
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
      if(mc==='bg-bug'){let bS=(bus.spz&&bus.spz!=='Neznama')?bus.spz:'Neznama SPZ';bugW=`<div style="background:#3f0000;border:2px solid #ef4444;border-radius:5px;padding:8px;margin:5px 0;font-size:11px;text-align:center;"><b style="color:#ef4444;font-size:13px;letter-spacing:.5px;">\u26d4 NEN\u00cd RE\u00c1LN\u00c1 POLOHA</b><br><span style="color:#fca5a5;font-weight:bold;">PRAVD\u011aPODOBN\u011a BUG NEBO POSLEDN\u00cd ZN\u00c1M\u00c1 POZICE</span><br><span style="color:#94a3b8;font-size:10px;">Pravd\u011bpodobn\u011b SPZ <b style="color:#fbbf24;">${bS}</b> \u2013 pozice nemus\u00ed odpov\u00eddat realit\u011b</span></div>`;}
      let orangeW='';
      if(mc==='bg-orange')orangeW=`<div style="background:rgba(245,158,11,.15);border:1px solid #f59e0b;border-radius:5px;padding:7px;margin:5px 0;font-size:11px;text-align:center;color:#f59e0b;"><b>🔍 Vyzkum - bus byl zasekly, nyni jede</b></div>`;
      let sc='#10b981';
      if(mc==='bg-bug')sc='#6b7280';else if(mc==='bg-orange')sc='#f59e0b';
      else if(bus.status.includes('prilis'))sc='#94a3b8';else if(bus.status.includes('Stoji'))sc='#ef4444';
      else if(bus.status.includes('Konečná')||bus.status.includes('Ztrata'))sc='#a855f7';
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
              <button onclick="adminAction('mark_bug','${bus.id}')" style="background:#3f0000;color:#fca5a5;border:1px solid #ef4444;border-radius:5px;font-size:11px;cursor:pointer;padding:5px 10px;touch-action:manipulation;font-weight:bold;">⛔ Označit BUG</button>
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
