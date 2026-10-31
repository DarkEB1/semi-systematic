#!/usr/bin/env python
"""Deterministic part of the meeting-notes skill (`just meeting DATE TITLE`).

Turns pasted bullets into a meeting file in template shape, applies the ADR test to each
`decision:` line (an ADR draft for those that pass, `(minor)` for the rest), checkboxes `action:`
lines with owner and date, and links related files found in knowledge/INDEX.md. The transcript is
never stored; pass `--recording URL`. Input lines:

    agenda: <item>
    decision: <text>            -> ADR test
    action: <text> @handle 2026-11-30
    <anything else>             -> Notes
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
MEETINGS = ROOT / "knowledge" / "meetings"
DECISIONS = ROOT / "knowledge" / "decisions"
INDEX_MD = ROOT / "knowledge" / "INDEX.md"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"

# The ADR test: a decision becomes an ADR when it changes a convention, a dependency, a data
# source, a method others will reuse, or costs money.
ADR_SIGNALS = {
    "convention": [
        "convention",
        "naming",
        "format",
        "schema",
        "template",
        "rule",
        "policy",
        "standard",
        "always",
        "never",
    ],
    "dependency": [
        "dependency",
        "library",
        "package",
        "upgrade",
        "pin",
        "switch to",
        "replace",
        "adopt",
        "migrate",
        "tool",
    ],
    "data source": [
        "source",
        "vendor",
        "feed",
        "dataset",
        "api",
        "endpoint",
        "bucket",
        "data from",
    ],
    "reusable method": [
        "method",
        "model",
        "signal",
        "backtest",
        "metric",
        "approach",
        "framework",
        "all experiments",
        "every experiment",
    ],
    "money": [
        "cost",
        "costs",
        "pay",
        "paid",
        "price",
        "budget",
        "subscription",
        "licence",
        "license",
        "$",
        "usd",
        "eur",
        "fee",
    ],
}
STOP = {
    "the",
    "and",
    "with",
    "from",
    "that",
    "this",
    "into",
    "about",
    "over",
    "under",
    "meeting",
    "notes",
    "weekly",
    "sync",
}


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40].rstrip("-") or "meeting"


def adr_test(text: str) -> list[str]:
    t = text.lower()
    return [why for why, words in ADR_SIGNALS.items() if any(w in t for w in words)]


def next_adr_number(start: int | None = None) -> int:
    if start:
        return start
    nums = [
        int(m.group(1))
        for p in DECISIONS.glob("ADR-*.md")
        if (m := re.match(r"ADR-(\d{4})", p.name))
    ]
    return (max(nums) + 1) if nums else 1


def parse(lines: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"agenda": [], "decision": [], "action": [], "notes": []}
    for raw in lines:
        s = raw.strip().lstrip("-*•").strip()
        if not s:
            continue
        m = re.match(r"^(agenda|decision|action)\s*:\s*(.+)$", s, flags=re.I)
        if m:
            out[m.group(1).lower()].append(m.group(2).strip())
        else:
            out["notes"].append(s)
    return out


def related(title: str, notes: list[str], limit: int = 3) -> list[tuple[str, str]]:
    """(id, relative link) of INDEX.md entries sharing words with the title/notes."""
    if not INDEX_MD.exists():
        return []
    words = {
        w
        for w in re.findall(r"[a-z]{5,}", (title + " " + " ".join(notes)).lower())
        if w not in STOP
    }
    hits: list[tuple[int, str, str]] = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md)\)", INDEX_MD.read_text(encoding="utf-8")):
        t, link = m.group(1), m.group(2)
        score = len(words & set(re.findall(r"[a-z]{5,}", t.lower())))
        if score:
            hits.append((score, Path(link).stem, link))
    seen, out = set(), []
    for _score, stem, link in sorted(hits, key=lambda h: (-h[0], h[1])):
        if stem not in seen:
            seen.add(stem)
            out.append((stem, link))
        if len(out) >= limit:
            break
    return out


def action_line(text: str, date: str) -> str:
    owner = re.search(r"@([A-Za-z0-9-]+)", text)
    due = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    body = re.sub(r"@[A-Za-z0-9-]+|\d{4}-\d{2}-\d{2}", "", text).strip(" ,;:")
    o = f"@{owner.group(1)}" if owner else "@TODO-owner"
    d = due.group(1) if due else "TODO-date"
    return f"- [ ] {body} ({o}, {d})"


def build(
    date: str,
    title: str,
    owner: str,
    parsed: dict[str, list[str]],
    recording: str,
    attendees: list[str],
    next_adr: int,
    with_related: bool,
) -> dict[str, str]:
    mid = f"{date}-{slugify(title)}"
    adrs: dict[str, str] = {}
    decision_lines = []
    n = next_adr
    for d in parsed["decision"]:
        reasons = adr_test(d)
        if reasons:
            adr_id = f"ADR-{n:04d}-{slugify(d)}"
            adrs[f"knowledge/decisions/{adr_id}.md"] = adr_text(
                adr_id, n, d, date, owner, reasons, mid
            )
            decision_lines.append(
                f"- {d} ([{adr_id.split('-', 2)[0]}-{n:04d}](../decisions/{adr_id}.md))"
            )
            n += 1
        else:
            decision_lines.append(f"- {d} (minor)")
    rel = related(title, parsed["notes"]) if with_related else []
    related_ids = [r[0] for r in rel] + [Path(k).stem for k in adrs]
    notes = "\n".join(f"- {x}" for x in parsed["notes"]) or "- (none)"
    agenda = (
        "\n".join(f"{i}. {x}" for i, x in enumerate(parsed["agenda"], 1)) or "1. (none recorded)"
    )
    actions = "\n".join(action_line(x, date) for x in parsed["action"]) or "- [ ] (none)"
    rel_lines = "\n".join(f"- [{stem}]({link})" for stem, link in rel)
    meeting = f"""---
