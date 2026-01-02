import argparse
import dateparser
from datetime import datetime
import re

import public_transit.message as message
import public_transit.project as project


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
    weekday_columns = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    column = weekday_columns[dt.weekday()]

    root_dir = project.get_root_dir()
    db_path = project.get_db_path(root_dir)
    with project.connect_db(db_path) as conn:
        rows = conn.execute(
            f'SELECT service_id FROM calendar WHERE "{column}" = 1'
        ).fetchall()
    return [service_id for (service_id,) in rows]

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

    message.write(f"Date and time: {dt}", verbosity)

    service_ids = detect_service_type(dt)
    service_id_names = {
        "N": "Sunday",
        "S": "Saturday",
        "RD": "work days",
    }

    if not service_ids:
        message.write("No matching service_id found", verbosity, message.QUIET)
        return 1
    message.write(f"service type: {service_ids[0]} ({service_id_names.get(service_ids[0], 'Unknown')})", verbosity)
    if verbosity >= message.VERBOSE and len(service_ids) > 1:
        message.write(f"all service_id: {service_ids}", verbosity, message.VERBOSE)

    return 0