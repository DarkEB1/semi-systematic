---
id: brl_series_daily
type: dataset
title: brl_series_daily
date: 2026-11-12
authors: [lucasvilliers]
owner: lucasvilliers
status: active
tags: [fx, macro, data]
datasets: [brl_series_daily]
---

# brl_series_daily

Banco Central do Brasil SGS series in long format: Selic target and effective rate, CDI and the
PTAX USD/BRL fixing, one row per series per day. The series are listed in
`catalog/reference/bcb_series.csv` (SGS `code` -> `symbol`). Raw lands under
`raw/bcb/brl_series_daily/year=YYYY/month=MM/`; curated snapshots under
`curated/brl_series_daily/snapshot=YYYY-MM-DD/` once promoted. Views: `bcb_brl_series_daily` (raw)
and `brl_series_daily` (curated).

## Source

- source: bcb
- url: https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json&dataInicial=dd/mm/yyyy&dataFinal=dd/mm/yyyy
- licence: Brazilian open-government data (Dados Abertos do Banco Central): free reuse with the source cited.

Fetched by `src/quant/ingest/bcb.py`. The API refuses daily windows longer than ten years, so the
ingest splits a request into windows of at most 3,600 days. It re-fetches every listed series from
the first day of the earliest affected month (default lookback 400 days; `--since` for a backfill)
and rewrites those monthly partitions whole. An empty series, or a replacement missing a stored
series/date row, is rejected before any write.

## Cadence

- cadence: daily
- lag_days: 3

Brazilian business days, except the Selic target (432) which has a row for every calendar day.
PTAX is set in the afternoon (Brasília time) and published the same day.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (Brasília) | Observation date |
| series_id | string | | `SGS<code>`, e.g. SGS432 |
| symbol | string | | Our symbol from bcb_series.csv, e.g. BR_SELIC, USDBRL_PTAX |
| value | float64 | per `units` in bcb_series.csv | Rates: percent per year; PTAX: BRL per USD |
| source | string | | Vendor name, constant `bcb` |
| ingested_at | timestamp[us, UTC] | | When the row was fetched |

## Known gaps

- Selic and CDI are annualised on a 252 business-day basis, not 360 or 365.
- PTAX is the selling rate of the official fixing; it differs from market closes.
- The SGS API is occasionally slow or returns HTTP 5xx; the ingest retries, then fails the whole run.

## Owner

lucasvilliers. Problems go to the data-health issue for this dataset.
