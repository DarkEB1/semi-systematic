"""FxPair: a spot FX position against USD, with carry paid as a daily cashflow.

The market symbol is the pair as quoted (``EURUSD`` = USD per EUR, ``USDBRL`` = BRL per USD), and
being long the pair means long the base currency, short the quote. One unit is one unit of the
non-USD currency, held or owed, so its value is always in USD:

- ``xxxUSD`` (EURUSD): one unit is 1 EUR held, worth ``S`` USD. P&L per unit ``S1 - S0``.
- ``USDxxx`` (USDBRL): one unit is 1 BRL owed, worth ``-1/S`` USD. Buying a unit borrows 1 BRL and
  sells it for ``1/S`` USD; P&L per unit ``1/S0 - 1/S1``, which per dollar of exposure is the
  USD return of a long USDBRL, ``1 - S0/S1`` (not ``S1/S0 - 1``).

Each unit's exposure is ``|value|``, so a weight of +0.5 on USDBRL is long USD against BRL for
half the NAV, as it reads.

Carry: long base, short quote earns ``exposure * (r_base - r_quote) / 100 * days / day_count``
from one close to the next, with the rates known at the earlier close (the last observation on or
before it). Rates are annual percentages in a ``Market`` stored in ``market.extras[rates]``, one
symbol per currency (``USD``, ``BRL`` ...). Simple accrual on ``day_count`` (360) for every
currency is an approximation: BRL's CDI compounds on 252 business days. ``rates=None`` is spot
only. Crosses without USD (EURJPY) are not supported yet.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backtest.instruments.base import Instrument
from backtest.market import Market

USD = "USD"


@dataclass(frozen=True)
class FxPair(Instrument):
    """Spot ``symbol`` against USD; carry from ``market.extras[rates]`` unless ``rates`` is None."""

    symbol: str
    rates: str | None = "rates"
    day_count: float = 360.0

    def __post_init__(self) -> None:
        s = self.symbol
        if len(s) != 6 or not s.isalpha() or not s.isupper():
            raise ValueError(f"FxPair: {s!r} is not a six-letter pair such as 'USDBRL'")
        if USD not in (s[:3], s[3:]) or s[:3] == s[3:]:
            raise ValueError(f"FxPair: {s!r} has no USD leg; crosses are not supported yet")

    @property
    def id(self) -> str:
        return self.symbol

    @property
    def base(self) -> str:
        return self.symbol[:3]

    @property
    def quote(self) -> str:
        return self.symbol[3:]

    def _unit(self, spot: float) -> float:
        return -1.0 / spot if self.base == USD else spot

    def value(self, market: Market, day: dt.date) -> float | None:
        spot = market.price(self.symbol, day)
        return None if spot is None else self._unit(spot)

    def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
        if self.rates is None:
            return 0.0
        spot = _last(market, self.symbol, prev_day, f"FxPair {self.symbol}: no spot")
        diff = self._rate(market, self.base, prev_day) - self._rate(market, self.quote, prev_day)
        return self.exposure(self._unit(spot)) * diff / 100 * (day - prev_day).days / self.day_count

    def _rate(self, market: Market, currency: str, day: dt.date) -> float:
        rates = market.extras.get(self.rates or "")
        if not isinstance(rates, Market):
            raise KeyError(f"FxPair {self.symbol}: market.extras[{self.rates!r}] is not a Market")
        if currency not in rates.symbols:
            raise KeyError(f"FxPair {self.symbol}: no {currency} rate in extras[{self.rates!r}]")
        return _last(rates, currency, day, f"FxPair {self.symbol}: no {currency} rate")


def _last(market: Market, symbol: str, day: dt.date, what: str) -> float:
    """The last observation of ``symbol`` on or before ``day``."""
    hist = market.history(symbol, day, lookback=1)
    if not hist:
        raise KeyError(f"{what} on or before {day}")
    return hist[-1][1]
