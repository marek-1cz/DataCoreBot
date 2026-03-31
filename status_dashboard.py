HTML_STATUS_SECTION = """
<div class="card" style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0; margin-bottom: 15px;"><i class="fas fa-satellite-dish"></i> Správa Discord Statusů</h3>
    <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">Nastavení se <strong>ukládá automaticky</strong> při změně. Zpráva na Discord se zaktualizuje po zaškrtnutí posledního políčka.</p>
    
    <form action="/dashboard/update_statuses" method="POST" id="statusForm">
        
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #3b82f6;">
            <p style="margin: 0 0 10px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase; font-weight: bold;">Generováno automaticky systémem</p>
            <div style="margin-bottom: 8px; color: white;"><strong>🗄️ Databáze:</strong> <span style="color: #10b981;">🟢 Stabilní a synchronizovaná</span></div>
            <div style="color: white;"><strong>💻 Globální vypínač:</strong> <span style="color: #94a3b8;">Reaguje na horní stav softwaru</span></div>
        </div>

        <div style="margin-bottom: 15px; padding: 15px; background: rgba(255, 255, 255, 0.03); border: 1px solid #475569; border-radius: 6px;">
            <label style="color: var(--blue-main); font-weight: bold; display: block; margin-bottom: 15px; font-size: 16px;"><i class="fas fa-download"></i> Status pro Stahování</label>
            
            <div style="margin-bottom: 12px;">
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px;">
                    <input type="radio" name="dl_status_mode" value="auto" {% if dl_status_mode == 'auto' or not dl_status_mode %}checked{% endif %} onchange="document.getElementById('statusForm').submit();" style="margin-right: 10px; transform: scale(1.2);">
                    <strong>1. Automatický mód</strong>&nbsp; <span style="color: var(--text-muted); font-size: 13px;">(Povoleno / Zakázáno)</span>
                </label>
            </div>
            
            <div style="margin-bottom: 12px;">
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px;">
                    <input type="radio" name="dl_status_mode" value="maintenance" {% if dl_status_mode == 'maintenance' %}checked{% endif %} onchange="document.getElementById('statusForm').submit();" style="margin-right: 10px; transform: scale(1.2);">
                    <strong>2. Oranžový mód (Údržba)</strong>&nbsp; <span style="color: #f59e0b; font-size: 13px;">(Probíhá oprava)</span>
                </label>
            </div>

            <div>
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px; margin-bottom: 10px;">
                    <input type="radio" name="dl_status_mode" value="custom" {% if dl_status_mode == 'custom' %}checked{% endif %} onchange="document.getElementById('statusForm').submit();" style="margin-right: 10px; transform: scale(1.2);">
                    <strong>3. Vlastní text a ikona</strong>
                </label>
                
                <div style="display: flex; gap: 10px; margin-left: 28px;">
                    <select name="dl_status_custom_icon" class="form-control" onchange="document.getElementById('statusForm').submit();" style="background: var(--bg-dark); color: white; border: 1px solid #475569; width: auto;">
                        <option value="🟢" {% if dl_status_custom_icon == '🟢' %}selected{% endif %}>🟢 Zelená</option>
                        <option value="🟠" {% if dl_status_custom_icon == '🟠' %}selected{% endif %}>🟠 Oranžová</option>
                        <option value="🔴" {% if dl_status_custom_icon == '🔴' %}selected{% endif %}>🔴 Červená</option>
                        <option value="🔵" {% if dl_status_custom_icon == '🔵' %}selected{% endif %}>🔵 Modrá</option>
                    </select>
                    <input type="text" name="dl_status_custom_text" class="form-control" onblur="document.getElementById('statusForm').submit();" onkeydown="if(event.key === 'Enter'){ this.blur(); return false; }" style="background: var(--bg-dark); color: white; border: 1px solid #475569; flex-grow: 1;" placeholder="Po dopsání klikni mimo pro uložení..." value="{{ dl_status_custom_text | default('') }}">
                </div>
            </div>
        </div>

        <hr style="border-color: #334155; margin: 20px 0;">

        <div style="margin-bottom: 5px;">
            <label style="display: flex; align-items: center; cursor: pointer; background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);">
                <input type="checkbox" name="send_to_discord" value="True" onchange="document.getElementById('statusForm').submit();" style="width: 22px; height: 22px; margin-right: 12px; cursor: pointer;">
                <span style="color: #10b981; font-weight: bold; font-size: 16px;"><i class="fab fa-discord"></i> Odeslat / Aktualizovat status na Discordu (kanál 🛜・status)</span>
            </label>
        </div>
    </form>
</div>
"""
