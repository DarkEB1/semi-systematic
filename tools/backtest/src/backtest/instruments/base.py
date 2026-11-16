"""Instrument: what the engine asks of anything it can hold.

Two questions only. ``value``: what one unit is worth on a day, in the reporting currency
(``None`` when the market has no observation that day). ``cashflow``: what one unit paid or cost
between two consecutive valuation days (dividends, carry, coupons, an expiry payoff); zero by
default. The engine never knows what kind of asset it holds; adding an asset class is a new
subclass, never a change to the engine.

Subclasses are frozen dataclasses, so an instrument is hashable and can key a position.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from backtest.market import Market


class Instrument(ABC):
    """Anything the engine can hold. ``id`` names it in positions, trades and results."""

    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    def value(self, market: Market, day: dt.date) -> float | None:
        """Value of one unit on ``day`` in the reporting currency; ``None`` if unobserved."""

    def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
        """Cash paid to (positive) or by (negative) one unit held from ``prev_day`` to ``day``."""
        return 0.0
