MAX_STEPS = 1000
DB_PATH = "memory/aiion.db"

# Modo de proveedor: "local" o "cloud"
MODEL_MODE = "cloud"

OLLAMA_LOCAL_URL = "http://localhost:11434/api/generate"
OLLAMA_CLOUD_URL = "https://ollama.com/api/generate"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

GEMINI_MODEL = "gemini-2.5-flash"
OLLAMA_CLOUD_MODEL = "gpt-oss:20b-cloud"  # ajusta al modelo cloud que tengas habilitado
