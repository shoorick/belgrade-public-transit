import pytest

import public_transit.retrieve as r

@pytest.mark.parametrize(
    "url,name",
    [
        ("https://example.com/path/to/file.txt", "file.txt"),
        ("https://example.com/path/to/file", "file"),
        ("https://example.com/path/to/file/", ""),
    ]
)

def test_url_basename(url,name):
    assert r.url_basename(url) == name
