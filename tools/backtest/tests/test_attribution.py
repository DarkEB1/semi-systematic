"""Attribution: the day's P&L split by instrument and cause must add back to the total."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import polars as pl
import pytest
from backtest import BpsCost, Context, Instrument, Market, PerUnitCost, Strategy, run

D1, D2, D3 = (dt.date(2026, 3, d) for d in (2, 3, 4))
SPY = {D1: 100.0, D2: 103.0, D3: 101.0}
QQQ = {D1: 50.0, D2: 48.0, D3: 51.0}


def assert_rows(df: pl.DataFrame, expected: list[tuple[str, float, float, float]]) -> None:
    """Same instruments in the same order, numbers equal to float precision."""
    got = df.rows()
    assert [r[0] for r in got] == [e[0] for e in expected]
    assert [x for r in got for x in r[1:]] == pytest.approx([x for e in expected for x in e[1:]])


class Fixed(Strategy):
    def __init__(self, plan: dict[dt.date, dict[str, float]]) -> None:
        self.plan = plan

    def on_day(self, ctx: Context) -> dict[str, float] | None:
        return self.plan.get(ctx.date)


def test_each_cause_lands_on_its_instrument() -> None:
    # Long 10 SPY, short 5 QQQ from Monday, 0.10 per unit traded.
    plan = {D1: {"SPY": 10, "QQQ": -5}}
    res = run(Fixed(plan), Market({"SPY": SPY, "QQQ": QQQ}), costs=PerUnitCost(0.10), delay=0)
    tue = res.pnl.filter(pl.col("date") == D2).sort("instrument")
    assert_rows(
        tue.select("instrument", "price", "cost", "pnl"),
        [("QQQ", 10.0, 0.0, 10.0), ("SPY", 30.0, 0.0, 30.0)],
    )
    mon = res.pnl.filter(pl.col("date") == D1).sort("instrument")
    assert mon["cost"].to_list() == pytest.approx([-0.5, -1.0])  # 5 and 10 units at 0.10


def test_attribution_adds_back_to_the_daily_pnl() -> None:
    plan = {D1: {"SPY": 10, "QQQ": -5}, D2: {"SPY": 4, "QQQ": 3}, D3: {}}
    res = run(
        Fixed(plan), Market({"SPY": SPY, "QQQ": QQQ}), capital=1000, costs=BpsCost(7), delay=0
    )
    per_day = res.pnl.group_by("date").agg(pl.col("pnl").sum()).sort("date")
    check = res.daily.select("date", "pnl").join(per_day, on="date", suffix="_split")
    for total, split in check.select("pnl", "pnl_split").rows():
        assert split == pytest.approx(total)
    by_cause = res.pnl.select(pl.col("price") + pl.col("cashflow") + pl.col("cost") - pl.col("pnl"))
    assert by_cause.to_series().abs().max() == pytest.approx(0.0)


def test_attribution_summary_over_the_run() -> None:
    plan = {D1: {"SPY": 10, "QQQ": -5}}
    res = run(Fixed(plan), Market({"SPY": SPY, "QQQ": QQQ}), costs=PerUnitCost(0.10), delay=0)
    summary = res.attribution()
    # SPY 100→101: +10 price, -1 cost; QQQ short 50→51: -5 price, -0.5 cost.
    assert_rows(
        summary.select("instrument", "price", "cost", "pnl"),
        [("SPY", 10.0, -1.0, 9.0), ("QQQ", -5.0, -0.5, -5.5)],
    )
    assert summary["pnl"].sum() == pytest.approx(res.daily["pnl"].sum())


def test_cashflows_are_attributed_separately_from_price() -> None:
    @dataclass(frozen=True)
    class Coupon(Instrument):
        @property
        def id(self) -> str:
            return "BOND"

        def value(self, market: Market, day: dt.date) -> float | None:
            return {D1: 100.0, D2: 99.0, D3: 99.0}[day]

        def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
            return 0.5

    class Hold(Strategy):
        def on_day(self, ctx: Context) -> dict[Instrument, float]:
            return {Coupon(): 2}

    res = run(Hold(), Market({"SPY": SPY}), delay=0)
    assert res.attribution().select("price", "cashflow", "pnl").row(0) == pytest.approx(
        (-2.0, 2.0, 0.0)
    )


def test_a_closed_position_stops_appearing() -> None:
    res = run(Fixed({D1: {"SPY": 10}, D2: {}}), Market({"SPY": SPY}), delay=0)
    assert res.pnl["date"].to_list() == [D1, D2]  # traded Mon, sold Tue, nothing Wed
