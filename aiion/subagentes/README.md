# 🤖 Subagentes AIION

Sub-agentes especializados que extienden AIION con capacidades específicas.

## Claude — Planificador de Proyectos

Subagente que usa el sistema `/plan` de AIION para generar, supervisar y reportar
planes de proyectos reales de la casa.

### Proyectos definidos
| Proyecto | Descripción |
|---|---|
| `blistv12` | Nueva versión modular de blist |
| `aiion_produccion` | Llevar AIION v0.2 a producción |
| `sara_cerebro` | SARA — sistema nervioso digital |
| `ecosistema_seguridad` | BLIST Security Shield |

### Uso
```bash
# Reporte completo de salud + planes + progreso
python aiion/subagentes/claude.py reporte

# Generar plan para un proyecto
python aiion/subagentes/claude.py generar blistv12

# Ver un plan específico
python aiion/subagentes/claude.py show blistv12

# Marcar tarea
python aiion/subagentes/claude.py check blistv12 F1.1 done
```

### Características
- ✅ Genera plan con PHVA + Pareto + Teoría de Colas
- ✅ Backup automático antes de cada plan
- ✅ Lectura de avance previo
- ✅ Gráficos ASCII de progreso
- ✅ Reporte consolidado del ecosistema

---

## 🌉 blist-bridge — Cliente MCP para blistv11

Subagente que conecta AIION con **blistv11** vía **Model Context Protocol (JSON-RPC 2.0)**.
Permite a AIION ejecutar tools del ecosistema blist (sensores, voz, sistema, búsqueda web,
automatizaciones Android, etc.) desde su propio orquestador.

### Comandos
```bash
# Estado de la conexión
python aiion/subagentes/blist_bridge.py status

# Listar tools disponibles (con filtro opcional)
python aiion/subagentes/blist_bridge.py tools            # todas
python aiion/subagentes/blist_bridge.py tools sensor     # filtro por nombre

# Ejecutar una tool remota
python aiion/subagentes/blist_bridge.py call system_stats
python aiion/subagentes/blist_bridge.py call web_search '{"query":"blist v12"}'
python aiion/subagentes/blist_bridge.py call list_directory '{"path":"/sdcard"}'

# Configurar URL y API key
python aiion/subagentes/blist_bridge.py connect http://127.0.0.1:7337/mcp mi-key

# Diagnóstico completo
python aiion/subagentes/blist_bridge.py health

# Demo end-to-end
python aiion/subagentes/blist_bridge.py demo

# Sincronizar planes AIION → blist (vía write_note)
python aiion/subagentes/blist_bridge.py sync
```

### Configuración
Se guarda en `~/AIION/data/mcp/blist_config.json`:
- `url` — endpoint MCP (default `http://127.0.0.1:7337/mcp`)
- `api_key` — bearer token (si blistv11 está en modo no-Gemini)
- `timeout` — segundos por request (default 30)
- `whitelist` — tools permitidas (vacío = todas)
- `blacklist` — tools bloqueadas (default: `run_shell_command`, `process_manager`, llamadas, SMS)
- `cache_ttl_s` — TTL del cache de tools (default 300)

### Preparar blistv11 para AIION

1. **Inicia blistv11** y arranca el servidor MCP en modo IA-agente:
   ```
   /mcp_server stop
   /mcp_server start 7337 blist7337-estiven-key gemini_only=false
   ```
   (cuando añadas el flag `gemini_only` configurable — por ahora edita
   `MCP_SERVER_STATE["gemini_only"]=False` en blistv11.py)

2. **Conecta AIION**:
   ```
   python aiion/subagentes/blist_bridge.py connect http://127.0.0.1:7337/mcp blist7337-estiven-key
   ```

3. **Verifica**:
   ```
   python aiion/subagentes/blist_bridge.py demo
   ```

### Integración en AIION
AIION también expone `/mcp status|tools|call|set` directamente en su REPL
cuando importas `cmd_mcp` desde `aiion.mcp.client`.

### Características
- ✅ JSON-RPC 2.0 nativo (urllib stdlib, sin deps)
- ✅ Cache TTL de tools y status (evita spam al servidor)
- ✅ Whitelist/blacklist por tool
- ✅ Auto-fallback si blistv11 está caído
- ✅ Compatible con el cliente MCP interno de blistv11 (mismas tools que el resto)
- ✅ Sincronización bidireccional de planes

