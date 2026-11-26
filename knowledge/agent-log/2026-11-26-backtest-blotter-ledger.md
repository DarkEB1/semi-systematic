---
id: 2026-11-26-backtest-blotter-ledger
type: agent-log
title: "Short borrow and dividends in tools/backtest"
date: 2026-11-26
authors: [Claude]
owner: DarkEB1
status: draft
tags: [backtest, infra, costs]
related: [ADR-0015-backtest-blotter-ledger-holding-costs, ADR-0014-backtest-engine, ADR-0013-backtest-tool-from-daniel-paleologo, 2026-11-25-backtest-merge]
---

# Short borrow and dividends in tools/backtest

## Task

@DarkEB1 asked for a critical read of the merged backtester (PR #15) as a discretionary shop
would see it, then for the five changes that read proposed, in one PR. After seeing them, he
judged all but two overcomplicated and asked to remove everything except borrow cost and
dividends. No skill or loop.

## Decisions with justification

- Borrow is a `CostModel.holding` hook (default zero) rather than an instrument cashflow, which
  is per unit whatever the sign. `BorrowCost` raises without a rate, like `BpsCost`.
- Dividends are a `Cash.cashflow` read from `market.extras["dividends"]`: no new layer.
- Removed from the branch before merge: `run_blotter`, `round_trips`, `trade_stats`, the
  `delay=1` default (back to `delay=0`, so ADR-0014 stands unchanged) and the README section on
  the scope of the haircut. The existing tests are back to their text on `main`.
- The ADR and this entry keep their first file names (knowledge files are never renamed), so
  the names still say blotter and ledger; the titles and the text are the smaller scope.

## Summary

Done: version 0.4.0, 11 new tests on hand-computed numbers. A run without `BorrowCost` and without
dividends gives the same numbers as 0.3.0. Nothing was run on real data.

## Files touched

- [tools/backtest/src/backtest/engine.py](../../tools/backtest/src/backtest/engine.py)
- [tools/backtest/src/backtest/costs.py](../../tools/backtest/src/backtest/costs.py)
- [tools/backtest/src/backtest/instruments/cash.py](../../tools/backtest/src/backtest/instruments/cash.py)
- [tools/backtest/src/backtest/__init__.py](../../tools/backtest/src/backtest/__init__.py)
- [tools/backtest/tests/test_holding.py](../../tools/backtest/tests/test_holding.py)
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
- [tools/AGENTS.md](../../tools/AGENTS.md)
- [knowledge/AGENTS.md](../AGENTS.md)

## PR

[#19](https://github.com/DarkEB1/semi-systematic/pull/19)
