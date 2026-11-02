# backtest

Reserved for the backtesting loop that signals share once two experiments need one. Today it is a
uv workspace member with a package skeleton and an import test, nothing more, on purpose.

## How it gets filled

The reuse rule in [AGENTS.md](../../AGENTS.md): code moves out of an experiment only on its second
use, with a test, in its own PR. The first experiment that needs a cost-aware backtest writes it in
its own `run.py`; the second experiment that needs the same loop moves it here, and the conventions
it must follow (simple returns, flat half-spread per trade by liquidity bucket, business-day
calendars, USD reporting) are in
[knowledge/context/conventions.md](../../knowledge/context/conventions.md). That move is an ADR
because it introduces a method others will reuse.

## What belongs here when it exists

- A loop that takes a signal table (date, symbol, weight) and a `prices_daily` snapshot and returns daily P&L after costs.
- The cost model named in `conventions.md`, as one function with its parameters, never hard-coded in a notebook.
- Tests under `tools/backtest/tests/` that run in `just test` without touching the bucket (fixtures only).

What does not belong here: anything used by one experiment, data access (that is `quant.data`),
and plotting.
