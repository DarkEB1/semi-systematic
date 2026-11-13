"""quant.ingest.cboe with the fixture in tests/fixtures (real VIX and OVX rows, no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import cboe

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "cboe_sample.json").read_text())
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)


def test_normalise_ohlc_file():
    t = cboe.normalise(FIXTURE["VIX"], "VIX", ingested_at=STAMP)
    assert t.schema.equals(cboe.SCHEMA)
    assert t.num_rows == 5
    first = t.slice(0, 1).to_pylist()[0]
    assert first["date"] == dt.date(2025, 12, 29)
    assert first["open"] == pytest.approx(14.69) and first["close"] == pytest.approx(14.2)


def test_normalise_single_column_file_stores_close_only():
    t = cboe.normalise(FIXTURE["OVX"], "OVX", ingested_at=STAMP)
    assert t.num_rows == 5
    assert set(t["open"].to_pylist()) == {None}
    assert t["close"].to_pylist()[0] == pytest.approx(32.16)


def test_normalise_drops_rows_before_since():
    t = cboe.normalise(FIXTURE["VIX"], "VIX", dt.date(2026, 1, 1))
    assert t["date"].to_pylist() == [dt.date(2026, 1, 2), dt.date(2026, 1, 5)]


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(cboe, "fetch", lambda index, **_k: FIXTURE[index])
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = cboe.run(dt.date(2025, 12, 15), indices=["VIX", "OVX"], client=s3)
    assert len(keys) == 2
    assert all(k.startswith("scratch/tester/raw/cboe/vol_indices_daily/") for k in keys)


def test_run_refuses_empty_index(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(cboe, "fetch", lambda *_a, **_k: "DATE,OPEN,HIGH,LOW,CLOSE\n")
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    with pytest.raises(ValueError, match="empty response"):
        cboe.run(dt.date(2025, 12, 15), indices=["VIX"], client=s3)
