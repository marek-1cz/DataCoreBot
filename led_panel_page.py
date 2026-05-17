HTML_LED_PANEL_LANDING = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LED Panel Simulátor</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
body { margin: 0; background: #0f172a; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: "Segoe UI", sans-serif; }
.card { text-align: center; padding: 60px 40px; background: #1e293b; border-radius: 16px; border: 1px solid #334155; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
h1 { color: #f59e0b; font-size: 28px; margin: 0 0 12px 0; letter-spacing: 1px; }
p { color: #94a3b8; font-size: 14px; line-height: 1.7; margin: 0 0 36px 0; }
.btn-open { display: inline-block; background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 900; font-size: 18px; padding: 18px 48px; border-radius: 50px; text-decoration: none; cursor: pointer; border: none; transition: 0.2s; box-shadow: 0 5px 20px rgba(245,158,11,0.4); letter-spacing: 1px; }
.btn-open:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(245,158,11,0.6); }
.hint { color: #475569; font-size: 12px; margin-top: 20px; }
</style>
</head>
<body>
<div class="card">
  <h1><i class="fas fa-tv" style="margin-right:10px;"></i>LED Panel Simulátor</h1>
  <p>Simulátor LED destinačních panelů BUSE BS-310 používaných v autobusech Plzeňského kraje. Vyzkoušej si nastavit linku, cílovou zastávku, VIA zastávky nebo upravit font.</p>
  <button class="btn-open" onclick="window.open('/led-panel/app','_blank','width=1400,height=900,scrollbars=yes')">
    <i class="fas fa-play"></i> Spustit simulátor
  </button>
  <div class="hint"><i class="fas fa-info-circle"></i> Otevře se v novém okně &nbsp;·&nbsp; Tvoje nastavení a úpravy fontu se ukládají do prohlížeče</div>
</div>
</body>
</html>
"""
