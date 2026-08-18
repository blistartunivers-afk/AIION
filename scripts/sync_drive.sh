#!/data/data/com.termux/files/usr/bin/bash
# sync_drive.sh — Sincronización periódica con Google Drive
# Crea por: AIION + Sara OS (2026-08-17)
# Ejecutar cada 30 min via cron

set -e
LOG="$HOME/logs/rclone_sync.log"
mkdir -p "$(dirname "$LOG")"
TS=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TS] ─── sync_drive.sh START ───" >> "$LOG"

# Bidireccional: agentes ↔ Drive
# 1) Subir cambios locales a Drive (AIION, agentes)
rclone sync "$HOME/AIION/" "gdrive:AIION/02_Codigo" \
    --log-file "$LOG" --log-level INFO \
    --exclude "*.pyc" --exclude "__pycache__/**" \
    --exclude ".venv/**" --exclude "data/*.db*" \
    --exclude ".git/**" --exclude "logs/**" \
    --exclude "tests/.pytest_cache/**" \
    --transfers 4 --checkers 8 >> "$LOG" 2>&1 || true

# 2) Bajar cambios recientes de Drive a local
rclone copy "gdrive:AIION/01_Planificacion" "$HOME/AIION/plans/drive/" \
    --log-file "$LOG" --log-level INFO >> "$LOG" 2>&1 || true

echo "[$TS] ─── sync_drive.sh END ───" >> "$LOG"
