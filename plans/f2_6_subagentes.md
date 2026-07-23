# F2.6 — Sub-agentes (Subagentes)

## 🎯 Objetivo
Crear un framework de sub-agentes que:
1. Encapsulen capabilities de dominio (sensores, auditoría, memoria).
2. Se auto-registren en un registry global.
3. Sean invocables desde CLI, desde el orchestrator, o desde la API REST.
4. Mantengan retrocompatibilidad con `claude.py` y `blist_bridge.py` legacy.

## 📦 Entregables (8 archivos)

| # | Archivo | Líneas | Función |
|---|---------|-------:|---------|
| 1 | `aiion/subagentes/base.py` | ~140 | Clase `Subagente` + `@subagente` + `REGISTRY` + `dispatch()` |
| 2 | `aiion/subagentes/sara_cerebro.py` | ~135 | SARA — sensores + voz + notif (7 caps) |
| 3 | `aiion/subagentes/security_audit.py` | ~180 | Auditor de seguridad (6 caps) |
| 4 | `aiion/subagentes/memory_keeper.py` | ~190 | Guardián de memoria (7 caps) |
| 5 | `aiion/subagentes/orchestrator_bridge.py` | ~80 | Inyecta subagentes en `aiion.orchestrator` |
| 6 | `aiion/subagentes/__init__.py` | ~20 | Re-exports |
| 7 | `aiion/subagentes/__main__.py` | ~80 | CLI `python -m aiion.subagentes {list,describe,call}` |
| 8 | `tests/test_subagentes.py` | ~180 | 14 tests pytest |

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│              aiion.subagentes                            │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  sara       │  │ security_aud │  │ memory_keeper│    │
│  │  (7 caps)   │  │  (6 caps)    │  │  (7 caps)    │    │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘    │
│         └────────────────┴──────────────────┘            │
│                         ↓                                │
│                  REGISTRY[name → Subagente]              │
│                         ↓                                │
│             orchestrator_bridge.register_all()           │
│                         ↓                                │
│             aiion.orchestrator.REGISTRY                  │
│                         ↓                                │
│      CLI __main__    API /agents    UI TUI               │
└──────────────────────────────────────────────────────────┘
```

## 🧱 Clase `Subagente`

```python
class Subagente:
    name: str
    description: str
    capabilities: list[str]
    version: str = "0.1"
    enabled: bool = True

    def can(self, capability) -> bool       # capability-check
    def dispatch(self, cap, args) -> dict   # entry point con manejo de errores
    def describe(self) -> dict              # metadata serializable
    def handle(self, cap, args) -> dict     # ← subclases override

# Decorator: auto-registra al import
@subagente
class SaraCerebro(Subagente):
    name = "sara"
    capabilities = ["sensor_status", "voice_speak", ...]
    def handle(self, cap, args): ...
```

## 🔁 Dispatch contract

```json
// request
{ "name": "memory_keeper", "capability": "stats", "args": {} }

// response
{
  "ok": true,
  "subagente": "memory_keeper",
  "capability": "stats",
  "result": { "memory_md": {...}, "history": {...} },
  "error": null
}

// on error
{ "ok": false, "subagente": "...", "capability": "...",
  "result": null, "error": "mensaje" }
```

## 📊 Subagentes implementados

### 1. `sara` — Sistema nervioso digital
- `sensor_status` — lee get_android_status (battery/wifi/system/location)
- `sensor_history` — últimos N puntos de un sensor
- `voice_speak` — TTS con voz opcional
- `voice_list` — lista voces disponibles
- `notify` — notificación Android
- `location` — GPS actual
- `info` — metadata del subagente

### 2. `security_audit` — Auditor de seguridad
- `audit_tail` — últimos N eventos del audit log
- `audit_summary` — resumen por status
- `tools_inventory` — todas las tools con risk-classification
- `risk_scan` — identifica tools de alto/medio riesgo + score
- `memory_check` — verifica cifrado de memoria L2/L3
- `recommendations` — plan de remediación

### 3. `memory_keeper` — Guardián de memoria
- `stats` — métricas de aiion_memory.md + history
- `top` — top N entries por score
- `search` — búsqueda en history
- `prune` — dry-run de poda (N días)
- `export` — backup a JSON
- `snapshot` — copia timestamped a data/backups/
- `self_check` — verifica integridad

## 🖥️ CLI

```bash
$ python -m aiion.subagentes list
📦 3 subagente(s) registrado(s):
  • sara            v0.1  —  SARA — sistema nervioso digital (...)
  • security_audit  v0.1  —  Auditor de seguridad (...)
  • memory_keeper   v0.1  —  Guardián de memoria (...)

$ python -m aiion.subagentes call memory_keeper stats
{"ok": true, "subagente": "memory_keeper", "capability": "stats", ...}

$ python -m aiion.subagentes call sara sensor_status '{"sensor":"battery"}'
```

## 🧪 Tests (14)

1. `test_registry_creates_instance`
2. `test_registry_duplicate_name_allowed`
3. `test_get_subagente_not_found`
4. `test_dispatch_capability_not_allowed`
5. `test_dispatch_handler_exception`
6. `test_dispatch_ok`
7. `test_subagente_disabled`
8. `test_describe_format`
9. `test_list_subagentes_only_enabled`
10. `test_sara_info_capability`
11. `test_sara_sensor_status_calls_tool`
12. `test_security_audit_risk_score_in_range`
13. `test_memory_keeper_stats_shape`
14. `test_memory_keeper_self_check_ok`

## 🛡️ Compatibilidad
- `claude.py` y `blist_bridge.py` (legacy CLIs) siguen funcionando sin cambios.
- El bridge solo inyecta los 3 subagentes nuevos en el orchestrator.
- Los tests existentes (116) deben seguir pasando 100%.

## ✅ Criterios de cierre
- [x] 3 subagentes + base + bridge + CLI = 7 archivos Python
- [x] 14 tests nuevos
- [x] Suite total 130/130 verdes
- [x] CLI `python -m aiion.subagentes` funcional
- [x] Retrocompatibilidad con legacy
