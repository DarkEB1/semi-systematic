"""Hub pages. Each module exposes ``render(mo, filters) -> element`` and a plain ``rows()`` used by
tests and headless checks. Pages read only catalog views, the chunk table or repo files; they
never compute a dataset they then cache."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def frontmatter(path: Path) -> dict:
    m = FM_RE.match(path.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return fm if isinstance(fm, dict) else {}
