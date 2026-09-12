import re
import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from app.db import get_db
from app.routes.auth_routes import login_required, role_required
from app.services.export_service import get_participants, generate_csv

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def slugify(text):
    """Generate a clean URL slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')

@admin_bp.route("/dashboard")
@login_required
@role_required("admin", "organizer")
def dashboard():
    """Real-time organizer telemetry dashboard."""
    db = get_db()

    # 1. High-Level Metrics
    events_count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_registrations = db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    total_checked_in = db.execute("SELECT COUNT(*) FROM registrations WHERE is_checked_in = 1").fetchone()[0]
    total_pending = db.execute("SELECT COUNT(*) FROM registrations WHERE is_checked_in = 0").fetchone()[0]

    attendance_rate = round((total_checked_in / total_registrations * 100), 1) if total_registrations > 0 else 0.0

    # 2. Event-by-Event Breakdown
    events_breakdown = db.execute("""
        SELECT 
            e.id, e.slug, e.title, e.category, e.mode, e.venue, e.start_time, e.max_capacity,
            COUNT(r.id) as registered_count,
            SUM(CASE WHEN r.is_checked_in = 1 THEN 1 ELSE 0 END) as checked_in_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        GROUP BY e.id
        ORDER BY e.start_time ASC
    """).fetchall()

    # Calculate percentages for each event
    formatted_events = []
    for ev in events_breakdown:
        reg = ev["registered_count"]
        chk = ev["checked_in_count"] or 0
        pend = reg - chk
        rate = round((chk / reg * 100), 1) if reg > 0 else 0.0
        formatted_events.append({
            "id": ev["id"],
            "slug": ev["slug"],
            "title": ev["title"],
            "category": ev["category"],
            "mode": ev["mode"],
            "venue": ev["venue"],
            "start_time": ev["start_time"],
            "max_capacity": ev["max_capacity"],
            "registered": reg,
            "checked_in": chk,
            "pending": pend,
            "rate": rate
        })

    # 3. Recent Check-in Logs Stream
    recent_logs = db.execute("""
        SELECT 
            l.id, l.scanned_code, l.status, l.timestamp,
            r.participant_name, r.ticket_code,
            e.title as event_title,
            u.full_name as volunteer_name
        FROM checkin_logs l
        LEFT JOIN registrations r ON l.registration_id = r.id
        LEFT JOIN events e ON l.event_id = e.id
        LEFT JOIN users u ON l.attempted_by = u.id
        ORDER BY l.timestamp DESC
        LIMIT 10
    """).fetchall()

    return render_template(
        "admin/dashboard.html",
        stats={
            "events_count": events_count,
            "total_registrations": total_registrations,
            "total_checked_in": total_checked_in,
            "total_pending": total_pending,
            "attendance_rate": attendance_rate
        },
        events=formatted_events,
        recent_logs=recent_logs
    )

@admin_bp.route("/events", methods=["GET"])
@login_required
@role_required("admin", "organizer")
def events_list():
    """Event management view."""
    db = get_db()
    events = db.execute("""
        SELECT 
            e.*,
            COUNT(r.id) as registrations_count,
            SUM(CASE WHEN r.is_checked_in = 1 THEN 1 ELSE 0 END) as checked_in_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        GROUP BY e.id
        ORDER BY e.created_at DESC
    """).fetchall()

    return render_template("admin/events.html", events=events)

@admin_bp.route("/events/new", methods=["POST"])
@login_required
@role_required("admin", "organizer")
def create_event():
    """Create a new event with custom registration fields."""
    db = get_db()

    title = request.form.get("title", "").strip()
    if not title:
        flash("Event title is required.", "danger")
        return redirect(url_for("admin.events_list"))

    slug = request.form.get("slug", "").strip() or slugify(title)
    # Ensure slug uniqueness
    existing = db.execute("SELECT id FROM events WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    tagline = request.form.get("tagline", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Hackathon")
    mode = request.form.get("mode", "offline")
    venue = request.form.get("venue", "").strip() or "Main Auditorium"
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    reg_deadline = request.form.get("registration_deadline", "").strip() or start_time
    max_capacity = int(request.form.get("max_capacity", 0) or 0)

    # Dynamic custom fields from JSON builder
    custom_fields_raw = request.form.get("custom_fields_json", "[]")
    try:
        custom_fields = json.loads(custom_fields_raw)
        if not isinstance(custom_fields, list):
            custom_fields = []
    except Exception:
        custom_fields = []

    db.execute("""
        INSERT INTO events (
            uuid, slug, title, tagline, description, category, mode,
            venue, start_time, end_time, registration_deadline,
            max_capacity, status, custom_fields_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', ?, ?)
    """, (
        str(uuid.uuid4()), slug, title, tagline, description, category, mode,
        venue, start_time, end_time, reg_deadline, max_capacity,
        json.dumps(custom_fields), session["user_id"]
    ))
    db.commit()

    flash(f"Event '{title}' published successfully!", "success")
    return redirect(url_for("admin.events_list"))

@admin_bp.route("/api/telemetry")
@login_required
@role_required("admin", "organizer")
def api_telemetry():
    """Live JSON endpoint for dashboard auto-polling."""
    db = get_db()
    total_reg = db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    total_chk = db.execute("SELECT COUNT(*) FROM registrations WHERE is_checked_in = 1").fetchone()[0]
    total_pnd = total_reg - total_chk
    rate = round((total_chk / total_reg * 100), 1) if total_reg > 0 else 0.0

    return jsonify({
        "total_registrations": total_reg,
        "total_checked_in": total_chk,
        "total_pending": total_pnd,
        "attendance_rate": rate
    })


# =========================================================================
# Phase 5: Participant Management
# =========================================================================

@admin_bp.route("/participants")
@login_required
@role_required("admin", "organizer")
def participants():
    """
    Searchable participant roster across all events (or scoped to one event).
    Supports live text filter via ?search=... and ?event_id=... query params.
    """
    db = get_db()

    # Event selector
    events = db.execute(
        "SELECT id, slug, title FROM events ORDER BY start_time ASC"
    ).fetchall()

    event_id = request.args.get("event_id", type=int)
    if not event_id and events:
        event_id = events[0]["id"]

    search = request.args.get("search", "").strip()

    participants_list = []
    selected_event = None
    summary = {"total": 0, "checked_in": 0, "pending": 0}

    if event_id:
        selected_event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        participants_list = get_participants(event_id, search)
        total = len(participants_list)
        checked_in = sum(1 for p in participants_list if p["is_checked_in"])
        summary = {
            "total": total,
            "checked_in": checked_in,
            "pending": total - checked_in
        }

    return render_template(
        "admin/participants.html",
        events=events,
        selected_event=selected_event,
        participants=participants_list,
        search=search,
        event_id=event_id,
        summary=summary
    )


@admin_bp.route("/participants/<int:registration_id>")
@login_required
@role_required("admin", "organizer")
def participant_detail(registration_id):
    """JSON endpoint returning full details of one registration."""
    db = get_db()
    row = db.execute("""
        SELECT
            r.id, r.ticket_code, r.participant_name, r.participant_email,
            r.participant_phone, r.answers_json, r.status,
            r.is_checked_in, r.checked_in_at, r.created_at as registered_at,
            e.title as event_title, e.slug as event_slug,
            e.venue as event_venue, e.start_time as event_start_time,
            e.custom_fields_json,
            u.full_name as checked_in_by_name
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        LEFT JOIN users u ON r.checked_in_by = u.id
        WHERE r.id = ?
    """, (registration_id,)).fetchone()

    if not row:
        return jsonify({"error": "Registration not found"}), 404

    item = dict(row)
    try:
        item["answers"] = json.loads(item.get("answers_json") or "{}")
    except Exception:
        item["answers"] = {}
    try:
        custom_fields = json.loads(item.get("custom_fields_json") or "[]")
    except Exception:
        custom_fields = []

    field_label_map = {f["id"]: f.get("label", f["id"]) for f in custom_fields}
    item["formatted_answers"] = [
        {"key": k, "label": field_label_map.get(k, k), "value": v}
        for k, v in item["answers"].items()
    ]
    return jsonify(item)


@admin_bp.route("/export/<int:event_id>.csv")
@login_required
@role_required("admin", "organizer")
def export_csv(event_id):
    """
    Stream a complete CSV file of all registrations for the given event,
    including custom question answers and attendance status.
    """
    csv_data, filename = generate_csv(event_id)
    if not csv_data:
        flash("No registrations found for that event.", "warning")
        return redirect(url_for("admin.participants", event_id=event_id))

    return Response(
        csv_data,
        status=200,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8"
        }
    )

