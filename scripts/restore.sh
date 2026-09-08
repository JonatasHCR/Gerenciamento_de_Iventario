#!/bin/sh
set -eu

BACKUP_FILE="${1:-}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ -z "$BACKUP_FILE" ]; then
  log "Uso: restore.sh <arquivo_backup.sql>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  log "Arquivo nao encontrado: ${BACKUP_FILE}"
  exit 1
fi

log "Iniciando restore: ${BACKUP_FILE} -> ${DB_NAME}@${DB_HOST:-postgres}"

# ON_ERROR_STOP=1: sem isto o psql segue depois de um erro e sai com codigo
# 0 tendo restaurado pela metade.
# O sed tira `SET transaction_timeout`, que o pg_dump 17 escreve e o servidor
# 16 nao conhece; sozinha, essa linha abortaria tudo no cabecalho.
sed '/^SET transaction_timeout/d' "$BACKUP_FILE" \
  | PGPASSWORD="${DB_PASSWORD}" psql \
      -v ON_ERROR_STOP=1 \
      -h "${DB_HOST:-postgres}" \
      -p "${DB_PORT:-5432}" \
      -U "${DB_USER}" \
      "${DB_NAME}"

log "Restore concluido."
