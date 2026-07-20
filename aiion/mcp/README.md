# 🌐 aiion.mcp — Cliente MCP para blistv11

Módulo que implementa el lado cliente del **Model Context Protocol** dentro de AIION,
para conectarse con **blistv11** (que actúa como servidor MCP en `http://127.0.0.1:7337/mcp`).

## Arquitectura
```
┌──────────────────┐                    ┌──────────────────┐
│     AIION        │   JSON-RPC 2.0     │     blistv11     │
│  (cliente MCP)   │ ─────────────────► │  (servidor MCP)  │
│                  │  POST /mcp         │                  │
│  aiion/mcp/      │  Authorization     │  :7337 /mcp      │
│  ├─ client.py    │  Bearer <key>      │  ~280 tools      │
│  └─ __init__.py │                    │  whitelist IP    │
└──────────────────┘                    └──────────────────┘
```

## Uso desde código
```python
from aiion.mcp.client import get_client

cli = get_client()
cli.refresh()              # ping + invalida cache
tools = cli.list_tools()   # lista tools (con cache)
r = cli.call_tool("system_stats")
print(r)
```

## Uso desde el REPL de AIION
```
/mcp status
/mcp tools sensor
/mcp call web_search '{"query":"blist"}'
/mcp set api_key mi-key-secreta
/mcp config
```

## Métodos JSON-RPC soportados (compatibles con blistv11)
| Método       | Función                                          |
|--------------|--------------------------------------------------|
| `ping`       | Health check                                     |
| `initialize` | Handshake + capabilities                         |
| `tools/list` | Lista tools disponibles (con schema)             |
| `tools/call` | Ejecuta una tool con argumentos                   |
| `status`     | Estado del agente (batería, RAM, salud, modelo)  |

## Archivos
- `client.py` — Implementación del cliente (`MCPClient`, `cmd_mcp`)
- `__init__.py` — Exporta `MCPClient`, `get_client`, `cmd_mcp`
- `../data/mcp/blist_config.json` — Configuración persistente

## Seguridad
- **Sin dependencias externas** — solo `urllib` de stdlib
- **Blacklist por defecto**: `run_shell_command`, `process_manager`, llamadas, SMS
- **Whitelist opcional** — permite modo paranoico
- **API key opcional** — si blistv11 está en modo con auth
- **Logs de errores** en cada call fallido

## Configuración por defecto
```json
{
  "url": "http://127.0.0.1:7337/mcp",
  "api_key": "",
  "timeout": 30,
  "auto_reconnect": true,
  "cache_ttl_s": 300,
  "whitelist": [],
  "blacklist": ["run_shell_command", "process_manager", "hacer_llamada", "enviar_sms"]
}
```
