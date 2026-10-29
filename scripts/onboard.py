#!/usr/bin/env python
"""One command to check a new machine: tools, .env, handle registration, bucket access.

Prints a checklist with OK / MISSING and exits 1 if anything required is missing. Used by people
and by the "Set up with your AI assistant" block in README.md. Never prints a secret value.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("uv", "just", "rclone", "duckdb", "gitleaks", "gh", "git")
REQUIRED_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ENDPOINT",
    "R2_BUCKET",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_HANDLE",
)
RECOMMENDED_VARS = ("R2_SCRATCH_ACCESS_KEY_ID", "R2_SCRATCH_SECRET_ACCESS_KEY")

rows: list[tuple[str, str, str]] = []  # (status, item, hint)


def ok(item: str, hint: str = "") -> None:
    rows.append(("OK", item, hint))


def missing(item: str, hint: str) -> None:
    rows.append(("MISSING", item, hint))


def warn(item: str, hint: str) -> None:
    rows.append(("WARN", item, hint))


def check_tools() -> None:
    for t in TOOLS:
        if shutil.which(t):
            ok(f"tool {t}")
        else:
            missing(f"tool {t}", "open the repo in the devcontainer; tools are installed there")
    if (
        Path("/.dockerenv").exists()
        or os.getenv("REMOTE_CONTAINERS")
        or str(ROOT).startswith("/workspaces/")
    ):
        ok("running inside a container")
    else:
        warn("not inside the devcontainer", "the devcontainer is the only supported runtime")


def check_env() -> dict[str, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        missing(".env file", "cp .env.example .env and fill it from the team password manager")
        return {}
    ok(".env exists")
    values = {k: (v or "") for k, v in dotenv_values(env_path).items()}
    example = {k for k in dotenv_values(ROOT / ".env.example")}
    for k in REQUIRED_VARS:
        if values.get(k):
            ok(f"{k} set")
        else:
            missing(f"{k} set", f"copy the value named in .env.example for {k}")
    for k in RECOMMENDED_VARS:
        if values.get(k):
            ok(f"{k} set")
        else:
            warn(f"{k} empty", "needed only when you write to scratch/<handle>/")
    extra = sorted(set(values) - example)
    if extra:
        warn(
            f"undeclared variables in .env: {extra}",
            "add them to .env.example if a recipe reads them",
        )
    acct, ep = values.get("R2_ACCOUNT_ID", ""), values.get("R2_ENDPOINT", "")
    if acct and ep:
        if re.fullmatch(rf"https://{re.escape(acct)}(\.eu)?\.r2\.cloudflarestorage\.com/?", ep):
            ok("R2_ENDPOINT matches the account id")
        else:
            missing(
                "R2_ENDPOINT well-formed",
                "expected https://<account-id>.eu.r2.cloudflarestorage.com (EU bucket)",
            )
    return values


def check_handle(values: dict[str, str]) -> None:
    handle = values.get("R2_HANDLE", "")
    if not handle:
        return
    team = (
        yaml.safe_load((ROOT / "knowledge" / "context" / "team.yaml").read_text(encoding="utf-8"))
        or {}
    )
    if handle in team.get("handles", []):
        ok(f"handle {handle} in knowledge/context/team.yaml")
    else:
        missing(
            f"handle {handle} in team.yaml",
            "add it to the handles list (same PR as notes dir and CODEOWNERS)",
        )
    if (ROOT / "knowledge" / "notes" / handle).is_dir():
        ok(f"knowledge/notes/{handle}/ exists")
    else:
        missing(
            f"knowledge/notes/{handle}/",
            f"mkdir -p knowledge/notes/{handle} && touch knowledge/notes/{handle}/.gitkeep",
        )
    co = ROOT / ".github" / "CODEOWNERS"
    if co.exists() and f"@{handle}" in co.read_text(encoding="utf-8"):
        ok(f"@{handle} in CODEOWNERS")
    else:
        missing(
            f"@{handle} in CODEOWNERS",
            f"add @{handle} to the knowledge/notes/{handle}/ line in .github/CODEOWNERS",
        )


def check_bucket(values: dict[str, str]) -> None:
    if not all(values.get(k) for k in REQUIRED_VARS[:5]):
        return
    if shutil.which("rclone"):
        env = dict(os.environ)
        env.update(
            RCLONE_CONFIG_R2_TYPE="s3",
            RCLONE_CONFIG_R2_PROVIDER="Cloudflare",
            RCLONE_CONFIG_R2_ACCESS_KEY_ID=values["R2_ACCESS_KEY_ID"],
            RCLONE_CONFIG_R2_SECRET_ACCESS_KEY=values["R2_SECRET_ACCESS_KEY"],
            RCLONE_CONFIG_R2_ENDPOINT=values["R2_ENDPOINT"],
            RCLONE_CONFIG_R2_REGION="auto",
            RCLONE_CONFIG_R2_NO_CHECK_BUCKET="true",
        )
        r = subprocess.run(
            ["rclone", "lsd", f"r2:{values['R2_BUCKET']}", "--max-depth", "1"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0:
            ok("rclone can list the bucket")
        else:
            missing(
                "rclone can list the bucket",
                (r.stderr.strip().splitlines() or ["check keys and endpoint"])[-1][:120],
            )
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from quant import data

        con = data.connect(views=False)
        con.execute("SELECT 1").fetchone()
        n = con.execute(f"SELECT count(*) FROM glob('s3://{values['R2_BUCKET']}/**')").fetchone()[0]
        ok(f"duckdb httpfs secret works ({n} object(s) visible)")
    except Exception as e:  # noqa: BLE001
        missing("duckdb can reach the bucket", str(e).splitlines()[0][:120])


def main() -> int:
    check_tools()
    values = check_env()
    check_handle(values)
    check_bucket(values)
    width = max(len(i) for _, i, _ in rows)
    for status, item, hint in rows:
        print(f"[{status:<7}] {item:<{width}}  {hint}")
    bad = [r for r in rows if r[0] == "MISSING"]
    print(f"\nonboard: {len(rows) - len(bad)} ok, {len(bad)} missing")
    if not bad:
        print(
            "Next: read AGENTS.md and knowledge/context/workflow.md, then run `just check` and `just test`."
        )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
