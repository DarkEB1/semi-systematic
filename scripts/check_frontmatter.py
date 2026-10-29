#!/usr/bin/env python
"""Validate frontmatter and body rules of every knowledge/**/*.md and catalog/datasets/*.md.

Exit non-zero on: a missing required key, id/filename mismatch, unknown type, unknown tag,
an owner not in knowledge/context/team.yaml, ``private`` on a note, a non-ISO date, a body
without exactly one ``#`` title, or a meeting Decisions line that neither links an ADR nor ends
with ``(minor)``. Templates (knowledge/templates/) and INDEX.md are skipped.

Usage: python scripts/check_frontmatter.py [paths...]
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("id", "type", "title", "date", "authors", "owner")
OPTIONAL = ("status", "tags", "datasets", "related", "private")
TYPES = {"context", "decision", "meeting", "note", "research-log", "agent-log", "dataset"}
STATUSES = {
    "draft",
    "active",
    "final",
    "superseded",
    "accepted",
    "proposed",
    "deprecated",
    "done",
    "open",
}
TAGS_FILE = ROOT / "knowledge" / "context" / "tags.md"
TEAM_FILE = ROOT / "knowledge" / "context" / "team.yaml"
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
ADR_LINK_RE = re.compile(r"\]\((?:\.\./)*(?:decisions/)?ADR-\d{4}[^)]*\)")


def load_tags(path: Path = TAGS_FILE) -> dict[str, str]:
    """One tag per line: ``- <tag>: <definition>`` anywhere in tags.md."""
    tags: dict[str, str] = {}
    if not path.exists():
        return tags
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s+`?([a-z0-9][a-z0-9-]*)`?\s*:\s+(.+?)\s*$", line)
        if m:
            tags[m.group(1)] = m.group(2)
    return tags


def load_handles(path: Path = TEAM_FILE) -> list[str]:
    if not path.exists():
        return []
    return list((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("handles", []))


def split(md: str) -> tuple[dict | None, str]:
    m = FM_RE.match(md)
    if not m:
        return None, md
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, md
    return (fm if isinstance(fm, dict) else None), m.group(2)


def check_file(path: Path, tags: dict[str, str], handles: list[str]) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    errs: list[str] = []
    fm, body = split(path.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{rel}: no YAML frontmatter"]
    for k in REQUIRED:
        if k not in fm or fm[k] in (None, "", []):
            errs.append(f"{rel}: missing required key {k!r}")
    unknown = set(fm) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        errs.append(f"{rel}: unknown frontmatter keys {sorted(unknown)}")
    if fm.get("id") != path.stem:
        errs.append(f"{rel}: id {fm.get('id')!r} must equal filename stem {path.stem!r}")
    typ = fm.get("type")
    if typ not in TYPES:
        errs.append(f"{rel}: unknown type {typ!r} (one of {sorted(TYPES)})")
    date = fm.get("date")
    if not isinstance(date, dt.date):
        try:
            dt.date.fromisoformat(str(date))
        except ValueError:
            errs.append(f"{rel}: date {date!r} is not ISO YYYY-MM-DD")
    for t in fm.get("tags") or []:
        if t not in tags:
            errs.append(
                f"{rel}: unknown tag {t!r}; add it to knowledge/context/tags.md in the same PR"
            )
    if handles and fm.get("owner") not in handles:
        errs.append(
            f"{rel}: owner {fm.get('owner')!r} not in knowledge/context/team.yaml handles {handles}"
        )
    authors = fm.get("authors")
    if authors is not None and not isinstance(authors, list):
        errs.append(f"{rel}: authors must be a list")
    if typ == "note" and "private" in fm:
        errs.append(f"{rel}: notes may not set 'private' (the note template has no such key)")
    if "status" in fm and fm["status"] not in STATUSES:
        errs.append(f"{rel}: status {fm['status']!r} not in {sorted(STATUSES)}")
    # body rules
    h1 = [ln for ln in body.splitlines() if re.match(r"^# ", ln)]
    if len(h1) != 1:
        errs.append(f"{rel}: body must have exactly one '# ' title (found {len(h1)})")
    if typ == "meeting":
        errs.extend(check_meeting_decisions(rel, body))
    return errs


def check_meeting_decisions(rel: str, body: str) -> list[str]:
    m = re.search(r"^## Decisions\s*$(.*?)(?=^## |\Z)", body, flags=re.M | re.S)
    if not m:
        return [f"{rel}: meeting has no '## Decisions' section"]
    errs = []
    for ln in m.group(1).splitlines():
        s = ln.strip()
        if not s.startswith("-"):
            continue
        if s.lower().endswith("(minor)") or ADR_LINK_RE.search(s):
            continue
        if re.fullmatch(r"-\s*(none|no decisions)\.?", s, flags=re.I):
            continue
        errs.append(f"{rel}: decision line must link an ADR or end with (minor): {s[:80]!r}")
    return errs


def target_files(args: list[str]) -> list[Path]:
    if args:
        return [Path(a).resolve() for a in args if a.endswith(".md")]
    files = list((ROOT / "knowledge").rglob("*.md")) + list(
        (ROOT / "catalog" / "datasets").glob("*.md")
    )
    skip = {ROOT / "knowledge" / "INDEX.md"}
    return [
        f
        for f in sorted(files)
        if f not in skip
        and "templates" not in f.relative_to(ROOT).parts
        and ".obsidian" not in f.parts
    ]


def main(argv: list[str]) -> int:
    tags, handles = load_tags(), load_handles()
    errors: list[str] = []
    files = target_files(argv)
    for f in files:
        if f.exists():
            errors.extend(check_file(f, tags, handles))
    for e in errors:
        print(e)
    print(f"frontmatter: {len(files)} file(s) checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
