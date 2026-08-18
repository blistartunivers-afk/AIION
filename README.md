# AIION — Agente Autónomo de Ecosistema

AIION es un agente autónomo diseñado para operar en **Android/Termux**, capaz de percibir su entorno (sensores), razonar con memoria a largo plazo, ejecutar tareas complejas mediante herramientas nativas y evolucionar de forma segura sin root ni nube obligatoria.

---

## 🚀 Características

- **Sensores en tiempo real:** batería, WiFi, GPS, llamadas, SMS, sistema.
- **Memoria cognitiva:** L2 (hechos) + L3 (episódica) cifrada en AES-256.
- **Orquestador con sub-agentes:** 3 subagentes (`sara`, `security_audit`, `memory_keeper`) + 3 builtins (`core`, `claude`, `blist_bridge`).
- **Cliente MCP:** conexión a `blistv11` (Sara OS) vía JSON-RPC con blacklist/whitelist.
- **API REST:** 8 endpoints con auth bearer, rate-limit y WebSocket bus.
- **Seguridad:** capability-check, audit log inmutable, denegación de comandos destructivos.
- **Cobertura de tests:** 42% (objetivo: 80% en módulos críticos).

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                 AIION (Android/Termux)                   │
├──────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   CLI /    │  │   REST API   │  │ WebSocket    │     │
│  │   TUI      │  │  (aiohttp)   │  │ bus          │     │
│  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘     │
│        └─────────────────┴──────────────────┘            │
│                          ↓                              │
│                ┌──────────────────┐                      │
│                │   Orchestrator   │  ← capability check  │
│                │  (audit + bus)   │                      │
│                └─────────┬────────┘                      │
│                          ↓                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ sara     │  │ security │  │ memory   │  + core/      │
│  │ (sensores│  │  _audit  │  │ _keeper  │    claude/    │
│  │  voz)    │  │  (audit) │  │  (L2/L3) │   blist_bridge│
│  └──────────┘  └──────────┘  └──────────┘              │
│                          ↓                              │
│  ┌─────────────────────────────────────────────┐        │
│  │  Tools: 37 — incluyendo DANGEROUS_TOOLS      │        │
│  │  (run_shell_command, write_file, replace,    │        │
│  │   process_manager) requieren permiso explícito│       │
│  └─────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

---

## 📦 Instalación

```bash
cd ~/AIION
pip install -r requirements.txt
pip install pytest pytest-cov pytest-timeout
```

## 🚀 Uso

### CLI
```bash
python -m aiion.orchestrator_cli agents    # lista agentes
python -m aiion.orchestrator_cli stats     # métricas
python -m aiion.orchestrator_cli audit 20  # últimos 20 eventos
python -m aiion.orchestrator_cli submit core doctor
python -m aiion.orchestrator_cli plan plan.json
```

### Subagentes
```bash
python -m aiion.subagentes list
python -m aiion.subagentes describe sara
python -m aiion.subagentes call memory_keeper stats
```

### API REST
```bash
# Arrancar (bind 127.0.0.1:8080)
python -m aiion.api_server

# Health check
curl http://127.0.0.1:8080/health
```

### Tests
```bash
make test          # suite completa (48s, 321 tests)
make test-fast     # sin integración (5s)
make coverage      # reporte HTML
```

---

## 📊 Estado

| Métrica | Valor |
|---------|-------|
| Tests | **321 passing** |
| Cobertura | **42%** |
| Plans cerrados | 1 (`aiion_produccion.md`) |
| Agentes | 3 subagentes + 3 builtins = **6** |
| Tools | **37** |
| Endpoints | 8 REST + 1 WS |

Para más detalle, ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🔐 Seguridad

- Tools peligrosas requieren permiso explícito (`ask_permission`).
- MCP con blacklist/whitelist configurable.
- Capability-check en cada `dispatch`.
- Audit log append-only en `orchestrator_audit.jsonl`.
- Ver tests: `make test-security`.

---

## 📜 Licencia

MIT — ver [LICENSE](LICENSE).

---

*Desarrollado como parte del ecosistema BLIST · 2026*
