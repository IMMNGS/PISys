"""Local LLM chat endpoint.

This endpoint forwards chat requests to a loopback OpenAI-compatible server
so the model stays on the user's machine. It also supports a local response
cache, PHI-safe logging defaults, and simple provider-aware model discovery.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from datetime import datetime, timedelta, timezone
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, request

from backend.models import LocalLlmCache, db

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


def _provider_name() -> str:
    return str(current_app.config.get("LOCAL_LLM_PROVIDER", "openai")).strip().lower()


def _base_url() -> str:
    return _validate_local_url(current_app.config["LOCAL_LLM_BASE_URL"])


def _cache_ttl_seconds() -> int:
    return max(0, int(current_app.config.get("LOCAL_LLM_CACHE_TTL_SECONDS", 0) or 0))


def _cache_key(payload: dict[str, object], provider: str, base_url: str) -> str:
    raw = json.dumps(
        {
            "provider": provider,
            "base_url": base_url,
            "model": payload.get("model"),
            "messages": payload.get("messages"),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_lookup(cache_key: str) -> dict[str, object] | None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return None

    now = current_app.config.get("_now_for_cache")
    if now is None:
        now = time.time()
    now_dt = __import__("datetime").datetime.fromtimestamp(now, tz=__import__("datetime").timezone.utc)

    expired = LocalLlmCache.query.filter(LocalLlmCache.expires_at <= now_dt).delete(synchronize_session=False)
    if expired:
        db.session.commit()

    row = LocalLlmCache.query.filter_by(cache_key=cache_key).filter(LocalLlmCache.expires_at > now_dt).first()
    if row is None:
        return None
    try:
        return json.loads(row.response_json)
    except json.JSONDecodeError:
        return None


def _cache_store(cache_key: str, provider: str, model: str, payload: dict[str, object], response: dict[str, object]) -> None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return

    now_dt = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    expires_at = now_dt + __import__("datetime").timedelta(seconds=ttl)

    existing = LocalLlmCache.query.filter_by(cache_key=cache_key).first()
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    response_json = json.dumps(response, ensure_ascii=False, sort_keys=True)
    if existing is None:
        existing = LocalLlmCache(
            cache_key=cache_key,
            provider=provider,
            model=model,
            payload_json=payload_json,
            response_json=response_json,
            created_at=now_dt,
            expires_at=expires_at,
        )
        db.session.add(existing)
    else:
        existing.provider = provider
        existing.model = model
        existing.payload_json = payload_json
        existing.response_json = response_json
        existing.created_at = now_dt
        existing.expires_at = expires_at

    db.session.query(LocalLlmCache).filter(LocalLlmCache.expires_at <= now_dt).delete(synchronize_session=False)
    db.session.commit()


def _redact_text(text: str) -> str:
    if not current_app.config.get("LOCAL_LLM_LOG_REDACT", True):
        return text
    patterns = [
        (r"\b[A-Z]{1,3}\d{2,6}\b", "[ID]"),
        (r"\b\d{2,4}-\d{2,4}-\d{2,4}\b", "[DATE]"),
        (r"\b[\w.-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
        (r"\b(?:\+?\d[\d\s-]{6,}\d)\b", "[PHONE]"),
    ]
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted


def _log_chat_event(*, cache_hit: bool, model: str, provider: str, messages: list[dict[str, str]], reply: str | None = None) -> None:
    parts = [
        "local LLM chat",
        f"provider={provider}",
        f"model={model}",
        f"messages={len(messages)}",
        f"cache={'hit' if cache_hit else 'miss'}",
    ]
    current_app.logger.info(" | ".join(parts))
    if current_app.config.get("LOCAL_LLM_LOG_PROMPTS", False):
        current_app.logger.info("local LLM prompt: %s", _redact_text(json.dumps(messages, ensure_ascii=False)))
    if reply is not None and current_app.config.get("LOCAL_LLM_LOG_RESPONSES", False):
        current_app.logger.info("local LLM reply: %s", _redact_text(reply))


def _fetch_json(url: str, timeout: int) -> object:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _scan_local_gguf_models() -> list[dict[str, str | bool]]:
    model_dir = Path(current_app.config["LOCAL_AI_MODELS_DIR"])
    default_file = Path(current_app.config["LOCAL_LLM_MODEL_FILE"]).name

    models: list[dict[str, str | bool]] = []
    if model_dir.exists():
        for path in sorted(model_dir.glob("*.gguf")) + sorted(model_dir.glob("*.GGUF")):
            models.append(
                {
                    "filename": path.name,
                    "label": _friendly_model_label(path.name),
                    "path": str(path),
                    "is_default": path.name == default_file,
                }
            )

    if not models:
        models.append(
            {
                "filename": default_file,
                "label": _friendly_model_label(default_file),
                "path": str(model_dir / default_file),
                "is_default": True,
            }
        )

    return models


def _models_endpoint(base_url: str, provider: str) -> str:
    parsed = urlparse(base_url)
    root = parsed._replace(query="", fragment="")
    path = root.path or ""
    if provider == "ollama":
        if path.endswith("/v1/chat/completions"):
            path = path[: -len("/v1/chat/completions")] + "/api/tags"
        elif path.endswith("/v1/chat/completions/"):
            path = path[: -len("/v1/chat/completions/")] + "/api/tags"
        else:
            path = "/api/tags"
        return root._replace(path=path).geturl()
    if path.endswith("/v1/chat/completions"):
        path = path[: -len("/chat/completions")] + "/models" if path.endswith("/chat/completions") else path
    elif path.endswith("/v1/chat/completions/"):
        path = path[: -len("/v1/chat/completions/")] + "/v1/models"
    elif not path.endswith("/v1/models"):
        path = path.rstrip("/") + "/v1/models"
    return root._replace(path=path).geturl()


def _extract_model_rows(upstream: object) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    if isinstance(upstream, dict):
        data = upstream.get("data")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("id") or item.get("name") or item.get("model") or "").strip()
                if not model_id:
                    continue
                rows.append(
                    {
                        "filename": model_id,
                        "label": _friendly_model_label(model_id),
                        "path": model_id,
                        "is_default": bool(item.get("is_default", False)),
                    }
                )
        models = upstream.get("models")
        if isinstance(models, list):
            for item in models:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or item.get("model") or item.get("id") or "").strip()
                if not name:
                    continue
                rows.append(
                    {
                        "filename": name,
                        "label": _friendly_model_label(name),
                        "path": name,
                        "is_default": bool(item.get("is_default", False)),
                    }
                )
        if not rows and isinstance(upstream.get("name"), str):
            name = str(upstream.get("name")).strip()
            rows.append({"filename": name, "label": _friendly_model_label(name), "path": name, "is_default": True})
    return rows


_RAG_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "onto",
    "about", "what", "when", "where", "which", "into", "onto", "patient",
    "patients", "case", "cases", "variant", "variants", "gene", "genes",
    "local", "model", "models", "tell", "show", "please", "give", "explain",
    "summarize", "summarise", "draft", "brief", "short", "help", "using",
    "based", "analysis", "clinical", "medical", "report", "reports",
}


def _rag_enabled() -> bool:
    return bool(current_app.config.get("RAG_ENABLED", True))


def _rag_corpus_path() -> Path:
    return Path(current_app.config.get("RAG_CORPUS_PATH", ""))


def _rag_signature(path: Path) -> tuple[str, int]:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (str(path), 0)
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    return (resolved, stat.st_mtime_ns)


@lru_cache(maxsize=4)
def _load_rag_corpus(signature: tuple[str, int]) -> tuple[dict[str, object], ...]:
    path = Path(signature[0])
    if not path.exists():
        return ()

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            rows.append(row)
    return tuple(rows)


def _tokenize_rag_query(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", (text or "").lower())
    return [token for token in tokens if token not in _RAG_STOP_WORDS]


def _rag_haystack(item: dict[str, object]) -> str:
    parts = [
        str(item.get("title") or ""),
        str(item.get("abstract") or ""),
        str(item.get("full_text") or ""),
        str(item.get("text") or ""),
        str(item.get("source") or ""),
        str(item.get("query") or ""),
        str(item.get("journal_title") or ""),
        str(item.get("authors") or ""),
    ]
    return " ".join(parts).lower()


def _score_rag_item(query_text: str, query_tokens: list[str], item: dict[str, object]) -> float:
    haystack = _rag_haystack(item)
    if not haystack:
        return 0.0

    score = 0.0
    unique_tokens = list(dict.fromkeys(query_tokens))
    for token in unique_tokens:
        if token in haystack:
            score += 2.0
            occurrences = haystack.count(token)
            if occurrences > 1:
                score += min(occurrences - 1, 4) * 0.2

    lowered_query = query_text.lower().strip()
    if lowered_query and lowered_query in haystack:
        score += 4.0

    title = str(item.get("title") or "").lower()
    if title:
        title_hits = sum(1 for token in unique_tokens if token in title)
        score += title_hits * 0.75

    source_query = str(item.get("query") or "").lower()
    if source_query and any(token in source_query for token in unique_tokens):
        score += 1.0

    return score


def _retrieve_rag_chunks(query_text: str, limit: int | None = None) -> list[dict[str, object]]:
    if not _rag_enabled():
        return []

    path = _rag_corpus_path()
    if not path.exists():
        return []

    corpus = _load_rag_corpus(_rag_signature(path))
    if not corpus:
        return []

    query_tokens = _tokenize_rag_query(query_text)
    if not query_tokens:
        return []

    ranked: list[tuple[float, dict[str, object]]] = []
    for item in corpus:
        score = _score_rag_item(query_text, query_tokens, item)
        if score > 0:
            ranked.append((score, item))

    if not ranked:
        return []

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    max_chunks = max(1, int(limit or current_app.config.get("RAG_MAX_CONTEXT_CHUNKS", 4)))
    return [item for _, item in ranked[:max_chunks]]


def _format_rag_citation_label(index: int, item: dict[str, object]) -> str:
    title = str(item.get("title") or "").strip()
    pmid = str(item.get("pmid") or "").strip()
    pmcid = str(item.get("pmcid") or "").strip()
    parts = [f"RAG {index}"]
    if title:
        parts.append(title)
    if pmid:
        parts.append(f"PMID:{pmid}")
    if pmcid:
        parts.append(f"PMCID:{pmcid}")
    return " — ".join(parts)


def _build_rag_context(query_text: str) -> tuple[str, list[dict[str, object]]]:
    chunks = _retrieve_rag_chunks(query_text)
    if not chunks:
        return "", []

    max_chars = max(1000, int(current_app.config.get("RAG_MAX_CONTEXT_CHARS", 6000)))
    lines = [
        "Local research context from the on-disk RAG corpus:",
        "Use these excerpts to answer when relevant. Prefer them over general knowledge.",
        "Cite sources inline as [RAG 1], [RAG 2], etc.",
        "",
    ]
    citations: list[dict[str, object]] = []
    used = 0
    for index, item in enumerate(chunks, start=1):
        text = str(item.get("text") or item.get("abstract") or item.get("title") or "").strip()
        if not text:
            continue
        label = _format_rag_citation_label(index, item)
        chunk_text = text[:1800].strip()
        block = f"[{label}]\n{chunk_text}"
        if used + len(block) > max_chars and lines[-1] != "":
            break
        lines.extend([block, ""])
        used += len(block)
        citations.append(
            {
                "type": "rag-chunk",
                "label": label,
                "fields": {
                    "doc_id": item.get("doc_id"),
                    "chunk_id": item.get("chunk_id"),
                    "source": item.get("source"),
                    "query": item.get("query"),
                    "title": item.get("title"),
                    "pmid": item.get("pmid"),
                    "pmcid": item.get("pmcid"),
                    "doi": item.get("doi"),
                    "source_url": item.get("source_url"),
                },
            }
        )

    return "\n".join(lines).strip(), citations


@local_llm_bp.route("/local-llm/models", methods=["GET"])
def list_local_llm_models():
    """Return local model options from the configured adapter or the GGUF directory."""
    provider = _provider_name()
    base_url = _base_url()
    timeout = int(current_app.config.get("LOCAL_LLM_TIMEOUT", 120))
    default_file = Path(current_app.config["LOCAL_LLM_MODEL_FILE"]).name

    model_rows: list[dict[str, str | bool]] = []
    if provider in {"ollama", "vllm", "openai"}:
        for candidate in [
            _models_endpoint(base_url, provider),
            _models_endpoint(base_url, "openai"),
        ]:
            try:
                upstream = _fetch_json(candidate, timeout)
                model_rows = _extract_model_rows(upstream)
                if model_rows:
                    break
            except Exception:
                continue

    if not model_rows:
        model_rows = _scan_local_gguf_models()

    if provider == "mock" and not model_rows:
        model_rows = [
            {
                "filename": default_file,
                "label": _friendly_model_label(default_file),
                "path": str(Path(current_app.config["LOCAL_AI_MODELS_DIR"]) / default_file),
                "is_default": True,
            }
        ]

    selected = next((m["filename"] for m in model_rows if m.get("is_default")), model_rows[0]["filename"])
    return jsonify({"provider": provider, "models": model_rows, "selected": selected})


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
        base_url = _base_url()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500

    provider = _provider_name()
    rag_query = "\n".join(
        message["content"] for message in messages if message.get("role") == "user"
    ).strip()
    rag_context, rag_citations = _build_rag_context(rag_query)
    augmented_messages = list(messages)
    if rag_context:
        if augmented_messages and augmented_messages[0].get("role") == "system":
            augmented_messages[0] = {
                **augmented_messages[0],
                "content": f"{augmented_messages[0]['content'].strip()}\n\n{rag_context}",
            }
        else:
            augmented_messages.insert(
                0,
                {
                    "role": "system",
                    "content": rag_context,
                },
            )

    payload: dict[str, object] = {
        "model": model,
        "messages": augmented_messages,
        "temperature": float(data.get("temperature", 0.2)),
        "top_p": float(data.get("top_p", 0.95)),
        "max_tokens": int(data.get("max_tokens", 512)),
        "stream": False,
    }

    cache_key = _cache_key(payload, provider, base_url)
    cached = _cache_lookup(cache_key)
    if isinstance(cached, dict):
        reply = str(cached.get("reply") or "").strip()
        if reply:
            _log_chat_event(cache_hit=True, model=model, provider=provider, messages=augmented_messages, reply=reply)
            response = {
                "model": model,
                "reply": reply,
                "cached": True,
                "citations": rag_citations,
                "retrieved_context": rag_context,
            }
            if "raw" in cached:
                response["raw"] = cached["raw"]
            return jsonify(response)

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
        return jsonify(
            {
                "error": "Local LLM server returned an error",
                "details": detail or exc.reason,
            }
        ), 502
    except URLError as exc:
        return jsonify(
            {
                "error": "Could not reach the local LLM server",
                "details": str(exc.reason),
            }
        ), 503

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

    _cache_store(cache_key, provider, model, payload, {"model": model, "reply": reply, "raw": upstream})
    _log_chat_event(cache_hit=False, model=model, provider=provider, messages=augmented_messages, reply=reply)
    return jsonify(
        {
            "model": model,
            "reply": reply,
            "raw": upstream,
            "cached": False,
            "citations": rag_citations,
            "retrieved_context": rag_context,
        }
    )