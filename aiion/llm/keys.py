"""aiion/llm/keys.py — Carga y rotación del pool de API keys de Ollama Cloud.

Nota: el gestor INTERACTIVO (menú para agregar/eliminar/probar keys) vive
por ahora en tu aiion_keys.py suelto en la raíz del repo — se deja ahí
como utilidad de CLI aparte (`python aiion_keys.py`). Este módulo es lo
que aiion_core.py usa en tiempo de ejecución para cargar y rotar keys.
"""
import os
from aiion.config import AIION_HOME
from aiion.cli.ui import c, YL

STATE = {"model":"","api_keys":[],"key_index":0,"use_cloud":False}

def load_api_keys():
    env=os.environ.get("OLLAMA_API_KEY","").strip()
    if env: return [k.strip() for k in env.split(",") if k.strip()]
    kf=AIION_HOME/"ollama_keys"
    if kf.exists(): return [l.strip() for l in kf.read_text().splitlines() if l.strip()]
    kf2=AIION_HOME/"ollama_key"
    if kf2.exists(): return [kf2.read_text().strip()]
    return []

def current_key():
    keys=STATE["api_keys"]
    return keys[STATE["key_index"]%len(keys)] if keys else ""

def rotate_key():
    STATE["key_index"]=(STATE["key_index"]+1)%max(len(STATE["api_keys"]),1)
    k=current_key()
    print(c(YL,f"  🔑 Rotando key #{STATE['key_index']+1}: {k[:8]}..."))
    return k
