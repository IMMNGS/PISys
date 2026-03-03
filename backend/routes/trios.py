"""Trio variant CRUD and XLSX upload routes."""

import os
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, request, current_app
from werkzeug.utils import secure_filename

from backend.models import db, Patient, Trio, VariantUpload
from backend.routes.helpers import (
    TRIO_FIELDS,
    _parse_variant_xlsx_rows,
    _normalize_variant_field,
    normalize_variant_row,
)

trios_bp = Blueprint("trios", __name__)


# ── CRUD ─────────────────────────────────────────────────────────────────

@trios_bp.route("/patients/<int:patient_id>/trios", methods=["GET"])
def list_trios(patient_id):
    """Return all trio findings for a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    rv_filter = request.args.get("reportable_variant", "").strip()
    query = Trio.query.filter_by(patient_id=patient_id)
    if rv_filter:
        query = query.filter(Trio.reportable_variant == rv_filter)
    trios = query.order_by(Trio.id).all()
    return jsonify([t.to_dict() for t in trios])


@trios_bp.route("/patients/<int:patient_id>/trios", methods=["POST"])
def create_trio(patient_id):
    """Create a new trio finding for a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    data = request.get_json()
    trio = Trio(patient_id=patient_id)
    for field in TRIO_FIELDS:
        if field in data:
            val = _normalize_variant_field(field, data[field])
            setattr(trio, field, val)
    db.session.add(trio)
    db.session.commit()
    return jsonify(trio.to_dict()), 201


@trios_bp.route("/trios/<int:trio_id>", methods=["PUT"])
def update_trio(trio_id):
    """Update an existing trio finding."""
    trio = db.session.get(Trio, trio_id)
    if not trio:
        abort(404)
    data = request.get_json()
    for field in TRIO_FIELDS:
        if field in data:
            val = _normalize_variant_field(field, data[field])
            setattr(trio, field, val)
    db.session.commit()
    return jsonify(trio.to_dict())


@trios_bp.route("/trios/<int:trio_id>", methods=["DELETE"])
def delete_trio(trio_id):
    """Delete a trio finding."""
    trio = db.session.get(Trio, trio_id)
    if not trio:
        abort(404)
    db.session.delete(trio)
    db.session.commit()
    return jsonify({"message": "Trio deleted"}), 200


# ── XLSX upload ──────────────────────────────────────────────────────────

@trios_bp.route(
    "/patients/<int:patient_id>/upload/trio", methods=["POST"]
)
def upload_trio_xlsx(patient_id):
    """Import trio variant findings from an XLSX file.

    Each row becomes a new Trio record linked to the patient.
    Column names are fuzzy-mapped to DB fields automatically.
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"error": "Only .xlsx / .xls files are accepted"}), 400

    rows = _parse_variant_xlsx_rows(f)
    if not rows:
        return jsonify({"error": "File is empty or has no data rows"}), 400

    variant_dir = (
        current_app.config.get("VARIANT_UPLOAD_DIR")
        or os.path.join(
            current_app.config.get("DATA_DIR", current_app.instance_path),
            "variant_uploads",
        )
    )
    patient_dir = os.path.join(variant_dir, patient.lab_number, "trio")
    os.makedirs(patient_dir, exist_ok=True)

    safe_name = secure_filename(f.filename) or "variant.xlsx"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stored_filename = f"{timestamp}_{safe_name}"
    dest = os.path.join(patient_dir, stored_filename)

    f.stream.seek(0)
    f.save(dest)

    relative_path = os.path.join(patient.lab_number, "trio", stored_filename)
    file_size = os.path.getsize(dest)

    count = 0
    try:
        for row in rows:
            trio = Trio(patient_id=patient_id)
            normalized = normalize_variant_row(row, TRIO_FIELDS)
            if normalized:
                for field, val in normalized.items():
                    setattr(trio, field, val)
                db.session.add(trio)
                count += 1

        upload_record = VariantUpload(
            patient_id=patient_id,
            file_type="trio",
            original_filename=f.filename,
            stored_filename=stored_filename,
            relative_path=relative_path,
            file_size=file_size,
        )
        db.session.add(upload_record)
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.isfile(dest):
            os.remove(dest)
        raise

    return jsonify({"message": f"Imported {count} trio variant(s)", "count": count}), 201
