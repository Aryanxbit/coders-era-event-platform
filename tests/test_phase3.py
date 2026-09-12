import os
import sys
import json
import unittest
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import get_db, init_db
from app.services.ticket_service import (
    generate_ticket_code,
    generate_ticket_secret,
    generate_qr_code_data_url,
    TICKET_CODE_REGEX
)

class Phase3TestCase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = str(PROJECT_ROOT / "test_coders_era_p3.db")
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
        db.execute("""
            INSERT INTO users (uuid, email, password_hash, full_name, role)
            VALUES ('organizer-uuid', 'organizer@codersera.in', 'fakehash', 'Lead Organizer', 'admin')
        """)

        # Seed event with dynamic custom fields and capacity of 2
        custom_fields = [
            {
                "id": "roll_no",
                "label": "Student Roll Number",
                "type": "text",
                "required": True,
                "placeholder": "e.g. 21CS045"
            },
            {
                "id": "branch",
                "label": "Branch / Department",
                "type": "select",
                "required": True,
                "options": ["CSE", "IT", "AI", "ECE"]
            }
        ]

        db.execute("""
            INSERT INTO events (
                uuid, slug, title, tagline, description, category, mode,
                venue, start_time, end_time, registration_deadline,
                max_capacity, status, custom_fields_json, created_by
            ) VALUES (
                'event-uuid-p3', 'hack-india-2026', 'Hack India 2026', '24hr Hackathon',
                'Join us to build cutting-edge software.', 'Hackathon', 'offline',
                'Tech Auditorium', '2026-09-25 09:00:00', '2026-09-26 17:00:00',
                '2026-09-24 23:59:59', 2, 'published', ?, 1
            )
        """, (json.dumps(custom_fields),))
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

    def test_ticket_code_and_secret_generation(self):
        """Ticket code must match CE-XXXX-XXXX-XXXX format and secret must have 256-bit entropy."""
        for _ in range(20):
            code = generate_ticket_code()
            self.assertTrue(TICKET_CODE_REGEX.match(code), f"Code '{code}' did not match regex pattern")
            
            secret = generate_ticket_secret()
            # 32 bytes base64 url-safe is ~43 chars
            self.assertGreaterEqual(len(secret), 40)

    def test_qr_code_generation(self):
        """QR code generation must return valid Base64 PNG data URL."""
        data_url = generate_qr_code_data_url("test-payload-12345")
        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertGreater(len(data_url), 100)

    def test_public_event_page_renders(self):
        """Public event detail page must render event info and registration form."""
        response = self.client.get("/event/hack-india-2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hack India 2026", response.data)
        self.assertIn(b"Tech Auditorium", response.data)
        self.assertIn(b"Student Roll Number", response.data)
        self.assertIn(b"Claim Your Pass", response.data)

    def test_successful_registration_and_ticket_redirect(self):
        """Submitting valid registration form must redirect to digital ticket pass."""
        response = self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "Dev Sharma",
            "participant_email": "dev.sharma@example.com",
            "participant_phone": "+91 9988776655",
            "custom_roll_no": "21CS099",
            "custom_branch": "CSE"
        })
        self.assertEqual(response.status_code, 302)
        redirect_url = response.headers["Location"]
        self.assertIn("/ticket/CE-", redirect_url)

        # Follow redirect and verify ticket pass view
        ticket_res = self.client.get(redirect_url)
        self.assertEqual(ticket_res.status_code, 200)
        self.assertIn(b"Dev Sharma", ticket_res.data)
        self.assertIn(b"dev.sharma@example.com", ticket_res.data)
        self.assertIn(b"Hack India 2026", ticket_res.data)
        self.assertIn(b"21CS099", ticket_res.data)
        self.assertIn(b"data:image/png;base64,", ticket_res.data)

    def test_duplicate_email_registration_rejected(self):
        """Duplicate registration for the same event with same email must be strictly rejected."""
        # 1. First registration succeeds
        self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "Dev Sharma",
            "participant_email": "dev.sharma@example.com",
            "custom_roll_no": "21CS099",
            "custom_branch": "CSE"
        })

        # 2. Duplicate registration attempt
        response = self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "Dev Sharma Duplicate",
            "participant_email": "dev.sharma@example.com",
            "custom_roll_no": "21CS099",
            "custom_branch": "CSE"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already registered for this event", response.data)

    def test_missing_required_custom_field_rejected(self):
        """Omission of required custom field must be rejected."""
        response = self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "Dev Sharma",
            "participant_email": "dev.different@example.com",
            "custom_roll_no": "",  # Missing required field
            "custom_branch": "CSE"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Roll Number", response.data)
        self.assertIn(b"required", response.data)

    def test_capacity_limit_enforcement(self):
        """Registration must be blocked when event capacity is reached."""
        # Register attendee 1 (Capacity is 2)
        self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "User 1",
            "participant_email": "user1@example.com",
            "custom_roll_no": "21CS001",
            "custom_branch": "CSE"
        })

        # Register attendee 2
        self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "User 2",
            "participant_email": "user2@example.com",
            "custom_roll_no": "21CS002",
            "custom_branch": "IT"
        })

        # Register attendee 3 -> Should fail
        response = self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "User 3",
            "participant_email": "user3@example.com",
            "custom_roll_no": "21CS003",
            "custom_branch": "AI"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"maximum participant capacity", response.data)

    def test_public_event_and_ticket_rest_apis(self):
        """REST APIs for event details, registration, and ticket lookup."""
        # 1. GET /api/events/<slug>
        res = self.client.get("/api/events/hack-india-2026")
        self.assertEqual(res.status_code, 200)
        ev_data = res.get_json()
        self.assertEqual(ev_data["slug"], "hack-india-2026")
        self.assertEqual(len(ev_data["custom_fields"]), 2)

        # 2. POST /api/events/<slug>/register
        reg_res = self.client.post("/api/events/hack-india-2026/register", json={
            "participant_name": "API User",
            "participant_email": "api.user@example.com",
            "participant_phone": "+91 9123456780",
            "custom_roll_no": "22CS100",
            "custom_branch": "AI"
        })
        self.assertEqual(reg_res.status_code, 201)
        reg_data = reg_res.get_json()
        self.assertTrue(reg_data["success"])
        ticket_code = reg_data["ticket_code"]
        self.assertTrue(TICKET_CODE_REGEX.match(ticket_code))

        # 3. Duplicate POST /api/events/<slug>/register returns 409
        dup_res = self.client.post("/api/events/hack-india-2026/register", json={
            "participant_name": "API User",
            "participant_email": "api.user@example.com",
            "custom_roll_no": "22CS100",
            "custom_branch": "AI"
        })
        self.assertEqual(dup_res.status_code, 409)

        # 4. GET /api/tickets/<ticket_code> returns 200 with ticket data
        tick_res = self.client.get(f"/api/tickets/{ticket_code}")
        self.assertEqual(tick_res.status_code, 200)
        tick_data = tick_res.get_json()
        self.assertEqual(tick_data["ticket_code"], ticket_code)
        self.assertEqual(tick_data["participant_email"], "api.user@example.com")
        self.assertEqual(tick_data["is_checked_in"], False)

    def test_ticket_retrieve_success_and_failures(self):
        """Ticket retrieval page and secure lookup verification."""
        # 1. Page renders
        get_res = self.client.get("/ticket/retrieve")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(b"Retrieve Your Ticket", get_res.data)

        # 2. Register a participant
        reg_res = self.client.post("/event/hack-india-2026/register", data={
            "participant_name": "Rohan Verma",
            "participant_email": "rohan.verma@example.com",
            "custom_roll_no": "22CS088",
            "custom_branch": "CSE"
        })
        ticket_code = reg_res.headers["Location"].split("/ticket/")[1]

        # 3. Successful retrieval with matching email and ticket_code
        post_res = self.client.post("/ticket/retrieve", data={
            "email": "rohan.verma@example.com",
            "ticket_code": ticket_code
        })
        self.assertEqual(post_res.status_code, 302)
        self.assertEqual(post_res.headers["Location"], f"/ticket/{ticket_code}")

        # 4. Failed retrieval with mismatched email
        fail_res = self.client.post("/ticket/retrieve", data={
            "email": "wrong.email@example.com",
            "ticket_code": ticket_code
        }, follow_redirects=True)
        self.assertEqual(fail_res.status_code, 200)
        self.assertIn(b"No matching ticket found", fail_res.data)

if __name__ == "__main__":
    unittest.main()

