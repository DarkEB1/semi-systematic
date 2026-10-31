#!/usr/bin/env python
"""Every environment variable a recipe reads must be listed in .env.example.

Scans the justfile, scripts/, src/, tools/, dashboards/, .claude/skills/ and .github/workflows/
for reads (``os.environ[...]``, ``os.getenv(...)``, ``$VAR``/``${VAR}`` in shell, and ``env:``
keys in workflows) and compares against the names declared in .env.example."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
SCAN_DIRS = [
    "scripts",
    "src",
    "tools",
    "dashboards",
    ".claude/skills",
    ".github/workflows",
    "research",
]
SCAN_FILES = ["justfile"]
CODE_EXT = {".py", ".sh", ".bash", ".yml", ".yaml", ""}

PY_RE = re.compile(
    r"(?:os\.environ(?:\.get)?|environ(?:\.get)?|os\.getenv|getenv)\s*[\[(]\s*[\"']([A-Z][A-Z0-9_]+)[\"']"
)
SH_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})(?:[:}\-?]|\b)")
WF_ENV_RE = re.compile(r"^\s+([A-Z][A-Z0-9_]{2,}):\s", re.M)
WF_SECRET_RE = re.compile(r"secrets\.([A-Z][A-Z0-9_]+)")

ALLOW_PREFIX = (
    "GITHUB_",
    "RUNNER_",
    "ACTIONS_",
    "INPUT_",
    "UV_",
    "PYTHON",
    "RCLONE_CONFIG_",
    "LC_",
    "PIP_",
    "PYTEST_",
    "PRE_COMMIT",
    "DOCKER",
    "MSYS",
    "AWS_",
    "MARIMO_",
    "HATCH_",
)
ALLOW = {
    "PATH",
    "HOME",
    "PWD",
    "TMPDIR",
    "TMP",
    "TEMP",
    "CI",
    "DEBIAN_FRONTEND",
    "LANG",
    "TZ",
    "SHELL",
    "USER",
    "HOSTNAME",
    "TERM",
    "VIRTUAL_ENV",
    "NO_COLOR",
    "FORCE_COLOR",
    "EDITOR",
    "PAGER",
    "SOURCE_DATE_EPOCH",
    "GH_REPO",
    "GH_HOST",
    "GITHUB_TOKEN",
    "DISPLAY",
    "COLUMNS",
    "REMOTE_CONTAINERS",
}
# GitHub secret names are mapped to env names inside the workflow; they are not env reads.
SECRET_NAMES_OK = {
    "R2_INGEST_KEY",
    "R2_INGEST_SECRET",
    "R2_ACCOUNT_ID",
    "VENDOR_API_KEY",
    "B2_KEY_ID",
    "B2_APPLICATION_KEY",
    "B2_BUCKET",
}


def declared() -> set[str]:
    names = set()
    for ln in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]+)=", ln)
        if m:
            names.add(m.group(1))
    return names


def files() -> list[Path]:
    out = [ROOT / f for f in SCAN_FILES if (ROOT / f).exists()]
    for d in SCAN_DIRS:
        p = ROOT / d
        if p.is_dir():
            out.extend(
                f
                for f in p.rglob("*")
                if f.is_file() and f.suffix in CODE_EXT and "__pycache__" not in f.parts
            )
    return out


def reads(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: set[str] = set()
    if path.suffix == ".py":
        found |= set(PY_RE.findall(text))
        # subprocess/env usage in shell strings inside python is rare; skip $VAR in .py
    elif path.suffix in {".yml", ".yaml"}:
        found |= set(WF_ENV_RE.findall(text))
        found |= set(SH_RE.findall(text))
    else:
        found |= set(SH_RE.findall(text))
    return found


def is_allowed(name: str) -> bool:
    # *_VERSION are tool pins declared inside a workflow or the Dockerfile, not configuration
    return name in ALLOW or name.startswith(ALLOW_PREFIX) or name.endswith("_VERSION")


def main() -> int:
    known = declared()
    problems: list[str] = []
    scanned = 0
    for f in files():
        scanned += 1
        for name in sorted(reads(f)):
            if name in known or is_allowed(name) or name in SECRET_NAMES_OK:
                continue
            problems.append(
                f"{f.relative_to(ROOT).as_posix()}: reads {name} which is not listed in .env.example"
            )
    for p in problems:
        print(p)
    print(
        f"env audit: {scanned} file(s) scanned, {len(known)} variable(s) declared, {len(problems)} undeclared read(s)"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
