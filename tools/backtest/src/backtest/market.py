"""Market: the data an instrument reads to value itself, one observation per symbol per day.

Built from a long table (``date, symbol, close``) or a wide one (``date`` plus one column per
symbol). A missing observation stays missing: ``price`` returns ``None`` and the engine books the
move on the next observed day, never a zero return. Anything else an instrument needs (rates, vol
surfaces, curves) travels in ``extras``, keyed by name.

``currency`` is the accounting currency: every instrument values itself in it, so the NAV is one
sum. ``rate(a, b, day)`` converts between currencies from the FX spots the market holds (the pair
either way round, or through USD when neither currency is USD).

``MarketView`` is the same data seen from one day: asking for a later day raises
``LookaheadError``. The engine hands strategies a view, never the market itself.
"""

from __future__ import annotations

import bisect
import datetime as dt
from collections.abc import Mapping
from typing import Any

import polars as pl

USD = "USD"


class LookaheadError(LookupError):
    """A strategy asked for data after the day it is deciding on."""


class Market:
    """Prices by symbol and day, plus named extras. Read-only once built."""

    def __init__(
        self,
        prices: Mapping[str, Mapping[dt.date, float]],
        extras: Mapping[str, Any] | None = None,
        currency: str = USD,
    ) -> None:
        self.currency = currency
        self._prices = {s: dict(obs) for s, obs in prices.items()}
        self._sorted = {s: sorted(obs) for s, obs in self._prices.items()}
        self.extras: dict[str, Any] = dict(extras or {})
        self.dates: list[dt.date] = sorted({d for obs in self._prices.values() for d in obs})

    @classmethod
    def from_long(
        cls,
        df: pl.DataFrame,
        *,
        date: str = "date",
        symbol: str = "symbol",
        value: str = "close",
        extras: Mapping[str, Any] | None = None,
        currency: str = USD,
    ) -> Market:
        """One row per (date, symbol). Null values are dropped; a duplicate (date, symbol) raises."""
        df = df.select(date, symbol, value).drop_nulls(value)
        if df.select(pl.struct(date, symbol).is_duplicated().any()).item():
            raise ValueError("Market.from_long: duplicate (date, symbol) rows")
        prices: dict[str, dict[dt.date, float]] = {}
        for d, s, v in df.iter_rows():
            prices.setdefault(s, {})[_as_date(d)] = float(v)
        return cls(prices, extras, currency)

    @classmethod
    def from_wide(
        cls,
        df: pl.DataFrame,
        *,
        date: str = "date",
        extras: Mapping[str, Any] | None = None,
        currency: str = USD,
    ) -> Market:
        """A ``date`` column plus one numeric column per symbol; nulls are missing observations."""
        long = df.unpivot(index=date, variable_name="symbol", value_name="close")
        return cls.from_long(long, date=date, extras=extras, currency=currency)

    @property
    def symbols(self) -> list[str]:
        return sorted(self._prices)

    def price(self, symbol: str, day: dt.date) -> float | None:
        """The observation for ``symbol`` on ``day``, or ``None`` if that day has none."""
        return self._obs(symbol).get(day)

    def history(
        self, symbol: str, until: dt.date, lookback: int | None = None
    ) -> list[tuple[dt.date, float]]:
        """Observed ``(date, price)`` pairs for ``symbol`` up to ``until`` inclusive, oldest first;
        the last ``lookback`` of them when given."""
        obs = self._obs(symbol)
        days = self._sorted[symbol]
        end = bisect.bisect_right(days, until)
        start = 0 if lookback is None else max(0, end - lookback)
        return [(d, obs[d]) for d in days[start:end]]

    def rate(self, base: str, quote: str, day: dt.date, *, asof: bool = False) -> float | None:
        """Units of ``quote`` per unit of ``base`` on ``day``, from the ``basequote`` or
        ``quotebase`` spot, else through USD. ``None`` if a spot is unobserved that day; with
        ``asof``, the last observation on or before ``day``. No spot at all raises ``KeyError``."""
        if base == quote:
            return 1.0
        for symbol, inverse in ((base + quote, False), (quote + base, True)):
            if symbol in self._prices:
                spot = self._at(symbol, day, asof)
                return None if spot is None else (1 / spot if inverse else spot)
        if USD in (base, quote):
            raise KeyError(f"Market: no {base}{quote} or {quote}{base} spot to convert {base}")
        legs = self.rate(base, USD, day, asof=asof), self.rate(USD, quote, day, asof=asof)
        return None if None in legs else legs[0] * legs[1]  # type: ignore[operator]

    def _at(self, symbol: str, day: dt.date, asof: bool) -> float | None:
        if not asof:
            return self.price(symbol, day)
        hist = self.history(symbol, day, lookback=1)
        return hist[-1][1] if hist else None

    def view(self, day: dt.date) -> MarketView:
        """The market as known at the close of ``day``."""
        return MarketView(self, day)

    def _obs(self, symbol: str) -> dict[dt.date, float]:
        try:
            return self._prices[symbol]
        except KeyError:
            raise KeyError(f"Market: unknown symbol {symbol!r}") from None


class MarketView:
    """``Market`` frozen at the close of ``today``: no observation after it is reachable.

    ``extras`` is passed through unguarded: a strategy that reads a dated extra must index it at
    ``today`` or earlier itself.
    """

    def __init__(self, market: Market, today: dt.date) -> None:
        self._market = market
        self.today = today
        self.extras = market.extras
        self.currency = market.currency

    @property
    def symbols(self) -> list[str]:
        return self._market.symbols

    def price(self, symbol: str, day: dt.date | None = None) -> float | None:
        """Observation on ``day`` (default today). A later day raises ``LookaheadError``."""
        day = day or self.today
        if day > self.today:
            raise LookaheadError(f"price({symbol!r}, {day}) asked on {self.today}")
        return self._market.price(symbol, day)

    def rate(self, base: str, quote: str, day: dt.date | None = None) -> float | None:
        """``Market.rate`` on ``day`` (default today). A later day raises ``LookaheadError``."""
        day = day or self.today
        if day > self.today:
            raise LookaheadError(f"rate({base!r}, {quote!r}, {day}) asked on {self.today}")
        return self._market.rate(base, quote, day)

    def history(self, symbol: str, lookback: int | None = None) -> list[tuple[dt.date, float]]:
        """Observed ``(date, price)`` pairs up to today, oldest first."""
        return self._market.history(symbol, self.today, lookback)

    def closes(self, symbol: str, lookback: int | None = None) -> list[float]:
        """Just the prices of ``history``."""
        return [v for _, v in self.history(symbol, lookback)]


def _as_date(v: dt.date | dt.datetime) -> dt.date:
    return v.date() if isinstance(v, dt.datetime) else v
