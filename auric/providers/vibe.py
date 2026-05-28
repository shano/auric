import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from auric.models.usage import RateLimitState, UsageSnapshot
from auric.providers.base import AbstractProvider

log = logging.getLogger(__name__)

_PING_URL = "https://api.mistral.ai/v1/chat/completions"
_PING_BODY = {
    "model": "mistral-small-latest",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "."}],
}


class VibeProvider(AbstractProvider):
    PROVIDER_ID = "vibe"

    def __init__(
        self,
        logs_dir: Path,
        http_client: httpx.Client,
        api_key: str = "",
    ) -> None:
        self._logs_dir = logs_dir
        self._http = http_client
        self._api_key = api_key

    def poll(self) -> UsageSnapshot | None:
        today = date.today().isoformat().replace("-", "")
        prefix = f"session_{today}_"

        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = 0.0
        model = "unknown"
        found = False

        try:
            dirs = [
                d
                for d in self._logs_dir.iterdir()
                if d.is_dir() and d.name.startswith(prefix)
            ]
        except OSError as e:
            log.warning("Failed to read vibe session logs: %s", e)
            return None

        for session_dir in dirs:
            meta_path = session_dir / "meta.json"
            try:
                data = json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError) as e:
                log.warning("Failed to read %s: %s", meta_path, e)
                continue

            stats = data.get("stats", {})
            prompt_tokens += stats.get("session_prompt_tokens", 0)
            completion_tokens += stats.get("session_completion_tokens", 0)
            cost_usd += stats.get("session_cost", 0.0)

            if model == "unknown":
                active = data.get("active_model") or data.get("model")
                if active:
                    model = active

            found = True

        if not found:
            return None

        return UsageSnapshot(
            provider_id=self.PROVIDER_ID,
            timestamp=datetime.now(tz=UTC),
            model=model,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            cache_read_tokens=0,
            cache_write_tokens=0,
            cost_usd=cost_usd,
        )

    def ping(self) -> RateLimitState | None:
        if not self._api_key:
            return None
        try:
            resp = self._http.post(
                _PING_URL,
                headers={
                    "authorization": f"Bearer {self._api_key}",
                    "content-type": "application/json",
                },
                json=_PING_BODY,
                timeout=10.0,
            )
        except httpx.HTTPError as e:
            log.warning("Mistral API ping failed: %s", e)
            return None

        return self._parse_rate_limit_headers(resp.headers)

    def _parse_rate_limit_headers(
        self, headers: httpx.Headers
    ) -> RateLimitState | None:
        remaining_str = headers.get("x-ratelimit-remaining-tokens")
        limit_str = headers.get("x-ratelimit-limit-tokens")
        reset_str = headers.get("x-ratelimit-reset-tokens")

        if not all([remaining_str, limit_str, reset_str]):
            return None

        try:
            remaining = int(remaining_str)
            limit = int(limit_str)
            remaining_pct = remaining / limit if limit > 0 else 0.0
            # reset is seconds until reset
            reset_secs = int(reset_str)
            reset_at = datetime.fromtimestamp(
                datetime.now(tz=UTC).timestamp() + reset_secs, tz=UTC
            )
        except (ValueError, ZeroDivisionError) as e:
            log.warning("Failed to parse Mistral rate limit headers: %s", e)
            return None

        return RateLimitState(
            provider_id=self.PROVIDER_ID,
            remaining_pct=remaining_pct,
            reset_at=reset_at,
            limit_type="token_window",
            requests_remaining=None,
        )
