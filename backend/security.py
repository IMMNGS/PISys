"""Session-based authentication and audit helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps

from flask import current_app, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.models import AccessLog, AuthUser, db


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def load_current_user() -> AuthUser | None:
    user_id = session.get("user_id")
    user = db.session.get(AuthUser, user_id) if user_id else None
    g.current_user = user
    return user


def auth_enabled() -> bool:
    if current_app.config.get("TESTING"):
        return False
    return AuthUser.query.count() > 0


def current_user() -> AuthUser | None:
    user = getattr(g, "current_user", None)
    if user is None:
        return load_current_user()
    return user


def require_login():
    if not auth_enabled():
        return None
    if current_user() is None:
        return jsonify({"error": "Authentication required"}), 401
    return None


def require_admin():
    denial = require_login()
    if denial is not None:
        return denial
    user = current_user()
    if not user or not user.is_admin:
        return jsonify({"error": "Administrator access required"}), 403
    return None


def login_user(user: AuthUser):
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    user.last_login_at = datetime.now(timezone.utc)
    db.session.add(user)
    db.session.commit()


def logout_user():
    session.pop("user_id", None)


def seed_default_admin_user():
    """Create a local administrator account when no users exist yet."""
    if current_app.config.get("TESTING"):
        return None
    if AuthUser.query.count() > 0:
        return AuthUser.query.filter_by(role="admin").first()

    username = current_app.config.get("DEFAULT_ADMIN_USERNAME") or current_app.config.get("ADMIN_USERNAME") or "admin"
    password = current_app.config.get("DEFAULT_ADMIN_PASSWORD") or current_app.config.get("ADMIN_PASSWORD") or "admin12345"
    full_name = current_app.config.get("DEFAULT_ADMIN_FULL_NAME") or current_app.config.get("ADMIN_FULL_NAME") or "Administrator"

    user = AuthUser(
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    current_app.logger.warning("Seeded default admin account '%s'. Override via ADMIN_USERNAME/ADMIN_PASSWORD.", username)
    return user


def _safe_target_from_request() -> str:
    path = request.path or ""
    view_args = request.view_args or {}

    if path.startswith("/api/patients/"):
        patient_id = view_args.get("patient_id")
        if patient_id is not None:
            suffix = path.split(f"/{patient_id}", 1)[-1].strip("/")
            if suffix:
                return f"patient:{patient_id} {suffix}"
            return f"patient:{patient_id}"

    if path == "/api/patients":
        search = (request.args.get("search") or "").strip()
        return f"patients list" + (f" search={search[:40]}" if search else "")

    if path == "/api/patients/list":
        parts = []
        for key in ("lab_number", "im_lab_number", "name", "sex", "age", "type_of_test"):
            value = (request.args.get(key) or "").strip()
            if value:
                parts.append(f"{key}={value[:30]}")
        return "patient table" + (f" [{', '.join(parts)}]" if parts else "")

    if path.startswith("/api/report/"):
        payload = request.get_json(silent=True) or {}
        lab_number = str(payload.get("lab_number") or "").strip()
        test_type = str(payload.get("test_type") or "").strip()
        bits = ["report"]
        if lab_number:
            bits.append(f"lab={lab_number}")
        if test_type:
            bits.append(f"type={test_type}")
        return " ".join(bits)

    if path.startswith("/api/upload"):
        return "upload"

    if path.startswith("/api/local-llm"):
        return "local_llm"

    if path.startswith("/api/admin/"):
        return path.removeprefix("/api/admin/") or "admin"

    return path.removeprefix("/api/") or path


def audit_action_for_method(method: str) -> str:
    return {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method.upper(), method.lower())


def should_audit_request() -> bool:
    if not request.path.startswith("/api/"):
        return False
    if request.endpoint in {"auth.login", "auth.me", "auth.logout"}:
        return False
    if request.endpoint and request.endpoint.startswith("admin."):
        return False
    return auth_enabled() and current_user() is not None


def log_access(response):
    user = current_user()
    if not user or not should_audit_request():
        return response
    if response.status_code >= 400:
        return response

    entry = AccessLog(
        user_id=user.id,
        username=user.username,
        action=audit_action_for_method(request.method),
        target=_safe_target_from_request(),
        method=request.method,
        path=request.path,
        status_code=response.status_code,
        remote_addr=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=(request.headers.get("User-Agent") or "")[:255] or None,
    )
    db.session.add(entry)
    db.session.commit()
    return response


def audit_event(user: AuthUser | None, action: str, target: str, status_code: int = 200):
    if not user:
        return None
    entry = AccessLog(
        user_id=user.id,
        username=user.username,
        action=action,
        target=target,
        method=request.method if request else "",
        path=request.path if request else "",
        status_code=status_code,
        remote_addr=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=(request.headers.get("User-Agent") or "")[:255] or None,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def serialize_user(user: AuthUser | None):
    return user.to_dict() if user else None


def admin_guard(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        denial = require_admin()
        if denial is not None:
            return denial
        return fn(*args, **kwargs)

    return wrapper


def login_guard(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        denial = require_login()
        if denial is not None:
            return denial
        return fn(*args, **kwargs)

    return wrapper
