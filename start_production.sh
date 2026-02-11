#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
#  Production Start Script
# ──────────────────────────────────────────────────────────────────────────
#  Builds the frontend, then starts the Flask app via Gunicorn.
#
#  Usage:
#    chmod +x start_production.sh
#    ./start_production.sh
#
#  Prerequisites:
#    - Python venv already created (run setup.sh first)
#    - Node.js installed
#    - MySQL running and configured via env vars or .env
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸ $*${NC}"; }
ok()    { echo -e "${GREEN}✓ $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ── Load .env if present ────────────────────────────────────────────────
if [[ -f .env ]]; then
    info "Loading .env file…"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    ok "Environment loaded"
fi

# ── Activate virtual environment ────────────────────────────────────────
if [[ -d venv ]]; then
    source venv/bin/activate
    ok "Virtual environment activated"
elif [[ -d .venv ]]; then
    source .venv/bin/activate
    ok "Virtual environment activated"
else
    fail "No virtual environment found. Run setup.sh first."
fi

# ── Validate required env vars for production ────────────────────────────
export FLASK_ENV=production

if [[ -z "${SECRET_KEY:-}" ]]; then
    fail "SECRET_KEY must be set for production. Add it to .env or export it."
fi

# ── Build frontend ──────────────────────────────────────────────────────
info "Building frontend…"
cd frontend
npm install --production=false
npm run build
cd "$PROJECT_DIR"
ok "Frontend built → frontend/dist/"

# ── Install Python dependencies ─────────────────────────────────────────
info "Installing Python dependencies…"
pip install -q -r requirements.txt
ok "Python dependencies installed"

# ── Seed database (first run only) ──────────────────────────────────────
if [[ "${SEED_DB:-}" == "1" || "${SEED_DB:-}" == "true" ]]; then
    info "Seeding database (HPO terms)…"
    FLASK_ENV=production python -m backend.seed
    ok "Database seeded"
else
    # Auto-detect: seed if the patients table is empty
    PATIENT_COUNT=$(mysql -u "${MYSQL_USER:-root}" \
        ${MYSQL_PASSWORD:+-p"$MYSQL_PASSWORD"} \
        -h "${MYSQL_HOST:-localhost}" \
        -P "${MYSQL_PORT:-3306}" \
        -N -s -e "SELECT COUNT(*) FROM ${MYSQL_DB:-patient_db}.patients" 2>/dev/null || echo "0")
    if [[ "$PATIENT_COUNT" == "0" ]]; then
        info "Empty database detected — seeding with HPO terms…"
        FLASK_ENV=production python -m backend.seed
        ok "Database seeded (HPO terms only)"
    else
        ok "Database already has $PATIENT_COUNT patients — skipping seed"
    fi
fi

# ── Start Gunicorn ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Starting production server${NC}"
echo -e "${GREEN}   Bind: ${GUNICORN_BIND:-0.0.0.0:8000}${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""

exec gunicorn -c gunicorn.conf.py run:app
