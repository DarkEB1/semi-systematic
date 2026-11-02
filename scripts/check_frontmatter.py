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
OPTIONAL = ("status", "tags", "datasets", "related", "private", "project", "due")
TYPES = {
    "context",
    "decision",
    "meeting",
    "note",
    "research-log",
    "agent-log",
    "dataset",
    "project",
    "todo",
}
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
    "todo",
    "doing",
}
TODO_STATUSES = ("todo", "doing", "done")
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


def check_keys(rel: str, path: Path, fm: dict) -> list[str]:
    """Required and unknown keys, id equals the file name, known type."""
    errs = [
        f"{rel}: missing required key {k!r}"
        for k in REQUIRED
        if k not in fm or fm[k] in (None, "", [])
    ]
    unknown = set(fm) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        errs.append(f"{rel}: unknown frontmatter keys {sorted(unknown)}")
    expected_id = path.parent.name if path.name == "README.md" else path.stem
    if fm.get("id") != expected_id:
        errs.append(
            f"{rel}: id {fm.get('id')!r} must equal {expected_id!r} (filename stem, or the folder for a README)"
        )
    if fm.get("type") not in TYPES:
        errs.append(f"{rel}: unknown type {fm.get('type')!r} (one of {sorted(TYPES)})")
    return errs


def check_values(rel: str, fm: dict, tags: dict[str, str], handles: list[str]) -> list[str]:
    """Date, tags, owner, authors, private and status values."""
    errs: list[str] = []
    date = fm.get("date")
    if not isinstance(date, dt.date):
        try:
            dt.date.fromisoformat(str(date))
        except ValueError:
            errs.append(f"{rel}: date {date!r} is not ISO YYYY-MM-DD")
    errs += [
        f"{rel}: unknown tag {t!r}; add it to knowledge/context/tags.md in the same PR"
        for t in fm.get("tags") or []
        if t not in tags
    ]
    if handles and fm.get("owner") not in handles:
        errs.append(
            f"{rel}: owner {fm.get('owner')!r} not in knowledge/context/team.yaml handles {handles}"
        )
    authors = fm.get("authors")
    if authors is not None and not isinstance(authors, list):
        errs.append(f"{rel}: authors must be a list")
    if fm.get("type") == "note" and "private" in fm:
        errs.append(f"{rel}: notes may not set 'private' (the note template has no such key)")
    if "status" in fm and fm["status"] not in STATUSES:
        errs.append(f"{rel}: status {fm['status']!r} not in {sorted(STATUSES)}")
    return errs


def check_todo(rel: str, fm: dict) -> list[str]:
    """A todo is a card: its status is a column and its due date, if any, is ISO."""
    if fm.get("type") != "todo":
        return []
    errs = []
    if fm.get("status") not in TODO_STATUSES:
        errs.append(
            f"{rel}: a todo's status is one of {list(TODO_STATUSES)}, got {fm.get('status')!r}"
        )
    due = fm.get("due")
    if due is not None and not isinstance(due, dt.date):
        try:
            dt.date.fromisoformat(str(due))
        except ValueError:
            errs.append(f"{rel}: due {due!r} is not ISO YYYY-MM-DD")
    return errs


def check_body(rel: str, typ: object, body: str) -> list[str]:
    """One title; meetings keep their Decisions grammar."""
    h1 = [ln for ln in body.splitlines() if re.match(r"^# ", ln)]
    errs = (
        [] if len(h1) == 1 else [f"{rel}: body must have exactly one '# ' title (found {len(h1)})"]
    )
    if typ == "meeting":
        errs.extend(check_meeting_decisions(rel, body))
    return errs


def check_file(path: Path, tags: dict[str, str], handles: list[str]) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    fm, body = split(path.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{rel}: no YAML frontmatter"]
    return (
        check_keys(rel, path, fm)
        + check_values(rel, fm, tags, handles)
        + check_todo(rel, fm)
        + check_body(rel, fm.get("type"), body)
    )


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
    files = (
        list((ROOT / "knowledge").rglob("*.md"))
        + list((ROOT / "catalog" / "datasets").glob("*.md"))
        + list((ROOT / "research").glob("*/README.md"))
    )
    skip = {ROOT / "knowledge" / "INDEX.md", ROOT / "knowledge" / "AGENTS.md"}
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
