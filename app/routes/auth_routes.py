from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.services.auth_service import authenticate_user

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")

def login_required(f):
    """Decorator to require an active organizer/volunteer session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access the organizer control portal.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to restrict routes by user role (e.g. admin, organizer, volunteer)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            
            user_role = session.get("user_role", "volunteer")
            if user_role not in allowed_roles:
                # Return JSON 403 for API endpoints, JSON requests, and data exports
                is_api_route = (
                    request.is_json or 
                    request.path.startswith("/admin/api/") or 
                    request.path.startswith("/api/") or 
                    request.path.endswith(".csv") or
                    (request.path.startswith("/admin/participants/") and request.path != "/admin/participants")
                )
                if is_api_route:
                    from flask import jsonify
                    return jsonify({"error": "Forbidden: Organizer access required"}), 403

                flash("Access denied: Organizer permissions required.", "danger")
                if user_role == "volunteer":
                    return redirect(url_for("checkin.scanner_view"))
                return redirect(url_for("admin.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Organizer and volunteer login portal."""
    if session.get("user_id"):
        if session.get("user_role") == "volunteer":
            return redirect(url_for("checkin.scanner_view"))
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(email, password)
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["user_uuid"] = user["uuid"]
            session["user_email"] = user["email"]
            session["user_name"] = user["full_name"]
            session["user_role"] = user["role"]
            session.permanent = True

            flash(f"Welcome, {user['full_name']}!", "success")

            # Default destination by role if next was not explicitly requested or was default
            requested_next = request.args.get("next")
            if requested_next:
                return redirect(requested_next)

            if user["role"] == "volunteer":
                return redirect(url_for("checkin.scanner_view"))
            else:
                return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")

    return render_template("admin/login.html")

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    """Clear session and log out."""
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
