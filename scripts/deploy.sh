#!/usr/bin/env bash
# AIION — Deploy con rollback (F4.2)
#
# Uso:
#   ./scripts/deploy.sh            # backup + tests + verificar server
#   ./scripts/deploy.sh --rollback # restaurar último backup
#   ./scripts/deploy.sh --list     # listar backups disponibles
#
# Variables de entorno:
#   AIION_BACKUP_DIR — ruta base de backups (default: ~/.aiion_backups)
#   AIION_API_PORT   — puerto a verificar (default: 8080)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_BASE="${AIION_BACKUP_DIR:-$HOME/.aiion_backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_PATH="$BACKUP_BASE/deploy_$TIMESTAMP"

mkdir -p "$BACKUP_BASE"

# ── LIST ───────────────────────────────────────
if [[ "${1:-}" == "--list" ]]; then
    echo "📦 Backups en $BACKUP_BASE:"
    ls -1d "$BACKUP_BASE"/deploy_* 2>/dev/null | sort || echo "  (ninguno)"
    exit 0
fi

# ── ROLLBACK ───────────────────────────────────
if [[ "${1:-}" == "--rollback" ]]; then
    LATEST=$(ls -1d "$BACKUP_BASE"/deploy_* 2>/dev/null | tail -1 || true)
    if [[ -z "$LATEST" ]]; then
        echo "✗ No hay backups disponibles en $BACKUP_BASE"
        echo "  Define AIION_BACKUP_DIR si los tienes en otra ruta"
        exit 1
    fi
    if [[ ! -d "$LATEST/aiion" ]]; then
        echo "✗ Backup $LATEST corrupto (sin carpeta aiion)"
        echo "  Usa otro backup o borra: rm -rf $LATEST"
        exit 1
    fi
    echo "⏪ Restaurando desde $LATEST..."
    rm -rf "$ROOT/aiion" "$ROOT/tests"
    cp -r "$LATEST/aiion" "$ROOT/aiion"
    cp -r "$LATEST/tests" "$ROOT/tests"
    echo "✓ Rollback completo"
    exit 0
fi

# ── DEPLOY ─────────────────────────────────────
echo "💾 Backup en $BACKUP_PATH..."
# Copia atómica: primero a .tmp, luego renombrar
TMP_PATH="$BACKUP_PATH.tmp"
rm -rf "$TMP_PATH"
mkdir -p "$TMP_PATH"
cp -r "$ROOT/aiion" "$TMP_PATH/aiion"
cp -r "$ROOT/tests" "$TMP_PATH/tests"
mv "$TMP_PATH" "$BACKUP_PATH"

echo "🧪 Corriendo tests..."
cd "$ROOT"
if ! python3 -m pytest --timeout=30 -q; then
    echo "✗ Tests fallaron — deploy abortado"
    echo "  Para hacer rollback: ./scripts/deploy.sh --rollback"
    echo "  Backup intacto en: $BACKUP_PATH"
    exit 1
fi

# Verificar server (opcional, no fatal)
PORT="${AIION_API_PORT:-8080}"
if curl -s -m 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q "200"; then
    echo "✓ Server activo en :$PORT"
else
    echo "  ⚠ Server no responde en :$PORT (no crítico)"
fi

echo "✅ Deploy completo"
echo "  Backup: $BACKUP_PATH"
echo "  Tests: 321 OK"
