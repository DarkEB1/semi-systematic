"""Block-pinned Ethereum Aave reserve state; no transactions or wallet histories."""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pyarrow as pa

from quant.ingest import _base

SOURCE = "aave_archive"
DATASETS = ("aave_reserve_daily",)
CADENCE = "daily"
RPC_URL = "https://eth-mainnet.g.alchemy.com/public"
POOLS = {
    "v2": "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9",
    "v3": "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
}
ASSETS = {
    "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
}
FEEDS = {
    "DAI": "0xaed0c38402a5d19df6e4c03f4e2dced6e29c1ee9",
    "USDC": "0x8fffffd4afb6115b954bd326cbe7b4ba576818f6",
    "USDT": "0x3e7d1eab13ad0104d2750b8863b489d65364e32d",
    "BTC": "0xf4030086522a5beea4988f8ca5b36dbc97bee88c",
    "ETH": "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",
}
SWITCH = dt.date(2023, 10, 15)
SCHEMA = pa.schema(
    [
        ("date", pa.date32()),
        ("symbol", pa.string()),
        ("protocol", pa.string()),
        ("block_number", pa.int64()),
        ("block_hash", pa.string()),
        ("block_time", pa.timestamp("us", tz="UTC")),
        ("next_block_time", pa.timestamp("us", tz="UTC")),
        ("reserve_hex", pa.string()),
        ("income_index", pa.string()),
        ("borrow_index", pa.string()),
        ("supply_apr_pct", pa.float64()),
        ("borrow_apr_pct", pa.float64()),
        ("supply_tokens", pa.float64()),
        ("variable_debt_tokens", pa.float64()),
        ("stable_debt_tokens", pa.float64()),
        ("available_tokens", pa.float64()),
        ("price_usd", pa.float64()),
        ("price_time", pa.timestamp("us", tz="UTC")),
        ("btc_usd", pa.float64()),
        ("eth_usd", pa.float64()),
        ("btc_price_time", pa.timestamp("us", tz="UTC")),
        ("eth_price_time", pa.timestamp("us", tz="UTC")),
        ("base_fee_gwei", pa.float64()),
        ("source", pa.string()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def rpc_results(result: Any, count: int, *, allow_no_data: bool = False) -> list[Any]:
    """Fail on partial, duplicate, missing or erroneous batch responses."""
    if not isinstance(result, list) or len(result) != count:
        raise RuntimeError(f"incomplete RPC batch: {str(result)[:200]}")
    by_id = {row["id"]: row for row in result}
    if set(by_id) != set(range(count)):
        raise RuntimeError("RPC response IDs mismatch")
    for row in by_id.values():
        if (
            allow_no_data
            and row.get("error", {}).get("message") == "execution reverted: No data present"
        ):
            row.pop("error")
            row["result"] = "no_data"
        if "error" in row or row.get("result") is None:
            raise RuntimeError(str(row))
    return [by_id[i]["result"] for i in range(count)]


def rpc(
    calls: list[tuple[str, list[Any]]], url: str = RPC_URL, *, allow_no_data: bool = False
) -> list[Any]:
    """Bounded retries; validate IDs, including reordered batches."""
    payload = [
        {"jsonrpc": "2.0", "id": i, "method": method, "params": args}
        for i, (method, args) in enumerate(calls)
    ]
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "semi-systematic-research/0.1"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.load(response)
            return rpc_results(result, len(calls), allow_no_data=allow_no_data)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            if attempt == 3:
                raise RuntimeError(f"archive RPC failed: {error}") from error
            time.sleep(10 * 2**attempt)
    raise AssertionError("unreachable")


def words(value: str) -> list[int]:
    """Decode static ABI words without truncation or float conversion."""
    if not value.startswith("0x") or len(value[2:]) % 64 or len(value) <= 2:
        raise ValueError("invalid static ABI return")
    return [int(value[i : i + 64], 16) for i in range(2, len(value), 64)]


def call(address: str, selector: str, block: int, argument: str = "") -> tuple[str, list[Any]]:
    return "eth_call", [{"to": address, "data": selector + argument}, hex(block)]


def aggregate(calls: list[tuple[str, list[Any]]], url: str) -> list[str]:
    """Use the historical Multicall deployment to reduce public RPC compute-unit usage."""
    block = calls[0][1][1]
    chunks, offsets, offset = [], [], 32 * len(calls)
    for method, params in calls:
        if method != "eth_call" or params[1] != block:
            raise ValueError("aggregate requires view calls at one block")
        payload = params[0]["data"][2:]
        chunk = params[0]["to"][2:].zfill(64) + format(64, "064x")
        chunk += format(len(payload) // 2, "064x") + payload.ljust(
            (len(payload) + 63) // 64 * 64, "0"
        )
        offsets.append(format(offset, "064x"))
        chunks.append(chunk)
        offset += len(chunk) // 2
    encoded = format(32, "064x") + format(len(calls), "064x") + "".join(offsets + chunks)
    result = rpc(
        [call("0xeefba1e63905ef1d7acba5a8513c70307c1ce441", "0x252dba42", int(block, 16), encoded)],
        url,
    )[0]
    blob = bytes.fromhex(result[2:])
    number = int.from_bytes(blob[:32])
    start = int.from_bytes(blob[32:64])
    count = int.from_bytes(blob[start : start + 32])
    if number != int(block, 16) or count != len(calls):
        raise ValueError("multicall block/count mismatch")
    output = []
    for i in range(count):
        pos = start + 32 + int.from_bytes(blob[start + 32 * (i + 1) : start + 32 * (i + 2)])
        size = int.from_bytes(blob[pos : pos + 32])
        if pos + 32 + size > len(blob):
            raise ValueError("truncated multicall return")
        output.append("0x" + blob[pos + 32 : pos + 32 + size].hex())
    return output


def block_at(timestamp: int, url: str = RPC_URL) -> tuple[dict[str, Any], dict[str, Any]]:
    """Last block at or before cutoff, with the next block proving the bracket."""
    low, high = rpc(
        [
            ("eth_getBlockByNumber", [hex(11500000), False]),
            ("eth_getBlockByNumber", ["finalized", False]),
        ],
        url,
    )
    if not int(low["timestamp"], 16) <= timestamp < int(high["timestamp"], 16):
        raise ValueError("cutoff outside available finalized history")
    for _ in range(40):
        lo, hi = int(low["number"], 16), int(high["number"], 16)
        if hi - lo == 1:
            return low, high
        lt, ht = int(low["timestamp"], 16), int(high["timestamp"], 16)
        guess = max(lo + 1, min(hi - 1, lo + (timestamp - lt) * (hi - lo) // (ht - lt)))
        middle = rpc([("eth_getBlockByNumber", [hex(guess), False])], url)[0]
        if int(middle["timestamp"], 16) <= timestamp:
            low = middle
        else:
            high = middle
    raise RuntimeError("block search did not converge")


def selectors(url: str = RPC_URL) -> tuple[str, str]:
    names = ("getReserveNormalizedIncome(address)", "getReserveNormalizedVariableDebt(address)")
    hashes = rpc([("web3_sha3", ["0x" + name.encode().hex()]) for name in names], url)
    return hashes[0][:10], hashes[1][:10]


def fetch_day(day: dt.date, selected: tuple[str, str], url: str = RPC_URL) -> dict[str, Any]:
    """Three reserves; include both protocols on the switch boundary."""
    timestamp = int(dt.datetime.combine(day, dt.time(), dt.UTC).timestamp())
    block, following = block_at(timestamp, url)
    number = int(block["number"], 16)
    versions = ["v2"] if day < SWITCH else ["v3"]
    if day in {SWITCH - dt.timedelta(days=1), SWITCH}:
        versions = ["v2", "v3"]
    identities = [(v, symbol) for v in versions for symbol in ASSETS]
    requests: list[tuple[str, list[Any]]] = []
    for version, symbol in identities:
        arg = ASSETS[symbol][2:].zfill(64)
        requests.extend(
            call(POOLS[version], selector, number, arg) for selector in ("0x35ea6a75", *selected)
        )
    returns = aggregate(requests, url)
    reserves: list[dict[str, Any]] = []
    requests = []
    for i, (version, symbol) in enumerate(identities):
        raw, income, borrow = returns[3 * i : 3 * i + 3]
        fields = words(raw)
        offset = 7 if version == "v2" else 8
        tokens = ["0x" + format(n, "040x") for n in fields[offset : offset + 3]]
        reserves.append(
            {
                "symbol": symbol,
                "protocol": version,
                "reserve_hex": raw,
                "income_index": str(words(income)[0]),
                "borrow_index": str(words(borrow)[0]),
            }
        )
        requests.extend(call(token, "0x18160ddd", number) for token in tokens)
        requests.append(call(ASSETS[symbol], "0x70a08231", number, tokens[0][2:].zfill(64)))
    balances = aggregate(requests, url)
    for i, reserve in enumerate(reserves):
        values = balances[4 * i : 4 * i + 4]
        # V3.2 removed stable debt: the legacy getter returns address(0).
        if reserve["protocol"] == "v3" and words(reserve["reserve_hex"])[9] == 0:
            if values[1] != "0x":
                raise ValueError("unexpected return from deprecated stable debt address")
            values[1] = "0x" + "0" * 64
        reserve["balances"] = [str(words(value)[0]) for value in values]
    feeds = rpc(
        [call(address, "0xfeaf968c", number) for address in FEEDS.values()], url, allow_no_data=True
    )
    return {
        "date": day.isoformat(),
        "block": block,
        "next_timestamp": following["timestamp"],
        "reserves": reserves,
        "feeds": dict(zip(FEEDS, feeds, strict=True)),
    }


def fetch(
    since: dt.date,
    until: dt.date | None = None,
    *,
    checkpoint: Path | None = None,
    url: str = RPC_URL,
) -> list[dict[str, Any]]:
    """Bounded range, four workers, daily restart checkpoints, no server writes."""
    until = until or (dt.date.today() - dt.timedelta(days=1))
    if since < dt.date(2021, 1, 1) or since > until or (until - since).days > 2200:
        raise ValueError("archive range must be ordered, start in 2021+, and span <=2200 days")
    selected = selectors(url)
    days = [since + dt.timedelta(days=i) for i in range((until - since).days + 1)]
    if checkpoint:
        checkpoint.mkdir(parents=True, exist_ok=True)

    def get_day(day: dt.date) -> dict[str, Any]:
        path = checkpoint / f"{day}.json" if checkpoint else None
        if path and path.exists():
            return json.loads(path.read_text())
        row = fetch_day(day, selected, url)
        row["block"] = {
            k: v
            for k, v in row["block"].items()
            if k in {"number", "hash", "timestamp", "baseFeePerGas"}
        }
        if path:
            path.write_text(json.dumps(row))
        time.sleep(0.75)
        return row

    result = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for i, row in enumerate(executor.map(get_day, days)):
            result.append(row)
            if (i + 1) % 30 == 0:
                print(f"archive: {i + 1}/{len(days)} daily cutoffs", flush=True)
    return result


def oracle(value: str, block_time: int) -> tuple[float | None, dt.datetime | None]:
    if value in {"0x", "no_data"}:
        return None, None  # Feed not yet deployed; never manufacture a $1 mark.
    values = words(value)
    if len(values) != 5 or not 0 < values[1] < 2**255 or not 0 < values[3] <= block_time:
        raise ValueError("invalid Chainlink round")
    return values[1] / 1e8, dt.datetime.fromtimestamp(values[3], dt.UTC)


def reserve_row(
    reserve: dict[str, Any], prices: dict[str, tuple[float | None, dt.datetime | None]]
) -> dict[str, Any]:
    fields = words(reserve["reserve_hex"])
    version, symbol = reserve["protocol"], reserve["symbol"]
    if len(fields) != (12 if version == "v2" else 15):
        raise ValueError("unexpected reserve ABI layout")
    decimals = (fields[0] >> 48) & 255
    if decimals != (18 if symbol == "DAI" else 6):
        raise ValueError("unexpected reserve token decimals")
    if min(int(reserve[k]) for k in ("income_index", "borrow_index")) < 10**27:
        raise ValueError("invalid normalized index")
    supply, stable, variable, available = [int(n) / 10**decimals for n in reserve["balances"]]
    return {
        "symbol": symbol,
        "protocol": version,
        "reserve_hex": reserve["reserve_hex"],
        "income_index": reserve["income_index"],
        "borrow_index": reserve["borrow_index"],
        "supply_apr_pct": fields[3 if version == "v2" else 2] / 1e25,
        "borrow_apr_pct": fields[4] / 1e25,
        "supply_tokens": supply,
        "stable_debt_tokens": stable,
        "variable_debt_tokens": variable,
        "available_tokens": available,
        "price_usd": prices[symbol][0],
        "price_time": prices[symbol][1],
        "btc_usd": prices["BTC"][0],
        "eth_usd": prices["ETH"][0],
        "btc_price_time": prices["BTC"][1],
        "eth_price_time": prices["ETH"][1],
    }


def normalise(payload: list[dict[str, Any]], *, ingested_at: dt.datetime | None = None) -> pa.Table:
    """Retain exact indices, block provenance, oracle times and reserve configuration."""
    stamp = ingested_at or dt.datetime.now(dt.UTC)
    rows = []
    for item in payload:
        block = item["block"]
        bt, nt = int(block["timestamp"], 16), int(item["next_timestamp"], 16)
        day = dt.date.fromisoformat(item["date"])
        cutoff = int(dt.datetime.combine(day, dt.time(), dt.UTC).timestamp())
        if not bt <= cutoff < nt or cutoff - bt > 120:
            raise ValueError("daily block bracket invalid or excessively stale")
        prices = {key: oracle(value, bt) for key, value in item["feeds"].items()}
        for reserve in item["reserves"]:
            row = reserve_row(reserve, prices)
            row.update(
                date=day,
                block_number=int(block["number"], 16),
                block_hash=block["hash"],
                block_time=dt.datetime.fromtimestamp(bt, dt.UTC),
                next_block_time=dt.datetime.fromtimestamp(nt, dt.UTC),
                base_fee_gwei=int(block["baseFeePerGas"], 16) / 1e9
                if "baseFeePerGas" in block
                else None,
                source=SOURCE,
                ingested_at=stamp,
            )
            rows.append(row)
    keys = {(r["date"], r["protocol"], r["symbol"]) for r in rows}
    if len(keys) != len(rows):
        raise ValueError("duplicate reserve cutoff")
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def run(since: dt.date | None = None, *, dry_run: bool = False, client: Any = None) -> list[str]:
    since = (since or (dt.date.today() - dt.timedelta(days=7))).replace(day=1)
    table = normalise(fetch(since))
    return _base.write_partitions(
        table, source=SOURCE, dataset=DATASETS[0], cadence=CADENCE, dry_run=dry_run, client=client
    )
