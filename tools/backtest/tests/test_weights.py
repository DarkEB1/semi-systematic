"""run_weights: a weight table through the same loop as a Strategy. Every number is by hand."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import BpsCost, Context, Market, Strategy, run, run_weights

D1, D2, D3, D4 = (dt.date(2026, 3, d) for d in (2, 3, 4, 5))
SPY = {D1: 100.0, D2: 110.0, D3: 99.0, D4: 105.0}
QQQ = {D1: 50.0, D2: 55.0, D3: 50.0, D4: 52.0}
MARKET = Market({"SPY": SPY, "QQQ": QQQ})


def table(rows: dict[dt.date, dict[str, float | None]]) -> pl.DataFrame:
    return pl.DataFrame([{"date": d} | w for d, w in rows.items()])


def qty(res: object, day: dt.date, symbol: str) -> float:
    pos = res.positions  # type: ignore[attr-defined]
    hit = pos.filter((pl.col("date") == day) & (pl.col("instrument") == symbol))
    return float(hit["quantity"].sum())


def test_fifty_fifty_by_hand() -> None:
    # 1000 split 500/500: 5 SPY at 100, 10 QQQ at 50. Tuesday: 5*110 + 10*55 = 1100.
    res = run_weights(table({D1: {"SPY": 0.5, "QQQ": 0.5}}), MARKET, capital=1000)
    assert qty(res, D1, "SPY") == pytest.approx(5.0)
    assert qty(res, D1, "QQQ") == pytest.approx(10.0)
    assert res.daily["nav"][1] == pytest.approx(1100.0)


def test_quantities_drift_between_rebalances() -> None:
    res = run_weights(table({D1: {"SPY": 0.5, "QQQ": 0.5}}), MARKET, capital=1000)
    assert [qty(res, d, "SPY") for d in (D1, D2, D3, D4)] == pytest.approx([5.0] * 4)
    assert len(res.trades) == 2  # bought once, never resized


def test_a_row_resizes_at_todays_nav_and_price() -> None:
    # Monday 100% SPY: 10 shares. Tuesday NAV 1100 at 110: 50% is 5 shares, so sell 5.
    res = run_weights(table({D1: {"SPY": 1.0}, D2: {"SPY": 0.5}}), MARKET, capital=1000)
    assert qty(res, D2, "SPY") == pytest.approx(5.0)
    assert res.trades.filter(pl.col("date") == D2)["quantity"].to_list() == pytest.approx([-5.0])


def test_short_weight() -> None:
    res = run_weights(table({D1: {"SPY": -0.5}}), MARKET, capital=1000)
    assert qty(res, D1, "SPY") == pytest.approx(-5.0)
    assert res.daily["pnl"][1] == pytest.approx(-50.0)


def test_null_weight_is_zero_and_closes() -> None:
    rows = {D1: {"SPY": 0.5, "QQQ": 0.5}, D2: {"SPY": None, "QQQ": 0.5}}
    res = run_weights(table(rows), MARKET, capital=1000)
    assert qty(res, D2, "SPY") == 0.0


def test_same_result_as_the_equivalent_strategy() -> None:
    rows = {D1: {"SPY": 0.6, "QQQ": -0.2}, D3: {"SPY": 0.1, "QQQ": 0.4}}

    class ByHand(Strategy):
        def on_day(self, ctx: Context) -> dict[str, float] | None:
            if ctx.date not in rows:
                return None
            return {k.id: q for k, q in ctx.quantities(rows[ctx.date]).items()}

    costs = BpsCost(5)
    a = run_weights(table(rows), MARKET, capital=1000, costs=costs)
    b = run(ByHand(), MARKET, capital=1000, costs=costs)
    assert a.daily.equals(b.daily)
    assert a.trades.equals(b.trades)
    assert a.pnl.equals(b.pnl)


def test_delay_applies_to_weights() -> None:
    res = run_weights(table({D1: {"SPY": 1.0}}), MARKET, capital=1000, delay=1)
    assert res.trades.select("date", "price").rows() == [(D2, 110.0)]


def test_missing_price_on_a_rebalance_day() -> None:
    # SPY has no Tuesday. A non-zero weight cannot be sized: the 10 shares stay.
    # A zero weight is sized without a price and fills on Wednesday.
    m = Market({"SPY": {D1: 100.0, D3: 99.0}, "QQQ": QQQ})
    keep = run_weights(table({D1: {"SPY": 1.0}, D2: {"SPY": 0.3}}), m, capital=1000)
    assert qty(keep, D2, "SPY") == pytest.approx(10.0)
    close = run_weights(table({D1: {"SPY": 1.0}, D2: {"SPY": 0.0}}), m, capital=1000)
    assert close.trades.select("date", "quantity").rows()[-1] == (D3, -10.0)


def test_bad_tables_raise() -> None:
    with pytest.raises(ValueError, match="no market data"):
        run_weights(table({dt.date(2026, 3, 7): {"SPY": 1.0}}), MARKET)  # a Saturday
    with pytest.raises(ValueError, match="no symbol column"):
        run_weights(pl.DataFrame({"date": [D1]}), MARKET)
    dup = pl.DataFrame({"date": [D1, D1], "SPY": [0.5, 0.6]})
    with pytest.raises(ValueError, match="duplicate"):
        run_weights(dup, MARKET)
    with pytest.raises(KeyError, match="unknown symbol"):
        run_weights(table({D1: {"IWM": 1.0}}), MARKET)
