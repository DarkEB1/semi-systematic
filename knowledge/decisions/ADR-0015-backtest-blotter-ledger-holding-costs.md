---
id: ADR-0015-backtest-blotter-ledger-holding-costs
type: decision
title: "ADR-0015: tools/backtest charges short borrow and pays dividends"
date: 2026-11-26
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [backtest, infra, costs]
related: [ADR-0014-backtest-engine, ADR-0013-backtest-tool-from-daniel-paleologo, conventions, 2026-11-15-fund-setup-trade-ideas-and-structure]
---

# ADR-0015: tools/backtest charges short borrow and pays dividends

## Context

In `backtest` 0.3.0 a short paid no borrow fee and no dividend, and a long received no dividend,
so a short book looked better than it is. The
[2026-11-15 meeting](../meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md) lists
micro-cap shorts among the first ideas, where the borrow fee can be most of the cost.

## Decision

`backtest` 0.4.0, no new dependency:

- **Holding costs.** `CostModel` gains `holding(...)`, charged for every position at every close
  (default zero). `BorrowCost` charges basis points a year on the value of a short at the previous
  close, over calendar days on 360, per instrument id, and raises for an id with no rate and no
  default.
- **Dividends.** `Cash` pays `market.extras["dividends"]` (amount per unit on the ex-date, in the
  quote currency) to whoever held the unit at the previous close; a short pays it.

## Consequences

- `daily.cost`, `cost_drag` and the `cost` column of `Result.pnl` now include borrow.
- A run with no `BorrowCost` and no `dividends` in `market.extras` gives the same numbers as 0.3.0.
- Dividends need unadjusted prices; with adjusted prices the dividend is counted twice.
- Follow-ups, not part of this decision: borrow has no availability, recall or rate history; no
  withholding tax.

## Alternatives considered

- Borrow as an `Instrument.cashflow`: a cashflow is per unit whatever the sign of the position,
  and borrow is paid by shorts only.
- Dividends through total-return prices: correct for a long, but a short would not be charged on
  the ex-date and the price P&L and the income could not be told apart in the attribution.
- A larger change (replay of a trade blotter, a round-trip ledger, next-close fills by default):
  built on the same branch and removed before merge as more than the fund needs now.
