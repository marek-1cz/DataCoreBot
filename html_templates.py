window.onerror = function(message, source, lineno, colno, error) {
    let errBox = document.getElementById('fatal-error-box');
    if (!errBox) {
        errBox = document.createElement('div');
        errBox.id = 'fatal-error-box';
        errBox.style.cssText = "position:fixed; top:0; left:0; width:100%; height:100%; background:#c0392b; color:white; z-index:9999999; padding:20px; font-weight:bold; overflow-y:auto; box-sizing:border-box;";
        document.body.appendChild(errBox);
    }
    
    let isCrit = errBox.innerHTML.includes('Kritická chyba');
    
    errBox.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid white; padding-bottom:10px; margin-bottom:10px;">
        <span style="font-size:20px;">Kritická chyba systému</span>
        <button onclick="document.getElementById('fatal-error-box').style.display='none'" style="background:black; color:white; border:1px solid white; padding:5px 15px; cursor:pointer; font-weight:bold;">ZAVŘÍT</button>
    </div>
    <p>${message}<br>Řádek: ${lineno}</p>
    ` + (isCrit ? errBox.innerHTML.split('</div>')[1] : '');
    
    errBox.style.display = 'block';
    console.error(`[IGNOROVANÝ ERROR] ${message} (Line ${lineno})`);

    let dId = localStorage.getItem('discordId') || "Neznámý";
    let nick = localStorage.getItem('discordNick') || "Neznámý";
    fetchBlesk(`${API_BASE}/api/report_error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discord_id: dId, nick: nick, type: "SYSTÉMOVÝ ERROR", message: `${message} na řádku ${lineno}` })
    }, 3000).catch(()=>{});

    return true; 
};

process.on('unhandledRejection', (reason) => { 
    window.onerror("Unhandled Promise: " + reason, "", 0, 0, null); 
});

console.log("== PALUBNÍ SYSTÉM - INICIALIZACE ==");

const { ipcRenderer } = require('electron');
const path = require('path');
const processCore = require('process');

const API_BASE = 'https://datacorebot.koyeb.app';
const APP_VERSION = "V1.5.1 RC"; // UPRAV PODLE VERZE, KTEROU MÁŠ V DATABÁZI

let isDevMode = false;
try { isDevMode = !__dirname.includes('app.asar'); } catch (e) { isDevMode = false; }

function getBasePath() { 
    try { return isDevMode ? __dirname : path.dirname(processCore.execPath); } 
    catch(e) { return __dirname; }
}

function debugLog(msg) {
    console.log(msg);
    let dt = document.getElementById('debug-text');
    if (dt) { 
        dt.innerHTML += `<span style="color:#0f0;">[${new Date().toLocaleTimeString()}]</span> ${msg}\n`; 
        dt.scrollTop = dt.scrollHeight; 
    }
}

window.playClick = function() { 
    try {
        let clickEl = document.getElementById('sound-click');
        if (!clickEl) {
            clickEl = document.createElement('audio');
            clickEl.id = 'sound-click';
            clickEl.src = "file:///" + path.join(getBasePath(), 'zvuky', 'Click.wav').replace(/\\/g, '/');
            document.body.appendChild(clickEl);
        }
        clickEl.currentTime = 0; 
        let p = clickEl.play(); 
        if (p !== undefined) p.catch(e => {});
    } catch(e) {}
};

let appState = 'BOOT'; 
let linkospojFocus = 'input'; 
let isListOpen = false;
let inputValues = { discordId: "", pinSetup: "", pinEnter: "", linkospoj: "", idpk: "" };
let machineHWID = localStorage.getItem('device_hwid') || "UNKNOWN-HWID"; 
let storedDiscordId = ""; 
let storedAppId = ""; 
let currentSessionId = localStorage.getItem('currentSessionId') || "";
let discordPollInterval = null; 
let pingInterval = null;

let availableFiles = []; 
let filteredFiles = []; 
let databaseFiles = []; 
let selectedListIndex = -1; 
let selectedIdpkRouteId = ""; 
let selectedStartStop = ""; 
let selectedDestination = "";

let currentHybridTemplate = null; 
let routeData = { line: "", routeId: "", destination: "", stops: [], realStopIndex: 0, previewStopIndex: 0, linkospojCode: "", nextTurnus: null, isMuted: false };
let drivePhase = 0; 
let stopSelectionBuffer = ""; 
let isAnnouncementPlaying = false; 
let isSystemLoading = true;

let stopPressed = false; 
let audioQueue = []; 
let isPlayingQueue = false; 
let pendingStopSound = false; 
let isStopCooldown = false;
let lastPlayedSequence = [];
window.currentAnnouncingStopName = ""; 

let isDelayMode = false; 
let isTimeBasedAuto = false; 
let isClassicAuto = false; 
let isDelayAuto = false; 
let isRandomContinue = false;
let classicAutoDelay = 5; 
let useFictionalTime = false; 
let fictionalTimeOffset = 0; 
let classicAutoTimer = null; 
let currentGlobalDelay = 0; 
let lockedAutoDelayMins = null; 
let lockedAutoStartTimeMins = null; 
let autoAnnounceCooldown = false; 
let routeStartupWait = false; 
let randomHistory = [];
let logoutConfirmStep = false; 
let currentAnnouncementId = null;
let currentAnnouncementIndex = 0;
const audioPlayer = new Audio();

let statsStartTime = 0;
let statsAnnouncedStops = [];
let statsUniqueStopsCount = 0;
let isStatsActive = false;

window.initStatsTracking = function() {
    statsStartTime = Date.now();
    statsAnnouncedStops = [];
    statsUniqueStopsCount = 0;
    isStatsActive = true;
};

window.trackStopAnnouncement = function(stopName) {
    if (!isStatsActive || !stopName) return;
    statsAnnouncedStops.push(stopName);
    let uniqueStops = [...new Set(statsAnnouncedStops)];
    statsUniqueStopsCount = uniqueStops.length;
};

window.submitStats = function() {
    if (!isStatsActive || !routeData.line) return;
    let timePlayed = Date.now() - statsStartTime;
    if (timePlayed > 30000 || statsUniqueStopsCount >= 2) {
        let dId = localStorage.getItem('discordId') || storedDiscordId || "";
        fetchBlesk(`${API_BASE}/api/submit_stats`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ line: routeData.line, stops: statsAnnouncedStops, discord_id: dId }),
            keepalive: true
        }, 3000).catch(e => {});
    }
    isStatsActive = false; 
};

async function fetchBlesk(url, options, msTimeout = 4000) {
    const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error("Timeout sítě")), msTimeout));
    return Promise.race([fetch(url, options), timeout]);
}

async function zanalyzujPripojeni() {
    if (!navigator.onLine) return { status: "WIFI_OFF", zprava: "Hrajete v OFFLINE režimu." };
    try {
        let response = await fetchBlesk(`${API_BASE}/api/status`, { method: 'GET' }, 4000);
        if (response.ok) return { status: "OK", zprava: "OK" };
        else return { status: "KOYEB_ERROR", zprava: "Databáze aktuálně neodpovídá.<br><br>Byli jste přepnuti do <b>OFFLINE režimu</b>." };
    } catch (error) {
        try {
            await fetchBlesk("https://1.1.1.1", { mode: 'no-cors' }, 3000);
            return { status: "BLOCKED_BY_FIREWALL", zprava: "Váš internet funguje, ale spojení aplikace bylo ZABLOKOVÁNO! (Antivirus/Firewall)" };
        } catch (cloudflareError) {
            return { status: "NO_INTERNET", zprava: "Váš počítač nemá přístup k internetu." };
        }
    }
}

window.showErrorModal = function(title, msg, isVersionBlock = false, type = 'error') {
    try {
        window.playClick();
        let msgEl = document.getElementById('error-msg-text');
        let modalEl = document.getElementById('error-modal');
        let hwidBtn = document.getElementById('error-hwid-btn');
        let isGlobalShutdown = msg.includes('VYPNUT') || msg.includes('vypnut');

        let color = "#e74c3c"; let icon = '<i class="fas fa-times-circle"></i>';
        if (type === 'info') { color = "#38bdf8"; icon = '<i class="fas fa-info-circle"></i>'; } 
        else if (type === 'warning') { color = "#f59e0b"; icon = '<i class="fas fa-shield-alt"></i>'; }

        if (msgEl) msgEl.innerHTML = `<span style="color:${color}; font-size:18px; font-weight:bold; text-transform:uppercase;">${icon} ${title}</span><br><br><span style="color:var(--text-main); font-size:14px; line-height:1.5;">${msg}</span>`;
        
        if (modalEl) {
            let allBtns = modalEl.querySelectorAll('button');
            allBtns.forEach(b => {
                if (!b.hasAttribute('data-custom-btn') && b.id !== 'error-hwid-btn') {
                    b.style.display = (isVersionBlock || isGlobalShutdown) ? 'none' : 'block';
                }
            });
        }
        
        if (hwidBtn) hwidBtn.style.display = (!isVersionBlock && !isGlobalShutdown && type === 'error' && (msg.includes('HWID') || msg.includes('IP adresa'))) ? 'block' : 'none';
        
        if (isGlobalShutdown) {
            if (msgEl && !msgEl.innerHTML.includes('UKONČIT')) {
                msgEl.innerHTML += `<br><br><div style="display:flex; gap:15px; justify-content:center; margin-top:20px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.1);"><button data-custom-btn="true" onclick="window.closeApp()" style="background:#c0392b; color:white; border:none; padding:12px 15px; cursor:pointer; font-weight:bold; border-radius:5px; flex:1;"><i class="fas fa-power-off"></i> UKONČIT APLIKACI</button></div>`;
            }
        } else if (isVersionBlock) {
            if (msgEl && !msgEl.innerHTML.includes('ADMIN BYPASS')) {
                msgEl.innerHTML += `<br><br><div style="display:flex; gap:15px; justify-content:center; margin-top:20px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.1);"><button data-custom-btn="true" onclick="window.closeApp()" style="background:#c0392b; color:white; border:none; padding:12px 15px; cursor:pointer; font-weight:bold; border-radius:5px; flex:1;"><i class="fas fa-power-off"></i> UKONČIT</button><button data-custom-btn="true" onclick="window.requestAdminBypass()" style="background:#f59e0b; color:black; border:none; padding:12px 15px; cursor:pointer; font-weight:bold; border-radius:5px; flex:1;"><i class="fas fa-unlock"></i> ADMIN BYPASS</button></div>`;
            }
        }
        if (modalEl) modalEl.style.display = 'flex';
        let loadEl = document.getElementById('loadingScreen');
        if (loadEl) loadEl.style.display = 'none';
    } catch(err) {}
};

window.closeErrorModal = function() {
    window.playClick(); 
    let modalEl = document.getElementById('error-modal');
    if (modalEl) modalEl.style.display = 'none'; 
    if (appState === 'LOGIN_WAITING') window.resetLoginFlow();
    else if (appState === 'LOGIN_DISCORD') {
        let inputEl = document.getElementById('login-identifier-input');
        if (inputEl) inputEl.focus();
    }
};

window.padTime = function(t) { 
    if(!t) return t; 
    let str = t.toString();
    if(!str.includes(':')) return str; 
    let p = str.split(':'); 
    let res = (p[0].length === 1 ? '0'+p[0] : p[0]) + ':' + (p[1].length === 1 ? '0'+p[1] : p[1]); 
    if (p[2]) res += ':' + (p[2].length === 1 ? '0'+p[2] : p[2]); 
    return res; 
};

window.timeToMins = function(t) { 
    if(!t) return 0; 
    let str = t.toString();
    if(!str.includes(':')) return 0; 
    let p = str.split(':'); 
    return parseInt(p[0]) * 60 + parseInt(p[1]); 
};

window.minsToTime = function(m) { 
    let h = Math.floor(m / 60) % 24; 
    let mn = m % 60; 
    if (h < 0) h += 24; 
    if (mn < 0) mn += 60; 
    return (h < 10 ? '0'+h : h) + ':' + (mn < 10 ? '0'+mn : mn); 
};

window.isModalOpen = function() { 
    return document.getElementById('funk-modal').style.display === 'flex' || 
           document.getElementById('settings-modal').style.display === 'flex' || 
           document.getElementById('error-modal').style.display === 'flex' || 
           document.getElementById('supporters-modal').style.display === 'flex' ||
           document.getElementById('feedback-modal').style.display === 'flex' ||
           document.getElementById('debug-overlay').style.display === 'flex' ||
           document.getElementById('announcement-modal').style.display === 'flex'; 
};

