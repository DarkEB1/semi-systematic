"""Agent channel hooks (ADR-0009): pinned issue #2 is where teammates' agents talk to each other.

``inbox`` (SessionStart) prints the open messages for this GitHub user so the session proposes to
resolve them before anything else. ``guard`` (PreToolUse on Edit/Write) blocks an edit to a file
another handle owns until a comment in #2 by this user tags ``@owner`` and names the path.

Stdlib only (runs on the host python). If gh is missing, logged out or offline, nothing is blocked.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ISSUE = 2
OWNER_RE = re.compile(r"^owner:\s*(\S+)\s*$", re.M)
TO_RE = re.compile(r"^to:\s*(.+)$", re.M | re.I)


def gh(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def login(cwd: Path) -> str | None:
    out = gh(["api", "user", "--jq", ".login"], cwd)
    return out.strip() or None if out else None


def comments(cwd: Path) -> list[dict] | None:
    out = gh(["issue", "view", str(ISSUE), "--json", "comments"], cwd)
    return json.loads(out)["comments"] if out else None


def author(comment: dict) -> str:
    return ((comment.get("author") or {}).get("login") or "").lower()


def tags(body: str, handle: str) -> bool:
    return re.search(rf"@{re.escape(handle)}\b", body, re.I) is not None


def addressed_to(body: str, handle: str) -> bool:
    to = TO_RE.search(body)
    names = re.split(r"[\s,|@]+", to.group(1).lower()) if to else []
    return tags(body, handle) or handle.lower() in names or "all" in names


def open_messages(all_comments: list[dict], me: str) -> list[dict]:
    """Comments by others addressed to ``me`` that no later ``done:`` comment links to."""
    done = [
        c["body"] for c in all_comments if c.get("body", "").lstrip().lower().startswith("done:")
    ]
    return [
        c
        for c in all_comments
        if author(c) != me.lower()
        and addressed_to(c.get("body", ""), me)
        and not any(c["url"].rsplit("#", 1)[-1] in d for d in done)
    ]


def inbox(cwd: Path) -> int:
    me, found = login(cwd), comments(cwd)
    if me is None or found is None:
        print(
            f"Agent channel (issue #{ISSUE}, ADR-0009): could not read it (gh missing, logged out or "
            f"offline). Read it with `gh issue view {ISSUE} --comments` before starting other work."
        )
        return 0
    pending = open_messages(found, me)
    if not pending:
        print(f"Agent channel (issue #{ISSUE}): no open messages for @{me}.")
        return 0
    print(f"Agent channel (issue #{ISSUE}, ADR-0009): {len(pending)} open message(s) for @{me}.")
    for c in pending:
        summary = " ".join(c.get("body", "").split())[:300]
        print(f"- {c['url']} from @{author(c)} ({c.get('createdAt', '')[:10]}): {summary}")
    print(
        "Before doing anything else, show these to the user and propose how to resolve each one. "
        f"Answer in issue #{ISSUE}; close a request with a comment that starts `done:` and links it."
    )
    return 0


def frontmatter_owner(path: Path) -> str | None:
    if path.suffix != ".md" or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    match = OWNER_RE.search(text.split("---", 2)[1] if text.count("---") >= 2 else "")
    return match.group(1) if match else None


def owner_of(path: Path, root: Path) -> tuple[str, Path] | None:
    """The owning handle and the owned unit: the file's own ``owner:``, else the nearest README's."""
    owner = frontmatter_owner(path)
    if owner:
        return owner, path
    for parent in path.parents:
        if parent == root or root not in parent.parents:
            return None
        owner = frontmatter_owner(parent / "README.md")
        if owner:
            return owner, parent
    return None


def guard(payload: dict, cwd: Path) -> int:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    path = Path(raw) if Path(raw).is_absolute() else cwd / raw
    path = path.resolve()
    if cwd not in path.parents:
        return 0
    owned = owner_of(path, cwd)
    if owned is None:
        return 0
    owner, unit = owned
    me = login(cwd)
    if me is None or me.lower() == owner.lower():
        return 0
    rel = unit.relative_to(cwd).as_posix()
    for c in comments(cwd) or []:
        if author(c) == me.lower() and tags(c.get("body", ""), owner) and rel in c.get("body", ""):
            return 0
    print(
        f"blocked by scripts/hooks/agent_channel.py: {rel} is owned by @{owner}. Post in issue "
        f"#{ISSUE} first (`gh issue comment {ISSUE} --body-file <file>`, format in the issue body) "
        f"tagging @{owner} and naming {rel}, with what you propose to change and why; then retry.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str]) -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    cwd = Path(payload.get("cwd") or ".").resolve()
    mode = argv[0] if argv else ""
    if mode == "inbox":
        return inbox(cwd)
    if mode == "guard":
        return guard(payload, cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
