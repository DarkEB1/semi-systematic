"""quant.promote: schema contract on curated/, never overwrite, README copied next to the data."""

from __future__ import annotations

import datetime as dt

import pyarrow as pa
import pytest
import yaml

from quant import data, promote


def _good_table() -> pa.Table:
    schema = data.schema_from_readme("prices_daily")
    return pa.table(
        {
            "date": [dt.date(2026, 10, 1)],
            "symbol": ["USDBRL"],
            "open": [5.3],
            "high": [5.4],
            "low": [5.2],
            "close": [5.35],
            "volume": [0],
            "source": ["yahoo"],
            "ingested_at": [dt.datetime(2026, 10, 2, tzinfo=dt.UTC)],
        },
        schema=schema,
    )


def _request(tmp_path, scratch_key: str, snapshot: str = "2026-10-29"):
    p = tmp_path / "2026-10-29-prices_daily.yml"
    p.write_text(
        yaml.safe_dump(
            {
                "name": "prices_daily",
                "scratch_key": scratch_key,
                "snapshot": snapshot,
                "requested_by": "tester",
                "date": "2026-10-29",
            }
        )
    )
    return p


def test_promote_copies_data_and_readme(s3, user_cfg, promote_cfg, tmp_path):
    key = "scratch/tester/prices_daily/data.parquet"
    data.write_once(_good_table(), key, client=s3, cfg=user_cfg)
    written = promote.promote(_request(tmp_path, key), client=s3, cfg=promote_cfg)
    assert written == [
        "curated/prices_daily/snapshot=2026-10-29/data.parquet",
        "curated/prices_daily/snapshot=2026-10-29/README.md",
    ]
    assert b"## Schema" in s3.store[("test-bucket", written[1])]
    with pytest.raises(data.ExistsError):
        promote.promote(_request(tmp_path, key), client=s3, cfg=promote_cfg)


def test_promote_refuses_schema_drift(s3, user_cfg, promote_cfg, tmp_path):
    bad = _good_table().drop_columns(["volume"])
    key = "scratch/tester/prices_daily/bad.parquet"
    data.write_once(bad, key, client=s3, cfg=user_cfg)
    with pytest.raises(data.SchemaMismatch):
        promote.promote(_request(tmp_path, key), client=s3, cfg=promote_cfg)
    assert not any(k.startswith("curated/") for k in s3.puts)


def test_promote_requires_promote_role(s3, user_cfg, tmp_path):
    key = "scratch/tester/prices_daily/data.parquet"
    data.write_once(_good_table(), key, client=s3, cfg=user_cfg)
    with pytest.raises(data.PrefixError):
        promote.promote(_request(tmp_path, key), client=s3, cfg=user_cfg)


def test_request_validation(tmp_path):
    with pytest.raises(ValueError, match="scratch_key must be under"):
        promote.read_request(_request(tmp_path, "raw/x/y.parquet"))
    with pytest.raises(ValueError, match="snapshot must be"):
        promote.read_request(_request(tmp_path, "scratch/t/x.parquet", snapshot="20261029"))
