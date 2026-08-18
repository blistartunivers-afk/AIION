"""aiion/intelligence/circuit_breaker.py — Circuit Breaker para tools.

Adaptado de blistv11.py → core/circuit_breaker.py al stack AIION.

Estados por tool:
- CLOSED     → ok, se ejecuta
- OPEN       → bloqueado (tras N fallos), espera cooldown
- HALF_OPEN  → probando recuperación

Persiste en tabla `circuit_breaker_state` (migración v3).
"""
from __future__ import annotations
import time
import threading
from collections import defaultdict
from typing import Optional

from aiion.db import get_conn


class CircuitBreaker:
    """Protege cada tool de bucles infinitos y fallos en cascada.

    Estados: CLOSED (ok) → OPEN (bloqueado) → HALF_OPEN (probando).
    """

    def __init__(self, threshold: int = 3, cooldown: float = 30.0) -> None:
        self._fails:     dict[str, int]   = defaultdict(int)
        self._last_fail: dict[str, float] = defaultdict(float)
        self._state:     dict[str, str]   = defaultdict(lambda: "CLOSED")
        self._threshold: int              = threshold
        self._cooldown:  float            = cooldown
        self._lock = threading.RLock()
        self._init_from_db()

    # ── Persistencia ────────────────────────────────────────────────────
    def _init_from_db(self) -> None:
        """Carga estado persistente (fails, last_fail, state) por tool."""
        try:
            with get_conn() as con:
                rows = con.execute(
                    "SELECT tool, fails, last_fail, state FROM circuit_breaker_state"
                ).fetchall()
            for tool, fails, last_fail, state in rows:
                self._fails[tool]     = int(fails)
                self._last_fail[tool] = float(last_fail)
                self._state[tool]     = state or "CLOSED"
        except Exception:
            pass  # tabla aún no existe, modo en memoria

    def _persist(self, tool: str) -> None:
        """Guarda estado de una tool en la DB (best-effort)."""
        try:
            with get_conn() as con:
                con.execute(
                    """INSERT INTO circuit_breaker_state (tool, fails, last_fail, state, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(tool) DO UPDATE SET
                         fails     = excluded.fails,
                         last_fail = excluded.last_fail,
                         state     = excluded.state,
                         updated_at = excluded.updated_at""",
                    (tool, self._fails[tool], self._last_fail[tool],
                     self._state[tool], time.time()),
                )
        except Exception:
            pass  # no bloquear operación si DB no está lista

    # ── API pública ─────────────────────────────────────────────────────
    def can_call(self, name: str) -> bool:
        """¿Se puede llamar a esta tool? Aplica lógica de cooldown."""
        with self._lock:
            state = self._state[name]
            if state == "CLOSED":
                return True
            if state == "OPEN":
                if time.time() - self._last_fail[name] > self._cooldown:
                    self._state[name] = "HALF_OPEN"
                    self._persist(name)
                    return True
                return False
            return True  # HALF_OPEN → permite 1 prueba

    def record_success(self, name: str) -> None:
        with self._lock:
            self._fails[name] = 0
            self._state[name] = "CLOSED"
        self._persist(name)

    def record_failure(self, name: str) -> None:
        with self._lock:
            self._fails[name]    += 1
            self._last_fail[name] = time.time()
            if self._fails[name] >= self._threshold:
                self._state[name] = "OPEN"
        self._persist(name)

    def status(self, name: str) -> str:
        with self._lock:
            return self._state[name]

    def get_all_states(self) -> dict[str, dict]:
        with self._lock:
            return {
                name: {
                    "state":     state,
                    "fails":     self._fails[name],
                    "last_fail": self._last_fail[name],
                }
                for name, state in self._state.items()
            }

    def open_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._state.values() if s == "OPEN")

    def reset(self, name: Optional[str] = None) -> None:
        """Reset de una tool o de todas."""
        with self._lock:
            if name:
                self._fails[name]     = 0
                self._state[name]     = "CLOSED"
                self._last_fail[name] = 0.0
            else:
                self._fails.clear()
                self._state.clear()
                self._last_fail.clear()
        # Persistir reset
        try:
            with get_conn() as con:
                if name:
                    con.execute("DELETE FROM circuit_breaker_state WHERE tool = ?", (name,))
                else:
                    con.execute("DELETE FROM circuit_breaker_state")
        except Exception:
            pass

    def report(self) -> str:
        """Reporte legible para /cb o /introspect."""
        with self._lock:
            if not self._state:
                return "Circuit breakers: (sin registros, todas las tools sanas)"
            lines = [f"╔══ Circuit Breakers (threshold={self._threshold}, cooldown={self._cooldown}s) ══"]
            for name, st in sorted(self._state.items()):
                tag  = ""
                icon = "✓"
                if st == "OPEN":
                    icon = "✗"
                    tag  = f" [fails={self._fails[name]}]"
                elif st == "HALF_OPEN":
                    icon = "?"
                    tag  = " (probando)"
                lines.append(f"  {icon} {name:25s} → {st}{tag}")
            lines.append(f"╚  Abiertos: {self.open_count()}/{len(self._state)}" + "═" * 15)
        return "\n".join(lines)


# Singleton global
CB = CircuitBreaker()
