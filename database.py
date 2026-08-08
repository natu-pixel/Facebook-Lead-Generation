import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database schema and handles migrations for older schemas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            place_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            rating REAL,
            reviews_count INTEGER,
            phone TEXT,
            email TEXT,
            opening_hours TEXT,
            maps_url TEXT,
            score INTEGER,
            found_at TEXT NOT NULL
        )
    """)
    
    # Query current column names to handle migrations dynamically
    cursor.execute("PRAGMA table_info(leads)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "email" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN email TEXT")
    if "opening_hours" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN opening_hours TEXT")
    if "facebook_search_url" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN facebook_search_url TEXT")
        
    conn.commit()
    conn.close()

def is_duplicate(place_id: str) -> bool:
    """Checks if a place_id has already been processed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM leads WHERE place_id = ?", (place_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_lead(lead: dict):
    """Saves a new lead into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Use current UTC time as ISO format string if not provided
    found_at = lead.get("found_at", datetime.utcnow().isoformat())
    
    cursor.execute("""
        INSERT INTO leads (place_id, name, city, country, rating, reviews_count, phone, email, opening_hours, facebook_search_url, maps_url, score, found_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead["place_id"],
        lead["name"],
        lead["city"],
        lead["country"],
        lead.get("rating"),
        lead.get("reviews_count"),
        lead.get("phone"),
        lead.get("email"),
        lead.get("opening_hours"),
        lead.get("facebook_search_url"),
        lead.get("maps_url"),
        lead.get("score"),
        found_at
    ))
    conn.commit()
    conn.close()

def get_all_leads():
    """Fetches all stored leads."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY score DESC, found_at DESC")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]
