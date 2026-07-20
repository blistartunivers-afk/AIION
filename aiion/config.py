"""aiion/config.py — Rutas y constantes compartidas por todo el paquete."""
from pathlib import Path
import os

VERSION = "0.2"

# ── Rutas de datos (separadas de cualquier otro agente) ──────────────────
AIION_HOME = Path.home() / "AIION" / "data"
AIION_HOME.mkdir(parents=True, exist_ok=True)

MEMORY_FILE  = AIION_HOME / "aiion_memory.md"
HISTORY_FILE = AIION_HOME / "aiion_history.jsonl"
SENSOR_DB    = AIION_HOME / "aiion_sensor_data.db"
MAX_HISTORY  = 5

# ── Ollama / API ───────────────────────────────────────────────────────────
OLLAMA_LOCAL     = "http://localhost:11434"
OLLAMA_CLOUD     = "https://ollama.com"
MAX_ITER         = 12
PREFERRED_MODELS = ["qwen3-coder:480b","deepseek-v3.1:671b","gemma3:27b","qwen3.5:397b"]

# ── Voz (Groq TTS) ─────────────────────────────────────────────────────────
GROQ_TTS_URL   = "https://api.groq.com/openai/v1/audio/speech"
GROQ_TTS_MODEL = "playai-tts"
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
TTS_CHUNK      = 800
VOICES         = ["Celeste-PlayAI","Valentina-PlayAI","Mateo-PlayAI","Fritz-PlayAI"]

# ── Tools peligrosas (requieren permiso) ────────────────────────────────────
DANGEROUS_TOOLS = {"run_shell_command","write_file","replace","process_manager"}
