import logging
import signal
import threading

import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from auric.models.config import AppConfig  # noqa: E402
from auric.services.collector import UsageCollector  # noqa: E402
from auric.views.tray import TrayIcon  # noqa: E402

log = logging.getLogger(__name__)


class AppController:
    def __init__(
        self,
        config: AppConfig,
        collector: UsageCollector,
        tray: TrayIcon,
    ) -> None:
        self._config = config
        self._collector = collector
        self._tray = tray

    def start(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self._quit())
        self._initial_update()
        self._schedule_timers()
        Gtk.main()

    def _initial_update(self) -> None:
        for provider in self._collector.all_providers():
            self._run_poll_bg(provider.id)
            self._run_ping_bg(provider.id)

    def _schedule_timers(self) -> None:
        for provider in self._collector.all_providers():
            cfg = self._config.providers.get(provider.id)
            if cfg and cfg.enabled:
                GLib.timeout_add_seconds(
                    cfg.poll_interval_s, self._poll_tick, provider.id
                )
                GLib.timeout_add_seconds(
                    cfg.ping_interval_s, self._ping_tick, provider.id
                )

    def _poll_tick(self, provider_id: str) -> bool:
        self._run_poll_bg(provider_id)
        return GLib.SOURCE_CONTINUE

    def _ping_tick(self, provider_id: str) -> bool:
        self._run_ping_bg(provider_id)
        return GLib.SOURCE_CONTINUE

    def _run_poll_bg(self, provider_id: str) -> None:
        def _work() -> None:
            self._collector.run_poll(provider_id)
            GLib.idle_add(self._refresh_tray)

        threading.Thread(target=_work, daemon=True).start()

    def _run_ping_bg(self, provider_id: str) -> None:
        def _work() -> None:
            self._collector.run_ping(provider_id)
            GLib.idle_add(self._refresh_tray)

        threading.Thread(target=_work, daemon=True).start()

    def _refresh_tray(self) -> bool:
        self._tray.update(self._collector.all_providers())
        return GLib.SOURCE_REMOVE

    def _quit(self) -> None:
        log.info("Shutting down Auric")
        Gtk.main_quit()
