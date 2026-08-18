"""aiion/intelligence/kalman.py — Selector adaptativo de modelos vía Filtro Kalman.

Inspirado en blistv11.py (líneas 1387-1530) pero adaptado al stack AIION:
- Persistencia vía aiion.db (no sqlite3 directo)
- Estado en memoria + tabla `model_performance` (nueva migración v3)
- Thread-safe con RLock

Score: 1.0 = perfecto (rápido, sin errores), 0.0 = pésimo.
x̂ = estimación del score (latencia normalizada × tasa de éxito)
P  = varianza del error de estimación
Al recibir una observación real, actualiza x̂ con ganancia óptima K.
"""
from __future__ import annotations
import time
import threading
from collections import defaultdict
from typing import Optional

from aiion.config import SENSOR_DB
from aiion.db import get_conn

Q = 0.01   # ruido del proceso (variación esperada del score)
R = 0.05   # ruido de medición (incertidumbre de cada observación)

FREE_MODELS: dict[str, list[str]] = {
    "ollama":   ["minimax-m3", "qwen3-coder:480b", "deepseek-v3.1:671b", "gemma3:27b"],
    "openrouter": ["deepseek/deepseek-chat-v3.1:free", "qwen/qwen-2.5-coder-32b-instruct:free"],
    "gemini":   ["gemini-2.5-flash", "gemini-2.5-pro"],
}


class KalmanModelSelector:
    """Filtro Kalman escalar por (proveedor, modelo)."""

    def __init__(self) -> None:
        # Por modelo: {"x": score_estimado, "P": varianza, "n": observaciones}
        self._state:   dict = defaultdict(lambda: {"x": 0.7, "P": 1.0, "n": 0})
        self._fail_ts: dict = defaultdict(list)   # timestamps de fallos recientes
        self._lock = threading.RLock()
        self._init_from_db()

    # ── Persistencia ───────────────────────────────────────────────────────
    def _init_from_db(self) -> None:
        """Carga estado desde los últimos 5 días."""
        try:
            five_days_ago = time.time() - (5 * 24 * 3600)
            with get_conn() as con:
                rows = con.execute(
                    "SELECT prov_id, model, success, latency_ms "
                    "FROM model_performance WHERE ts > ?",
                    (five_days_ago,),
                ).fetchall()
            for prov, model, succ, lat in rows:
                self._apply_observation(prov, model, bool(succ), float(lat))
        except Exception as e:  # silent fail: la tabla aún no existe en DB nueva
            pass

    # ── Núcleo Kalman ─────────────────────────────────────────────────────
    @staticmethod
    def _model_key(prov_id: str, model: str) -> str:
        return f"{prov_id}::{model}"

    def _apply_observation(self, prov_id: str, model: str,
                           success: bool, latency_ms: float) -> None:
        """Actualización Kalman (sin DB)."""
        lat_norm  = max(0.0, 1.0 - latency_ms / 10_000.0)
        obs_score = (0.7 * float(success) + 0.3 * lat_norm) if success else 0.0
        with self._lock:
            s = self._state[self._model_key(prov_id, model)]
            # Predicción
            P_pred = s["P"] + Q
            # Ganancia Kalman
            K = P_pred / (P_pred + R)
            # Actualización
            s["x"] = s["x"] + K * (obs_score - s["x"])
            s["P"] = (1 - K) * P_pred
            s["n"] += 1

    # ── API pública ───────────────────────────────────────────────────────
    def update(self, prov_id: str, model: str,
               success: bool, latency_ms: float) -> None:
        """Persiste + actualiza estado."""
        # 1. Persistir
        try:
            with get_conn() as con:
                con.execute(
                    "INSERT INTO model_performance "
                    "(prov_id, model, success, latency_ms, ts) VALUES (?,?,?,?,?)",
                    (prov_id, model, int(bool(success)), float(latency_ms), time.time()),
                )
        except Exception:
            pass  # tabla aún no existe — primer arranque

        # 2. Estado
        self._apply_observation(prov_id, model, success, latency_ms)

        # 3. Registrar fallo para cooldown de quota
        if not success:
            now = time.time()
            k = self._model_key(prov_id, model)
            with self._lock:
                self._fail_ts[k].append(now)
                # Mantener solo últimos 60 min
                self._fail_ts[k] = [t for t in self._fail_ts[k] if now - t < 3600]

    def in_quota_cooldown(self, prov_id: str, model: str,
                          window_s: float = 300.0) -> bool:
        """True si el modelo ha fallado ≥3 veces en los últimos `window_s` segundos."""
        k = self._model_key(prov_id, model)
        now = time.time()
        with self._lock:
            recent = [t for t in self._fail_ts.get(k, []) if now - t < window_s]
        return len(recent) >= 3

    def best_model(self, prov_id: str, candidates: list[str]) -> str:
        """Devuelve el candidato con mayor score Kalman que NO esté en cooldown.

        Si todos están en cooldown, devuelve el de menor conteo de cooldown.
        """
        if not candidates:
            return ""

        # Priorizar modelos FREE del proveedor si están en candidates
        free = FREE_MODELS.get(prov_id, [])
        priority = [m for m in candidates
                    if any(f.lower() in m.lower() for f in free)]
        priority += [m for m in candidates if m not in priority]
        if not priority:
            priority = candidates

        with self._lock:
            scored = []
            for m in priority:
                k    = self._model_key(prov_id, m)
                s    = self._state[k]
                cdwn = self.in_quota_cooldown(prov_id, m)
                scored.append((s["x"], cdwn, m))
        # Sin cooldown primero, luego score descendente
        scored.sort(key=lambda t: (t[1], -t[0]))
        return scored[0][2] if scored else ""

    def score(self, prov_id: str, model: str) -> float:
        with self._lock:
            return round(self._state[self._model_key(prov_id, model)]["x"], 3)

    def report(self) -> str:
        """Reporte de estado para /stats o /introspect."""
        with self._lock:
            lines = ["╔══ Kalman Model Selector ══════════════════"]
            for k, s in sorted(self._state.items(), key=lambda x: -x[1]["x"]):
                prov, model = k.split("::", 1)
                cdwn = self.in_quota_cooldown(prov, model)
                tag  = " [cooldown]" if cdwn else ""
                lines.append(f"  {s['x']:.3f}  {prov[:3].upper():3s}  {model[:30]:30s}  n={s['n']}{tag}")
            lines.append("╚" + "═" * 43)
        return "\n".join(lines)

    def reset(self) -> None:
        """Limpia el estado (útil para tests)."""
        with self._lock:
            self._state.clear()
            self._fail_ts.clear()


# Singleton global
KALMAN = KalmanModelSelector()
