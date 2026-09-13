-- SQLite Relational Schema for Coders Era Event Platform
PRAGMA foreign_keys = ON;

-- Users Table (Organizers, Admins, Volunteers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'organizer', 'volunteer')) DEFAULT 'organizer',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Events Table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL COLLATE NOCASE,
    title TEXT NOT NULL,
    tagline TEXT,
    description TEXT,
    banner_url TEXT,
    category TEXT DEFAULT 'Hackathon',
    mode TEXT CHECK(mode IN ('offline', 'online', 'hybrid')) DEFAULT 'offline',
    venue TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    registration_start DATETIME,
    registration_deadline DATETIME NOT NULL,
    max_capacity INTEGER DEFAULT 0,
    status TEXT CHECK(status IN ('draft', 'published', 'closed', 'archived')) DEFAULT 'published',
    custom_fields_json TEXT DEFAULT '[]',
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE RESTRICT
);

-- Registrations / Tickets Table
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_code TEXT UNIQUE NOT NULL,
    ticket_secret TEXT UNIQUE NOT NULL,
    event_id INTEGER NOT NULL,
    participant_name TEXT NOT NULL,
    participant_email TEXT NOT NULL COLLATE NOCASE,
    participant_phone TEXT,
    answers_json TEXT DEFAULT '{}',
    status TEXT CHECK(status IN ('confirmed', 'cancelled', 'waitlisted')) DEFAULT 'confirmed',
    is_checked_in INTEGER DEFAULT 0 CHECK(is_checked_in IN (0, 1)),
    checked_in_at DATETIME DEFAULT NULL,
    checked_in_by INTEGER DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY(checked_in_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(event_id, participant_email)
);

-- Checkin Audit Logs Table
CREATE TABLE IF NOT EXISTS checkin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER,
    event_id INTEGER NOT NULL,
    scanned_code TEXT NOT NULL,
    status TEXT CHECK(status IN ('SUCCESS', 'ALREADY_USED', 'INVALID_TICKET', 'EVENT_MISMATCH')) NOT NULL,
    attempted_by INTEGER NOT NULL,
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(registration_id) REFERENCES registrations(id) ON DELETE SET NULL,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY(attempted_by) REFERENCES users(id) ON DELETE RESTRICT
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_events_slug ON events(slug);
CREATE INDEX IF NOT EXISTS idx_reg_ticket_code ON registrations(ticket_code);
CREATE INDEX IF NOT EXISTS idx_reg_ticket_secret ON registrations(ticket_secret);
CREATE INDEX IF NOT EXISTS idx_reg_event_lookup ON registrations(event_id, is_checked_in);
CREATE INDEX IF NOT EXISTS idx_logs_event ON checkin_logs(event_id, timestamp DESC);
