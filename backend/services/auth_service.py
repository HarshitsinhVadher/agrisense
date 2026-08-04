"""
AgriSense Authentication Service
---------------------------------
• Uses PostgreSQL (via DATABASE_URL env var) when deployed on Render.
• Falls back to local SQLite when DATABASE_URL is not set (local dev).
"""

import hashlib
import hmac
import secrets
import time
import json
import os
import re
from typing import Dict, Any, Optional, Tuple

# ─── DB Mode Detection ───────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

# Secret key for token signing — stable via env var, random fallback for dev
_SECRET_KEY = os.environ.get("AGRISENSE_SECRET", secrets.token_hex(32))


# ─── Connection Helpers ──────────────────────────────────────────────────────

def _pg_conn():
    """Return a psycopg2 connection to Render PostgreSQL."""
    import psycopg2
    import psycopg2.extras
    # Render uses postgres:// but psycopg2 needs postgresql://
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(url)
    return conn


def _sqlite_conn():
    """Return a sqlite3 connection to local agrisense.db."""
    import sqlite3
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(script_dir), 'agrisense.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Table Initialization ────────────────────────────────────────────────────

def init_auth_tables():
    """Create users and farmers tables if they don't exist (PostgreSQL or SQLite)."""
    if USE_POSTGRES:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(15) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS farmers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL DEFAULT 'Farmer',
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                latitude REAL DEFAULT 22.57,
                longitude REAL DEFAULT 72.93,
                soil_type TEXT DEFAULT 'Loamy Soil',
                "N" REAL DEFAULT 180.0,
                "P" REAL DEFAULT 42.0,
                "K" REAL DEFAULT 160.0,
                "pH" REAL DEFAULT 7.2,
                "EC" REAL DEFAULT 0.65,
                "OC" REAL DEFAULT 0.52,
                preferred_language TEXT DEFAULT 'gu',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("[AuthService] PostgreSQL tables initialised.")
    else:
        import sqlite3
        conn = _sqlite_conn()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS farmers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL DEFAULT 'Farmer',
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                latitude REAL DEFAULT 22.57,
                longitude REAL DEFAULT 72.93,
                soil_type TEXT DEFAULT 'Loamy Soil',
                N REAL DEFAULT 180.0,
                P REAL DEFAULT 42.0,
                K REAL DEFAULT 160.0,
                pH REAL DEFAULT 7.2,
                EC REAL DEFAULT 0.65,
                OC REAL DEFAULT 0.52,
                preferred_language TEXT DEFAULT 'gu',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()
        print("[AuthService] SQLite tables initialised (local dev mode).")


# ─── Password Hashing ────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """Hash password with PBKDF2-HMAC-SHA256 and a random salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000
    )
    return pw_hash.hex(), salt


# ─── Token Handling ──────────────────────────────────────────────────────────

def _generate_token(user_id: int, username: str) -> str:
    """Generate a signed token containing user_id, username, and 30-day expiry."""
    payload = json.dumps({
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + 86400 * 30
    })
    signature = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + signature
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a token. Returns payload dict or None if invalid/expired."""
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


def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user_id from a valid auth token."""
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None


# ─── Register ────────────────────────────────────────────────────────────────

def register_user(username: str, password: str) -> Dict[str, Any]:
    """Register a new user using a 10-digit Indian mobile number."""
    phone_clean = re.sub(r'\D', '', username or '')
    if phone_clean.startswith('91') and len(phone_clean) == 12:
        phone_clean = phone_clean[2:]

    if not phone_clean or len(phone_clean) != 10 or not re.match(r'^[6-9]\d{9}$', phone_clean):
        return {"error": "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210)"}
    if not password or len(password) < 4:
        return {"error": "Password must be at least 4 characters"}

    pw_hash, salt = _hash_password(password)

    if USE_POSTGRES:
        try:
            conn = _pg_conn()
            cur = conn.cursor()

            # Check duplicate
            cur.execute('SELECT id FROM users WHERE username = %s', (phone_clean,))
            if cur.fetchone():
                cur.close(); conn.close()
                return {"error": "An account with this mobile number already exists. Please login."}

            cur.execute(
                'INSERT INTO users (username, password_hash, password_salt) VALUES (%s, %s, %s) RETURNING id',
                (phone_clean, pw_hash, salt)
            )
            user_id = cur.fetchone()[0]

            # Auto-create farmer profile
            cur.execute('''
                INSERT INTO farmers (user_id, name, phone, preferred_language)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, f"Farmer ({phone_clean[-4:]})", phone_clean, 'gu'))

            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[AuthService] PostgreSQL register error: {e}")
            return {"error": "Database error during registration. Please try again."}
    else:
        conn = _sqlite_conn()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE username = ?', (phone_clean,))
        if cur.fetchone():
            conn.close()
            return {"error": "An account with this mobile number already exists. Please login."}

        cur.execute(
            'INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)',
            (phone_clean, pw_hash, salt)
        )
        user_id = cur.lastrowid
        cur.execute('''
            INSERT INTO farmers (user_id, name, phone, preferred_language)
            VALUES (?, ?, ?, ?)
        ''', (user_id, f"Farmer ({phone_clean[-4:]})", phone_clean, 'gu'))
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


# ─── Login ───────────────────────────────────────────────────────────────────

def login_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate a user using mobile number and password."""
    phone_clean = re.sub(r'\D', '', username or '')
    if phone_clean.startswith('91') and len(phone_clean) == 12:
        phone_clean = phone_clean[2:]

    if not phone_clean or len(phone_clean) != 10:
        return {"error": "Please enter your 10-digit registered mobile number"}
    if not password:
        return {"error": "Password is required"}

    if USE_POSTGRES:
        try:
            import psycopg2.extras
            conn = _pg_conn()
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE username = %s', (phone_clean,))
            row = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[AuthService] PostgreSQL login error: {e}")
            return {"error": "Database error during login. Please try again."}
    else:
        conn = _sqlite_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', (phone_clean,))
        row = cur.fetchone()
        conn.close()
        if row:
            row = dict(row)

    if not row:
        return {"error": "No account found with this mobile number. Please register first."}

    pw_hash, _ = _hash_password(password, row['password_salt'])
    if pw_hash != row['password_hash']:
        return {"error": "Incorrect password. Please try again."}

    user_id = row['id']
    token = _generate_token(user_id, row['username'])
    return {
        "success": True,
        "user_id": user_id,
        "username": row['username'],
        "phone": row['username'],
        "token": token,
        "message": "Login successful!"
    }
