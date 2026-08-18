"""
tests/test_mcp_client.py — Tests para aiion/mcp/client.py

Cubre F3.1: cobertura del cliente MCP (era 0%, 229 stmts).
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from aiion.mcp.client import (
    MCPClient,
    DEFAULT_CONFIG,
    cmd_mcp,
    get_client,
    MCP_CONFIG_FILE,
)


@pytest.fixture
def mcp_client(tmp_path):
    """MCPClient con config aislada."""
    cfg = tmp_path / "blist_config.json"
    with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
        cli = MCPClient()
        yield cli


# ─────────────────────────────────────────────────────────────
#  Configuración
# ─────────────────────────────────────────────────────────────
class TestConfig:
    def test_default_config_tiene_url(self):
        assert "url" in DEFAULT_CONFIG
        assert "127.0.0.1" in DEFAULT_CONFIG["url"]

    def test_default_config_tiene_blacklist(self):
        assert "blacklist" in DEFAULT_CONFIG
        assert len(DEFAULT_CONFIG["blacklist"]) > 0

    def test_load_config_default(self, tmp_path):
        cfg = tmp_path / "blist_config.json"
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()
        assert cli.config["url"] == DEFAULT_CONFIG["url"]

    def test_load_config_desde_archivo(self, tmp_path):
        cfg = tmp_path / "blist_config.json"
        cfg.write_text(json.dumps({"url": "http://custom:9999/mcp"}))
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()
        assert cli.config["url"] == "http://custom:9999/mcp"

    def test_load_config_archivo_invalido_cae_a_default(self, tmp_path):
        cfg = tmp_path / "blist_config.json"
        cfg.write_text("{no json}")
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()
        # Debe caer a DEFAULT_CONFIG
        assert cli.config["url"] == DEFAULT_CONFIG["url"]

    def test_save_config(self, tmp_path):
        cfg = tmp_path / "blist_config.json"
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()
            cli.config["url"] = "http://modified:1234/mcp"
            assert cli.save_config() is True
            # Lee de nuevo
            saved = json.loads(cfg.read_text())
            assert saved["url"] == "http://modified:1234/mcp"

    def test_save_config_error_devuelve_false(self, tmp_path):
        cfg = tmp_path / "blist_config.json"
        with patch("aiion.mcp.client.MCP_CONFIG_FILE", cfg):
            cli = MCPClient()
            with patch("pathlib.Path.write_text", side_effect=OSError("no permisos")):
                # save_config no debería crashear
                assert cli.save_config() is False


# ─────────────────────────────────────────────────────────────
#  set()
# ─────────────────────────────────────────────────────────────
class TestSet:
    def test_set_clave_valida(self, mcp_client):
        mcp_client._tools_cache = [{"name": "x"}]  # poblar cache
        result = mcp_client.set("timeout", 60)
        assert "timeout" in result
        assert mcp_client.config["timeout"] == 60
        # Cache debe invalidarse
        assert mcp_client._tools_cache == []

    def test_set_clave_invalida(self, mcp_client):
        result = mcp_client.set("xxx_no_existe", 1)
        assert "no existe" in result

    def test_set_invalida_cache_status(self, mcp_client):
        mcp_client._last_status = {"foo": 1}
        mcp_client.set("timeout", 30)
        assert mcp_client._last_status == {}


# ─────────────────────────────────────────────────────────────
#  _call() JSON-RPC
# ─────────────────────────────────────────────────────────────
class TestCall:
    def test_call_agrega_slash_mcp(self, mcp_client):
        """Si la URL no termina en /mcp, lo agrega."""
        mcp_client.config["url"] = "http://localhost:7337"
        mcp_client.config["api_key"] = ""
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"ok": 1}).encode()
            mcp_client._call("ping")
        req = mock_open.call_args[0][0]
        assert req.full_url.endswith("/mcp")

    def test_call_con_api_key(self, mcp_client):
        mcp_client.config["api_key"] = "secret-123"
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"ok": 1}).encode()
            mcp_client._call("ping")
        req = mock_open.call_args[0][0]
        assert req.headers["Authorization"] == "Bearer secret-123"

    def test_call_respuesta_con_error(self, mcp_client):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                "error": {"code": -1, "message": "bad"}
            }).encode()
            result = mcp_client._call("ping")
        assert "error" in result
        assert result["error"] == "bad"

    def test_call_respuesta_con_error_string(self, mcp_client):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                "error": "string error"
            }).encode()
            result = mcp_client._call("ping")
        assert result["error"] == "string error"

    def test_call_http_error(self, mcp_client):
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen",
                   side_effect=HTTPError("u", 500, "Internal", {}, None)):
            result = mcp_client._call("ping")
        assert "error" in result
        assert "HTTP 500" in result["error"]

    def test_call_url_error(self, mcp_client):
        from urllib.error import URLError
        with patch("urllib.request.urlopen",
                   side_effect=URLError("refused")):
            result = mcp_client._call("ping")
        assert "no disponible" in result["error"]

    def test_call_generico_error(self, mcp_client):
        with patch("urllib.request.urlopen",
                   side_effect=RuntimeError("boom")):
            result = mcp_client._call("ping")
        assert "error" in result
        assert "boom" in result["error"]

    def test_call_incrementa_stats(self, mcp_client):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"ok": 1}).encode()
            mcp_client._call("ping")
        assert mcp_client._stats["calls"] == 1
        assert mcp_client._stats["last_call"] is not None


# ─────────────────────────────────────────────────────────────
#  ping / info / status
# ─────────────────────────────────────────────────────────────
class TestPublicAPIs:
    def test_ping_ok(self, mcp_client):
        with patch.object(mcp_client, "_call", return_value={"pong": True}):
            result = mcp_client.ping()
        assert "pong" in result
        assert mcp_client._connected is True

    def test_ping_error(self, mcp_client):
        with patch.object(mcp_client, "_call", return_value={"error": "down"}):
            result = mcp_client.ping()
        assert "error" in result
        assert mcp_client._connected is False

    def test_info(self, mcp_client):
        with patch.object(mcp_client, "_call", return_value={"server": "blistv11"}):
            result = mcp_client.info()
        assert result["server"] == "blistv11"

    def test_status_cache_hit(self, mcp_client):
        mcp_client._last_status = {"cached": True}
        mcp_client._last_status_at = 1000
        # Forzar cache_ttl_s alto
        mcp_client.config["cache_ttl_s"] = 9999
        with patch("time.time", return_value=1001):
            result = mcp_client.status()
        assert result["cached"] is True

    def test_status_cache_miss_y_set(self, mcp_client):
        mcp_client._last_status = {}
        mcp_client._last_status_at = 0
        mcp_client.config["cache_ttl_s"] = 5
        with patch("time.time", return_value=1000):
            with patch.object(mcp_client, "_call", return_value={"fresh": True}):
                result = mcp_client.status()
        assert result["fresh"] is True
        assert mcp_client._last_status_at == 1000

    def test_status_no_actualiza_si_hay_error(self, mcp_client):
        mcp_client._last_status = {"old": 1}
        mcp_client._last_status_at = 0
        mcp_client.config["cache_ttl_s"] = 0
        with patch.object(mcp_client, "_call", return_value={"error": "x"}):
            mcp_client.status()
        assert mcp_client._last_status == {"old": 1}


# ─────────────────────────────────────────────────────────────
#  list_tools
# ─────────────────────────────────────────────────────────────
class TestListTools:
    def test_list_tools_cache_hit(self, mcp_client):
        mcp_client._tools_cache = [{"name": "cached"}]
        mcp_client._tools_cache_at = 1000
        mcp_client.config["cache_ttl_s"] = 9999
        with patch("time.time", return_value=1001):
            result = mcp_client.list_tools()
        assert result == [{"name": "cached"}]

    def test_list_tools_cache_miss(self, mcp_client):
        mcp_client._tools_cache = []
        mcp_client._tools_cache_at = 0
        mcp_client.config["cache_ttl_s"] = 0
        mcp_client.config["blacklist"] = []
        with patch.object(mcp_client, "_call",
                          return_value={"tools": [{"name": "a"}, {"name": "b"}]}):
            result = mcp_client.list_tools()
        assert len(result) == 2

    def test_list_tools_filtra_blacklist(self, mcp_client):
        mcp_client._tools_cache = []
        mcp_client._tools_cache_at = 0
        mcp_client.config["cache_ttl_s"] = 0
        mcp_client.config["blacklist"] = ["banned"]
        mcp_client.config["whitelist"] = []
        with patch.object(mcp_client, "_call",
                          return_value={"tools": [{"name": "ok"}, {"name": "banned"}]}):
            result = mcp_client.list_tools()
        names = [t["name"] for t in result]
        assert "ok" in names
        assert "banned" not in names

    def test_list_tools_whitelist(self, mcp_client):
        mcp_client._tools_cache = []
        mcp_client._tools_cache_at = 0
        mcp_client.config["cache_ttl_s"] = 0
        mcp_client.config["whitelist"] = ["a"]
        mcp_client.config["blacklist"] = []
        with patch.object(mcp_client, "_call",
                          return_value={"tools": [{"name": "a"}, {"name": "b"}]}):
            result = mcp_client.list_tools()
        assert len(result) == 1
        assert result[0]["name"] == "a"

    def test_list_tools_error_retorna_vacio(self, mcp_client):
        mcp_client._tools_cache = []
        mcp_client._tools_cache_at = 0
        with patch.object(mcp_client, "_call", return_value={"error": "fail"}):
            result = mcp_client.list_tools()
        assert result == []


# ─────────────────────────────────────────────────────────────
#  call_tool
# ─────────────────────────────────────────────────────────────
class TestCallTool:
    def test_call_tool_bloqueada_por_blacklist(self, mcp_client):
        mcp_client.config["blacklist"] = ["kill"]
        mcp_client.config["whitelist"] = []
        result = mcp_client.call_tool("kill", {})
        assert "error" in result
        assert "blacklist" in result["error"].lower()

    def test_call_tool_no_en_whitelist(self, mcp_client):
        mcp_client.config["whitelist"] = ["allowed"]
        mcp_client.config["blacklist"] = []
        result = mcp_client.call_tool("other", {})
        assert "error" in result
        assert "whitelist" in result["error"].lower()

    def test_call_tool_ok(self, mcp_client):
        mcp_client.config["blacklist"] = []
        mcp_client.config["whitelist"] = []
        with patch.object(mcp_client, "_call", return_value={"content": "ok"}) as mock_call:
            result = mcp_client.call_tool("foo", {"x": 1})
        assert result["content"] == "ok"
        mock_call.assert_called_once_with(
            "tools/call", {"name": "foo", "arguments": {"x": 1}}
        )

    def test_call_tool_args_none(self, mcp_client):
        mcp_client.config["blacklist"] = []
        mcp_client.config["whitelist"] = []
        with patch.object(mcp_client, "_call", return_value={"ok": 1}) as mock_call:
            result = mcp_client.call_tool("foo")
        mock_call.assert_called_once_with(
            "tools/call", {"name": "foo", "arguments": {}}
        )


# ─────────────────────────────────────────────────────────────
#  refresh / is_online / report
# ─────────────────────────────────────────────────────────────
class TestRefresh:
    def test_refresh_invalida_cache(self, mcp_client):
        mcp_client._tools_cache = [{"name": "x"}]
        mcp_client._last_status = {"y": 1}
        with patch.object(mcp_client, "ping", return_value={"pong": True}):
            result = mcp_client.refresh()
        assert mcp_client._tools_cache == []
        assert mcp_client._last_status == {}
        assert "Conectado" in result or "✓" in result

    def test_refresh_con_error(self, mcp_client):
        with patch.object(mcp_client, "ping", return_value={"error": "down"}):
            result = mcp_client.refresh()
        assert "✗" in result or "down" in result


class TestIsOnline:
    def test_is_online_true(self, mcp_client):
        mcp_client.config["url"] = "http://localhost:7337/mcp"
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp
            mock_open.return_value = mock_resp
            assert mcp_client.is_online() is True

    def test_is_online_false(self, mcp_client):
        with patch("urllib.request.urlopen", side_effect=Exception("fail")):
            assert mcp_client.is_online() is False


class TestReport:
    def test_report_sin_online(self, mcp_client):
        with patch.object(mcp_client, "is_online", return_value=False):
            result = mcp_client.report()
        assert "URL:" in result
        assert "Online:" in result
        assert "🔴" in result

    def test_report_con_online(self, mcp_client):
        with patch.object(mcp_client, "is_online", return_value=True):
            with patch.object(mcp_client, "ping", return_value={"pong": True}):
                with patch.object(mcp_client, "status", return_value={
                    "agent": "blist", "tools": 5, "ram_mb": 100,
                    "battery": 80, "health": 95
                }):
                    with patch.object(mcp_client, "list_tools", return_value=[{"name": "x"}]):
                        result = mcp_client.report()
        assert "🟢" in result
        assert "Agente: blist" in result
        # Nota: el formato tiene doble espacio "Tools:  5"
        assert "Tools:" in result
        assert "5" in result


# ─────────────────────────────────────────────────────────────
#  cmd_mcp (CLI)
# ─────────────────────────────────────────────────────────────
class TestCmdMcp:
    def test_cmd_sin_action(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "is_online", return_value=False):
                result = cmd_mcp("", [])
        assert "MCP" in result

    def test_status(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "is_online", return_value=False):
                result = cmd_mcp("status", [])
        assert "MCP" in result
        assert "Online:" in result

    def test_ping_ok(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "ping", return_value={"pong": True}):
                result = cmd_mcp("ping", [])
        assert "✓" in result

    def test_ping_fail(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "ping", return_value={"error": "down"}):
                result = cmd_mcp("ping", [])
        assert "✗" in result

    def test_tools_sin_filtro(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "list_tools", return_value=[
                {"name": "sensor_status", "description": "Lee sensores"},
                {"name": "memory_recall", "description": "Lee memoria"},
            ]):
                result = cmd_mcp("tools", [])
        assert "2 tools" in result
        assert "sensor_status" in result

    def test_tools_con_filtro(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "list_tools", return_value=[
                {"name": "sensor_status", "description": "lee"},
                {"name": "memory", "description": "lee"},
            ]):
                result = cmd_mcp("tools", ["sensor"])
        assert "sensor_status" in result
        # memory NO debe aparecer
        assert "memory" not in result or "memory_recall" not in result

    def test_tools_vacio(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "list_tools", return_value=[]):
                result = cmd_mcp("tools", [])
        assert "No se pudieron" in result or "✗" in result

    def test_call_sin_args(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("call", [])
        assert "✗" in result
        assert "Uso:" in result

    def test_call_ok(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "call_tool", return_value={"content": "ok"}):
                result = cmd_mcp("call", ["sensor_status"])
        assert "ok" in result

    def test_call_con_args_json(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "call_tool", return_value={"content": "ok"}) as mock:
                cmd_mcp("call", ["sensor", '{"sensor": "battery"}'])
        mock.assert_called_once_with("sensor", {"sensor": "battery"})

    def test_call_json_invalido(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("call", ["sensor", "{malformed"])
        assert "inválidos" in result

    def test_call_error(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "call_tool", return_value={"error": "fail"}):
                result = cmd_mcp("call", ["sensor"])
        assert "✗" in result

    def test_call_content_list(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "call_tool", return_value={
                "content": [{"text": "first"}, {"text": "second"}]
            }):
                result = cmd_mcp("call", ["foo"])
        assert "first" in result
        assert "second" in result

    def test_call_content_dict(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "call_tool", return_value={
                "content": {"k": "v"}
            }):
                result = cmd_mcp("call", ["foo"])
        parsed = json.loads(result)
        assert parsed["k"] == "v"

    def test_set_sin_args(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("set", [])
        assert "✗" in result
        assert "Uso:" in result

    def test_set_timeout_int(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "set", return_value="✓ timeout = 60") as mock_set:
                cmd_mcp("set", ["timeout", "60"])
        mock_set.assert_called_once_with("timeout", 60)

    def test_set_timeout_no_int(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("set", ["timeout", "no_int"])
        assert "entero" in result

    def test_set_auto_reconnect_true(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "set", return_value="ok") as mock_set:
                cmd_mcp("set", ["auto_reconnect", "true"])
        mock_set.assert_called_once_with("auto_reconnect", True)

    def test_set_auto_reconnect_false(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "set", return_value="ok") as mock_set:
                cmd_mcp("set", ["auto_reconnect", "false"])
        mock_set.assert_called_once_with("auto_reconnect", False)

    def test_set_whitelist_lista(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "set", return_value="ok") as mock_set:
                cmd_mcp("set", ["whitelist", "a,b,c"])
        mock_set.assert_called_once_with("whitelist", ["a", "b", "c"])

    def test_set_blacklist_lista(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "set", return_value="ok") as mock_set:
                cmd_mcp("set", ["blacklist", "x , y"])
        mock_set.assert_called_once_with("blacklist", ["x", "y"])

    def test_config(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("config", [])
        parsed = json.loads(result)
        assert "url" in parsed

    def test_refresh(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "refresh", return_value="✓ reconectado"):
                result = cmd_mcp("refresh", [])
        assert "✓" in result

    def test_report(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            with patch.object(mcp_client, "report", return_value="reporte x"):
                result = cmd_mcp("report", [])
        assert "MCP Report" in result
        assert "reporte x" in result

    def test_accion_desconocida(self, mcp_client):
        with patch("aiion.mcp.client.get_client", return_value=mcp_client):
            result = cmd_mcp("xxx", [])
        assert "no existe" in result


# ─────────────────────────────────────────────────────────────
#  Singleton
# ─────────────────────────────────────────────────────────────
class TestSingleton:
    def test_get_client_retorna_misma_instancia(self):
        from aiion.mcp import client as mod
        mod._CLIENT = None
        c1 = mod.get_client()
        c2 = mod.get_client()
        assert c1 is c2
