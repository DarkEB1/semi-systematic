"""Strategy: the user's code. The engine calls ``on_day`` at every close and holds what it returns.

``on_day(ctx)`` returns the target quantity of each instrument to hold after today's close. An
instrument left out of the answer is closed; return ``None`` to keep every position unchanged.
A plain string key means ``Cash(key)``. The strategy may keep any state it likes on ``self``
(open trades, entry dates, signals): the engine never touches it.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from backtest.instruments import Cash, Instrument
from backtest.market import Market, MarketView

Targets = Mapping[Instrument | str, float]


@dataclass(frozen=True)
class Context:
    """What a strategy sees at the close of ``date``. Nothing in it reaches past ``date``."""

    date: dt.date
    market: MarketView
    positions: Mapping[Instrument, float]
    cash: float
    nav: float
    _full: Market

    def value(self, instrument: Instrument) -> float | None:
        """Today's value of one unit of ``instrument`` (``None`` if unobserved today)."""
        return instrument.value(self._full, self.date)

    def position(self, instrument: Instrument | str) -> float:
        """Quantity held now, zero if none."""
        return self.positions.get(as_instrument(instrument), 0.0)


class Strategy(ABC):
    """Subclass it and implement ``on_day``."""

    def on_start(self, ctx: Context) -> None:  # noqa: B027 - optional hook
        """Called once, at the first close, before the first ``on_day``."""

    @abstractmethod
    def on_day(self, ctx: Context) -> Targets | None:
        """Target quantities to hold after this close, or ``None`` to change nothing."""


def as_instrument(key: Instrument | str) -> Instrument:
    """A string is shorthand for ``Cash(string)``."""
    return Cash(key) if isinstance(key, str) else key
