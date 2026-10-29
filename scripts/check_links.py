#!/usr/bin/env python
"""Relative markdown links must resolve. Scans knowledge/, catalog/, .claude/skills/, ai/,
research/, README.md and AGENTS.md. External (http, mailto) and pure anchor links are ignored."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SCAN = [
    "knowledge",
    "catalog",
    ".claude/skills",
    "ai",
    "research",
    "README.md",
    "AGENTS.md",
    "tools",
    "dashboards",
]
SKIP_PREFIX = ("http://", "https://", "mailto:", "#", "tel:")


def md_files() -> list[Path]:
    out: list[Path] = []
    for s in SCAN:
        p = ROOT / s
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(
                f
                for f in p.rglob("*.md")
                if ".obsidian" not in f.parts and "templates" not in f.relative_to(ROOT).parts
            )
    return sorted(out)


def check(path: Path) -> list[str]:
    errs = []
    text = path.read_text(encoding="utf-8", errors="replace")
    in_fence = False
    for ln in text.splitlines():
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(ln):
            if target.startswith(SKIP_PREFIX) or "<" in target or ">" in target:
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (
                (path.parent / clean).resolve()
                if not clean.startswith("/")
                else (ROOT / clean.lstrip("/")).resolve()
            )
            if not resolved.exists():
                errs.append(f"{path.relative_to(ROOT).as_posix()}: broken link {target!r}")
    return errs


def main() -> int:
    files = md_files()
    errors = [e for f in files for e in check(f)]
    for e in errors:
        print(e)
    print(f"links: {len(files)} file(s) checked, {len(errors)} broken")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
