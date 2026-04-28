"""Session management with SQLite backend for conversation checkpointing.

Provides LangGraph-style session checkpointing for multi-turn conversations.
Stores conversation state, collected slots, and path history.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Checkpoint:
    """A checkpoint of conversation state at a specific turn."""
    turn_id: int
    current_node: str
    collected_slots: dict[str, Any] = field(default_factory=dict)
    path_history: list[str] = field(default_factory=list)
    failure_count: int = 0
    timestamp: str = ""
    paused_at: list[str] = field(default_factory=list)
    paused_ttl: str | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class SessionStore:
    """SQLite-backed session store for conversation checkpoints.

    Usage:
        store = SessionStore("path/to/sessions.db")
        store.save_checkpoint("session_123", checkpoint)
        checkpoint = store.load_checkpoint("session_123")
    """

    def __init__(self, db_path: str | Path | None = None):
        """Initialize session store.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.nexo/sessions.db
        """
        if db_path is None:
            db_path = Path.home() / ".nexo" / "sessions.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    session_id TEXT PRIMARY KEY,
                    turn_id INTEGER,
                    current_node TEXT,
                    collected_slots TEXT,
                    path_history TEXT,
                    failure_count INTEGER DEFAULT 0,
                    timestamp TEXT,
                    paused_at TEXT,
                    paused_ttl TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    turn_id INTEGER,
                    user_input TEXT,
                    ai_response TEXT,
                    matched_nodes TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES checkpoints(session_id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)"
            )
            conn.commit()
        finally:
            conn.close()

    def save_checkpoint(self, session_id: str, checkpoint: Checkpoint) -> None:
        """Save a checkpoint for a session.

        Args:
            session_id: Unique session identifier
            checkpoint: Checkpoint data to save
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints (
                    session_id, turn_id, current_node, collected_slots,
                    path_history, failure_count, timestamp, paused_at, paused_ttl, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                session_id,
                checkpoint.turn_id,
                checkpoint.current_node,
                json.dumps(checkpoint.collected_slots),
                json.dumps(checkpoint.path_history),
                checkpoint.failure_count,
                checkpoint.timestamp,
                json.dumps(checkpoint.paused_at) if checkpoint.paused_at else None,
                checkpoint.paused_ttl,
            ))
            conn.commit()
        finally:
            conn.close()

    def load_checkpoint(self, session_id: str) -> Checkpoint | None:
        """Load the latest checkpoint for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            Checkpoint if found, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM checkpoints WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return Checkpoint(
                turn_id=row["turn_id"],
                current_node=row["current_node"],
                collected_slots=json.loads(row["collected_slots"]) if row["collected_slots"] else {},
                path_history=json.loads(row["path_history"]) if row["path_history"] else [],
                failure_count=row["failure_count"],
                timestamp=row["timestamp"],
                paused_at=json.loads(row["paused_at"]) if row["paused_at"] else [],
                paused_ttl=row["paused_ttl"],
            )
        finally:
            conn.close()

    def get_active_path(self, session_id: str) -> list[str]:
        """Get the current conversation path for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of node IDs in the current path, or empty list if not found
        """
        checkpoint = self.load_checkpoint(session_id)
        if checkpoint is None:
            return []
        return checkpoint.path_history

    def pause_path(
        self,
        session_id: str,
        paused_at: list[str],
        ttl_hours: int = 12,
    ) -> None:
        """Pause the current conversation path with a TTL.

        Args:
            session_id: Unique session identifier
            paused_at: Path to resume from later
            ttl_hours: Hours until the paused path expires
        """
        from datetime import timedelta

        checkpoint = self.load_checkpoint(session_id)
        if checkpoint is None:
            checkpoint = Checkpoint(
                turn_id=0,
                current_node="",
                path_history=paused_at,
            )

        checkpoint.paused_at = paused_at
        checkpoint.paused_ttl = (
            datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        ).isoformat()

        self.save_checkpoint(session_id, checkpoint)

    def save_turn(
        self,
        session_id: str,
        turn_id: int,
        user_input: str,
        ai_response: str,
        matched_nodes: list[str] | None = None,
    ) -> None:
        """Save a conversation turn.

        Args:
            session_id: Unique session identifier
            turn_id: Turn number
            user_input: User's input text
            ai_response: AI's response text
            matched_nodes: Node IDs that matched the input
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO turns (
                    session_id, turn_id, user_input, ai_response,
                    matched_nodes, timestamp
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                session_id,
                turn_id,
                user_input,
                ai_response,
                json.dumps(matched_nodes or []),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_turns(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation turns for a session.

        Args:
            session_id: Unique session identifier
            limit: Maximum number of turns to return (None for all)

        Returns:
            List of turn dicts with user_input, ai_response, timestamp
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            query = "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_id"
            if limit:
                query += f" DESC LIMIT {limit}"
            cursor = conn.execute(query, (session_id,))
            rows = cursor.fetchall()

            turns = []
            for row in rows:
                turns.append({
                    "turn_id": row["turn_id"],
                    "user_input": row["user_input"],
                    "ai_response": row["ai_response"],
                    "matched_nodes": json.loads(row["matched_nodes"]) if row["matched_nodes"] else [],
                    "timestamp": row["timestamp"],
                })

            return list(reversed(turns)) if limit else turns
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its turns.

        Args:
            session_id: Unique session identifier
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "DELETE FROM turns WHERE session_id = ?",
                (session_id,),
            )
            conn.execute(
                "DELETE FROM checkpoints WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def list_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of session IDs
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT session_id FROM checkpoints ORDER BY updated_at DESC"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        """Delete sessions with expired paused_ttl.

        Returns:
            Number of sessions deleted
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            now = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                """
                SELECT session_id FROM checkpoints
                WHERE paused_ttl IS NOT NULL AND paused_ttl < ?
                """,
                (now,),
            )
            expired_sessions = [row[0] for row in cursor.fetchall()]

            for session_id in expired_sessions:
                self.delete_session(session_id)

            return len(expired_sessions)
        finally:
            conn.close()
