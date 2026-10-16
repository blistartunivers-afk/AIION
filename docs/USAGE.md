# Guía de Uso de AIION

> Cómo instalar, configurar y usar AIION en Termux/Android.

---

## 📱 Requisitos

- **Android** sin root.
- **Termux** instalado ([termux.dev](https://termux.dev/)).
- **Termux:API** instalada y los permisos concedidos.
- **Python 3.10+** dentro de Termux.
- (Opcional) **Ollama** para modo local o keys de **Ollama Cloud**.

---

## 🚀 Instalación rápida

```bash
# 1. Clona el repo
git clone https://github.com/blistartunivers-afk/AIION.git
cd AIION

# 2. Verifica Python
python --version  # >= 3.10

# 3. No necesitas pip install (solo stdlib)
#    Pero si quieres correr tests/lint localmente:
pip install -r requirements-dev.txt  # si existe

# 4. Ejecuta AIION
python main.py
```

---

## ⚙️ Configuración inicial

### 1. Copia la plantilla de configuración

```bash
cp aiion/config.py.example aiion/config.py
```

### 2. Configura tus keys (modo nube)

```bash
export AIION_OLLAMA_KEYS="tu-key-1,tu-key-2"
```

O usa el gestor interactivo:

```bash
python aiion_keys.py
```

### 3. Verifica que termux-api funciona

```bash
termux-battery-status
```

Si ves un JSON con nivel de batería, todo está listo.

---

## 🎮 Comandos principales

Al iniciar `python main.py`, AIION entra en un loop interactivo.

### Modos de operación

| Comando | Descripción |
|---------|-------------|
| `local` | Usa Ollama corriendo en el dispositivo. |
| `cloud` | Usa Ollama Cloud con key rotativa. |
| `gemini` | Usa Google Gemini (requiere key). |

### Comandos del sistema

| Comando | Acción |
|---------|--------|
| `/help` | Muestra ayuda. |
| `/mode` | Cambia entre local/cloud/gemini. |
| `/memory` | Muestra resumen de memoria activa. |
| `/sensors` | Lista sensores disponibles y últimos valores. |
| `/tools` | Lista tools disponibles. |
| `/clear` | Limpia el historial de la sesión. |
| `/exit` | Cierra AIION guardando estado. |

---

## 💬 Casos de uso típicos

### 1. "¿Cuál es el estado de mi dispositivo?"

```
Tú: resume el estado del sistema
AIION: (lee sensores de batería, RAM, red, GPS y responde)
```

### 2. "Tómale una foto y descríbela"

```
Tú: abre la cámara y describe lo que ves
AIION: (usa tool de cámara + análisis de imagen si está configurado)
```

### 3. "Envía un SMS a mamá"

```
Tú: envía un sms a +1234567890 diciendo que llego tarde
AIION: (muestra diálogo de confirmación antes de enviar)
```

### 4. "Investiga este error"

```
Tú: el último comando falló con "permission denied", ¿qué pasó?
AIION: (consulta logs, historial de shell y explica)
```

---

## 🛠️ Herramientas disponibles

AIION expone ~28 tools organizadas en 4 categorías:

### Filesystem / Shell / Web

- `read_file`, `write_file`, `replace`
- `run_shell_command`, `run_python`
- `web_fetch`

### Android

- `take_photo`, `get_gps`, `get_battery`
- `scan_wifi`, `get_android_status`
- `notificacion`, `torch`, `vibrate`

### Comunicación

- `enviar_sms`, `hacer_llamada`
- `hablar` (TTS)

### GitHub

- Operaciones sobre repos del usuario (vía `gh` CLI).

> Las tools peligrosas (shell, SMS, llamadas) siempre piden confirmación.

---

## 🧠 Memoria

AIION tiene 4 capas de memoria:

| Capa | Dónde vive | Para qué sirve |
|------|------------|----------------|
| Short-term | RAM | Contexto de la conversación actual. |
| Long-term | SQLite (`data/aiion.db`) | Hechos persistentes del usuario. |
| Episodic | SQLite + TF-IDF | Recuerdo de interacciones pasadas. |
| Vector | SQLite + embeddings locales | Búsqueda semántica de conocimiento. |

Puedes consultar la memoria con:

```
Tú: ¿qué sabes sobre mí?
```

---

## ❓ Troubleshooting FAQ

### `ModuleNotFoundError: aiion.config`

Asegúrate de haber copiado `aiion/config.py.example` a `aiion/config.py`.

### `termux-sensor` no devuelve nada

Concede permisos a Termux:API en Android → Ajustes → Aplicaciones → Termux:API → Permisos.

### El modo local no responde

Verifica que Ollama esté corriendo:

```bash
ollama list
```

### El modo cloud dice "key inválida"

Revisa que `AIION_OLLAMA_KEYS` esté exportada y que las keys estén separadas por comas.

### Los tests fallan localmente

```bash
make test
```

Si falla un test de sensores, es normal si `termux-api` no está disponible en tu entorno de escritorio.

---

## 📚 Más documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Cómo está construido internamente.
- [`CONTRIBUTING-CORE.md`](CONTRIBUTING-CORE.md) — Cómo extenderlo.
- [`SECURITY-MODEL.md`](SECURITY-MODEL.md) — Cómo protege tus datos.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — Guía general para contribuidores.
