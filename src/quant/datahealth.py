"""Data health: latest raw partition per dataset versus the cadence its README promises.

This is the headless form of the dashboard's data-health page; data-health.yml runs it nightly
with ``--issues`` to open or update one GitHub issue per stale dataset.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any

from quant import data
from quant.datasets import DatasetDoc, dataset_docs

_PART = re.compile(
    r"(?:year=(\d{4})/month=(\d{2})|date=(\d{4}-\d{2}-\d{2})|snapshot=(\d{4}-\d{2}-\d{2}))"
)


@dataclass
class Health:
    dataset: str
    source: str
    cadence: str
    owner: str
    latest_partition: str | None
    latest_key: str | None
    expected_through: str
    status: str  # ok | stale | missing
    days_behind: int | None


def last_business_day(today: dt.date, lag_days: int) -> dt.date:
    d = today - dt.timedelta(days=lag_days)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def partition_date(key: str) -> dt.date | None:
    m = _PART.search(key)
    if not m:
        return None
    y, mo, d1, d2 = m.groups()
    if y:
        return dt.date(int(y), int(mo), 1)
    return dt.date.fromisoformat(d1 or d2)


def latest_partition(keys: list[dict[str, Any]]) -> tuple[dt.date | None, str | None]:
    best: tuple[dt.date, str] | None = None
    for obj in keys:
        d = partition_date(obj["Key"])
        if d and (best is None or d > best[0]):
            best = (d, obj["Key"])
    return (best[0], best[1]) if best else (None, None)


def max_date_in(key: str, *, con: Any = None, cfg: data.Settings | None = None) -> dt.date | None:
    """For a monthly partition, the true latest day comes from the file itself."""
    cfg = cfg or data.settings()
    con = con or data.connect(views=False)
    try:
        row = con.execute(
            "SELECT max(date) FROM read_parquet(?)", [f"s3://{cfg.bucket}/{key}"]
        ).fetchone()
        return row[0] if row and row[0] else None
    except Exception:  # noqa: BLE001 - a file without a date column is reported as its partition
        return None


def assess(
    doc: DatasetDoc,
    keys: list[dict[str, Any]],
    today: dt.date,
    *,
    con: Any = None,
    cfg: data.Settings | None = None,
    probe: bool = True,
) -> Health:
    expected = last_business_day(today, doc.lag_days)
    part, key = latest_partition(keys)
    if part is None:
        return Health(
            doc.name,
            doc.source,
            doc.cadence,
            doc.owner,
            None,
            None,
            expected.isoformat(),
            "missing",
            None,
        )
    latest = part
    if doc.cadence == "daily" and key and probe:
        latest = max_date_in(key, con=con, cfg=cfg) or part
    behind = (expected - latest).days
    status = "ok" if behind <= 0 else "stale"
    return Health(
        doc.name,
        doc.source,
        doc.cadence,
        doc.owner,
        latest.isoformat(),
        key,
        expected.isoformat(),
        status,
        max(behind, 0),
    )


def report(
    today: dt.date | None = None,
    *,
    client: Any = None,
    cfg: data.Settings | None = None,
    con: Any = None,
) -> list[Health]:
    today = today or dt.date.today()
    cfg = cfg or data.settings()
    out = []
    for doc in dataset_docs():
        keys = data.list_keys(doc.raw_prefix, client=client, cfg=cfg) if doc.source else []
        out.append(assess(doc, keys, today, con=con, cfg=cfg))
    return out


def format_table(rows: list[Health]) -> str:
    head = f"{'dataset':<20} {'source':<8} {'status':<8} {'latest':<10} {'expected':<10} {'behind':>6}  owner"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r.dataset:<20} {r.source:<8} {r.status:<8} {r.latest_partition or '-':<10} {r.expected_through:<10} {r.days_behind if r.days_behind is not None else '-':>6}  {r.owner}"
        )
    return "\n".join(lines)


def upsert_issue(r: Health, repo: str | None = None) -> None:
    """Open or update one issue per stale/missing dataset, titled ``data-health: <dataset>``."""
    title = f"data-health: {r.dataset}"
    body = (
        f"Dataset `{r.dataset}` (source `{r.source}`, cadence {r.cadence}) is **{r.status}**.\n\n"
        f"- latest partition: {r.latest_partition or 'none'}\n- expected through: {r.expected_through}\n"
        f"- days behind: {r.days_behind}\n- owner: @{r.owner}\n\n"
        f"Run `just refresh` (refresh-data skill) to fill the gap. This issue is updated nightly by data-health.yml."
    )
    repo_args = ["--repo", repo] if repo else []
    existing = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            *repo_args,
            "--state",
            "open",
            "--search",
            f'"{title}" in:title',
            "--json",
            "number,title",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    numbers = [i["number"] for i in json.loads(existing.stdout or "[]") if i["title"] == title]
    if numbers:
        subprocess.run(
            ["gh", "issue", "comment", str(numbers[0]), *repo_args, "--body", body], check=False
        )
    else:
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                *repo_args,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "data-health",
            ],
            check=False,
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just data-health")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--issues",
        action="store_true",
        help="open/update a GitHub issue per stale dataset (needs gh)",
    )
    p.add_argument("--today", type=dt.date.fromisoformat, default=None)
    a = p.parse_args(argv)
    rows = report(a.today)
    if a.json:
        print(json.dumps([asdict(r) for r in rows], indent=2))
    else:
        print(format_table(rows))
    if a.issues:
        for r in rows:
            if r.status != "ok":
                upsert_issue(r)
    stale = [r for r in rows if r.status != "ok"]
    if stale:
        print(f"{len(stale)} dataset(s) not ok", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
