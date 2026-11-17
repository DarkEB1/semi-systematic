"""FxPair: a spot FX position, with carry paid as a daily cashflow.

The market symbol is the pair as quoted (``EURUSD`` = USD per EUR, ``USDBRL`` = BRL per USD), and
being long the pair means long the base currency, short the quote. Values are in the market's
accounting currency (``market.currency``, USD by default; "rep" below).

**A pair with a rep leg** is held as itself. One unit is one unit of its other currency, held or
owed, so its value is in rep:

- ``xxxREP`` (EURUSD in USD): one unit is 1 EUR held, worth ``S``. P&L per unit ``S1 - S0``.
- ``REPxxx`` (USDBRL in USD): one unit is 1 BRL owed, worth ``-1/S``. Buying a unit borrows 1 BRL
  and sells it for ``1/S``; per unit of exposure the P&L is ``1 - S0/S1`` (not ``S1/S0 - 1``).

Each unit's exposure is ``|value|``, so a weight of +0.5 on USDBRL is long USD against BRL for
half the NAV, as it reads.

**A cross** (no rep leg: EURJPY in USD) is held as its two legs against rep, sized by
``split``: long EURJPY for N of exposure is long EURUSD and long USDJPY for N each (the pairs as
the market quotes them). The positions, trades and attribution show the legs; the carry adds up
to ``r_EUR - r_JPY``. The JPY owed is fixed when the legs are sized, so a gain stays in the
position (and moves with USDJPY) until a rebalance resizes the legs and banks it. A cross cannot
be held directly; size it through weights (``ctx.quantities``, ``run_weights``).

Carry: long base, short quote earns ``exposure * (r_base - r_quote) / 100 * days / day_count``
from one close to the next, with the rates known at the earlier close (the last observation on or
before it). Rates are annual percentages in a ``Market`` stored in ``market.extras[rates]``, one
symbol per currency (``USD``, ``BRL`` ...). Simple accrual on ``day_count`` (360) for every
currency is an approximation: BRL's CDI compounds on 252 business days. ``rates=None`` is spot
only.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backtest.instruments.base import Instrument
from backtest.market import Market


@dataclass(frozen=True)
class FxPair(Instrument):
    """Spot ``symbol``; carry from ``market.extras[rates]`` unless ``rates`` is None."""

    symbol: str
    rates: str | None = "rates"
    day_count: float = 360.0

    def __post_init__(self) -> None:
        s = self.symbol
        if len(s) != 6 or not s.isalpha() or not s.isupper() or s[:3] == s[3:]:
            raise ValueError(f"FxPair: {s!r} is not a six-letter pair such as 'USDBRL'")

    @property
    def id(self) -> str:
        return self.symbol

    @property
    def base(self) -> str:
        return self.symbol[:3]

    @property
    def quote(self) -> str:
        return self.symbol[3:]

    def is_cross(self, market: Market) -> bool:
        return market.currency not in (self.base, self.quote)

    def _unit(self, market: Market, spot: float) -> float:
        if self.is_cross(market):
            raise TypeError(
                f"FxPair {self.symbol} is a cross in {market.currency}: it is held as its two "
                "legs, so size it through weights (ctx.quantities or run_weights)"
            )
        return -1.0 / spot if self.base == market.currency else spot

    def value(self, market: Market, day: dt.date) -> float | None:
        spot = market.price(self.symbol, day)
        return None if spot is None else self._unit(market, spot)

    def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
        if self.rates is None:
            return 0.0
        spot = _last(market, self.symbol, prev_day, f"FxPair {self.symbol}: no spot")
        diff = self._rate(market, self.base, prev_day) - self._rate(market, self.quote, prev_day)
        unit = self.exposure(self._unit(market, spot))
        return unit * diff / 100 * (day - prev_day).days / self.day_count

    def split(
        self, market: Market, day: dt.date, notional: float
    ) -> dict[Instrument, float | None] | None:
        """A cross: long base and short quote, each for ``notional`` of exposure, through the
        pairs against the accounting currency. Not a cross: ``None`` (held as itself)."""
        if not self.is_cross(market):
            return None
        return self._leg(market, day, self.base, notional) | self._leg(
            market, day, self.quote, -notional
        )

    def _leg(
        self, market: Market, day: dt.date, ccy: str, notional: float
    ) -> dict[Instrument, float | None]:
        """Quantity of the ``ccy``-against-rep pair holding ``notional`` of ``ccy`` (owed if
        negative). That pair's unit is 1 ``ccy`` held when ``ccy`` is its base, owed otherwise."""
        rep = market.currency
        symbol = next((s for s in (ccy + rep, rep + ccy) if s in market.symbols), None)
        if symbol is None:
            raise KeyError(
                f"FxPair {self.symbol}: no {ccy}{rep} or {rep}{ccy} spot for its {ccy} leg"
            )
        leg = FxPair(symbol, rates=self.rates, day_count=self.day_count)
        v = leg.value(market, day)
        if v is None:
            return {leg: None}
        held = 1.0 if symbol.startswith(ccy) else -1.0
        return {leg: held * notional / leg.exposure(v)}

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
