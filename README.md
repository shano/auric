# Auric

Linux/GNOME system tray application that monitors AI coding tool usage, rate limits, and costs live.

**v1 supports:** Claude Code

## Requirements

```
sudo dnf install python3-gobject libayatana-appindicator-gtk3   # Fedora
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0     # Ubuntu/Debian
sudo pacman -S python-gobject gtk3                               # Arch
```

## Install

```bash
uv venv --python /usr/bin/python3 --system-site-packages .venv
uv sync
uv run auric
```

## Data sources

- `~/.claude/stats-cache.json` — polled every 30s for historical usage
- `POST /v1/messages` — pinged every 5min to harvest `x-ratelimit-*` headers

## Development

```bash
uv sync --dev
uv run pytest --cov
pre-commit install
```
