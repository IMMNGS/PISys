import os
import logging

import pymysql
from flask import Flask, request, send_from_directory
from flask_cors import CORS

from backend.config import config as config_map
from backend.models import db

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


def _ensure_databases(cfg):
    """Create the MySQL database if it doesn't exist yet."""
    user = cfg.MYSQL_USER
    password = cfg.MYSQL_PASSWORD
    host = cfg.MYSQL_HOST
    port = int(cfg.MYSQL_PORT)

    conn = pymysql.connect(host=host, port=port, user=user, password=password)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg.MYSQL_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
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
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        allowed = os.environ.get("CORS_ORIGINS", "").split(",")
        allowed = [o.strip() for o in allowed if o.strip()]
        if allowed:
            CORS(app, resources={r"/api/*": {"origins": allowed}})

    # Initialise extensions
    db.init_app(app)

    # Prevent browsers from caching API responses
    @app.after_request
    def _no_cache_api(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

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

    return app
