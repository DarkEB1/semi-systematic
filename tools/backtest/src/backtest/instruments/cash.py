"""Cash: an instrument worth its quoted price, converted into the market's currency.

Stocks, ETFs, indices, anything whose value is the number in ``Market``. ``currency`` is the
currency the price is quoted in; left out, it is the market's own. A price in another currency is
converted every day at that day's spot (``Market.rate``), so a day without the spot is a day
without a value. Dividends are not modelled yet: feed a total-return series if they matter.
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

    @property
    def id(self) -> str:
        return self.symbol

    def value(self, market: Market, day: dt.date) -> float | None:
        price = market.price(self.symbol, day)
        if price is None or self.currency in (None, market.currency):
            return price
        fx = market.rate(self.currency, market.currency, day)
        return None if fx is None else price * fx
