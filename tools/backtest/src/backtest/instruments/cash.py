"""Cash: an instrument worth its quoted price, converted into the market's currency.

Stocks, ETFs, indices, anything whose value is the number in ``Market``. ``currency`` is the
currency the price is quoted in; left out, it is the market's own. A price in another currency is
converted every day at that day's spot (``Market.rate``), so a day without the spot is a day
without a value.

Dividends: when ``market.extras["dividends"]`` is a ``Market`` holding this symbol, each
observation is the amount paid per unit on its ex-date, in the quote currency. Whoever held the
unit at the previous close receives it in cash on the ex-date (a short pays it), converted at the
last spot. Use it with unadjusted prices; with a total-return series, leave the extra out or set
``dividends=None``, or the dividend is counted twice.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backtest.instruments.base import Instrument
from backtest.market import Market


@dataclass(frozen=True)
class Cash(Instrument):
    """One unit is worth ``market.price(symbol, day)``, converted from ``currency``."""

    symbol: str
    currency: str | None = None
    dividends: str | None = "dividends"

    @property
    def id(self) -> str:
        return self.symbol

    def value(self, market: Market, day: dt.date) -> float | None:
        price = market.price(self.symbol, day)
        if price is None or self.currency in (None, market.currency):
            return price
        fx = market.rate(self.currency, market.currency, day)
        return None if fx is None else price * fx

    def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
        table = market.extras.get(self.dividends or "")
        if not isinstance(table, Market) or self.symbol not in table.symbols:
            return 0.0
        paid = sum(v for d, v in table.history(self.symbol, day) if d > prev_day)
        if not paid or self.currency is None or self.currency == market.currency:
            return paid
        fx = market.rate(self.currency, market.currency, day, asof=True)
        if fx is None:
            raise KeyError(f"Cash {self.symbol}: no {self.currency} spot on or before {day}")
        return paid * fx
