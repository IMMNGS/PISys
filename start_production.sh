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
info "Installing frontend dependencies for build (including dev deps)…"
npm ci
npm run build
info "Pruning dev dependencies to keep production install small…"
npm prune --production || true
cd "$PROJECT_DIR"
ok "Frontend built → frontend/dist/"

# ── Install Python dependencies ─────────────────────────────────────────
info "Installing Python dependencies…"
pip install -q -r requirements.txt
ok "Python dependencies installed"

# ── Load HPO terms on first run ─────────────────────────────────────────
HPO_COUNT=$(mysql -u "${MYSQL_USER:-root}" \
    ${MYSQL_PASSWORD:+-p"$MYSQL_PASSWORD"} \
    -h "${MYSQL_HOST:-localhost}" \
    -P "${MYSQL_PORT:-3306}" \
    -N -s -e "SELECT COUNT(*) FROM ${MYSQL_DB:-patient_db}.hpo_terms" 2>/dev/null || echo "0")
if [[ "$HPO_COUNT" == "0" ]]; then
    info "No HPO terms found — loading from PyHPO (one-time init)…"
    python -c "
from backend.app import create_app
import sys
app = create_app()
with app.app_context():
    from backend.models import db, HPOTerm
    from pyhpo import Ontology
    _ = Ontology()
    added = 0
    for term in Ontology:
        if not HPOTerm.query.filter_by(hpo_id=term.id).first():
            db.session.add(HPOTerm(
                hpo_id=term.id,
                term_name=term.name,
                definition=term.definition or None,
                synonyms=', '.join(term.synonym) if term.synonym else None,
            ))
            added += 1
    db.session.commit()
    print(f'Loaded {added} HPO terms')
"
    ok "HPO terms loaded"
else
    ok "HPO terms already loaded ($HPO_COUNT terms) — skipping"
fi

# ── Start Gunicorn ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Starting production server${NC}"
echo -e "${GREEN}   Bind: ${GUNICORN_BIND:-0.0.0.0:8000}${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""

exec gunicorn -c gunicorn.conf.py run:app
