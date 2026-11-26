"""family: engine results into the haircut. Every number is by hand or from ras_lower_bounds."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pytest
from backtest import (
    LookaheadError,
    Market,
    evaluate,
    load_scores,
    ras_lower_bounds,
    run_weights,
    save_scores,
    scores,
    walk_forward_weights,
)

DAYS = [dt.date(2026, 3, d) for d in (2, 3, 4, 5, 6, 9)]
SPY = dict(zip(DAYS, [100.0, 110.0, 99.0, 105.0, 105.0, 84.0], strict=True))
QQQ = dict(zip(DAYS, [50.0, 55.0, 50.0, 52.0, 52.0, 52.0], strict=True))
MARKET = Market({"SPY": SPY, "QQQ": QQQ})


def test_fit_and_rule_see_only_the_past() -> None:
    seen: list[tuple[dt.date, list[dt.date], dt.date]] = []

    def fit(view, window):
        def rule(today):
            seen.append((view.today, window, today.today))
            with pytest.raises(LookaheadError):
                today.price("SPY", today.today + dt.timedelta(days=1))
            return {"SPY": 1.0}

        return rule

    w = walk_forward_weights(fit, MARKET, train=2, test=2, gap=1)
    # splits over 6 dates: train [0,1] -> test [3,4]; train [2,3] -> test [5]
    assert w["date"].to_list() == [DAYS[3], DAYS[4], DAYS[5]]
    assert seen == [
        (DAYS[1], DAYS[0:2], DAYS[3]),
        (DAYS[1], DAYS[0:2], DAYS[4]),
        (DAYS[3], DAYS[2:4], DAYS[5]),
    ]


def test_rule_none_holds_and_missing_symbol_is_zero() -> None:
    def fit(view, window):
        return lambda today: None if today.today == DAYS[4] else {"QQQ": 0.5}

    w = walk_forward_weights(fit, MARKET, train=3, test=1)
    assert w["date"].to_list() == [DAYS[3], DAYS[5]]
    assert w.columns == ["date", "QQQ"]

    def fit2(view, window):
        return lambda today: {"SPY": 1.0} if today.today == DAYS[3] else {"QQQ": 1.0}

    w2 = walk_forward_weights(fit2, MARKET, train=3, test=1)
    assert w2.row(1, named=True) == {"date": DAYS[4], "SPY": 0.0, "QQQ": 1.0}


def test_scores_are_nav_returns_on_shared_dates() -> None:
    a = run_weights(_table({DAYS[0]: 1.0}, "SPY"), MARKET, capital=1000, delay=0)
    b = run_weights(_table({DAYS[2]: 1.0}, "QQQ"), MARKET, capital=1000, start=DAYS[2], delay=0)
    s = scores({"spy": a, "qqq": b})
    assert s["date"].to_list() == DAYS[2:]  # inner join
    # spy: 10 shares; 99 -> 105 is +6%; qqq bought at 50 on DAYS[2], first day 0, then +4%
    assert s["spy"].to_list()[:2] == pytest.approx([99 / 110 - 1, 105 / 99 - 1])
    assert s["qqq"].to_list()[:2] == pytest.approx([0.0, 0.04])
    assert scores({"spy": a}, start=DAYS[4])["date"].to_list() == DAYS[4:]


def test_evaluate_matches_ras_on_the_same_matrix() -> None:
    a = run_weights(_table({DAYS[0]: 1.0}, "SPY"), MARKET, capital=1000, delay=0)
    b = run_weights(_table({DAYS[0]: 1.0}, "QQQ"), MARKET, capital=1000, delay=0)
    table, R = evaluate({"spy": a, "qqq": b}, kappa=0.25, B=500, seed=1, start=DAYS[1])
    X = scores({"spy": a, "qqq": b}, start=DAYS[1]).drop("date").to_numpy()
    L, R2 = ras_lower_bounds(X, 0.25, 0.01, 500, 1)
    assert R == pytest.approx(R2)
    got = dict(zip(table["candidate"], table["lower_bound"], strict=True))
    assert got == pytest.approx({"spy": L[0], "qqq": L[1]})
    assert table["lower_bound"].to_list() == sorted(L, reverse=True)
    assert table["days"].to_list() == [5, 5]
    assert table["ann_mean"].to_list() == pytest.approx(list(np.sort(X.mean(0))[::-1] * 252))


def test_evaluate_refuses_a_kappa_the_scores_break() -> None:
    a = run_weights(_table({DAYS[0]: 1.0}, "SPY"), MARKET, capital=1000, delay=0)
    with pytest.raises(ValueError, match="exceeds kappa"):
        evaluate({"spy": a}, kappa=0.1)  # SPY falls 20% on the last day


def _table(rows: dict[dt.date, float], symbol: str):
    import polars as pl

    return pl.DataFrame([{"date": d, symbol: w} for d, w in rows.items()])


def test_saved_scores_reload_across_directories(tmp_path) -> None:
    a = run_weights(_table({DAYS[0]: 1.0}, "SPY"), MARKET, capital=1000, delay=0)
    b = run_weights(_table({DAYS[0]: 1.0}, "QQQ"), MARKET, capital=1000, delay=0)
    save_scores({"spy": a}, tmp_path / "monday")
    save_scores({"qqq": b}, tmp_path / "wednesday")
    loaded = load_scores(tmp_path / "monday", tmp_path / "wednesday")
    assert loaded.equals(scores({"spy": a, "qqq": b}).select(loaded.columns))
    t1, r1 = evaluate(loaded, kappa=0.25, B=500, start=DAYS[1])
    t2, r2 = evaluate({"spy": a, "qqq": b}, kappa=0.25, B=500, start=DAYS[1])
    assert r1 == pytest.approx(r2)
    assert t1.equals(t2)


def test_one_name_in_two_directories_raises(tmp_path) -> None:
    a = run_weights(_table({DAYS[0]: 1.0}, "SPY"), MARKET, capital=1000, delay=0)
    save_scores({"spy": a}, tmp_path / "x")
    save_scores({"spy": a}, tmp_path / "y")
    with pytest.raises(ValueError, match="'spy'"):
        load_scores(tmp_path / "x", tmp_path / "y")
