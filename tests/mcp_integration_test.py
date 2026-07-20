"""Mock MCP server para probar aiion/mcp/client sin depender de blistv11."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockMCPHandler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass  # silenciar

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/mcp"):
            self._send_json(200, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "mock-mcp", "version": "0.1"},
                "capabilities": {"tools": {"listChanged": False}},
            })
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/mcp":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": {"code": -32700, "message": "bad json"}})
            return
        method = req.get("method", "")
        params = req.get("params", {})
        rid = req.get("id", 1)

        if method == "ping":
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "result": {"pong": True, "version": "11.0",
                                              "agent": "blist v11.0 'Triforce' (mock)"}})
        elif method == "initialize":
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "result": {
                                       "protocolVersion": "2024-11-05",
                                       "serverInfo": {"name": "blist-mcp", "version": "11.0"},
                                       "capabilities": {"tools": {"listChanged": False}},
                                   }})
        elif method == "tools/list":
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "result": {"tools": [
                                       {"name": "system_stats",
                                        "description": "Métricas del sistema",
                                        "inputSchema": {"type": "object", "properties": {}}},
                                       {"name": "web_search",
                                        "description": "Búsqueda web",
                                        "inputSchema": {"type": "object",
                                                        "properties": {"query": {"type": "string"}}}},
                                       {"name": "list_directory",
                                        "description": "Lista archivos",
                                        "inputSchema": {"type": "object",
                                                        "properties": {"path": {"type": "string"}}}},
                                       {"name": "run_shell_command",
                                        "description": "[BLOQUEADA]",
                                        "inputSchema": {"type": "object",
                                                        "properties": {"command": {"type": "string"}}}},
                                   ]}})
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "result": {"content": [
                                       {"type": "text",
                                        "text": f"[mock] Ejecuté {name} con {args}"}
                                   ]}})
        elif method == "status":
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "result": {"agent": "blist v11.0 'Triforce'",
                                             "model": "qwen3-coder-next:cloud",
                                             "provider": "ollama-cloud",
                                             "tools": 87,
                                             "health": 78,
                                             "battery": 64,
                                             "ram_mb": 1456,
                                             "uptime_s": 3600}})
        else:
            self._send_json(200, {"jsonrpc": "2.0", "id": rid,
                                   "error": {"code": -32601,
                                             "message": f"Método '{method}' no soportado"}})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7337
    srv = HTTPServer(("127.0.0.1", port), MockMCPHandler)
    print(f"[mock-mcp] Escuchando en http://127.0.0.1:{port}/mcp")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock-mcp] Apagando")
        srv.shutdown()


if __name__ == "__main__":
    main()
