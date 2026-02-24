"""Trio variant CRUD and XLSX upload routes."""

from flask import Blueprint, abort, jsonify, request

from backend.models import db, Patient, Trio
from backend.routes.helpers import (
    TRIO_FIELDS,
    _parse_variant_xlsx_rows,
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
            val = data[field]
            if field == "igv_review" and isinstance(val, str):
                val = val.lower() in ("true", "1", "yes")
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
            val = data[field]
            if field == "igv_review" and isinstance(val, str):
                val = val.lower() in ("true", "1", "yes")
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

    count = 0
    for row in rows:
        trio = Trio(patient_id=patient_id)
        has_data = False
        for field in TRIO_FIELDS:
            val = row.get(field)
            if val is None:
                continue
            if isinstance(val, float) and str(val).lower() == "nan":
                continue
            has_data = True
            if field == "igv_review":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                elif isinstance(val, (int, float)):
                    val = bool(val)
            setattr(trio, field, val)
        if has_data:
            db.session.add(trio)
            count += 1

    db.session.commit()
    return jsonify({"message": f"Imported {count} trio variant(s)", "count": count}), 201
