#!/usr/bin/env python3
"""
AIION Orchestrator Daemon — Modo Autónomo Total
Corre continuamente, ejecuta tareas delegadas por Estiven/Sara y reporta estado.

Uso: python orchestrator_daemon.py [--interval 60]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

AIION_HOME = Path(os.environ.get("AIION_HOME", "/data/data/com.termux/files/home/AIION"))
sys.path.insert(0, str(AIION_HOME))

from aiion.orchestrator import get_orchestrator, TaskStatus
from aiion.sensors.daemon import sensor_start, SENSOR_STATE as _SENSOR_STATE  # FIX #1: iniciar sensor daemon


AGENT_REGISTRY_EXTRA = [
    # ── Git ──────────────────────────────────────────────────────────────────
    {
        "name": "github",
        "description": "Operador Git — commits, push, PR, status",
        "capabilities": ["status", "commit", "push", "log", "branch", "diff"],
    },
    # ── Drive ─────────────────────────────────────────────────────────────────
    {
        "name": "drive",
        "description": "Operador Google Drive — listar, descargar, subir, sincronizar",
        "capabilities": ["list", "pull", "push", "sync", "tree"],
    },
    # ── Sara OS bridge ────────────────────────────────────────────────────────
    {
        "name": "sara",
        "description": "Enlace AIION ↔ Sara OS (WebSocket :7773, MCP HTTP)",
        "capabilities": ["ping", "send", "status", "history"],
    },
    # ── Android / dispositivo ─────────────────────────────────────────────────
    {
        "name": "android",
        "description": "Dispositivo Android — sensores, cámara, GPS, notificaciones, tareas",
        "capabilities": [
            "status", "sensors", "photo", "cameras", "gps",
            "notify", "cancel_notify", "schedule", "list_tasks", "kill_task",
        ],
    },
    # ── Comunicación (SMS/llamadas/voz) ───────────────────────────────────────
    {
        "name": "communication",
        "description": "Comunicación — SMS, llamadas, TTS, info telefónica",
        "capabilities": ["sms_read", "sms_send", "calls", "call", "phone_info", "tts", "voices"],
    },
    # ── Filesystem / shell / búsqueda ─────────────────────────────────────────
    {
        "name": "filesystem",
        "description": "Sistema de archivos — leer, escribir, shell, grep, glob, fetch web",
        "capabilities": ["read", "write", "replace", "shell", "ls", "grep", "glob", "fetch", "diff", "process"],
    },
]


def install_extra_agents(orch):
    """Registra agentes extra (github, drive, sara, android, communication, filesystem) al orquestador."""
    from aiion.orchestrator import AgentSpec

    # ── Handlers ──────────────────────────────────────────────────────────────
    def gh_handler(action, args):
        from aiion.tools.git_ops import run_git
        return run_git(action, args)

    def drive_handler(action, args):
        from aiion.tools.drive_ops import run_drive
        return run_drive(action, args)

    def sara_handler(action, args):
        from aiion.tools.sara_ops import run_sara
        return run_sara(action, args)

    def android_handler(action, args):
        """Mapea acciones del agente → tools reales."""
        from aiion.tools.android import (
            tool_get_android_status, tool_sensor_query, tool_take_photo,
            tool_listar_camaras, tool_get_gps, tool_notificacion,
            tool_cancelar_notificacion, tool_crear_tarea, tool_listar_tareas,
            tool_eliminar_tarea,
        )
        MAP = {
            "status":       lambda a: tool_get_android_status(a.get("detail","all")),
            "sensors":      lambda a: tool_sensor_query(a.get("sensor","battery"), a.get("minutes",60), a.get("limit",50)),
            "photo":        lambda a: tool_take_photo(a.get("camera_id",0), a.get("filename","")),
            "cameras":      lambda a: tool_listar_camaras(),
            "gps":          lambda a: tool_get_gps(a.get("provider","network")),
            "notify":       lambda a: tool_notificacion(a["title"], a["content"], a.get("id",1234)),
            "cancel_notify":lambda a: tool_cancelar_notificacion(a["id"]),
            "schedule":     lambda a: tool_crear_tarea(a["comando"], a["cuando"], a.get("nombre","tarea_aiion")),
            "list_tasks":   lambda a: tool_listar_tareas(),
            "kill_task":    lambda a: tool_eliminar_tarea(a["id"]),
        }
        fn = MAP.get(action)
        if not fn: return f"android: acción desconocida '{action}'. Válidas: {list(MAP.keys())}"
        try: return fn(args or {})
        except Exception as ex: return f"android.{action} error: {ex}"

    def communication_handler(action, args):
        """Mapea acciones comunicación → SMS/llamadas/TTS."""
        from aiion.tools.communication import (
            tool_leer_sms, tool_enviar_sms, tool_historial_llamadas,
            tool_hacer_llamada, tool_info_telefonia, tool_hablar, tool_listar_voces,
        )
        MAP = {
            "sms_read":    lambda a: tool_leer_sms(a.get("limit",5), a.get("type","all")),
            "sms_send":    lambda a: tool_enviar_sms(a["number"], a["message"]),
            "calls":       lambda a: tool_historial_llamadas(a.get("limit",10)),
            "call":        lambda a: tool_hacer_llamada(a["number"]),
            "phone_info":  lambda a: tool_info_telefonia(),
            "tts":         lambda a: tool_hablar(a["texto"], a.get("voz")),
            "voices":      lambda a: tool_listar_voces(),
        }
        fn = MAP.get(action)
        if not fn: return f"communication: acción desconocida '{action}'. Válidas: {list(MAP.keys())}"
        try: return fn(args or {})
        except Exception as ex: return f"communication.{action} error: {ex}"

    def filesystem_handler(action, args):
        """Mapea acciones filesystem → read/write/shell/etc."""
        from aiion.tools.filesystem import (
            tool_read_file, tool_write_file, tool_replace, tool_run_shell_command,
            tool_list_directory, tool_glob, tool_grep_search, tool_web_fetch, tool_diff_files,
        )
        from aiion.tools.registry import tool_process_manager
        MAP = {
            "read":    lambda a: tool_read_file(a["path"], a.get("start_line"), a.get("end_line")),
            "write":   lambda a: tool_write_file(a["path"], a["content"]),
            "replace": lambda a: tool_replace(a["path"], a["old_str"], a["new_str"]),
            "shell":   lambda a: tool_run_shell_command(a["command"], a.get("timeout",30)),
            "ls":      lambda a: tool_list_directory(a["path"], a.get("show_hidden",False)),
            "grep":    lambda a: tool_grep_search(a["pattern"], a["path"], a.get("recursive",True)),
            "glob":    lambda a: tool_glob(a["pattern"], a.get("base_path")),
            "fetch":   lambda a: tool_web_fetch(a["url"], a.get("max_chars",5000)),
            "diff":    lambda a: tool_diff_files(a["path_a"], a.get("path_b"), a.get("context_lines",3)),
            "process": lambda a: tool_process_manager(a["action"], a.get("target",""), a.get("signal","TERM")),
        }
        fn = MAP.get(action)
        if not fn: return f"filesystem: acción desconocida '{action}'. Válidas: {list(MAP.keys())}"
        try: return fn(args or {})
        except Exception as ex: return f"filesystem.{action} error: {ex}"

    HANDLERS = {
        "github": gh_handler,
        "drive": drive_handler,
        "sara": sara_handler,
        "android": android_handler,
        "communication": communication_handler,
        "filesystem": filesystem_handler,
    }

    for spec_data in AGENT_REGISTRY_EXTRA:
        name = spec_data["name"]
        if name in orch.registry:
            continue
        orch.register(AgentSpec(
            name=name,
            description=spec_data["description"],
            capabilities=spec_data["capabilities"],
            handler=HANDLERS[name],
        ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60,
                        help="Intervalo entre ciclos del daemon (s)")
    parser.add_argument("--once", action="store_true",
                        help="Ejecuta una sola iteración y sale")
    args = parser.parse_args()

    print(f"[daemon] AIION_HOME = {AIION_HOME}")
    orch = get_orchestrator()
    install_extra_agents(orch)

    # FIX #1: arrancar sensor daemon para que android.status sea instantáneo (<50ms)
    if not _SENSOR_STATE.get("running"):
        sensor_start()
        print(f"[daemon] Sensor daemon arrancado (hilo en background)")

    print(f"[daemon] Agentes activos ({len(orch.list_agents())}): {orch.list_agents()}")
    print(f"[daemon] Iniciando ciclo autónomo cada {args.interval}s")
    orch.audit.record("daemon.start", interval=args.interval, agents=orch.list_agents())

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n[daemon] ─── Ciclo #{cycle} ──────────────────────────────")
            # 1) Doctor — salud del sistema
            t = orch.submit("core", "doctor")
            print(f"  core.doctor           → {t.status.value} ({t.duration_ms}ms)")
            # 2) Estado de Sara
            t = orch.submit("blist_bridge", "health")
            print(f"  blist_bridge.health   → {t.status.value} ({t.duration_ms}ms)")
            # 3) Git status
            t = orch.submit("github", "status")
            print(f"  github.status         → {t.status.value} ({t.duration_ms}ms)")
            # 4) Drive list
            t = orch.submit("drive", "list", {"path": "/"})
            print(f"  drive.list            → {t.status.value} ({t.duration_ms}ms)")
            # 5) Android status — FIX #3: solo sensores rápidos (sin location=5s)
            t = orch.submit("android", "status", {"detail": "battery"})
            print(f"  android.status        → {t.status.value} ({t.duration_ms}ms)")
            # 6) Filesystem ls home (NUEVO)
            t = orch.submit("filesystem", "ls", {"path": str(AIION_HOME)})
            print(f"  filesystem.ls         → {t.status.value} ({t.duration_ms}ms)")

            orch.audit.record("daemon.cycle", n=cycle,
                              stats=orch.stats())

            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[daemon] Detenido por usuario.")
    finally:
        orch.audit.record("daemon.stop")


if __name__ == "__main__":
    main()