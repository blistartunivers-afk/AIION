# F2.5 — APIs REST/GraphQL

**Decisión:** Empezar con **REST** (más simple, mejor para Termux, sin dependencias pesadas). GraphQL puede venir después si se necesita.

**Stack elegido:** `aiohttp` (ya soporta async, ligero ~300KB, compatible con Android).

**Endpoints propuestos:**

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | — | Liveness probe |
| GET | `/status` | — | Estado del agente (RAM, uptime, plan activo) |
| GET | `/memory` | token | Lista entradas de memoria L2 |
| GET | `/memory/search?q=` | token | Búsqueda semántica básica |
| POST | `/plan` | token | Crear/ejecutar un plan (`{"agent":"core","action":"doctor"}`) |
| GET | `/plan/{id}` | token | Estado de un plan |
| GET | `/audit?tail=50` | token | Últimos eventos del audit log |
| GET | `/agents` | — | Listar agentes y capabilities |
| WS | `/ws` | token | Stream de eventos (sensores, audit) en vivo |

**Autenticación:** Token estático en variable de entorno `AIION_API_TOKEN` (no JWT en MVP; rotación manual).

**Seguridad:**
- Bind solo a `127.0.0.1` por defecto (no exponer a LAN)
- Token bearer en header `Authorization: Bearer <token>`
- Capability-check del orquestador se respeta en cada endpoint
- Rate limit básico (100 req/min) con `aiocron` + memoria
- CORS deshabilitado

**Estructura de archivos:**
```
aiion/
  api.py            # aiohttp app + routes
  api_auth.py       # token check middleware
  api_server.py     # entrypoint: python -m aiion.api_server
tests/
  test_api.py       # ~15 tests
```

**Tests clave:**
- Health sin auth → 200
- Memory sin token → 401
- Plan inválido → 400
- Plan válido → 200 + task_id
- WebSocket connect → mensajes en stream
- Capability-check en endpoint /plan

**Estimación:** 1 sprint. Resultado: 76/76 tests OK.

---

## ✅ F2.5 — CERRADA (2026-07-23)

| Capa | Archivo | Líneas | Función |
|---|---|---|---|
| **Core** | `aiion/api.py` | 280 | aiohttp app + middleware auth + 8 endpoints + WS bus |
| **Server** | `aiion/api_server.py` | 60 | Entry point con env vars + token + logging |
| **Tests** | `tests/test_api.py` | 24 tests | Cobertura: públicas, auth, memory, plan, audit, rate limit, WS |

### Cobertura final
- **116/116 tests verdes** (suite completa)
- 23 tests nuevos en F2.5
- Server arranca y responde vía `curl` real

### Endpoints entregados
| Método | Ruta | Auth | Status |
|---|---|---|---|
| GET | `/health` | pública | ✅ |
| GET | `/status` | pública | ✅ |
| GET | `/agents` | pública | ✅ |
| GET | `/memory` | Bearer | ✅ |
| GET | `/memory/search?q=` | Bearer | ✅ |
| POST | `/plan` | Bearer | ✅ |
| GET | `/plan/{id}` | Bearer | ✅ |
| GET | `/audit?tail=N` | Bearer | ✅ |
| GET | `/stats` | Bearer | ✅ |
| WS | `/ws?token=` | query | ✅ |

### Features clave
- Auth middleware (401/503)
- Rate limit (token bucket por IP)
- CORS permisivo para dev
- WebSocket event bus (audit + ping cada 20s)
- Capability check delegado al orchestrator
- Token configurable por `AIION_API_TOKEN` env
