"""aiion/tools/registry.py — Definición JSON de las 28 tools, dispatch table y sistema de permisos."""
import json, os, subprocess, inspect
from aiion.config import DANGEROUS_TOOLS
from aiion.cli.ui import c, YL, PK, CO, GR, RE, BOLD, PU, CY
from aiion.memory.persistence import history_search
from aiion.tools.filesystem import (
    tool_read_file, tool_write_file, tool_replace, tool_run_shell_command,
    tool_list_directory, tool_glob, tool_grep_search, tool_web_fetch, tool_diff_files,
)
from aiion.tools.android import (
    tool_get_android_status, tool_sensor_query, tool_take_photo, tool_listar_camaras,
    tool_get_gps, tool_notificacion, tool_cancelar_notificacion,
    tool_crear_tarea, tool_listar_tareas, tool_eliminar_tarea,
)
from aiion.tools.communication import (
    tool_leer_sms, tool_enviar_sms, tool_historial_llamadas, tool_hacer_llamada,
    tool_info_telefonia, tool_hablar, tool_listar_voces,
)

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
