"""aiion/intelligence — Capa de inteligencia artificial del agente.

Componentes:
- KalmanModelSelector: filtro Kalman escalar que aprende qué modelo es
  el mejor para cada (proveedor, modelo) según latencia y tasa de éxito.
  Rota automáticamente al mejor modelo disponible que no esté en cooldown.

- MythosEngine: análisis pre-LLM de la intención del usuario (logos),
  urgencia del sistema (pathos) y validación ética (ethos).
  Detecta tareas destructivas y modula el system prompt.

- CircuitBreaker: protege cada tool de bucles infinitos y fallos en
  cascada. Estados CLOSED → OPEN → HALF_OPEN. Persiste en DB.

- CodeInvest: análisis profundo de código — métricas de complejidad
  (ciclomática, cognitiva, Halstead, Maintainability Index), code smells,
  detección de patrones/anti-patrones, dependencias circulares, código
  duplicado, código muerto, God Classes, acoplamiento/cohesión.

Todos son adaptaciones de blistv11.py al ecosistema AIION:
- Usan aiion.db (no sqlite3 directo)
- Usan aiion.config (no constantes globales)
- Usan aiion.sensors.daemon (no core.sensor_daemon)
"""
from aiion.intelligence.kalman           import KalmanModelSelector, KALMAN
from aiion.intelligence.mythos           import MythosEngine,         MYTHOS
from aiion.intelligence.circuit_breaker  import CircuitBreaker,       CB
from aiion.intelligence.code_invest      import (
    CodeInvest, CodeInvestReport, CodeMetric, CodeSmell,
    ComplexityMetrics, ClassMetrics, ModuleMetrics,
    DependencyEdge, CircularDependency, CodeDuplicate,
    DesignPattern, AntiPattern, DeadCode,
    CODE_INVEST_TOOLS,
    code_invest_analyze, code_invest_file, code_invest_smells,
    code_invest_dependencies, code_invest_duplicates, code_invest_patterns,
    code_invest_dead_code, code_invest_complexity, code_invest_god_classes,
)

__all__ = [
    "KalmanModelSelector", "KALMAN",
    "MythosEngine",        "MYTHOS",
    "CircuitBreaker",      "CB",
    "CodeInvest", "CodeInvestReport", "CodeMetric", "CodeSmell",
    "ComplexityMetrics", "ClassMetrics", "ModuleMetrics",
    "DependencyEdge", "CircularDependency", "CodeDuplicate",
    "DesignPattern", "AntiPattern", "DeadCode",
    "CODE_INVEST_TOOLS",
    "code_invest_analyze", "code_invest_file", "code_invest_smells",
    "code_invest_dependencies", "code_invest_duplicates", "code_invest_patterns",
    "code_invest_dead_code", "code_invest_complexity", "code_invest_god_classes",
]
