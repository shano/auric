import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3

    _HAS_INDICATOR = True
except ValueError:
    _HAS_INDICATOR = False

from auric.models.provider import Provider, ProviderStatus  # noqa: E402
from auric.views.menu import PopupMenu  # noqa: E402

_INDICATOR_ID = "auric"
_ICON_NAME = "appointment-new"


class TrayIcon:
    def __init__(self) -> None:
        self._menu = PopupMenu()
        if _HAS_INDICATOR:
            self._indicator = AppIndicator3.Indicator.new(
                _INDICATOR_ID,
                _ICON_NAME,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        else:
            # Fallback: Gtk.StatusIcon (deprecated but functional outside GNOME Wayland)
            self._status_icon = Gtk.StatusIcon()
            self._status_icon.set_from_icon_name(_ICON_NAME)
            self._status_icon.set_visible(True)
            self._status_icon.connect("popup-menu", self._on_status_icon_popup)
            self._status_icon.connect("activate", self._on_status_icon_activate)
            self._last_menu: Gtk.Menu | None = None

    def update(self, providers: list[Provider]) -> None:
        label = self._compute_label(providers)
        menu = self._menu.build(providers)
        if _HAS_INDICATOR:
            self._indicator.set_label(label, "")
            self._indicator.set_menu(menu)
        else:
            self._status_icon.set_tooltip_text(label)
            self._last_menu = menu

    def _compute_label(self, providers: list[Provider]) -> str:
        active = [p for p in providers if p.status == ProviderStatus.ACTIVE]
        if not active:
            return "—"
        tightest = min(
            (p for p in active if p.rate_limit),
            key=lambda p: p.rate_limit.remaining_pct,
            default=None,
        )
        return f"{tightest.rate_limit.remaining_pct_display}%" if tightest else "·"

    def _on_status_icon_popup(self, icon, button, time) -> None:
        if self._last_menu:
            self._last_menu.popup(None, None, None, None, button, time)

    def _on_status_icon_activate(self, icon) -> None:
        if self._last_menu:
            self._last_menu.popup(
                None, None, None, None, 0, Gtk.get_current_event_time()
            )
