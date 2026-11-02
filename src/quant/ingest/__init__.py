"""Ingest registry and CLI.

Every source is a module in this package with the shape of ``_template.py`` (see the pull-data
skill): ``SOURCE``, ``DATASETS``, ``CADENCE`` and ``run(since, *, dry_run)``. Register it in
``SOURCES`` below; ingest.yml reads this registry (``python -m quant.ingest --list``) so a new
source runs nightly without touching the workflow.

Where writes go (see quant.data):
- ``QUANT_ROLE=ingest`` (CI): ``raw/<source>/<dataset>/<partition>/data.parquet``, overwriting the
  affected partitions in place.
- otherwise (a laptop, an agent): ``scratch/<handle>/raw/<source>/<dataset>/run=<stamp>/<partition>/data.parquet``,
  never overwriting. The data layer refuses raw/ for any other role.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from types import ModuleType

from quant.ingest import yahoo

SOURCES: dict[str, ModuleType] = {
    yahoo.SOURCE: yahoo,
}


def resolve(name: str) -> ModuleType:
    """Accept a source name or a dataset name."""
    if name in SOURCES:
        return SOURCES[name]
    for mod in SOURCES.values():
        if name in mod.DATASETS:
            return mod
    known = (
        ", ".join(sorted(SOURCES))
        + " / datasets: "
        + ", ".join(d for m in SOURCES.values() for d in m.DATASETS)
    )
    raise SystemExit(f"unknown source or dataset {name!r}. Known sources: {known}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just ingest", description="Ingest one registered source.")
    p.add_argument("source", nargs="?", help="source name (or a dataset name)")
    p.add_argument(
        "--since",
        type=dt.date.fromisoformat,
        default=None,
        help="YYYY-MM-DD; default: the source's default lookback",
    )
    p.add_argument("--dry-run", action="store_true", help="fetch and normalise but write nothing")
    p.add_argument("--list", action="store_true", help="print registered sources, one per line")
    a = p.parse_args(argv)
    if a.list:
        for name in sorted(SOURCES):
            print(name)
        return 0
    if not a.source:
        p.error("source is required (or --list)")
    mod = resolve(a.source)
    written = mod.run(since=a.since, dry_run=a.dry_run)
    for key in written:
        print(key)
    print(
        f"[{mod.SOURCE}] {'would write' if a.dry_run else 'wrote'} {len(written)} object(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
