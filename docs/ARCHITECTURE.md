# Arquitectura de AIION v0.2

<p align="center">
  <img src="../assets/logo.jpg" alt="AIION logo" width="120">
</p>

> Visión técnica de cómo AIION procesa una interacción, gestiona memoria y ejecuta herramientas.

---

## 🌐 Flujo de una interacción

```
┌─────────────┐
│   main.py   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  aiion.core.main()  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  1. select_mode()                           │
│     → elige Local, Cloud o Gemini             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  2. RAMGUARD.start()                        │
│     → hilo de monitoreo de memoria          │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  3. sensor_start()                            │
│     → hilo de recolección de sensores       │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  4. Loop principal                            │
│     input usuario                             │
│       │                                       │
│       ▼                                       │
│     run_agent(user_input, history)            │
│       │                                       │
│       ├── build_system_prompt()                 │
│       │   └── memoria + sensores + historial  │
│       │       + tools disponibles             │
│       │                                       │
│       ├── chat_native()                       │
│       │   └── Ollama tool-calling             │
│       │                                       │
│       ├── fallback: chat_react_text()         │
│       │   └── parseo manual de tool calls    │
│       │                                       │
│       ├── execute_tool(name, args)            │
│       │   └── ask_permission() si peligrosa   │
│       │                                       │
│       └── respuesta final                     │
│           ├── speak()                         │
│           ├── notify_response()               │
│           └── history_save()                  │
└─────────────────────────────────────────────┘
```

---

## 🧠 Capas de memoria

AIION organiza la memoria en 4 capas con distintas velocidades y duraciones.

```
┌────────────────────────────────────────────────────────────┐
│  CAPA              │  MEDIO              │  VIDA ÚTIL       │
├────────────────────────────────────────────────────────────┤
│  Short-term (L1)   │  RAM / dict STATE   │  Sesión          │
│  Long-term (L2)    │  SQLite             │  Persistente     │
│  Episodic (L3)     │  SQLite + TF-IDF    │  Persistente     │
│  Vector (L4)       │  SQLite + embeddings│  Persistente     │
└────────────────────────────────────────────────────────────┘
```

### Short-term (L1)

- Vive en `STATE`, un diccionario global en memoria.
- Contiene: sensores recientes, estado de voz, historial de la conversación actual.
- Se pierde al cerrar AIION.

### Long-term (L2)

- Persistencia en `data/aiion.db` vía `aiion/db.py`.
- Almacena: hechos aprendidos, preferencias del usuario, configuraciones.
- Migraciones idempotentes permiten actualizar el schema sin perder datos.

### Episodic (L3)

- Índice semántico TF-IDF en `aiion/memory/persistence.py`.
- Permite buscar interacciones similares a la consulta actual.
- Útil para recuperar contexto de conversaciones pasadas.

### Vector (L4)

- Embeddings locales almacenados en SQLite.
- Búsqueda por similitud para conocimiento semántico.
- No requiere servicios externos.

---

## 🧩 Módulos

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `aiion/config.py` | Constantes y rutas (`AIION_HOME`, límites, endpoints) | — |
| `aiion/cli/ui.py` | Paleta Drácula/Neón, `c()`, `hr()`, `badge()`, `BANNER` | `config` |
| `aiion/cli/keys_cli.py` | Interfaz interactiva para gestionar keys | `config`, `llm/keys` |
| `aiion/memory/ram_guard.py` | Clase `RamGuard`: presión de RAM, swap automático, kill de zombis | `cli/ui` |
| `aiion/memory/cognitive_index.py` | Clase `CognitiveIndex`: qué archivos leyó/escribió el agente | `cli/ui` |
| `aiion/memory/persistence.py` | Memoria L2 e historial L3 con búsqueda TF-IDF | `config` |
| `aiion/sensors/collectors.py` | 17 recolectores + SQLite WAL | `config` |
| `aiion/sensors/daemon.py` | Hilo que ejecuta los recolectores según sus intervalos | `sensors/collectors` |
| `aiion/voice/tts.py` | Texto→voz vía Groq PlayAI con fallback a termux-tts-speak | `config` |
| `aiion/voice/stt.py` | Voz→texto vía termux-speech-to-text | `cli/ui` |
| `aiion/llm/keys.py` | Carga/rotación del pool de keys + STATE global | `config`, `cli/ui` |
| `aiion/llm/client.py` | Payload, request HTTP, tool-calling nativo, parser ReAct de respaldo | `llm/keys`, `tools/registry` |
| `aiion/llm/kalman.py` | Filtro de Kalman para suavizar métricas de latencia | stdlib |
| `aiion/tools/filesystem.py` | Tools de filesystem/shell/web | `memory/cognitive_index` |
| `aiion/tools/android.py` | Tools de sensores/cámara/GPS/notificaciones/tareas | `sensors/*` |
| `aiion/tools/communication.py` | Tools de SMS/llamadas/voz | `sensors/collectors`, `voice/tts` |
| `aiion/tools/github.py` | Operaciones de GitHub vía `gh` CLI | `config` |
| `aiion/tools/registry.py` | Definición JSON de las tools, TOOL_MAP, permisos, execute_tool | todos los tools |
| `aiion/subagentes/claude.py` | Sub-agente especialista (ejemplo) | `core` |
| `aiion/core_modules/mythos_engine.py` | Motor de análisis logos/pathos/ethos | stdlib |
| `aiion/core_modules/langgraph_integration.py` | Integración con grafos de ejecución | stdlib |
| `aiion/core.py` | Orquestador: system prompt, loop del agente, comandos, main() | todos los anteriores |
| `aiion/db.py` | SQLite con migraciones idempotentes | `config` |

---

## ⚙️ Ciclo de vida de un comando

```
Usuario escribe: "envía un sms a Juan"
        │
        ▼
┌─────────────────────┐
│  core.main()        │
│  recibe input       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  build_system_prompt│
│  + memoria + tools  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  llm/client.py      │
│  envía a Ollama/     │
│  Gemini             │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Modelo responde    │
│  con tool call:     │
│  send_sms           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  tools/registry.py  │
│  execute_tool()     │
│  detecta peligrosa  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  ask_permission()   │
│  (dialogo con user) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  tools/communication│
│  envía SMS          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  core formatea      │
│  respuesta final    │
│  + TTS + notificación│
└─────────────────────┘
```

---

## 🏛️ Notas de diseño

- El estado global compartido (STATE, VOICE_STATE, SENSOR_STATE, TOOL_CALL_STATE) vive en el módulo dueño de esa responsabilidad, no en un `state.py` genérico.
- Sin dependencias externas: cada módulo sigue usando solo librería estándar, igual que el original.
- `aiion_keys.py` (gestor interactivo, `python aiion_keys.py`) sigue en la raíz pero ahora importa `AIION_HOME` desde `aiion.config`.
- Las migraciones de base de datos son idempotentes: pueden correrse múltiples veces sin duplicar tablas.

---

## 📚 Documentación relacionada

- [`USAGE.md`](USAGE.md) — Cómo instalar y usar AIION.
- [`CONTRIBUTING-CORE.md`](CONTRIBUTING-CORE.md) — Cómo extender sensores, tools y sub-agentes.
- [`SECURITY-MODEL.md`](SECURITY-MODEL.md) — Cómo AIION protege datos y keys.
