"""Engine: the day loop, the books, and the no-lookahead guarantee. Every number is by hand."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import polars as pl
import pytest
from backtest import Cash, Context, Instrument, LookaheadError, Market, Result, Strategy, run

D1, D2, D3, D4 = (dt.date(2026, 3, d) for d in (2, 3, 4, 5))
SPY = {D1: 100.0, D2: 103.0, D3: 101.0}


class Fixed(Strategy):
    """Returns a fixed answer per day (missing day: change nothing)."""

    def __init__(self, plan: dict[dt.date, dict[str, float]]) -> None:
        self.plan = plan

    def on_day(self, ctx: Context) -> dict[str, float] | None:
        return self.plan.get(ctx.date)


def pnl(res: Result) -> list[float]:
    return res.daily["pnl"].to_list()


def test_hold_ten_shares_example() -> None:
    # Buy 10 at Monday's close (100); Tuesday 103 → +30; Wednesday 101 → -20.
    res = run(Fixed({D1: {"SPY": 10}}), Market({"SPY": SPY}), capital=1000)
    assert pnl(res) == pytest.approx([0.0, 30.0, -20.0])
    assert res.daily["nav"].to_list() == pytest.approx([1000.0, 1030.0, 1010.0])
    assert res.trades.to_dicts() == [
        {"date": D1, "instrument": "SPY", "quantity": 10.0, "price": 100.0}
    ]


def test_a_decision_earns_the_next_move_not_todays() -> None:
    # Buying on Tuesday after seeing 103 must not earn Monday→Tuesday's +3.
    res = run(Fixed({D2: {"SPY": 10}}), Market({"SPY": SPY}), capital=1000)
    assert pnl(res) == pytest.approx([0.0, 0.0, -20.0])


def test_strategy_cannot_read_the_future() -> None:
    class Peeker(Strategy):
        def on_day(self, ctx: Context) -> None:
            ctx.market.price("SPY", ctx.date + dt.timedelta(days=1))

    with pytest.raises(LookaheadError):
        run(Peeker(), Market({"SPY": SPY}))


def test_history_stops_today() -> None:
    seen: list[list[float]] = []

    class Recorder(Strategy):
        def on_day(self, ctx: Context) -> None:
            seen.append(ctx.market.closes("SPY"))

    run(Recorder(), Market({"SPY": SPY}))
    assert seen == [[100.0], [100.0, 103.0], [100.0, 103.0, 101.0]]


def test_history_lookback() -> None:
    m = Market({"SPY": SPY})
    assert m.view(D3).closes("SPY", lookback=2) == [103.0, 101.0]
    assert m.view(D1).closes("SPY", lookback=5) == [100.0]


def test_short_position_loses_when_price_rises() -> None:
    res = run(Fixed({D1: {"SPY": -10}}), Market({"SPY": SPY}), capital=1000)
    assert pnl(res) == pytest.approx([0.0, -30.0, 20.0])


def test_left_out_instrument_is_closed() -> None:
    res = run(Fixed({D1: {"SPY": 10}, D2: {}}), Market({"SPY": SPY}), capital=1000)
    assert res.trades["quantity"].to_list() == [10.0, -10.0]
    assert res.positions["date"].to_list() == [D1]  # nothing held after Tuesday
    assert res.daily["nav"][-1] == pytest.approx(1030.0)


def test_none_keeps_positions() -> None:
    res = run(Fixed({D1: {"SPY": 10}}), Market({"SPY": SPY}))
    assert res.positions["quantity"].to_list() == [10.0, 10.0, 10.0]


def test_missing_day_books_the_move_on_the_next_observed_day() -> None:
    # SPY has no Tuesday (holiday); QQQ trades, so Tuesday is a market day.
    m = Market({"SPY": {D1: 100.0, D3: 106.0}, "QQQ": {D1: 1.0, D2: 1.0, D3: 1.0}})
    res = run(Fixed({D1: {"SPY": 10}}), m, capital=1000)
    assert pnl(res) == pytest.approx([0.0, 0.0, 60.0])


def test_order_on_a_missing_day_waits_for_the_next_price() -> None:
    m = Market({"SPY": {D1: 100.0, D3: 106.0}, "QQQ": {D1: 1.0, D2: 1.0, D3: 1.0}})
    res = run(Fixed({D2: {"SPY": 10}}), m)
    assert res.trades.select("date", "price").rows() == [(D3, 106.0)]


def test_delay_one_fills_at_the_next_close() -> None:
    res = run(Fixed({D1: {"SPY": 10}}), Market({"SPY": SPY}), capital=1000, delay=1)
    assert res.trades.select("date", "price").rows() == [(D2, 103.0)]
    assert pnl(res) == pytest.approx([0.0, 0.0, -20.0])


def test_books_always_reconcile() -> None:
    plan = {D1: {"SPY": 10, "QQQ": -5}, D2: {"SPY": 4}, D3: {"QQQ": 2}}
    m = Market({"SPY": SPY, "QQQ": {D1: 50.0, D2: 48.0, D3: 51.0}})
    res = run(Fixed(plan), m, capital=1000)
    d = res.daily
    assert d["pnl"].sum() == pytest.approx(d["nav"][-1] - 1000)
    held = res.positions.group_by("date").agg(pl.col("value").sum())
    check = d.join(held, on="date", how="left").fill_null(0.0)
    for nav, cash, value in check.select("nav", "cash", "value").rows():
        assert nav == pytest.approx(cash + value)


def test_cashflows_are_paid_to_holders() -> None:
    @dataclass(frozen=True)
    class Coupon(Instrument):
        """Worth 100 every day, pays 1 per unit per close held."""

        @property
        def id(self) -> str:
            return "BOND"

        def value(self, market: Market, day: dt.date) -> float | None:
            return 100.0

        def cashflow(self, market: Market, prev_day: dt.date, day: dt.date) -> float:
            return 1.0

    class Hold(Strategy):
        def on_day(self, ctx: Context) -> dict[Instrument, float]:
            return {Coupon(): 3}

    res = run(Hold(), Market({"SPY": SPY}), capital=1000)
    assert pnl(res) == pytest.approx([0.0, 3.0, 3.0])


def test_on_start_runs_once_before_the_first_day() -> None:
    calls: list[str] = []

    class Hooks(Strategy):
        def on_start(self, ctx: Context) -> None:
            calls.append(f"start {ctx.date}")

        def on_day(self, ctx: Context) -> None:
            calls.append(f"day {ctx.date}")

    run(Hooks(), Market({"SPY": SPY}), start=D2)
    assert calls == [f"start {D2}", f"day {D2}", f"day {D3}"]


def test_context_exposes_positions_and_values() -> None:
    seen: list[tuple[float, float | None]] = []

    class Look(Strategy):
        def on_day(self, ctx: Context) -> dict[str, float]:
            seen.append((ctx.position("SPY"), ctx.value(Cash("SPY"))))
            return {"SPY": 1}

    run(Look(), Market({"SPY": SPY}))
    assert seen == [(0.0, 100.0), (1.0, 103.0), (1.0, 101.0)]


def test_returns_against_starting_capital() -> None:
    res = run(Fixed({D1: {"SPY": 10}}), Market({"SPY": SPY}), capital=1000)
    assert res.returns.to_list() == pytest.approx([0.0, 0.03, -20 / 1030])


def test_bad_arguments_raise() -> None:
    m = Market({"SPY": SPY})
    with pytest.raises(ValueError, match="no market day"):
        run(Fixed({}), m, start=D4)
    with pytest.raises(ValueError, match="delay"):
        run(Fixed({}), m, delay=-1)
