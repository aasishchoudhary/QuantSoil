#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
out="${1:-backups/quantsoil-$(date -u +%Y%m%dT%H%M%SZ).dump}"
mkdir -p "$(dirname "$out")"
umask 077
pg_dump --format=custom --no-owner --no-privileges --file "$out" "$DATABASE_URL"
pg_restore --list "$out" >/dev/null
printf 'backup verified: %s\n' "$out"
