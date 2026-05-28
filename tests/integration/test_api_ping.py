import httpx
import pytest
import respx

from auric.providers.claude import ClaudeProvider

RESET_TIME = "2026-05-28T12:20:00Z"


@respx.mock
def test_ping_extracts_rate_limit_headers(tmp_path):
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            headers={
                "anthropic-ratelimit-tokens-remaining": "68000",
                "anthropic-ratelimit-tokens-limit": "100000",
                "anthropic-ratelimit-tokens-reset": RESET_TIME,
                "anthropic-ratelimit-requests-remaining": "50",
            },
            json={"id": "msg_test", "content": [{"text": "."}]},
        )
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-test",
    )
    result = provider.ping()
    assert result is not None
    assert result.provider_id == "claude"
    assert result.remaining_pct == pytest.approx(0.68)
    assert result.limit_type == "5hr_window"
    assert result.requests_remaining == 50
    assert result.is_stale is False


@respx.mock
def test_ping_returns_none_on_network_error(tmp_path):
    respx.post("https://api.anthropic.com/v1/messages").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-test",
    )
    assert provider.ping() is None


@respx.mock
def test_ping_at_zero_on_429(tmp_path):
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            429,
            headers={
                "anthropic-ratelimit-tokens-remaining": "0",
                "anthropic-ratelimit-tokens-limit": "100000",
                "anthropic-ratelimit-tokens-reset": RESET_TIME,
            },
        )
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-test",
    )
    result = provider.ping()
    assert result is not None
    assert result.remaining_pct == pytest.approx(0.0)


@respx.mock
def test_ping_returns_none_when_headers_missing(tmp_path):
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"id": "msg_test"})
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-test",
    )
    assert provider.ping() is None


@respx.mock
def test_ping_extracts_unified_rate_limit_headers(tmp_path):
    """OAuth users (Pro, Max) return unified headers instead of token headers."""
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            headers={
                "anthropic-ratelimit-unified-5h-utilization": "0.58",
                "anthropic-ratelimit-unified-5h-reset": "1748432400",
            },
            json={"id": "msg_test", "content": [{"text": "."}]},
        )
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-oat-test",
    )
    result = provider.ping()
    assert result is not None
    assert result.remaining_pct == pytest.approx(0.42)
    assert result.limit_type == "5hr_window"
    assert result.requests_remaining is None
    assert result.weekly_remaining_pct is None
    assert result.weekly_reset_at is None


@respx.mock
def test_ping_extracts_unified_7d_headers(tmp_path):
    """7d fields populated when both 5h and 7d unified headers present."""
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            headers={
                "anthropic-ratelimit-unified-5h-utilization": "0.58",
                "anthropic-ratelimit-unified-5h-reset": "1748432400",
                "anthropic-ratelimit-unified-7d-utilization": "0.20",
                "anthropic-ratelimit-unified-7d-reset": "1748895600",
            },
            json={"id": "msg_test", "content": [{"text": "."}]},
        )
    )
    provider = ClaudeProvider(
        stats_cache_path=tmp_path / "missing.json",
        http_client=httpx.Client(),
        api_key="sk-ant-oat-test",
    )
    result = provider.ping()
    assert result is not None
    assert result.weekly_remaining_pct == pytest.approx(0.80)
    assert result.weekly_reset_at is not None
