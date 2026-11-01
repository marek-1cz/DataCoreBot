# -*- coding: utf-8 -*-
"""
discord_embed.py  -  vylepšený vzhled Discord upozornění (DM) pro OIS IDPK
=====================================================================
Beze změny stávající fronty: dál předáváte stejný slovník embed_data
({title, description, color, fields:[{name,value,inline}], footer:{text}}).
Modul jen doladí vzhled a postaví tlačítka.

Co zlepšuje oproti dnešku
  - proužek s názvem systému nahoře (author) a čas události dole (timestamp)
  - SPZ / ID / číslo linky automaticky ve značce kódu (`2P5 1234`)
  - stavové body 🟢 🟡 🔴 u zpoždění (funkce delay_badge)
  - pole se řadí do úhledných trojic (inline), dlouhé hodnoty na celou šířku
  - barva podle typu (příjezd zelená, zpoždění žlutá, výpadek červená, info modrá)
  - zprávy od administrátora mají vlastní hlavičku a bez tlačítka "Vypnout"

NÁHRADA V main.py, ve funkci check_notification_queue():
  Celý blok od "view = None" až po "em.set_footer(...)" nahradí:

      from discord_embed import build_embed, build_view
      view = build_view(rule_id, is_one_time)          # discord.ui.View s tlačítky
      em = build_embed(embed_data, rule_id, is_one_time)  # discord.Embed
      await user.send(embed=em, view=view)

  Zbytek (fallback na dm_text, chyby, TRACKER) zůstává stejný.
=====================================================================
"""
import re
import datetime

BASE_URL = "https://datacorebot.koyeb.app"
SYSTEM_NAME = "OIS IDPK • Centrální systém"

COLORS = {"arrival": 0x35D07F, "delay": 0xFFC933, "outage": 0xFF6B6B,
          "info": 0x38D6FF, "admin": 0x2F6BFF}

_SPZ = re.compile(r"^[0-9A-Z]{1,3}\s?[0-9A-Z]{3,5}$")
_ID = re.compile(r"^#?\d{1,10}$")


def delay_badge(minutes):
    """Číslo minut -> '🟢 včas', '🟡 +3 min', '🔴 +12 min'."""
    try:
        m = int(minutes)
    except Exception:
        return str(minutes)
    if m <= 0:
        return "🟢 včas" if m == 0 else "🟢 %d min dříve" % abs(m)
    return ("🟡 +%d min" if m < 8 else "🔴 +%d min") % m


def _code_if_id(name, value):
    n = (name or "").lower()
    v = str(value or "").strip()
    if v.startswith("`") or "](" in v:
        return v
    if any(k in n for k in ("spz", "id", "vozidlo", "linka")) and (_SPZ.match(v.upper()) or _ID.match(v)):
        return "`%s`" % v
    return v


def enhance(embed_data, rule_id=None, is_one_time=False, now=None):
    """Vrací nový slovník: stejné klíče + author, timestamp, upravená pole."""
    ed = dict(embed_data or {})
    is_admin = str(rule_id or "").startswith("admin_direct")
    ed.setdefault("title", "Zpráva od administrátora" if is_admin else "Upozornění na autobus")
    ed["color"] = ed.get("color") or (COLORS["admin"] if is_admin else COLORS["info"])
    ed["author"] = {"name": ("Zpráva od administrátora" if is_admin else "Sledování spojů") + " • " + SYSTEM_NAME}
    fields = []
    for f in ed.get("fields") or []:
        name = str(f.get("name") or "Info").strip()[:256] or "Info"
        val = _code_if_id(name, str(f.get("value") or "-").strip()[:1024] or "-")
        inline = bool(f.get("inline", True)) and len(val) <= 36 and "\n" not in val
        fields.append({"name": name, "value": val, "inline": inline})
    # poslední neúplná trojice inline polí by vypadala "děravě" -> necháme ji jako je,
    # ale jedno osamělé inline pole zvětšíme na celou šířku
    inl = [f for f in fields if f["inline"]]
    if len(inl) == 1:
        inl[0]["inline"] = False
    ed["fields"] = fields
    foot = (ed.get("footer") or {}).get("text") or ""
    parts = [p for p in (foot, "OIS IDPK") if p]
    ed["footer"] = {"text": " • ".join(dict.fromkeys(parts))[:2000]}
    ed["timestamp"] = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    return ed


def build_embed(embed_data, rule_id=None, is_one_time=False):
    """discord.Embed připravený k odeslání."""
    import discord
    ed = enhance(embed_data, rule_id, is_one_time)
    em = discord.Embed(title=str(ed["title"]).replace("\r", "").replace("\n", " ")[:250],
                       description=str(ed.get("description", ""))[:2000],
                       color=ed["color"],
                       timestamp=datetime.datetime.fromisoformat(ed["timestamp"]))
    em.set_author(name=ed["author"]["name"][:256])
    for f in ed["fields"][:25]:
        em.add_field(name=f["name"], value=f["value"], inline=f["inline"])
    em.set_footer(text=ed["footer"]["text"])
    return em


def build_view(rule_id=None, is_one_time=False, base_url=BASE_URL):
    """discord.ui.View s odkazovými tlačítky (stejné jako dnes, jen čistší popisky)."""
    import discord
    view = discord.ui.View()
    if not is_one_time and rule_id and not str(rule_id).startswith("admin_direct"):
        view.add_item(discord.ui.Button(label="Vypnout notifikace", emoji="🔕", style=discord.ButtonStyle.link,
                                        url="%s/api/notifications/unsubscribe?id=%s" % (base_url, rule_id)))
    view.add_item(discord.ui.Button(label="Proč mi chodí upozornění?", emoji="ℹ️", style=discord.ButtonStyle.link,
                                    url=base_url + "/proc-notifikace"))
    view.add_item(discord.ui.Button(label="Podpora", emoji="💬", style=discord.ButtonStyle.link, url=base_url + "/podpora"))
    return view


SAMPLES = {
    "arrival": {"title": "🚌 Linka 722 přijíždí k zastávce Plasy", "color": COLORS["arrival"],
                "description": "Sledovaný spoj právě **přijíždí** k zastávce.",
                "fields": [{"name": "Linka", "value": "722"}, {"name": "SPZ", "value": "2P5 1234"},
                           {"name": "Zpoždění", "value": delay_badge(0)},
                           {"name": "Příjezd", "value": "14:32"}, {"name": "Zastávka", "value": "Plasy, nám."},
                           {"name": "Mapa", "value": "[Zobrazit na mapě](https://datacorebot.koyeb.app/mapa)"}],
                "footer": {"text": "Pravidlo č. 12"}},
    "delay": {"title": "⏱️ Linka 722 má zpoždění", "color": COLORS["delay"],
              "description": "Spoj **14:20 Plzeň → Plasy** jede se zpožděním.",
              "fields": [{"name": "Linka", "value": "722"}, {"name": "SPZ", "value": "2P5 1234"},
                         {"name": "Zpoždění", "value": delay_badge(12)},
                         {"name": "Nový příjezd", "value": "14:44"}],
              "footer": {"text": "Pravidlo č. 12"}},
    "admin": {"title": "Plánovaná údržba dnes večer", "color": COLORS["admin"],
              "description": "Dnes od **22:00** do 23:00 bude web krátce nedostupný. Děkujeme za trpělivost.",
              "fields": []},
}

if __name__ == "__main__":
    import json
    out = {k: enhance(v, "admin_direct_1" if k == "admin" else 12) for k, v in SAMPLES.items()}
    json.dump(out, open("discord-vzory.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("hotovo")
