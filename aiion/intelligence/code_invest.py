"""aiion/intelligence/code_invest.py — Code Invest: Análisis profundo de código.

Módulo de inteligencia de código para AIION. Capacidades:
- Análisis de complejidad ciclomática y cognitiva
- Detección de deuda técnica y code smells
- Análisis de dependencias y acoplamiento
- Detección de patrones (patrones de diseño, anti-patrones)
- Métricas de calidad: complejidad ciclomática, cognitiva, acoplamiento, cohesión
- Detección de code smells: God classes, long methods, feature envy, etc.
- Análisis de dependencias y grafo de acoplamiento
- Detección de código muerto, código duplicado, complejidad ciclomática
- Métricas de Halstead, Maintainability Index, Cognitive Complexity
- Detección de code smells: God Class, Long Method, Feature Envy, Data Class, etc.
- Análisis de dependencias circulares, acoplamiento aferente/eferente
- Detección de código muerto, código duplicado (similitud)
- Métricas de mantenibilidad (Maintainability Index, Cognitive Complexity)
- Detección de patrones: Singleton, Factory, Observer, Strategy, etc.
- Anti-patrones: God Class, Spaghetti Code, Spaghetti SQL, etc.
"""

from __future__ import annotations
import ast
import os
import re
import json
import hashlib
import subprocess
import subprocess as sp
from pathlib import Path
from typing import Any, Dict, List, Set, Dict, Tuple, Optional, Set
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
import subprocess
import subprocess as sp
import ast
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES — Métricas y hallazgos
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CodeMetric:
    """Métrica individual de código."""
    name: str
    value: float
    threshold: float
    status: str  # "ok" | "warning" | "critical"
    description: str


@dataclass
class CodeSmell:
    """Code smell detectado."""
    type: str                    # "god_class", "long_method", "feature_envy", etc.
    severity: str                # "critical" | "warning" | "info"
    file: str
    line: int
    symbol: str                  # clase, método, función
    message: str
    metric_value: float = 0.0
    threshold: float = 0.0
    suggestion: str = ""


@dataclass
class ComplexityMetrics:
    """Métricas de complejidad para una función/método."""
    cyclomatic: int = 1
    cognitive: int = 0
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    halstead_effort: float = 0.0
    maintainability_index: float = 100.0
    lines_of_code: int = 0
    logical_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    max_nesting: int = 0
    param_count: int = 0
    local_vars: int = 0


@dataclass
class ClassMetrics:
    """Métricas a nivel de clase."""
    name: str
    file: str
    line: int
    methods: int = 0
    fields: int = 0
    loc: int = 0
    wmc: int = 0              # Weighted Methods per Class (suma complejidad ciclomática)
    rfc: int = 0              # Response For Class
    cbo: int = 0              # Coupling Between Objects
    lcom: float = 0.0         # Lack of Cohesion of Methods
    dit: int = 0              # Depth of Inheritance Tree
    noc: int = 0              # Number of Children
    is_god_class: bool = False
    is_data_class: bool = False
    god_class_score: float = 0.0


@dataclass
class ModuleMetrics:
    """Métricas a nivel de módulo/archivo."""
    file: str
    loc: int = 0
    lloc: int = 0             # Logical lines of code
    classes: int = 0
    functions: int = 0
    imports: int = 0
    complexity_avg: float = 0.0
    complexity_max: int = 0
    maintainability_index: float = 100.0
    comment_ratio: float = 0.0
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


@dataclass
class DependencyEdge:
    """Arista en el grafo de dependencias."""
    from_module: str
    to_module: str
    type: str                 # "import", "import_from", "inherit", "compose"
    line: int


@dataclass
class CircularDependency:
    """Ciclo de dependencia detectado."""
    cycle: List[str]
    severity: str             # "critical" | "warning"


@dataclass
class CodeDuplicate:
    """Bloque de código duplicado."""
    file_a: str
    line_a: int
    file_b: str
    line_b: int
    lines: int
    similarity: float
    code_snippet: str


@dataclass
class DesignPattern:
    """Patrón de diseño detectado."""
    pattern: str              # "singleton", "factory", "observer", "strategy", etc.
    confidence: float         # 0.0 - 1.0
    file: str
    class_name: str
    evidence: List[str]


@dataclass
class AntiPattern:
    """Anti-patrón detectado."""
    pattern: str              # "god_class", "spaghetti_code", "spaghetti_sql", etc.
    severity: str
    file: str
    symbol: str
    line: int
    evidence: List[str]
    suggestion: str


@dataclass
class DeadCode:
    """Código muerto detectado."""
    type: str                 # "unused_function", "unused_class", "unused_import", "dead_code"
    file: str
    symbol: str
    line: int
    confidence: float


@dataclass
class CodeInvestReport:
    """Reporte completo de Code Invest."""
    timestamp: str
    project_root: str
    files_analyzed: int
    total_loc: int
    total_lloc: int
    total_classes: int
    total_functions: int
    avg_complexity: float
    max_complexity: int
    avg_maintainability: float
    file_metrics: List[ModuleMetrics]
    class_metrics: List[ClassMetrics]
    function_metrics: Dict[str, ComplexityMetrics]  # key: "file:func"
    code_smells: List[CodeSmell]
    circular_dependencies: List[CircularDependency]
    code_duplicates: List[CodeDuplicate]
    design_patterns: List[DesignPattern]
    anti_patterns: List[AntiPattern]
    dead_code: List[DeadCode]
    dependency_graph: List[DependencyEdge]
    coupling_metrics: Dict[str, Dict[str, float]]  # module -> {afferent, efferent, instability}
    summary: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════
# VISITORES AST — Análisis estático
# ═══════════════════════════════════════════════════════════════════════════

