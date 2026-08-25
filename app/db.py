from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    sample_id TEXT PRIMARY KEY,
                    scenario_type TEXT NOT NULL,
                    task_types TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT NOT NULL,
                    before_json TEXT NOT NULL,
                    after_json TEXT NOT NULL,
                    editor TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    sample_id TEXT,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def clear_all(self) -> None:
        """Clear the local demo database before a reproducible demo run."""
        with self.connect() as connection:
            connection.executescript("DELETE FROM revisions; DELETE FROM audit_events; DELETE FROM samples;")

    def upsert_samples(self, samples: list[dict[str, Any]]) -> None:
        timestamp = now_iso()
        with self.connect() as connection:
            for sample in samples:
                connection.execute(
                    """INSERT INTO samples(sample_id, scenario_type, task_types, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sample_id) DO UPDATE SET scenario_type=excluded.scenario_type,
                    task_types=excluded.task_types, payload_json=excluded.payload_json, updated_at=excluded.updated_at""",
                    (
                        sample["sample_id"],
                        sample["scenario_type"],
                        json.dumps(sample["task_types"], ensure_ascii=False),
                        json.dumps(sample, ensure_ascii=False),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    "INSERT INTO audit_events(event_type, sample_id, detail_json, created_at) VALUES (?, ?, ?, ?)",
                    ("import", sample["sample_id"], "{}", timestamp),
                )

    def list_samples(self, scenario_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM samples"
        params: tuple[Any, ...] = ()
        if scenario_type:
            query += " WHERE scenario_type = ?"
            params = (scenario_type,)
        query += " ORDER BY sample_id"
        with self.connect() as connection:
            return [json.loads(row["payload_json"]) for row in connection.execute(query, params)]

    def get_sample(self, sample_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT payload_json FROM samples WHERE sample_id = ?", (sample_id,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def update_sample(self, sample: dict[str, Any]) -> None:
        self.upsert_samples([sample])

    def save_revision(self, sample_id: str, before: dict[str, Any], after: dict[str, Any], editor: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO revisions(sample_id, before_json, after_json, editor, created_at) VALUES (?, ?, ?, ?, ?)",
                (sample_id, json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False), editor, now_iso()),
            )
            connection.execute(
                "INSERT INTO audit_events(event_type, sample_id, detail_json, created_at) VALUES (?, ?, ?, ?)",
                ("revision", sample_id, json.dumps({"editor": editor}, ensure_ascii=False), now_iso()),
            )
