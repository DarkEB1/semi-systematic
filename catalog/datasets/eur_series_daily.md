---
id: eur_series_daily
type: dataset
title: eur_series_daily
date: 2026-11-12
authors: [lucasvilliers]
owner: lucasvilliers
status: active
tags: [fx, macro, data]
datasets: [eur_series_daily]
---

# eur_series_daily

ECB euro reference FX rates and the euro short-term rate (ESTR) in long format, one row per series
per day. The series are listed in `catalog/reference/ecb_series.csv` (`flow` + `key` -> `symbol`).
Raw lands under `raw/ecb/eur_series_daily/year=YYYY/month=MM/`; curated snapshots under
`curated/eur_series_daily/snapshot=YYYY-MM-DD/` once promoted. Views: `ecb_eur_series_daily` (raw)
and `eur_series_daily` (curated).

## Source

- source: ecb
- url: https://data-api.ecb.europa.eu/service/data/<flow>/<key>?format=csvdata&detail=dataonly
- licence: ECB statistics reuse policy: free reuse, including commercial, with the source cited; the reference rates are for information purposes only.

Fetched by `src/quant/ingest/ecb.py`. The ingest re-fetches every listed series from the first day
of the earliest affected month (default lookback 400 days; `--since` for a backfill) and rewrites
those monthly partitions whole. An empty series, or a replacement missing a stored series/date row,
is rejected before any write.

## Cadence

- cadence: daily
- lag_days: 3

TARGET business days. The FX reference rates are set around 14:15 CET and published around 16:00
CET the same day; ESTR for a day is published at 08:00 CET the next TARGET day.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (CET) | Observation date |
| series_id | string | | `<flow>.<key>`, e.g. EXR.D.PLN.EUR.SP00.A |
| symbol | string | | Our symbol from ecb_series.csv, e.g. EURPLN, EUR_ESTR |
| value | float64 | per `units` in ecb_series.csv | FX: currency units per EUR; ESTR: percent |
| source | string | | Vendor name, constant `ecb` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- FX values are a single 14:15 CET fixing, not a close and not OHLC.
- No row on TARGET holidays (1 January, Good Friday, Easter Monday, 1 May, 25-26 December).
- ESTR starts 2019-10-01; most EXR series start 1999-01-04 (TRY, ZAR, BRL, MXN, INR, KRW and CNY later).
- TRY was redenominated in 2005: values before 2005 are in old lira per EUR.

## Owner

lucasvilliers. Problems go to the data-health issue for this dataset.
