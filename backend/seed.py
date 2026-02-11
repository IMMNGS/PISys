"""
Seed the database with HPO terms from all_hpo_terms.csv.

This is production-safe — it only loads reference data (HPO terms),
never mock patients. For mock data, use generate_mock_data.py.

Usage:
    python -m backend.seed
"""

import csv
import os

from backend.app import create_app
from backend.models import db, HPOTerm


def seed_hpo_terms(csv_path: str):
    """Load HPO terms from CSV into the database (skip existing)."""
    existing = {t.hpo_id for t in HPOTerm.query.with_entities(HPOTerm.hpo_id).all()}

    terms_to_add = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hpo_id = row["hpo_id"].strip()
            if hpo_id in existing:
                continue
            terms_to_add.append(HPOTerm(
                hpo_id=hpo_id,
                term_name=row["term_name"].strip(),
                definition=row.get("definition", "").strip() or None,
                synonyms=row.get("synonyms", "").strip() or None,
            ))

    if terms_to_add:
        db.session.bulk_save_objects(terms_to_add)
        db.session.commit()
        print(f"  ✓ Inserted {len(terms_to_add)} HPO terms.")
    else:
        print("  • HPO terms already loaded — skipping.")


def main():
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "all_hpo_terms.csv")

    with app.app_context():
        print("Seeding database …")
        seed_hpo_terms(csv_path)
        print("Done.")


if __name__ == "__main__":
    main()
