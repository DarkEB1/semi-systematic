"""Source ``cftc``: CFTC Traders in Financial Futures (TFF, futures only) positions for the CME
currency futures, one row per contract per weekly report.

CFTC Public Reporting (Socrata) API, free, no key. Positions are as of Tuesday (``date`` is the
report date) and published the following Friday. Contracts are identified by their CFTC contract
market code; the market names changed in 2022 for some of them, the codes did not.

Shape shared by every source module (see the pull-data skill's template):
``SOURCE``, ``DATASETS``, ``CADENCE``, ``fetch`` -> ``normalise`` -> ``write_partitions``, ``run``.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pyarrow as pa

from quant import data
from quant.ingest import _base

SOURCE = "cftc"
DATASETS = ("tff_fx_weekly",)
CADENCE = "daily"  # weekly observations, stored in the daily (year/month) layout
DEFAULT_LOOKBACK_DAYS = 400
ENDPOINT = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
HEADERS = {"User-Agent": "semi-systematic ingest"}
PAGE = 50000
# CFTC contract market code -> currency of the CME future (priced in USD per unit of it).
CONTRACTS = {
    "099741": "EUR",
    "097741": "JPY",
    "096742": "GBP",
    "090741": "CAD",
    "092741": "CHF",
    "232741": "AUD",
    "112741": "NZD",
    "095741": "MXN",
    "102741": "BRL",
    "122741": "ZAR",
}
# Our column -> TFF field.
FIELDS = {
    "open_interest": "open_interest_all",
    "dealer_long": "dealer_positions_long_all",
    "dealer_short": "dealer_positions_short_all",
    "asset_mgr_long": "asset_mgr_positions_long",
    "asset_mgr_short": "asset_mgr_positions_short",
    "lev_money_long": "lev_money_positions_long",
    "lev_money_short": "lev_money_positions_short",
}

SCHEMA = pa.schema(
    [
        pa.field("date", pa.date32()),
        pa.field("contract_code", pa.string()),
        pa.field("symbol", pa.string()),
        pa.field("market_name", pa.string()),
        *[pa.field(col, pa.int64()) for col in FIELDS],
        pa.field("source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def fetch(
    since: dt.date,
    until: dt.date | None = None,
    *,
    codes: list[str] | None = None,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Every TFF record for ``codes`` with a report date in ``since``..``until``, all pages.
    Raises on any error; never returns partial data."""
    until = until or dt.date.today()
    codes = codes or list(CONTRACTS)
    where = (
        "cftc_contract_market_code in(" + ",".join(f"'{c}'" for c in codes) + ")"
        f" and report_date_as_yyyy_mm_dd between '{since.isoformat()}' and '{until.isoformat()}'"
    )
    select = ",".join(
        ["report_date_as_yyyy_mm_dd", "cftc_contract_market_code", "market_and_exchange_names"]
        + list(FIELDS.values())
    )
    records: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "$select": select,
                "$where": where,
                "$order": "report_date_as_yyyy_mm_dd,cftc_contract_market_code",
                "$limit": PAGE,
                "$offset": offset,
            }
        )
        page = _get(f"{ENDPOINT}?{query}", retries)
        records.extend(page)
        if len(page) < PAGE:
            return records
        offset += PAGE


def _get(url: str, retries: int) -> list[dict[str, Any]]:
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 400:
                break
        except (OSError, json.JSONDecodeError) as e:  # pragma: no cover - network, timeout, reset
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"cftc: failed to fetch TFF: {last}")


def normalise(payload: list[dict[str, Any]], *, ingested_at: dt.datetime | None = None) -> pa.Table:
    """TFF records -> one typed row per contract per report date."""
    ingested_at = ingested_at or dt.datetime.now(dt.UTC)
    rows: dict[str, list[Any]] = {k: [] for k in SCHEMA.names}
    seen: set[tuple[str, dt.date]] = set()
    for rec in payload:
        code = rec["cftc_contract_market_code"].strip()
        day = dt.date.fromisoformat(rec["report_date_as_yyyy_mm_dd"][:10])
        if code not in CONTRACTS or (code, day) in seen:
            continue
        seen.add((code, day))
        rows["date"].append(day)
        rows["contract_code"].append(code)
        rows["symbol"].append(CONTRACTS[code])
        rows["market_name"].append(rec.get("market_and_exchange_names"))
        for col, field in FIELDS.items():
            v = rec.get(field)
            rows[col].append(int(float(v)) if v not in (None, "") else None)
        rows["source"].append(SOURCE)
        rows["ingested_at"].append(ingested_at)
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def run(since: dt.date | None = None, *, dry_run: bool = False, client: Any = None) -> list[str]:
    """Fetch every contract from the first day of ``since``'s month (whole months are rewritten)
    and write the partitions. Returns the keys written."""
    today = dt.date.today()
    since = since or (today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    since = since.replace(day=1)
    table = normalise(fetch(since, today))
    missing = set(CONTRACTS.values()) - set(table["symbol"].to_pylist())
    # every contract reports weekly since 2022-02 (ZAR and BRL have gaps before)
    if not table.num_rows or (since >= dt.date(2022, 3, 1) and missing):
        raise ValueError(f"cftc: empty response for {sorted(missing)}; no partitions written")
    cfg = data.settings(write=True)
    if cfg.role == "ingest":
        client = client or data.s3_client(write=True)
        _base.check_history(
            table,
            since,
            source=SOURCE,
            dataset=DATASETS[0],
            id_col="contract_code",
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
