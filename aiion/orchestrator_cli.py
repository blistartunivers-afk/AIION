"""
aiion/orchestrator_cli.py — CLI del orquestador AIION.

Uso:
  python -m aiion.orchestrator_cli agents                 # lista agentes
  python -m aiion.orchestrator_cli submit <agent> <action> [json_args]
  python -m aiion.orchestrator_cli plan <json_file>       # ejecuta plan
  python -m aiion.orchestrator_cli stats                  # métricas
  python -m aiion.orchestrator_cli audit [N]              # últimos N eventos
"""
import sys
import json
from pathlib import Path

from aiion.orchestrator import get_orchestrator
from aiion.cli.ui import c, CY, GR, YL, RE, CO, BOLD


def _print_banner(title: str):
    print(c(CY + BOLD, f"\n  🎼 ORQUESTADOR AIION — {title}"))
    print(c(CO, "  " + "─" * 56))


def cmd_agents(_args):
    _print_banner("AGENTES REGISTRADOS")
    orch = get_orchestrator()
    for name in orch.list_agents():
        spec = orch.describe(name)
        caps = ", ".join(spec.capabilities[:5])
        if len(spec.capabilities) > 5:
            caps += f" … (+{len(spec.capabilities) - 5})"
        print(c(GR, f"  ✓ {name:14s} ") + c(CO, f"— {spec.description}"))
        print(c(CO, f"      capabilities: {caps}"))


def cmd_submit(args):
    if len(args) < 2:
        print(c(RE, "  ✗ Uso: submit <agent> <action> [json_args]"))
        return 1
    agent, action = args[0], args[1]
    params = {}
    if len(args) >= 3:
        try:
            params = json.loads(" ".join(args[2:]))
        except json.JSONDecodeError as e:
            print(c(RE, f"  ✗ JSON inválido: {e}"))
            return 1
    _print_banner(f"EJECUTANDO  {agent}.{action}")
    t = get_orchestrator().submit(agent, action, params)
    color = GR if t.status.value == "success" else RE
    print(c(color, f"  • status:   {t.status.value}"))
    print(c(CO,    f"  • task_id:  {t.id}"))
    if t.duration_ms is not None:
        print(c(CO,  f"  • latency:  {t.duration_ms} ms"))
    if t.error:
        print(c(RE,  f"  • error:    {t.error}"))
    if t.result is not None and not isinstance(t.result, dict):
        print(c(CO,  f"  • result:   {t.result}"))
    return 0 if t.status.value == "success" else 1


def cmd_plan(args):
    if not args:
        print(c(RE, "  ✗ Uso: plan <json_file>"))
        return 1
    path = Path(args[0])
    if not path.exists():
        print(c(RE, f"  ✗ No existe: {path}"))
        return 1
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(c(RE, f"  ✗ JSON inválido: {e}"))
        return 1
    _print_banner(f"EJECUTANDO PLAN ({len(plan)} pasos)")
    results = get_orchestrator().execute_plan(plan)
    ok = sum(1 for t in results if t.status.value == "success")
    color = GR if ok == len(results) else YL
    print(c(color, f"\n  ▸ {ok}/{len(results)} tareas exitosas"))


def cmd_stats(_args):
    _print_banner("MÉTRICAS")
    s = get_orchestrator().stats()
    print(c(GR, f"  • total:         {s['total']}"))
    print(c(CY, f"  • success_rate:  {s.get('success_rate', '—')}%"))
    if s.get("avg_latency_ms") is not None:
        print(c(CY, f"  • avg_latency:   {s['avg_latency_ms']} ms"))
    print(c(CO, "  • by_status:"))
    for k, v in (s.get("by_status") or {}).items():
        print(c(CO, f"      {k:8s} = {v}"))
    print(c(CO, "  • by_agent:"))
    for k, v in (s.get("by_agent") or {}).items():
        print(c(CO, f"      {k:14s} = {v}"))


def cmd_audit(args):
    n = int(args[0]) if args else 10
    _print_banner(f"ÚLTIMOS {n} EVENTOS")
    log = get_orchestrator().audit.tail(n)
    for e in log:
        ts = e.get("ts", 0)
        event = e.get("event", "?")
        extras = " ".join(f"{k}={v}" for k, v in e.items()
                          if k not in ("ts", "event") and isinstance(v, (str, int, float, bool)))
        print(c(CO, f"  {ts:.2f}  ") + c(CY, f"{event:20s} ") + c(GR, extras))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, *rest = sys.argv[1:]
    cmds = {
        "agents": cmd_agents,
        "submit": cmd_submit,
        "plan":   cmd_plan,
        "stats":  cmd_stats,
        "audit":  cmd_audit,
    }
    handler = cmds.get(cmd)
    if handler is None:
        print(c(RE, f"  ✗ Comando '{cmd}' no existe. Opciones: {', '.join(cmds)}"))
        return 1
    try:
        return handler(rest)
    except KeyboardInterrupt:
        print(c(YL, "\n  Interrumpido"))
        return 130
    except Exception as e:
        print(c(RE, f"\n  ✗ Error: {e}"))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