class ComplexityVisitor(ast.NodeVisitor):
    """Calcula complejidad ciclomática, cognitiva, métricas de Halstead, etc."""
    
    def __init__(self, source: str, file_path: str):
        self.source = source
        self.file_path = file_path
        self.lines = source.splitlines()
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.function_metrics: Dict[str, ComplexityMetrics] = {}
        self.class_metrics: List[ClassMetrics] = []
        self.imports: List[str] = []
        self.exports: List[str] = []
        self._nesting = 0
        self._max_nesting = 0
        
    def visit(self, node: ast.AST):
        """Override para trackear nesting."""
        old_nesting = self._nesting
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
            self._nesting += 1
            self._max_nesting = max(self._max_nesting, self._nesting)
        super().visit(node)
        self._nesting = old_nesting
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}" if module else alias.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_function(node, is_method=bool(self.current_class))
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_function(node, is_method=bool(self.current_class))
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self._analyze_class(node)
        self.current_class = old_class
        self.generic_visit(node)
    
    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool):
        """Analiza una función/método completo."""
        key = f"{self.file_path}:{self.current_class + '.' if self.current_class else ''}{node.name}"
        
        metrics = ComplexityMetrics()
        metrics.lines_of_code = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        metrics.param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg: metrics.param_count += 1
        if node.args.kwarg: metrics.param_count += 1
        
        # Complejidad ciclomática
        metrics.cyclomatic = self._cyclomatic_complexity(node)
        
        # Complejidad cognitiva
        metrics.cognitive = self._cognitive_complexity(node)
        
        # Nesting
        metrics.max_nesting = self._max_nesting(node)
        
        # Métricas de Halstead
        operators, operands = self._halstead_metrics(node)
        metrics.halstead_volume = self._halstead_volume(operators, operands)
        metrics.halstead_difficulty = self._halstead_difficulty(operators, operands)
        metrics.halstead_effort = metrics.halstead_volume * metrics.halstead_difficulty
        
        # Líneas lógicas, comentarios, etc.
        metrics.logical_lines, metrics.comment_lines, metrics.blank_lines = self._count_lines(node)
        
        # Variables locales
        metrics.local_vars = self._count_local_vars(node)
        
        # Maintainability Index
        metrics.maintainability_index = self._maintainability_index(metrics)
        
        self.function_metrics[key] = metrics
    
    def _cyclomatic_complexity(self, node: ast.AST) -> int:
        """Complejidad ciclomática de McCabe."""
        complexity = 1  # Base
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.Try, ast.With)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        return complexity
    
    def _cognitive_complexity(self, node: ast.AST) -> int:
        """Complejidad cognitiva (SonarSource)."""
        complexity = 0
        nesting = 0
        
        def walk(n: ast.AST, nest: int):
            nonlocal complexity
            if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1 + nest
                nest += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
            elif isinstance(n, (ast.Try, ast.With)):
                nest += 1
            elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1
            
            for child in ast.iter_child_nodes(n):
                walk(child, nest)
        
        walk(node, 0)
        return complexity
    
    def _max_nesting(self, node: ast.AST) -> int:
        max_nest = 0
        def walk(n: ast.AST, nest: int):
            nonlocal max_nest
            if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                nest += 1
                max_nest = max(max_nest, nest)
            for child in ast.iter_child_nodes(n):
                walk(child, nest)
        walk(node, 0)
        return max_nest
    
    def _halstead_metrics(self, node: ast.AST) -> Tuple[Counter, Counter]:
        """Operadores y operandos para métricas de Halstead."""
        operators = Counter()
        operands = Counter()
        
        OPERATOR_NODES = {
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
            ast.FloorDiv, ast.MatMult,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.Is, ast.IsNot, ast.In, ast.NotIn,
            ast.And, ast.Or, ast.Not,
            ast.Assign, ast.AnnAssign, ast.AugAssign,
            ast.If, ast.For, ast.While, ast.Try, ast.With,
            ast.Return, ast.Yield, ast.YieldFrom,
            ast.Call, ast.Lambda,
            ast.List, ast.Tuple, ast.Set, ast.Dict,
            ast.Subscript, ast.Attribute, ast.Name,
        }
        
        for node in ast.walk(node):
            node_type = type(node)
            if node_type in OPERATOR_NODES:
                operators[node_type.__name__] += 1
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                operands[node.id] += 1
            elif isinstance(node, (ast.Constant, ast.Num, ast.Str, ast.Bytes)):
                operands[str(node.value)] += 1
        
        return operators, operands
    
    def _halstead_volume(self, operators: Counter, operands: Counter) -> float:
        n1 = len(operators)
        n2 = len(operands)
        N1 = sum(operators.values())
        N2 = sum(operands.values())
        if n1 + n2 == 0:
            return 0.0
        return (N1 + N2) * (n1 + n2).bit_length()
    
    def _halstead_difficulty(self, operators: Counter, operands: Counter) -> float:
        n1 = len(operators)
        n2 = len(operands)
        N2 = sum(operands.values())
        if n2 == 0:
            return 0.0
        return (n1 / 2) * (N2 / n2)
    
    def _count_lines(self, node: ast.AST) -> Tuple[int, int, int]:
        """Cuenta líneas lógicas, comentarios, en blanco en el rango del nodo."""
        if not node.end_lineno:
            return 0, 0, 0
        logical = 0
        comments = 0
        blank = 0
        for i in range(node.lineno - 1, node.end_lineno):
            if i >= len(self.lines):
                break
            line = self.lines[i].strip()
            if not line:
                blank += 1
            elif line.startswith('#'):
                comments += 1
            else:
                logical += 1
        return logical, comments, blank
    
    def _count_local_vars(self, node: ast.AST) -> int:
        vars_set = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                vars_set.add(n.id)
        return len(vars_set)
    
    def _maintainability_index(self, m: ComplexityMetrics) -> float:
        """Maintainability Index (MI) - fórmula original de Coleman."""
        if m.halstead_volume == 0 or m.cyclomatic == 0:
            return 100.0
        # MI = 171 - 5.2 * ln(Volume) - 0.23 * Cyclomatic - 16.2 * ln(LOC)
        import math
        mi = 171 - 5.2 * math.log(m.halstead_volume) - 0.23 * m.cyclomatic - 16.2 * math.log(max(1, m.lines_of_code))
        return max(0, min(100, mi * 100 / 171))
    
    def _analyze_class(self, node: ast.ClassDef):
        """Analiza una clase completa."""
        metrics = ClassMetrics(
            name=node.name,
            file=self.file_path,
            line=node.lineno
        )
        
        # Contar métodos y campos
        methods = []
        fields = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item)
                metrics.methods += 1
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.append(target.id)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
        
        metrics.fields = len(fields)
        
        # WMC = suma de complejidad ciclomática de métodos
        wmc = 0
        for method in methods:
            key = f"{self.file_path}:{node.name}.{method.name}"
            if key in self.function_metrics:
                wmc += self.function_metrics[key].cyclomatic
        metrics.wmc = wmc
        
        # RFC = métodos + métodos llamados (aprox: métodos + imports usados en métodos)
        metrics.rfc = metrics.methods + len(self.imports)
        
        # CBO aproximado = imports únicos usados en la clase
        metrics.cbo = len(set(self.imports))
        
        # LCOM aproximado
        if metrics.methods > 1 and metrics.fields > 0:
            # Simplificado: fracción de métodos que no usan campos
            metrics.lcom = 0.5  # placeholder simplificado
        
        # DIT y NOC - simplificado
        metrics.dit = len(node.bases)
        
        # Detección God Class
        metrics.god_class_score = self._god_class_score(metrics)
        metrics.is_god_class = metrics.god_class_score > 0.7
        
        # Data Class
        metrics.is_data_class = metrics.methods <= 2 and metrics.fields >= 3
        
        self.class_metrics.append(metrics)
    
    def _god_class_score(self, m: ClassMetrics) -> float:
        """Score 0-1 para God Class (WMC alto, CBO alto, LCOM alto, muchos campos)."""
        score = 0.0
        if m.wmc > 50: score += 0.3
        elif m.wmc > 30: score += 0.2
        elif m.wmc > 15: score += 0.1
        
        if m.cbo > 10: score += 0.2
        elif m.cbo > 5: score += 0.1
        
        if m.fields > 20: score += 0.2
        elif m.fields > 10: score += 0.1
        
        if m.lcom > 0.8: score += 0.3
        elif m.lcom > 0.5: score += 0.1
        
        return min(1.0, score)


class DependencyVisitor(ast.NodeVisitor):
    """Extrae dependencias entre módulos."""
    
    def __init__(self, file_path: str, project_root: Path):
        self.file_path = file_path
        self.project_root = project_root
        self.edges: List[DependencyEdge] = []
        self.imports: List[str] = []
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
            self.edges.append(DependencyEdge(
                from_module=self._module_name(self.file_path),
                to_module=alias.name,
                type="import",
                line=node.lineno
            ))
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            full = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full)
            self.edges.append(DependencyEdge(
                from_module=self._module_name(self.file_path),
                to_module=module if module else alias.name,
                type="import_from",
                line=node.lineno
            ))
    
    def visit_ClassDef(self, node: ast.ClassDef):
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.edges.append(DependencyEdge(
                    from_module=self._module_name(self.file_path),
                    to_module=base.id,
                    type="inherit",
                    line=node.lineno
                ))
        self.generic_visit(node)
    
    def _module_name(self, file_path: str) -> str:
        """Convierte path a nombre de módulo."""
        rel = Path(file_path).relative_to(self.project_root)
        return str(rel.with_suffix('')).replace('/', '.').replace('\\', '.')


# ═══════════════════════════════════════════════════════════════════════════
# DETECTORES DE CODE SMELLS, PATRONES, ANTI-PATRONES
# ═══════════════════════════════════════════════════════════════════════════

