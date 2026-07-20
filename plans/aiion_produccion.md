# 📋 Plan: Aiion Produccion

**Creado:** 2026-07-17
**Estado:** 🆕 Nuevo

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

### ⏳ F2. HACER — Implementación Core
- ✅ F2.1 Setup del proyecto (estructura, dependencias, versionado) — **COMPLETADO**
- ✅ F2.2 Backend base (núcleo event-driven, tool-calling nativo/ReAct, MCP client, daemon sensores, memoria L2/L3, voz TTS) — **COMPLETADO**
- 🔄 F2.3 Modelo de datos + migraciones (SQLite schema versionado, migraciones automáticas) — **EN PROGRESO**
- ⏳ F2.4 Lógica de negocio principal (sub-agentes, planificación, ejecución autónoma)
- ⏳ F2.5 APIs REST/GraphQL documentadas (exposición controlada para frontends externos)

### ⏳ F3. VERIFICAR — Testing y Calidad
- ⏳ F3.1 Tests unitarios (cobertura ≥ 80%)
- ⏳ F3.2 Tests de integración
- ⏳ F3.3 Tests de seguridad (OWASP Top 10)
- ⏳ F3.4 Tests de carga (teoría de colas: λ=tasas, μ=servicio)
- ⏳ F3.5 Pruebas E2E

### ⏳ F4. ACTUAR — Despliegue y Mejora Continua
- ⏳ F4.1 Pipeline CI/CD
- ⏳ F4.2 Despliegue a producción (con rollback)
- ⏳ F4.3 Monitoreo y alertas (KPIs)
- ⏳ F4.4 Documentación final (usuario + técnico)
- ⏳ F4.5 Retrospectiva (Kaizen) — qué mejorar

---

## 🔄 Cómo actualizar este plan
```bash
/plan check aiion_produccion F1.1 done      # marca como completado ✅
/plan check aiion_produccion F1.1 partial   # en progreso 🔄
/plan check aiion_produccion F1.1 pending   # pendiente ⏳
/plan show aiion_produccion                 # ver plan completo
```

## 📈 Métricas de Éxito
- ⏳ % completitud del plan
- ⏳ Cobertura de tests
- ⏳ Latencia media (ms)
- ⏳ Uptime (%)
