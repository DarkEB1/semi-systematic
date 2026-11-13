"""quant.ingest.ecb with the fixture in tests/fixtures (a real EXR PLN response, no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import ecb

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ecb_sample.json").read_text())["csv"]
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)
ONE = [{"flow": "EXR", "key": "D.PLN.EUR.SP00.A", "symbol": "EURPLN"}]


def test_normalise_matches_schema():
    t = ecb.normalise(FIXTURE, "EXR.D.PLN.EUR.SP00.A", "EURPLN", ingested_at=STAMP)
    assert t.schema.equals(ecb.SCHEMA)
    assert t.num_rows == 5
    assert t["date"].to_pylist()[0] == dt.date(2025, 12, 29)
    assert t["value"].to_pylist()[0] == pytest.approx(4.2295)
    assert set(t["source"].to_pylist()) == {"ecb"}


def test_normalise_empty_payload():
    assert ecb.normalise("", "X", "X").num_rows == 0


def test_series_list_is_unique():
    rows = ecb.series_list()
    assert rows and len({r["symbol"] for r in rows}) == len(rows)
    assert {r["flow"] for r in rows} <= {"EXR", "EST"}


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(ecb, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = ecb.run(dt.date(2025, 12, 15), series=ONE, client=s3)
    assert len(keys) == 2
    assert all(k.startswith("scratch/tester/raw/ecb/eur_series_daily/") for k in keys)


def test_run_refuses_empty_series(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(ecb, "fetch", lambda *_a, **_k: "")
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    with pytest.raises(ValueError, match="empty response"):
        ecb.run(dt.date(2025, 12, 15), series=ONE, client=s3)
