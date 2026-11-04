# -*- coding: utf-8 -*-
"""
ois_email.py  -  jednotná HTML šablona e-mailů Projekt OIS IDPK
=====================================================================
Jeden soubor, žádné závislosti mimo standardní knihovnu. Šablona je
tabulková s inline CSS (funguje v Gmailu, Outlooku, Seznamu, Apple Mail),
bez JavaScriptu, bez obrázků. Tmavé "okno" s barevným pruhem podle typu.

POUŽITÍ (vložte do main.py):

    from ois_email import (build_notification_email, build_magic_link_email,
                           build_admin_email)

1) Upozornění (nahrazuje celé sestavení html ve send_notification_email_sync):

    subject, html, text = build_notification_email(
        embed_data, dm_text, rule_id=rule_id, is_one_time=is_one_time)
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain", "utf-8"))   # nejdřív prostý text
    msg.attach(MIMEText(html, "html", "utf-8"))    # HTML musí být poslední

   Zprávy od administrátora (rule_id začíná "admin_direct") se samy poznají:
   dostanou štítek "ZPRÁVA OD ADMINISTRÁTORA" a bez tlačítka vypnutí.

2) Přihlašovací e-mail (send_magic_link_email):

    subject, html, text = build_magic_link_email(login_url, token)

3) Vlastní zpráva (cokoliv jiného):

    subject, html, text = build_admin_email("Nadpis", "Text zprávy\\nna více řádků",
                                            buttons=[("Otevřít", "https://...")])

Barva pruhu: embed_data["color"] (celé číslo jako na Discordu) nebo parametr accent.
Hodnoty jsou vždy escapované. Povolená značka v textu: **tučně**, `kód`, [text](url).
=====================================================================
"""
import html as _h
import re

BASE_URL = "https://datacorebot.koyeb.app"
BRAND = "PROJEKT OIS IDPK"

# barvy (shodné s webem)
C_BG = "#05070f"
C_CARD = "#0a1230"
C_CARD2 = "#0f1b44"
C_LINE = "#1d2c5e"
C_TEXT = "#eaf0ff"
C_MUTED = "#9fb0d6"
C_BLUE = "#2f6bff"
C_CYAN = "#38d6ff"
C_YELLOW = "#ffc933"
C_GREEN = "#35d07f"
C_RED = "#ff6b6b"

FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace"


def _esc(s):
    return _h.escape("" if s is None else str(s), quote=True)


def _int_to_hex(c, default=C_CYAN):
    try:
        c = int(c)
        if 0 <= c <= 0xFFFFFF:
            return "#%06x" % c
    except Exception:
        pass
    return default


def _rich(text):
    """Escapuje text a povolí **tučně**, `kód`, [text](url) a nové řádky."""
    t = _esc(text)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: '<a href="%s" style="color:%s;text-decoration:underline;">%s</a>' % (m.group(2), C_CYAN, m.group(1)), t)
    t = re.sub(r"\*\*(.+?)\*\*", r'<strong style="color:#ffffff;">\1</strong>', t)
    t = re.sub(r"`([^`]+)`",
               lambda m: '<span style="font-family:%s;background-color:%s;color:%s;padding:2px 7px;border-radius:5px;font-size:13px;">%s</span>' % (MONO, C_CARD2, C_CYAN, m.group(1)), t)
    t = re.sub(r"&lt;t:\d+(?::[a-zA-Z])?&gt;", "", t)  # Discord časové značky v e-mailu nedávají smysl
    return t.replace("\n", "<br>")


def _plain(text):
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", str(text or ""))
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = t.replace("`", "")
    return re.sub(r"<t:\d+(?::[a-zA-Z])?>", "", t)


