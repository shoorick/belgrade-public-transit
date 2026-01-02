#!/usr/bin/env python3

import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from urllib.request import urlretrieve

import gtfs_kit as gk
import pandas as pd
import yaml


def dict_to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: dict_to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [dict_to_namespace(v) for v in value]
    return value


def load_config(config_path: Path):
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raw = {}
    return dict_to_namespace(raw)


def url_basename(url: str) -> str:
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def read_config(repo_root: Path):
    config_path = repo_root / "config.yaml"
    if not config_path.exists():
        config_path = repo_root / "config.yml"
    if not config_path.exists():
        raise FileNotFoundError("config.yaml or config.yml not found")

    config = load_config(config_path)

    if not hasattr(config, "data") or not hasattr(config.data, "dir"):
        raise KeyError("Missing config.data.dir in YAML")
    if not hasattr(config.data, "db"):
        raise KeyError("Missing config.data.db in YAML")
    if not hasattr(config, "bus") or not hasattr(config.bus, "source"):
        raise KeyError("Missing config.bus.source in YAML")

    return config


def feed_to_sqlite(feed, db_path: Path) -> None:
    table_names = [
        "agency",
        "stops",
        "routes",
        "trips",
        "stop_times",
        "calendar",
        "calendar_dates",
        "fare_attributes",
        "fare_rules",
        "shapes",
        "frequencies",
        "transfers",
        "feed_info",
        "levels",
        "pathways",
        "translations",
        "attributions",
    ]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        for name in table_names:
            df = getattr(feed, name, None)
            if df is None or isinstance(df, (str, int, float, bool)):
                continue
            if not isinstance(df, pd.DataFrame):
                continue
            df.to_sql(name, conn, if_exists="replace", index=False)


def main() -> int:
    repo_root = Path(__file__).resolve().parent

    config = read_config(repo_root)

    data_dir = (repo_root / config.data.dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    zip_name = url_basename(config.bus.source)
    zip_path = data_dir / zip_name

    if zip_path.exists():
        print(f"File already exists: {zip_path}")
        return 0

    print(f"Downloading {config.bus.source} -> {zip_path}")
    urlretrieve(config.bus.source, zip_path)

    print(f"Reading GTFS feed: {zip_path}")
    feed = gk.read_feed(str(zip_path), dist_units="km")

    db_path = (data_dir / config.data.db).resolve()
    print(f"Writing SQLite DB: {db_path}")
    feed_to_sqlite(feed, db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
