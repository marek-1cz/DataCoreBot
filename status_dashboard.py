HTML_STATUS_SECTION = """
<div class="card" style="background-color: var(--bg-dark); padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-top: 20px;">
    <h3 style="color: var(--blue-main); margin-top: 0; margin-bottom: 15px;"><i class="fas fa-satellite-dish"></i> Správa Discord Statusů</h3>
    <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">Zde spravuješ texty pro kanál <strong>🛜・status</strong>. Většina věcí se generuje automaticky z tvého nastavení nahoře. Zpráva se odešle/zaktualizuje <strong>POUZE</strong> při zaškrtnutí políčka dole.</p>
    
    <form action="/dashboard/update_statuses" method="POST">
        
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #3b82f6;">
            <p style="margin: 0 0 10px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase; font-weight: bold;">Generováno automaticky systémem</p>
            <div style="margin-bottom: 8px; color: white;"><strong>🤖 Discord Bot:</strong> <span style="color: #10b981;">🟢 Vždy plně aktivní a komunikuje</span></div>
            <div style="margin-bottom: 8px; color: white;"><strong>🗄️ Databáze:</strong> <span style="color: #10b981;">🟢 Stabilní a synchronizovaná</span></div>
            <div style="color: white;"><strong>💻 Globální vypínač:</strong> <span style="color: #94a3b8;">Reaguje automaticky na horní stav softwaru</span></div>
        </div>

        <div style="margin-bottom: 15px; padding: 15px; background: rgba(255, 255, 255, 0.03); border: 1px solid #475569; border-radius: 6px;">
            <label style="color: var(--blue-main); font-weight: bold; display: block; margin-bottom: 15px; font-size: 16px;"><i class="fas fa-download"></i> Jaký status nastavit pro Stahování?</label>
            
            <div style="margin-bottom: 12px;">
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px;">
                    <input type="radio" name="dl_status_mode" value="auto" {% if dl_status_mode == 'auto' or not dl_status_mode %}checked{% endif %} style="margin-right: 10px; transform: scale(1.2);">
                    <strong>1. Automatický mód</strong>&nbsp; <span style="color: var(--text-muted); font-size: 13px;">(Vezme to, co je naklikané nahoře: ✅ Povoleno / ⛔ Zakázáno)</span>
                </label>
            </div>
            
            <div style="margin-bottom: 12px;">
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px;">
                    <input type="radio" name="dl_status_mode" value="maintenance" {% if dl_status_mode == 'maintenance' %}checked{% endif %} style="margin-right: 10px; transform: scale(1.2);">
                    <strong>2. Oranžový mód (Údržba)</strong>&nbsp; <span style="color: #f59e0b; font-size: 13px;">(Napíše: Probíhá oprava, některé soubory nemusí fungovat)</span>
                </label>
            </div>

            <div>
                <label style="display: flex; align-items: center; cursor: pointer; color: white; font-size: 15px; margin-bottom: 10px;">
                    <input type="radio" name="dl_status_mode" value="custom" {% if dl_status_mode == 'custom' %}checked{% endif %} style="margin-right: 10px; transform: scale(1.2);">
                    <strong>3. Vlastní text a ikona</strong>&nbsp; <span style="color: var(--text-muted); font-size: 13px;">(Napiš si cokoliv chceš)</span>
                </label>
                
                <div style="display: flex; gap: 10px; margin-left: 28px;">
                    <select name="dl_status_custom_icon" class="form-control" style="background: var(--bg-dark); color: white; border: 1px solid #475569; width: auto;">
                        <option value="🟢" {% if dl_status_custom_icon == '🟢' %}selected{% endif %}>🟢 Zelená</option>
                        <option value="🟠" {% if dl_status_custom_icon == '🟠' %}selected{% endif %}>🟠 Oranžová</option>
                        <option value="🔴" {% if dl_status_custom_icon == '🔴' %}selected{% endif %}>🔴 Červená</option>
                        <option value="🔵" {% if dl_status_custom_icon == '🔵' %}selected{% endif %}>🔵 Modrá</option>
                    </select>
                    <input type="text" name="dl_status_custom_text" class="form-control" style="background: var(--bg-dark); color: white; border: 1px solid #475569; flex-grow: 1;" placeholder="Např. Omlouváme se, instalátor V3 teď zlobí..." value="{{ dl_status_custom_text | default('') }}">
                </div>
            </div>
        </div>

        <hr style="border-color: #334155; margin: 20px 0;">

        <div style="margin-bottom: 20px;">
            <label style="display: flex; align-items: center; cursor: pointer; background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);">
                <input type="checkbox" name="send_to_discord" value="True" style="width: 22px; height: 22px; margin-right: 12px; cursor: pointer;">
                <span style="color: #10b981; font-weight: bold; font-size: 16px;"><i class="fab fa-discord"></i> Odeslat / Aktualizovat status na Discordu (kanál 🛜・status)</span>
            </label>
        </div>

        <button type="submit" class="btn btn-primary" style="background-color: var(--blue-main); border: none; padding: 14px 20px; font-weight: bold; width: 100%; font-size: 16px; border-radius: 6px;"><i class="fas fa-save"></i> Uložit nastavení a provést akci</button>
    </form>
</div>
"""
