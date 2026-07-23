# F2.7 — Integración end-to-end (Subagentes ↔ Orchestrator ↔ API ↔ CLI)

## 🎯 Objetivo
Cerrar el ciclo de comunicación entre las 4 capas actuales para que cualquier
invocación pueda viajar de UI/API → orchestrator → subagente y devolver resultado
con la misma forma (mismo envelope JSON), sin código duplicado y sin estado
divergente entre módulos.

## 🧩 Estado actual (desconexiones detectadas)

| Capa | Estado | Problema |
|------|--------|----------|
| **Subagentes** | Aislados, solo accesibles vía `python -m aiion.subagentes` o `OrchestratorBridge` | El bridge solo inyecta refs; el orchestrator no sabe ejecutar capabilities de subagentes |
| **Orchestrator** | `dispatch(action)` valida capability contra su `REGISTRY` de tools (no subagentes) | `dispatch("sara.sensor_status", ...)` falla — la capability no está en su registry |
| **API** | `POST /plan` llama `orchestrator.dispatch(action)` | Si la acción es de un subagente, da 400 capability_not_allowed |
| **CLI** | `python -m aiion.orchestrator_cli` solo conoce actions del orchestrator | No hay forma de invocar subagentes desde el CLI unificado |

## 📦 Entregables (5 archivos)

| # | Archivo | Función |
|---|---------|---------|
| 1 | `aiion/integration.py` | Nuevo — Router unificado: `dispatch_unified(target, capability, args)` con prefijo `subagente.capability` |
| 2 | `aiion/orchestrator.py` | Modificar — `dispatch()` acepta target con formato `name.cap` y delega al router |
| 3 | `aiion/api.py` | Modificar — `/plan` permite invocar subagentes via `{"target": "sara", "capability": "sensor_status"}` |
| 4 | `aiion/orchestrator_cli.py` | Modificar — comando `run` acepta `--target sara --capability sensor_status` |
| 5 | `tests/test_integration.py` | Nuevo — 12 tests E2E del flujo completo |

## 🔁 Contrato unificado

```python
# Formato canónico en todas las capas
target:      str   # "orchestrator" | "sara" | "security_audit" | "memory_keeper"
             # (también se acepta "<name>.<capability>" como atajo)
capability:  str   # "doctor" | "sensor_status" | "stats" | ...
args:        dict  # parámetros

# Response envelope (mismo en todas las capas)
{
  "ok": bool,
  "target": str,
  "capability": str,
  "result": Any | None,
  "error": str | None,
  "duration_ms": float
}
```

## 🧪 Tests (12)

1. `test_router_resolves_orchestrator_capability`
2. `test_router_resolves_subagente_capability`
3. `test_router_resolves_dotted_target`
4. `test_router_unknown_target`
5. `test_router_orchestrator_denied_capability`
6. `test_router_subagente_denied_capability`
7. `test_orchestrator_dispatch_delegates_to_router`
8. `test_api_plan_endpoint_invokes_subagente`
9. `test_api_plan_endpoint_invokes_orchestrator`
10. `test_api_plan_endpoint_unknown_target_404`
11. `test_cli_run_invokes_subagente`
12. `test_integration_full_chain_logs_audit`

## 📊 Métricas de éxito
- [ ] 12/12 tests nuevos verdes
- [ ] 144/144 (suite total previa) sigue verde
- [ ] `curl POST /plan {"target":"sara","capability":"info"}` → 200 + envelope
- [ ] `python -m aiion.orchestrator_cli run --target memory_keeper --capability stats` → JSON
- [ ] Audit log registra TODAS las invocaciones (sub o main)

## ⏱️ Estimación: 1 sesión.
