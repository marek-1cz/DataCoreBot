HTML_LED_PANEL_VIEW = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>LED Panel — Náhled</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
#wrap{width:100%;padding:12px}
canvas#cv{display:block;width:100%;height:auto;image-rendering:pixelated;background:#020202;border-radius:4px}
</style>
</head>
<body>
<div id="wrap"><canvas id="cv"></canvas></div>
<script>
var FONT={};
var SMAP={};
for(var i=0;i<10;i++){var k=String.fromCharCode(0xE000+i);SMAP[String(i)]=k;}

function loadFont(){
  try{var cf=localStorage.getItem('buse_custom_font');
    if(cf){var d=JSON.parse(cf);Object.keys(d).forEach(function(k){if(Array.isArray(d[k]))FONT[k]=d[k];});}}
  catch(e){}
}

function loadS(){try{return JSON.parse(localStorage.getItem('buse_data')||'{}');}catch(e){return {};}}

var COLS=160,CELL=10,H1=19,FH=13,H2=13,GAP=1,SH=16;
var cv=document.getElementById('cv'),ctx=cv.getContext('2d'),fb;

function sp(x,y,v,tot){if(x>=0&&x<COLS&&y>=0&&y<tot)fb[y*COLS+x]=v;}
function mW(t){var w=0;for(var i=0;i<t.length;i++){var g=FONT[t[i]];w+=(g?g[0].length:4)+1;}return w>0?w-1:0;}
function mH(t){var h=0;for(var i=0;i<t.length;i++){var g=FONT[t[i]];if(g&&g.length>h)h=g.length;}return h||13;}
function norm(t){var o='';for(var i=0;i<t.length;i++){var c=t[i];if(FONT[c]!==undefined)o+=c;}return o;}

function drawNum(str,pm,tot,MNW){
  if(!str||!str.trim())return 0;
  if(pm==='side'){var tmp='';for(var i=0;i<str.length;i++){var c=str[i];tmp+=SMAP[c]||c;}str=tmp;}
  var vrH=(pm==='front'?FH:tot);var nh=mH(str),tw=mW(str),sc=Math.min(vrH/nh,MNW/Math.max(1,tw)),x=1;
  for(var i=0;i<str.length;i++){
    var c=str[i],g=FONT[c];if(!g){x+=Math.round(4*sc)+1;continue;}
    var nw=g[0].length,sw=Math.max(1,Math.round(nw*sc)),sh=Math.max(1,Math.round(nh*sc));
    var textMid=tot-6.5,yo=Math.max(0,Math.round(textMid-sh/2));
    for(var dy=0;dy<sh;dy++){
      if(yo+dy>=tot)break;
      var srcY=Math.min(g.length-1,Math.floor((dy+.5)/sc)),srcRow=g[srcY]||'';
      for(var dx=0;dx<sw;dx++){var srcX=Math.min(nw-1,Math.floor((dx+.5)/sc));sp(x+dx,yo+dy,srcRow[srcX]==='1'?1:0,tot);}
    }
    x+=sw+Math.max(1,Math.round(sc));
  }
  return Math.min(COLS-20,x+3);
}

function drawZone(text,le,yZ,zH,tot,center){
  var av=COLS-le-1,tw=mW(text),x=le+1+(center&&tw<av?Math.floor((av-tw)/2):0);
  for(var i=0;i<text.length;i++){
    var c=text[i],g=FONT[c];if(!g){x+=5;continue;}
    var gw=g[0].length,gh=g.length,yo=zH-gh;
    for(var r=0;r<gh;r++){var row=g[r];for(var col=0;col<gw;col++)sp(x+col,yZ+yo+r,row[col]==='1'?1:0,tot);}
    x+=gw+1;
  }
}

function renderFrame(tot){
  ctx.fillStyle='#020202';ctx.fillRect(0,0,cv.width,cv.height);
  for(var y=0;y<tot;y++)for(var x=0;x<COLS;x++){
    var on=fb[y*COLS+x],px=x*CELL+CELL*.5,py=y*CELL+CELL*.5;
    ctx.beginPath();ctx.arc(px,py,CELL*.37,0,Math.PI*2);
    if(on){ctx.fillStyle='#ff8800';ctx.shadowColor='#ff3300';ctx.shadowBlur=CELL*.85;}
    else{ctx.fillStyle='#130900';ctx.shadowBlur=0;}
    ctx.fill();
  }
  ctx.shadowBlur=0;
}

