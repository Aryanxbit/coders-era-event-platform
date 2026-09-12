from flask import Blueprint, render_template, request, jsonify, session
from app.db import get_db
from app.routes.auth_routes import login_required
from app.services.checkin_service import verify_and_checkin

checkin_bp = Blueprint("checkin", __name__)

@checkin_bp.route("/admin/scanner")
@login_required
def scanner_view():
    """
    Mobile-optimized QR Camera Scanner & Manual Verification Console.
    Available to Organizers, Admins, and Gate Volunteers.
    """
    db = get_db()
    events = db.execute("SELECT id, slug, title, category, venue FROM events WHERE status != 'archived' ORDER BY start_time ASC").fetchall()
    
    # Pre-select first event if available
    selected_event_id = request.args.get("event_id", type=int)
    if not selected_event_id and events:
        selected_event_id = events[0]["id"]

    return render_template("admin/scanner.html", events=events, selected_event_id=selected_event_id)

@checkin_bp.route("/api/checkin/verify", methods=["POST"])
@login_required
def api_verify_checkin():
    """
    Fast Check-In Verification API.
    Performs atomic validation against the SQLite database and records an audit log.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({
            "status": "INVALID_INPUT",
            "message": "Missing verification payload."
        }), 400

    raw_input = data.get("code") or data.get("ticket_code") or data.get("input", "")
    if not raw_input:
        return jsonify({
            "status": "INVALID_INPUT",
            "message": "Ticket code or QR payload is required."
        }), 400

    event_id = data.get("event_id")
    if event_id:
        try:
            event_id = int(event_id)
        except (ValueError, TypeError):
            event_id = None

    user_id = session.get("user_id", 1)
    client_ip = request.remote_addr or "127.0.0.1"

    result = verify_and_checkin(
        raw_input=raw_input,
        target_event_id=event_id,
        attempted_by_user_id=user_id,
        ip_address=client_ip
    )

    http_status = result.pop("http_status", 200)
    return jsonify(result), http_status

@checkin_bp.route("/api/checkin/recent")
@login_required
def api_recent_scans():
    """Returns the latest 10 scan logs for the active event."""
    db = get_db()
    event_id = request.args.get("event_id", type=int)

    query = """
        SELECT 
            l.id, l.scanned_code, l.status, l.timestamp,
            r.participant_name, r.ticket_code,
            e.title as event_title,
            u.full_name as volunteer_name
        FROM checkin_logs l
        LEFT JOIN registrations r ON l.registration_id = r.id
        LEFT JOIN events e ON l.event_id = e.id
        LEFT JOIN users u ON l.attempted_by = u.id
    """
    params = []
    if event_id:
        query += " WHERE l.event_id = ?"
        params.append(event_id)

    query += " ORDER BY l.timestamp DESC LIMIT 10"

    logs = db.execute(query, tuple(params)).fetchall()
    
    return jsonify({
        "logs": [dict(log) for log in logs]
    })
