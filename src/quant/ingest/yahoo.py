"""Source ``yahoo``: daily OHLCV for the FX universe from the Yahoo Finance chart endpoint.

Free, no key. Volume is reported as 0 for FX pairs. Universe comes from
``catalog/reference/universe.csv`` (column ``yahoo_symbol``). Raw is stored as received after a
light normalisation (one row per symbol per day, typed columns); no schema contract applies.

Shape shared by every source module (see the pull-data skill's template):
``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``, ``run``.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import time
import urllib.error
import urllib.request
from typing import Any

import pyarrow as pa

from quant import data
from quant.ingest import _base

SOURCE = "yahoo"
DATASETS = ("prices_daily",)
CADENCE = "daily"
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; semi-systematic ingest)"}

SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("symbol", pa.string()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.int64()),
        pa.field("source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def universe() -> list[dict[str, str]]:
    """Rows of catalog/reference/universe.csv that have a yahoo_symbol."""
    path = data.REPO_ROOT / "catalog" / "reference" / "universe.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("yahoo_symbol")]


def fetch(
    symbol: str, since: dt.date, until: dt.date | None = None, *, retries: int = 3
) -> dict[str, Any]:
    """One chart payload (JSON) for ``symbol`` between ``since`` and ``until`` inclusive."""
    until = until or dt.date.today()
    p1 = int(dt.datetime.combine(since, dt.time.min, tzinfo=dt.UTC).timestamp())
    p2 = int(
        dt.datetime.combine(until + dt.timedelta(days=1), dt.time.min, tzinfo=dt.UTC).timestamp()
    )
    url = ENDPOINT.format(symbol=symbol) + f"?interval=1d&period1={p1}&period2={p2}&events=history"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:  # pragma: no cover
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"yahoo: failed to fetch {symbol} after {retries} attempts: {last}")


def normalise(
    payload: dict[str, Any], symbol: str, *, ingested_at: dt.datetime | None = None
) -> pa.Table:
    """Chart JSON -> one typed row per trading day. Rows without a close are dropped.
    ``symbol`` is our universe symbol (e.g. USDBRL), not Yahoo's."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"yahoo: {symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        return SCHEMA.empty_table()
    r = results[0]
    ts = r.get("timestamp") or []
    q = (r.get("indicators", {}).get("quote") or [{}])[0]
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    seen: set[dt.date] = set()
    for i, t in enumerate(ts):
        close = (q.get("close") or [None] * len(ts))[i]
        if close is None:
            continue
        day = dt.datetime.fromtimestamp(t, tz=dt.UTC).date()
        if day in seen:  # yahoo sometimes repeats the live bar
            continue
        seen.add(day)
        rows["date"].append(day)
        rows["symbol"].append(symbol)
        for col in ("open", "high", "low", "close"):
            v = (q.get(col) or [None] * len(ts))[i]
            rows[col].append(float(v) if v is not None else None)
        vol = (q.get("volume") or [None] * len(ts))[i]
        rows["volume"].append(int(vol) if vol is not None else None)
        rows["source"].append(SOURCE)
        rows["ingested_at"].append(ingested_at)
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def run(
    since: dt.date | None = None,
    *,
    dry_run: bool = False,
    symbols: list[dict[str, str]] | None = None,
    client: Any = None,
) -> list[str]:
    """Fetch every universe symbol from the first day of ``since``'s month (so monthly partitions
    are always rewritten whole) and write the partitions. Returns the keys written."""
    today = dt.date.today()
    since = since or (today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    since = since.replace(day=1)
    tables = []
    for row in symbols or universe():
        payload = fetch(row["yahoo_symbol"], since, today)
        tables.append(normalise(payload, row["symbol"]))
    table = pa.concat_tables(tables) if tables else SCHEMA.empty_table()
    return _base.write_partitions(
        table, source=SOURCE, dataset=DATASETS[0], cadence=CADENCE, dry_run=dry_run, client=client
    )
