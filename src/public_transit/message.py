QUIET = 0
NORMAL = 1
VERBOSE = 2


class Message:
    def __init__(self, current_level: int = NORMAL) -> None:
        self.current_level = current_level

    def write(self, message: str, target_level: int = NORMAL) -> None:
        """
        Print a message with the given level of verbosity.
        """
        if self.current_level >= target_level:
            print(message)
