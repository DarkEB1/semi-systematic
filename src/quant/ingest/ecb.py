"""Source ``ecb``: ECB euro reference FX rates and the euro short-term rate (ESTR), one row per
series per day.

ECB Data Portal SDMX API, free, no key. The series list is ``catalog/reference/ecb_series.csv``
(``flow`` + ``key`` -> our ``symbol``); adding a series is a row there, not code.

Shape shared by every source module (see the pull-data skill's template):
``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``, ``run``.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pyarrow as pa

from quant import data
from quant.ingest import _base

SOURCE = "ecb"
DATASETS = ("eur_series_daily",)
CADENCE = "daily"  # daily | intraday | snapshot
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
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
    """Rows of catalog/reference/ecb_series.csv."""
    path = data.REPO_ROOT / "catalog" / "reference" / "ecb_series.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("key")]


def fetch(
    flow: str, key: str, since: dt.date, until: dt.date | None = None, *, retries: int = 3
) -> str:
    """CSV text for one series between ``since`` and ``until`` inclusive; ``""`` when the ECB has
    no observation in the window (HTTP 404). Raises on any other error."""
    until = until or dt.date.today()
    query = urllib.parse.urlencode(
        {
            "format": "csvdata",
            "detail": "dataonly",
            "startPeriod": since.isoformat(),
            "endPeriod": until.isoformat(),
        }
    )
    url = ENDPOINT.format(flow=flow, key=key) + f"?{query}"
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            last = f"HTTP {e.code}"
            if e.code == 400:
                break
        except OSError as e:  # pragma: no cover - network, timeout, reset
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ecb: failed to fetch {flow}.{key}: {last}")


def normalise(
    payload: str, series_id: str, symbol: str, *, ingested_at: dt.datetime | None = None
) -> pa.Table:
    """SDMX CSV -> one typed row per observed day. Rows without a value are dropped."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    for rec in csv.DictReader(io.StringIO(payload)):
        value = (rec.get("OBS_VALUE") or "").strip()
        if not value or value.upper() == "NAN":
            continue
        rows["date"].append(dt.date.fromisoformat(rec["TIME_PERIOD"]))
        rows["series_id"].append(series_id)
        rows["symbol"].append(symbol)
        rows["value"].append(float(value))
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
        series_id = f"{row['flow']}.{row['key']}"
        normalised = normalise(
            fetch(row["flow"], row["key"], since, today), series_id, row["symbol"]
        )
        if not normalised.num_rows:
            raise ValueError(f"ecb: empty response for {series_id}; no partitions written")
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
