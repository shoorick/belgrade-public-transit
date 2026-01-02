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
        # Common days
        ((2026, 1, 3), {"S"}),
        ((2026, 1, 4), {"N"}),
        ((2026, 1, 5), {"RD"}),
        # Future holidays
        ((2033, 1, 1), {"N"}),
        ((2033, 11, 11), {"N"}),
        # Holidays, this year
        ((2026, 1, 1), {"N"}),
        ((2026, 1, 2), {"N"}),
        ((2026, 1, 7), {"N"}),
        ((2026, 2, 15), {"N"}),
        ((2026, 2, 16), {"N"}),
        ((2026, 2, 17), {"N"}),
        ((2026, 4, 10), {"N"}),
        ((2026, 4, 12), {"N"}),
        ((2026, 4, 13), {"N"}),
        ((2026, 5, 1), {"N"}),
        ((2026, 5, 2), {"N"}),
        # Past holidays, last year
        ((2025, 1, 1), {"N"}),
        ((2025, 1, 2), {"N"}),
        ((2025, 1, 7), {"N"}),
        ((2025, 2, 15), {"N"}),
        ((2025, 2, 16), {"N"}),
        ((2025, 2, 17), {"N"}),
        ((2025, 4, 18), {"N"}),
        ((2025, 4, 20), {"N"}),
        ((2025, 4, 21), {"N"}),
        ((2025, 5, 1), {"N"}),
        ((2025, 5, 2), {"N"}),
        ((2025, 11, 11), {"N"}),
        # few years ago
        ((2020, 1, 1), {"N"}),
        ((2020, 11, 11), {"N"}),
    ]
)
def test_detect_service_type(date, expected):
    assert s.detect_service_type(datetime(*date)) == expected
