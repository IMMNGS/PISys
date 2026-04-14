#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸ $*${NC}"; }
ok()    { echo -e "${GREEN}✓ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

escape_sql_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

escape_sql_identifier() {
  printf "%s" "$1" | sed 's/"/""/g'
}

read_required_secret() {
  local prompt="$1"
  local value=""
  while true; do
    read -r -s -p "$prompt: " value
    echo
    if [[ -n "$value" ]]; then
      printf "%s" "$value"
      return
    fi
    warn "A non-empty password is required for setup"
  done
}

psql_with_password() {
  local password="$1"
  shift
  PGPASSWORD="$password" psql "$@"
}

psql_can_login() {
  local user="$1"
  local password="$2"

  psql_with_password "$password" \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$user" \
    -d postgres \
    -tAc "SELECT 1;" >/dev/null 2>&1
}

ensure_postgres_role_for_setup() {
  case "${POSTGRES_HOST}" in
    localhost|127.0.0.1|::1) ;;
    *)
      warn "Skipping PostgreSQL role bootstrap for non-local host ${POSTGRES_HOST}"
      return
      ;;
  esac

  if [[ -z "${POSTGRES_PASSWORD}" ]]; then
    if [[ -t 0 ]]; then
      POSTGRES_PASSWORD="$(read_required_secret "Enter NEW PostgreSQL password for user '${POSTGRES_USER}'")"
      export POSTGRES_PASSWORD
    else
      fail "POSTGRES_PASSWORD is empty; set it in .env for non-interactive setup"
    fi
  fi

  if psql_can_login "$POSTGRES_USER" "$POSTGRES_PASSWORD"; then
    ok "PostgreSQL credentials for '${POSTGRES_USER}' are valid"
    return
  fi

  warn "Could not authenticate as '${POSTGRES_USER}'. Bootstrapping role/password via admin account"

  local admin_user="${POSTGRES_ADMIN_USER:-postgres}"
  local admin_password="${POSTGRES_ADMIN_PASSWORD:-}"
  local admin_ready=false

  if [[ -n "$admin_password" ]] && psql_can_login "$admin_user" "$admin_password"; then
    admin_ready=true
  fi

  if [[ "$admin_ready" == false && -t 0 ]]; then
    local attempt
    for attempt in 1 2 3; do
      admin_password="$(read_required_secret "Enter CURRENT PostgreSQL password for admin user '${admin_user}'")"
      if psql_can_login "$admin_user" "$admin_password"; then
        admin_ready=true
        break
      fi
      warn "Admin authentication failed (attempt ${attempt}/3)"
    done
  fi

  if [[ "$admin_ready" == false ]]; then
    fail "Unable to authenticate as PostgreSQL admin '${admin_user}'. Set POSTGRES_ADMIN_USER/POSTGRES_ADMIN_PASSWORD and rerun setup."
  fi

  local escaped_user
  local escaped_password
  escaped_user="$(escape_sql_identifier "$POSTGRES_USER")"
  escaped_password="$(escape_sql_literal "$POSTGRES_PASSWORD")"

  local bootstrap_sql
  bootstrap_sql=$(cat <<SQL
DO
\$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
    EXECUTE 'CREATE ROLE "${escaped_user}" LOGIN PASSWORD ''${escaped_password}''';
  ELSE
    EXECUTE 'ALTER ROLE "${escaped_user}" WITH LOGIN PASSWORD ''${escaped_password}''';
  END IF;
END
\$\$;
SQL
)

  psql_with_password "$admin_password" \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$admin_user" \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "$bootstrap_sql" >/dev/null

  if ! psql_can_login "$POSTGRES_USER" "$POSTGRES_PASSWORD"; then
    fail "PostgreSQL role bootstrap ran, but login still failed for '${POSTGRES_USER}'"
  fi

  ok "PostgreSQL role '${POSTGRES_USER}' is ready for setup"
}

