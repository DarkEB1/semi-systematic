"""Pinned scratch inputs cannot silently substitute, change or bypass the schema."""

import hashlib

import pytest

from quant import data


def setup_input(s3, user_cfg, monkeypatch):
    table = data.schema_from_readme("prices_daily").empty_table()
    key = "scratch/tester/prices_daily/snapshot=2026-11-03/data.parquet"
    data.write_once(table, key, client=s3, cfg=user_cfg)
    digest = hashlib.sha256(s3.store[(user_cfg.bucket, key)]).hexdigest()
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    monkeypatch.setattr(data, "s3_client", lambda **_k: s3)
    return {"name": "prices_daily", "snapshot": "2026-11-03", "scratch_key": key, "sha256": digest}


def test_load_pin_and_duplicate_rejection(s3, user_cfg, monkeypatch):
    item = setup_input(s3, user_cfg, monkeypatch)
    assert data.load({"datasets": [item]})["prices_daily"].num_rows == 0
    with pytest.raises(ValueError, match="duplicate"):
        data.load({"datasets": [item, item]})
    item["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        data.load({"datasets": [item]})


@pytest.mark.parametrize(
    "key",
    [
        "curated/prices_daily/snapshot=2026-11-03/data.parquet",
        "scratch/tester/../prices_daily/snapshot=2026-11-03/data.parquet",
        "scratch/tester/prices_daily/snapshot=2026-11-02/data.parquet",
        "scratch/tester/prices_daily/snapshot=2026-11-03/*.parquet",
    ],
)
def test_invalid_location_fails(s3, user_cfg, monkeypatch, key):
    item = setup_input(s3, user_cfg, monkeypatch)
    item["scratch_key"] = key
    with pytest.raises(ValueError):
        data.load({"datasets": [item]})


def test_missing_digest_and_schema_drift(s3, user_cfg, monkeypatch):
    item = setup_input(s3, user_cfg, monkeypatch)
    del item["sha256"]
    with pytest.raises(ValueError, match="SHA-256"):
        data.load({"datasets": [item]})
    item = dict(
        item, sha256=hashlib.sha256(s3.store[(user_cfg.bucket, item["scratch_key"])]).hexdigest()
    )
    item["name"] = "usd_reference_rates"
    with pytest.raises(data.SchemaMismatch):
        data.load({"datasets": [item]})
