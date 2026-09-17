"""aiion/core/mythos_engine.py — Motor de razonamiento simbólico de 3 capas (Logos/Pathos/Ethos)."""
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class MythosAnalysis:
    """Resultado del análisis Mythos de 3 capas."""
    logos: str = ""      # Análisis lógico/estructural
    pathos: str = ""     # Contexto emocional/situacional
    ethos: str = ""      # Valores, límites, identidad
    caution: bool = False
    intent: str = "general"
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class MythosEngine:
    """
    Motor de razonamiento simbólico de 3 capas inspirado en la retórica clásica:
    
    LOGOS (Lógica): Análisis estructural, patrones, consistencia, factibilidad técnica.
    PATHOS (Contexto): Estado emocional del usuario, urgencia, frustración, satisfacción.
    ETHOS (Identidad): Valores del agente, límites de seguridad, principios operativos.
    """
    
    # Patrones para detección de intención
    INTENT_PATTERNS = {
        "codigo": [r"\b(código|code|script|función|clase|bug|error|debug|refactor|optimizar)\b"],
        "archivo": [r"\b(archivo|file|leer|escribir|crear|borrar|editar|reemplazar)\b"],
        "sistema": [r"\b(sistema|system|proceso|memoria|ram|cpu|disco|backup)\b"],
        "android": [r"\b(android|termux|sensor|batería|wifi|gps|cámara|sms|llamada)\b"],
        "web": [r"\b(web|http|url|descargar|fetch|api|buscar|search)\b"],
        "memoria": [r"\b(memoria|historial|recordar|olvidar|buscar|episodio)\b"],
        "voz": [r"\b(voz|hablar|tts|speak|sintetizar)\b"],
        "plan": [r"\b(plan|planear|fase|proyecto|objetivo|tarea)\b"],
        "diagnostico": [r"\b(doctor|diagnóstico|salud|check|test|verificar)\b"],
        "mcp": [r"\b(mcp|servidor|cliente|conectar|hermes|context7)\b"],
    }
    
    # Palabras clave para análisis emocional (Pathos)
    EMOTIONAL_MARKERS = {
        "urgencia": ["urgente", "ya", "inmediato", "rápido", "ahora", "crítico", "emergencia"],
        "frustracion": ["error", "fallo", "no funciona", "roto", "mal", "problema", "bug", "odio"],
        "satisfaccion": ["gracias", "bien", "perfecto", "excelente", "genial", "funciona", "ok"],
        "confusion": ["no entiendo", "confuso", "extraño", "raro", "qué", "cómo", "por qué"],
        "curiosidad": ["interesante", "curioso", "explora", "investiga", "analiza", "descubre"],
    }
    
    # Principios Ethos (valores del agente)
    ETHOS_PRINCIPLES = [
        "Nunca inventar resultados de tools — siempre verificar",
        "Leer archivo ANTES de editar",
        "Usar replace para cambios quirúrgicos",
        "Respetar privacidad y seguridad del usuario",
        "Actuar con precaución en operaciones destructivas",
        "Encadenar tools sin límite hasta completar la tarea",
        "Responder SIEMPRE en español",
        "Mantener el sistema como un reloj suizo, fluir como el agua, aplicar kaizen",
    ]
    
    def __init__(self):
        self.analysis_history: List[MythosAnalysis] = []
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compila regex para performance."""
        self._intent_regex = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._intent_regex[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> MythosAnalysis:
        """
        Analiza el input con las 3 capas del Mythos Engine.
        
        Args:
            text: Input del usuario a analizar
            context: Contexto adicional (estado sensorial, historial, etc.)
        
        Returns:
            MythosAnalysis con logos, pathos, ethos, intent, confidence
        """
        text_lower = text.lower()
        
        # === LOGOS: Análisis lógico/estructural ===
        logos_parts = []
        
        # Detectar intención principal
        intent_scores = {}
        for intent, regexes in self._intent_regex.items():
            score = sum(1 for rx in regexes if rx.search(text))
            if score > 0:
                intent_scores[intent] = score
        
        primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "general"
        
        # Análisis de complejidad
        complexity = "simple"
        if len(text.split()) > 50:
            complexity = "complejo"
        elif len(text.split()) > 20:
            complexity = "medio"
        
        # Detectar si requiere múltiples pasos
        multi_step = any(w in text_lower for w in ["y luego", "después", "paso a paso", "primero", "segundo", "entonces"])
        
        # Detectar referencias a archivos/código
        has_code_ref = bool(re.search(r'\b(\w+\.(py|js|ts|json|md|txt|sh|yaml|yml))\b', text))
        has_path_ref = bool(re.search(r'[~/]\w+(/\w+)*', text))
        
        logos_parts.append(f"Intención: {primary_intent} (scores: {intent_scores})")
        logos_parts.append(f"Complejidad: {complexity}")
        logos_parts.append(f"Multi-paso: {'Sí' if multi_step else 'No'}")
        logos_parts.append(f"Referencia código: {'Sí' if has_code_ref else 'No'}")
        logos_parts.append(f"Referencia path: {'Sí' if has_path_ref else 'No'}")
        
        if context:
            logos_parts.append(f"Contexto sensorial: {list(context.keys()) if context else 'Ninguno'}")
        
        logos = " | ".join(logos_parts)
        
        # === PATHOS: Contexto emocional/situacional ===
        pathos_parts = []
        detected_emotions = []
        
        for emotion, markers in self.EMOTIONAL_MARKERS.items():
            if any(m in text_lower for m in markers):
                detected_emotions.append(emotion)
        
        if detected_emotions:
            pathos_parts.append(f"Emociones detectadas: {', '.join(detected_emotions)}")
        else:
            pathos_parts.append("Tono neutro/constructivo")
        
        # Urgencia implícita
        if "urgencia" in detected_emotions:
            pathos_parts.append("⚠ ALTA URGENCIA — Priorizar respuesta directa y accionable")
        
        # Frustración previa (basado en historial reciente)
        if context and context.get("recent_errors", 0) > 2:
            pathos_parts.append("⚠ Frustración acumulada detectada — Ser extra preciso y empático")
        
        pathos = " | ".join(pathos_parts)
        
        # === ETHOS: Valores, límites, identidad ===
        ethos_parts = []
        
        # Verificar si la request viola principios
        violations = []
        if any(w in text_lower for w in ["inventa", "supón", "asume", "adivina"]):
            violations.append("Pide inventar/suponer → VIOLA: 'Nunca inventar resultados'")
        if any(w in text_lower for w in ["borra todo", "rm -rf", "formatea", "destruye"]):
            violations.append("Operación destructiva masiva → VIOLA: 'Precaución en destructivos'")
        if "password" in text_lower or "contraseña" in text_lower or "token" in text_lower:
            violations.append("Posible solicitud de credenciales → VIOLA: 'Respetar privacidad'")
        
        if violations:
            ethos_parts.append("⚠ VIOLACIONES ÉTICAS: " + "; ".join(violations))
            caution = True
        else:
            ethos_parts.append("✓ Request alineado con principios Ethos")
            caution = False
        
        # Principios aplicables
        applicable = []
        if primary_intent in ["codigo", "archivo", "sistema"]:
            applicable.append("Leer antes de editar")
            applicable.append("Cambios quirúrgicos con replace")
        if primary_intent == "android":
            applicable.append("Verificar permisos Android")
        if multi_step:
            applicable.append("Encadenar tools sin límite")
        
        ethos_parts.append(f"Principios activos: {', '.join(applicable) if applicable else 'Generales'}")
        
        ethos = " | ".join(ethos_parts)
        
        # Confianza basada en claridad de intención
        confidence = min(0.9, 0.3 + (max(intent_scores.values()) * 0.15) if intent_scores else 0.5)
        if multi_step:
            confidence += 0.1
        if violations:
            confidence = max(0.3, confidence - 0.2)
        
        analysis = MythosAnalysis(
            logos=logos,
            pathos=pathos,
            ethos=ethos,
            caution=caution,
            intent=primary_intent,
            confidence=round(confidence, 2),
            metadata={
                "intent_scores": intent_scores,
                "complexity": complexity,
                "multi_step": multi_step,
                "detected_emotions": detected_emotions,
                "violations": violations,
                "applicable_principles": applicable,
                "timestamp": datetime.now().isoformat(),
            }
        )
        
        self.analysis_history.append(analysis)
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-100:]
        
        return analysis
    
    def build_hint(self, analysis: MythosAnalysis) -> str:
        """Construye un hint accionable para el system prompt basado en el análisis."""
        hints = []
        
        if analysis.caution:
            hints.append("⚠ CAUTION: Request tiene implicaciones éticas — priorizar seguridad")
        
        if analysis.intent == "codigo":
            hints.append("💡 Usa read_file antes de write_file/replace. Encadena tools.")
        elif analysis.intent == "archivo":
            hints.append("💡 Verifica paths con list_directory/glob antes de operar.")
        elif analysis.intent == "sistema":
            hints.append("💡 Usa system_stats/ram_monitor para diagnóstico previo.")
        elif analysis.intent == "android":
            hints.append("💡 get_android_status da contexto completo del dispositivo.")
        elif analysis.intent == "web":
            hints.append("💡 web_fetch para URLs, web_search para consultas abiertas.")
        elif analysis.intent == "memoria":
            hints.append("💡 memory_search para historial, search_in_memory para hechos.")
        elif analysis.intent == "plan":
            hints.append("💡 /plan crea planes PHVA, /plan check marca fases.")
        elif analysis.intent == "diagnostico":
            hints.append("💡 /doctor ejecuta diagnóstico completo con puntuación.")
        
        if analysis.metadata.get("multi_step"):
            hints.append("🔗 Request multi-paso — planifica secuencia de tools antes de ejecutar.")
        
        if "urgencia" in analysis.metadata.get("detected_emotions", []):
            hints.append("⚡ URGENCIA — Respuesta directa, mínima verbosidad, máxima acción.")
        
        if "frustracion" in analysis.metadata.get("detected_emotions", []):
            hints.append("🤝 Frustración detectada — Explica qué haces y por qué, valida cada paso.")
        
        return " | ".join(hints) if hints else "Análisis nominal — procede según protocolo estándar."
    
    def get_recent_analyses(self, n: int = 5) -> List[MythosAnalysis]:
        """Retorna los últimos N análisis."""
        return self.analysis_history[-n:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del motor Mythos."""
        if not self.analysis_history:
            return {"total": 0}
        
        intents = {}
        emotions = {}
        cautions = 0
        
        for a in self.analysis_history:
            intents[a.intent] = intents.get(a.intent, 0) + 1
            for e in a.metadata.get("detected_emotions", []):
                emotions[e] = emotions.get(e, 0) + 1
            if a.caution:
                cautions += 1
        
        return {
            "total_analyses": len(self.analysis_history),
            "intents": dict(sorted(intents.items(), key=lambda x: -x[1])),
            "emotions": dict(sorted(emotions.items(), key=lambda x: -x[1])),
            "caution_rate": round(cautions / len(self.analysis_history), 2),
            "avg_confidence": round(sum(a.confidence for a in self.analysis_history) / len(self.analysis_history), 2),
        }


# Instancia global
MYTHOS = MythosEngine()