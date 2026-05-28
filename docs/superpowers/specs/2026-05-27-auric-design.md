# Auric — Design Document

**Date:** 2026-05-27
**Status:** Approved
**Python:** ≥3.11 required (uses stdlib `tomllib`, `match` statements)

## Problem

Linux/GNOME users who rely on AI coding tools (Claude Code, Gemini CLI, Codex, Mistral, DeepSeek) have no equivalent to SessionWatcher (macOS). There is no ambient, always-visible indicator of live rate limits, token usage, and costs across AI providers.

## What Auric Is

A Python system tray application for Linux/GNOME that:

- Auto-detects installed AI coding tools
- Polls local data files for historical usage (tokens, costs, models)
- Pings provider APIs at low frequency to capture live rate-limit state from response headers
- Displays current usage, % remaining in rate-limit window, reset time, and today's token/cost totals in a GTK tray popup menu

Auric does **not** summarise coding sessions, intercept network traffic, or require proxy configuration.

---

## Scope

### v1 (this document)

- Claude Code only
- System tray indicator + popup menu
- Auto-detect + manual config override
- Live rate-limit ping (every 5 min)
- Historical stats from `~/.claude/stats-cache.json` (poll every 30s)
- SQLite local cache for trend storage
- Full test suite, ruff, bandit, pre-commit

### Out of scope for v1

- Gemini, Codex, Mistral, DeepSeek providers (architecture supports them; implementation deferred)
- Dashboard window
- Notifications / alerts
- Systemd user service (daemon mode)
- Cost estimation for subscription plans beyond $0.00 display

---

## Architecture

Single Python process. GTK main loop runs on the main thread via GLib. Background threads handle I/O (API pings); results are delivered back to the main thread via `GLib.idle_add()`. No async framework — avoids the fragile gbulb dependency.

Pattern: **MVC + dependency injection**. `container.py` constructs every object and injects dependencies. No globals, no singletons. Views hold no business logic.

### Package Layout

```
auric/
├── main.py              # entry point — build container, start GLib loop
├── container.py         # DI wiring
├── app.py               # AppController — owns GLib loop, shutdown signal
├── models/
│   ├── provider.py      # Provider, ProviderStatus
│   ├── usage.py         # UsageSnapshot, RateLimitState
│   └── config.py        # AppConfig
├── providers/
│   ├── base.py          # AbstractProvider interface
│   └── claude.py        # ClaudeProvider
├── services/
│   ├── collector.py     # UsageCollector — schedules and orchestrates polling
│   ├── detector.py      # AutoDetector — finds installed providers
│   └── storage.py       # SQLiteStorage
├── views/
│   ├── tray.py          # AppIndicator icon + left/right click handling
│   └── menu.py          # GTK popup menu — renders provider list
├── config/
│   └── manager.py       # reads/writes ~/.config/auric/config.toml
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
        └── stats-cache.json
```

---

## Data Model

All models are plain Python dataclasses. No GTK dependency in models layer.

```python
class ProviderStatus(Enum):
    ACTIVE        = "active"
    NOT_DETECTED  = "not_detected"
    RATE_LIMITED  = "rate_limited"
    AUTH_ERROR    = "auth_error"
    DEGRADED      = "degraded"   # stale data, network failure

@dataclass
class RateLimitState:
    provider_id: str
    remaining_pct: float          # 0.0–1.0
    reset_at: datetime
    limit_type: str               # "5hr_window" | "daily" | "requests"
    requests_remaining: int | None
    is_stale: bool = False        # True after 2 consecutive missed pings

@dataclass
class UsageSnapshot:
    provider_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float

@dataclass
class Provider:
    id: str
    display_name: str
    status: ProviderStatus
    rate_limit: RateLimitState | None
    last_snapshot: UsageSnapshot | None
    error_msg: str | None = None

@dataclass
class AppConfig:
    providers: dict[str, ProviderConfig]

@dataclass
class ProviderConfig:
    api_key: str = ""             # blank = auto-detect
    ping_interval_s: int = 300
    poll_interval_s: int = 30
    enabled: bool = True
```

---

## Polling Strategy

Two GLib timer loops per provider:

| Loop | Default interval | Mechanism | Data source | Output |
|---|---|---|---|---|
| File poll | 30s | `GLib.timeout_add_seconds` (main thread) | `~/.claude/stats-cache.json` | `UsageSnapshot` |
| API ping | 300s | `threading.Thread` + `GLib.idle_add` | `POST /v1/messages` (1 token) | `RateLimitState` |

### API Ping Detail

```
POST https://api.anthropic.com/v1/messages
{"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}
```

Headers extracted regardless of response body:
- `anthropic-ratelimit-tokens-remaining`
- `anthropic-ratelimit-tokens-reset`
- `anthropic-ratelimit-requests-remaining`

Cost on Max plan: effectively $0.00 per ping (1 output token, covered by subscription).
Cost on API key: ~$0.000001 per ping at Haiku pricing.

### File Poll Detail

Reads `~/.claude/stats-cache.json`. Extracts:
- `dailyModelTokens` → today's token count by model
- `modelUsage` → cumulative totals
- `dailyActivity` → session/message/tool counts

Stats-cache.json is written by Claude Code — we treat it as read-only.

---

## Provider Detection

Runs at startup and on manual "Re-detect" from tray menu.

### Claude detection sequence

