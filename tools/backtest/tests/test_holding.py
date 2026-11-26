"""What holding a position costs or pays between closes: short borrow and dividends."""

from __future__ import annotations

import datetime as dt

import pytest
from backtest import BorrowCost, BpsCost, Cash, Context, Market, Strategy, run

D1, D2, D3 = (dt.date(2026, 3, d) for d in (2, 3, 4))
SPY = {D1: 100.0, D2: 103.0, D3: 101.0}


class Fixed(Strategy):
    def __init__(self, plan: dict[dt.date, dict[object, float]]) -> None:
        self.plan = plan

    def on_day(self, ctx: Context) -> dict[object, float] | None:
        return self.plan.get(ctx.date)


def test_a_short_pays_borrow_on_the_previous_close() -> None:
    # 360 bp a year is 1 bp a calendar day: 1000 short costs 0.10, then 1030 short costs 0.103.
    res = run(
        Fixed({D1: {"SPY": -10}}),
        Market({"SPY": SPY}),
        capital=1000,
        costs=BorrowCost(360),
    )
    assert res.daily["cost"].to_list() == pytest.approx([0.0, 0.10, 0.103])
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, -30.10, 20.0 - 0.103])
    assert res.attribution()["cost"].to_list() == pytest.approx([-0.203])


def test_borrow_counts_calendar_days() -> None:
    friday, monday = dt.date(2026, 3, 6), dt.date(2026, 3, 9)
    market = Market({"SPY": {friday: 100.0, monday: 100.0}})
    res = run(Fixed({friday: {"SPY": -10}}), market, capital=1000, costs=BorrowCost(360))
    assert res.daily["cost"].to_list() == pytest.approx([0.0, 0.30])


def test_a_long_pays_no_borrow() -> None:
    res = run(Fixed({D1: {"SPY": 10}}), Market({"SPY": SPY}), capital=1000, costs=BorrowCost(360))
    assert res.daily["cost"].sum() == 0.0


def test_borrow_adds_to_a_trading_cost() -> None:
    costs = BpsCost(10) + BorrowCost({"SPY": 360})
    res = run(Fixed({D1: {"SPY": -10}}), Market({"SPY": SPY}), capital=1000, costs=costs)
    assert res.daily["cost"].to_list() == pytest.approx([1.0, 0.10, 0.103])


def test_a_short_without_a_borrow_rate_raises() -> None:
    with pytest.raises(KeyError, match="BorrowCost"):
        run(
            Fixed({D1: {"SPY": -10}}),
            Market({"SPY": SPY}),
            costs=BorrowCost({"QQQ": 50}),
        )


def test_a_negative_borrow_rate_raises() -> None:
    with pytest.raises(ValueError, match="BorrowCost"):
        BorrowCost(-1)


def dividends(amount: float) -> dict[str, Market]:
    return {"dividends": Market({"SPY": {D2: amount}})}


def test_a_long_receives_the_dividend_on_the_ex_date() -> None:
    market = Market({"SPY": SPY}, extras=dividends(0.5))
    res = run(Fixed({D1: {"SPY": 10}}), market, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, 35.0, -20.0])
    assert res.attribution()["cashflow"].to_list() == pytest.approx([5.0])


def test_a_short_pays_the_dividend() -> None:
    market = Market({"SPY": SPY}, extras=dividends(0.5))
    res = run(Fixed({D1: {"SPY": -10}}), market, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, -35.0, 20.0])


def test_bought_on_the_ex_date_gets_nothing() -> None:
    market = Market({"SPY": SPY}, extras=dividends(0.5))
    res = run(Fixed({D2: {"SPY": 10}}), market, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, 0.0, -20.0])


def test_a_foreign_dividend_is_converted_at_the_ex_date_spot() -> None:
    sap = Cash("SAP", currency="EUR")
    market = Market(
        {"SAP": SPY, "EURUSD": {D1: 1.0, D2: 1.2, D3: 1.2}},
        extras={"dividends": Market({"SAP": {D2: 0.5}})},
    )
    res = run(Fixed({D1: {sap: 10}}), market, capital=1000)
    assert res.attribution()["cashflow"].to_list() == pytest.approx([10 * 0.5 * 1.2])


def test_dividends_can_be_switched_off() -> None:
    spy = Cash("SPY", dividends=None)
    market = Market({"SPY": SPY}, extras=dividends(0.5))
    res = run(Fixed({D1: {spy: 10}}), market, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, 30.0, -20.0])
