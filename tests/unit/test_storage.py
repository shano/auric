from datetime import UTC, datetime

import pytest

from auric.models.usage import RateLimitState, UsageSnapshot
from auric.services.storage import SQLiteStorage


def make_snapshot(total: int = 1000) -> UsageSnapshot:
    q = total // 4
    return UsageSnapshot(
        provider_id="claude",
        timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
        model="claude-sonnet-4-6",
        input_tokens=q,
        output_tokens=q,
        cache_read_tokens=total - 2 * q,
        cache_write_tokens=0,
        cost_usd=0.0,
    )


def make_rate_limit(pct: float = 0.68) -> RateLimitState:
    return RateLimitState(
        provider_id="claude",
        remaining_pct=pct,
        reset_at=datetime(2026, 5, 28, 12, 20, tzinfo=UTC),
        limit_type="5hr_window",
        requests_remaining=None,
    )


class TestSQLiteStorage:
    def test_creates_db_on_init(self, tmp_path):
        db = tmp_path / "test.db"
        SQLiteStorage(db_path=db)
        assert db.exists()

    def test_creates_parent_dirs(self, tmp_path):
        db = tmp_path / "nested" / "dir" / "auric.db"
        SQLiteStorage(db_path=db)
        assert db.exists()

    def test_save_and_retrieve_snapshot(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        snap = make_snapshot()
        storage.save_snapshot(snap)
        results = storage.get_snapshots("claude", limit=10)
        assert len(results) == 1
        assert results[0].provider_id == "claude"
        assert results[0].total_tokens == snap.total_tokens

    def test_save_multiple_snapshots(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        for _ in range(5):
            storage.save_snapshot(make_snapshot())
        assert len(storage.get_snapshots("claude", limit=10)) == 5

    def test_get_snapshots_respects_limit(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        for _ in range(10):
            storage.save_snapshot(make_snapshot())
        assert len(storage.get_snapshots("claude", limit=3)) == 3

    def test_snapshots_scoped_to_provider(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        storage.save_snapshot(make_snapshot())
        assert storage.get_snapshots("gemini", limit=10) == []

    def test_save_and_retrieve_rate_limit(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        storage.save_rate_limit(make_rate_limit())
        result = storage.get_latest_rate_limit("claude")
        assert result is not None
        assert result.remaining_pct == pytest.approx(0.68)
        assert result.limit_type == "5hr_window"

    def test_get_latest_rate_limit_returns_most_recent(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        storage.save_rate_limit(make_rate_limit(pct=0.9))
        storage.save_rate_limit(make_rate_limit(pct=0.5))
        result = storage.get_latest_rate_limit("claude")
        assert result.remaining_pct == pytest.approx(0.5)

    def test_get_latest_rate_limit_returns_none_when_empty(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        assert storage.get_latest_rate_limit("claude") is None

    def test_rate_limit_scoped_to_provider(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        storage.save_rate_limit(make_rate_limit())
        assert storage.get_latest_rate_limit("gemini") is None