window.setDelayMode = function(state) { 
    if (isDelayMode !== state) { 
        isDelayMode = state; 
        window.updateBtnState('btn-delay-mode', isDelayMode); 
    } 
};

function safeGetHWID() {
    return Promise.race([
        ipcRenderer.invoke('get-hwid'),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout HWID')), 3000))
    ]);
}

window.addEventListener('beforeunload', () => {
    window.submitStats(); 
    if (!appState.startsWith('LOGIN') && appState !== 'LOCKED' && storedDiscordId) {
        fetchBlesk(`${API_BASE}/api/app_ping`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ discord_id: storedDiscordId, action: 'stop', session_id: currentSessionId }),
            keepalive: true
        }, 3000).catch(e=>{});
    }
});

window.checkAnnouncementsFromWeb = async function(discordId, appId) {
    try {
        if (!discordId) return;
        
        let loadEl = document.getElementById('loadingScreen');
        let msgEl = document.getElementById('loading-msg');
        if(loadEl && msgEl) {
            msgEl.textContent = "KONTROLA OZNÁMENÍ...";
            loadEl.style.zIndex = "999999"; 
            loadEl.style.display = 'flex';
        }

        const response = await fetchBlesk(`${API_BASE}/api/get_messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_id: discordId, app_id: appId })
        }, 5000);
        
        if(loadEl && msgEl) {
            loadEl.style.display = 'none';
            msgEl.textContent = "NAČÍTÁM DATA...";
            loadEl.style.zIndex = "50000";
        }

        const resData = await response.json();
        
        if (resData.messages && resData.messages.length > 0) {
            window.announcementList = resData.messages;
            window.showAnnouncement(0);
        }
    } catch (e) {
        debugLog("Nepodařilo se zkontrolovat oznámení z webu.");
        let loadEl = document.getElementById('loadingScreen');
        if(loadEl) {
            loadEl.style.display = 'none';
            loadEl.style.zIndex = "50000";
        }
    }
};

window.showAnnouncement = function(index) {
    if (!window.announcementList || index >= window.announcementList.length) return;
    const msg = window.announcementList[index];
    
    currentAnnouncementId = msg.id;
    currentAnnouncementIndex = index;
    
    let titleEl = document.getElementById('announcement-title');
    let textEl = document.getElementById('announcement-text');
    let btnEl = document.getElementById('announcement-link-btn');
    
    if (titleEl) titleEl.innerText = msg.title;
    if (textEl) textEl.innerHTML = msg.content;
    
    if (btnEl) {
        if (msg.link_url && msg.link_url.trim() !== '') {
            btnEl.style.display = 'block';
            btnEl.setAttribute('data-url', msg.link_url);
        } else {
            btnEl.style.display = 'none';
        }
    }
    
    document.getElementById('announcement-modal').style.display = 'flex';
};

window.openAnnouncementLink = function() {
    window.playClick();
    let btnEl = document.getElementById('announcement-link-btn');
    if (btnEl && btnEl.getAttribute('data-url')) {
        require('electron').shell.openExternal(btnEl.getAttribute('data-url'));
    }
};

window.closeAnnouncement = function() {
    window.playClick();
    document.getElementById('announcement-modal').style.display = 'none';
    
    if (currentAnnouncementId && storedDiscordId) {
        fetchBlesk(`${API_BASE}/api/mark_message_read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_id: storedDiscordId, message_id: currentAnnouncementId })
        }, 4000).catch(() => {});
    }
    
    window.showAnnouncement(currentAnnouncementIndex + 1);
};

window.openFeedback = function(type) {
    window.playClick();
    
    let errMod = document.getElementById('error-modal');
    if (errMod && errMod.style.display === 'flex') errMod.style.display = 'none';
    
    let setMod = document.getElementById('settings-modal');
    if (setMod && setMod.style.display === 'flex') setMod.style.display = 'none';

    let mod = document.getElementById('feedback-modal');
    if (mod) mod.style.display = 'flex';
    
    document.getElementById('fb-type').value = type;
    document.getElementById('fb-text').value = ''; 
    
    let dId = localStorage.getItem('discordId') || storedDiscordId || 'Není zadáno';
    let nick = localStorage.getItem('discordNick') || 'Neznámý Uživatel';
    
    let inEl = document.getElementById('login-identifier-input');
    if (dId === 'Není zadáno' && inEl && inEl.value) { dId = inEl.value; nick = inEl.value; }
    
    document.getElementById('fb-nick').textContent = nick;
    document.getElementById('fb-id').textContent = dId;
    
    if (type === 'HWID') {
        document.getElementById('fb-text').placeholder = "Žádám o reset HWID k tomuto účtu z důvodu: \n(Napište důvod - např. nový počítač, reinstalace Windows...)";
    } else {
        document.getElementById('fb-text').placeholder = "Napište svou zprávu, návrh na zlepšení nebo žádost zde...";
    }
};

window.submitFeedback = async function() {
    window.playClick();
    let text = document.getElementById('fb-text').value.trim();
    let type = document.getElementById('fb-type').value;
    
    let dId = localStorage.getItem('discordId') || storedDiscordId;
    let nick = localStorage.getItem('discordNick') || 'Neznámý Uživatel';
    
    let inEl = document.getElementById('login-identifier-input');
    if (!dId && inEl && inEl.value) { dId = inEl.value; nick = inEl.value; }
    
    if (!dId || dId.toLowerCase() === "není zadáno" || dId.toLowerCase() === "none" || dId.trim() === "") {
        return window.showErrorModal("CHYBÍ ÚDAJE", "Systém ztratil vaše identifikační údaje (např. z důvodu nepodporovaných znaků v nicku).\n\nAbychom váš účet našli, musíte ZAVŘÍT toto okno, vrátit se k žádosti a NAPSAT SVÉ ČÍSELNÉ DISCORD ID přímo do textu zprávy!", false, 'warning');
    }

    if (!text) return window.showErrorModal("CHYBA", "Zpráva nemůže být prázdná.");

    let loadEl = document.getElementById('loadingScreen');
    if (loadEl) loadEl.style.display = 'flex';

    try {
        let res = await fetchBlesk(`${API_BASE}/api/submit_feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_id: dId, nick: nick, type: type, message: text })
        }, 6000);
        
        if (loadEl) loadEl.style.display = 'none';
        let data = await res.json();
        
        if (data.status === 'success') {
            document.getElementById('feedback-modal').style.display = 'none';
            if (type === 'HWID') {
                let hwidScr = document.getElementById('hwid-success-screen');
                if (hwidScr) hwidScr.style.display = 'flex';
            } else {
                setTimeout(() => { alert("Úspěšně odesláno! Děkujeme za zpětnou vazbu."); }, 100);
            }
        } else {
            window.showErrorModal("CHYBA", "Odeslání selhalo: " + data.message);
        }
    } catch(e) {
        if (loadEl) loadEl.style.display = 'none';
        window.showErrorModal("CHYBA SPOJENÍ", "Nelze se spojit se serverem. Zkontrolujte připojení.");
    }
};

window.closeApp = function() {
    window.playClick();
    window.submitStats(); 
    try { ipcRenderer.send('quit-app'); } catch(e) {}
    window.close();
};

window.requestAdminBypass = async function() {
    window.playClick();
    let dId = localStorage.getItem('discordId') || storedDiscordId;
    let nick = localStorage.getItem('discordNick') || 'Neznámý Uživatel';
    
    let inEl = document.getElementById('login-identifier-input');
    if (!dId && inEl && inEl.value) { dId = inEl.value; nick = inEl.value; }
    
    if (!dId || dId.toLowerCase() === "není zadáno" || dId.toLowerCase() === "none") {
        alert("Nejprve prosím zadejte své číslo ID nebo jednoduchý Nick (bez emoji) do políčka, abychom věděli, pro koho žádost poslat.");
        window.closeErrorModal();
        return;
    }

    let loadEl = document.getElementById('loadingScreen');
    if (loadEl) loadEl.style.display = 'flex'; 

    try {
        let res = await fetchBlesk(`${API_BASE}/api/submit_feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_id: dId, nick: nick, type: 'ADMIN_BYPASS', message: 'Žádost o jednorázový Admin Bypass pro starou verzi.' })
        }, 6000);
        if (loadEl) loadEl.style.display = 'none';
        let data = await res.json();
        
        if (data.status === 'success') {
            alert("Žádost úspěšně odeslána! Jakmile ji administrátor na webu schválí, zkuste se přihlásit znovu. Bude vám povolen jednorázový vstup.");
            window.closeApp();
        } else {
            alert("Chyba při odesílání: " + data.message);
        }
    } catch(e) {
        if (loadEl) loadEl.style.display = 'none';
        alert("Nelze se spojit se serverem. Zkontrolujte připojení k internetu.");
    }
};

