import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from auric.models.usage import RateLimitState, UsageSnapshot

_CREATE_USAGE = """
CREATE TABLE IF NOT EXISTS usage_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id         TEXT NOT NULL,
    timestamp           INTEGER NOT NULL,
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER NOT NULL,
    cache_read_tokens   INTEGER NOT NULL,
    cache_write_tokens  INTEGER NOT NULL,
    cost_usd            REAL NOT NULL
)
"""

_CREATE_RATE_LIMIT = """
CREATE TABLE IF NOT EXISTS rate_limit_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id         TEXT NOT NULL,
    timestamp           INTEGER NOT NULL,
    remaining_pct       REAL NOT NULL,
    reset_at            INTEGER NOT NULL,
    limit_type          TEXT NOT NULL,
    requests_remaining  INTEGER
)
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_usage_provider_ts"
    " ON usage_snapshots(provider_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_ratelimit_provider_ts"
    " ON rate_limit_snapshots(provider_id, timestamp)",
]


class SQLiteStorage:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or Path.home() / ".local" / "share" / "auric" / "auric.db"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_USAGE)
            conn.execute(_CREATE_RATE_LIMIT)
            for idx in _CREATE_INDEXES:
                conn.execute(idx)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_snapshot(self, snap: UsageSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO usage_snapshots "
                "(provider_id, timestamp, model, input_tokens, output_tokens, "
                "cache_read_tokens, cache_write_tokens, cost_usd) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snap.provider_id,
                    int(snap.timestamp.timestamp()),
                    snap.model,
                    snap.input_tokens,
                    snap.output_tokens,
                    snap.cache_read_tokens,
                    snap.cache_write_tokens,
                    snap.cost_usd,
                ),
            )

    def get_snapshots(self, provider_id: str, limit: int = 100) -> list[UsageSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM usage_snapshots WHERE provider_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (provider_id, limit),
            ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def save_rate_limit(self, state: RateLimitState) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rate_limit_snapshots "
                "(provider_id, timestamp, remaining_pct, reset_at,"
                " limit_type, requests_remaining) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    state.provider_id,
                    int(datetime.now(tz=UTC).timestamp()),
                    state.remaining_pct,
                    int(state.reset_at.timestamp()),
                    state.limit_type,
                    state.requests_remaining,
                ),
            )

    def get_latest_rate_limit(self, provider_id: str) -> RateLimitState | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM rate_limit_snapshots WHERE provider_id = ? "
                "ORDER BY timestamp DESC LIMIT 1",
                (provider_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_rate_limit(row)

    def _row_to_snapshot(self, row: sqlite3.Row) -> UsageSnapshot:
        return UsageSnapshot(
            provider_id=row["provider_id"],
            timestamp=datetime.fromtimestamp(row["timestamp"], tz=UTC),
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cache_read_tokens=row["cache_read_tokens"],
            cache_write_tokens=row["cache_write_tokens"],
            cost_usd=row["cost_usd"],
        )

    def _row_to_rate_limit(self, row: sqlite3.Row) -> RateLimitState:
        return RateLimitState(
            provider_id=row["provider_id"],
            remaining_pct=row["remaining_pct"],
            reset_at=datetime.fromtimestamp(row["reset_at"], tz=UTC),
            limit_type=row["limit_type"],
            requests_remaining=row["requests_remaining"],
        )
