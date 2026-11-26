"""round_trips and trade_stats: the trade-level view of a result. Every number is by hand."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import Context, Market, Strategy, round_trips, run, run_blotter, trade_stats

D1, D2, D3, D4 = (dt.date(2026, 3, d) for d in (2, 3, 4, 5))
MARKET = Market({"SPY": {D1: 100.0, D2: 103.0, D3: 101.0, D4: 105.0}})


class Fixed(Strategy):
    def __init__(self, plan: dict[dt.date, dict[str, float]]) -> None:
        self.plan = plan

    def on_day(self, ctx: Context) -> dict[str, float] | None:
        return self.plan.get(ctx.date)


def test_one_round_trip_from_a_blotter() -> None:
    b = pl.DataFrame(
        {
            "date": [D1, D3],
            "symbol": ["SPY", "SPY"],
            "quantity": [10.0, -10.0],
            "price": [99.0, 102.0],
            "idea": ["spy-dip", "spy-dip"],
            "owner": ["DarkEB1", "DarkEB1"],
        }
    )
    trips = round_trips(run_blotter(b, MARKET, capital=1000))
    assert trips.to_dicts() == [
        {
            "instrument": "SPY",
            "idea": "spy-dip",
            "owner": "DarkEB1",
            "side": "long",
            "entry": D1,
            "exit": D3,
            "days": 2,
            "size": 10.0,
            "entry_price": 99.0,
            "exit_price": 102.0,
            "pnl": pytest.approx(30.0),
            "cashflow": 0.0,
            "cost": 0.0,
            "worst": 0.0,
            "best": pytest.approx(40.0),  # 10 on the day in, 30 more on Tuesday
        }
    ]


def test_a_flip_closes_one_trip_and_opens_another_left_open() -> None:
    res = run(Fixed({D1: {"SPY": 10}, D2: {"SPY": -10}}), MARKET, capital=1000, delay=0)
    long, short = round_trips(res).to_dicts()
    assert (long["side"], long["entry"], long["exit"]) == ("long", D1, D2)
    assert long["pnl"] == pytest.approx(30.0)
    assert (short["side"], short["entry"], short["exit"]) == ("short", D2, None)
    assert short["entry_price"] == 103.0
    assert short["exit_price"] is None
    assert short["days"] == 2
    assert short["pnl"] == pytest.approx(-20.0)  # +20 on Wednesday, -40 on Thursday
    assert (short["worst"], short["best"]) == pytest.approx((-20.0, 20.0))
    assert short["idea"] is None


def test_trips_add_up_to_the_books() -> None:
    res = run(Fixed({D1: {"SPY": 10}, D2: {"SPY": -10}, D3: {}}), MARKET, capital=1000, delay=0)
    assert round_trips(res)["pnl"].sum() == pytest.approx(res.daily["pnl"].sum())


def test_no_trades_is_an_empty_ledger() -> None:
    trips = round_trips(run(Fixed({}), MARKET))
    assert trips.height == 0
    assert "pnl" in trips.columns


def test_trade_stats() -> None:
    trips = pl.DataFrame(
        {"exit": [D2, D3, None, D3], "pnl": [30.0, -10.0, 5.0, 20.0], "days": [1, 2, 3, 3]}
    )
    assert trade_stats(trips) == pytest.approx(
        {
            "trades": 3.0,
            "open": 1.0,
            "hit_rate": 2 / 3,
            "avg_win": 25.0,
            "avg_loss": -10.0,
            "payoff": 2.5,
            "expectancy": 40 / 3,
            "avg_days": 2.0,
            "total_pnl": 40.0,
        }
    )


def test_trade_stats_without_a_closed_trade_is_nan() -> None:
    stats = trade_stats(pl.DataFrame({"exit": [None], "pnl": [5.0], "days": [3]}))
    assert stats["trades"] == 0.0
    assert stats["open"] == 1.0
    assert stats["hit_rate"] != stats["hit_rate"]  # NaN
