"""Instruments: the base contract and Cash."""

from __future__ import annotations

import datetime as dt

import pytest
from backtest import Cash, Instrument, Market

D1, D2, D3 = dt.date(2026, 3, 2), dt.date(2026, 3, 3), dt.date(2026, 3, 4)
MARKET = Market({"SPY": {D1: 100.0, D2: 103.0}})


def test_cash_is_worth_its_price() -> None:
    spy = Cash("SPY")
    assert spy.id == "SPY"
    assert spy.value(MARKET, D1) == 100.0
    v1, v2 = spy.value(MARKET, D1), spy.value(MARKET, D2)
    assert v1 is not None and v2 is not None
    assert v2 / v1 - 1 == pytest.approx(0.03)


def test_cash_missing_day_is_none() -> None:
    assert Cash("SPY").value(MARKET, D3) is None


def test_cash_pays_no_cashflow() -> None:
    assert Cash("SPY").cashflow(MARKET, D1, D2) == 0.0


def test_instruments_are_hashable_and_compare_by_value() -> None:
    # Positions are keyed by instrument: two Cash("SPY") must be the same key.
    positions = {Cash("SPY"): 10.0}
    assert positions[Cash("SPY")] == 10.0
    assert Cash("SPY") != Cash("QQQ")


def test_instrument_is_abstract() -> None:
    with pytest.raises(TypeError):
        Instrument()  # type: ignore[abstract]


def test_a_new_asset_class_is_just_a_subclass() -> None:
    class Constant(Instrument):
        @property
        def id(self) -> str:
            return "ONE"

        def value(self, market: Market, day: dt.date) -> float | None:
            return 1.0

    assert Constant().value(MARKET, D1) == 1.0
