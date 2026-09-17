"""aiion/llm/kalman.py — Kalman filter for model selection."""
import os
import threading
import time
import sqlite3
from collections import defaultdict
from pathlib import Path
from aiion.config import AIION_HOME
from aiion.cli.ui import c, N_GREEN, N_YELLOW, N_RED, N_BLUE, N_WHITE, N_DIM, N_ORANGE

# ── Evolución DB ────────────────────────────────────────────────────────
EVOLUTION_DB = AIION_HOME / "evolution.db"

# ── Modelos gratuitos por proveedor (puede ampliarse) ─────────────────────
FREE_MODELS = {
    "ollama": [],  # se puede poblar desde config si se desea
    "openrouter": [],
    "gemini": [],
}
RETIRED_MODELS = set()  # modelos retirados por quota/fallos persistentes

def _log_silent_error(context: str, exc: BaseException = None):
    """Registra un error silenciado (en except: pass) para depuración."""
    try:
        if exc is not None:
            import traceback
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            msg = f"{context}: {type(exc).__name__}: {exc}\n{''.join(tb[-3:])}"
        else:
            msg = context
        # En un entorno real se podría guardar en un buffer o log.
        # Por ahora, solo imprimir si es crítico.
        if exc is not None:
            print(f"[SILENT ERROR] {msg}", file=sys.stderr)
    except Exception:
        pass  # nunca debe romper el flujo principal


class KalmanModelSelector:
    """
    Filtro Kalman escalar por modelo:
      x̂ = estimación del score (latencia normalizada × tasa de éxito)
      P = varianza del error de estimación
    Al recibir una observación real, actualiza x̂ con ganancia óptima K.

    Score: 1.0 = perfecto (rápido, sin errores), 0.0 = pésimo.
    """
    Q = 0.01   # ruido del proceso (variación esperada del score)
    R = 0.05   # ruido de medición (incertidumbre de cada observación)

    def _model_key(self, prov_id: str, model: str) -> str:
        return f"{prov_id}::{model}"

    def __init__(self):
        # Por modelo: {"x": score_estimado, "P": varianza, "n": observaciones}
        self._state: dict = defaultdict(lambda: {"x": 0.7, "P": 1.0, "n": 0})
        self._fail_ts: dict = defaultdict(list)   # timestamps de fallos recientes
        self._lock = threading.Lock()
        self._init_from_db()

    def _init_from_db(self):
        """Inicializa el estado desde los últimos 5 días en evolution.db."""
        try:
            con = sqlite3.connect(str(EVOLUTION_DB), timeout=5.0)
            five_days_ago = time.time() - (5 * 24 * 3600)
            cursor = con.cursor()
            cursor.execute("SELECT prov_id, model, success, latency_ms FROM model_performance WHERE ts > ?", (five_days_ago,))
            for prov, model, succ, lat in cursor.fetchall():
                self._apply_observation(prov, model, bool(succ), lat)
        except Exception as _e_silent:
            _log_silent_error("main", _e_silent)
        finally:
            try:
                con.close()
            except Exception:
                pass

    def _apply_observation(self, prov_id, model, success, latency_ms):
        """Lógica interna de actualización Kalman (sin DB)."""
        lat_norm = max(0.0, 1.0 - latency_ms / 10_000.0)
        obs_score = (0.7 * float(success) + 0.3 * lat_norm) if success else 0.0
        k = self._model_key(prov_id, model)
        s = self._state[k]
        # Predicción
        P_pred = s["P"] + self.Q
        # Ganancia Kalman
        K = P_pred / (P_pred + self.R)
        # Actualización
        s["x"] = s["x"] + K * (obs_score - s["x"])
        s["P"] = (1 - K) * P_pred
        s["n"] += 1

    def update(self, prov_id: str, model: str,
               success: bool, latency_ms: float):
        """
        Actualiza el filtro, persiste en DB y actualiza estado.
        """
        # 1. Persistir
        try:
            con = sqlite3.connect(str(EVOLUTION_DB), timeout=5.0)
            con.execute("INSERT INTO model_performance VALUES (?,?,?,?,?)",
                        (prov_id, model, int(success), latency_ms, time.time()))
            con.commit()
        except Exception as _e_silent:
            _log_silent_error("main", _e_silent)
        finally:
            try:
                con.close()
            except Exception:
                pass

        # 2. Actualizar estado
        with self._lock:
            self._apply_observation(prov_id, model, success, latency_ms)

            # Registrar timestamp de fallo para cooldown de quota
            if not success:
                now = time.time()
                self._fail_ts[self._model_key(prov_id, model)].append(now)
                # Mantener solo últimos 60 min
                self._fail_ts[self._model_key(prov_id, model)] = [t for t in self._fail_ts[self._model_key(prov_id, model)] if now - t < 3600]

    def in_quota_cooldown(self, prov_id: str, model: str,
                          window_s: float = 300.0) -> bool:
        """
        Retorna True si el modelo ha fallado ≥3 veces en los últimos window_s
        segundos (señal de quota/rate-limit — esperar antes de reintentar).
        """
        k = self._model_key(prov_id, model)
        now = time.time()
        recent = [t for t in self._fail_ts.get(k, []) if now - t < window_s]
        return len(recent) >= 3

    def best_model(self, prov_id: str, candidates: list) -> str:
        """
        Devuelve el modelo candidato con mayor score Kalman estimado
        que NO esté en cooldown de quota.
        Si todos están en cooldown, devuelve el de menor cooldown count.
        candidates: lista de nombres de modelo para este proveedor.
        """
        if not candidates:
            return ""

        # Filtrar modelos libres conocidos + candidatos del pool
        free = FREE_MODELS.get(prov_id, [])
        # Combinar: primero los libres que también están en candidates
        priority = [m for m in candidates if any(f.lower() in m.lower() for f in free)]
        # Agregar el resto (modelos cacheados del gestor que no matchean free)
        priority += [m for m in candidates if m not in priority]
        if not priority:
            priority = candidates

        scored = []
        for m in priority:
            k = self._model_key(prov_id, m)
            s = self._state[k]
            cdwn = self.in_quota_cooldown(prov_id, m)
            scored.append((s["x"], cdwn, m))

        # Ordenar: primero sin cooldown, luego por score descendente
        scored.sort(key=lambda t: (t[1], -t[0]))
        return scored[0][2]

    def score(self, prov_id: str, model: str) -> float:
        k = self._model_key(prov_id, model)
        return round(self._state[k]["x"], 3)

    def report(self) -> str:
        """Reporte texto del estado del selector — para /stats o introspect."""
        lines = [f"\n{c(N_GREEN,'╔══ Kalman Model Selector ══════════════════')}"]
        for k, s in sorted(self._state.items(), key=lambda x: -x[1]["x"]):
            prov, model = k.split("::", 1)
            cdwn = self.in_quota_cooldown(prov, model)
            cdwn_str = c(N_ORANGE, " [cooldown]") if cdwn else ""
            col = N_GREEN if s["x"] > 0.6 else N_YELLOW if s["x"] > 0.3 else N_RED
            score_str = f"{s['x']:.3f}"
            n_str = f"n={s['n']}"
            lines.append(
                f"{c(N_GREEN,'║')} {c(col, score_str)} "
                f"{c(N_BLUE, prov[:3].upper())} {c(N_WHITE, model[:30])}"
                f" {c(N_DIM, n_str)}{cdwn_str}"
            )
        lines.append(c(N_GREEN, '╚'+'═'*43))
        return "\n".join(lines)


# Instancia global
KALMAN = KalmanModelSelector()