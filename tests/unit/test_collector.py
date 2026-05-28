from datetime import UTC, datetime

import pytest

from auric.models.provider import Provider, ProviderStatus
from auric.models.usage import RateLimitState, UsageSnapshot
from auric.providers.base import AbstractProvider
from auric.services.collector import UsageCollector
from auric.services.storage import SQLiteStorage


def make_snapshot() -> UsageSnapshot:
    return UsageSnapshot(
        provider_id="claude",
        timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
        model="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=8000,
        cache_write_tokens=200,
        cost_usd=0.0,
    )


def make_rate_limit() -> RateLimitState:
    return RateLimitState(
        provider_id="claude",
        remaining_pct=0.68,
        reset_at=datetime(2026, 5, 28, 12, 20, tzinfo=UTC),
        limit_type="5hr_window",
        requests_remaining=None,
    )


class StubProvider(AbstractProvider):
    def __init__(self, snapshot=None, rate_limit=None):
        self._snapshot = snapshot
        self._rate_limit = rate_limit
        self.poll_count = 0
        self.ping_count = 0

    def poll(self) -> UsageSnapshot | None:
        self.poll_count += 1
        return self._snapshot

    def ping(self) -> RateLimitState | None:
        self.ping_count += 1
        return self._rate_limit


def make_collector(tmp_path, snapshot=None, rate_limit=None) -> UsageCollector:
    stub = StubProvider(snapshot=snapshot, rate_limit=rate_limit)
    provider = Provider(
        id="claude", display_name="Claude Max", status=ProviderStatus.ACTIVE
    )
    storage = SQLiteStorage(db_path=tmp_path / "test.db")
    return UsageCollector(providers=[(provider, stub)], storage=storage)


class TestUsageCollector:
    def test_poll_calls_provider(self, tmp_path):
        stub = StubProvider(snapshot=make_snapshot())
        provider = Provider(
            id="claude", display_name="Claude Max", status=ProviderStatus.ACTIVE
        )
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector = UsageCollector(providers=[(provider, stub)], storage=storage)
        collector.run_poll("claude")
        assert stub.poll_count == 1

    def test_poll_saves_snapshot_to_storage(self, tmp_path):
        snap = make_snapshot()
        collector = make_collector(tmp_path, snapshot=snap)
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector.run_poll("claude")
        saved = storage.get_snapshots("claude", limit=1)
        assert len(saved) == 1
        assert saved[0].total_tokens == snap.total_tokens

    def test_poll_none_does_not_save(self, tmp_path):
        collector = make_collector(tmp_path, snapshot=None)
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector.run_poll("claude")
        assert storage.get_snapshots("claude") == []

    def test_ping_saves_rate_limit(self, tmp_path):
        rl = make_rate_limit()
        collector = make_collector(tmp_path, rate_limit=rl)
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector.run_ping("claude")
        saved = storage.get_latest_rate_limit("claude")
        assert saved is not None
        assert saved.remaining_pct == pytest.approx(0.68)

    def test_ping_none_does_not_save(self, tmp_path):
        collector = make_collector(tmp_path, rate_limit=None)
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector.run_ping("claude")
        assert storage.get_latest_rate_limit("claude") is None

    def test_get_provider_state_returns_provider(self, tmp_path):
        collector = make_collector(tmp_path)
        result = collector.get_provider_state("claude")
        assert result is not None
        assert result.id == "claude"

    def test_get_provider_state_unknown_returns_none(self, tmp_path):
        storage = SQLiteStorage(db_path=tmp_path / "test.db")
        collector = UsageCollector(providers=[], storage=storage)
        assert collector.get_provider_state("unknown") is None

    def test_all_providers_returns_list(self, tmp_path):
        collector = make_collector(tmp_path)
        providers = collector.all_providers()
        assert len(providers) == 1
        assert providers[0].id == "claude"

    def test_unknown_provider_id_poll_is_noop(self, tmp_path):
        collector = make_collector(tmp_path)
        collector.run_poll("unknown")  # should not raise
