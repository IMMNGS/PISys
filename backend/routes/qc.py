"""QC metrics CRUD and variant audit log routes.

Two QC file formats are supported:
  * ``panel`` — panel-of-genes pipeline output
  * ``exome`` — whole-exome (DRAGEN-style) output

The QC file is wide-format: one row per metric, one column per sample.
The first sample column is the run's positive control; the remaining
columns are patient samples keyed by ``Patient.lab_number``. The batch
label (e.g. ``26P1`` = 2026, panel batch 1) is parsed from the filename.

Three values per sample are extracted into dedicated columns for fast
lookup by the report generator: ``median_coverage``, ``pct_20x``,
``uniformity_pct``. All other rows are preserved as JSON in ``metrics``
for downstream analysis/plotting; the run's positive-control values are
stored alongside in ``positive_control``.
"""

import csv
import io
import json
import os
import re
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, request, current_app
from werkzeug.utils import secure_filename

from backend.models import db, Patient, NgsQc, NgsQcBatch, VariantAuditLog

qc_bp = Blueprint("qc", __name__)


# ── Key resolution: file rows → report-critical metrics ─────────────────

PANEL_KEY_MAP = {
    "median_coverage": ["Median_coverage"],
    "pct_20x": ["Coverage_20X(%)", "Coverage_20X_pct"],
    "uniformity_pct": ["Uniformity(%)", "Uniformity_pct"],
}

EXOME_KEY_MAP = {
    "median_coverage": ["median_autosomal_coverage_over_target_region"],
    "pct_20x": ["pct_of_target_region_with_coverage_20x_inf"],
    "uniformity_pct": ["uniformity_of_coverage_pct_gt_02mean_over_target_region"],
}


def _coerce_numeric(value):
    """Strip percent signs / commas and try to parse as float."""
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _detect_delimiter(first_line: str) -> str:
    if "\t" in first_line:
        return "\t"
    if "," in first_line:
        return ","
    return ","


