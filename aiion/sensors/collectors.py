"""aiion/sensors/collectors.py — Recolectores individuales vía termux-api + almacenamiento SQLite."""
import json, subprocess, sqlite3, threading
from datetime import datetime
from aiion.config import SENSOR_DB

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


SENSOR_SAMPLERS = {
    "battery":_s_battery,"wifi":_s_wifi,"system":_s_system,
    "sensors":_s_sensors,"location":_s_location,"cellinfo":_s_cellinfo,
    "telephony":_s_telephony,"volume":_s_volume,"brightness":_s_brightness,
    "clipboard":_s_clipboard,"camera_info":_s_camera_info,
    "audio":_s_audio,"nfc":_s_nfc,
}
