#!/usr/bin/env python3
"""Convert raw research downloads into a chunked local RAG corpus.

This script scans data/rag/raw/**/manifest.jsonl files, loads the downloaded
research text, splits it into retrieval-friendly chunks, and writes JSONL
corpus files under data/rag/corpus/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = PROJECT_ROOT / "data" / "rag" / "raw"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "rag" / "corpus"


def safe_relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    chunk_index: int
    chunk_count: int
    text: str
    title: str | None = None
    source: str | None = None
    query: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    journal_title: str | None = None
    pub_year: str | None = None
    authors: str | None = None
    citation_count: int | None = None
    is_open_access: bool | None = None
    source_url: str | None = None
    text_sha256: str | None = None
    created_at: str | None = None


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    step = max(1, max_chars - overlap)
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def load_manifest_records(raw_root: Path) -> list[dict]:
    records: list[dict] = []
    seen_doc_ids: set[str] = set()
    for manifest_path in raw_root.rglob("manifest.jsonl"):
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc_id = str(record.get("doc_id") or "").strip()
            if doc_id and doc_id in seen_doc_ids:
                continue
            if doc_id:
                seen_doc_ids.add(doc_id)
            record["_manifest_path"] = str(manifest_path)
            records.append(record)
    return records


def load_document_text(record: dict) -> str:
    text_path = record.get("text_path")
    if text_path:
        path = PROJECT_ROOT / text_path
        if path.exists():
            return path.read_text(encoding="utf-8")

    raw_json_path = record.get("raw_json_path")
    if raw_json_path:
        path = PROJECT_ROOT / raw_json_path
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return normalize_text(
                str(data.get("title") or ""),
                str(data.get("abstract") or ""),
                str(data.get("full_text") or ""),
            )

    return normalize_text(
        str(record.get("title") or ""),
        str(record.get("abstract") or ""),
        str(record.get("full_text") or ""),
    )


def build_chunk_records(record: dict, max_chars: int, overlap: int) -> list[ChunkRecord]:
    text = load_document_text(record)
    if not text:
        return []

    chunks = split_text(text, max_chars=max_chars, overlap=overlap)
    total = len(chunks)
    created_at = datetime.now(timezone.utc).isoformat()
    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    results: list[ChunkRecord] = []
    for index, chunk in enumerate(chunks):
        chunk_hash = hashlib.sha256(f"{record.get('doc_id')}::{index}::{chunk}".encode("utf-8")).hexdigest()[:16]
        results.append(
            ChunkRecord(
                chunk_id=f"{record.get('doc_id')}:{index:03d}:{chunk_hash}",
                doc_id=str(record.get("doc_id") or "").strip(),
                chunk_index=index,
                chunk_count=total,
                text=chunk,
                title=record.get("title"),
                source=record.get("source"),
                query=record.get("query"),
                pmid=record.get("pmid"),
                pmcid=record.get("pmcid"),
                doi=record.get("doi"),
                journal_title=record.get("journal_title"),
                pub_year=record.get("pub_year"),
                authors=record.get("authors"),
                citation_count=record.get("citation_count"),
                is_open_access=record.get("is_open_access"),
                source_url=record.get("source_url"),
                text_sha256=text_sha256,
                created_at=created_at,
            )
        )
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a chunked RAG corpus from raw research manifests.")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT, help="Root directory containing raw manifests.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for corpus JSONL files.")
    parser.add_argument("--max-chars", type=int, default=1600, help="Maximum characters per chunk.")
    parser.add_argument("--overlap", type=int, default=200, help="Character overlap between chunks.")
    parser.add_argument("--print-summary", action="store_true", help="Print a summary after the corpus is written.")
    return parser


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = build_arg_parser().parse_args()
    records = load_manifest_records(args.raw_root)
    if not records:
        print(f"No manifests found under {args.raw_root}")
        return 0

    chunk_records: list[dict] = []
    doc_count = 0
    for record in records:
        chunks = build_chunk_records(record, max_chars=args.max_chars, overlap=args.overlap)
        if not chunks:
            continue
        doc_count += 1
        for chunk in chunks:
            chunk_records.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "chunk_count": chunk.chunk_count,
                "text": chunk.text,
                "title": chunk.title,
                "source": chunk.source,
                "query": chunk.query,
                "pmid": chunk.pmid,
                "pmcid": chunk.pmcid,
                "doi": chunk.doi,
                "journal_title": chunk.journal_title,
                "pub_year": chunk.pub_year,
                "authors": chunk.authors,
                "citation_count": chunk.citation_count,
                "is_open_access": chunk.is_open_access,
                "source_url": chunk.source_url,
                "text_sha256": chunk.text_sha256,
                "created_at": chunk.created_at,
            })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = args.out_dir / "corpus.jsonl"
    manifest_path = args.out_dir / "manifest.json"
    write_jsonl(corpus_path, chunk_records)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_root": safe_relative_path(args.raw_root),
        "documents": doc_count,
        "chunks": len(chunk_records),
        "corpus_path": safe_relative_path(corpus_path),
    }
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(chunk_records)} chunks from {doc_count} documents to {corpus_path}")
    if args.print_summary:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
