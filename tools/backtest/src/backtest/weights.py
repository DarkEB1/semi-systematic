"""run_weights: backtest a table of target weights without writing a Strategy.

The table is wide: a ``date`` column plus one column per symbol, each cell the fraction of NAV to
hold after that close (negative is short, null is zero). A row is a rebalance: on its date the
book is resized to the weights at today's NAV and prices; between rows the quantities are held
and drift with prices. It runs through the same day loop as any ``Strategy``, so costs,
attribution, missing days and ``delay`` behave identically.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping

import polars as pl

from backtest.costs import CostModel
from backtest.engine import run
from backtest.instruments import Instrument
from backtest.market import Market
from backtest.result import Result
from backtest.strategy import Context, Strategy, as_instrument


class TargetWeights(Strategy):
    """Rebalance to a row of ``weights`` on each of its dates; hold in between."""

    def __init__(
        self,
        weights: pl.DataFrame,
        *,
        date: str = "date",
        instruments: Mapping[str, Instrument] | None = None,
    ) -> None:
        columns = [c for c in weights.columns if c != date]
        if not columns:
            raise ValueError("TargetWeights: no symbol column besides the date")
        instruments = instruments or {}
        self.instruments = {c: instruments.get(c) or as_instrument(c) for c in columns}
        self.rows: dict[dt.date, dict[Instrument, float]] = {}
        for row in weights.iter_rows(named=True):
            day = row[date]
            day = day.date() if isinstance(day, dt.datetime) else day
            if day in self.rows:
                raise ValueError(f"TargetWeights: duplicate row for {day}")
            self.rows[day] = {self.instruments[c]: float(row[c] or 0.0) for c in columns}

    def on_day(self, ctx: Context) -> dict[Instrument, float] | None:
        row = self.rows.get(ctx.date)
        if row is None:
            return None
        targets = ctx.quantities(row)
        for inst, qty in ctx.positions.items():  # held but not in the table: keep it
            targets.setdefault(inst, qty)
        return targets


def run_weights(
    weights: pl.DataFrame,
    market: Market,
    *,
    date: str = "date",
    instruments: Mapping[str, Instrument] | None = None,
    capital: float = 1_000_000.0,
    start: dt.date | None = None,
    end: dt.date | None = None,
    delay: int = 0,
    costs: CostModel | None = None,
) -> Result:
    """Backtest the weight table on ``market``. ``instruments`` maps a column to a non-Cash
    instrument (default ``Cash(column)``). Rows dated off the market calendar raise, so a
    rebalance is never silently skipped."""
    strategy = TargetWeights(weights, date=date, instruments=instruments)
    calendar = set(market.dates)
    off = sorted(d for d in strategy.rows if d not in calendar)
    if off:
        raise ValueError(
            f"run_weights: {len(off)} weight row(s) on days with no market data, first {off[0]}"
        )
    return run(strategy, market, capital=capital, start=start, end=end, delay=delay, costs=costs)
