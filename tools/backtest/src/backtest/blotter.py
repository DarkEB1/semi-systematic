"""run_blotter: replay trades that were actually made, through the engine's books.

The blotter is a table with one row per trade: ``date``, ``symbol``, ``quantity`` (signed units:
positive buys, negative sells), and optionally ``price``, ``idea`` and ``owner``. Nothing is
decided here, so there is no ``Strategy`` and no ``delay``: each row is filled on its date, at its
``price`` or, when that is null or the column is absent, at that day's close. The rest is the
engine's: cash plus marks, the cost model, cashflows, missing days.

``price`` is the value of one unit in the market's currency, the number ``Result.trades`` shows:
the traded price for a stock, ETF or index quoted in that currency. For anything else (an asset
quoted in another currency, an ``FxPair``, whose unit is described in ``instruments/fx.py``),
convert it or leave it null. A fill away from the close is marked to the close the same day, and
the difference is that day's price P&L of the instrument.

``idea`` and ``owner`` are copied onto ``Result.trades``; ``round_trips`` reads them from there.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from collections.abc import Mapping

import polars as pl

from backtest.costs import CostModel, NoCost
from backtest.engine import _Book, _Run
from backtest.instruments import Instrument
from backtest.market import Market
from backtest.result import Result
from backtest.strategy import as_instrument


def run_blotter(
    blotter: pl.DataFrame,
    market: Market,
    *,
    instruments: Mapping[str, Instrument] | None = None,
    capital: float = 1_000_000.0,
    start: dt.date | None = None,
    end: dt.date | None = None,
    costs: CostModel | None = None,
) -> Result:
    """The books of ``blotter`` on ``market``. ``instruments`` maps a symbol to a non-Cash
    instrument (default ``Cash(symbol)``). A trade dated off the days being run, with a zero
    quantity, or with neither a price nor a close that day raises: no trade is silently dropped.
    Rows of one day are filled in table order."""
    instruments = instruments or {}
    days = [d for d in market.dates if (start is None or d >= start) and (end is None or d <= end)]
    by_day: dict[dt.date, list[dict[str, object]]] = {}
    for row in blotter.iter_rows(named=True):
        day = row["date"].date() if isinstance(row["date"], dt.datetime) else row["date"]
        by_day.setdefault(day, []).append(row)
    off = sorted(set(by_day) - set(days))
    if off:
        raise ValueError(
            f"run_blotter: {len(off)} trade date(s) on days with no market data, first {off[0]}"
        )
    r = _Run(market=market, book=_Book(cash=capital), capital=capital, costs=costs or NoCost())
    tags: list[tuple[object, object]] = []
    prev: dt.date | None = None
    for day in days:
        r.revalue(prev, day)
        for row in by_day.get(day, []):
            symbol = str(row["symbol"])
            inst = instruments.get(symbol) or as_instrument(symbol)
            qty = float(row["quantity"])  # type: ignore[arg-type]
            if qty == 0:
                raise ValueError(f"run_blotter: zero quantity for {symbol} on {day}")
            close = inst.value(market, day)
            price = row.get("price")
            if price is None:
                if close is None:
                    raise ValueError(f"run_blotter: no price and no close for {symbol} on {day}")
                r.fill(inst, qty, close, day)
            else:  # no close today: the units join what is held at its last mark
                held = r.book.marks[inst] if inst in r.book.positions else None
                mark = close if close is not None else held
                r.fill(inst, qty, float(price), day, mark=mark)  # type: ignore[arg-type]
            tags.append((row.get("idea"), row.get("owner")))
        r.record(day)
        prev = day
    res = r.result()
    trades = res.trades.with_columns(
        pl.Series("idea", [t[0] for t in tags], dtype=pl.String),
        pl.Series("owner", [t[1] for t in tags], dtype=pl.String),
    )
    return dataclasses.replace(res, trades=trades)
