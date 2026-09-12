import os
from datetime import datetime
from flask import Flask, render_template, jsonify
from app.config import config_by_name
from app import db


# ---------------------------------------------------------------------------
# Template filter helpers
# ---------------------------------------------------------------------------

def _parse_dt(value):
    """Parse an SQLite datetime string into a datetime object."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None


def format_dt(value, style="full"):
    """
    Render an SQLite datetime string as human-friendly IST text.
    Styles:
      full  → "Friday, 25 Sep 2026 · 9:00 AM IST"
      short → "25 Sep 2026, 9:00 AM"
      date  → "25 September 2026"
      time  → "9:00 AM IST"
      iso   → unchanged passthrough (for machine use)
    """
    dt = _parse_dt(value)
    if dt is None:
        return value or "—"

    # Windows-safe: use %I then strip leading zero manually
    hour_min = dt.strftime("%I:%M %p").lstrip("0")
    day = str(dt.day)  # no leading zero

    if style == "full":
        return f"{dt.strftime('%A')}, {day} {dt.strftime('%b %Y')} · {hour_min} IST"
    if style == "short":
        return f"{day} {dt.strftime('%b %Y')}, {hour_min}"
    if style == "date":
        return f"{day} {dt.strftime('%B %Y')}"
    if style == "time":
        return f"{hour_min} IST"
    return str(value)


def mode_label(value):
    """Map event mode values to human-friendly display strings."""
    mapping = {
        "offline": "In-Person",
        "online": "Online",
        "hybrid": "Hybrid",
    }
    return mapping.get(str(value).lower(), str(value).capitalize())


def create_app(config_name=None):
    """
    Application factory pattern for Flask.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize SQLite database teardown
    db.init_app(app)

    # Register Jinja2 template filters
    app.jinja_env.filters["format_dt"] = format_dt
    app.jinja_env.filters["mode_label"] = mode_label

    # Health check route
    @app.route("/api/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Coders Era Event Platform",
            "environment": config_name
        })

    # Placeholder home route for Phase 1 testing
    @app.route("/")
    def index():
        database = db.get_db()
        events = database.execute(
            "SELECT * FROM events WHERE status = 'published' ORDER BY start_time ASC"
        ).fetchall()
        return render_template("index.html", events=events)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.public_routes import public_bp
    from app.routes.checkin_routes import checkin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(checkin_bp)

    return app
