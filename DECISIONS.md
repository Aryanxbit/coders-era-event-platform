# Coders Era Event Platform — Architectural Decision Records (ADRs)

This document records key technical, architectural, and design decisions made for the **Coders Era Event Platform**, along with their context, trade-offs, and rationale.

---

## ADR 001: Technology Stack Selection (Python Flask + SQLite)

### Status: APPROVED
### Context
The user requested a practical, beginner-friendly, and robust tech stack suitable for a college project technical submission, easy to demonstrate in viva interviews, and achievable within a limited timeline.
System verification confirmed:
- **Python 3.14.5** is installed natively with `pip`.
- **Node v24.21.0** and **npm 11.19.0** (via `npm.cmd`) are installed and verified.
- **Git 2.55.0.windows.3** is installed.

### Decision
Despite the availability of Node.js, we intentionally adopt **Python (Flask 3.x) with SQLite and Modern Vanilla HTML5/CSS3/ES6**.

### Rationale & Trade-offs
1. **Deadline Feasibility:** Flask requires minimal boilerplate and eliminates complex compilation steps, frontend framework build pipelines, and hydration overhead.
2. **Academic & Viva Value:** Examiners can easily inspect clean Python routes, standard relational SQL queries, and explicit ACID transactions without wrestling with complex state stores or opaque node_modules.
3. **Single Process Architecture:** The entire system runs from a single command (`python run.py`), hosting both the API and the static/template client without needing reverse proxies or separate dev servers.

---

## ADR 002: Frontend Styling Architecture (Custom Vanilla CSS Design System)

### Status: APPROVED
### Context
The platform requires a modern developer aesthetic inspired by the Coders Era community (dark midnight navy, electric violet accents, cyber cyan highlights, and glassmorphic cards).

### Decision
Implement a bespoke **Vanilla CSS Design System** using CSS Custom Properties (variables) and modular stylesheets (`main.css`, `dashboard.css`, `ticket.css`).

### Rationale
- Zero build tools or compilation steps required.
- Instant loading and complete offline rendering capability during college presentations.
- Complete control over animations, glassmorphic cards, and mobile responsiveness.

---

## ADR 003: Atomic Concurrency Control for One-Time Check-In

### Status: APPROVED
### Context
A core requirement is that once a ticket is checked in, it must NEVER be accepted again for the same event, even if scanned simultaneously at two different gates (Time-of-Check to Time-of-Use race condition).

### Decision
Implement single-statement atomic updates:
```sql
UPDATE registrations
SET is_checked_in = 1,
    checked_in_at = CURRENT_TIMESTAMP,
    checked_in_by = :user_id
WHERE id = :ticket_id
  AND is_checked_in = 0;
```
Inspect `cursor.rowcount`:
- `rowcount == 1`: Verification granted (HTTP 200).
- `rowcount == 0`: Verification rejected (HTTP 409 Conflict).

### Rationale
- Guaranteed atomic execution backed by SQLite's transactional engine.
- 100% immune to race conditions without requiring external distributed locks (e.g. Redis).

---

## ADR 004: In-Browser Mobile Camera Scanning (`html5-qrcode`)

### Status: APPROVED
### Context
Organizers need to scan QR codes quickly at event entry points.

### Decision
Integrate the lightweight **`html5-qrcode`** JavaScript library directly into the web application's `/admin/scanner` page with a manual code input fallback.

### Rationale
- Zero client installation: Organizers can use their phone's native browser.
- Operates on iOS Safari, Android Chrome, and desktop webcams.
- Manual fallback guarantees check-in continues even if a screen is scratched or camera permissions fail.

---

## ADR 005: Dual-Token Ticket Cryptography

### Status: APPROVED
### Context
Tickets must be easily read by humans over desk inquiries (`CE-XXXX-XXXX-XXXX`), while remaining immune to automated URL enumeration or guessing attacks.

### Decision
Implement a **Dual-Token Architecture**:
1. **Public Ticket Code (`ticket_code`):** Formatted uppercase hex code: `CE-XXXX-XXXX-XXXX`.
2. **Cryptographic Secret (`ticket_secret`):** High-entropy 32-byte URL-safe string (`secrets.token_urlsafe(32)`).

The QR code encodes a verification URL containing `ticket_secret`, while manual entry accepts `ticket_code` under authenticated organizer access.

---

## ADR 006: Core MVP Scope Prioritization

### Status: APPROVED
### Context
This project is built under college deadline constraints. Scope creep risks incomplete delivery.

### Decision
Strictly decouple the **Core MVP** from secondary optional features:
- **Core MVP (Must deliver):** Public event page, registration form, duplicate prevention, unique Ticket ID, QR digital ticket, organizer auth, admin dashboard, participant management/search, QR scanner, manual check-in fallback, atomic check-in, attendance statistics, CSV export.
- **Optional Features (Non-blocking):** Email delivery, JSON export, sound effects, complex particle animations, advanced multi-chart telemetry.

---

## ADR 007: Read-Only Design Reference Policy

### Status: APPROVED
### Context
The platform's design aesthetic is inspired by the Coders Era website (`codersera.in`).

### Decision
The public domain `codersera.in` is strictly treated as an external, read-only design and thematic reference.
- No modifications, deployments, or claims of ownership over that domain or third-party assets are permitted.
- The project is an independent college submission and retains clean, original asset implementations.

---

## ADR 008: Strict Development Freeze (September 17, 2026)

### Status: APPROVED
### Context
To avoid introducing regression bugs or destabilizing the codebase right before the final submission and evaluation, a hard development cutoff is necessary.

### Decision
Enforce a **Strict Development & Feature Freeze at the end of September 17, 2026**.
- By the end of September 17, 2026, the application must be 100% feature-complete, stable, and demo-ready.
- No new major features or architectural modifications may be introduced after this freeze.
- September 18, 2026 is strictly reserved for final verification, minor cosmetic/bug fixes, demo rehearsal, and project submission.

---

## ADR 009: Zero Hardcoded Credentials & Dynamic Password Resolution

### Status: APPROVED
### Context
Hardcoding default passwords (even for development or seeding) in source code creates a severe security risk and bad engineering precedent.

### Decision
Enforce a **Strict Zero-Hardcoded Credential Policy**:
1. **Dynamic Resolution in `seed.py`:**
   - Primary: Read from environment variables (`DEV_ADMIN_PASSWORD` / `ADMIN_PASSWORD` via `.env`).
   - Interactive: If running in an interactive terminal without env vars, prompt the developer securely using `getpass.getpass()`.
   - Automated/Unattended: If running unattended without env vars, generate a cryptographically strong temporary password on the fly (`secrets.token_urlsafe(16)`).
2. **Secure Persistence:**
   - Passwords are never stored as plaintext in the database or logs; only salted PBKDF2-HMAC-SHA256 hashes (1,000,000 rounds) are stored in SQLite.
3. **Repository Cleanliness:**
   - All `.env`, `.env.*`, `*.key`, and credential files are strictly excluded from version control via `.gitignore`.


