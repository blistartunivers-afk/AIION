# Plan de Mejoras para AIION — Repo Público

> **Documento vivo.** Se actualiza al cerrar cada fase.
> **Estado:** 🟡 En planificación → 🟢 En ejecución → ✅ Cerrado

---

## 🎯 Objetivo General

Llevar al repositorio público `blistartunivers-afk/AIION` de un estado
**"MVP funcional"** a un estado **"proyecto production-ready open source"**
que inspire confianza a contribuidores externos y refleje la filosofía
del ecosistema BLIST.

## 📅 Fecha de inicio

2026-07-28

## 👤 Responsable

Estiven (con asistencia de Sara/blist)

---

## 📊 Línea Base (Estado Actual del Repo)

Realizado en auditoría del 2026-07-28:

| Elemento | Estado | Notas |
|----------|--------|-------|
| `README.md` profesional | ✅ Existe | Con badges, arquitectura, instalación |
| `CHANGELOG.md` | ✅ Existe | Formato Keep a Changelog |
| `CONTRIBUTING.md` | ✅ Existe | Guía completa de contribución |
| `LICENSE` MIT | ✅ Existe | Código libre de origen |
| `Makefile` | ✅ Existe | Comandos estandarizados |
| `.gitignore` blindado | ✅ Existe | Cubre secretos, datos, BD, envs |
| `.pre-commit-config.yaml` | ✅ Existe | Hooks de calidad |
| `.github/CODE_OF_CONDUCT.md` | ✅ Existe | Bilingüe (ES/EN) v2.1 |
| `.github/SECURITY.md` | ✅ Existe | Política de reporte privado |
| `.github/ISSUE_TEMPLATE/*.yml` | ✅ Existe | bug_report + feature_request |
| `.github/PULL_REQUEST_TEMPLATE.md` | ✅ Existe | Checklist completo |
| `CONTRIBUTORS.md` | ✅ Existe | Con instrucciones de entrada |
| `aiion/` estructura | ✅ Existe | core, db, memory, llm, tools, etc. |
| `aiion_keys.py` | ✅ Existe | Pool de keys, sin datos sensibles |
| `tests/` | ✅ Existe | `test_db.py`, `test_memory.py` (825 líneas) |
| `docs/ARCHITECTURE.md` | ✅ Existe | Documentación técnica |
| `plans/` | ✅ Existe | Plantillas internas (no público) |
| `pyproject.toml` | ✅ Existe | Configuración de paquete |
| `requirements.txt` | ✅ Existe | Dependencias |

### ❌ Lo que aún falta

| Categoría | Pendiente |
|-----------|-----------|
| **Releases** | Sin tags ni GitHub Releases |
| **CI/CD** | Sin GitHub Actions automatizados |
| **Páginas web** | Sin GitHub Pages configurado |
| **Visual** | Logo/banner generativo |
| **Documentación avanzada** | CONTRIBUTING-CORE, SECURITY-MODEL, USAGE |
| **Features nuevas** | Plugins, dashboard, más LLMs |

---

## 🗺️ Roadmap por Fases

### ✅ Fase 0 — Auditoría y Diagnóstico (COMPLETADA)
**Fecha:** 2026-07-28

- [x] Auditoría de archivos existentes
- [x] Verificación de `.gitignore` (sin secretos)
- [x] Confirmación de `aiion_keys.py` sin keys reales
- [x] README inicial profesional
- [x] CHANGELOG inicial
- [x] CONTRIBUTING inicial
- [x] Push a rama `master`
- [x] Verificación en GitHub público

**Resultado:** Repo base profesional, sin grietas de seguridad.

---

### ✅ Fase 1 — Fundamentos de Comunidad (COMPLETADA)
**Fecha de cierre:** 2026-07-28
**Duración:** 1 sesión
**Objetivo:** Establecer el esqueleto de archivos GitHub-native que todo repo open source maduro necesita.

#### Tareas completadas:
- [x] `.github/CODE_OF_CONDUCT.md` (5862 bytes)
  - Basado en Contributor Covenant v2.1
  - Idioma: Español + Inglés
- [x] `.github/SECURITY.md` (3543 bytes)
  - Política de reporte de vulnerabilidades
  - Canal privado: email
  - SLA por severidad (Crítica/Alta/Media/Baja)
- [x] `.github/ISSUE_TEMPLATE/bug_report.yml` (4175 bytes)
  - Formulario estructurado con 10 secciones
- [x] `.github/ISSUE_TEMPLATE/feature_request.yml` (3482 bytes)
  - Descripción + motivación + alternativa + mockups
- [x] `.github/PULL_REQUEST_TEMPLATE.md` (3020 bytes)
  - Checklist completo: código, tests, docs, seguridad, filosofía
- [x] `CONTRIBUTORS.md` (2289 bytes)
  - (vacío, pero con instrucciones de cómo añadirse)
- [x] Commit `docs(community)` con mensaje detallado
- [x] Push a `master` (commit 407d310)
- [x] Verificación con `gh_list_files`

**Criterio de cierre:** ✅ Cualquier usuario externo puede abrir un issue o PR siguiendo los guidelines.

---

