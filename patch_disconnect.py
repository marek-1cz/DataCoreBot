import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace mirror_mobile_state logic
old_func = """    def generate():
        last_state_hash = None
        while True:
            if session_id not in MIRROR_STATES:
                yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
                time.sleep(2)
                continue
                
            s = MIRROR_STATES[session_id]
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

new_func = """    def generate():
        last_state_hash = None
        try:
            while True:
                if session_id not in MIRROR_STATES:
                    yield f"data: {{\\"status\\": \\"offline\\"}}\\n\\n"
                    time.sleep(2)
                    continue
                    
                s = MIRROR_STATES[session_id]
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
                time.sleep(0.5)
        except GeneratorExit:
            pass
        finally:
            if session_id in MIRROR_STATES:
                MIRROR_STATES[session_id]["approved"] = False
                MIRROR_STATES[session_id]["connection_requested"] = False"""

code = code.replace(old_func, new_func)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Backend main.py updated with try-finally for mobile disconnect!")
