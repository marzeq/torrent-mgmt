# torrent-mgmt

Simple qBittorrent cleanup daemon.

Removes completed torrents when either:
- the target ratio has been reached, or
- the torrent has exceeded a size-adjusted seeding timeout.

Torrents are only considered for removal if they have been inactive for at least 6 hours.

Files can optionally be deleted together with the torrent.

## Requirements

- Python
- uv
- qBittorrent with WebUI enabled

## Environment variables/configuration

[Example .env file](./.env.example) is included.

## Install

```bash
uv sync
```

## Run

```bash
export $(grep -v '^#' .env | xargs) # load environment variables from .env file
uv run python main.py
```

## Timeout behaviour

Torrent timeout is based on size.

Smaller torrents are retained longer than larger torrents.

Current curve:

* ~120 days for very small torrents
* ~60 days around 15 GiB
* ~30 days around 30 GiB
* ~8 days around 100 GiB

Curve can be adjusted in:

```python
def torrent_timeout(size_gib: float) -> float:
```

## systemd

[Service file](./torrent-mgmt.service) is included for running the script as a systemd service.

## Notes

* Only completed torrents are considered.
* Torrents with recent activity are ignored.
* The script retries automatically on qBittorrent API failures.
* No database or persistent state is used, we rely on qBittorrent's API for all state management.
