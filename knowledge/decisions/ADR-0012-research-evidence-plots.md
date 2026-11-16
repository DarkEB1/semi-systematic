---
id: ADR-0012-research-evidence-plots
type: decision
title: "ADR-0012: use Matplotlib for exported research evidence"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra, data]
related: [ADR-0010-defi-repo-research-sources]
---

# ADR-0012: use Matplotlib for exported research evidence

## Context

The DeFi-repo experiment needs readable rate, spread and cumulative-performance figures that can be reviewed outside the interactive notebook. The existing statistical extra has Statsmodels but no plotting backend.

## Decision

Add Matplotlib to the existing optional `ml` research extra and lock it with uv. Export static PNG figures below the repository size limit. Run the notebook with `uv run --extra ml`. Keep the ingestion/data layer independent of the research extra.

## Consequences

Figures can be reproduced from pinned inputs and included with the research results. This adds a free Python dependency and its locked transitive dependencies; no service or paid vendor. Statistical results remain in machine-readable outputs as well as figures.

## Alternatives considered

- Tables alone: retain them, but long time-series comparisons are clearer with plots.
- Hand-coded rendering: more custom code and less reproducible scientific presentation.
