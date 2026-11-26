"""Currencies: the accounting currency, conversion, foreign-currency assets and FX crosses.
Every number is by hand."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import Cash, Context, FxPair, Market, Strategy, run, run_weights

D1, D2, D3 = (dt.date(2026, 3, d) for d in (2, 3, 4))


def wtable(rows: dict[dt.date, dict[str, float]]) -> pl.DataFrame:
    return pl.DataFrame([{"date": d} | w for d, w in rows.items()])


def fx(symbols: list[str]) -> dict[str, FxPair]:
    return {s: FxPair(s, rates=None) for s in symbols}


def qty(res: object, day: dt.date) -> dict[str, float]:
    pos = res.positions.filter(pl.col("date") == day)  # type: ignore[attr-defined]
    return dict(pos.select("instrument", "quantity").iter_rows())


# --- conversion ------------------------------------------------------------------------------


def test_rate_direct_inverse_and_through_usd() -> None:
    m = Market({"USDBRL": {D1: 5.0}, "EURUSD": {D1: 1.25}})
    assert m.rate("USD", "BRL", D1) == pytest.approx(5.0)
    assert m.rate("BRL", "USD", D1) == pytest.approx(0.2)
    assert m.rate("EUR", "BRL", D1) == pytest.approx(6.25)  # 1.25 USD per EUR * 5 BRL per USD
    assert m.rate("BRL", "BRL", D1) == 1.0


def test_rate_missing_day_and_missing_pair() -> None:
    m = Market({"USDBRL": {D1: 5.0}, "SPY": {D2: 1.0}})
    assert m.rate("BRL", "USD", D2) is None
    assert m.rate("BRL", "USD", D2, asof=True) == pytest.approx(0.2)
    with pytest.raises(KeyError, match="no MXNUSD or USDMXN"):
        m.rate("MXN", "USD", D1)


def test_accounting_currency_travels_with_the_market() -> None:
    m = Market.from_wide(pl.DataFrame({"date": [D1], "EURUSD": [1.25]}), currency="EUR")
    assert m.currency == "EUR"
    assert m.view(D1).currency == "EUR"
    res = run_weights(wtable({D1: {"EURUSD": 0.0}}), m, instruments=fx(["EURUSD"]), delay=0)
    assert res.currency == "EUR"


# --- an asset quoted in another currency -----------------------------------------------------


def test_foreign_stock_is_converted_every_day() -> None:
    # 10 shares at 30 BRL with USDBRL 5 are worth 60 USD. Next day 33 BRL but USDBRL 5.5:
    # still 6 USD a share, so the BRL gain is wiped out by the FX loss: P&L 0.
    m = Market({"PETR4": {D1: 30.0, D2: 33.0}, "USDBRL": {D1: 5.0, D2: 5.5}})
    petr = Cash("PETR4", currency="BRL")
    assert petr.value(m, D1) == pytest.approx(6.0)

    class Hold(Strategy):
        def on_day(self, ctx: Context) -> dict[Cash, float]:
            return {petr: 10}

    res = run(Hold(), m, capital=1000, delay=0)
    assert res.daily["pnl"].to_list() == pytest.approx([0.0, 0.0])


def test_foreign_stock_without_spot_that_day_has_no_value() -> None:
    m = Market({"PETR4": {D1: 30.0, D2: 33.0}, "USDBRL": {D1: 5.0}})
    assert Cash("PETR4", currency="BRL").value(m, D2) is None


def test_stock_in_the_accounting_currency_is_untouched() -> None:
    m = Market({"SPY": {D1: 100.0}})
    assert Cash("SPY", currency="USD").value(m, D1) == 100.0
    assert Cash("SPY").value(m, D1) == 100.0


# --- FX pairs in another accounting currency -------------------------------------------------


def test_eurusd_in_a_eur_book() -> None:
    # In EUR, one unit of EURUSD is 1 USD owed (-1/1.25 = -0.8 EUR). Long 50% of 1000 EUR:
    # 625 USD owed. EURUSD 1.25 -> 1.30: 500 * (1 - 1.25/1.30) = 19.23 EUR.
    m = Market({"EURUSD": {D1: 1.25, D2: 1.30}}, currency="EUR")
    assert FxPair("EURUSD").value(m, D1) == pytest.approx(-0.8)
    res = run_weights(
        wtable({D1: {"EURUSD": 0.5}}), m, instruments=fx(["EURUSD"]), capital=1000, delay=0
    )
    assert qty(res, D1)["EURUSD"] == pytest.approx(625.0)
    assert res.daily["pnl"][1] == pytest.approx(500 * (1 - 1.25 / 1.30))


# --- crosses ---------------------------------------------------------------------------------

CROSS = {  # EURJPY = EURUSD * USDJPY: 121, then 132, then 132 again with a weaker yen
    "EURUSD": {D1: 1.10, D2: 1.20, D3: 0.88},
    "USDJPY": {D1: 110.0, D2: 110.0, D3: 150.0},
}


def test_cross_is_held_as_its_two_legs() -> None:
    # Long EURJPY for 1100 USD: 1000 EUR held (EURUSD units) and 121 000 JPY owed (USDJPY units).
    res = run_weights(
        wtable({D1: {"EURJPY": 1.0}}),
        Market(CROSS),
        instruments=fx(["EURJPY"]),
        capital=1100,
        delay=0,
    )
    assert qty(res, D1) == pytest.approx({"EURUSD": 1000.0, "USDJPY": 121_000.0})
    assert res.daily["gross"][0] == pytest.approx(2200.0)  # two legs of 1100


def test_cross_gain_stays_in_the_position_until_rebalanced() -> None:
    # Day 2: EURJPY 121 -> 132, +11 JPY on 1000 EUR = 11 000 JPY = +100 USD at 110.
    # Day 3: EURJPY flat, USDJPY 110 -> 150. Held: the gain is still 11 000 JPY, now 73.33 USD.
    held = run_weights(
        wtable({D1: {"EURJPY": 1.0}}),
        Market(CROSS),
        instruments=fx(["EURJPY"]),
        capital=1100,
        delay=0,
    )
    assert held.daily["pnl"].to_list() == pytest.approx([0.0, 100.0, 11_000 / 150 - 100])
    # Rebalanced on day 2: the legs are resized, the 100 USD banked, and day 3 is flat.
    banked = run_weights(
        wtable({D1: {"EURJPY": 1.0}, D2: {"EURJPY": 1.0}}),
        Market(CROSS),
        instruments=fx(["EURJPY"]),
        capital=1100,
        delay=0,
    )
    assert banked.daily["pnl"].to_list() == pytest.approx([0.0, 100.0, 0.0])


def test_cross_carry_is_the_rate_differential_of_its_currencies() -> None:
    rates = Market({"USD": {D1: 4.0}, "EUR": {D1: 2.0}, "JPY": {D1: 0.5}})
    flat = {"EURUSD": {D1: 1.10, D2: 1.10}, "USDJPY": {D1: 110.0, D2: 110.0}}
    res = run_weights(
        wtable({D1: {"EURJPY": 1.0}}),
        Market(flat, extras={"rates": rates}),
        instruments={"EURJPY": FxPair("EURJPY")},
        capital=1100,
        delay=0,
    )
    # (2 - 4) + (4 - 0.5) = 1.5% a year on 1100 for one day.
    assert res.pnl["cashflow"].sum() == pytest.approx(1100 * 1.5 / 100 / 360)


def test_cross_and_direct_leg_add_up() -> None:
    # Long EURJPY (owes JPY through USDJPY) and short USDJPY for the same amount: the JPY nets out.
    res = run_weights(
        wtable({D1: {"EURJPY": 0.5, "USDJPY": -0.5}}),
        Market(CROSS),
        instruments=fx(["EURJPY", "USDJPY"]),
        capital=1100,
        delay=0,
    )
    assert qty(res, D1) == pytest.approx({"EURUSD": 500.0})


def test_zero_weight_closes_the_legs() -> None:
    res = run_weights(
        wtable({D1: {"EURJPY": 1.0}, D2: {"EURJPY": 0.0}}),
        Market(CROSS),
        instruments=fx(["EURJPY"]),
        capital=1100,
        delay=0,
    )
    assert qty(res, D2) == {}


def test_cross_without_a_leg_spot_raises() -> None:
    m = Market({"EURUSD": {D1: 1.10}})
    with pytest.raises(KeyError, match="no JPYUSD or USDJPY spot for its JPY leg"):
        run_weights(wtable({D1: {"EURJPY": 1.0}}), m, instruments=fx(["EURJPY"]), delay=0)


def test_a_cross_cannot_be_held_directly() -> None:
    class Direct(Strategy):
        def on_day(self, ctx: Context) -> dict[FxPair, float]:
            return {FxPair("EURJPY", rates=None): 1000}

    with pytest.raises(TypeError, match="held as its two legs"):
        run(Direct(), Market(CROSS | {"EURJPY": {D1: 121.0}}), delay=0)
