"""Cost models: what a fill costs, in the reporting currency, always >= 0.

The engine asks ``cost(instrument, quantity, price, day)`` at every fill and takes the answer out
of cash. Two models cover most uses and add up with ``+``:

- ``BpsCost``: a fraction of the traded notional ``|quantity * price|``, in basis points, per
  instrument id or per bucket (the flat half-spread of the conventions: G10, liquid EM, rest).
- ``PerUnitCost``: a fixed amount per unit traded (per option or futures contract).

The numbers are the experiment's (``config.yaml`` ``params``), never this package's. Anything
else (a cost in vol points times vega, a size-dependent impact) is a ``CostModel`` subclass.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Mapping

from backtest.instruments import Instrument


class CostModel(ABC):
    """What one fill costs. Implement ``cost``; combine models with ``+``."""

    @abstractmethod
    def cost(self, instrument: Instrument, quantity: float, price: float, day: dt.date) -> float:
        """Cost of trading ``quantity`` units (signed) at ``price`` on ``day``; never negative."""

    def __add__(self, other: CostModel) -> CostModel:
        return _Sum((self, other))


class NoCost(CostModel):
    """Free trading: the engine's default, for checking a strategy before costs."""

    def cost(self, instrument: Instrument, quantity: float, price: float, day: dt.date) -> float:
        return 0.0


class _Sum(CostModel):
    def __init__(self, parts: tuple[CostModel, ...]) -> None:
        self.parts = parts

    def cost(self, instrument: Instrument, quantity: float, price: float, day: dt.date) -> float:
        return sum(p.cost(instrument, quantity, price, day) for p in self.parts)


def _rate(table: Mapping[str, float], key: str, default: float | None, what: str) -> float:
    if key in table:
        return table[key]
    if default is None:
        raise KeyError(f"{what}: no cost for {key!r} and no default")
    return default


def _check(values: Mapping[str, float], default: float | None, what: str) -> None:
    if any(v < 0 for v in values.values()) or (default is not None and default < 0):
        raise ValueError(f"{what}: costs must be >= 0")


class BpsCost(CostModel):
    """``|quantity * price| * bps / 10_000``.

    ``BpsCost(5)`` charges 5 bp on everything. ``BpsCost({"EURUSD": 1, "USDBRL": 5})`` charges per
    instrument id; ``default`` covers ids not listed (otherwise they raise, so a forgotten
    instrument never trades for free). ``BpsCost.by_bucket`` maps ids to buckets first.
    """

    def __init__(self, bps: float | Mapping[str, float], *, default: float | None = None) -> None:
        if isinstance(bps, int | float):
            self.bps: dict[str, float] = {}
            self.default: float | None = float(bps)
        else:
            self.bps = {k: float(v) for k, v in bps.items()}
            self.default = default
        _check(self.bps, self.default, "BpsCost")

    @classmethod
    def by_bucket(
        cls,
        buckets: Mapping[str, str],
        bps: Mapping[str, float],
        *,
        default: float | None = None,
    ) -> BpsCost:
        """``buckets`` maps instrument id to bucket, ``bps`` bucket to basis points."""
        unknown = sorted(set(buckets.values()) - set(bps))
        if unknown:
            raise KeyError(f"BpsCost.by_bucket: no bps for bucket(s) {unknown}")
        return cls({i: bps[b] for i, b in buckets.items()}, default=default)

    def cost(self, instrument: Instrument, quantity: float, price: float, day: dt.date) -> float:
        bps = _rate(self.bps, instrument.id, self.default, "BpsCost")
        return abs(quantity * price) * bps / 10_000


class PerUnitCost(CostModel):
    """``|quantity| * amount``: a fixed cost per unit (contract) traded, per instrument id."""

    def __init__(
        self, amount: float | Mapping[str, float], *, default: float | None = None
    ) -> None:
        if isinstance(amount, int | float):
            self.amount: dict[str, float] = {}
            self.default: float | None = float(amount)
        else:
            self.amount = {k: float(v) for k, v in amount.items()}
            self.default = default
        _check(self.amount, self.default, "PerUnitCost")

    def cost(self, instrument: Instrument, quantity: float, price: float, day: dt.date) -> float:
        return abs(quantity) * _rate(self.amount, instrument.id, self.default, "PerUnitCost")
