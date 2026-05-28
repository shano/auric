import tomllib
from pathlib import Path

import tomli_w

from auric.models.config import AppConfig, ProviderConfig

_DEFAULTS: dict = {
    "claude": {
        "api_key": "",
        "ping_interval": 300,
        "poll_interval": 30,
        "enabled": True,
    }
}


class ConfigManager:
    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or Path.home() / ".config" / "auric" / "config.toml"

    def load(self) -> AppConfig:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(tomli_w.dumps(_DEFAULTS))
            return self._build_config(_DEFAULTS)

        raw = tomllib.loads(self._path.read_text())
        merged: dict = {}
        for provider, defaults in _DEFAULTS.items():
            merged[provider] = {**defaults, **raw.get(provider, {})}
        return self._build_config(merged)

    def _build_config(self, raw: dict) -> AppConfig:
        providers = {
            provider_id: ProviderConfig(
                api_key=vals.get("api_key", ""),
                ping_interval_s=vals.get("ping_interval", 300),
                poll_interval_s=vals.get("poll_interval", 30),
                enabled=vals.get("enabled", True),
            )
            for provider_id, vals in raw.items()
        }
        return AppConfig(providers=providers)
