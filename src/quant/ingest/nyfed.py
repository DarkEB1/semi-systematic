"""Official New York Fed SOFR/EFFR observations, not executable funding quotes."""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
from typing import Any

import pyarrow as pa

from quant.ingest import _base

SOURCE = "nyfed"
DATASETS = ("usd_reference_rates",)
CADENCE = "daily"
ENDPOINT = "https://markets.newyorkfed.org/api/rates/{market}/{rate}/search.json"
SCHEMA = pa.schema(
    [
        ("date", pa.date32()),
        ("symbol", pa.string()),
        ("rate_pct", pa.float64()),
        ("volume_billions", pa.float64()),
        ("revision", pa.string()),
        ("source", pa.string()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def fetch(since: dt.date, until: dt.date | None = None) -> list[dict[str, Any]]:
    """Fetch both series completely; any request failure aborts the ingest."""
    until = until or dt.date.today()
    rows = []
    for market, rate in (("secured", "sofr"), ("unsecured", "effr")):
        url = ENDPOINT.format(market=market, rate=rate)
        url += f"?startDate={since}&endDate={until}"
        req = urllib.request.Request(url, headers={"User-Agent": "semi-systematic-research/0.1"})
        with urllib.request.urlopen(req, timeout=60) as response:
            part = json.load(response)["refRates"]
        if not part:
            raise ValueError(f"nyfed: empty {rate} response")
        rows.extend(part)
    return rows


def normalise(payload: list[dict[str, Any]], *, ingested_at: dt.datetime | None = None) -> pa.Table:
    """Preserve effective dates and revision indicators; never fill missing days."""
    stamp = ingested_at or dt.datetime.now(dt.UTC)
    rows = []
    seen = set()
    for item in payload:
        day, symbol = dt.date.fromisoformat(item["effectiveDate"]), item["type"]
        if symbol not in {"SOFR", "EFFR"} or (day, symbol) in seen:
            raise ValueError("nyfed: unexpected series or duplicate observation")
        seen.add((day, symbol))
        rows.append(
            {
                "date": day,
                "symbol": symbol,
                "rate_pct": float(item["percentRate"]),
                "volume_billions": float(item["volumeInBillions"]),
                "revision": item.get("revisionIndicator", ""),
                "source": SOURCE,
                "ingested_at": stamp,
            }
        )
    return pa.Table.from_pylist(sorted(rows, key=lambda r: (r["date"], r["symbol"])), schema=SCHEMA)


def run(since: dt.date | None = None, *, dry_run: bool = False, client: Any = None) -> list[str]:
    """Refresh whole months; local invocations write only run-stamped scratch objects."""
    since = (since or (dt.date.today() - dt.timedelta(days=35))).replace(day=1)
    table = normalise(fetch(since))
    return _base.write_partitions(
        table, source=SOURCE, dataset=DATASETS[0], cadence=CADENCE, dry_run=dry_run, client=client
    )
