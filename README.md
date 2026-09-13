# Coders Era Event Platform 🚀

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Database-SQLite3](https://img.shields.io/badge/Database-SQLite3%20WAL-lightgrey.svg)](https://sqlite.org/)
[![License-MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, high-performance event management and secure one-time verification platform engineered for developer communities, hackathons, and technical symposiums. Designed with a modern, high-craft developer dark-mode aesthetic inspired by developer community hubs like Coders Era.

> [!NOTE]
> **Design Reference Notice:**
> The public website `codersera.in` is utilized strictly as an external, read-only design and thematic reference for dark-mode styling and developer-centric aesthetics. This repository is an independent college project and does not modify, deploy to, or claim ownership of any third-party domain or trademarked assets.

> [!IMPORTANT]
> **Project Delivery Timeline & Development Freeze:**
> - **Development Freeze (Feature-Complete Deadline):** **September 17, 2026 (End of Day)** — The application must be demo-ready, fully functional, and stable. **No major new features will be introduced after September 17.**
> - **Buffer & Final Submission Day:** **September 18, 2026** — Strictly reserved for final regression testing, minor bug fixes, demo practice, and final project submission.

---

## 🌟 Core MVP Features

1. **🌐 Responsive Event Landing Page:** Event showcases featuring countdown timers, category tags, mode indicators (Offline/Online/Hybrid), and venue logistics.
2. **📝 Dynamic Registration Form:** Online form supporting attendee information and custom event questions (e.g. GitHub handle, College ID, Branch).
3. **🛡️ Duplicate Registration Prevention:** Enforces unique email registrations per event to eliminate duplicate passes.
4. **🎟️ Unique Secure Ticket ID:** Generates unpredictable `CE-XXXX-XXXX-XXXX` codes backed by 256-bit cryptographic secrets.
5. **📱 QR Digital Ticket:** Rendered digital boarding pass displaying attendee details, Ticket ID, and QR code with one-click PNG download and print support.
6. **🔑 Organizer Authentication:** Session-based authentication with salted PBKDF2 password hashing.
7. **📊 Admin Dashboard:** Real-time telemetry displaying total registrations, checked-in count, pending count, and attendance percentage.
8. **🔍 Participant Management & Search:** Searchable attendee directory with live query filtering.
9. **📷 In-Browser Camera Scanner:** Native mobile browser QR code scanner powered by `html5-qrcode` without requiring any mobile app download.
10. **⌨️ Manual Ticket ID Verification:** Manual code entry fallback for damaged screens or offline verification.
11. **⚡ Atomic One-Time Check-In:** Guaranteed race-condition-proof verification. Once a ticket is checked in, it can **never** be checked in again for that event. Fast verification response suitable for real-time event check-in.
12. **📈 Attendance Statistics:** Live calculations of attendance rates.
13. **📁 CSV Export:** One-click download of the complete attendee roster and custom question responses.

*(Optional post-MVP features such as automated email delivery, JSON export, sound effects, and complex particle animations are strictly non-blocking).*

---

## 🏗️ Architecture & Technology Selection

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.14 + Flask 3.x | Lightweight, robust, standard university viva appeal, clear modular architecture. |
| **Database** | SQLite3 (WAL Mode) | Zero configuration, ACID-compliant transactional consistency, zero server daemon overhead. |
| **Frontend** | Modern Vanilla HTML5 + CSS3 + ES6 JS | Fast, zero build step (no compilation or bundler overhead), lightweight, developer dark aesthetic. |
| **QR Generation**| Python `qrcode` + Pillow | Vector/matrix QR generation with embedded cryptographic secrets. |
| **Camera Scanner**| `html5-qrcode` | Native in-browser camera scanning on iOS Safari, Android Chrome, and laptop webcams. |

> [!TIP]
> **Environment Note:**
> While Node.js (v24.21.0) and npm (11.19.0) are available on the development machine, the Python Flask + SQLite stack was chosen deliberately to maximize reliability, avoid complex frontend build toolchains, and ensure effortless execution on any evaluation machine for the college deadline.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Verified with Python 3.14.5 on Windows)
- Git

### 2. Setup Virtual Environment & Dependencies
```powershell
# Navigate to project directory
cd "coders-era-event-platform"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
# source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment (Optional for Custom Dev Credentials)
```powershell
# Copy the example environment file
Copy-Item .env.example .env
# Edit .env to customize local admin credentials or secret keys if desired
```

### 4. Initialize Database & Seed Sample Data
```powershell
# Run the database seeder to create schema and safe dev accounts/events
.\venv\Scripts\python.exe app/seed.py
```

### 5. Run the Development Server
```powershell
.\venv\Scripts\python.exe run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

### 🔑 Local Development Credentials (Zero Hardcoded Credentials)
> [!NOTE]
> Passwords are **never** stored in plaintext. They are hashed using salted **PBKDF2-HMAC-SHA256** (1,000,000 rounds).
> - When you run `.\venv\Scripts\python.exe app/seed.py`, it checks your `.env` for `DEV_ADMIN_PASSWORD`.
> - If unset, it will prompt you interactively or auto-generate a secure random temporary password and print it in the console.

| Role | Email | Password Source | Purpose |
| :--- | :--- | :--- | :--- |
| **Admin / Organizer** | `organizer@codersera.in` | Provided in `.env` or auto-generated at seed time | Event management, dashboard telemetry, CSV export |
| **Volunteer (Scanner)**| `volunteer@codersera.in` | Provided in `.env` or auto-generated at seed time | Gate check-in and QR code scanner access |

---

## 🎓 College Viva & Demo Walkthrough Guide

Follow these steps during your project demonstration or interview:

1. **Event Discovery (Home Page):**
   - Open `http://127.0.0.1:5000/`.
   - Point out the modern developer aesthetic (midnight dark theme, neon violet glows, event badges).
   - Show active events like *"Automate India Hackathon"* or *"Synapse & Syntax Masterclass"*.

2. **Participant Registration & Ticket Issuance:**
   - Click on an event to view the responsive landing page with countdown timer.
   - Fill in the registration form (Name, Email, GitHub Handle, College Roll No).
   - Submit the form. Show how the platform instantly creates a confirmed registration and displays the **Digital Boarding Pass**.
   - Point out the unique Ticket Code (`CE-XXXX-XXXX-XXXX`), dynamic QR code, and click **"Download Ticket (PNG)"**.

3. **Organizer Control Dashboard:**
   - Open an incognito window and go to `http://127.0.0.1:5000/admin/login`.
   - Log in using `organizer@codersera.in` and the password printed by `seed.py` (or set in `.env`).
   - View the live dashboard showing Total Registrations, Checked-In, Pending, and Attendance percentage.

4. **Gate Check-In & One-Time Security Demo (The "Wow" Factor):**
   - Navigate to **"QR Scanner"** (`/admin/scanner`).
   - Scan the QR code from the attendee's ticket using the webcam or paste the Ticket ID into the manual input box.
   - **First Attempt:** Shows an instant **GREEN "ACCESS GRANTED"** banner with attendee details.
   - Look back at the Dashboard: Checked-in count increments immediately!
   - **Second Attempt (Duplicate Check):** Scan the exact same QR code again.
   - Shows an instant **RED "REJECTED: ALREADY CHECKED IN"** alert, showing the exact time it was previously checked in and by whom.
   - Explain to the examiner why this is atomic and immune to race conditions (refer to `ARCHITECTURE.md`).

5. **Participant Management & CSV Export:**
   - Go to `/admin/participants`.
   - Use the live search bar to filter by name or ticket code.
   - Click **"Export CSV"** to download the complete attendance sheet with all custom question columns.

---

## 📚 Project Documentation Files
- [PROJECT_SPEC.md](file:///c:/Users/Aryan%20Gupta/coders-era-event-platform/PROJECT_SPEC.md) — Product specification, Core MVP scope, timeline, and non-functional requirements.
- [ARCHITECTURE.md](file:///c:/Users/Aryan%20Gupta/coders-era-event-platform/ARCHITECTURE.md) — System architecture, ERD, API contracts, and concurrency proofs.
- [DECISIONS.md](file:///c:/Users/Aryan%20Gupta/coders-era-event-platform/DECISIONS.md) — Architectural Decision Records (ADRs 001–008).
- [TODO.md](file:///c:/Users/Aryan%20Gupta/coders-era-event-platform/TODO.md) — Phased MVP task tracker and Development Freeze policy.

---

## Author

Built by Aryan Gupta for the Coders Era Club Selection Process (2026).

GitHub: https://github.com/Aryanxbit
