#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/data/local_ai" ]; then
  mkdir -p "$ROOT_DIR/data/local_ai/bin" "$ROOT_DIR/data/local_ai/models"
fi

if [ ! -d "$ROOT_DIR/.venv" ]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi

source "$ROOT_DIR/.venv/bin/activate"

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

python scripts/start_local_llm.py --mode auto &
LLM_PID=$!

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
  kill "$LLM_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

(cd frontend && npm run dev)