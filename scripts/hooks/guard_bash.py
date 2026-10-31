"""PreToolUse hook for Bash: block the few shell actions this repo never allows.

Stdlib only (runs on the host python). Reads the hook JSON on stdin, exits 2 with the reason on
stderr to block, 0 otherwise. The list is deliberately short; everything else is Claude's call.
"""

from __future__ import annotations

import json
import re
import sys

RULES: list[tuple[str, str]] = [
    (
        r"\bgit\s+commit\b[^|;&]*\s(--no-verify|-n)\b",
        "never skip the pre-commit hooks; fix what they report",
    ),
    (
        r"\bgit\s+push\b[^|;&]*\s(--force|-f)\b(?!-with-lease)",
        "never force-push; a new commit on top is the fix",
    ),
    (
        r"\bgit\s+push\b[^|;&]*\s(origin\s+)?main\b",
        "main is protected; push a branch and open a PR",
    ),
    (
        r"\bgit\s+(mv|rm)\b[^|;&]*\sknowledge/",
        "files under knowledge/ are never renamed, moved or deleted",
    ),
    (
        r"(^|[\s;&|])(mv|rm)\s[^|;&]*\sknowledge/",
        "files under knowledge/ are never renamed, moved or deleted",
    ),
    (
        r"(^|[\s;&|])(cat|less|more|head|tail|grep|sed|awk|type|bat|strings)\b[^|;&]*\s\.env(?![\w.]*example)\b",
        "never read .env back; .env.example is the variable list",
    ),
    (
        r"\b(rclone\s+(copy|copyto|sync|move|moveto|delete|purge|deletefile)|aws\s+s3\s+(cp|sync|mv|rm)|s3cmd\s+(put|sync|del))\b[^|;&]*(:|/)(raw|curated)/",
        "raw/ and curated/ are written only by the ingest and promote workflows; write scratch/<handle>/",
    ),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    for pattern, reason in RULES:
        if re.search(pattern, command, flags=re.I | re.S):
            print(f"blocked by scripts/hooks/guard_bash.py: {reason}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
