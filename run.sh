#!/usr/bin/env bash
set -euo pipefail

# Unified script to perform first-time setup and start the app in
# development or production mode.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸ $*${NC}"; }
ok()    { echo -e "${GREEN}✓ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Load .env if present
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODE="production"
RUN_LOCAL_LLM="${RUN_LOCAL_LLM:-1}"

for arg in "$@"; do
  case "$arg" in
    setup|development|production)
      MODE="$arg"
      ;;
    --no-ai|-n)
      RUN_LOCAL_LLM=0
      ;;
    -h|--help)
      echo "Usage: $0 [--no-ai] [setup|development|production]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--no-ai] [setup|development|production]"
      exit 2
      ;;
  esac
done

MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DB="${MYSQL_DB:-hpo_database}"
LOCAL_LLM_PORT="${LOCAL_LLM_PORT:-8080}"
LOCAL_LLM_BASE_URL="${LOCAL_LLM_BASE_URL:-http://127.0.0.1:${LOCAL_LLM_PORT}/v1/chat/completions}"
LOCAL_LLM_MODEL_FILE="${LOCAL_LLM_MODEL_FILE:-$PROJECT_DIR/data/local_ai/models/Qwen3.5-4B-Q4_K_M.gguf}"
LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-qwen3.5-4b-instruct}"

export LOCAL_LLM_PORT LOCAL_LLM_BASE_URL LOCAL_LLM_MODEL_FILE LOCAL_LLM_MODEL

GUNICORN_PID=""
BACKEND_PID=""
LLM_PID=""

cleanup() {
  if [[ -n "${GUNICORN_PID:-}" ]]; then
    kill "$GUNICORN_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${LLM_PID:-}" ]]; then
    kill "$LLM_PID" >/dev/null 2>&1 || true
  fi
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  local delay="${4:-1}"

  for ((i = 1; i <= attempts; i++)); do
    if python3 - <<PY >/dev/null 2>&1
from urllib.request import urlopen
urlopen("$url", timeout=2)
PY
    then
      return 0
    fi
    sleep "$delay"
  done

  fail "$label did not become ready at $url"
}

start_local_llm() {
  if [[ "$RUN_LOCAL_LLM" == "0" ]]; then
    warn "RUN_LOCAL_LLM=0 — skipping local LLM startup"
    return 0
  fi

  if [[ ! -f "$LOCAL_LLM_MODEL_FILE" ]]; then
    fail "Local LLM model file not found: $LOCAL_LLM_MODEL_FILE"
  fi

  info "Starting local LLM server on port ${LOCAL_LLM_PORT}"
  python scripts/start_local_llm.py --mode llama --host 127.0.0.1 --port "$LOCAL_LLM_PORT" &
  LLM_PID=$!
  wait_for_http "http://127.0.0.1:${LOCAL_LLM_PORT}/health" "Local LLM server"
  ok "Local LLM server ready"
}

# Detect whether basic setup steps are needed
first_time_setup=false
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  first_time_setup=true
fi
if [ ! -d "$PROJECT_DIR/data/vcf" ]; then
  first_time_setup=true
fi

if [ "$MODE" = "setup" ]; then
  first_time_setup=true
fi

if [ "$first_time_setup" = true ]; then
  info "Running first-time setup steps..."

  # Check Python
  if command -v python3 &>/dev/null; then
    PYTHON=python3
  elif command -v python &>/dev/null; then
    PYTHON=python
  else
    fail "Python 3 is required but not found."
  fi
  ok "Python: $($PYTHON --version 2>&1)"

  # Check Node
  if ! command -v node &>/dev/null; then
    fail "Node.js is required but not found."
  fi
  ok "Node: $(node --version)"

  # Create venv if missing
  if [ ! -d "$PROJECT_DIR/.venv" ]; then
    info "Creating virtual environment at .venv"
    $PYTHON -m venv "$PROJECT_DIR/.venv"
  else
    info "Virtual environment already exists"
  fi

  # Activate venv
  # shellcheck disable=SC1091
  if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
  elif [ -f "$PROJECT_DIR/.venv/Scripts/activate" ]; then
    source "$PROJECT_DIR/.venv/Scripts/activate"
  else
    fail "Could not find a virtual environment activate script in .venv/bin or .venv/Scripts."
  fi
  ok "Virtual environment activated: $(which python)"

  # Install python deps
  info "Installing Python dependencies"
  pip install -r requirements.txt
  ok "Python dependencies installed"

  # Create data directories
  info "Creating data directories"
  mkdir -p "$PROJECT_DIR/data/vcf"
  mkdir -p "$PROJECT_DIR/data/rag/raw"
  mkdir -p "$PROJECT_DIR/data/rag/corpus"
  mkdir -p "$PROJECT_DIR/data/rag/eval"
  mkdir -p "$PROJECT_DIR/data/local_ai/bin"
  mkdir -p "$PROJECT_DIR/data/local_ai/models"
  if [ ! -f "$PROJECT_DIR/data/disease_terms.csv" ]; then
    cat > "$PROJECT_DIR/data/disease_terms.csv" <<'CSV'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
