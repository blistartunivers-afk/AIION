"""aiion/llm/keys.py — Carga y rotación del pool de API keys de Ollama Cloud con selección de modelo mediante filtro Kalman."""
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from aiion.config import AIION_HOME, PREFERRED_MODELS
from aiion.db import init_db
from aiion.cli.ui import c, YL, N_GREEN, N_YELLOW, N_RED, N_BLUE, N_WHITE, N_DIM, N_ORANGE

# ── Evolución DB ────────────────────────────────────────────────────────
EVOLUTION_DB = AIION_HOME / "evolution.db"

# ── Modelos gratuitos por proveedor (Ollama Cloud trata todos como accesibles con key) ─────
FREE_MODELS = {
    "ollama": [],  # se puede poblar desde config si se desea
}
RETIRED_MODELS = set()  # modelos retirados por quota/fallos persistentes


class PoolCooldownError(RuntimeError):
    """No queda una combinación de clave y modelo disponible por ahora."""


_KEY_HEALTH = {}
_KEY_LOCK = threading.RLock()


def _key_candidates():
    return list(dict.fromkeys([STATE["model"]] + PREFERRED_MODELS))


def record_key_failure(status: int, retry_after: float = 0.0) -> None:
    """Autenticación afecta la clave; cuota y modelo afectan la combinación."""
    scope = None if status in (401, 402, 403) else STATE["model"]
    duration = {401: 300, 402: 300, 403: 60, 404: 3600,
                410: 3600, 429: 65}.get(status, 5)
    identity = (STATE["provider"], current_key(), scope)
    with _KEY_LOCK:
        _KEY_HEALTH[identity] = max(
            _KEY_HEALTH.get(identity, 0), time.time() + max(duration, retry_after))

def _log_silent_error(context: str, exc: BaseException = None):
    """Registra un error silenciado (en except: pass) para depuración."""
    try:
        if exc is not None:
            import traceback, sys
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            msg = f"{context}: {type(exc).__name__}: {exc}\n{''.join(tb[-3:])}"
            print(f"[SILENT ERROR] {msg}", file=sys.stderr)
        else:
            print(f"[SILENT ERROR] {context}", file=sys.stderr)
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
            con = init_db(EVOLUTION_DB)
            five_days_ago = time.time() - (5 * 24 * 3600)
            cursor = con.cursor()
            cursor.execute("SELECT prov_id, model, success, latency_ms FROM model_performance WHERE ts > ?", (five_days_ago,))
            for prov, model, succ, lat in cursor.fetchall():
                self._apply_observation(prov, model, bool(succ), lat)
        except Exception as _e_silent:
            _log_silent_error("main", _e_silent)

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
            con = init_db(EVOLUTION_DB)
            con.execute("INSERT INTO model_performance VALUES (?,?,?,?,?)",
                        (prov_id, model, int(success), latency_ms, time.time()))
            con.commit()
        except Exception as _e_silent:
            _log_silent_error("main", _e_silent)

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

# ── Estado de keys y modelo ─────────────────────────────────────────────────────
STATE = {
    "model": "",           # modelo actual seleccionado
    "api_keys": [],        # pool de API keys cargadas
    "key_index": 0,        # índice de la key en uso
    "use_cloud": False,    # True si se usa Ollama Cloud, False para local
    "provider": "ollama",  # id de proveedor para Kalman (ollama, openrouter, gemini)
}

def load_api_keys():
    """Carga las API keys desde variable de entorno o archivos."""
    env = os.environ.get("OLLAMA_API_KEY", "").strip()
    if env:
        return list(dict.fromkeys(k.strip() for k in env.split(",") if k.strip()))
    kf = AIION_HOME / "ollama_keys"
    if kf.exists():
        return [l.strip() for l in kf.read_text().splitlines() if l.strip()]
    kf2 = AIION_HOME / "ollama_key"
    if kf2.exists():
        return [kf2.read_text().strip()]
    shared = Path.home() / ".blist_keys"
    if shared.exists():
        keys = []
        for raw in shared.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                provider, key, *_ = (part.strip() for part in line.split("|"))
                if provider.lower() != "ollama":
                    continue
            else:
                key = line
            if key and key not in keys:
                keys.append(key)
        return keys
    return []

def current_key():
    """Devuelve la key actual según el índice."""
    keys = STATE["api_keys"]
    return keys[STATE["key_index"] % len(keys)] if keys else ""

def rotate_key():
    """Elige otra clave sana; si se agotan, prueba los modelos candidatos."""
    keys = STATE["api_keys"]
    if not keys:
        raise PoolCooldownError("No hay claves configuradas.")
    start = STATE["key_index"] % len(keys)
    now = time.time()
    with _KEY_LOCK:
        for model in _key_candidates():
            for step in range(1, len(keys) + 1):
                index = (start + step) % len(keys)
                key = keys[index]
                identity = (STATE["provider"], key)
                if (_KEY_HEALTH.get((*identity, None), 0) <= now and
                        _KEY_HEALTH.get((*identity, model), 0) <= now):
                    STATE.update(key_index=index, model=model)
                    print(c(YL, f"  🔑 Pool: entrada {index + 1}/{len(keys)} | {model}"))
                    return key
    raise PoolCooldownError("Todas las claves y modelos están en espera; reintenta más tarde.")

# Para compatibilidad con código que espera estas funciones
def _kalman_record(prov_id: str, model: str, success: bool, t0: float):
    """Registra resultado en Kalman. Llamar desde client después de cada llamada."""
    latency = (time.time() - t0) * 1000
    KALMAN.update(prov_id, model, success, latency)
