import argparse
import calendar
import dateparser
from datetime import datetime, timedelta
import re
import holidays
from types import SimpleNamespace
from cyrtranslit import to_latin

import public_transit.message as message
import public_transit.project as project

def fix_typos(text: str) -> str:
    """
    Fix common typos and mistakes derived from English and Russian languages
    like block → blok, аэродром → аеродром, Яково → Јаково.

    Side effect: lowercases the result.
    """
    text = text.lower()

    replacements: list[tuple[str | re.Pattern[str], str]] = [
        ("аэро", "аеро"),
        ("бульвар", "булевар"),
        ("ая площадь", "и трг"),
        ("площадь", "трг"),
        ("пл.", "трг"),
        (re.compile(r"[иы]й\b"), "и"),
        (re.compile(r"ая\b"), "а"),
        ("й", "ј"),
        ("ль", "љ"),
        ("лю", "љу"),
        ("ля", "ља"),
        ("нь", "њ"),
        ("ню", "њу"),
        ("ня", "ња"),
        ("цы", "ци"),
        ("щ", "шт"),
        ("ю", "ју"),
        ("я", "ја"),
        (re.compile(r"\bblock\b"), "blok"),
    ]

    for src, dst in replacements:
        if isinstance(src, str):
            text = text.replace(src, dst)
        else:
            text = src.sub(dst, text)

    return text

def transliterate(text: str) -> str:
    return to_latin(text, "sr")

def parse_args(argv: list[str] | None = None):
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(add_help=True)

    # Verbosity: only -q or -v can be used, not both
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress unnecessary messages")
    group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more messages")

    parser.add_argument(
        "-d",
        "--date",
        type=str,
        help="Date and time: YYYY-MM-DD or HH:MM or any other relative date like Monday or 'in 15 minutes'",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=30,
        help="Interval in minutes (default is 30)",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        help="Stop name (case-insensitive using Latin alphabet) like Kalemegdan or Savski trg or digital code like 5 or 20333",
    )

    return parser.parse_args(argv)


def parse_date(date_value: str | None):
    """
    Parse date and time.
    """
    base = datetime.now()
    date_value = date_value if date_value else "today"

    if re.fullmatch(r"\d{8}", date_value):
        date_value = f"{date_value[0:4]}-{date_value[4:6]}-{date_value[6:8]}"
    elif re.fullmatch(r"\d{12}", date_value):
        date_value = (
            f"{date_value[0:4]}-{date_value[4:6]}-{date_value[6:8]} "
            f"{date_value[8:10]}:{date_value[10:12]}"
        )
    elif re.fullmatch(r"\d{14}", date_value):
        date_value = (
            f"{date_value[0:4]}-{date_value[4:6]}-{date_value[6:8]} "
            f"{date_value[8:10]}:{date_value[10:12]}:{date_value[12:14]}"
        )

    return dateparser.parse(date_value, settings={"RELATIVE_BASE": base})


def detect_service_type(dt: datetime):
    """
    Detect service type for the given date.
    """
    column = calendar.day_name[dt.weekday()].lower()
    rs_holidays = holidays.country_holidays("RS")
    if dt.date() in rs_holidays:
        column = "sunday"

    date_key = int(dt.strftime("%Y%m%d"))

    with project.connect_db() as conn:
        base_rows = conn.execute(
            f'SELECT service_id FROM calendar WHERE "{column}" = 1'
        ).fetchall()

        service_ids = {service_id for (service_id,) in base_rows}

        exception_rows = conn.execute(
            'SELECT service_id, exception_type FROM calendar_dates WHERE "date" = ?',
            (date_key,),
        ).fetchall()

        for service_id, exception_type in exception_rows:
            if exception_type == 1:
                service_ids.add(service_id)
            elif exception_type == 2:
                service_ids.discard(service_id)

    return service_ids


