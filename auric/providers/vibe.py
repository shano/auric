import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from auric.models.usage import RateLimitState, UsageSnapshot
from auric.providers.base import AbstractProvider

log = logging.getLogger(__name__)

_WHOAMI_URL = "https://console.mistral.ai/api/vibe/whoami"


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
            resp = self._http.get(
                _WHOAMI_URL,
                headers={"authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
        except httpx.HTTPError as e:
            log.warning("Mistral whoami ping failed: %s", e)
            return None

        if not resp.is_success:
            log.warning("Mistral whoami returned %s", resp.status_code)
            return None

        return self._parse_whoami(resp.json())

    def _parse_whoami(self, payload: dict) -> RateLimitState | None:
        tokens_used = payload.get("tokens_used", 0) or 0
        tokens_limit = payload.get("tokens_limit", 0) or 0

        if tokens_limit == 0:
            return None

        try:
            tokens_used = int(tokens_used)
            tokens_limit = int(tokens_limit)
            remaining_pct = max(0.0, (tokens_limit - tokens_used) / tokens_limit)
        except (ValueError, ZeroDivisionError) as e:
            log.warning("Failed to parse whoami token fields: %s", e)
            return None

        reset_at = None
        reset_str = payload.get("reset_time")
        if reset_str and isinstance(reset_str, str):
            try:
                reset_at = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        if reset_at is None:
            return None

        return RateLimitState(
            provider_id=self.PROVIDER_ID,
            remaining_pct=remaining_pct,
            reset_at=reset_at,
            limit_type="monthly",
            requests_remaining=None,
        )
