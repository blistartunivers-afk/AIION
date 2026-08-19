import asyncio, json, sys
sys.path.insert(0, "/data/data/com.termux/files/home/AIION")
from aiion.tools.sara_ops import _ws_send

# Saludo corto y directo
saludo = "ping desde AIION: ¿me recibes, Sara? Estiven nos activó. Estamos los 9 agentes en línea. Te saludo."
try:
    resp = asyncio.run(_ws_send(saludo, timeout=30))
    print("📩 Respuesta de Sara (timeout 30s):")
    print(resp[:2000] if isinstance(resp, str) else resp)
except Exception as e:
    print(f"⚠️ WS send error: {e}")
