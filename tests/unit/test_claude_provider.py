import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from auric.providers.claude import ClaudeProvider

FIXTURE = Path(__file__).parent.parent / "fixtures" / "stats-cache.json"


def _fixture_for_today(tmp_path: Path) -> Path:
    """Copy fixture to tmp_path with dates updated to today."""
    data = json.loads(FIXTURE.read_text())
    today = date.today().isoformat()
    for entry in data.get("dailyModelTokens", []):
        entry["date"] = today
    for entry in data.get("dailyActivity", []):
        entry["date"] = today
    data["lastComputedDate"] = today
    out = tmp_path / "stats-cache.json"
    out.write_text(json.dumps(data))
    return out


class TestClaudeFilePoller:
    def test_poll_returns_snapshot_for_today(self, tmp_path):
        cache = _fixture_for_today(tmp_path)
        provider = ClaudeProvider(
            stats_cache_path=cache,
            http_client=MagicMock(spec=httpx.Client),
        )
        snapshot = provider.poll()
        assert snapshot is not None
        assert snapshot.provider_id == "claude"
        # fixture: 84000 + 2100 daily tokens, but total_tokens uses modelUsage breakdown
        # for primary model: 5000+12000+65000+2000 = 84000
        assert snapshot.total_tokens == 84000

    def test_poll_returns_none_when_file_missing(self, tmp_path):
        provider = ClaudeProvider(
            stats_cache_path=tmp_path / "missing.json",
            http_client=MagicMock(spec=httpx.Client),
        )
        assert provider.poll() is None

    def test_poll_returns_none_when_file_malformed(self, tmp_path):
        bad = tmp_path / "stats-cache.json"
        bad.write_text("not json {{{")
        provider = ClaudeProvider(
            stats_cache_path=bad,
            http_client=MagicMock(spec=httpx.Client),
        )
        assert provider.poll() is None

    def test_poll_returns_none_when_no_entry_for_today(self, tmp_path):
        data = {
            "version": 3,
            "dailyModelTokens": [
                {"date": "2000-01-01", "tokensByModel": {"claude-sonnet-4-6": 1000}}
            ],
            "modelUsage": {},
        }
        cache = tmp_path / "stats-cache.json"
        cache.write_text(json.dumps(data))
        provider = ClaudeProvider(
            stats_cache_path=cache,
            http_client=MagicMock(spec=httpx.Client),
        )
        assert provider.poll() is None

    def test_snapshot_cost_zero_for_subscription(self, tmp_path):
        cache = _fixture_for_today(tmp_path)
        provider = ClaudeProvider(
            stats_cache_path=cache,
            http_client=MagicMock(spec=httpx.Client),
        )
        snapshot = provider.poll()
        assert snapshot is not None
        assert snapshot.cost_usd == 0.0

    def test_snapshot_provider_id_is_claude(self, tmp_path):
        cache = _fixture_for_today(tmp_path)
        provider = ClaudeProvider(
            stats_cache_path=cache,
            http_client=MagicMock(spec=httpx.Client),
        )
        snapshot = provider.poll()
        assert snapshot is not None
        assert snapshot.provider_id == "claude"

    def test_ping_returns_none_without_api_key(self, tmp_path):
        provider = ClaudeProvider(
            stats_cache_path=tmp_path / "missing.json",
            http_client=MagicMock(spec=httpx.Client),
        )
        assert provider.ping() is None
