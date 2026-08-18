"""
tests/test_integration.py — Tests de integración end-to-end (F3.2)

Cubre el flujo:
  CLI → orchestrator → subagente → audit log → resultado
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────
#  Flujo completo CLI → orchestrator → subagente
# ─────────────────────────────────────────────────────────────
class TestEndToEndFlow:
    """El flujo completo debe funcionar y dejar rastro en audit."""

    def test_cli_agents_lista_orquestador(self, tmp_path, capsys):
        """Cuando el usuario corre 'agents', ve los agentes disponibles."""
        from aiion.orchestrator_cli import main
        with patch("sys.argv", ["cli", "agents"]):
            main()
        out = capsys.readouterr().out
        # Al menos debe mencionarse el agente 'core'
        assert "core" in out

    def test_cli_submit_ejecuta_y_audita(self, tmp_path):
        """Submit ejecuta una tarea core y registra en audit."""
        from aiion.orchestrator import get_orchestrator, TaskStatus, AuditLog
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

            # Ejecutar una capability válida
            task = orch.submit("core", "doctor", {})
            assert task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)
            # El audit debe contener el evento
            log = orch.audit.tail(5)
            events = [e.get("event") for e in log]
            assert "task.submit" in events

    def test_flujo_denegacion_graba_audit(self, tmp_path):
        """Cuando se rechaza una capability, audit guarda el denial."""
        from aiion.orchestrator import get_orchestrator, TaskStatus, AuditLog
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

            task = orch.submit("core", "no_existe", {})
            assert task.status == TaskStatus.DENIED
            log = orch.audit.tail(5)
            events = [e.get("event") for e in log]
            assert "task.denied" in events


# ─────────────────────────────────────────────────────────────
#  Plan execution
# ─────────────────────────────────────────────────────────────
class TestPlanExecution:
    """Planes deben ejecutar en orden y registrar cada paso."""

    def test_plan_stop_on_error(self, tmp_path):
        """Plan con error se detiene en el paso fallido."""
        from aiion.orchestrator import get_orchestrator, TaskStatus, AuditLog
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
                {"agent": "core", "action": "doctor"},      # OK
                {"agent": "core", "action": "no_existe"},   # DENIED
                {"agent": "core", "action": "memory_recall"},# No llega
            ]
            results = orch.execute_plan(plan, stop_on_error=True)
            # Solo 2 pasos ejecutados
            assert len(results) == 2
            assert results[1].status == TaskStatus.DENIED

    def test_plan_continue_on_error(self, tmp_path):
        """Plan con stop_on_error=False ejecuta todos los pasos."""
        from aiion.orchestrator import get_orchestrator, TaskStatus, AuditLog
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
            results = orch.execute_plan(plan, stop_on_error=False)
            assert len(results) == 2


# ─────────────────────────────────────────────────────────────
#  Subagente integration
# ─────────────────────────────────────────────────────────────
class TestSubagenteIntegration:
    """El subagente registry debe estar poblado al importar."""

    def test_subagentes_registrados_al_importar(self):
        """El bridge auto-registra 3 subagentes."""
        from aiion.subagentes.base import REGISTRY
        # Al menos debe haber sara, security_audit, memory_keeper
        assert "sara" in REGISTRY
        assert "security_audit" in REGISTRY
        assert "memory_keeper" in REGISTRY

    def test_subagente_info_retorna_metadata(self):
        from aiion.subagentes.base import get_subagente
        sara = get_subagente("sara")
        info = sara.describe()
        assert info["name"] == "sara"
        assert "capabilities" in info
        assert isinstance(info["capabilities"], list)


# ─────────────────────────────────────────────────────────────
#  Stats consistency
# ─────────────────────────────────────────────────────────────
class TestStatsConsistency:
    """Las stats deben reflejar el historial correctamente."""

    def test_stats_vacio_inicio(self, tmp_path):
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
            s = orch.stats()
            assert s["total"] == 0
            assert "by_status" in s or "agents" in s

    def test_stats_refleja_submits(self, tmp_path):
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

            # Generar varias tareas
            for i in range(3):
                orch.submit("core", "doctor", {})
            # 1 denied
            orch.submit("core", "no_existe", {})

            s = orch.stats()
            assert s["total"] >= 4
            by_status = s.get("by_status", {})
            assert "denied" in by_status
            assert by_status["denied"] >= 1
            assert "success" in by_status or "failed" in by_status
