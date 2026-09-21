import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Define the new HTML
new_html = '''    html = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
    <title>IDPK Mobilní Zrcadlo</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/morphdom@2.7.4/dist/morphdom-umd.min.js"></script>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background: #035689; height: 100dvh; width: 100vw; display: flex; justify-content: center; align-items: center; }
        #mirror-container { 
            width: 100vw; height: 100dvh; 
            display: flex; justify-content: center; align-items: flex-start;
            overflow: hidden; pointer-events: auto;
            transform-origin: top center;
        }
        
        /* Overrides to make PC UI fit mobile perfectly */
        #mirror-container .main-container { height: 100dvh !important; max-height: 100dvh !important; }
        
        .mobile-settings-btn {
            position: fixed; top: env(safe-area-inset-top, 10px); right: 15px;
            width: 32px; height: 32px; color: rgba(255,255,255,0.7);
            font-size: 24px; display: flex; justify-content: center;
            align-items: center; cursor: pointer; z-index: 999999;
            text-shadow: 0 0 5px rgba(0,0,0,0.8);
        }
        
        #mobile-settings-overlay {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(2, 25, 45, 0.93); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            z-index: 9999999; flex-direction: column; align-items: center; justify-content: center; padding: 30px 20px;
        }
        .mob-settings-title { color: white; font-size: 16px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 30px; text-align: center; font-family: sans-serif; }
        .mob-glass-btn {
            width: 100%; max-width: 300px; padding: 16px 20px; margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.15); border-radius: 14px;
            background: rgba(255,255,255,0.08); color: white; font-size: 15px;
            font-weight: 600; cursor: pointer; text-align: center; backdrop-filter: blur(4px); transition: background 0.2s; font-family: sans-serif;
            text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px;
        }
        .mob-glass-btn.red { border-color: rgba(231,76,60,0.5); background: rgba(231,76,60,0.15); }
        .mob-glass-btn.close { border-color: rgba(255,255,255,0.2); color: rgba(255,255,255,0.6); }
        
        #status-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(2, 25, 45, 0.95); z-index: 900000; display: flex;
            flex-direction: column; align-items: center; justify-content: center;
            color: white; font-family: 'Segoe UI', sans-serif; backdrop-filter: blur(10px);
        }
        .offline-icon-container { position: relative; width: 140px; height: 100px; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; }
        .offline-icon { font-size: 45px; color: rgba(255,255,255,0.3); position: absolute; }
        .icon-pc { left: 10px; }
        .icon-mobile { right: 10px; }
        .icon-bolt { color: #e74c3c; font-size: 35px; animation: pulseBolt 1.5s infinite; z-index: 2; }
        @keyframes pulseBolt {
            0% { transform: scale(1); opacity: 1; text-shadow: 0 0 10px #e74c3c; }
            50% { transform: scale(1.3); opacity: 0.5; text-shadow: 0 0 25px #e74c3c; }
            100% { transform: scale(1); opacity: 1; text-shadow: 0 0 10px #e74c3c; }
        }
        .status-title { font-size: 22px; font-weight: 800; margin: 0 0 10px 0; letter-spacing: 2px; }
        .status-desc { font-size: 14px; color: rgba(255,255,255,0.6); text-align: center; max-width: 280px; margin-bottom: 30px; line-height: 1.5; }
        .troubleshoot-btn {
            background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
            color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none;
            font-weight: 600; transition: all 0.2s; display: flex; align-items: center; gap: 8px;
        }
        .troubleshoot-btn:hover { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.4); }
    </style>
</head>
<body>
    <div id="status-overlay">
        <div class="offline-icon-container">
            <i class="fas fa-desktop offline-icon icon-pc"></i>
            <i class="fas fa-bolt icon-bolt"></i>
            <i class="fas fa-mobile-alt offline-icon icon-mobile"></i>
        </div>
        <h2 id="status-title" class="status-title">SPOJENÍ PŘERUŠENO</h2>
        <p id="status-desc" class="status-desc">Nepodařilo se připojit k PC. Zkontrolujte, zda je aplikace zapnutá a PC je připojen k internetu.</p>
        <a href="/mobilni-sdileni" class="troubleshoot-btn"><i class="fas fa-life-ring"></i> Řešení problémů</a>
    </div>
    
    <div class="mobile-settings-btn" onclick="openMobileSettings()">⚙</div>
    <div id="mirror-container"></div>
    
    <div id="mobile-settings-overlay">
        <div class="mob-settings-title">⚙ Nastavení Zrcadla</div>
        <a href="/mobilni-sdileni" class="mob-glass-btn">
            <i class="fas fa-book"></i> Návod a řešení problémů
        </a>
        <button type="button" class="mob-glass-btn red" onclick="disconnectAndClose()">
            <i class="fas fa-sign-out-alt"></i> Odpojit se od PC
        </button>
        <button type="button" class="mob-glass-btn close" onclick="closeMobileSettings()">
            Zavřít
        </button>
    </div>

    <script>
        // Auto scale to fit width if needed (e.g., iPhone SE is 320px wide)
        function scaleUI() {
            const container = document.getElementById('mirror-container');
            if (window.innerWidth < 380) {
                const scale = window.innerWidth / 380;
                container.style.transform = `scale(${scale})`;
            } else {
                container.style.transform = 'none';
            }
        }
        window.addEventListener('resize', scaleUI);
        scaleUI();

        function sendEval(codeStr) {
            fetch('/api/mirror/mobile_action/{{ session_id }}', { 
                method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ action: "eval", code: codeStr }) 
            }).catch(()=>{});
            if ("vibrate" in navigator) { navigator.vibrate(20); }
        }
        
        function sendInput(id, val) {
            fetch('/api/mirror/mobile_action/{{ session_id }}', { 
                method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ action: "input", id: id, value: val }) 
            }).catch(()=>{});
        }

        document.getElementById('mirror-container').addEventListener('click', function(e) {
            let btn = e.target.closest('[onclick]');
            if (btn) {
                let code = btn.getAttribute('onclick');
                if (code) {
                    e.preventDefault(); e.stopPropagation();
                    sendEval(code);
                }
            }
        }, true);
        
        document.getElementById('mirror-container').addEventListener('input', function(e) {
            let el = e.target;
            if (el.tagName === 'INPUT' && el.id) {
                sendInput(el.id, el.value);
            }
        });

        function openMobileSettings() { document.getElementById('mobile-settings-overlay').style.display = 'flex'; }
        function closeMobileSettings() { document.getElementById('mobile-settings-overlay').style.display = 'none'; }
        function disconnectAndClose() { closeMobileSettings(); window.location.href = '/mobilni-sdileni'; }
    </script>

    <script>
        const sessionId = '{{ session_id }}';
        function connectSSE() {
            const source = new EventSource('/api/mirror/mobile_state/' + sessionId);
            source.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const statusOverlay = document.getElementById('status-overlay');
                const container = document.getElementById('mirror-container');
                const sTitle = document.getElementById('status-title');
                const sDesc = document.getElementById('status-desc');
                
                if (data.status === 'offline') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'PC JE OFFLINE';
                    sDesc.textContent = 'Aplikace přestala odesílat data. Zkontrolujte, zda PC neusnulo.';
                } else if (data.status === 'online') {
                    statusOverlay.style.display = 'none';
                    if (data.state && data.state.dom) {
                        if (!window.lastDom || window.lastDom !== data.state.dom) {
                            window.lastDom = data.state.dom;
                            if (typeof morphdom !== 'undefined') {
                                let temp = document.createElement('div');
                                temp.id = 'mirror-container';
                                temp.innerHTML = data.state.dom;
                                morphdom(container, temp, {
                                    onBeforeElUpdated: function(fromEl, toEl) {
                                        if (fromEl.isEqualNode && fromEl.isEqualNode(toEl)) return false;
                                        return true;
                                    }
                                });
                            } else {
                                container.innerHTML = data.state.dom;
                            }
                            scaleUI(); // Re-apply scaling just in case
                        }
                    }
                }
            };
            source.onerror = function() {
                document.getElementById('status-overlay').style.display = 'flex';
                document.getElementById('status-title').textContent = 'CHYBA SPOJENÍ';
                document.getElementById('status-desc').textContent = 'Ztratili jsme spojení se serverem.';
            };
        }
        connectSSE();
    </script>
</body>
</html>
    """'''

# Regex to replace the html variable content in mirror_mobile_ui
pattern = re.compile(r'    html = """\n<!DOCTYPE html>.*?\n</html>\n    """', re.DOTALL)
if pattern.search(code):
    new_code = pattern.sub(new_html, code)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print("Mobile UI successfully updated!")
else:
    print("Could not find the HTML block to replace.")
