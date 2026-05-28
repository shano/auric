from datetime import UTC, datetime

import pytest

from auric.models.config import AppConfig, ProviderConfig
from auric.models.provider import Provider, ProviderStatus
from auric.models.usage import RateLimitState, UsageSnapshot


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


class TestUsageSnapshot:
    def test_fields_stored(self):
        s = make_snapshot()
        assert s.provider_id == "claude"
        assert s.model == "claude-sonnet-4-6"
        assert s.input_tokens == 1000
        assert s.output_tokens == 500
        assert s.cache_read_tokens == 8000
        assert s.cache_write_tokens == 200
        assert s.cost_usd == 0.0

    def test_total_tokens(self):
        s = make_snapshot()
        assert s.total_tokens == 9700  # 1000+500+8000+200

    def test_immutable(self):
        s = make_snapshot()
        with pytest.raises((AttributeError, TypeError)):
            s.input_tokens = 999  # frozen dataclass


class TestRateLimitState:
    def test_fields_stored(self):
        r = make_rate_limit()
        assert r.provider_id == "claude"
        assert r.remaining_pct == pytest.approx(0.68)
        assert r.limit_type == "5hr_window"
        assert r.requests_remaining is None

    def test_stale_defaults_false(self):
        r = make_rate_limit()
        assert r.is_stale is False

    def test_remaining_pct_display(self):
        r = make_rate_limit()
        assert r.remaining_pct_display == 68

    def test_remaining_pct_display_rounds(self):
        r = RateLimitState(
            provider_id="claude",
            remaining_pct=0.694,
            reset_at=datetime(2026, 5, 28, 12, 20, tzinfo=UTC),
            limit_type="5hr_window",
            requests_remaining=None,
        )
        assert r.remaining_pct_display == 69


class TestProvider:
    def test_active_provider(self):
        p = Provider(
            id="claude",
            display_name="Claude Max",
            status=ProviderStatus.ACTIVE,
        )
        assert p.id == "claude"
        assert p.status == ProviderStatus.ACTIVE
        assert p.rate_limit is None
        assert p.last_snapshot is None
        assert p.error_msg is None

    def test_provider_with_rate_limit(self):
        r = make_rate_limit()
        p = Provider(
            id="claude",
            display_name="Claude Max",
            status=ProviderStatus.ACTIVE,
            rate_limit=r,
        )
        assert p.rate_limit.remaining_pct == pytest.approx(0.68)

    def test_all_provider_statuses_valid(self):
        for status in ProviderStatus:
            p = Provider(id="x", display_name="X", status=status)
            assert p.status == status

    def test_degraded_provider_carries_error_msg(self):
        p = Provider(
            id="claude",
            display_name="Claude Max",
            status=ProviderStatus.DEGRADED,
            error_msg="Network unreachable",
        )
        assert p.error_msg == "Network unreachable"


class TestConfig:
    def test_default_provider_config(self):
        c = ProviderConfig()
        assert c.api_key == ""
        assert c.ping_interval_s == 300
        assert c.poll_interval_s == 30
        assert c.enabled is True

    def test_app_config_providers_dict(self):
        config = AppConfig(providers={"claude": ProviderConfig()})
        assert "claude" in config.providers
        assert config.providers["claude"].ping_interval_s == 300

    def test_app_config_empty_providers(self):
        config = AppConfig(providers={})
        assert config.providers == {}
