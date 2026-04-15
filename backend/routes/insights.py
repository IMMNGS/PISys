"""Local analytics and explanation endpoints.

All logic in this module is local-only and does not call external services.
"""

from collections import Counter, defaultdict
from datetime import date
import gzip
import os
import re

from flask import Blueprint, current_app, jsonify, request

from backend.models import HPOTerm, Patient, Singleton, Trio, VcfFile

insights_bp = Blueprint("insights", __name__)

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


def _normalize_reportable_variant(value: str | None) -> str:
    text = (value or "").strip().upper()
    if not text:
        return "Unknown"
    if text in {"C", "I", "A", "N"}:
        return text
    return text[0] if text[0] in {"C", "I", "A", "N"} else "Unknown"


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


def _classify_vcf_variant_type(ref: str | None, alt: str | None) -> str:
    ref_text = (ref or "").strip()
    alt_text = (alt or "").strip()
    if not ref_text or not alt_text:
        return "Unknown"
    if alt_text.startswith("<") and alt_text.endswith(">"):
        return "Symbolic"
    if len(ref_text) == 1 and len(alt_text) == 1:
        return "SNV"
    if len(ref_text) == len(alt_text):
        return "MNV"
    if len(ref_text) < len(alt_text):
        return "Insertion"
    if len(ref_text) > len(alt_text):
        return "Deletion"
    return "Complex"


def _extract_vcf_statistics(path: str) -> dict | None:
    """Parse a VCF or VCF.GZ file and return summary counters.

    The summary is intentionally lightweight so the descriptive statistics page
    can surface content-level VCF metrics without introducing a heavy parser.
    """
    lower_path = str(path).lower()
    if not (lower_path.endswith(".vcf") or lower_path.endswith(".vcf.gz")):
        return None

    opener = gzip.open if lower_path.endswith(".gz") else open
    chromosome_counter = Counter()
    variant_type_counter = Counter()
    variant_count = 0

    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line or line.startswith("#"):
                    continue

                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5:
                    continue

                chrom = _extract_chromosome(parts[0])
                ref = parts[3]
                alts = parts[4]

                for alt in str(alts).split(","):
                    alt_text = alt.strip()
                    if not alt_text:
                        continue
                    variant_count += 1
                    if chrom:
                        chromosome_counter[chrom] += 1
                    variant_type_counter[_classify_vcf_variant_type(ref, alt_text)] += 1
    except OSError:
        return None

    return {
        "variant_count": variant_count,
        "chromosome_counter": chromosome_counter,
        "variant_type_counter": variant_type_counter,
    }