// VIA animation state
var viaState={phase:'header',idx:0,off:0,max:0,t:0,stops:[]};
var PAUSE=500,RESUME=2500,VIA_HDR=5000,VIA_MIN=2000,PX_MS=0.055;

function viaScrollMax(t,le){return Math.max(0,mW(t)-(COLS-le-1));}

function tickVIA(ts,le,tot){
  var stops=viaState.stops;if(!stops.length)return false;
  if(!viaState.t)viaState.t=ts;
  var el=ts-viaState.t;
  if(viaState.phase==='header'){
    drawZone(norm('Přes zastávky:'),le,SH+GAP,H2,tot,false);
    if(el>=VIA_HDR){viaState.idx=0;viaState.off=0;viaState.max=viaScrollMax(stops[0],le);viaState.phase='stop-s';viaState.t=ts;}
    return true;
  }
  if(viaState.phase==='stop-s'){
    // clear row2
    for(var y=SH+GAP;y<tot;y++)for(var x=le;x<COLS;x++)sp(x,y,0,tot);
    drawZone(norm(stops[viaState.idx]),le,SH+GAP,H2,tot,true);
    if(el>=PAUSE){viaState.phase=viaState.max>0?'stop-sc':'stop-e';viaState.t=ts;}
    return false;
  }
  if(viaState.phase==='stop-sc'){
    var no=Math.min(viaState.max,Math.floor(el*PX_MS));
    if(no!==viaState.off){
      viaState.off=no;
      for(var y=SH+GAP;y<tot;y++)for(var x=le;x<COLS;x++)sp(x,y,0,tot);
      // scroll
      var t2=stops[viaState.idx],av2=COLS-le-1,tw2=mW(t2);
      var x2=le+1-no;
      for(var i=0;i<t2.length;i++){
        var c=t2[i],g=FONT[c];if(!g){x2+=5;continue;}
        var gw=g[0].length,gh=g.length,yo=H2-gh;
        for(var r=0;r<gh;r++){var row=g[r];for(var col=0;col<gw;col++){var fx=x2+col;if(fx>=le+1&&fx<COLS)sp(fx,SH+GAP+yo+r,row[col]==='1'?1:0,tot);}}
        x2+=gw+1;
      }
    }
    if(no>=viaState.max){viaState.phase='stop-e';viaState.t=ts;}
    return true;
  }
  if(viaState.phase==='stop-e'){
    if(el>=Math.max(VIA_MIN,PAUSE)){
      viaState.idx++;
      if(viaState.idx>=stops.length){viaState.phase='header';viaState.t=ts;}
      else{viaState.max=viaScrollMax(stops[viaState.idx],le);viaState.off=0;viaState.phase='stop-s';viaState.t=ts;}
    }
    return false;
  }
  return false;
}

var lastKey='',animId=null;

function fullRender(ts){
  loadFont();
  var S=loadS();
  var pm=S.pm||'front';
  var via=S.via&&pm==='side';
  var tot=pm==='side'?SH+GAP+H2:FH;
  var key=JSON.stringify({pm,ln:S.lineNum,r1:S.row1,r2:S.row2,via,stops:S.viaStops});

  if(key!==lastKey){
    lastKey=key;
    cv.width=COLS*CELL;cv.height=tot*CELL;
    fb=new Uint8Array(COLS*tot);
    var le=drawNum(norm((S.lineNum||'').toUpperCase()),pm,tot,32);
    drawZone(norm(S.row1||''),le,0,pm==='side'?SH:H1,tot,true);
    if(pm==='side'&&!via) drawZone(norm(S.row2||''),le,SH+GAP,H2,tot,true);
    if(via){
      viaState.stops=(S.viaStops||[]).map(function(s){return norm(s);}).filter(function(s){return s.trim();});
      viaState.phase='header';viaState.idx=0;viaState.off=0;viaState.t=0;
      drawZone(norm('Přes zastávky:'),le,SH+GAP,H2,tot,false);
    }
    renderFrame(tot);
    window._le=le;window._pm=pm;window._tot=tot;window._via=via;
  } else if(via){
    var dirty=tickVIA(ts,window._le||0,tot);
    if(dirty)renderFrame(tot);
  }
  animId=requestAnimationFrame(fullRender);
}

// Sync from main window
window.addEventListener('storage',function(e){
  if(e.key==='buse_data'||e.key==='buse_custom_font'){lastKey='';}
});

requestAnimationFrame(fullRender);
</script>
</body>
</html>
"""
