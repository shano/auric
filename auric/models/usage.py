from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UsageSnapshot:
    provider_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


@dataclass
class RateLimitState:
    provider_id: str
    remaining_pct: float
    reset_at: datetime
    limit_type: str
    requests_remaining: int | None
    is_stale: bool = False

    @property
    def remaining_pct_display(self) -> int:
        return round(self.remaining_pct * 100)
