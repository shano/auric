import json
import os
from pathlib import Path

from auric.models.provider import Provider, ProviderStatus


class AutoDetector:
    def __init__(self, home_dir: Path | None = None) -> None:
        self._home = home_dir or Path.home()

    def detect_all(self) -> list[Provider]:
        return [self.detect_claude(), self.detect_vibe()]

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

    def detect_vibe(self) -> Provider:
        config = self._home / ".vibe" / "config.toml"
        if not config.exists():
            return Provider(
                id="vibe",
                display_name="Mistral Vibe",
                status=ProviderStatus.NOT_DETECTED,
            )
        if not self.resolve_vibe_api_key():
            return Provider(
                id="vibe",
                display_name="Mistral Vibe",
                status=ProviderStatus.NOT_DETECTED,
            )
        return Provider(
            id="vibe", display_name="Mistral Vibe", status=ProviderStatus.ACTIVE
        )

    def resolve_vibe_api_key(self) -> str:
        env_file = self._home / ".vibe" / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text().splitlines():
                    if line.startswith("MISTRAL_API_KEY="):
                        return line.split("=", 1)[1].strip().strip("'\"")
            except OSError:
                pass
        return os.environ.get("MISTRAL_API_KEY", "")

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
