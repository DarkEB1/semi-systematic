---
id: 2026-11-26-backtest-blotter-ledger
type: agent-log
title: "Blotter replay, round-trip ledger, borrow, dividends and next-close fills in tools/backtest"
date: 2026-11-26
authors: [Claude]
owner: DarkEB1
status: draft
tags: [backtest, infra, costs]
related: [ADR-0015-backtest-blotter-ledger-holding-costs, ADR-0014-backtest-engine, ADR-0013-backtest-tool-from-daniel-paleologo, 2026-11-25-backtest-merge]
---

# Blotter replay, round-trip ledger, borrow, dividends and next-close fills in tools/backtest

## Task

@DarkEB1 asked for a critical read of the merged backtester (PR #15) as a discretionary shop
would see it, then for the five changes that read proposed, in one PR: blotter replay, a
round-trip ledger tagged by idea and owner, borrow cost and dividends, `delay=1` as the default,
and the haircut kept for the systematic sleeves only. No skill or loop.

## Decisions with justification

- `run_blotter` drives the engine's books directly (`_Run`, `_Book`) instead of going through a
  `Strategy`: a strategy can only fill at a close, and the traded price is what a blotter adds.
  `_Run.fill` takes an optional `mark` so the new units move to the close the same day.
- The ledger is built from `Result.pnl` and `Result.positions`, not from fills, so a trip's P&L
  holds carry, dividends and borrow and the trips add up to the run. The cost is that the book
  nets an instrument: two ideas open in one instrument are one trip. Written in the README.
- Borrow is a `CostModel.holding` hook (default zero) rather than an instrument cashflow, which
  is per unit whatever the sign. `BorrowCost` raises without a rate, like `BpsCost`.
- Dividends are a `Cash.cashflow` read from `market.extras["dividends"]`: no new layer.
- `delay=1` default: the 62 existing test calls that relied on the old default now pass
  `delay=0` explicitly (their hand-computed numbers are unchanged); one new test pins the default.
- The haircut's scope is a documentation change (README, ADR-0015); `evaluate` is untouched.
- ADR-0014 (owner lucasvilliers) is not edited; ADR-0015 records the changed default.
- Not done, listed as follow-ups in ADR-0015: foreign-quote blotter prices, per-idea netting,
  borrow availability, withholding tax, the 251 against 252 periods.

## Summary

Done: version 0.4.0, 27 new tests on hand-computed numbers (148 in the package). Nothing was run
on real data: there is no blotter of real trades yet, and the first one is the test of the API.
Needs a human: lucasvilliers to read the PR, since the default of his engine changes.

## Files touched

- [tools/backtest/src/backtest/blotter.py](../../tools/backtest/src/backtest/blotter.py)
- [tools/backtest/src/backtest/ledger.py](../../tools/backtest/src/backtest/ledger.py)
- [tools/backtest/src/backtest/engine.py](../../tools/backtest/src/backtest/engine.py)
- [tools/backtest/src/backtest/costs.py](../../tools/backtest/src/backtest/costs.py)
- [tools/backtest/src/backtest/weights.py](../../tools/backtest/src/backtest/weights.py)
- [tools/backtest/src/backtest/family.py](../../tools/backtest/src/backtest/family.py)
- [tools/backtest/src/backtest/instruments/cash.py](../../tools/backtest/src/backtest/instruments/cash.py)
- [tools/backtest/src/backtest/__init__.py](../../tools/backtest/src/backtest/__init__.py)
- [tools/backtest/tests/test_blotter.py](../../tools/backtest/tests/test_blotter.py)
- [tools/backtest/tests/test_ledger.py](../../tools/backtest/tests/test_ledger.py)
- [tools/backtest/tests/test_holding.py](../../tools/backtest/tests/test_holding.py)
- [tools/backtest/tests/test_engine.py](../../tools/backtest/tests/test_engine.py)
- [tools/backtest/tests/test_weights.py](../../tools/backtest/tests/test_weights.py)
- [tools/backtest/tests/test_costs.py](../../tools/backtest/tests/test_costs.py)
- [tools/backtest/tests/test_currency.py](../../tools/backtest/tests/test_currency.py)
- [tools/backtest/tests/test_attribution.py](../../tools/backtest/tests/test_attribution.py)
- [tools/backtest/tests/test_family.py](../../tools/backtest/tests/test_family.py)
- [tools/backtest/tests/test_fx.py](../../tools/backtest/tests/test_fx.py)
- [tools/backtest/tests/test_metrics.py](../../tools/backtest/tests/test_metrics.py)
- [tools/backtest/tests/test_import.py](../../tools/backtest/tests/test_import.py)
- [tools/backtest/pyproject.toml](../../tools/backtest/pyproject.toml)
- [tools/backtest/README.md](../../tools/backtest/README.md)
- [knowledge/decisions/ADR-0015-backtest-blotter-ledger-holding-costs.md](../decisions/ADR-0015-backtest-blotter-ledger-holding-costs.md)
- [knowledge/INDEX.md](../INDEX.md)
- [uv.lock](../../uv.lock)

## Files relied on

- [knowledge/decisions/ADR-0014-backtest-engine.md](../decisions/ADR-0014-backtest-engine.md)
- [knowledge/decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md](../decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md)
- [knowledge/context/conventions.md](../context/conventions.md)
- [tools/backtest/src/backtest/result.py](../../tools/backtest/src/backtest/result.py)
- [tools/backtest/src/backtest/market.py](../../tools/backtest/src/backtest/market.py)
- [tools/backtest/src/backtest/instruments/fx.py](../../tools/backtest/src/backtest/instruments/fx.py)
- [tools/AGENTS.md](../../tools/AGENTS.md)
- [knowledge/AGENTS.md](../AGENTS.md)

## PR

Opened from `feat/backtest-blotter`; the link is in the PR that carries this file.
