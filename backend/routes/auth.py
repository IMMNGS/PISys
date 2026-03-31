"""Authentication routes."""

from flask import Blueprint, jsonify, request

from backend.models import AuthUser, db
from backend.security import (
    audit_event,
    current_user,
    current_csrf_token,
    hash_password,
    issue_csrf_token,
    login_user,
    logout_user,
    serialize_user,
    verify_password,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/me", methods=["GET"])
def me():
    user = current_user()
    return jsonify({"authenticated": bool(user), "user": serialize_user(user), "csrf_token": current_csrf_token()})


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = AuthUser.query.filter_by(username=username).first()
    if not user or not user.is_active or not verify_password(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user)
    audit_event(user, "login", "session", status_code=200)
    return jsonify({"message": "Logged in", "user": serialize_user(user), "csrf_token": current_csrf_token()})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    user = current_user()
    if user:
        audit_event(user, "logout", "session", status_code=200)
    logout_user()
    return jsonify({"message": "Logged out", "csrf_token": current_csrf_token()})


@auth_bp.route("/auth/change-password", methods=["POST"])
def change_password():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True) or {}
    current_password = str(data.get("current_password") or "")
    new_password = str(data.get("new_password") or "")

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400
    if not verify_password(user.password_hash, current_password):
        return jsonify({"error": "Current password is incorrect"}), 401
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user.password_hash = hash_password(new_password)
    db.session.add(user)
    db.session.commit()
    issue_csrf_token(reset=True)
    audit_event(user, "update", "password", status_code=200)
    return jsonify({"message": "Password updated", "csrf_token": current_csrf_token()})