document.addEventListener('DOMContentLoaded', async () => {
    debugLog("DOM Načten, startuji a otevírám bootovací obrazovku.");
    
    setTimeout(() => {
        let allEls = document.querySelectorAll('*');
        allEls.forEach(el => {
            if(el.getAttribute('onclick') && el.getAttribute('onclick').includes('switchToIdpkMode')) {
                if(!el.innerHTML.includes('bez zvuku')) {
                    el.innerHTML += " <span style='font-size:10px; color:#f59e0b;'>(bez zvuku)</span>";
                }
            }
        });
        
        let debugWrap = document.getElementById('debug-overlay');
        if (debugWrap && !document.getElementById('copy-log-btn')) {
            let btn = document.createElement('button');
            btn.id = 'copy-log-btn';
            btn.innerHTML = '<i class="fas fa-copy"></i> Zkopírovat log';
            btn.style.cssText = "margin-top:10px; width:100%; padding:10px; background:#38bdf8; border:none; color:black; font-weight:bold; border-radius:5px; cursor:pointer;";
            btn.onclick = function() {
                let dt = document.getElementById('debug-text');
                if (dt) {
                    let text = dt.innerText;
                    navigator.clipboard.writeText(text);
                    btn.innerHTML = '<i class="fas fa-check"></i> Zkopírováno!';
                    setTimeout(() => btn.innerHTML = '<i class="fas fa-copy"></i> Zkopírovat log', 2000);
                }
            };
            
            let dt = document.getElementById('debug-text');
            if (dt && dt.parentNode) {
                dt.parentNode.insertBefore(btn, dt.nextSibling);
            }
        }
    }, 500);

    if (isDevMode) debugLog("⚠️ DETEKOVÁN VSC (VÝVOJÁŘSKÝ REŽIM) - BLOKACE IGNOROVÁNY!");

    ipcRenderer.invoke('get-link-files').then(files => { 
        availableFiles = files; 
        filteredFiles = files; 
    }).catch(()=>{});
    
    ipcRenderer.invoke('gtfs-load-routes').then(db => { 
        databaseFiles = db; 
    }).catch(()=>{});

    ipcRenderer.on('trigger-key-action', (event, payload) => {
        let k = typeof payload === 'string' ? payload : payload.key;
        let c = typeof payload === 'object' ? payload.code : '';
        window.handleKeyInput(k, c);
    });

    document.addEventListener('click', (e) => {
        if (appState === 'LOGIN_DISCORD' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TEXTAREA') {
            let i = document.getElementById('login-identifier-input');
            if (i && !i.disabled && !window.isModalOpen()) i.focus();
        }
    });

    if (machineHWID === "UNKNOWN-HWID" || machineHWID === "PENDING" || !machineHWID.startsWith("PC-")) {
        try {
            let hw = await safeGetHWID();
            if (hw && hw !== "" && !hw.includes("UNKNOWN") && hw.startsWith("PC-")) {
                machineHWID = hw;
            } else {
                machineHWID = "PC-" + Math.random().toString(36).substring(2, 12).toUpperCase();
            }
        } catch(e) {
            machineHWID = "PC-" + Math.random().toString(36).substring(2, 12).toUpperCase();
        }
        localStorage.setItem('device_hwid', machineHWID);
    }
    
    debugLog("Unikátní HWID tohoto PC je: " + machineHWID);

    let startEl = document.getElementById('startupScreen');
    if (startEl) startEl.style.display = 'flex';
    ipcRenderer.send('panel-boot');

    let pripojeni = await zanalyzujPripojeni();
    let isServerOnline = (pripojeni.status === "OK");
    let ksStatus = 'enabled';

    if (isServerOnline) {
        try {
            const res = await fetchBlesk(`${API_BASE}/api/status`, { method: 'GET' }, 4000);
            const data = await res.json();
            ksStatus = data.status;
            localStorage.setItem('lastKillSwitchState', ksStatus);
            debugLog("Server je online. Kill-Switch stav: " + ksStatus);
        } catch (e) {
            isServerOnline = false;
        }
    }

    if (!isServerOnline) {
        ksStatus = localStorage.getItem('lastKillSwitchState') || 'enabled';
        debugLog("Server nedostupný (offline). Poslední známý stav KS: " + ksStatus);
        
        if (pripojeni.status === "BLOCKED_BY_FIREWALL") {
            window.showErrorModal("ZABLOKOVÁNO ANTIVIREM", pripojeni.zprava, false, 'warning');
        } else {
            window.showErrorModal("INFORMAČNÍ SYSTÉM", pripojeni.zprava, false, 'info');
        }
    }

    if (ksStatus === 'disabled') {
        if (isDevMode) {
            debugLog("⚠️ VSC REŽIM: Ignoruji Globální Kill-Switch!");
        } else {
            if (startEl) startEl.style.display = 'none';
            appState = 'LOCKED';
            sessionStorage.removeItem('softResetState'); 
            
            if (!isServerOnline) {
                window.showErrorModal("SYSTÉM UZAMČEN", "Při posledním připojení byl software GLOBÁLNĚ VYPNUT. Pro odemčení se musíte připojit k internetu.", true, 'error');
            } else {
                window.showErrorModal("SYSTÉM UZAMČEN", "SOFTWARE JE NYNÍ GLOBÁLNĚ VYPNUT (ÚDRŽBA).", true, 'error');
            }
            return; 
        }
    }

    const savedStateStr = sessionStorage.getItem('softResetState');
    if (savedStateStr) {
        sessionStorage.removeItem('softResetState'); 
        const state = JSON.parse(savedStateStr);
        
        appState = state.appState; 
        inputValues = state.inputValues;
        linkospojFocus = state.linkospojFocus; 
        isListOpen = state.isListOpen; 
        selectedIdpkRouteId = state.selectedIdpkRouteId;
        selectedStartStop = state.selectedStartStop; 
        selectedDestination = state.selectedDestination;
        currentHybridTemplate = state.currentHybridTemplate; 
        routeData = state.routeData;
        drivePhase = state.drivePhase; 
        stopSelectionBuffer = state.stopSelectionBuffer; 
        stopPressed = state.stopPressed;
        isDelayMode = state.isDelayMode; 
        isTimeBasedAuto = state.isTimeBasedAuto; 
        isClassicAuto = state.isClassicAuto;
        isDelayAuto = state.isDelayAuto; 
        isRandomContinue = state.isRandomContinue; 
        classicAutoDelay = state.classicAutoDelay;
        useFictionalTime = state.useFictionalTime; 
        fictionalTimeOffset = state.fictionalTimeOffset;
        currentGlobalDelay = state.currentGlobalDelay; 
        lockedAutoDelayMins = state.lockedAutoDelayMins;
        lockedAutoStartTimeMins = state.lockedAutoStartTimeMins;
        storedDiscordId = localStorage.getItem('discordId') || "";
        storedAppId = localStorage.getItem('appId') || "";

        if (startEl) startEl.style.display = 'none';
        document.querySelectorAll('.login-view').forEach(v => { v.style.display = 'none'; });

        ipcRenderer.send('open-panel-window');

        if (appState === 'DRIVE') {
            window.switchToDriveScreen();
            setTimeout(() => window.sendDataToPanel(drivePhase === 1), 1000);
        } else if (appState === 'LINKOSPOJ') {
            window.switchToLinkospojScreen();
            ipcRenderer.send('panel-idle');
        } else {
            window.switchToIdpkMode();
            ipcRenderer.send('panel-idle');
        }
        window.startPingLoop();
        
        if (storedDiscordId && isServerOnline) {
            let loadEl = document.getElementById('loadingScreen');
            let msgEl = document.getElementById('loading-msg');
            if(loadEl && msgEl) {
                msgEl.textContent = "OBNOVA SYSTÉMU...";
                loadEl.style.zIndex = "999999"; 
                loadEl.style.display = 'flex';
            }
            setTimeout(() => {
                window.checkAnnouncementsFromWeb(storedDiscordId, storedAppId);
            }, 4000);
        }
    } else {
        window.initLoginFlow(isServerOnline);
    }

    setInterval(window.timeLoop, 1000);
});

window.toggleSettings = function() { 
    window.playClick(); 
    let el = document.getElementById('settings-modal');
    let authOnly = document.getElementById('auth-only-settings');

    if (el) { 
        if (el.style.display === 'flex') {
            el.style.display = 'none';
        } else {
            if (authOnly) {
                if (appState.startsWith('LOGIN') || appState === 'BOOT' || appState === 'LOCKED') {
                    authOnly.style.display = 'none';
                } else {
                    authOnly.style.display = 'flex';
                }
            }
            el.style.display = 'flex';
        }
    }
};

window.fullReset = function() { 
    window.playClick(); 
    location.reload(); 
};

window.softReset = function() {
    if (appState === 'LOCKED') return; 
    window.playClick();
    window.submitStats(); 
    
    const stateToSave = {
        appState, inputValues, linkospojFocus, isListOpen, selectedIdpkRouteId,
        selectedStartStop, selectedDestination, currentHybridTemplate, routeData,
        drivePhase, stopSelectionBuffer, stopPressed, isDelayMode, isTimeBasedAuto, isClassicAuto,
        isDelayAuto, isRandomContinue, classicAutoDelay, useFictionalTime, fictionalTimeOffset,
        currentGlobalDelay, lockedAutoDelayMins, lockedAutoStartTimeMins
    };
    sessionStorage.setItem('softResetState', JSON.stringify(stateToSave));
    localStorage.setItem('currentSessionId', currentSessionId);
    location.reload(); 
};

window.refreshPanel = function() { 
    window.playClick(); 
    ipcRenderer.send('reload-panel-window'); 
    setTimeout(() => { 
        if(appState === 'DRIVE') window.sendDataToPanel(drivePhase === 1); 
        else ipcRenderer.send('reset-panel'); 
    }, 2000); 
};

window.openSupporters = async function() {
    window.playClick();
    let mod = document.getElementById('supporters-modal');
    if(mod) mod.style.display = 'flex';
    
    let list = document.getElementById('supporters-list');
    if(list) list.innerHTML = '<div style="color:#aaa; text-align:center; padding-top:20px;">Stahuji data z databáze...<div class="spinner" style="margin:20px auto; width:20px; height:20px; border-width:3px;"></div></div>';

    try {
        let res = await fetchBlesk(`${API_BASE}/api/supporters`, { method: 'GET' }, 8000);
        if (!res.ok) throw new Error("Chyba spojení");
        
        let data = await res.json();
        let sups = data.supporters || data.data || data; 
        
        if (Array.isArray(sups) && sups.length > 0) {
            let htmlStr = "";
            sups.forEach(sup => {
                let name = sup.name || "Anonymní podpora";
                let tier = sup.tier || 1;
                let cardBaseStyle = "box-sizing: border-box; max-width: 100%; word-wrap: break-word; overflow-wrap: break-word; width: 100%; ";
                let cardStyle, nameStyle, titleBadge, amtStyle;

                if (tier === 3) {
                    cardStyle = cardBaseStyle + "border: 2px solid #ff3333; box-shadow: 0 0 30px rgba(255, 51, 51, 0.8); background: linear-gradient(135deg, #330000, #660000); animation: pulseExtreme 1.5s infinite alternate; padding: 20px;";
                    nameStyle = "color: #fff; text-shadow: 0 0 15px #ff3333, 0 0 30px #ff3333; font-size: 22px; font-weight: 900; text-transform: uppercase;";
                    titleBadge = "<div style='color:#ff3333; font-size:10px; font-weight:bold; letter-spacing:2px; margin-bottom:5px; text-shadow:0 0 5px #ff3333;'>MEGA PODPOROVATEL</div>";
                    amtStyle = "background:#ff3333; color:#fff; padding:6px 12px; border-radius:15px; font-weight:bold; font-size:15px; box-shadow:0 0 15px #ff3333; border: 1px solid #fff;";
                } else if (tier === 2) {
                    cardStyle = cardBaseStyle + "border: 1px solid #f59e0b; box-shadow: 0 0 15px rgba(245, 158, 11, 0.5); background: linear-gradient(135deg, #0f172a, #332200); padding: 15px; animation: pulseMedium 2s infinite alternate;";
                    nameStyle = "color: #fcd34d; font-size: 18px; font-weight: bold; text-shadow: 0 0 8px rgba(245, 158, 11, 0.8);";
                    titleBadge = "<div style='color:#f59e0b; font-size:9px; font-weight:bold; letter-spacing:1px; margin-bottom:5px;'>VELKÝ PODPOROVATEL</div>";
                    amtStyle = "background:rgba(245, 158, 11, 0.2); color:#fcd34d; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:14px; border:1px solid #f59e0b; box-shadow:0 0 10px rgba(245, 158, 11, 0.4);";
                } else {
                    cardStyle = cardBaseStyle + "border: 1px solid #38bdf8; background: rgba(15, 23, 42, 0.8); border-left: 4px solid #38bdf8; padding: 12px;";
                    nameStyle = "color: #e0f2fe; font-size: 15px; font-weight: bold; text-shadow: 0 0 5px rgba(56, 189, 248, 0.5);";
                    titleBadge = "<div style='color:#38bdf8; font-size:8px; font-weight:bold; margin-bottom:3px;'>PODPOROVATEL</div>";
                    amtStyle = "background:rgba(56, 189, 248, 0.1); color:#38bdf8; padding:3px 8px; border-radius:10px; font-weight:bold; font-size:12px; border:1px solid #38bdf8;";
                }

                htmlStr += `
                <div style="margin-bottom:20px; border-radius:10px; transition:0.3s; display:flex; flex-direction:column; align-items:center; text-align:center; ${cardStyle}">
                    ${titleBadge}
                    <div style="${nameStyle}; margin-bottom:10px;">${name}</div>
                    <div style="${amtStyle}">${sup.amount}</div>
                    ${sup.message ? `<div style="color:white; font-size:13px; font-style:italic; line-height:1.5; background:rgba(0,0,0,0.3); padding:10px; margin-top:10px; border-radius:6px; border-left:2px solid rgba(255,255,255,0.2); width:100%; box-sizing:border-box; word-wrap:break-word;">"${sup.message}"</div>` : ''}
                    <div style="color:#aaa; font-size:10px; text-align:center; margin-top:10px; padding-top:5px; border-top:1px solid rgba(255,255,255,0.05); width:100%;">${sup.created_at || ''}</div>
                </div>`;
            });
            list.innerHTML = htmlStr;
        } else {
            list.innerHTML = '<div style="color:#aaa; text-align:center; padding-top:20px;">Zatím žádní podporovatelé. Buďte první!</div>';
        }
    } catch(e) {
        if(list) list.innerHTML = `<div style="color:#e74c3c; text-align:center; padding-top:20px; font-weight:bold;">Chyba načítání dat.<br><br><span style="font-size:10px; color:#aaa;">Data ze serveru se zatím nepodařilo získat.</span></div>`;
    }
};

window.closeSupporters = function() {
    window.playClick();
    let mod = document.getElementById('supporters-modal');
    if(mod) mod.style.display = 'none';
};

window.switchLoginView = function(viewId) {
    try {
        document.querySelectorAll('.login-view').forEach(v => { v.style.display = 'none'; });
        let viewEl = document.getElementById(viewId);
        if (viewEl) viewEl.style.display = 'flex';
        
        let keypad = document.getElementById('main-keypad');
        if (viewId === 'login-pin-view') {
            if (keypad) keypad.style.display = 'grid';
            let delKey = document.getElementById('key-del');
            if (delKey) delKey.style.display = 'flex';
            let funkKey = document.getElementById('key-funk');
            if (funkKey) funkKey.style.display = 'none';
            let hwidPin = document.getElementById('hwid-display-pin');
            if (hwidPin) hwidPin.textContent = "HWID: " + machineHWID;
        } else if (viewId === 'login-discord-view') {
            if (keypad) keypad.style.display = 'none';
            setTimeout(() => {
                let inputEl = document.getElementById('login-identifier-input');
                if (inputEl) { inputEl.disabled = false; inputEl.focus(); }
            }, 100);
        } else if (viewId === 'login-auto-view') {
            if (keypad) keypad.style.display = 'none';
            let hwidAuto = document.getElementById('hwid-display-auto');
            if (hwidAuto) hwidAuto.textContent = "HWID: " + machineHWID;
        } else {
            if (keypad) keypad.style.display = 'none';
        }
    } catch(err) {}
}

