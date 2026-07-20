"""
aiion/mcp/client.py — Cliente MCP de AIION para conectar con blistv11

Soporta JSON-RPC 2.0 con auto-reconexión, cache de tools y whitelist.
Protocolo compatible con el servidor MCP de blistv11 (puerto 7337).
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from aiion.config import AIION_HOME

# ── Configuración ────────────────────────────────────────────────────────────
MCP_DIR = AIION_HOME / "data" / "mcp"
MCP_DIR.mkdir(parents=True, exist_ok=True)
MCP_CONFIG_FILE = MCP_DIR / "blist_config.json"

DEFAULT_CONFIG = {
    "url":           "http://127.0.0.1:7337/mcp",
    "api_key":       "",
    "timeout":       30,
    "auto_reconnect": True,
    "cache_ttl_s":   300,
    "whitelist":     [],   # tools permitidas (vacío = todas)
    "blacklist":     ["run_shell_command", "process_manager",
                      "hacer_llamada", "enviar_sms"],
}


class MCPClient:
    """Cliente MCP JSON-RPC 2.0 compatible con blistv11."""

    def __init__(self):
        self.config = self._load_config()
        self._tools_cache: list = []
        self._tools_cache_at: float = 0
        self._last_status: dict = {}
        self._last_status_at: float = 0
        self._connected: bool = False
        self._stats = {"calls": 0, "errors": 0, "last_call": None}

    def _load_config(self) -> dict:
        if MCP_CONFIG_FILE.exists():
            try:
                return {**DEFAULT_CONFIG, **json.loads(MCP_CONFIG_FILE.read_text())}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def save_config(self) -> bool:
        """Guarda la configuración actual en disco."""
        try:
            MCP_CONFIG_FILE.write_text(json.dumps(self.config, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"  ✗ Error guardando config MCP: {e}")
            return False

    def set(self, key: str, value: Any) -> str:
        """Actualiza un valor de configuración."""
        if key not in DEFAULT_CONFIG:
            return f"  ✗ Clave '{key}' no existe. Válidas: {list(DEFAULT_CONFIG.keys())}"
        self.config[key] = value
        self.save_config()
        # Invalidar cache
        self._tools_cache = []
        self._last_status = {}
        return f"  ✓ MCP.{key} = {value}"

    def _call(self, method: str, params: Optional[dict] = None,
              timeout: int = 0) -> dict:
        """Realiza una llamada JSON-RPC 2.0 al servidor MCP."""
        url = self.config["url"].rstrip("/")
        # blistv11 acepta POST a /mcp
        if not url.endswith("/mcp"):
            url = url + "/mcp"

        payload = json.dumps({
            "jsonrpc": "2.0",
            "id":      int(time.time() * 1000) % 100000,
            "method":  method,
            "params":  params or {},
        }).encode()

        headers = {"Content-Type": "application/json"}
        if self.config.get("api_key"):
            headers["Authorization"] = f"Bearer {self.config['api_key']}"

        to = timeout or self.config.get("timeout", 30)
        self._stats["calls"] += 1
        self._stats["last_call"] = datetime.now().isoformat()

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=to) as r:
                body = r.read()
            data = json.loads(body)
            self._connected = True
            if "error" in data:
                err = data["error"]
                self._stats["errors"] += 1
                if isinstance(err, dict):
                    return {"error": err.get("message", str(err))}
                return {"error": str(err)}
            return data.get("result", data)
        except urllib.error.HTTPError as e:
            self._connected = False
            self._stats["errors"] += 1
            try:
                body = e.read().decode("utf-8", "ignore")
                return {"error": f"HTTP {e.code}: {body[:200]}"}
            except Exception:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            self._connected = False
            self._stats["errors"] += 1
            return {"error": f"Servidor MCP no disponible: {e.reason}"}
        except Exception as e:
            self._connected = False
            self._stats["errors"] += 1
            return {"error": f"Error: {e}"}

    # ── API pública ───────────────────────────────────────────────────────────

    def ping(self) -> dict:
        """Verifica que el servidor MCP responde."""
        result = self._call("ping")
        if "error" not in result:
            self._connected = True
        return result

    def info(self) -> dict:
        """Información del servidor (protocolo, versión, capabilities)."""
        return self._call("initialize")

    def status(self, use_cache: bool = True) -> dict:
        """Estado del agente blist (batería, RAM, salud, modelo)."""
        if use_cache and (time.time() - self._last_status_at) < self.config["cache_ttl_s"]:
            return self._last_status
        s = self._call("status")
        if "error" not in s:
            self._last_status = s
            self._last_status_at = time.time()
        return s

    def list_tools(self, use_cache: bool = True) -> list:
        """Lista todas las tools expuestas (con cache TTL)."""
        if use_cache and self._tools_cache and (time.time() - self._tools_cache_at) < self.config["cache_ttl_s"]:
            return self._tools_cache
        result = self._call("tools/list")
        if "error" in result:
            return []
        tools = result.get("tools", [])
        # Filtrar blacklist
        bl = set(self.config.get("blacklist", []))
        wl = self.config.get("whitelist", [])
        if wl:
            tools = [t for t in tools if t.get("name") in wl]
        else:
            tools = [t for t in tools if t.get("name") not in bl]
        self._tools_cache = tools
        self._tools_cache_at = time.time()
        return tools

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Ejecuta una tool remota en blistv11."""
        bl = set(self.config.get("blacklist", []))
        wl = self.config.get("whitelist", [])
        if name in bl:
            return {"error": f"Tool '{name}' bloqueada por AIION (blacklist)"}
        if wl and name not in wl:
            return {"error": f"Tool '{name}' no está en whitelist"}
        result = self._call("tools/call", {"name": name, "arguments": arguments or {}})
        return result

    def refresh(self) -> str:
        """Invalida cache y reconecta."""
        self._tools_cache = []
        self._last_status = {}
        ping = self.ping()
        if "error" in ping:
            return f"  ✗ {ping['error']}"
        return f"  ✓ Conectado a {self.config['url']} — {ping}"

    # ── Diagnóstico ───────────────────────────────────────────────────────────

    def is_online(self) -> bool:
        """¿Está el servidor MCP disponible?"""
        try:
            url = self.config["url"].rstrip("/").replace("/mcp", "/")
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def report(self) -> str:
        """Genera un reporte en texto del estado MCP."""
        lines = []
        lines.append(f"  URL:    {self.config['url']}")
        lines.append(f"  Key:    {'✓ configurada' if self.config.get('api_key') else '— sin auth'}")
        online = self.is_online()
        lines.append(f"  Online: {'🟢 sí' if online else '🔴 no'}")
        if online:
            ping = self.ping()
            if "error" not in ping:
                lines.append(f"  Ping:   ✓ {ping}")
            status = self.status(use_cache=False)
            if "error" not in status:
                lines.append(f"  Agente: {status.get('agent','?')}")
                lines.append(f"  Tools:  {status.get('tools','?')}")
                lines.append(f"  RAM:    {status.get('ram_mb','?')} MB")
                lines.append(f"  Batería:{status.get('battery','?')}%")
                lines.append(f"  Health: {status.get('health','?')}/100")
            tools = self.list_tools(use_cache=False)
            lines.append(f"  Tools disponibles: {len(tools)}")
        lines.append(f"  Stats:  {self._stats['calls']} calls, {self._stats['errors']} errors")
        return "\n".join(lines)


