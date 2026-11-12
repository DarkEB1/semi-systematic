---
id: 2026-11-12-fred-ingest-source
type: agent-log
title: "Add FRED as a daily ingest source (series_daily)"
date: 2026-11-12
authors: [claude-code]
owner: lucasvilliers
status: draft
tags: [data, fx, macro]
related: [vendors]
---

# Add FRED as a daily ingest source (series_daily)

## Task

Asked by @lucasvilliers on 2026-11-12: a free daily pipeline for FX spot and rates, starting with
FRED, built and tested locally before any push. Skill: pull-data (`just scaffold-source fred`).

## Decisions with justification

- One long-format dataset (`date, series_id, symbol, value`) driven by `catalog/reference/fred_series.csv`: adding a series is a CSV row, as with `universe.csv`. One dataset per series kind was ruled out as more modules for the same endpoint.
- Daily series only (H.10 FX, DTB3, DGS3MO, SOFR, DFF, dollar indices). The monthly OECD 3-month rates used in the earlier local pipeline are left for a separate monthly dataset, so cadence and data-health stay meaningful.
- No ADR: FRED is free and adds to, rather than replaces, the Yahoo source (pull-data step 6). `vendors.md` moves FRED from Evaluated to In use.
- `check_history` duplicated from `yahoo.py` keyed on `series_id` rather than shared: reuse rule (second use) and no change to the Yahoo module in this PR.
- `lag_days: 3`: data-health takes the most current series (rates, next business day); H.10 FX runs about a week behind and is documented under Cadence.

## Summary

Done: module, series list, dataset README, catalog views `fred_series_daily` and `ref_fred_series`, tests with a real DEXUSEU fixture, `FRED_API_KEY` in `.env.example` and in `ingest.yml`. `just test` (119 passed) and `just check` green. `just ingest fred --since 2003-01-01` wrote 287 objects to `scratch/lucasvilliers/raw/fred/series_daily/run=20261112T151610Z/`: 22 series, FX from 2003-01-02 to 2026-11-06.

Finding for the data-layer owner: against FRED's noon New York fixing, Yahoo `prices_daily` closes match best one day later (median absolute gap 0.088% with Yahoo date = FRED date + 1, against 0.221% on the same date, since 2025-09). The Yahoo dates may be shifted by one day; not changed here.

Needs a human: `FRED_API_KEY` repository secret before the first nightly run; review of the `catalog/` and `.github/` paths by the data-layer owner.

## Files touched

- [src/quant/ingest/fred.py](../../src/quant/ingest/fred.py)
- [src/quant/ingest/__init__.py](../../src/quant/ingest/__init__.py)
- [catalog/reference/fred_series.csv](../../catalog/reference/fred_series.csv)
- [catalog/datasets/series_daily.md](../../catalog/datasets/series_daily.md)
- [catalog/catalog.sql](../../catalog/catalog.sql)
- [tests/test_ingest_fred.py](../../tests/test_ingest_fred.py)
- [tests/fixtures/fred_sample.json](../../tests/fixtures/fred_sample.json)
- [tests/test_data.py](../../tests/test_data.py)
- [.env.example](../../.env.example)
- [.github/workflows/ingest.yml](../../.github/workflows/ingest.yml)
- [knowledge/context/vendors.md](../context/vendors.md)

## Files relied on

- [.claude/skills/pull-data/SKILL.md](../../.claude/skills/pull-data/SKILL.md)
- [src/quant/ingest/yahoo.py](../../src/quant/ingest/yahoo.py)
- [src/quant/ingest/_base.py](../../src/quant/ingest/_base.py)
- [src/quant/datahealth.py](../../src/quant/datahealth.py)
- [AGENTS.md](../../AGENTS.md)

## PR

None yet: built locally at the owner's request; the branch is stacked on the onboarding branch and is pushed later.
