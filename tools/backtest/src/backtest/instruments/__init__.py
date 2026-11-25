"""Instrument types the engine can hold: one module per asset class, not per asset."""

from __future__ import annotations

from backtest.instruments.base import Instrument
from backtest.instruments.cash import Cash
from backtest.instruments.fx import FxPair

__all__ = ["Cash", "FxPair", "Instrument"]
