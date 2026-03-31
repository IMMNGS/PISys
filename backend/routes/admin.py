"""Administrator monitoring routes."""

from flask import Blueprint, jsonify, request

from backend.models import AccessLog, AuthUser, db
from backend.security import admin_guard, audit_event, current_user, hash_password

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/users", methods=["GET"])
@admin_guard
def list_users():
    users = AuthUser.query.order_by(AuthUser.id.asc()).all()
    return jsonify({"items": [u.to_dict() for u in users]})


@admin_bp.route("/admin/users", methods=["POST"])
@admin_guard
def create_user():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    role = str(data.get("role") or "user").strip().lower() or "user"
    full_name = str(data.get("full_name") or "").strip() or None

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if role not in {"admin", "user"}:
        return jsonify({"error": "role must be admin or user"}), 400
    if AuthUser.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = AuthUser(
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()

    audit_event(current_user(), "create", f"user:{username}", status_code=201)
    return jsonify({"message": "User created", "user": user.to_dict()}), 201


@admin_bp.route("/admin/audit-logs", methods=["GET"])
@admin_guard
def list_audit_logs():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    username = request.args.get("username", "").strip()
    action = request.args.get("action", "").strip()
    target = request.args.get("target", "").strip()

    query = AccessLog.query
    if username:
        query = query.filter(AccessLog.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(AccessLog.action == action)
    if target:
        query = query.filter(AccessLog.target.ilike(f"%{target}%"))

    total = query.count()
    items = (
        query.order_by(AccessLog.created_at.desc(), AccessLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items], "total": total})
