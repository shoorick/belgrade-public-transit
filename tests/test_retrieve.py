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


@pytest.mark.parametrize(
    "suffixed,expected",
    [
        (42, 42),
        ("42", 42),
        ("42s", 42),
        ("3m", 3 * 60),
        ("1h", 60 * 60),
        ("2d", 2 * 60 * 60 * 24),
        ("7w", 7 * 60 * 60 * 24 * 7),
        ("", None),
    ]
)
def test_parse_time(suffixed, expected):
    assert r.parse_time(suffixed) == expected