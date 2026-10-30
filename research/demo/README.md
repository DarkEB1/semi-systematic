---
id: demo
type: project
title: "Demo: the day-one pipeline works end to end"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra, data]
related: [2026-10-29-demo-prices-daily-sanity, ADR-0001-initial-setup]
---

# Demo: the day-one pipeline works end to end

The project every new teammate and agent can run first. It makes no claim about markets; it
exists so that the experiment loop, the research-log and the dashboard have one real example.

## Goal

Show that a dataset ingested by the nightly job loads through `quant.data`, that an experiment
folder runs headless, that `--finish` drafts the research-log entry from `outputs/` only, and that
the hub lists the result.

## Hypotheses

- `prices_daily` has one row per symbol per business day and no symbol is missing more than a
  holiday's worth of days in the last month ([research-log entry](../../knowledge/research-log/2026-10-29-demo-prices-daily-sanity.md)).

## Data

- `prices_daily` (raw view `yahoo_prices_daily` until the first curated snapshot exists).

## Status

Open until the first nightly ingest has filled `raw/` and the notebook has run against it.
