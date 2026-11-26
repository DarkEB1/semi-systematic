"""FxPair: spot in USD by quoting direction, carry as a cashflow. Every number is by hand."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import BpsCost, FxPair, Market, run_weights

MON, TUE, WED = dt.date(2026, 3, 6 - 4), dt.date(2026, 3, 3), dt.date(2026, 3, 4)
FRI, NEXT_MON = dt.date(2026, 3, 6), dt.date(2026, 3, 9)
NAV = 1_000_000.0


def rates(**by_ccy: float) -> Market:
    """Flat annual % rates from Monday on, one symbol per currency."""
    return Market({c: {MON: r} for c, r in by_ccy.items()})


def weights(day: dt.date, **w: float) -> pl.DataFrame:
    return pl.DataFrame([{"date": day} | w])


def fx_run(prices: dict[str, dict[dt.date, float]], w: pl.DataFrame, **kw: object):  # noqa: ANN201
    extras = {"rates": kw.pop("rates")} if "rates" in kw else {}
    market = Market(prices, extras=extras)
    carry = "rates" if extras else None
    instruments = {s: FxPair(s, rates=carry) for s in prices}
    return run_weights(w, market, instruments=instruments, capital=NAV, **kw, delay=0)  # type: ignore[arg-type]


# --- the pair --------------------------------------------------------------------------------


def test_legs() -> None:
    assert (FxPair("USDBRL").base, FxPair("USDBRL").quote) == ("USD", "BRL")
    assert (FxPair("EURUSD").base, FxPair("EURUSD").quote) == ("EUR", "USD")


@pytest.mark.parametrize("bad", ["USDUSD", "usdbrl", "USDBR", "USD/BRL"])
def test_bad_symbols_raise(bad: str) -> None:
    with pytest.raises(ValueError):
        FxPair(bad)


def test_unit_values_in_usd() -> None:
    m = Market({"EURUSD": {MON: 1.10}, "USDBRL": {MON: 5.0}})
    assert FxPair("EURUSD").value(m, MON) == pytest.approx(1.10)  # 1 EUR held
    assert FxPair("USDBRL").value(m, MON) == pytest.approx(-0.2)  # 1 BRL owed
    assert FxPair("USDBRL").exposure(-0.2) == pytest.approx(0.2)


# --- spot P&L --------------------------------------------------------------------------------


def test_long_usdbrl_spot_return_is_one_minus_s0_over_s1() -> None:
    # +50% USDBRL at 5.00, BRL weakens to 5.10: 500k * (1 - 5.00/5.10) = 9 803.92, not 10 000.
    res = fx_run({"USDBRL": {MON: 5.0, TUE: 5.1}}, weights(MON, USDBRL=0.5))
    assert res.daily["pnl"][1] == pytest.approx(500_000 * (1 - 5.0 / 5.1))
    assert res.daily["gross"][0] == pytest.approx(500_000)
    assert res.daily["net"][0] == pytest.approx(500_000)  # long the pair reads as long


def test_long_usdbrl_loses_when_brl_strengthens() -> None:
    res = fx_run({"USDBRL": {MON: 5.0, TUE: 4.9}}, weights(MON, USDBRL=0.5))
    assert res.daily["pnl"][1] == pytest.approx(500_000 * (1 - 5.0 / 4.9))
    assert res.daily["pnl"][1] < 0


def test_long_eurusd_spot_return_is_s1_over_s0_minus_one() -> None:
    res = fx_run({"EURUSD": {MON: 1.10, TUE: 1.12}}, weights(MON, EURUSD=0.5))
    assert res.daily["pnl"][1] == pytest.approx(500_000 * (1.12 / 1.10 - 1))


def test_short_usdbrl_is_the_mirror() -> None:
    long = fx_run({"USDBRL": {MON: 5.0, TUE: 5.1}}, weights(MON, USDBRL=0.5))
    short = fx_run({"USDBRL": {MON: 5.0, TUE: 5.1}}, weights(MON, USDBRL=-0.5))
    assert short.daily["pnl"][1] == pytest.approx(-long.daily["pnl"][1])
    assert short.daily["net"][0] == pytest.approx(-500_000)


# --- carry -----------------------------------------------------------------------------------


def test_carry_one_day() -> None:
    # Long USD (4.3%) against BRL (15%) on 500k for one day: 500k * -10.7% / 360 = -148.61.
    res = fx_run(
        {"USDBRL": {MON: 5.0, TUE: 5.0}}, weights(MON, USDBRL=0.5), rates=rates(USD=4.3, BRL=15.0)
    )
    assert res.attribution()["cashflow"][0] == pytest.approx(500_000 * (4.3 - 15.0) / 100 / 360)


def test_carry_long_eurusd_sign() -> None:
    # Long EUR (2%) against USD (4.3%): negative carry on 1.10 * units.
    res = fx_run(
        {"EURUSD": {MON: 1.10, TUE: 1.10}}, weights(MON, EURUSD=0.5), rates=rates(USD=4.3, EUR=2.0)
    )
    assert res.attribution()["cashflow"][0] == pytest.approx(500_000 * (2.0 - 4.3) / 100 / 360)


def test_weekend_accrues_three_days() -> None:
    res = fx_run(
        {"USDBRL": {MON: 5.0, FRI: 5.0, NEXT_MON: 5.0}},
        weights(FRI, USDBRL=0.5),
        rates=rates(USD=4.3, BRL=15.0),
    )
    weekend = res.pnl.filter(pl.col("date") == NEXT_MON)["cashflow"][0]
    assert weekend == pytest.approx(3 * 500_000 * (4.3 - 15.0) / 100 / 360)


def test_carry_uses_the_rate_known_the_evening_before() -> None:
    # The BRL rate jumps to 20% on Tuesday: Monday→Tuesday still accrues at 15%.
    r = Market({"USD": {MON: 4.3}, "BRL": {MON: 15.0, TUE: 20.0}})
    res = fx_run({"USDBRL": {MON: 5.0, TUE: 5.0, WED: 5.0}}, weights(MON, USDBRL=0.5), rates=r)
    flows = res.pnl.sort("date")["cashflow"].to_list()
    assert flows[1] == pytest.approx(500_000 * (4.3 - 15.0) / 100 / 360)
    assert flows[2] == pytest.approx(500_000 * (4.3 - 20.0) / 100 / 360)


def test_missing_currency_rate_raises() -> None:
    with pytest.raises(KeyError, match="no BRL rate"):
        fx_run({"USDBRL": {MON: 5.0, TUE: 5.0}}, weights(MON, USDBRL=0.5), rates=rates(USD=4.3))


def test_no_rates_in_market_raises_when_carry_is_on() -> None:
    market = Market({"USDBRL": {MON: 5.0, TUE: 5.0}})
    with pytest.raises(KeyError, match="not a Market"):
        run_weights(
            weights(MON, USDBRL=0.5), market, instruments={"USDBRL": FxPair("USDBRL")}, delay=0
        )


# --- the worked example ----------------------------------------------------------------------


def test_one_day_worked_example() -> None:
    # From 0 to +50% USDBRL at 5.00, 5 bp, rates USD 4.3% / BRL 15%, then 5.10 the next day:
    # spot +0.980%, carry -0.015%, cost -0.025%: net +0.940% of NAV.
    res = fx_run(
        {"USDBRL": {MON: 5.0, TUE: 5.1}},
        weights(MON, USDBRL=0.5),
        rates=rates(USD=4.3, BRL=15.0),
        costs=BpsCost(5),
    )
    a = res.attribution().row(0, named=True)
    assert a["price"] / NAV == pytest.approx(0.5 * (1 - 5.0 / 5.1))
    assert a["cashflow"] / NAV == pytest.approx(0.5 * -0.107 / 360)
    assert a["cost"] / NAV == pytest.approx(-0.5 * 5 / 10_000)
    exact = 0.5 * (1 - 5.0 / 5.1) + 0.5 * -0.107 / 360 - 0.5 * 5 / 10_000
    assert res.daily["nav"][-1] / NAV - 1 == pytest.approx(exact)
    assert round(exact * 100, 2) == 0.94  # the +0.94% of the worked example
