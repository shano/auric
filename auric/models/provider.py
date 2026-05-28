from dataclasses import dataclass
from enum import Enum

from auric.models.usage import RateLimitState, UsageSnapshot


class ProviderStatus(Enum):
    ACTIVE = "active"
    NOT_DETECTED = "not_detected"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    DEGRADED = "degraded"


@dataclass
class Provider:
    id: str
    display_name: str
    status: ProviderStatus
    rate_limit: RateLimitState | None = None
    last_snapshot: UsageSnapshot | None = None
    error_msg: str | None = None
