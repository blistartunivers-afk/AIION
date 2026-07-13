"""aiion/tools/android.py — Tools de dispositivo Android: sensores, cámara, GPS, notificaciones, tareas."""
import json, subprocess
from pathlib import Path
from datetime import datetime
from aiion.sensors.daemon import sensor_last, sensor_query
from aiion.sensors.collectors import SENSOR_INTERVALS, _termux, _sh

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
