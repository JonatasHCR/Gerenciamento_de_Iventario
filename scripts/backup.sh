#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Iniciando backup: ${DB_NAME}@${DB_HOST:-postgres}"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
  -h "${DB_HOST:-postgres}" \
  -p "${DB_PORT:-5432}" \
  -U "${DB_USER}" \
  "${DB_NAME}" \
  | gzip > "${BACKUP_FILE}"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
log "Backup salvo: ${BACKUP_FILE} (${SIZE})"

REMOVED=$(find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime +"${KEEP_DAYS}" -print -delete 2>/dev/null | wc -l | tr -d ' ')
[ "$REMOVED" -gt 0 ] && log "Rotacao: ${REMOVED} arquivo(s) removido(s) (> ${KEEP_DAYS} dias)"

log "Concluido."
