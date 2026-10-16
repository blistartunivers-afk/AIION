import os
from pathlib import Path

# ─── Rutas base ───
AIION_HOME = Path(os.getenv("AIION_HOME", "~/AIION/data")).expanduser()
AIION_HOME.mkdir(parents=True, exist_ok=True)

# ─── Archivos de persistencia ───
MEMORY_FILE = AIION_HOME / "memory.txt"
HISTORY_FILE = AIION_HOME / "history.jsonl"
COGINDEX_FILE = AIION_HOME / "cogindex.json"
SENSOR_DB = AIION_HOME / "sensors.db"
KEYS_FILE = AIION_HOME / "ollama_keys"
KEYS_CACHE = AIION_HOME / "ollama_key"

# ─── Configuración general ───
VERSION = "0.2.0"
MAX_ITER = 1000

# ─── Ollama endpoints ───
OLLAMA_LOCAL = os.getenv("OLLAMA_LOCAL", "http://127.0.0.1:11434")
OLLAMA_CLOUD = os.getenv("OLLAMA_CLOUD", "https://ollama.com")

# ─── Modelos preferidos (orden de prioridad) ───
PREFERRED_MODELS = [
    "qwen3-coder:480b",
    "qwen3:32b",
    "deepseek-coder:33b",
    "codellama:34b",
    "llama3.1:70b",
    "qwen2.5-coder:32b",
    "deepseek-r1:32b",
    "nemotron3-ultra:253b",
]

# ─── Voces TTS (Groq PlayAI) ───
VOICES = [
    "Celeste-PlayAI",
    "Valentina-PlayAI",
    "Mateo-PlayAI",
    "Arista-PlayAI",
    "Atlas-PlayAI",
    "Basil-PlayAI",
    "Briggs-PlayAI",
    "Calum-PlayAI",
    "Celeste-PlayAI",
    "Cheyenne-PlayAI",
    "Chip-PlayAI",
    "Cillian-PlayAI",
    "Deedee-PlayAI",
    "Fritz-PlayAI",
    "Gail-PlayAI",
    "Indigo-PlayAI",
    "Mamaw-PlayAI",
    "Mason-PlayAI",
    "Mikail-PlayAI",
    "Mitch-PlayAI",
    "Quinn-PlayAI",
    "Thunder-PlayAI",
]

# ─── Groq TTS ───
GROQ_TTS_URL = os.getenv("GROQ_TTS_URL", "https://api.groq.com/openai/v1/audio/speech")
GROQ_TTS_MODEL = "playai-tts"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TTS_CHUNK = 4000

# ─── MCP ───
BLIST_MCP_URL = os.getenv('BLIST_MCP_URL', 'http://127.0.0.1:7337/mcp')
BLIST_API_KEY = os.getenv('BLIST_API_KEY', '')

# ─── Subagentes ───
ENABLE_CLAUDE = False
LOG_LEVEL = 'INFO'

# ─── Herramientas peligrosas (requieren permiso) ───
DANGEROUS_TOOLS = {
    "write_file", "replace", "run_shell_command", "enviar_sms",
    "hacer_llamada", "crear_tarea", "eliminar_tarea",
    "cancelar_notificacion", "take_photo"
}
MAX_HISTORY = 20
