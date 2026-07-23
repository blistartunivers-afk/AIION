"""
tests/test_orchestrator.py — Tests del orquestador AIION (F2.4).

Cubre:
  • Registry: registrar/listar/describir agentes
  • Capability-check: denegación cuando action no permitida
  • Dispatch: éxito, fallo, denegado
  • execute_plan: ejecución secuencial + stop_on_error
  • Audit log: persistencia de eventos
  • Stats: agregaciones correctas
  • Handlers built-in: doctor, memory_recall (sin red)
"""
import json
import pytest
from pathlib import Path
from aiion.orchestrator import (
    Orchestrator, AgentSpec, TaskStatus, CapabilityError, AuditLog,
)


@pytest.fixture
def orch(tmp_path, monkeypatch):
    """Orquestador fresco con DBs y home en tmp."""
    # Aislar audit log
    home = tmp_path / "AIION_home"
    home.mkdir()
    monkeypatch.setattr("aiion.config.AIION_HOME", home)
    monkeypatch.setattr("aiion.config.SENSOR_DB", home / "sensor.db")
    # Inicializar DB que necesitan algunos handlers
    from aiion.db import init_db
    init_db()
    # Crear orquestador
    return Orchestrator()


class TestRegistry:
    def test_builtins_registrados(self, orch):
        assert "core" in orch.registry
        assert "claude" in orch.registry
        assert "blist_bridge" in orch.registry

    def test_list_agents_devuelve_los_3(self, orch):
        names = orch.list_agents()
        assert set(names) == {"core", "claude", "blist_bridge"}

    def test_describe(self, orch):
        spec = orch.describe("core")
        assert spec is not None
        assert "doctor" in spec.capabilities
        assert spec.description

    def test_register_agente_personalizado(self, orch):
        spec = AgentSpec(
            name="tester",
            description="Agente de prueba",
            capabilities=["ping"],
            handler=lambda action, args: "pong",
        )
        orch.register(spec)
        assert "tester" in orch.list_agents()

    def test_register_duplicado_falla(self, orch):
        spec = AgentSpec(name="core", description="dup",
                         capabilities=["x"], handler=None)
        with pytest.raises(ValueError, match="ya registrado"):
            orch.register(spec)

    def test_agente_deshabilitado_no_aparece(self, orch):
        orch.registry["core"].enabled = False
        assert "core" not in orch.list_agents()


class TestCapabilityCheck:
    def test_accion_no_permitida_es_denegada(self, orch):
        t = orch.submit("core", "rm_rf", {"path": "/"})  # no existe en caps
        assert t.status == TaskStatus.DENIED
        assert "rm_rf" in t.error

    def test_agente_inexistente_es_denegado(self, orch):
        t = orch.submit("fantasma", "ping")
        assert t.status == TaskStatus.DENIED
        assert "fantasma" in t.error

    def test_agente_deshabilitado_es_denegado(self, orch):
        orch.registry["core"].enabled = False
        t = orch.submit("core", "doctor")
        assert t.status == TaskStatus.DENIED

    def test_accion_permitida_pasa_check(self, orch):
        # memory_recall no hace I/O de red
        t = orch.submit("core", "memory_recall")
        assert t.status == TaskStatus.SUCCESS


class TestDispatch:
    def test_handler_exitoso(self, orch):
        spec = AgentSpec(name="ok", description="ok",
                         capabilities=["do"],
                         handler=lambda a, args: {"echo": args.get("x")})
        orch.register(spec)
        t = orch.submit("ok", "do", {"x": 42})
        assert t.status == TaskStatus.SUCCESS
        assert t.result == {"echo": 42}
        assert t.duration_ms is not None
        assert t.duration_ms >= 0

    def test_handler_con_excepcion_marca_failed(self, orch):
        def bad(a, args): raise RuntimeError("boom")
        spec = AgentSpec(name="bad", description="bad",
                         capabilities=["go"], handler=bad)
        orch.register(spec)
        t = orch.submit("bad", "go")
        assert t.status == TaskStatus.FAILED
        assert "boom" in t.error

    def test_handler_none_marca_failed(self, orch):
        spec = AgentSpec(name="nh", description="nh",
                         capabilities=["x"], handler=None)
        orch.register(spec)
        t = orch.submit("nh", "x")
        assert t.status == TaskStatus.FAILED
        assert "sin handler" in t.error

    def test_task_id_unico(self, orch):
        spec = AgentSpec(name="u", description="u",
                         capabilities=["x"],
                         handler=lambda a, args: 1)
        orch.register(spec)
        ids = {orch.submit("u", "x").id for _ in range(10)}
        assert len(ids) == 10


