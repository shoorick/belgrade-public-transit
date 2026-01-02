from pathlib import Path
from types import SimpleNamespace

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


def read_config(repo_root: Path):
    """
    Read and parse configuration from YAML file.
    """
    config_path = repo_root / "config.yaml"
    if not config_path.exists():
        config_path = repo_root / "config.yml"
    if not config_path.exists():
        raise FileNotFoundError("config.yaml or config.yml not found")

    config = load_config(config_path)

    # Validate configuration
    if not hasattr(config, "data") or not hasattr(config.data, "dir"):
        raise KeyError("Missing config.data.dir in YAML")
    if not hasattr(config.data, "db"):
        raise KeyError("Missing config.data.db in YAML")
    if not hasattr(config, "bus") or not hasattr(config.bus, "source"):
        raise KeyError("Missing config.bus.source in YAML")

    return config
