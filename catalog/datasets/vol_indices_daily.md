---
id: vol_indices_daily
type: dataset
title: vol_indices_daily
date: 2026-11-12
authors: [lucasvilliers]
owner: lucasvilliers
status: active
tags: [options, data]
datasets: [vol_indices_daily]
---

# vol_indices_daily

Cboe volatility indices, one row per index per day: VIX (S&P 500), VXEEM (EM equities ETF EEM),
OVX (oil ETF USO) and GVZ (gold ETF GLD). The list is `INDICES` in `src/quant/ingest/cboe.py`.
Raw lands under `raw/cboe/vol_indices_daily/year=YYYY/month=MM/`; curated snapshots under
`curated/vol_indices_daily/snapshot=YYYY-MM-DD/` once promoted. Views: `cboe_vol_indices_daily`
(raw) and `vol_indices_daily` (curated).

## Source

- source: cboe
- url: https://cdn.cboe.com/api/global/us_indices/daily_prices/<INDEX>_History.csv
- licence: Cboe public historical index data, free download; research and internal use. VIX is a Cboe trademark; redistribution of the data as a product needs a Cboe licence.

Fetched by `src/quant/ingest/cboe.py`. Each file holds the full history and is downloaded whole;
the ingest keeps rows from the first day of the earliest affected month (default lookback 400
days; `--since` for a backfill) and rewrites those monthly partitions whole. An empty index, or a
replacement missing a stored symbol/date row, is rejected before any write.

## Cadence

- cadence: daily
- lag_days: 3

US equity trading days; the files are updated after the close.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (US Eastern) | Trading day |
| symbol | string | | Index, e.g. VIX, VXEEM |
| open | float64 | annualised vol points | Open; null for OVX and GVZ |
| high | float64 | annualised vol points | High; null for OVX and GVZ |
| low | float64 | annualised vol points | Low; null for OVX and GVZ |
| close | float64 | annualised vol points | Close |
| source | string | | Vendor name, constant `cboe` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- OVX and GVZ files carry a close only.
- VIX from 1990-01-02, VXEEM from 2011-03-16, OVX and GVZ from 2009-09-18.
- Implied vol of equity ETFs (VXEEM) is a risk-sentiment proxy, not FX implied vol.

## Owner

lucasvilliers. Problems go to the data-health issue for this dataset.
