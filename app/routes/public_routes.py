import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from app.db import get_db
from app.services.ticket_service import register_participant, get_ticket_details

public_bp = Blueprint("public", __name__)

@public_bp.route("/event/<slug>")
def event_detail(slug):
    """
    Public Event Landing Page.
    Displays event logistics, schedule, venue, and dynamic registration form.
    """
    db = get_db()
    event_row = db.execute("SELECT * FROM events WHERE slug = ?", (slug,)).fetchone()
    
    if not event_row:
        abort(404, description="Event not found.")

    event = dict(event_row)

    # Parse custom fields
    try:
        event["custom_fields"] = json.loads(event.get("custom_fields_json") or "[]")
    except Exception:
        event["custom_fields"] = []

    # Get current registration count and remaining capacity
    reg_count = db.execute(
        "SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status = 'confirmed'",
        (event["id"],)
    ).fetchone()[0]
    
    event["registration_count"] = reg_count
    event["is_full"] = event["max_capacity"] > 0 and reg_count >= event["max_capacity"]
    event["remaining_spots"] = max(0, event["max_capacity"] - reg_count) if event["max_capacity"] > 0 else None

    return render_template("event_detail.html", event=event)

@public_bp.route("/event/<slug>/register", methods=["POST"])
def event_register(slug):
    """
    Process public event registration form submission.
    Validates form data, generates secure ticket, and redirects to digital ticket pass.
    """
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE slug = ?", (slug,)).fetchone()
    
    if not event:
        flash("The requested event was not found.", "danger")
        return redirect(url_for("index"))

    form_dict = request.form.to_dict()
    success, message, new_reg = register_participant(event["id"], form_dict)

    if not success:
        flash(message, "danger")
        return redirect(url_for("public.event_detail", slug=slug))

    flash("Registration confirmed! Here is your digital pass.", "success")
    return redirect(url_for("public.ticket_view", ticket_code=new_reg["ticket_code"]))

@public_bp.route("/ticket/retrieve", methods=["GET", "POST"])
def ticket_retrieve():
    """
    Secure ticket retrieval flow.
    Requires BOTH the registered email AND the ticket code to match.
    This prevents any single-field enumeration of other participants' tickets.
    """
    if request.method == "GET":
        return render_template("ticket_retrieve.html")

    email = request.form.get("email", "").strip().lower()
    ticket_code = request.form.get("ticket_code", "").strip().upper()

    if not email or not ticket_code:
        flash("Both email and Ticket Code are required.", "danger")
        return redirect(url_for("public.ticket_retrieve"))

    db = get_db()
    reg = db.execute("""
        SELECT ticket_code FROM registrations
        WHERE participant_email = ? AND ticket_code = ?
    """, (email, ticket_code)).fetchone()

    if not reg:
        flash("No matching ticket found. Double-check your email and Ticket Code.", "danger")
        return redirect(url_for("public.ticket_retrieve"))

    return redirect(url_for("public.ticket_view", ticket_code=reg["ticket_code"]))

@public_bp.route("/ticket/<ticket_code>")
def ticket_view(ticket_code):
    """
    Digital Boarding Pass / Attendee Badge View.
    Displays cryptographic QR code, ticket details, and print options.
    """
    ticket = get_ticket_details(ticket_code)
    if not ticket:
        abort(404, description="Ticket not found or invalid.")

    return render_template("ticket_view.html", ticket=ticket)


# =========================================================================
# REST API Endpoints (Phase 3 Spec)
# =========================================================================

@public_bp.route("/api/events/<slug>", methods=["GET"])
def api_event_detail(slug):
    """API: Get event details and dynamic custom fields schema."""
    db = get_db()
    event_row = db.execute("SELECT * FROM events WHERE slug = ?", (slug,)).fetchone()
    if not event_row:
        return jsonify({"error": "Event not found"}), 404

    event = dict(event_row)
    try:
        event["custom_fields"] = json.loads(event.get("custom_fields_json") or "[]")
    except Exception:
        event["custom_fields"] = []

    reg_count = db.execute(
        "SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event["id"],)
    ).fetchone()[0]

    return jsonify({
        "id": event["id"],
        "slug": event["slug"],
        "title": event["title"],
        "tagline": event["tagline"],
        "description": event["description"],
        "category": event["category"],
        "mode": event["mode"],
        "venue": event["venue"],
        "start_time": event["start_time"],
        "end_time": event["end_time"],
        "registration_deadline": event["registration_deadline"],
        "max_capacity": event["max_capacity"],
        "current_registrations": reg_count,
        "status": event["status"],
        "custom_fields": event["custom_fields"]
    })

@public_bp.route("/api/events/<slug>/register", methods=["POST"])
def api_event_register(slug):
    """API: Register participant via JSON or form submission."""
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE slug = ?", (slug,)).fetchone()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"error": "Request body must contain registration data"}), 400

    success, message, new_reg = register_participant(event["id"], data)
    if not success:
        status_code = 409 if "already registered" in message.lower() else 400
        return jsonify({"error": message}), status_code

    return jsonify({
        "success": True,
        "message": message,
        "ticket_code": new_reg["ticket_code"],
        "ticket_secret": new_reg["ticket_secret"],
        "participant_name": new_reg["participant_name"],
        "participant_email": new_reg["participant_email"],
        "ticket_url": f"/ticket/{new_reg['ticket_code']}"
    }), 201

@public_bp.route("/api/tickets/<ticket_code>", methods=["GET"])
def api_ticket_detail(ticket_code):
    """API: Retrieve public ticket verification data."""
    ticket = get_ticket_details(ticket_code)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify({
        "ticket_code": ticket["ticket_code"],
        "event_title": ticket["event_title"],
        "event_venue": ticket["event_venue"],
        "event_start_time": ticket["event_start_time"],
        "participant_name": ticket["participant_name"],
        "participant_email": ticket["participant_email"],
        "status": ticket["status"],
        "is_checked_in": bool(ticket["is_checked_in"]),
        "checked_in_at": ticket["checked_in_at"],
        "registered_at": ticket["registered_at"],
        "answers": ticket["answers"]
    })
