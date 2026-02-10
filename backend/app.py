import os

import pymysql
from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.config import Config
from backend.models import db

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


def _ensure_databases(config_class):
    """Create the MySQL database if it doesn't exist yet."""
    user = config_class.MYSQL_USER
    password = config_class.MYSQL_PASSWORD
    host = config_class.MYSQL_HOST
    port = int(config_class.MYSQL_PORT)

    conn = pymysql.connect(host=host, port=port, user=user, password=password)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config_class.MYSQL_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIST,
        static_url_path="",
    )
    app.config.from_object(config_class)

    # Allow CORS for local Vite dev server
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialise extensions
    db.init_app(app)

    # Register API blueprint
    from backend.routes.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Serve React SPA — all non-API routes fall through to index.html
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str):
        # If the file exists in dist/ (JS, CSS, assets), serve it
        file_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIST, path)
        # Otherwise serve index.html (React Router handles routing)
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
