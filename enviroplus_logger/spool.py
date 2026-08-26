from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class PendingMessage:
    id: int
    topic: str
    payload: str
    attempts: int


class TelemetrySpool:
    """Durable, transactional queue for at-least-once telemetry delivery."""

    def __init__(self, path: str | Path) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at_ms INTEGER NOT NULL,
                last_error TEXT
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def enqueue(self, topic: str, payload: str, now_ms: int | None = None) -> int:
        timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO pending_messages
                    (topic, payload, created_at_ms, next_attempt_at_ms)
                VALUES (?, ?, ?, ?)
                """,
                (topic, payload, timestamp, timestamp),
            )
        return int(cursor.lastrowid)

    def due(self, now_ms: int | None = None, limit: int = 100) -> list[PendingMessage]:
        timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
        rows = self._connection.execute(
            """
            SELECT id, topic, payload, attempts
            FROM pending_messages
            WHERE next_attempt_at_ms <= ?
            ORDER BY id
            LIMIT ?
            """,
            (timestamp, limit),
        ).fetchall()
        return [PendingMessage(*row) for row in rows]

    def mark_sent(self, message_id: int) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM pending_messages WHERE id = ?", (message_id,)
            )

    def mark_failed(
        self,
        message: PendingMessage,
        error: Exception,
        now_ms: int | None = None,
        base_delay_seconds: int = 1,
        max_delay_seconds: int = 300,
    ) -> None:
        timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
        delay_seconds = min(
            base_delay_seconds * (2**message.attempts), max_delay_seconds
        )
        with self._connection:
            self._connection.execute(
                """
                UPDATE pending_messages
                SET attempts = attempts + 1,
                    next_attempt_at_ms = ?,
                    last_error = ?
                WHERE id = ?
                """,
                (timestamp + delay_seconds * 1000, str(error)[:1000], message.id),
            )

    def count(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM pending_messages"
        ).fetchone()
        return int(row[0])

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
