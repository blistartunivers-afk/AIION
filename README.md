```
╔══════════════════════════════════════════════════╗
║   █████╗ ██╗██╗ ██████╗ ███╗   ██╗                ║
║  ██╔══██╗██║██║██╔═══██╗████╗  ██║                ║
║  ███████║██║██║██║   ██║██╔██╗ ██║                ║
║  ██╔══██║██║██║██║   ██║██║╚██╗██║                ║
║  ██║  ██║██║██║╚██████╔╝██║ ╚████║                ║
║  ╚═╝  ╚═╝╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝                ║
║        Agente Autónomo v0.1 — Android/Termux/PC   ║
╚══════════════════════════════════════════════════╝
```

# AIION

**AIION** es un agente de IA autónomo tipo CLI (similar en concepto a Gemini CLI), pensado para correr tanto en **Android (Termux)** como en **Linux de escritorio**, con tema visual **Drácula** y sensado nativo de dispositivo cuando está disponible.

No requiere librerías externas de Python — está construido enteramente sobre la librería estándar (`urllib`, `sqlite3`, `subprocess`, etc.), lo que lo hace liviano y fácil de instalar en un entorno con recursos limitados como Termux.

## ✨ Características

- **28 tools** organizadas en 9 categorías: filesystem, web, memoria, procesos, Android, notificaciones, comunicación (SMS/llamadas), voz y tareas programadas.
- **Doble modo de ejecución**: Local (Ollama corriendo en el dispositivo) o Nube (Ollama Cloud con pool de API keys y rotación automática).
- **Memoria persistente en 3 niveles**: RAM (L1), búsqueda TF-IDF sobre historial (L2) y SQLite en disco (L3).
- **Sensores en tiempo real** vía `termux-api` (batería, WiFi, ubicación, sensores de movimiento, celda, telefonía, portapapeles, cámara, audio, NFC), guardados con SQLite en modo WAL.
- **Voz**: texto-a-voz con Groq PlayAI (4 voces) con fallback automático a `termux-tts-speak`, y reconocimiento de voz vía `termux-speech-to-text`.
- **RAM Guard**: monitor de presión de memoria con swap automático y limpieza de procesos zombis cuando el uso es crítico.
- **Índice cognitivo**: rastrea qué archivos ha leído/modificado el agente durante la sesión.
- **Sistema de permisos**: las tools destructivas (`run_shell_command`, `write_file`, `replace`, `process_manager`) requieren confirmación explícita.
- **Interfaz interactiva** con barra de estado en vivo (RAM, sensores, voz, modelo activo) y tema Drácula completo.

## 🧰 Tools disponibles

| Categoría | Tools |
|---|---|
| 📁 Filesystem | `read_file`, `write_file` 🔒, `replace` 🔒, `run_shell_command` 🔒, `list_directory`, `glob`, `grep_search` |
| 🌐 Web | `web_fetch` |
| 🧠 Memoria | `diff_files`, `memory_search` |
| ⚙️ Procesos | `process_manager` 🔒 |
| 📱 Android | `get_android_status`, `sensor_query`, `take_photo`, `listar_camaras`, `get_gps` |
| 🔔 Notificaciones | `notificacion`, `cancelar_notificacion` |
| 📞 Comunicación | `leer_sms`, `enviar_sms`, `historial_llamadas`, `hacer_llamada`, `info_telefonia` |
| 🔊 Voz | `hablar`, `listar_voces` |
| ⏰ Tareas | `crear_tarea`, `listar_tareas`, `eliminar_tarea` |

🔒 = requiere confirmación de permiso antes de ejecutarse.

## 📋 Requisitos

