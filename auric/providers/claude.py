import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from auric.models.usage import RateLimitState, UsageSnapshot
from auric.providers.base import AbstractProvider

log = logging.getLogger(__name__)

_PING_URL = "https://api.anthropic.com/v1/messages"
_PING_BODY = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "."}],
}


class ClaudeProvider(AbstractProvider):
    PROVIDER_ID = "claude"

    def __init__(
        self,
        stats_cache_path: Path,
        http_client: httpx.Client,
        api_key: str = "",
    ) -> None:
        self._cache_path = stats_cache_path
        self._http = http_client
        self._api_key = api_key

    def poll(self) -> UsageSnapshot | None:
        try:
            raw = json.loads(self._cache_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            log.warning("Failed to read stats-cache.json: %s", e)
            return None

        today = date.today().isoformat()
        today_entry = next(
            (e for e in raw.get("dailyModelTokens", []) if e["date"] == today),
            None,
        )
        if today_entry is None:
            return None

        model = next(iter(today_entry.get("tokensByModel", {})), "unknown")
        model_usage = raw.get("modelUsage", {}).get(model, {})

        return UsageSnapshot(
            provider_id=self.PROVIDER_ID,
            timestamp=datetime.now(tz=UTC),
            model=model,
            input_tokens=model_usage.get("inputTokens", 0),
            output_tokens=model_usage.get("outputTokens", 0),
            cache_read_tokens=model_usage.get("cacheReadInputTokens", 0),
            cache_write_tokens=model_usage.get("cacheCreationInputTokens", 0),
            cost_usd=model_usage.get("costUSD", 0.0),
        )

    def ping(self) -> RateLimitState | None:
        if not self._api_key:
            return None
        try:
            resp = self._http.post(
                _PING_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=_PING_BODY,
                timeout=10.0,
            )
        except httpx.HTTPError as e:
            log.warning("Claude API ping failed: %s", e)
            return None

        return self._parse_rate_limit_headers(resp.headers)

    def _parse_rate_limit_headers(
        self, headers: httpx.Headers
    ) -> RateLimitState | None:
        remaining_str = headers.get("anthropic-ratelimit-tokens-remaining")
        limit_str = headers.get("anthropic-ratelimit-tokens-limit")
        reset_str = headers.get("anthropic-ratelimit-tokens-reset")
        requests_str = headers.get("anthropic-ratelimit-requests-remaining")

        if not all([remaining_str, limit_str, reset_str]):
            return None

        try:
            remaining = int(remaining_str)
            limit = int(limit_str)
            remaining_pct = remaining / limit if limit > 0 else 0.0
            reset_at = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
            requests_remaining = int(requests_str) if requests_str else None
        except (ValueError, ZeroDivisionError) as e:
            log.warning("Failed to parse rate limit headers: %s", e)
            return None

        return RateLimitState(
            provider_id=self.PROVIDER_ID,
            remaining_pct=remaining_pct,
            reset_at=reset_at,
            limit_type="5hr_window",
            requests_remaining=requests_remaining,
        )
