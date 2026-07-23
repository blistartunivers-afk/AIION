"""
aiion/subagentes/base.py — Clase base Subagente + decorator de registry.

Patrón: cada subagente es un módulo con clase que hereda de Subagente.
El decorador @subagente auto-registra en REGISTRY global.

Uso:
    from aiion.subagentes.base import Subagente, subagente, get_subagente

    @subagente
    class MiAgente(Subagente):
        name = "mi"
        capabilities = ["do_x", "do_y"]
        def handle(self, capability, args):
            ...
"""
from __future__ import annotations
import inspect
from typing import Any, Callable


# Registry global {name: instancia}
REGISTRY: dict[str, "Subagente"] = {}


class SubagenteError(Exception):
    """Error de subagente (no registrado, capability negada, etc)."""


class Subagente:
    """Clase base para todos los sub-agentes AIION.

    Subclases deben definir:
      - name: str (identificador único)
      - description: str (humana)
      - capabilities: list[str] (capacidades que ofrece)
      - handle(capability, args) -> dict  (implementación)

    Opcional:
      - enabled: bool = True (puede deshabilitarse sin perder el registro)
      - version: str = "0.1"
    """

    name: str = ""
    description: str = ""
    capabilities: list[str] = []
    version: str = "0.1"
    enabled: bool = True

    # -------------------- API pública --------------------
    def can(self, capability: str) -> bool:
        """¿Este subagente ofrece la capability?"""
        return self.enabled and capability in self.capabilities

    def handle(self, capability: str, args: dict | None = None) -> dict:
        """Ejecuta una capability. Subclases DEBEN override."""
        raise NotImplementedError(
            f"{type(self).__name__} no implementa handle()"
        )

    def describe(self) -> dict:
        """Descripción serializable (para /agents, /status, etc)."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "capabilities": list(self.capabilities),
        }

    def dispatch(self, capability: str, args: dict | None = None) -> dict:
        """Punto de entrada con capability-check.

        Retorna dict estándar:
          {"ok": bool, "subagente": str, "capability": str,
           "result": Any, "error": str|None}
        """
        if not self.enabled:
            return self._err("subagente deshabilitado")
        if not self.can(capability):
            return self._err(
                f"capability '{capability}' no permitida "
                f"(ofrecidas: {self.capabilities})"
            )
        try:
            result = self.handle(capability, args or {})
            return {
                "ok": True,
                "subagente": self.name,
                "capability": capability,
                "result": result,
                "error": None,
            }
        except Exception as e:
            return self._err(str(e))

    # -------------------- internos --------------------
    def _err(self, msg: str) -> dict:
        return {
            "ok": False,
            "subagente": self.name,
            "capability": "",
            "result": None,
            "error": msg,
        }

    def __repr__(self) -> str:
        return f"<Subagente {self.name} caps={self.capabilities}>"


# -------------------- Decorator / registry --------------------
def subagente(cls: type) -> type:
    """Decorator: registra una subclase de Subagente en REGISTRY.

    Valida que la clase tenga los atributos requeridos y
    crea una instancia singleton accesible por `cls.instance`.
    """
    if not inspect.isclass(cls) or not issubclass(cls, Subagente):
        raise SubagenteError(
            f"@subagente solo aplica a subclases de Subagente (got {cls})"
        )
    if not cls.name:
        raise SubagenteError(f"{cls.__name__} debe definir .name")
    if not cls.capabilities:
        raise SubagenteError(
            f"{cls.__name__} debe definir .capabilities (no vacía)"
        )
    if cls.name in REGISTRY:
        # permitir redefinición en tests, pero loguear
        pass

    instance = cls()
    REGISTRY[cls.name] = instance
    cls.instance = instance  # singleton por clase
    return cls


def get_subagente(name: str) -> Subagente:
    """Obtiene subagente registrado por nombre. Lanza SubagenteError si no."""
    if name not in REGISTRY:
        raise SubagenteError(
            f"subagente '{name}' no registrado "
            f"(disponibles: {list(REGISTRY)})"
        )
    return REGISTRY[name]


def list_subagentes(only_enabled: bool = True) -> list[Subagente]:
    """Lista instancias registradas."""
    items = list(REGISTRY.values())
    if only_enabled:
        items = [s for s in items if s.enabled]
    return items


def reset_registry() -> None:
    """Limpia el registry (uso en tests)."""
    REGISTRY.clear()
