# Coders Era Event Platform — Implementation Tracker (TODO)

This document tracks all deliverables for the **Coders Era Event Platform**, strictly prioritizing the **Core MVP** for college project submission by **September 17, 2026**.

---

## 🛑 Development Freeze Policy

> [!IMPORTANT]
> **HARD DEVELOPMENT FREEZE: SEPTEMBER 17, 2026 (End of Day)**
> - The application must be **feature-complete, stable, and demo-ready** by the end of September 17, 2026.
> - **DO NOT introduce major new features after September 17.**
> - September 18, 2026 is strictly reserved for final verification, minor edge-case bug fixes, demo practice, and project submission.

---

## 📅 Timeline & Milestone Gates

- **September 10:** Phase 1 — Environment & Core Database Foundation
- **September 11:** Phase 2 — Organizer Authentication & Admin Dashboard
- **September 12–13:** Phase 3 — Public Event Landing, Dynamic Form & Digital Ticket
- **September 14–15:** Phase 4 — Fast QR Scanner & Atomic Check-In
- **September 16:** Phase 5 — Participant Directory & CSV Export
- **September 17:** Phase 6 — Concurrency Verification, Integration & **DEVELOPMENT FREEZE**
- **September 18:** Buffer & Final Submission Day (Zero new features)

---

## 🎯 Core MVP Checklist (Priority 1 — Target: By Sept 17)

- [ ] **Public Event Landing Page:** Responsive event showcase with event logistics and countdown.
- [ ] **Registration Form:** Dynamic online form supporting attendee info and custom questions.
- [ ] **Duplicate Registration Prevention:** Enforce unique email per event in SQLite.
- [ ] **Unique Secure Ticket ID:** Generation of `CE-XXXX-XXXX-XXXX` and 256-bit secret token.
- [ ] **QR Digital Ticket:** Rendered boarding pass ticket with QR code and download/print support.
- [ ] **Organizer Authentication:** Session-based login/logout for event staff with PBKDF2 hashing.
- [ ] **Admin Dashboard:** Overview telemetry (Total, Checked-In, Pending, Attendance %).
- [ ] **Participant Management & Search:** Searchable directory with live text filter.
- [ ] **In-Browser QR Scanner:** Mobile camera QR code scanner using `html5-qrcode`.
- [ ] **Manual Ticket ID Verification:** Fallback text input for typing ticket codes.
- [ ] **Atomic One-Time Check-In:** Concurrency-proof SQL update preventing duplicate entries.
- [ ] **Attendance Statistics:** Live calculated metrics.
- [ ] **CSV Export:** Downloadable spreadsheet of attendees including custom question answers.

---

## ⏳ Optional Features Checklist (Priority 2 — Post-MVP / Non-Blocking)
*These features must NOT block the delivery of the Core MVP:*
- [ ] Automated email delivery of tickets via SMTP / SendGrid.
- [ ] JSON data export endpoint.
- [ ] Audio feedback (chimes and buzzer sound files).
- [ ] Advanced multi-chart telemetry graphs.
- [ ] Particle and micro-interaction animations.
- [ ] Multi-day / session check-in logs.

---

## 📋 Phased Execution Schedule (Sept 10 – Sept 17)

### Phase 1: Environment & Core Database Foundation (Target: Sept 10) — COMPLETED
- [x] Setup Python virtual environment (`venv`)
- [x] Create `requirements.txt` with minimal dependencies (`flask`, `qrcode`, `pillow`, `werkzeug`, `python-dotenv`)
- [x] Implement `app/config.py` with environment variable handling and secure defaults
- [x] Build `app/db.py` SQLite connection manager with WAL mode, foreign keys, and `sqlite3.Row` factory
- [x] Write `app/schema.sql` with tables (`users`, `events`, `registrations`, `checkin_logs`) and indexes
- [x] Write `app/seed.py` to populate initial organizer account and sample hackathon event with safe PBKDF2 hashing
- [x] Create base HTML layout (`base.html`) and design system (`main.css`) with Coders Era dark theme
- [x] Create `run.py` entry point and verify `/api/health` and `/` endpoints return 200 OK