1. Check `~/.claude/settings.json` exists
2. Resolve API key (priority order):
   1. `config.toml` `[claude] api_key`
   2. `ANTHROPIC_API_KEY` environment variable
   3. Claude Code OAuth token from `~/.claude/.credentials.json`
3. Key found → `ACTIVE`, trigger immediate ping
4. No key → `NOT_DETECTED`, greyed out in menu, no polling

---

## Error Handling

| Condition | Status | UI behaviour |
|---|---|---|
| Ping succeeds | `ACTIVE` | progress bar + stats |
| Ping 429 | `RATE_LIMITED` | bar at 0%, red tint |
| Ping 401/403 | `AUTH_ERROR` | orange warning, tooltip explains |
| Network failure | `DEGRADED` | last known data + "(stale)" label |
| stats-cache.json missing | `DEGRADED` | log warning, retry next interval |
| Not installed/no key | `NOT_DETECTED` | greyed row, no polling |

**Backoff on API errors:** 30s → 60s → 120s → 300s cap. Resets to normal on next success.

**Stale threshold:** `DEGRADED` after 2 consecutive missed pings (~10 min). A missed ping is any `httpx` exception or HTTP non-2xx response from the API.

**Thread safety:** All thread→UI updates via `GLib.idle_add()`. No shared mutable state between ping thread and main thread except `threading.Lock`-protected provider state.

---

## SQLite Schema

```sql
CREATE TABLE usage_snapshots (
    id                  INTEGER PRIMARY KEY,
    provider_id         TEXT NOT NULL,
    timestamp           INTEGER NOT NULL,   -- unix epoch
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER NOT NULL,
    cache_read_tokens   INTEGER NOT NULL,
    cache_write_tokens  INTEGER NOT NULL,
    cost_usd            REAL NOT NULL
);

CREATE TABLE rate_limit_snapshots (
    id              INTEGER PRIMARY KEY,
    provider_id     TEXT NOT NULL,
    timestamp       INTEGER NOT NULL,
    remaining_pct   REAL NOT NULL,
    reset_at        INTEGER NOT NULL,
    limit_type      TEXT NOT NULL
);

CREATE INDEX idx_usage_provider_ts ON usage_snapshots(provider_id, timestamp);
CREATE INDEX idx_ratelimit_provider_ts ON rate_limit_snapshots(provider_id, timestamp);
```

DB location: `~/.local/share/auric/auric.db`

---

## Config File

Location: `~/.config/auric/config.toml`

```toml
[claude]
api_key = ""          # blank = auto-detect
ping_interval = 300   # seconds
poll_interval = 30    # seconds
enabled = true
```

Created with defaults on first run if absent. Never stores OAuth tokens — those stay in Claude Code's own auth files.

---

## UI

### Tray Icon

- Library: `libayatana-appindicator` via `gi.repository.AppIndicator3`
- Icon: gold hexagon SVG (scalable, theme-compatible)
- Label: `"68%"` (remaining % of tightest active rate limit) or `"—"` if no provider active

### Popup Menu (GTK)

Per provider (v1: Claude only):

```
Claude Max                        68%
[████████████████░░░░░░░]
Resets 12:20AM · 2h 18m left
Today: 84k tokens · $0.00
────────────────────────────────
Re-detect providers
Settings...
Quit
```

Not-detected providers show as greyed-out single line: `Gemini · not detected`

---

## Toolchain

| Tool | Purpose |
|---|---|
| `uv` | dependency management, virtualenv |
| `ruff` | lint + format (replaces flake8, isort, black) |
| `pytest` + `pytest-cov` | test runner, coverage (≥80% required) |
| `bandit` | security static analysis |
| `pre-commit` | gates: ruff + bandit on every commit |
| `pyproject.toml` | single config file for all tools |

### Key runtime dependencies

| Package | Why |
|---|---|
| `PyGObject` | GTK4 + GLib bindings |
| `libayatana-appindicator3` | system tray (system package) |
| `httpx` | API pings (sync client, future async-compatible) |
| `tomllib` (stdlib) | config parsing (requires Python ≥3.11) |

No ORM. stdlib `sqlite3` only.

---

## Testing Strategy

### Unit tests

- `ClaudeProvider` receives `stats_cache_path: Path` and `http_client: httpx.Client` as constructor args — both swappable in tests
- `AutoDetector` receives `home_dir: Path` — tests use `tmp_path`
- `SQLiteStorage` receives `db_path: Path` — tests use `tmp_path / "test.db"`
- Views hold zero logic — not unit tested

### Integration tests

- File poller: reads `tests/fixtures/stats-cache.json` (real scrubbed snapshot)
- API pinger: `respx` mock server returns realistic `x-ratelimit-*` headers

### Boundaries

Mock at: filesystem (`tmp_path`), HTTP (`respx`). Never mock internal classes.

### CI gates

```
ruff check .
ruff format --check .
pytest --cov=auric --cov-fail-under=80
bandit -r auric/ -ll
```

---

## Directory Structure (repo root)

```
SessionWatcherLinux/
├── auric/               # application package
├── tests/               # pytest suite
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-27-auric-design.md
├── pyproject.toml
├── README.md
└── .pre-commit-config.yaml
```

---

## Out of Scope (future sprints)

- Additional providers: Gemini, Codex, Mistral, DeepSeek
- Dashboard window (usage history charts)
- Desktop notifications (rate limit threshold alerts)
- Systemd user service (background daemon mode)
- Flatpak / AUR packaging
