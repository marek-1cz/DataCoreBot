
with open('html_templates.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

start = content.find('HTML_DOWNLOADS_MGMT = ')
end_match = re.search(r'\n[A-Z_]+ = ', content[start+10:])
end_idx = start + 10 + end_match.start()

new_template = '''HTML_DOWNLOADS_MGMT = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
  <h2 style="margin:0;color:var(--text-main);display:flex;align-items:center;gap:10px;">
    <i class="fas fa-layer-group" style="color:var(--blue-main);"></i> Manager Verzí Launcheru
  </h2>
  <button onclick="document.getElementById('modal-add-version').style.display='flex'"
    style="background:var(--blue-main);color:#fff;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:8px;">
    <i class="fas fa-plus"></i> Přidat verzi
  </button>
</div>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}
    <div style="padding:12px 16px;border-radius:8px;margin-bottom:16px;background:{% if cat=='success' %}rgba(16,185,129,0.15);border:1px solid #10b981;color:#10b981{% else %}rgba(239,68,68,0.15);border:1px solid #ef4444;color:#ef4444{% endif %};">
      <i class="fas fa-{% if cat=='success' %}check-circle{% else %}exclamation-circle{% endif %}"></i> {{msg}}
    </div>
  {% endfor %}
{% endwith %}

<!-- Tabulka verzí -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="background:rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.08);">
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Verze</th>
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">DB verze</th>
        <th style="padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Role</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Aktivní = verze existuje. Vypnuto = nikdo ji nevidí.">Aktivní</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Viditelné v Launcheru">Viditelné</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Lze stáhnout">Stáhnout</th>
        <th style="padding:14px 8px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);" title="Lze spustit">Spustit</th>
        <th style="padding:14px 16px;text-align:right;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);">Akce</th>
      </tr>
    </thead>
    <tbody>
    {% for v in versions %}
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);{% if not v.get('is_active') %}opacity:0.45;{% endif %}"
          data-vid="{{ v.get('id','') }}"
          data-vname="{{ v.get('version_name','') | e }}"
          data-dbver="{{ v.get('db_version','') | e }}"
          data-furl="{{ v.get('file_url','') | e }}"
          data-role="{{ v.get('target_role','User') | e }}"
          data-active="{{ '1' if v.get('is_active') else '0' }}"
          data-show="{{ '1' if v.get('show_in_launcher', True) else '0' }}"
          data-dl="{{ '1' if v.get('can_download', True) else '0' }}"
          data-launch="{{ '1' if v.get('can_launch', True) else '0' }}">
        <td style="padding:14px 16px;">
          <div style="font-weight:600;color:var(--text-main);">{{ v.get('version_name','—') }}</div>
        </td>
        <td style="padding:14px 16px;">
          <span style="font-size:13px;color:var(--text-muted);font-family:monospace;">{{ v.get('db_version','—') }}</span>
        </td>
        <td style="padding:14px 16px;">
          <span style="background:rgba(96,165,250,0.15);color:#60a5fa;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">
            {{ v.get('target_role','—') }}
          </span>
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('is_active') %}
            <span style="color:#10b981;font-size:18px;" title="Aktivní – verze je dostupná"><i class="fas fa-toggle-on"></i></span>
          {% else %}
            <span style="color:#ef4444;font-size:18px;" title="Vypnuto – verze neexistuje pro nikoho"><i class="fas fa-toggle-off"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('show_in_launcher', True) %}
            <span style="color:#10b981;" title="Viditelné v Launcheru"><i class="fas fa-eye"></i></span>
          {% else %}
            <span style="color:#6b7280;" title="Skryté – zobrazí se jako Nedostupné"><i class="fas fa-eye-slash"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('can_download', True) %}
            <span style="color:#10b981;" title="Stahování povoleno"><i class="fas fa-download"></i></span>
          {% else %}
            <span style="color:#ef4444;" title="Stahování zakázáno"><i class="fas fa-ban"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 8px;text-align:center;">
          {% if v.get('can_launch', True) %}
            <span style="color:#10b981;" title="Spuštění povoleno"><i class="fas fa-play-circle"></i></span>
          {% else %}
            <span style="color:#ef4444;" title="Spuštění zakázáno"><i class="fas fa-stop-circle"></i></span>
          {% endif %}
        </td>
        <td style="padding:14px 16px;text-align:right;">
          <button class="btn-edit-version"
            style="background:rgba(96,165,250,0.15);color:#60a5fa;border:1px solid rgba(96,165,250,0.3);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;margin-right:6px;">
            <i class="fas fa-edit"></i> Upravit
          </button>
          <form method="POST" action="/dashboard/delete_version" style="display:inline;"
            onsubmit="return confirm('Smazat tuto verzi?')">
            <input type="hidden" name="version_id" value="{{ v.get('id') }}">
            <button type="submit" style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;">
              <i class="fas fa-trash"></i>
            </button>
          </form>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="8" style="padding:40px;text-align:center;color:var(--text-muted);">
        <i class="fas fa-inbox" style="font-size:32px;opacity:0.3;display:block;margin-bottom:10px;"></i>
        Zatím nebyly přidány žádné verze. Klikni na <b>Přidat verzi</b> výše.
      </td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>

<!-- LEGENDA -->
<div style="margin-top:16px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:var(--text-muted);">
  <span><i class="fas fa-toggle-off" style="color:#ef4444;"></i> <b>Aktivní=VYP</b> – nikdo nevidí</span>
  <span><i class="fas fa-eye-slash" style="color:#6b7280;"></i> <b>Viditelné=VYP</b> – zobrazí se jako "Nedostupné"</span>
  <span><i class="fas fa-ban" style="color:#ef4444;"></i> <b>Stáhnout=VYP</b> – nelze stáhnout</span>
  <span><i class="fas fa-stop-circle" style="color:#ef4444;"></i> <b>Spustit=VYP</b> – nelze spustit</span>
</div>

<!-- MODAL: Přidat verzi -->
<div id="modal-add-version" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;justify-content:center;align-items:center;">
  <div style="background:#0f172a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:32px;width:520px;max-width:95vw;max-height:90vh;overflow-y:auto;">
    <h3 style="margin:0 0 24px;color:var(--text-main);"><i class="fas fa-plus-circle" style="color:var(--blue-main);"></i> Přidat novou verzi</h3>
    <form method="POST" action="/dashboard/add_version">
      <div style="display:grid;gap:16px;">
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Název verze *</label>
          <input name="version_name" required placeholder="např. 1.6.1" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Verze DB * <span style="color:var(--text-muted);font-weight:400;">(kontrola kompatibility – např. 2026-09)</span></label>
          <input name="db_version" required placeholder="např. 2026-09" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">URL ke stažení (ZIP) *</label>
          <input name="file_url" required placeholder="https://github.com/.../releases/download/..." style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Minimální role pro přístup *</label>
          <select name="target_role" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
            <option value="User">User (všichni)</option>
            <option value="BT">BT (Beta Testeři)</option>
            <option value="DEV">DEV (Vývojáři)</option>
            <option value="SA">SA (Super Admin)</option>
          </select>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px;display:grid;gap:14px;">
          <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Nastavení přístupu</div>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Aktivní</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí skryje verzi úplně pro všechny (ani SA ji neuvidí)</div>
            </div>
            <input type="checkbox" name="is_active" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Viditelné v Launcheru</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí zobrazí verzi jako „Nedostupné" – nikdo ji nemůže stáhnout ani spustit</div>
            </div>
            <input type="checkbox" name="show_in_launcher" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze stáhnout</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Stáhnout – pokud vypnuto, nelze nově stáhnout</div>
            </div>
            <input type="checkbox" name="can_download" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div>
              <div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze spustit</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Spustit – pokud vypnuto, verze nejde spustit ani ze stažené kopie</div>
            </div>
            <input type="checkbox" name="can_launch" checked style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-top:24px;">
        <button type="submit" style="flex:1;background:var(--blue-main);color:#fff;border:none;padding:12px;border-radius:8px;cursor:pointer;font-weight:600;font-size:15px;">
          <i class="fas fa-plus"></i> Přidat verzi
        </button>
        <button type="button" onclick="document.getElementById('modal-add-version').style.display='none'"
          style="padding:12px 24px;background:rgba(255,255,255,0.06);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);border-radius:8px;cursor:pointer;">
          Zrušit
        </button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL: Upravit verzi -->
<div id="modal-edit-version" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;justify-content:center;align-items:center;">
  <div style="background:#0f172a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:32px;width:520px;max-width:95vw;max-height:90vh;overflow-y:auto;">
    <h3 style="margin:0 0 24px;color:var(--text-main);"><i class="fas fa-edit" style="color:#f59e0b;"></i> Upravit verzi</h3>
    <form method="POST" action="/dashboard/edit_version" id="form-edit-version">
      <input type="hidden" name="version_id" id="edit-version-id">
      <div style="display:grid;gap:16px;">
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Název verze *</label>
          <input name="version_name" id="edit-version-name" required style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Verze DB * <span style="color:var(--text-muted);font-weight:400;">(kontrola kompatibility)</span></label>
          <input name="db_version" id="edit-db-version" required style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">URL ke stažení (ZIP)</label>
          <input name="file_url" id="edit-file-url" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px;">Minimální role</label>
          <select name="target_role" id="edit-target-role" style="width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;">
            <option value="User">User (všichni)</option>
            <option value="BT">BT (Beta Testeři)</option>
            <option value="DEV">DEV (Vývojáři)</option>
            <option value="SA">SA (Super Admin)</option>
          </select>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px;display:grid;gap:14px;">
          <div style="font-size:13px;font-weight:600;color:var(--text-muted);">Nastavení přístupu</div>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Aktivní</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí skryje verzi úplně pro všechny</div></div>
            <input type="checkbox" name="is_active" id="edit-is-active" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Viditelné v Launcheru</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Vypnutí zobrazí badge „Nedostupné"</div></div>
            <input type="checkbox" name="show_in_launcher" id="edit-show-in-launcher" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze stáhnout</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Stáhnout v Launcheru</div></div>
            <input type="checkbox" name="can_download" id="edit-can-download" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
          <label style="display:flex;justify-content:space-between;align-items:flex-start;cursor:pointer;gap:12px;">
            <div><div style="font-size:14px;color:var(--text-main);font-weight:500;">Lze spustit</div><div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Povolí tlačítko Spustit (i ze stažené kopie)</div></div>
            <input type="checkbox" name="can_launch" id="edit-can-launch" style="width:20px;height:20px;cursor:pointer;accent-color:var(--blue-main);flex-shrink:0;margin-top:2px;">
          </label>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-top:24px;">
        <button type="submit" style="flex:1;background:#f59e0b;color:#000;border:none;padding:12px;border-radius:8px;cursor:pointer;font-weight:600;font-size:15px;">
          <i class="fas fa-save"></i> Uložit změny
        </button>
        <button type="button" onclick="document.getElementById('modal-edit-version').style.display='none'"
          style="padding:12px 24px;background:rgba(255,255,255,0.06);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);border-radius:8px;cursor:pointer;">
          Zrušit
        </button>
      </div>
    </form>
  </div>
</div>

<script>
// Edit button – reads data-* attrs from the <tr> row
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.btn-edit-version').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tr = this.closest('tr');
      document.getElementById('edit-version-id').value = tr.dataset.vid || '';
      document.getElementById('edit-version-name').value = tr.dataset.vname || '';
      document.getElementById('edit-db-version').value = tr.dataset.dbver || '';
      document.getElementById('edit-file-url').value = tr.dataset.furl || '';
      var roleEl = document.getElementById('edit-target-role');
      for (var i = 0; i < roleEl.options.length; i++) {
        if (roleEl.options[i].value === tr.dataset.role) { roleEl.selectedIndex = i; break; }
      }
      document.getElementById('edit-is-active').checked = tr.dataset.active === '1';
      document.getElementById('edit-show-in-launcher').checked = tr.dataset.show === '1';
      document.getElementById('edit-can-download').checked = tr.dataset.dl === '1';
      document.getElementById('edit-can-launch').checked = tr.dataset.launch === '1';
      document.getElementById('modal-edit-version').style.display = 'flex';
    });
  });
  // Close modals on backdrop click
  ['modal-add-version','modal-edit-version'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('click', function(e) { if (e.target === this) this.style.display = 'none'; });
  });
});
</script>
"""

'''

new_content = content[:start] + new_template + content[end_idx:]

with open('html_templates.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Template fixed!")