**Comunes (Android y PC):**
- Python 3.8 o superior
- Acceso a internet para modo Nube (Ollama Cloud) o una instancia local de [Ollama](https://ollama.com) corriendo en `localhost:11434` para modo Local

**Solo en Android (Termux):**
- [Termux](https://termux.dev) instalado (recomendado desde F-Droid, no Play Store)
- Paquete `termux-api` (Python) + app [Termux:API](https://f-droid.org/packages/com.termux.api/) instalada desde F-Droid
- `mpv` para reproducción de audio TTS (opcional — si falta, usa `termux-tts-speak` como respaldo)

**Opcional (para funciones de voz):**
- Variable de entorno `GROQ_API_KEY` para TTS con Groq PlayAI (sin ella, cae automáticamente a la voz nativa de Android)

**Para modo Nube:**
- Una o más API keys de Ollama Cloud

## 🚀 Instalación

### En Android (Termux)

```bash
# 1. Actualizar paquetes e instalar dependencias del sistema
pkg update && pkg upgrade -y
pkg install -y python termux-api mpv git

# 2. Instalar la app Termux:API desde F-Droid (necesaria además del paquete)
#    https://f-droid.org/packages/com.termux.api/

# 3. Clonar el repositorio
git clone https://github.com/blistartunivers-afk/AIION.git
cd AIION

# 4. (Opcional) configurar voz TTS con Groq
export GROQ_API_KEY="tu_api_key_aqui"

# 5. Ejecutar
python aiion_core.py
```

### En Linux (PC)

```bash
# 1. Clonar el repositorio
git clone https://github.com/blistartunivers-afk/AIION.git
cd AIION

# 2. (Opcional) instalar Ollama para modo local
curl -fsSL https://ollama.com/install.sh | sh

# 3. (Opcional) configurar voz TTS con Groq
export GROQ_API_KEY="tu_api_key_aqui"

# 4. Ejecutar
python3 aiion_core.py
```

> Nota: las funciones de Android (sensores, SMS, llamadas, cámara, notificaciones) requieren `termux-api` y solo funcionan dentro de Termux. En Linux de escritorio, AIION corre igual pero esas tools específicas de Android no tendrán datos disponibles.

### Configurar API keys de Ollama Cloud (modo Nube)

Al iniciar, AIION te pedirá elegir modo Local o Nube. Para modo Nube, guarda tus keys (una por línea) en:

```bash
~/AIION/data/ollama_keys
```

o exporta la variable de entorno `OLLAMA_API_KEY`. AIION detecta automáticamente cuántas keys tienes disponibles y rota entre ellas.

## 💻 Uso

```bash
python aiion_core.py
```

Al arrancar, elige el modo (Local o Nube) y el modelo. Luego puedes interactuar en lenguaje natural o usar comandos internos:

| Comando | Descripción |
|---|---|
| `/help` | Ver todos los comandos |
| `/exit` | Salir del agente |
| `/clear` | Limpiar historial de sesión |
| `/model` | Cambiar modelo |
| `/tools` | Ver todas las tools disponibles |
| `/cd <path>` | Cambiar directorio |
| `/ram` | Estado de RAM en detalle |
| `/memory` | Ver memoria persistente |
| `/remember <dato>` | Guardar dato en memoria |
| `/history` | Ver conversaciones pasadas |
| `/index` | Ver índice cognitivo (archivos leídos/modificados) |
| `/sensors` | Estado de sensores en tiempo real |
| `/toolmode` | Alternar entre modo nativo y ReAct |
| `/voice on` \| `off` \| `test` | Controlar voz |
| `/voice set <voz>` | Cambiar voz (Celeste/Valentina/Mateo/Fritz) |
| `/voice vol <0-100>` | Volumen |
| `/voice speed <0.5-2>` | Velocidad de habla |

## 🗂️ Estructura de datos

AIION mantiene su propia carpeta de datos, completamente separada de otros agentes:

```
~/AIION/data/
├── aiion_memory.md        # Memoria persistente en texto
├── aiion_history.jsonl    # Historial de conversaciones
├── aiion_sensor_data.db   # Base de datos SQLite de sensores
└── ollama_keys            # Pool de API keys (una por línea)
```

## 📄 Licencia

Este proyecto está bajo licencia MIT — ver [LICENSE](LICENSE) para más detalles.

## 👤 Autor

Desarrollado por [Estiven](https://github.com/blistartunivers-afk).