class CodeSmellDetector:
    """Detecta code smells usando métricas calculadas."""
    
    THRESHOLDS = {
        "long_method_loc": 50,
        "long_method_cyclomatic": 10,
        "long_method_cognitive": 15,
        "long_class_loc": 500,
        "long_class_methods": 20,
        "god_class_wmc": 50,
        "god_class_cbo": 10,
        "god_class_fields": 20,
        "feature_envy_cbo": 5,
        "data_class_methods": 2,
        "data_class_fields": 5,
        "long_parameter_list": 5,
        "large_class_lcom": 0.8,
        "dead_code_confidence": 0.7,
    }
    
    def __init__(self, report: CodeInvestReport):
        self.report = report
        self.smells: List[CodeSmell] = []
    
    def detect_all(self) -> List[CodeSmell]:
        self._detect_long_methods()
        self._detect_long_classes()
        self._detect_god_classes()
        self._detect_feature_envy()
        self._detect_data_classes()
        self._detect_long_parameter_lists()
        self._detect_large_class_low_cohesion()
        return self.smells
    
    def _detect_long_methods(self):
        for key, m in self.report.function_metrics.items():
            file_path, func = key.split(":", 1)
            
            if m.lines_of_code > self.THRESHOLDS["long_method_loc"]:
                self.smells.append(CodeSmell(
                    type="long_method",
                    severity="warning" if m.lines_of_code < 100 else "critical",
                    file=file_path,
                    line=0,  # se llenaría con info real
                    symbol=func,
                    message=f"Método largo: {m.lines_of_code} líneas (umbral: {self.THRESHOLDS['long_method_loc']})",
                    metric_value=m.lines_of_code,
                    threshold=self.THRESHOLDS["long_method_loc"],
                    suggestion="Extraer métodos pequeños, cada uno con una responsabilidad única."
                ))
            
            if m.cyclomatic > self.THRESHOLDS["long_method_cyclomatic"]:
                self.smells.append(CodeSmell(
                    type="high_cyclomatic_complexity",
                    severity="warning" if m.cyclomatic < 20 else "critical",
                    file=file_path,
                    line=0,
                    symbol=func,
                    message=f"Complejidad ciclomática alta: {m.cyclomatic} (umbral: {self.THRESHOLDS['long_method_cyclomatic']})",
                    metric_value=m.cyclomatic,
                    threshold=self.THRESHOLDS["long_method_cyclomatic"],
                    suggestion="Simplificar lógica condicional, extraer métodos, usar polimorfismo."
                ))
            
            if m.cognitive > self.THRESHOLDS["long_method_cognitive"]:
                self.smells.append(CodeSmell(
                    type="high_cognitive_complexity",
                    severity="warning" if m.cognitive < 30 else "critical",
                    file=file_path,
                    line=0,
                    symbol=func,
                    message=f"Complejidad cognitiva alta: {m.cognitive} (umbral: {self.THRESHOLDS['long_method_cognitive']})",
                    metric_value=m.cognitive,
                    threshold=self.THRESHOLDS["long_method_cognitive"],
                    suggestion="Reducir anidamiento, extraer métodos, simplificar condiciones."
                ))
    
    def _detect_long_classes(self):
        for cm in self.report.class_metrics:
            if cm.loc > self.THRESHOLDS["long_class_loc"]:
                self.smells.append(CodeSmell(
                    type="long_class",
                    severity="warning" if cm.loc < 1000 else "critical",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"Clase larga: {cm.loc} líneas (umbral: {self.THRESHOLDS['long_class_loc']})",
                    metric_value=cm.loc,
                    threshold=self.THRESHOLDS["long_class_loc"],
                    suggestion="Dividir en clases más pequeñas con responsabilidad única (SRP)."
                ))
            
            if cm.methods > self.THRESHOLDS["long_class_methods"]:
                self.smells.append(CodeSmell(
                    type="too_many_methods",
                    severity="warning",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"Demasiados métodos: {cm.methods} (umbral: {self.THRESHOLDS['long_class_methods']})",
                    metric_value=cm.methods,
                    threshold=self.THRESHOLDS["long_class_methods"],
                    suggestion="Aplicar Single Responsibility Principle, extraer clases."
                ))
    
    def _detect_god_classes(self):
        for cm in self.report.class_metrics:
            if cm.is_god_class:
                self.smells.append(CodeSmell(
                    type="god_class",
                    severity="critical",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"God Class detectada (score: {cm.god_class_score:.2f}): WMC={cm.wmc}, CBO={cm.cbo}, Campos={cm.fields}",
                    metric_value=cm.god_class_score,
                    threshold=0.7,
                    suggestion="Aplicar Extract Class, delegar responsabilidades, usar composición."
                ))
    
    def _detect_feature_envy(self):
        # Feature Envy: método que usa más datos de otra clase que de la suya
        for key, m in self.report.function_metrics.items():
            if m.cyclomatic > 5 and m.local_vars > 10:
                # Heurística simple: muchos accesos a atributos externos
                self.smells.append(CodeSmell(
                    type="feature_envy",
                    severity="info",
                    file=key.split(":")[0],
                    line=0,
                    symbol=key.split(":")[1],
                    message=f"Posible Feature Envy: muchas variables locales ({m.local_vars}) y complejidad ({m.cyclomatic})",
                    metric_value=m.local_vars,
                    threshold=10,
                    suggestion="Mover método a la clase cuyos datos usa predominantemente."
                ))
    
    def _detect_data_classes(self):
        for cm in self.report.class_metrics:
            if cm.is_data_class:
                self.smells.append(CodeSmell(
                    type="data_class",
                    severity="info",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"Data Class: {cm.methods} métodos, {cm.fields} campos",
                    metric_value=cm.fields,
                    threshold=self.THRESHOLDS["data_class_fields"],
                    suggestion="Considerar usar dataclass, namedtuple o añadir comportamiento."
                ))
    
    def _detect_long_parameter_lists(self):
        for key, m in self.report.function_metrics.items():
            if m.param_count > self.THRESHOLDS["long_parameter_list"]:
                file_path, func = key.split(":", 1)
                self.smells.append(CodeSmell(
                    type="long_parameter_list",
                    severity="warning" if m.param_count < 8 else "critical",
                    file=file_path,
                    line=0,
                    symbol=func,
                    message=f"Lista de parámetros larga: {m.param_count} parámetros",
                    metric_value=m.param_count,
                    threshold=self.THRESHOLDS["long_parameter_list"],
                    suggestion="Usar objeto de parámetros (Parameter Object), Builder, o agrupar en dataclass."
                ))
    
    def _detect_large_class_low_cohesion(self):
        for cm in self.report.class_metrics:
            if cm.lcom > self.THRESHOLDS["large_class_lcom"] and cm.methods > 5:
                self.smells.append(CodeSmell(
                    type="low_cohesion",
                    severity="warning",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"Baja cohesión (LCOM={cm.lcom:.2f}): métodos no comparten campos",
                    metric_value=cm.lcom,
                    threshold=self.THRESHOLDS["large_class_lcom"],
                    suggestion="Dividir clase en varias cohesivas, cada una con responsabilidad única."
                ))


class DesignPatternDetector:
    """Detecta patrones de diseño clásicos (GoF)."""
    
    PATTERNS = {
        "singleton": {
            "indicators": [
                r"__new__\s*\(",
                r"_instance\s*=",
                r"get_instance\s*\(",
                r"instance\s*=\s*None",
            ],
            "class_indicators": ["Singleton", "Instance", "getInstance"],
        },
        "factory": {
            "indicators": [
                r"create_\w+\s*\(",
                r"make_\w+\s*\(",
                r"build_\w+\s*\(",
                r"factory\s*\(",
            ],
            "class_indicators": ["Factory", "Builder", "Creator"],
        },
        "builder": {
            "indicators": [
                r"\.with_\w+\s*\(",
                r"\.set_\w+\s*\(",
                r"\.build\s*\(\s*\)",
                r"class\s+\w+Builder",
            ],
            "class_indicators": ["Builder"],
        },
        "observer": {
            "indicators": [
                r"add_observer\s*\(",
                r"remove_observer\s*\(",
                r"notify_\w+\s*\(",
                r"subscribe\s*\(",
                r"unsubscribe\s*\(",
            ],
            "class_indicators": ["Observer", "Listener", "Subscriber", "Event"],
        },
        "strategy": {
            "indicators": [
                r"set_strategy\s*\(",
                r"execute_strategy\s*\(",
                r"class\s+\w+Strategy",
            ],
            "class_indicators": ["Strategy", "Policy", "Algorithm"],
        },
        "decorator": {
            "indicators": [
                r"@\w+",
                r"__call__\s*\(",
                r"wrapped\s*=",
            ],
            "class_indicators": ["Decorator", "Wrapper"],
        },
        "adapter": {
            "indicators": [
                r"adapt\s*\(",
                r"convert\s*\(",
                r"class\s+\w+Adapter",
            ],
            "class_indicators": ["Adapter", "Wrapper"],
        },
        "facade": {
            "indicators": [
                r"class\s+\w+Facade",
                r"simplify\s*\(",
            ],
            "class_indicators": ["Facade", "Gateway"],
        },
        "proxy": {
            "indicators": [
                r"class\s+\w+Proxy",
                r"__getattr__\s*\(",
                r"lazy\s*\(",
            ],
            "class_indicators": ["Proxy", "Lazy"],
        },
        "command": {
            "indicators": [
                r"execute\s*\(\s*\)",
                r"undo\s*\(\s*\)",
                r"class\s+\w+Command",
            ],
            "class_indicators": ["Command", "Action"],
        },
        "template_method": {
            "indicators": [
                r"def\s+template_\w+",
                r"@abstractmethod",
                r"hook_\w+",
            ],
            "class_indicators": ["Template", "Base"],
        },
    }
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def detect(self, file_path: Path, source: str, class_metrics: List[ClassMetrics]) -> List[DesignPattern]:
        patterns = []
        lines = source.splitlines()
        
        for pattern_name, config in self.PATTERNS.items():
            confidence = 0.0
            evidence = []
            
            # Buscar indicadores en código
            for indicator in config["indicators"]:
                for i, line in enumerate(lines):
                    if re.search(indicator, line):
                        confidence += 0.15
                        evidence.append(f"L{i+1}: {line.strip()[:80]}")
            
            # Buscar en nombres de clases
            for cm in class_metrics:
                if cm.file == str(file_path):
                    for class_indicator in config["class_indicators"]:
                        if class_indicator.lower() in cm.name.lower():
                            confidence += 0.3
                            evidence.append(f"Clase: {cm.name}")
            
            if confidence >= 0.4:
                patterns.append(DesignPattern(
                    pattern=pattern_name,
                    confidence=min(1.0, confidence),
                    file=str(file_path),
                    class_name=class_metrics[0].name if class_metrics else "unknown",
                    evidence=evidence[:5]
                ))
        
        return patterns


