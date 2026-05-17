HTML_LED_PANEL_VIEW = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>LED Panel — Náhled</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
#wrap{width:100%;max-width:1400px;padding:20px}
canvas#cv{display:block;width:100%;height:auto;image-rendering:pixelated;background:#020202;border-radius:6px}
#info{position:fixed;top:10px;right:12px;font-family:monospace;font-size:11px;color:#333}
</style>
</head>
<body>
<div id="wrap"><canvas id="cv"></canvas></div>
<div id="info">🔴 live</div>
<script>
// ── Minimal rendering engine — mirrors led_panel_html.js ──
var FONT={};
var SMAP={};
for(var i=0;i<10;i++){var k=String.fromCharCode(0xE000+i);SMAP[String(i)]=k;}

function loadFont(){
  try{
    var cf=localStorage.getItem('buse_custom_font');
    if(cf){var d=JSON.parse(cf);Object.keys(d).forEach(function(k){if(Array.isArray(d[k]))FONT[k]=d[k];});}
  }catch(e){}
}

function loadSettings(){
  try{return JSON.parse(localStorage.getItem('buse_data')||'{}');}
  catch(e){return {};}
}

var COLS=160,CELL=10,H1=19,H2=13,GAP=1;
var cv=document.getElementById('cv'),ctx=cv.getContext('2d'),fb;

function setpx(x,y,v,tot){if(x>=0&&x<COLS&&y>=0&&y<tot)fb[y*COLS+x]=v;}
function mW(t){var w=0;for(var i=0;i<t.length;i++){var g=FONT[t[i]];w+=(g?g[0].length:4)+1;}return w>0?w-1:0;}
function mH2(t){var h=0;for(var i=0;i<t.length;i++){var g=FONT[t[i]];if(g&&g.length>h)h=g.length;}return h||13;}
function norm(t){var o='';for(var i=0;i<t.length;i++){var c=t[i];if(FONT[c]!==undefined)o+=c;}return o;}

function render(){
  loadFont();
  var S=loadSettings();
  var pm=S.pm||'front';
  var tot=pm==='side'?H1+GAP+H2:H1;
  cv.width=COLS*CELL; cv.height=tot*CELL;
  fb=new Uint8Array(COLS*tot);

  var ln=norm((S.lineNum||'').toUpperCase());
  if(pm==='side'){var tmp='';for(var i=0;i<ln.length;i++){var c=ln[i];tmp+=SMAP[c]||c;}ln=tmp;}

  var le=0;
  if(ln){
    var nh=mH2(ln),tw=mW(ln),sc=Math.min(tot/nh,28/Math.max(1,tw)),x=1;
    for(var i=0;i<ln.length;i++){
      var c=ln[i],g=FONT[c];if(!g){x+=4;continue;}
      var nw=g[0].length,sw=Math.max(1,Math.round(nw*sc)),sh=Math.max(1,Math.round(nh*sc)),yo=tot-sh;
      for(var dy=0;dy<sh;dy++){
        var sy=Math.min(g.length-1,Math.floor((dy+.5)/sc)),sr=g[sy]||'';
        for(var dx=0;dx<sw;dx++){var sx=Math.min(nw-1,Math.floor((dx+.5)/sc));setpx(x+dx,yo+dy,sr[sx]==='1'?1:0,tot);}
      }
      x+=sw+Math.max(1,Math.round(sc));
    }
    le=Math.min(COLS-20,x+3);
  }

  function zone(text,yZ,zH){
    var av=COLS-le-1,tw=mW(text),x=le+1+(tw<av?Math.floor((av-tw)/2):0);
    for(var i=0;i<text.length;i++){
      var c=text[i],g=FONT[c];if(!g){x+=5;continue;}
      var gw=g[0].length,gh=g.length,yo=zH-gh;
      for(var r=0;r<gh;r++){var row=g[r];for(var col=0;col<gw;col++)setpx(x+col,yZ+yo+r,row[col]==='1'?1:0,tot);}
      x+=gw+1;
    }
  }
  zone(norm(S.row1||''),0,H1);
  if(pm==='side')zone(norm(S.row2||''),H1+GAP,H2);

  ctx.fillStyle='#020202';ctx.fillRect(0,0,cv.width,cv.height);
  for(var y=0;y<tot;y++)for(var x=0;x<COLS;x++){
    var on=fb[y*COLS+x],px2=x*CELL+CELL*.5,py2=y*CELL+CELL*.5;
    ctx.beginPath();ctx.arc(px2,py2,CELL*.37,0,Math.PI*2);
    if(on){ctx.fillStyle='#ff8800';ctx.shadowColor='#ff3300';ctx.shadowBlur=CELL*.85;}
    else{ctx.fillStyle='#130900';ctx.shadowBlur=0;}
    ctx.fill();
  }
  ctx.shadowBlur=0;

  // blink info dot
  var d=document.getElementById('info');
  d.style.color=d.style.color==='#4ade80'?'#333':'#4ade80';
}

// Initial render + font load
render();

// Live update on any localStorage change (from main simulator window)
window.addEventListener('storage',function(e){
  if(e.key==='buse_data'||e.key==='buse_custom_font') render();
});

// Also poll every 1s as fallback (same-window updates don't fire storage event)
setInterval(render,1000);
</script>
</body>
</html>
"""
