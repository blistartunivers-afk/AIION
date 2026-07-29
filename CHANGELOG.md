# Changelog — AIION

Todos los cambios notables del proyecto serán documentados aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [Unreleased]

### Planeado
- Sistema de plugins dinámicos
- Dashboard web opcional (Flask)
- Integración con más proveedores LLM (Anthropic, Mistral)
- Tests E2E con mocks de termux-api

---

## [0.2.0] — 2026-07-28

### 🎉 Primera versión pública

#### Añadido
- **README profesional** con badges, arquitectura visual y guía de instalación
- **Estructura modular completa**:
  - `aiion/core.py` — Núcleo de orquestación
  - `aiion/db.py` — SQLite con migraciones idempotentes
  - `aiion/memory/` — Sistema de memoria cognitiva de 4 capas
  - `aiion/llm/` — Clientes para Ollama Cloud y Gemini
  - `aiion/cli/` — UI CLI con Drácula palette
- **`aiion_keys.py`** — Gestor de pool de API keys con rotación automática
- **`.gitignore` blindado** — Excluye datos sensibles, claves, BD local y entornos virtuales
- **`LICENSE` MIT** — Código libre para uso comercial y personal
- **`Makefile`** — Comandos estandarizados (`make install`, `make test`, `make lint`)
- **`.pre-commit-config.yaml`** — Hooks de calidad pre-commit
- **`docs/`** — Documentación técnica base

#### Seguridad
- Verificado: **0 secretos** en el historial de git
- Verificado: **`aiion_keys.py` es código fuente**, NO contiene keys reales
- Verificado: **`config.py.example` no expone credenciales**
- Confirmado: **`.gitignore` cubre** todas las rutas sensibles (`data/`, `*.env`, claves, BD)

---

## [0.1.0] — 2026-07-12 (interno)

### Añadido
- Estructura inicial del proyecto
- Núcleo básico `core.py`
- Sistema de logging
- Tests unitarios iniciales

---

## Leyenda de tipos de cambios

- `Añadido` — para funcionalidades nuevas
- `Cambiado` — para cambios en funcionalidades existentes
- `Obsoleto` — para funcionalidades que serán removidas
- `Removido` — para funcionalidades removidas
- `Corregido` — para corrección de bugs
- `Seguridad` — para vulnerabilidades y mejoras de seguridad

---

[Unreleased]: https://github.com/blistartunivers-afk/AIION/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/blistartunivers-afk/AIION/releases/tag/v0.2.0
[0.1.0]: https://github.com/blistartunivers-afk/AIION/releases/tag/v0.1.0
