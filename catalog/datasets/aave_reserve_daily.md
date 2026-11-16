---
id: aave_reserve_daily
type: dataset
title: "aave_reserve_daily"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [data, data-quality, crypto]
datasets: [aave_reserve_daily]
---

# aave_reserve_daily

Bounded research acquisition; private scratch objects are not yet promoted. Raw view `aave_archive_aave_reserve_daily` is populated only after owner-approved integration and workflow ingestion.

## Source

- source: aave_archive (Ethereum mainnet, chain ID 1)
- url: https://eth-mainnet.g.alchemy.com/public
- licence: public blockchain state queried for internal research, subject to [RPC terms](https://legal.alchemy.com/); no proprietary vendor dataset mirrored.

[Source decision](../../knowledge/decisions/ADR-0010-defi-repo-research-sources.md). Aave [v2 ABI](https://github.com/aave/protocol-v2/blob/master/contracts/protocol/libraries/types/DataTypes.sol), [v3 ABI](https://github.com/aave/aave-v3-core/blob/master/contracts/protocol/libraries/types/DataTypes.sol), [address book](https://github.com/bgd-labs/aave-address-book), and [Chainlink interface](https://docs.chain.link/data-feeds/api-reference) define interpretation. Exact addresses and selector construction are in the ingest module. Normalized indices include protocol-accrued interest and applicable index distributions; do not assume external reward tokens are included.

Fetched by [the ingest module](../../src/quant/ingest/aave_archive.py). Local runs write only run-stamped scratch partitions. Default refresh rewrites whole monthly partitions in CI, never curated snapshots.

## Cadence

- cadence: daily
- lag_days: 1

UTC midnight state; seven days per week. Default refresh starts at the first day of the month containing seven days ago.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | UTC date | Midnight cutoff for Aave; effective date for NY Fed |
| symbol | string | identifier | DAI/USDC/USDT or SOFR/EFFR |
| protocol | string |  | protocol |
| block_number | int64 |  | block number |
| block_hash | string |  | block hash |
| block_time | timestamp[us, UTC] | UTC | Timestamp of final block at or before midnight |
| next_block_time | timestamp[us, UTC] | UTC | Next block timestamp, strictly after the cutoff |
| reserve_hex | string | ABI hex | Lossless getReserveData return, including configuration flags |
| income_index | string | ray integer string | Exact normalized supply index; divide only within a protocol |
| borrow_index | string | ray integer string | Exact normalized variable debt index |
| supply_apr_pct | float64 | percent per year | supply apr pct |
| borrow_apr_pct | float64 | percent per year | borrow apr pct |
| supply_tokens | float64 | tokens | supply tokens |
| variable_debt_tokens | float64 | tokens | variable debt tokens |
| stable_debt_tokens | float64 | tokens | stable debt tokens |
| available_tokens | float64 | tokens | available tokens |
| price_usd | float64 | USD per token | Chainlink reference mark, nullable before feed data exists; not executable |
| price_time | timestamp[us, UTC] | UTC | Last oracle update; inspect staleness |
| btc_usd | float64 |  | btc usd |
| eth_usd | float64 |  | eth usd |
| btc_price_time | timestamp[us, UTC] |  | btc price time |
| eth_price_time | timestamp[us, UTC] |  | eth price time |
| base_fee_gwei | float64 | gwei | Block base fee, null before EIP-1559; not a full transaction fee |
| source | string |  | source |
| ingested_at | timestamp[us, UTC] |  | ingested at |

## Known gaps

- Three selected stablecoins only. v2 until 2023-10-14, v3 thereafter, with both at the splice boundary; not a survivorship-free cross-protocol universe.
- No wallet histories, liquidation execution, intraday prices, exact transaction fees, bridge costs or executable off-chain funding quotes.
- Early USDC/USDT USD feeds have no observations; null is retained. No peg imputation. Chainlink marks can be stale and do not measure intraday depeg troughs.
- BTC/ETH and stablecoin feed answers use 8 decimals, verified against on-chain decimals calls in acquisition validation. Values are reference marks, not exchange closes.
- Base fees are absent before EIP-1559. No invented historical gas observations.
- Public RPC availability is not guaranteed. RPC errors abort acquisition; only a feed's explicit no-data result becomes a missing price.
- Exact indices are strings to avoid 64-bit overflow/float rounding. Token aggregates are floats and are not suitable for exact accounting reconciliation.
- Historical snapshots do not capture every operational constraint or action between daily cutoffs.

## Owner

DarkEB1. Schema changes and promotion require data-layer review. Acquisition manifests record exact object sizes and hashes; research remains draft while inputs are in scratch.
