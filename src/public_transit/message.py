QUIET = 0
NORMAL = 1
VERBOSE = 2


def write(message: str, current_level: int = NORMAL, target_level: int = NORMAL) -> None:
    """
    Print a message with the given level of verbosity.
    """
    if current_level >= target_level:
        print(message)
