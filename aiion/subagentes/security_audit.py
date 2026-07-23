"""
aiion/subagentes/security_audit.py — Subagente de seguridad y auditoría.

Analiza el sistema en busca de problemas de seguridad:
  - Lista tools habilitadas y sus capabilities
  - Detecta tools peligrosas (run_shell_command, sms, llamadas, etc)
  - Revisa el audit log reciente
  - Verifica cifrado de memoria
  - Recomienda acciones

Capabilities:
  - audit_tail      → últimos N eventos del audit
  - audit_summary   → resumen de eventos por status
  - tools_inventory → lista de tools con flags de seguridad
  - risk_scan       → identifica tools de alto riesgo
  - memory_check    → verifica cifrado de memoria
  - recommendations → genera plan de remediación
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import sys

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiion.subagentes.base import Subagente, subagente

# Tools consideradas de ALTO RIESGO (por defecto bloqueadas en blist_bridge)
HIGH_RISK_TOOLS = {
    "run_shell_command", "tool_run_shell_command",
    "process_manager", "tool_process_manager",
    "enviar_sms", "tool_enviar_sms",
    "hacer_llamada", "tool_hacer_llamada",
    "delete_file", "tool_delete_file",
    "rm_tree", "tool_rm_tree",
}

# Tools de RIESGO MEDIO
MEDIUM_RISK_TOOLS = {
    "write_file", "tool_write_file",
    "replace", "tool_replace",
    "create_tarea", "tool_crear_tarea",
}


@subagente
class SecurityAudit(Subagente):
    name = "security_audit"
    description = "Auditor de seguridad: tools, capabilities, audit log, cifrado"
    version = "0.1"
    capabilities = [
        "audit_tail",
        "audit_summary",
        "tools_inventory",
        "risk_scan",
        "memory_check",
        "recommendations",
    ]

    def handle(self, capability: str, args: dict) -> dict:
        if capability == "audit_tail":
            return self._audit_tail(int(args.get("n", 20)))
        if capability == "audit_summary":
            return self._audit_summary()
        if capability == "tools_inventory":
            return self._tools_inventory()
        if capability == "risk_scan":
            return self._risk_scan()
        if capability == "memory_check":
            return self._memory_check()
        if capability == "recommendations":
            return self._recommendations()
        raise ValueError(f"capability '{capability}' no implementada")

    # --------- implementations ---------
    def _audit_tail(self, n: int) -> dict:
        """Lee últimos N eventos del audit log del orchestrator."""
        try:
            from aiion.orchestrator import audit_tail  # type: ignore
            events = audit_tail(n)
            return {"count": len(events), "events": events}
        except Exception as e:
            return {"count": 0, "events": [], "error": str(e)}

    def _audit_summary(self) -> dict:
        try:
            from aiion.orchestrator import audit_summary as _summary  # type: ignore
            return _summary()
        except Exception as e:
            return {"error": str(e), "fallback": "orchestrator sin audit_summary"}

    def _tools_inventory(self) -> dict:
        """Inventario de tools registradas con clasificación de riesgo."""
        try:
            from aiion.tools.registry import REGISTRY as TREG  # type: ignore
            tools = []
            for name, meta in TREG.items():
                tools.append({
                    "name": name,
                    "risk": "high" if name in HIGH_RISK_TOOLS
                            else "medium" if name in MEDIUM_RISK_TOOLS
                            else "low",
                    "description": (meta.get("description", "") if isinstance(meta, dict) else ""),
                })
            return {"total": len(tools), "tools": tools}
        except Exception as e:
            return {"total": 0, "tools": [], "error": str(e)}

    def _risk_scan(self) -> dict:
        inv = self._tools_inventory()
        high = [t["name"] for t in inv["tools"] if t["risk"] == "high"]
        medium = [t["name"] for t in inv["tools"] if t["risk"] == "medium"]
        score = 100 - len(high) * 15 - len(medium) * 5
        score = max(0, min(100, score))
        return {
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": [t["name"] for t in inv["tools"] if t["risk"] == "low"],
            "score": score,
            "rating": "A" if score >= 90 else "B" if score >= 75 else
                      "C" if score >= 60 else "D" if score >= 40 else "F",
            "ts": time.time(),
        }

    def _memory_check(self) -> dict:
        """Verifica que la memoria L2/L3 está cifrada."""
        result = {"encrypted": False, "files": [], "warnings": []}
        try:
            from aiion.config import DATA_DIR  # type: ignore
            data_dir = Path(DATA_DIR)
        except Exception:
            data_dir = _ROOT / "data"

        for fname in ("aiion_memory.md", "aiion_history.jsonl",
                      "memory.jsonl", "cognito_index.json"):
            p = data_dir / fname
            if p.exists():
                # Si el archivo empieza con Fernet token (gAAAAA...) está cifrado
                try:
                    with open(p, "rb") as f:
                        head = f.read(8)
                    encrypted = head.startswith(b"gAAAAA")
                except Exception:
                    encrypted = False
                result["files"].append({
                    "name": fname,
                    "path": str(p),
                    "size": p.stat().st_size,
                    "encrypted": encrypted,
                })
                if not encrypted:
                    result["warnings"].append(
                        f"{fname} NO cifrado")
        result["encrypted"] = (
            len(result["files"]) > 0 and
            all(f["encrypted"] for f in result["files"])
        )
        return result

    def _recommendations(self) -> dict:
        risk = self._risk_scan()
        mem = self._memory_check()
        recs = []

        if risk["high_risk"]:
            recs.append({
                "priority": "high",
                "msg": f"Tools de alto riesgo activas: {risk['high_risk']}. "
                       f"Aplicar capability-check o mover a blacklist.",
            })
        if mem["warnings"]:
            recs.append({
                "priority": "high",
                "msg": f"Archivos sin cifrar: {mem['warnings']}. "
                       f"Aplicar AES-256 (Fernet).",
            })
        if risk["score"] < 75:
            recs.append({
                "priority": "medium",
                "msg": f"Score de seguridad {risk['score']}/100 "
                       f"(rating {risk['rating']}). Reforzar capability-check.",
            })
        if not recs:
            recs.append({
                "priority": "info",
                "msg": "Sin hallazgos críticos. Mantener rotación de llaves (90d).",
            })
        return {
            "score": risk["score"],
            "rating": risk["rating"],
            "recommendations": recs,
            "ts": time.time(),
        }