CSV
    ok "Created data/disease_terms.csv template"
  fi
  ok "data/, data/vcf/, data/rag/, and data/local_ai/ ready"

  # MySQL DB creation if CLI available
  if command -v mysql &>/dev/null; then
    info "Ensuring MySQL database '${MYSQL_DB}' exists (if possible)"
    MYSQL_ARGS=(-u "$MYSQL_USER" -h "$MYSQL_HOST" -P "$MYSQL_PORT")
    if [ -n "$MYSQL_PASSWORD" ]; then
      MYSQL_ARGS+=(-p"$MYSQL_PASSWORD")
    fi
    mysql "${MYSQL_ARGS[@]}" -e "CREATE DATABASE IF NOT EXISTS \`${MYSQL_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || warn "Could not create database automatically"
  else
    warn "mysql CLI not found — skipping automatic DB creation"
  fi

  # Frontend install/build (do full build during setup)
  info "Installing frontend dependencies and building (setup)"
  (cd frontend && npm install --silent 2>/dev/null || npm install)
  (cd frontend && npm run build)
  ok "Frontend installed and built"

  ok "First-time setup finished"
fi

# Ensure venv is active for subsequent steps
if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"
fi

# Ensure disease terms CSV exists and sync terms into DB
if [ ! -f "$PROJECT_DIR/data/disease_terms.csv" ]; then
  info "Creating data/disease_terms.csv template"
  cat > "$PROJECT_DIR/data/disease_terms.csv" <<'CSV'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
CSV
fi

info "Syncing disease terms from data/disease_terms.csv"
python - <<'PY'
import csv
from pathlib import Path

from backend.app import create_app
from backend.models import DiseaseTerm, db


def normalize(text: str) -> str:
  return " ".join((text or "").strip().lower().split())


csv_path = Path("data/disease_terms.csv")
if not csv_path.exists():
  print("No disease_terms.csv found; skipping")
  raise SystemExit(0)

app = create_app()
added = 0
updated = 0

with app.app_context():
  with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
      term_name = (row.get("term_name") or "").strip()
      notes = (row.get("notes") or "").strip() or None
      if not term_name:
        continue

      normalized = normalize(term_name)
      existing = DiseaseTerm.query.filter_by(normalized_name=normalized).first()
      if existing is None:
        db.session.add(DiseaseTerm(
          term_name=term_name,
          normalized_name=normalized,
          notes=notes,
        ))
        added += 1
      else:
        changed = False
        if existing.term_name != term_name:
          existing.term_name = term_name
          changed = True
        if notes and existing.notes != notes:
          existing.notes = notes
          changed = True
        if changed:
          updated += 1

  db.session.commit()

print(f"Disease terms sync complete. Added {added}, updated {updated}.")
PY
ok "Disease terms sync completed"

if [ "$MODE" = "production" ]; then
  info "Starting in production mode"

  export FLASK_ENV=production
  if [[ -z "${SECRET_KEY:-}" ]]; then
    # Generate a random SECRET_KEY and warn the user
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    export SECRET_KEY
    warn "SECRET_KEY was not set. Generated a random one for this session: $SECRET_KEY"
    warn "Set SECRET_KEY in your environment or .env for persistent sessions."
  fi

  # Build frontend for production
  info "Building frontend for production"
  # Keep devDependencies by default so local lint/test tooling remains available
  # after a production build. Set PRUNE_FRONTEND_DEV_DEPS=1 to restore pruning.
  PRUNE_FRONTEND_DEV_DEPS="${PRUNE_FRONTEND_DEV_DEPS:-0}"
  if [[ "$PRUNE_FRONTEND_DEV_DEPS" == "1" ]]; then
    (cd frontend && npm ci && npm run build && npm prune --omit=dev || true)
    warn "Frontend devDependencies pruned (PRUNE_FRONTEND_DEV_DEPS=1). Lint/test tools may be unavailable until npm install."
  else
    (cd frontend && npm ci && npm run build)
  fi
  ok "Frontend built → frontend/dist/"

  # Install/ensure python deps are present (quiet attempt)
  info "Ensuring Python dependencies installed"
  pip install -r requirements.txt
  ok "Python dependencies OK"

  # One-time HPO load detection (best-effort using mysql CLI)
  if command -v mysql &>/dev/null; then
    HPO_COUNT=$(mysql -u "$MYSQL_USER" ${MYSQL_PASSWORD:+-p"$MYSQL_PASSWORD"} -h "$MYSQL_HOST" -P "$MYSQL_PORT" -N -s -e "SELECT COUNT(*) FROM ${MYSQL_DB}.hpo_terms" 2>/dev/null || echo "0")
  else
    HPO_COUNT=1
  fi
  if [[ "$HPO_COUNT" == "0" ]]; then
    info "No HPO terms found — loading (one-time)"
    python - <<'PY'
from backend.app import create_app
from backend.models import db, HPOTerm
from pyhpo import Ontology
app = create_app()
with app.app_context():
    ont = Ontology()
    added = 0
    for term in ont:
        if not HPOTerm.query.filter_by(hpo_id=term.id).first():
            db.session.add(HPOTerm(hpo_id=term.id, term_name=term.name, definition=term.definition or None, synonyms=', '.join(term.synonym) if term.synonym else None))
            added += 1
    db.session.commit()
    print(f'Loaded {added} HPO terms')
PY
    ok "HPO terms loaded"
  else
    ok "HPO terms already present — skipping load"
  fi

  trap cleanup EXIT INT TERM

  start_local_llm

  info "Launching Gunicorn"
  gunicorn -c gunicorn.conf.py run:app &
  GUNICORN_PID=$!
  wait "$GUNICORN_PID"
else
  info "Starting in development mode"
  info "Run the frontend dev server separately with: (cd frontend && npm run dev)"
  exec python run.py
fi