@insights_bp.route("/insights/summary", methods=["GET"])
def get_summary():
    start_date_raw = (request.args.get("start_date") or "").strip()
    end_date_raw = (request.args.get("end_date") or "").strip()
    test_type = (request.args.get("test_type") or "").strip()

    query = Patient.query
    if start_date_raw:
        try:
            query = query.filter(Patient.report_date >= date.fromisoformat(start_date_raw))
        except ValueError:
            return jsonify({"error": "start_date must be YYYY-MM-DD"}), 400
    if end_date_raw:
        try:
            query = query.filter(Patient.report_date <= date.fromisoformat(end_date_raw))
        except ValueError:
            return jsonify({"error": "end_date must be YYYY-MM-DD"}), 400
    if test_type:
        query = query.filter(Patient.type_of_test.ilike(f"%{test_type}%"))

    patient_rows = query.order_by(Patient.id.asc()).all()
    patient_ids = [patient.id for patient in patient_rows]
    patients = len(patient_rows)

    singleton_query = Singleton.query
    trio_query = Trio.query
    vcf_query = VcfFile.query
    if patient_ids:
        singleton_query = singleton_query.filter(Singleton.patient_id.in_(patient_ids))
        trio_query = trio_query.filter(Trio.patient_id.in_(patient_ids))
        vcf_query = vcf_query.filter(VcfFile.patient_id.in_(patient_ids))
    else:
        singleton_query = singleton_query.filter(False)
        trio_query = trio_query.filter(False)
        vcf_query = vcf_query.filter(False)

    singletons = singleton_query.all()
    trios = trio_query.all()
    vcf_rows = vcf_query.all()

    combined = [*singletons, *trios]

    chromosome_counter = Counter()
    variant_counter = Counter()
    gene_counter = Counter()
    gene_chromosome_counter = defaultdict(Counter)
    keyword_counter = Counter()
    reportable_variant_counter = Counter()
    sex_counter = Counter()
    age_counter = Counter()
    ethnicity_counter = Counter()
    test_counter = Counter()
    vcf_size_counter = Counter()
    vcf_content_chromosome_counter = Counter()
    vcf_content_type_counter = Counter()
    vcf_patient_variant_counter = Counter()
    vcf_patient_file_counter = Counter()
    vcf_content_variant_count = 0
    readable_vcf_files = 0
    skipped_vcf_files = 0
    sample_singleton_counter = Counter()
    sample_trio_counter = Counter()

    patient_lab_numbers = {
        patient.id: patient.lab_number
        for patient in patient_rows
    }

    for row in combined:
        chrom = _extract_chromosome(getattr(row, "chr_pos", None))
        if chrom:
            chromosome_counter[chrom] += 1

        reportable_variant_counter[_normalize_reportable_variant(getattr(row, "reportable_variant", None))] += 1

        chr_pos = (getattr(row, "chr_pos", None) or "").strip()
        ref_alt = (getattr(row, "ref_alt", None) or "").strip()
        if chr_pos or ref_alt:
            variant_counter[f"{chr_pos} {ref_alt}".strip()] += 1

        for gene in _split_genes(getattr(row, "gene_names", None)):
            gene_counter[gene] += 1
            if chrom:
                gene_chromosome_counter[gene][chrom] += 1

        for keyword in _tokenize_keywords(
            getattr(row, "title", None),
            getattr(row, "classification", None),
            getattr(row, "second_review_comment", None),
        ):
            keyword_counter[keyword] += 1

    for row in singletons:
        sample_singleton_counter[row.patient_id] += 1

    for row in trios:
        sample_trio_counter[row.patient_id] += 1

    for patient in patient_rows:
        sex_counter[_normalize_sex(getattr(patient, "sex", None))] += 1
        ethnicity_counter[_normalize_bucket_label(getattr(patient, "ethnicity", None))] += 1
        test_counter[_normalize_bucket_label(getattr(patient, "type_of_test", None))] += 1

        age_years = _parse_age_years(getattr(patient, "age", None), getattr(patient, "age_unit", None))
        age_bucket = _bucket_age(age_years)
        if age_bucket:
            age_counter[age_bucket] += 1

    for row in vcf_rows:
        vcf_patient_file_counter[row.patient_id] += 1

        size_bucket = _bucket_file_size(getattr(row, "file_size", None))
        if size_bucket:
            vcf_size_counter[size_bucket] += 1

        disk_path = os.path.join(current_app.config["VCF_DIR"], row.relative_path)
        stats = _extract_vcf_statistics(disk_path)
        if not stats:
            skipped_vcf_files += 1
            continue

        readable_vcf_files += 1
        vcf_content_variant_count += stats["variant_count"]
        vcf_content_chromosome_counter.update(stats["chromosome_counter"])
        vcf_content_type_counter.update(stats["variant_type_counter"])
        vcf_patient_variant_counter[row.patient_id] += stats["variant_count"]

    vcf_by_patient = []
    for patient_id, variant_count in vcf_patient_variant_counter.most_common(20):
        vcf_by_patient.append({
            "patient_id": patient_id,
            "lab_number": patient_lab_numbers.get(patient_id, f"Patient {patient_id}"),
            "file_count": vcf_patient_file_counter.get(patient_id, 0),
            "variant_count": variant_count,
        })

    sample_variant_counts = []
    for patient in patient_rows:
        singleton_count = sample_singleton_counter.get(patient.id, 0)
        trio_count = sample_trio_counter.get(patient.id, 0)
        total_count = singleton_count + trio_count
        if total_count == 0:
            continue
        sample_variant_counts.append({
            "patient_id": patient.id,
            "lab_number": patient.lab_number,
            "singleton_count": singleton_count,
            "trio_count": trio_count,
            "total_count": total_count,
        })

    sample_variant_counts.sort(
        key=lambda item: (-item["total_count"], item["lab_number"])
    )

    payload = {
        "filters": {
            "start_date": start_date_raw or None,
            "end_date": end_date_raw or None,
            "test_type": test_type or None,
        },
        "counts": {
            "patients": patients,
            "singleton_variants": len(singletons),
            "trio_variants": len(trios),
            "total_variants": len(combined),
            "vcf_files": len(vcf_rows),
            "vcf_content_variants": vcf_content_variant_count,
            "vcf_files_readable": readable_vcf_files,
            "vcf_files_skipped": skipped_vcf_files,
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
        "vcf_content_distribution": {
            "chromosome": [
                {"chromosome": k, "count": v}
                for k, v in vcf_content_chromosome_counter.most_common(24)
            ],
            "variant_type": [
                {"label": k, "count": v}
                for k, v in vcf_content_type_counter.most_common()
            ],
            "by_patient": vcf_by_patient,
        },
        "chromosome_distribution": [
            {"chromosome": k, "count": v}
            for k, v in chromosome_counter.most_common(24)
        ],
        "reported_variant_distribution": [
            {
                "label": label,
                "count": reportable_variant_counter.get(label, 0),
            }
            for label in ["C", "I", "A", "N"]
        ],
        "sample_variant_counts": sample_variant_counts,
        "top_variants": [
            {"variant": k, "count": v}
            for k, v in variant_counter.most_common(30)
        ],
        "top_genes": [
            {
                "gene": gene,
                "count": count,
                "chromosome": (
                    gene_chromosome_counter[gene].most_common(1)[0][0]
                    if gene_chromosome_counter.get(gene)
                    else None
                ),
            }
            for gene, count in gene_counter.most_common(30)
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
