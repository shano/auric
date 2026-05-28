import json
from datetime import date

import httpx
import pytest
import respx

from auric.providers.vibe import VibeProvider


def _make_session(
    tmp_path,
    name: str,
    prompt: int,
    completion: int,
    cost: float,
    model: str = "mistral-medium-3.5",
):
    d = tmp_path / name
    d.mkdir()
    meta = {
        "active_model": model,
        "stats": {
            "session_prompt_tokens": prompt,
            "session_completion_tokens": completion,
            "session_cost": cost,
        },
    }
    (d / "meta.json").write_text(json.dumps(meta))
    return d


class TestVibeProviderPoll:
    def test_poll_aggregates_todays_sessions(self, tmp_path):
        today = date.today().isoformat().replace("-", "")
        _make_session(tmp_path, f"session_{today}_120000_aaa", 100, 50, 0.001)
        _make_session(tmp_path, f"session_{today}_130000_bbb", 200, 80, 0.002)

        provider = VibeProvider(logs_dir=tmp_path, http_client=httpx.Client())
        result = provider.poll()

        assert result is not None
        assert result.provider_id == "vibe"
        assert result.input_tokens == 300
        assert result.output_tokens == 130
        assert result.cost_usd == pytest.approx(0.003)

    def test_poll_ignores_other_days(self, tmp_path):
        _make_session(tmp_path, "session_20200101_120000_old", 999, 999, 9.99)

        provider = VibeProvider(logs_dir=tmp_path, http_client=httpx.Client())
        assert provider.poll() is None

    def test_poll_returns_none_when_logs_dir_missing(self, tmp_path):
        provider = VibeProvider(
            logs_dir=tmp_path / "nonexistent",
            http_client=httpx.Client(),
        )
        assert provider.poll() is None

    def test_poll_skips_malformed_meta(self, tmp_path):
        today = date.today().isoformat().replace("-", "")
        _make_session(tmp_path, f"session_{today}_120000_good", 100, 50, 0.001)
        bad = tmp_path / f"session_{today}_130000_bad"
        bad.mkdir()
        (bad / "meta.json").write_text("not json {{{")

        provider = VibeProvider(logs_dir=tmp_path, http_client=httpx.Client())
        result = provider.poll()
        assert result is not None
        assert result.input_tokens == 100

    def test_poll_uses_model_from_meta(self, tmp_path):
        today = date.today().isoformat().replace("-", "")
        _make_session(
            tmp_path,
            f"session_{today}_120000_aaa",
            10,
            5,
            0.0,
            model="devstral-small-latest",
        )

        provider = VibeProvider(logs_dir=tmp_path, http_client=httpx.Client())
        result = provider.poll()
        assert result is not None
        assert result.model == "devstral-small-latest"


class TestVibeProviderPing:
    @respx.mock
    def test_ping_returns_none_when_no_key(self, tmp_path):
        provider = VibeProvider(
            logs_dir=tmp_path, http_client=httpx.Client(), api_key=""
        )
        assert provider.ping() is None

    @respx.mock
    def test_ping_parses_rate_limit_headers(self, tmp_path):
        respx.post("https://api.mistral.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                headers={
                    "x-ratelimit-remaining-tokens": "450000",
                    "x-ratelimit-limit-tokens": "500000",
                    "x-ratelimit-reset-tokens": "3600",
                },
                json={"id": "chat_test", "choices": [{"message": {"content": "."}}]},
            )
        )
        provider = VibeProvider(
            logs_dir=tmp_path,
            http_client=httpx.Client(),
            api_key="test-key",
        )
        result = provider.ping()
        assert result is not None
        assert result.provider_id == "vibe"
        assert result.remaining_pct == pytest.approx(0.9)
        assert result.limit_type == "token_window"
        assert result.requests_remaining is None

    @respx.mock
    def test_ping_returns_none_when_headers_missing(self, tmp_path):
        respx.post("https://api.mistral.ai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"id": "chat_test"})
        )
        provider = VibeProvider(
            logs_dir=tmp_path,
            http_client=httpx.Client(),
            api_key="test-key",
        )
        assert provider.ping() is None

    @respx.mock
    def test_ping_returns_none_on_network_error(self, tmp_path):
        respx.post("https://api.mistral.ai/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        provider = VibeProvider(
            logs_dir=tmp_path,
            http_client=httpx.Client(),
            api_key="test-key",
        )
        assert provider.ping() is None
