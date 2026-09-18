# Coders Era Event Platform 🚀

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Database-SQLite3](https://img.shields.io/badge/Database-SQLite3%20WAL-lightgrey.svg)](https://sqlite.org/)
[![License-MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end event management and secure one-time verification platform engineered for developer communities, hackathons, and technical symposiums. Designed with a modern dark-mode developer aesthetic inspired by community-focused technical platforms.
## 🚀 Live Demo

**Live Application:** https://aryan-coders-era-event-platform.onrender.com

Try the deployed platform to explore event registration, digital tickets, QR verification, organizer dashboard, participant management, and one-time check-in.

> [!NOTE]
> **Design Reference Notice:**
> This is an independent project developed for the Coders Era Club selection process. Coders Era names, branding, and third-party assets referenced for design inspiration remain the property of their respective owners.

---

## 🌟 Core MVP Features

1. **🌐 Responsive Event Landing Page:** Event showcases featuring countdown timers, category tags, mode indicators (Offline/Online/Hybrid), and venue logistics.
2. **📝 Dynamic Registration Form:** Online form supporting attendee information and custom event questions (e.g. GitHub handle, College ID, Branch).
3. **🛡️ Duplicate Registration Prevention:** Enforces unique email registrations per event to eliminate duplicate passes.
4. **🎟️ Unique Secure Ticket ID:** Generates unpredictable `CE-XXXX-XXXX-XXXX` codes backed by 256-bit cryptographic secrets.
5. **📱 QR Digital Ticket:** Rendered digital boarding pass displaying attendee details, Ticket ID, and QR code with one-click PNG download and print support.
6. **🔑 Organizer Authentication:** Session-based authentication with salted PBKDF2 password hashing.
7. **📊 Admin Dashboard:** Live dashboard displaying total registrations, checked-in count, pending count, and attendance percentage.
8. **🔍 Participant Management & Search:** Searchable attendee directory with live query filtering.
9. **📷 In-Browser Camera Scanner:** QR code scanner powered by `html5-qrcode`, using supported device cameras and webcams without requiring a separate mobile app.
10. **⌨️ Manual Ticket ID Verification:** Manual Ticket ID entry fallback when QR scanning is unavailable.
11. **⚡ Atomic One-Time Check-In:** Guaranteed race-condition-proof verification. Once a ticket is checked in, it can **never** be checked in again for that event. Fast verification response suitable for real-time event check-in.
12. **📈 Attendance Statistics:** Live calculations of attendance rates.
13. **📁 CSV Export:** One-click download of the complete attendee roster and custom question responses.

> Optional post-MVP enhancements such as automated email delivery and JSON export are non-blocking.

---

## 🏗️ Architecture & Technology Selection

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.14 + Flask 3.x | Lightweight, robust, and easy to understand, with a clear modular architecture. |
| **Database** | SQLite3 (WAL Mode) | Zero configuration, ACID-compliant transactional consistency, zero server daemon overhead. |
| **Frontend** | Modern Vanilla HTML5 + CSS3 + ES6 JS | Fast, zero build step (no compilation or bundler overhead), lightweight, developer dark aesthetic. |
| **QR Generation**| Python `qrcode` + Pillow | Generates QR tickets containing secure verification tokens. |
| **Camera Scanner**| `html5-qrcode` | In-browser QR scanning using supported device cameras and webcams.|

> [!TIP]
> **Environment Note:** The project intentionally uses Python + Flask + SQLite with no frontend build step, keeping local setup lightweight and straightforward for development and evaluation.

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

## 🎯 Demo Walkthrough Guide

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
   - Explain why the check-in operation is atomic and protected against duplicate or concurrent verification attempts (refer to `ARCHITECTURE.md`).

5. **Participant Management & CSV Export:**
   - Go to `/admin/participants`.
   - Use the live search bar to filter by name or ticket code.
   - Click **"Export CSV"** to download the complete attendance sheet with all custom question columns.

---

## 📚 Project Documentation Files
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Product specification, Core MVP scope, and non-functional requirements.

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture, ERD, API contracts, and concurrency proofs.

- [DECISIONS.md](DECISIONS.md) — Architectural Decision Records (ADRs 001–008).

- [TODO.md](TODO.md) — Phased MVP task tracker.

---

## Author

Built by Aryan Gupta for the Coders Era Club Selection Process (2026).

GitHub: [Aryanxbit](https://github.com/Aryanxbit)
