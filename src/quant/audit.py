"""Bucket audit: every key must live under raw/, curated/ or scratch/<known handle>/, and the
bucket must stay under a size cap. audit.yml runs this nightly and opens an issue on findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from quant import data

TEAM_FILE = data.REPO_ROOT / "knowledge" / "context" / "team.yaml"
RESERVED_HANDLES = ("ci",)  # scratch/ci/ is where CI runs without the ingest role land


def handles(path: Path = TEAM_FILE) -> list[str]:
    return list((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("handles", []))


def allowed(key: str, known: list[str]) -> bool:
    if key.startswith(data.RAW) or key.startswith(data.CURATED):
        return True
    return any(key.startswith(f"{data.SCRATCH}{h}/") for h in (*known, *RESERVED_HANDLES))


def audit(
    *,
    max_gb: float = 8.0,
    client: Any = None,
    cfg: data.Settings | None = None,
    known: list[str] | None = None,
) -> dict[str, Any]:
    known = known if known is not None else handles()
    objects = data.list_keys("", client=client, cfg=cfg)
    total = sum(int(o.get("Size", 0)) for o in objects)
    bad = sorted(o["Key"] for o in objects if not allowed(o["Key"], known))
    by_prefix: dict[str, int] = {}
    for o in objects:
        top = "/".join(o["Key"].split("/")[: 2 if o["Key"].startswith(data.SCRATCH) else 1]) + "/"
        by_prefix[top] = by_prefix.get(top, 0) + int(o.get("Size", 0))
    return {
        "objects": len(objects),
        "total_bytes": total,
        "total_gb": round(total / 1e9, 3),
        "max_gb": max_gb,
        "over_cap": total > max_gb * 1e9,
        "stray_keys": bad,
        "by_prefix_bytes": dict(sorted(by_prefix.items())),
        "ok": not bad and total <= max_gb * 1e9,
    }


def open_issue(result: dict[str, Any], repo: str | None = None) -> None:
    title = "bucket audit: findings"
    lines = [f"Total size {result['total_gb']} GB (cap {result['max_gb']} GB).", ""]
    if result["over_cap"]:
        lines.append("- **over the size cap**")
    for k in result["stray_keys"][:50]:
        lines.append(f"- stray key outside raw/, curated/, scratch/<handle>/: `{k}`")
    body = "\n".join(lines) + "\n\nProduced by audit.yml (`just audit`)."
    repo_args = ["--repo", repo] if repo else []
    subprocess.run(
        ["gh", "issue", "create", *repo_args, "--title", title, "--body", body, "--label", "infra"],
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just audit")
    p.add_argument("--max-gb", type=float, default=8.0)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--issue", action="store_true", help="open a GitHub issue when there are findings"
    )
    a = p.parse_args(argv)
    result = audit(max_gb=a.max_gb)
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"objects={result['objects']} total={result['total_gb']} GB (cap {a.max_gb} GB)")
        for k, v in result["by_prefix_bytes"].items():
            print(f"  {k:<32} {v / 1e6:10.2f} MB")
        for k in result["stray_keys"]:
            print(f"  STRAY {k}")
    if not result["ok"]:
        if a.issue:
            open_issue(result)
        print("audit: findings", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
