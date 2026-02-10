"""Trio (variant) CRUD and XLSX import routes."""

from flask import Blueprint, jsonify, request

from backend.models import db, Patient, Trio
from backend.routes.helpers import _parse_xlsx_rows, TRIO_FIELDS

trios_bp = Blueprint("trios", __name__)


@trios_bp.route("/patients/<int:patient_id>/trios", methods=["GET"])
def get_patient_trios(patient_id):
    """List all trio findings for a patient."""
    Patient.query.get_or_404(patient_id)
    trios = Trio.query.filter_by(patient_id=patient_id).all()
    return jsonify([t.to_dict() for t in trios])


@trios_bp.route("/patients/<int:patient_id>/trios", methods=["POST"])
def create_trio(patient_id):
    Patient.query.get_or_404(patient_id)
    data = request.get_json()
    trio = Trio(patient_id=patient_id)
    for field in TRIO_FIELDS:
        if field in data:
            setattr(trio, field, data[field])
    db.session.add(trio)
    db.session.commit()
    return jsonify(trio.to_dict()), 201


@trios_bp.route("/trios/<int:trio_id>", methods=["PUT"])
def update_trio(trio_id):
    trio = Trio.query.get_or_404(trio_id)
    data = request.get_json()
    for field in TRIO_FIELDS:
        if field in data:
            setattr(trio, field, data[field])
    db.session.commit()
    return jsonify(trio.to_dict())


@trios_bp.route("/trios/<int:trio_id>", methods=["DELETE"])
def delete_trio(trio_id):
    trio = Trio.query.get_or_404(trio_id)
    db.session.delete(trio)
    db.session.commit()
    return jsonify({"message": "Trio deleted"}), 200


# ── XLSX Import ──────────────────────────────────────────────────────────

@trios_bp.route("/patients/<int:patient_id>/upload/trio", methods=["POST"])
def upload_trio_xlsx(patient_id):
    """Import trio variants from an XLSX file."""
    Patient.query.get_or_404(patient_id)

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files are accepted"}), 400

    rows = _parse_xlsx_rows(f)
    added = 0
    for row in rows:
        t = Trio(patient_id=patient_id)
        for field in TRIO_FIELDS:
            if field in row and row[field] is not None:
                setattr(t, field, row[field])
        db.session.add(t)
        added += 1

    db.session.commit()
    return jsonify({"message": f"Imported {added} trio variant(s)", "count": added}), 201
