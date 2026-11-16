"""Market: the data an instrument reads to value itself, one observation per symbol per day.

Built from a long table (``date, symbol, close``) or a wide one (``date`` plus one column per
symbol). A missing observation stays missing: ``price`` returns ``None`` and the engine books the
move on the next observed day, never a zero return. Anything else an instrument needs (rates, vol
surfaces, curves) travels in ``extras``, keyed by name.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

import polars as pl


class Market:
    """Prices by symbol and day, plus named extras. Read-only once built."""

    def __init__(
        self,
        prices: Mapping[str, Mapping[dt.date, float]],
        extras: Mapping[str, Any] | None = None,
    ) -> None:
        self._prices = {s: dict(obs) for s, obs in prices.items()}
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
    ) -> Market:
        """One row per (date, symbol). Null values are dropped; a duplicate (date, symbol) raises."""
        df = df.select(date, symbol, value).drop_nulls(value)
        if df.select(pl.struct(date, symbol).is_duplicated().any()).item():
            raise ValueError("Market.from_long: duplicate (date, symbol) rows")
        prices: dict[str, dict[dt.date, float]] = {}
        for d, s, v in df.iter_rows():
            prices.setdefault(s, {})[_as_date(d)] = float(v)
        return cls(prices, extras)

    @classmethod
    def from_wide(
        cls,
        df: pl.DataFrame,
        *,
        date: str = "date",
        extras: Mapping[str, Any] | None = None,
    ) -> Market:
        """A ``date`` column plus one numeric column per symbol; nulls are missing observations."""
        long = df.unpivot(index=date, variable_name="symbol", value_name="close")
        return cls.from_long(long, date=date, extras=extras)

    @property
    def symbols(self) -> list[str]:
        return sorted(self._prices)

    def price(self, symbol: str, day: dt.date) -> float | None:
        """The observation for ``symbol`` on ``day``, or ``None`` if that day has none."""
        try:
            obs = self._prices[symbol]
        except KeyError:
            raise KeyError(f"Market: unknown symbol {symbol!r}") from None
        return obs.get(day)


def _as_date(v: dt.date | dt.datetime) -> dt.date:
    return v.date() if isinstance(v, dt.datetime) else v
