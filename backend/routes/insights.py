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


def _normalize_bucket_label(value: str | None, fallback: str = "Unknown") -> str:
    text = (value or "").strip()
    return text if text else fallback


def _normalize_sex(value: str | None) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "Unknown"
    if text in {"m", "male", "man", "boy"}:
        return "Male"
    if text in {"f", "female", "woman", "girl"}:
        return "Female"
    return text.title()


def _parse_age_years(age: str | int | float | None, age_unit: str | None) -> float | None:
    if age is None:
        return None
    try:
        numeric_age = float(str(age).strip())
    except ValueError:
        return None

    unit = (age_unit or "years").strip().lower()
    if unit in {"y", "yr", "yrs", "year", "years"}:
        return numeric_age
    if unit in {"m", "mo", "mos", "month", "months"}:
        return numeric_age / 12.0
    if unit in {"d", "day", "days"}:
        return numeric_age / 365.0
    if unit in {"w", "wk", "wks", "week", "weeks"}:
        return numeric_age / 52.0
    return numeric_age


def _bucket_age(years: float | None) -> str | None:
    if years is None:
        return None
    if years < 1:
        return "<1"
    if years < 18:
        return "1-17"
    if years < 30:
        return "18-29"
    if years < 45:
        return "30-44"
    if years < 60:
        return "45-59"
    if years < 75:
        return "60-74"
    return "75+"


def _bucket_file_size(size: int | None) -> str | None:
    if size is None or size < 0:
        return None
    if size < 1_000_000:
        return "<1 MB"
    if size < 5_000_000:
        return "1-5 MB"
    if size < 20_000_000:
        return "5-20 MB"
    if size < 100_000_000:
        return "20-100 MB"
    return "100+ MB"


@insights_bp.route("/insights/summary", methods=["GET"])
def get_summary():
    # TODO(analytics-filters): Support query params for date range and test type,
    # then compute aggregates on the filtered subset.
    patients = Patient.query.count()
    patient_rows = Patient.query.all()
    singletons = Singleton.query.all()
    trios = Trio.query.all()
    vcf_rows = VcfFile.query.all()

    combined = [*singletons, *trios]

    chromosome_counter = Counter()
    variant_counter = Counter()
    gene_counter = Counter()
    keyword_counter = Counter()
    sex_counter = Counter()
    age_counter = Counter()
    ethnicity_counter = Counter()
    test_counter = Counter()
    vcf_size_counter = Counter()

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

    for patient in patient_rows:
        sex_counter[_normalize_sex(getattr(patient, "sex", None))] += 1
        ethnicity_counter[_normalize_bucket_label(getattr(patient, "ethnicity", None))] += 1
        test_counter[_normalize_bucket_label(getattr(patient, "type_of_test", None))] += 1

        age_years = _parse_age_years(getattr(patient, "age", None), getattr(patient, "age_unit", None))
        age_bucket = _bucket_age(age_years)
        if age_bucket:
            age_counter[age_bucket] += 1

    for row in vcf_rows:
        size_bucket = _bucket_file_size(getattr(row, "file_size", None))
        if size_bucket:
            vcf_size_counter[size_bucket] += 1

    payload = {
        "counts": {
            "patients": patients,
            "singleton_variants": len(singletons),
            "trio_variants": len(trios),
            "total_variants": len(combined),
            "vcf_files": len(vcf_rows),
        },
        "demographic_distribution": {
            "sex": [
                {"label": k, "count": v}
                for k, v in sex_counter.most_common()
            ],
            "age": [
                {"label": k, "count": v}
                for k, v in age_counter.most_common()
            ],
            "ethnicity": [
                {"label": k, "count": v}
                for k, v in ethnicity_counter.most_common(12)
            ],
            "test_type": [
                {"label": k, "count": v}
                for k, v in test_counter.most_common(12)
            ],
        },
        "vcf_distribution": {
            "file_size": [
                {"label": k, "count": v}
                for k, v in vcf_size_counter.most_common()
            ],
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
    include_citations = bool(data.get("include_citations", True))

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
        citations = []
        if include_citations:
            citations.append({
                "type": "hpo-term",
                "label": f"{term.term_name} ({term.hpo_id})",
                "fields": {
                    "hpo_id": term.hpo_id,
                    "term_name": term.term_name,
                    "definition": definition,
                    "synonyms": synonyms,
                },
            })
        return jsonify({
            "kind": "hpo",
            "query": query,
            "matched": {"hpo_id": term.hpo_id, "term_name": term.term_name},
            "explanation": f"{term.term_name} ({term.hpo_id}): {definition}",
            "details": {"synonyms": synonyms},
            "source": "local-hpo-database",
            "citations": citations,
        })

    if kind == "variant":
        raw = query.replace("\t", " ").replace(",", " ")
        chrom_match = re.search(r"(?:chr)?([0-9]{1,2}|X|Y|MT|M)", raw, re.IGNORECASE)
        chrom = chrom_match.group(1).upper() if chrom_match else "unknown"
        gene_hint = re.search(r"\b([A-Z0-9]{2,12})\b", query)
        gene = gene_hint.group(1) if gene_hint else "unspecified gene"
        citations = []
        if include_citations:
            citations.append({
                "type": "variant-heuristic",
                "label": "Rule-based variant interpretation",
                "fields": {
                    "chromosome": chrom,
                    "gene_hint": gene,
                    "query": query,
                },
            })
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
            "citations": citations,
        })

    return jsonify({
        "kind": "text",
        "query": query,
        "explanation": (
            "This is a local explainer stub. For fully local small-model inference, plug in a "
            "local model runtime (for example via an on-device service) and keep PHI on your host."
        ),
        "source": "local-rule-based",
        "citations": [] if include_citations else None,
    })


# TODO(tests): Add backend tests for /api/insights/summary and /api/insights/explain.