id: {mid}
type: meeting
title: "Meeting: {title}"
date: {date}
authors: [{owner}]
owner: {owner}
status: draft
tags: []
related: [{", ".join(related_ids)}]
---

# Meeting: {title}

Recording: {recording or "none"}

## Attendees

{chr(10).join(f"- @{h}" for h in attendees) or f"- @{owner}"}

## Agenda

{agenda}

## Notes

{notes}

## Decisions

{chr(10).join(decision_lines) or "- none"}

## Actions

{actions}
"""
    if rel_lines:
        meeting += f"\n## Related\n\n{rel_lines}\n"
    return {f"knowledge/meetings/{mid}.md": meeting, **adrs}


def adr_text(
    adr_id: str, n: int, decision: str, date: str, owner: str, reasons: list[str], meeting_id: str
) -> str:
    return f"""---
id: {adr_id}
type: decision
title: "ADR-{n:04d}: {decision[:90]}"
date: {date}
authors: [{owner}]
owner: {owner}
status: proposed
tags: []
related: [{meeting_id}]
---

# ADR-{n:04d}: {decision[:90]}

Drafted by the meeting-notes skill from [{meeting_id}](../meetings/{meeting_id}.md). It passed the
ADR test because it changes: {", ".join(reasons)}. Edit, then set `status: accepted`.

## Context

TODO: what forced the decision.

## Decision

{decision}

## Consequences

TODO.

## Alternatives considered

- TODO
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just meeting")
    p.add_argument("date")
    p.add_argument("title")
    p.add_argument("--input", default="-", help="file with bullets, or - for stdin")
    p.add_argument("--owner", default=None)
    p.add_argument("--recording", default="")
    p.add_argument("--attendees", default="", help="comma-separated handles")
    p.add_argument("--next-adr", type=int, default=None, help="force the first ADR number (evals)")
    p.add_argument("--no-related", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    dt.date.fromisoformat(a.date)
    text = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8")
    parsed = parse(text.splitlines())
    owner = a.owner or default_owner()
    attendees = [h.strip().lstrip("@") for h in a.attendees.split(",") if h.strip()]
    files = build(
        a.date,
        a.title,
        owner,
        parsed,
        a.recording,
        attendees,
        next_adr_number(a.next_adr),
        not a.no_related,
    )
    for rel, body in files.items():
        if a.dry_run:
            print(f"--- {rel}")
            print(body, end="")
            continue
        path = ROOT / rel
        if path.exists():
            print(f"exists, not overwritten: {rel}", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
