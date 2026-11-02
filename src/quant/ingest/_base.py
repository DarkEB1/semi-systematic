"""Shared write path for ingest modules: partition a normalised table and write each partition
through ``quant.data.write_once`` under the prefix the current role is allowed to write."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

from quant import data


def target_prefix(
    cfg: data.Settings, source: str, dataset: str, run_stamp: str | None = None
) -> str:
    """``raw/<source>/<dataset>`` for the ingest role, otherwise a run-stamped mirror under
    ``scratch/<handle>/raw/<source>/<dataset>/run=<stamp>`` so repeated local runs never collide."""
    if cfg.role == "ingest":
        return f"{data.RAW}{source}/{dataset}"
    stamp = run_stamp or dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{cfg.allowed_prefix}raw/{source}/{dataset}/run={stamp}"


def split_partitions(
    table: pa.Table, cadence: str, date_col: str = "date", asset_col: str | None = None
) -> list[tuple[str, pa.Table]]:
    """Group rows into partitions by cadence. Returns ``[(relative_key, sub_table), ...]``."""
    if table.num_rows == 0:
        return []
    dates = pc.cast(table[date_col], pa.date32()).to_pylist()
    classes = table[asset_col].to_pylist() if asset_col else [None] * table.num_rows
    buckets: dict[tuple[Any, ...], list[int]] = {}
    for i, (d, c) in enumerate(zip(dates, classes, strict=True)):
        parts, fname = data.partition_parts(cadence, d, asset_class=c)
        key = (tuple(parts.items()), fname)
        buckets.setdefault(key, []).append(i)
    out = []
    for (parts, fname), idx in sorted(buckets.items()):
        rel = data.partition_key("", **dict(parts)).lstrip("/") + "/" + fname
        out.append((rel, table.take(idx)))
    return out


def write_partitions(
    table: pa.Table,
    *,
    source: str,
    dataset: str,
    cadence: str,
    date_col: str = "date",
    asset_col: str | None = None,
    dry_run: bool = False,
    client: Any = None,
    cfg: data.Settings | None = None,
    run_stamp: str | None = None,
) -> list[str]:
    """Write every partition of ``table``. In the ingest role partitions under raw/ are overwritten
    in place; everywhere else nothing is ever overwritten. Returns the keys written."""
    cfg = cfg or data.settings(write=True)
    prefix = target_prefix(cfg, source, dataset, run_stamp)
    overwrite = cfg.role == "ingest"
    keys = []
    for rel, sub in split_partitions(table, cadence, date_col, asset_col):
        key = f"{prefix}/{rel}"
        data.check_write_allowed(key, overwrite=overwrite, cfg=cfg)
        if not dry_run:
            data.write_once(sub, key, overwrite=overwrite, client=client, cfg=cfg)
        keys.append(key)
    return keys
