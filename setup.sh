#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
#  Patient Information System — Full Setup Script
# ──────────────────────────────────────────────────────────────────────────
#  This script will:
#    1. Check prerequisites (Python, Node, MySQL)
#    2. Create/activate a Python virtual environment
#    3. Install Python dependencies
#    4. Create the MySQL database
#    5. Create data directories (data/, data/vcf/)
#    6. Install Node/frontend dependencies & build the React app
#    7. Seed the database (HPO terms) & generate demo patients
#
#  Usage:
#    chmod +x setup.sh
#    ./setup.sh
#
#  Environment variables (optional — defaults shown):
#    MYSQL_USER=root   MYSQL_PASSWORD=password
#    MYSQL_HOST=localhost   MYSQL_PORT=3306   MYSQL_DB=hpo_database
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}▸ $*${NC}"; }
ok()    { echo -e "${GREEN}✓ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

# ── Configuration ────────────────────────────────────────────────────────
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DB="${MYSQL_DB:-hpo_database}"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   Patient Information System — Setup${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Check prerequisites ──────────────────────────────────────────────
info "Checking prerequisites…"

# Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    fail "Python 3 is required but not found. Install it from https://python.org"
fi
PY_VERSION=$($PYTHON --version 2>&1)
ok "Python found: $PY_VERSION"

# pip
if ! $PYTHON -m pip --version &>/dev/null; then
    fail "pip is required but not found."
fi
ok "pip available"

# Node.js
if ! command -v node &>/dev/null; then
    fail "Node.js is required but not found. Install it from https://nodejs.org"
fi
NODE_VERSION=$(node --version)
ok "Node.js found: $NODE_VERSION"

# npm
if ! command -v npm &>/dev/null; then
    fail "npm is required but not found."
fi
ok "npm found: $(npm --version)"

# MySQL client
if command -v mysql &>/dev/null; then
    ok "mysql client found"
    HAS_MYSQL_CLI=true
else
    warn "mysql CLI not found — will skip automatic database creation."
    warn "Please create the database manually:"
    warn "  CREATE DATABASE IF NOT EXISTS ${MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    HAS_MYSQL_CLI=false
fi

echo ""

# ── 2. Virtual environment ───────────────────────────────────────────────
VENV_DIR="$PROJECT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    info "Existing virtual environment found at .venv"
else
    info "Creating virtual environment at .venv…"
    $PYTHON -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
PYTHON="$VENV_DIR/bin/python"
ok "Virtual environment active: $(which python)"
echo ""

# ── 3. Python dependencies ──────────────────────────────────────────────
info "Installing Python dependencies…"
$PYTHON -m pip install -r requirements.txt --quiet
ok "Python packages installed"
echo ""

# ── 4. Create MySQL database ────────────────────────────────────────────
if [ "$HAS_MYSQL_CLI" = true ]; then
    info "Creating MySQL database '${MYSQL_DB}' (if it doesn't exist)…"

    MYSQL_CMD="mysql"
    MYSQL_ARGS=(-u "$MYSQL_USER" -h "$MYSQL_HOST" -P "$MYSQL_PORT")
    if [ -n "$MYSQL_PASSWORD" ] && [ "$MYSQL_PASSWORD" != "" ]; then
        MYSQL_ARGS+=(-p"$MYSQL_PASSWORD")
    fi

    if $MYSQL_CMD "${MYSQL_ARGS[@]}" -e \
        "CREATE DATABASE IF NOT EXISTS \`${MYSQL_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null; then
        ok "Database '${MYSQL_DB}' ready"
    else
        warn "Could not create database automatically."
        warn "Please create it manually and re-run, or ensure MySQL is running."
    fi
else
    warn "Skipping database creation (no mysql CLI). Ensure '${MYSQL_DB}' exists."
fi
echo ""

# ── 5. Create data directories ───────────────────────────────────────────
info "Creating data directories…"
mkdir -p "$PROJECT_DIR/data/vcf"
ok "data/ and data/vcf/ ready"
echo ""

# ── 6. Frontend build ────────────────────────────────────────────────────
info "Installing frontend dependencies…"
cd "$PROJECT_DIR/frontend"
npm install --silent 2>/dev/null || npm install
ok "Node modules installed"

info "Building React/TypeScript frontend…"
npm run build
ok "Frontend built → frontend/dist/"
cd "$PROJECT_DIR"
echo ""

# ── 7. Seed database ────────────────────────────────────────────────────
info "Seeding HPO terms…"
$PYTHON -m backend.seed
ok "HPO terms loaded"

info "Generating demo patients…"
$PYTHON -m backend.generate_mock_data --predefined
ok "Database seeded (HPO terms + 20 demo patients)"
echo ""

# ── Done ─────────────────────────────────────────────────────────────────
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Setup complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Activate the virtual environment first:"
echo -e "    ${CYAN}source .venv/bin/activate${NC}"
echo ""
echo -e "  To start the app:"
echo -e "    ${CYAN}python run.py${NC}"
echo -e "    Open ${CYAN}http://localhost:5000${NC}"
echo ""
echo -e "  For frontend development with hot-reload:"
echo -e "    Terminal 1: ${CYAN}python run.py${NC}                    (API on :5000)"
echo -e "    Terminal 2: ${CYAN}cd frontend && npm run dev${NC}       (Vite on :3000)"
echo ""
