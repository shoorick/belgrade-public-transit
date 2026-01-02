import argparse
import os
import time
import sqlite3
import zipfile
from io import TextIOWrapper
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

import pandas as pd

from public_transit.config import read_config
import public_transit.message as message

def url_basename(url: str) -> str:
    """
    Extract the basename from a URL.
    """
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def parse_expire_seconds(expire) -> float | None:
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
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                name_in_zip = info.filename
                if not name_in_zip.lower().endswith(".txt"):
                    continue

                table_name = Path(name_in_zip).stem
                with zf.open(info, "r") as raw:
                    text_stream = TextIOWrapper(raw, encoding="utf-8", newline="")
                    df = pd.read_csv(text_stream)
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                message.write(f"Wrote table: {table_name} ({len(df)} rows)", verbosity, message.VERBOSE)


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(add_help=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress unnecessary messages")
    group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more messages")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    verbosity = message.NORMAL
    if args.quiet:
        verbosity = message.QUIET
    elif args.verbose:
        verbosity = message.VERBOSE

    repo_root = Path(__file__).resolve().parents[2]

    config = read_config(repo_root)

    data_dir = (repo_root / config.data.dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    zip_name = url_basename(config.bus.source)
    zip_path = data_dir / zip_name

    if zip_path.exists():
        expire_seconds = parse_expire_seconds(getattr(config.bus, "expire", None))
        if not is_path_expired(zip_path, expire_seconds):
            message.write(f"File already exists: {zip_path}", verbosity)
            return 0

    message.write(f"Downloading {config.bus.source} -> {zip_path}", verbosity)
    urlretrieve(config.bus.source, zip_path)

    db_path = (data_dir / config.data.db).resolve()
    message.write(f"Writing SQLite DB: {db_path}", verbosity)
    zip_to_sqlite(zip_path, db_path, verbosity=verbosity)
    return 0
