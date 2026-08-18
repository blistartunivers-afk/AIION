"""aiion/intelligence/mythos.py — Análisis pre-LLM de la intención del usuario.

Adaptado de blistv11.py → core/mythos_engine.py al stack AIION.

Tres dimensiones:
- LOGOS:  qué quiere hacer (intents, complejidad)
- PATHOS: estado del sistema (RAM, batería, urgencia)
- ETHOS:  valores y seguridad (palabras peligrosas, validaciones)

Genera un bloque de pistas (build_hint) que se inyecta en el system prompt
para modular el comportamiento del modelo.
"""
from __future__ import annotations
import re
from typing import Any

from aiion.memory.ram_guard import RAMGUARD
from aiion.sensors.daemon import sensor_last


class MythosEngine:
    """Trinidad: Logos · Pathos · Ethos."""

    # Patrones de intención (detección pre-LLM)
    INTENT_PATTERNS: dict[str, str] = {
        "filesystem": r"\b(lee|leer|escrib|crea|modifica|borra|lista|busca|archivo|fichero|código|script|carpeta|directorio)\b",
        "system":     r"\b(proceso|cpu|ram|memoria|disco|pid|matar|reiniciar|monitor|termux|pkg|apt)\b",
        "android":    r"\b(batería|wifi|sensor|gps|foto|cámara|sms|llamada|notificación|linterna|brillo|volumen)\b",
        "web":        r"\b(busca|descarga|url|http|web|página|internet|navegador|curl|wget)\b",
        "memory":     r"\b(recuerda|olvida|historial|nota|memoria|apunta|guarda|anota)\b",
        "voice":      r"\b(habla|di|pronuncia|voz|tts|escucha|microf)\b",
        "evolution":  r"\b(test|prueba|evoluciona|mejora|habilidad|error|bug|skill|debug)\b",
        "meta":       r"\b(quién eres|qué eres|reflexiona|analízate|estado|salud|vers)\b",
        "self":       r"\b(kalman|mythos|cogindex|ramguard|aiion|tu nucleo|sistema|configuración)\b",
    }

    # Palabras que activan modo precaución (Ethos)
    CAUTION_WORDS: set[str] = {
        "borra", "elimina", "rm", "format", "wipe", "destroy", "drop",
        "contraseña", "password", "token", "secret", "key", "apikey",
        "sudo", "root", "chmod 777", "chown",
    }

    def analyze(self, user_input: str, sensor_ctx: dict | None = None) -> dict[str, Any]:
        """Retorna dict con logos/pathos/ethos + intent + urgency."""
        text = (user_input or "").lower()
        original_words = user_input.split() if user_input else []

        # LOGOS: detección de intención
        intents = [k for k, pat in self.INTENT_PATTERNS.items()
                   if re.search(pat, text, re.IGNORECASE)]
        if not intents:
            intents = ["general"]

        # LOGOS: complejidad estimada
        complexity = "simple"
        if len(original_words) > 20 or len(intents) > 2:
            complexity = "complex"
        if any(w in text for w in ["todos", "completo", "analiza", "migra", "refactor", "audita"]):
            complexity = "deep"

        # PATHOS: urgencia del sistema
        urgency = "normal"
        try:
            ram_p = RAMGUARD.pressure()
        except Exception:
            ram_p = 0.0
        bat = sensor_last("battery") or {}
        bat_pct = bat.get("percentage", 100)
        if ram_p > 0.85 or bat_pct < 10:
            urgency = "critical"
        elif ram_p > 0.70 or bat_pct < 20:
            urgency = "high"

        # ETHOS: validación
        caution = any(w in text for w in self.CAUTION_WORDS)

        return {
            "intents":    intents,
            "complexity": complexity,
            "urgency":    urgency,
            "caution":    caution,
            "safe":       not caution,
            "logos":      f"Tarea: {complexity} | Intenciones: {', '.join(intents)}",
            "pathos":     f"RAM: {ram_p:.0%} | Batería: {bat_pct}% | Urgencia: {urgency}",
            "ethos":      "⚠ PRECAUCIÓN activada" if caution else "✓ Operación normal",
        }

    def build_hint(self, analysis: dict[str, Any]) -> str:
        """Genera pista de razonamiento para incluir en el system prompt."""
        hints: list[str] = []
        if analysis["complexity"] == "deep":
            hints.append("- Tarea profunda: planifica primero, luego ejecuta paso a paso.")
        if analysis["complexity"] == "complex":
            hints.append("- Tarea compleja: descompón en subtareas y verifica cada paso.")
        if analysis["urgency"] == "critical":
            hints.append("- ⚠ Sistema bajo presión (RAM/batería crítica): minimiza operaciones costosas.")
        elif analysis["urgency"] == "high":
            hints.append("- ⚠ Sistema con recursos limitados: prefiere tools rápidas sobre análisis largos.")
        if analysis["caution"]:
            hints.append("- ⚠ ÉTICA: detectada operación potencialmente destructiva. "
                         "Confirma antes de ejecutar y muestra advertencias.")
        if "filesystem" in analysis["intents"] and "web" in analysis["intents"]:
            hints.append("- Tarea mixta: descarga datos de la web y procésalos en el sistema de archivos.")
        if "self" in analysis["intents"]:
            hints.append("- Pregunta sobre el propio sistema: usa /introspect o /status para datos reales.")
        return "\n".join(hints) if hints else ""

    def report(self, analysis: dict | None = None) -> str:
        """Muestra un análisis de mythos en formato /mythos."""
        if analysis is None:
            analysis = getattr(self, "_last", None) or self.analyze("status")
        intents = ", ".join(analysis.get("intents", [])) or "—"
        caution = "⚠ SÍ" if analysis.get("caution") else "no"
        return (
            f"╔══ Mythos Engine ══\n"
            f"  Logos   : {intents}\n"
            f"  Pathos  : urgency={analysis.get('urgency','?')}  complexity={analysis.get('complexity','?')}\n"
            f"  Ethos   : caution={caution}\n"
            f"╚══════════════════"
        )


# Singleton global
MYTHOS = MythosEngine()
