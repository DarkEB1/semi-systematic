"""Result: what a backtest returns, as polars tables.

``daily``: one row per day (``date, nav, pnl, cash, gross, net, traded, cost``); ``pnl`` is after
costs, ``traded`` the absolute notional filled that day. ``positions``: holdings after each close
(``date, instrument, quantity, value``). ``trades``: every fill (``date, instrument, quantity,
price, cost``).
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class Result:
    daily: pl.DataFrame
    positions: pl.DataFrame
    trades: pl.DataFrame
    capital: float

    @property
    def returns(self) -> pl.Series:
        """Simple daily returns of the NAV (the first day's against the starting capital)."""
        nav = self.daily["nav"]
        prev = nav.shift(1).fill_null(self.capital)
        return (nav / prev - 1).alias("ret")
