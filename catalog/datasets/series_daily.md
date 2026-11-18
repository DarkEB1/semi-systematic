---
id: series_daily
type: dataset
title: series_daily
date: 2026-11-12
authors: [lucasvilliers]
owner: lucasvilliers
status: active
tags: [fx, macro, data]
datasets: [series_daily]
---

# series_daily

Daily FRED series in long format: H.10 FX fixings, US short rates and the Fed's dollar indices,
one row per series per day. The series are listed in `catalog/reference/fred_series.csv`
(`series_id` -> `symbol`, `kind`, `units`). Raw lands under `raw/fred/series_daily/year=YYYY/month=MM/`;
curated snapshots under `curated/series_daily/snapshot=YYYY-MM-DD/` once promoted. Views:
`fred_series_daily` (raw) and `series_daily` (curated).

## Source

- source: fred
- url: https://api.stlouisfed.org/fred/series/observations?series_id=<id>&file_type=json
- licence: FRED API terms of use; the listed series are Federal Reserve Board (H.10, dollar indices, Treasury) and NY Fed (SOFR) public data. Check a series' notes for third-party copyright before adding it.

Fetched by `src/quant/ingest/fred.py` with the key in `FRED_API_KEY`. The ingest re-fetches every
listed series from the first day of the earliest affected month (default lookback 400 days;
`--since` for a backfill) and rewrites those monthly partitions whole. An empty response for any
series, or a replacement missing a stored series/date row, is rejected before any write.

## Cadence

- cadence: daily
- lag_days: 3

Business days. Rates (DTB3, DGS3MO, SOFR, DFF) are usually available the next business day. The
H.10 FX fixings and dollar indices are released weekly (Monday, for the previous week), so they run
up to about ten days behind the rates; data-health only checks the most current series.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (UTC) | Observation date |
| series_id | string | | FRED series id, e.g. DEXUSEU |
| symbol | string | | Our symbol from fred_series.csv, e.g. EURUSD, US_SOFR |
| value | float64 | per `units` in fred_series.csv | FX: quote per base as named by symbol; rates: percent; indices: Jan 2006=100 |
| source | string | | Vendor name, constant `fred` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- FX values are New York noon buying rates (a single fixing), not OHLC; they differ slightly from Yahoo closes.
- US holidays have no row (FRED reports `"."`, dropped at ingest), including for non-US currencies.
- DFF has a row for every calendar day, weekends included.
- SOFR starts 2018-04-03; dollar indices start 2006-01-02.

## Owner

lucasvilliers. Problems go to the data-health issue for this dataset.
