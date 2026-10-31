"""quant.ingest.yahoo with the small fixture in tests/fixtures (no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pyarrow as pa
import pytest

from quant import data
from quant.ingest import SOURCES, _base, resolve, yahoo

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "yahoo_chart.json").read_text())
STAMP = dt.datetime(2026, 10, 29, 12, 0, tzinfo=dt.UTC)


def test_registry_resolves_source_and_dataset():
    assert "yahoo" in SOURCES
    assert resolve("yahoo") is yahoo
    assert resolve("prices_daily") is yahoo
    with pytest.raises(SystemExit):
        resolve("nope")


def test_normalise_types_rows_and_drops_null_close():
    t = yahoo.normalise(FIXTURE, "USDBRL", ingested_at=STAMP)
    assert t.schema.equals(yahoo.SCHEMA)
    assert t.num_rows == 3, "one null-close bar dropped and the repeated day kept once"
    assert t["symbol"].to_pylist() == ["USDBRL"] * 3
    assert t["date"].to_pylist() == [
        dt.date(2026, 9, 29),
        dt.date(2026, 9, 30),
        dt.date(2026, 10, 2),
    ]
    assert t["close"].to_pylist() == [5.32, 5.33, 5.35], "first occurrence of a repeated day wins"
    assert t["source"].to_pylist() == ["yahoo"] * 3
    assert t["volume"].type == pa.int64()


def test_normalise_empty_payload():
    assert yahoo.normalise({"chart": {"result": []}}, "X").num_rows == 0


def test_normalise_error_payload():
    with pytest.raises(RuntimeError, match="boom"):
        yahoo.normalise({"chart": {"result": None, "error": "boom"}}, "X")


def test_split_partitions_groups_by_month():
    t = yahoo.normalise(FIXTURE, "USDBRL", ingested_at=STAMP)
    parts = _base.split_partitions(t, "daily")
    assert [rel for rel, _ in parts] == [
        "year=2026/month=09/data.parquet",
        "year=2026/month=10/data.parquet",
    ]
    assert [sub.num_rows for _, sub in parts] == [2, 1]


def test_run_writes_scratch_mirror_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(yahoo, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = yahoo.run(
        dt.date(2026, 10, 15), symbols=[{"symbol": "USDBRL", "yahoo_symbol": "BRL=X"}], client=s3
    )
    assert len(keys) == 2
    assert all(k.startswith("scratch/tester/raw/yahoo/prices_daily/run=") for k in keys)
    assert not any(k.startswith("raw/") for k in s3.puts)


def test_run_writes_raw_and_overwrites_for_ingest_role(s3, ingest_cfg, monkeypatch):
    monkeypatch.setattr(yahoo, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: ingest_cfg)
    first = yahoo.run(
        dt.date(2026, 10, 15), symbols=[{"symbol": "USDBRL", "yahoo_symbol": "BRL=X"}], client=s3
    )
    second = yahoo.run(
        dt.date(2026, 10, 15), symbols=[{"symbol": "USDBRL", "yahoo_symbol": "BRL=X"}], client=s3
    )
    assert (
        first
        == second
        == [
            "raw/yahoo/prices_daily/year=2026/month=09/data.parquet",
            "raw/yahoo/prices_daily/year=2026/month=10/data.parquet",
        ]
    )
    assert s3.puts.count(first[0]) == 2, "ingest role rewrites the partition in place"


def test_dry_run_writes_nothing(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(yahoo, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = yahoo.run(
        dt.date(2026, 10, 15),
        dry_run=True,
        symbols=[{"symbol": "USDBRL", "yahoo_symbol": "BRL=X"}],
        client=s3,
    )
    assert len(keys) == 2 and s3.puts == []


def test_universe_has_yahoo_symbols():
    rows = yahoo.universe()
    assert {"symbol", "yahoo_symbol", "asset_class"} <= set(rows[0])
    assert any(r["symbol"] == "USDBRL" for r in rows)
