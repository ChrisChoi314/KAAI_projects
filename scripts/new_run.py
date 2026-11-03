#!/usr/bin/env python3
"""Create an independent run by copying inputs, never generated output."""

import argparse
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[1]


def run_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise argparse.ArgumentTypeError("Use letters, digits, hyphens, or underscores.")
    return value


def create_run(template, destination):
    inputs = sorted(template.glob("*.in"))
    settings = sorted((template / "src").glob("*.local"))
    required = [template / n for n in ("start.in", "run.in")]
    required += [template / "src" / n for n in ("Makefile.local", "cparam.local")]
    if not all(p.is_file() for p in required):
        raise ValueError(f"Template is missing required input/settings files: {template}")
    # Refuse to overwrite an existing run, even an empty directory.
    destination.mkdir()
    (destination / "src").mkdir()
    (destination / "data").mkdir()
    for path in inputs:
        shutil.copy2(path, destination / path.name)
    for path in settings:
        shutil.copy2(path, destination / "src" / path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", type=run_name, help="New folder name under runs/")
    parser.add_argument("--from", dest="template", type=run_name, default="jeans-x",
                        help="Existing run to copy (default: jeans-x)")
    args = parser.parse_args()
    destination = REPO / "runs" / args.name
    try:
        create_run(REPO / "runs" / args.template, destination)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot create run: {error}\n")
    print(f"Created {destination}")
    print("Edit its .in and src/*.local files, then follow the README to build and run.")


if __name__ == "__main__":
    main()
