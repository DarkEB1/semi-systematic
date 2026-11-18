"""quant.ingest.cftc with the fixture in tests/fixtures (real TFF EUR and MXN rows, no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import _base, cftc

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "cftc_sample.json").read_text())
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)


def test_normalise_matches_schema():
    t = cftc.normalise(FIXTURE, ingested_at=STAMP)
    assert t.schema.equals(cftc.SCHEMA)
    assert t.num_rows == len(FIXTURE)
    assert set(t["symbol"].to_pylist()) == {"EUR", "MXN"}
    mxn = next(r for r in t.to_pylist() if r["symbol"] == "MXN")
    assert mxn["date"] == dt.date(2025, 12, 23)
    assert mxn["lev_money_long"] == 120475 and mxn["lev_money_short"] == 64964


def test_normalise_ignores_unknown_contracts():
    other = dict(FIXTURE[0], cftc_contract_market_code="999999")
    assert cftc.normalise([other]).num_rows == 0


def test_run_refuses_missing_contract(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(cftc, "fetch", lambda *_a, **_k: FIXTURE)  # only EUR and MXN
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    with pytest.raises(ValueError, match="empty response"):
        cftc.run(dt.date(2025, 12, 15), client=s3)


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(cftc, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(cftc, "CONTRACTS", {"099741": "EUR", "095741": "MXN"})
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = cftc.run(dt.date(2025, 12, 15), client=s3)
    assert len(keys) == 2
    assert all(k.startswith("scratch/tester/raw/cftc/tff_fx_weekly/") for k in keys)


def test_check_history_refuses_a_shorter_replacement(s3, ingest_cfg):
    table = cftc.normalise(FIXTURE, ingested_at=STAMP)
    _base.write_partitions(
        table, source="cftc", dataset="tff_fx_weekly", cadence="daily", client=s3, cfg=ingest_cfg
    )
    shorter = table.slice(1)
    with pytest.raises(ValueError, match="incomplete replacement"):
        _base.check_history(
            shorter,
            dt.date(2025, 12, 1),
            source="cftc",
            dataset="tff_fx_weekly",
            id_col="contract_code",
            client=s3,
            cfg=ingest_cfg,
        )
