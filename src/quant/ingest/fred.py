"""Source ``fred``: daily FRED series (H.10 FX fixings, US short rates, dollar indices), one row
per series per day.

Official FRED API, free key in ``FRED_API_KEY``. The series list is
``catalog/reference/fred_series.csv`` (``series_id`` -> our ``symbol``); adding a series is a row
there, not code. FRED marks a day without a value (holiday) as ``"."``; those rows are dropped.

Shape shared by every source module (see the pull-data skill's template):
``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``, ``run``.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pyarrow as pa

from quant import data
from quant.ingest import _base

SOURCE = "fred"
DATASETS = ("series_daily",)
CADENCE = "daily"  # daily | intraday | snapshot
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"
HEADERS = {"User-Agent": "semi-systematic ingest"}

SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("series_id", pa.string()),
        pa.field("symbol", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def series_list() -> list[dict[str, str]]:
    """Rows of catalog/reference/fred_series.csv."""
    path = data.REPO_ROOT / "catalog" / "reference" / "fred_series.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("series_id")]


def api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise RuntimeError("fred: FRED_API_KEY is not set (see .env.example)")
    return key


def fetch(
    series_id: str, since: dt.date, until: dt.date | None = None, *, retries: int = 3
) -> dict[str, Any]:
    """Observations payload (JSON) for ``series_id`` between ``since`` and ``until`` inclusive.
    Raises on any error; never returns partial data. Error messages never contain the key."""
    until = until or dt.date.today()
    query = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key(),
            "file_type": "json",
            "observation_start": since.isoformat(),
            "observation_end": until.isoformat(),
        }
    )
    req = urllib.request.Request(f"{ENDPOINT}?{query}", headers=HEADERS)
    last = ""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (400, 403, 404):  # bad series id or key: retrying will not help
                break
        except (OSError, json.JSONDecodeError) as e:  # pragma: no cover - network, timeout, reset
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fred: failed to fetch {series_id}: {last}")


def normalise(
    payload: dict[str, Any], series_id: str, symbol: str, *, ingested_at: dt.datetime | None = None
) -> pa.Table:
    """Observations JSON -> one typed row per observed day. ``"."`` (no value) is dropped."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    if "observations" not in payload:
        raise RuntimeError(f"fred: {series_id}: no observations in response")
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    for obs in payload["observations"]:
        if obs.get("value") in (None, "", "."):
            continue
        rows["date"].append(dt.date.fromisoformat(obs["date"]))
        rows["series_id"].append(series_id)
        rows["symbol"].append(symbol)
        rows["value"].append(float(obs["value"]))
        rows["source"].append(SOURCE)
        rows["ingested_at"].append(ingested_at)
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def run(
    since: dt.date | None = None,
    *,
    dry_run: bool = False,
    series: list[dict[str, str]] | None = None,
    client: Any = None,
) -> list[str]:
    """Fetch every listed series from the first day of ``since``'s month (daily cadence rewrites
    whole months) and write the partitions. Returns the keys written."""
    today = dt.date.today()
    since = since or (today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    since = since.replace(day=1)
    tables = []
    for row in series or series_list():
        normalised = normalise(
            fetch(row["series_id"], since, today), row["series_id"], row["symbol"]
        )
        if not normalised.num_rows:
            raise ValueError(f"fred: empty response for {row['series_id']}; no partitions written")
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
            id_col="series_id",
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
