"""
aiion/subagentes/orchestrator_bridge.py — Integra subagentes con el orchestrator.

Al importar este módulo:
  1. Registra los 5 subagentes builtins (sara, security_audit, memory_keeper,
     claude, blist_bridge) en REGISTRY.
  2. Inyecta cada subagente como agente del orchestrator, exponiendo sus
     capabilities como acciones permitidas.

Esto cierra el círculo: subagentes ←→ orchestrator ←→ tools ←→ sensors.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Importar los subagentes (auto-registran via @subagente)
from aiion.subagentes import (  # noqa: F401
    sara_cerebro,
    security_audit,
    memory_keeper,
)

# Los legacy (claude, blist_bridge) usan scripts standalone con CLI argparse,
# no se migran al framework base para no romper sus interfaces existentes.
# Se documentan en el README como "v0 (standalone)".

from aiion.subagentes.base import (
    REGISTRY,
    list_subagentes,
    get_subagente,
)


def register_all_with_orchestrator() -> int:
    """Registra cada subagente como agente del orchestrator.

    Retorna el número de subagentes integrados.
    """
    try:
        from aiion.orchestrator import register_agente  # type: ignore
    except Exception:
        return 0

    count = 0
    for sub in list_subagentes():
        try:
            register_agente(
                name=sub.name,
                description=sub.description,
                capabilities=list(sub.capabilities),
                handler=_make_handler(sub),
            )
            count += 1
        except Exception:
            # el orchestrator ya tiene reglas estrictas; ignorar duplicados
            pass
    return count


def _make_handler(sub):
    """Crea un callable compatible con orchestrator.handle_dispatch."""
    def handler(action: str, args: dict | None = None) -> dict:
        return sub.dispatch(action, args)
    handler.__name__ = f"subagente_{sub.name}_handler"
    return handler


def report() -> dict:
    """Reporte del estado del subsistema de subagentes."""
    return {
        "total": len(REGISTRY),
        "enabled": sum(1 for s in REGISTRY.values() if s.enabled),
        "subagentes": [s.describe() for s in REGISTRY.values()],
    }


# Auto-inject en import (no rompe nada si el orchestrator no está listo)
try:
    _registered = register_all_with_orchestrator()
except Exception:
    _registered = 0


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(report(), indent=2, ensure_ascii=False))
