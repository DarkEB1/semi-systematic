---
id: 2026-11-12-fred-ingest-source
type: agent-log
title: "Add FRED, ECB, BCB, Cboe and CFTC as ingest sources"
date: 2026-11-12
authors: [claude-code]
owner: lucasvilliers
status: draft
tags: [data, fx, macro]
related: [vendors]
---

# Add FRED, ECB, BCB, Cboe and CFTC as ingest sources

## Task

Asked by @lucasvilliers on 2026-11-12: a free daily pipeline for FX spot and rates, starting with
FRED, then the ECB, BCB, Cboe and CFTC sources discussed, built and tested locally before any push. Skill: pull-data (`just scaffold-source fred`).

## Decisions with justification

- One long-format dataset (`date, series_id, symbol, value`) driven by `catalog/reference/fred_series.csv`: adding a series is a CSV row, as with `universe.csv`. One dataset per series kind was ruled out as more modules for the same endpoint.
- Daily series only (H.10 FX, DTB3, DGS3MO, SOFR, DFF, dollar indices). The monthly OECD 3-month rates used in the earlier local pipeline are left for a separate monthly dataset, so cadence and data-health stay meaningful.
- No ADR: FRED is free and adds to, rather than replaces, the Yahoo source (pull-data step 6). `vendors.md` moves FRED from Evaluated to In use.
- `check_history` moved to `_base.check_history(id_col=...)` once a third source needed it (reuse rule); `yahoo.py` keeps its own copy, untouched in this PR.
- ECB and BCB series lists are CSVs under `catalog/reference/` like FRED's; the four Cboe indices and ten CFTC contracts are module constants, as they are fixed by the vendor.
- CFTC weekly reports are stored in the daily (year/month) layout with `lag_days: 10`; a run missing a contract is rejected only from March 2022, since ZAR and BRL report sparsely before.
- Banxico (MXN rates) left out: it needs a token the owner does not have yet.
- `lag_days: 3`: data-health takes the most current series (rates, next business day); H.10 FX runs about a week behind and is documented under Cadence.

## Summary

Done: five source modules with their series lists, dataset READMEs, catalog views and tests on real vendor fixtures; `FRED_API_KEY` in `.env.example` and in `ingest.yml`. `just test` (139 passed) and `just check` green. Network errors (including a connection reset) now trigger the retries.

Backfills written to `scratch/lucasvilliers/raw/<source>/<dataset>/run=<stamp>/`:

- fred `series_daily`, run=20261112T151610Z, 287 objects: 15 H.10 FX pairs from 2003-01-02 to 2026-11-06, 4 US rates, 3 dollar indices from 2006.
- ecb `eur_series_daily`, run=20261113T091812Z, 287 objects: 16 EUR pairs from 2003-01-02 to 2026-11-12, ESTR from 2019-10-01.
- bcb `brl_series_daily`, run=20261113T092456Z, 287 objects: Selic target and effective, CDI, PTAX from 2003 to 2026-11-12.
- cboe `vol_indices_daily`, run=20261113T093047Z, 287 objects: VIX from 2003, OVX and GVZ from 2009, VXEEM from 2011, to 2026-11-12.
- cftc `tff_fx_weekly`, run=20261113T093636Z, 246 objects: 10 currency futures from 2006-06-13 (BRL 2011, ZAR 2010) to 2026-11-03.

Finding for the data-layer owner: Yahoo's daily FX "close" for date D is the price at the start of D (about D-1's close), not the end of D. Checked on 2026-11-13 against Yahoo's own hourly bars, 6 pairs over one month: median gap 0.006-0.027% to the last hourly close before the bar's timestamp, 0.19-0.54% to the 21:00 UTC close of D, for a median daily high-low range of 0.45-0.97%. Open and close of each daily bar are nearly equal. The date handling in `yahoo.py` is correct; the vendor value is stale. Against FRED's noon New York fixing, `prices_daily` matches best one day later (median gap 0.088% with Yahoo date = FRED date + 1, against 0.221% on the same date). No look-ahead, but signals built on it lag one day and cross-source joins are misaligned by a day. Not changed here.

Ingest runs here first failed with `RequestTimeTooSkewed`: the Docker Desktop VM clock had drifted after the Mac slept. One failed Cboe run left a partial `run=20261112T170020Z` folder (17 objects) in scratch; it was deleted.

