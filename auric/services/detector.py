import json
import os
from pathlib import Path

from auric.models.provider import Provider, ProviderStatus


class AutoDetector:
    def __init__(self, home_dir: Path | None = None) -> None:
        self._home = home_dir or Path.home()

    def detect_all(self) -> list[Provider]:
        return [self.detect_claude()]

    def detect_claude(self) -> Provider:
        settings = self._home / ".claude" / "settings.json"
        if not settings.exists():
            return Provider(
                id="claude",
                display_name="Claude Code",
                status=ProviderStatus.NOT_DETECTED,
            )
        if not self.resolve_claude_api_key():
            return Provider(
                id="claude",
                display_name="Claude Code",
                status=ProviderStatus.NOT_DETECTED,
            )
        return Provider(
            id="claude", display_name="Claude Code", status=ProviderStatus.ACTIVE
        )

    def resolve_claude_api_key(self) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
        creds = self._home / ".claude" / ".credentials.json"
        if creds.exists():
            try:
                data = json.loads(creds.read_text())
                token = data.get("claudeAiOauth", {}).get("accessToken", "")
                if token:
                    return token
            except (json.JSONDecodeError, OSError):
                pass
        return ""
