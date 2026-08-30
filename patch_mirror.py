import re

def update_html():
    # Read ovladac.html to extract CSS
    with open(r'..\IDPK-OIS-RC-EDITION-V1.6\ovladac.html', 'r', encoding='utf-8') as f:
        ovladac_html = f.read()

    css_match = re.search(r'<style>(.*?)</style>', ovladac_html, re.DOTALL)
    if not css_match:
        print("CSS not found!")
        return
    css = css_match.group(1)

    # Build the full mobile UI
    mobile_ui = f"""
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <title>IDPK Mobilní Zrcadlo (1:1)</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            {css}
            /* Extra mobile tweaks */
            body {{
                overflow: hidden !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            .system-header {{ display: none !important; }} /* Hide header bar to save space on mobile */
            /* Hide the mobile control button in settings just in case */
            #settings-mobile-link {{ display: none !important; }}
            #premium-watermark {{ top: 15px !important; left: 15px !important; display: block !important; }}
            
            #mobile-offline-overlay {{
                display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.85); z-index: 999999;
                flex-direction: column; align-items: center; justify-content: center;
                color: white; font-family: 'Segoe UI', sans-serif; text-align: center;
            }}
        </style>
    </head>
    <body>
        <div id="mobile-offline-overlay">
            <i class="fas fa-wifi" style="font-size: 50px; color: #e74c3c; margin-bottom: 20px;"></i>
            <h2>PC JE OFFLINE</h2>
            <p>Spojení s palubním počítačem bylo přerušeno.</p>
        </div>
        
        <!-- The PC DOM will be injected here -->
        <div id="mirror-container"></div>

        <script>
            const sessionId = '{{ session_id }}';
            let isFocused = false;

            function connectSSE() {{
                const source = new EventSource('/api/mirror/mobile_state/' + sessionId);
                
                source.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    const offline = document.getElementById('mobile-offline-overlay');
                    const container = document.getElementById('mirror-container');
                    
                    if (data.status === 'offline') {{
                        offline.style.display = 'flex';
                    }} else if (data.status === 'online') {{
                        offline.style.display = 'none';
                        if (data.state && data.state.dom && !isFocused) {{
                            container.innerHTML = data.state.dom;
                        }}
                    }}
                }};
                
                source.onerror = function() {{
                    document.getElementById('mobile-offline-overlay').style.display = 'flex';
                }};
            }}

            // Handle Clicks
            document.addEventListener('click', function(e) {{
                // Find nearest element with onclick
                let el = e.target.closest('[onclick]');
                if (!el) {{
                    // Fallback to finding generic buttons
                    el = e.target.closest('.glass-btn, .settings-action-btn, .funk-action-btn, .link-suggestion-item, .nav-btn, .funk-btn-close');
                }}
                
                if (el) {{
                    let actionCode = el.getAttribute('onclick');
                    
                    if (actionCode) {{
                        e.preventDefault();
                        if (navigator.vibrate) navigator.vibrate(20);
                        
                        fetch('/api/mirror/mobile_action/' + sessionId, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ action: 'eval', code: actionCode }})
                        }});
                    }}
                }}
            }});

            // Handle Input Typing
            document.addEventListener('focusin', function(e) {{
                if (e.target.tagName === 'INPUT') {{
                    isFocused = true;
                }}
            }});
            
            document.addEventListener('focusout', function(e) {{
                if (e.target.tagName === 'INPUT') {{
                    isFocused = false;
                }}
            }});

            document.addEventListener('input', function(e) {{
                if (e.target.tagName === 'INPUT') {{
                    fetch('/api/mirror/mobile_action/' + sessionId, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ action: 'input', id: e.target.id, value: e.target.value }})
                    }});
                }}
            }});

            connectSSE();
        </script>
    </body>
    </html>
    """

    with open('main.py', 'r', encoding='utf-8') as f:
        py_content = f.read()

    new_html = '    html = """\\n' + mobile_ui + '\\n    """'
    py_content = re.sub(r'    html = """(.*?)    """', new_html, py_content, flags=re.DOTALL)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(py_content)

if __name__ == "__main__":
    update_html()
    print("Patch OK")
