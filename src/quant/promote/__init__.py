"""Promote a scratch Parquet to curated/ under the schema contract.

A promote request is a YAML file in ``promote/requests/``::

    name: prices_daily                     # catalog/datasets/<name>.md must exist
    scratch_key: scratch/DarkEB1/.../data.parquet
    snapshot: 2026-10-29                   # curated/<name>/snapshot=<snapshot>/
    requested_by: DarkEB1
    date: 2026-10-29
    notes: optional free text

promote.yml runs ``just promote <request>`` with ``QUANT_ROLE=promote`` on merge to main. The step
refuses a file whose columns or types differ from the README's Schema table, never overwrites an
existing snapshot, and copies the README next to the data.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from quant import data

REQUIRED = ("name", "scratch_key", "snapshot", "requested_by", "date")


def read_request(path: str | Path) -> dict[str, Any]:
    req = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [k for k in REQUIRED if k not in req]
    if missing:
        raise ValueError(f"{path}: missing keys {missing}")
    snap = str(req["snapshot"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap):
        raise ValueError(f"{path}: snapshot must be YYYY-MM-DD, got {snap!r}")
    if not str(req["scratch_key"]).startswith(data.SCRATCH):
        raise ValueError(f"{path}: scratch_key must be under {data.SCRATCH!r}")
    req["snapshot"] = snap
    return req


def curated_keys(name: str, snapshot: str) -> tuple[str, str]:
    base = f"{data.CURATED}{name}/{data.partition_key('', snapshot=snapshot).lstrip('/')}"
    return f"{base}/data.parquet", f"{base}/README.md"


def promote(
    request: str | Path,
    *,
    dry_run: bool = False,
    client: Any = None,
    cfg: data.Settings | None = None,
) -> list[str]:
    """Validate and copy. Returns the curated keys written (or that would be written)."""
    req = read_request(request)
    cfg = cfg or data.settings(write=True)
    client = client or data.s3_client(write=True)
    table = data.read_parquet(req["scratch_key"], client=client, cfg=cfg)
    data.validate_schema(table, req["name"])  # raises SchemaMismatch
    data_key, readme_key = curated_keys(req["name"], req["snapshot"])
    data.check_write_allowed(data_key, cfg=cfg)
    if dry_run:
        return [data_key, readme_key]
    readme = (data.DATASET_DOCS / f"{req['name']}.md").read_text(encoding="utf-8")
    data.write_once(table, data_key, client=client, cfg=cfg)
    data.put_text(readme, readme_key, client=client, cfg=cfg)
    return [data_key, readme_key]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just promote", description="Execute a promote request.")
    p.add_argument("request", help="path to promote/requests/<date>-<name>.yml")
    p.add_argument("--dry-run", action="store_true", help="validate only")
    a = p.parse_args(argv)
    try:
        for key in promote(a.request, dry_run=a.dry_run):
            print(key)
    except (
        data.SchemaMismatch,
        data.PrefixError,
        data.ExistsError,
        ValueError,
        FileNotFoundError,
    ) as e:
        print(f"promote refused: {e}", file=sys.stderr)
        return 1
    return 0
