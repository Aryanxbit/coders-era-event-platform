import os
from flask import Flask, render_template, jsonify
from app.config import config_by_name
from app import db

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app
