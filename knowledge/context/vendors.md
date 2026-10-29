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

## Evaluated

- Stooq daily CSV: behind a JavaScript challenge since at least 2026-10, unusable from a script.
- FRED (`fredgraph.csv?id=DEX...`): reliable free daily FX fixings, single value per day (no OHLC).
  Good fallback or second source for a data-quality cross-check.

## Rules

- A new source is added with the pull-data skill: module, README, view, test, registry, workflow.
- Adding a vendor that costs money or changes a data source is an ADR (see the ADR test).
- Keys go in `.env` (laptop) or repository secrets (CI), never in a file under git.
