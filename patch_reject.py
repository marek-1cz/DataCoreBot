import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace PC sync logic
old_pc = """    if "approve_connection" in data:
        if data["approve_connection"] is True:
            MIRROR_STATES[session_id]["approved"] = True
        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = False
            MIRROR_STATES[session_id]["connection_requested"] = False
            
    conn_req = MIRROR_STATES[session_id].get("connection_requested", False)
    approved = MIRROR_STATES[session_id].get("approved", False)"""

new_pc = """    if "approve_connection" in data:
        if data["approve_connection"] is True:
            MIRROR_STATES[session_id]["approved"] = True
        elif data["approve_connection"] is False:
            MIRROR_STATES[session_id]["approved"] = "rejected"
            MIRROR_STATES[session_id]["connection_requested"] = False
            
    conn_req = MIRROR_STATES[session_id].get("connection_requested", False)
    approved = MIRROR_STATES[session_id].get("approved")
    
    # We only want to trigger the prompt if it's NOT approved and NOT rejected
    is_approved_bool = (approved is True)
    conn_req_flag = conn_req and (approved is False or approved is None)"""
code = code.replace(old_pc, new_pc)

# Fix jsonify return in pc_sync
old_ret = """return jsonify({"status": "ok", "actions": actions, "connection_requested": conn_req and not approved, "is_approved": approved})"""
new_ret = """return jsonify({"status": "ok", "actions": actions, "connection_requested": conn_req_flag, "is_approved": is_approved_bool})"""
code = code.replace(old_ret, new_ret)

# Replace SSE logic
old_sse = """                    if not s.get("connection_requested") and not s.get("approved"):
                        s["connection_requested"] = True
                        
                    if not s.get("approved"):
                        yield f"data: {{\\"status\\": \\"waiting_for_approval\\"}}\\n\\n"
                    else:"""

new_sse = """                    if s.get("approved") == "rejected":
                        yield f"data: {{\\"status\\": \\"rejected\\"}}\\n\\n"
                        time.sleep(1)
                        break
                        
                    if not s.get("connection_requested") and not s.get("approved"):
                        s["connection_requested"] = True
                        
                    if not s.get("approved"):
                        yield f"data: {{\\"status\\": \\"waiting_for_approval\\"}}\\n\\n"
                    elif s.get("approved") is True:"""
code = code.replace(old_sse, new_sse)

# Replace HTML in mirror_mobile_ui to handle 'rejected'
old_html = """                } else if (data.status === 'waiting_for_approval') {"""
new_html = """                } else if (data.status === 'rejected') {
                    statusOverlay.style.display = 'flex';
                    sTitle.textContent = 'ZAMÍTNUTO';
                    sDesc.innerHTML = 'Spojení bylo odmítnuto z PC.<br>Nelze se připojit.';
                    source.close();
                } else if (data.status === 'waiting_for_approval') {"""
code = code.replace(old_html, new_html)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Backend main.py updated with reject state handling!")