def _button(label, href, primary=True, color=None):
    """Bulletproof tlačítko (funguje i v Outlooku)."""
    if primary:
        bg, fg, bd = color or C_CYAN, "#06101f", color or C_CYAN
    else:
        bg, fg, bd = C_CARD2, C_TEXT, C_LINE
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;margin:0 10px 10px 0;">'
        '<tr><td align="center" bgcolor="%s" style="background-color:%s;border:1px solid %s;border-radius:10px;">'
        '<a href="%s" target="_blank" style="display:inline-block;padding:12px 20px;font-family:%s;font-size:14px;font-weight:700;'
        'color:%s;text-decoration:none;border-radius:10px;">%s</a></td></tr></table>'
        % (bg, bg, bd, _esc(href), FONT, fg, _esc(label))
    )


def _fields_table(fields, accent):
    rows = []
    for f in fields or []:
        name = _esc(f.get("name") or "Info")
        val = _rich(f.get("value") or "-")
        rows.append(
            '<tr>'
            '<td valign="top" width="38%%" style="padding:11px 14px;border-bottom:1px solid %s;font-family:%s;font-size:12px;'
            'letter-spacing:.06em;text-transform:uppercase;color:%s;">%s</td>'
            '<td valign="top" style="padding:11px 14px;border-bottom:1px solid %s;font-family:%s;font-size:15px;line-height:1.5;color:%s;">%s</td>'
            '</tr>' % (C_LINE, FONT, C_MUTED, name, C_LINE, FONT, C_TEXT, val))
    if not rows:
        return ""
    return (
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:22px 0 4px 0;background-color:%s;border:1px solid %s;border-radius:12px;border-collapse:separate;">%s</table>'
        % (C_CARD2, C_LINE, "".join(rows)))


def wrap_email(*, label, title, intro_html="", fields=None, buttons=None, accent=C_CYAN,
               preheader="", footer_links=None, footer_note="", code=None):
    """Složí celý e-mail. Ostatní funkce jen připraví vstupy.
    buttons: [(popisek, url, primary_bool), ...]  footer_links: [(popisek, url), ...]
    code: volitelně velký kód (např. 5místný přihlašovací)."""
    btn_html = "".join(_button(b[0], b[1], (b[2] if len(b) > 2 else True), accent if (len(b) > 2 and b[2]) or len(b) == 2 else None)
                       for b in (buttons or []))
    code_html = ""
    if code:
        code_html = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 18px 0;">'
            '<tr><td style="padding:14px 26px;background-color:%s;border:1px dashed %s;border-radius:12px;font-family:%s;'
            'font-size:30px;letter-spacing:.35em;font-weight:700;color:#ffffff;">%s</td></tr></table>' % (C_CARD2, accent, MONO, _esc(code)))
    links = footer_links or []
    links_html = " &nbsp;&bull;&nbsp; ".join(
        '<a href="%s" target="_blank" style="color:%s;text-decoration:none;">%s</a>' % (_esc(u), C_MUTED, _esc(t)) for t, u in links)
    pre = ('<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">%s</div>' % _esc(preheader)) if preheader else ""
    return f"""<!DOCTYPE html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light"><meta name="supported-color-schemes" content="dark light">
<title>{_esc(title)}</title></head>
<body style="margin:0;padding:0;background-color:{C_BG};">{pre}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{C_BG}" style="background-color:{C_BG};">
<tr><td align="center" style="padding:28px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
    <tr><td style="padding:0 6px 14px 6px;font-family:{FONT};font-size:11px;letter-spacing:.22em;font-weight:700;color:{C_MUTED};">
        <span style="color:{accent};">&#9679;</span>&nbsp; {BRAND} &nbsp;&bull;&nbsp; CENTRÁLNÍ SYSTÉM</td></tr>
    <tr><td bgcolor="{C_CARD}" style="background-color:{C_CARD};border:1px solid {C_LINE};border-radius:18px;overflow:hidden;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td height="5" bgcolor="{accent}" style="height:5px;line-height:5px;font-size:0;background-color:{accent};border-radius:18px 18px 0 0;">&nbsp;</td></tr>
        <tr><td style="padding:30px 30px 8px 30px;">
          <div style="display:inline-block;padding:5px 12px;border-radius:999px;background-color:{C_CARD2};border:1px solid {C_LINE};
                      font-family:{FONT};font-size:11px;letter-spacing:.14em;font-weight:700;color:{accent};">{_esc(label)}</div>
          <h1 style="margin:16px 0 0 0;font-family:{FONT};font-size:24px;line-height:1.3;font-weight:800;color:#ffffff;">{_esc(title)}</h1>
        </td></tr>
        <tr><td style="padding:10px 30px 8px 30px;font-family:{FONT};font-size:16px;line-height:1.6;color:{C_TEXT};">
          {intro_html}
          {code_html}
          {_fields_table(fields, accent)}
        </td></tr>
        <tr><td style="padding:18px 30px 10px 30px;">{btn_html}</td></tr>
        <tr><td style="padding:6px 30px 26px 30px;font-family:{FONT};font-size:13px;line-height:1.6;color:{C_MUTED};">{footer_note}</td></tr>
      </table>
    </td></tr>
    <tr><td align="center" style="padding:18px 10px 6px 10px;font-family:{FONT};font-size:12px;line-height:1.7;color:{C_MUTED};">
      {links_html}<br>
      Hezký den přeje tým Projekt OIS IDPK<br>
      <span style="color:#6b7aa6;">Nezávislý komunitní projekt, není oficiálním produktem dopravců.</span>
    </td></tr>
  </table>
</td></tr></table></body></html>"""


