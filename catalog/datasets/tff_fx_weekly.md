---
id: tff_fx_weekly
type: dataset
title: tff_fx_weekly
date: 2026-11-12
authors: [lucasvilliers]
owner: lucasvilliers
status: active
tags: [fx, futures, data]
datasets: [tff_fx_weekly]
---

# tff_fx_weekly

CFTC Traders in Financial Futures (futures only) positions for the CME currency futures, one row
per contract per weekly report: open interest and the long and short positions of dealers, asset
managers and leveraged funds. The contracts are `CONTRACTS` in `src/quant/ingest/cftc.py` (EUR, JPY,
GBP, CAD, CHF, AUD, NZD, MXN, BRL, ZAR). Raw lands under `raw/cftc/tff_fx_weekly/year=YYYY/month=MM/`;
curated snapshots under `curated/tff_fx_weekly/snapshot=YYYY-MM-DD/` once promoted. Views:
`cftc_tff_fx_weekly` (raw) and `tff_fx_weekly` (curated).

## Source

- source: cftc
- url: https://publicreporting.cftc.gov/resource/gpe5-46if.json
- licence: US government public data (CFTC), no restriction on reuse.

Fetched by `src/quant/ingest/cftc.py` in one paged query. The ingest re-fetches every contract from
the first day of the earliest affected month (default lookback 400 days; `--since` for a backfill)
and rewrites those monthly partitions whole. From March 2022 on, a run where any contract is
missing is rejected, as is a replacement missing a stored contract/date row.

## Cadence

- cadence: weekly
- lag_days: 10

Positions are as of Tuesday and published the following Friday at 15:30 US Eastern (later after a
US holiday). Stored in the daily year/month layout; `date` is the Tuesday report date.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (US Eastern) | Report date (positions as of this Tuesday) |
| contract_code | string | | CFTC contract market code, e.g. 099741 |
| symbol | string | | Currency of the future, e.g. EUR, MXN |
| market_name | string | | CFTC market and exchange name as reported |
| open_interest | int64 | contracts | Open interest, all |
| dealer_long | int64 | contracts | Dealer/intermediary long |
| dealer_short | int64 | contracts | Dealer/intermediary short |
| asset_mgr_long | int64 | contracts | Asset manager/institutional long |
| asset_mgr_short | int64 | contracts | Asset manager/institutional short |
| lev_money_long | int64 | contracts | Leveraged funds long |
| lev_money_short | int64 | contracts | Leveraged funds short |
| source | string | | Vendor name, constant `cftc` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- TFF starts 2006-06-13; BRL from 2011-04-05; ZAR reports are sparse before February 2022.
- Positions are long the foreign currency against USD (CME convention), whatever the spot quote.
- Spread positions and the other-reportable and non-reportable categories are not stored.

## Owner

lucasvilliers. Problems go to the data-health issue for this dataset.