window.initLoginFlow = async function(isServerOnline = true) {
    try {
        let startEl = document.getElementById('startupScreen');
        if (startEl) startEl.style.display = 'none';
        ipcRenderer.send('panel-idle'); 

        let savedMode = localStorage.getItem('loginMode');
        storedDiscordId = localStorage.getItem('discordId');

        if (savedMode === 'AUTO' && storedDiscordId) {
            if (!isServerOnline) {
                debugLog("Offline režim: Přihlašuji z lokální paměti (AUTO).");
                appState = 'LOGIN_AUTO';
                let nickEl = document.getElementById('auto-login-name');
                if (nickEl) nickEl.textContent = localStorage.getItem('discordNick') || "Řidič (Offline)";
                window.switchLoginView('login-auto-view');
                return;
            }

            try {
                let r = await fetchBlesk(`${API_BASE}/api/silent_check`, { 
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' }, 
                    body: JSON.stringify({ discord_id: storedDiscordId, hwid: machineHWID, app_version: APP_VERSION })
                }, 6000);
                let d = await r.json();
                
                if (isDevMode && d.status === 'error' && (d.message.includes('VYPNUT') || d.message.includes('verzi') || d.message.includes('verze') || d.message.includes('podporována'))) {
                    debugLog("⚠️ VSC REŽIM: Ignoruji blokaci od serveru (" + d.message + ")");
                    d.status = 'success';
                    d.app_id = d.app_id || localStorage.getItem('appId') || 1000;
                }

                if (d.status === 'success') {
                    appState = 'LOGIN_AUTO';
                    let nickEl = document.getElementById('auto-login-name');
                    if (nickEl) nickEl.textContent = localStorage.getItem('discordNick') || "Řidič";
                    if (d.app_id) {
                        storedAppId = d.app_id;
                        localStorage.setItem('appId', storedAppId);
                    }
                    window.switchLoginView('login-auto-view');
                    return;
                } else {
                    let isVerError = d.message && (d.message.toLowerCase().includes('verz') || d.message.toLowerCase().includes('podporována'));
                    window.showErrorModal("ZAMÍTNUTO", d.message || "Tento PC nemá přístup.", isVerError, 'error');
                    window.resetLoginFlow();
                    return;
                }
            } catch(e){ 
                debugLog("Chyba při tichém ověření, fallback na offline režim.");
                appState = 'LOGIN_AUTO';
                let nickEl = document.getElementById('auto-login-name');
                if (nickEl) nickEl.textContent = localStorage.getItem('discordNick') || "Řidič (Offline)";
                window.switchLoginView('login-auto-view');
                return;
            }
        } 
        else if (savedMode === 'PIN' && storedDiscordId) {
            if (!isServerOnline) {
                appState = 'LOGIN_PIN_ENTER';
                inputValues.pinEnter = "";
                window.updatePinVisuals('pinEnter');
                let pinText = document.getElementById('pin-header-text');
                if (pinText) pinText.textContent = "ZADEJTE PIN (OFFLINE)";
                let cancelBtn = document.getElementById('pin-cancel-btn');
                if(cancelBtn) cancelBtn.style.display = 'block';
                window.switchLoginView('login-pin-view');
                return;
            }

            try {
                let r = await fetchBlesk(`${API_BASE}/api/silent_check`, { 
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' }, 
                    body: JSON.stringify({ discord_id: storedDiscordId, hwid: machineHWID, app_version: APP_VERSION })
                }, 6000);
                let d = await r.json();

                if (isDevMode && d.status === 'error' && (d.message.includes('VYPNUT') || d.message.includes('verzi') || d.message.includes('verze') || d.message.includes('podporována'))) {
                    d.status = 'success';
                    d.app_id = d.app_id || localStorage.getItem('appId') || 1000;
                }

                if (d.status === 'success') {
                    appState = 'LOGIN_PIN_ENTER';
                    inputValues.pinEnter = "";
                    window.updatePinVisuals('pinEnter');
                    let pinText = document.getElementById('pin-header-text');
                    if (pinText) pinText.textContent = "ZADEJTE PIN";
                    let cancelBtn = document.getElementById('pin-cancel-btn');
                    if(cancelBtn) cancelBtn.style.display = 'block';
                    if (d.app_id) { storedAppId = d.app_id; localStorage.setItem('appId', storedAppId); }
                    window.switchLoginView('login-pin-view');
                    return;
                } else {
                    let isVerError = d.message && (d.message.toLowerCase().includes('verz') || d.message.toLowerCase().includes('podporována'));
                    window.showErrorModal("ZAMÍTNUTO", d.message || "Tento PC nemá přístup.", isVerError, 'error');
                    window.resetLoginFlow();
                    return;
                }
            } catch(e){
                appState = 'LOGIN_PIN_ENTER';
                inputValues.pinEnter = "";
                window.updatePinVisuals('pinEnter');
                let pinText = document.getElementById('pin-header-text');
                if (pinText) pinText.textContent = "ZADEJTE PIN (OFFLINE)";
                let cancelBtn = document.getElementById('pin-cancel-btn');
                if(cancelBtn) cancelBtn.style.display = 'block';
                window.switchLoginView('login-pin-view');
                return;
            }
        } 
        window.resetLoginFlow();
    } catch(err) {}
}

window.resetLoginFlow = function() {
    window.playClick();
    if(discordPollInterval) clearInterval(discordPollInterval);
    appState = 'LOGIN_DISCORD';
    inputValues.discordId = "";
    let el = document.getElementById('login-identifier-input');
    if(el) { el.value = ""; el.disabled = false; }
    window.switchLoginView('login-discord-view');
}

window.startDiscordAuth = async function() {
    try {
        debugLog("Odesílám ověření pro HWID: " + machineHWID);
        const inputEl = document.getElementById('login-identifier-input');
        if (!inputEl) return;
        
        const val = inputEl.value.trim();
        if (!val || val === "") {
            window.showErrorModal("CHYBÍ ÚDAJE", "Zadejte prosím své ID nebo Nick.", false, 'warning');
            return;
        }

        let pripojeni = await zanalyzujPripojeni();
        if (pripojeni.status !== "OK") {
            if (pripojeni.status === "BLOCKED_BY_FIREWALL") {
                window.showErrorModal("ZABLOKOVÁNO ANTIVIREM", "Pro první přihlášení přes Discord je vyžadováno spojení se serverem, ale to je <b>blokováno vaším Antivirem nebo Firewallem!</b><br><br>Prosím, přidejte aplikaci do výjimek a zkuste to znovu.", false, 'warning');
            } else {
                window.showErrorModal("CHYBÍ PŘIPOJENÍ", "Pro první přihlášení (spárování účtu) je <b>vyžadován funkční internet</b>.<br><br>" + pripojeni.zprava, false, 'info');
            }
            window.resetLoginFlow();
            return;
        }
        
        appState = 'LOGIN_WAITING';
        window.switchLoginView('login-waiting-view');

        const res = await fetchBlesk(`${API_BASE}/api/app_login`, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier: val, hwid: machineHWID, app_version: APP_VERSION })
        }, 6000);
        
        const textData = await res.text();
        let data;
        try {
            const fixedText = textData.replace(/"discord_id":\s*(\d+)/g, '"discord_id": "$1"');
            data = JSON.parse(fixedText);
        } catch(parseErr) {
            window.showErrorModal("CHYBA SERVERU", "Aplikace nemůže přečíst API. Zkuste zadat přímo číslo ID.", false, 'error');
            return;
        }

        if (isDevMode && data.status === 'error' && data.message && (data.message.includes('VYPNUT') || data.message.includes('verzi') || data.message.includes('verze') || data.message.includes('podporována'))) {
            data.status = 'waiting';
            data.discord_id = val; 
        }
        
        if (data.status === 'waiting') {
            storedDiscordId = data.discord_id;
            discordPollInterval = setInterval(() => window.pollDiscordAuth(), 2000);
        } else if (data.status === 'error') {
            let isVerError = data.message && (data.message.toLowerCase().includes('verz') || data.message.toLowerCase().includes('podporována') || data.message.includes('VYPNUT'));
            window.showErrorModal("PŘÍSTUP ODEPŘEN", data.message, isVerError, 'error');
            window.resetLoginFlow();
        } else {
            window.showErrorModal("PŘÍSTUP ODEPŘEN", data.message || "Chybné jméno nebo HWID.", false, 'error');
            window.resetLoginFlow();
        }
    } catch(e) {
        window.showErrorModal("CHYBA SPOJENÍ", "Při pokusu o přihlášení došlo k výpadku sítě.", false, 'error');
        window.resetLoginFlow();
    }
}

window.pollDiscordAuth = async function() {
    try {
        const res = await fetchBlesk(`${API_BASE}/api/app_check`, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discord_id: storedDiscordId, hwid: machineHWID })
        }, 4000);
        const data = await res.json();
        
        if (data.status === 'success' || (isDevMode && data.status === 'error')) {
            if (isDevMode && data.status === 'error') {
                debugLog("⚠️ VSC REŽIM: Ignoruji chybu Discord Pollingu.");
            }
            clearInterval(discordPollInterval);
            localStorage.setItem('discordId', storedDiscordId);
            localStorage.setItem('discordNick', data.display_name || "VSC_DEV");
            if (data.app_id) {
                storedAppId = data.app_id;
                localStorage.setItem('appId', storedAppId);
            }
            appState = 'LOGIN_SETUP_CHOICE';
            window.switchLoginView('login-setup-view');
        } else if (data.status === 'error') {
            clearInterval(discordPollInterval);
            window.showErrorModal("OVĚŘENÍ SELHALO", data.message || "Zamítnuto v aplikaci Discord.", false, 'error');
        }
    } catch(e) {}
}

window.selectLoginMethod = function(mode) {
    window.playClick();
    if (mode === 'AUTO') {
        localStorage.setItem('loginMode', 'AUTO');
        window.finalizeLogin();
    } else {
        appState = 'LOGIN_PIN_SETUP';
        inputValues.pinSetup = "";
        window.updatePinVisuals('pinSetup');
        let txt = document.getElementById('pin-header-text');
        if(txt) txt.textContent = "VYTVOŘTE NOVÝ PIN";
        let cancelBtn = document.getElementById('pin-cancel-btn');
        if(cancelBtn) cancelBtn.style.display = 'none'; 
        window.switchLoginView('login-pin-view');
    }
}

window.updatePinVisuals = function(target) {
    const val = inputValues[target];
    for(let i=1; i<=4; i++) {
        let dot = document.getElementById('pin-'+i);
        if (!dot) continue;
        if (i <= val.length) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    }
}

window.submitPinNumber = function(numStr) {
    if (appState === 'LOGIN_PIN_SETUP') {
        if (inputValues.pinSetup.length < 4) { 
            inputValues.pinSetup += numStr; 
        }
        window.updatePinVisuals('pinSetup');
        
        if (inputValues.pinSetup.length === 4) {
            localStorage.setItem('loginMode', 'PIN');
            localStorage.setItem('savedPin', inputValues.pinSetup);
            window.finalizeLogin();
        }
    } else if (appState === 'LOGIN_PIN_ENTER') {
        if (inputValues.pinEnter.length < 4) { 
            inputValues.pinEnter += numStr; 
        }
        window.updatePinVisuals('pinEnter');
        
        if (inputValues.pinEnter.length === 4) {
            if (inputValues.pinEnter === localStorage.getItem('savedPin')) {
                window.finalizeLogin();
            } else {
                inputValues.pinEnter = "";
                let hdr = document.getElementById('pin-header-text');
                if(hdr) { 
                    hdr.textContent = "NESPRÁVNÝ PIN!"; 
                    hdr.style.color = "#e74c3c"; 
                }
                window.updatePinVisuals('pinEnter');
                setTimeout(() => {
                    if(hdr) { 
                        hdr.textContent = "ZADEJTE PIN"; 
                        hdr.style.color = "white"; 
                    }
                }, 1500);
            }
        }
    }
}