Finding for the data-layer owner: `just scaffold-source` silently skips the registry import once ruff has merged the imports into one line (`from quant.ingest import fred, yahoo`), because the regex in `pull_data.py` expects one module per line; the imports were fixed by hand. On 2026-11-18 the regex was widened to accept a comma-separated import (one character class), and the pull-data golden (`ai/evals/pull-data/expected.txt`) was updated for the longer source matrix in `ingest.yml`, its only other diff.

Needs a human: `FRED_API_KEY` repository secret before the first nightly run; review of the `catalog/` and `.github/` paths by the data-layer owner.

## Files touched

- [src/quant/ingest/fred.py](../../src/quant/ingest/fred.py)
- [src/quant/ingest/__init__.py](../../src/quant/ingest/__init__.py)
- [src/quant/ingest/_base.py](../../src/quant/ingest/_base.py)
- [src/quant/ingest/ecb.py](../../src/quant/ingest/ecb.py)
- [src/quant/ingest/bcb.py](../../src/quant/ingest/bcb.py)
- [src/quant/ingest/cboe.py](../../src/quant/ingest/cboe.py)
- [src/quant/ingest/cftc.py](../../src/quant/ingest/cftc.py)
- [catalog/reference/ecb_series.csv](../../catalog/reference/ecb_series.csv)
- [catalog/reference/bcb_series.csv](../../catalog/reference/bcb_series.csv)
- [catalog/datasets/eur_series_daily.md](../../catalog/datasets/eur_series_daily.md)
- [catalog/datasets/brl_series_daily.md](../../catalog/datasets/brl_series_daily.md)
- [catalog/datasets/vol_indices_daily.md](../../catalog/datasets/vol_indices_daily.md)
- [catalog/datasets/tff_fx_weekly.md](../../catalog/datasets/tff_fx_weekly.md)
- [tests/test_ingest_ecb.py](../../tests/test_ingest_ecb.py)
- [tests/test_ingest_bcb.py](../../tests/test_ingest_bcb.py)
- [tests/test_ingest_cboe.py](../../tests/test_ingest_cboe.py)
- [tests/test_ingest_cftc.py](../../tests/test_ingest_cftc.py)
- [tests/fixtures/ecb_sample.json](../../tests/fixtures/ecb_sample.json)
- [tests/fixtures/bcb_sample.json](../../tests/fixtures/bcb_sample.json)
- [tests/fixtures/cboe_sample.json](../../tests/fixtures/cboe_sample.json)
- [tests/fixtures/cftc_sample.json](../../tests/fixtures/cftc_sample.json)
- [catalog/reference/fred_series.csv](../../catalog/reference/fred_series.csv)
- [catalog/datasets/series_daily.md](../../catalog/datasets/series_daily.md)
- [catalog/catalog.sql](../../catalog/catalog.sql)
- [tests/test_ingest_fred.py](../../tests/test_ingest_fred.py)
- [tests/fixtures/fred_sample.json](../../tests/fixtures/fred_sample.json)
- [tests/test_data.py](../../tests/test_data.py)
- [.env.example](../../.env.example)
- [.github/workflows/ingest.yml](../../.github/workflows/ingest.yml)
- [knowledge/context/vendors.md](../context/vendors.md)
- [.claude/skills/pull-data/pull_data.py](../../.claude/skills/pull-data/pull_data.py)
- [ai/evals/pull-data/expected.txt](../../ai/evals/pull-data/expected.txt)
- [knowledge/INDEX.md](../INDEX.md)

## Files relied on

- [.claude/skills/pull-data/pull_data.py](../../.claude/skills/pull-data/pull_data.py)
- [.claude/skills/pull-data/SKILL.md](../../.claude/skills/pull-data/SKILL.md)
- [src/quant/ingest/yahoo.py](../../src/quant/ingest/yahoo.py)
- [src/quant/ingest/_base.py](../../src/quant/ingest/_base.py)
- [src/quant/datahealth.py](../../src/quant/datahealth.py)
- [AGENTS.md](../../AGENTS.md)

## PR

Branch `feat/ingest-free-sources`, stacked on the onboarding PR (https://github.com/DarkEB1/semi-systematic/pull/13); its PR follows once pushed.
