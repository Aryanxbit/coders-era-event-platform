from werkzeug.security import check_password_hash
from app.db import get_db

def authenticate_user(email, password):
    """
    Verify user credentials against stored PBKDF2 password hash.
    Returns the user row dict if valid, else None.
    """
    if not email or not password:
        return None

    db = get_db()
    user = db.execute(
        "SELECT id, uuid, email, password_hash, full_name, role FROM users WHERE email = ? COLLATE NOCASE",
        (email.strip(),)
    ).fetchone()

    if not user:
        return None

    if check_password_hash(user["password_hash"], password):
        return {
            "id": user["id"],
            "uuid": user["uuid"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }

    return None

def get_user_by_id(user_id):
    """Retrieve user details by ID."""
    if not user_id:
        return None

    db = get_db()
    user = db.execute(
        "SELECT id, uuid, email, full_name, role, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user:
        return dict(user)
    return None
