import os
import sys
import uuid
import json
import secrets
import getpass
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash

# Try loading .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.config import Config
from app.db import init_db, get_db

def generate_ticket_code():
    """Generate a clean, human-readable ticket code e.g. CE-A1B2-C3D4."""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"CE-{part1}-{part2}"

def resolve_credential(env_key, account_label, allow_interactive=True):
    """
    Safely resolve a password without hardcoded defaults:
    1. Read from environment variable (e.g. from .env file).
    2. Prompt interactively via getpass if running in an interactive terminal.
    3. If unattended / unset, generate a high-entropy temporary password on the fly.
    """
    password = os.getenv(env_key)
    if password:
        return password, "Environment Variable (.env)"

    # Check for interactive terminal input
    if allow_interactive and sys.stdin.isatty():
        try:
            entered = getpass.getpass(f"Enter password for {account_label} (or press Enter to auto-generate): ").strip()
            if entered:
                return entered, "Interactive Input"
        except (EOFError, KeyboardInterrupt):
            pass

    # Generate a cryptographically secure random temporary password
    generated = secrets.token_urlsafe(16)
    return generated, "Auto-Generated (One-Time Temporary)"

def seed_database(db_path=None, interactive=False):
    """
    Safely seed initial development data.
    ZERO hardcoded passwords exist in source code.
    Passwords are NEVER stored as plaintext in the database; only salted PBKDF2 hashes are saved.
    Credentials can be customized via environment variables in .env.
    """
    if db_path is None:
        db_path = Config.DATABASE_PATH

    print(f"[*] Initializing database schema at: {db_path}")
    init_db(db_path)

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Resolve Credentials Dynamically (Zero Hardcoded Passwords)
    admin_email = os.getenv("DEV_ADMIN_EMAIL", "organizer@codersera.in")
    admin_name = os.getenv("DEV_ADMIN_NAME", "Coders Era Lead Organizer")
    admin_password, admin_source = resolve_credential(
        "DEV_ADMIN_PASSWORD", "Admin Organizer", allow_interactive=interactive
    )

    volunteer_email = os.getenv("DEV_VOLUNTEER_EMAIL", "volunteer@codersera.in")
    volunteer_name = os.getenv("DEV_VOLUNTEER_NAME", "Gate Check-in Volunteer")
    volunteer_password, volunteer_source = resolve_credential(
        "DEV_VOLUNTEER_PASSWORD", "Volunteer Scanner", allow_interactive=interactive
    )

    # Hash passwords securely using PBKDF2-SHA256 (1,000,000 rounds)
    admin_hash = generate_password_hash(admin_password, method="pbkdf2:sha256")
    volunteer_hash = generate_password_hash(volunteer_password, method="pbkdf2:sha256")

    # Insert or update Admin User
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    admin_user = cursor.fetchone()
    if not admin_user:
        cursor.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, 'admin')
        """, (str(uuid.uuid4()), admin_email, admin_hash, admin_name))
        admin_id = cursor.lastrowid
        print(f"[+] Created Admin Organizer account: {admin_email}")
    else:
        admin_id = admin_user["id"]
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (admin_hash, admin_id))
        print(f"[*] Updated existing Admin account: {admin_email}")

    # Insert or update Volunteer User
    cursor.execute("SELECT id FROM users WHERE email = ?", (volunteer_email,))
    volunteer_user = cursor.fetchone()
    if not volunteer_user:
        cursor.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, 'volunteer')
        """, (str(uuid.uuid4()), volunteer_email, volunteer_hash, volunteer_name))
        volunteer_id = cursor.lastrowid
        print(f"[+] Created Volunteer account: {volunteer_email}")
    else:
        volunteer_id = volunteer_user["id"]
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (volunteer_hash, volunteer_id))
        print(f"[*] Updated existing Volunteer account: {volunteer_email}")

    # 2. Seed Sample Hackathon Event
    sample_event_slug = "automate-india-2026"
    cursor.execute("SELECT id FROM events WHERE slug = ?", (sample_event_slug,))
    event_row = cursor.fetchone()

    custom_fields = [
        {
            "id": "roll_no",
            "label": "College Roll Number / Student ID",
            "type": "text",
            "required": True,
            "placeholder": "e.g. 21CS045"
        },
        {
            "id": "branch",
            "label": "Branch / Department",
            "type": "select",
            "required": True,
            "options": ["Computer Science & Engineering", "Information Technology", "AI & Data Science", "Electronics", "Other"]
        },
        {
            "id": "github_handle",
            "label": "GitHub Profile Username",
            "type": "text",
            "required": False,
            "placeholder": "e.g. octocat"
        }
    ]

    if not event_row:
        cursor.execute("""
            INSERT INTO events (
                uuid, slug, title, tagline, description, category, mode,
                venue, start_time, end_time, registration_deadline,
                max_capacity, status, custom_fields_json, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', ?, ?)
        """, (
            str(uuid.uuid4()),
            sample_event_slug,
            "Automate India Hackathon 2026",
            "Building high-craft GenAI & Cloud systems with Coders Era",
            "Join 300+ ambitious student developers for an intensive 24-hour hackathon. Build open source solutions, deploy live production URLs, and compete for exciting prizes and mentorship.",
            "Hackathon",
            "offline",
            "Main Auditorium & Innovation Lab, Tech Campus",
            "2026-09-25 09:00:00",
            "2026-09-26 17:00:00",
            "2026-09-24 23:59:59",
            300,
            json.dumps(custom_fields),
            admin_id
        ))
        event_id = cursor.lastrowid
        print(f"[+] Created Demo Event: Automate India Hackathon 2026 (Slug: {sample_event_slug})")
    else:
        event_id = event_row["id"]
        print(f"[*] Demo Event already exists (ID: {event_id})")

    # 3. Seed Sample Attendee Registrations
    sample_attendees = [
        ("Aarav Sharma", "aarav.sharma@example.com", "+91 9876543210", {"roll_no": "21CS010", "branch": "Computer Science & Engineering", "github_handle": "aaravsharma"}),
        ("Riya Patel", "riya.patel@example.com", "+91 9876543211", {"roll_no": "21IT045", "branch": "Information Technology", "github_handle": "riyapatel"}),
        ("Kavya Verma", "kavya.verma@example.com", "+91 9876543212", {"roll_no": "22AI018", "branch": "AI & Data Science", "github_handle": "kavyaverma"})
    ]

    for name, email, phone, answers in sample_attendees:
        cursor.execute("SELECT id FROM registrations WHERE event_id = ? AND participant_email = ?", (event_id, email))
        if not cursor.fetchone():
            ticket_code = generate_ticket_code()
            ticket_secret = secrets.token_urlsafe(32)
            cursor.execute("""
                INSERT INTO registrations (
                    ticket_code, ticket_secret, event_id, participant_name,
                    participant_email, participant_phone, answers_json,
                    status, is_checked_in
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', 0)
            """, (ticket_code, ticket_secret, event_id, name, email, phone, json.dumps(answers)))
            print(f"[+] Seeded Attendee: {name} | Ticket: {ticket_code}")

    conn.commit()
    conn.close()

    print("\n" + "="*65)
    print("[OK] DATABASE SEEDING COMPLETED (SECURE HASHES STORED)")
    print("="*65)
    print("LOCAL DEVELOPMENT DEMO CREDENTIALS:")
    print(f"  Role: Admin / Organizer")
    print(f"  Email:     {admin_email}")
    print(f"  Password:  {admin_password}")
    print(f"  Source:    {admin_source}")
    print("-" * 65)
    print(f"  Role: Volunteer (Gate Scanner)")
    print(f"  Email:     {volunteer_email}")
    print(f"  Password:  {volunteer_password}")
    print(f"  Source:    {volunteer_source}")
    print("="*65)
    print("Security Notice:")
    print("  * Passwords are stored in SQLite exclusively as PBKDF2-SHA256 hashes.")
    print("  * No credentials are hard-coded in source code.")
    print("  * Set DEV_ADMIN_PASSWORD in a private .env file for fixed local credentials.")
    print("="*65 + "\n")

if __name__ == "__main__":
    is_interactive = "--interactive" in sys.argv
    seed_database(interactive=is_interactive)
