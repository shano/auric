import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from auric.models.provider import Provider, ProviderStatus  # noqa: E402

_LIMIT_LABELS = {
    "5hr_window": "5h",
    "1min_window": "1min",
    "token_window": "tokens",
}


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
            rl = provider.rate_limit
            label = _LIMIT_LABELS.get(rl.limit_type, rl.limit_type)
            if rl.limit_type == "1min_window":
                parts.append(f"{label}: {rl.remaining_pct_display}%")
            else:
                reset = rl.reset_at.astimezone().strftime("%-I:%M%p").lower()
                parts.append(f"{label}: {rl.remaining_pct_display}% · resets {reset}")
            if rl.weekly_remaining_pct is not None and rl.weekly_reset_at is not None:
                weekly_reset = (
                    rl.weekly_reset_at.astimezone().strftime("%a %-I:%M%p").lower()
                )
                parts.append(
                    f"7d: {rl.weekly_remaining_pct_display}% · resets {weekly_reset}"
                )
        elif provider.last_snapshot is not None:
            s = provider.last_snapshot
            tokens_k = (s.input_tokens + s.output_tokens) / 1000
            parts.append(f"{tokens_k:.1f}K tokens · ${s.cost_usd:.4f} today")
        return " | ".join(parts)

    def _add_action(self, label: str, callback) -> None:
        item = Gtk.MenuItem(label=label)
        if callback:
            item.connect("activate", lambda _: callback())
        self._menu.append(item)
