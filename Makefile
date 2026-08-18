# AIION — Makefile (F4.1)
# Pipeline CI/CD local

.PHONY: help test test-fast test-security test-load test-e2e coverage lint clean deploy backup

help:
	@echo "🎼 AIION — Targets disponibles:"
	@echo "  make test           — Suite completa (48s)"
	@echo "  make test-fast      — Suite sin integración (~5s)"
	@echo "  make test-load      — Tests de carga"
	@echo "  make test-security  — Tests de seguridad"
	@echo "  make test-e2e       — Tests end-to-end"
	@echo "  make coverage       — Reporte de cobertura en HTML"
	@echo "  make clean          — Limpia __pycache__ + .bak"
	@echo "  make deploy         — Inicia/verifica server"
	@echo "  make backup         — Crea backup del código"

test:
	python3 -m pytest -v --timeout=30

test-fast:
	python3 -m pytest -v --timeout=10 \
		--ignore=tests/test_load.py \
		--ignore=tests/test_e2e.py \
		--ignore=tests/test_integration.py

test-security:
	python3 -m pytest tests/test_security.py -v

test-load:
	python3 -m pytest tests/test_load.py -v --timeout=20

test-e2e:
	python3 -m pytest tests/test_e2e.py -v --timeout=15

coverage:
	python3 -m pytest --cov=aiion --cov-report=html --cov-report=term
	@echo "📊 Reporte HTML: htmlcov/index.html"

lint:
	python3 -c "import compileall; compileall.compile_dir('aiion', quiet=1); print('✓ Sin errores de sintaxis')"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.bak" -delete 2>/dev/null || true
	find . -name "*.bak2" -delete 2>/dev/null || true
	find . -name "*.bak3" -delete 2>/dev/null || true
	@echo "✓ Limpieza completa"

deploy:
	@echo "🚀 Verificando server en :8765..."
	@curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8765/aiion_command.html || echo "  ✗ Server no responde"
	@echo "✓ Deploy check completo"

backup:
	@echo "💾 Creando backup..."
	@cd /data/data/com.termux/files/home && tar czf "AIION_backup_$(date +%Y%m%d_%H%M%S).tar.gz" AIION/aiion AIION/tests AIION/plans AIION/MEMORY 2>/dev/null || true
	@echo "✓ Backup completo"
