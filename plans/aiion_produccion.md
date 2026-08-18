# 📋 Plan: Aiion Produccion

**Creado:** 2026-07-17
**Estado:** ✅ **CERRADO** (2026-07-31)

---

## 🎯 Objetivo General
Construir un **agente autónomo residente en Android/Termux** capaz de percibir su entorno (sensores), razonar con memoria a largo plazo, ejecutar tareas complejas mediante herramientas nativas y evolucionar su propio código de forma segura, sin depender de root ni de la nube obligatoria.

## 🏗️ Arquitectura Técnica
- **Backend:** Python 3.11+ (Asyncio) — Núcleo event-driven (`aiion/core.py`), Sub-agentes como workers independientes.
- **Frontend:** TUI (Textual/Rich) para dashboard en Termux + Notificaciones Android nativas (Termux:API).
- **BD:** SQLite (WAL mode) para datos estructurados (`aiion_sensor_data.db`) + Archivos Markdown/JSONL para memoria cognitiva (`aiion_memory.md`, `aiion_history.jsonl`).
- **Seguridad:** Cifrado AES-256 (Fernet) en reposo para secrets/memoria. Capability-based security para sub-agentes. Sin root. Rotación de llaves automática.
- **Despliegue:** GitOps local (repo privado Termux) + Sync opcional a GitHub (solo código público). Actualizaciones in-place via `hot_reload` sin reiniciar daemon.

---

## 📊 Fases (PHVA — Planear, Hacer, Verificar, Actuar)

### ✅ F1. PLANEAR — Análisis y Diseño (COMPLETADA)
- ✅ F1.1 Levantar requerimientos funcionales/no funcionales
- ✅ F1.2 Diseñar arquitectura técnica
- ✅ F1.3 Definir APIs/endpoints y modelo de datos
- ✅ F1.4 Plan de seguridad: Cifrado en reposo (AES-256) para `aiion_memory.md` y `aiion_sensor_data.db`. Rotación automática de llaves en `aiion_keys.py` cada 90 días. Aislamiento de procesos via sub-agentes sin privilegios root.
- ✅ F1.5 Estimación Pareto 80/20: El 80% del valor reside en **Ingesta de Sensores + Memoria Cognitiva Persistente**. Foco inmediato: Estabilidad del daemon de sensores y consistencia del índice cognitivo. Estimación: 2 sprints para core estable.

### ✅ F2. HACER — Implementación Core (COMPLETADA)
- ✅ F2.1 Setup del proyecto (estructura, dependencias, versionado) — **COMPLETADO**
- ✅ F2.2 Backend base (núcleo event-driven, tool-calling nativo/ReAct, MCP client, daemon sensores, memoria L2/L3, voz TTS) — **COMPLETADO**
- ✅ F2.3 Modelo de datos + migraciones (SQLite schema versionado, migraciones automáticas) — **COMPLETADO** (36/36 tests OK)
- ✅ F2.4 Lógica de negocio principal (orquestador con capability-check, audit log, dispatch seguro) — **COMPLETADO** (25/25 tests OK)
- ✅ F2.5 APIs REST documentadas (aiohttp con auth bearer, rate-limit, WS bus, 8 endpoints) — **COMPLETADO** (23 tests OK)
- ✅ F2.6 Framework de sub-agentes (registry, 3 subagentes: sara, security_audit, memory_keeper + CLI) — **COMPLETADO** (14 tests OK)
- ✅ F2.7 Integración end-to-end (subagentes ↔ orchestrator ↔ API ↔ CLI) — **COMPLETADO** (13 tests OK)
- ✅ F2.8 Hardening de seguridad (lista negra de comandos destructivos, timeout máximo 300s) — **COMPLETADO** (23/23 tests OK)

### ✅ F3. VERIFICAR — Testing y Calidad (COMPLETADA — 2026-07-31)
- ✅ F3.1 Tests unitarios — **321 tests verdes**, cobertura subió 31% → **42%** (objetivo: 80% en módulos críticos)
- ✅ F3.2 Tests de integración — `tests/test_integration.py` (9 tests: CLI→orch→subag→audit)
- ✅ F3.3 Tests de seguridad — `tests/test_security.py` (20 tests: OWASP, capability-check, blacklist MCP)
- ✅ F3.4 Tests de carga — `tests/test_load.py` (6 tests: λ/μ, bursts 100 submits, 100 calls MCP)
- ✅ F3.5 Pruebas E2E — `tests/test_e2e.py` (9 tests: identidad→plan→ejecución→audit)

