from abc import ABC, abstractmethod

from auric.models.usage import RateLimitState, UsageSnapshot


class AbstractProvider(ABC):
    @abstractmethod
    def poll(self) -> UsageSnapshot | None:
        """Read local files and return today's usage snapshot, or None on failure."""

    @abstractmethod
    def ping(self) -> RateLimitState | None:
        """Make a lightweight API call and return live rate limit state, or None."""
