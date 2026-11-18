"""Source ``bcb``: Banco Central do Brasil SGS series (Selic target and effective, CDI, PTAX
USD/BRL), one row per series per day.

SGS open-data API, free, no key. The API accepts at most a ten-year window for a daily series, so
``fetch`` splits longer requests. The series list is ``catalog/reference/bcb_series.csv``
(SGS ``code`` -> our ``symbol``); adding a series is a row there, not code.

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

SOURCE = "bcb"
DATASETS = ("brl_series_daily",)
CADENCE = "daily"  # daily | intraday | snapshot
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?formato=json&dataInicial={start}&dataFinal={end}"
)
HEADERS = {"User-Agent": "semi-systematic ingest"}
MAX_WINDOW_DAYS = 3600  # the API refuses daily windows longer than ten years

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
    """Rows of catalog/reference/bcb_series.csv."""
    path = data.REPO_ROOT / "catalog" / "reference" / "bcb_series.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("code")]


def windows(since: dt.date, until: dt.date) -> list[tuple[dt.date, dt.date]]:
    """Consecutive inclusive windows of at most MAX_WINDOW_DAYS covering since..until."""
    out = []
    start = since
    while start <= until:
        end = min(until, start + dt.timedelta(days=MAX_WINDOW_DAYS - 1))
        out.append((start, end))
        start = end + dt.timedelta(days=1)
    return out


def _get(url: str, retries: int) -> list[dict[str, str]]:
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:  # no observation in the window
                return []
            last = f"HTTP {e.code}"
        except (OSError, json.JSONDecodeError) as e:  # pragma: no cover - network, timeout, reset
            last = type(e).__name__
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(last)


def fetch(
    code: str, since: dt.date, until: dt.date | None = None, *, retries: int = 3
) -> list[dict[str, str]]:
    """Every ``{"data": "dd/mm/yyyy", "valor": "..."}`` record for SGS ``code`` between ``since``
    and ``until`` inclusive. Raises on any error; never returns partial data."""
    until = until or dt.date.today()
    records: list[dict[str, str]] = []
    for start, end in windows(since, until):
        url = ENDPOINT.format(
            code=code, start=start.strftime("%d/%m/%Y"), end=end.strftime("%d/%m/%Y")
        )
        try:
            records.extend(_get(url, retries))
        except RuntimeError as e:
            raise RuntimeError(f"bcb: failed to fetch {code} {start}..{end}: {e}") from None
    return records


def normalise(
    payload: list[dict[str, str]],
    series_id: str,
    symbol: str,
    *,
    ingested_at: dt.datetime | None = None,
) -> pa.Table:
    """SGS records -> one typed row per observed day (deduplicated on date)."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    seen: set[dt.date] = set()
    for rec in payload:
        value = (rec.get("valor") or "").strip()
        if not value:
            continue
        day = dt.datetime.strptime(rec["data"], "%d/%m/%Y").date()
        if day in seen:  # adjacent windows never overlap, but be safe
            continue
        seen.add(day)
        rows["date"].append(day)
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
        series_id = f"SGS{row['code']}"
        normalised = normalise(fetch(row["code"], since, today), series_id, row["symbol"])
        if not normalised.num_rows:
            raise ValueError(f"bcb: empty response for {series_id}; no partitions written")
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
