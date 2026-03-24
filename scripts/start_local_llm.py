#!/usr/bin/env python3
"""Start a local LLM server for the app.

Behavior:
- If llama.cpp is installed under LOCAL_AI_DIR/bin, it will launch that server.
- Otherwise it starts a small mock OpenAI-compatible server so the UI can be
  tested immediately.

The app expects an OpenAI-compatible endpoint at /v1/chat/completions.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _guess_model_file(local_ai_models_dir: Path, model_name: str) -> Path:
    candidates = [
        local_ai_models_dir / model_name,
        local_ai_models_dir / f"{model_name}.gguf",
        local_ai_models_dir / f"{model_name}.GGUF",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    ggufs = sorted(local_ai_models_dir.glob("*.gguf")) + sorted(local_ai_models_dir.glob("*.GGUF"))
    if ggufs:
        return ggufs[0]
    return candidates[1]


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: N802
        print(f"[mock-llm] {self.address_string()} - {fmt % args}")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send_json({"ok": True, "mode": "mock"})
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._send_json({"error": "not found"}, 404)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {}

        messages = payload.get("messages") or []
        user_text = ""
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                user_text = str(message.get("content") or "").strip()
                if user_text:
                    break

        model = str(payload.get("model") or "mock-qwen3.5-9b-instruct")
        temperature = payload.get("temperature")
        reply = (
            "Mock local LLM response.\n\n"
            f"Model: {model}\n"
            f"Temperature: {temperature}\n"
            f"User prompt: {user_text or '(empty)'}\n\n"
            "This server is a local test stub. When you point the app at a real "
            "llama.cpp or compatible server, the same page will send the same "
            "request format to the actual model."
        )
        self._send_json({
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
        })


def _start_mock(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), MockHandler)
    print(f"[mock-llm] Listening on http://{host}:{port}")
    print("[mock-llm] POST /v1/chat/completions")
    print("[mock-llm] GET  /health")
    server.serve_forever()


def _start_llama_cpp(host: str, port: int, model_file: Path, model_name: str) -> int | None:
    repo_root = _repo_root()
    local_ai_dir = Path(_env("LOCAL_AI_DIR", str(repo_root / "data" / "local_ai")))
    bin_dir = Path(_env("LOCAL_AI_BIN_DIR", str(local_ai_dir / "bin")))
    candidates = [
        bin_dir / "llama-server",
        bin_dir / "server",
        bin_dir / "llama-cli",
        repo_root / "data" / "local_ai" / "src" / "llama.cpp" / "build" / "bin" / "llama-server",
        repo_root / "data" / "local_ai" / "src" / "llama.cpp" / "build" / "bin" / "server",
    ]
    binary = next((candidate for candidate in candidates if candidate.exists()), None)
    if binary is None:
        return None

    if not model_file.exists():
        print(f"[llama.cpp] Model file not found: {model_file}")
        return None

    cmd = [
        str(binary),
        "--host",
        host,
        "--port",
        str(port),
        "--reasoning",
        "off",
        "-m",
        str(model_file),
    ]

    # Keep the process output visible in the launching terminal.
    print("[llama.cpp] Launching:", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=_env("LOCAL_LLM_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(_env("LOCAL_LLM_PORT", "8080")))
    parser.add_argument("--mode", choices=["auto", "mock", "llama"], default="auto")
    args = parser.parse_args()

    repo_root = _repo_root()
    local_ai_dir = Path(_env("LOCAL_AI_DIR", str(repo_root / "data" / "local_ai")))
    local_ai_models_dir = Path(_env("LOCAL_AI_MODELS_DIR", str(local_ai_dir / "models")))
    local_ai_models_dir.mkdir(parents=True, exist_ok=True)

    model_name = _env("LOCAL_LLM_MODEL", "qwen3.5-4b-instruct")
    model_file_env = _env("LOCAL_LLM_MODEL_FILE", "")
    model_file = Path(model_file_env) if model_file_env else _guess_model_file(local_ai_models_dir, model_name)

    if args.mode in {"auto", "llama"}:
        launched = _start_llama_cpp(args.host, args.port, model_file, model_name)
        if launched is not None:
            return launched
        if args.mode == "llama":
            print("[llama.cpp] Could not start llama.cpp; check binary and model path.")
            return 1

    _start_mock(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())