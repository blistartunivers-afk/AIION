"""
aiion/orchestrator.py — Orquestador de sub-agentes AIION (F2.4).

Responsabilidad:
  • Registrar sub-agentes con sus capacidades (registry).
  • Recibir tareas de alto nivel, descomponerlas y delegarlas.
  • Aplicar capability-based security (allowlist por agente).
  • Persistir un audit log inmutable (quién hizo qué, cuándo).
  • Exponer un bus de eventos simple para sincronización.

NO rompe `claude.py` ni `blist_bridge.py`: ambos siguen funcionando
como scripts standalone. Este orquestador los *usa* opcionalmente.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aiion import config


# ──────────────────────────────────────────────────────────────────────
# Tipos de datos
# ──────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    DENIED    = "denied"   # bloqueada por capability check
    TIMEOUT   = "timeout"


@dataclass
class Task:
    """Tarea atómica que un sub-agente puede ejecutar."""
    id: str
    agent: str           # nombre del sub-agente ("claude", "blist_bridge", "core")
    action: str          # verbo: "plan", "tools", "call", "status", etc.
    args: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["duration_ms"] = self.duration_ms
        return d

    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at) * 1000)
        return None


@dataclass
class AgentSpec:
    """Especificación declarativa de un sub-agente."""
    name: str
    description: str
    capabilities: List[str]        # acciones que puede realizar
    required_tools: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    enabled: bool = True


# ──────────────────────────────────────────────────────────────────────
# Audit log (append-only JSONL)
# ──────────────────────────────────────────────────────────────────────

class AuditLog:
    """Registro inmutable de operaciones del orquestador."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (config.AIION_HOME / "orchestrator_audit.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def record(self, event: str, **fields) -> None:
        entry = {
            "ts":    time.time(),
            "event": event,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def tail(self, n: int = 20) -> List[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for ln in lines[-n:]:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out


# ──────────────────────────────────────────────────────────────────────
# Capability-based security
# ──────────────────────────────────────────────────────────────────────

class CapabilityError(PermissionError):
    """Lanzada cuando un agente intenta una acción fuera de sus capabilities."""


# ──────────────────────────────────────────────────────────────────────
# Orquestador
# ──────────────────────────────────────────────────────────────────────

class Orchestrator:
    """Bus central de sub-agentes con capability-check y audit log."""

    def __init__(self):
        self.registry: Dict[str, AgentSpec] = {}
        self.history: List[Task] = []
        self.audit = AuditLog()
        self.audit.record("orchestrator.init", version=config.VERSION)
        self._register_builtins()

    # ── Registry ────────────────────────────────────────────────────
    def register(self, spec: AgentSpec) -> None:
        if spec.name in self.registry:
            raise ValueError(f"Agente '{spec.name}' ya registrado")
        self.registry[spec.name] = spec
        self.audit.record("agent.registered", name=spec.name,
                          capabilities=spec.capabilities)

    def list_agents(self) -> List[str]:
        return [n for n, s in self.registry.items() if s.enabled]

    def describe(self, name: str) -> Optional[AgentSpec]:
        return self.registry.get(name)

    # ── Capability check ────────────────────────────────────────────
    def _authorize(self, task: Task) -> None:
        spec = self.registry.get(task.agent)
        if spec is None:
            raise CapabilityError(f"agente '{task.agent}' no existe")
        if not spec.enabled:
            raise CapabilityError(f"agente '{task.agent}' deshabilitado")
        if task.action not in spec.capabilities:
            raise CapabilityError(
                f"agente '{task.agent}' no tiene capability '{task.action}'"
            )

    # ── Dispatch ────────────────────────────────────────────────────
    def submit(self, agent: str, action: str, args: Optional[dict] = None,
               *, timeout_s: float = 60.0) -> Task:
        task = Task(
            id=uuid.uuid4().hex[:12],
            agent=agent,
            action=action,
            args=args or {},
        )
        self.audit.record("task.submit", **task.to_dict())

        # 1) Capability check
        try:
            self._authorize(task)
        except CapabilityError as e:
            task.status = TaskStatus.DENIED
            task.error = str(e)
            task.finished_at = time.time()
            self.history.append(task)
            self.audit.record("task.denied", task_id=task.id, reason=str(e))
            return task

        # 2) Ejecutar
        spec = self.registry[task.agent]
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        try:
            if spec.handler is None:
                raise RuntimeError(f"agente '{task.agent}' sin handler")
            task.result = spec.handler(task.action, task.args)
            task.status = TaskStatus.SUCCESS
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"{type(e).__name__}: {e}"
        finally:
            task.finished_at = time.time()
            self.history.append(task)
            self.audit.record("task.done",
                              task_id=task.id,
                              status=task.status.value,
                              duration_ms=task.duration_ms)
        return task

    # ── Plan execution (alto nivel) ────────────────────────────────
    def execute_plan(self, plan: List[dict], *, stop_on_error: bool = True) -> List[Task]:
        """Ejecuta una secuencia de {agent, action, args}.

        Devuelve la lista de Task en orden de ejecución.
        """
        results: List[Task] = []
        for step in plan:
            t = self.submit(
                agent=step["agent"],
                action=step["action"],
                args=step.get("args", {}),
            )
            results.append(t)
            if stop_on_error and t.status in (TaskStatus.FAILED, TaskStatus.DENIED):
                self.audit.record("plan.aborted", last_task=t.id)
                break
        return results

    # ── Métricas ────────────────────────────────────────────────────
    def stats(self) -> dict:
        total = len(self.history)
        if total == 0:
            return {"total": 0, "agents": self.list_agents()}
        by_status: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        durations: List[int] = []
        for t in self.history:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            by_agent[t.agent] = by_agent.get(t.agent, 0) + 1
            d = t.duration_ms
            if d is not None and t.status == TaskStatus.SUCCESS:
                durations.append(d)
        return {
            "total":         total,
            "by_status":     by_status,
            "by_agent":      by_agent,
            "success_rate":  round(by_status.get("success", 0) / total * 100, 1),
            "avg_latency_ms": (round(sum(durations) / len(durations), 1)
                               if durations else None),
            "agents":        self.list_agents(),
        }

    # ── Registro de agentes built-in ───────────────────────────────
    def _register_builtins(self) -> None:
        # 1) core: introspección del propio AIION
        self.register(AgentSpec(
            name="core",
            description="Núcleo AIION — doctor, backup, planes, sensor daemon",
            capabilities=["doctor", "backup", "plan_list", "plan_show",
                          "sensor_status", "memory_recall"],
            handler=self._handle_core,
        ))
        # 2) claude: planificador (delega al script existente)
        self.register(AgentSpec(
            name="claude",
            description="Sub-agente Claude — planificación de proyectos",
            capabilities=["reporte", "generar", "show"],
            handler=self._handle_claude,
        ))
        # 3) blist_bridge: MCP hacia blistv11
        self.register(AgentSpec(
            name="blist_bridge",
            description="Puente MCP AIION ↔ blistv11 (sensores, voz, tools)",
            capabilities=["status", "ping", "tools", "call", "health", "sync"],
            required_tools=["mcp_client"],
            handler=self._handle_blist,
        ))

    # ── Handlers built-in ──────────────────────────────────────────
    def _handle_core(self, action: str, args: dict) -> Any:
        """Acceso indirecto a funciones de aiion.core sin import circular."""
        from aiion import core as _core
        if action == "doctor":
            _core.system_doctor()
            return {"ok": True}
        if action == "backup":
            label = args.get("label", "auto")
            _core.do_backup(label)
            return {"backup": label}
        if action == "plan_list":
            return _core.create_plan("list")
        if action == "plan_show":
            return _core.create_plan(f"show {args.get('name', '')}")
        if action == "sensor_status":
            from aiion.sensors.daemon import sensor_query
            return sensor_query(minutes=int(args.get("minutes", 5)),
                                sensor=args.get("sensor", "system"))
        if action == "memory_recall":
            from aiion.memory.persistence import memory_load
            return memory_load()
        raise ValueError(f"acción core '{action}' no implementada")

    def _handle_claude(self, action: str, args: dict) -> Any:
        """Delegar al sub-agente Claude (import lazy)."""
        from aiion.subagentes.claude import ejecutar
        proyecto = args.get("proyecto", "")
        ejecutar(proyecto, action)
        return {"proyecto": proyecto, "accion": action}

    def _handle_blist(self, action: str, args: dict) -> Any:
        """Delegar al bridge MCP (import lazy)."""
        from aiion.mcp.client import get_client
        cli = get_client()
        if action == "status":
            return cli.report()
        if action == "ping":
            return cli.ping()
        if action == "tools":
            return cli.list_tools(use_cache=False)
        if action == "call":
            return cli.call_tool(args.get("tool", ""), args.get("params", {}))
        if action == "health":
            return {"online": cli.is_online(), "info": cli.info()}
        if action == "sync":
            from aiion.subagentes.claude import reporte as _reporte
            txt = _reporte()
            return cli.call_tool("write_note", {
                "title":   "AIION sync",
                "content": txt[:4000],
                "category": "aiion",
            })
        raise ValueError(f"acción blist_bridge '{action}' no implementada")


# ── Singleton lazy ─────────────────────────────────────────────────
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
