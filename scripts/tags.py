#!/usr/bin/env python
"""Print the controlled tag vocabulary (knowledge/context/tags.md). ``--names`` prints bare names."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_frontmatter import load_tags  # noqa: E402


def main(argv: list[str]) -> int:
    tags = load_tags()
    if not tags:
        print("no tags found in knowledge/context/tags.md", file=sys.stderr)
        return 1
    for name, definition in tags.items():
        print(name if "--names" in argv else f"{name}: {definition}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
