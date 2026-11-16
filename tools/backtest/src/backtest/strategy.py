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

# Keys are instruments or symbol strings; Mapping is invariant in its key, so all three spellings.
Targets = Mapping[Instrument, float] | Mapping[str, float] | Mapping[Instrument | str, float]


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

    def quantities(self, weights: Targets) -> dict[Instrument, float]:
        """Weights (fractions of today's NAV) as target quantities: ``weight * nav / exposure``
        (``exposure`` is the instrument's per-unit exposure at today's value, ``|value|`` for most).

        A zero weight is a zero quantity (the engine fills it at the next observed price). Any
        other weight on an instrument with no value today cannot be sized, so it keeps its
        current quantity.
        """
        out: dict[Instrument, float] = {}
        for key, w in weights.items():
            inst = as_instrument(key)
            if w == 0:
                out[inst] = 0.0
                continue
            v = self.value(inst)
            if v is None:
                out[inst] = self.position(inst)
            elif inst.exposure(v) == 0:
                raise ValueError(f"cannot size {inst.id} on {self.date}: its exposure is zero")
            else:
                out[inst] = w * self.nav / inst.exposure(v)
        return out


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