window.finalizeLogin = function() {
    window.playClick();
    debugLog("Přihlášení úspěšné. Otevírám druhý monitor.");
    
    let loadEl = document.getElementById('loadingScreen');
    let msgEl = document.getElementById('loading-msg');
    if(loadEl && msgEl) {
        msgEl.textContent = "NAHRÁVÁNÍ GRAFIKY NA DRUHÝ MONITOR...";
        loadEl.style.zIndex = "999999"; 
        loadEl.style.display = 'flex';
    }

    ipcRenderer.send('reload-panel-window');
    
    setTimeout(() => {
        ipcRenderer.send('open-panel-window');
        ipcRenderer.send('panel-idle');
        
        setTimeout(() => {
            document.querySelectorAll('.login-view').forEach(v => { 
                v.style.display = 'none'; 
            });
            
            window.switchToLinkospojScreen();
            
            fetch(`${API_BASE}/api/app_ping`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ discord_id: storedDiscordId, action: 'start' }) 
            }).then(r => r.json()).then(data => {
                if(data.session_id) {
                    currentSessionId = data.session_id;
                    localStorage.setItem('currentSessionId', currentSessionId);
                    window.startPingLoop(); 
                }
            }).catch(e=>{});

            if (storedDiscordId) {
                window.checkAnnouncementsFromWeb(storedDiscordId, storedAppId);
            } else {
                if(loadEl) loadEl.style.display = 'none';
            }
        }, 2000);
    }, 1000);
}

window.backToLogin = function() {
    window.playClick();
    
    if (!logoutConfirmStep) {
        logoutConfirmStep = true;
        let btn = document.getElementById('btn-logout');
        if(btn){
            btn.textContent = "POTVRDIT ODHLÁŠENÍ";
            btn.style.background = "#e74c3c";
        }
        setTimeout(() => {
            logoutConfirmStep = false;
            let resetBtn = document.getElementById('btn-logout');
            if(resetBtn){ 
                resetBtn.textContent = "ODHLÁSIT SE"; 
                resetBtn.style.background = "#3498db"; 
            }
        }, 3000);
        return;
    }
    
    window.submitStats(); 
    
    logoutConfirmStep = false;
    let btn = document.getElementById('btn-logout');
    if(btn){ 
        btn.textContent = "ODHLÁSIT SE"; 
        btn.style.background = "#3498db"; 
    }

    localStorage.removeItem('loginMode');
    localStorage.removeItem('savedPin');
    localStorage.removeItem('discordId');
    localStorage.removeItem('discordNick');
    sessionStorage.removeItem('softResetState');
    
    fetch(`${API_BASE}/api/app_ping`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ discord_id: storedDiscordId, action: 'stop', session_id: currentSessionId }) 
    }).catch(e=>{});
    currentSessionId = "";
    localStorage.removeItem('currentSessionId');
    if(pingInterval) clearInterval(pingInterval);
    
    ipcRenderer.send('reset-panel');
    
    document.querySelectorAll('.settings-modal, .funk-modal, .error-modal, #debug-overlay, .loading-overlay, .announcement-modal').forEach(el => el.style.display = 'none');
    document.getElementById('linkospoj-wrapper').style.display = 'none';
    document.getElementById('idpk-db-wrapper').style.display = 'none';
    document.getElementById('idpk-direction-wrapper').style.display = 'none';
    document.getElementById('drive-ui-wrapper').style.display = 'none';
    document.getElementById('drive-controls-area').style.display = 'none';
    document.getElementById('main-keypad').style.display = 'none';
    
    appState = 'BOOT';
    storedDiscordId = "";
    storedAppId = "";
    window.resetLoginFlow();

    setTimeout(() => {
        window.focus();
        let inputEl = document.getElementById('login-identifier-input');
        if (inputEl) {
            inputEl.disabled = false;
            inputEl.readOnly = false;
            inputEl.blur(); 
            inputEl.focus();
            inputEl.click();
        }
    }, 100);
}

window.startPingLoop = function() {
    if(pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
        if (!appState.startsWith('LOGIN') && appState !== 'LOCKED' && storedDiscordId) {
            fetch(`${API_BASE}/api/app_ping`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ discord_id: storedDiscordId, action: 'ping', session_id: currentSessionId }) 
            }).catch(e=>{});
        }
    }, 60000);
}

window.updateAHIndicator = function() {
    const ind = document.getElementById('ah-indicator');
    if (ind) {
        if (isClassicAuto || isTimeBasedAuto || isDelayAuto) {
            ind.style.display = 'block';
        } else {
            ind.style.display = 'none';
        }
    }
};

window.syncTimeWithCurrentStop = function() {
    if (!isClassicAuto || !routeData.stops || routeData.stops.length === 0) return;
    let currentStop = routeData.stops[routeData.realStopIndex];
    if (currentStop && currentStop.time) {
        let targetMins = window.timeToMins(currentStop.time);
        let now = new Date();
        let targetDate = new Date();
        targetDate.setHours(Math.floor(targetMins / 60) % 24, targetMins % 60, 0, 0);
        fictionalTimeOffset = targetDate.getTime() - now.getTime();
        useFictionalTime = true;
        window.timeLoop();
    }
};

window.timeLoop = function() {
    let now = new Date();
    if (useFictionalTime) { 
        now = new Date(now.getTime() + fictionalTimeOffset); 
    }
    
    let timeStr = window.padTime(now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }));
    let timeStrSec = window.padTime(now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    
    let liveClockEl = document.getElementById('live-clock-display');
    if(liveClockEl) {
        liveClockEl.textContent = timeStrSec;
    }

    if (appState !== 'DRIVE') {
        ipcRenderer.send('update-time-delay', { timeOnly: true, timeStr: " " });
        return;
    } else {
        ipcRenderer.send('update-time-delay', { timeOnly: true, timeStr: timeStr });
    }

    let s1 = routeData.stops[routeData.realStopIndex];
    currentGlobalDelay = 0;
    
    if (s1 && s1.time && s1.time.includes(':')) {
        let currentMins = now.getHours() * 60 + now.getMinutes();
        let s1Mins = window.timeToMins(s1.time);
        currentGlobalDelay = currentMins - s1Mins;
        if (currentGlobalDelay < -720) currentGlobalDelay += 1440; 
        if (currentGlobalDelay > 720) currentGlobalDelay -= 1440;
    }

    window.sendDataToPanel(drivePhase === 1); 
    
    if (!routeStartupWait) {
        window.checkAutoAnnounce(now, s1);
    }
};

window.sendDataToPanel = function(showBig = false) {
    const idx = routeData.realStopIndex; 
    let s1 = routeData.stops[idx] ? { ...routeData.stops[idx] } : null; 
    let s2 = routeData.stops[idx+1] ? { ...routeData.stops[idx+1] } : null; 
    let s3 = routeData.stops[idx+2] ? { ...routeData.stops[idx+2] } : null; 
    
    if (s1 && s1.time) s1.time = window.padTime(s1.time);
    if (s2 && s2.time) s2.time = window.padTime(s2.time);
    if (s3 && s3.time) s3.time = window.padTime(s3.time);

    let est1 = null, est2 = null, est3 = null;
    let visualDelay = currentGlobalDelay;
    
    if (isDelayAuto && lockedAutoDelayMins !== null) {
        visualDelay = lockedAutoDelayMins;
    }

    if (isDelayMode && visualDelay >= 3 && s1 && s1.time) {
        if (isDelayAuto) {
            est1 = window.padTime(window.minsToTime(window.timeToMins(s1.time) + visualDelay));
        } else {
            let now = new Date();
            if (useFictionalTime) now = new Date(now.getTime() + fictionalTimeOffset);
            est1 = window.padTime(now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }));
        }
        if (s2 && s2.time) est2 = window.padTime(window.minsToTime(window.timeToMins(s2.time) + visualDelay));
        if (s3 && s3.time) est3 = window.padTime(window.minsToTime(window.timeToMins(s3.time) + visualDelay));
    }

    ipcRenderer.send('update-panel-data', { 
        line: routeData.line, 
        destination: routeData.destination, 
        stop1: s1, 
        stop2: s2, 
        stop3: s3, 
        est1: est1, 
        est2: est2, 
        est3: est3,
        showBigStop: showBig, 
        isMuted: routeData.isMuted, 
        stopPressed: false // TLAČÍTKO STOP NENÍ PODPOROVÁNO
    });
};

window.checkAutoAnnounce = function(now, s1) {
    if (appState !== 'DRIVE' || isAnnouncementPlaying || pendingStopSound || autoAnnounceCooldown || window.isAtEndOfRoute() || !s1 || !s1.time) return;

    let schedMins = window.timeToMins(s1.time);
    let currentMins = now.getHours() * 60 + now.getMinutes();
    let currentSecs = now.getSeconds();

    if (isTimeBasedAuto) {
        let isLate = false;
        if (drivePhase === 0 && (currentMins > schedMins || (currentMins === schedMins && currentSecs >= 0))) isLate = true;
        if (drivePhase === 1 && (currentMins > schedMins || (currentMins === schedMins && currentSecs >= 30))) isLate = true;
        if (isLate) window.triggerAutoRapid();
    } 
    else if (isDelayAuto && lockedAutoDelayMins !== null && lockedAutoStartTimeMins !== null) {
        let isLate = false;
        if (currentMins >= lockedAutoStartTimeMins) {
            if (drivePhase === 0 && (currentMins > schedMins + lockedAutoDelayMins || (currentMins === schedMins + lockedAutoDelayMins && currentSecs >= 0))) isLate = true;
            if (drivePhase === 1 && (currentMins > schedMins + lockedAutoDelayMins || (currentMins === schedMins + lockedAutoDelayMins && currentSecs >= 30))) isLate = true;
        }
        if (isLate) window.triggerAutoRapid();
    }
};

window.triggerAutoRapid = function() {
    window.smartButtonAction();
    autoAnnounceCooldown = true;
    setTimeout(() => { autoAnnounceCooldown = false; }, 5000); 
};

window.openStopWindow = function() { 
    window.playClick(); 
    // Odstraněno ipcRenderer.send('open-stop-window');
    window.toggleSettings(); 
};

window.openFunkMenu = function() { 
    window.playClick(); 
    let el = document.getElementById('funk-modal'); 
    if(el) el.style.display = 'flex'; 
};

window.closeFunkMenu = function() { 
    window.playClick(); 
    let el = document.getElementById('funk-modal'); 
    if(el) el.style.display = 'none'; 
};

window.toggleDelayMode = function() { 
    window.playClick(); 
    setDelayMode(!isDelayMode); 
    window.timeLoop(); 
};

window.toggleRandomContinue = function() { 
    window.playClick(); 
    isRandomContinue = !isRandomContinue; 
    window.updateBtnState('btn-random-continue', isRandomContinue); 
};

window.toggleTimeAuto = function() { 
    window.playClick();
    isTimeBasedAuto = !isTimeBasedAuto; 
    window.updateBtnState('btn-auto-time', isTimeBasedAuto); 
    if(isTimeBasedAuto) { 
        isClassicAuto = false; 
        window.updateBtnState('btn-auto-announce', false); 
        clearTimeout(classicAutoTimer); 
        isDelayAuto = false; 
        window.updateBtnState('btn-delay-auto', false);
        
        if (appState === 'DRIVE' && !routeStartupWait) {
            setTimeout(() => {
                let now = new Date();
                if (useFictionalTime) now = new Date(now.getTime() + fictionalTimeOffset);
                let currentStop = routeData.stops[routeData.realStopIndex];
                if(currentStop) window.checkAutoAnnounce(now, currentStop);
            }, 3000);
        }
    }
    window.updateAHIndicator();
};

window.toggleDelayAuto = function() { 
    window.playClick();
    if (!isDelayMode) {
        debugLog("<span style='color:red;'>Nejprve zapněte funkci ZPOŽDĚNÍ!</span>");
        return;
    }
    isDelayAuto = !isDelayAuto; 
    window.updateBtnState('btn-delay-auto', isDelayAuto); 
    
    if(isDelayAuto) { 
        isClassicAuto = false; 
        window.updateBtnState('btn-auto-announce', false); 
        clearTimeout(classicAutoTimer); 
        isTimeBasedAuto = false; 
        window.updateBtnState('btn-auto-time', false);
        
        let now = new Date();
        if (useFictionalTime) { 
            now = new Date(now.getTime() + fictionalTimeOffset); 
        }
        
        let currentMins = now.getHours() * 60 + now.getMinutes();
        let startStop = routeData.stops[routeData.realStopIndex];
        
        if (startStop && startStop.time) {
            let sMins = window.timeToMins(startStop.time);
            lockedAutoDelayMins = (currentMins - sMins);
            if (now.getSeconds() > 30 && lockedAutoDelayMins >= 0) {
                lockedAutoDelayMins += 1;
            }
            if (lockedAutoDelayMins < -720) lockedAutoDelayMins += 1440;
            if (lockedAutoDelayMins > 720) lockedAutoDelayMins -= 1440;
            lockedAutoStartTimeMins = sMins + lockedAutoDelayMins;
        } else {
            lockedAutoDelayMins = 0; 
            lockedAutoStartTimeMins = currentMins;
        }

        if (appState === 'DRIVE' && !routeStartupWait) {
            setTimeout(() => {
                let checkNow = new Date();
                if (useFictionalTime) checkNow = new Date(checkNow.getTime() + fictionalTimeOffset);
                let currentStopCheck = routeData.stops[routeData.realStopIndex];
                if(currentStopCheck) window.checkAutoAnnounce(checkNow, currentStopCheck);
            }, 3000);
        }
    } else {
        lockedAutoDelayMins = null; 
        lockedAutoStartTimeMins = null;
    }
    window.updateAHIndicator();
    window.timeLoop();
};

