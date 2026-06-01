#!/bin/sh
set -eu

BACKUP_FILE="${1:-}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ -z "$BACKUP_FILE" ]; then
  log "Uso: restore.sh <arquivo_backup.sql.gz>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  log "Arquivo nao encontrado: ${BACKUP_FILE}"
  exit 1
fi

log "Iniciando restore: ${BACKUP_FILE} -> ${DB_NAME}@${DB_HOST:-postgres}"

gunzip -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD}" psql \
  -h "${DB_HOST:-postgres}" \
  -p "${DB_PORT:-5432}" \
  -U "${DB_USER}" \
  "${DB_NAME}"

log "Restore concluido."
