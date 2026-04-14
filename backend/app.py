import os
import logging

import psycopg2
from psycopg2 import sql
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.config import config as config_map
from backend.models import db
from backend.security import (
    auth_enabled,
    load_current_user,
    log_access,
    seed_default_admin_user,
    validate_csrf_request,
)

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


def _ensure_databases(cfg):
    """Create the PostgreSQL database if it doesn't exist yet."""
    user = cfg.POSTGRES_USER
    password = cfg.POSTGRES_PASSWORD
    host = cfg.POSTGRES_HOST
    port = int(cfg.POSTGRES_PORT)
    db_name = cfg.POSTGRES_DB

    conn = psycopg2.connect(
        dbname="postgres",
        user=user,
        password=password,
        host=host,
        port=port,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(db_name)))
    finally:
        conn.close()


def create_app(config_name="development"):
    """Application factory.

    Args:
        config_name: one of 'development', 'production', or 'default'.
    """
    config_class = config_map.get(config_name, config_map["default"])

    # Disable Flask's automatic static file handling so that requests
    # for unknown paths (e.g. SPA routes like /patients/123) are routed
    # to the `serve_spa` view which will return `index.html`.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    # Run any config-specific initialisation
    if hasattr(config_class, "init_app"):
        config_class.init_app(app)

    # Configure logging
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    # CORS — restrict in production, allow all in dev
    if app.debug:
        CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    else:
        allowed = os.environ.get("CORS_ORIGINS", "").split(",")
        allowed = [o.strip() for o in allowed if o.strip()]
        if allowed:
            CORS(app, resources={r"/api/*": {"origins": allowed}}, supports_credentials=True)
        else:
            CORS(app, resources={r"/api/*": {"origins": []}}, supports_credentials=True)

    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    if not app.debug:
        app.config.setdefault("SESSION_COOKIE_SECURE", True)

    # Initialise extensions
    db.init_app(app)

    @app.before_request
    def _load_auth_context():
        user = load_current_user()

        if not request.path.startswith("/api/"):
            return None

        public_paths = {"/api/auth/login", "/api/auth/me", "/api/auth/logout"}
        if request.path in public_paths:
            return None

        if not auth_enabled():
            return None

        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        return None

    @app.before_request
    def _protect_csrf():
        if not request.path.startswith("/api/"):
            return None
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        if not auth_enabled():
            return None
        if not validate_csrf_request():
            return jsonify({"error": "CSRF token missing or invalid"}), 403
        return None

    # Prevent browsers from caching API responses
    @app.after_request
    def _no_cache_api(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return log_access(response)

    # Register API blueprints
    from backend.routes import register_blueprints

    register_blueprints(app)

    # Serve React SPA — all non-API routes fall through to index.html
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str):
        file_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIST, path)
        index = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index):
            return send_from_directory(FRONTEND_DIST, "index.html")
        return (
            "<h3>Frontend not built yet.</h3>"
            "<p>Run <code>cd frontend && npm install && npm run build</code> first, "
            "or use <code>npm run dev</code> on port 3000 for development.</p>"
        ), 404

    # Create tables if they don't exist yet
    _ensure_databases(config_class)
    with app.app_context():
        db.create_all()
        seed_default_admin_user()

    return app