### Phase 2: Organizer Authentication & Admin Dashboard (Target: Sept 11) — COMPLETED
- [x] Implement `app/services/auth_service.py` (PBKDF2 password hashing & verification)
- [x] Build login (`/admin/login`) and logout session routes in `app/routes/auth_routes.py`
- [x] Implement `@login_required` and `@role_required` decorators
- [x] Build admin dashboard (`/admin/dashboard`) showing live metrics:
  - Total Registrations
  - Total Checked-in
  - Pending Check-ins
  - Attendance Percentage
- [x] Implement event creation and management page (`/admin/events`) with custom fields configuration
- [x] Build live telemetry API endpoint (`/admin/api/telemetry`)
- [x] Implement unit & integration test suite (`tests/test_phase2.py`) with 7/7 tests passing

### Phase 3: Public Event Landing, Dynamic Form & Digital Ticket (Target: Sept 12–13) — COMPLETED
- [x] Build public event discovery and details page (`/event/<slug>`)
- [x] Implement dynamic registration form rendering and validation
- [x] Enforce unique `(event_id, participant_email)` duplicate prevention
- [x] Implement `app/services/ticket_service.py`:
  - `ticket_code`: `CE-XXXX-XXXX-XXXX`
  - `ticket_secret`: 256-bit random token
  - Dynamic QR code generation with Python `qrcode`
- [x] Build digital boarding pass ticket view (`/ticket/<ticket_code>`) with PNG/print options
- [x] Implement unit & integration test suite (`tests/test_phase3.py`) with 8/8 tests passing (15/15 overall)

### Phase 4: Fast QR Scanner & Atomic Check-In (Target: Sept 14–15)
- [ ] Build mobile-optimized scanner view (`/admin/scanner`) using `html5-qrcode`
- [ ] Build manual Ticket ID input box fallback
- [ ] Implement atomic check-in transaction in `app/services/checkin_service.py`:
  - `UPDATE registrations SET is_checked_in = 1 ... WHERE id = :id AND is_checked_in = 0`
  - Inspect `cursor.rowcount` (1 = SUCCESS, 0 = ALREADY_USED)
- [ ] Implement `/api/checkin/verify` route returning structured JSON responses:
  - `200 OK`: Verified
  - `409 CONFLICT`: Already checked in (with timestamp and staff details)
  - `404 NOT FOUND`: Invalid ticket
  - `400 BAD REQUEST`: Ticket for different event
- [ ] Record audit trail entry in `checkin_logs`
- [ ] Instant visual status feedback modal (Green for success, Red for rejection)

### Phase 5: Participant Management & CSV Export (Target: Sept 16) — COMPLETED
- [x] Build searchable participant roster (`/admin/participants`)
- [x] Implement instant search filter (by name, email, or ticket code)
- [x] Implement per-registration detail modal via `/admin/participants/<id>` JSON API
- [x] Implement CSV exporter (`app/services/export_service.py`) including custom question responses
- [x] Implement unit & integration test suite (`tests/test_phase5.py`) with 14/14 tests passing (37/37 overall)

### Phase 6: System Integration & Concurrency Verification (Target: Sept 17 — Development Freeze)
- [ ] Verify full end-to-end user flow: Event view -> Register -> Ticket -> Admin login -> Scan -> Verify duplicate rejection
- [ ] Test check-in concurrency with multi-threaded verification script
- [ ] Verify mobile layout responsiveness on smartphone viewports
- [ ] **ENFORCE FEATURE FREEZE:** Lock down all core functionality; ensure application is stable and demo-ready

---

## 🛡️ Buffer & Submission Day (September 18 ONLY)
- [ ] Final end-to-end regression testing on a clean browser profile
- [ ] Fix any remaining minor edge cases or cosmetic bugs
- [ ] Final text, label, and copy refinements
- [ ] Rehearse live college viva demo walkthrough (per `README.md` guide)
- [ ] Final project submission
