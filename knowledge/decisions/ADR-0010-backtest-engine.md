---
id: ADR-0010-backtest-engine
type: decision
title: "ADR-0010: fill tools/backtest with a daily position-based engine before its second use"
date: 2026-11-17
authors: [lucasvilliers]
owner: lucasvilliers
status: proposed
tags: [backtest, infra, costs, fx]
related: [ADR-0002-tools-are-isolated-packages, ADR-0003-isolation-principle, conventions]
---

# ADR-0010: fill tools/backtest with a daily position-based engine before its second use

## Context

`tools/backtest` was a reserved slot to be filled on the second experiment that needs a backtest
(root `AGENTS.md`, reuse rule). The 2026-11-15 meeting assigned a backtesting framework to Alec and
Lucas as a team deliverable, with strategies of different shapes already in view: FX carry and
momentum on the ingested FRED, ECB and BCB data, micro-cap shorts, and path-dependent relative
value (entries on a z-score, exits on convergence or a time stop). Writing the loop inside one
experiment first would fit only that experiment's shape and be rewritten on the next.

## Decision

Fill `tools/backtest` now, as version 0.2.0, with a daily engine for any strategy that can say
what it wants to hold after each close. Three layers, each replaceable without the others:

- `Market`: prices by symbol and day, named extras, an accounting currency (USD by default) and conversion between currencies.
- `Instrument`: one class per asset class, never per asset, answering `value`, `cashflow` and `exposure`. `Cash` covers anything worth its quoted price in any currency; `FxPair` is spot FX with carry from short rates, a cross being held as its two legs against the accounting currency.
- `Strategy.on_day(ctx)`: the user's code, returning target quantities; `run_weights` turns a weight table into such a strategy.

`run` replays the calendar and keeps cash-plus-marks books: revalue and pay cashflows, fill due
orders, ask the strategy through a `Context` that cannot read past today, fill at the close
through a `CostModel`, record. It returns daily NAV and P&L, positions, trades and the P&L split
by instrument and cause; `metrics` summarises it. It follows `conventions.md` (simple returns, no
forward-filled prices, flat half-spread by bucket, one reporting currency) and adds no dependency
(polars and pyarrow were already declared).

This is an exception to the second-use rule, taken once and on purpose: the engine is covered by
fixture tests written by hand, and was run on real data (FX carry and momentum, 2003 to 2026) in a
sandbox experiment before this ADR.

## Consequences

- An experiment backtests by building a `Market` from what it loaded and calling `run` or `run_weights`; it never writes its own loop or cost code.
- A new asset class is an `Instrument` subclass with its tests; the engine does not change. A new cost shape is a `CostModel` subclass.
- Known limits, each a follow-up rather than part of this decision: no short-borrow cost (needed by the micro-cap shorts), no per-member books or position limits (the idea pods), no risk-based sizing (Kelly), short rates only for USD, EUR and BRL, carry as simple interest on 360 days for every currency, no dividends, margin or interest on cash, daily only.
- The TODO in `conventions.md` ("confirm each convention against the first backtest") can now be checked; a change it finds is a new ADR.

## Alternatives considered

- Write the loop in the first experiment and move it on second use: the rule's default, but the framework was assigned as a deliverable and the second use was already scheduled.
- Wrap a third-party engine (backtrader, vectorbt, zipline): a new dependency, equity-first models of FX units and carry, and accounting that is hard to check line by line against the conventions.
- A vectorised-only engine (weights times returns): fast, but cannot express state such as entry dates, convergence exits or time stops; kept instead as the `run_weights` adapter over the same loop.
- An event-driven intraday simulator with an order book: far more than a daily macro and FX book needs today.