window.toggleAutoAnnounce = function() {
    window.playClick();
    isClassicAuto = !isClassicAuto; 
    window.updateBtnState('btn-auto-announce', isClassicAuto);
    
    if(isClassicAuto) { 
        setDelayMode(false); 
        isTimeBasedAuto = false; 
        window.updateBtnState('btn-auto-time', false); 
        isDelayAuto = false; 
        window.updateBtnState('btn-delay-auto', false); 
        clearTimeout(classicAutoTimer); 
        
        if (appState === 'DRIVE' && !routeStartupWait) {
            setTimeout(() => {
                window.syncTimeWithCurrentStop();
                window.scheduleClassicAuto(); 
            }, 3000);
        }
    } else { 
        clearTimeout(classicAutoTimer); 
    }
    window.updateAHIndicator();
};

window.updateDelayDisplay = function() { 
    let slider = document.getElementById('delay-slider');
    if (slider) {
        classicAutoDelay = parseInt(slider.value); 
        slider.setAttribute('value', classicAutoDelay); 
        let dVal = document.getElementById('delay-val');
        if (dVal) {
            dVal.textContent = classicAutoDelay + "s"; 
        }
    }
};

window.updateBtnState = function(id, state) { 
    const btn = document.getElementById(id); 
    if(btn) { 
        if(state) { 
            btn.textContent = "ZAPNUTO"; 
            btn.classList.add('on'); 
        } else { 
            btn.textContent = "VYPNUTO"; 
            btn.classList.remove('on'); 
        } 
    } 
};

window.setFictionalTime = function() {
    window.playClick();
    const inputEl = document.getElementById('fictional-time-input');
    if(!inputEl) return;
    const input = inputEl.value;
    inputEl.setAttribute('value', input); 
    if (!input) { 
        useFictionalTime = false; 
        window.timeLoop(); 
        return; 
    }
    
    useFictionalTime = true;
    let parts = input.split(':'); 
    let now = new Date(); 
    let target = new Date();
    target.setHours(parseInt(parts[0]), parseInt(parts[1]), 0, 0);
    fictionalTimeOffset = target.getTime() - now.getTime();
    
    autoAnnounceCooldown = true;
    setTimeout(() => { 
        autoAnnounceCooldown = false; 
    }, 3000);

    window.timeLoop(); 
    window.closeFunkMenu();
};

window.scheduleClassicAuto = function() {
    if (!isClassicAuto || appState !== 'DRIVE' || routeStartupWait) return;
    clearTimeout(classicAutoTimer);
    classicAutoTimer = setTimeout(() => {
        if (!isClassicAuto || appState !== 'DRIVE' || routeStartupWait) return;
        if (!isAnnouncementPlaying && !window.isAtEndOfRoute()) { 
            window.smartButtonAction(); 
        } else { 
            window.scheduleClassicAuto(); 
        }
    }, classicAutoDelay * 1000);
};

window.manualContinueTrip = function() {
    window.playClick();
    window.submitStats();
    
    if(window.autoContinueTimeout) { 
        clearTimeout(window.autoContinueTimeout); 
        window.autoContinueTimeout = null; 
    }
    
    selectedStartStop = routeData.stops[routeData.stops.length - 1].name; 
    selectedIdpkRouteId = routeData.routeId || selectedIdpkRouteId; 
    inputValues.idpk = routeData.line; 
    
    let d1 = document.getElementById('drive-ui-wrapper'); 
    if(d1) d1.style.display = 'none';
    let d2 = document.getElementById('drive-controls-area'); 
    if(d2) d2.style.display = 'none';
    
    appState = 'IDPK_START'; 
    let d3 = document.getElementById('idpk-direction-wrapper'); 
    if(d3) d3.style.display = 'flex';
    let d4 = document.getElementById('idpk-selected-line'); 
    if(d4) d4.textContent = "Linka: " + inputValues.idpk;
    
    let mk = document.getElementById('main-keypad'); 
    if(mk) mk.style.display = 'grid'; 
    let kd = document.getElementById('key-del'); 
    if(kd) kd.style.display = 'flex';
    let kf = document.getElementById('key-funk'); 
    if(kf) kf.style.display = 'none';
    
    window.updateSelectionHeader(`VÝCHOZÍ: ${selectedStartStop}`, "window.backToManualWithLoad()");
    window.loadDestinationsForStart();
};

window.backToManualWithLoad = function() {
    window.playClick();
    let loadScreen = document.getElementById('loadingScreen');
    if (loadScreen) loadScreen.style.display = 'flex';
    
    ipcRenderer.invoke('gtfs-get-start-stops', selectedIdpkRouteId).then(starts => {
        if(loadScreen) loadScreen.style.display = 'none';
        window.showStartStopSelection(starts);
    }).catch(e => { 
        if(loadScreen) loadScreen.style.display = 'none'; 
    });
};

window.autoStartRandomTrip = async function() {
    window.playClick();
    window.submitStats();
    
    if (availableFiles.length === 0) return;
    
    let choices = availableFiles.filter(f => !randomHistory.includes(f));
    if (choices.length === 0) { 
        choices = availableFiles; 
        randomHistory = []; 
    }
    let pick = choices[Math.floor(Math.random() * choices.length)];
    
    randomHistory.push(pick);
    if (randomHistory.length > 5) randomHistory.shift();

    appState = 'LINKOSPOJ';
    inputValues.linkospoj = pick.replace('_auto', '').replace('-beta', '');
    window.updateLinkospojDisplay();
    
    let fileToLoad = inputValues.linkospoj;
    let resolved = window.getResolvedFile(fileToLoad);
    if (resolved) {
        fileToLoad = resolved;
    }
    
    let loadScreen = document.getElementById('loadingScreen');
    if (loadScreen) loadScreen.style.display = 'flex';
    
    try {
        let content = await ipcRenderer.invoke('read-route-file', fileToLoad);
        if (!content) throw new Error("Nelze přečíst " + fileToLoad);
        
        let responseObj;
        if (content.toUpperCase().includes("GTFS-DATA") || content.toUpperCase().includes("GTSF-DATA")) {
            let response = await ipcRenderer.invoke('process-hybrid-file', content);
            if (response.error) throw new Error(response.error);
            
            if (response.isTemplate) {
                let routeId = response.routeId; 
                currentHybridTemplate = response; 
                inputValues.idpk = response.lineNum;
                
                let starts = await ipcRenderer.invoke('gtfs-get-start-stops', routeId);
                let randomStart = starts[Math.floor(Math.random() * starts.length)];
                
                let dests = await ipcRenderer.invoke('gtfs-get-destinations-from-start', { routeId, startStopName: randomStart });
                let randomDest = dests[Math.floor(Math.random() * dests.length)];
                
                let trips = await ipcRenderer.invoke('gtfs-get-final-trips', { routeId, startStopName: randomStart, headsign: randomDest });
                let randomTrip = trips[Math.floor(Math.random() * trips.length)];
                
                let tripData = await ipcRenderer.invoke('hybrid-get-trip-data', { tripId: randomTrip.tripId, stopMapObj: currentHybridTemplate.stopMap });
                if (tripData.error) throw new Error(tripData.error);
                
                responseObj = { 
                    lineNum: currentHybridTemplate.lineNum, 
                    routeId: routeId, 
                    linkospojCode: randomTrip.tripNumber, 
                    destination: tripData.destination, 
                    stops: tripData.stops 
                };
            } else {
                responseObj = { 
                    lineNum: response.line, 
                    routeId: response.routeId, 
                    linkospojCode: response.linkospoj, 
                    destination: response.destination, 
                    stops: response.stops 
                };
            }
        } else {
            currentHybridTemplate = null; 
            window.parseRouteData(content);
            responseObj = { 
                lineNum: routeData.line, 
                routeId: routeData.routeId, 
                linkospojCode: routeData.linkospojCode, 
                destination: routeData.destination, 
                stops: routeData.stops 
            };
        }

        let s1 = responseObj.stops[0];
        if (s1 && s1.time) {
            let targetMins = window.timeToMins(s1.time);
            let generatedDelay = 0;

            if (isClassicAuto) {
                if (isDelayMode) setDelayMode(false);
                let r = Math.random() * 100;
                if (r < 70) generatedDelay = 0;
                else if (r < 90) generatedDelay = 3 + Math.floor(Math.random() * 28);
                else generatedDelay = 31 + Math.floor(Math.random() * 30);
            } 
            else if (isTimeBasedAuto) {
                let r = Math.random() * 100;
                if (r < 38) generatedDelay = 0; 
                else if (r < 78) generatedDelay = 5 + Math.floor(Math.random() * 6); 
                else if (r < 93) generatedDelay = 11 + Math.floor(Math.random() * 15); 
                else generatedDelay = 26 + Math.floor(Math.random() * 35); 
                
                if (generatedDelay >= 3 && !isDelayMode) setDelayMode(true);
                else if (generatedDelay < 3 && isDelayMode) setDelayMode(false);
            } 
            else if (isDelayAuto) {
                let r = Math.random() * 100;
                if (r < 70) generatedDelay = 5 + Math.floor(Math.random() * 11); 
                else if (r < 90) generatedDelay = 16 + Math.floor(Math.random() * 10); 
                else if (r < 98) generatedDelay = 26 + Math.floor(Math.random() * 25); 
                else generatedDelay = 51 + Math.floor(Math.random() * 10); 
                
                if (!isDelayMode) setDelayMode(true);
                lockedAutoDelayMins = generatedDelay;
                lockedAutoStartTimeMins = targetMins + generatedDelay;
            }

            targetMins += generatedDelay;
            let now = new Date(); 
            let targetDate = new Date();
            targetDate.setHours(Math.floor(targetMins / 60) % 24, targetMins % 60, 0, 0);
            fictionalTimeOffset = targetDate.getTime() - now.getTime();
            useFictionalTime = true;
        }

        if (loadScreen) {
            loadScreen.style.display = 'none';
        }
        
        routeData.isMuted = false; 
        routeData.line = responseObj.lineNum; 
        routeData.routeId = responseObj.routeId; 
        routeData.linkospojCode = responseObj.linkospojCode;
        routeData.destination = responseObj.destination; 
        routeData.stops = responseObj.stops;
        routeData.realStopIndex = 0; 
        routeData.previewStopIndex = 0; 
        drivePhase = 0;
        
        window.initStatsTracking();
        window.switchToDriveScreen(); 
        
        routeStartupWait = true;
        setTimeout(() => { 
            routeStartupWait = false;
            if (isClassicAuto) {
                window.syncTimeWithCurrentStop();
                window.scheduleClassicAuto(); 
            }
            else if (isTimeBasedAuto || isDelayAuto) {
                window.checkAutoAnnounce(new Date(), routeData.stops[0]);
            }
        }, 10000);

    } catch (e) {
        if (loadScreen) loadScreen.style.display = 'none';
        appState = 'LINKOSPOJ'; 
        inputValues.linkospoj = ""; 
        window.updateLinkospojDisplay(); 
        window.switchToLinkospojScreen();
    }
};

