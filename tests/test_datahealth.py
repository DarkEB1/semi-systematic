"""Freshness must include every expected symbol, including on a partition's first day."""

import datetime as dt

import duckdb
import pyarrow as pa
import pytest

from quant import datahealth
from quant.datasets import DatasetDoc


@pytest.mark.parametrize(
    "dates,status,latest",
    [
        (["2026-10-02", "2026-10-01"], "stale", "2026-10-01"),
        (["2026-10-02", "2026-10-02"], "ok", "2026-10-02"),
        (["2026-10-02", None], "missing", None),
    ],
)
def test_daily_health_uses_least_current_expected_symbol(
    tmp_path, monkeypatch, user_cfg, dates, status, latest
):
    doc = DatasetDoc("prices_daily", tmp_path, "tester", "yahoo", "daily", 1)
    monkeypatch.setattr(datahealth, "universe", lambda: [{"symbol": s} for s in ["A", "B"]])
    with duckdb.connect() as con:
        con.register(
            "bars",
            pa.table(
                {
                    "symbol": ["A", "B"],
                    "date": pa.array(
                        [dt.date.fromisoformat(d) if d else None for d in dates], pa.date32()
                    ),
                }
            ),
        )

        class LocalConnection:
            def execute(self, sql, params):
                return con.execute(sql.replace("read_parquet(?)", "bars"))

        result = datahealth.assess(
            doc,
            [{"Key": "raw/yahoo/prices_daily/year=2026/month=10/data.parquet"}],
            dt.date(2026, 10, 3),
            con=LocalConnection(),
            cfg=user_cfg,
        )
    assert result.status == status
    assert result.latest_partition == latest


def test_missing_symbol_and_unreadable_file_cannot_be_healthy_on_month_start(user_cfg):
    class Connection:
        def execute(self, *_):
            return self

        def fetchall(self):
            return [("A", dt.date(2026, 10, 1))]

    assert datahealth.max_date_in("key", con=Connection(), cfg=user_cfg, symbols=["A", "B"]) is None

    class BrokenConnection:
        def execute(self, *_):
            raise OSError("unreadable")

    assert datahealth.max_date_in("key", con=BrokenConnection(), cfg=user_cfg) is None