class TestExecutePlan:
    def test_plan_exitoso(self, orch):
        spec = AgentSpec(name="p", description="p", capabilities=["x"],
                         handler=lambda a, args: "ok")
        orch.register(spec)
        plan = [{"agent": "p", "action": "x"} for _ in range(3)]
        results = orch.execute_plan(plan)
        assert len(results) == 3
        assert all(t.status == TaskStatus.SUCCESS for t in results)

    def test_plan_se_detiene_en_error(self, orch):
        def fail(a, args): raise RuntimeError("stop")
        spec = AgentSpec(name="p2", description="p2", capabilities=["x"],
                         handler=fail)
        orch.register(spec)
        plan = [{"agent": "p2", "action": "x"} for _ in range(5)]
        results = orch.execute_plan(plan, stop_on_error=True)
        assert len(results) == 1  # solo la primera se ejecutó
        assert results[0].status == TaskStatus.FAILED

    def test_plan_sin_stop_ejecuta_todo(self, orch):
        def fail(a, args): raise RuntimeError("x")
        spec = AgentSpec(name="p3", description="p3", capabilities=["x"],
                         handler=fail)
        orch.register(spec)
        plan = [{"agent": "p3", "action": "x"} for _ in range(3)]
        results = orch.execute_plan(plan, stop_on_error=False)
        assert len(results) == 3


class TestAuditLog:
    def test_audit_persiste(self, orch, tmp_path):
        # orch ya escribió init + register
        assert orch.audit.path.exists()
        lines = orch.audit.path.read_text().strip().splitlines()
        assert len(lines) >= 3  # init + 3 registers
        # Cada línea es JSON válido
        for ln in lines:
            json.loads(ln)

    def test_audit_tail(self, orch):
        tail = orch.audit.tail(5)
        assert isinstance(tail, list)
        assert all("ts" in e and "event" in e for e in tail)

    def test_audit_graba_denial(self, orch):
        orch.submit("fantasma", "x")
        events = [e["event"] for e in orch.audit.tail(20)]
        assert "task.denied" in events

    def test_audit_graba_task_done(self, orch):
        orch.submit("core", "memory_recall")
        events = [e["event"] for e in orch.audit.tail(20)]
        assert "task.done" in events


class TestStats:
    def test_stats_sin_historial(self, orch):
        s = orch.stats()
        assert s["total"] == 0
        assert "core" in s["agents"]

    def test_stats_con_mezcla(self, orch):
        orch.submit("core", "memory_recall")        # success
        orch.submit("fantasma", "x")                # denied
        s = orch.stats()
        assert s["total"] == 2
        assert s["by_status"]["success"] == 1
        assert s["by_status"]["denied"] == 1
        assert s["by_agent"]["core"] == 1
        assert s["success_rate"] == 50.0
        assert s["avg_latency_ms"] is not None
        assert s["avg_latency_ms"] >= 0


class TestBuiltinHandlers:
    """Tests de integración con handlers reales (sin red)."""

    def test_core_memory_recall(self, orch):
        t = orch.submit("core", "memory_recall")
        assert t.status == TaskStatus.SUCCESS

    def test_core_sensor_status(self, orch):
        t = orch.submit("core", "sensor_status", {"minutes": 1, "sensor": "battery"})
        assert t.status == TaskStatus.SUCCESS
