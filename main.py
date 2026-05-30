import os
import time
from enum import Enum

import qbittorrentapi


def getenv_required(name: str) -> str:
    value = os.getenv(name)

    if value is None:
        raise ValueError(f"{name} environment variable not set")

    return value


TARGET_RATIO = float(getenv_required("TARGET_RATIO"))
LOOP_INTERVAL_SECONDS = int(getenv_required("LOOP_INTERVAL_SECONDS"))
DELETE_FILES = (getenv_required("DELETE_FILES").lower() == "true")


def bytes_to_gib(x: int) -> float:
    return x / (1024 ** 3)


def seconds_to_days(x: int) -> float:
    return x / (24 * 3600)


def torrent_timeout(size_gib: float) -> float:
    # fine tune parameters here:
    # https://www.desmos.com/calculator/vcxftplzyi
    c = 5
    b = 2
    d = 120
    a = 15.8

    x = max(0, size_gib)

    return c + (d - c) / (1 + (x / a) ** b)


def initialise_client() -> qbittorrentapi.Client:
    client = qbittorrentapi.Client(
        host=getenv_required("QB_HOST"),
        username=getenv_required("QB_USER"),
        password=getenv_required("QB_PASS"),
    )

    client.auth_log_in()

    return client


class DeleteReason(Enum):
    DONT = "dont"
    RATIO = "ratio"
    TIMEOUT = "timeout"


def should_delete(
    torrent: qbittorrentapi.TorrentDictionary,
) -> DeleteReason:
    size_gib = bytes_to_gib(torrent.size)
    timeout_days = torrent_timeout(size_gib)
    seeding_days = seconds_to_days(torrent.seeding_time)
    ratio = max(0.0, torrent.ratio or 0.0)

    if torrent.progress < 0.999: # don't delete if torrent isn't fully downloaded
        return DeleteReason.DONT

    if ratio >= TARGET_RATIO: # delete if target ratio is reached
        return DeleteReason.RATIO

    if seeding_days >= timeout_days: # delete if seeding time exceeds timeout
        return DeleteReason.TIMEOUT

    return DeleteReason.DONT # keep seeding


def main() -> int:
    client = None

    while True:
        try:
            if client is None:
                print("Connecting to qBittorrent...")
                client = initialise_client()
                print("Connected.")

            torrents = client.torrents.info()

            for torrent in torrents:
                try:
                    can_delete = should_delete(torrent)

                    if can_delete != DeleteReason.DONT:
                        print(f"Removing: {torrent.name}", end="")

                        match can_delete:
                            case DeleteReason.RATIO:
                                print(" (ratio)")

                            case DeleteReason.TIMEOUT:
                                print(" (timeout)")

                        try:
                            torrent.delete(
                                delete_files=DELETE_FILES,
                                torrent_hashes=torrent.hash,
                            )
                        except:
                            print(
                                f"Failed deleting torrent "
                                f"{torrent.name} (hash: {torrent.hash})"
                            )

                except Exception as e:
                    print(
                        f"Failed processing torrent "
                        f"{torrent.name}: {e}"
                    )

        except (
            qbittorrentapi.LoginFailed,
            qbittorrentapi.APIConnectionError,
            qbittorrentapi.APIError,
        ) as e:
            print(f"Connection/API failure: {e}")

            client = None

        except Exception as e:
            print(f"Unexpected error: {e}")

        finally:
            time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
