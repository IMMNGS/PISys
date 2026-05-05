"""Route blueprint registration."""

from backend.routes.auth import auth_bp
from backend.routes.admin import admin_bp
from backend.routes.hpo_terms import hpo_bp
from backend.routes.disease_terms import disease_terms_bp
from backend.routes.patients import patients_bp
from backend.routes.singletons import singletons_bp
from backend.routes.trios import trios_bp
from backend.routes.vcf import vcf_bp
from backend.routes.reports import reports_bp
from backend.routes.insights import insights_bp
from backend.routes.qc import qc_bp

ALL_BLUEPRINTS = [
    auth_bp,
    admin_bp,
    hpo_bp,
    disease_terms_bp,
    patients_bp,
    singletons_bp,
    trios_bp,
    vcf_bp,
    reports_bp,
    insights_bp,
    qc_bp,
]


def register_blueprints(app, url_prefix="/api"):
    """Register all API blueprints on the Flask app."""
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp, url_prefix=url_prefix)
