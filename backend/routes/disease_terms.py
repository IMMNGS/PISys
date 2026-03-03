"""Free-text disease term routes.

Used for disease descriptors that cannot be mapped to canonical HPO terms.
"""

from flask import Blueprint, abort, jsonify, request

from backend.models import db, DiseaseTerm, HPOTerm, Patient


disease_terms_bp = Blueprint("disease_terms", __name__)


def _normalize_term(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _term_label_hpo(term: HPOTerm) -> str:
    return f"HPO — {term.hpo_id} — {term.term_name}"


def _term_label_disease(term: DiseaseTerm) -> str:
    return f"Free text — {term.term_name}"


@disease_terms_bp.route("/disease_terms", methods=["GET"])
def get_disease_terms():
    """Return disease terms with optional search (paginated)."""
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = DiseaseTerm.query
    if search:
        like = f"%{search}%"
        query = query.filter(DiseaseTerm.term_name.ilike(like))

    query = query.order_by(DiseaseTerm.term_name)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "items": [t.to_dict() for t in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@disease_terms_bp.route("/disease_terms/options", methods=["GET"])
def get_disease_term_options():
    """Lightweight endpoint for dropdowns.

    Query params: search, limit (default 20), offset (default 0)
    Returns: {items: [{id, term_name}], total}
    """
    search = request.args.get("search", "").strip()
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    query = DiseaseTerm.query
    if search:
        like = f"%{search}%"
        query = query.filter(DiseaseTerm.term_name.ilike(like))

    query = query.order_by(DiseaseTerm.term_name)
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    items = [{"id": t.id, "term_name": t.term_name} for t in rows]
    return jsonify({"items": items, "total": total})


@disease_terms_bp.route("/disease_terms", methods=["POST"])
def create_disease_term():
    """Create a free-text disease term (deduplicated by normalized text)."""
    data = request.get_json() or {}
    term_name = str(data.get("term_name", "")).strip()
    notes = data.get("notes")

    if not term_name:
        return jsonify({"error": "term_name is required"}), 400

    normalized = _normalize_term(term_name)
    existing = DiseaseTerm.query.filter_by(normalized_name=normalized).first()
    if existing:
        if notes is not None and str(notes).strip() and not existing.notes:
            existing.notes = str(notes).strip()
            db.session.commit()
        return jsonify(existing.to_dict()), 200

    row = DiseaseTerm(
        term_name=term_name,
        normalized_name=normalized,
        notes=str(notes).strip() if notes is not None and str(notes).strip() else None,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@disease_terms_bp.route("/terms/free_text", methods=["POST"])
def upsert_free_text_term():
    """Create a free-text disease term (or return existing one) for quick assignment UI."""
    data = request.get_json() or {}
    term_name = str(data.get("term_name", "")).strip()
    notes = data.get("notes")

    if not term_name:
        return jsonify({"error": "term_name is required"}), 400

    normalized = _normalize_term(term_name)
    row = DiseaseTerm.query.filter_by(normalized_name=normalized).first()
    if not row:
        row = DiseaseTerm(
            term_name=term_name,
            normalized_name=normalized,
            notes=str(notes).strip() if notes is not None and str(notes).strip() else None,
        )
        db.session.add(row)
        db.session.commit()
    elif notes is not None and str(notes).strip() and not row.notes:
        row.notes = str(notes).strip()
        db.session.commit()

    return jsonify({
        "id": -row.id,
        "term_id": row.id,
        "term_type": "disease",
        "label": _term_label_disease(row),
    }), 200


@disease_terms_bp.route("/terms/options", methods=["GET"])
def get_combined_term_options():
    """Combined term options for one-search UI.

    Returns HPO and free-text disease terms in one paginated list.
    HPO IDs are positive. Disease-term IDs are negative.
    """
    search = request.args.get("search", "").strip()
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    hpo_query = HPOTerm.query
    disease_query = DiseaseTerm.query
    if search:
        like = f"%{search}%"
        hpo_query = hpo_query.filter(
            db.or_(
                HPOTerm.hpo_id.ilike(like),
                HPOTerm.term_name.ilike(like),
                HPOTerm.synonyms.ilike(like),
            )
        )
        disease_query = disease_query.filter(DiseaseTerm.term_name.ilike(like))

    hpo_query = hpo_query.order_by(HPOTerm.hpo_id)
    disease_query = disease_query.order_by(DiseaseTerm.term_name)

    hpo_total = hpo_query.count()
    disease_total = disease_query.count()
    total = hpo_total + disease_total

    items = []
    if offset < hpo_total:
        hpo_rows = hpo_query.offset(offset).limit(limit).all()
        items.extend([
            {
                "id": t.id,
                "term_type": "hpo",
                "term_id": t.id,
                "hpo_id": t.hpo_id,
                "term_name": t.term_name,
                "label": _term_label_hpo(t),
            }
            for t in hpo_rows
        ])
        remaining = limit - len(hpo_rows)
        if remaining > 0:
            disease_rows = disease_query.limit(remaining).all()
            items.extend([
                {
                    "id": -t.id,
                    "term_type": "disease",
                    "term_id": t.id,
                    "term_name": t.term_name,
                    "label": _term_label_disease(t),
                }
                for t in disease_rows
            ])
    else:
        disease_offset = max(0, offset - hpo_total)
        disease_rows = disease_query.offset(disease_offset).limit(limit).all()
        items.extend([
            {
                "id": -t.id,
                "term_type": "disease",
                "term_id": t.id,
                "term_name": t.term_name,
                "label": _term_label_disease(t),
            }
            for t in disease_rows
        ])

    return jsonify({"items": items, "total": total})


@disease_terms_bp.route("/patients/<int:patient_id>/disease_terms", methods=["GET"])
def get_patient_disease_terms(patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)
    return jsonify([t.to_dict() for t in patient.disease_terms])


@disease_terms_bp.route("/patients/assign_disease_terms", methods=["POST"])
def assign_disease_terms_to_patients():
    """Assign one or more free-text disease terms to one or more patients.

    Body: {"patient_ids": [1,2], "disease_term_ids": [4,5]}
    """
    data = request.get_json() or {}
    patient_ids = data.get("patient_ids", [])
    disease_term_ids = data.get("disease_term_ids", [])

    patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
    terms = DiseaseTerm.query.filter(DiseaseTerm.id.in_(disease_term_ids)).all()
    terms_map = {t.id: t for t in terms}

    added = 0
    for patient in patients:
        existing_ids = {t.id for t in patient.disease_terms}
        for term_id in disease_term_ids:
            if term_id not in existing_ids and term_id in terms_map:
                patient.disease_terms.append(terms_map[term_id])
                added += 1

    db.session.commit()
    return jsonify({
        "message": f"Assigned {added} disease term(s) across {len(patients)} patient(s)."
    }), 200


@disease_terms_bp.route("/patients/assign_terms", methods=["POST"])
def assign_terms_to_patients():
    """Assign combined term IDs to patients.

    Body: {"patient_ids": [1,2], "term_ids": [12, -3]}
      - positive id  => hpo_terms.id
      - negative id  => disease_terms.id (absolute value)
    """
    data = request.get_json() or {}
    patient_ids = data.get("patient_ids", [])
    term_ids = data.get("term_ids", [])

    hpo_ids = [int(i) for i in term_ids if isinstance(i, int) and i > 0]
    disease_ids = [abs(int(i)) for i in term_ids if isinstance(i, int) and i < 0]

    patients = Patient.query.filter(Patient.id.in_(patient_ids)).all()
    hpo_terms = HPOTerm.query.filter(HPOTerm.id.in_(hpo_ids)).all() if hpo_ids else []
    disease_terms = (
        DiseaseTerm.query.filter(DiseaseTerm.id.in_(disease_ids)).all()
        if disease_ids else []
    )

    hpo_map = {t.id: t for t in hpo_terms}
    disease_map = {t.id: t for t in disease_terms}

    hpo_added = 0
    disease_added = 0
    for patient in patients:
        existing_hpo_ids = {t.id for t in patient.hpo_terms}
        for hpo_id in hpo_ids:
            if hpo_id not in existing_hpo_ids and hpo_id in hpo_map:
                patient.hpo_terms.append(hpo_map[hpo_id])
                hpo_added += 1

        existing_disease_ids = {t.id for t in patient.disease_terms}
        for disease_id in disease_ids:
            if disease_id not in existing_disease_ids and disease_id in disease_map:
                patient.disease_terms.append(disease_map[disease_id])
                disease_added += 1

    db.session.commit()
    return jsonify({
        "message": (
            f"Assigned {hpo_added} HPO term(s) and {disease_added} free-text term(s) "
            f"across {len(patients)} patient(s)."
        ),
        "hpo_added": hpo_added,
        "disease_added": disease_added,
    }), 200


@disease_terms_bp.route(
    "/patients/<int:patient_id>/disease_terms/<int:term_id>", methods=["DELETE"]
)
def remove_disease_term_from_patient(patient_id, term_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        abort(404)

    term = db.session.get(DiseaseTerm, term_id)
    if not term:
        abort(404)

    if term in patient.disease_terms:
        patient.disease_terms.remove(term)
        db.session.commit()

    return jsonify({"message": "Disease term removed from patient"}), 200
