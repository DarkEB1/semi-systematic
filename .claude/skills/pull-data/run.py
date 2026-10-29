#!/usr/bin/env python
"""Deterministic part of the pull-data skill (`just scaffold-source SOURCE`).

Writes, from templates: src/quant/ingest/<source>.py, catalog/datasets/<dataset>.md, the raw
catalog view, tests/test_ingest_<source>.py with a small fixture, the registry entry in
src/quant/ingest/__init__.py and the ingest.yml matrix entry. `--dry-run` prints everything
instead of writing. Existing files are never overwritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template_source.py"
DATASET_TEMPLATE = ROOT / "knowledge" / "templates" / "dataset.md"
REGISTRY = ROOT / "src" / "quant" / "ingest" / "__init__.py"
CATALOG = ROOT / "catalog" / "catalog.sql"
WORKFLOW = ROOT / ".github" / "workflows" / "ingest.yml"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"
GLOBS = {"daily": "*/*/*.parquet", "intraday": "*/*.parquet", "snapshot": "*/*.parquet"}


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def module_text(source: str, dataset: str, cadence: str, description: str) -> str:
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__SOURCE__", source)
        .replace("__DATASET__", dataset)
        .replace("__CADENCE__", cadence)
        .replace("__DESCRIPTION__", description)
    )


def readme_text(
    source: str, dataset: str, cadence: str, owner: str, date: str, description: str
) -> str:
    return f"""---
id: {dataset}
type: dataset
title: {dataset}
date: {date}
authors: [{owner}]
owner: {owner}
status: active
tags: [data]
datasets: [{dataset}]
---

# {dataset}

{description} Raw lands under `raw/{source}/{dataset}/`; curated snapshots under
`curated/{dataset}/snapshot=YYYY-MM-DD/` once promoted. Views: `{source}_{dataset}` (raw) and
`{dataset}` (curated).

## Source

- source: {source}
- url: TODO
- licence: TODO

Fetched by `src/quant/ingest/{source}.py`. TODO: what the ingest rewrites and how far back it looks.

## Cadence

- cadence: {cadence}
- lag_days: 1

TODO: calendar notes.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (UTC) | Observation date |
| symbol | string | | Universe symbol |
| value | float64 | TODO | TODO |
| source | string | | Vendor name, constant `{source}` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- TODO

## Owner

{owner}. Problems go to the data-health issue for this dataset.
"""


def view_text(source: str, dataset: str, cadence: str) -> str:
    return (
        f"\n-- raw: {dataset} from {source} ({cadence})\n"
        f"CREATE OR REPLACE VIEW {source}_{dataset} AS\n"
        f"SELECT * FROM read_parquet('s3://{{bucket}}/raw/{source}/{dataset}/{GLOBS[cadence]}', hive_partitioning = true, union_by_name = true);\n"
    )


def test_text(source: str, dataset: str) -> str:
    return f'''"""quant.ingest.{source} with the fixture in tests/fixtures (no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from quant import data
from quant.ingest import {source}

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "{source}_sample.json").read_text())
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)


def test_normalise_matches_schema():
    t = {source}.normalise(FIXTURE, ingested_at=STAMP)
    assert t.schema.equals({source}.SCHEMA)
    assert t.num_rows == len(FIXTURE)
    assert t["source"].to_pylist() == ["{source}"] * len(FIXTURE)


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr({source}, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = {source}.run(dt.date(2026, 1, 15), client=s3)
    assert keys and all(k.startswith("scratch/tester/raw/{source}/{dataset}/") for k in keys)
'''


FIXTURE_ROWS = [
    {"date": "2026-01-02", "symbol": "AAA", "value": 1.0},
    {"date": "2026-01-05", "symbol": "AAA", "value": 1.5},
]


def registry_patch(source: str) -> tuple[str, str]:
    text = REGISTRY.read_text(encoding="utf-8")
    if f"from quant.ingest import {source}" in text:
        return text, text
    new = re.sub(
        r"(from quant\.ingest import [a-z_]+\n)(?!from quant\.ingest import)",
        rf"\1from quant.ingest import {source}\n",
        text,
        count=1,
    )
    new = new.replace(
        "SOURCES: dict[str, ModuleType] = {\n",
        f"SOURCES: dict[str, ModuleType] = {{\n    {source}.SOURCE: {source},\n",
        1,
    )
    return text, new


def workflow_patch(source: str) -> tuple[str, str]:
    if not WORKFLOW.exists():
        return "", ""
    text = WORKFLOW.read_text(encoding="utf-8")
    m = re.search(r"source:\s*\[([^\]]*)\]", text)
    if not m:
        return text, text
    items = [s.strip() for s in m.group(1).split(",") if s.strip()]
    if source in items:
        return text, text
    items.append(source)
    new = text[: m.start()] + f"source: [{', '.join(items)}]" + text[m.end() :]
    return text, new


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just scaffold-source")
    p.add_argument("source", help="python identifier, e.g. fred")
    p.add_argument("--dataset", default=None, help="dataset name (default <source>_daily)")
    p.add_argument("--cadence", choices=sorted(GLOBS), default="daily")
    p.add_argument("--description", default="TODO: one line on what this source provides.")
    p.add_argument("--owner", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", a.source):
        print("source must be a lowercase python identifier", file=sys.stderr)
        return 2
    dataset = a.dataset or f"{a.source}_daily"
    owner = a.owner or default_owner()
    date = a.date or dt.date.today().isoformat()

    files = {
        f"src/quant/ingest/{a.source}.py": module_text(a.source, dataset, a.cadence, a.description),
        f"catalog/datasets/{dataset}.md": readme_text(
            a.source, dataset, a.cadence, owner, date, a.description
        ),
        f"tests/test_ingest_{a.source}.py": test_text(a.source, dataset),
        f"tests/fixtures/{a.source}_sample.json": json.dumps(FIXTURE_ROWS, indent=1) + "\n",
    }
    appends = {"catalog/catalog.sql": view_text(a.source, dataset, a.cadence)}
    patches = {
        "src/quant/ingest/__init__.py": registry_patch(a.source),
        ".github/workflows/ingest.yml": workflow_patch(a.source),
    }

    if a.dry_run:
        for rel, text in files.items():
            print(f"--- {rel}")
            print(text, end="")
        for rel, text in appends.items():
            print(f"--- append to {rel}")
            print(text, end="")
        for rel, (old, new) in patches.items():
            if old != new:
                print(f"--- patch {rel}")
                for ln in new.splitlines():
                    if ln not in old.splitlines():
                        print(f"+ {ln}")
        return 0

    for rel, text in files.items():
        path = ROOT / rel
        if path.exists():
            print(f"exists, not overwritten: {rel}", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(rel)
    for rel, text in appends.items():
        path = ROOT / rel
        if f"VIEW {a.source}_{dataset} " not in path.read_text(encoding="utf-8"):
            with path.open("a", encoding="utf-8") as f:
                f.write(text)
            print(f"{rel} (view appended)")
    for rel, (old, new) in patches.items():
        if old != new:
            (ROOT / rel).write_text(new, encoding="utf-8")
            print(f"{rel} (patched)")
    print(
        f"next: fill fetch/normalise in src/quant/ingest/{a.source}.py, the Schema table in catalog/datasets/{dataset}.md, then `just test` and `just ingest {a.source} --dry-run`"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
