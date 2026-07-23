"""
aiion/subagentes/__main__.py — CLI unificado para subagentes.

Uso:
  python -m aiion.subagentes list
  python -m aiion.subagentes describe <name>
  python -m aiion.subagentes call <name> <capability> [json_args]

El módulo orchestrator_bridge auto-registra los 5 builtins al importarse.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Disparar auto-registro
from aiion.subagentes import orchestrator_bridge  # noqa: F401
from aiion.subagentes.base import (
    REGISTRY,
    list_subagentes,
    get_subagente,
    SubagenteError,
)


def _print(obj, indent: int = 0) -> None:
    print(json.dumps(obj, indent=indent + 2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "list":
        print(f"📦 {len(REGISTRY)} subagente(s) registrado(s):\n")
        for s in list_subagentes():
            caps = ", ".join(s.capabilities)
            print(f"  • {s.name:18s} v{s.version}  —  {s.description}")
            print(f"    caps: {caps}\n")
        return 0

    if cmd == "describe":
        if not rest:
            print("✗ Falta nombre de subagente")
            return 2
        try:
            _print(get_subagente(rest[0]).describe())
            return 0
        except SubagenteError as e:
            print(f"✗ {e}")
            return 1

    if cmd == "call":
        if len(rest) < 2:
            print("✗ Uso: call <name> <capability> [json_args]")
            return 2
        name = rest[0]
        capability = rest[1]
        try:
            args = json.loads(rest[2]) if len(rest) >= 3 else {}
        except json.JSONDecodeError as e:
            print(f"✗ Args inválidos: {e}")
            return 2
        try:
            sub = get_subagente(name)
        except SubagenteError as e:
            print(f"✗ {e}")
            return 1
        result = sub.dispatch(capability, args)
        _print(result, indent=0)
        return 0 if result.get("ok") else 1

    print(f"✗ Comando '{cmd}' no reconocido. Usa: list | describe | call")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
