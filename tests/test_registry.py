"""tests/test_registry.py — Tests para aiion/tools/registry.py."""
import json
from unittest.mock import patch, MagicMock
import pytest

from aiion.tools.registry import (
    TOOLS,
    TOOL_MAP,
    DANGEROUS_TOOLS,
    SESSION_ALLOWED,
    tool_memory_search,
    tool_process_manager,
    ask_permission,
    execute_tool,
)
from aiion.config import DANGEROUS_TOOLS as CONFIG_DANGEROUS_TOOLS


class TestToolDefinitions:
    """Tests para las definiciones de tools."""

    def test_tools_count(self):
        """Verifica que hay 37 tools definidas (28 base + 9 Code Invest)."""
        assert len(TOOLS) == 37

    def test_tool_map_count(self):
        """Verifica que TOOL_MAP tiene 37 entradas."""
        assert len(TOOL_MAP) == 37

    def test_tool_names_match(self):
        """Nombres en TOOLS coinciden con claves de TOOL_MAP."""
        tool_names = {t["function"]["name"] for t in TOOLS}
        assert set(TOOL_MAP.keys()) == tool_names

    def test_all_tools_have_required_fields(self):
        """Cada tool tiene type, function, name, description, parameters."""
        for tool in TOOLS:
            assert tool["type"] == "function"
            assert "function" in tool
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]
            assert "required" in func["parameters"]

    def test_dangerous_tools_set(self):
        """DANGEROUS_TOOLS coincide con config."""
        assert DANGEROUS_TOOLS == CONFIG_DANGEROUS_TOOLS
        expected = {"run_shell_command", "write_file", "replace", "process_manager"}
        assert DANGEROUS_TOOLS == expected

    def test_tool_categories(self):
        """Verifica que las tools están en las categorías esperadas."""
        # Filesystem (7)
        fs_tools = {"read_file", "write_file", "replace", "run_shell_command",
                    "list_directory", "glob", "grep_search"}
        # Web (1)
        web_tools = {"web_fetch"}
        # Memoria (2)
        mem_tools = {"diff_files", "memory_search"}
        # Procesos (1)
        proc_tools = {"process_manager"}
        # Android (5)
        android_tools = {"get_android_status", "sensor_query", "take_photo",
                         "listar_camaras", "get_gps"}
        # Notificaciones (2)
        notif_tools = {"notificacion", "cancelar_notificacion"}
        # Comunicación (5)
        comm_tools = {"leer_sms", "enviar_sms", "historial_llamadas",
                      "hacer_llamada", "info_telefonia"}
        # Voz (2)
        voice_tools = {"hablar", "listar_voces"}
        # Tareas (3)
        task_tools = {"crear_tarea", "listar_tareas", "eliminar_tarea"}
        # Code Invest (9)
        code_invest_tools = {"code_invest_analyze", "code_invest_file", "code_invest_smells",
                             "code_invest_dependencies", "code_invest_duplicates", "code_invest_patterns",
                             "code_invest_dead_code", "code_invest_complexity", "code_invest_god_classes"}
        
        all_expected = (fs_tools | web_tools | mem_tools | proc_tools | 
                        android_tools | notif_tools | comm_tools | voice_tools | task_tools | code_invest_tools)
        actual = set(TOOL_MAP.keys())
        assert actual == all_expected


class TestToolMemorySearch:
    """Tests para tool_memory_search."""

    @patch("aiion.tools.registry.history_search")
    def test_memory_search_with_results(self, mock_history_search):
        """Búsqueda con resultados."""
        mock_history_search.return_value = [
            {"ts": "2026-01-01T10:00:00", "user": "Hola", "agent": "¡Hola!"},
            {"ts": "2026-01-01T11:00:00", "user": "Adiós", "agent": "Hasta luego"},
        ]
        
        result = tool_memory_search("Hola", top_k=2)
        
        assert "Resultados para 'Hola'" in result
        assert "Hola" in result
        assert "¡Hola!" in result
        assert "2026-01-01" in result
        mock_history_search.assert_called_once_with("Hola", top_k=2)

    @patch("aiion.tools.registry.history_search")
    def test_memory_search_no_results(self, mock_history_search):
        """Búsqueda sin resultados."""
        mock_history_search.return_value = []
        
        result = tool_memory_search("xyz123")
        
        assert "Sin resultados en historial" in result


