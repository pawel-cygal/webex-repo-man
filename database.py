# database.py
import sqlite3
from datetime import datetime

DB_NAME = "repoman.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create statuses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_email TEXT NOT NULL,
        status_text TEXT NOT NULL,
        message_id TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP NOT NULL
    )
    """)

    # Create reminders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_by TEXT NOT NULL,
        room_id TEXT NOT NULL,
        reminder_text TEXT NOT NULL,
        remind_at TIMESTAMP NOT NULL,
        is_sent BOOLEAN NOT NULL DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")

def add_status(person_email: str, status_text: str, message_id: str):
    """Adds a daily status to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO statuses (person_email, status_text, message_id, created_at)
        VALUES (?, ?, ?, ?)
        """, (person_email, status_text, message_id, datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        # This message_id already exists, so we ignore it.
        # This can happen if Webex sends the same webhook event multiple times.
        pass
    finally:
        conn.close()

def get_statuses_for_today() -> list:
    """Retrieves all statuses recorded today."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor.execute("""
    SELECT person_email, status_text FROM statuses
    WHERE created_at >= ?
    ORDER BY person_email, created_at
    """, (today_start,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_reminder(created_by: str, room_id: str, text: str, remind_at: datetime) -> int:
    """Adds a new reminder to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO reminders (created_by, room_id, reminder_text, remind_at)
    VALUES (?, ?, ?, ?)
    """, (created_by, room_id, text, remind_at))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_due_reminders() -> list:
    """Retrieves all reminders that are due to be sent."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, room_id, reminder_text FROM reminders
    WHERE remind_at <= ? AND is_sent = 0
    """, (datetime.now(),))
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_reminder_as_sent(reminder_id: int):
    """Marks a reminder as sent in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # If you run this file directly, it will initialize the database.
    init_db()