### 🔵 FASE 2 — Primer Release Oficial (v0.2.0) (PRÓXIMA)
**Duración estimada:** 30 min
**Objetivo:** Materializar el trabajo de Fases 0 y 1 en una release pública de GitHub.

#### Tareas:
- [ ] Crear tag `v0.2.0` local
- [ ] Push del tag a GitHub
- [ ] Crear Release en GitHub (vía `gh release create`)
  - Título: "v0.2.0 — Primera versión pública"
  - Descripción: copia del CHANGELOG [0.2.0]
  - Marcar como "latest"
- [ ] Añadir badge en README de "última release"
- [ ] Verificar que el badge renderiza

**Criterio de cierre:** Releases page muestra v0.2.0 con notas claras.

---

### 🟣 FASE 3 — CI/CD con GitHub Actions
**Duración estimada:** 45 min
**Objetivo:** Que cada PR se pruebe automáticamente antes de merge.

#### Tareas:
- [ ] Crear `.github/workflows/tests.yml`
  - Trigger: PR a `master`, push a `master`
  - Python matrix: 3.9, 3.10, 3.11, 3.12
  - Instalar dependencias
  - Correr `pytest`
  - Correr `flake8` / `ruff`
- [ ] Crear `.github/workflows/lint.yml`
  - Pre-commit hooks en CI
- [ ] Crear `.github/workflows/security.yml`
  - `pip-audit` para dependencias
  - `gitleaks` para secretos
  - Trivy para archivos
- [ ] Verificar primer run con un commit vacío
- [ ] Añadir badges de CI en README

**Criterio de cierre:** Un PR de prueba gatilla todos los workflows.

---

### 🟠 FASE 4 — Documentación Avanzada
**Duración estimada:** 1 sesión
**Objetivo:** Que un desarrollador externo pueda entender y usar AIION sin ayuda.

#### Tareas:
- [ ] Expandir `docs/ARCHITECTURE.md`
  - Diagramas de flujo en ASCII
  - Explicación de cada capa de memoria
  - Ciclo de vida de un comando
- [ ] Crear `docs/CONTRIBUTING-CORE.md`
  - Cómo añadir un nuevo sensor
  - Cómo añadir una nueva tool
  - Cómo añadir un nuevo sub-agente
- [ ] Crear `docs/SECURITY-MODEL.md`
  - Qué protege el `.gitignore`
  - Cómo funciona `aiion_keys.py` (sin revelar keys)
  - Threat model del sistema
- [ ] Crear `docs/USAGE.md`
  - Comandos principales con ejemplos
  - Casos de uso típicos
  - Troubleshooting FAQ
- [ ] Vincular desde el README

**Criterio de cierre:** Cero preguntas básicas en "cómo se usa" en nuevos issues.

---

### 🔴 FASE 5 — Identidad Visual
**Duración estimada:** 30 min
**Objetivo:** Que el repo sea reconocible y memorable.

#### Tareas:
- [ ] Generar logo con `generate_image`
  - Prompt: "AIION logo, minimal, neon, dolphin-like water motif"
- [ ] Generar banner con `generate_image`
  - Prompt: "AIION banner 1200x400, futuristic, ecosystem"
- [ ] Crear carpeta `assets/`
- [ ] Insertar logo en README (header)
- [ ] Insertar banner en `docs/ARCHITECTURE.md`
- [ ] Configurar repo social preview
  - GitHub Settings → Social preview → upload imagen

**Criterio de cierre:** Repo tiene identidad visual única.

---

### 🟤 FASE 6 — Funcionalidades Incrementales
**Duración estimada:** según feedback
**Objetivo:** Empezar a incorporar features que diferencien a AIION.

#### Ideas (se priorizan tras feedback):
- [ ] Sistema de plugins dinámicos
- [ ] Dashboard web opcional (Flask)
- [ ] Más integraciones LLM (Anthropic, Mistral)
- [ ] Tests E2E con mocks de termux-api
- [ ] Métricas Prometheus
- [ ] Distribución vía PyPI
- [ ] Empaquetado Termux (`.apt`)

**Criterio de cierre:** Al menos 1 feature de la lista integrada y testeada.

---

### ⚪ FASE 7 — Comunidad y Crecimiento
**Duración estimada:** continuo
**Objetivo:** Atraer y mantener contribuidores.

#### Tareas:
- [ ] Publicar en Reddit r/Python, r/Termux
- [ ] Publicar en HackerNews (Show HN)
- [ ] Crear tutorial en YouTube/Medium
- [ ] Responder todos los issues en <48h
- [ ] Reconocer contribuidores en `CONTRIBUTORS.md`
- [ ] Celebrar hitos (100 stars, 1k downloads)

---

## 📐 Convenciones del Plan

- ✅ **Completado** — fase cerrada y verificada en GitHub
- 🟡 **En progreso** — tareas en curso
- 🔵 **Próximo** — listo para empezar
- 🟢 **🟣 🟠 🔴 🟤** — fases planificadas en orden
- ⚪ **Futuro** — depende de feedback

## 🔄 Cómo Actualizar

Al cerrar cada fase:
1. Cambiar ✅ en su fase
2. Añadir fecha de cierre
3. Apuntar lecciones aprendidas al final

---

## 📝 Lecciones Aprendidas

*(Esta sección se llena al cerrar fases)*
