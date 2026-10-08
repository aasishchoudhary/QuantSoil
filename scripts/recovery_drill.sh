#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
workdir="${1:-$(mktemp -d)}"
mkdir -p "$workdir"
trap 'rm -rf "$workdir"' EXIT

backup="$workdir/production-drill.dump"
recovery_db="gods_eye_recovery_drill_$$"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$recovery_db\""
cleanup() {
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$recovery_db\"" >/dev/null
}
trap cleanup EXIT

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE TABLE IF NOT EXISTS public.recovery_drill_marker(id integer PRIMARY KEY, marker text NOT NULL)"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO public.recovery_drill_marker VALUES (1, 'production-acceptance') ON CONFLICT (id) DO UPDATE SET marker=EXCLUDED.marker"

pg_dump --format=custom --no-owner --no-privileges --file "$backup" "$DATABASE_URL"
pg_restore --list "$backup" >/dev/null
ALLOW_DESTRUCTIVE_RESTORE=1 DATABASE_URL="${DATABASE_URL%/*}/$recovery_db" "$(dirname "$0")/restore_postgres.sh" "$backup"

marker="$(psql "$DATABASE_URL%/*/$recovery_db" -Atqc "SELECT marker FROM public.recovery_drill_marker WHERE id=1")"
test "$marker" = "production-acceptance"
printf 'PASS: isolated PostgreSQL backup/restore drill (%s)\n' "$recovery_db"
