import os
import sys
import json
import unittest
import threading
import sqlite3
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import get_db, init_db
from werkzeug.security import generate_password_hash

class Phase4CheckinTestCase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = str(PROJECT_ROOT / "test_coders_era_p4.db")
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.app = create_app("testing")
        self.app.config["DATABASE_PATH"] = self.test_db_path
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        init_db(self.test_db_path)
        db = get_db(self.test_db_path)

        # 1. Seed Organizer User
        pw_hash = generate_password_hash("ValidPass123!", method="pbkdf2:sha256")
        db.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('organizer-uuid', 'volunteer@codersera.in', ?, 'Gate Volunteer', 'volunteer')
        """, (pw_hash,))

        # 2. Seed Events (Event 1 & Event 2)
        db.execute("""
            INSERT INTO events (id, uuid, slug, title, venue, start_time, end_time, registration_deadline, max_capacity, status, created_by)
            VALUES 
            (1, 'ev-1', 'hackathon-2026', 'National Hackathon', 'Main Hall', '2026-09-25 09:00:00', '2026-09-26 17:00:00', '2026-09-24 23:59:59', 100, 'published', 1),
            (2, 'ev-2', 'workshop-2026', 'GenAI Workshop', 'Lab 3', '2026-09-27 10:00:00', '2026-09-27 16:00:00', '2026-09-26 23:59:59', 50, 'published', 1)
        """)

        # 3. Seed Registrations
        db.execute("""
            INSERT INTO registrations (id, ticket_code, ticket_secret, event_id, participant_name, participant_email, status, is_checked_in)
            VALUES 
            (1, 'CE-1111-2222-3333', 'secret-token-1111', 1, 'Alice Walker', 'alice@example.com', 'confirmed', 0),
            (2, 'CE-4444-5555-6666', 'secret-token-2222', 1, 'Bob Smith', 'bob@example.com', 'confirmed', 1),
            (3, 'CE-7777-8888-9999', 'secret-token-3333', 2, 'Charlie Brown', 'charlie@example.com', 'confirmed', 0)
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

    def login_staff(self):
        """Helper to authenticate staff session."""
        self.client.post("/admin/login", data={
            "email": "volunteer@codersera.in",
            "password": "ValidPass123!"
        })

    def test_scanner_view_requires_authentication(self):
        """Unauthenticated request to /admin/scanner must redirect to login."""
        res = self.client.get("/admin/scanner")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login", res.headers["Location"])

    def test_scanner_view_renders_for_logged_in_staff(self):
        """Authenticated staff must be able to load the scanner interface."""
        self.login_staff()
        res = self.client.get("/admin/scanner")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Gate Check-In Scanner", res.data)
        self.assertIn(b"National Hackathon", res.data)
        self.assertIn(b"manual-code-input", res.data)

    def test_successful_checkin_via_ticket_code(self):
        """Valid unused ticket code must successfully check in attendee with status 200."""
        self.login_staff()
        res = self.client.post("/api/checkin/verify", json={
            "code": "CE-1111-2222-3333",
            "event_id": 1
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["ticket"]["participant_name"], "Alice Walker")

        # Verify database state
        db = get_db(self.test_db_path)
        reg = db.execute("SELECT is_checked_in, checked_in_by FROM registrations WHERE id = 1").fetchone()
        self.assertEqual(reg["is_checked_in"], 1)
        self.assertEqual(reg["checked_in_by"], 1)

        # Verify audit log
        log = db.execute("SELECT status, attempted_by FROM checkin_logs WHERE registration_id = 1").fetchone()
        self.assertEqual(log["status"], "SUCCESS")

    def test_successful_checkin_via_qr_json_payload(self):
        """QR scanner emitting JSON payload with secret token must succeed."""
        self.login_staff()
        qr_payload = json.dumps({
            "ticket_code": "CE-1111-2222-3333",
            "secret": "secret-token-1111",
            "event_id": 1
        })
        res = self.client.post("/api/checkin/verify", json={
            "code": qr_payload,
            "event_id": 1
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["ticket"]["participant_name"], "Alice Walker")

    def test_already_used_ticket_rejection(self):
        """Scanning an already checked-in ticket must return 409 ALREADY_USED and record audit log."""
        self.login_staff()
        # Bob Smith (ID 2) is already seeded with is_checked_in = 1
        res = self.client.post("/api/checkin/verify", json={
            "code": "CE-4444-5555-6666",
            "event_id": 1
        })
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertEqual(data["status"], "ALREADY_USED")
        self.assertIn("already checked in", data["message"].lower())

        # Verify audit log recorded ALREADY_USED
        db = get_db(self.test_db_path)
        log = db.execute("SELECT status FROM checkin_logs WHERE registration_id = 2").fetchone()
        self.assertEqual(log["status"], "ALREADY_USED")

    def test_invalid_ticket_code_rejection(self):
        """Unrecognized ticket codes must return 404 INVALID_TICKET."""
        self.login_staff()
        res = self.client.post("/api/checkin/verify", json={
            "code": "CE-FAKE-CODE-0000",
            "event_id": 1
        })
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["status"], "INVALID_TICKET")

    def test_event_mismatch_rejection(self):
        """Scanning a ticket for Event 2 while scanning for Event 1 must return 400 EVENT_MISMATCH."""
        self.login_staff()
        # Charlie Brown has ticket for Event 2
        res = self.client.post("/api/checkin/verify", json={
            "code": "CE-7777-8888-9999",
            "event_id": 1 # Target Event 1 mismatch
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "EVENT_MISMATCH")
        self.assertIn("GenAI Workshop", data["message"])

    def test_concurrent_double_checkin_race_condition(self):
        """
        Concurrency Test:
        Simulate 10 simultaneous verification requests on the same unused ticket.
        Exactly 1 request must succeed (200 SUCCESS), and exactly 9 must fail (409 ALREADY_USED).
        """
        from app.services.checkin_service import verify_and_checkin

        results = []
        threads = []

        def worker():
            with self.app.app_context():
                # SQLite per-thread connection
                res = verify_and_checkin(
                    raw_input="CE-1111-2222-3333",
                    target_event_id=1,
                    attempted_by_user_id=1,
                    ip_address="127.0.0.1"
                )
                results.append(res)

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        conflict_count = sum(1 for r in results if r["status"] == "ALREADY_USED")

        self.assertEqual(len(results), 10)
        self.assertEqual(success_count, 1, f"Expected exactly 1 SUCCESS, got {success_count}")
        self.assertEqual(conflict_count, 9, f"Expected exactly 9 ALREADY_USED, got {conflict_count}")

if __name__ == "__main__":
    unittest.main()
