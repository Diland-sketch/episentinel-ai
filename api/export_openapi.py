"""Export the frontend contract to a new file; never overwrite evidence."""
import argparse
import json
from pathlib import Path

from .main import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(app.openapi(), handle, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
