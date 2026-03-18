"""Local analytics and explanation endpoints.

All logic in this module is local-only and does not call external services.
"""

from collections import Counter
import re

from flask import Blueprint, jsonify, request

from backend.models import HPOTerm, Patient, Singleton, Trio, VcfFile

insights_bp = Blueprint("insights", __name__)

# TODO(local-llm): Add optional on-device model adapter (e.g. Ollama/llama.cpp)
# and keep this endpoint local-only by validating model host/path is loopback/local.
# TODO(caching): Add response cache table keyed by (kind, query) to reduce repeat work.
# TODO(guardrails): Add PHI-safe request/response logging controls and retention settings.


def _extract_chromosome(chr_pos: str | None) -> str | None:
    text = (chr_pos or "").strip()
    if not text:
        return None
    left = text.split(":", 1)[0].strip()
    if not left:
        return None
    if left.lower().startswith("chr"):
        left = left[3:]
    return left.upper()


def _split_genes(gene_names: str | None) -> list[str]:
    text = (gene_names or "").strip()
    if not text:
        return []
    parts = re.split(r"[;,/|]+", text)
    return [p.strip().upper() for p in parts if p.strip()]


def _tokenize_keywords(*values: str | None) -> list[str]:
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "variant",
        "variants", "patient", "patients", "gene", "genes", "unknown",
        "likely", "pathogenic", "benign", "vus", "inherited", "review",
        "comment", "on", "of", "to", "in", "is", "are", "a", "an",
    }
    merged = " ".join((v or "") for v in values)
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", merged)
    return [t.lower() for t in raw if t.lower() not in stop_words]


@insights_bp.route("/insights/summary", methods=["GET"])
def get_summary():
    # TODO(analytics-filters): Support query params for date range and test type,
    # then compute aggregates on the filtered subset.
    patients = Patient.query.count()
    singletons = Singleton.query.all()
    trios = Trio.query.all()
    vcf_files = VcfFile.query.count()

    combined = [*singletons, *trios]

    chromosome_counter = Counter()
    variant_counter = Counter()
    gene_counter = Counter()
    keyword_counter = Counter()

    for row in combined:
        chrom = _extract_chromosome(getattr(row, "chr_pos", None))
        if chrom:
            chromosome_counter[chrom] += 1

        chr_pos = (getattr(row, "chr_pos", None) or "").strip()
        ref_alt = (getattr(row, "ref_alt", None) or "").strip()
        if chr_pos or ref_alt:
            variant_counter[f"{chr_pos} {ref_alt}".strip()] += 1

        for gene in _split_genes(getattr(row, "gene_names", None)):
            gene_counter[gene] += 1

        for keyword in _tokenize_keywords(
            getattr(row, "title", None),
            getattr(row, "classification", None),
            getattr(row, "second_review_comment", None),
        ):
            keyword_counter[keyword] += 1

    payload = {
        "counts": {
            "patients": patients,
            "singleton_variants": len(singletons),
            "trio_variants": len(trios),
            "total_variants": len(combined),
            "vcf_files": vcf_files,
        },
        "chromosome_distribution": [
            {"chromosome": k, "count": v}
            for k, v in chromosome_counter.most_common(24)
        ],
        "top_variants": [
            {"variant": k, "count": v}
            for k, v in variant_counter.most_common(30)
        ],
        "top_genes": [
            {"gene": k, "count": v}
            for k, v in gene_counter.most_common(30)
        ],
        "top_keywords": [
            {"keyword": k, "count": v}
            for k, v in keyword_counter.most_common(40)
        ],
    }
    return jsonify(payload)


@insights_bp.route("/insights/explain", methods=["POST"])
def explain_entity():
    """Local, small-footprint explainer for HPO terms and variants.

    Request body:
      {"kind": "hpo" | "variant" | "text", "query": "..."}
    """
    data = request.get_json() or {}
    kind = str(data.get("kind", "text")).strip().lower()
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({"error": "query is required"}), 400

    if kind == "hpo":
        lower = query.lower()
        term = HPOTerm.query.filter(HPOTerm.hpo_id.ilike(query)).first()
        if term is None:
            term = HPOTerm.query.filter(HPOTerm.term_name.ilike(f"%{lower}%")).first()

        if term is None:
            return jsonify({
                "kind": "hpo",
                "query": query,
                "explanation": (
                    "No exact HPO record matched locally. Try an HPO ID like 'HP:0001250' "
                    "or a more specific term name."
                ),
                "source": "local-rule-based",
            })

        synonyms = term.synonyms or "No synonyms available in local DB."
        definition = term.definition or "No definition stored for this term in local DB."
        return jsonify({
            "kind": "hpo",
            "query": query,
            "matched": {"hpo_id": term.hpo_id, "term_name": term.term_name},
            "explanation": f"{term.term_name} ({term.hpo_id}): {definition}",
            "details": {"synonyms": synonyms},
            "source": "local-hpo-database",
        })

    if kind == "variant":
        raw = query.replace("\t", " ").replace(",", " ")
        chrom_match = re.search(r"(?:chr)?([0-9]{1,2}|X|Y|MT|M)", raw, re.IGNORECASE)
        chrom = chrom_match.group(1).upper() if chrom_match else "unknown"
        gene_hint = re.search(r"\b([A-Z0-9]{2,12})\b", query)
        gene = gene_hint.group(1) if gene_hint else "unspecified gene"
        return jsonify({
            "kind": "variant",
            "query": query,
            "explanation": (
                f"Local interpretation helper: this variant appears to involve chromosome {chrom} "
                f"and gene hint '{gene}'. Review zygosity, inheritance pattern, and phenotype match "
                "before clinical conclusions."
            ),
            "source": "local-rule-based",
            "medical_disclaimer": "For research support only; not a diagnostic statement.",
        })

    return jsonify({
        "kind": "text",
        "query": query,
        "explanation": (
            "This is a local explainer stub. For fully local small-model inference, plug in a "
            "local model runtime (for example via an on-device service) and keep PHI on your host."
        ),
        "source": "local-rule-based",
    })


# TODO(tests): Add backend tests for /api/insights/summary and /api/insights/explain.