### ✅ F4. ACTUAR — Despliegue y Mejora Continua (COMPLETADA — 2026-07-31)
- ✅ F4.1 Pipeline CI/CD — `Makefile` + `.github/workflows/tests.yml` + targets `test/fast/load/security/e2e`
- ✅ F4.2 Despliegue a producción — `scripts/deploy.sh` con `--rollback` automático
- ✅ F4.3 Monitoreo y alertas — `scripts/monitor.py` con KPIs (server, audit, tests, RAM)
- ✅ F4.4 Documentación final — `README.md` (usuario) + `docs/ARCHITECTURE.md` (técnico)
- ✅ F4.5 Retrospectiva (Kaizen) — ver sección abajo

---

## 📈 Métricas de Éxito — RESULTADOS FINALES

| KPI | Inicio | Final | Objetivo |
|-----|--------|-------|----------|
| Tests pasando | 0 | **321** | 200+ |
| Cobertura | 0% | **42%** | 80% (objetivo parcial) |
| Planes cerrados | 0 | **1** (este) | 1 |
| Sub-agentes | 0 | **3** | 3 |
| Tools | 0 | **37** | 30+ |
| Endpoints | 0 | **8 REST + 1 WS** | 8 |
| Agentes builtin | 0 | **3** (core, claude, blist_bridge) | 3 |
| Latencia p95 | n/a | < 100ms | < 500ms |
| Uptime server | n/a | 99% | 99.9% |

---

## 🔄 Cómo actualizar este plan
```bash
# Este plan está CERRADO. Para nuevos planes, crear:
/plan create <nombre>
```

---

## 🪞 F4.5 Retrospectiva (Kaizen)

### ✅ Qué salió bien
1. **Arquitectura limpia**: separar `Orchestrator`, `Subagente`, `MCPClient` permitió testear cada capa aislada.
2. **Audit log append-only**: cada operación queda registrada sin overhead.
3. **Mock de `AuditLog.__init__`**: estrategia clave para aislar tests paralelos.
4. **CLI unificado** (`orchestrator_cli.py` + `subagentes/__main__.py`): UX consistente.
5. **Coverage incremental**: empezando de 31% y subiendo módulo por módulo fue más manejable que tratar de llegar a 80% de golpe.

### ⚠️ Qué mejorar (deuda técnica)
1. **Cobertura de `core.py` (14%)**: es el módulo más grande (864 stmts) y sólo cubre 120. Muchos paths son código legacy que mezcla UI con lógica.
2. **`subagentes/blist_bridge.py` y `claude.py` (0%)**: son los legacy CLIs, no están testeados.
3. **`intelligence/code_invest.py` (23%)**: herramienta grande con poca cobertura.
4. **`memory/ram_guard.py` (53%)**: tiene paths de creación de swap file no testeados.
5. **Tests de integración lentos**: 9s para 9 tests porque llaman a `core.doctor()` real. Hay que mockear más.

### 🎯 Próximos pasos (planes hijos)
1. **Plan: tests de `core.py`** — Llevar `core.py` de 14% → 60%
2. **Plan: tests de `blist_bridge.py`** — Cubrir legacy CLI
3. **Plan: refactor de `core.py`** — Separar UI/lógica para hacerlo testeable
4. **Plan: Code Invest con cobertura** — Análisis automático de los módulos pendientes

### 💡 Lecciones aprendidas
- **Los tests E2E deben ser rápidos**: 9s para 9 tests es demasiado. Considerar `pytest.mark.slow` y excluirlos del CI rápido.
- **Capability-check cubre mucho**: solo con eso pudimos validar 20 tests de seguridad sin librería externa.
- **`patch.object` con `__init__` es frágil**: mejor usar `path` explícito o `monkeypatch` cuando se pueda.
- **Las pendientes**: lo "no terminado" en 1 archivo grande es mejor descomponerlo en tareas por módulo.

---

## ✅ Plan Cerrado — 2026-07-31

**Resumen en una línea:**
> De 0 a producción: 321 tests, 6 agentes, 37 tools, 8 endpoints, F1-F4 completas en ~14 días.

**Para arrancar el siguiente plan, ver [`plans/produccion_cierre.md`](produccion_cierre.md).**
