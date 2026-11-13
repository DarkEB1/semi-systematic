---
id: vendors
type: context
title: "Vendors and data sources"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [vendor, data, costs]
related: [universe]
---

# Vendors and data sources

TODO: add the paid vendor we settle on, its licence terms, cost and the `VENDOR_API_KEY` scope.

## In use

- Yahoo Finance chart endpoint (free, no key): daily OHLCV for the FX universe, dataset
  [prices_daily](../../catalog/datasets/prices_daily.md). Personal and research use only; do not
  redistribute. Unofficial API, can change without notice; the ingest fails loudly rather than
  writing partial data.
- FRED API (free key in `FRED_API_KEY`): H.10 FX fixings (single value per day, no OHLC), US
  short rates and dollar indices, dataset [series_daily](../../catalog/datasets/series_daily.md).
  Federal Reserve / NY Fed public data; also a second source to cross-check Yahoo FX.
- ECB Data Portal (free, no key): euro reference FX rates and ESTR, dataset
  [eur_series_daily](../../catalog/datasets/eur_series_daily.md). Free reuse with the source cited.
- Banco Central do Brasil SGS (free, no key): Selic, CDI and PTAX USD/BRL, dataset
  [brl_series_daily](../../catalog/datasets/brl_series_daily.md). Ten-year window per request.
- Cboe index history files (free, no key): VIX, VXEEM, OVX, GVZ, dataset
  [vol_indices_daily](../../catalog/datasets/vol_indices_daily.md). Research and internal use.
- CFTC Public Reporting (free, no key): TFF positions for CME currency futures, dataset
  [tff_fx_weekly](../../catalog/datasets/tff_fx_weekly.md). US government public data.

## Evaluated

- Stooq daily CSV: behind a JavaScript challenge since at least 2026-10, unusable from a script.

## Rules

- A new source is added with the pull-data skill: module, README, view, test, registry, workflow.
- Adding a vendor that costs money or changes a data source is an ADR (see the ADR test).
- Keys go in `.env` (laptop) or repository secrets (CI), never in a file under git.
