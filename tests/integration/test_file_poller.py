import json
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from auric.providers.claude import ClaudeProvider

FIXTURE = Path(__file__).parent.parent / "fixtures" / "stats-cache.json"


def test_fixture_file_exists():
    assert FIXTURE.exists(), f"Fixture missing: {FIXTURE}"


def test_poll_parses_fixture_without_error(tmp_path):
    cache = tmp_path / "stats-cache.json"
    shutil.copy(FIXTURE, cache)
    data = json.loads(cache.read_text())
    today = date.today().isoformat()
    for entry in data.get("dailyModelTokens", []):
        entry["date"] = today
    for entry in data.get("dailyActivity", []):
        entry["date"] = today
    data["lastComputedDate"] = today
    cache.write_text(json.dumps(data))

    provider = ClaudeProvider(
        stats_cache_path=cache,
        http_client=MagicMock(spec=httpx.Client),
    )
    result = provider.poll()
    assert result is not None
    assert result.provider_id == "claude"
    assert result.total_tokens > 0
    assert result.model == "claude-sonnet-4-6"
