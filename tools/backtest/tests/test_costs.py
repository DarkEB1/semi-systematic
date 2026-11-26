"""Costs: the models on their own, then charged by the engine. Every number is by hand."""

from __future__ import annotations

import datetime as dt

import pytest
from backtest import (
    BpsCost,
    Cash,
    Context,
    CostModel,
    Instrument,
    Market,
    NoCost,
    PerUnitCost,
    Result,
    Strategy,
    run,
)

D1, D2, D3 = (dt.date(2026, 3, d) for d in (2, 3, 4))
SPY = {D1: 100.0, D2: 103.0, D3: 101.0}
FLAT = {D1: 100.0, D2: 100.0, D3: 100.0}


class Fixed(Strategy):
    def __init__(self, plan: dict[dt.date, dict[str, float]]) -> None:
        self.plan = plan

    def on_day(self, ctx: Context) -> dict[str, float] | None:
        return self.plan.get(ctx.date)


def cost_of(model: CostModel, symbol: str, qty: float, price: float) -> float:
    return model.cost(Cash(symbol), qty, price, D1)


# --- the models -----------------------------------------------------------------------------


def test_bps_on_traded_notional() -> None:
    assert cost_of(BpsCost(5), "SPY", 10, 100) == pytest.approx(0.5)  # 1000 * 5bp
    assert cost_of(BpsCost(5), "SPY", -10, 100) == pytest.approx(0.5)  # selling costs too


def test_bps_per_instrument_and_default() -> None:
    model = BpsCost({"EURUSD": 1, "USDBRL": 5}, default=15)
    assert cost_of(model, "EURUSD", 1_000_000, 1) == pytest.approx(100.0)
    assert cost_of(model, "USDBRL", 1_000_000, 1) == pytest.approx(500.0)
    assert cost_of(model, "USDTRY", 1_000_000, 1) == pytest.approx(1500.0)


def test_unlisted_instrument_without_default_raises() -> None:
    with pytest.raises(KeyError, match="'USDTRY'"):
        cost_of(BpsCost({"EURUSD": 1}), "USDTRY", 1, 1)


def test_by_bucket() -> None:
    model = BpsCost.by_bucket(
        {"EURUSD": "G10", "USDBRL": "EM_LIQUID", "USDNGN": "EM_OTHER"},
        {"G10": 1, "EM_LIQUID": 5, "EM_OTHER": 15},
    )
    assert cost_of(model, "USDBRL", 10_000, 1) == pytest.approx(5.0)
    assert cost_of(model, "USDNGN", 10_000, 1) == pytest.approx(15.0)


def test_by_bucket_rejects_a_bucket_without_bps() -> None:
    with pytest.raises(KeyError, match="EM_OTHER"):
        BpsCost.by_bucket({"USDNGN": "EM_OTHER"}, {"G10": 1})


def test_per_unit() -> None:
    assert cost_of(PerUnitCost(0.10), "SPY", -10, 100) == pytest.approx(1.0)
    assert cost_of(PerUnitCost({"ES": 2.5}), "ES", 4, 5000) == pytest.approx(10.0)


def test_models_add_up() -> None:
    model = BpsCost(5) + PerUnitCost(0.10)
    assert cost_of(model, "SPY", 10, 100) == pytest.approx(0.5 + 1.0)


def test_negative_costs_rejected() -> None:
    with pytest.raises(ValueError):
        BpsCost(-1)
    with pytest.raises(ValueError):
        PerUnitCost({"ES": -2})


def test_no_cost() -> None:
    assert cost_of(NoCost(), "SPY", 10, 100) == 0.0


# --- charged by the engine ------------------------------------------------------------------


def test_round_trip_costs_twice_the_half_spread() -> None:
    res = run(Fixed({D1: {"SPY": 10}, D2: {}}), Market({"SPY": FLAT}), capital=1000,
              costs=BpsCost(5))  # fmt: skip
    assert res.trades["cost"].to_list() == pytest.approx([0.5, 0.5])
    assert res.daily["nav"][-1] == pytest.approx(1000 - 2 * 0.5)


def test_three_day_example_with_spread() -> None:
    # The worked example: buy 10 at 100, hold through 103, sell at 101; 0.10 per share each way.
    plan = {D1: {"SPY": 10}, D3: {}}
    res = run(Fixed(plan), Market({"SPY": SPY}), capital=1000, costs=PerUnitCost(0.10))
    assert res.daily["pnl"].to_list() == pytest.approx([-1.0, 30.0, -21.0])
    assert res.daily["nav"][-1] == pytest.approx(1008.0)


def test_daily_columns_report_traded_and_cost() -> None:
    plan = {D1: {"SPY": 10}, D2: {"SPY": 4}}
    res = run(Fixed(plan), Market({"SPY": SPY}), capital=1000, costs=BpsCost(10))
    assert res.daily["traded"].to_list() == pytest.approx([1000.0, 618.0, 0.0])
    assert res.daily["cost"].to_list() == pytest.approx([1.0, 0.618, 0.0])
    assert res.daily["cost"].sum() == pytest.approx(res.trades["cost"].sum())


def test_gross_minus_costs_is_net() -> None:
    plan = {D1: {"SPY": 10}, D2: {"SPY": -10}, D3: {}}
    free = run(Fixed(plan), Market({"SPY": SPY}), capital=1000)
    paid = run(Fixed(plan), Market({"SPY": SPY}), capital=1000, costs=BpsCost(5))
    diff = free.daily["nav"] - paid.daily["nav"]
    assert diff[-1] == pytest.approx(paid.trades["cost"].sum())
    assert pnl_sum(paid) == pytest.approx(pnl_sum(free) - paid.trades["cost"].sum())


def pnl_sum(res: Result) -> float:
    return float(res.daily["pnl"].sum())


def test_negative_cost_from_a_custom_model_raises() -> None:
    class Rebate(CostModel):
        def cost(
            self, instrument: Instrument, quantity: float, price: float, day: dt.date
        ) -> float:
            return -1.0

    with pytest.raises(ValueError, match="negative cost"):
        run(Fixed({D1: {"SPY": 1}}), Market({"SPY": SPY}), costs=Rebate())


def test_missing_cost_entry_fails_the_run() -> None:
    with pytest.raises(KeyError, match="'SPY'"):
        run(Fixed({D1: {"SPY": 1}}), Market({"SPY": SPY}), costs=BpsCost({"QQQ": 1}))
