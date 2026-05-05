import os
import logging

import pymysql
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
    """Create the MySQL database if it doesn't exist yet."""
    user = cfg.MYSQL_USER
    password = cfg.MYSQL_PASSWORD
    host = cfg.MYSQL_HOST
    port = int(cfg.MYSQL_PORT)
    db_name = cfg.MYSQL_DB
    escaped_db_name = db_name.replace("`", "``")

    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        port=port,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{escaped_db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()


def _sync_missing_columns(app):
    """Auto-add missing columns to existing MySQL tables.

    This project does not use Alembic, so when models gain new columns we
    detect them at startup and issue ``ALTER TABLE ADD COLUMN`` statements.
    Only MySQL is supported for this helper; SQLite tests use :memory:.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.dialects.mysql.base import MySQLTypeCompiler

    dialect_name = db.engine.dialect.name
    if dialect_name != "mysql":
        return

    inspector = inspect(db.engine)
    conn = db.engine.connect()
    compiler = MySQLTypeCompiler(db.engine.dialect)

    try:
        for table_name, table in db.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                # Let SQLAlchemy compile the type for MySQL.
                mysql_type = compiler.process(col.type)
                nullable = "NULL" if col.nullable else "NOT NULL"

                # Simple scalar defaults only; skip callables.
                default_clause = ""
                if col.default is not None:
                    arg = getattr(col.default, "arg", None)
                    if arg is not None and not callable(arg):
                        if isinstance(arg, bool):
                            default_clause = f" DEFAULT {1 if arg else 0}"
                        elif isinstance(arg, (int, float)):
                            default_clause = f" DEFAULT {arg}"
                        elif isinstance(arg, str):
                            default_clause = f" DEFAULT '{arg.replace(chr(39), chr(39)+chr(39))}'"

                stmt = (
                    f"ALTER TABLE `{table_name}` "
                    f"ADD COLUMN `{col.name}` {mysql_type} {nullable}{default_clause}"
                )
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                    app.logger.info("Added missing column: %s.%s", table_name, col.name)
                except Exception as exc:
                    app.logger.warning(
                        "Could not add column %s.%s: %s", table_name, col.name, exc
                    )
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
        try:
            db.create_all()
        except Exception as exc:
            # MySQL error 1050 = "Table already exists"
            # This happens when multiple Gunicorn workers race on startup.
            # We only ignore that specific error; everything else is fatal.
            orig = getattr(exc, "orig", None)
            if orig and hasattr(orig, "args") and len(orig.args) >= 2 and orig.args[0] == 1050:
                app.logger.warning(
                    "Table already exists (multi-worker race on startup): %s", orig.args[1]
                )
            else:
                raise
        _sync_missing_columns(app)
        seed_default_admin_user()

    return app
