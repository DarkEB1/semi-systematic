---
id: 2026-10-29-open-questions-after-the-scaffold
type: note
title: "Open questions after the scaffold"
date: 2026-10-29
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra, data, idea]
related: [ADR-0001-initial-setup, start-here, universe]
---

# Open questions after the scaffold

A note in the shape every note has: frontmatter from the template, one title, short sections,
relative links. It doubles as the list of things the scaffold left open on purpose, so the first
real notes can start from here rather than from a blank page.

## Storage

- The `scratch/` lifecycle rule was skipped in Step 0 (ADR-0001). Until it exists, scratch grows
  forever; `just audit` reports size, nobody deletes. Decide a retention (30 days?) and add the rule.
- The B2 backup bucket is a TODO; `just backup` prints a notice and exits. Weekly `backup.yml`
  will keep doing that until the three `B2_*` secrets exist.

## Data

- `raw/` is empty until the first nightly `ingest.yml` run; `just data-health` shows
  `prices_daily missing` until then. Trigger it once by hand after the scaffold PR merges.
- Yahoo is free and unofficial. The first paid or official vendor is an ADR; candidates and the
  rejected ones live in [vendors](../../context/vendors.md).
- The universe is 15 FX pairs. Which EM local-rates or equity-index series come first, and from
  where, decides the next two ingest modules.

## Research

- Per-currency holiday calendars are a TODO in [conventions](../../context/conventions.md);
  data-health counts Monday to Friday, so a Brazilian holiday looks like a gap.
- The cost model is a flat half-spread by liquidity bucket. The first backtest should test
  whether that assumption changes any verdict; if it does, the cost model is an ADR.

## Tooling

- Retrieval is keyword-only. Embeddings wait for an `EMBEDDING_MODEL` decision (cost, provider),
  which is an ADR because it costs money.
- The dashboard's signals page is empty until the reuse rule fires for the first time.
