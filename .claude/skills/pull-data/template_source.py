"""Source ``__SOURCE__``: __DESCRIPTION__

Scaffolded by the pull-data skill. Fill in ``fetch`` and ``normalise``; keep the shape
(``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``,
``run``) so the registry, the nightly workflow and data-health treat every source the same.
Raw is stored as received after light normalisation; no schema contract applies to raw/.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
from typing import Any

import pyarrow as pa

from quant.ingest import _base

SOURCE = "__SOURCE__"
DATASETS = ("__DATASET__",)
CADENCE = "__CADENCE__"  # daily | intraday | snapshot
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://example.com/api/__DATASET__?since={since}"  # TODO
HEADERS = {"User-Agent": "semi-systematic ingest"}

SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("symbol", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def fetch(since: dt.date, until: dt.date | None = None) -> Any:
    """Return the vendor payload as received. Raise on any error; never return partial data."""
    until = until or dt.date.today()
    url = ENDPOINT.format(since=since.isoformat(), until=until.isoformat())
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


def normalise(payload: Any, *, ingested_at: dt.datetime | None = None) -> pa.Table:
    """Vendor payload -> one typed row per observation, matching SCHEMA. TODO."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    for item in payload or []:
        rows["date"].append(dt.date.fromisoformat(str(item["date"])))
        rows["symbol"].append(str(item["symbol"]))
        rows["value"].append(float(item["value"]))
        rows["source"].append(SOURCE)
        rows["ingested_at"].append(ingested_at)
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def run(since: dt.date | None = None, *, dry_run: bool = False, client: Any = None) -> list[str]:
    """Fetch from the first day of ``since``'s month (daily cadence rewrites whole months)."""
    today = dt.date.today()
    since = since or (today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    if CADENCE == "daily":
        since = since.replace(day=1)
    table = normalise(fetch(since, today))
    return _base.write_partitions(
        table, source=SOURCE, dataset=DATASETS[0], cadence=CADENCE, dry_run=dry_run, client=client
    )
