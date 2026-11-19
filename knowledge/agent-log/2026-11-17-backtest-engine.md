---
id: 2026-11-17-backtest-engine
type: agent-log
title: "Build the daily backtesting engine in tools/backtest"
date: 2026-11-17
authors: [Claude]
owner: lucasvilliers
status: draft
tags: [backtest, infra, costs, fx]
related: [ADR-0010-backtest-engine]
---

# Build the daily backtesting engine in tools/backtest

## Task

@lucasvilliers asked for the backtesting framework assigned to Alec and Lucas at the 2026-11-15
meeting: one engine able to test any strategy, built step by step with Claude Code, explained as it
went, then documented for a PR. No skill or loop; branch `feat/backtest`, stacked on the
onboarding branch.

## Decisions with justification

- A daily loop over cash-plus-marks books, not a vectorised engine: it covers path-dependent strategies (entries, exits, time stops), and `run_weights` keeps the weight-table shortcut on the same loop, so both give identical results (tested).
- Instruments are one class per asset class answering `value`, `cashflow`, `exposure`: adding an asset class never touches the loop. One unit of a pair is its non-accounting currency, held or owed, so `USDBRL` returns `1 - S0/S1` per dollar with no special case in the books.
- One accounting currency carried by `Market`, USD by default per `conventions.md`; foreign-currency prices are converted at each day's spot and a cross is held as its two legs, so the carry adds up to the cross's own rate differential. The gain of an unrebalanced cross stays in the position, which is the trade's real economics.
- Missing data is refused, never filled: a duplicate (date, symbol), a missing cost entry, a missing rate or conversion spot all raise. On real data this caught EURUSD present in both FRED and ECB.
- No ADR edits to files owned by @DarkEB1 (`start-here.md`, `conventions.md`): their stale lines are listed for the owner instead, per the agent-channel rule.
- The exception to the second-use rule is an ADR (ADR-0010, `status: proposed`) for @DarkEB1 to accept or reject.

## Summary

Eight commits fill `tools/backtest` as 0.2.0: `Market` and `MarketView`, `Instrument` with `Cash`
and `FxPair`, `Strategy` and `Context`, the `run` loop, `CostModel` (`BpsCost`, `PerUnitCost`),
P&L attribution, `run_weights`, `metrics`, then accounting currencies and FX crosses. About a
hundred fixture tests, every number computed by hand; `just check` and `just test` green.

A sandbox experiment in `research/test-data/` (not committed: it reads `scratch/`, not curated
snapshots) ran FX carry and momentum on the ingested data, 2003 to 2026: BRL carry net Sharpe 0.60
with 0.10x turnover, momentum on 15 pairs net Sharpe 0.08 after costs halved it. Rerunning it after
the currency change gave identical numbers.

Needs a human: @DarkEB1 to accept ADR-0010, and to update the `backtest` line in `start-here.md`.
Follow-ups listed in the ADR: short-borrow cost, per-member books and limits, risk-based sizing,
rates for more currencies, CDI compounding.

## Files touched

- [tools/backtest/src/backtest/__init__.py](../../tools/backtest/src/backtest/__init__.py)
- [tools/backtest/src/backtest/market.py](../../tools/backtest/src/backtest/market.py)
- [tools/backtest/src/backtest/instruments/__init__.py](../../tools/backtest/src/backtest/instruments/__init__.py)
- [tools/backtest/src/backtest/instruments/base.py](../../tools/backtest/src/backtest/instruments/base.py)
- [tools/backtest/src/backtest/instruments/cash.py](../../tools/backtest/src/backtest/instruments/cash.py)
- [tools/backtest/src/backtest/instruments/fx.py](../../tools/backtest/src/backtest/instruments/fx.py)
- [tools/backtest/src/backtest/strategy.py](../../tools/backtest/src/backtest/strategy.py)
- [tools/backtest/src/backtest/engine.py](../../tools/backtest/src/backtest/engine.py)
- [tools/backtest/src/backtest/costs.py](../../tools/backtest/src/backtest/costs.py)
- [tools/backtest/src/backtest/weights.py](../../tools/backtest/src/backtest/weights.py)
- [tools/backtest/src/backtest/result.py](../../tools/backtest/src/backtest/result.py)
- [tools/backtest/src/backtest/metrics.py](../../tools/backtest/src/backtest/metrics.py)
- [tools/backtest/tests/](../../tools/backtest/tests/)
- [tools/backtest/pyproject.toml](../../tools/backtest/pyproject.toml)
- [tools/backtest/README.md](../../tools/backtest/README.md)
- [tools/README.md](../../tools/README.md)
- [knowledge/decisions/ADR-0010-backtest-engine.md](../decisions/ADR-0010-backtest-engine.md)
- [knowledge/agent-log/2026-11-17-backtest-engine.md](2026-11-17-backtest-engine.md)
- [knowledge/INDEX.md](../INDEX.md)
- [uv.lock](../../uv.lock)

## Files relied on

- [AGENTS.md](../../AGENTS.md)
- [tools/AGENTS.md](../../tools/AGENTS.md)
- [knowledge/context/conventions.md](../context/conventions.md)
- [knowledge/decisions/ADR-0002-tools-are-isolated-packages.md](../decisions/ADR-0002-tools-are-isolated-packages.md)
- [knowledge/decisions/ADR-0003-isolation-principle.md](../decisions/ADR-0003-isolation-principle.md)
- [knowledge/templates/decision.md](../templates/decision.md)
- [knowledge/templates/agent-log.md](../templates/agent-log.md)
- [knowledge/meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md](../meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md)

## PR

Branch `feat/backtest`, rebased on main after the onboarding
([#13](https://github.com/DarkEB1/semi-systematic/pull/13)) and data sources
([#14](https://github.com/DarkEB1/semi-systematic/pull/14)) merged; its PR follows.
