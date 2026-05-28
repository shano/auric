from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    api_key: str = ""
    ping_interval_s: int = 300
    poll_interval_s: int = 30
    enabled: bool = True


@dataclass
class AppConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
