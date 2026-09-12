import unittest
import json
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.config import TestingConfig
from app.db import init_db

TEST_DB_PATH = Path(__file__).resolve().parent / "test_rbac.db"

class RBACTestConfig(TestingConfig):
    DATABASE_PATH = str(TEST_DB_PATH)

class RBACTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config.from_object(RBACTestConfig)
        self.client = self.app.test_client()

        # Re-initialize DB
        init_db(str(TEST_DB_PATH))
        self.seed_test_data()

    def tearDown(self):
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except PermissionError:
                pass

    def seed_test_data(self):
        conn = sqlite3.connect(str(TEST_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Create Organizer User
        cursor.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('org-uuid', 'organizer@codersera.in', ?, 'Organizer User', 'organizer')
        """, (generate_password_hash("Admin@123", method="pbkdf2:sha256"),))
        self.org_id = cursor.lastrowid

        # 2. Create Volunteer User
        cursor.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('vol-uuid', 'volunteer@codersera.in', ?, 'Gate Volunteer', 'volunteer')
        """, (generate_password_hash("Volunteer@123", method="pbkdf2:sha256"),))
        self.vol_id = cursor.lastrowid

        # 3. Create Sample Event
        cursor.execute("""
            INSERT INTO events (
                uuid, slug, title, tagline, description, category, mode,
                venue, start_time, end_time, registration_deadline,
                max_capacity, status, custom_fields_json, created_by
            ) VALUES (
                'event-uuid', 'hack-test', 'Hack Test', 'Tagline', 'Description',
                'Hackathon', 'offline', 'Tech Hall', '2026-09-25 09:00:00',
                '2026-09-26 17:00:00', '2026-09-24 23:59:59', 100,
                'published', '[]', ?
            )
        """, (self.org_id,))
        self.event_id = cursor.lastrowid

        # 4. Create Sample Registration
        cursor.execute("""
            INSERT INTO registrations (
                ticket_code, ticket_secret, event_id, participant_name,
                participant_email, participant_phone, answers_json,
                status, is_checked_in
            ) VALUES (
                'CE-TEST-1234', 'testsecrettoken1234567890123456', ?, 'Aarav Test',
                'aarav@example.com', '+91 9999999999', '{}', 'confirmed', 0
            )
        """, (self.event_id,))
        self.reg_id = cursor.lastrowid

        conn.commit()
        conn.close()

    def login_as_organizer(self):
        return self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "Admin@123"
        }, follow_redirects=False)

    def login_as_volunteer(self):
        return self.client.post("/admin/login", data={
            "email": "volunteer@codersera.in",
            "password": "Volunteer@123"
        }, follow_redirects=False)

    # -------------------------------------------------------------------------
    # 1. Login Redirection Separation
    # -------------------------------------------------------------------------

    def test_organizer_login_redirects_to_dashboard(self):
        """Organizer logging in without next param should redirect to /admin/dashboard."""
        res = self.login_as_organizer()
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers["Location"], "/admin/dashboard")

    def test_volunteer_login_redirects_to_scanner(self):
        """Volunteer logging in without next param should land directly on /admin/scanner."""
        res = self.login_as_volunteer()
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers["Location"], "/admin/scanner")

    # -------------------------------------------------------------------------
    # 2. Organizer Full Access Tests
    # -------------------------------------------------------------------------

    def test_organizer_can_access_dashboard_and_telemetry(self):
        """Organizer must have full access to dashboard and telemetry API."""
        self.login_as_organizer()

        dash_res = self.client.get("/admin/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Command & Telemetry Console", dash_res.data)

        tel_res = self.client.get("/admin/api/telemetry")
        self.assertEqual(tel_res.status_code, 200)
        tel_data = tel_res.get_json()
        self.assertEqual(tel_data["total_registrations"], 1)

    def test_organizer_can_access_event_management_and_create_events(self):
        """Organizer must be able to view events list and publish new events."""
        self.login_as_organizer()

        events_res = self.client.get("/admin/events")
        self.assertEqual(events_res.status_code, 200)

        create_res = self.client.post("/admin/events/new", data={
            "title": "New Workshop 2026",
            "slug": "new-workshop-2026",
            "venue": "Lab 1",
            "start_time": "2026-10-01 10:00:00",
            "end_time": "2026-10-01 16:00:00"
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b"New Workshop 2026", create_res.data)

    def test_organizer_can_access_participants_and_export_csv(self):
        """Organizer must be able to view participant roster, details API, and CSV export."""
        self.login_as_organizer()

        parts_res = self.client.get("/admin/participants")
        self.assertEqual(parts_res.status_code, 200)
        self.assertIn(b"Aarav Test", parts_res.data)

        detail_res = self.client.get(f"/admin/participants/{self.reg_id}")
        self.assertEqual(detail_res.status_code, 200)

        csv_res = self.client.get(f"/admin/export/{self.event_id}.csv")
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(csv_res.mimetype, "text/csv")
        self.assertIn(b"Aarav Test", csv_res.data)

    def test_organizer_can_access_scanner(self):
        """Organizer must be able to access the QR scanner console."""
        self.login_as_organizer()
        scanner_res = self.client.get("/admin/scanner")
        self.assertEqual(scanner_res.status_code, 200)
        self.assertIn(b"Gate Check-In Scanner", scanner_res.data)
        self.assertIn(b"Back to Dashboard", scanner_res.data)

    # -------------------------------------------------------------------------
    # 3. Volunteer Access & Restrictions Tests
    # -------------------------------------------------------------------------

    def test_volunteer_can_access_scanner_and_checkin(self):
        """Volunteer must be able to view scanner and execute check-in verifications."""
        self.login_as_volunteer()

        scanner_res = self.client.get("/admin/scanner")
        self.assertEqual(scanner_res.status_code, 200)
        self.assertIn(b"Gate Check-In Scanner", scanner_res.data)
        self.assertIn(b"Gate Volunteer Station", scanner_res.data)

        # Check-in API works for volunteer
        verify_res = self.client.post("/api/checkin/verify", json={
            "code": "CE-TEST-1234",
            "event_id": self.event_id
        })
        self.assertEqual(verify_res.status_code, 200)
        verify_data = verify_res.get_json()
        self.assertEqual(verify_data["status"], "SUCCESS")

    def test_volunteer_cannot_access_dashboard_or_telemetry(self):
        """Volunteer accessing /admin/dashboard must be redirected to scanner, and telemetry API returns 403."""
        self.login_as_volunteer()

        # UI route redirects to /admin/scanner with flash message
        dash_res = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(dash_res.status_code, 302)
        self.assertEqual(dash_res.headers["Location"], "/admin/scanner")

        # Telemetry API returns 403 Forbidden
        tel_res = self.client.get("/admin/api/telemetry")
        self.assertEqual(tel_res.status_code, 403)
        self.assertIn("error", tel_res.get_json())

    def test_volunteer_cannot_access_event_management(self):
        """Volunteer accessing /admin/events or /admin/events/new must be denied."""
        self.login_as_volunteer()

        events_res = self.client.get("/admin/events", follow_redirects=False)
        self.assertEqual(events_res.status_code, 302)
        self.assertEqual(events_res.headers["Location"], "/admin/scanner")

        new_ev_res = self.client.post("/admin/events/new", data={
            "title": "Unauthorized Event"
        }, follow_redirects=False)
        self.assertEqual(new_ev_res.status_code, 302)
        self.assertEqual(new_ev_res.headers["Location"], "/admin/scanner")

    def test_volunteer_cannot_access_participants_or_csv_export(self):
        """Volunteer accessing /admin/participants or /admin/export/*.csv must be rejected."""
        self.login_as_volunteer()

        parts_res = self.client.get("/admin/participants", follow_redirects=False)
        self.assertEqual(parts_res.status_code, 302)
        self.assertEqual(parts_res.headers["Location"], "/admin/scanner")

        detail_res = self.client.get(f"/admin/participants/{self.reg_id}")
        self.assertEqual(detail_res.status_code, 403)

        csv_res = self.client.get(f"/admin/export/{self.event_id}.csv")
        self.assertEqual(csv_res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