def _parse_wide_qc(text: str) -> list[tuple[str, dict[str, str]]]:
    """Parse a wide-format QC file.

    Layout::

        <metric col header>, <sample_label_1>, <sample_label_2>, ...
        <metric_name_1>,     <val>,            <val>,            ...
        <metric_name_2>,     <val>,            <val>,            ...

    Returns a list of ``(sample_label, metrics_dict)`` for each column.
    The first element is usually the positive control; subsequent
    elements are patient samples. Returning a list preserves duplicate
    sample labels if the same sample was run multiple times in the batch.
    """
    text = (text or "").strip()
    if not text:
        return []

    first_line = text.split("\n", 1)[0]
    delim = _detect_delimiter(first_line)

    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = [r for r in reader if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return []

    header = rows[0]
    # Keep the label and corresponding original column index
    cols = []
    for col_idx, h in enumerate(header[1:], start=1):
        label = (h or "").strip()
        if label:
            cols.append((col_idx, label))

    if not cols:
        return []

    # Initialize a list of dicts for each valid column
    parsed_columns = [(label, {}) for _, label in cols]

    for row in rows[1:]:
        metric = (row[0] or "").strip() if row else ""
        if not metric:
            continue
        
        for i, (col_idx, _label) in enumerate(cols):
            if col_idx < len(row):
                value = (row[col_idx] or "").strip()
                if value:
                    parsed_columns[i][1][metric] = value

    return parsed_columns


def _extract_report_metrics(qc_type: str, metrics: dict) -> dict:
    """Pull median_coverage, pct_20x, uniformity_pct out of the raw dict."""
    key_map = EXOME_KEY_MAP if qc_type == "exome" else PANEL_KEY_MAP
    lower_metrics = {k.lower(): v for k, v in metrics.items()}

    out = {"median_coverage": None, "pct_20x": None, "uniformity_pct": None}
    for field, candidates in key_map.items():
        for cand in candidates:
            if cand in metrics:
                out[field] = _coerce_numeric(metrics[cand])
                break
            if cand.lower() in lower_metrics:
                out[field] = _coerce_numeric(lower_metrics[cand.lower()])
                break
    return out


# Filename batch pattern: yyPx (e.g. "26P1" = year 2026, panel batch 1).
# Matches case-insensitively as a standalone token in the filename.
_BATCH_RE = re.compile(r"(?<![A-Za-z0-9])(\d{2})([Pp])(\d+)(?![A-Za-z0-9])")


def _extract_batch_label(filename: str) -> str | None:
    if not filename:
        return None
    match = _BATCH_RE.search(filename)
    if not match:
        return None
    yy, _p, num = match.groups()
    return f"{yy}P{int(num)}"


def _extract_batch_from_label(label: str) -> str | None:
    """Extract a batch token (e.g. '26P1') from a sample label such as a
    positive control name formatted as ``xxxxx-yyPz``.
    """
    if not label:
        return None
    match = _BATCH_RE.search(label)
    if not match:
        return None
    yy, _p, num = match.groups()
    return f"{yy}P{int(num)}"


# ── Routes ──────────────────────────────────────────────────────────────

@qc_bp.route("/patients/<int:patient_id>/qc", methods=["GET"])
def list_qc(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    records = (
        NgsQc.query
        .filter_by(patient_id=patient_id)
        .order_by(NgsQc.uploaded_at.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in records])


@qc_bp.route("/patients/<int:patient_id>/qc", methods=["POST"])
def create_qc_manual(patient_id):
    """Create a single QC record for one patient from a JSON body.

    For multi-sample QC files, use ``POST /api/qc/upload`` instead.
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)

    data = request.get_json(silent=True) or {}
    qc_type = (data.get("qc_type") or "panel").strip().lower()
    if qc_type not in ("panel", "exome"):
        return jsonify({"error": "qc_type must be 'panel' or 'exome'"}), 400

    metrics = data.get("metrics") or {}
    if not isinstance(metrics, dict):
        return jsonify({"error": "metrics must be an object"}), 400

    extracted = (
        _extract_report_metrics(qc_type, metrics)
        if metrics else {"median_coverage": None, "pct_20x": None, "uniformity_pct": None}
    )

    qc = NgsQc(patient_id=patient_id, qc_type=qc_type)
    qc.batch = (data.get("batch") or "").strip() or None
    qc.metrics = json.dumps(metrics) if metrics else None
    # Explicit overrides win over file-derived values.
    qc.median_coverage = (
        _coerce_numeric(data.get("median_coverage"))
        if "median_coverage" in data else extracted["median_coverage"]
    )
    qc.pct_20x = (
        _coerce_numeric(data.get("pct_20x"))
        if "pct_20x" in data else extracted["pct_20x"]
    )
    qc.uniformity_pct = (
        _coerce_numeric(data.get("uniformity_pct"))
        if "uniformity_pct" in data else extracted["uniformity_pct"]
    )
    qc.pass_fail = (data.get("pass_fail") or "").strip().upper() or None
    qc.notes = data.get("notes") or None

    db.session.add(qc)
    db.session.commit()
    return jsonify(qc.to_dict()), 201


@qc_bp.route("/qc/upload", methods=["POST"])
def upload_qc_bulk():
    """Upload a wide-format QC file containing many samples.

    multipart/form-data:
        file:     CSV / TSV with columns [metric, pos_ctrl, sample1, sample2, ...]
        qc_type:  "panel" | "exome"
        batch:    optional override; otherwise parsed from the filename.

    Returns a summary of created records and any unmatched lab numbers.
    Existing records for the same (patient, batch) are not deduplicated —
    re-uploading creates a new entry; the report uses the most recent.
    """
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]

    qc_type = (request.form.get("qc_type") or "panel").strip().lower()
    if qc_type not in ("panel", "exome"):
        return jsonify({"error": "qc_type must be 'panel' or 'exome'"}), 400

    try:
        text = f.stream.read().decode("utf-8", errors="replace")
    except Exception:
        return jsonify({"error": "Could not read QC file as text"}), 400

    parsed_columns = _parse_wide_qc(text)
    if not parsed_columns:
        return jsonify({"error": "Could not parse any samples from file"}), 400

    # First sample column is the positive control; the rest are patient samples.
    pos_ctrl_label, pos_ctrl_metrics = parsed_columns[0]
    pos_ctrl_blob = json.dumps(pos_ctrl_metrics) if pos_ctrl_metrics else None

    patient_columns = parsed_columns[1:]
    patient_labels = [label for label, _ in patient_columns]

    # Batch comes from the explicit form field, else parsed from filename,
    # else extracted from the positive control label (e.g. NA12878-26P1).
    batch = (
        (request.form.get("batch") or "").strip()
        or _extract_batch_label(f.filename)
        or _extract_batch_from_label(pos_ctrl_label)
    )

    # Persist the uploaded file once so every created NgsQc row can reference it.
    qc_dir = current_app.config.get("QC_DIR") or os.path.join(
        current_app.config.get("DATA_DIR", current_app.instance_path),
        "qc_uploads",
    )
    batch_dir = os.path.join(qc_dir, batch or "no_batch", qc_type)
    os.makedirs(batch_dir, exist_ok=True)

    safe_name = secure_filename(f.filename) or f"{qc_type}_qc.csv"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stored_filename = f"{timestamp}_{safe_name}"
    dest = os.path.join(batch_dir, stored_filename)

    f.stream.seek(0)
    f.save(dest)
    relative_path = os.path.join(batch or "no_batch", qc_type, stored_filename)
    file_size = os.path.getsize(dest)

    # Look up patients in one query (match against both lab_number and im_lab_number).
    patients_by_lab = {}
    if patient_labels:
        patients = Patient.query.filter(
            db.or_(Patient.lab_number.in_(patient_labels), Patient.im_lab_number.in_(patient_labels))
        ).all()
        for p in patients:
            if p.im_lab_number and p.im_lab_number in patient_labels:
                patients_by_lab[p.im_lab_number] = p
            if p.lab_number in patient_labels:
                patients_by_lab[p.lab_number] = p

    matched = []
    unmatched = []
    pass_fail_form = (request.form.get("pass_fail") or "").strip().upper() or None
    notes_form = request.form.get("notes") or None

    try:
        for label, sample_metrics in patient_columns:
            patient = patients_by_lab.get(label)
            if not patient:
                unmatched.append(label)
                continue

            extracted = _extract_report_metrics(qc_type, sample_metrics)

            qc = NgsQc(
                patient_id=patient.id,
                qc_type=qc_type,
                batch=batch,
                median_coverage=extracted["median_coverage"],
                pct_20x=extracted["pct_20x"],
                uniformity_pct=extracted["uniformity_pct"],
                pass_fail=pass_fail_form,
                notes=notes_form,
                metrics=json.dumps(sample_metrics) if sample_metrics else None,
                positive_control=pos_ctrl_blob,
                original_filename=f.filename,
                relative_path=relative_path,
                file_size=file_size,
            )
            db.session.add(qc)
            matched.append(qc)

        # Persist a batch row even when zero patients matched so the
        # positive control and file metadata are never lost.
        batch_record = NgsQcBatch(
            qc_type=qc_type,
            batch=batch,
            positive_control_label=pos_ctrl_label,
            positive_control=pos_ctrl_blob,
            original_filename=f.filename,
            relative_path=relative_path,
            file_size=file_size,
            matched_count=len(matched),
            unmatched_labels=json.dumps(unmatched) if unmatched else None,
        )
        db.session.add(batch_record)

        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.isfile(dest):
            os.remove(dest)
        raise

    return jsonify({
        "batch": batch,
        "qc_type": qc_type,
        "filename": f.filename,
        "positive_control_label": pos_ctrl_label,
        "positive_control": pos_ctrl_metrics,
        "matched_count": len(matched),
        "unmatched": unmatched,
        "records": [r.to_dict() for r in matched],
    }), 201


@qc_bp.route("/qc/<int:qc_id>", methods=["DELETE"])
def delete_qc(qc_id):
    qc = db.session.get(NgsQc, qc_id)
    if not qc:
        abort(404)

    # Only delete the file if no other QC row still references it (bulk
    # uploads share one file across many rows).
    if qc.relative_path:
        still_used = (
            NgsQc.query
            .filter(NgsQc.relative_path == qc.relative_path, NgsQc.id != qc.id)
            .first()
        )
        if not still_used:
            qc_dir = current_app.config.get("QC_DIR", "")
            if qc_dir:
                disk_path = os.path.join(qc_dir, qc.relative_path)
                if os.path.isfile(disk_path):
                    os.remove(disk_path)

    db.session.delete(qc)
    db.session.commit()
    return jsonify({"message": "QC record deleted"}), 200


@qc_bp.route("/qc/batches", methods=["GET"])
def list_qc_batches():
    """List all QC file uploads (batches), including those with zero patient matches."""
    batches = (
        NgsQcBatch.query
        .order_by(NgsQcBatch.uploaded_at.desc())
        .all()
    )
    return jsonify([b.to_dict() for b in batches])


@qc_bp.route("/qc/batch/<int:batch_id>", methods=["DELETE"])
def delete_qc_batch(batch_id):
    """Delete a QC batch and all associated per-patient NgsQc records.

    Also removes the underlying file if nothing else references it.
    """
    batch = db.session.get(NgsQcBatch, batch_id)
    if not batch:
        abort(404)

    # Delete all per-patient QC rows linked to this upload.
    if batch.relative_path:
        NgsQc.query.filter(NgsQc.relative_path == batch.relative_path).delete(
            synchronize_session=False
        )

        # Delete the file on disk if it exists.
        qc_dir = current_app.config.get("QC_DIR", "")
        if qc_dir:
            disk_path = os.path.join(qc_dir, batch.relative_path)
            if os.path.isfile(disk_path):
                os.remove(disk_path)

    db.session.delete(batch)
    db.session.commit()
    return jsonify({"message": "QC batch deleted"}), 200


@qc_bp.route("/patients/<int:patient_id>/variant_audit", methods=["GET"])
def list_variant_audit(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    limit = min(int(request.args.get("limit", 200)), 500)
    entries = (
        VariantAuditLog.query
        .filter_by(patient_id=patient_id)
        .order_by(VariantAuditLog.changed_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([e.to_dict() for e in entries])
