"""metrics: each figure on a series whose answer is known, checked against the standard library."""

from __future__ import annotations

import datetime as dt
import math
import statistics

import polars as pl
import pytest
from backtest import BpsCost, Market, Result, metrics, run_weights

START = dt.date(2026, 1, 1)


def result(navs: list[float], capital: float = 1000.0, **cols: list[float]) -> Result:
    """A Result with only the daily table filled: NAV path, P&L derived, optional columns."""
    n = len(navs)
    pnl = [b - a for a, b in zip([capital, *navs], navs, strict=False)]
    daily = pl.DataFrame(
        {
            "date": [START + dt.timedelta(days=i) for i in range(n)],
            "nav": navs,
            "pnl": pnl,
            "traded": cols.get("traded", [0.0] * n),
            "cost": cols.get("cost", [0.0] * n),
        }
    )
    empty = pl.DataFrame()
    return Result(daily=daily, positions=empty, trades=empty, pnl=empty, capital=capital)


def test_returns_vol_and_sharpe_match_the_textbook() -> None:
    navs = [1010.0, 1000.0, 1030.0, 1020.0]
    rets = [1010 / 1000 - 1, 1000 / 1010 - 1, 1030 / 1000 - 1, 1020 / 1030 - 1]
    m = metrics(result(navs))
    assert m["total_return"] == pytest.approx(0.02)
    assert m["ann_vol"] == pytest.approx(statistics.stdev(rets) * math.sqrt(252))
    assert m["sharpe"] == pytest.approx(
        statistics.mean(rets) / statistics.stdev(rets) * math.sqrt(252)
    )
    assert m["days"] == 4


def test_ann_return_compounds() -> None:
    # Doubling over exactly one year of days is +100% a year; over half a year, +300%.
    daily = 2 ** (1 / 252)
    year = metrics(result([1000 * daily**i for i in range(1, 253)]))
    assert year["ann_return"] == pytest.approx(1.0)
    half = metrics(result([1000 * daily ** (2 * i) for i in range(1, 127)]))
    assert half["ann_return"] == pytest.approx(3.0)


def test_periods_per_year() -> None:
    navs = [1010.0, 1000.0, 1030.0]
    m252, m260 = metrics(result(navs)), metrics(result(navs), periods_per_year=260)
    assert m260["ann_vol"] / m252["ann_vol"] == pytest.approx(math.sqrt(260 / 252))


def test_max_drawdown_from_a_running_peak() -> None:
    assert metrics(result([1200.0, 900.0, 1300.0]))["max_drawdown"] == pytest.approx(-0.25)


def test_max_drawdown_counts_the_starting_capital() -> None:
    assert metrics(result([900.0, 950.0]))["max_drawdown"] == pytest.approx(-0.10)


def test_no_drawdown_is_zero() -> None:
    assert metrics(result([1001.0, 1002.0]))["max_drawdown"] == 0.0


def test_hit_rate_ignores_flat_days() -> None:
    # P&L +10, -5, 0, +5: two winners out of three days that moved.
    assert metrics(result([1010.0, 1005.0, 1005.0, 1010.0]))["hit_rate"] == pytest.approx(2 / 3)


def test_turnover_and_cost_drag_per_year() -> None:
    # 252 days at NAV 1000, 2000 traded and 2 paid in costs in total: 2x and 0.2% a year.
    n = 252
    traded, cost = [0.0] * n, [0.0] * n
    traded[0], traded[100], cost[0], cost[100] = 1000.0, 1000.0, 1.0, 1.0
    m = metrics(result([1000.0] * n, traded=traded, cost=cost))
    assert m["turnover"] == pytest.approx(2.0)
    assert m["cost_drag"] == pytest.approx(0.002)
    assert m["total_cost"] == pytest.approx(2.0)


def test_undefined_figures_are_nan() -> None:
    one = metrics(result([1010.0]))
    assert math.isnan(one["ann_vol"]) and math.isnan(one["sharpe"])
    flat = metrics(result([1000.0, 1000.0]))
    assert math.isnan(flat["sharpe"]) and math.isnan(flat["hit_rate"])


def test_empty_result_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        metrics(result([]))


def test_on_a_real_run() -> None:
    days = [dt.date(2026, 3, d) for d in (2, 3, 4, 5)]
    market = Market({"SPY": dict(zip(days, [100.0, 103.0, 101.0, 104.0], strict=True))})
    w = pl.DataFrame({"date": [days[0]], "SPY": [1.0]})
    res = run_weights(w, market, capital=1000, costs=BpsCost(10), delay=0)
    m = metrics(res)
    assert m["total_return"] == pytest.approx(res.daily["nav"][-1] / 1000 - 1)
    assert m["total_cost"] == pytest.approx(1.0)  # 1000 traded at 10 bp
    assert m["max_drawdown"] == pytest.approx(101 / 103 - 1, rel=1e-3)
