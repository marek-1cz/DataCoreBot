import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update mirror_pc_sync
old_pc_sync = """    # Aktualizace stavu
    if session_id not in MIRROR_STATES:
        MIRROR_STATES[session_id] = {"pending_actions": []}
        
    MIRROR_STATES[session_id]["last_updated"] = time.time()
    MIRROR_STATES[session_id]["state"] = data.get('state', {})
    
    # Vrácení a vyčištění akcí, co byly stisknuty na mobilu
    actions = MIRROR_STATES[session_id]["pending_actions"].copy()
    MIRROR_STATES[session_id]["pending_actions"].clear()
    
    # Čištění starých session (starší 2 minuty)
    now = time.time()
    to_delete = [sid for sid, s in MIRROR_STATES.items() if now - s["last_updated"] > 120]
    for sid in to_delete:
        del MIRROR_STATES[sid]
        
    return jsonify({"status": "ok", "actions": actions})"""

new_pc_sync = """    # Aktualizace stavu
    if session_id not in MIRROR_STATES:
        MIRROR_STATES[session_id] = {"pending_actions": [], "approved": False, "connection_requested": False}
        
    MIRROR_STATES[session_id]["last_updated"] = time.time()
    MIRROR_STATES[session_id]["state"] = data.get('state', {})
    
    if "approve_connection" in data:
        if data["approve_connection"] is True:
            MIRROR_STATES[session_id]["approved"] = True
        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = False
            MIRROR_STATES[session_id]["connection_requested"] = False
            
    conn_req = MIRROR_STATES[session_id].get("connection_requested", False)
    approved = MIRROR_STATES[session_id].get("approved", False)
    
    actions = MIRROR_STATES[session_id]["pending_actions"].copy()
    MIRROR_STATES[session_id]["pending_actions"].clear()
    
    now = time.time()
    to_delete = [sid for sid, s in MIRROR_STATES.items() if now - s["last_updated"] > 120]
    for sid in to_delete:
        del MIRROR_STATES[sid]
        
    return jsonify({"status": "ok", "actions": actions, "connection_requested": conn_req and not approved, "is_approved": approved})"""

code = code.replace(old_pc_sync, new_pc_sync)

# 2. Update mirror_mobile_state
old_mobile_state = """            s = MIRROR_STATES[session_id]
            if time.time() - s["last_updated"] > 10:
                yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
            else:
                import json
                state = s.get("state", {})
                state_str = json.dumps(state)
                h = hash(state_str)
                if h != last_state_hash:
                    last_state_hash = h
                    yield f"data: {{\\"status\\": \\"online\\", \\"state\\": {state_str}}}\\n\\n"
            time.sleep(0.5)"""

new_mobile_state = """            s = MIRROR_STATES[session_id]
            if time.time() - s["last_updated"] > 10:
                yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
            else:
                if not s.get("connection_requested") and not s.get("approved"):
                    s["connection_requested"] = True
                    
                if not s.get("approved"):
                    yield f"data: {{\\"status\\": \\"waiting_for_approval\\"}}\\n\\n"
                else:
                    import json
                    state = s.get("state", {})
                    state_str = json.dumps(state)
                    h = hash(state_str)
                    if h != last_state_hash:
                        last_state_hash = h
                        yield f"data: {{\\"status\\": \\"online\\", \\"state\\": {state_str}}}\\n\\n"
            time.sleep(0.5)"""

code = code.replace(old_mobile_state, new_mobile_state)

# 3. Update mirror_mobile_ui styles and script
old_icons = """.offline-icon-container { position: relative; width: 140px; height: 100px; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; }
        .offline-icon { font-size: 45px; color: rgba(255,255,255,0.3); position: absolute; }
        .icon-pc { left: 10px; }
        .icon-mobile { right: 10px; }"""
new_icons = """.offline-icon-container { width: 100%; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; gap: 20px; }
        .offline-icon { font-size: 45px; color: rgba(255,255,255,0.3); }"""
code = code.replace(old_icons, new_icons)

old_sse_js = """                if (data.status === 'offline') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'PC JE OFFLINE';
                    sDesc.textContent = 'Aplikace přestala odesílat data. Zkontrolujte, zda PC neusnulo.';
                } else if (data.status === 'online') {"""
new_sse_js = """                if (data.status === 'offline') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'PC JE OFFLINE';
                    sDesc.textContent = 'Aplikace přestala odesílat data. Zkontrolujte, zda PC neusnulo.';
                } else if (data.status === 'waiting_for_approval') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ČEKÁM NA SCHVÁLENÍ';
                    sDesc.innerHTML = 'Potvrďte prosím na vašem PC žádost o připojení ke sdílení.<br><br><i class="fas fa-spinner fa-spin" style="font-size: 24px; color: #F4CC17;"></i>';
                } else if (data.status === 'online') {"""
code = code.replace(old_sse_js, new_sse_js)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Backend state and mobile UI successfully updated!")