def get_schedule(service_id: str, dt: datetime, stop_name: str, interval: int):
    """
    Get schedule for the given service_id, timestamp, stop name and interval.
    """

    condition = "lower(s.stop_name) = ?"
    order = "arrival_time"
    stop_key = str(stop_name).lower()

    if '*' in stop_key:
        stop_key = stop_key.replace('*', '%')
        condition = "lower(s.stop_name) LIKE ?"
        order = "s.stop_name"
    elif re.fullmatch(r"\d{5}", stop_key):
        condition = "s.stop_id = ?"
    elif re.fullmatch(r"\d{1,4}", stop_key):
        condition = "s.stop_code = ?"

    sql = f"""
        SELECT
            st.arrival_time,
            s.stop_name,
            r.route_short_name, r.route_long_name, r.route_type,
            t.direction_id, t.trip_headsign
        FROM stops s
        LEFT JOIN stop_times st ON st.stop_id = s.stop_id 
        LEFT JOIN trips t ON t.trip_id = st.trip_id
        LEFT JOIN routes r ON r.route_id = t.route_id 
        WHERE {condition}
            AND t.service_id = ?
            AND st.arrival_time BETWEEN ? AND ?
        ORDER BY {order}
    """

    def primary_service_id_for_day(day_dt: datetime) -> str:
        service_ids = detect_service_type(day_dt)
        if not service_ids:
            return service_id
        return sorted(service_ids)[0]

    results: list[SimpleNamespace] = []

    start_dt = dt
    end_dt = dt + timedelta(minutes=interval)
    base_date = start_dt.date()

    def gtfs_time_for(base: datetime, target: datetime) -> str:
        hour = target.hour
        if target.date() != base.date():
            hour += 24
        return f"{hour:02d}:{target.minute:02d}:{target.second:02d}"

    time_windows: list[tuple[str, str, str]] = []
    if end_dt.date() == base_date:
        time_windows.append((service_id, gtfs_time_for(start_dt, start_dt), gtfs_time_for(start_dt, end_dt)))
    else:
        time_windows.append((service_id, gtfs_time_for(start_dt, start_dt), gtfs_time_for(start_dt, end_dt)))
        next_service_id = primary_service_id_for_day(start_dt + timedelta(days=1))
        time_windows.append((next_service_id, "00:00:00", gtfs_time_for(end_dt, end_dt)))

    with project.connect_db() as conn:
        for window_service_id, start_time, end_time in time_windows:
            rows = conn.execute(
                sql,
                (stop_key, window_service_id, start_time, end_time),
            ).fetchall()
            results.extend(SimpleNamespace(**dict(row)) for row in rows)

    return results


def main() -> int:
    args = parse_args()
    verbosity = message.NORMAL
    if args.quiet:
        verbosity = message.QUIET
    elif args.verbose:
        verbosity = message.VERBOSE

    dt = parse_date(args.date)
    if dt is None:
        message.write(f"Invalid date: {args.date}", verbosity, message.QUIET)
        return 1

    message.write(f"Date and time: {str(dt)[:16]}", verbosity)

    service_ids = detect_service_type(dt)
    service_id_names = {
        "N": "Sunday",
        "S": "Saturday",
        "RD": "work days",
    }

    if not service_ids:
        message.write("No matching service_id found", verbosity, message.QUIET)
        return 1

    primary_service_id = sorted(service_ids)[0]
    message.write(
        f"Service type: {primary_service_id} ({service_id_names.get(primary_service_id, 'Unknown')})",
        verbosity, message.VERBOSE
    )
    if len(service_ids) > 1:
        message.write(f"All service_id: {sorted(service_ids)}", verbosity, message.VERBOSE)

    if args.name:
        name = transliterate(fix_typos(args.name))
        schedule = get_schedule(primary_service_id, dt, name, args.interval)
        types = {0: "Tm 🚋", 3: "A  🚌", 11: "Tb 🚎"}

        if not schedule:
            message.write("No schedule found", verbosity)
            return 1

        old_header_name = ''

        for row in schedule:
            header_name = getattr(row, "stop_name", "?")
            if header_name != old_header_name:
                message.write(header_name, verbosity, message.QUIET)
                old_header_name = header_name

            type_emoji = types.get(row.route_type, "Unknn")
            number = (row.route_short_name or "").ljust(5)
            message.write(f"{row.arrival_time[:5]} {type_emoji} {number} {row.trip_headsign}", verbosity, message.QUIET)
        
    return 0
