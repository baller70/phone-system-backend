
"""
Database helper for logging calls to the dashboard database.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from contextlib import contextmanager

# Database connection string - fetched from dashboard
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://role_151b3281cd:1OhWAdgclIqVA92DmfBBy95WxugHLZnk@db-151b3281cd.db002.hosteddb.reai.io:5432/151b3281cd?connect_timeout=15')

@contextmanager
def get_db_connection():
    """Create a database connection context manager."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def log_call_to_dashboard(
    caller_id: str,
    caller_name: str = None,
    duration: int = 0,
    intent: str = "unknown",
    outcome: str = "completed",
    recording_url: str = None,
    transcription: str = None,
    notes: str = None,
    cost: float = 0.0
):
    """
    Log a call to the dashboard database.
    
    Args:
        caller_id: Phone number of the caller
        caller_name: Name of the caller (optional)
        duration: Call duration in seconds
        intent: The intent/purpose of the call (booking, pricing, info, etc.)
        outcome: Call outcome (completed, failed, transferred, etc.)
        recording_url: URL to the call recording (optional)
        transcription: Full call transcription (optional)
        notes: Additional notes about the call (optional)
        cost: Estimated call cost in dollars
    
    Returns:
        The ID of the created call log entry, or None if failed
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Generate a unique ID (cuid style - starts with 'c')
                import random
                import string
                call_id = 'c' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
                
                # Insert into CallLog table
                cur.execute("""
                    INSERT INTO "CallLog" (
                        id, "callerId", "callerName", duration, intent, outcome,
                        timestamp, "recordingUrl", transcription, notes, cost,
                        "createdAt", "updatedAt"
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                """, (
                    call_id,
                    caller_id,
                    caller_name or "Unknown",
                    duration,
                    intent,
                    outcome,
                    datetime.now(),
                    recording_url,
                    transcription,
                    notes,
                    cost,
                    datetime.now(),
                    datetime.now()
                ))
                
                result = cur.fetchone()
                print(f"✓ Call logged to dashboard: {caller_id} - {intent} - {outcome}")
                return result['id'] if result else None
                
    except Exception as e:
        print(f"Failed to log call to dashboard: {e}")
        return None

def get_recent_calls(limit: int = 10):
    """Fetch recent calls from the dashboard database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM "CallLog"
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    except Exception as e:
        print(f"Failed to fetch recent calls: {e}")
        return []

def test_database_connection():
    """Test the database connection."""
    try:
        print(f"Testing database connection...")
        print(f"DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
        with get_db_connection() as conn:
            print(f"Connection established")
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM \"CallLog\"")
                count = cur.fetchone()[0]
                print(f"✓ Database connection successful! Found {count} call logs.")
                return True
    except Exception as e:
        print(f"✗ Database connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