# ----------------------------------------------------------------------
def build_notification_email(embed_data, dm_text="", rule_id=None, is_one_time=False,
                             base_url=BASE_URL, accent=None):
    """Upozornění nebo zpráva od administrátora. Vrací (subject, html, text)."""
    is_admin = str(rule_id or "").startswith("admin_direct")
    ed = embed_data or {}
    title = str(ed.get("title") or ("Zpráva od administrátora" if is_admin else "Upozornění na autobus")).replace("\n", " ")
    desc = ed.get("description") or ("" if ed else dm_text)
    fields = ed.get("fields") or []
    color = accent or _int_to_hex(ed.get("color"), C_YELLOW if is_admin else C_CYAN)
    label = "ZPRÁVA OD ADMINISTRÁTORA" if is_admin else ("JEDNORÁZOVÉ UPOZORNĚNÍ" if is_one_time else "UPOZORNĚNÍ NA SPOJ")
    intro = '<div style="font-size:16px;line-height:1.65;color:%s;">%s</div>' % (C_TEXT, _rich(desc)) if desc else ""

    buttons, links = [], []
    why = (base_url + "/proc-notifikace?typ=admin") if is_admin else (base_url + "/proc-notifikace")
    why_label = "Proč mi přišla zpráva od administrátora?" if is_admin else "Proč mi chodí upozornění?"
    if not is_one_time and rule_id and not is_admin:
        unsub = "%s/api/notifications/unsubscribe?id=%s" % (base_url, _h.escape(str(rule_id), quote=True))
        links.append(("Vypnout pravidelné notifikace", unsub))
    links.append((why_label, why))
    links.append(("Podpora", base_url + "/podpora"))
    buttons.append((why_label, why, False))
    if not is_one_time and rule_id and not is_admin:
        buttons.insert(0, ("Vypnout pravidelné notifikace", unsub, True))

    foot = ed.get("footer", {}).get("text") if isinstance(ed.get("footer"), dict) else ""
    note = _esc(foot) if foot else ""
    pre = _plain(desc)[:110] or title
    html = wrap_email(label=label, title=title, intro_html=intro, fields=fields,
                      buttons=buttons, accent=color, preheader=pre, footer_links=links, footer_note=note)
    text_lines = [title, "", _plain(desc)]
    for f in fields:
        text_lines.append("%s: %s" % (f.get("name", ""), _plain(f.get("value", ""))))
    text_lines += ["", "Proč mi chodí upozornění: " + why]
    if not is_one_time and rule_id and not is_admin:
        text_lines.append("Vypnout notifikace: " + unsub)
    return title, html, "\n".join(text_lines)


