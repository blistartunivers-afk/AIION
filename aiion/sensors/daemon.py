"""aiion/sensors/daemon.py — Hilo de fondo que recolecta sensores en intervalos."""
import json, time, threading
from aiion.sensors.collectors import (
    SENSOR_STATE, SENSOR_STOP, SENSOR_INTERVALS, SENSOR_SAMPLERS,
    _sensor_db, _sensor_save,
)

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

