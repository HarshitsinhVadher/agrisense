import sqlite3
import hashlib
import hmac
import secrets
import time
import json
import os
from typing import Dict, Any, Optional, Tuple

# Secret key for token signing — generated once per server lifetime
_SECRET_KEY = os.environ.get("AGRISENSE_SECRET", secrets.token_hex(32))

def get_db_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(script_dir), 'agrisense.db')

def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """Hash password with PBKDF2-HMAC-SHA256 and a random salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return pw_hash.hex(), salt

def _generate_token(user_id: int, username: str) -> str:
    """Generate a signed token containing user_id, username, and expiry."""
    payload = json.dumps({
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + 86400 * 30  # 30-day expiry
    })
    signature = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + signature
    return token

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a token. Returns payload dict or None if invalid."""
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        expected_sig = hmac.new(_SECRET_KEY.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(payload_bytes.decode())
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def register_user(username: str, password: str) -> Dict[str, Any]:
    """Register a new user. Returns user info + auth token."""
    if not username or len(username) < 3:
        return {"error": "Username must be at least 3 characters"}
    if not password or len(password) < 4:
        return {"error": "Password must be at least 4 characters"}

    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (username.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        return {"error": "Username already taken"}

    pw_hash, salt = _hash_password(password)
    cursor.execute(
        'INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)',
        (username.lower().strip(), pw_hash, salt)
    )
    user_id = cursor.lastrowid

    # Auto-create a farmer profile for this user
    cursor.execute('''
        INSERT INTO farmers (user_id, name, phone, location, latitude, longitude, soil_type, N, P, K, pH, EC, OC, preferred_language)
        VALUES (?, ?, '', '', 22.57, 72.93, 'Loamy Soil', 180.0, 42.0, 160.0, 7.2, 0.65, 0.52, 'en')
    ''', (user_id, username.strip()))

    conn.commit()
    conn.close()

    token = _generate_token(user_id, username.lower().strip())
    return {
        "success": True,
        "user_id": user_id,
        "username": username.lower().strip(),
        "token": token,
        "message": "Account created successfully!"
    }

def login_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate a user. Returns user info + auth token."""
    if not username or not password:
        return {"error": "Username and password are required"}

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username.lower().strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "Invalid username or password"}

    user = dict(row)
    pw_hash, _ = _hash_password(password, user['password_salt'])

    if pw_hash != user['password_hash']:
        return {"error": "Invalid username or password"}

    token = _generate_token(user['id'], user['username'])
    return {
        "success": True,
        "user_id": user['id'],
        "username": user['username'],
        "token": token,
        "message": "Login successful!"
    }

def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user_id from a valid auth token."""
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None
