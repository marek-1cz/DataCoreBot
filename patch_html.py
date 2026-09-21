with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_html = """                } else if (data.status === 'rejected') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Nelze se připojit.';
                    source.close();
                } else if (data.status === 'waiting_for_approval') {"""

new_html = """                } else if (data.status === 'request_needed') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'IDPK ZRCADLO';
                    sDesc.innerHTML = '<button onclick="requestConnection()" style="padding: 15px 30px; font-size: 18px; font-weight: bold; background: #22c55e; color: white; border: none; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 15px rgba(34,197,94,0.4); margin-top: 15px;">Zažádat o připojení</button>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'lockout') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Další pokus za <b style="font-size:24px;">' + data.remaining + '</b> sekund.';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'rejected') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Nelze se připojit.';
                    source.close();
                } else if (data.status === 'waiting_for_approval') {"""
code = code.replace(old_html, new_html)

old_script = """    <script>
        const sessionId = '{{ session_id }}';
        function connectSSE() {"""

new_script = """    <script>
        const sessionId = '{{ session_id }}';
        
        function requestConnection() {
            const sDesc = document.getElementById('status-desc');
            sDesc.innerHTML = 'Odesílám žádost...';
            fetch('/api/mirror/request_connection/{{ session_id }}', {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if(data.status === 'error') {
                    sDesc.innerHTML = 'Chyba: ' + data.message;
                }
            })
            .catch(e => {
                sDesc.innerHTML = 'Chyba připojení k serveru.';
            });
        }
        
        function connectSSE() {"""
code = code.replace(old_script, new_script)

# And fix waiting_for_approval to show spinner again if hidden by lockout/request
old_waiting = """                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ';
                    sDesc.innerHTML = 'Potvrďte prosím na vašem PC žádost o připojení ke sdílení.<br><br><i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #F4CC17;"></i>';
                } else if (data.status === 'online') {"""

new_waiting = """                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ';
                    sDesc.innerHTML = 'Potvrďte prosím na vašem PC žádost o připojení ke sdílení.<br><br><i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #F4CC17;"></i>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'block';
                } else if (data.status === 'online') {"""
code = code.replace(old_waiting, new_waiting)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Backend main.py updated with actual HTML logic!")
