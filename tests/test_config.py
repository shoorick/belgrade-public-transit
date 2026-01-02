import pytest
import re
from pathlib import Path
from types import SimpleNamespace

from public_transit.config import read_config

def test_read_config():
    repo_root = Path(__file__).resolve().parents[1]
    config = read_config(repo_root)
    
    assert isinstance(config, SimpleNamespace)
    
    assert re.fullmatch(r"[\w/\.]+", config.data.dir)
    assert re.fullmatch(r"[\w/\.]+", config.data.db)
    assert re.match(r"^https?://", config.bus.source)
    assert re.match(r"^\d+[wdhms]?$", str(config.bus.expire))

def test_failed_read_config():
    with pytest.raises(FileNotFoundError):
        read_config(Path("/nonexistent"))
