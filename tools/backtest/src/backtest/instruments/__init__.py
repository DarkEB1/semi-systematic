"""Instrument types the engine can hold: one module per asset class, not per asset."""

from __future__ import annotations

from backtest.instruments.base import Instrument
from backtest.instruments.cash import Cash

__all__ = ["Cash", "Instrument"]
