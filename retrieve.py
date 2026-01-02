#!/usr/bin/env python3

from pathlib import Path
import sys

def main() -> int:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    sys.path.insert(0, str(src_dir))

    from public_transit.retrieve import main as run

    return run()


if __name__ == "__main__":
    sys.exit(main())
