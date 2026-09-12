import csv
import io
import json
from app.db import get_db


def get_participants(event_id: int, search: str = "") -> list[dict]:
    """
    Fetch all registrations for an event with optional full-text search
    across participant_name, participant_email, and ticket_code.
    """
    db = get_db()
    search = search.strip()

    if search:
        like = f"%{search}%"
        rows = db.execute("""
            SELECT
                r.id, r.ticket_code, r.participant_name, r.participant_email,
                r.participant_phone, r.answers_json, r.status,
                r.is_checked_in, r.checked_in_at, r.created_at as registered_at,
                e.title as event_title, e.custom_fields_json,
                u.full_name as checked_in_by_name
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            LEFT JOIN users u ON r.checked_in_by = u.id
            WHERE r.event_id = ?
              AND (
                  r.participant_name LIKE ? COLLATE NOCASE
                  OR r.participant_email LIKE ? COLLATE NOCASE
                  OR r.ticket_code LIKE ? COLLATE NOCASE
              )
            ORDER BY r.created_at DESC
        """, (event_id, like, like, like)).fetchall()
    else:
        rows = db.execute("""
            SELECT
                r.id, r.ticket_code, r.participant_name, r.participant_email,
                r.participant_phone, r.answers_json, r.status,
                r.is_checked_in, r.checked_in_at, r.created_at as registered_at,
                e.title as event_title, e.custom_fields_json,
                u.full_name as checked_in_by_name
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            LEFT JOIN users u ON r.checked_in_by = u.id
            WHERE r.event_id = ?
            ORDER BY r.created_at DESC
        """, (event_id,)).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        try:
            item["answers"] = json.loads(item.get("answers_json") or "{}")
        except Exception:
            item["answers"] = {}
        try:
            item["custom_fields"] = json.loads(item.get("custom_fields_json") or "[]")
        except Exception:
            item["custom_fields"] = []
        result.append(item)
    return result


def generate_csv(event_id: int) -> tuple[str, str]:
    """
    Generate a complete CSV export for all registrations of an event.
    Returns: (csv_string, filename)
    """
    db = get_db()

    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        return "", "export.csv"

    participants = get_participants(event_id)

    # Determine all unique custom field IDs from the event schema
    try:
        custom_fields = json.loads(event["custom_fields_json"] or "[]")
    except Exception:
        custom_fields = []

    custom_field_labels = [(f["id"], f.get("label", f["id"])) for f in custom_fields]

    # Build CSV header
    base_headers = [
        "Ticket Code",
        "Full Name",
        "Email",
        "Phone",
        "Registration Status",
        "Checked In",
        "Check-In Time",
        "Checked In By",
        "Registered At",
    ]
    custom_headers = [label for _, label in custom_field_labels]
    all_headers = base_headers + custom_headers

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(all_headers)

    for p in participants:
        checked_in = "Yes" if p["is_checked_in"] else "No"
        row = [
            p["ticket_code"],
            p["participant_name"],
            p["participant_email"],
            p.get("participant_phone") or "",
            p.get("status") or "confirmed",
            checked_in,
            p.get("checked_in_at") or "",
            p.get("checked_in_by_name") or "",
            p.get("registered_at") or "",
        ]
        for field_id, _ in custom_field_labels:
            row.append(p["answers"].get(field_id, ""))
        writer.writerow(row)

    event_slug = event["slug"].replace("-", "_")
    filename = f"participants_{event_slug}.csv"
    return output.getvalue(), filename