class AntiPatternDetector:
    """Detecta anti-patrones comunes."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def detect(self, file_path: Path, source: str, class_metrics: List[ClassMetrics],
               function_metrics: Dict[str, ComplexityMetrics]) -> List[AntiPattern]:
        anti_patterns = []
        lines = source.splitlines()
        
        # Spaghetti Code: alta complejidad ciclomática global en archivo
        file_complexity = sum(m.cyclomatic for m in function_metrics.values() 
                             if m.file == str(file_path))
        if file_complexity > 100:
            anti_patterns.append(AntiPattern(
                pattern="spaghetti_code",
                severity="critical" if file_complexity > 200 else "warning",
                file=str(file_path),
                symbol="<module>",
                line=1,
                evidence=[f"Complejidad ciclomática total del archivo: {file_complexity}"],
                suggestion="Refactorizar en módulos más pequeños, reducir complejidad ciclomática."
            ))
        
        # Spaghetti SQL: queries SQL embebidas complejas
        sql_pattern = re.compile(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+', re.IGNORECASE)
        sql_count = sum(1 for line in lines if sql_pattern.search(line))
        if sql_count > 5:
            anti_patterns.append(AntiPattern(
                pattern="spaghetti_sql",
                severity="warning",
                file=str(file_path),
                symbol="<module>",
                line=1,
                evidence=[f"{sql_count} sentencias SQL embebidas detectadas"],
                suggestion="Extraer queries a repositorio/DAO, usar ORM o query builder."
            ))
        
        # God Object (clase que hace todo)
        for cm in class_metrics:
            if cm.file == str(file_path) and cm.is_god_class:
                anti_patterns.append(AntiPattern(
                    pattern="god_object",
                    severity="critical",
                    file=str(file_path),
                    symbol=cm.name,
                    line=cm.line,
                    evidence=[f"WMC={cm.wmc}, CBO={cm.cbo}, Campos={cm.fields}, LCOM={cm.lcom:.2f}"],
                    suggestion="Dividir en múltiples clases con responsabilidad única (SRP)."
                ))
        
        # Copy-Paste Programming: código duplicado (se detecta aparte)
        
        # Hardcoded Values
        hardcoded = re.findall(r'\b\d{4,}\b|["\'][a-zA-Z0-9_\-]{20,}["\']', source)
        if len(hardcoded) > 5:
            anti_patterns.append(AntiPattern(
                pattern="magic_numbers_strings",
                severity="warning",
                file=str(file_path),
                symbol="<module>",
                line=1,
                evidence=[f"{len(hardcoded)} valores hardcoded detectados"],
                suggestion="Extraer a constantes, configuración, o variables de entorno."
            ))
        
        # Long Method Chains (Law of Demeter violation)
        demeter_violations = len(re.findall(r'\.\w+\(\s*\)\.\w+\(\s*\)\.\w+', source))
        if demeter_violations > 3:
            anti_patterns.append(AntiPattern(
                pattern="law_of_demeter_violation",
                severity="warning",
                file=str(file_path),
                symbol="<module>",
                line=1,
                evidence=[f"{demeter_violations} cadenas de llamadas profundas detectadas"],
                suggestion="Aplicar Law of Demeter: hablar solo con amigos inmediatos."
            ))
        
        return anti_patterns


class DeadCodeDetector:
    """Detecta código muerto (funciones, clases, imports no usados)."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.all_imports: Dict[str, Set[str]] = defaultdict(set)  # file -> imported names
        self.all_definitions: Dict[str, Set[str]] = defaultdict(set)  # file -> defined names
        self.all_usages: Dict[str, Set[str]] = defaultdict(set)  # file -> used names
    
    def analyze_project(self, python_files: List[Path]):
        """Primera pasada: recolectar definiciones e imports."""
        for f in python_files:
            source = f.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(source)
            
            # Definiciones
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.all_definitions[str(f)].add(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.all_imports[str(f)].add(alias.asname or alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        self.all_imports[str(f)].add(alias.asname or alias.name)
            
            # Usos (Name nodes en Load context)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    self.all_usages[str(f)].add(node.id)
                elif isinstance(node, ast.Attribute):
                    # attribute access: obj.attr
                    if isinstance(node.value, ast.Name):
                        self.all_usages[str(f)].add(node.value.id)
    
    def detect_dead_code(self, file_path: Path) -> List[DeadCode]:
        dead = []
        fstr = str(file_path)
        
        # Imports no usados
        for imp in self.all_imports.get(fstr, set()):
            if imp not in self.all_usages.get(fstr, set()):
                # Verificar si se usa en otros archivos del proyecto
                used_elsewhere = any(
                    imp in self.all_usages.get(other, set()) 
                    for other in self.all_usages if other != fstr
                )
                if not used_elsewhere:
                    dead.append(DeadCode(
                        type="unused_import",
                        file=fstr,
                        symbol=imp,
                        line=0,
                        confidence=0.8
                    ))
        
        # Funciones/clases no usadas (privadas)
        for defn in self.all_definitions.get(fstr, set()):
            if defn.startswith('_') and not defn.startswith('__'):
                used = any(
                    defn in self.all_usages.get(other, set()) 
                    for other in self.all_usages
                )
                if not used:
                    dead.append(DeadCode(
                        type="unused_private_function" if not defn[0].isupper() else "unused_private_class",
                        file=fstr,
                        symbol=defn,
                        line=0,
                        confidence=0.7
                    ))
        
        return dead


class DuplicateCodeDetector:
    """Detecta código duplicado usando hashing de bloques normalizados."""
    
    def __init__(self, min_lines: int = 6, similarity_threshold: float = 0.8):
        self.min_lines = min_lines
        self.threshold = similarity_threshold
    
    def normalize_code(self, code: str) -> str:
        """Normaliza código para comparación: quita comentarios, normaliza whitespace."""
        lines = []
        for line in code.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Normalizar literales y nombres
                line = re.sub(r'\b\d+\b', 'N', line)
                line = re.sub(r'["\'][^"\']*["\']', 'S', line)
                line = re.sub(r'\b[a-zA-Z_]\w*\b', 'X', line)
                lines.append(line)
        return '\n'.join(lines)
    
    def detect(self, python_files: List[Path]) -> List[CodeDuplicate]:
        duplicates = []
        file_blocks: Dict[str, List[Tuple[int, str]]] = {}  # file -> [(line, normalized_block)]
        
        # Extraer bloques normalizados de cada archivo
        for f in python_files:
            source = f.read_text(encoding='utf-8', errors='ignore')
            lines = source.splitlines()
            blocks = []
            
            for i in range(len(lines) - self.min_lines + 1):
                block = '\n'.join(lines[i:i + self.min_lines])
                normalized = self.normalize_code(block)
                if normalized.strip():
                    blocks.append((i + 1, normalized))
            
            file_blocks[str(f)] = blocks
        
        # Comparar bloques entre archivos
        files = list(file_blocks.keys())
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                file_a, file_b = files[i], files[j]
                blocks_a = file_blocks[file_a]
                blocks_b = file_blocks[file_b]
                
                for line_a, norm_a in blocks_a:
                    for line_b, norm_b in blocks_b:
                        similarity = self._similarity(norm_a, norm_b)
                        if similarity >= self.threshold:
                            # Obtener snippet original
                            source_a = Path(file_a).read_text(encoding='utf-8', errors='ignore')
                            snippet = '\n'.join(source_a.splitlines()[line_a-1:line_a-1+self.min_lines])
                            
                            duplicates.append(CodeDuplicate(
                                file_a=file_a,
                                line_a=line_a,
                                file_b=file_b,
                                line_b=line_b,
                                lines=self.min_lines,
                                similarity=similarity,
                                code_snippet=snippet[:200]
                            ))
        
        return duplicates
    
    def _similarity(self, a: str, b: str) -> float:
        """Similitud de Jaccard entre conjuntos de líneas."""
        set_a = set(a.splitlines())
        set_b = set(b.splitlines())
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)


# ═══════════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL — CodeInvest
# ═══════════════════════════════════════════════════════════════════════════

class CodeInvest:
    """Motor principal de análisis de código."""
    
    def __init__(self, project_root: str | Path = "."):
        self.project_root = Path(project_root).resolve()
        self.python_files: List[Path] = []
        self.report: Optional[CodeInvestReport] = None
    
    def discover_files(self, patterns: List[str] = None) -> List[Path]:
        """Descubre archivos Python en el proyecto."""
        if patterns is None:
            patterns = ["**/*.py"]
        
        files = []
        for pattern in patterns:
            files.extend(self.project_root.glob(pattern))
        
        # Filtrar __pycache__, .git, venv, etc.
        exclude = {'.git', '__pycache__', '.venv', 'venv', 'env', '.env', 'build', 'dist', '.pytest_cache'}
        self.python_files = [
            f for f in files 
            if not any(part in exclude for part in f.parts)
            and f.is_file()
        ]
        return self.python_files
    
    def analyze_file(self, file_path: Path) -> Tuple[ModuleMetrics, List[ClassMetrics], Dict[str, ComplexityMetrics], List[DependencyEdge]]:
        """Analiza un archivo Python individual."""
        source = file_path.read_text(encoding='utf-8', errors='ignore')
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return ModuleMetrics(file=str(file_path)), [], {}, []
        
        # Complejidad y métricas de funciones/clases
        complexity_visitor = ComplexityVisitor(source, str(file_path))
        complexity_visitor.visit(tree)
        
        # Métricas de módulo
        module_metrics = ModuleMetrics(file=str(file_path))
        module_metrics.loc = len(source.splitlines())
        module_metrics.classes = len(complexity_visitor.class_metrics)
        module_metrics.functions = len([k for k in complexity_visitor.function_metrics if '.' not in k.split(':')[-1]])
        module_metrics.imports = complexity_visitor.imports
        module_metrics.exports = complexity_visitor.exports
        
        if complexity_visitor.function_metrics:
            complexities = [m.cyclomatic for m in complexity_visitor.function_metrics.values()]
            module_metrics.complexity_avg = sum(complexities) / len(complexities)
            module_metrics.complexity_max = max(complexities)
        
        module_metrics.maintainability_index = sum(
            m.maintainability_index for m in complexity_visitor.function_metrics.values()
        ) / max(1, len(complexity_visitor.function_metrics))
        
        total_lines = module_metrics.loc
        comment_lines = sum(m.comment_lines for m in complexity_visitor.function_metrics.values())
        module_metrics.comment_ratio = comment_lines / max(1, total_lines)
        
        # Dependencias
        dep_visitor = DependencyVisitor(str(file_path), self.project_root)
        dep_visitor.visit(tree)
        
        return (
            module_metrics,
            complexity_visitor.class_metrics,
            complexity_visitor.function_metrics,
            dep_visitor.edges
        )
    
    def analyze(self, patterns: List[str] = None) -> CodeInvestReport:
        """Ejecuta análisis completo del proyecto."""
        self.discover_files(patterns)
        
        all_file_metrics: List[ModuleMetrics] = []
        all_class_metrics: List[ClassMetrics] = []
        all_function_metrics: Dict[str, ComplexityMetrics] = {}
        all_dependency_edges: List[DependencyEdge] = []
        
        # Analizar cada archivo
        for f in self.python_files:
            fm, cm, funcm, deps = self.analyze_file(f)
            all_file_metrics.append(fm)
            all_class_metrics.extend(cm)
            all_function_metrics.update(funcm)
            all_dependency_edges.extend(deps)
        
        # Detectores
        smell_detector = CodeSmellDetector(None)  # report se llena después
        design_detector = DesignPatternDetector(self.project_root)
        anti_detector = AntiPatternDetector(self.project_root)
        dead_detector = DeadCodeDetector(self.project_root)
        dup_detector = DuplicateCodeDetector()
        
        # Dead code necesita análisis de todo el proyecto primero
        dead_detector.analyze_project(self.python_files)
        
        all_smells: List[CodeSmell] = []
        all_patterns: List[DesignPattern] = []
        all_anti: List[AntiPattern] = []
        all_dead: List[DeadCode] = []
        
        for f in self.python_files:
            source = f.read_text(encoding='utf-8', errors='ignore')
            file_class_metrics = [cm for cm in all_class_metrics if cm.file == str(f)]
            file_func_metrics = {k: v for k, v in all_function_metrics.items() if k.startswith(str(f) + ":")}
            
            # Code smells
            # (CodeSmellDetector necesita report, lo hacemos inline aquí)
            for key, m in file_func_metrics.items():
                file_path, func = key.split(":", 1)
                if m.lines_of_code > 50:
                    all_smells.append(CodeSmell("long_method", "warning", file_path, 0, func,
                        f"Método largo: {m.lines_of_code} líneas", m.lines_of_code, 50,
                        "Extraer métodos pequeños"))
                if m.cyclomatic > 10:
                    all_smells.append(CodeSmell("high_cyclomatic", "warning", file_path, 0, func,
                        f"CC alta: {m.cyclomatic}", m.cyclomatic, 10,
                        "Simplificar lógica"))
                if m.cognitive > 15:
                    all_smells.append(CodeSmell("high_cognitive", "warning", file_path, 0, func,
                        f"Cognitiva alta: {m.cognitive}", m.cognitive, 15,
                        "Reducir anidamiento"))
                if m.param_count > 5:
                    all_smells.append(CodeSmell("long_params", "warning", file_path, 0, func,
                        f"{m.param_count} parámetros", m.param_count, 5,
                        "Usar Parameter Object"))
            
            for cm in file_class_metrics:
                if cm.loc > 500:
                    all_smells.append(CodeSmell("long_class", "warning", cm.file, cm.line, cm.name,
                        f"Clase larga: {cm.loc} líneas", cm.loc, 500,
                        "Dividir clase (SRP)"))
                if cm.is_god_class:
                    all_smells.append(CodeSmell("god_class", "critical", cm.file, cm.line, cm.name,
                        f"God Class (score: {cm.god_class_score:.2f})", cm.god_class_score, 0.7,
                        "Extraer responsabilidades"))
                if cm.is_data_class:
                    all_smells.append(CodeSmell("data_class", "info", cm.file, cm.line, cm.name,
                        f"Data class: {cm.methods} métodos, {cm.fields} campos", cm.fields, 5,
                        "Considerar dataclass"))
            
            # Patrones de diseño
            all_patterns.extend(design_detector.detect(f, source, file_class_metrics))
            
            # Anti-patrones
            all_anti.extend(anti_detector.detect(f, source, file_class_metrics, file_func_metrics))
            
            # Código muerto
            all_dead.extend(dead_detector.detect_dead_code(f))
        
        # Duplicados
        duplicates = dup_detector.detect(self.python_files)
        
        # Dependencias circulares
        circular = self._detect_circular_dependencies(all_dependency_edges)
        
        # Métricas de acoplamiento
        coupling = self._calculate_coupling(all_dependency_edges)
        
        # Resumen
        total_loc = sum(fm.loc for fm in all_file_metrics)
        total_lloc = sum(fm.lloc for fm in all_file_metrics)
        total_classes = sum(fm.classes for fm in all_file_metrics)
        total_functions = sum(fm.functions for fm in all_file_metrics)
        avg_complexity = sum(fm.complexity_avg for fm in all_file_metrics) / max(1, len(all_file_metrics))
        max_complexity = max((fm.complexity_max for fm in all_file_metrics), default=0)
        avg_maintainability = sum(fm.maintainability_index for fm in all_file_metrics) / max(1, len(all_file_metrics))
        
        # Crear reporte temporal para CodeSmellDetector
        temp_report = CodeInvestReport(
            timestamp=datetime.now().isoformat(),
            project_root=str(self.project_root),
            files_analyzed=len(self.python_files),
            total_loc=total_loc,
            total_lloc=total_lloc,
            total_classes=total_classes,
            total_functions=total_functions,
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
            avg_maintainability=avg_maintainability,
            file_metrics=all_file_metrics,
            class_metrics=all_class_metrics,
            function_metrics=all_function_metrics,
            code_smells=all_smells,
            circular_dependencies=circular,
            code_duplicates=duplicates,
            design_patterns=all_patterns,
            anti_patterns=all_anti,
            dead_code=all_dead,
            dependency_graph=all_dependency_edges,
            coupling_metrics=coupling,
            summary={}
        )
        
        # Re-ejecutar smell detector con reporte completo
        smell_detector.report = temp_report
        all_smells = smell_detector.detect_all()
        
        # Resumen final
        summary = {
            "health_score": self._calculate_health_score(temp_report),
            "critical_issues": len([s for s in all_smells if s.severity == "critical"]),
            "warnings": len([s for s in all_smells if s.severity == "warning"]),
            "info": len([s for s in all_smells if s.severity == "info"]),
            "circular_deps": len(circular),
            "duplicates": len(duplicates),
            "dead_code": len(all_dead),
            "patterns_found": len(all_patterns),
            "anti_patterns": len(all_anti),
            "god_classes": len([cm for cm in all_class_metrics if cm.is_god_class]),
            "data_classes": len([cm for cm in all_class_metrics if cm.is_data_class]),
        }
        
        self.report = CodeInvestReport(
            timestamp=datetime.now().isoformat(),
            project_root=str(self.project_root),
            files_analyzed=len(self.python_files),
            total_loc=total_loc,
            total_lloc=total_lloc,
            total_classes=total_classes,
            total_functions=total_functions,
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
            avg_maintainability=avg_maintainability,
            file_metrics=all_file_metrics,
            class_metrics=all_class_metrics,
            function_metrics=all_function_metrics,
            code_smells=all_smells,
            circular_dependencies=circular,
            code_duplicates=duplicates,
            design_patterns=all_patterns,
            anti_patterns=all_anti,
            dead_code=all_dead,
            dependency_graph=all_dependency_edges,
            coupling_metrics=coupling,
            summary=summary
        )
        
        return self.report
    
    def _detect_circular_dependencies(self, edges: List[DependencyEdge]) -> List[CircularDependency]:
        """Detecta ciclos en el grafo de dependencias (Tarjan)."""
        graph = defaultdict(set)
        for e in edges:
            graph[e.from_module].add(e.to_module)
        
        # Tarjan's algorithm
        index = 0
        stack = []
        on_stack = set()
        indices = {}
        lowlink = {}
        cycles = []
        
        def strongconnect(v: str):
            nonlocal index
            indices[v] = lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)
            
            for w in graph.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])
            
            if lowlink[v] == indices[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                if len(scc) > 1:
                    cycles.append(scc)
        
        for v in graph:
            if v not in indices:
                strongconnect(v)
        
        return [CircularDependency(cycle=c, severity="critical" if len(c) > 2 else "warning") for c in cycles]
    
    def _calculate_coupling(self, edges: List[DependencyEdge]) -> Dict[str, Dict[str, float]]:
        """Calcula acoplamiento aferente/eferente e inestabilidad."""
        afferent = defaultdict(set)   # quién me importa
        efferent = defaultdict(set)   # a quién importo
        
        for e in edges:
            efferent[e.from_module].add(e.to_module)
            afferent[e.to_module].add(e.from_module)
        
        all_modules = set(afferent.keys()) | set(efferent.keys())
        coupling = {}
        
        for m in all_modules:
            ca = len(afferent.get(m, set()))
            ce = len(efferent.get(m, set()))
            instability = ce / (ca + ce) if (ca + ce) > 0 else 0
            coupling[m] = {
                "afferent": ca,
                "efferent": ce,
                "instability": instability,
                "abstractness": 0.0  # requeriría análisis de clases abstractas
            }
        
        return coupling
    
    def _calculate_health_score(self, report: CodeInvestReport) -> float:
        """Score de salud 0-100."""
        score = 100.0
        
        # Penalizar por issues
        score -= report.summary.get("critical_issues", 0) * 10
        score -= report.summary.get("warnings", 0) * 3
        score -= report.summary.get("circular_deps", 0) * 15
        score -= report.summary.get("god_classes", 0) * 20
        score -= min(report.summary.get("duplicates", 0) * 2, 20)
        score -= min(report.summary.get("dead_code", 0) * 1, 10)
        
        # Bonus por buena mantenibilidad
        if report.avg_maintainability > 80:
            score += 5
        elif report.avg_maintainability > 60:
            score += 2
        
        # Penalizar complejidad alta
        if report.avg_complexity > 15:
            score -= 10
        elif report.avg_complexity > 10:
            score -= 5
        
        return max(0, min(100, score))
    
    def generate_report(self, format: str = "text") -> str:
        """Genera reporte en formato texto, JSON o markdown."""
        if not self.report:
            return "No hay reporte. Ejecuta analyze() primero."
        
        r = self.report
        
        if format == "json":
            return json.dumps(asdict(r), indent=2, default=str)
        
        elif format == "markdown":
            return self._markdown_report(r)
        
        return self._text_report(r)
    
    def _text_report(self, r: CodeInvestReport) -> str:
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════════════════╗")
        lines.append("║                    🔍 CODE INVEST — REPORTE DE ANÁLISIS                    ║")
        lines.append("╚════════════════════════════════════════════════════════════════════════════╝")
        lines.append(f"")
        lines.append(f"📅 Timestamp: {r.timestamp}")
        lines.append(f"📁 Proyecto: {r.project_root}")
        lines.append(f"📊 Archivos analizados: {r.files_analyzed}")
        lines.append(f"")
        lines.append(f"═══ MÉTRICAS GLOBALES ═══")
        lines.append(f"  📏 Líneas totales (LOC):     {r.total_loc:,}")
        lines.append(f"  📏 Líneas lógicas (LLOC):    {r.total_lloc:,}")
        lines.append(f"  🏗️  Clases totales:           {r.total_classes}")
        lines.append(f"  ⚙️  Funciones totales:        {r.total_functions}")
        lines.append(f"  📈 Complejidad ciclomática:  avg={r.avg_complexity:.1f}  max={r.max_complexity}")
        lines.append(f"  🏥 Maintainability Index:    {r.avg_maintainability:.1f}/100")
        lines.append(f"  💚 Health Score:             {r.summary.get('health_score', 0):.1f}/100")
        lines.append(f"")
        
        # Resumen de issues
        lines.append(f"═══ RESUMEN DE HALLAZGOS ═══")
        lines.append(f"  🔴 Críticos:      {r.summary.get('critical_issues', 0)}")
        lines.append(f"  🟡 Advertencias:  {r.summary.get('warnings', 0)}")
        lines.append(f"  🔵 Info:          {r.summary.get('info', 0)}")
        lines.append(f"  🔄 Deps circulares: {r.summary.get('circular_deps', 0)}")
        lines.append(f"  📋 Duplicados:    {r.summary.get('duplicates', 0)}")
        lines.append(f"  💀 Código muerto: {r.summary.get('dead_code', 0)}")
        lines.append(f"  🎯 Patrones:      {r.summary.get('patterns_found', 0)}")
        lines.append(f"  ⚠️ Anti-patrones: {r.summary.get('anti_patterns', 0)}")
        lines.append(f"  👑 God Classes:   {r.summary.get('god_classes', 0)}")
        lines.append(f"  📦 Data Classes:  {r.summary.get('data_classes', 0)}")
        lines.append(f"")
        
        # Top code smells
        if r.code_smells:
            lines.append(f"═══ TOP CODE SMELLS ═══")
            critical = [s for s in r.code_smells if s.severity == "critical"]
            warning = [s for s in r.code_smells if s.severity == "warning"]
            for s in (critical + warning)[:10]:
                lines.append(f"  {s.severity.upper()[0]} {s.file}:{s.line} {s.symbol} — {s.message}")
            lines.append(f"")
        
        # Dependencias circulares
        if r.circular_dependencies:
            lines.append(f"═══ DEPENDENCIAS CIRCULARES ═══")
            for c in r.circular_dependencies[:5]:
                lines.append(f"  🔄 {' → '.join(c.cycle)} → {c.cycle[0]}")
            lines.append(f"")
        
        # Top duplicados
        if r.code_duplicates:
            lines.append(f"═══ CÓDIGO DUPLICADO ═══")
            for d in r.code_duplicates[:5]:
                lines.append(f"  📋 {d.file_a}:{d.line_a} ↔ {d.file_b}:{d.line_b} ({d.similarity:.0%} similar, {d.lines} líneas)")
            lines.append(f"")
        
        # Patrones detectados
        if r.design_patterns:
            lines.append(f"═══ PATRONES DE DISEÑO ═══")
            for p in r.design_patterns[:10]:
                lines.append(f"  ✨ {p.pattern} ({p.confidence:.0%}) en {p.file}:{p.class_name}")
            lines.append(f"")
        
        # Anti-patrones
        if r.anti_patterns:
            lines.append(f"═══ ANTI-PATRONES ═══")
            for a in r.anti_patterns[:10]:
                lines.append(f"  ⚠️ {a.pattern} [{a.severity}] en {a.file}:{a.symbol}")
            lines.append(f"")
        
        # Acoplamiento crítico
        if r.coupling_metrics:
            lines.append(f"═══ ACOPLAMIENTO (Top 10 inestables) ═══")
            sorted_coupling = sorted(
                r.coupling_metrics.items(), 
                key=lambda x: x[1]["instability"], 
                reverse=True
            )
            for mod, m in sorted_coupling[:10]:
                lines.append(f"  📦 {mod}: Ca={m['afferent']} Ce={m['efferent']} I={m['instability']:.2f}")
            lines.append(f"")
        
        return "\n".join(lines)
    
    def _markdown_report(self, r: CodeInvestReport) -> str:
        lines = []
        lines.append(f"# 🔍 Code Invest Report")
        lines.append(f"")
        lines.append(f"**Proyecto:** {r.project_root}  ")
        lines.append(f"**Fecha:** {r.timestamp}  ")
        lines.append(f"**Archivos:** {r.files_analyzed}  ")
        lines.append(f"")
        lines.append(f"## 📊 Métricas Globales")
        lines.append(f"")
        lines.append(f"| Métrica | Valor |")
        lines.append(f"|---------|-------|")
        lines.append(f"| LOC | {r.total_loc:,} |")
        lines.append(f"| LLOC | {r.total_lloc:,} |")
        lines.append(f"| Clases | {r.total_classes} |")
        lines.append(f"| Funciones | {r.total_functions} |")
        lines.append(f"| Complejidad avg/max | {r.avg_complexity:.1f} / {r.max_complexity} |")
        lines.append(f"| Maintainability Index | {r.avg_maintainability:.1f}/100 |")
        lines.append(f"| Health Score | {r.summary.get('health_score', 0):.1f}/100 |")
        lines.append(f"")
        
        # Issues summary
        lines.append(f"## 📋 Resumen de Hallazgos")
        lines.append(f"")
        lines.append(f"| Tipo | Cuenta |")
        lines.append(f"|------|--------|")
        lines.append(f"| 🔴 Críticos | {r.summary.get('critical_issues', 0)} |")
        lines.append(f"| 🟡 Advertencias | {r.summary.get('warnings', 0)} |")
        lines.append(f"| 🔵 Info | {r.summary.get('info', 0)} |")
        lines.append(f"| 🔄 Deps circulares | {r.summary.get('circular_deps', 0)} |")
        lines.append(f"| 📋 Duplicados | {r.summary.get('duplicates', 0)} |")
        lines.append(f"| 💀 Código muerto | {r.summary.get('dead_code', 0)} |")
        lines.append(f"| 🎯 Patrones | {r.summary.get('patterns_found', 0)} |")
        lines.append(f"| ⚠️ Anti-patrones | {r.summary.get('anti_patterns', 0)} |")
        lines.append(f"")
        
        # Code smells table
        if r.code_smells:
            lines.append(f"## 🔍 Code Smells (Top 20)")
            lines.append(f"")
            lines.append(f"| Severidad | Tipo | Archivo | Símbolo | Mensaje |")
            lines.append(f"|-----------|------|---------|---------|---------|")
            for s in sorted(r.code_smells, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x.severity])[:20]:
                lines.append(f"| {s.severity} | {s.type} | {s.file} | {s.symbol} | {s.message[:60]} |")
            lines.append(f"")
        
        return "\n".join(lines)
    
    def save_report(self, path: str | Path, format: str = "json"):
        """Guarda reporte a archivo."""
        path = Path(path)
        content = self.generate_report(format)
        path.write_text(content, encoding='utf-8')
        return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# HERRAMIENTAS PARA AIION (tools registry)
