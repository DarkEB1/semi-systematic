---
id: 2026-10-29-demo-prices-daily-sanity
type: research-log
title: "Demo: prices_daily loads and has no obvious gaps"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: draft
tags: [fx, data, data-quality]
datasets: [prices_daily]
project: demo
related: [ADR-0001-initial-setup, demo]
---

# Demo: prices_daily loads and has no obvious gaps

This entry exists to demonstrate the research-log template and the experiment loop end to end.
It makes no claim about markets.

## Hypothesis

The day-one pipeline works: the Yahoo ingest produces a `prices_daily` table that loads through
`quant.data`, has one row per symbol per business day, and no symbol is missing more than a
holiday's worth of days in the last month.

## Data

- prices_daily, raw view `yahoo_prices_daily` (no curated snapshot exists yet, so `config.yaml`
  lists none and the notebook reads the raw view directly; the first promotion will fix a snapshot)

## Method

Run the demo experiment notebook headless, count rows per symbol and per month, list symbols with
fewer than 18 rows in the latest full month. Seed 0, no model.

## Result

Not run yet. Numbers go here only when copied from the notebook's output cells.

## Verdict

Pending. Keep: this is the smoke test every new source should pass before its PR.

## Links

- project: [research/demo](../../research/demo/README.md)
- experiment: [research/demo/experiments/2026-10-29-demo](../../research/demo/experiments/2026-10-29-demo/results.md)
- dataset: [catalog/datasets/prices_daily.md](../../catalog/datasets/prices_daily.md)
