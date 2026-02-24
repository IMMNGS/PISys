"""Singleton variant CRUD and XLSX upload routes."""

from flask import Blueprint, abort, jsonify, request

from backend.models import db, Patient, Singleton
from backend.routes.helpers import (
    SINGLETON_FIELDS,
    _parse_variant_xlsx_rows,
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
            val = data[field]
            # Handle igv_review boolean
            if field == "igv_review" and isinstance(val, str):
                val = val.lower() in ("true", "1", "yes")
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
            val = data[field]
            if field == "igv_review" and isinstance(val, str):
                val = val.lower() in ("true", "1", "yes")
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

    rows = _parse_variant_xlsx_rows(f)
    if not rows:
        return jsonify({"error": "File is empty or has no data rows"}), 400

    count = 0
    for row in rows:
        singleton = Singleton(patient_id=patient_id)
        has_data = False
        for field in SINGLETON_FIELDS:
            val = row.get(field)
            if val is None:
                continue
            # Convert NaN-like values
            if isinstance(val, float) and str(val).lower() == "nan":
                continue
            has_data = True
            if field == "igv_review":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                elif isinstance(val, (int, float)):
                    val = bool(val)
            setattr(singleton, field, val)
        if has_data:
            db.session.add(singleton)
            count += 1

    db.session.commit()
    return jsonify({"message": f"Imported {count} singleton variant(s)", "count": count}), 201
