#!/usr/bin/env python3
"""Download public research text for a local-only RAG corpus.

This script uses Europe PMC's public REST API to collect article metadata,
abstracts, and optional open-access full text, then writes a local raw corpus
under data/rag/raw/.

Examples:
  python scripts/rag/fetch_public_research.py
  python scripts/rag/fetch_public_research.py --query "primary immunodeficiency" --max-records 25
  python scripts/rag/fetch_public_research.py --queries-file data/rag/queries.txt --include-full-text
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUERIES_FILE = PROJECT_ROOT / "data" / "rag" / "queries.txt"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "rag" / "raw" / "europe_pmc"
EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_FULL_TEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"

DEFAULT_QUERIES = [
    "inborn errors of immunity",
    "primary immunodeficiency",
    "Human Phenotype Ontology",
    "ACMG variant interpretation",
    "ClinVar pathogenic variant",
    "genotype phenotype correlation",
    "gene-disease association",
    "exome sequencing diagnostic yield",
    "rare disease diagnosis",
    "variant curation clinical genetics",
]


@dataclass
class ResearchDocument:
    doc_id: str
    source: str
    query: str
    title: str | None = None
    abstract: str | None = None
    full_text: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    journal_title: str | None = None
    pub_year: str | None = None
    authors: str | None = None
    is_open_access: bool | None = None
    citation_count: int | None = None
    source_url: str | None = None
    raw_json_path: str | None = None
    text_path: str | None = None
    fetched_at: str | None = None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "query"


def read_queries(queries_file: Path | None, inline_queries: list[str]) -> list[str]:
    queries: list[str] = []
    if queries_file and queries_file.exists():
        for line in queries_file.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            queries.append(text)
    queries.extend(q.strip() for q in inline_queries if q.strip())
    if not queries:
        queries = DEFAULT_QUERIES[:]
    # preserve order but deduplicate
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped


def http_get_json(url: str, timeout: int = 30) -> dict:
    request = Request(url, headers={"User-Agent": "HA-local-RAG/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def http_get_text(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": "HA-local-RAG/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("._-") or "document"


def extract_text_from_fulltext_xml(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""

    sections: list[str] = []
    for paragraph in root.findall(".//p"):
        text = " ".join((paragraph.itertext()))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            sections.append(text)
    return "\n\n".join(sections).strip()


def normalize_text(*parts: str | None) -> str:
    joined = "\n\n".join(part.strip() for part in parts if part and part.strip())
    joined = re.sub(r"[ \t]+", " ", joined)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def load_existing_ids(manifest_path: Path) -> set[str]:
    ids: set[str] = set()
    if not manifest_path.exists():
        return ids
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        doc_id = str(record.get("doc_id") or "").strip()
        if doc_id:
            ids.add(doc_id)
    return ids


def fetch_europe_pmc(query: str, max_records: int, page_size: int, sleep_seconds: float, include_full_text: bool) -> list[ResearchDocument]:
    collected: list[ResearchDocument] = []
    cursor_mark = "*"
    while len(collected) < max_records:
        size = min(page_size, max_records - len(collected))
        url = (
            f"{EUROPE_PMC_SEARCH_URL}?query={quote_plus(query)}"
            f"&format=json&resultType=core&pageSize={size}&cursorMark={quote_plus(cursor_mark)}"
        )
        data = http_get_json(url)
        page_results = data.get("resultList", {}).get("result", [])
        if not page_results:
            break

        for item in page_results:
            source = str(item.get("source") or "EuropePMC")
            pmid = str(item.get("pmid") or "").strip() or None
            pmcid = str(item.get("pmcid") or "").strip() or None
            doi = str(item.get("doi") or "").strip() or None
            doc_id = pmid or pmcid or str(item.get("id") or "").strip()
            if not doc_id:
                continue

            title = str(item.get("title") or "").strip() or None
            abstract = str(item.get("abstractText") or "").strip() or None
            authors = str(item.get("authorString") or "").strip() or None
            journal_title = str(item.get("journalTitle") or "").strip() or None
            pub_year = str(item.get("pubYear") or "").strip() or None
            citation_count = item.get("citedByCount")
            try:
                citation_count = int(citation_count) if citation_count is not None else None
            except (TypeError, ValueError):
                citation_count = None
            is_open_access = str(item.get("isOpenAccess") or "").upper() == "Y"

            full_text = None
            if include_full_text and pmcid and is_open_access:
                try:
                    full_url = EUROPE_PMC_FULL_TEXT_URL.format(pmcid=pmcid)
                    xml_text = http_get_text(full_url)
                    full_text = extract_text_from_fulltext_xml(xml_text) or None
                except (HTTPError, URLError, TimeoutError, ValueError):
                    full_text = None

            combined_text = normalize_text(title, abstract, full_text)
            if not combined_text:
                continue

            fetched_at = datetime.now(timezone.utc).isoformat()
            source_url = f"https://europepmc.org/article/{source}/{doc_id}"
            collected.append(
                ResearchDocument(
                    doc_id=doc_id,
                    source=source,
                    query=query,
                    title=title,
                    abstract=abstract,
                    full_text=full_text,
                    pmid=pmid,
                    pmcid=pmcid,
                    doi=doi,
                    journal_title=journal_title,
                    pub_year=pub_year,
                    authors=authors,
                    is_open_access=is_open_access,
                    citation_count=citation_count,
                    source_url=source_url,
                    fetched_at=fetched_at,
                )
            )

        next_cursor = data.get("nextCursorMark") or cursor_mark
        if next_cursor == cursor_mark:
            break
        cursor_mark = next_cursor
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return collected


def write_documents(documents: Iterable[ResearchDocument], out_dir: Path, query: str, include_existing: bool = True) -> tuple[int, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    query_slug = slugify(query)
    query_dir = out_dir / query_slug
    query_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = query_dir / "manifest.jsonl"
    existing_ids = load_existing_ids(manifest_path) if include_existing else set()

    written = 0
    with manifest_path.open("a", encoding="utf-8") as manifest_file:
        for doc in documents:
            if doc.doc_id in existing_ids:
                continue

            source_key = safe_filename((doc.source or "EuropePMC").lower())
            doc_key = safe_filename(doc.doc_id)
            raw_json_path = query_dir / f"{source_key}_{doc_key}.json"
            text_path = query_dir / f"{source_key}_{doc_key}.txt"

            text_content = normalize_text(doc.title, doc.abstract, doc.full_text)
            text_path.write_text(text_content + "\n", encoding="utf-8")

            payload = asdict(doc)
            payload["raw_json_path"] = str(raw_json_path.relative_to(PROJECT_ROOT))
            payload["text_path"] = str(text_path.relative_to(PROJECT_ROOT))
            payload["query_slug"] = query_slug
            payload["text_sha256"] = hashlib.sha256(text_content.encode("utf-8")).hexdigest()

            raw_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            written += 1

    return written, manifest_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download public research into a local RAG corpus.")
    parser.add_argument("--query", action="append", default=[], help="Add a search query (may be repeated).")
    parser.add_argument("--queries-file", type=Path, default=DEFAULT_QUERIES_FILE, help="Path to a newline-delimited query file.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for raw research downloads.")
    parser.add_argument("--max-records", type=int, default=25, help="Maximum records to fetch per query.")
    parser.add_argument("--page-size", type=int, default=25, help="Records per Europe PMC request.")
    parser.add_argument("--sleep-seconds", type=float, default=0.5, help="Sleep between paginated requests.")
    parser.add_argument("--include-full-text", action="store_true", help="Try to fetch open-access full text XML for PMCID articles.")
    parser.add_argument("--print-manifest", action="store_true", help="Print created manifest paths.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    queries = read_queries(args.queries_file, args.query)
    total_written = 0
    manifests: list[Path] = []

    for query in queries:
        documents = fetch_europe_pmc(
            query=query,
            max_records=args.max_records,
            page_size=args.page_size,
            sleep_seconds=args.sleep_seconds,
            include_full_text=args.include_full_text,
        )
        written, manifest_path = write_documents(documents, args.out_dir, query)
        total_written += written
        manifests.append(manifest_path)
        print(f"[{query}] wrote {written} documents to {manifest_path}")

    print(f"Done. Total new documents written: {total_written}")
    if args.print_manifest:
        for manifest in manifests:
            print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
