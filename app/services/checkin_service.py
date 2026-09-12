import json
import re
from app.db import get_db

def parse_scan_input(raw_input: str) -> dict:
    """
    Parse various barcode/scanner inputs:
    1. JSON object payload from QR code: {"ticket_code": "...", "secret": "..."}
    2. URL containing /ticket/<ticket_code>
    3. Direct Ticket Code string (e.g., CE-XXXX-XXXX-XXXX)
    4. Direct Ticket Secret token
    """
    if not raw_input:
        return {"code": "", "secret": "", "raw": ""}

    raw_input = raw_input.strip()

    # Try JSON parsing
    if raw_input.startswith("{") and raw_input.endswith("}"):
        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, dict):
                return {
                    "code": parsed.get("ticket_code", "").strip().upper(),
                    "secret": parsed.get("secret", "").strip(),
                    "event_id": parsed.get("event_id"),
                    "raw": raw_input
                }
        except Exception:
            pass

    # Match URL pattern like /ticket/CE-XXXX-XXXX-XXXX
    url_match = re.search(r'/ticket/(CE-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4})', raw_input)
    if url_match:
        return {
            "code": url_match.group(1).upper(),
            "secret": "",
            "raw": raw_input
        }

    # Match raw ticket code format CE-XXXX-XXXX-XXXX
    code_match = re.search(r'CE-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}', raw_input, re.IGNORECASE)
    if code_match:
        return {
            "code": code_match.group(0).upper(),
            "secret": "",
            "raw": raw_input
        }

    # Fallback to checking as raw ticket code or secret token
    return {
        "code": raw_input.upper() if raw_input.upper().startswith("CE-") else "",
        "secret": raw_input if not raw_input.upper().startswith("CE-") else "",
        "raw": raw_input
    }

def verify_and_checkin(raw_input: str, target_event_id: int | None, attempted_by_user_id: int, ip_address: str = "127.0.0.1") -> dict:
    """
    Atomic check-in verification engine:
    1. Resolves ticket from raw QR or manual input.
    2. Validates event matching.
    3. Executes atomic one-time SQL state transition (WHERE id = ? AND is_checked_in = 0).
    4. Records an immutable entry in checkin_logs.
    """
    db = get_db()
    parsed = parse_scan_input(raw_input)
    search_code = parsed.get("code")
    search_secret = parsed.get("secret")
    raw_str = parsed.get("raw") or raw_input

    # Step 1: Find registration record
    reg = None
    if search_secret:
        reg = db.execute("""
            SELECT r.*, e.title as event_title, e.venue as event_venue, e.slug as event_slug
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            WHERE r.ticket_secret = ?
        """, (search_secret,)).fetchone()

    if not reg and search_code:
        reg = db.execute("""
            SELECT r.*, e.title as event_title, e.venue as event_venue, e.slug as event_slug
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            WHERE r.ticket_code = ?
        """, (search_code,)).fetchone()

    if not reg and raw_str:
        reg = db.execute("""
            SELECT r.*, e.title as event_title, e.venue as event_venue, e.slug as event_slug
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            WHERE r.ticket_code = ? OR r.ticket_secret = ?
        """, (raw_str, raw_str)).fetchone()

    # If ticket does not exist
    if not reg:
        default_event_id = target_event_id or 1
        db.execute("""
            INSERT INTO checkin_logs (registration_id, event_id, scanned_code, status, attempted_by, ip_address)
            VALUES (NULL, ?, ?, 'INVALID_TICKET', ?, ?)
        """, (default_event_id, raw_str[:100], attempted_by_user_id, ip_address))
        db.commit()

        return {
            "status": "INVALID_TICKET",
            "http_status": 404,
            "message": "Invalid Ticket: No registration found matching the scanned code or token.",
            "ticket": None
        }

    reg_dict = dict(reg)
    event_id = reg_dict["event_id"]

    # Step 2: Validate Event ID match if target_event_id specified
    if target_event_id and int(target_event_id) != event_id:
        db.execute("""
            INSERT INTO checkin_logs (registration_id, event_id, scanned_code, status, attempted_by, ip_address)
            VALUES (?, ?, ?, 'EVENT_MISMATCH', ?, ?)
        """, (reg_dict["id"], int(target_event_id), reg_dict["ticket_code"], attempted_by_user_id, ip_address))
        db.commit()

        return {
            "status": "EVENT_MISMATCH",
            "http_status": 400,
            "message": f"Event Mismatch: This ticket is for '{reg_dict['event_title']}', not the selected event.",
            "ticket": {
                "ticket_code": reg_dict["ticket_code"],
                "participant_name": reg_dict["participant_name"],
                "event_title": reg_dict["event_title"]
            }
        }

    # Step 3: Atomic One-Time Check-In State Transition
    cursor = db.cursor()
    cursor.execute("""
        UPDATE registrations
        SET is_checked_in = 1,
            checked_in_at = CURRENT_TIMESTAMP,
            checked_in_by = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND is_checked_in = 0
    """, (attempted_by_user_id, reg_dict["id"]))

    if cursor.rowcount == 1:
        # Atomic transition successful
        db.execute("""
            INSERT INTO checkin_logs (registration_id, event_id, scanned_code, status, attempted_by, ip_address)
            VALUES (?, ?, ?, 'SUCCESS', ?, ?)
        """, (reg_dict["id"], event_id, reg_dict["ticket_code"], attempted_by_user_id, ip_address))
        db.commit()

        # Re-fetch checked_in_at timestamp
        updated_reg = db.execute("SELECT checked_in_at FROM registrations WHERE id = ?", (reg_dict["id"],)).fetchone()
        checked_at = updated_reg["checked_in_at"] if updated_reg else "Just now"

        return {
            "status": "SUCCESS",
            "http_status": 200,
            "message": f"Verification Successful! Welcome, {reg_dict['participant_name']}.",
            "ticket": {
                "id": reg_dict["id"],
                "ticket_code": reg_dict["ticket_code"],
                "participant_name": reg_dict["participant_name"],
                "participant_email": reg_dict["participant_email"],
                "participant_phone": reg_dict["participant_phone"],
                "event_title": reg_dict["event_title"],
                "event_venue": reg_dict["event_venue"],
                "checked_in_at": checked_at
            }
        }
    else:
        # Already checked in
        prior_info = db.execute("""
            SELECT r.checked_in_at, u.full_name as staff_name
            FROM registrations r
            LEFT JOIN users u ON r.checked_in_by = u.id
            WHERE r.id = ?
        """, (reg_dict["id"],)).fetchone()

        prior_time = prior_info["checked_in_at"] if prior_info and prior_info["checked_in_at"] else "Earlier"
        staff = prior_info["staff_name"] if prior_info and prior_info["staff_name"] else "Staff"

        db.execute("""
            INSERT INTO checkin_logs (registration_id, event_id, scanned_code, status, attempted_by, ip_address)
            VALUES (?, ?, ?, 'ALREADY_USED', ?, ?)
        """, (reg_dict["id"], event_id, reg_dict["ticket_code"], attempted_by_user_id, ip_address))
        db.commit()

        return {
            "status": "ALREADY_USED",
            "http_status": 409,
            "message": f"Entry Denied: Ticket was already checked in on {prior_time} (by {staff}).",
            "ticket": {
                "ticket_code": reg_dict["ticket_code"],
                "participant_name": reg_dict["participant_name"],
                "participant_email": reg_dict["participant_email"],
                "event_title": reg_dict["event_title"],
                "checked_in_at": prior_time
            }
        }
