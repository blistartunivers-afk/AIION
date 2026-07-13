"""aiion/core.py — Orquestador: system prompt, loop del agente, comandos internos y main()."""
import json, os, re, subprocess, sys, shutil, urllib.request
from pathlib import Path
from datetime import datetime

from aiion.config import AIION_HOME, MAX_ITER, VERSION, OLLAMA_LOCAL, OLLAMA_CLOUD, PREFERRED_MODELS
from aiion.cli.ui import (
    c, hr, badge, BANNER, R, BOLD, DIM, ITALIC,
    CY, GR, YL, OR, RE, PK, PU, CO, D_FG,
)
from aiion.memory.ram_guard import RAMGUARD
from aiion.memory.cognitive_index import COGINDEX
from aiion.memory.persistence import (
    memory_load, memory_append, history_save, history_load_all,
    history_summary_for_prompt, MEMORY_FILE,
)
from aiion.sensors.daemon import sensor_start, sensor_stop, sensor_last
from aiion.sensors.collectors import SENSOR_STATE, SENSOR_INTERVALS
from aiion.voice.tts import speak, VOICE_STATE
from aiion.voice.stt import listen
from aiion.config import VOICES
from aiion.llm.keys import STATE, load_api_keys, current_key
from aiion.llm.client import chat_native, chat_react_text, parse_react, TOOL_CALL_STATE
from aiion.tools.registry import TOOLS, TOOL_MAP, DANGEROUS_TOOLS, execute_tool, ask_permission

def status_bar():
    """Barra de estado en vivo: RAM | Sensores | Voz | Modelo"""
    ram  = RAMGUARD.stats_str()
    sens = f"{c(GR,'●')} Sensores" if SENSOR_STATE.get("running") else f"{c(CO,'○')} Sensores"
    voz  = f"{c(PK,'🔊')} Voz" if VOICE_STATE.get("enabled") else f"{c(CO,'🔇')} Voz"
    mdl  = c(CY, STATE.get("model","")[:20]) if STATE.get("model") else c(CO,"sin modelo")
    ts   = c(CO, datetime.now().strftime("%H:%M:%S"))
    return f"{ram}  {sens}  {voz}  {mdl}  {ts}"

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

