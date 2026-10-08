#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${ALLOW_DESTRUCTIVE_RESTORE:?Set ALLOW_DESTRUCTIVE_RESTORE=1 only for an isolated recovery target}"
if [[ "$ALLOW_DESTRUCTIVE_RESTORE" != "1" ]]; then exit 2; fi
: "${1:?usage: ALLOW_DESTRUCTIVE_RESTORE=1 DATABASE_URL=... restore_postgres.sh backup.dump}"
pg_restore --clean --if-exists --no-owner --no-privileges --dbname "$DATABASE_URL" "$1"
printf 'restore completed; run schema validation, evidence hash verification, and replay/evaluation gates before serving traffic.\n'
