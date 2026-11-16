"""Cash: an instrument worth its quoted price, already in the reporting currency.

Stocks, ETFs, indices, anything whose value is the number in ``Market``. Dividends are not
modelled yet: feed a total-return series if they matter.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backtest.instruments.base import Instrument
from backtest.market import Market


@dataclass(frozen=True)
class Cash(Instrument):
    """One unit is worth ``market.price(symbol, day)``."""

    symbol: str

    @property
    def id(self) -> str:
        return self.symbol

    def value(self, market: Market, day: dt.date) -> float | None:
        return market.price(self.symbol, day)
