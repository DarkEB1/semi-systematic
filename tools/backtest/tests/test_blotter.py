"""run_blotter: replay trades that were actually made, at the prices they were made at."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import BpsCost, Market, run_blotter

D1, D2, D3 = (dt.date(2026, 3, d) for d in (2, 3, 4))
MARKET = Market({"SPY": {D1: 100.0, D2: 103.0, D3: 101.0}})


def blotter(*rows: tuple[object, ...], columns: tuple[str, ...]) -> pl.DataFrame:
    return pl.DataFrame([dict(zip(columns, r, strict=True)) for r in rows])


def test_a_trade_without_a_price_fills_at_the_close() -> None:
    b = blotter((D1, "SPY", 10.0), columns=("date", "symbol", "quantity"))
    res = run_blotter(b, MARKET, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, 30.0, -20.0])


def test_a_trade_away_from_the_close_earns_the_difference_that_day() -> None:
    # Buy 10 at 99 when the close is 100: +10 on the day. Sell 10 at 102 when the close is 101:
    # -20 from the close-to-close move, +10 for selling above it. Round trip: 10 * (102 - 99).
    b = blotter(
        (D1, "SPY", 10.0, 99.0),
        (D3, "SPY", -10.0, 102.0),
        columns=("date", "symbol", "quantity", "price"),
    )
    res = run_blotter(b, MARKET, capital=1000)
    assert res.daily["pnl"].to_list() == pytest.approx([10.0, 30.0, -10.0])
    assert res.daily["nav"][-1] == pytest.approx(1030.0)
    assert res.daily["cash"][-1] == pytest.approx(1030.0)
    assert res.trades["price"].to_list() == [99.0, 102.0]
    assert res.pnl["pnl"].sum() == pytest.approx(30.0)


def test_costs_are_charged_on_the_traded_notional() -> None:
    b = blotter((D1, "SPY", 10.0, 99.0), columns=("date", "symbol", "quantity", "price"))
    res = run_blotter(b, MARKET, capital=1000, costs=BpsCost(10))
    assert res.trades["cost"].to_list() == pytest.approx([0.99])
    assert res.daily["pnl"][0] == pytest.approx(10.0 - 0.99)


def test_idea_and_owner_are_kept_on_the_trades() -> None:
    b = blotter(
        (D1, "SPY", 10.0, "spy-dip", "DarkEB1"),
        columns=("date", "symbol", "quantity", "idea", "owner"),
    )
    res = run_blotter(b, MARKET)
    assert res.trades["idea"].to_list() == ["spy-dip"]
    assert res.trades["owner"].to_list() == ["DarkEB1"]


def test_untagged_trades_have_null_tags() -> None:
    b = blotter((D1, "SPY", 10.0), columns=("date", "symbol", "quantity"))
    assert run_blotter(b, MARKET).trades["idea"].to_list() == [None]


def test_two_trades_on_one_day_are_two_fills() -> None:
    b = blotter(
        (D1, "SPY", 10.0, 99.0),
        (D1, "SPY", -4.0, 101.0),
        columns=("date", "symbol", "quantity", "price"),
    )
    res = run_blotter(b, MARKET, capital=1000)
    # 10 bought 1 under the close, 4 sold 1 over it; 6 left, marked at 100.
    assert res.daily["pnl"][0] == pytest.approx(14.0)
    assert res.positions.filter(pl.col("date") == D1)["quantity"].to_list() == [6.0]


def test_a_trade_off_the_calendar_raises() -> None:
    b = blotter((dt.date(2026, 3, 7), "SPY", 10.0), columns=("date", "symbol", "quantity"))
    with pytest.raises(ValueError, match="no market data"):
        run_blotter(b, MARKET)


def test_a_zero_quantity_raises() -> None:
    b = blotter((D1, "SPY", 0.0), columns=("date", "symbol", "quantity"))
    with pytest.raises(ValueError, match="zero quantity"):
        run_blotter(b, MARKET)


def test_no_price_and_no_close_raises() -> None:
    market = Market({"SPY": {D1: 100.0, D3: 101.0}, "QQQ": {D2: 50.0}})
    b = blotter((D2, "SPY", 10.0), columns=("date", "symbol", "quantity"))
    with pytest.raises(ValueError, match="no price"):
        run_blotter(b, market)
