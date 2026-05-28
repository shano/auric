from pathlib import Path

import httpx

from auric.app import AppController
from auric.config.manager import ConfigManager
from auric.providers.claude import ClaudeProvider
from auric.services.collector import UsageCollector
from auric.services.detector import AutoDetector
from auric.services.storage import SQLiteStorage
from auric.views.tray import TrayIcon


def build() -> AppController:
    config = ConfigManager().load()
    detector = AutoDetector()
    providers_state = detector.detect_all()

    http_client = httpx.Client()
    storage = SQLiteStorage()

    providers = []
    for provider_state in providers_state:
        if provider_state.id == "claude":
            cfg = config.providers.get("claude")
            api_key = (
                cfg.api_key
                if cfg and cfg.api_key
                else detector.resolve_claude_api_key()
            )
            impl = ClaudeProvider(
                stats_cache_path=Path.home() / ".claude" / "stats-cache.json",
                http_client=http_client,
                api_key=api_key,
            )
            providers.append((provider_state, impl))

    collector = UsageCollector(providers=providers, storage=storage)
    tray = TrayIcon()
    return AppController(config=config, collector=collector, tray=tray)
