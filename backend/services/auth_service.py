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

import re

def register_user(username: str, password: str) -> Dict[str, Any]:
    """Register a new user using a 10-digit Indian Mobile Number. Returns user info + auth token."""
    # Clean phone input (remove spaces, hyphens, +91 prefix)
    phone_clean = re.sub(r'\D', '', username or '')
    if phone_clean.startswith('91') and len(phone_clean) == 12:
        phone_clean = phone_clean[2:]

    if not phone_clean or len(phone_clean) != 10 or not re.match(r'^[6-9]\d{9}$', phone_clean):
        return {"error": "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210)"}
    if not password or len(password) < 4:
        return {"error": "Password must be at least 4 characters"}

    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # Check if phone number already exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (phone_clean,))
    if cursor.fetchone():
        conn.close()
        return {"error": "An account with this mobile number already exists. Please login."}

    pw_hash, salt = _hash_password(password)
    cursor.execute(
        'INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)',
        (phone_clean, pw_hash, salt)
    )
    user_id = cursor.lastrowid

    # Auto-create a farmer profile for this user
    cursor.execute('''
        INSERT INTO farmers (user_id, name, phone, location, latitude, longitude, soil_type, N, P, K, pH, EC, OC, preferred_language)
        VALUES (?, ?, ?, '', 22.57, 72.93, 'Loamy Soil', 180.0, 42.0, 160.0, 7.2, 0.65, 0.52, 'gu')
    ''', (user_id, f"Farmer ({phone_clean[-4:]})", phone_clean))

    conn.commit()
    conn.close()

    token = _generate_token(user_id, phone_clean)
    return {
        "success": True,
        "user_id": user_id,
        "username": phone_clean,
        "phone": phone_clean,
        "token": token,
        "message": "Account created successfully!"
    }

def login_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate a user using Mobile Number & Password."""
    phone_clean = re.sub(r'\D', '', username or '')
    if phone_clean.startswith('91') and len(phone_clean) == 12:
        phone_clean = phone_clean[2:]

    if not phone_clean or len(phone_clean) != 10:
        return {"error": "Please enter your 10-digit registered mobile number"}
    if not password:
        return {"error": "Password is required"}

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (phone_clean,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "No account found with this mobile number. Please register first."}

    user = dict(row)
    pw_hash, _ = _hash_password(password, user['password_salt'])

    if pw_hash != user['password_hash']:
        return {"error": "Incorrect password. Please try again."}

    token = _generate_token(user['id'], user['username'])
    return {
        "success": True,
        "user_id": user['id'],
        "username": user['username'],
        "phone": user['username'],
        "token": token,
        "message": "Login successful!"
    }

def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user_id from a valid auth token."""
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None
