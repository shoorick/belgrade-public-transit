from pathlib import Path
import sqlite3

from public_transit.config import read_config


def get_root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def get_db_path(root_dir: Path | None = None) -> Path:
    if root_dir is None:
        root_dir = get_root_dir()
    config = read_config(root_dir)
    data_dir = (root_dir / config.data.dir).resolve()
    return (data_dir / config.data.db).resolve()


def connect_db(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    return sqlite3.connect(str(db_path))
