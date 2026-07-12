"""SQLite results store: the queryable summary over the raw JSONL logs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    optimizer   TEXT NOT NULL,
    tuned_keys  TEXT NOT NULL,
    started_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flights (
    flight_id    TEXT PRIMARY KEY,
    campaign_id  TEXT,
    started_at   TEXT NOT NULL,
    param_hash   TEXT NOT NULL,
    params_json  TEXT NOT NULL,
    gates_passed INTEGER NOT NULL,
    lap_time_s   REAL,
    gate_clips   INTEGER NOT NULL,
    env_hits     INTEGER NOT NULL,
    finished     INTEGER NOT NULL,
    aborted      INTEGER NOT NULL,
    abort_reason TEXT,
    score        REAL NOT NULL,
    notes        TEXT
);
"""


class ResultsDB:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def record_campaign(self, campaign_id: str, optimizer: str,
                        tuned_keys: list[str], started_at: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO campaigns VALUES (?, ?, ?, ?)",
            (campaign_id, optimizer, json.dumps(tuned_keys), started_at),
        )
        self.conn.commit()

    def record_flight(self, flight_id: str, started_at: str, params,
                      result: dict, score: float,
                      campaign_id: str | None = None, notes: str = "") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO flights VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                flight_id,
                campaign_id,
                started_at,
                params.hash,
                params.canonical_json(),
                result.get("gates_passed", 0),
                result.get("lap_time_s"),
                result.get("gate_clips", 0),
                result.get("env_hits", 0),
                1 if result.get("finished") else 0,
                1 if result.get("aborted") else 0,
                result.get("abort_reason", ""),
                score,
                notes,
            ),
        )
        self.conn.commit()

    def best_flight(self, campaign_id: str | None = None) -> sqlite3.Row | None:
        if campaign_id is None:
            cur = self.conn.execute("SELECT * FROM flights ORDER BY score DESC LIMIT 1")
        else:
            cur = self.conn.execute(
                "SELECT * FROM flights WHERE campaign_id = ? ORDER BY score DESC LIMIT 1",
                (campaign_id,),
            )
        return cur.fetchone()

    def flights(self, campaign_id: str | None = None) -> list[sqlite3.Row]:
        if campaign_id is None:
            cur = self.conn.execute("SELECT * FROM flights ORDER BY started_at")
        else:
            cur = self.conn.execute(
                "SELECT * FROM flights WHERE campaign_id = ? ORDER BY started_at",
                (campaign_id,),
            )
        return cur.fetchall()
