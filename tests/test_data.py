"""quant.data: write policy, partition keys, schema contract."""

from __future__ import annotations

import datetime as dt

import pyarrow as pa
import pytest

from quant import data

TABLE = pa.table({"date": [dt.date(2026, 10, 1)], "symbol": ["USDBRL"], "close": [5.35]})


# --- write_once ---------------------------------------------------------------


def test_write_once_writes_then_refuses_on_exists(s3, user_cfg):
    key = "scratch/tester/demo/data.parquet"
    assert data.write_once(TABLE, key, client=s3, cfg=user_cfg) == key
    assert s3.puts == [key]
    with pytest.raises(data.ExistsError):
        data.write_once(TABLE, key, client=s3, cfg=user_cfg)
    assert s3.puts == [key], "second write must not reach the bucket"


def test_overwrite_allowed_only_under_raw(s3, ingest_cfg, user_cfg):
    raw_key = "raw/yahoo/prices_daily/year=2026/month=10/data.parquet"
    data.write_once(TABLE, raw_key, client=s3, cfg=ingest_cfg)
    data.write_once(
        TABLE, raw_key, overwrite=True, client=s3, cfg=ingest_cfg
    )  # fine: raw + ingest role
    assert s3.puts.count(raw_key) == 2
    with pytest.raises(ValueError, match="only for keys under 'raw/'"):
        data.write_once(TABLE, "scratch/tester/x.parquet", overwrite=True, client=s3, cfg=user_cfg)


def test_overwrite_under_curated_raises_even_for_promote_role(s3, promote_cfg):
    with pytest.raises(ValueError, match="only for keys under 'raw/'"):
        data.write_once(
            TABLE,
            "curated/prices_daily/snapshot=2026-10-29/data.parquet",
            overwrite=True,
            client=s3,
            cfg=promote_cfg,
        )


# --- prefix rules -------------------------------------------------------------


@pytest.mark.parametrize(
    "role,key",
    [
        ("user", "raw/yahoo/prices_daily/year=2026/month=10/data.parquet"),
        ("user", "curated/prices_daily/snapshot=2026-10-29/data.parquet"),
        ("user", "scratch/someone-else/x.parquet"),
        ("ingest", "curated/prices_daily/snapshot=2026-10-29/data.parquet"),
        ("ingest", "scratch/tester/x.parquet"),
        ("promote", "raw/yahoo/prices_daily/year=2026/month=10/data.parquet"),
    ],
)
def test_prefix_rules_refuse(s3, role, key):
    cfg = data.Settings("a", "https://e", "b", "k", "s", "tester", role)
    with pytest.raises(data.PrefixError):
        data.write_once(TABLE, key, client=s3, cfg=cfg)
    assert s3.puts == []


def test_allowed_prefix_per_role(user_cfg, ingest_cfg, promote_cfg):
    assert user_cfg.allowed_prefix == "scratch/tester/"
    assert ingest_cfg.allowed_prefix == "raw/"
    assert promote_cfg.allowed_prefix == "curated/"


def test_scratch_without_handle_is_refused(s3):
    cfg = data.Settings("a", "https://e", "b", "k", "s", "", "user")
    with pytest.raises(data.PrefixError, match="R2_HANDLE"):
        data.write_once(TABLE, "scratch/x/y.parquet", client=s3, cfg=cfg)


def test_bad_keys_rejected(s3, user_cfg):
    with pytest.raises(ValueError):
        data.check_write_allowed("/scratch/tester/x", cfg=user_cfg)
    with pytest.raises(ValueError):
        data.check_write_allowed("scratch/tester/../x", cfg=user_cfg)


# --- partitioning --------------------------------------------------------------


def test_partition_key_hive_style():
    assert (
        data.partition_key("prices_daily", year=2026, month=3) == "prices_daily/year=2026/month=03"
    )
    assert data.partition_key("ticks", date="2026-10-29") == "ticks/date=2026-10-29"
    assert (
        data.partition_key("prices_daily", snapshot="2026-10-29")
        == "prices_daily/snapshot=2026-10-29"
    )


def test_partition_parts_by_cadence():
    d = dt.date(2026, 10, 29)
    assert data.partition_parts("daily", d) == ({"year": 2026, "month": 10}, "data.parquet")
    assert data.partition_parts("intraday", d, asset_class="fx") == (
        {"date": "2026-10-29"},
        "fx.parquet",
    )
    assert data.partition_parts("snapshot", d) == ({"snapshot": "2026-10-29"}, "data.parquet")
    with pytest.raises(ValueError):
        data.partition_parts("intraday", d)
    with pytest.raises(ValueError):
        data.partition_parts("hourly", d)


# --- schema contract -----------------------------------------------------------


def test_schema_from_readme_prices_daily():
    schema = data.schema_from_readme("prices_daily")
    assert schema.names == [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "ingested_at",
    ]
    assert schema.field("date").type == pa.date32()
    assert schema.field("volume").type == pa.int64()
    assert schema.field("ingested_at").type == pa.timestamp("us", tz="UTC")
    assert schema.field("open").metadata[b"units"] == b"quote per base"


def test_validate_schema_accepts_matching_and_rejects_drift():
    schema = data.schema_from_readme("prices_daily")
    good = schema.empty_table()
    data.validate_schema(good, "prices_daily")
    drifted = good.drop_columns(["volume"]).append_column("vol", pa.array([], pa.int64()))
    with pytest.raises(data.SchemaMismatch, match="missing=\\['volume'\\]"):
        data.validate_schema(drifted, "prices_daily")
    retyped = good.set_column(
        good.schema.get_field_index("close"), "close", pa.array([], pa.float32())
    )
    with pytest.raises(data.SchemaMismatch, match="close: expected double"):
        data.validate_schema(retyped, "prices_daily")


def test_schema_from_readme_missing_dataset():
    with pytest.raises(FileNotFoundError):
        data.schema_from_readme("does_not_exist")


# --- helpers ---------------------------------------------------------------------


def test_read_back_and_list(s3, user_cfg):
    key = "scratch/tester/rb/data.parquet"
    data.write_once(TABLE, key, client=s3, cfg=user_cfg)
    assert data.read_parquet(key, client=s3, cfg=user_cfg).equals(TABLE)
    assert [o["Key"] for o in data.list_keys("scratch/tester/", client=s3, cfg=user_cfg)] == [key]
