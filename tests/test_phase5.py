import os
import sys
import json
import csv
import io
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import get_db, init_db
from werkzeug.security import generate_password_hash


class Phase5ParticipantsTestCase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = str(PROJECT_ROOT / "test_coders_era_p5.db")
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.app = create_app("testing")
        self.app.config["DATABASE_PATH"] = self.test_db_path
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        init_db(self.test_db_path)
        db = get_db(self.test_db_path)

        # Seed organizer
        pw_hash = generate_password_hash("Pass123!", method="pbkdf2:sha256")
        db.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('org-uuid', 'organizer@codersera.in', ?, 'Lead Organizer', 'admin')
        """, (pw_hash,))

        # Seed event with two custom fields
        custom_fields = [
            {"id": "roll_no", "label": "Roll Number", "type": "text", "required": True},
            {"id": "branch",  "label": "Branch",      "type": "select", "required": True,
             "options": ["CSE", "IT"]}
        ]
        db.execute("""
            INSERT INTO events (id, uuid, slug, title, venue, start_time, end_time,
                registration_deadline, max_capacity, status, custom_fields_json, created_by)
            VALUES (1, 'ev-uuid', 'demo-event', 'Demo Event 2026', 'Auditorium',
                '2026-09-25 09:00:00', '2026-09-26 17:00:00', '2026-09-24 23:59:59',
                100, 'published', ?, 1)
        """, (json.dumps(custom_fields),))

        # Seed 3 registrations: 2 checked-in, 1 pending
        db.execute("""
            INSERT INTO registrations
                (id, ticket_code, ticket_secret, event_id, participant_name, participant_email,
                 participant_phone, answers_json, status, is_checked_in, checked_in_at, checked_in_by)
            VALUES
            (1, 'CE-AA00-BB11-CC22', 'sec-a', 1, 'Alice Kumar', 'alice@example.com',
             '+91 9000000001',
             '{"roll_no": "21CS001", "branch": "CSE"}', 'confirmed', 1, '2026-09-25 10:05:00', 1),
            (2, 'CE-DD33-EE44-FF55', 'sec-b', 1, 'Bob Patel', 'bob@example.com',
             '+91 9000000002',
             '{"roll_no": "21IT002", "branch": "IT"}', 'confirmed', 0, NULL, NULL),
            (3, 'CE-GG66-HH77-II88', 'sec-c', 1, 'Charlie Dev', 'charlie@example.com',
             '+91 9000000003',
             '{"roll_no": "22CS003", "branch": "CSE"}', 'confirmed', 1, '2026-09-25 10:12:00', 1)
        """)
        db.commit()

    def tearDown(self):
        from app.db import close_db
        close_db()
        self.app_context.pop()
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except Exception:
            pass

    def login(self):
        self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "Pass123!"
        })

    # ------------------------------------------------------------------
    # Authentication guard
    # ------------------------------------------------------------------

    def test_participants_page_requires_login(self):
        """Unauthenticated access must redirect to login."""
        res = self.client.get("/admin/participants")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login", res.headers["Location"])

    # ------------------------------------------------------------------
    # Participant listing
    # ------------------------------------------------------------------

    def test_participants_page_lists_all_registrations(self):
        """Participants page must render all 3 seeded registrations."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alice Kumar", res.data)
        self.assertIn(b"Bob Patel", res.data)
        self.assertIn(b"Charlie Dev", res.data)

    def test_participants_shows_ticket_codes(self):
        """Table must display ticket codes for all participants."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1")
        self.assertIn(b"CE-AA00-BB11-CC22", res.data)
        self.assertIn(b"CE-DD33-EE44-FF55", res.data)
        self.assertIn(b"CE-GG66-HH77-II88", res.data)

    def test_participants_shows_checkin_and_pending_status(self):
        """Table must show checked-in and pending status badges correctly."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1")
        # 2 checked in, 1 pending
        self.assertIn(b"Checked In", res.data)
        self.assertIn(b"Pending", res.data)

    def test_participants_summary_stats_are_correct(self):
        """Summary bar must show correct totals: 3 total, 2 checked-in, 1 pending."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1")
        self.assertEqual(res.status_code, 200)
        # The numbers appear in summary stat cards
        self.assertIn(b">3<", res.data)   # total
        self.assertIn(b">2<", res.data)   # checked in
        self.assertIn(b">1<", res.data)   # pending

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def test_search_by_name(self):
        """Search by name must return only matching participants."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1&search=Alice")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alice Kumar", res.data)
        self.assertNotIn(b"Bob Patel", res.data)
        self.assertNotIn(b"Charlie Dev", res.data)

    def test_search_by_email(self):
        """Search by email must return only matching participants."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1&search=bob@example.com")
        self.assertIn(b"Bob Patel", res.data)
        self.assertNotIn(b"Alice Kumar", res.data)

    def test_search_by_ticket_code(self):
        """Search by ticket code must return only matching participants."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1&search=CE-GG66")
        self.assertIn(b"Charlie Dev", res.data)
        self.assertNotIn(b"Alice Kumar", res.data)

    def test_search_no_results(self):
        """Search with no matches must show empty state."""
        self.login()
        res = self.client.get("/admin/participants?event_id=1&search=DOES-NOT-EXIST-XYZ")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(b"Alice Kumar", res.data)
        self.assertNotIn(b"Bob Patel", res.data)

    # ------------------------------------------------------------------
    # Per-participant JSON detail API
    # ------------------------------------------------------------------

    def test_participant_detail_api_returns_correct_data(self):
        """Detail API must return registration data including custom field answers."""
        self.login()
        res = self.client.get("/admin/participants/1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["participant_name"], "Alice Kumar")
        self.assertEqual(data["ticket_code"], "CE-AA00-BB11-CC22")
        self.assertEqual(data["is_checked_in"], 1)
        self.assertIn("answers", data)
        self.assertEqual(data["answers"].get("roll_no"), "21CS001")
        self.assertIn("formatted_answers", data)

    def test_participant_detail_api_404_for_unknown_id(self):
        """Detail API must return 404 for non-existent registration ID."""
        self.login()
        res = self.client.get("/admin/participants/9999")
        self.assertEqual(res.status_code, 404)

    # ------------------------------------------------------------------
    # CSV Export
    # ------------------------------------------------------------------

    def test_csv_export_returns_valid_csv(self):
        """CSV export must return text/csv with correct headers and all 3 rows."""
        self.login()
        res = self.client.get("/admin/export/1.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.content_type)
        self.assertIn("participants_demo_event.csv", res.headers.get("Content-Disposition", ""))

        content = res.data.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Header row + 3 data rows
        self.assertGreaterEqual(len(rows), 4)

        header = rows[0]
        self.assertIn("Ticket Code", header)
        self.assertIn("Full Name", header)
        self.assertIn("Email", header)
        self.assertIn("Checked In", header)
        self.assertIn("Roll Number", header)
        self.assertIn("Branch", header)

    def test_csv_export_includes_checkin_status(self):
        """CSV must accurately reflect checked-in (Yes) and pending (No) status."""
        self.login()
        res = self.client.get("/admin/export/1.csv")
        content = res.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        by_email = {r["Email"]: r for r in rows}
        self.assertEqual(by_email["alice@example.com"]["Checked In"], "Yes")
        self.assertEqual(by_email["bob@example.com"]["Checked In"], "No")
        self.assertEqual(by_email["charlie@example.com"]["Checked In"], "Yes")

    def test_csv_export_includes_custom_field_answers(self):
        """CSV rows must include data from custom question fields."""
        self.login()
        res = self.client.get("/admin/export/1.csv")
        content = res.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        by_email = {r["Email"]: r for r in rows}

        self.assertEqual(by_email["alice@example.com"]["Roll Number"], "21CS001")
        self.assertEqual(by_email["alice@example.com"]["Branch"], "CSE")
        self.assertEqual(by_email["bob@example.com"]["Roll Number"], "21IT002")
        self.assertEqual(by_email["bob@example.com"]["Branch"], "IT")


if __name__ == "__main__":
    unittest.main()