class TestToolProcessManager:
    """Tests para tool_process_manager."""

    @patch("subprocess.run")
    def test_process_manager_list(self, mock_run):
        """Lista procesos top por memoria."""
        mock_result = MagicMock()
        mock_result.stdout = "USER  PID %MEM COMMAND\nuser 123 5.0 python\nuser 456 3.0 bash"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = tool_process_manager("list")
        
        assert "Top procesos RAM" in result
        assert "python" in result
        assert "bash" in result
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_process_manager_find_found(self, mock_run):
        """Busca proceso y lo encuentra."""
        mock_result = MagicMock()
        mock_result.stdout = "user 123 0.5 0:00 python script.py"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = tool_process_manager("find", "python")
        
        assert "Procesos 'python'" in result
        assert "python script.py" in result

    @patch("subprocess.run")
    def test_process_manager_find_not_found(self, mock_run):
        """Busca proceso y no lo encuentra."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = tool_process_manager("find", "inexistente")
        
        assert "No encontrado: inexistente" in result

    @patch("subprocess.run")
    def test_process_manager_kill_success(self, mock_run):
        """Mata proceso exitosamente."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = tool_process_manager("kill", "12345")
        
        assert "OK: PID 12345 terminado" in result
        mock_run.assert_called_once()
        # Verifica que se usó kill -15 (TERM)
        call_args = mock_run.call_args[0][0]
        assert "kill -15 12345" in call_args

    @patch("subprocess.run")
    def test_process_manager_kill_fail(self, mock_run):
        """Fallo al matar proceso."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"
        mock_run.return_value = mock_result
        
        result = tool_process_manager("kill", "12345")
        
        assert "Error: Permission denied" in result

    def test_process_manager_kill_self(self):
        """No permite matar el propio proceso."""
        import os
        result = tool_process_manager("kill", str(os.getpid()))
        assert "Error: No puedes matar el agente" in result

    def test_process_manager_invalid_pid(self):
        """PID inválido."""
        result = tool_process_manager("kill", "no-es-numero")
        assert "PID inválido" in result

    def test_process_manager_unknown_action(self):
        """Acción desconocida."""
        result = tool_process_manager("accion_invalida")
        assert "Acción desconocida" in result


class TestAskPermission:
    """Tests para ask_permission."""

    def test_non_dangerous_tool(self):
        """Tool no peligrosa no pide permiso."""
        # read_file no está en DANGEROUS_TOOLS
        result = ask_permission("read_file", {"path": "/tmp/test.txt"})
        assert result is True

    def test_dangerous_tool_session_allowed(self):
        """Tool peligrosa ya permitida en sesión."""
        SESSION_ALLOWED.add("write_file")
        try:
            result = ask_permission("write_file", {"path": "/tmp/test.txt", "content": "x"})
            assert result is True
        finally:
            SESSION_ALLOWED.discard("write_file")

    def test_process_manager_list_allowed(self):
        """process_manager con action=list no pide permiso."""
        result = ask_permission("process_manager", {"action": "list"})
        assert result is True

    @patch("builtins.input", side_effect=["1"])  # Permitir una vez
    @patch("builtins.print")
    def test_ask_permission_allow_once(self, mock_print, mock_input):
        """Usuario permite una vez."""
        result = ask_permission("write_file", {"path": "/tmp/test.txt", "content": "x"})
        assert result is True
        assert "write_file" not in SESSION_ALLOWED  # No se agrega a sesión

    @patch("builtins.input", side_effect=["2"])  # Permitir sesión
    @patch("builtins.print")
    def test_ask_permission_allow_session(self, mock_print, mock_input):
        """Usuario permite para toda la sesión."""
        result = ask_permission("write_file", {"path": "/tmp/test.txt", "content": "x"})
        assert result is True
        assert "write_file" in SESSION_ALLOWED
        SESSION_ALLOWED.discard("write_file")

    @patch("builtins.input", side_effect=["3"])  # Cancelar
    @patch("builtins.print")
    def test_ask_permission_cancel(self, mock_print, mock_input):
        """Usuario cancela."""
        result = ask_permission("write_file", {"path": "/tmp/test.txt", "content": "x"})
        assert result is False

    @patch("builtins.input", side_effect=["", "1"])  # Enter = permitir
    @patch("builtins.print")
    def test_ask_permission_empty_input(self, mock_print, mock_input):
        """Enter vacío = permitir."""
        result = ask_permission("write_file", {"path": "/tmp/test.txt", "content": "x"})
        assert result is True


class TestExecuteTool:
    """Tests para execute_tool."""

    def test_execute_unknown_tool(self):
        """Tool desconocida."""
        result = execute_tool("herramienta_inexistente", {})
        assert "Tool desconocida: herramienta_inexistente" in result

    @patch("aiion.tools.registry.ask_permission", return_value=False)
    def test_execute_permission_denied(self, mock_ask):
        """Permiso denegado."""
        result = execute_tool("write_file", {"path": "/tmp/test.txt", "content": "x"})
        assert "Acción cancelada" in result
        mock_ask.assert_called_once()

    @patch("aiion.tools.registry.ask_permission", return_value=True)
    def test_execute_missing_required_arg(self, mock_ask):
        """Falta argumento requerido."""
        # write_file requiere 'path'
        result = execute_tool("write_file", {"content": "solo contenido"})
        assert "Error: 'write_file' requiere 'path'" in result

    @patch("aiion.tools.registry.ask_permission", return_value=True)
    def test_execute_tool_error_handling(self, mock_ask):
        """Manejo de errores en tool."""
        # read_file con path inexistente
        result = execute_tool("read_file", {"path": "/no/existe.txt"})
        assert "Error: No existe" in result

    @patch("aiion.tools.registry.ask_permission", return_value=True)
    def test_execute_type_error(self, mock_ask):
        """Error de tipos en argumentos."""
        # read_file espera string, pasamos int
        result = execute_tool("read_file", {"path": 123})
        assert "Error args" in result or "Error" in result

    @patch("aiion.tools.registry.ask_permission", return_value=True)
    def test_execute_retry_logic(self, mock_ask):
        """Lógica de reintento tras 2 fallos sin arg requerido."""
        # Primera llamada: falta 'path'
        result1 = execute_tool("read_file", {"otro": "valor"})
        assert "Error: 'read_file' requiere 'path'" in result1
        
        # Segunda llamada: mismo error
        result2 = execute_tool("read_file", {"otro": "valor"})
        assert "STOP: 'read_file' falló sin 'path'" in result2
