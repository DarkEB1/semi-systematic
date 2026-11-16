"""Offline contract decoding, incomplete-response and scratch-write checks."""

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from quant import data
from quant.ingest import aave_archive as source

FIXTURE = json.loads((Path(__file__).parent / "fixtures/aave_archive_sample.json").read_text())
STAMP = dt.datetime(2026, 11, 3, tzinfo=dt.UTC)


def test_real_historical_reserves_and_missing_feed():
    table = source.normalise(FIXTURE, ingested_at=STAMP)
    data.validate_schema(table, source.DATASETS[0])
    assert table.num_rows == 12
    rows = table.to_pylist()
    assert rows[1]["price_usd"] is None
    stress = next(r for r in rows if r["date"] == dt.date(2023, 3, 12) and r["symbol"] == "USDT")
    assert stress["supply_apr_pct"] == pytest.approx(56.41535291353616)
    assert stress["price_usd"] == pytest.approx(1.009)
    assert int(stress["income_index"]) > 10**27
    v3 = next(r for r in rows if r["date"] == dt.date(2025, 1, 1) and r["symbol"] == "USDC")
    assert v3["supply_apr_pct"] == pytest.approx(9.165077337242561)
    assert v3["protocol"] == "v3"


def test_wrong_block_bracket_and_duplicates_fail():
    bad = copy.deepcopy(FIXTURE)
    bad[0]["next_timestamp"] = bad[0]["block"]["timestamp"]
    with pytest.raises(ValueError, match="bracket"):
        source.normalise(bad)
    with pytest.raises(ValueError, match="duplicate"):
        source.normalise(FIXTURE + FIXTURE)


def test_batch_order_and_fail_closed():
    assert source.rpc_results([{"id": 1, "result": "b"}, {"id": 0, "result": "a"}], 2) == ["a", "b"]
    for rows in [
        [{"id": 0, "result": "a"}],
        [{"id": 0, "result": "a"}, {"id": 0, "result": "b"}],
        [{"id": 0, "result": "a"}, {"id": 1, "error": {"message": "execution reverted"}}],
    ]:
        with pytest.raises(RuntimeError):
            source.rpc_results(rows, 2)
    no_data = [{"id": 0, "error": {"message": "execution reverted: No data present"}}]
    with pytest.raises(RuntimeError):
        source.rpc_results(copy.deepcopy(no_data), 1)
    assert source.rpc_results(no_data, 1, allow_no_data=True) == ["no_data"]


def test_oracle_no_peg_imputation_and_future_timestamp():
    assert source.oracle("0x", 1) == (None, None)
    assert source.oracle("no_data", 1) == (None, None)
    with pytest.raises(ValueError, match="round"):
        source.oracle(FIXTURE[1]["feeds"]["USDC"], 1)


def test_unknown_abi_and_precision_fail():
    bad = copy.deepcopy(FIXTURE)
    bad[0]["reserves"][0]["reserve_hex"] += "0" * 64
    with pytest.raises(ValueError, match="ABI"):
        source.normalise(bad)


def test_run_writes_only_scratch(s3, user_cfg, monkeypatch):
    monkeypatch.setattr(source, "fetch", lambda *_a, **_k: FIXTURE)
    monkeypatch.setattr(data, "settings", lambda **_k: user_cfg)
    keys = source.run(dt.date(2021, 1, 1), client=s3)
    assert keys and all(k.startswith("scratch/tester/raw/aave_archive/") for k in keys)


def test_deprecated_stable_debt_is_zero_only_for_zero_address(monkeypatch):
    sample = copy.deepcopy(next(r for r in FIXTURE if r["date"] == "2025-01-01"))
    # Synthetic zero-address legacy field, as returned during the V3.2 upgrade.
    for reserve in sample["reserves"]:
        raw = reserve["reserve_hex"]
        reserve["reserve_hex"] = raw[: 2 + 9 * 64] + "0" * 64 + raw[2 + 10 * 64 :]
    reserves = sample["reserves"]
    assert all(source.words(r["reserve_hex"])[9] == 0 for r in reserves)
    monkeypatch.setattr(
        source, "block_at", lambda *_a: (sample["block"], {"timestamp": sample["next_timestamp"]})
    )
    returns = [
        v
        for r in reserves
        for v in [
            r["reserve_hex"],
            "0x" + format(int(r["income_index"]), "064x"),
            "0x" + format(int(r["borrow_index"]), "064x"),
        ]
    ]
    balances = [
        "0x" if j == 1 else "0x" + format(int(v), "064x")
        for r in reserves
        for j, v in enumerate(r["balances"])
    ]
    responses = iter([returns, balances])
    monkeypatch.setattr(source, "aggregate", lambda *_a: next(responses))
    monkeypatch.setattr(source, "rpc", lambda *_a, **_k: list(sample["feeds"].values()))
    row = source.fetch_day(dt.date(2025, 1, 1), ("0xd15e0053", "0x386497fd"))
    assert all(r["balances"][1] == "0" for r in row["reserves"])
    with pytest.raises(ValueError, match="ABI"):
        source.words("0x")
