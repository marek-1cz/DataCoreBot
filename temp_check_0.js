
let allData=[];
function buildFreqMap(data){const f={};data.forEach(r=>{const spz=r.spz||'Neznama';if(spz==='Neznama')return;const lb=String(r.linka||'').replace(/\\/.*/g,'').trim().replace(/[^0-9]/g,'');f[spz+'_'+lb]=(f[spz+'_'+lb]||0)+1;});return f;}
function renderStats(data){
  const ss=new Set(data.filter(r=>r.spz&&r.spz!=='Neznama').map(r=>r.spz));
  const total=data.length,active=data.filter(r=>!r.end_actual&&!r.status?.includes('Timeout')&&!r.status?.includes('depu')).length,depot=data.filter(r=>r.status?.includes('depu')||r.status?.includes('Vozovn')).length;
  document.getElementById('statsBar').innerHTML=`
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#38bdf8;font-size:22px;font-weight:900;">${total}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📋 Zaznamu</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#f59e0b;font-size:22px;font-weight:900;">${ss.size}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🚌 Unikatnich SPZ</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#10b981;font-size:22px;font-weight:900;">${active}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">📡 Probiha</div></div>
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:130px;text-align:center;"><div style="color:#64748b;font-size:22px;font-weight:900;">${depot}</div><div style="color:#64748b;font-size:11px;text-transform:uppercase;">🏢 V garáži</div></div>`;
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
      const lb=String(linka).replace(/\\/.*/,'').trim().replace(/[^0-9]/g,'');
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
        <td style="padding:11px 14px;vertical-align:middle;font-size:13px;">${dayStr}<br><span style="color:#475569;font-size:10px;">${String(row.trip_id||'').substring(0,10)}...</span></td>
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
