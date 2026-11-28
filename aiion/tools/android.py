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
        r=subprocess.run(["termux-camera-photo", "-c", str(int(camera_id)), fn],
                         shell=False,capture_output=True,text=True,timeout=15)
        if r.returncode==0 and Path(fn).exists():
            size=Path(fn).stat().st_size
            return f"OK: Foto guardada en {fn} ({size} bytes)"
        return f"Error: {r.stderr.strip() or 'cámara no disponible'}"
    except Exception as ex: return f"Error: {ex}"

def tool_listar_camaras():
    d=_termux("termux-camera-info")
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: termux-api no disponible"

def tool_get_gps(provider="network"):
    d=_termux(["termux-location", "-p", str(provider)],timeout=20)
    if not d and provider!="network": d=_termux("termux-location -p network",timeout=15)
    return json.dumps(d,indent=2,ensure_ascii=False) if d else "Error: no se pudo obtener ubicación"

def tool_notificacion(title, content, id=1234):
    r=subprocess.run(["termux-notification", "--title", str(title), "--content", str(content), "--id", str(int(id))],
                     shell=False,capture_output=True,text=True,timeout=8)
    return "OK: Notificación enviada" if r.returncode==0 else f"Error: {r.stderr.strip()}"

def tool_cancelar_notificacion(id):
    r=subprocess.run(["termux-notification-remove", str(int(id))],shell=False,capture_output=True,text=True,timeout=5)
    return f"OK: Notificación {id} cancelada" if r.returncode==0 else f"Error: {r.stderr.strip()}"


def tool_crear_tarea(comando, cuando, nombre="tarea_aiion"):
    try:
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 128 or any(c in nombre for c in "\r\n\0"):
            return "Error: nombre de tarea inválido"
        if any(c in str(cuando) for c in "\r\n\0"):
            return "Error: el horario debe ser una sola línea"
        # Intentar con at
        r=subprocess.run(["at", "--", str(cuando)],
                         input=str(comando)+"\n",capture_output=True,text=True,timeout=10)
        if r.returncode==0: return f"OK: Tarea programada para '{cuando}'"
        # Fallback crontab
        if "\n" in str(comando): return "Error: tareas multilínea requieren at"
        r2=subprocess.run(["crontab", "-l"],shell=False,capture_output=True,text=True,timeout=5)
        existing=r2.stdout.strip()
        new_line=f"# {nombre}\n{cuando} {comando}"
        new_cron=existing+"\n"+new_line if existing else new_line
        r3=subprocess.run(["crontab", "-"],shell=False,input=new_cron,capture_output=True,text=True,timeout=5)
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
    task_id = str(id)
    if not task_id or len(task_id) > 128 or any(c in task_id for c in "\r\n\0"):
        return "Error: ID o nombre inválido"
    if task_id.isdigit():
        r=subprocess.run(["atrm", task_id],capture_output=True,text=True,timeout=5)
        return "OK: Tarea eliminada" if r.returncode==0 else f"Error: {r.stderr.strip()}"
    r=subprocess.run(["crontab", "-l"],capture_output=True,text=True,timeout=5)
    if r.returncode != 0: return f"Error leyendo crontab: {r.stderr.strip()}"
    lines=r.stdout.splitlines()
    marker="# " + task_id
    positions=[i for i,line in enumerate(lines) if line == marker]
    if len(positions) != 1: return "Error: se requiere un único nombre exacto de tarea"
    index=positions[0]
    if index+1 >= len(lines) or not lines[index+1].strip() or lines[index+1].lstrip().startswith("#"):
        return "Error: el marcador no identifica una tarea programada"
    updated="\n".join(lines[:index]+lines[index+2:])+"\n"
    result=subprocess.run(["crontab", "-"],input=updated,capture_output=True,text=True,timeout=5)
    return "OK: Tarea eliminada" if result.returncode==0 else f"Error: {result.stderr.strip()}"
