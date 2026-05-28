from datetime import UTC, date

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from auric.models.provider import Provider, ProviderStatus  # noqa: E402


class PopupMenu:
    def __init__(self) -> None:
        self._menu = Gtk.Menu()

    def build(self, providers: list[Provider]) -> Gtk.Menu:
        for child in self._menu.get_children():
            self._menu.remove(child)

        for provider in providers:
            self._add_provider_section(provider)

        self._menu.append(Gtk.SeparatorMenuItem())
        self._add_action("Re-detect providers", None)
        self._add_action("Settings...", None)
        self._add_action("Quit", Gtk.main_quit)
        self._menu.show_all()
        return self._menu

    def _add_provider_section(self, provider: Provider) -> None:
        if provider.status == ProviderStatus.NOT_DETECTED:
            item = Gtk.MenuItem(label=f"{provider.display_name} · not detected")
            item.set_sensitive(False)
            self._menu.append(item)
            return

        label = self._format_label(provider)
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(False)
        self._menu.append(item)

    def _format_label(self, provider: Provider) -> str:
        parts = [provider.display_name]
        if provider.rate_limit:
            pct = provider.rate_limit.remaining_pct_display
            reset = provider.rate_limit.reset_at.strftime("%-I:%M%p").lower()
            parts.append(f"{pct}% · resets {reset}")
        if provider.last_snapshot:
            total = provider.last_snapshot.total_tokens
            cost = provider.last_snapshot.cost_usd
            snap_date = provider.last_snapshot.timestamp.astimezone(UTC).date()
            day_label = (
                "Today" if snap_date == date.today() else snap_date.strftime("%b %-d")
            )
            parts.append(f"{day_label}: {total:,} tokens · ${cost:.2f}")
        return " | ".join(parts)

    def _add_action(self, label: str, callback) -> None:
        item = Gtk.MenuItem(label=label)
        if callback:
            item.connect("activate", lambda _: callback())
        self._menu.append(item)
