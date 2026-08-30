import re

def update_html():
    with open(r'..\IDPK-OIS-RC-EDITION-V1.6\web_ovladac.html', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("fetch('/press/' + action)", "fetch('/api/mirror/mobile_action/{{ session_id }}', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: action }) })")
    content = content.replace("SPOJENÍ S PC AKTIVNÍ", "PŘIPOJUJI SE...")
    content = content.replace("ODESÍLÁM STISKY · ŽIVÝ TEXT ZASTÁVEK NENÍ DOSTUPNÝ", "<div id='mobile-state-text'>Načítání zrcadla...</div>")

    js_script = """
    <script>
        const sessionId = '{{ session_id }}';
        function connectSSE() {
            const source = new EventSource('/api/mirror/mobile_state/' + sessionId);
            source.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const box = document.getElementById('status-box');
                const txt = document.getElementById('mobile-state-text');
                if (data.status === 'offline') {
                    box.style.borderColor = 'rgba(231,76,60,0.7)';
                    box.style.color = '#e74c3c';
                    box.textContent = 'PC JE OFFLINE';
                    if (txt) txt.innerHTML = 'Palubní počítač není připojen.';
                } else if (data.status === 'online') {
                    box.style.borderColor = 'rgba(4,142,86,0.8)';
                    box.style.color = '#2ecc71';
                    box.textContent = 'PC JE ONLINE';
                    if (txt && data.state) {
                        let info = '';
                        if (data.state.appState === 'LINKOSPOJ') {
                            info = 'VÝBĚR LINKY: ' + (data.state.displayLinkospoj || '---');
                        } else if (data.state.appState === 'IDPK_LINE') {
                            info = 'IDPK DATABÁZE';
                        } else if (data.state.appState === 'DRIVE') {
                            info = (data.state.header || '') + '<br>' + (data.state.currStop || '');
                        } else {
                            info = data.state.appState || 'Čekání na akci...';
                        }
                        txt.innerHTML = info;
                    }
                }
            };
            source.onerror = function() {
                const box = document.getElementById('status-box');
                box.style.borderColor = 'rgba(231,76,60,0.7)';
                box.style.color = '#e74c3c';
                box.textContent = 'SPOJENÍ ZTRACENO';
            };
        }
        connectSSE();
    </script>
</body>
"""
    content = content.replace("</body>", js_script)

    with open('main.py', 'r', encoding='utf-8') as f:
        py_content = f.read()

    new_html = '    html = """\\n' + content + '\\n    """'
    py_content = re.sub(r'    html = """(.*?)    """', new_html, py_content, flags=re.DOTALL)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(py_content)

if __name__ == "__main__":
    update_html()
    print("Done")
