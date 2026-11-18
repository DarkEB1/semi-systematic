"""Source ``cboe``: Cboe volatility indices (VIX, VXEEM, OVX, GVZ), one row per index per day.

Public history files on cdn.cboe.com, free, no key. Each file holds the full history and is
re-downloaded whole; rows before ``since`` are dropped. VIX and VXEEM files carry OHLC; OVX and GVZ
carry a single column, stored as ``close`` with ``open``/``high``/``low`` null.

Shape shared by every source module (see the pull-data skill's template):
``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``, ``run``.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import time
import urllib.error
import urllib.request
from typing import Any

import pyarrow as pa

from quant import data
from quant.ingest import _base

SOURCE = "cboe"
DATASETS = ("vol_indices_daily",)
CADENCE = "daily"  # daily | intraday | snapshot
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{index}_History.csv"
HEADERS = {"User-Agent": "semi-systematic ingest"}
# Index -> what it measures. Adding one is a line here once its history file exists on the CDN.
INDICES = {
    "VIX": "30-day implied vol of the S&P 500",
    "VXEEM": "30-day implied vol of the iShares MSCI Emerging Markets ETF (EEM)",
    "OVX": "30-day implied vol of the United States Oil Fund (USO)",
    "GVZ": "30-day implied vol of the SPDR Gold Shares ETF (GLD)",
}

SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("symbol", pa.string()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def fetch(index: str, *, retries: int = 3) -> str:
    """The full history CSV for ``index``. Raises on any error."""
    url = ENDPOINT.format(index=index)
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (403, 404):
                break
        except OSError as e:  # pragma: no cover - network, timeout, reset
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"cboe: failed to fetch {index}: {last}")


def _num(v: str | None) -> float | None:
    v = (v or "").strip()
    return float(v) if v and v != "." else None


def normalise(
    payload: str,
    index: str,
    since: dt.date | None = None,
    *,
    ingested_at: dt.datetime | None = None,
) -> pa.Table:
    """History CSV -> one typed row per day from ``since`` on. Rows without a close are dropped."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    reader = csv.DictReader(io.StringIO(payload))
    single = index if reader.fieldnames and "CLOSE" not in reader.fieldnames else None
    seen: set[dt.date] = set()
    for rec in reader:
        close = _num(rec.get(single or "CLOSE"))
        if close is None:
            continue
        day = dt.datetime.strptime(rec["DATE"].strip(), "%m/%d/%Y").date()
        if (since and day < since) or day in seen:
            continue
        seen.add(day)
        rows["date"].append(day)
        rows["symbol"].append(index)
        for col in ("open", "high", "low"):
            rows[col].append(None if single else _num(rec.get(col.upper())))
        rows["close"].append(close)
        rows["source"].append(SOURCE)
        rows["ingested_at"].append(ingested_at)
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def run(
    since: dt.date | None = None,
    *,
    dry_run: bool = False,
    indices: list[str] | None = None,
    client: Any = None,
) -> list[str]:
    """Fetch every index, keep rows from the first day of ``since``'s month (daily cadence
    rewrites whole months) and write the partitions. Returns the keys written."""
    today = dt.date.today()
    since = since or (today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    since = since.replace(day=1)
    tables = []
    for index in indices or list(INDICES):
        normalised = normalise(fetch(index), index, since)
        if not normalised.num_rows:
            raise ValueError(f"cboe: empty response for {index}; no partitions written")
        tables.append(normalised)
    table = pa.concat_tables(tables) if tables else SCHEMA.empty_table()
    cfg = data.settings(write=True)
    if cfg.role == "ingest":
        client = client or data.s3_client(write=True)
        _base.check_history(
            table,
            since,
            source=SOURCE,
            dataset=DATASETS[0],
            id_col="symbol",
            client=client,
            cfg=cfg,
        )
    return _base.write_partitions(
        table,
        source=SOURCE,
        dataset=DATASETS[0],
        cadence=CADENCE,
        dry_run=dry_run,
        client=client,
        cfg=cfg,
    )