ensure_postgres_installed() {
  if command -v psql >/dev/null 2>&1; then
    ok "PostgreSQL client detected"
    return
  fi

  info "PostgreSQL not found; attempting automatic installation"

  if command -v brew >/dev/null 2>&1; then
    brew install postgresql@18 || brew install postgresql
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-client
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y postgresql18-server postgresql18 || sudo dnf install -y postgresql-server postgresql
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y postgresql18-server postgresql18 || sudo yum install -y postgresql-server postgresql
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm postgresql
  else
    fail "No supported package manager found to install PostgreSQL automatically"
  fi

  if ! command -v psql >/dev/null 2>&1; then
    fail "PostgreSQL installation appears incomplete (psql not found)"
  fi

  ok "PostgreSQL installation complete"
}

ensure_postgres_service_running() {
  case "${POSTGRES_HOST}" in
    localhost|127.0.0.1|::1) ;;
    *) return ;;
  esac

  if command -v brew >/dev/null 2>&1; then
    brew services start postgresql@18 >/dev/null 2>&1 || brew services start postgresql >/dev/null 2>&1 || true
  elif command -v systemctl >/dev/null 2>&1; then
    sudo systemctl start postgresql-18 >/dev/null 2>&1 || sudo systemctl start postgresql >/dev/null 2>&1 || sudo systemctl start postgresql-17 >/dev/null 2>&1 || true
  fi
}

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODE="production"
for arg in "$@"; do
  case "$arg" in
    setup|development|production)
      MODE="$arg"
      ;;
    -h|--help)
      echo "Usage: $0 [setup|development|production]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [setup|development|production]"
      exit 2
      ;;
  esac
done

POSTGRES_USER="${POSTGRES_USER:-${MYSQL_USER:-pisysdb}}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${MYSQL_PASSWORD:-}}"
POSTGRES_HOST="${POSTGRES_HOST:-${MYSQL_HOST:-localhost}}"
POSTGRES_PORT="${POSTGRES_PORT:-${MYSQL_PORT:-5432}}"
POSTGRES_DB="${POSTGRES_DB:-${MYSQL_DB:-pisys_db}}"

export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT POSTGRES_DB

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  fail "Python 3 is required but not found"
fi

if [[ "$MODE" == "setup" || ! -d "$PROJECT_DIR/.venv" || ! -d "$PROJECT_DIR/data/vcf" ]]; then
  info "Running setup"

  ensure_postgres_installed
  ensure_postgres_service_running
  ensure_postgres_role_for_setup

  if ! command -v node >/dev/null 2>&1; then
    fail "Node.js is required but not found"
  fi

  if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
    info "Creating virtual environment"
    "$PYTHON" -m venv "$PROJECT_DIR/.venv"
  fi

  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"

  info "Installing Python dependencies"
  pip install -r requirements.txt

  info "Creating data directories"
  mkdir -p "$PROJECT_DIR/data/vcf"
  mkdir -p "$PROJECT_DIR/data/variant_uploads"

  if [[ ! -f "$PROJECT_DIR/data/disease_terms.csv" ]]; then
    cat > "$PROJECT_DIR/data/disease_terms.csv" <<'CSV'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
CSV
  fi

  info "Ensuring PostgreSQL database exists"
  "$PYTHON" - <<'PY' || true
from backend.app import _ensure_databases
from backend.config import DevelopmentConfig

_ensure_databases(DevelopmentConfig)
PY

  info "Installing frontend dependencies and building"
  (cd frontend && npm install && npm run build)

  ok "Setup finished"
fi

if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"
fi

if [[ "$MODE" == "production" ]]; then
  info "Starting in production mode"
  export FLASK_ENV=production

  if [[ -z "${SECRET_KEY:-}" ]]; then
    SECRET_KEY=$("$PYTHON" -c "import secrets; print(secrets.token_hex(32))")
    export SECRET_KEY
    warn "SECRET_KEY not set. Generated one for this session."
  fi

  info "Building frontend"
  (cd frontend && npm ci && npm run build)

  info "Ensuring Python dependencies"
  pip install -r requirements.txt

  info "Launching Gunicorn"
  exec gunicorn -c gunicorn.conf.py run:app
else
  info "Starting in development mode"
  info "Run frontend separately: (cd frontend && npm run dev)"
  exec python run.py
fi
