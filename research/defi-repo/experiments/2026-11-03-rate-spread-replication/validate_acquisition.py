"""Rebuild tables from checkpoints and cross-check an independent node before upload."""

import datetime as dt
import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq

from quant import data
from quant.ingest import aave_archive as aave
from quant.ingest import nyfed

HERE = Path(__file__).resolve().parent
CHECK_DATES = ["2021-01-03", "2023-03-12", "2023-10-15", "2024-10-09", "2025-01-01", "2026-01-30"]
SECOND_RPC = "https://eth.drpc.org"


def independent_calls(requests, *, allow_no_data=False):
    # Public dRPC rejects some larger archive batches; use bounded individual requests.
    def one(request):
        method, params = request
        body = json.dumps(dict(jsonrpc="2.0", id=0, method=method, params=params)).encode()
        req = urllib.request.Request(
            SECOND_RPC,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "semi-systematic-research/0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.load(response)
        return aave.rpc_results([result], 1, allow_no_data=allow_no_data)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(one, requests))


def independent_checks(out):
    checks = []
    assert independent_calls([("eth_chainId", [])]) == ["0x1"]
    for day in CHECK_DATES:
        print(f"independent check: {day}", flush=True)
        sample = json.loads((out / "archive" / f"{day}.json").read_text())
        block = int(sample["block"]["number"], 16)
        header = independent_calls([("eth_getBlockByNumber", [hex(block), False])])[0]
        assert header["hash"] == sample["block"]["hash"]
        requests, expected = [], []
        for reserve in sample["reserves"]:
            address = aave.POOLS[reserve["protocol"]]
            argument = aave.ASSETS[reserve["symbol"]][2:].zfill(64)
            requests.extend(
                aave.call(address, selector, block, argument)
                for selector in ("0x35ea6a75", "0xd15e0053", "0x386497fd")
            )
            expected.extend(
                [
                    reserve["reserve_hex"],
                    "0x" + format(int(reserve["income_index"]), "064x"),
                    "0x" + format(int(reserve["borrow_index"]), "064x"),
                ]
            )
        assert independent_calls(requests) == expected
        balance_calls, balance_expected = [], []
        for reserve in sample["reserves"]:
            offset = 7 if reserve["protocol"] == "v2" else 8
            tokens = aave.words(reserve["reserve_hex"])[offset : offset + 3]
            for token, value in zip(tokens, reserve["balances"][:3], strict=True):
                if token == 0:
                    assert value == "0"
                    continue
                balance_calls.append(aave.call("0x" + format(token, "040x"), "0x18160ddd", block))
                balance_expected.append(int(value))
            balance_calls.append(
                aave.call(
                    aave.ASSETS[reserve["symbol"]], "0x70a08231", block, format(tokens[0], "064x")
                )
            )
            balance_expected.append(int(reserve["balances"][3]))
        assert [aave.words(v)[0] for v in independent_calls(balance_calls)] == balance_expected
        feeds = independent_calls(
            [aave.call(address, "0xfeaf968c", block) for address in aave.FEEDS.values()],
            allow_no_data=True,
        )
        assert feeds == list(sample["feeds"].values())
        checks.append(
            {
                "date": day,
                "block": block,
                "block_hash_agrees": True,
                "reserve_and_index_calls_agree": len(expected),
            }
        )
    decimals = independent_calls(
        [aave.call(address, "0x313ce567", block) for address in aave.FEEDS.values()]
    )
    assert [aave.words(v)[0] for v in decimals] == [8] * len(aave.FEEDS)
    return checks


def main():
    out = HERE / "outputs"
    start, end = dt.date(2021, 1, 3), dt.date(2026, 1, 31)
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    payload = [json.loads((out / "archive" / f"{day}.json").read_text()) for day in days]
    tables = {
        "aave_reserve_daily": aave.normalise(payload),
        "usd_reference_rates": nyfed.normalise(
            json.loads((out / "nyfed-response.json").read_text())
        ),
    }
    assert tables["aave_reserve_daily"].num_rows == len(days) * 3 + 6
    manifest = {
        "acquired_at": dt.datetime.now(dt.UTC).isoformat(),
        "onchain_source": aave.RPC_URL,
        "offchain_source": nyfed.ENDPOINT,
        "independent_rpc": SECOND_RPC,
        "checks": independent_checks(out),
        "feed_decimals_verified": 8,
        "datasets": [],
    }
    for name, table in tables.items():
        data.validate_schema(table, name)
        path = out / f"{name}.parquet"
        pq.write_table(table, path, compression="zstd")
        body = path.read_bytes()
        manifest["datasets"].append(
            {
                "name": name,
                "rows": table.num_rows,
                "bytes": len(body),
                "local_sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    manifest["total_bytes"] = sum(row["bytes"] for row in manifest["datasets"])
    assert manifest["total_bytes"] < 10_000_000, "review storage footprint before upload"
    (out / "acquisition-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
