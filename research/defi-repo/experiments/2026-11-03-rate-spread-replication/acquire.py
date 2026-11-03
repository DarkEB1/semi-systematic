"""Acquire the bounded study sample locally; server publication is a separate step."""

import datetime as dt
import json
from pathlib import Path

import pyarrow.parquet as pq

from quant.ingest import aave_archive, nyfed

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)
    start, end = dt.date(2021, 1, 3), dt.date(2026, 1, 31)
    rates = nyfed.fetch(dt.date(2020, 12, 28), end)
    (out / "nyfed-response.json").write_text(json.dumps(rates))
    pq.write_table(nyfed.normalise(rates), out / "usd_reference_rates.parquet", compression="zstd")
    raw = aave_archive.fetch(start, end, checkpoint=out / "archive")
    table = aave_archive.normalise(raw)
    expected = ((end - start).days + 1) * 3 + 6
    assert table.num_rows == expected, (table.num_rows, expected)
    pq.write_table(table, out / "aave_reserve_daily.parquet", compression="zstd")
    print(f"acquired {table.num_rows} reserve rows; no server writes", flush=True)


if __name__ == "__main__":
    main()
