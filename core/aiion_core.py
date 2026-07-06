#!/usr/bin/env python3
"""
aiion_core.py — Agente Autónomo AIION | Android/Termux/PC (Linux)
════════════════════════════════════════════════════
Nucleo de AIION, adaptado de la base de Sara OS v2 (agente privado de Estiven).
AIION es un proyecto separado, open source, con su propia memoria/DBs/keys.
Fusión completa: agente + voz + qa_tools + sensor_daemon
  · 28 tools (filesystem, android, sensores, voz, comunicación, tareas)
  · Sensores termux-api en tiempo real (17 sensores, SQLite WAL)
  · TTS Groq PlayAI + STT termux-speech-to-text
  · Paleta Drácula completa
  · RamGuard con swap automático
  · Memoria 3 niveles: L1 RAM / L2 TF-IDF / L3 SQLite
  · Pool multi-API con rotación automática
  · Interfaz avanzada con barra de estado en vivo
"""

import json, os, re, subprocess, sys, urllib.request, urllib.error
import time, math, threading, shutil, gc, hashlib, sqlite3, tempfile, signal
from pathlib import Path
from datetime import datetime
from collections import deque

# ══════════════════════════════════════════════════════════════════════════════
# PALETA DRÁCULA
# ══════════════════════════════════════════════════════════════════════════════
R       = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
ITALIC  = "\033[3m"

# Drácula exacto
D_BG      = "\033[48;2;40;42;54m"       # #282A36 fondo
D_FG      = "\033[38;2;248;248;242m"    # #F8F8F2 texto
D_CYAN    = "\033[38;2;139;233;253m"    # #8BE9FD
D_GREEN   = "\033[38;2;80;250;123m"     # #50FA7B
D_YELLOW  = "\033[38;2;241;250;140m"    # #F1FA8C
D_ORANGE  = "\033[38;2;255;184;108m"    # #FFB86C
D_RED     = "\033[38;2;255;85;85m"      # #FF5555
D_PINK    = "\033[38;2;255;121;198m"    # #FF79C6
D_PURPLE  = "\033[38;2;189;147;249m"    # #BD93F9
D_COMMENT = "\033[38;2;98;114;164m"     # #6272A4

def c(col, txt):  return f"{col}{txt}{R}"
def bold(txt):    return f"{BOLD}{txt}{R}"
def dim(txt):     return f"{DIM}{txt}{R}"

# Aliases cortos para uso frecuente
CY = D_CYAN; GR = D_GREEN; YL = D_YELLOW
OR = D_ORANGE; RE = D_RED; PK = D_PINK
PU = D_PURPLE; CO = D_COMMENT

# ══════════════════════════════════════════════════════════════════════════════
# BANNER + UI
# ══════════════════════════════════════════════════════════════════════════════
VERSION = "0.1"

# Paleta Neón Degradado (Azul a Amarillo)
N_BORDER = "\033[38;2;0;180;255m"   # Azul neón eléctrico
N_L1     = "\033[38;2;0;120;255m"   # Azul neón
N_L2     = "\033[38;2;0;180;255m"   # Azul claro neón
N_L3     = "\033[38;2;0;240;255m"   # Cyan neón
N_L4     = "\033[38;2;0;255;150m"   # Verde-cyan neón
N_L5     = "\033[38;2;150;255;0m"   # Amarillo-verde neón
N_L6     = "\033[38;2;255;230;0m"   # Amarillo neón

BANNER = f"""
{c(N_BORDER+BOLD,'╔══════════════════════════════════════════════════╗')}
{c(N_BORDER+BOLD,'║')}  {c(N_L1+BOLD,' █████╗ ██╗██╗ ██████╗ ███╗   ██╗')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L2+BOLD,'██╔══██╗██║██║██╔═══██╗████╗  ██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L3+BOLD,'███████║██║██║██║   ██║██╔██╗ ██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L4+BOLD,'██╔══██║██║██║██║   ██║██║╚██╗██║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L5+BOLD,'██║  ██║██║██║╚██████╔╝██║ ╚████║')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}  {c(N_L6+BOLD,'╚═╝  ╚═╝╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝')}             {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'║')}        {c(N_L6+BOLD, f'Agente Autónomo v{VERSION} — Android/Termux/PC')}     {c(N_BORDER+BOLD,'║')}
{c(N_BORDER+BOLD,'╚══════════════════════════════════════════════════╝')}
"""

def hr(char='─', col=CO): return c(col, char * 52)

def badge(label, col=PU):
    return f"{c(col+BOLD, f'[{label}]')}"

def status_bar():
    """Barra de estado en vivo: RAM | Sensores | Voz | Modelo"""
    ram  = RAMGUARD.stats_str()
    sens = f"{c(GR,'●')} Sensores" if SENSOR_STATE.get("running") else f"{c(CO,'○')} Sensores"
    voz  = f"{c(PK,'🔊')} Voz" if VOICE_STATE.get("enabled") else f"{c(CO,'🔇')} Voz"
    mdl  = c(CY, STATE.get("model","")[:20]) if STATE.get("model") else c(CO,"sin modelo")
    ts   = c(CO, datetime.now().strftime("%H:%M:%S"))
    return f"{ram}  {sens}  {voz}  {mdl}  {ts}"

