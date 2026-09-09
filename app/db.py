import sqlite3
from pathlib import Path
from flask import current_app, g

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db(db_path=None):
    """
    Get or create a thread-local database connection for the current request.
    Configures WAL mode and foreign key constraints.
    """
    if db_path is None:
        if current_app:
            db_path = current_app.config.get("DATABASE_PATH")
        else:
            from app.config import Config
            db_path = Config.DATABASE_PATH

    if "db" not in g:
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=10.0
        )
        g.db.row_factory = sqlite3.Row
        
        # Performance and integrity pragmas
        cursor = g.db.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.close()

    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(db_path=None):
    """Initialize the database schema from schema.sql."""
    if db_path is None:
        from app.config import Config
        db_path = Config.DATABASE_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
        
    conn.commit()
    conn.close()

def init_app(app):
    """Register database teardown with Flask app factory."""
    app.teardown_appcontext(close_db)
