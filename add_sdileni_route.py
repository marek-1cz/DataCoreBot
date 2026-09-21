import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

html_page = '''
@app.route('/mobilni-sdileni')
def mobilni_sdileni_page():
    html = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDPK Ovladač - Mobilní Zrcadlo</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --primary: #035689; --secondary: #023e63; --accent: #F4CC17; --text: #f0f0f0; --bg: #0b1121; }
        * { box-sizing: border-box; }
        body { margin: 0; padding: 0; background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; }
        
        .header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 60px 20px; text-align: center; border-bottom: 3px solid var(--accent); }
        .header h1 { margin: 0 0 10px 0; font-size: 32px; letter-spacing: 1px; color: white; }
        .header p { margin: 0; font-size: 18px; color: rgba(255,255,255,0.8); }
        
        .badge { display: inline-block; background: var(--accent); color: #000; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; margin-bottom: 15px; }
        
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        
        .card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 25px; margin-bottom: 30px; }
        .card h2 { color: var(--accent); margin-top: 0; font-size: 22px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        
        .steps { padding-left: 20px; margin-bottom: 0; }
        .steps li { margin-bottom: 15px; font-size: 16px; }
        .steps li::marker { color: var(--accent); font-weight: bold; }
        
        .faq-item { margin-bottom: 20px; }
        .faq-q { font-weight: 600; font-size: 17px; margin-bottom: 5px; color: white; display: flex; align-items: flex-start; gap: 8px; }
        .faq-a { color: rgba(255,255,255,0.7); margin: 0 0 0 25px; }
        
        .footer { text-align: center; padding: 30px; color: rgba(255,255,255,0.5); font-size: 14px; margin-top: 20px; }
        .back-btn { display: inline-block; background: rgba(255,255,255,0.1); color: white; text-decoration: none; padding: 10px 20px; border-radius: 8px; margin-top: 20px; transition: 0.2s; }
        .back-btn:hover { background: rgba(255,255,255,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <span class="badge">Premium / Beta Tester</span>
        <h1><i class="fas fa-mobile-alt"></i> Ovladač v Kapse</h1>
        <p>Propojte svůj telefon s palubním počítačem a ovládejte hru odkudkoliv.</p>
    </div>
    
    <div class="container">
        <div class="card">
            <h2><i class="fas fa-magic"></i> Jak to funguje?</h2>
            <p>Funkce <strong>Mobilní zrcadlo</strong> umožňuje živě přenášet obrazovku palubního počítače z vašeho monitoru přímo do mobilu. Všechna tlačítka na mobilu okamžitě reagují ve hře na počítači. Nemusíte přepínat okna!</p>
            <ol class="steps">
                <li>Otevřete Palubní Počítač na PC (Ovladač).</li>
                <li>Klikněte vpravo nahoře na žlutou ikonku <strong>hvězdičky</strong> (nebo nastavení zrcadla).</li>
                <li>Vezměte svůj mobil a <strong>naskenujte zobrazený QR kód</strong> fotoaparátem.</li>
                <li>Otevřete odkaz a hotovo! Váš mobil je nyní plnohodnotný ovladač.</li>
            </ol>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-life-ring"></i> Řešení problémů (FAQ)</h2>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Prohlížeč v mobilu mě po čase odpojí</div>
                <p class="faq-a">Zrcadlo vyžaduje nepřetržité spojení. Pokud vám zhasne displej nebo aplikaci minimalizujete, prohlížeč spojení ukončí. <strong>Řešení:</strong> Nastavte si v mobilu, aby displej nezhasínal, nebo nechte stránku neustále otevřenou.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Stránka ukazuje "SPOJENÍ PŘERUŠENO"</div>
                <p class="faq-a">Váš počítač přestal odesílat data. To se stane, pokud aplikaci zavřete, nebo pokud má PC výpadek internetu. <strong>Řešení:</strong> Restartujte Palubní Počítač na PC a znovu načtěte stránku na mobilu.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Tlačítka reagují opožděně</div>
                <p class="faq-a">Spojení je závislé na rychlosti vašeho internetu (obě zařízení komunikují přes server). Doporučujeme mít jak PC, tak mobil připojené na stabilní Wi-Fi nebo 4G/5G síť.</p>
            </div>
            
            <div class="faq-item">
                <div class="faq-q"><i class="fas fa-exclamation-circle" style="color: #e74c3c; margin-top: 3px;"></i> Jsem Beta Tester, ale QR kód se mi neukazuje</div>
                <p class="faq-a">Ujistěte se, že jste v Launcheru přihlášeni přes Discord a máte příslušnou roli na našem Discord serveru. Zkuste se případně v Launcheru odhlásit a znovu přihlásit.</p>
            </div>
        </div>
        
        <div style="text-align: center;">
            <a href="javascript:history.back()" class="back-btn"><i class="fas fa-arrow-left"></i> Zpět</a>
        </div>
    </div>
    
    <div class="footer">
        &copy; 2026 IDPK OIS - Vytvořeno pro komunitu
    </div>
</body>
</html>
    """
    return render_template_string(html)

def check_and_download_latest_gtfs():
'''

pattern = re.compile(r'def check_and_download_latest_gtfs\(\):')
if pattern.search(code):
    new_code = pattern.sub(html_page, code)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print("New route added successfully!")
else:
    print("Could not find the target string to replace.")
