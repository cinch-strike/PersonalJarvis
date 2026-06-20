#!/usr/bin/env python3
"""
Jarvis Phase 1 — Memory module
──────────────────────────────────────────────────────
Local persistent memory backed by SQLite (stdlib sqlite3).

Two tables:
  • sessions      — one row per Jarvis run (start/end timestamps)
  • conversations — one row per turn (user or assistant)

Public API:
  start_session()                         -> session_id
  save_turn(session_id, role, content)    -> turn_id
  load_recent_turns(n=20)                 -> list[dict] (oldest → newest)
  close_session(session_id)               -> None

The DB file lives next to this module so it travels with the project and
does not depend on the current working directory.
"""

import os
import sqlite3
from datetime import datetime, timezone

# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memory.db")


# ─── Internal helpers ───────────────────────────────────────────────────────────

def _now() -> str:
    """UTC timestamp in ISO-8601 (sortable as text)."""
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    """Open a connection with the schema ensured.

    We open per-call rather than holding a module-level connection so the
    module is safe to import from any thread (sounddevice/pynput run callbacks
    on their own threads). check_same_thread=False keeps that simple.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            ended_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL REFERENCES sessions(id),
            role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            synced      INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_created
            ON conversations(created_at);
        CREATE INDEX IF NOT EXISTS idx_conversations_synced
            ON conversations(synced);
        """
    )
    conn.commit()


# ─── Public API ─────────────────────────────────────────────────────────────────

def start_session() -> int:
    """Open a new session and return its id."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)", (_now(),)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_turn(session_id: int, role: str, content: str) -> int:
    """Persist a single conversation turn. Returns the new row id.

    role must be 'user' or 'assistant'.
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def load_recent_turns(n: int = 20) -> list[dict]:
    """Return the most recent n turns across all sessions, oldest → newest.

    Each item: {"id", "session_id", "role", "content", "created_at"}.
    Ordered chronologically so the result can be fed straight into a prompt.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM conversations ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        conn.close()
    # Fetched newest-first for the LIMIT; reverse to chronological order.
    return [dict(row) for row in reversed(rows)]


def close_session(session_id: int) -> None:
    """Mark a session as ended."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (_now(), session_id),
        )
        conn.commit()
    finally:
        conn.close()


# ─── Sync support (used by aws_sync.py) ──────────────────────────────────────────

def get_unsynced_turns() -> list[dict]:
    """Return all conversation turns not yet pushed to DynamoDB, oldest first."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM conversations WHERE synced = 0 ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def mark_synced(turn_ids: list[int]) -> None:
    """Flag the given conversation rows as synced."""
    if not turn_ids:
        return
    conn = _connect()
    try:
        conn.executemany(
            "UPDATE conversations SET synced = 1 WHERE id = ?",
            [(tid,) for tid in turn_ids],
        )
        conn.commit()
    finally:
        conn.close()