window.submitAction = function() {
    try {
        debugLog("Odesílám akci ve stavu: " + appState);
        window.playClick(); 
        
        if (appState === 'LOGIN_DISCORD') { 
            window.startDiscordAuth(); 
        }
        else if (appState === 'LOGIN_AUTO') { 
            window.finalizeLogin(); 
        }
        else if (appState === 'LINKOSPOJ') {
            if (linkospojFocus === 'list') { 
                window.confirmSelection(); 
                return; 
            }
            
            let fileToLoad = inputValues.linkospoj; 
            let resolved = window.getResolvedFile(fileToLoad); 
            if (resolved) { 
                fileToLoad = resolved; 
                inputValues.linkospoj = resolved; 
                window.updateLinkospojDisplay(); 
            }
            
            let loadScreen = document.getElementById('loadingScreen');
            if (loadScreen) loadScreen.style.display = 'flex';
            isSystemLoading = true; 
            
            ipcRenderer.invoke('read-route-file', fileToLoad).then(content => {
                if (content) {
                    if (content.toUpperCase().includes("GTFS-DATA") || content.toUpperCase().includes("GTSF-DATA")) {
                        ipcRenderer.invoke('process-hybrid-file', content).then(response => {
                            isSystemLoading = false; 
                            if(loadScreen) loadScreen.style.display = 'none';
                            
                            if (response.error) { 
                                window.showErrorModal("CHYBA DATABÁZE", response.error);
                            } 
                            else if (response.isTemplate) {
                                currentHybridTemplate = response; 
                                selectedIdpkRouteId = response.routeId; 
                                inputValues.idpk = response.lineNum; 
                                isSystemLoading = true; 
                                if(loadScreen) loadScreen.style.display = 'flex'; 
                                
                                ipcRenderer.invoke('gtfs-get-start-stops', selectedIdpkRouteId).then(starts => { 
                                    isSystemLoading = false; 
                                    if(loadScreen) loadScreen.style.display = 'none'; 
                                    window.showStartStopSelection(starts); 
                                });
                            } else {
                                routeData.isMuted = false; 
                                routeData.line = response.line; 
                                routeData.routeId = response.routeId; 
                                routeData.linkospojCode = response.linkospoj; 
                                routeData.destination = response.destination; 
                                routeData.stops = response.stops; 
                                routeData.nextTurnus = response.nextTurnus; 
                                routeData.realStopIndex = 0; 
                                routeData.previewStopIndex = 0; 
                                drivePhase = 0; 
                                window.initStatsTracking();
                                window.switchToDriveScreen(); 
                                window.sendDataToPanel();
                            }
                        }).catch(e => { 
                            isSystemLoading = false; 
                            if(loadScreen) loadScreen.style.display = 'none'; 
                            debugLog("GTFS proces chyba: "+e); 
                        });
                    } else { 
                        isSystemLoading = false; 
                        if(loadScreen) loadScreen.style.display = 'none'; 
                        currentHybridTemplate = null; 
                        routeData.isMuted = false; 
                        window.parseRouteData(content); 
                        window.initStatsTracking();
                        window.switchToDriveScreen(); 
                        window.sendDataToPanel(); 
                    }
                } else { 
                    isSystemLoading = false; 
                    if(loadScreen) loadScreen.style.display = 'none'; 
                    window.showErrorModal("CHYBA", "SOUBOR NENALEZEN: " + fileToLoad); 
                }
            }).catch(e => { 
                isSystemLoading = false; 
                if(loadScreen) loadScreen.style.display = 'none'; 
            });
        }
        else if (appState === 'IDPK_LINE') {
            if (linkospojFocus === 'list') { 
                window.confirmSelection(); 
                return; 
            }
            
            if (!selectedIdpkRouteId) {
                const found = databaseFiles.find(line => { 
                    const num = line.split('|')[0].trim(); 
                    return num === inputValues.idpk || num.endsWith(inputValues.idpk); 
                });
                if(found) {
                    selectedIdpkRouteId = found.split('|')[2] ? found.split('|')[2].trim() : ""; 
                } else { 
                    window.showErrorModal("CHYBA", "LINKA NENALEZENA V DB"); 
                    return; 
                }
            }
            currentHybridTemplate = null; 
            isSystemLoading = true; 
            
            let loadScreen = document.getElementById('loadingScreen');
            if(loadScreen) loadScreen.style.display = 'flex'; 
            
            ipcRenderer.invoke('gtfs-get-start-stops', selectedIdpkRouteId).then(starts => { 
                isSystemLoading = false; 
                if(loadScreen) loadScreen.style.display = 'none'; 
                
                if (starts.length === 0 || (starts.length === 1 && starts[0].includes("CHYBA"))) {
                    window.showErrorModal("CHYBA", starts.length > 0 ? starts[0] : "ŽÁDNÉ SPOJE K LINCE"); 
                } else { 
                    window.showStartStopSelection(starts); 
                }
            }).catch(e => { 
                isSystemLoading = false; 
                if(loadScreen) loadScreen.style.display = 'none'; 
            });
        }
    } catch(err) {
        window.onerror("Chyba při Submit: " + err.message, "", 0, 0, err);
    }
};

window.updateLinkospojDisplay = function() { 
    let rawInput = inputValues.linkospoj || ''; 
    let displayEl = document.getElementById('display-linkospoj');
    if (!displayEl) return;
    
    if (!rawInput) { 
        displayEl.textContent = '-----'; 
        return; 
    }
    
    let resolvedFile = window.getResolvedFile(rawInput); 
    let isBeta = false; 
    let cleanText = rawInput.toString();
    
    if (resolvedFile) { 
        isBeta = resolvedFile.toUpperCase().includes('BETA'); 
        cleanText = resolvedFile.replace(/_auto-BETA/i, '').replace(/_auto/i, '').replace(/-BETA/i, '').replace(/_BETA/i, ''); 
    } else { 
        isBeta = rawInput.toString().toUpperCase().includes('BETA'); 
        cleanText = rawInput.toString().replace(/_auto-BETA/i, '').replace(/_auto/i, '').replace(/-BETA/i, '').replace(/_BETA/i, ''); 
    }
    
    if (isBeta) { 
        displayEl.innerHTML = `<span class="beta-badge">BETA</span><span class="beta-text">${cleanText}</span>`; 
    } else { 
        displayEl.innerHTML = `<span>${cleanText}</span>`; 
    }
};

window.updateLinkospojUI = function() { 
    const listEl = document.getElementById('link-list'); 
    let wrapper = null;
    
    if (appState === 'IDPK_LINE') { 
        wrapper = document.getElementById('idpk-db-wrapper'); 
    } else { 
        wrapper = document.getElementById('linkospoj-wrapper'); 
    }
    if (listEl && wrapper) wrapper.appendChild(listEl);

    const check = document.getElementById(appState === 'IDPK_LINE' ? 'idpk-checkbox' : 'checkbox-icon'); 
    const toggle = document.getElementById(appState === 'IDPK_LINE' ? 'idpk-list-toggle' : 'list-toggle'); 
    
    if (linkospojFocus === 'list' || isListOpen) { 
        if(toggle) toggle.classList.add('selected'); 
    } else { 
        if(toggle) toggle.classList.remove('selected'); 
    }
    
    if(check) check.textContent = isListOpen ? "[x]" : "[ ]"; 
    
    if(listEl) listEl.style.display = isListOpen ? 'block' : 'none'; 
    if (isListOpen) window.renderLinkList(); 
};

window.selectListItem = function(index) {
    if(appState === 'IDPK_LINE') {
        let parts = filteredFiles[index].split('|'); 
        inputValues.idpk = parts[0].trim(); 
        selectedIdpkRouteId = parts[2] ? parts[2].trim() : "";
        
        let disp = document.getElementById('display-idpk'); 
        if (disp) disp.textContent = inputValues.idpk;
        
        selectedListIndex = index; 
        linkospojFocus = 'input'; 
        isListOpen = false; 
        
        window.updateLinkospojUI(); 
        window.playClick(); 
        window.submitAction();
    } else {
        inputValues.linkospoj = filteredFiles[index]; 
        selectedListIndex = index; 
        linkospojFocus = 'input'; 
        isListOpen = false; 
        
        window.updateLinkospojDisplay(); 
        window.updateLinkospojUI(); 
        window.playClick(); 
        window.submitAction(); 
    }
};

window.renderLinkList = function() { 
    const listEl = document.getElementById('link-list'); 
    if(!listEl) return;
    
    listEl.innerHTML = ""; 
    filteredFiles.forEach((file, index) => { 
        const div = document.createElement('div'); 
        div.className = 'link-item'; 
        
        if (index === selectedListIndex) {
            div.classList.add('selected'); 
        }
        
        if (appState === 'IDPK_LINE') {
            let parts = file.split('|');
            div.textContent = parts[0].trim() + " | " + (parts[1] ? parts[1].trim() : "");
        } else {
            let isBeta = file.toUpperCase().includes('BETA'); 
            let cleanName = file.replace(/_auto-BETA/i, '').replace(/_auto/i, '').replace(/-BETA/i, ''); 
            
            if (isBeta) { 
                div.classList.add('beta-item'); 
                div.innerHTML = `<span class="beta-badge">BETA</span><span class="beta-text">${cleanName}</span>`; 
            } else { 
                div.textContent = cleanName; 
            } 
        }
        div.setAttribute('onclick', `window.selectListItem(${index})`);
        listEl.appendChild(div); 
    }); 
};

window.getResolvedFile = function(inputStr) { 
    if (!inputStr) return null; 
    let str = inputStr.toString().toLowerCase();
    
    let exact = availableFiles.find(f => f.toLowerCase() === str); 
    if (exact) return exact; 
    
    let searchNum = str.replace(/\D/g, ''); 
    if (!searchNum) return null; 
    
    let betaMatch = availableFiles.find(f => { 
        let fNums = f.replace(/\D/g, ''); 
        return fNums.startsWith(searchNum) && f.toUpperCase().includes('BETA'); 
    }); 
    if (betaMatch) return betaMatch; 
    
    let fuzzy = availableFiles.find(f => { 
        let fNums = f.replace(/\D/g, ''); 
        return fNums.startsWith(searchNum); 
    }); 
    return fuzzy || null; 
};

window.toggleListMouse = function() { 
    window.playClick(); 
    if(appState !== 'LINKOSPOJ' && appState !== 'IDPK_LINE') return; 
    
    if(isListOpen) { 
        isListOpen = false; 
        linkospojFocus = 'input'; 
    } else { 
        isListOpen = true; 
        linkospojFocus = 'list'; 
        selectedListIndex = 0; 
        window.updateFilter(); 
    } 
    window.updateLinkospojUI(); 
};

window.updateFilter = function() { 
    if (appState === 'LINKOSPOJ') { 
        const val = (inputValues.linkospoj || "").toString().toLowerCase(); 
        filteredFiles = val ? availableFiles.filter(f => { 
            let fClean = f.toLowerCase().replace(/[^a-z0-9]/g, ''); 
            let vClean = val.replace(/[^a-z0-9]/g, ''); 
            return fClean.includes(vClean) || f.toLowerCase().includes(val); 
        }) : availableFiles; 
    } else { 
        const val = (inputValues.idpk || "").toString(); 
        filteredFiles = val ? databaseFiles.filter(f => { 
            const lineNum = f.split('|')[0].trim(); 
            return lineNum.includes(val) || lineNum.endsWith(val); 
        }) : databaseFiles; 
    } 
};

window.updateSelectionHeader = function(title, backActionStr) { 
    const header = document.getElementById('selection-header'); 
    if(!header) return;
    
    header.innerHTML = ""; 
    header.style.position = "relative"; 
    
    if (backActionStr) { 
        const arrow = document.createElement('div'); 
        arrow.innerHTML = "&#10094;"; 
        arrow.style.cssText = "position:absolute; left:20px; top:50%; transform:translateY(-50%); font-size:30px; cursor:pointer; color:var(--idpk-yellow);"; 
        arrow.setAttribute('onclick', `event.stopPropagation(); window.playClick(); ${backActionStr}`); 
        header.appendChild(arrow); 
    } 
    const text = document.createElement('span'); 
    text.textContent = title; 
    header.appendChild(text); 
    header.onclick = null; 
};

