# 🏁 Plan de Cierre — `aiion_produccion.md`

**Objetivo:** Llevar `aiion_produccion.md` de **~65% → 100%** en esta sesión.

**Estado actual verificado:**
- ✅ 144/144 tests verdes en 4.6s
- ✅ Cobertura: **31%** (objetivo: ≥80%)
- ✅ F1 + F2.1-F2.8 completas
- ⏳ F3 (Verificar) y F4 (Actuar) pendientes

---

## 🎯 Entregables para llegar al 100%

### F3. VERIFICAR — Testing y Calidad

| # | Tarea | Estado | Cómo |
|---|-------|--------|------|
| F3.1 | Cobertura ≥ 80% | ⏳ | Crear tests para módulos 0% (orchestrator_cli, subagentes/__main__, mcp/client, llm/client) |
| F3.2 | Tests de integración | ⏳ | `test_integration.py` — flujo CLI → orchestrator → subagente |
| F3.3 | Tests de seguridad | ⏳ | `test_security.py` — OWASP top 10 sobre API + capability-check |
| F3.4 | Tests de carga | ⏳ | `test_load.py` — burst a `/plan` y `/memory` con métricas λ/μ |
| F3.5 | Pruebas E2E | ⏳ | `test_e2e.py` — escenario completo: ident → plan → skill → audit |

### F4. ACTUAR — Despliegue y Mejora Continua

| # | Tarea | Estado | Cómo |
|---|-------|--------|------|
| F4.1 | Pipeline CI/CD | ⏳ | `Makefile` + `run_tests.sh` + GitHub Actions YAML mínimo |
| F4.2 | Despliegue a producción | ⏳ | `deploy.sh` con rollback, systemd-like wrapper para Termux |
| F4.3 | Monitoreo y alertas | ⏳ | `metrics.py` + script `monitor.py` con KPIs (uptime, latencia, RAM) |
| F4.4 | Documentación final | ⏳ | `README.md` (usuario) + `ARCHITECTURE.md` (técnico) |
| F4.5 | Retrospectiva (Kaizen) | ⏳ | Sección final en este plan con qué mejorar |

---

## 📊 Backlog priorizado (Pareto 80/20)

Los 4 archivos que más suben la cobertura (1450 stmts destapadas):

1. **`aiion/orchestrator_cli.py`** — 104 stmts → cubre F3.1
2. **`aiion/subagentes/__main__.py`** — 58 stmts → cubre F3.1
3. **`aiion/llm/client.py`** — 53 stmts → cubre F3.1
4. **`aiion/mcp/client.py`** — 229 stmts → cubre F3.1+F3.2

---

## ⏱️ Estimación: 2-3 sesiones max.

**Hoy:**
- ✅ Estado medido (ya hecho)
- Tests cobertura módulos 0% (F3.1)
- Tests integración CLI (F3.2)
- Tests seguridad (F3.3)
- Documentación (F4.4)

**Siguiente:**
- Tests carga (F3.4)
- Tests E2E (F3.5)
- CI/CD + deploy (F4.1, F4.2)
- Monitoreo (F4.3)
- Retrospectiva (F4.5)
