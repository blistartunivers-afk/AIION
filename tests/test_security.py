"""
tests/test_security.py — Tests de seguridad (F3.3 - OWASP Top 10)

Cubre:
- Capability-check del orchestrator (denegación de tools no autorizadas)
- Blacklist/whitelist de MCP
- Sanitización de inputs
- Audit log registra denials
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from aiion.orchestrator import get_orchestrator
from aiion.tools.registry import (
    DANGEROUS_TOOLS,
    ask_permission,
    SESSION_ALLOWED,
)


# ─────────────────────────────────────────────────────────────
#  Dangerous tools catalog
# ─────────────────────────────────────────────────────────────
class TestDangerousTools:
    """Verifica que las herramientas críticas estén en la blacklist."""

    def test_dangerous_tools_incluye_shell(self):
        assert "run_shell_command" in DANGEROUS_TOOLS

    def test_dangerous_tools_incluye_write_file(self):
        assert "write_file" in DANGEROUS_TOOLS

    def test_dangerous_tools_incluye_replace(self):
        assert "replace" in DANGEROUS_TOOLS

    def test_dangerous_tools_incluye_process_manager(self):
        assert "process_manager" in DANGEROUS_TOOLS

    def test_count_dangerous_tools(self):
        """El set debe tener al menos 4 entries críticas."""
        assert len(DANGEROUS_TOOLS) >= 4


# ─────────────────────────────────────────────────────────────
#  Permission gating
# ─────────────────────────────────────────────────────────────
class TestPermissionGating:
    """Tools peligrosas requieren permiso explícito."""

    def setup_method(self):
        SESSION_ALLOWED.clear()

    def test_run_shell_command_cancela_sin_permiso(self):
        with patch("builtins.input", return_value="3"):  # cancelar
            assert ask_permission("run_shell_command", {"command": "ls"}) is False

    def test_read_file_no_requiere_permiso(self):
        """Tool de solo lectura no debe pedir permiso (no es dangerous)."""
        assert ask_permission("read_file", {"path": "/x"}) is True

    def test_ask_permission_allow_once(self):
        with patch("builtins.input", return_value="1"):
            assert ask_permission("run_shell_command", {"command": "ls"}) is True

    def test_ask_permission_session_persiste(self):
        with patch("builtins.input", return_value="2"):
            ask_permission("run_shell_command", {"command": "ls"})
        # Ahora debe estar en session allowed
        assert "run_shell_command" in SESSION_ALLOWED
        # Y ya no debe preguntar
        assert ask_permission("run_shell_command", {"command": "ls"}) is True

    def test_process_manager_list_no_pide_permiso(self):
        """acción 'list' siempre permitida sin prompt."""
        assert ask_permission("process_manager", {"action": "list"}) is True

    def test_process_manager_kill_pide_permiso(self):
        """otras acciones de process_manager requieren prompt."""
        with patch("builtins.input", return_value="3"):
            assert ask_permission("process_manager", {"action": "kill", "pid": 1}) is False


# ─────────────────────────────────────────────────────────────
#  Blacklist MCP
# ─────────────────────────────────────────────────────────────
class TestMCPBlacklist:
    """El cliente MCP debe bloquear herramientas en blacklist."""

    def test_default_blacklist_incluye_shell(self):
        from aiion.mcp.client import DEFAULT_CONFIG
        bl = DEFAULT_CONFIG["blacklist"]
        assert "run_shell_command" in bl
        assert "process_manager" in bl
        assert "hacer_llamada" in bl
        assert "enviar_sms" in bl

    def test_call_tool_bloqueada_por_blacklist(self):
        from aiion.mcp.client import MCPClient
        cli = MCPClient()
        cli.config["blacklist"] = ["dangerous_tool"]
        cli.config["whitelist"] = []
        result = cli.call_tool("dangerous_tool", {})
        assert "error" in result
        assert "blacklist" in result["error"].lower()

    def test_call_tool_no_en_whitelist(self):
        from aiion.mcp.client import MCPClient
        cli = MCPClient()
        cli.config["whitelist"] = ["allowed_only"]
        cli.config["blacklist"] = []
        result = cli.call_tool("other_tool", {})
        assert "error" in result
        assert "whitelist" in result["error"].lower()

    def test_call_tool_permitida_pasa(self):
        from aiion.mcp.client import MCPClient
        cli = MCPClient()
        cli.config["blacklist"] = []
        cli.config["whitelist"] = ["allowed_tool"]
        with patch.object(cli, "_call", return_value={"content": "ok"}) as mock_call:
            result = cli.call_tool("allowed_tool", {"x": 1})
        assert "error" not in result
        mock_call.assert_called_once_with(
            "tools/call",
            {"name": "allowed_tool", "arguments": {"x": 1}}
        )


# ─────────────────────────────────────────────────────────────
#  Audit log persiste
# ─────────────────────────────────────────────────────────────
class TestAuditPersistence:
    """El audit log debe persistir y registrar denials."""

    def test_audit_graba_eventos(self, tmp_orch):
        from aiion.orchestrator import TaskStatus
        orch = tmp_orch
        # Generar evento de denial
        task = orch.submit("xxx", "yyy", {})
        assert task.status == TaskStatus.DENIED
        log = orch.audit.tail(10)
        # Debe haber al menos un evento de denial
        assert any(e.get("event") == "task.denied" for e in log)

    def test_audit_mantiene_orden_cronologico(self, tmp_orch):
        orch = tmp_orch
        # Hacer varios submits
        for i in range(5):
            orch.submit("xxx", f"yyy_{i}", {})
        log = orch.audit.tail(5)
        # Las timestamps deben ser monotónicas
        ts_list = [e.get("ts", 0) for e in log]
        assert ts_list == sorted(ts_list)

    def test_audit_init_registra(self, tmp_orch):
        """Al inicializar el orchestrator, registra eventos init + agents."""
        orch = tmp_orch
        log = orch.audit.tail(20)
        events = {e.get("event") for e in log}
        # Debe tener orchestrator.init y agent.registered
        assert "orchestrator.init" in events
        assert "agent.registered" in events


# ─────────────────────────────────────────────────────────────
#  Capability check del orchestrator
# ─────────────────────────────────────────────────────────────
class TestCapabilityCheck:
    """El orchestrator debe rechazar capabilities no autorizadas."""

    def test_orchestrator_rechaza_capability_desconocida(self, tmp_orch):
        from aiion.orchestrator import TaskStatus
        orch = tmp_orch
        task = orch.submit("core", "accion_que_no_existe", {})
        assert task.status == TaskStatus.DENIED
        assert "no tiene capability" in task.error or "capability" in task.error.lower()

    def test_orchestrator_rechaza_agente_desconocido(self, tmp_orch):
        from aiion.orchestrator import TaskStatus
        orch = tmp_orch
        task = orch.submit("agente_inexistente", "doctor", {})
        assert task.status == TaskStatus.DENIED


# ─────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def tmp_orch(tmp_path):
    """Orchestrator con audit aislado por test."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    audit_file = audit_dir / "audit.jsonl"
    # Patchear DEFAULT_NAME dentro de AuditLog
    from aiion.orchestrator import AuditLog
    with patch.object(AuditLog, "__init__", lambda self, path=None: (
        setattr(self, "path", path or audit_file),
        audit_file.parent.mkdir(parents=True, exist_ok=True),
        audit_file.touch() if not audit_file.exists() else None,
        audit_file.write_text("")
    )[0]):
        # Reset singleton
        from aiion import orchestrator as orch_mod
        orch_mod._orchestrator = None
        yield get_orchestrator()
