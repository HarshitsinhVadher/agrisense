import sqlite3
import os
import json
from typing import Dict, Any, List, Optional

def get_db_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(script_dir), 'agrisense.db')

def init_sql_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 0. Users Authentication Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 1. Farmers Relational Table (linked to users via user_id)
    cursor.execute('''
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
            preferred_language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert default farmer profile if none exists (for backwards compatibility)
    cursor.execute('SELECT COUNT(*) FROM farmers')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO farmers (user_id, name, phone, location, latitude, longitude, soil_type, N, P, K, pH, EC, OC, preferred_language)
            VALUES (NULL, 'Ramesh Patel', '+91 98765 43210', 'Anand, Gujarat', 22.57, 72.93, 'Loamy Soil', 180.0, 42.0, 160.0, 7.2, 0.65, 0.52, 'en')
        ''')

    # 2. Soil Health Card Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS soil_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            user_id INTEGER,
            sample_id TEXT,
            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,
            ph REAL,
            ec REAL,
            oc REAL,
            status_json TEXT,
            raw_ocr_snippet TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 3. Label Scans History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS label_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            user_id INTEGER,
            matched_product_name TEXT,
            match_confidence REAL,
            raw_ocr_text TEXT,
            ai_summary TEXT,
            disclaimer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 4. Crop Recommendations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crop_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            user_id INTEGER,
            top_crop TEXT,
            confidence REAL,
            input_n REAL,
            input_p REAL,
            input_k REAL,
            input_ph REAL,
            input_temp REAL,
            input_humidity REAL,
            input_rain REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# ---------- Farmers DAO ----------

def get_farmer_profile(farmer_id: int = None, user_id: int = None) -> Dict[str, Any]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if user_id:
        cursor.execute('SELECT * FROM farmers WHERE user_id = ?', (user_id,))
    elif farmer_id:
        cursor.execute('SELECT * FROM farmers WHERE id = ?', (farmer_id,))
    else:
        cursor.execute('SELECT * FROM farmers WHERE id = 1')

    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "id": 1, "name": "Farmer", "phone": "", "location": "",
        "latitude": 22.57, "longitude": 72.93, "soil_type": "Loamy Soil",
        "N": 180.0, "P": 42.0, "K": 160.0, "pH": 7.2, "EC": 0.65, "OC": 0.52,
        "preferred_language": "en"
    }

def update_farmer_profile(data: Dict[str, Any], farmer_id: int = None, user_id: int = None) -> Dict[str, Any]:
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    if user_id:
        cursor.execute('''
            UPDATE farmers
            SET name=?, phone=?, location=?, latitude=?, longitude=?, soil_type=?, N=?, P=?, K=?, pH=?, EC=?, OC=?, preferred_language=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (
            data.get("name", "Farmer"), data.get("phone", ""),
            data.get("location", ""), data.get("latitude", 22.57),
            data.get("longitude", 72.93), data.get("soil_type", "Loamy Soil"),
            data.get("N", 180.0), data.get("P", 42.0), data.get("K", 160.0),
            data.get("pH", 7.2), data.get("EC", 0.65), data.get("OC", 0.52),
            data.get("preferred_language", "en"), user_id
        ))
    else:
        fid = farmer_id or data.get("id", 1)
        cursor.execute('''
            UPDATE farmers
            SET name=?, phone=?, location=?, latitude=?, longitude=?, soil_type=?, N=?, P=?, K=?, pH=?, EC=?, OC=?, preferred_language=?, updated_at=CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get("name", "Farmer"), data.get("phone", ""),
            data.get("location", ""), data.get("latitude", 22.57),
            data.get("longitude", 72.93), data.get("soil_type", "Loamy Soil"),
            data.get("N", 180.0), data.get("P", 42.0), data.get("K", 160.0),
            data.get("pH", 7.2), data.get("EC", 0.65), data.get("OC", 0.52),
            data.get("preferred_language", "en"), fid
        ))

    conn.commit()
    conn.close()
    return get_farmer_profile(farmer_id=farmer_id, user_id=user_id)

# ---------- History Recording DAOs ----------

def record_soil_report_sql(farmer_id: int, sample_id: str, n: float, p: float, k: float, ph: float, ec: float, oc: float, status: Dict[str, Any], snippet: str, user_id: int = None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO soil_reports (farmer_id, user_id, sample_id, nitrogen, phosphorus, potassium, ph, ec, oc, status_json, raw_ocr_snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (farmer_id, user_id, sample_id, n, p, k, ph, ec, oc, json.dumps(status), snippet))
    conn.commit()
    conn.close()

def record_label_scan_sql(farmer_id: int, product_name: str, confidence: float, ocr_text: str, summary: str, disclaimer: str, user_id: int = None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO label_scans (farmer_id, user_id, matched_product_name, match_confidence, raw_ocr_text, ai_summary, disclaimer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (farmer_id, user_id, product_name, confidence, ocr_text, summary, disclaimer))
    conn.commit()
    conn.close()

def record_crop_recommendation_sql(farmer_id: int, top_crop: str, confidence: float, n: float, p: float, k: float, ph: float, temp: float, humidity: float, rain: float, user_id: int = None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO crop_recommendations (farmer_id, user_id, top_crop, confidence, input_n, input_p, input_k, input_ph, input_temp, input_humidity, input_rain)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (farmer_id, user_id, top_crop, confidence, n, p, k, ph, temp, humidity, rain))
    conn.commit()
    conn.close()

def fetch_all_history_sql(farmer_id: int = None, user_id: int = None) -> Dict[str, Any]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if user_id:
        cursor.execute('SELECT * FROM soil_reports WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
        soil_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM label_scans WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
        label_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM crop_recommendations WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
        crop_rows = [dict(r) for r in cursor.fetchall()]
    else:
        fid = farmer_id or 1
        cursor.execute('SELECT * FROM soil_reports WHERE farmer_id = ? ORDER BY id DESC LIMIT 10', (fid,))
        soil_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM label_scans WHERE farmer_id = ? ORDER BY id DESC LIMIT 10', (fid,))
        label_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM crop_recommendations WHERE farmer_id = ? ORDER BY id DESC LIMIT 10', (fid,))
        crop_rows = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "soil_reports": soil_rows,
        "label_scans": label_rows,
        "crop_recommendations": crop_rows
    }
