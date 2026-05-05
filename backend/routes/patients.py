"""Patient CRUD and bulk-import routes."""

import gzip
import io
import math
import os
from datetime import date, datetime, timezone

from flask import Blueprint, abort, jsonify, request, current_app, send_file

from backend.models import (
    db,
    Patient,
    VcfFile,
    patient_disease_term,
    patient_hpo,
)
from backend.routes.helpers import (
    _patient_to_dict, _parse_xlsx_rows,
    PATIENT_FIELDS, DATE_FIELDS,
    validate_lab_number, get_available_patient_fields,
    auto_map_columns,
)

patients_bp = Blueprint("patients", __name__)

_FULL = dict(include_hpo=True, include_singletons=True,
             include_trios=True, include_vcf_files=True,
             include_disease_terms=True, include_variant_uploads=True)


def _coerce_patient_date(value):
    """Normalize patient date-like input to ``date`` or ``None``.

    XLSX uploads can contain notes/comments in date columns. Treat any
    non-date or unparseable value as null so import remains resilient.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

    return None


def _normalize_patient_sex_age(row):
    """Populate ``sex``/``age`` from compact values such as ``M/8``.

    Files may contain dedicated ``sex`` and ``age`` columns, or a combined
    ``sex/age``-style column. This normalizer fills missing canonical fields
    without overriding explicitly provided separate values.
    """
    normalized = dict(row or {})

    def _is_blank(value):
        if value is None:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def _normalize_sex_token(token):
        if token is None:
            return None
        text = str(token).strip().upper()
        if text in {"M", "MALE", "BOY"}:
            return "M"
        if text in {"F", "FEMALE", "GIRL"}:
            return "F"
        return None

    def _split_compact(value):
        if _is_blank(value):
            return None, None
        text = str(value).strip()
        if "/" not in text:
            return None, None
        left, right = [part.strip() for part in text.split("/", 1)]
        if not left or not right:
            return None, None

        left_sex = _normalize_sex_token(left)
        right_sex = _normalize_sex_token(right)
        if left_sex:
            return left_sex, right
        if right_sex:
            return right_sex, left
        return None, None

    current_sex = normalized.get("sex")
    current_age = normalized.get("age")

    combined_candidates = [
        normalized.get("sex/age"),
        normalized.get("sex_age"),
        current_sex,
        current_age,
    ]

    parsed_sex = None
    parsed_age = None
    for candidate in combined_candidates:
        s_val, a_val = _split_compact(candidate)
        if s_val and a_val:
            parsed_sex, parsed_age = s_val, a_val
            break

    sex_has_compact_value = isinstance(current_sex, str) and "/" in current_sex
    if (_is_blank(current_sex) or sex_has_compact_value) and parsed_sex:
        normalized["sex"] = parsed_sex
    elif not _is_blank(current_sex):
        normalized_sex = _normalize_sex_token(current_sex)
        if normalized_sex:
            normalized["sex"] = normalized_sex

    if _is_blank(current_age) and parsed_age:
        normalized["age"] = parsed_age

    return normalized


def _extract_variant_keys_from_vcf(path):
    """Parse one .vcf/.vcf.gz file and return a set of (chrom, pos, ref, alt)."""
    opener = gzip.open if str(path).lower().endswith(".gz") else open
    keys = set()
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            chrom, pos, _vid, ref, alts = parts[:5]
            chrom = str(chrom).strip()
            pos = str(pos).strip()
            ref = str(ref).strip()
            if not chrom or not pos or not ref:
                continue
            for alt in str(alts).split(","):
                alt_value = alt.strip()
                if alt_value:
                    keys.add((chrom, pos, ref, alt_value))
    return keys


# ── CRUD ─────────────────────────────────────────────────────────────────

@patients_bp.route("/patients", methods=["GET"])
def get_patients():
    """Return all patients with optional search."""
    search = request.args.get("search", "").strip()
    query = Patient.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Patient.lab_number.ilike(like),
                Patient.im_lab_number.ilike(like),
                Patient.name.ilike(like),
                Patient.type_of_test.ilike(like),
                Patient.type_of_findings.ilike(like),
                Patient.request_dr.ilike(like),
            )
        )
    query = query.order_by(Patient.id)
    patients = query.all()
    return jsonify([_patient_to_dict(p, **_FULL) for p in patients])


@patients_bp.route("/patients/options", methods=["GET"])
def get_patient_options():
    """Lightweight paginated endpoint returning only id, lab_number, name.
    Query params: search, limit (default 20), offset (default 0).
    Returns {items: [...], total: int}."""
    search = request.args.get("search", "").strip()
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    query = Patient.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Patient.lab_number.ilike(like),
                Patient.im_lab_number.ilike(like),
                Patient.name.ilike(like),
            )
        )
    query = query.order_by(Patient.id)
    total = query.count()
    patients = query.offset(offset).limit(limit).all()
    items = [{
        "id": p.id,
        "lab_number": p.lab_number,
        "im_lab_number": p.im_lab_number,
        "name": p.name,
    }
             for p in patients]
    return jsonify({"items": items, "total": total})


@patients_bp.route("/patients/list", methods=["GET"])
def get_patient_list():
    """Paginated patient list for the table view — lightweight (no nested data).
    Supports per-column filters as query params.
    Returns {items: [...], total: int}."""
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    query = Patient.query

    # Per-column filters
    for col_name, col_attr in [
        ("lab_number", Patient.lab_number),
        ("im_lab_number", Patient.im_lab_number),
        ("name", Patient.name),
        ("sex", Patient.sex),
        ("type_of_test", Patient.type_of_test),
    ]:
        val = request.args.get(col_name, "").strip()
        if val:
            query = query.filter(col_attr.ilike(f"%{val}%"))

    age_filter = request.args.get("age", "").strip()
    if age_filter:
        query = query.filter(Patient.age.ilike(f"%{age_filter}%"))

    # Combined terms filter (HPO + free-text disease) — require ALL selected
    # term IDs. Positive IDs = hpo_terms.id, negative IDs = disease_terms.id.
    term_ids = request.args.get("term_ids", "").strip()
    if term_ids:
        try:
            id_list = [int(x) for x in term_ids.split(",") if x.strip()]
        except ValueError:
            id_list = []
        for term_id in id_list:
            if term_id > 0:
                query = query.filter(
                    Patient.id.in_(
                        db.session.query(patient_hpo.c.patient_id).filter(
                            patient_hpo.c.hpo_term_id == term_id
                        )
                    )
                )
            elif term_id < 0:
                disease_id = abs(term_id)
                query = query.filter(
                    Patient.id.in_(
                        db.session.query(patient_disease_term.c.patient_id).filter(
                            patient_disease_term.c.disease_term_id == disease_id
                        )
                    )
                )

    query = query.order_by(Patient.id)
    total = query.count()
    patients = query.offset(offset).limit(limit).all()
    items = [p.to_dict(include_hpo=True, include_disease_terms=True) for p in patients]
    return jsonify({"items": items, "total": total})


@patients_bp.route("/patients/<int:patient_id>", methods=["GET"])
def get_patient(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    return jsonify(_patient_to_dict(patient, **_FULL))


@patients_bp.route("/patients/filter_options", methods=["GET"])
def get_filter_options():
    """Return distinct values for dropdown filters.
    Returns {sex: [...], type_of_test: [...], terms: [...]}."""
    sex_values = sorted([
        r[0] for r in
        db.session.query(Patient.sex).filter(Patient.sex.isnot(None), Patient.sex != "").distinct().all()
    ])
    test_values = sorted([
        r[0] for r in
        db.session.query(Patient.type_of_test).filter(
            Patient.type_of_test.isnot(None), Patient.type_of_test != ""
        ).distinct().all()
    ])
    return jsonify({"sex": sex_values, "type_of_test": test_values, "terms": []})


@patients_bp.route("/patients", methods=["POST"])
def create_patient():
    """Create a new patient."""
    data = request.get_json(silent=True) or {}
    lab_number = str(data.get("lab_number") or "").strip()
    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400
    if not validate_lab_number(lab_number):
        return jsonify({"error": "Invalid lab number format"}), 400
    if Patient.query.filter_by(lab_number=lab_number).first():
        return jsonify({"error": f"Lab number {lab_number} already exists"}), 409

    if "case_history" not in data and data.get("clinical_history") is not None:
        data["case_history"] = data.get("clinical_history")
    if "clinical_history" not in data and data.get("case_history") is not None:
        data["clinical_history"] = data.get("case_history")

    patient = Patient(lab_number=lab_number)
    for field in PATIENT_FIELDS:
        if field != "lab_number" and field in data:
            value = data[field]
            if field in DATE_FIELDS:
                value = _coerce_patient_date(value)
            setattr(patient, field, value)
    db.session.add(patient)
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL)), 201


@patients_bp.route("/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    """Update an existing patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    data = request.get_json()
    if "clinical_history" not in data and "case_history" in data:
        data["clinical_history"] = data.get("case_history")
    for field in PATIENT_FIELDS:
        if field in data:
            setattr(patient, field, data[field])
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL))


