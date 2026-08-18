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


AGENT_REGISTRY_EXTRA = [
    # Agentes adicionales solicitados por Estiven
    {
        "name": "github",
        "description": "Operador Git — commits, push, PR, status",
        "capabilities": ["status", "commit", "push", "log", "branch", "diff"],
    },
    {
        "name": "drive",
        "description": "Operador Google Drive — listar, descargar, subir, sincronizar",
        "capabilities": ["list", "pull", "push", "sync", "tree"],
    },
    {
        "name": "sara",
        "description": "Enlace AIION ↔ Sara OS (WebSocket :7773, MCP HTTP)",
        "capabilities": ["ping", "send", "status", "history"],
    },
]


def install_extra_agents(orch):
    """Registra agentes extra (github, drive, sara) al orquestador."""
    from aiion.orchestrator import AgentSpec

    def gh_handler(action, args):
        from aiion.tools.git_ops import run_git
        return run_git(action, args)

    def drive_handler(action, args):
        from aiion.tools.drive_ops import run_drive
        return run_drive(action, args)

    def sara_handler(action, args):
        from aiion.tools.sara_ops import run_sara
        return run_sara(action, args)

    for spec_data in AGENT_REGISTRY_EXTRA:
        name = spec_data["name"]
        if name in orch.registry:
            continue
        handler = {
            "github": gh_handler,
            "drive": drive_handler,
            "sara": sara_handler,
        }[name]
        orch.register(AgentSpec(
            name=name,
            description=spec_data["description"],
            capabilities=spec_data["capabilities"],
            handler=handler,
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

    print(f"[daemon] Agentes activos: {orch.list_agents()}")
    print(f"[daemon] Iniciando ciclo autónomo cada {args.interval}s")
    orch.audit.record("daemon.start", interval=args.interval)

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n[daemon] ─── Ciclo #{cycle} ──────────────────────────────")
            # 1) Doctor — salud del sistema
            t = orch.submit("core", "doctor")
            print(f"  core.doctor → {t.status.value} ({t.duration_ms}ms)")
            # 2) Estado de Sara
            t = orch.submit("blist_bridge", "health")
            print(f"  blist_bridge.health → {t.status.value} ({t.duration_ms}ms)")
            # 3) Git status
            t = orch.submit("github", "status")
            print(f"  github.status → {t.status.value} ({t.duration_ms}ms)")
            # 4) Drive list
            t = orch.submit("drive", "list", {"path": "/"})
            print(f"  drive.list → {t.status.value} ({t.duration_ms}ms)")

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
