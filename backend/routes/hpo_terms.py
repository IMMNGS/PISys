"""HPO term routes."""

from flask import Blueprint, jsonify, request

from backend.models import db, HPOTerm

hpo_bp = Blueprint("hpo_terms", __name__)


@hpo_bp.route("/hpo_terms/refresh", methods=["POST"])
def refresh_hpo_terms():
    """Pull latest HPO terms from pyhpo and upsert into the database."""
    try:
        from pyhpo import Ontology

        _ = Ontology()

        existing = {t.hpo_id: t for t in HPOTerm.query.all()}
        added = 0
        updated = 0

        for term in Ontology:
            hpo_id = term.id
            term_name = term.name
            definition = term.definition or None
            synonyms = ", ".join(term.synonym) if term.synonym else None

            if hpo_id in existing:
                row = existing[hpo_id]
                changed = False
                if row.term_name != term_name:
                    row.term_name = term_name
                    changed = True
                if row.definition != definition:
                    row.definition = definition
                    changed = True
                if row.synonyms != synonyms:
                    row.synonyms = synonyms
                    changed = True
                if changed:
                    updated += 1
            else:
                db.session.add(HPOTerm(
                    hpo_id=hpo_id,
                    term_name=term_name,
                    definition=definition,
                    synonyms=synonyms,
                ))
                added += 1

        db.session.commit()
        return jsonify({
            "message": f"Refresh complete. Added {added}, updated {updated} HPO terms.",
            "added": added,
            "updated": updated,
        }), 200

    except ImportError:
        return jsonify({"error": "pyhpo is not installed. Run: pip install pyhpo"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@hpo_bp.route("/hpo_terms", methods=["GET"])
def get_hpo_terms():
    """Return HPO terms with optional search (paginated)."""
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = HPOTerm.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                HPOTerm.hpo_id.ilike(like),
                HPOTerm.term_name.ilike(like),
                HPOTerm.synonyms.ilike(like),
            )
        )
    query = query.order_by(HPOTerm.hpo_id)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "items": [t.to_dict() for t in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@hpo_bp.route("/hpo_terms/<int:term_id>", methods=["GET"])
def get_hpo_term(term_id):
    term = HPOTerm.query.get_or_404(term_id)
    return jsonify(term.to_dict())
