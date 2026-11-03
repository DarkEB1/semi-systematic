"""Official reference-rate fixture; no network or calendar filling."""

import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import nyfed

FIXTURE = json.loads((Path(__file__).parent / "fixtures/nyfed_sample.json").read_text())


def test_normalise_preserves_effective_date_and_rate():
    table = nyfed.normalise(FIXTURE)
    data.validate_schema(table, nyfed.DATASETS[0])
    assert table.num_rows == 2
    rows = {r["symbol"]: r for r in table.to_pylist()}
    for original in FIXTURE:
        row = rows[original["type"]]
        assert row["date"] == dt.date.fromisoformat(original["effectiveDate"])
        assert row["rate_pct"] == original["percentRate"]


def test_duplicate_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        nyfed.normalise(FIXTURE + FIXTURE)


def test_run_writes_scratch_for_user_role(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(nyfed, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = nyfed.run(dt.date(2026, 1, 1), client=s3)
    assert keys and all(k.startswith("scratch/tester/raw/nyfed/") for k in keys)
