"""aiion/tools/communication.py — Tools de comunicación: SMS, llamadas, voz."""
import json, subprocess
from aiion.sensors.collectors import _termux
from aiion.voice.tts import speak, VOICE_STATE
from aiion.config import VOICES, GROQ_TTS_MODEL

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

