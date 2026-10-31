#!/usr/bin/env python
"""Deterministic part of the refresh-data skill (`just refresh`).

Computes expected vs actual latest partition per raw dataset (via quant.datahealth), prints the
refresh plan as `just ingest <source> --since <date>` commands, runs them with `--execute`, and
summarises. `--fixture JSON` replaces the bucket listing for evals/tests. Unrecoverable gaps
(an ingest that fails) are reported; with `--issue` an issue is opened for each.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from quant import datahealth
from quant.datasets import DatasetDoc, dataset_docs

ROOT = Path(__file__).resolve().parents[3]
LOOKBACK_DAYS = 400


def from_fixture(path: Path, today: dt.date) -> list[datahealth.Health]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for d in spec["datasets"]:
        doc = DatasetDoc(
            name=d["name"],
            path=Path(f"catalog/datasets/{d['name']}.md"),
            owner=d.get("owner", "?"),
            source=d["source"],
            cadence=d.get("cadence", "daily"),
            lag_days=int(d.get("lag_days", 1)),
        )
        keys = [{"Key": k, "Size": 0} for k in d.get("keys", [])]
        out.append(datahealth.assess(doc, keys, today, probe=False))
    return out


def plan(
    rows: list[datahealth.Health], today: dt.date
) -> list[tuple[datahealth.Health, list[str]]]:
    cmds = []
    for r in rows:
        if r.status == "ok":
            continue
        since = r.latest_partition or (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
        cmds.append((r, ["just", "ingest", r.source, "--since", since]))
    return cmds


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just refresh")
    p.add_argument("--today", type=dt.date.fromisoformat, default=None)
    p.add_argument(
        "--fixture", type=Path, default=None, help="JSON listing instead of the bucket (evals)"
    )
    p.add_argument("--execute", action="store_true", help="run the ingest commands")
    p.add_argument(
        "--issue", action="store_true", help="open an issue for each unrecoverable gap (needs gh)"
    )
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    today = a.today or dt.date.today()
    rows = from_fixture(a.fixture, today) if a.fixture else datahealth.report(today)
    todo = plan(rows, today)
    if a.json:
        print(
            json.dumps(
                {"health": [asdict(r) for r in rows], "plan": [c for _, c in todo]}, indent=2
            )
        )
    else:
        print(datahealth.format_table(rows))
        print()
        if not todo:
            print("refresh: nothing to do")
        for r, cmd in todo:
            print(f"refresh: {r.dataset} is {r.status} -> {' '.join(cmd)}")
    failures = []
    if a.execute:
        for r, cmd in todo:
            res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                failures.append((r, (res.stderr.strip().splitlines() or ["?"])[-1]))
                print(f"refresh: FAILED {r.dataset}: {failures[-1][1]}", file=sys.stderr)
            else:
                print(f"refresh: ingested {r.dataset}")
        if a.issue:
            for r, err in failures:
                body = f"`{' '.join(plan([r], today)[0][1])}` failed:\n\n```\n{err}\n```\n\nOwner @{r.owner}. Opened by the refresh-data skill."
                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "create",
                        "--title",
                        f"refresh-data: {r.dataset} unrecoverable gap",
                        "--body",
                        body,
                        "--label",
                        "data-health",
                    ],
                    check=False,
                )
    docs = {d.name for d in dataset_docs()} if not a.fixture else set()
    if docs:
        print(
            f"refresh: {len(rows)} dataset(s) checked, {len(todo)} to refresh, {len(failures)} failed",
            file=sys.stderr,
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
