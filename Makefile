# AIION Makefile — Comandos de desarrollo
# Uso: make <target>

.PHONY: help install test test-unit test-integration test-cov lint typecheck format check clean run release

# Configuración
PYTHON := python3
PIP := pip
POETRY := poetry
VENV := .venv

# Colores para output
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
NC     := \033[0m

help: ## Muestra esta ayuda
	@echo "$(GREEN)AIION - Comandos disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# INSTALACIÓN Y ENTORNO
# =============================================================================

install: ## Instala dependencias de desarrollo en venv
	@echo "$(GREEN)Creando entorno virtual...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/$(PIP) install -U pip setuptools wheel
	$(VENV)/bin/$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ Entorno listo. Activa con: source $(VENV)/bin/activate$(NC)"

install-system: ## Instala dependencias del sistema (Termux/Android)
	@echo "$(GREEN)Instalando dependencias del sistema...$(NC)"
	pkg install -y termux-api mpv ollama 2>/dev/null || echo "$(YELLOW)Algunos paquetes no disponibles en este entorno$(NC)"

# =============================================================================
# TESTS
# =============================================================================

test: test-unit ## Ejecuta todos los tests (unit + integration)


test-unit: ## Tests unitarios rápidos (sin deps externas)
	@echo "$(GREEN)Ejecutando tests unitarios...$(NC)"
	$(VENV)/bin/pytest tests/ -m "unit" -v


test-integration: ## Tests de integración (requieren termux-api)
	@echo "$(GREEN)Ejecutando tests de integración...$(NC)"
	$(VENV)/bin/pytest tests/ -m "integration" -v


test-android: ## Tests que requieren Android/Termux
	@echo "$(GREEN)Ejecutando tests Android...$(NC)"
	$(VENV)/bin/pytest tests/ -m "android" -v


test-slow: ## Tests lentos (>5s)
	@echo "$(GREEN)Ejecutando tests lentos...$(NC)"
	$(VENV)/bin/pytest tests/ -m "slow" -v


test-cov: ## Tests con cobertura
	@echo "$(GREEN)Ejecutando tests con cobertura...$(NC)"
	$(VENV)/bin/pytest tests/ --cov=aiion --cov-report=term-missing --cov-report=html


test-watch: ## Tests en modo watch (requiere pytest-watch)
	$(VENV)/bin/ptw tests/ -- -v

# =============================================================================
# CALIDAD DE CÓDIGO
# =============================================================================

lint: ## Linting con Ruff
	@echo "$(GREEN)Linting...$(NC)"
	$(VENV)/bin/ruff check aiion/ tests/

lint-fix: ## Linting con auto-fix
	@echo "$(GREEN)Linting + fix...$(NC)"
	$(VENV)/bin/ruff check aiion/ tests/ --fix

format: ## Formateo con Black + Ruff
	@echo "$(GREEN)Formateando...$(NC)"
	$(VENV)/bin/ruff format aiion/ tests/
	$(VENV)/bin/black aiion/ tests/

format-check: ## Verifica formato sin modificar
	@echo "$(GREEN)Verificando formato...$(NC)"
	$(VENV)/bin/ruff format --check aiion/ tests/
	$(VENV)/bin/black --check aiion/ tests/


typecheck: ## Type checking con MyPy
	@echo "$(GREEN)Type checking...$(NC)"
	$(VENV)/bin/mypy aiion/

check: lint format-check typecheck ## Pipeline completo de calidad
	@echo "$(GREEN)✓ Todos los checks pasan$(NC)"

# =============================================================================
# EJECUCIÓN
# =============================================================================

run: ## Ejecuta AIION en modo interactivo
	@echo "$(GREEN)Iniciando AIION...$(NC)"
	$(PYTHON) -m aiion

run-headless: ## Ejecuta AIION en modo headless (ej: python -m aiion -p "hola")
	@echo "$(GREEN)Modo headless$(NC)"
	$(PYTHON) -m aiion -p "$(ARGS)"

run-dev: ## Ejecuta con hot-reload (requiere watchdog)
	@echo "$(GREEN)Modo desarrollo con hot-reload...$(NC)"
	$(VENV)/bin/watchmedo auto-restart --directory=aiion --pattern=*.py --recursive -- $(PYTHON) -m aiion

# =============================================================================
# LIMPIEZA
# =============================================================================

clean: ## Limpia archivos generados
	@echo "$(GREEN)Limpiando...$(NC)"
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete

clean-data: ## Limpia datos de AIION (CUIDADO: borra memoria)
	@echo "$(RED)ADVERTENCIA: Borrando datos de AIION...$(NC)"
	rm -rf data/aiion_memory.md data/aiion_history.jsonl data/aiion_sensor_data.db

# =============================================================================
# RELEASE
# =============================================================================

version: ## Muestra versión actual
	@grep '^version' pyproject.toml | cut -d'"' -f2

bump-patch: ## Incrementa versión patch (0.2.0 -> 0.2.1)
	@$(VENV)/bin/bump2version patch

bump-minor: ## Incrementa versión minor (0.2.0 -> 0.3.0)
	@$(VENV)/bin/bump2version minor

bump-major: ## Incrementa versión major (0.2.0 -> 1.0.0)
	@$(VENV)/bin/bump2version major

build: clean ## Construye paquetes de distribución
	@echo "$(GREEN)Construyendo paquetes...$(NC)"
	$(VENV)/bin/$(PYTHON) -m build

publish-test: build ## Publica a TestPyPI
	@echo "$(GREEN)Publicando a TestPyPI...$(NC)"
	$(VENV)/bin/twine upload --repository testpypi dist/*

publish: build ## Publica a PyPI
	@echo "$(GREEN)Publicando a PyPI...$(NC)"
	$(VENV)/bin/twine upload dist/*

release: check test build ## Pipeline completo de release
	@echo "$(GREEN)✓ Release listo. Ejecuta 'make publish' para subir a PyPI$(NC)"

# =============================================================================
# DESARROLLO
# =============================================================================

pre-commit-install: ## Instala hooks de pre-commit
	$(VENV)/bin/pre-commit install
	$(VENV)/bin/pre-commit install --hook-type commit-msg

pre-commit-run: ## Ejecuta pre-commit en todos los archivos
	$(VENV)/bin/pre-commit run --all-files

docs: ## Genera documentación local
	@echo "$(GREEN)Generando docs...$(NC)"
	$(VENV)/bin/mkdocs serve

docs-build: ## Construye docs estáticas
	$(VENV)/bin/mkdocs build

# =============================================================================
# UTILIDADES ANDROID/TERMUX
# =============================================================================

termux-setup: ## Configura Termux para AIION (ejecutar en Termux)
	@echo "$(GREEN)Configurando Termux...$(NC)"
	pkg update && pkg upgrade -y
	pkg install -y python termux-api mpv git openssh
	termux-setup-storage
	@echo "$(GREEN)✓ Termux listo. Instala app Termux:API desde F-Droid/Play Store$(NC)"

ollama-serve: ## Inicia Ollama en background
	@echo "$(GREEN)Iniciando Ollama...$(NC)"
	ollama serve &

ollama-pull: ## Descarga modelos recomendados
	@echo "$(GREEN)Descargando modelos...$(NC)"
	ollama pull qwen3-coder:latest
	ollama pull deepseek-coder:latest
	ollama pull gemma3:latest

# =============================================================================
# DEBUG
# =============================================================================

debug: ## Ejecuta con debug verbose
	PYTHONPATH=. $(PYTHON) -m aiion --debug

profile: ## Profile de rendimiento
	PYTHONPATH=. $(PYTHON) -m cProfile -o profile.stats -m aiion
	$(VENV)/bin/snakeviz profile.stats

# =============================================================================
# DEFAULT
# =============================================================================

default: help
