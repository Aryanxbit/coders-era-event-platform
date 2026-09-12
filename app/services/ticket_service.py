import re
import io
import json
import base64
import secrets
import sqlite3
import qrcode
from app.db import get_db

TICKET_CODE_REGEX = re.compile(r"^CE-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}$")
EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$")

def generate_ticket_code() -> str:
    """
    Generate a cryptographically random, human-readable ticket ID.
    Format: CE-XXXX-XXXX-XXXX (uppercase hexadecimal)
    e.g., CE-A4F1-99B2-7C3D
    """
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    part3 = secrets.token_hex(2).upper()
    return f"CE-{part1}-{part2}-{part3}"

def generate_ticket_secret() -> str:
    """
    Generate a 256-bit (32 bytes) cryptographically secure URL-safe random token.
    This secret is embedded into the QR code to eliminate brute-force enumeration.
    """
    return secrets.token_urlsafe(32)

def generate_qr_code_data_url(payload: str) -> str:
    """
    Generate a high-contrast QR code image from the payload string
    and return it as a Base64 PNG data URL suitable for <img> src tags.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#070a12", back_color="#ffffff")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

def validate_registration_input(event: dict, form_data: dict) -> tuple[bool, str, dict]:
    """
    Validate core and dynamic custom question inputs against the event's schema.
    Returns: (is_valid, error_message, validated_custom_answers)
    """
    name = form_data.get("participant_name", "").strip()
    email = form_data.get("participant_email", "").strip().lower()
    phone = form_data.get("participant_phone", "").strip()

    if not name:
        return False, "Participant full name is required.", {}
    if len(name) < 2 or len(name) > 100:
        return False, "Full name must be between 2 and 100 characters.", {}

    if not email:
        return False, "Participant email address is required.", {}
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address.", {}

    # Validate dynamic custom fields
    custom_fields_raw = event.get("custom_fields_json", "[]")
    if isinstance(custom_fields_raw, str):
        try:
            custom_fields = json.loads(custom_fields_raw)
        except Exception:
            custom_fields = []
    elif isinstance(custom_fields_raw, list):
        custom_fields = custom_fields_raw
    else:
        custom_fields = []

    answers = {}
    for field in custom_fields:
        field_id = field.get("id")
        label = field.get("label", field_id)
        is_required = field.get("required", False)
        val = form_data.get(f"custom_{field_id}", "").strip()

        if is_required and not val:
            return False, f"Field '{label}' is required.", {}

        answers[field_id] = val

    return True, "", answers

def register_participant(event_id: int, form_data: dict) -> tuple[bool, str, dict | None]:
    """
    Atomically register an attendee for an event with duplicate prevention.
    Enforces SQLite UNIQUE(event_id, participant_email).
    """
    db = get_db()

    # Fetch event and verify status & capacity
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        return False, "Event not found.", None

    if event["status"] != "published":
        return False, f"Event is currently {event['status']} and not accepting registrations.", None

    # Check capacity limit if set (> 0)
    if event["max_capacity"] and event["max_capacity"] > 0:
        current_count = db.execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status = 'confirmed'",
            (event_id,)
        ).fetchone()[0]
        if current_count >= event["max_capacity"]:
            return False, "This event has reached maximum participant capacity.", None

    # Validate form input
    is_valid, err_msg, custom_answers = validate_registration_input(dict(event), form_data)
    if not is_valid:
        return False, err_msg, None

    participant_name = form_data.get("participant_name", "").strip()
    participant_email = form_data.get("participant_email", "").strip().lower()
    participant_phone = form_data.get("participant_phone", "").strip()

    # Generate unique ticket codes
    ticket_code = generate_ticket_code()
    ticket_secret = generate_ticket_secret()

    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO registrations (
                ticket_code, ticket_secret, event_id, participant_name,
                participant_email, participant_phone, answers_json,
                status, is_checked_in
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', 0)
        """, (
            ticket_code,
            ticket_secret,
            event_id,
            participant_name,
            participant_email,
            participant_phone,
            json.dumps(custom_answers)
        ))
        db.commit()

        new_reg = {
            "id": cursor.lastrowid,
            "ticket_code": ticket_code,
            "ticket_secret": ticket_secret,
            "event_id": event_id,
            "participant_name": participant_name,
            "participant_email": participant_email,
            "participant_phone": participant_phone,
            "answers": custom_answers
        }
        return True, "Registration successful!", new_reg

    except sqlite3.IntegrityError as e:
        db.rollback()
        err_text = str(e).lower()
        if "unique" in err_text and ("participant_email" in err_text or "registrations" in err_text):
            return False, f"The email '{participant_email}' is already registered for this event. Each participant may only register once.", None
        return False, "A database conflict occurred while processing registration.", None

def get_ticket_details(ticket_code: str) -> dict | None:
    """
    Fetch comprehensive ticket and event details for rendering digital boarding pass.
    """
    db = get_db()
    row = db.execute("""
        SELECT 
            r.id, r.ticket_code, r.ticket_secret, r.participant_name,
            r.participant_email, r.participant_phone, r.answers_json,
            r.status, r.is_checked_in, r.checked_in_at, r.created_at as registered_at,
            e.id as event_id, e.slug as event_slug, e.title as event_title,
            e.tagline as event_tagline, e.description as event_description,
            e.category as event_category, e.mode as event_mode, e.venue as event_venue,
            e.start_time as event_start_time, e.end_time as event_end_time,
            e.custom_fields_json
        FROM registrations r
        INNER JOIN events e ON r.event_id = e.id
        WHERE r.ticket_code = ?
    """, (ticket_code,)).fetchone()

    if not row:
        return None

    ticket_data = dict(row)
    
    # Parse answers JSON
    try:
        ticket_data["answers"] = json.loads(ticket_data.get("answers_json") or "{}")
    except Exception:
        ticket_data["answers"] = {}

    # Parse custom fields schema
    try:
        ticket_data["custom_fields"] = json.loads(ticket_data.get("custom_fields_json") or "[]")
    except Exception:
        ticket_data["custom_fields"] = []

    # Format custom answers with labels for display
    formatted_answers = []
    field_label_map = {f.get("id"): f.get("label", f.get("id")) for f in ticket_data["custom_fields"]}
    for k, v in ticket_data["answers"].items():
        label = field_label_map.get(k, k.replace("_", " ").title())
        formatted_answers.append({"key": k, "label": label, "value": v})
    ticket_data["formatted_answers"] = formatted_answers

    # Generate QR Code with secret token embedded in JSON payload
    qr_payload = json.dumps({
        "ticket_code": ticket_data["ticket_code"],
        "secret": ticket_data["ticket_secret"],
        "event_id": ticket_data["event_id"],
        "name": ticket_data["participant_name"]
    }, separators=(',', ':'))

    ticket_data["qr_data_url"] = generate_qr_code_data_url(qr_payload)

    return ticket_data
