---
id: ADR-0013-backtest-tool-from-daniel-paleologo
type: decision
title: "ADR-0013: tools/backtest is the walk-forward plus Rademacher haircut framework"
date: 2026-11-18
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [backtest, infra]
related: [ADR-0002-tools-are-isolated-packages, conventions]
---

# ADR-0013: tools/backtest is the walk-forward plus Rademacher haircut framework

## Context

`tools/backtest` was a reserved, empty package waiting for a second experiment to need a shared
loop. On 2026-11-18 @DarkEB1 asked for it to be built now, from one source and nothing else:
Daniel and Paleologo, "Backtesting: Evaluating Excess Returns" (FINC B8420 Quantitative Investing,
lecture 6, Fall 2026). The lecture specifies a protocol (non-anticipative walk-forward
reconstruction, net PnL, one score matrix for the whole candidate family) and an evaluation layer
(the Rademacher Anti-Serum lower bound), with worked numbers that serve as tests. It does not
specify a cost model, a portfolio constructor or a data layer.

The number skips 0010 to 0012, which are taken on the unmerged `research/defi-repo-replication`
branch.

## Decision

`backtest` 0.2.0 implements exactly what the lecture gives formulas for, on numpy arrays:

- splits: `walk_forward` (rolling or expanding, with a gap) and `purged_kfold` (purge and embargo);
- per-date scores under one timing convention (decision row t meets outcome row t+1):
  `net_pnl`, `risk_scaled`, `information_coefficient`;
- joint evaluation of a T x N score matrix: `rademacher`, `ras_lower_bounds` (bounded theorem,
  factor 3, optional Monte Carlo allowance), `subgaussian_lower_bounds`, `massart_bound`,
  `block_means`, `annualize` and `sharpe_se` (251 periods a year).

A strategy is reported with its lower bound and the `kappa`, `delta`, `B` and `seed` used, over the
full family that was tried. The dependency changes from `polars` and `pyarrow` to `numpy`.

## Consequences

- An experiment gets leak-safe splits and a search-aware haircut from one import, and the tests
  pin the lecture's own numbers (hand example R = .375, Massart .741, estimation term .003906).
- This sets aside the second-use rule for this tool: the code was not lifted from an experiment.
  The first experiment that uses it is the real test of the API.
- Costs are an input array. The flat half-spread in `conventions.md` is not implemented here;
  adding it is a later change.
- The bound is conservative and assumes iid rows; a calibrated, less conservative screen would be
  a new decision with its own validation.

## Alternatives considered

- Wait for the second experiment: the default, overridden by an explicit request.
- Wrap a third-party engine: outside the source, and none provides the family-level haircut.
- Polars tables as the interface: the method is matrix arithmetic; the caller pivots once.
