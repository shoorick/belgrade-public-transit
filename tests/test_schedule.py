import pytest

import public_transit.schedule as s
from datetime import datetime

@pytest.mark.parametrize(
    "date,expected",
    [
        ("2025-01-02", datetime(2025, 1, 2)),
        ("2025-01-02 12:34", datetime(2025, 1, 2, 12, 34)),
        ("2025-01-02 12:34:56", datetime(2025, 1, 2, 12, 34, 56)),
        ("20250102", datetime(2025, 1, 2)),
        ("202501021234", datetime(2025, 1, 2, 12, 34)),
        ("20250102123456", datetime(2025, 1, 2, 12, 34, 56)),
    ]
)
def test_parse_absolute_date(date, expected):
    assert s.parse_date(date) == expected

@pytest.mark.parametrize(
    "date,expected",
    [
        (datetime(2026, 1, 2), ["RD"]),
        (datetime(2026, 1, 3), ["S"]),
        (datetime(2026, 1, 4), ["N"]),
    ]
)
def test_detect_service_type(date, expected):
    assert s.detect_service_type(date) == expected
