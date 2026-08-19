
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
loadDetail();setInterval(loadDetail,10000);
