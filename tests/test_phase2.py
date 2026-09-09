import os
import sys
import unittest
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import get_db, init_db
from werkzeug.security import generate_password_hash

class Phase2TestCase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = str(PROJECT_ROOT / "test_coders_era.db")
        # Remove any existing test DB file
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.app = create_app("testing")
        self.app.config["DATABASE_PATH"] = self.test_db_path
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize test database schema
        init_db(self.test_db_path)
        db = get_db(self.test_db_path)
        
        # Seed test organizer
        pw_hash = generate_password_hash("ValidSecret123!", method="pbkdf2:sha256")
        db.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('test-uuid-1', 'organizer@codersera.in', ?, 'Test Organizer', 'admin')
        """, (pw_hash,))
        
        # Seed test event
        db.execute("""
            INSERT INTO events (
                uuid, slug, title, tagline, description, category, mode,
                venue, start_time, end_time, registration_deadline,
                max_capacity, status, custom_fields_json, created_by
            ) VALUES (
                'event-uuid-1', 'test-hackathon', 'Test Hackathon 2026', 'Building cool apps',
                'Detailed description', 'Hackathon', 'offline', 'Lab 1',
                '2026-09-25 10:00:00', '2026-09-26 10:00:00', '2026-09-24 23:59:59',
                100, 'published', '[]', 1
            )
        """)
        
        # Seed two registrations: one checked in, one pending
        db.execute("""
            INSERT INTO registrations (
                ticket_code, ticket_secret, event_id, participant_name,
                participant_email, status, is_checked_in, checked_in_at
            ) VALUES 
            ('CE-0001-AAAA', 'sec1', 1, 'Attendee One', 'one@example.com', 'confirmed', 1, CURRENT_TIMESTAMP),
            ('CE-0002-BBBB', 'sec2', 1, 'Attendee Two', 'two@example.com', 'confirmed', 0, NULL)
        """)
        
        # Seed checkin log
        db.execute("""
            INSERT INTO checkin_logs (registration_id, event_id, scanned_code, status, attempted_by)
            VALUES (1, 1, 'CE-0001-AAAA', 'SUCCESS', 1)
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

    def test_unauthenticated_dashboard_redirects(self):
        """Unauthenticated requests to /admin/dashboard must redirect to /admin/login."""
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_login_page_renders(self):
        """Login page must render successfully with status 200."""
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Organizer Access", response.data)

    def test_invalid_login_rejected(self):
        """Invalid credentials must show error and reject login."""
        response = self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "WrongPassword!"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email or password", response.data)

    def test_successful_login_and_dashboard_telemetry(self):
        """Valid credentials must authenticate session and load dashboard telemetry."""
        response = self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "ValidSecret123!"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Command & Telemetry Console", response.data)
        self.assertIn(b"Total Registrations", response.data)
        # Check that metrics render correctly: 2 registered, 1 checked-in, 50.0% rate
        self.assertIn(b"50.0%", response.data)

    def test_telemetry_api(self):
        """API /admin/api/telemetry must return accurate real-time stats."""
        # Authenticate first
        self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "ValidSecret123!"
        })
        response = self.client.get("/admin/api/telemetry")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total_registrations"], 2)
        self.assertEqual(data["total_checked_in"], 1)
        self.assertEqual(data["total_pending"], 1)
        self.assertEqual(data["attendance_rate"], 50.0)

    def test_event_creation(self):
        """Organizers must be able to create events with custom question schemas."""
        self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "ValidSecret123!"
        })
        response = self.client.post("/admin/events/new", data={
            "title": "Synapse Masterclass",
            "slug": "synapse-masterclass",
            "category": "Masterclass",
            "mode": "offline",
            "venue": "Lab 4",
            "start_time": "2026-09-22T10:00",
            "end_time": "2026-09-22T16:00",
            "max_capacity": "80",
            "tagline": "Hands-on Masterclass",
            "custom_fields_json": '[{"id":"roll","label":"Roll Number","type":"text","required":true}]'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Synapse Masterclass", response.data)

    def test_logout(self):
        """Logging out must clear session and redirect to login."""
        self.client.post("/admin/login", data={
            "email": "organizer@codersera.in",
            "password": "ValidSecret123!"
        })
        response = self.client.post("/admin/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You have been securely logged out", response.data)

        # Confirm dashboard is no longer accessible
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)

if __name__ == "__main__":
    unittest.main()
