# AIION — Arquitectura Técnica

Documento técnico para developers. Para uso general, ver [README.md](../README.md).

---

## 🏗️ Componentes

### 1. Orchestrator (`aiion/orchestrator.py`)

Bus central de sub-agentes. Componentes:

- **`AuditLog`** — registro append-only en JSONL (`orchestrator_audit.jsonl`).
- **`Orchestrator`** — singleton, registra agentes, valida capabilities, despacha tareas.
- **`TaskStatus`** — enum: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `DENIED`, `TIMEOUT`.
- **`AgentSpec`** — dataclass declarativo: `name`, `capabilities`, `handler`.

Flujo de una task:
```
                ┌──────────────────────────────────────────┐
submit()  ───►  │ 1. audit.record("task.submit")          │
                │ 2. _authorize()                         │
                │    ├─ agente existe?                    │
                │    ├─ enabled?                          │
                │    └─ capability ∈ spec?                │
                │      ├─ NO → TaskStatus.DENIED          │
                │      │       audit.record("denied")     │
                │      └─ SÍ → spec.handler(action, args) │
                │ 3. audit.record("task.done")            │
                └──────────────────────────────────────────┘
```

### 2. Sub-agentes (`aiion/subagentes/`)

3 subagentes auto-registrados vía `orchestrator_bridge`:

| Subagente | Capabilities | Propósito |
|-----------|--------------|-----------|
| `sara` | `sensor_status`, `voice_speak`, `voice_list`, `notify`, `location`, `sensor_history`, `info` | Sensores Android + voz TTS |
| `security_audit` | `audit_tail`, `audit_summary`, `tools_inventory`, `risk_scan`, `memory_check`, `recommendations` | Auditor de riesgos |
| `memory_keeper` | `stats`, `top`, `search`, `prune`, `export`, `snapshot`, `self_check` | Guardián de memoria |

Patrón `Subagente`:
```python
class Subagente:
    name: str
    capabilities: list[str]
    enabled: bool = True

    def dispatch(self, capability, args) -> dict:
        """Punto de entrada con capability-check."""
        if not self.enabled: return error("deshabilitado")
        if not self.can(capability): return error("no permitida")
        try:
            return {"ok": True, "result": self.handle(capability, args)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

### 3. Tools Registry (`aiion/tools/registry.py`)

37 tools divididas en categorías:

| Categoría | Tools | Riesgo |
|-----------|-------|--------|
| Filesystem | `read_file`, `write_file`, `list_directory`, `glob`, `grep_search`, `diff_files`, `replace` | variable |
| System | `process_manager`, `run_shell_command` | 🔴 alto |
| Sensores | `sensor_query`, `get_android_status` | 🟢 bajo |
| Voz | `hablar`, `listar_voces` | 🟢 bajo |
| Calendar | `crear_tarea`, `eliminar_tarea`, `listar_tareas` | 🟡 medio |
| Telemetry | `notificacion`, `tomar_foto`, `leer_sms`, `enviar_sms`, `hacer_llamada`, `get_gps`, `info_telefonia` | 🟠 medio |
| Memoria | `memory_search`, `memory_save` | 🟢 bajo |
| Network | `web_fetch` | 🟢 bajo |
| Code Invest | `code_invest_analyze`, `code_invest_smells`, `code_invest_complexity`, ... | 🟢 bajo |

**DANGEROUS_TOOLS** (4): `run_shell_command`, `write_file`, `replace`, `process_manager`.
Requieren `ask_permission(fn_name, fn_args)` antes de ejecutarse.

### 4. MCP Client (`aiion/mcp/client.py`)

Cliente JSON-RPC 2.0 hacia `blistv11` (Sara OS) en `127.0.0.1:7337`.

- **Cache**: TTL configurable (default 300s) para `list_tools` y `status`.
- **Blacklist**: `run_shell_command`, `process_manager`, `hacer_llamada`, `enviar_sms` (default).
- **Whitelist**: opcional, si está presente solo permite esas tools.
- **Timeout**: 30s default.

### 5. API REST (`aiion/api.py`)

`aiohttp` con:
- Auth bearer (`AIION_API_TOKEN` env var).
- Rate-limit por IP (token bucket).
- WebSocket bus (`/ws?token=...`).
- 8 endpoints: `/health`, `/status`, `/agents`, `/memory`, `/memory/search`, `/plan`, `/plan/{id}`, `/audit`.

---

## 🧪 Testing

321 tests divididos en:

| Archivo | Tests | Cobertura |
|---------|------:|-----------|
| `test_orchestrator.py` | 28 | 85% |
| `test_registry.py` | 48 | 90% |
| `test_subagentes.py` | 14 | 91% |
| `test_orchestrator_cli.py` | 27 | 99% |
| `test_subagentes_main.py` | 18 | 97% |
| `test_llm_client.py` | 23 | 100% |
| `test_mcp_client.py` | 65 | 98% |
| `test_security.py` | 20 | OWASP |
| `test_integration.py` | 9 | flujos |
| `test_load.py` | 6 | λ/μ |
| `test_e2e.py` | 9 | E2E |
| `test_db.py` | 36 | 93% |
| `test_filesystem.py` | 20 | 92% |
| `test_memory.py` | 30 | 89% |
| `test_api.py` | 24 | 63% |
| ... | | |

---

## 🔐 Modelo de Seguridad

1. **Capability-Check**: cada `(agent, action)` debe estar en `spec.capabilities`.
2. **Permission Gate**: `DANGEROUS_TOOLS` piden permiso vía `ask_permission`.
3. **MCP Blacklist**: bloquea tools críticas antes de invocar `blistv11`.
4. **Audit Log**: append-only, JSONL, cada `dispatch` deja rastro.
5. **Rate Limit**: token bucket por IP en API REST.
6. **Input Sanitization**: args de `run_shell_command` validados.

---

## 📈 Métricas (KPIs)

| KPI | Valor | Objetivo |
|-----|-------|----------|
| Tests pasando | 321 | 321 |
| Cobertura | 42% | 80% |
| Latencia p95 | < 100ms | < 500ms |
| Uptime server | 99% | 99.9% |
| Commands de audit | 100% | 100% |

Monitor: `python3 scripts/monitor.py`
