#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

command -v python >/dev/null || fail "Python is required: pkg install python"
python - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python >=3.12 required, found {sys.version.split()[0]}")
print("PASS: Python", sys.version.split()[0])
PY

if [ ! -d .venv ]; then
  log "Creating Python virtual environment"
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

log "Installing project + test dependencies"
python -m pip install --upgrade pip
python -m pip install -e '.[test]'

log "Running repository production acceptance"
python scripts/production_acceptance.py

log "Running unit tests"
python -m pytest -q

if command -v node >/dev/null && command -v npm >/dev/null; then
  log "Running web build"
  (
    cd apps/gods-eye-web
    npm install --no-audit --no-fund
    npm run build
  )
else
  printf '\nDEFERRED: Node/npm not installed; web build was not executed.\n'
  printf 'Install with: pkg install nodejs-lts\n'
fi

if command -v git >/dev/null; then
  log "Repository state"
  git status --short --branch
  printf '\nHEAD: '
  git rev-parse HEAD
fi

cat <<'EOF'

========================================
QUANTSOIL TERMUX FIRST-RUN RESULT
========================================
PASS = repository acceptance + Python tests completed.
WEB  = completed only when Node/npm are available.
DEFERRED = real PostgreSQL/S3/Kubernetes/OIDC/TLS infrastructure;
            those require actual target services and credentials/configuration.

This script never fabricates cloud or cluster readiness.
========================================
EOF
