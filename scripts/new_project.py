#!/usr/bin/env python
"""`just project SLUG`: create research/<slug>/ with a README from the project template.

A project is a folder (ADR-0004): research/<slug>/README.md (frontmatter type project, id equals
the folder name) and research/<slug>/experiments/ where `just experiment SLUG --project <slug>`
puts experiments. Projects are isolated units; they meet only through datasets, the dashboard
and knowledge/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
TEMPLATE = ROOT / "knowledge" / "templates" / "project.md"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def readme_text(slug: str, title: str, owner: str, date: str, goal: str) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->\n*", "", text, flags=re.S)
    return (
        text.replace("<project-slug>", slug)
        .replace("<project in one line>", title)
        .replace("YYYY-MM-DD", date)
        .replace("[<handle>]", f"[{owner}]")
        .replace("<handle>", owner)
        .replace("<what question this project answers, and what decision it informs>", goal)
    )


def projects() -> list[str]:
    if not RESEARCH.exists():
        return []
    return sorted(p.name for p in RESEARCH.iterdir() if (p / "README.md").exists())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just project")
    p.add_argument("slug", help="short-kebab-case; becomes research/<slug>/")
    p.add_argument("--title", default=None, help="one line (default: the slug)")
    p.add_argument("--goal", default="TODO: the question this project answers")
    p.add_argument("--owner", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--dry-run", action="store_true", help="print files instead of writing")
    a = p.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", a.slug) or a.slug == "experiments":
        print("slug must be short-kebab-case (and not 'experiments')", file=sys.stderr)
        return 2
    owner = a.owner or default_owner()
    date = a.date or dt.date.today().isoformat()
    files = {
        f"research/{a.slug}/README.md": readme_text(a.slug, a.title or a.slug, owner, date, a.goal),
        f"research/{a.slug}/experiments/.gitkeep": "",
    }
    if a.dry_run:
        for rel, text in files.items():
            print(f"--- {rel}")
            print(text, end="" if text.endswith("\n") or not text else "\n")
        return 0
    if (RESEARCH / a.slug).exists():
        print(f"research/{a.slug} exists; projects are never renamed", file=sys.stderr)
        return 1
    for rel, text in files.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(rel)
    print(f"next: fill the README, then `just experiment <slug> --project {a.slug}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
