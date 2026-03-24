"""Local LLM chat endpoint.

This endpoint forwards chat requests to a loopback OpenAI-compatible server
so the model stays on the user's machine.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, request

local_llm_bp = Blueprint("local_llm", __name__)


def _friendly_model_label(filename: str) -> str:
    label = Path(filename).stem.replace("_", " ").replace("-", " ")
    return " ".join(part for part in label.split() if part) or filename


def _is_local_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".localhost")


def _validate_local_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("LOCAL_LLM_BASE_URL must use http or https")
    if not _is_local_host(parsed.hostname):
        raise ValueError("LOCAL_LLM_BASE_URL must point to a local/loopback host")
    return parsed.geturl()


def _clean_messages(messages: object) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    cleaned: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()
        if role not in {"system", "user", "assistant"} or not content:
            continue
        cleaned.append({"role": role, "content": content})
    return cleaned


@local_llm_bp.route("/local-llm/models", methods=["GET"])
def list_local_llm_models():
    """Return local GGUF files found in the configured model directory."""
    model_dir = Path(current_app.config["LOCAL_AI_MODELS_DIR"])
    default_file = Path(current_app.config["LOCAL_LLM_MODEL_FILE"]).name

    models: list[dict[str, str | bool]] = []
    if model_dir.exists():
      for path in sorted(model_dir.glob("*.gguf")) + sorted(model_dir.glob("*.GGUF")):
          models.append({
              "filename": path.name,
              "label": _friendly_model_label(path.name),
              "path": str(path),
              "is_default": path.name == default_file,
          })

    if not models:
        models.append({
            "filename": default_file,
            "label": _friendly_model_label(default_file),
            "path": str(model_dir / default_file),
            "is_default": True,
        })

    selected = next((m["filename"] for m in models if m["is_default"]), models[0]["filename"])
    return jsonify({"models": models, "selected": selected})


@local_llm_bp.route("/local-llm/chat", methods=["POST"])
def chat_local_llm():
    """Forward a chat request to the configured local LLM server."""
    data = request.get_json(silent=True) or {}

    try:
        messages = _clean_messages(data.get("messages"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not messages:
        return jsonify({"error": "messages are required"}), 400

    model = str(data.get("model") or current_app.config["LOCAL_LLM_MODEL"]).strip()
    if not model:
        return jsonify({"error": "model is required"}), 400

    try:
        base_url = _validate_local_url(current_app.config["LOCAL_LLM_BASE_URL"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(data.get("temperature", 0.2)),
        "top_p": float(data.get("top_p", 0.95)),
        "max_tokens": int(data.get("max_tokens", 512)),
        "stream": False,
    }

    req = Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=current_app.config["LOCAL_LLM_TIMEOUT"]) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return jsonify({
            "error": "Local LLM server returned an error",
            "details": detail or exc.reason,
        }), 502
    except URLError as exc:
        return jsonify({
            "error": "Could not reach the local LLM server",
            "details": str(exc.reason),
        }), 503

    try:
        upstream = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "Local LLM server returned invalid JSON"}), 502

    reply = ""
    if isinstance(upstream, dict):
        choices = upstream.get("choices") or []
        if choices and isinstance(choices, list):
            first = choices[0] or {}
            message = first.get("message") or {}
            reply = str(message.get("content") or "").strip()
        if not reply:
            reply = str(upstream.get("response") or upstream.get("text") or "").strip()

    if not reply:
        return jsonify({"error": "Local LLM server returned no reply text"}), 502

    return jsonify({"model": model, "reply": reply, "raw": upstream})