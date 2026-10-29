"""Signals page (placeholder): lists research/signals/ modules with their first docstring line."""

from __future__ import annotations

import ast

from pages import ROOT

SIGNALS = ROOT / "research" / "signals"


def rows() -> list[dict]:
    out = []
    for p in sorted(SIGNALS.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        try:
            doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
        except SyntaxError:
            doc = ""
        out.append(
            {
                "module": p.relative_to(ROOT).as_posix(),
                "summary": doc.splitlines()[0] if doc else "",
            }
        )
    return out


def render(mo, filters: dict):
    data = rows()
    if not data:
        return mo.md(
            "_No signals yet. Code moves here from an experiment on second use, with a test, in its own PR._"
        )
    return mo.vstack([mo.md(f"**{len(data)} module(s)**"), mo.ui.table(data, selection=None)])
