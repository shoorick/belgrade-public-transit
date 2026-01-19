import argparse
import os
import time
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

import pandas as pd

from public_transit.config import read_config
import public_transit.message as message
import public_transit.project as project

def url_basename(url: str) -> str:
    """
    Extract the basename from a URL.
    """
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def parse_time(expire) -> float | None:
    """
    Parse time value with possible suffixes s/m/h/d/w to seconds.
    """
    if expire is None:
        return None

    if isinstance(expire, (int, float)):
        return float(expire)

    if isinstance(expire, str):
        s = expire.strip().lower()
        if not s:
            return None

        unit = s[-1]
        if unit.isdigit():
            return float(s)

        value = float(s[:-1])
        multipliers = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800,
        }
        if unit not in multipliers:
            raise ValueError("Unsupported expire unit; use s/m/h/d/w")
        return value * multipliers[unit]

    raise TypeError("expire must be a number of seconds or a string like '24h'")


def is_path_expired(path: Path, expire_seconds: float | None, now: float | None = None) -> bool:
    if expire_seconds is None:
        return False

    if now is None:
        now = time.time()

    mtime = path.stat().st_mtime
    age_seconds = now - mtime
    return age_seconds > expire_seconds


def zip_to_sqlite(zip_path: Path, db_path: Path, verbosity: int = 1) -> None:
    """
    Convert GTFS zip archive to SQLite database.
    """
    msg = message.Message(verbosity)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_mtime = datetime.fromtimestamp(zip_path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    msg.write(f"Dataset modified at {dataset_mtime}", message.VERBOSE)

    with sqlite3.connect(str(db_path)) as conn:
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                name_in_zip = info.filename
                if not name_in_zip.lower().endswith(".txt"):
                    continue

                table_name = Path(name_in_zip).stem
                table_mtime = datetime(*info.date_time).astimezone().isoformat(timespec="seconds")
                msg.write(f"{table_name} modified at {table_mtime}", message.VERBOSE)

                with zf.open(info, "r") as raw:
                    df = pd.read_csv(raw, encoding="utf-8")
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                msg.write(f"Wrote table: {table_name} ({len(df)} rows)", message.VERBOSE)

                for column in df.columns:
                    if column.lower().endswith("_id") or (
                        table_name == "stops" and column in {"stop_code", "stop_name", "stop_lat", "stop_lon"}
                    ) or (
                        table_name == "stop_times" and column == "arrival_time"
                    ):
                        index_name = f"{table_name}_{column}_IDX"
                        conn.execute(
                            f'CREATE INDEX IF NOT EXISTS "{index_name}" '
                            f'ON "{table_name}" ("{column}")'
                        )
                        msg.write(f"Created index: {index_name}", message.VERBOSE)


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(add_help=True)

    # Verbosity: only -q or -v can be used, not both
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress unnecessary messages")
    group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more messages")

    parser.add_argument(
        "-f",
        "--force",
        choices=["download", "parse", "all"],
        help="Force actions even if data already processed: download GTFS data, parse it and store to database, or both",
    )

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    verbosity = message.NORMAL
    if args.quiet:
        verbosity = message.QUIET
    elif args.verbose:
        verbosity = message.VERBOSE

    msg = message.Message(verbosity)

    force_download = args.force in {"download", "all"}
    force_parse = args.force in {"parse", "all"}

    root_dir = project.get_root_dir()

    config = read_config(root_dir)

    data_dir = (root_dir / config.data.dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    zip_name = url_basename(config.bus.source)
    zip_path = data_dir / zip_name

    zip_expired = False
    if zip_path.exists() and not force_download:
        expire_seconds = parse_time(getattr(config.bus, "expire", None))
        zip_expired = is_path_expired(zip_path, expire_seconds)
        if not zip_expired and not force_parse:
            msg.write(f"File already exists: {zip_path}")
            return 0

    if force_download or (not zip_path.exists()) or zip_expired:
        msg.write(f"Downloading {config.bus.source} -> {zip_path}")
        urlretrieve(config.bus.source, zip_path)

    db_path = project.get_db_path(root_dir)
    msg.write(f"Writing SQLite DB: {db_path}")
    zip_to_sqlite(zip_path, db_path, verbosity=verbosity)
    return 0
