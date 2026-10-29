#!/usr/bin/env python
"""Deterministic part of the promote-dataset skill (`just promote-request NAME SCRATCH_KEY`).

Validates a Parquet (in scratch/, or a local file with --local-parquet) against the dataset README's
Schema table, writes the README from the template when it is missing (--write-readme), creates
promote/requests/<date>-<name>.yml and prints the PR checklist. promote.yml does the copy on merge.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from quant import data  # noqa: E402

TEAM = ROOT / "knowledge" / "context" / "team.yaml"
REQUESTS = ROOT / "promote" / "requests"
TYPE_NAMES = {
    pa.string(): "string",
    pa.date32(): "date",
    pa.float64(): "float64",
    pa.float32(): "float32",
    pa.int64(): "int64",
    pa.int32(): "int32",
    pa.bool_(): "bool",
    pa.timestamp("us"): "timestamp",
    pa.timestamp("us", tz="UTC"): "timestamp[us, UTC]",
}


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def readme_from_schema(name: str, schema: pa.Schema, owner: str, date: str) -> str:
    rows = "\n".join(
        f"| {f.name} | {TYPE_NAMES.get(f.type, str(f.type))} | TODO | TODO |" for f in schema
    )
    return f"""---
id: {name}
type: dataset
title: {name}
date: {date}
authors: [{owner}]
owner: {owner}
status: active
tags: [data]
datasets: [{name}]
---

# {name}

TODO: one paragraph. Curated snapshots live under `curated/{name}/snapshot=YYYY-MM-DD/`; view `{name}`.

## Source

- source: TODO (the experiment or ingest module that produced it)
- url: n/a
- licence: TODO

## Cadence

- cadence: snapshot
- lag_days: 30

## Schema

| column | type | units | description |
|---|---|---|---|
{rows}

## Known gaps

- TODO

## Owner

{owner}.
"""


def request_text(
    name: str, scratch_key: str, snapshot: str, owner: str, date: str, notes: str
) -> str:
    return yaml.safe_dump(
        {
            "name": name,
            "scratch_key": scratch_key,
            "snapshot": snapshot,
            "requested_by": owner,
            "date": date,
            "notes": notes,
        },
        sort_keys=False,
    )


def checklist(name: str, snapshot: str, req_rel: str) -> str:
    return f"""PR checklist (paste into the PR body):

- [ ] `{req_rel}` requests `{name}` at snapshot `{snapshot}`
- [ ] the Parquet matched `catalog/datasets/{name}.md` (schema contract) locally
- [ ] the README's Source, Cadence, Known gaps and Owner are filled, not TODO
- [ ] `just check` and `just test` are green
- [ ] no existing snapshot with the same date (promote never overwrites)
- [ ] `promote/**` and `catalog/**` are under CODEOWNERS: this PR waits for the data-layer owner
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just promote-request")
    p.add_argument("name")
    p.add_argument("scratch_key", help="scratch/<handle>/.../file.parquet")
    p.add_argument("--snapshot", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--owner", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--notes", default="")
    p.add_argument(
        "--local-parquet",
        type=Path,
        default=None,
        help="validate this file instead of reading the bucket",
    )
    p.add_argument(
        "--write-readme",
        action="store_true",
        help="create catalog/datasets/<name>.md from the Parquet schema if missing",
    )
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    owner = a.owner or default_owner()
    date = a.date or dt.date.today().isoformat()
    snapshot = a.snapshot or date
    if not a.scratch_key.startswith(data.SCRATCH):
        print(f"scratch_key must start with {data.SCRATCH!r}", file=sys.stderr)
        return 2

    table = pq.read_table(a.local_parquet) if a.local_parquet else data.read_parquet(a.scratch_key)
    readme = data.DATASET_DOCS / f"{a.name}.md"
    files: dict[str, str] = {}
    if not readme.exists():
        if not a.write_readme:
            print(
                f"no README at catalog/datasets/{a.name}.md; rerun with --write-readme, then fill it in",
                file=sys.stderr,
            )
            return 1
        files[f"catalog/datasets/{a.name}.md"] = readme_from_schema(
            a.name, table.schema, owner, date
        )
        if not a.dry_run:
            readme.write_text(files[f"catalog/datasets/{a.name}.md"], encoding="utf-8")
    try:
        data.validate_schema(table, a.name) if readme.exists() else None
    except data.SchemaMismatch as e:
        print(f"schema mismatch: {e}", file=sys.stderr)
        return 1
    req_rel = f"promote/requests/{date}-{a.name}.yml"
    files[req_rel] = request_text(a.name, a.scratch_key, snapshot, owner, date, a.notes)
    if a.dry_run:
        for rel, text in files.items():
            print(f"--- {rel}")
            print(text, end="")
        print(f"--- schema ok: {table.num_rows} rows, {table.num_columns} columns")
        print(checklist(a.name, snapshot, req_rel))
        return 0
    out = ROOT / req_rel
    if out.exists():
        print(f"{req_rel} exists; pick another --date or edit it", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(files[req_rel], encoding="utf-8")
    for rel in files:
        print(rel)
    print(checklist(a.name, snapshot, req_rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
