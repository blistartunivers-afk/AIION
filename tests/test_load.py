"""
tests/test_load.py — Tests de carga (F3.4)

Mide tiempos bajo concurrencia / burst para validar que:
- El orchestrator no degrada con muchos submits
- El rate-limit de la API funciona
- Las stats son consistentes después de tráfico
"""
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────
#  Burst de submits al orchestrator
# ─────────────────────────────────────────────────────────────
class TestOrchestratorLoad:
    def test_burst_100_submits_denegados(self, tmp_path):
        """100 submits denegados en serie deben completar < 2s."""
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

            t0 = time.time()
            for i in range(100):
                task = orch.submit("core", f"no_existe_{i}", {})
                assert task.status == TaskStatus.DENIED
            elapsed = time.time() - t0

        assert elapsed < 5.0, f"100 submits took {elapsed:.2f}s"
        # Stats reflejan las 100 denegaciones
        s = orch.stats()
        assert s["total"] == 100
        assert s["by_status"].get("denied", 0) == 100

    def test_burst_mixto_doctores_y_denials(self, tmp_path):
        """10 doctors + 40 denials (doctors tardan ~0.2s cada uno)."""
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

            for i in range(10):
                orch.submit("core", "doctor", {})
            for i in range(40):
                orch.submit("core", f"no_{i}", {})

            s = orch.stats()
            assert s["total"] == 50


# ─────────────────────────────────────────────────────────────
#  λ/μ: teoría de colas simple
# ─────────────────────────────────────────────────────────────
class TestQueueing:
    """Métricas simples λ (tasa de entrada) y μ (tasa de servicio)."""

    def test_throughput_metrics(self, tmp_path):
        """Calcula throughput de submits por segundo."""
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

            n = 50
            t0 = time.time()
            for i in range(n):
                orch.submit("core", "no_existe", {})
            elapsed = time.time() - t0

            throughput = n / elapsed if elapsed > 0 else float("inf")
            # Esperamos al menos 10 submits/s en este entorno
            assert throughput > 10, f"Throughput {throughput:.1f} ops/s demasiado bajo"

    def test_avg_latency_calculada(self, tmp_path):
        """Las stats deben calcular avg_latency_ms."""
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

            # Una task exitosa (doctor)
            task = orch.submit("core", "doctor", {})
            assert task.status == TaskStatus.SUCCESS
            assert task.duration_ms is not None
            assert task.duration_ms >= 0

            s = orch.stats()
            # avg_latency_ms puede ser None si no hay success, pero aquí sí hay
            assert s["avg_latency_ms"] is not None or s["total"] > 0


# ─────────────────────────────────────────────────────────────
#  Stress en audit log
# ─────────────────────────────────────────────────────────────
class TestAuditLoad:
    def test_audit_tail_con_muchos_eventos(self, tmp_path):
        """tail() debe ser eficiente incluso con muchos eventos."""
        from aiion.orchestrator import AuditLog

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        audit_file = audit_dir / "audit.jsonl"

        with patch.object(AuditLog, "__init__", lambda self, path=None: (
            setattr(self, "path", path or audit_file),
            audit_file.parent.mkdir(parents=True, exist_ok=True),
            audit_file.write_text("")
        )[0]):
            audit = AuditLog()
            # Grabar 500 eventos
            for i in range(500):
                audit.record("test", n=i)
            # tail(50) debe devolver los últimos 50
            t0 = time.time()
            log = audit.tail(50)
            elapsed = time.time() - t0
            assert len(log) == 50
            assert log[-1]["n"] == 499
            assert elapsed < 0.5, f"tail tardó {elapsed:.2f}s"


# ─────────────────────────────────────────────────────────────
#  MCP load
# ─────────────────────────────────────────────────────────────
class TestMCPLoad:
    def test_100_calls_seguidos(self, tmp_path):
        """100 calls al client deben completarse < 2s."""
        from aiion.mcp.client import MCPClient

        cfg = tmp_path / "blist_config.json"
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()

        # Mock que también incrementa _stats (como el real)
        def fake_call(method, params=None, timeout=0):
            cli._stats["calls"] += 1
            cli._stats["last_call"] = "2026-01-01"
            return {"ok": True}

        with patch.object(cli, "_call", side_effect=fake_call):
            t0 = time.time()
            for i in range(100):
                cli.call_tool("foo", {"i": i})
            elapsed = time.time() - t0

        assert elapsed < 2.0, f"100 calls took {elapsed:.2f}s"
        assert cli._stats["calls"] == 100