# ═══════════════════════════════════════════════════════════════════════════

def code_invest_analyze(project_path: str = ".", patterns: list = None, format: str = "text") -> str:
    """
    Ejecuta análisis completo de Code Invest en un proyecto Python.
    
    Args:
        project_path: Ruta al proyecto (default: directorio actual)
        patterns: Patrones glob para archivos (default: ["**/*.py"])
        format: Formato de salida: "text", "markdown", "json"
    
    Returns:
        Reporte formateado según formato solicitado.
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze(patterns)
        return invest.generate_report(format)
    except Exception as e:
        return f"❌ Error en Code Invest: {e}"


def code_invest_file(file_path: str, format: str = "text") -> str:
    """
    Analiza un solo archivo Python en profundidad.
    """
    try:
        invest = CodeInvest(str(Path(file_path).parent))
        # Analizar solo este archivo
        fm, cm, funcm, deps = invest.analyze_file(Path(file_path))
        
        # Mini-reporte
        lines = []
        lines.append(f"🔍 CODE INVEST — Análisis de archivo: {file_path}")
        lines.append(f"")
        lines.append(f"📏 LOC: {fm.loc} | LLOC: {fm.lloc} | Clases: {fm.classes} | Funciones: {fm.functions}")
        lines.append(f"📈 Complejidad: avg={fm.complexity_avg:.1f} max={fm.complexity_max}")
        lines.append(f"🏥 Maintainability: {fm.maintainability_index:.1f}/100")
        lines.append(f"💬 Comentarios: {fm.comment_ratio:.1%}")
        lines.append(f"")
        
        if cm:
            lines.append(f"🏗️ CLASES:")
            for c in cm:
                lines.append(f"  • {c.name} (L{c.line}): {c.methods}m {c.fields}f WMC={c.wmc} CBO={c.cbo} LCOM={c.lcom:.2f}")
                if c.is_god_class:
                    lines.append(f"    ⚠️ GOD CLASS (score: {c.god_class_score:.2f})")
                if c.is_data_class:
                    lines.append(f"    📦 Data Class")
        
        if funcm:
            lines.append(f"")
            lines.append(f"⚙️ FUNCIONES (Top 10 por complejidad):")
            sorted_funcs = sorted(funcm.items(), key=lambda x: x[1].cyclomatic, reverse=True)
            for key, m in sorted_funcs[:10]:
                name = key.split(":")[-1]
                lines.append(f"  • {name}: CC={m.cyclomatic} Cog={m.cognitive} LOC={m.lines_of_code} MI={m.maintainability_index:.1f}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error analizando archivo: {e}"


def code_invest_smells(project_path: str = ".", severity: str = "all") -> str:
    """
    Lista code smells detectados en el proyecto.
    
    Args:
        project_path: Ruta al proyecto
        severity: "critical", "warning", "info", "all"
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze()
        
        smells = report.code_smells
        if severity != "all":
            smells = [s for s in smells if s.severity == severity]
        
        if not smells:
            return f"✅ No se detectaron code smells de severidad '{severity}'."
        
        lines = [f"🔍 CODE SMELLS ({severity.upper()}) — {len(smells)} hallazgos"]
        lines.append("")
        
        for s in sorted(smells, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x.severity]):
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[s.severity]
            lines.append(f"{icon} [{s.severity.upper()}] {s.type}")
            lines.append(f"   📁 {s.file}:{s.line}  ⚙️ {s.symbol}")
            lines.append(f"   💬 {s.message}")
            if s.suggestion:
                lines.append(f"   💡 {s.suggestion}")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_dependencies(project_path: str = ".", format: str = "text") -> str:
    """
    Analiza dependencias y acoplamiento del proyecto.
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze()
        
        lines = [f"🔗 CODE INVEST — Análisis de Dependencias: {project_path}"]
        lines.append("")
        
        # Circular deps
        if report.circular_dependencies:
            lines.append(f"🔄 DEPENDENCIAS CIRCULARES ({len(report.circular_dependencies)}):")
            for c in report.circular_dependencies:
                lines.append(f"  {' → '.join(c.cycle)} → {c.cycle[0]} [{c.severity}]")
            lines.append("")
        
        # Coupling
        lines.append(f"📦 ACOPLAMIENTO POR MÓDULO:")
        lines.append(f"  {'Módulo':<40} {'Ca':>4} {'Ce':>4} {'I':>5}")
        lines.append(f"  {'-'*40} {'-'*4} {'-'*4} {'-'*5}")
        sorted_coupling = sorted(
            report.coupling_metrics.items(), 
            key=lambda x: x[1]["instability"], 
            reverse=True
        )
        for mod, m in sorted_coupling[:20]:
            mod_short = mod[-38:] if len(mod) > 38 else mod
            lines.append(f"  {mod_short:<40} {m['afferent']:>4} {m['efferent']:>4} {m['instability']:>5.2f}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_duplicates(project_path: str = ".", min_lines: int = 6, threshold: float = 0.8) -> str:
    """
    Detecta código duplicado en el proyecto.
    """
    try:
        invest = CodeInvest(project_path)
        invest.discover_files()
        
        detector = DuplicateCodeDetector(min_lines=min_lines, similarity_threshold=threshold)
        duplicates = detector.detect(invest.python_files)
        
        if not duplicates:
            return f"✅ No se detectó código duplicado (min_lines={min_lines}, threshold={threshold:.0%})."
        
        lines = [f"📋 CÓDIGO DUPLICADO — {len(duplicates)} bloques detectados"]
        lines.append(f"")
        
        for d in duplicates[:20]:
            lines.append(f"  📄 {d.file_a}:{d.line_a}  ↔  {d.file_b}:{d.line_b}")
            lines.append(f"     Similitud: {d.similarity:.0%} | Líneas: {d.lines}")
            lines.append(f"     ```python")
            lines.append(f"     {d.code_snippet}")
            lines.append(f"     ```")
            lines.append(f"")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_patterns(project_path: str = ".") -> str:
    """
    Detecta patrones de diseño y anti-patrones en el proyecto.
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze()
        
        lines = [f"🎯 CODE INVEST — Patrones y Anti-patrones: {project_path}"]
        lines.append(f"")
        
        if report.design_patterns:
            lines.append(f"✨ PATRONES DE DISEÑO ({len(report.design_patterns)}):")
            for p in report.design_patterns:
                lines.append(f"  • {p.pattern} ({p.confidence:.0%}) — {p.file}:{p.class_name}")
                for e in p.evidence[:3]:
                    lines.append(f"     ↳ {e}")
            lines.append(f"")
        
        if report.anti_patterns:
            lines.append(f"⚠️ ANTI-PATRONES ({len(report.anti_patterns)}):")
            for a in report.anti_patterns:
                lines.append(f"  • {a.pattern} [{a.severity}] — {a.file}:{a.symbol}")
                for e in a.evidence[:2]:
                    lines.append(f"     ↳ {e}")
                lines.append(f"     💡 {a.suggestion}")
            lines.append(f"")
        
        if not report.design_patterns and not report.anti_patterns:
            lines.append("ℹ️ No se detectaron patrones ni anti-patrones significativos.")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_dead_code(project_path: str = ".") -> str:
    """
    Detecta código muerto (imports, funciones, clases no usadas).
    """
    try:
        invest = CodeInvest(project_path)
        invest.discover_files()
        
        detector = DeadCodeDetector(invest.project_root)
        detector.analyze_project(invest.python_files)
        
        all_dead = []
        for f in invest.python_files:
            all_dead.extend(detector.detect_dead_code(f))
        
        if not all_dead:
            return "✅ No se detectó código muerto obvio."
        
        lines = [f"💀 CÓDIGO MUERTO — {len(all_dead)} hallazgos"]
        lines.append(f"")
        
        by_type = defaultdict(list)
        for d in all_dead:
            by_type[d.type].append(d)
        
        for dtype, items in by_type.items():
            lines.append(f"  📦 {dtype} ({len(items)}):")
            for d in items[:10]:
                lines.append(f"     • {d.file}:{d.symbol} (confianza: {d.confidence:.0%})")
            lines.append(f"")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_complexity(project_path: str = ".", top: int = 20) -> str:
    """
    Ranking de funciones/métodos más complejos del proyecto.
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze()
        
        # Ordenar por complejidad ciclomática
        sorted_funcs = sorted(
            report.function_metrics.items(),
            key=lambda x: x[1].cyclomatic,
            reverse=True
        )
        
        lines = [f"📈 TOP {top} FUNCIONES MÁS COMPLEJAS — {project_path}"]
        lines.append(f"")
        lines.append(f"  {'Función':<50} {'CC':>4} {'Cog':>4} {'LOC':>5} {'MI':>5} {'Params':>6}")
        lines.append(f"  {'-'*50} {'-'*4} {'-'*4} {'-'*5} {'-'*5} {'-'*6}")
        
        for key, m in sorted_funcs[:top]:
            name = key.split(":")[-1]
            if len(name) > 48:
                name = name[:45] + "..."
            lines.append(f"  {name:<50} {m.cyclomatic:>4} {m.cognitive:>4} {m.lines_of_code:>5} {m.maintainability_index:>5.1f} {m.param_count:>6}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def code_invest_god_classes(project_path: str = ".") -> str:
    """
    Detecta y reporta God Classes en el proyecto.
    """
    try:
        invest = CodeInvest(project_path)
        report = invest.analyze()
        
        god_classes = [cm for cm in report.class_metrics if cm.is_god_class]
        
        if not god_classes:
            return "✅ No se detectaron God Classes."
        
        lines = [f"👑 GOD CLASSES DETECTADAS — {len(god_classes)}"]
        lines.append(f"")
        
        for gc in sorted(god_classes, key=lambda x: x.god_class_score, reverse=True):
            lines.append(f"  🔴 {gc.file}:{gc.line} — {gc.name}")
            lines.append(f"     Score: {gc.god_class_score:.2f} | WMC: {gc.wmc} | CBO: {gc.cbo} | Campos: {gc.fields} | Métodos: {gc.methods} | LCOM: {gc.lcom:.2f}")
            lines.append(f"     💡 Sugerencia: Extraer responsabilidades, aplicar SRP, usar composición.")
            lines.append(f"")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRO DE HERRAMIENTAS PARA AIION
# ═══════════════════════════════════════════════════════════════════════════

CODE_INVEST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "code_invest_analyze",
            "description": "Análisis completo de código (Code Invest) en proyecto Python: métricas, code smells, dependencias, duplicados, patrones, anti-patrones, código muerto, complejidad, God Classes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Ruta al proyecto (default: directorio actual)"},
                    "patterns": {"type": "array", "items": {"type": "string"}, "description": "Patrones glob (default: ['**/*.py'])"},
                    "format": {"type": "string", "enum": ["text", "markdown", "json"], "description": "Formato de salida", "default": "text"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_file",
            "description": "Análisis profundo de un solo archivo Python.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Ruta al archivo .py"},
                    "format": {"type": "string", "enum": ["text", "markdown", "json"], "default": "text"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_smells",
            "description": "Lista code smells detectados en el proyecto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."},
                    "severity": {"type": "string", "enum": ["critical", "warning", "info", "all"], "default": "all"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_dependencies",
            "description": "Análisis de dependencias y acoplamiento (circular deps, Ca/Ce, inestabilidad).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."},
                    "format": {"type": "string", "enum": ["text", "json"], "default": "text"}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_duplicates",
            "description": "Detecta código duplicado en el proyecto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."},
                    "min_lines": {"type": "integer", "default": 6},
                    "threshold": {"type": "number", "default": 0.8}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_patterns",
            "description": "Detecta patrones de diseño (GoF) y anti-patrones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_dead_code",
            "description": "Detecta código muerto (imports, funciones, clases no usadas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_complexity",
            "description": "Ranking de funciones/métodos más complejos del proyecto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."},
                    "top": {"type": "integer", "default": 20}
                },
                "required": ["project_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_invest_god_classes",
            "description": "Detecta God Classes (clases que hacen demasiado).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "default": "."}
                },
                "required": ["project_path"]
            }
        }
    },
]

# Exportar funciones para registro en tools/registry.py
__all__ = [
    "CodeInvest",
    "CodeInvestReport",
    "CodeMetric",
    "CodeSmell",
    "ComplexityMetrics",
    "ClassMetrics",
    "ModuleMetrics",
    "DependencyEdge",
    "CircularDependency",
    "CodeDuplicate",
    "DesignPattern",
    "AntiPattern",
    "DeadCode",
    "CODE_INVEST_TOOLS",
    "code_invest_analyze",
    "code_invest_file",
    "code_invest_smells",
    "code_invest_dependencies",
    "code_invest_duplicates",
    "code_invest_patterns",
    "code_invest_dead_code",
    "code_invest_complexity",
    "code_invest_god_classes",
]