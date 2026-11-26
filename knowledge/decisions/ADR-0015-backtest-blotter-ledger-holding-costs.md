---
id: ADR-0015-backtest-blotter-ledger-holding-costs
type: decision
title: "ADR-0015: tools/backtest replays a blotter, reports round trips, charges borrow and dividends, and fills at the next close by default"
date: 2026-11-26
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [backtest, infra, costs]
related: [ADR-0014-backtest-engine, ADR-0013-backtest-tool-from-daniel-paleologo, conventions, 2026-11-15-fund-setup-trade-ideas-and-structure]
---

# ADR-0015: tools/backtest replays a blotter, reports round trips, charges borrow and dividends, and fills at the next close by default

## Context

A review of `backtest` 0.3.0 on 2026-11-26, read as a discretionary shop would, found five gaps.
The fund is semi-systematic: besides rules, it holds trades made by hand in idea pods, and the
[2026-11-15 meeting](../meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md) lists
micro-cap shorts among the first ideas.

- The engine only ran rules. A trade that was actually made, at the price it was made at, could
  not be put through the books.
- The unit of every report was the daily return. A hand-made trade is judged as a trade: entry,
  exit, how far it went against the thesis, whose idea it was.
- Shorts paid no borrow fee and no dividend, so a short book looked better than it is.
- A decision filled at the close that produced it (`delay=0`), which assumes the signal is known
  and the order placed before that close.
- The Rademacher haircut was presented as the evaluation for everything, although it needs a
  family that can be listed and years of daily returns per candidate; a book of thirty trades has
  neither, and on the BRL carry example of ADR-0014 it was inconclusive even for a rule.

## Decision

`backtest` 0.4.0, no new dependency:

- **Blotter replay.** `run_blotter(blotter, market, ...)` fills each row of a trade table
  (`date`, `symbol`, signed `quantity`, optional `price`, `idea`, `owner`) on its date, at its
  price or at the close when the price is null, through the same books as `run`. A fill away from
  the close is marked to the close the same day and the difference is that day's price P&L. A
  trade that cannot be booked raises. `idea` and `owner` are kept on `Result.trades`.
- **Round-trip ledger.** `round_trips(res)` turns any `Result` into one row per instrument held
  from flat to flat, with its P&L (price, cashflow and cost, summed from `Result.pnl`, so the
  trips add up to the run), the lowest and highest its running P&L stood, and the idea and owner
  of the fill that opened it. `trade_stats(trips)` gives the hit rate, average win and loss,
  payoff, expectancy and average days held.
- **Holding costs.** `CostModel` gains `holding(...)`, charged for every position at every close;
  `BorrowCost` charges basis points a year on the value of a short at the previous close, over
  calendar days on 360, per instrument id, and raises for an id with no rate and no default.
- **Dividends.** `Cash` pays `market.extras["dividends"]` (amount per unit on the ex-date, in the
  quote currency) to whoever held the unit at the previous close; a short pays it.
- **Next-close fills by default.** `run` and `run_weights` default to `delay=1`. `delay=0` stays
  available and is exactly the timing of ADR-0013's `pnl.py`.
- **Scope of the haircut.** `evaluate` (ADR-0013) is the test for a rule and its variants. Trades
  made by hand are read with the ledger, against the thesis written before the trade.

## Consequences

- A call to `run` or `run_weights` without `delay` now fills one close later, so its numbers
  change; the BRL carry figures quoted in ADR-0014 were run with `delay=0`. The existing tests
  pass `delay=0` explicitly and one new test pins the default. ADR-0014 stands otherwise.
- `daily.cost`, `cost_drag` and the `cost` column of `Result.pnl` now include borrow.
- A book of hand-made trades has a P&L, an attribution and a ledger per idea and per owner from
  one call; the NAV itself is still one book per run.
- Second use: the code was not lifted from an experiment (as ADR-0013 and ADR-0014). The first
  blotter of real trades is the test of the API.
- Follow-ups, not part of this decision: a blotter price in a foreign quote or in FX terms is not
  converted; two ideas open in the same instrument net into one trip; borrow has no availability,
  recall or rate history; no withholding tax; no limit on size against volume; `annualize` uses
  251 periods while `metrics` and `evaluate` default to 252.

## Alternatives considered

- A `Strategy` that replays the blotter through `run`: fills only at closes, so the price actually
  traded is lost, and that price is the point of a blotter.
- A ledger built from fills alone (matching buys to sells): misses carry, dividends and borrow,
  and does not add up to the books.
- Borrow as an `Instrument.cashflow`: a cashflow is per unit whatever the sign of the position,
  and borrow is paid by shorts only.
- Keep `delay=0` and document it: the optimistic choice would stay the one nobody has to ask for.
- Drop the haircut: it is the right test for the systematic sleeves; only its scope is narrowed.
