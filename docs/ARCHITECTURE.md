# Arquitectura de AIION v0.2

## Flujo de una interacción

```
main.py → aiion.core.main()
  1. select_mode()            → elige Local u Ollama Cloud
  2. RAMGUARD.start()          → hilo de monitoreo de memoria
  3. sensor_start()            → hilo de recolección de sensores
  4. loop principal:
       input usuario
         → run_agent(user_input, history)
             → build_system_prompt()  (memoria + sensores + historial + tools)
             → chat_native() [Ollama tool-calling]
                 → si el modelo no soporta tools: fallback a chat_react_text()
             → execute_tool(name, args)  → ask_permission() si es peligrosa
             → respuesta final → speak() + notify_response() + history_save()
```

## Módulos

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `aiion/config.py` | Constantes y rutas (`AIION_HOME`, límites, endpoints) | — |
| `aiion/cli/ui.py` | Paleta Drácula/Neón, `c()`, `hr()`, `badge()`, `BANNER` | `config` |
| `aiion/memory/ram_guard.py` | Clase `RamGuard`: presión de RAM, swap automático, kill de zombis | `cli/ui` |
| `aiion/memory/cognitive_index.py` | Clase `CognitiveIndex`: qué archivos leyó/escribió el agente | `cli/ui` |
| `aiion/memory/persistence.py` | Memoria L2 e historial L3 con búsqueda TF-IDF | `config` |
| `aiion/sensors/collectors.py` | 17 recolectores + SQLite WAL | `config` |
| `aiion/sensors/daemon.py` | Hilo que ejecuta los recolectores según sus intervalos | `sensors/collectors` |
| `aiion/voice/tts.py` | Texto→voz vía Groq PlayAI con fallback a termux-tts-speak | `config` |
| `aiion/voice/stt.py` | Voz→texto vía termux-speech-to-text | `cli/ui` |
| `aiion/llm/keys.py` | Carga/rotación del pool de keys + STATE global | `config`, `cli/ui` |
| `aiion/llm/client.py` | Payload, request HTTP, tool-calling nativo, parser ReAct de respaldo | `llm/keys`, `tools/registry` |
| `aiion/tools/filesystem.py` | 9 tools de filesystem/shell/web | `memory/cognitive_index` |
| `aiion/tools/android.py` | 10 tools de sensores/cámara/GPS/notificaciones/tareas | `sensors/*` |
| `aiion/tools/communication.py` | 7 tools de SMS/llamadas/voz | `sensors/collectors`, `voice/tts` |
| `aiion/tools/registry.py` | Definición JSON de las 28 tools, TOOL_MAP, permisos, execute_tool | tools/filesystem, tools/android, tools/communication |
| `aiion/core.py` | Orquestador delgado: system prompt, loop del agente, comandos, main() | todos los anteriores |

## Notas de diseño

- El estado global compartido (STATE, VOICE_STATE, SENSOR_STATE, TOOL_CALL_STATE) vive en el módulo dueño de esa responsabilidad, no en un "state.py" genérico.
- Sin dependencias externas: cada módulo sigue usando solo librería estándar, igual que el original.
- aiion_keys.py (gestor interactivo, `python aiion_keys.py`) sigue en la raíz pero ahora importa AIION_HOME desde aiion.config.
