"""Patient CRUD and bulk-import routes."""

from flask import Blueprint, jsonify, request

from backend.models import db, HPOTerm, Patient
from backend.routes.helpers import (
    _patient_to_dict, _parse_xlsx_rows,
    PATIENT_FIELDS, DATE_FIELDS,
)

patients_bp = Blueprint("patients", __name__)

_FULL = dict(include_hpo=True, include_singletons=True,
             include_trios=True, include_vcf_files=True)


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
                Patient.name.ilike(like),
                Patient.type_of_test.ilike(like),
                Patient.type_of_findings.ilike(like),
                Patient.request_dr.ilike(like),
            )
        )
    query = query.order_by(Patient.id)
    patients = query.all()
    return jsonify([_patient_to_dict(p, **_FULL) for p in patients])


@patients_bp.route("/patients/<int:patient_id>", methods=["GET"])
def get_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return jsonify(_patient_to_dict(patient, **_FULL))


@patients_bp.route("/patients", methods=["POST"])
def create_patient():
    """Create a new patient."""
    data = request.get_json()
    patient = Patient(lab_number=data["lab_number"])
    for field in PATIENT_FIELDS:
        if field != "lab_number" and field in data:
            setattr(patient, field, data[field])
    db.session.add(patient)
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL)), 201


@patients_bp.route("/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    """Update an existing patient."""
    patient = Patient.query.get_or_404(patient_id)
    data = request.get_json()
    for field in PATIENT_FIELDS:
        if field in data:
            setattr(patient, field, data[field])
    db.session.commit()
    return jsonify(_patient_to_dict(patient, **_FULL))


@patients_bp.route("/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.hpo_terms.clear()
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
    for row in rows:
        lab = row.get("lab_number")
        if not lab:
            continue
        lab = str(lab).strip()
        if lab in existing_labs:
            skipped.append(lab)
            continue

        patient = Patient(lab_number=lab)
        for field in PATIENT_FIELDS:
            if field == "lab_number":
                continue
            val = row.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                continue
            if field in DATE_FIELDS and isinstance(val, str):
                try:
                    from datetime import date as _date
                    val = _date.fromisoformat(val)
                except ValueError:
                    pass
            if field == "age" and val is not None:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            setattr(patient, field, val)

        db.session.add(patient)
        existing_labs.add(lab)
        added += 1

    db.session.commit()
    msg = f"Imported {added} patient(s)"
    if skipped:
        msg += f", skipped {len(skipped)} duplicate(s): {', '.join(skipped)}"
    return jsonify({"message": msg, "added": added, "skipped": skipped}), 201


# ── Patient ↔ HPO Assignment ────────────────────────────────────────────

@patients_bp.route("/patients/<int:patient_id>/hpo_terms", methods=["GET"])
def get_patient_hpo_terms(patient_id):
    """List all HPO terms assigned to a patient."""
    patient = Patient.query.get_or_404(patient_id)
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
    patient = Patient.query.get_or_404(patient_id)
    term = HPOTerm.query.get_or_404(term_id)
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
