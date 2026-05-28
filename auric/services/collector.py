import logging
import threading

from auric.models.provider import Provider
from auric.providers.base import AbstractProvider
from auric.services.storage import SQLiteStorage

log = logging.getLogger(__name__)


class UsageCollector:
    def __init__(
        self,
        providers: list[tuple[Provider, AbstractProvider]],
        storage: SQLiteStorage,
    ) -> None:
        self._storage = storage
        self._lock = threading.Lock()
        self._by_id: dict[str, tuple[Provider, AbstractProvider]] = {
            p.id: (p, impl) for p, impl in providers
        }

    def run_poll(self, provider_id: str) -> None:
        entry = self._by_id.get(provider_id)
        if entry is None:
            return
        provider, impl = entry
        try:
            snapshot = impl.poll()
        except Exception as e:
            log.warning("Poll failed for %s: %s", provider_id, e)
            return
        if snapshot is None:
            return
        self._storage.save_snapshot(snapshot)
        with self._lock:
            provider.last_snapshot = snapshot

    def run_ping(self, provider_id: str) -> None:
        entry = self._by_id.get(provider_id)
        if entry is None:
            return
        provider, impl = entry
        try:
            rate_limit = impl.ping()
        except Exception as e:
            log.warning("Ping failed for %s: %s", provider_id, e)
            return
        if rate_limit is None:
            return
        self._storage.save_rate_limit(rate_limit)
        with self._lock:
            provider.rate_limit = rate_limit

    def get_provider_state(self, provider_id: str) -> Provider | None:
        entry = self._by_id.get(provider_id)
        return entry[0] if entry else None

    def all_providers(self) -> list[Provider]:
        return [p for p, _ in self._by_id.values()]
