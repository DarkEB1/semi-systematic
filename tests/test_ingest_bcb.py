"""quant.ingest.bcb with the fixture in tests/fixtures (a real SGS 1 PTAX response, no network)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import bcb

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "bcb_sample.json").read_text())
STAMP = dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.UTC)
ONE = [{"code": "1", "symbol": "USDBRL_PTAX"}]


def test_normalise_matches_schema_and_parses_brazilian_dates():
    t = bcb.normalise(FIXTURE, "SGS1", "USDBRL_PTAX", ingested_at=STAMP)
    assert t.schema.equals(bcb.SCHEMA)
    assert t.num_rows == 5
    assert t["date"].to_pylist()[0] == dt.date(2025, 12, 29)
    assert t["value"].to_pylist()[0] == pytest.approx(5.5739)


def test_windows_never_exceed_ten_years_and_cover_the_range():
    w = bcb.windows(dt.date(2003, 1, 1), dt.date(2026, 11, 12))
    assert w[0][0] == dt.date(2003, 1, 1) and w[-1][1] == dt.date(2026, 11, 12)
    assert all((end - start).days < bcb.MAX_WINDOW_DAYS for start, end in w)
    assert all(w[i][1] + dt.timedelta(days=1) == w[i + 1][0] for i in range(len(w) - 1))


def test_fetch_joins_windows(monkeypatch):
    calls = []
    monkeypatch.setattr(bcb, "_get", lambda url, _r: calls.append(url) or FIXTURE[:1])
    out = bcb.fetch("432", dt.date(2003, 1, 1), dt.date(2026, 1, 1))
    assert len(calls) == len(bcb.windows(dt.date(2003, 1, 1), dt.date(2026, 1, 1))) == len(out)


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(bcb, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = bcb.run(dt.date(2025, 12, 15), series=ONE, client=s3)
    assert len(keys) == 2
    assert all(k.startswith("scratch/tester/raw/bcb/brl_series_daily/") for k in keys)


def test_run_refuses_empty_series(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(bcb, "fetch", lambda *_a, **_k: [])
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    with pytest.raises(ValueError, match="empty response"):
        bcb.run(dt.date(2025, 12, 15), series=ONE, client=s3)
