import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update PC sync logic for lockout
old_pc = """        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = "rejected"
            MIRROR_STATES[session_id]["connection_requested"] = False"""

new_pc = """        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = "rejected"
            MIRROR_STATES[session_id]["connection_requested"] = False
            MIRROR_STATES[session_id]["lockout_until"] = time.time() + 60"""
code = code.replace(old_pc, new_pc)

# 2. Add request_connection endpoint
new_endpoint = """@app.route('/api/mirror/request_connection/<session_id>', methods=['POST'])
def mirror_request_connection(session_id):
    if session_id in MIRROR_STATES:
        s = MIRROR_STATES[session_id]
        if s.get("lockout_until", 0) > time.time():
            return jsonify({"status": "error", "message": "locked out"}), 429
        s["connection_requested"] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "session not found"}), 404
"""
if "/api/mirror/request_connection" not in code:
    code = code.replace("@app.route('/api/mirror/mobile_state", new_endpoint + "\n@app.route('/api/mirror/mobile_state")

# 3. Update SSE logic
old_sse = """                if time.time() - s["last_updated"] > 10:
                    yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
                else:
                    if s.get("approved") == "rejected":
                        yield f"data: {{\\"status\\": \\"rejected\\"}}\\n\\n"
                        time.sleep(1)
                        break
                        
                    if not s.get("connection_requested") and not s.get("approved"):
                        s["connection_requested"] = True
                        
                    if not s.get("approved"):
                        yield f"data: {{\\"status\\": \\"waiting_for_approval\\"}}\\n\\n"
                    elif s.get("approved") is True:"""

new_sse = """                if time.time() - s["last_updated"] > 10:
                    yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
                else:
                    if s.get("lockout_until", 0) > time.time():
                        remaining = int(s["lockout_until"] - time.time())
                        yield f"data: {{\\"status\\": \\"lockout\\", \\"remaining\\": {remaining}}}\\n\\n"
                    else:
                        if s.get("approved") == "rejected":
                            s["approved"] = False
                        
                        if not s.get("connection_requested") and not s.get("approved"):
                            yield f"data: {{\\"status\\": \\"request_needed\\"}}\\n\\n"
                        elif s.get("connection_requested") and not s.get("approved"):
                            yield f"data: {{\\"status\\": \\"waiting_for_approval\\"}}\\n\\n"
                        elif s.get("approved") is True:"""
code = code.replace(old_sse, new_sse)

# 4. Update mobile UI HTML inside mirror_mobile_ui
old_html_logic = """                } else if (data.status === 'rejected') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Nelze se připojit.';
                    source.close();
                } else if (data.status === 'waiting_for_approval') {"""

new_html_logic = """                } else if (data.status === 'request_needed') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'IDPK ZRCADLO';
                    sDesc.innerHTML = '<button onclick="requestConnection()" style="padding: 15px 30px; font-size: 18px; font-weight: bold; background: #22c55e; color: white; border: none; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 15px rgba(34,197,94,0.4); margin-top: 15px;">Zažádat o připojení</button>';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'lockout') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Další pokus za <b>' + data.remaining + '</b> sekund.';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'none';
                } else if (data.status === 'waiting_for_approval') {"""

if "request_needed" not in code:
    code = code.replace(old_html_logic, new_html_logic)
    
    script_to_add = """        function requestConnection() {
            let sDesc = document.getElementById('s-desc');
            sDesc.innerHTML = 'Odesílám žádost...';
            fetch('/api/mirror/request_connection/{{ session_id }}', {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if(data.status === 'error') {
                    sDesc.innerHTML = 'Chyba: ' + data.message;
                }
            })
            .catch(e => {
                sDesc.innerHTML = 'Chyba připojení';
            });
        }"""
    
    # insert the script before connectSSE
    code = code.replace("function connectSSE() {", script_to_add + "\n        function connectSSE() {")

    # update waiting for approval to show spinner again
    old_waiting = """                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ...';
                    sDesc.textContent = 'Potvrďte prosím připojení ve hře na PC.';
                } else if (data.status === 'online') {"""
    new_waiting = """                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ...';
                    sDesc.textContent = 'Potvrďte prosím připojení ve hře na PC.';
                    let sp = document.querySelector('.spinner');
                    if(sp) sp.style.display = 'block';
                } else if (data.status === 'online') {"""
    code = code.replace(old_waiting, new_waiting)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Backend main.py updated with request connection logic and lockout!")