@patients_bp.route("/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    patient.hpo_terms.clear()
    patient.disease_terms.clear()
    db.session.delete(patient)
    db.session.commit()
    return jsonify({"message": "Patient deleted"}), 200


# ── Bulk XLSX import ─────────────────────────────────────────────────────

@patients_bp.route("/patients/upload", methods=["POST"])
def upload_patients_xlsx():
    """Import patients from an XLSX file.

    Each row becomes a new patient record.  The ``lab_number`` column is
    required and must be unique — rows whose lab_number already exists in
    the DB are **skipped** (not updated) and reported back to the caller.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files are accepted"}), 400

    rows = _parse_xlsx_rows(f)
    if not rows:
        return jsonify({"error": "File is empty or has no data rows"}), 400

    existing_labs = {p.lab_number for p in
                     Patient.query.with_entities(Patient.lab_number).all()}

    added = 0
    skipped = []
    invalid = []

    def _has_non_lab_data(row_dict):
        """True when at least one non-lab field in a row has a meaningful value."""
        for key, value in row_dict.items():
            if key == "lab_number":
                continue
            if value is None:
                continue
            if isinstance(value, float) and math.isnan(value):
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return True
        return False

    for row in rows:
        row = _normalize_patient_sex_age(row)
        lab = row.get("lab_number")
        if not lab:
            continue
        lab = str(lab).strip()
        if not _has_non_lab_data(row):
            # Ignore rows where only lab number is present.
            continue
        if not validate_lab_number(lab):
            invalid.append(lab)
            continue
        if lab in existing_labs:
            skipped.append(lab)
            continue

        if "case_history" not in row and row.get("clinical_history") is not None:
            row["case_history"] = row.get("clinical_history")

        patient = Patient(lab_number=lab)
        for field in PATIENT_FIELDS:
            if field == "lab_number":
                continue
            val = row.get(field)
            if field in DATE_FIELDS:
                val = _coerce_patient_date(val)
                if val is None:
                    continue

            if val is None or (isinstance(val, str) and val.strip() == ""):
                continue
            setattr(patient, field, val)

        db.session.add(patient)
        existing_labs.add(lab)
        added += 1

    db.session.commit()
    msg = f"Imported {added} patient(s)"
    if skipped:
        msg += f", skipped {len(skipped)} duplicate(s): {', '.join(skipped)}"
    if invalid:
        msg += f", skipped {len(invalid)} invalid lab number(s): {', '.join(invalid)}"
    return jsonify({"message": msg, "added": added, "skipped": skipped, "invalid": invalid}), 201


# ── Patient ↔ HPO Assignment ────────────────────────────────────────────

@patients_bp.route("/patients/<int:patient_id>/hpo_terms", methods=["GET"])
def get_patient_hpo_terms(patient_id):
    """List all HPO terms assigned to a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    return jsonify([t.to_dict() for t in patient.hpo_terms])


@patients_bp.route("/patients/assign_hpo", methods=["POST"])
def assign_hpo_to_patients():
    """
    Assign one or more HPO terms to one or more patients.
    Body: { "patient_ids": [1, 2], "hpo_term_ids": [5, 10] }
    """
    data = request.get_json()
    patient_ids = data.get("patient_ids", [])
    hpo_term_ids = data.get("hpo_term_ids", [])

    patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
    terms = HPOTerm.query.filter(HPOTerm.id.in_(hpo_term_ids)).all()
    terms_map = {t.id: t for t in terms}

    added = 0
    for patient in patients:
        existing_ids = {t.id for t in patient.hpo_terms}
        for tid in hpo_term_ids:
            if tid not in existing_ids and tid in terms_map:
                patient.hpo_terms.append(terms_map[tid])
                added += 1

    db.session.commit()
    return jsonify({"message": f"Assigned {added} HPO term(s) across {len(patients)} patient(s)."}), 200


@patients_bp.route("/patients/<int:patient_id>/hpo_terms/<int:term_id>", methods=["DELETE"])
def remove_hpo_from_patient(patient_id, term_id):
    """Remove an HPO term from a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    term = db.session.get(HPOTerm, term_id)
    if not term:
        abort(404)
    if term in patient.hpo_terms:
        patient.hpo_terms.remove(term)
    db.session.commit()
    return jsonify({"message": "HPO term removed from patient"}), 200


# ── Selection / Analysis Endpoint ────────────────────────────────────────

@patients_bp.route("/patients/selected", methods=["POST"])
def get_selected_patients():
    """
    Return full details for a set of selected patient IDs.
    Body: { "patient_ids": [1, 2, 3] }
    """
    data = request.get_json()
    ids = data.get("patient_ids", [])
    patients = Patient.query.filter(Patient.id.in_(ids)).all()
    return jsonify([_patient_to_dict(p, **_FULL) for p in patients])


@patients_bp.route("/patients/extract", methods=["POST"])
def extract_patients_with_mode():
    """Extract selected patients with configurable related file payload.

    Body:
      {
        "patient_ids": [1,2],
                "mode": "selected_files" | "all_files",
        "file_types": ["singletons", "trios", "vcf_files"]
      }
    """
    data = request.get_json() or {}
    ids = data.get("patient_ids", [])
    mode = str(data.get("mode", "all_files")).strip().lower()
    file_types = data.get("file_types", []) or []

    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "patient_ids is required"}), 400
    if mode == "which_files":
        mode = "selected_files"
    if mode not in {"selected_files", "all_files"}:
        return jsonify({"error": "mode must be 'selected_files' or 'all_files'"}), 400
    if mode == "selected_files" and not isinstance(file_types, list):
        return jsonify({"error": "file_types must be a list"}), 400

    selected_types = {str(t).strip() for t in file_types}
    include_singletons = mode == "all_files" or "singletons" in selected_types
    include_trios = mode == "all_files" or "trios" in selected_types
    include_vcf_files = mode == "all_files" or "vcf_files" in selected_types

    rows = Patient.query.filter(Patient.id.in_(ids)).all()
    by_id = {p.id: p for p in rows}

    payload = []
    for pid in ids:
        patient = by_id.get(pid)
        if not patient:
            continue
        payload.append(patient.to_dict(
            include_hpo=True,
            include_disease_terms=True,
            include_singletons=include_singletons,
            include_trios=include_trios,
            include_vcf_files=include_vcf_files,
        ))

    return jsonify(payload)


@patients_bp.route("/patients/extract/common_variants_vcf", methods=["POST"])
def extract_common_variants_vcf():
    """Find common variants across selected patients and return a VCF file.

    A variant key is defined as (CHROM, POS, REF, ALT).
    For each selected patient, variants are the union across all readable
    `.vcf` and `.vcf.gz` files linked to that patient.
    """
    data = request.get_json() or {}
    ids = data.get("patient_ids", [])
    if not isinstance(ids, list) or len(ids) < 2:
        return jsonify({"error": "Select at least 2 patients for common variants"}), 400

    patients = Patient.query.filter(Patient.id.in_(ids)).all()
    if len(patients) < 2:
        return jsonify({"error": "At least 2 valid patients are required"}), 400

    vcf_dir = current_app.config["VCF_DIR"]
    per_patient_variant_sets = []

    for patient in patients:
        variant_keys = set()
        files = VcfFile.query.filter_by(patient_id=patient.id).all()
        for record in files:
            lower = (record.filename or "").lower()
            if not (lower.endswith(".vcf") or lower.endswith(".vcf.gz")):
                continue
            disk_path = os.path.join(vcf_dir, record.relative_path)
            if not os.path.isfile(disk_path):
                continue
            try:
                variant_keys |= _extract_variant_keys_from_vcf(disk_path)
            except OSError:
                continue

        if not variant_keys:
            return jsonify({
                "error": f"No readable .vcf/.vcf.gz variants found for patient {patient.lab_number}"
            }), 400

        per_patient_variant_sets.append(variant_keys)

    common_keys = set.intersection(*per_patient_variant_sets) if per_patient_variant_sets else set()

    def _sort_key(item):
        chrom, pos, ref, alt = item
        try:
            pos_num = int(pos)
        except ValueError:
            pos_num = 10**12
        return chrom, pos_num, ref, alt

    now_utc = datetime.now(timezone.utc)
    lines = [
        "##fileformat=VCFv4.1",
        "##source=HA-common-variants",
        f"##generated={now_utc.isoformat()}",
        f"##selected_patients={','.join(str(i) for i in ids)}",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]
    for chrom, pos, ref, alt in sorted(common_keys, key=_sort_key):
        lines.append(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t.\tPASS\t.")

    content = "\n".join(lines) + "\n"
    filename = f"common_variants_{now_utc.strftime('%Y%m%d_%H%M%S')}.vcf"
    return send_file(
        io.BytesIO(content.encode("utf-8")),
        mimetype="text/vcf",
        as_attachment=True,
        download_name=filename,
    )


# ── Update findings / report-date ────────────────────────────────────────

@patients_bp.route("/patients/<int:patient_id>/findings", methods=["PUT"])
def update_findings(patient_id):
    """Update only the type_of_findings field on a patient.

    Body: { "type_of_findings": "C" }
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    data = request.get_json()
    findings = data.get("type_of_findings")
    if findings is None:
        return jsonify({"error": "type_of_findings is required"}), 400
    patient.type_of_findings = findings
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL))


@patients_bp.route(
    "/patients/<int:patient_id>/findings_and_report_date", methods=["PUT"]
)
def update_findings_and_report_date(patient_id):
    """Update type_of_findings *and* report_date in one request.

    Body: { "type_of_findings": "C", "report_date": "2025-03-15" }
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    data = request.get_json()
    if "type_of_findings" in data:
        patient.type_of_findings = data["type_of_findings"]
    if "report_date" in data and data["report_date"]:
        try:
            from datetime import date as _date
            patient.report_date = _date.fromisoformat(str(data["report_date"])[:10])
        except ValueError:
            pass
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL))


# ── Patient field metadata (for dynamic frontend column mapping UI) ──────

@patients_bp.route("/patients/fields", methods=["GET"])
def get_patient_fields_route():
    """Return available database fields for patient data mapping.

    Useful for the frontend to build the column-mapping UI when importing
    XLSX files.
    """
    return jsonify({
        "success": True,
        "fields": get_available_patient_fields(),
    })
