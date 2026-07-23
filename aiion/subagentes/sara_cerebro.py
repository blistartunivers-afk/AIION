"""
aiion/subagentes/sara_cerebro.py — Subagente SARA (sensores + voz + notificaciones).

Capa de automatización: traduce capabilities en llamadas a las tools
existentes (aiion.tools, aiion.voice, aiion.sensors).

Capabilities:
  - sensor_status  → lee batería+wifi+system
  - sensor_history → consulta últimos N puntos de un sensor
  - voice_speak    → TTS con voz por defecto
  - voice_list     → lista voces disponibles
  - notify         → manda notificación Android
  - location       → GPS actual
  - info           → estado del subagente
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

# path bootstrap
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiion.subagentes.base import Subagente, subagente


@subagente
class SaraCerebro(Subagente):
    name = "sara"
    description = "SARA — sistema nervioso digital (sensores, voz, notificaciones)"
    version = "0.1"
    capabilities = [
        "sensor_status",
        "sensor_history",
        "voice_speak",
        "voice_list",
        "notify",
        "location",
        "info",
    ]

    def handle(self, capability: str, args: dict) -> dict:
        if capability == "info":
            return self._info()
        if capability == "sensor_status":
            return self._sensor_status(args.get("sensor", "all"))
        if capability == "sensor_history":
            return self._sensor_history(
                args.get("sensor", "battery"),
                int(args.get("limit", 10)),
            )
        if capability == "voice_speak":
            return self._voice_speak(args.get("text", ""), args.get("voice"))
        if capability == "voice_list":
            return self._voice_list()
        if capability == "notify":
            return self._notify(args.get("title", "AIION"), args.get("content", ""))
        if capability == "location":
            return self._location()
        raise ValueError(f"capability '{capability}' no implementada en handle")

    # --------- implementations ---------
    def _info(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "tools": ["get_android_status", "sensor_query", "hablar",
                      "listar_voces", "notificacion", "get_gps"],
        }

    def _sensor_status(self, sensor: str) -> dict:
        """Llama al tool get_android_status / sensor_query del sistema."""
        try:
            from aiion.tools.system import tool_get_android_status  # type: ignore
            data = tool_get_android_status(detail=sensor)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            return {"sensor": sensor, "data": data}
        except ImportError:
            return {"sensor": sensor, "data": None,
                    "warning": "aiion.tools.system no disponible"}

    def _sensor_history(self, sensor: str, limit: int) -> dict:
        try:
            from aiion.tools.system import tool_sensor_query  # type: ignore
            data = tool_sensor_query(sensor=sensor, limit=limit)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            return {"sensor": sensor, "limit": limit, "data": data}
        except ImportError:
            return {"sensor": sensor, "limit": limit, "data": None,
                    "warning": "aiion.tools.system no disponible"}

    def _voice_speak(self, text: str, voice: str | None) -> dict:
        if not text or not text.strip():
            raise ValueError("text vacío")
        try:
            from aiion.voice.tts import hablar  # type: ignore
            hablar(texto=text, voz=voice)
            return {"spoken": len(text), "voice": voice or "default"}
        except Exception as e:
            return {"spoken": 0, "voice": voice, "error": str(e)}

    def _voice_list(self) -> dict:
        try:
            from aiion.voice.tts import listar_voces  # type: ignore
            voces = listar_voces()
            return {"voices": voces if isinstance(voces, list) else [str(voces)]}
        except Exception as e:
            return {"voices": [], "error": str(e)}

    def _notify(self, title: str, content: str) -> dict:
        try:
            from aiion.tools.android import tool_notificacion  # type: ignore
            tool_notificacion(title=title, content=content)
            return {"title": title, "length": len(content)}
        except Exception as e:
            return {"title": title, "length": len(content), "error": str(e)}

    def _location(self) -> dict:
        try:
            from aiion.tools.android import tool_get_gps  # type: ignore
            data = tool_get_gps()
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            return {"location": data}
        except Exception as e:
            return {"location": None, "error": str(e)}