# ══════════════════════════════════════════════════════════════════════════════
# RAM GUARD
# ══════════════════════════════════════════════════════════════════════════════
class RamGuard:
    STATES     = ["VERDE","AMARILLO","ROJO","CRÍTICO"]
    THRESHOLDS = [0.60, 0.80, 0.90, 1.0]
    INTERVAL   = 20
    SWAP_FILE  = str(Path.home() / "swapfile")
    SWAP_MB    = 1024

    def __init__(self):
        self._stop        = threading.Event()
        self._thread      = None
        self._state       = "VERDE"
        self._history     = deque(maxlen=20)
        self._actions     = 0
        self._swap_active = False

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="RamGuard", daemon=True)
        self._thread.start()

    def stop(self): self._stop.set()

    def _meminfo(self):
        info = {}
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0])
        except: pass
        return info

    def pressure(self):
        m = self._meminfo()
        return 1.0 - (m.get("MemAvailable", m.get("MemTotal",1)) / max(m.get("MemTotal",1),1))

    def stats_str(self):
        m       = self._meminfo()
        total   = m.get("MemTotal",0)//1024
        avail   = m.get("MemAvailable",0)//1024
        used    = total - avail
        pct     = self.pressure()*100
        col     = GR if pct<60 else YL if pct<80 else RE
        return f"{c(CO,'RAM')} {c(col+BOLD,f'{pct:.0f}%')} {c(CO,f'{used}/{total}MB')}"

    def trend(self):
        if len(self._history)<4: return "estable"
        ts=[x[0] for x in self._history]; ps=[x[1] for x in self._history]
        n=len(ts); t0=ts[0]; ts2=[t-t0 for t in ts]
        mt=sum(ts2)/n; mp=sum(ps)/n
        num=sum((ts2[i]-mt)*(ps[i]-mp) for i in range(n))
        den=sum((ts2[i]-mt)**2 for i in range(n)) or 1
        spm=(num/den)*60
        if abs(spm)<0.005: return "estable"
        return f"↑{spm:.1%}/m" if spm>0 else f"↓{abs(spm):.1%}/m"

    def _classify(self,p):
        for thresh,state in zip(self.THRESHOLDS,self.STATES):
            if p<thresh: return state
        return "CRÍTICO"

    def _loop(self):
        time.sleep(4)
        while not self._stop.is_set():
            try:
                p=self.pressure(); self._history.append((time.time(),p))
                self._state=self._classify(p)
                if p>=0.60: gc.collect()
                if p>=0.80: self._ensure_swap()
                if p>=0.90: self._kill_zombies()
            except: pass
            self._stop.wait(self.INTERVAL)

    def _ensure_swap(self):
        if self._swap_active: return
        try:
            if self._meminfo().get("SwapTotal",0)>0:
                self._swap_active=True; return
            free=shutil.disk_usage(str(Path.home())).free//(1024*1024)
            if free<self.SWAP_MB+200: return
            sp=Path(self.SWAP_FILE)
            if not sp.exists():
                subprocess.run(f"dd if=/dev/zero of={self.SWAP_FILE} bs=1M count={self.SWAP_MB} 2>/dev/null",
                               shell=True,timeout=90)
                subprocess.run(f"chmod 600 {self.SWAP_FILE} && mkswap {self.SWAP_FILE}",
                               shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            subprocess.run(f"swapon {self.SWAP_FILE}",shell=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self._swap_active=True; self._actions+=1
        except: pass

    def _kill_zombies(self):
        try:
            r=subprocess.run("ps aux|grep '[n]ode'|awk '{print $1}'",
                             shell=True,capture_output=True,text=True,timeout=5)
            my=str(os.getpid())
            for pid in r.stdout.strip().split():
                if pid!=my:
                    subprocess.run(f"kill -9 {pid}",shell=True,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    self._actions+=1
        except: pass

    def status(self): return f"{self.stats_str()} {c(CO,self.trend())} {c(CO,f'acc:{self._actions}')}"

RAMGUARD = RamGuard()

# ══════════════════════════════════════════════════════════════════════════════
# ÍNDICE COGNITIVO
# ══════════════════════════════════════════════════════════════════════════════
class CognitiveIndex:
    def __init__(self):
        self._read={}; self._written={}

    def mark_read(self, path, content=""):
        sha=hashlib.sha256(content.encode(errors="replace")).hexdigest()[:12]
        self._read[str(path)]={"sha":sha,"lines":content.count("\n")+1,"ts":datetime.now().isoformat()}

    def mark_written(self, path, action="write"):
        self._written[str(path)]={"action":action,"ts":datetime.now().isoformat()}

    def was_read(self,path): return str(path) in self._read

    def summary(self):
        lines=[f"{c(CY+BOLD,'📂 Índice cognitivo:')}"]
        if self._read:
            lines.append(f"  {c(GR,'Leídos')} ({len(self._read)}):")
            for p,m in self._read.items():
                tag = f"[{m['lines']}L sha:{m['sha']}]"
                lines.append(f"    {c(CO,p)}  {c(YL,tag)}")
        if self._written:
            lines.append(f"  {c(PK,'Modificados')} ({len(self._written)}):")
            for p,m in self._written.items():
                tag = f"[{m['action']} @ {m['ts'][:16]}]"
                lines.append(f"    {c(CO,p)}  {c(OR,tag)}")
        if not self._read and not self._written:
            lines.append(f"  {c(CO,'(vacío)')}")
        return "\n".join(lines)

    def context_block(self):
        if not self._read and not self._written: return ""
        parts=[]
        if self._read:
            parts.append("ARCHIVOS YA LEÍDOS:\n"+"\n".join(f"  - {p}" for p in self._read))
        if self._written:
            parts.append("ARCHIVOS MODIFICADOS:\n"+"\n".join(f"  - {p}" for p in self._written))
        return "\n".join(parts)

COGINDEX = CognitiveIndex()

# ══════════════════════════════════════════════════════════════════════════════
# MEMORIA PERSISTENTE L1/L2/L3
# ══════════════════════════════════════════════════════════════════════════════
# AIION tiene su propia carpeta de datos, separada de Sara OS.
# Nunca lee ni escribe archivos del home compartido (~/.agent_memory.md, etc).
AIION_HOME   = Path.home() / "AIION" / "data"
AIION_HOME.mkdir(parents=True, exist_ok=True)

MEMORY_FILE  = AIION_HOME / "aiion_memory.md"
HISTORY_FILE = AIION_HOME / "aiion_history.jsonl"
SENSOR_DB    = AIION_HOME / "aiion_sensor_data.db"
MAX_HISTORY  = 5

def memory_load():
    return MEMORY_FILE.read_text(errors='replace').strip() if MEMORY_FILE.exists() else ""

def memory_append(fact):
    existing=memory_load(); now=datetime.now().strftime("%Y-%m-%d")
    block=f"\n- [{now}] {fact.strip()}"
    if fact.strip() not in existing:
        MEMORY_FILE.write_text(existing+block+"\n")

def history_save(user_input, agent_response):
    entry={"ts":datetime.now().isoformat(),"user":user_input,"agent":agent_response}
    with open(HISTORY_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(entry,ensure_ascii=False)+"\n")

def history_load_all():
    if not HISTORY_FILE.exists(): return []
    entries=[]
    with open(HISTORY_FILE,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                try: entries.append(json.loads(line))
                except: pass
    return entries

def _tokenize(text): return re.findall(r'\w+',text.lower())

def _tfidf(query_tokens, doc_tokens):
    if not doc_tokens: return 0.0
    doc_set=set(doc_tokens)
    return sum(doc_tokens.count(t)/len(doc_tokens) for t in query_tokens if t in doc_set)

def history_search(query, top_k=MAX_HISTORY):
    entries=history_load_all()
    if not entries: return []
    qt=_tokenize(query)
    scored=[((_tfidf(qt,_tokenize(e.get("user","")+e.get("agent",""))),e)) for e in entries]
    scored=[x for x in scored if x[0]>0]
    scored.sort(key=lambda x:x[0],reverse=True)
    return [e for _,e in scored[:top_k]]

def history_summary_for_prompt(query):
    relevant=history_search(query)
    if not relevant: return ""
    lines=["CONVERSACIONES PASADAS RELEVANTES:"]
    for e in relevant:
        ts=e.get("ts","")[:10]
        lines.append(f"[{ts}] U: {e['user'][:120]}")
        lines.append(f"[{ts}] A: {e['agent'][:200]}\n")
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
# SENSOR DAEMON INTEGRADO
# ══════════════════════════════════════════════════════════════════════════════
SENSOR_STATE = {"running": False, "last": {}, "thread": None}
SENSOR_STOP  = threading.Event()

SENSOR_INTERVALS = {
    "battery":15, "wifi":20, "system":10, "sensors":8,
    "location":180, "cellinfo":30, "telephony":60,
    "volume":20, "brightness":30, "clipboard":15,
    "camera_info":120, "audio":25, "nfc":30,
}

def _sensor_db():
    con=sqlite3.connect(str(SENSOR_DB))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, sensor TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sensor_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, level TEXT NOT NULL,
            sensor TEXT NOT NULL, message TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_st ON readings(sensor,ts);
    """)
    con.commit()
    return con

def _sensor_save(sensor, data):
    try:
        con=_sensor_db()
        con.execute("INSERT INTO readings(ts,sensor,data) VALUES(?,?,?)",
                    (datetime.now().isoformat(),sensor,json.dumps(data,ensure_ascii=False)))
        con.execute("DELETE FROM readings WHERE ts < datetime('now','-3 days')")
        con.commit(); con.close()
        SENSOR_STATE["last"][sensor]={"ts":datetime.now().isoformat(),**data} if isinstance(data,dict) else {"ts":datetime.now().isoformat(),"raw":str(data)}
    except: pass

def _termux(cmd, timeout=10):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=timeout)
        if r.returncode==0 and r.stdout.strip():
            return json.loads(r.stdout.strip())
    except: pass
    return None

def _sh(cmd, timeout=6):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=timeout)
        return r.stdout.strip()
    except: return ""

# Samplers individuales
def _s_battery():
    d=_termux("termux-battery-status")
    if d: _sensor_save("battery",d)

def _s_wifi():
    d=_termux("termux-wifi-connectioninfo")
    if d: _sensor_save("wifi",d)

def _s_system():
    m={}
    for line in _sh("cat /proc/meminfo").splitlines():
        parts=line.split(":")
        if len(parts)==2:
            try: m[parts[0].strip()]=int(parts[1].strip().split()[0])
            except: pass
    total=m.get("MemTotal",1); avail=m.get("MemAvailable",total)
    load=_sh("cat /proc/loadavg").split()
    _sensor_save("system",{
        "ram_total_mb":total//1024,"ram_avail_mb":avail//1024,
        "ram_used_pct":round((total-avail)/total*100,1),
        "load_1m":load[0] if load else "?",
        "processes":_sh("ps aux 2>/dev/null|wc -l").strip()
    })

def _s_sensors():
    names=",".join(["TYPE_ACCELEROMETER","TYPE_GYROSCOPE","TYPE_LIGHT",
                    "TYPE_PROXIMITY","TYPE_MAGNETIC_FIELD","TYPE_GRAVITY",
                    "TYPE_LINEAR_ACCELERATION","TYPE_STEP_COUNTER","TYPE_PRESSURE"])
    d=_termux(f"termux-sensor -s '{names}' -d 500 -n 1",timeout=8)
    if d: _sensor_save("sensors",d)

def _s_location():
    d=_termux("termux-location -p passive",timeout=15)
    if not d: d=_termux("termux-location -p network",timeout=12)
    if d: _sensor_save("location",d)

def _s_cellinfo():
    d=_termux("termux-telephony-cellinfo")
    if d: _sensor_save("cellinfo",d)

def _s_telephony():
    d=_termux("termux-telephony-deviceinfo")
    if d: _sensor_save("telephony",d)

def _s_volume():
    d=_termux("termux-volume")
    if d: _sensor_save("volume",d)

def _s_brightness():
    b=_sh("cat /sys/class/leds/lcd-backlight/brightness 2>/dev/null || cat /sys/class/backlight/*/brightness 2>/dev/null|head -1")
    mx=_sh("cat /sys/class/leds/lcd-backlight/max_brightness 2>/dev/null || cat /sys/class/backlight/*/max_brightness 2>/dev/null|head -1")
    if b: _sensor_save("brightness",{"value":b,"max":mx})

def _s_clipboard():
    out=_sh("termux-clipboard-get",timeout=4)
    if out: _sensor_save("clipboard",{"content":out[:300]})

def _s_camera_info():
    d=_termux("termux-camera-info")
    if d: _sensor_save("camera_info",d)

def _s_audio():
    info=_sh("dumpsys audio 2>/dev/null|grep -E 'mode|ringerMode|volume'|head -8")
    if info: _sensor_save("audio",{"raw":info})

def _s_nfc():
    nfc=_sh("dumpsys nfc 2>/dev/null|grep -i 'enabled|state'|head -3")
    if nfc: _sensor_save("nfc",{"raw":nfc})

SENSOR_SAMPLERS = {
    "battery":_s_battery,"wifi":_s_wifi,"system":_s_system,
    "sensors":_s_sensors,"location":_s_location,"cellinfo":_s_cellinfo,
    "telephony":_s_telephony,"volume":_s_volume,"brightness":_s_brightness,
    "clipboard":_s_clipboard,"camera_info":_s_camera_info,
    "audio":_s_audio,"nfc":_s_nfc,
}

def _sensor_loop():
    last={k:0 for k in SENSOR_INTERVALS}
    SENSOR_STATE["running"]=True
    # Init DB
    try: con=_sensor_db(); con.close()
    except: pass
    while not SENSOR_STOP.is_set():
        now=time.time()
        for name,interval in SENSOR_INTERVALS.items():
            if now-last[name]>=interval:
                fn=SENSOR_SAMPLERS.get(name)
                if fn:
                    try: fn()
                    except: pass
                last[name]=now
        SENSOR_STOP.wait(4)
    SENSOR_STATE["running"]=False

def sensor_start():
    if SENSOR_STATE.get("running"): return
    SENSOR_STOP.clear()
    t=threading.Thread(target=_sensor_loop,name="SensorDaemon",daemon=True)
    t.start(); SENSOR_STATE["thread"]=t

def sensor_stop():
    SENSOR_STOP.set()

def sensor_last(sensor):
    return SENSOR_STATE["last"].get(sensor)

def sensor_query(sensor, minutes=60, limit=50):
    try:
        con=_sensor_db()
        rows=con.execute(
            "SELECT ts,data FROM readings WHERE sensor=? AND ts>=datetime('now',? ||' minutes') ORDER BY ts DESC LIMIT ?",
            (sensor,f"-{minutes}",limit)).fetchall()
        con.close()
        return [{"ts":r[0],**json.loads(r[1])} for r in rows]
    except: return []

# ══════════════════════════════════════════════════════════════════════════════
# VOZ — GROQ PLAYAI TTS + TERMUX STT
# ══════════════════════════════════════════════════════════════════════════════
VOICE_STATE = {
    "enabled": False, "voice": "Celeste-PlayAI",
    "volume": 100, "speed": 1.0, "last_error": "",
}
GROQ_TTS_URL  = "https://api.groq.com/openai/v1/audio/speech"
GROQ_TTS_MODEL= "playai-tts"
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY","")
TTS_CHUNK     = 800
VOICES        = ["Celeste-PlayAI","Valentina-PlayAI","Mateo-PlayAI","Fritz-PlayAI"]

def _clean_for_tts(text):
    text=re.sub(r'\*{1,2}([^*]+)\*{1,2}',r'\1',text)
    text=re.sub(r'`[^`]+`','',text)
    text=re.sub(r'#{1,6}\s+','',text)
    text=re.sub(r'\033\[[0-9;]*m','',text)
    text=re.sub(r'\n{2,}','. ',text)
    return re.sub(r'\n',' ',text).strip()

def _split_tts(text, max_len=TTS_CHUNK):
    if len(text)<=max_len: return [text]
    chunks=[]; sentences=re.split(r'(?<=[.!?])\s+',text); cur=""
    for s in sentences:
        if len(cur)+len(s)+1<=max_len: cur=(cur+" "+s).strip()
        else:
            if cur: chunks.append(cur)
            cur=s if len(s)<=max_len else s[:max_len]
    if cur: chunks.append(cur)
    return chunks or [text[:max_len]]

def _tts_chunk_api(text, voice):
    if not GROQ_API_KEY: return None
    payload=json.dumps({"model":GROQ_TTS_MODEL,"input":text,"voice":voice,"response_format":"mp3"}).encode()
    req=urllib.request.Request(GROQ_TTS_URL,data=payload,
        headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as r: return r.read()

def speak(text, blocking=True):
    if not VOICE_STATE["enabled"] or not text.strip(): return False
    clean=_clean_for_tts(text)
    if not clean: return False
    voice=VOICE_STATE["voice"]

    def _play():
        # Intentar Groq primero, fallback a termux-tts-speak
        if GROQ_API_KEY:
            for chunk in _split_tts(clean):
                try:
                    audio=_tts_chunk_api(chunk,voice)
                    if not audio: raise Exception("empty")
                    with tempfile.NamedTemporaryFile(suffix=".mp3",delete=False) as f:
                        f.write(audio); tmp=f.name
                    subprocess.run(["mpv","--no-video","--really-quiet",
                                   f"--volume={VOICE_STATE['volume']}",
                                   f"--speed={VOICE_STATE['speed']}",tmp],timeout=60)
                    os.unlink(tmp)
                except Exception as e:
                    VOICE_STATE["last_error"]=str(e)
                    _tts_fallback(clean); break
        else:
            _tts_fallback(clean)

    def _tts_fallback(text):
        try:
            subprocess.run(["termux-tts-speak","-r","1.0","-l","es",text[:400]],timeout=8)
        except: pass

    if blocking: _play()
    else: threading.Thread(target=_play,daemon=True).start()
    return True

def listen(prompt="🎤 Escuchando..."):
    print(c(PK,f"\n  {prompt}"),flush=True)
    try:
        r=subprocess.run(["termux-speech-to-text"],capture_output=True,text=True,timeout=30)
        text=r.stdout.strip()
        if text:
            print(c(GR,f"  🗣  {text}"))
            return text
        return ""
    except subprocess.TimeoutExpired:
        print(c(YL,"  Timeout STT")); return ""
    except Exception as e:
        print(c(RE,f"  STT: {e}")); return ""

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG + API POOL
# ══════════════════════════════════════════════════════════════════════════════
OLLAMA_LOCAL     = "http://localhost:11434"
OLLAMA_CLOUD     = "https://ollama.com"
MAX_ITER         = 12
PREFERRED_MODELS = ["qwen3-coder:480b","deepseek-v3.1:671b","gemma3:27b","qwen3.5:397b"]

STATE = {"model":"","api_keys":[],"key_index":0,"use_cloud":False}

def load_api_keys():
    env=os.environ.get("OLLAMA_API_KEY","").strip()
    if env: return [k.strip() for k in env.split(",") if k.strip()]
    kf=AIION_HOME/"ollama_keys"
    if kf.exists(): return [l.strip() for l in kf.read_text().splitlines() if l.strip()]
    kf2=AIION_HOME/"ollama_key"
    if kf2.exists(): return [kf2.read_text().strip()]
    return []

def current_key():
    keys=STATE["api_keys"]
    return keys[STATE["key_index"]%len(keys)] if keys else ""

def rotate_key():
    STATE["key_index"]=(STATE["key_index"]+1)%max(len(STATE["api_keys"]),1)
    k=current_key()
    print(c(YL,f"  🔑 Rotando key #{STATE['key_index']+1}: {k[:8]}..."))
    return k

# ══════════════════════════════════════════════════════════════════════════════
# TOOLS — 28 DEFINICIONES
# ══════════════════════════════════════════════════════════════════════════════
DANGEROUS_TOOLS = {"run_shell_command","write_file","replace","process_manager"}
SESSION_ALLOWED = set()

TOOLS = [
    # ── FILESYSTEM (7) ──────────────────────────────────────────────────────
    {"type":"function","function":{"name":"read_file","description":"Lee un archivo con números de línea.",
     "parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer"},"end_line":{"type":"integer"}},"required":["path"]}}},
    {"type":"function","function":{"name":"write_file","description":"Escribe o crea un archivo.",
     "parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
    {"type":"function","function":{"name":"replace","description":"Reemplaza texto único en un archivo (requiere permiso).",
     "parameters":{"type":"object","properties":{"path":{"type":"string"},"old_str":{"type":"string"},"new_str":{"type":"string"}},"required":["path","old_str","new_str"]}}},
    {"type":"function","function":{"name":"run_shell_command","description":"Ejecuta comando bash en Termux.",
     "parameters":{"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer"}},"required":["command"]}}},
    {"type":"function","function":{"name":"list_directory","description":"Lista archivos con tamaños.",
     "parameters":{"type":"object","properties":{"path":{"type":"string"},"show_hidden":{"type":"boolean"}},"required":["path"]}}},
    {"type":"function","function":{"name":"glob","description":"Busca archivos por patrón glob.",
     "parameters":{"type":"object","properties":{"pattern":{"type":"string"},"base_path":{"type":"string"}},"required":["pattern"]}}},
    {"type":"function","function":{"name":"grep_search","description":"Busca patrón regex en archivos.",
     "parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"},"recursive":{"type":"boolean"}},"required":["pattern","path"]}}},
    # ── WEB (1) ─────────────────────────────────────────────────────────────
    {"type":"function","function":{"name":"web_fetch","description":"Descarga texto de una URL.",
     "parameters":{"type":"object","properties":{"url":{"type":"string"},"max_chars":{"type":"integer"}},"required":["url"]}}},
    # ── MEMORIA (2) ─────────────────────────────────────────────────────────
    {"type":"function","function":{"name":"diff_files","description":"Diferencias entre dos archivos.",
     "parameters":{"type":"object","properties":{"path_a":{"type":"string"},"path_b":{"type":"string"},"context_lines":{"type":"integer"}},"required":["path_a"]}}},
    {"type":"function","function":{"name":"memory_search","description":"Busca en historial de conversaciones.",
     "parameters":{"type":"object","properties":{"query":{"type":"string"},"top_k":{"type":"integer"}},"required":["query"]}}},
    # ── PROCESOS (1) ────────────────────────────────────────────────────────
    {"type":"function","function":{"name":"process_manager","description":"Lista, busca o mata procesos.",
     "parameters":{"type":"object","properties":{"action":{"type":"string","enum":["list","find","kill"]},"target":{"type":"string"},"signal":{"type":"string"}},"required":["action"]}}},
    # ── ANDROID/DEVICE (5) ──────────────────────────────────────────────────
    {"type":"function","function":{"name":"get_android_status","description":"Estado completo del dispositivo Android: batería, wifi, sistema, sensores en tiempo real.",
     "parameters":{"type":"object","properties":{"detail":{"type":"string","enum":["all","battery","wifi","system","sensors","location"]}},"required":[]}}},
    {"type":"function","function":{"name":"sensor_query","description":"Consulta historial de sensores termux-api (battery, wifi, location, system, sensors, etc).",
     "parameters":{"type":"object","properties":{"sensor":{"type":"string"},"minutes":{"type":"integer"},"limit":{"type":"integer"}},"required":["sensor"]}}},
    {"type":"function","function":{"name":"take_photo","description":"Toma foto con cámara del dispositivo.",
     "parameters":{"type":"object","properties":{"camera_id":{"type":"integer"},"filename":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"listar_camaras","description":"Lista cámaras disponibles.",
     "parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_gps","description":"Obtiene ubicación GPS actual.",
     "parameters":{"type":"object","properties":{"provider":{"type":"string","enum":["gps","network","passive"]}},"required":[]}}},
    # ── NOTIFICACIONES (2) ──────────────────────────────────────────────────
    {"type":"function","function":{"name":"notificacion","description":"Envía notificación Android.",
     "parameters":{"type":"object","properties":{"title":{"type":"string"},"content":{"type":"string"},"id":{"type":"integer"}},"required":["title","content"]}}},
    {"type":"function","function":{"name":"cancelar_notificacion","description":"Cancela notificación por ID.",
     "parameters":{"type":"object","properties":{"id":{"type":"integer"}},"required":["id"]}}},
    # ── COMUNICACIÓN (5) ────────────────────────────────────────────────────
    {"type":"function","function":{"name":"leer_sms","description":"Lee mensajes SMS.",
     "parameters":{"type":"object","properties":{"limit":{"type":"integer"},"type":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"enviar_sms","description":"Envía SMS a un número.",
     "parameters":{"type":"object","properties":{"number":{"type":"string"},"message":{"type":"string"}},"required":["number","message"]}}},
    {"type":"function","function":{"name":"historial_llamadas","description":"Historial de llamadas.",
     "parameters":{"type":"object","properties":{"limit":{"type":"integer"}},"required":[]}}},
    {"type":"function","function":{"name":"hacer_llamada","description":"Realiza una llamada telefónica.",
     "parameters":{"type":"object","properties":{"number":{"type":"string"}},"required":["number"]}}},
    {"type":"function","function":{"name":"info_telefonia","description":"Info del dispositivo de telefonía.",
     "parameters":{"type":"object","properties":{},"required":[]}}},
    # ── VOZ (2) ─────────────────────────────────────────────────────────────
    {"type":"function","function":{"name":"hablar","description":"Sintetiza voz TTS (Groq PlayAI).",
     "parameters":{"type":"object","properties":{"texto":{"type":"string"},"voz":{"type":"string"}},"required":["texto"]}}},
    {"type":"function","function":{"name":"listar_voces","description":"Lista voces TTS disponibles.",
     "parameters":{"type":"object","properties":{},"required":[]}}},
    # ── TAREAS (3) ──────────────────────────────────────────────────────────
    {"type":"function","function":{"name":"crear_tarea","description":"Programa tarea con cron/at.",
     "parameters":{"type":"object","properties":{"comando":{"type":"string"},"cuando":{"type":"string"},"nombre":{"type":"string"}},"required":["comando","cuando"]}}},
    {"type":"function","function":{"name":"listar_tareas","description":"Lista tareas programadas.",
     "parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"eliminar_tarea","description":"Elimina tarea programada por nombre o ID.",
     "parameters":{"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}}},
]

# ══════════════════════════════════════════════════════════════════════════════
# IMPLEMENTACIÓN DE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

def tool_read_file(path, start_line=None, end_line=None):
    try:
        p=Path(path).expanduser()
        if not p.exists(): return f"Error: No existe: {path}"
        content=p.read_text(errors='replace')
        lines=content.splitlines()
        if start_line or end_line:
            s=(start_line or 1)-1; e=end_line or len(lines)
            lines=lines[s:e]
        COGINDEX.mark_read(path,content)
        return f"Archivo {path} ({len(lines)} líneas):\n"+"\n".join(f"{i+1:4}│ {l}" for i,l in enumerate(lines))
    except Exception as ex: return f"Error: {ex}"

def tool_write_file(path, content):
    try:
        p=Path(path).expanduser()
        if p.exists():
            p.with_suffix(p.suffix+".bak").write_text(p.read_text(errors='replace'))
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(content); COGINDEX.mark_written(path,"write")
        return f"OK: {path} escrito ({len(content)} bytes)"
    except Exception as ex: return f"Error: {ex}"

def tool_replace(path, old_str, new_str):
    try:
        p=Path(path).expanduser(); content=p.read_text(errors='replace')
        count=content.count(old_str)
        if count==0: return f"Error: Texto no encontrado en {path}"
        if count>1:  return f"Error: Texto aparece {count} veces — debe ser único"
        p.with_suffix(p.suffix+".bak").write_text(content)
        p.write_text(content.replace(old_str,new_str,1)); COGINDEX.mark_written(path,"replace")
        return f"OK: Reemplazo exitoso en {path}"
    except Exception as ex: return f"Error: {ex}"

def tool_run_shell_command(command, timeout=60):
    try:
        r=subprocess.run(command,shell=True,capture_output=True,text=True,timeout=timeout)
        parts=[]
        if r.stdout.strip(): parts.append(f"STDOUT:\n{r.stdout.strip()}")
        if r.stderr.strip(): parts.append(f"STDERR:\n{r.stderr.strip()}")
        if r.returncode:     parts.append(f"Exit: {r.returncode}")
        return "\n".join(parts) if parts else "OK: sin salida"
    except subprocess.TimeoutExpired: return f"Error: Timeout ({timeout}s)"
    except Exception as ex: return f"Error: {ex}"

def tool_list_directory(path, show_hidden=False):
    try:
        p=Path(path).expanduser()
        if not p.exists(): return f"Error: No existe: {path}"
        entries=sorted(p.iterdir(),key=lambda x:(x.is_file(),x.name))
        lines=[]
        for e in entries:
            if not show_hidden and e.name.startswith('.'): continue
            icon="📁" if e.is_dir() else "📄"
            size=f" {e.stat().st_size}B" if e.is_file() else ""
            lines.append(f"{icon} {e.name}{size}")
        return f"Dir {path} ({len(lines)} entradas):\n"+"\n".join(lines) if lines else f"{path}: vacío"
    except Exception as ex: return f"Error: {ex}"

def tool_glob(pattern, base_path="."):
    try:
        matches=sorted(Path(base_path).expanduser().glob(pattern))
        if not matches: return f"Sin resultados: {pattern}"
        return f"{len(matches)} archivos:\n"+"\n".join(str(m) for m in matches[:100])
    except Exception as ex: return f"Error: {ex}"

def tool_grep_search(pattern, path, recursive=True):
    try:
        flag="-r" if recursive else ""
        cmd=f"grep -n {flag} -E '{pattern}' '{path}' 2>/dev/null | head -60"
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=20)
        out=r.stdout.strip()
        return f"Resultados '{pattern}':\n{out}" if out else f"Sin coincidencias: {pattern}"
    except Exception as ex: return f"Error: {ex}"

def tool_web_fetch(url, max_chars=4000):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=20) as r:
            content=r.read().decode('utf-8',errors='replace')
        content=re.sub(r'<style[^>]*>.*?</style>','',content,flags=re.DOTALL)
        content=re.sub(r'<script[^>]*>.*?</script>','',content,flags=re.DOTALL)
        content=re.sub(r'<[^>]+>','',content)
        content=re.sub(r'\n{3,}','\n\n',content).strip()
        return content[:max_chars]+("\n...[truncado]" if len(content)>max_chars else "")
    except Exception as ex: return f"Error: {ex}"

def tool_diff_files(path_a, path_b="", context_lines=3):
    try:
        pa=Path(path_a).expanduser()
        if not pa.exists(): return f"Error: No existe: {path_a}"
        pb=pa.with_suffix(pa.suffix+".bak") if not path_b else Path(path_b).expanduser()
        if not pb.exists(): return f"No hay backup de {path_a}. Pasa path_b explícito."
        r=subprocess.run(f"diff -u '{pb}' '{pa}'|head -120",
                         shell=True,capture_output=True,text=True,timeout=15)
        return f"Diff {pb}→{pa}:\n{r.stdout.strip()}" if r.stdout.strip() else "Archivos idénticos."
    except Exception as ex: return f"Error: {ex}"

def tool_memory_search(query, top_k=3):
    results=history_search(query,top_k=top_k)
    if not results: return "Sin resultados en historial."
    lines=[f"Resultados para '{query}':"]
    for i,e in enumerate(results,1):
        lines.append(f"\n[{i}] {e.get('ts','')[:10]}")
        lines.append(f"  U: {e['user'][:150]}")
        lines.append(f"  A: {e['agent'][:300]}")
    return "\n".join(lines)

def tool_process_manager(action, target="", signal="TERM"):
    try:
        if action=="list":
            r=subprocess.run("ps aux --sort=-%mem|head -20",shell=True,capture_output=True,text=True,timeout=10)
            return f"Top procesos RAM:\n{r.stdout.strip()}"
        elif action=="find":
            r=subprocess.run(f"ps aux|grep -i '{target}'|grep -v grep",shell=True,capture_output=True,text=True,timeout=10)
            return f"Procesos '{target}':\n{r.stdout.strip()}" if r.stdout.strip() else f"No encontrado: {target}"
        elif action=="kill":
            try: pid=int(target)
            except: return f"PID inválido: {target}"
            if pid==os.getpid(): return "Error: No puedes matar el agente."
            sig="-15" if signal.upper()=="TERM" else "-9"
            r=subprocess.run(f"kill {sig} {pid}",shell=True,capture_output=True,text=True,timeout=10)
            return f"OK: PID {pid} terminado." if r.returncode==0 else f"Error: {r.stderr.strip()}"
        return f"Acción desconocida: {action}"
    except Exception as ex: return f"Error: {ex}"

def tool_get_android_status(detail="all"):
    parts={}
    # Siempre incluir datos en tiempo real del sensor daemon
    for sensor in ["battery","wifi","system","sensors","location"]:
        if detail=="all" or detail==sensor:
            d=sensor_last(sensor)
            if d: parts[sensor]=d
    # Fallback si sensores no corrieron aun
    if not parts.get("battery"):
        d=_termux("termux-battery-status")
        if d: parts["battery"]=d
    if not parts.get("wifi"):
        d=_termux("termux-wifi-connectioninfo")
        if d: parts["wifi"]=d
    return json.dumps(parts,indent=2,ensure_ascii=False) if parts else "Sin datos de sensores aún (espera 10s)"

def tool_sensor_query(sensor, minutes=60, limit=50):
    data=sensor_query(sensor,minutes,limit)
    if not data: return f"Sin datos de '{sensor}' en los últimos {minutes} minutos."
    return f"Sensor '{sensor}' — {len(data)} lecturas (últimos {minutes}min):\n"+json.dumps(data[-5:],indent=2,ensure_ascii=False)

def tool_take_photo(camera_id=0, filename=""):
    try:
        fn=filename or f"~/foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        fn=str(Path(fn).expanduser())
        r=subprocess.run(f"termux-camera-photo -c {camera_id} {fn}",
                         shell=True,capture_output=True,text=True,timeout=15)
        if r.returncode==0 and Path(fn).exists():
            size=Path(fn).stat().st_size
            return f"OK: Foto guardada en {fn} ({size} bytes)"
        return f"Error: {r.stderr.strip() or 'cámara no disponible'}"
    except Exception as ex: return f"Error: {ex}"

def tool_listar_camaras():
    d=_termux("termux-camera-info")
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: termux-api no disponible"

def tool_get_gps(provider="network"):
    d=_termux(f"termux-location -p {provider}",timeout=20)
    if not d and provider!="network": d=_termux("termux-location -p network",timeout=15)
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: no se pudo obtener ubicación"

def tool_notificacion(title, content, id=1234):
    r=subprocess.run(f"termux-notification --title '{title}' --content '{content}' --id {id}",
                     shell=True,capture_output=True,text=True,timeout=8)
    return "OK: Notificación enviada" if r.returncode==0 else f"Error: {r.stderr.strip()}"

def tool_cancelar_notificacion(id):
    r=subprocess.run(f"termux-notification-remove {id}",shell=True,capture_output=True,text=True,timeout=5)
    return f"OK: Notificación {id} cancelada" if r.returncode==0 else f"Error: {r.stderr.strip()}"

def tool_leer_sms(limit=5, type="all"):
    d=_termux(f"termux-sms-list -l {limit} -t {type}",timeout=12)
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: no se pudo leer SMS"

def tool_enviar_sms(number, message):
    r=subprocess.run(f"termux-sms-send -n '{number}' '{message}'",
                     shell=True,capture_output=True,text=True,timeout=15)
    return f"OK: SMS enviado a {number}" if r.returncode==0 else f"Error: {r.stderr.strip()}"

def tool_historial_llamadas(limit=10):
    d=_termux(f"termux-call-log -l {limit}",timeout=10)
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: no se pudo leer historial"

def tool_hacer_llamada(number):
    r=subprocess.run(f"termux-telephony-call {number}",shell=True,capture_output=True,text=True,timeout=10)
    return f"OK: Llamando a {number}" if r.returncode==0 else f"Error: {r.stderr.strip()}"

def tool_info_telefonia():
    d=_termux("termux-telephony-deviceinfo")
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: termux-api no disponible"

def tool_hablar(texto, voz=None):
    if voz and voz in VOICES: VOICE_STATE["voice"]=voz
    old_enabled=VOICE_STATE["enabled"]
    VOICE_STATE["enabled"]=True
    result=speak(texto,blocking=True)
    VOICE_STATE["enabled"]=old_enabled
    return f"OK: '{texto[:50]}...' sintetizado" if result else "Error: TTS falló — verifica GROQ_API_KEY o mpv"

def tool_listar_voces():
    lines=[f"Voces disponibles ({GROQ_TTS_MODEL}):"]
    for v in VOICES:
        marker=" ← activa" if v==VOICE_STATE["voice"] else ""
        lines.append(f"  {v}{marker}")
    return "\n".join(lines)

def tool_crear_tarea(comando, cuando, nombre="tarea_aiion"):
    try:
        # Intentar con at
        r=subprocess.run(f"echo '{comando}' | at {cuando} 2>&1",
                         shell=True,capture_output=True,text=True,timeout=10)
        if r.returncode==0: return f"OK: Tarea programada para '{cuando}'"
        # Fallback crontab
        r2=subprocess.run("crontab -l 2>/dev/null",shell=True,capture_output=True,text=True,timeout=5)
        existing=r2.stdout.strip()
        new_line=f"# {nombre}\n{cuando} {comando}"
        new_cron=existing+"\n"+new_line if existing else new_line
        r3=subprocess.run("crontab -",shell=True,input=new_cron,capture_output=True,text=True,timeout=5)
        return "OK: Tarea añadida a crontab" if r3.returncode==0 else f"Error: {r3.stderr.strip()}"
    except Exception as ex: return f"Error: {ex}"

def tool_listar_tareas():
    parts=[]
    cron=_sh("crontab -l 2>/dev/null")
    if cron: parts.append(f"Crontab:\n{cron}")
    atq=_sh("atq 2>/dev/null")
    if atq: parts.append(f"At queue:\n{atq}")
    return "\n\n".join(parts) if parts else "Sin tareas programadas"

def tool_eliminar_tarea(id):
    r=subprocess.run(f"atrm {id} 2>/dev/null || echo 'intento_cron'",
                     shell=True,capture_output=True,text=True,timeout=5)
    if "intento_cron" not in r.stdout:
        return f"OK: Tarea at {id} eliminada"
    r2=subprocess.run("crontab -l 2>/dev/null",shell=True,capture_output=True,text=True,timeout=5)
    lines=[l for l in r2.stdout.splitlines() if id not in l]
    r3=subprocess.run("crontab -",shell=True,input="\n".join(lines),capture_output=True,text=True,timeout=5)
    return "OK: Tarea eliminada de crontab" if r3.returncode==0 else f"Error: {r3.stderr.strip()}"

# ── Mapa de tools ────────────────────────────────────────────────────────────
TOOL_MAP = {
    "read_file":            tool_read_file,
    "write_file":           tool_write_file,
    "replace":              tool_replace,
    "run_shell_command":    tool_run_shell_command,
    "list_directory":       tool_list_directory,
    "glob":                 tool_glob,
    "grep_search":          tool_grep_search,
    "web_fetch":            tool_web_fetch,
    "diff_files":           tool_diff_files,
    "memory_search":        tool_memory_search,
    "process_manager":      tool_process_manager,
    "get_android_status":   tool_get_android_status,
    "sensor_query":         tool_sensor_query,
    "take_photo":           tool_take_photo,
    "listar_camaras":       tool_listar_camaras,
    "get_gps":              tool_get_gps,
    "notificacion":         tool_notificacion,
    "cancelar_notificacion":tool_cancelar_notificacion,
    "leer_sms":             tool_leer_sms,
    "enviar_sms":           tool_enviar_sms,
    "historial_llamadas":   tool_historial_llamadas,
    "hacer_llamada":        tool_hacer_llamada,
    "info_telefonia":       tool_info_telefonia,
    "hablar":               tool_hablar,
    "listar_voces":         tool_listar_voces,
    "crear_tarea":          tool_crear_tarea,
    "listar_tareas":        tool_listar_tareas,
    "eliminar_tarea":       tool_eliminar_tarea,
}

assert len(TOOL_MAP)==28, f"Error: {len(TOOL_MAP)} tools (esperadas 28)"

# ══════════════════════════════════════════════════════════════════════════════
# PERMISOS
# ══════════════════════════════════════════════════════════════════════════════
def ask_permission(fn_name, fn_args):
    if fn_name not in DANGEROUS_TOOLS: return True
    if fn_name in SESSION_ALLOWED:     return True
    if fn_name=="process_manager" and fn_args.get("action")=="list": return True
    preview=json.dumps(fn_args,ensure_ascii=False,indent=2)
    if len(preview)>300: preview=preview[:300]+"\n  ..."
    print(f"\n{c(YL+BOLD,'┌─ Permiso requerido ─────────────────────')}")
    print(f"{c(YL,'│')} {c(PK+BOLD,fn_name)}")
    print(c(CO,f"│ {preview.replace(chr(10), chr(10)+'│ ')}"))
    print(f"{c(YL,'└─────────────────────────────────────────')}")
    print(f"  {c(GR,'[1]')} Permitir una vez   {c(CY,'[2]')} Permitir sesión   {c(RE,'[3]')} Cancelar\n")
    while True:
        try: ch=input(c(PU,"  › ")).strip()
        except (KeyboardInterrupt,EOFError): ch="3"
        if ch in("1",""): return True
        if ch=="2": SESSION_ALLOWED.add(fn_name); return True
        if ch=="3": return False
        print(c(RE,"  Escribe 1, 2 o 3"))

_tool_err = {}

def execute_tool(name, args):
    fn=TOOL_MAP.get(name)
    if not fn: return f"Tool desconocida: {name}"
    REQUIRED={"run_shell_command":"command","write_file":"path","read_file":"path",
               "replace":"path","list_directory":"path","grep_search":"pattern",
               "glob":"pattern","web_fetch":"url","diff_files":"path_a",
               "memory_search":"query","process_manager":"action",
               "enviar_sms":"number","hacer_llamada":"number","hablar":"texto",
               "crear_tarea":"comando","eliminar_tarea":"id","sensor_query":"sensor"}
    req=REQUIRED.get(name)
    if req and not (args or {}).get(req):
        _tool_err[name]=_tool_err.get(name,0)+1
        if _tool_err[name]>=2:
            _tool_err[name]=0
            return f"STOP: '{name}' falló sin '{req}' — responde con lo que sabes."
        return f"Error: '{name}' requiere '{req}'"
    if not ask_permission(name,args): return "Acción cancelada."
    _tool_err[name]=0
    try:
        return fn(**args)
    except TypeError as e:
        import inspect; sig=inspect.signature(fn)
        return f"Error args '{name}': {e}. Firma: {name}{sig}"
    except Exception as e:
        return f"Error inesperado '{name}': {e}"

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════
def build_system_prompt(user_input=""):
    home=str(Path.home()); cwd=os.getcwd()
    now=datetime.now().strftime("%Y-%m-%d %H:%M")
    tools_desc="\n".join([f"- {t['function']['name']}: {t['function']['description']}" for t in TOOLS])
    mem=memory_load()
    mem_block=f"\nMEMORIA DEL USUARIO:\n{mem}\n" if mem else ""
    hist=history_summary_for_prompt(user_input) if user_input else ""
    hist_block=f"\n{hist}\n" if hist else ""
    cog=COGINDEX.context_block()
    cog_block=f"\n{cog}\n" if cog else ""
    # Contexto sensorial en tiempo real
    sens_parts=[]
    for s in ["battery","wifi","system","sensors"]:
        d=sensor_last(s)
        if d: sens_parts.append(f"  {s}: {json.dumps(d,ensure_ascii=False)[:150]}")
    sens_block=("\nESTADO SENSORIAL EN TIEMPO REAL:\n"+"\n".join(sens_parts)+"\n") if sens_parts else ""
    keys_info=f"Pool {len(STATE['api_keys'])} keys" if STATE["use_cloud"] else "Local"

    return (
        "Eres AIION, agente autónomo experto en Linux/Android/Termux con herramientas reales.\n"
        "Tienes acceso a sensores del dispositivo en tiempo real (batería, wifi, GPS, etc).\n"
        "NUNCA describes lo que harías — SIEMPRE actúas usando herramientas.\n\n"
        f"FECHA: {now} | MODO: {'Nube ('+keys_info+')' if STATE['use_cloud'] else 'Local'}\n"
        f"HOME: {home} | CWD: {cwd}\n"
        "IMPORTANTE: En Termux el home es /data/data/com.termux/files/home\n"
        +mem_block+hist_block+cog_block+sens_block+
        "\nHERRAMIENTAS:\n"+tools_desc+
        "\n\n════════ PROTOCOLO REACT ════════\n"
        "Para usar herramienta:\n"
        "Pensamiento: [razón]\n"
        "Accion: nombre_tool\n"
        "Parametros: {\"key\": \"val\"}\n\n"
        "Para respuesta final:\n"
        "Respuesta: [texto en español]\n\n"
        "════════ REGLAS ════════\n"
        "✅ Lee archivo ANTES de editar\n"
        "✅ Usa replace para cambios pequeños\n"
        "✅ Encadena tools sin límite\n"
        "✅ Responde SIEMPRE en español\n"
        "❌ NUNCA inventes resultados de tools\n"
        "❌ NUNCA omitas Parametros\n"
    )

# ══════════════════════════════════════════════════════════════════════════════
# OLLAMA API
# ══════════════════════════════════════════════════════════════════════════════
# ── Modelos que soportan tool calling nativo ────────────────────────────────
# Se detecta automáticamente; se puede forzar con /toolmode on|off
TOOL_CALL_STATE = {"native": True}  # True=intentar nativo, False=forzar ReAct

def _build_payload(messages, use_tools=True):
    base = {"model": STATE["model"], "messages": messages, "stream": False}
    if use_tools:
        base["tools"] = TOOLS
    if STATE["use_cloud"]:
        base["options"] = {"temperature": 0.1}
    else:
        base["options"] = {"temperature": 0.1, "num_ctx": 8192}
    return json.dumps(base).encode()

def _do_request(payload, retry=0):
    if STATE["use_cloud"]:
        req = urllib.request.Request(
            f"{OLLAMA_CLOUD}/api/chat", data=payload,
            headers={"Content-Type":"application/json",
                     "Authorization":f"Bearer {current_key()}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401,429) and len(STATE["api_keys"])>1 and retry<len(STATE["api_keys"]):
                rotate_key()
                return _do_request(payload, retry=retry+1)
            raise
    else:
        req = urllib.request.Request(
            f"{OLLAMA_LOCAL}/api/chat", data=payload,
            headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())

def chat_native(messages, retry=0):
    """Llama con tool calling nativo. Retorna (tipo, datos).
       tipo='tool_call' → datos=[(name,args,id), ...]
       tipo='text'      → datos=str
    """
    payload = _build_payload(messages, use_tools=True)
    resp    = _do_request(payload, retry=retry)
    msg     = resp.get("message", {})
    calls   = msg.get("tool_calls") or []
    if calls:
        parsed = []
        for tc in calls:
            fn   = tc.get("function", {})
            name = fn.get("name","")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except: args = {}
            parsed.append((name, args, tc.get("id","")))
        return ("tool_call", parsed, msg)
    return ("text", msg.get("content",""), msg)

def chat_react_text(messages, retry=0):
    """Llama SIN tools (ReAct texto plano). Retorna string."""
    payload = _build_payload(messages, use_tools=False)
    resp    = _do_request(payload, retry=retry)
    return resp.get("message",{}).get("content","")

def parse_react(text):
    """Parser ReAct de fallback."""
    m = re.search(
        r'[Aa]ccion\s*:\s*(\w+)\s*\n[Pp]arametros\s*:\s*(\{.*?\})\s*(?=\n[A-ZÁÉÍÓÚ]|\Z)',
        text, re.DOTALL)
    if not m:
        m = re.search(r'[Aa]ccion\s*:\s*(\w+)\s*\n[Pp]arametros\s*:\s*(\{[^}]*\})',
                      text, re.DOTALL)
    if m:
        name = m.group(1).strip(); raw = m.group(2).strip()
        try: args = json.loads(raw)
        except:
            try: args = json.loads(raw.replace("'",'"'))
            except: args = {}
        th = re.search(r'[Pp]ensamiento\s*:\s*(.+?)(?=\n[Aa]ccion)', text, re.DOTALL)
        return ("action", name, args, th.group(1).strip() if th else "")
    resp = re.search(r'[Rr]espuesta\s*:\s*(.+)', text, re.DOTALL)
    if resp: return ("final", resp.group(1).strip())
    return ("final", text.strip())

# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICACIÓN TERMUX
# ══════════════════════════════════════════════════════════════════════════════
_NOTIFY_OK=None
def notify_response(text, steps=0):
    global _NOTIFY_OK
    if _NOTIFY_OK is None: _NOTIFY_OK=bool(shutil.which("termux-notification"))
    if not _NOTIFY_OK: return
    try:
        summary=text.strip().replace('"',"'")[:80].replace('\n',' ')
        if len(text)>80: summary+="…"
        tag=f" ({steps} pasos)" if steps>1 else ""
        subprocess.Popen(["termux-notification","--title",f"AIION{tag}",
                         "--content",summary,"--icon","message","--id","aiion","--priority","high"],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# LOOP AGENTE — tool calling nativo + fallback ReAct
# ══════════════════════════════════════════════════════════════════════════════
def _print_final(final_response, step):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"\n{c(PU,'╔')+c(PU,'═'*50)}")
    print(f"{c(PU,'║')} {c(PK+BOLD,'AIION')} {c(CO,'['+now+']')}")
    print(c(PU,'╟'+'─'*50))
    for line in final_response.split('\n'):
        print(f"{c(PU,'║')} {c(D_FG,line)}")
    print(c(PU,'╚'+'═'*50)+"\n")

def run_agent(user_input, history):
    messages     = [{"role":"system","content":build_system_prompt(user_input)}]
    messages    += history
    messages.append({"role":"user","content":user_input})
    final_response = ""
    spinner        = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    # ── Modo nativo ───────────────────────────────────────────────────────────
    if TOOL_CALL_STATE["native"]:
        for step in range(MAX_ITER):
            sp = spinner[step % len(spinner)]
            print(c(PU,f"  {sp} Pensando... paso {step+1}/{MAX_ITER}"),end="\r",flush=True)
            try:
                kind, data, raw_msg = chat_native(messages)
            except Exception as ex:
                # Si falla tool calling, degradar a ReAct para esta sesión
                TOOL_CALL_STATE["native"] = False
                print(c(YL,f"\n  ⚠ Tool calling no soportado, usando ReAct ({ex})"))
                break
            print(" "*55, end="\r")

            if kind == "tool_call":
                # El modelo quiere llamar tools
                messages.append({"role":"assistant","content": raw_msg.get("content",""),
                                  "tool_calls": raw_msg.get("tool_calls",[])})
                for fn_name, fn_args, call_id in data:
                    thought = raw_msg.get("content","").strip()
                    if thought:
                        print(f"  {c(CO,'💭')} {c(CO+ITALIC,thought[:100])}")
                    if fn_name not in TOOL_MAP:
                        obs = f"Error: '{fn_name}' no existe. Disponibles: {', '.join(TOOL_MAP.keys())}"
                    else:
                        args_prev = json.dumps(fn_args, ensure_ascii=False)[:60]
                        print(f"  {c(PU,'▸')} {c(CY+BOLD,fn_name)} {c(CO,args_prev)}")
                        obs = execute_tool(fn_name, fn_args)
                        lines   = obs.split('\n')
                        preview = '\n'.join(lines[:8])
                        if len(lines)>8:
                            preview += f"\n{c(CO,f'  ··· +{len(lines)-8} líneas')}"
                        print(c(GR,preview))
                        print(c(CO,f"  {'─'*48}"))
                    # Respuesta de tool en formato Ollama
                    messages.append({"role":"tool","content":obs,
                                     "tool_call_id": call_id, "name": fn_name})

            else:  # kind == "text" → respuesta final
                final_response = data.strip()
                _print_final(final_response, step)
                history_save(user_input, final_response)
                notify_response(final_response, steps=step)
                speak(final_response, blocking=False)
                return messages

        if final_response:
            return messages
        # Si salió del loop sin respuesta y sigue en modo nativo → warn
        if TOOL_CALL_STATE["native"]:
            print(c(YL,f"\n  ⚠ Límite {MAX_ITER} pasos alcanzado.\n"))
            return messages
        # Si degradó a ReAct, continúa abajo con los mensajes limpios

    # ── Fallback ReAct (texto plano) ──────────────────────────────────────────
    # Reconstruir mensajes sin tool_calls para modelos que no lo soportan
    clean_msgs = []
    for m in messages:
        if m.get("role") == "tool":
            clean_msgs.append({"role":"user","content":f"Observacion: {m['content']}"})
        elif m.get("role") == "assistant" and m.get("tool_calls"):
            clean_msgs.append({"role":"assistant","content": m.get("content","") or
                               "Accion: "+m["tool_calls"][0]["function"]["name"]})
        else:
            clean_msgs.append({k:v for k,v in m.items() if k in ("role","content")})

    for step in range(MAX_ITER):
        sp = spinner[step % len(spinner)]
        print(c(CO,f"  {sp} [ReAct] paso {step+1}/{MAX_ITER}"),end="\r",flush=True)
        try:
            raw = chat_react_text(clean_msgs)
        except Exception as ex:
            print(c(RE,f"\n  ✗ API error: {ex}"))
            return messages
        print(" "*55, end="\r")
        clean_msgs.append({"role":"assistant","content":raw})
        parsed = parse_react(raw)

        if parsed[0] == "action":
            _, fn_name, fn_args, thought = parsed
            if thought:
                print(f"  {c(CO,'💭')} {c(CO+ITALIC,thought[:100])}")
            if fn_name not in TOOL_MAP:
                obs = f"Error: '{fn_name}' no existe. Disponibles: {', '.join(TOOL_MAP.keys())}"
            else:
                args_prev = json.dumps(fn_args,ensure_ascii=False)[:60]
                print(f"  {c(PU,'▸')} {c(CY+BOLD,fn_name)} {c(CO,args_prev)}")
                obs = execute_tool(fn_name, fn_args)
                lines   = obs.split('\n')
                preview = '\n'.join(lines[:8])
                if len(lines)>8:
                    preview += f"\n{c(CO,f'  ··· +{len(lines)-8} líneas')}"
                print(c(GR,preview))
                print(c(CO,f"  {'─'*48}"))
            clean_msgs.append({"role":"user","content":f"Observacion: {obs}"})

        elif parsed[0] == "final":
            final_response = parsed[1]
            _print_final(final_response, step)
            history_save(user_input, final_response)
            notify_response(final_response, steps=step)
            speak(final_response, blocking=False)
            break

    if not final_response:
        print(c(YL,f"\n  ⚠ Límite {MAX_ITER} pasos alcanzado.\n"))
    return messages

# ══════════════════════════════════════════════════════════════════════════════
# SELECCIÓN DE MODO
# ══════════════════════════════════════════════════════════════════════════════
def get_local_models():
    try:
        req=urllib.request.Request(f"{OLLAMA_LOCAL}/api/tags")
        with urllib.request.urlopen(req,timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models",[])]
    except: return []

def get_cloud_models(api_key):
    try:
        req=urllib.request.Request(f"{OLLAMA_CLOUD}/api/tags",
            headers={"Authorization":f"Bearer {api_key}"})
        with urllib.request.urlopen(req,timeout=10) as r:
            return [m["name"] for m in json.loads(r.read()).get("models",[])]
    except: return []

def get_model_type(name):
    l=name.lower()
    if any(x in l for x in ["llava","vision","moondream"]): return "multimodal"
    if any(x in l for x in ["coder","code","deepseek","qwen3"]): return "codigo"
    return "general"

def type_badge(tipo):
    if tipo=="multimodal": return c(PK,  "[multimodal]")
    if tipo=="codigo":     return c(GR,  "[codigo]    ")
    return                        c(CY,  "[general]   ")

def find_preferred_model(models):
    for pref in PREFERRED_MODELS:
        for m in models:
            if pref.lower() in m.lower(): return m
    return None

def select_mode():
    os.system("clear")
    print(BANNER)
    print(f"  {c(GR+BOLD,'1.')} {c(GR,'Local')}  — Modelos en Android")
    print(f"  {c(CY+BOLD,'2.')} {c(CY,'Nube ')}  — Ollama Cloud + pool de API keys\n")
    while True:
        try: choice=input(c(PU+BOLD,"  ▸ Elige modo [1/2]: ")).strip()
        except (KeyboardInterrupt,EOFError): sys.exit(0)
        if choice=="1": return _setup_local()
        if choice=="2": return _setup_cloud()
        print(c(RE,"  Escribe 1 o 2"))

def _setup_local():
    models=get_local_models()
    if not models:
        print(c(RE,"\n  Ollama no corre o sin modelos.")); sys.exit(1)
    print(f"\n{c(CY+BOLD,'  Modelos locales:')}\n")
    for i,name in enumerate(models,1):
        print(f"  {c(PU+BOLD,str(i)+'.')} {type_badge(get_model_type(name))} {c(D_FG,name)}")
    print()
    while True:
        try:
            idx=int(input(c(PU+BOLD,"  ▸ Elige modelo [número]: ")).strip())-1
            if 0<=idx<len(models):
                STATE["model"]=models[idx]; STATE["use_cloud"]=False; STATE["api_keys"]=[]
                return
        except (ValueError,KeyboardInterrupt,EOFError): sys.exit(0)

def _setup_cloud():
    print(f"\n{c(CY+BOLD,'  Ollama Cloud — Pool de API Keys')}")
    print(c(CO,"  ~/AIION/data/ollama_keys (una por línea) | OLLAMA_API_KEY=[MASKED]"))
    keys=load_api_keys()
    if keys:
        print(c(GR,f"  {len(keys)} key(s) detectadas:"))
        for i,k in enumerate(keys,1): print(c(CO,f"    {i}. {k[:8]}..."))
        if input(c(PU+BOLD,"  ▸ Usar estas keys? [S/n]: ")).strip().lower() in("n","no"):
            keys=[]
    if not keys:
        try: raw=input(c(PU+BOLD,"  ▸ API Key(s) separadas por coma: ")).strip()
        except (KeyboardInterrupt,EOFError): sys.exit(0)
        keys=[k.strip() for k in raw.split(",") if k.strip()]
        if keys and input(c(CO,"  ▸ Guardar en ~/AIION/data/ollama_keys? [S/n]: ")).strip().lower() not in("n","no"):
            kf=AIION_HOME/"ollama_keys"; kf.write_text("\n".join(keys)); kf.chmod(0o600)
    if not keys: return _setup_local()
    STATE.update(api_keys=keys,key_index=0,use_cloud=True)
    print(c(CO,"  Verificando modelos..."))
    models=get_cloud_models(current_key())
    if not models:
        try: STATE["model"]=input(c(PU+BOLD,"  ▸ Nombre modelo: ")).strip() or "qwen3-coder:480b"
        except (KeyboardInterrupt,EOFError): sys.exit(0)
        return
    print(f"\n{c(CY+BOLD,'  Modelos disponibles:')}\n")
    for i,name in enumerate(models,1):
        print(f"  {c(PU+BOLD,str(i)+'.')} {type_badge(get_model_type(name))} {c(D_FG,name)}")
    auto=find_preferred_model(models)
    if auto:
        print(c(GR,f"\n  Modelo recomendado: {auto}"))
        if input(c(PU+BOLD,"  ▸ Usar automáticamente? [S/n]: ")).strip().lower() not in("n","no"):
            STATE["model"]=auto; return
    print()
    while True:
        try:
            idx=int(input(c(PU+BOLD,"  ▸ Elige modelo [número]: ")).strip())-1
            if 0<=idx<len(models): STATE["model"]=models[idx]; return
        except (ValueError,KeyboardInterrupt,EOFError): sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════════
# COMANDOS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════
def print_help():
    print(f"""
{c(PU+BOLD,'╔══ Comandos ═══════════════════════════════════════╗')}
{c(PU,'║')}  {c(CY,'/exit')}              Salir del agente
{c(PU,'║')}  {c(CY,'/clear')}             Limpiar historial de sesión
{c(PU,'║')}  {c(CY,'/model')}             Cambiar modelo
{c(PU,'║')}  {c(CY,'/tools')}             Ver todas las tools
{c(PU,'║')}  {c(CY,'/cd <path>')}         Cambiar directorio
{c(PU,'║')}  {c(CY,'/ram')}               Estado de RAM en detalle
{c(PU,'║')}  {c(CY,'/memory')}            Ver memoria persistente
{c(PU,'║')}  {c(CY,'/remember <dato>')}   Guardar dato en memoria
{c(PU,'║')}  {c(CY,'/history')}           Ver conversaciones pasadas
{c(PU,'║')}  {c(CY,'/index')}             Ver índice cognitivo
{c(PU,'║')}  {c(CY,'/sensors')}           Estado de sensores en tiempo real
{c(PU,'║')}  {c(CY,'/toolmode')}          Alternar nativo↔ReAct
{c(PU,'║')}  {c(CY,'/voice test')}        Probar voz
{c(PU,'║')}  {c(CY,'/voice set <voz>')}   Cambiar voz (Celeste/Valentina/Mateo)
{c(PU,'║')}  {c(CY,'/voice vol <0-100>')} Volumen
{c(PU,'║')}  {c(CY,'/voice speed <0.5-2>')} Velocidad
{c(PU,'╚═══════════════════════════════════════════════════╝')}
""")

def print_sensors_status():
    if not SENSOR_STATE["running"]:
        print(c(YL,"  Sensores no activos")); return
    print(f"\n{c(CY+BOLD,'╔══ Sensores en Tiempo Real ════════════════════════╗')}")
    for sensor in SENSOR_INTERVALS:
        d=sensor_last(sensor)
        if d:
            ts=d.get("ts","")[-8:]
            # Preview compacto
            preview=""
            if sensor=="battery":
                preview=f"{d.get('percentage','?')}% {d.get('status','')}"
            elif sensor=="wifi":
                preview=f"{d.get('ssid','?')} {d.get('rssi','?')}dBm"
            elif sensor=="system":
                preview=f"RAM {d.get('ram_used_pct','?')}% load:{d.get('load_1m','?')}"
            elif sensor=="location":
                preview=f"lat:{d.get('latitude','?')} lon:{d.get('longitude','?')}"
            else:
                preview=str(d)[:40]+"..."
            print(f"{c(PU,'║')}  {c(GR,'●')} {c(CY,f'{sensor:<18}')} {c(D_FG,f'{preview:<25}')} {c(CO,ts)}")
        else:
            print(f"{c(PU,'║')}  {c(CO,'○')} {c(CO,f'{sensor:<18}')} {c(CO,'sin datos aún')}")
    print(c(PU,'╚'+'═'*50))
    print()

def handle_voice_command(cmd):
    cmd=cmd.strip().lower()
    if cmd=="/voice on":
        VOICE_STATE["enabled"]=True
        print(c(GR,f"\n  🔊 Voz activada — {VOICE_STATE['voice']}"))
        speak("Hola, voz activada.",blocking=False); return True
    elif cmd=="/voice off":
        VOICE_STATE["enabled"]=False
        print(c(CO,"  🔇 Voz desactivada")); return True
    elif cmd=="/voice test":
        VOICE_STATE["enabled"]=True
        speak("Prueba de voz AIION funcionando correctamente.",blocking=True)
        return True
    elif cmd.startswith("/voice set "):
        voz=cmd[11:].strip()
        match=next((v for v in VOICES if voz.lower() in v.lower()),None)
        if match:
            VOICE_STATE["voice"]=match
            print(c(GR,f"  ✓ Voz: {match}")); speak(f"Voz {match.split('-')[0]}",blocking=False)
        else:
            print(c(YL,f"  Voces: {', '.join(VOICES)}")); return True
        return True
    elif cmd.startswith("/voice vol "):
        try: VOICE_STATE["volume"]=max(0,min(100,int(cmd[11:]))); print(c(GR,f"  Vol: {VOICE_STATE['volume']}%"))
        except: print(c(RE,"  Uso: /voice vol 0-100")); return True
    elif cmd.startswith("/voice speed "):
        try: VOICE_STATE["speed"]=max(0.5,min(2.0,float(cmd[13:]))); print(c(GR,f"  Speed: {VOICE_STATE['speed']}x"))
        except: print(c(RE,"  Uso: /voice speed 0.5-2.0")); return True
    elif cmd=="/voice":
        print(f"\n  {c(CY+BOLD,'Comandos de voz:')} /voice on|off|test|set <voz>|vol <n>|speed <n>")
        print(f"  Voces: {c(GR,', '.join(VOICES))}\n"); return True
    return False

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    select_mode()
    RAMGUARD.start()
    sensor_start()

    # Activar wake lock
    subprocess.Popen("termux-wake-lock 2>/dev/null",shell=True,
                     stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    os.system("clear")
    print(BANNER)
    modo=c(CY+BOLD,f"NUBE | {STATE['model']} ({len(STATE['api_keys'])} keys)") \
        if STATE["use_cloud"] else c(GR+BOLD,f"LOCAL | {STATE['model']}")
    print(f"  {c(CO,'Modo:')}    {modo}")
    print(f"  {c(CO,'Tipo:')}    {type_badge(get_model_type(STATE['model']))}")
    print(f"  {c(CO,'Dir:')}     {c(CO,os.getcwd())}")
    print(f"  {c(CO,'Sensores:')} {c(GR,'activos')} ({len(SENSOR_INTERVALS)} sensores)")
    print(f"  {c(CO,'Tools:')}   {c(PU,str(len(TOOL_MAP)))} disponibles")
    print(f"  {c(CO,'Ayuda:')}   /help\n")
    print(hr())

    history=[]
    prompt=f"{c(PU+BOLD,'aiion')} {c(CO,'›')} "

    while True:
        # Barra de estado compacta
        print(c(CO,f"  {status_bar()}"),flush=True)
        try:
            if VOICE_STATE.get("enabled"):
                print(c(PK+BOLD,prompt)+c(CO,"[Enter=hablar / escribe texto] "),end="",flush=True)
                user_input=input("").strip()
                if not user_input: user_input=listen()
            else:
                user_input=input(f"\n{prompt}").strip()
        except (KeyboardInterrupt,EOFError):
            print(c(CO,"\n\n  Hasta luego 👋"))
            RAMGUARD.stop(); sensor_stop()
            subprocess.Popen("termux-wake-unlock 2>/dev/null",shell=True,
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            sys.exit(0)

        if not user_input: continue

        # ── Comandos internos ─────────────────────────────────────────────
        if user_input=="/exit":
            print(c(CO,"  Hasta luego 👋"))
            RAMGUARD.stop(); sensor_stop(); sys.exit(0)

        elif user_input=="/help": print_help()

        elif user_input=="/clear":
            history=[]; os.system("clear"); print(BANNER)
            print(c(GR,"  ✓ Historial limpiado"))

        elif user_input=="/ram":
            print(f"\n{c(CY+BOLD,'╔══ RAM Guard ══════════════════════════════')}")
            print(f"{c(CY,'║')} {RAMGUARD.status()}")
            print(f"{c(CY,'║')} Tendencia: {c(YL,RAMGUARD.trend())}")
            print(c(CY,'╚'+'═'*43)+"\n")

        elif user_input=="/sensors": print_sensors_status()

        elif user_input=="/memory":
            mem=memory_load()
            print(f"\n{c(CY+BOLD,'📋 Memoria persistente:')}")
            print(c(D_FG,mem) if mem else c(CO,"  (vacía)")); print()

        elif user_input.startswith("/remember "):
            fact=user_input[10:].strip(); memory_append(fact)
            print(c(GR,f"  ✓ Guardado: {fact}"))

        elif user_input=="/memory clear":
            MEMORY_FILE.write_text(""); print(c(YL,"  Memoria borrada"))

        elif user_input=="/history":
            entries=history_load_all()
            print(f"\n{c(CY+BOLD,f'📚 Historial: {len(entries)} conversaciones')}")
            for e in entries[-5:]:
                print(f"  {c(CO,e.get('ts','')[:10])} {c(D_FG,e['user'][:70])}")
            print()

        elif user_input=="/index": print(COGINDEX.summary()); print()

        elif user_input=="/model":
            select_mode(); print(c(GR,f"  ✓ Modelo: {STATE['model']}"))

        elif user_input=="/tools":
            print(f"\n{c(CY+BOLD,'╔══ 28 Tools disponibles ═══════════════════')}")
            cats={"📁 Filesystem":["read_file","write_file","replace","run_shell_command","list_directory","glob","grep_search"],
                  "🌐 Web":["web_fetch"],
                  "🧠 Memoria":["diff_files","memory_search"],
                  "⚙️ Procesos":["process_manager"],
                  "📱 Android":["get_android_status","sensor_query","take_photo","listar_camaras","get_gps"],
                  "🔔 Notif":["notificacion","cancelar_notificacion"],
                  "📞 Comun":["leer_sms","enviar_sms","historial_llamadas","hacer_llamada","info_telefonia"],
                  "🔊 Voz":["hablar","listar_voces"],
                  "⏰ Tareas":["crear_tarea","listar_tareas","eliminar_tarea"]}
            for cat,tools in cats.items():
                print(f"{c(PU,'║')} {c(YL+BOLD,cat)}")
                for t in tools:
                    danger=c(RE," [permiso]") if t in DANGEROUS_TOOLS else ""
                    print(f"{c(PU,'║')}   {c(GR,'▸')} {c(CY,t)}{danger}")
            print(c(PU,'╚'+'═'*43)+"\n")

        elif user_input.startswith("/cd "):
            path=user_input[4:].strip()
            try: os.chdir(os.path.expanduser(path)); print(c(GR,f"  ✓ {os.getcwd()}"))
            except Exception as ex: print(c(RE,f"  ✗ {ex}"))

        elif user_input=="/toolmode":
            TOOL_CALL_STATE["native"] = not TOOL_CALL_STATE["native"]
            modo = c(GR,"nativo ✓") if TOOL_CALL_STATE["native"] else c(YL,"ReAct (texto)")
            print(f"  Modo tools: {modo}")

        elif handle_voice_command(user_input): pass

        else:
            print()
            history=run_agent(user_input,history[-20:])

if __name__=="__main__":
    main()