def build_magic_link_email(login_url, token, base_url=BASE_URL):
    """Přihlašovací e-mail. Vrací (subject, html, text)."""
    subject = "Přihlášení do aplikace OIS IDPK"
    intro = ('<p style="margin:0 0 14px 0;">Dobrý den,</p>'
             '<p style="margin:0 0 18px 0;">posíláme odkaz pro přístup do aplikace OIS IDPK. Pro dokončení přihlášení stačí kliknout na tlačítko níže. '
             'Případně můžete ručně zadat tento 5místný kód:</p>')
    note = "Pokud se právě do aplikace nepřihlašujete, nic se neděje a e-mail můžete v klidu smazat. Váš účet je v bezpečí."
    html = wrap_email(label="PŘIHLÁŠENÍ", title="Potvrďte své přihlášení", intro_html=intro, code=token,
                      buttons=[("Potvrdit přihlášení", login_url, True)], accent=C_CYAN,
                      preheader="Odkaz a kód pro přihlášení do OIS IDPK",
                      footer_links=[("Podpora", base_url + "/podpora"), ("Centrum pomoci", base_url + "/pomoc")],
                      footer_note=_esc(note))
    text = "Dobrý den,\n\nodkaz pro přihlášení: %s\nNebo zadejte kód: %s\n\n%s\n\nTým Projekt OIS IDPK" % (login_url, token, note)
    return subject, html, text


def build_admin_email(title, body, buttons=None, accent=C_YELLOW, label="ZPRÁVA OD ADMINISTRÁTORA",
                      fields=None, base_url=BASE_URL):
    """Libovolná zpráva. buttons: [(popisek, url), ...]. Vrací (subject, html, text)."""
    btns = [(t, u, i == 0) for i, (t, u) in enumerate(buttons or [])]
    html = wrap_email(label=label, title=title, intro_html='<div>%s</div>' % _rich(body), fields=fields,
                      buttons=btns, accent=accent, preheader=_plain(body)[:110],
                      footer_links=[("Podpora", base_url + "/podpora"), ("Centrum pomoci", base_url + "/pomoc")])
    return title, html, "%s\n\n%s\n\nTým Projekt OIS IDPK" % (title, _plain(body))


# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Vygeneruje ukázky: python3 ois_email.py
    demo = {"title": "🚌 Autobus linky 722 je u zastávky Plasy", "color": 0x35d07f,
            "description": "Sledovaný spoj právě **přijíždí** k zastávce.",
            "fields": [{"name": "Linka", "value": "722 Plzeň – Plasy"}, {"name": "SPZ", "value": "`2P5 1234`"},
                       {"name": "Zpoždění", "value": "🟡 +3 min"}, {"name": "Příjezd", "value": "14:32"},
                       {"name": "Mapa", "value": "[Zobrazit na mapě](https://datacorebot.koyeb.app/mapa)"}],
            "footer": {"text": "Pravidlo č. 12 • OIS IDPK"}}
    s, h, t = build_notification_email(demo, "", rule_id=12)
    open("vzor-notifikace.html", "w", encoding="utf-8").write(h)
    s, h, t = build_notification_email({"title": "Plánovaná údržba", "color": 0xffc933,
                                        "description": "Dnes od **22:00** do 23:00 bude web krátce nedostupný.\nDěkujeme za trpělivost."},
                                       "", rule_id="admin_direct_1")
    open("vzor-zprava-admin.html", "w", encoding="utf-8").write(h)
    s, h, t = build_magic_link_email("https://datacorebot.koyeb.app/api/auth/finalize?token=48213", "48213")
    open("vzor-prihlaseni.html", "w", encoding="utf-8").write(h)
    print("hotovo")