window.switchToIdpkMode = function() { 
    appState = 'IDPK_LINE'; 
    inputValues.idpk = ""; 
    selectedIdpkRouteId = ""; 
    currentHybridTemplate = null; 

    ipcRenderer.invoke('gtfs-load-routes').then(db => { 
        databaseFiles = db; 
        if (appState === 'IDPK_LINE') {
            filteredFiles = databaseFiles; 
            window.updateLinkospojUI(); 
        }
    }).catch(()=>{});
    
    let lWrap = document.getElementById('linkospoj-wrapper'); 
    if(lWrap) lWrap.style.display = 'none'; 
    
    let idpkWrap = document.getElementById('idpk-db-wrapper'); 
    if(idpkWrap) {
        idpkWrap.style.display = 'flex'; 
        
        let warn = document.getElementById('idpk-no-sound-warn');
        if(!warn) {
            warn = document.createElement('div');
            warn.id = 'idpk-no-sound-warn';
            warn.innerHTML = "⚠️ <b style='text-transform:uppercase;'>Tyto linky jsou bez zvuku</b>";
            warn.style.cssText = "color: #f59e0b; font-size: 14px; text-align: center; margin-bottom: 10px; width: 100%; border: 1px solid #f59e0b; padding: 5px; border-radius: 5px; background: rgba(245, 158, 11, 0.1);";
            idpkWrap.insertBefore(warn, idpkWrap.firstChild);
        }
    }
    
    let keypad = document.getElementById('main-keypad'); 
    if(keypad) keypad.style.display = 'grid'; 
    
    let delK = document.getElementById('key-del'); 
    if(delK) delK.style.display = 'flex';
    
    let funK = document.getElementById('key-funk'); 
    if(funK) funK.style.display = 'none';
    
    linkospojFocus = 'input'; 
    isListOpen = false; 
    filteredFiles = databaseFiles; 
    
    window.updateLinkospojUI(); 
    
    let disp = document.getElementById('display-idpk'); 
    if(disp) disp.textContent = "-----"; 
};

window.backToManual = function() { 
    appState = 'LINKOSPOJ'; 
    inputValues.linkospoj = ""; 
    
    let d1 = document.getElementById('idpk-db-wrapper'); 
    if (d1) d1.style.display = 'none'; 
    
    let d2 = document.getElementById('idpk-direction-wrapper'); 
    if (d2) d2.style.display = 'none'; 
    
    let d3 = document.getElementById('linkospoj-wrapper'); 
    if (d3) d3.style.display = 'flex'; 
    
    let k = document.getElementById('main-keypad'); 
    if(k) k.style.display = 'grid';
    
    let del = document.getElementById('key-del'); 
    if(del) del.style.display = 'flex';
    
    let fnk = document.getElementById('key-funk'); 
    if(fnk) fnk.style.display = 'none';
    
    linkospojFocus = 'input'; 
    isListOpen = false; 

    ipcRenderer.invoke('get-link-files').then(files => { 
        availableFiles = files; 
        filteredFiles = files; 
        if (appState === 'LINKOSPOJ') {
            window.updateLinkospojUI(); 
        }
    }).catch(()=>{});
    
    window.updateLinkospojUI(); 
};

window.backToIdpkList = function() { 
    appState = 'IDPK_LINE'; 
    let d1 = document.getElementById('idpk-direction-wrapper'); 
    if(d1) d1.style.display = 'none'; 
    
    let d2 = document.getElementById('idpk-db-wrapper'); 
    if(d2) d2.style.display = 'flex'; 
    
    let del = document.getElementById('key-del'); 
    if(del) del.style.display = 'flex';
    
    let fnk = document.getElementById('key-funk'); 
    if(fnk) fnk.style.display = 'none';
};

window.backToIdpkMode = function() {
    appState = 'IDPK_LINE'; 
    let d1 = document.getElementById('idpk-direction-wrapper'); 
    if(d1) d1.style.display = 'none'; 
    
    let d2 = document.getElementById('idpk-db-wrapper'); 
    if(d2) d2.style.display = 'flex'; 
    
    let del = document.getElementById('key-del'); 
    if(del) del.style.display = 'flex';
    
    let fnk = document.getElementById('key-funk'); 
    if(fnk) fnk.style.display = 'none';
};

window.selectStartStop = function(s) { 
    window.playClick(); 
    selectedStartStop = s; 
    window.loadDestinationsForStart(); 
};

window.showStartStopSelection = function(starts) { 
    appState = 'IDPK_START'; 
    let w1 = document.getElementById('idpk-db-wrapper'); 
    if(w1) w1.style.display = 'none'; 
    
    let w2 = document.getElementById('linkospoj-wrapper'); 
    if(w2) w2.style.display = 'none'; 
    
    let w3 = document.getElementById('idpk-direction-wrapper'); 
    if(w3) w3.style.display = 'flex'; 
    
    let sl = document.getElementById('idpk-selected-line'); 
    if(sl) sl.textContent = "Linka: " + inputValues.idpk; 
    
    window.updateSelectionHeader("VÝCHOZÍ ZASTÁVKA", "window.backToIdpkMode()"); 
    
    const container = document.getElementById('direction-list'); 
    if(!container) return;
    
    container.innerHTML = ""; 
    if (starts.length === 0) { 
        window.showErrorModal("CHYBA", "Žádná data zastávek"); 
        return;
    } 
    
    starts.forEach(s => { 
        const div = document.createElement('div'); 
        div.style.padding = "15px"; 
        div.style.borderBottom = "1px solid #555"; 
        div.style.cursor = "pointer"; 
        div.style.color = "white"; 
        div.style.fontWeight = "bold"; 
        div.textContent = s; 
        div.setAttribute('onclick', `window.selectStartStop('${s}')`); 
        container.appendChild(div); 
    }); 
};

window.reloadStartStops = function() {
    isSystemLoading = true; 
    let l = document.getElementById('loadingScreen'); 
    if(l) l.style.display = 'flex'; 
    
    ipcRenderer.invoke('gtfs-get-start-stops', selectedIdpkRouteId).then(starts => { 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
        window.showStartStopSelection(starts); 
    }).catch(e => { 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
    });
};

window.selectDestination = function(d) { 
    window.playClick(); 
    selectedDestination = d; 
    window.loadTimesForTrip(); 
};

window.loadDestinationsForStart = function() { 
    isSystemLoading = true; 
    let l = document.getElementById('loadingScreen'); 
    if(l) l.style.display = 'flex'; 
    
    ipcRenderer.invoke('gtfs-get-destinations-from-start', { routeId: selectedIdpkRouteId, startStopName: selectedStartStop }).then(dests => { 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
        
        window.updateSelectionHeader("CÍLOVÁ STANICE", "window.reloadStartStops()"); 
        const container = document.getElementById('direction-list'); 
        if(!container) return; 
        container.innerHTML = ""; 
        
        dests.forEach(d => { 
            const div = document.createElement('div'); 
            div.style.padding = "15px"; 
            div.style.borderBottom = "1px solid #555"; 
            div.style.cursor = "pointer"; 
            div.style.color = "white"; 
            div.style.display = "flex"; 
            div.style.alignItems = "center"; 
            div.innerHTML = `<span style="color:var(--idpk-yellow); font-size:20px; margin-right:10px;">➔</span><span style="font-weight:bold; font-size:14px;">${d}</span>`; 
            div.setAttribute('onclick', `window.selectDestination('${d}')`); 
            container.appendChild(div); 
        }); 
    }).catch(e=>{ 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
    }); 
};

window.loadTimesForTrip = function() { 
    isSystemLoading = true; 
    let l = document.getElementById('loadingScreen'); 
    if(l) l.style.display = 'flex'; 
    
    ipcRenderer.invoke('gtfs-get-final-trips', { routeId: selectedIdpkRouteId, startStopName: selectedStartStop, headsign: selectedDestination }).then(trips => { 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
        
        window.updateSelectionHeader("VÝBĚR ČASU", "window.loadDestinationsForStart()"); 
        const container = document.getElementById('direction-list'); 
        if(!container) return; 
        
        container.innerHTML = `<div style="padding:10px; color:#aaa; font-size:12px;">Z: ${selectedStartStop}<br>DO: ${selectedDestination}</div>`; 
        
        if (trips.length === 0) { 
            window.showErrorModal("CHYBA", "Žádné spoje nenalezeny"); 
            return; 
        } 
        
        trips.forEach(trip => { 
            let displayName = trip.formattedName; 
            let badgeClass = "badge-yellow"; 
            if (trip.spojNum >= 100) badgeClass = "badge-green"; 
            
            const div = document.createElement('div'); 
            div.style.padding = "15px"; 
            div.style.borderBottom = "1px solid #555"; 
            div.style.cursor = "pointer"; 
            div.style.color = "white"; 
            div.style.display = "flex"; 
            div.style.alignItems = "center"; 
            div.style.justifyContent = "space-between"; 
            div.style.width = "90%"; 
            div.innerHTML = `<span style="color:white; font-weight:bold; font-size:20px;">${window.padTime(trip.time)}</span><span class="trip-badge ${badgeClass}">${displayName}</span>`; 
            div.setAttribute('onclick', `window.finalizeTripSelection('${trip.tripId}', '${trip.headsign}', '${trip.tripNumber}')`); 
            container.appendChild(div); 
        }); 
    }).catch(e=>{ 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
    }); 
};

window.finalizeTripSelection = function(tripId, destination, tripNumber) { 
    if (currentHybridTemplate) { 
        isSystemLoading = true; 
        let l = document.getElementById('loadingScreen'); 
        if(l) l.style.display = 'flex'; 
        
        ipcRenderer.invoke('hybrid-get-trip-data', { tripId: tripId, stopMapObj: currentHybridTemplate.stopMap }).then(response => { 
            isSystemLoading = false; 
            if(l) l.style.display = 'none'; 
            
            if (response.error) { 
                window.showErrorModal("CHYBA", response.error); 
                return; 
            } 
            
            routeData.isMuted = false; 
            routeData.line = currentHybridTemplate.lineNum; 
            routeData.routeId = selectedIdpkRouteId; 
            routeData.linkospojCode = tripNumber; 
            routeData.destination = response.destination; 
            routeData.stops = response.stops; 
            routeData.realStopIndex = 0; 
            routeData.previewStopIndex = 0; 
            drivePhase = 0; 
            
            let w = document.getElementById('idpk-direction-wrapper'); 
            if(w) w.style.display = 'none'; 
            
            window.initStatsTracking(); 
            window.switchToDriveScreen(); 
            window.sendDataToPanel(); 
        }).catch(e=>{ 
            isSystemLoading = false; 
            if(l) l.style.display = 'none'; 
        }); 
    } else { 
        window.startIdpkRide(tripId, destination, tripNumber); 
    } 
};

window.startIdpkRide = function(tripId, destination, tripNumber) { 
    isSystemLoading = true; 
    let l = document.getElementById('loadingScreen'); 
    if(l) l.style.display = 'flex'; 
    
    ipcRenderer.invoke('gtfs-get-stops', tripId).then(stops => { 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
        
        if (stops.error) { 
            window.showErrorModal("CHYBA", stops.error); 
            return; 
        } 
        if (stops.length === 0) { 
            window.showErrorModal("CHYBA", "Spoj nemá zastávky"); 
            return; 
        } 
        
        routeData.isMuted = true; 
        routeData.line = inputValues.idpk; 
        routeData.routeId = selectedIdpkRouteId; 
        routeData.linkospojCode = tripNumber || (inputValues.idpk + " (GTFS)"); 
        routeData.destination = destination; 
        routeData.stops = stops; 
        routeData.realStopIndex = 0; 
        routeData.previewStopIndex = 0; 
        drivePhase = 0; 
        
        let w = document.getElementById('idpk-direction-wrapper'); 
        if(w) w.style.display = 'none'; 
        
        window.initStatsTracking();
        window.switchToDriveScreen(); 
        window.sendDataToPanel(); 
    }).catch(e=>{ 
        isSystemLoading = false; 
        if(l) l.style.display = 'none'; 
    }); 
};

window.switchToLinkospojScreen = function() { 
    appState = 'LINKOSPOJ'; 
    inputValues.linkospoj = ""; 
    
    document.querySelectorAll('.login-view').forEach(v => { v.style.display = 'none'; }); 
    
    let d1 = document.getElementById('drive-ui-wrapper'); 
    if(d1) d1.style.display = 'none'; 
    
    let d2 = document.getElementById('drive-controls-area'); 
    if(d2) d2.style.display = 'none'; 
    
    let d3 = document.getElementById('linkospoj-wrapper'); 
    if(d3) d3.style.display = 'flex'; 
    
    let d4 = document.getElementById('idpk-db-wrapper'); 
    if(d4) d4.style.display = 'none'; 
    
    let d5 = document.getElementById('idpk-direction-wrapper'); 
    if(d5) d5.style.display = 'none'; 
    
    let k = document.getElementById('main-keypad'); 
    if(k) k.style.display = 'grid'; 
    
    let key1 = document.getElementById('key-del'); 
    if(key1) key1.style.display = 'flex'; 
    
    let key2 = document.getElementById('key-funk'); 
    if(key2) key2.style.display = 'none'; 
    
    window.updateLinkospojDisplay(); 
};
