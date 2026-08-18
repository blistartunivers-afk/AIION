"""
tests/test_e2e.py — Tests End-to-End (F3.5)

Escenarios completos que validan el flujo de alto nivel:
1. Identidad → Capability → Ejecución → Audit → Stats
2. Subagente sara → Comando → Resultado
3. Plan JSON → Orchestrator → Subagentes
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────
#  Escenario 1: Flujo de identidad completo
# ─────────────────────────────────────────────────────────────
class TestIdentityFlow:
    """Valida el flujo: validar identidad → cargar plan → ejecutar → audit."""

    def test_flush_identidad_audita_evento(self, tmp_path):
        """Cada paso del flujo debe dejar rastro en audit."""
        from aiion.orchestrator import get_orchestrator, AuditLog, TaskStatus
        from aiion import orchestrator as orch_mod

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            orch_mod._orchestrator = None
            orch = get_orchestrator()

            # ejecutar varias cosas
            orch.submit("core", "doctor", {})  # OK
            orch.submit("core", "no_existe", {})  # DENIED

            log = orch.audit.tail(20)
            events = [e.get("event") for e in log]
            # Eventos clave del flujo
            assert "orchestrator.init" in events
            assert "agent.registered" in events
            assert "task.submit" in events
            assert "task.done" in events
            assert "task.denied" in events

    def test_metricas_coherentes_post_flujo(self, tmp_path):
        """Stats reflejan correctamente el historial tras operaciones."""
        from aiion.orchestrator import get_orchestrator, AuditLog
        from aiion import orchestrator as orch_mod

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            orch_mod._orchestrator = None
            orch = get_orchestrator()

            # 3 doctores + 2 denials
            for _ in range(3):
                orch.submit("core", "doctor", {})
            for _ in range(2):
                orch.submit("core", "no_existe", {})

            s = orch.stats()
            assert s["total"] == 5
            assert s["by_status"].get("denied", 0) == 2
            assert s["by_status"].get("success", 0) + \
                   s["by_status"].get("failed", 0) == 3


# ─────────────────────────────────────────────────────────────
#  Escenario 2: Subagente flow
# ─────────────────────────────────────────────────────────────
class TestSubagenteFlow:
    """Verifica el flujo subagente.describe + dispatch."""

    def test_sara_info_fluye(self):
        """sara.info debe retornar metadata correcta."""
        from aiion.subagentes.base import get_subagente
        sara = get_subagente("sara")
        info = sara.describe()
        assert info["name"] == "sara"
        assert isinstance(info["capabilities"], list)
        assert len(info["capabilities"]) > 0

    def test_memory_keeper_stats_retorna_forma_esperada(self):
        """memory_keeper.stats debe retornar dict con métricas."""
        from aiion.subagentes.base import get_subagente
        mk = get_subagente("memory_keeper")
        # Puede fallar si no hay memoria, pero debe retornar dict
        result = mk.dispatch("stats", {})
        assert "ok" in result
        assert result["subagente"] == "memory_keeper"

    def test_security_audit_info_fluye(self):
        """security_audit.info debe retornar capabilities."""
        from aiion.subagentes.base import get_subagente
        sa = get_subagente("security_audit")
        # info puede no estar en capabilities, probemos describe
        info = sa.describe()
        assert info["name"] == "security_audit"
        assert "audit_tail" in info["capabilities"]


# ─────────────────────────────────────────────────────────────
#  Escenario 3: Plan JSON completo
# ─────────────────────────────────────────────────────────────
class TestPlanJSONFlow:
    """Cargar plan JSON → ejecutar → resultados."""

    def test_plan_json_valido(self, tmp_path):
        """Cargar plan desde archivo JSON y ejecutar."""
        from aiion.orchestrator import get_orchestrator, AuditLog, TaskStatus
        from aiion import orchestrator as orch_mod

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps([
            {"agent": "core", "action": "doctor"},
            {"agent": "core", "action": "sensor_status"},
        ]))

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            orch_mod._orchestrator = None
            orch = get_orchestrator()

            plan = json.loads(plan_file.read_text())
            results = orch.execute_plan(plan)
            assert len(results) == 2
            for task in results:
                assert task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)

    def test_plan_con_mixto_exitoso_y_fallido(self, tmp_path):
        """Plan con 1 OK + 1 denied."""
        from aiion.orchestrator import get_orchestrator, AuditLog, TaskStatus
        from aiion import orchestrator as orch_mod

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            orch_mod._orchestrator = None
            orch = get_orchestrator()

            plan = [
                {"agent": "core", "action": "doctor"},
                {"agent": "core", "action": "no_existe"},
            ]
            results = orch.execute_plan(plan, stop_on_error=True)
            assert len(results) == 2
            assert results[0].status in (TaskStatus.SUCCESS, TaskStatus.FAILED)
            assert results[1].status == TaskStatus.DENIED


# ─────────────────────────────────────────────────────────────
#  Escenario 4: Audit trail completo
# ─────────────────────────────────────────────────────────────
class TestAuditTrail:
    """El audit debe registrar todos los eventos clave en orden."""

    def test_audit_eventos_ordenados(self, tmp_path):
        """Los eventos deben aparecer en orden cronológico."""
        from aiion.orchestrator import get_orchestrator, AuditLog
        from aiion import orchestrator as orch_mod

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            orch_mod._orchestrator = None
            orch = get_orchestrator()

            # Hacer 5 submits
            for i in range(5):
                orch.submit("core", "no_existe", {})

            log = orch.audit.tail(20)
            ts_list = [e.get("ts", 0) for e in log]
            # Monotónico
            assert ts_list == sorted(ts_list)

    def test_audit_persiste_entre_lecturas(self, tmp_path):
        """El audit debe persistir en disco y poder releerse."""
        from aiion.orchestrator import AuditLog

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        # No usar mock: dejar comportamiento nativo (no trunca)
        audit = AuditLog(path=audit_file)
        audit.record("event1", foo=1)
        audit.record("event2", foo=2)

        # Releer sin truncar
        audit2 = AuditLog(path=audit_file)
        log = audit2.tail(10)
        assert len(log) >= 2
        events = [e["event"] for e in log]
        assert "event1" in events
        assert "event2" in events
