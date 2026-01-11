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


@pytest.mark.parametrize(
    "src,expected",
    [
        ("Калемегдан", "Kalemegdan"),
        ("Тадеуша Кошћушка", "Tadeuša Košćuška"),
        ("Боља", "Bolja"),
        ("Бањица", "Banjica"),
        ("Чукарица", "Čukarica"),
        ("Ђурђевдан", "Đurđevdan"),
        ("Џона Кенедија", "Džona Kenedija"),
        ("Жарково", "Žarkovo"),
    ],
)
def test_transliterate(src, expected):
    assert s.transliterate(src) == expected


@pytest.mark.parametrize(
    "src,expected",
    [
        ("block 44", "blok 44"),
        ("аэродром", "аеродром"),
        ("Батайница", "батајница"),
        ("белый", "бели"),
        ("Блок 70", "блок 70"), # just lowercase
        ("здравля", "здравља"),
        ("Конярник", "коњарник"),
        ("Космайская", "космајска"),
        ("Любице", "љубице"),
        ("Населье", "насеље"),
        ("нёке", "њоке"),
        ("Площадь Славия", "трг славија"),
        ("пл. Републике", "трг републике"),
        ("русская", "руска"),
        ("Савская площадь", "савски трг"),
        ("французская", "француска"),
        ("южный бульвар", "јужни булевар"),
        ("Юнска", "јунска"),
        ("Юрия", "јурија"),
        ("Яково", "јаково"),
    ],
)
def test_fix_typos(src, expected):
    assert s.fix_typos(src) == expected

@pytest.mark.parametrize(
    "name,expected",
    [
        ("Kalemegdan", True), # Human-readable name
        ("nonexistent", False),
        (148, True), # int stop_code = Karađorđev park
        (7777, False), # int stop_code (nonexistent)
        (20148, True), # int stop_id = Karađorđev park
        (88888, False), # int stop_id (nonexistent)
        ("1111", True), # str stop_code = Blok 70
        ("8888", False), # str stop_code (nonexistent)
        ("21111", True), # str stop_id = Blok 70
        ("99999", False), # str stop_id (nonexistent)
    ]
)
def test_schedule_exists(name, expected):
    schedule = s.get_schedule(datetime(2026, 1, 1, 0, 0, 0), name, 86400)
    schedule_length = len(schedule)
    if expected:
        assert schedule_length > 0
        assert schedule[0].stop_name == schedule[-1].stop_name
    else:
        assert schedule_length == 0

@pytest.mark.parametrize(
    "name",
    [
        ("Trg*"), # match case
        ("blok*"), # lowercase
        ("BELI*"), # uppercase
        ("*trg"), # starts with *
        ("*kosa*"), # contains
    ]
)
def test_schedule_exists_with_asterisk(name):
    schedule = s.get_schedule(datetime(2026, 1, 1, 10, 0, 0), name, 7200)
    schedule_length = len(schedule)
    assert schedule_length > 0
    assert schedule[0].stop_name != schedule[-1].stop_name