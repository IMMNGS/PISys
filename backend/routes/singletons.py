"""Singleton (variant) CRUD and XLSX import routes."""

from flask import Blueprint, jsonify, request

from backend.models import db, Patient, Singleton
from backend.routes.helpers import _parse_xlsx_rows, SINGLETON_FIELDS

singletons_bp = Blueprint("singletons", __name__)


@singletons_bp.route("/patients/<int:patient_id>/singletons", methods=["GET"])
def get_patient_singletons(patient_id):
    """List all singleton findings for a patient."""
    Patient.query.get_or_404(patient_id)
    singletons = Singleton.query.filter_by(patient_id=patient_id).all()
    return jsonify([s.to_dict() for s in singletons])


@singletons_bp.route("/patients/<int:patient_id>/singletons", methods=["POST"])
def create_singleton(patient_id):
    """Create a new singleton finding for a patient."""
    Patient.query.get_or_404(patient_id)
    data = request.get_json()
    singleton = Singleton(patient_id=patient_id)
    for field in SINGLETON_FIELDS:
        if field in data:
            setattr(singleton, field, data[field])
    db.session.add(singleton)
    db.session.commit()
    return jsonify(singleton.to_dict()), 201


@singletons_bp.route("/singletons/<int:singleton_id>", methods=["GET"])
def get_singleton(singleton_id):
    """Get a single singleton finding by ID."""
    singleton = Singleton.query.get_or_404(singleton_id)
    return jsonify(singleton.to_dict())


@singletons_bp.route("/singletons/<int:singleton_id>", methods=["PUT"])
def update_singleton(singleton_id):
    """Update a singleton finding."""
    singleton = Singleton.query.get_or_404(singleton_id)
    data = request.get_json()
    for field in SINGLETON_FIELDS:
        if field in data:
            setattr(singleton, field, data[field])
    db.session.commit()
    return jsonify(singleton.to_dict())


@singletons_bp.route("/singletons/<int:singleton_id>", methods=["DELETE"])
def delete_singleton(singleton_id):
    """Delete a singleton finding."""
    singleton = Singleton.query.get_or_404(singleton_id)
    db.session.delete(singleton)
    db.session.commit()
    return jsonify({"message": "Singleton deleted"}), 200


# ── XLSX Import ──────────────────────────────────────────────────────────

@singletons_bp.route("/patients/<int:patient_id>/upload/singleton", methods=["POST"])
def upload_singleton_xlsx(patient_id):
    """Import singleton variants from an XLSX file.

    Column headers in the XLSX should match the Singleton model fields
    (case-insensitive, spaces → underscores).  Unrecognised columns are
    silently ignored.
    """
    Patient.query.get_or_404(patient_id)

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files are accepted"}), 400

    rows = _parse_xlsx_rows(f)
    added = 0
    for row in rows:
        s = Singleton(patient_id=patient_id)
        for field in SINGLETON_FIELDS:
            if field in row and row[field] is not None:
                setattr(s, field, row[field])
        db.session.add(s)
        added += 1

    db.session.commit()
    return jsonify({"message": f"Imported {added} singleton variant(s)", "count": added}), 201
