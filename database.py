"""
JanSahayak Database Layer
Handles SQLite persistence for customer requests, immutable audit events,
persisted conversation states, and idempotency tracking.
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jansahayak.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite database tables with proper indexing and constraints."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                location TEXT NOT NULL,
                occupation TEXT NOT NULL,
                income_bracket TEXT,
                purpose TEXT NOT NULL,
                selected_scheme TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL,
                staff_notes TEXT,
                idempotency_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Audit events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # Conversation state persistence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_states (
                session_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_ref ON requests(reference_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_events(reference_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_idempotency ON requests(idempotency_token)")

        conn.commit()


def compute_idempotency_token(customer_name: str, location: str, occupation: str, purpose: str, session_id: str) -> str:
    """Generate a deterministic token to prevent duplicate submissions from repeated clicks or reruns."""
    payload = f"{customer_name.strip().lower()}|{location.strip().lower()}|{occupation.strip().lower()}|{purpose.strip().lower()}|{session_id.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def check_duplicate_request(idempotency_token: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Check if a request with this idempotency token already exists."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests WHERE idempotency_token = ?", (idempotency_token,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def create_request(
    reference_id: str,
    customer_name: str,
    location: str,
    occupation: str,
    income_bracket: str,
    purpose: str,
    selected_scheme: str,
    language: str,
    idempotency_token: str,
    status: str = "SUBMITTED",
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Creates a new banking assistance request with duplicate prevention.
    Returns: (success: bool, message: str, record: dict or None)
    """
    now = datetime.now().isoformat()
    existing = check_duplicate_request(idempotency_token, db_path=db_path)
    if existing:
        return False, f"Duplicate submission detected. Request already exists with ID {existing['reference_id']}.", existing

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO requests (
                    reference_id, customer_name, location, occupation, income_bracket,
                    purpose, selected_scheme, language, status, staff_notes,
                    idempotency_token, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reference_id, customer_name, location, occupation, income_bracket,
                purpose, selected_scheme, language, status, "",
                idempotency_token, now, now
            ))

            # Record audit event
            cursor.execute("""
                INSERT INTO audit_events (reference_id, actor, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                reference_id, "CUSTOMER", "REQUEST_SUBMITTED",
                f"New request created for {customer_name} ({location}) for {selected_scheme}",
                now
            ))
            conn.commit()

            cursor.execute("SELECT * FROM requests WHERE reference_id = ?", (reference_id,))
            created_record = dict(cursor.fetchone())
            return True, "Request submitted successfully.", created_record
        except sqlite3.IntegrityError as e:
            return False, f"Database integrity error: {str(e)}", None


def get_request_by_ref(reference_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a single request by its reference ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests WHERE reference_id = ?", (reference_id.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_requests(status_filter: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """List requests for demo staff portal, optionally filtered by status."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if status_filter and status_filter.upper() != "ALL":
            cursor.execute("SELECT * FROM requests WHERE status = ? ORDER BY id DESC", (status_filter.upper(),))
        else:
            cursor.execute("SELECT * FROM requests ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_audit_trail(reference_id: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve complete immutable audit events for a request."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events WHERE reference_id = ? ORDER BY id ASC", (reference_id.strip().upper(),))
        return [dict(row) for row in cursor.fetchall()]


def update_request_status(
    reference_id: str,
    new_status: str,
    staff_notes: str,
    actor: str = "STAFF",
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str]:
    """
    Update request status by staff with audit logging.
    Valid new_status values: 'APPROVED_FOR_PROCESSING', 'RETURNED', 'REJECTED'.
    """
    valid_statuses = {"SUBMITTED", "APPROVED_FOR_PROCESSING", "RETURNED", "REJECTED"}
    if new_status not in valid_statuses:
        return False, f"Invalid status: {new_status}. Allowed values: {valid_statuses}"

    req = get_request_by_ref(reference_id, db_path=db_path)
    if not req:
        return False, f"Request with ID {reference_id} not found."

    now = datetime.now().isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE requests
            SET status = ?, staff_notes = ?, updated_at = ?
            WHERE reference_id = ?
        """, (new_status, staff_notes, now, reference_id.strip().upper()))

        cursor.execute("""
            INSERT INTO audit_events (reference_id, actor, action, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            reference_id.strip().upper(), actor, f"STATUS_CHANGED_TO_{new_status}",
            f"Notes: {staff_notes or 'No notes provided'}",
            now
        ))
        conn.commit()
        return True, f"Request status updated to {new_status}."


def resubmit_returned_request(
    reference_id: str,
    updated_fields: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str]:
    """
    Allow customer to correct and resubmit a RETURNED request.
    Enforces deterministic check that only RETURNED requests can be resubmitted.
    """
    req = get_request_by_ref(reference_id, db_path=db_path)
    if not req:
        return False, f"Request {reference_id} does not exist."
    if req["status"] != "RETURNED":
        return False, f"Cannot resubmit request with status '{req['status']}'. Only 'RETURNED' requests can be corrected and resubmitted."

    now = datetime.now().isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        # Build update clause for provided fields
        allowed_fields = {"customer_name", "location", "occupation", "income_bracket", "purpose", "selected_scheme"}
        updates = []
        params = []
        changes_desc = []
        for k, v in updated_fields.items():
            if k in allowed_fields:
                updates.append(f"{k} = ?")
                params.append(v)
                changes_desc.append(f"{k}='{v}'")

        updates.extend(["status = ?", "updated_at = ?"])
        params.extend(["SUBMITTED", now, reference_id.strip().upper()])

        sql = f"UPDATE requests SET {', '.join(updates)} WHERE reference_id = ?"
        cursor.execute(sql, params)

        details = f"Customer corrected: {', '.join(changes_desc)}. Resubmitted for staff review."
        cursor.execute("""
            INSERT INTO audit_events (reference_id, actor, action, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (reference_id.strip().upper(), "CUSTOMER", "REQUEST_RESUBMITTED", details, now))
        conn.commit()
        return True, "Request successfully corrected and resubmitted for staff review."


def save_session_state(session_id: str, state_dict: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Persist conversation state to SQLite."""
    now = datetime.now().isoformat()
    state_json = json.dumps(state_dict)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO session_states (session_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
        """, (session_id, state_json, now))
        conn.commit()


def load_session_state(session_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Load persisted conversation state from SQLite."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT state_json FROM session_states WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["state_json"])
        return None