# Singleton
_CLIENT: Optional[MCPClient] = None
def get_client() -> MCPClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = MCPClient()
    return _CLIENT


# ── Comandos CLI (para integrar en aiion/core.py) ───────────────────────────

def cmd_mcp(action: str, args: list) -> str:
    """
    Comando /mcp para AIION.
    Acciones:
      status              → estado de la conexión
      ping                → prueba conexión
      tools [filtro]      → lista tools (opcional: filtro por nombre)
      call <tool> <json>  → ejecuta una tool remota
      set <key> <valor>   → cambia config (url, api_key, timeout, etc)
      config              → muestra config actual
      refresh             → invalida cache y reconecta
      report              → reporte completo
    """
    cli = get_client()
    if not action:
        return cmd_mcp("status", [])

    if action == "status":
        online = cli.is_online()
        status = cli.status() if online else {}
        lines = [
            f"🌐 MCP — Model Context Protocol",
            f"  URL:    {cli.config['url']}",
            f"  Online: {'🟢 sí' if online else '🔴 no'}",
        ]
        if online and status:
            lines.append(f"  Agente: {status.get('agent','?')}")
            lines.append(f"  Tools:  {status.get('tools','?')}")
            lines.append(f"  Health: {status.get('health','?')}/100")
        return "\n".join(lines)

    elif action == "ping":
        r = cli.ping()
        return f"{'✓' if 'error' not in r else '✗'} {r}"

    elif action == "tools":
        filtro = args[0] if args else ""
        tools = cli.list_tools(use_cache=False)
        if not tools:
            return "  ✗ No se pudieron listar tools (¿blistv11 activo?)"
        out = [f"🔧 {len(tools)} tools disponibles en blistv11:"]
        for t in tools:
            n = t.get("name", "?")
            if filtro and filtro.lower() not in n.lower():
                continue
            d = t.get("description", "")[:70]
            out.append(f"  • {n:30s} — {d}")
        return "\n".join(out)

    elif action == "call":
        if len(args) < 1:
            return "  ✗ Uso: /mcp call <tool> [json_args]"
        tool_name = args[0]
        tool_args = {}
        if len(args) >= 2:
            try:
                tool_args = json.loads(" ".join(args[1:]))
            except json.JSONDecodeError as e:
                return f"  ✗ Args inválidos: {e}"
        r = cli.call_tool(tool_name, tool_args)
        if "error" in r:
            return f"  ✗ {r['error']}"
        content = r.get("content", r)
        if isinstance(content, list):
            return "\n".join(c.get("text", str(c)) for c in content)
        return json.dumps(content, indent=2, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)

    elif action == "set":
        if len(args) < 2:
            return f"  ✗ Uso: /mcp set <key> <valor>\n  Claves: {list(DEFAULT_CONFIG.keys())}"
        key = args[0]
        val = " ".join(args[1:])
        # Cast según tipo
        if key == "timeout" or key == "cache_ttl_s":
            try: val = int(val)
            except: return "  ✗ Debe ser entero"
        elif key == "auto_reconnect":
            val = val.lower() in ("true", "1", "yes", "si", "sí")
        elif key in ("whitelist", "blacklist"):
            val = [x.strip() for x in val.split(",") if x.strip()]
        return cli.set(key, val)

    elif action == "config":
        return json.dumps(cli.config, indent=2, ensure_ascii=False)

    elif action == "refresh":
        return cli.refresh()

    elif action == "report":
        return "🌐 MCP Report\n" + cli.report()

    else:
        return f"  ✗ Acción '{action}' no existe. Usa: status, ping, tools, call, set, config, refresh, report"
