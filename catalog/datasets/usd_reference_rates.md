---
id: usd_reference_rates
type: dataset
title: "usd_reference_rates"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [data, data-quality, macro]
datasets: [usd_reference_rates]
---

# usd_reference_rates

Bounded research acquisition; private scratch objects are not yet promoted. Raw view `nyfed_usd_reference_rates` is populated only after owner-approved integration and workflow ingestion.

## Source

- source: nyfed
- url: https://markets.newyorkfed.org/static/docs/markets-api.html
- licence: use subject to the [New York Fed terms](https://www.newyorkfed.org/privacy/termsofuse.html), including reference-rate attribution and disclaimer requirements.

The SOFR and EFFR data are subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not responsible for publication of these data by semi-systematic, does not endorse this republication, and has no liability for your use.

semi-systematic is not affiliated with the New York Fed. The New York Fed does not sanction, endorse, or recommend any products or services offered by semi-systematic.

Fetched by [the ingest module](../../src/quant/ingest/nyfed.py). Local runs write only run-stamped scratch partitions. Default refresh rewrites whole monthly partitions in CI, never curated snapshots.

## Cadence

- cadence: daily
- lag_days: 1

New York Fed publication calendar; default refresh starts at the first day of the month containing 35 days ago.

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | UTC date | Midnight cutoff for Aave; effective date for NY Fed |
| symbol | string | identifier | DAI/USDC/USDT or SOFR/EFFR |
| rate_pct | float64 | percent per year | Published nominal reference rate, ACT/360 for accrual |
| volume_billions | float64 |  | volume billions |
| revision | string | flag | NY Fed revision indicator; data are current vintage |
| source | string |  | source |
| ingested_at | timestamp[us, UTC] |  | ingested at |

## Known gaps

- Effective date is not publication time. SOFR/EFFR are published on the following applicable business day; a same-effective-date decision would look ahead.
- Current-vintage history may contain revisions. The API revision flag is retained; no historical first-release vintage is claimed.
- Non-business days have no rows; no ingest interpolation. The experiment models contractual accrual over non-business spans separately and records its calendar convention.
- SOFR is a transaction-based secured overnight benchmark; EFFR is an unsecured benchmark. Neither establishes the researcher's executable funding or investment rate.

## Owner

DarkEB1. Schema changes and promotion require data-layer review. Acquisition manifests record exact object sizes and hashes; research remains draft while inputs are in scratch.
