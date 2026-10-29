---
id: prices_daily
type: dataset
title: prices_daily
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [fx, data]
datasets: [prices_daily]
---

# prices_daily

Daily OHLCV bars for the FX universe in `catalog/reference/universe.csv`. Raw lands under
`raw/yahoo/prices_daily/year=YYYY/month=MM/`; curated snapshots under `curated/prices_daily/snapshot=YYYY-MM-DD/`
once promoted. Views: `yahoo_prices_daily` (raw) and `prices_daily` (curated).

## Source

- source: yahoo
- url: https://query1.finance.yahoo.com/v8/finance/chart/<symbol>?interval=1d
- licence: free public endpoint, no key; terms allow personal and research use only

Fetched by `src/quant/ingest/yahoo.py` for each `yahoo_symbol` in the universe. The ingest
re-fetches from the first day of the earliest affected month and rewrites those monthly
partitions whole, so a partition is never half-updated.

## Cadence

- cadence: daily
- lag_days: 1

Business days. The nightly ingest runs at 01:30 UTC Tuesday to Saturday, so by Saturday morning the
dataset is expected through Friday. Weekend rows are absent, not null.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (UTC) | Bar date |
| symbol | string | | Universe symbol, e.g. USDBRL (not the vendor ticker) |
| open | float64 | quote per base | Open |
| high | float64 | quote per base | High |
| low | float64 | quote per base | Low |
| close | float64 | quote per base | Close |
| volume | int64 | contracts | Volume; Yahoo reports 0 for FX |
| source | string | | Vendor name, constant `yahoo` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- Yahoo occasionally repeats the live bar for the current day; the ingest keeps the first occurrence.
- Volume is meaningless for FX from this source.
- No history before 2003 for most EM pairs.
- Holidays differ by currency; a missing day is not necessarily a gap (see conventions.md, calendars).

## Owner

DarkEB1. Questions and gap reports go to the data-health issue for this dataset.
