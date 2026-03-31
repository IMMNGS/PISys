#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RUN_LOCAL_LLM=1
for arg in "$@"; do
  case "$arg" in
    --no-ai|-n)
      RUN_LOCAL_LLM=0
      ;;
    -h|--help)
      echo "Usage: $0 [--no-ai]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--no-ai]"
      exit 2
      ;;
  esac
done

if [ ! -d "$ROOT_DIR/data/local_ai" ]; then
  mkdir -p "$ROOT_DIR/data/local_ai/bin" "$ROOT_DIR/data/local_ai/models"
fi

if [ ! -d "$ROOT_DIR/.venv" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$ROOT_DIR/.venv"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$ROOT_DIR/.venv"
  elif command -v py >/dev/null 2>&1; then
    py -3 -m venv "$ROOT_DIR/.venv"
  else
    echo "Python is required but was not found on PATH."
    exit 1
  fi
fi

if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  source "$ROOT_DIR/.venv/bin/activate"
elif [ -f "$ROOT_DIR/.venv/Scripts/activate" ]; then
  source "$ROOT_DIR/.venv/Scripts/activate"
else
  echo "Could not find a virtual environment activate script in .venv/bin or .venv/Scripts."
  exit 1
fi

python -m pip install -r requirements.txt >/dev/null

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  (cd frontend && npm install)
fi

export LOCAL_LLM_PORT="${LOCAL_LLM_PORT:-8080}"
export LOCAL_LLM_BASE_URL="${LOCAL_LLM_BASE_URL:-http://127.0.0.1:${LOCAL_LLM_PORT}/v1/chat/completions}"
export LOCAL_LLM_MODEL_FILE="${LOCAL_LLM_MODEL_FILE:-$ROOT_DIR/data/local_ai/models/Qwen3.5-4B-Q4_K_M.gguf}"
export LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-qwen3.5-4b-instruct}"

python run.py &
BACKEND_PID=$!

if [ "$RUN_LOCAL_LLM" = "1" ]; then
  python scripts/start_local_llm.py --mode auto &
  LLM_PID=$!
fi

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
  if [ -n "${LLM_PID:-}" ]; then
    kill "$LLM_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

(cd frontend && npm run dev)