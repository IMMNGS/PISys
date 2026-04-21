"""Singleton variant CRUD and XLSX upload routes."""

import os
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, request, current_app
from werkzeug.utils import secure_filename

from backend.models import db, Patient, Singleton, VariantUpload
from backend.routes.helpers import (
    SINGLETON_FIELDS,
    _parse_variant_xlsx_rows,
    _normalize_variant_field,
    normalize_variant_row,
    variant_upload_id_mismatch_message,
)

singletons_bp = Blueprint("singletons", __name__)


# ── CRUD ─────────────────────────────────────────────────────────────────

@singletons_bp.route("/patients/<int:patient_id>/singletons", methods=["GET"])
def list_singletons(patient_id):
    """Return all singleton findings for a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    # Optional filter by reportable_variant type (C, A, I, N)
    rv_filter = request.args.get("reportable_variant", "").strip()
    query = Singleton.query.filter_by(patient_id=patient_id)
    if rv_filter:
        query = query.filter(Singleton.reportable_variant == rv_filter)
    singletons = query.order_by(Singleton.id).all()
    return jsonify([s.to_dict() for s in singletons])


@singletons_bp.route("/patients/<int:patient_id>/singletons", methods=["POST"])
def create_singleton(patient_id):
    """Create a new singleton finding for a patient."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    data = request.get_json()
    singleton = Singleton(patient_id=patient_id)
    for field in SINGLETON_FIELDS:
        if field in data:
            val = _normalize_variant_field(field, data[field])
            setattr(singleton, field, val)
    db.session.add(singleton)
    db.session.commit()
    return jsonify(singleton.to_dict()), 201


@singletons_bp.route("/singletons/<int:singleton_id>", methods=["PUT"])
def update_singleton(singleton_id):
    """Update an existing singleton finding."""
    singleton = db.session.get(Singleton, singleton_id)
    if not singleton:
        abort(404)
    data = request.get_json()
    for field in SINGLETON_FIELDS:
        if field in data:
            val = _normalize_variant_field(field, data[field])
            setattr(singleton, field, val)
    db.session.commit()
    return jsonify(singleton.to_dict())


@singletons_bp.route("/singletons/<int:singleton_id>", methods=["DELETE"])
def delete_singleton(singleton_id):
    """Delete a singleton finding."""
    singleton = db.session.get(Singleton, singleton_id)
    if not singleton:
        abort(404)
    db.session.delete(singleton)
    db.session.commit()
    return jsonify({"message": "Singleton deleted"}), 200


# ── XLSX upload ──────────────────────────────────────────────────────────

@singletons_bp.route(
    "/patients/<int:patient_id>/upload/singleton", methods=["POST"]
)
def upload_singleton_xlsx(patient_id):
    """Import singleton variant findings from an XLSX file.

    Each row becomes a new Singleton record linked to the patient.
    The first rows that look like headers are automatically detected and
    column names are fuzzy-mapped to DB fields.
    """
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"error": "Only .xlsx / .xls files are accepted"}), 400

    mismatch_error = variant_upload_id_mismatch_message(f, patient, expect_trio=False)
    if mismatch_error:
        return jsonify({"error": mismatch_error}), 400

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
    patient_dir = os.path.join(variant_dir, patient.lab_number, "singleton")
    os.makedirs(patient_dir, exist_ok=True)

    safe_name = secure_filename(f.filename) or "variant.xlsx"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stored_filename = f"{timestamp}_{safe_name}"
    dest = os.path.join(patient_dir, stored_filename)

    f.stream.seek(0)
    f.save(dest)

    relative_path = os.path.join(patient.lab_number, "singleton", stored_filename)
    file_size = os.path.getsize(dest)

    count = 0
    try:
        for row in rows:
            singleton = Singleton(patient_id=patient_id)
            normalized = normalize_variant_row(row, SINGLETON_FIELDS)
            if normalized:
                for field, val in normalized.items():
                    setattr(singleton, field, val)
                db.session.add(singleton)
                count += 1

        upload_record = VariantUpload(
            patient_id=patient_id,
            file_type="singleton",
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

    return jsonify({"message": f"Imported {count} singleton variant(s)", "count": count}), 201
