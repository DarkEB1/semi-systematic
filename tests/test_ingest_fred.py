"""quant.ingest.fred with the fixture in tests/fixtures (a real DEXUSEU response, no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import fred

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "fred_sample.json").read_text())
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)
ONE = [{"series_id": "DEXUSEU", "symbol": "EURUSD"}]


def test_normalise_matches_schema_and_drops_missing():
    t = fred.normalise(FIXTURE, "DEXUSEU", "EURUSD", ingested_at=STAMP)
    assert t.schema.equals(fred.SCHEMA)
    assert t.num_rows == 4  # two "." holidays dropped
    assert dt.date(2025, 12, 25) not in t["date"].to_pylist()
    assert t["value"].to_pylist()[0] == pytest.approx(1.178)
    assert set(t["symbol"].to_pylist()) == {"EURUSD"}
    assert set(t["source"].to_pylist()) == {"fred"}


def test_normalise_rejects_error_payload():
    with pytest.raises(RuntimeError, match="no observations"):
        fred.normalise({"error_code": 400, "error_message": "Bad Request"}, "X", "X")


def test_series_list_is_unique_and_complete():
    rows = fred.series_list()
    assert rows
    assert len({r["series_id"] for r in rows}) == len(rows)
    assert len({r["symbol"] for r in rows}) == len(rows)
    assert all(r["kind"] in {"fx_spot", "rate", "index"} for r in rows)


def test_missing_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        fred.fetch("DEXUSEU", dt.date(2026, 1, 1))


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(fred, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = fred.run(dt.date(2025, 12, 15), series=ONE, client=s3)
    assert len(keys) == 2  # 2025-12 and 2026-01
    assert all(k.startswith("scratch/tester/raw/fred/series_daily/") for k in keys)


def test_run_refuses_empty_series(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(fred, "fetch", lambda *_a, **_k: {"observations": []})
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    with pytest.raises(ValueError, match="empty response"):
        fred.run(dt.date(2025, 12, 15), series=ONE, client=s3)
