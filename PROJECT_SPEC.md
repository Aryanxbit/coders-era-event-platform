# Coders Era Event Platform — Project Specification

## 1. Executive Summary
**Coders Era Event Platform** is an end-to-end event management, registration, and cryptographic verification system engineered for developer communities, hackathons, college technical symposiums, and workshops.

The platform delivers a modern dark-mode tech aesthetic inspired by developer community hubs. Public platforms like `codersera.in` serve strictly as an external, read-only visual reference for styling, dark themes, and typography. This project is an independent college submission and does not modify, deploy to, or claim ownership of any third-party domain or trademarked assets.

---

## 2. Target Personas & Stakeholder Stories

### 2.1 Event Organizer / Club Lead
- **Goal:** Create events, customize registration questions, track registration velocity, inspect attendance metrics in real time, and export verified records for certificates and college attendance.
- **Story:** *"As an organizer, I want to publish a hackathon, view live attendance telemetry as participants arrive, and download a CSV of verified attendees after the event."*

### 2.2 Participant / Student Developer
- **Goal:** Discover technical events, register seamlessly, and immediately receive a verifiable digital badge/ticket with a unique QR code.
- **Story:** *"As a student, I want to register for a workshop, receive immediate confirmation, and view or download a sleek QR ticket to present at the check-in desk."*

### 2.3 Registration Desk Volunteer / Gatekeeper
- **Goal:** Verify incoming attendees quickly using a smartphone camera or laptop webcam, preventing badge sharing, forged tickets, or double-entry.
- **Story:** *"As a volunteer at the venue gate, I want to scan an attendee's QR code or manually enter their Ticket ID and receive instant verification feedback."*

---

## 3. Scope Boundary: Core MVP vs. Optional Features

This project is planned for a time-limited college project submission. Therefore, execution is strictly prioritized on the **Core MVP**.

### 3.1 Core MVP (Mandatory Deliverables)
All development prioritizes these essential items:
1. **Public Event Landing Page:** Modern, responsive event showcase with event details, venue logistics, and countdown.
2. **Registration Form:** Online form supporting participant details and custom event questions.
3. **Duplicate Registration Prevention:** Enforces unique participant email per event.
4. **Unique Secure Ticket ID:** Generates unpredictable `CE-XXXX-XXXX-XXXX` codes backed by 256-bit cryptographic secrets.
5. **QR Digital Ticket:** Rendered digital ticket badge displaying attendee details, Ticket ID, and QR code with PNG/print support.
6. **Organizer Authentication:** Secure login and session management for event staff.
7. **Admin Dashboard:** Real-time summary of total registrations, checked-in count, pending count, and attendance percentage.
8. **Participant Management & Search:** Searchable directory of registered attendees with query filtering.
9. **In-Browser QR Scanner:** Mobile camera QR scanner using `html5-qrcode` without requiring native app installs.
10. **Manual Ticket ID Verification:** Fallback input for typing ticket codes directly.
11. **Atomic One-Time Check-In:** Concurrency-proof check-in preventing duplicate admissions.
12. **Attendance Statistics:** Real-time telemetry calculations.
13. **CSV Export:** One-click download of participant roster and custom question responses.

### 3.2 Optional Features (Strictly Post-MVP, Non-Blocking)
The following items are optional extensions and must **NOT** block the delivery of the Core MVP:
- Automated email delivery of tickets (via SMTP / SendGrid).
- JSON data export.
- Sound effects (success chimes / error buzzers).
- Advanced multi-chart analytics.
- Complex micro-animations and particle effects.
- Multi-day / multi-session tracking.

---

## 4. Functional Requirements (Core MVP)

### 4.1 Event Management & Landing Page
- **FR-1.1:** Organizers can create and view events with Title, Tagline, Category, Mode (Offline/Online/Hybrid), Venue, Start/End Time, Registration Deadline, and Capacity.
- **FR-1.2:** Dynamic Form Configuration: Support custom questions (e.g. Roll Number, GitHub, Branch) stored as JSON.
- **FR-1.3:** Public landing page displaying event information and responsive layout for mobile and desktop.

### 4.2 Registration & Ticket Generation
- **FR-2.1:** Online registration validating name, email, phone, and dynamic fields.
- **FR-2.2:** Duplicate check: Rejects repeat registration for the same email on the same event with a clear status message.
- **FR-2.3:** Ticket Generation: Creates unpredictable `CE-XXXX-XXXX-XXXX` Ticket ID and 256-bit URL secret.
- **FR-2.4:** Digital Ticket: Displays event details, attendee info, unique ID, and QR code.

### 4.3 Secure Check-In & Gate Verification
- **FR-3.1:** In-browser QR camera scanner supporting mobile and desktop cameras.
- **FR-3.2:** Manual Ticket ID input fallback for damaged screens or manual entry.
- **FR-3.3 (Atomic One-Time Check-In):**
  - First valid scan: Marks `is_checked_in = 1`, records timestamp and operator ID. Returns **200 SUCCESS**.
  - Subsequent scan: Returns **409 CONFLICT: ALREADY CHECKED IN** with previous check-in time and staff name.
  - Invalid/Fake scan: Returns **404 NOT FOUND: INVALID TICKET**.
  - Event mismatch: Returns **400 BAD REQUEST: WRONG EVENT**.
- **FR-3.4:** Audit logging of every check-in attempt into `checkin_logs`.

### 4.4 Admin Dashboard & Attendee Management
- **FR-4.1:** Dashboard cards for Total Registrations, Checked-In Attendees, Pending Attendees, and Attendance Percentage.
- **FR-4.2:** Participant directory with real-time text search (name, email, ticket code) and status filtering.
- **FR-4.3:** CSV Export generating a spreadsheet of all participants with custom field columns.

---

## 5. Non-Functional Requirements

| Requirement | Specification | Implementation Detail |
| :--- | :--- | :--- |
| **Check-In Latency** | Fast verification response suitable for real-time event check-in | B-Tree indexed lookups on `ticket_code` and `ticket_secret` in SQLite with WAL mode. |
| **Concurrency & Integrity** | Zero double-entry race conditions | Single-statement SQL `UPDATE ... WHERE id = :id AND is_checked_in = 0` with rowcount validation. |
| **Responsiveness** | Mobile-friendly and responsive | CSS Grid/Flexbox layout optimized for smartphones and desktop viewports. |
| **Simplicity & Zero Build** | Direct execution without build complexity | Python 3.14 + Flask 3.x + Vanilla HTML/CSS/JS. No compilation or bundlers required. |
| **Security** | OWASP Top 10 compliance | PBKDF2 password hashing, parameterized SQL queries, authenticated admin routes. |

---

## 6. Project Timeline & Development Freeze Policy

- **Core Feature Freeze Deadline:** **September 17, 2026 (End of Day)**
  - All 13 Core MVP features, backend endpoints, database models, frontend interfaces, and concurrency safeguards must be 100% finished, integrated, and stable by this date.
  - The application must be **demo-ready and stable** at the close of September 17.
  - **No major new features will be introduced after September 17.**
- **Buffer & Submission Date:** **September 18, 2026**
  - Strictly reserved for:
    1. Final end-to-end verification and cross-device testing.
    2. Minor edge-case bug fixes.
    3. Final copy/text and cosmetic adjustments.
    4. Demonstration & presentation rehearsal.
    5. Final academic submission.
