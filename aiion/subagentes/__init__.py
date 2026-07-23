"""
aiion/subagentes/__init__.py — Paquete de sub-agentes AIION.

Estructura:
  - base.py            → clase Subagente + decorator + REGISTRY
  - sara_cerebro.py    → subagente SARA (sensores+voz+notif)
  - security_audit.py  → subagente seguridad (audit+risk+memory)
  - memory_keeper.py   → subagente memoria (stats+top+export+snapshot)
  - claude.py          → legacy CLI standalone (planificador)
  - blist_bridge.py    → legacy CLI standalone (MCP a blistv11)
  - orchestrator_bridge.py → integración con aiion.orchestrator
  - __main__.py        → CLI unificado: python -m aiion.subagentes
"""
from aiion.subagentes import (  # noqa: F401
    sara_cerebro,
    security_audit,
    memory_keeper,
)
# Nota: claude.py y blist_bridge.py son CLIs legacy con argparse.
# Se mantienen para retrocompatibilidad; los nuevos subagentes usan base.Subagente.
