import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.app import create_app
from backend.models import db, HPOTerm

def seed_hpo_terms():
    app = create_app('development')
    with app.app_context():
        if HPOTerm.query.first():
            print("HPO terms already exist. Skipping seed.", flush=True)
            return

        print("Seeding initial HPO terms into database (this may take a minute)...", flush=True)
        try:
            from pyhpo import Ontology
            _ = Ontology()
            terms = []
            for term in Ontology:
                terms.append(HPOTerm(
                    hpo_id=term.id,
                    term_name=term.name,
                    definition=term.definition or None,
                    synonyms=", ".join(term.synonym) if term.synonym else None,
                ))
            db.session.bulk_save_objects(terms)
            db.session.commit()
            print(f"Seeded {len(terms)} HPO terms.", flush=True)
        except ImportError:
            print("Missing pyhpo library. Install pyhpo.", flush=True)
        except Exception as e:
            db.session.rollback()
            print(f"Failed to seed HPO terms: {e}", flush=True)

if __name__ == '__main__':
    seed_hpo_terms()
