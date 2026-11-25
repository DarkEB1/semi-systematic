"""Market: building it from long and wide tables, missing days, unknown symbols."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from backtest import Market

D1, D2, D3 = dt.date(2026, 3, 2), dt.date(2026, 3, 3), dt.date(2026, 3, 4)


def test_from_long_reads_every_observation() -> None:
    df = pl.DataFrame(
        {"date": [D1, D2, D1], "symbol": ["SPY", "SPY", "QQQ"], "close": [100.0, 103.0, 50.0]}
    )
    m = Market.from_long(df)
    assert m.symbols == ["QQQ", "SPY"]
    assert m.dates == [D1, D2]
    assert m.price("SPY", D2) == 103.0
    assert m.price("QQQ", D1) == 50.0


def test_from_wide_matches_from_long() -> None:
    wide = pl.DataFrame({"date": [D1, D2], "SPY": [100.0, 103.0], "QQQ": [50.0, None]})
    m = Market.from_wide(wide)
    assert m.price("SPY", D1) == 100.0
    assert m.price("QQQ", D2) is None  # a null is a missing day, not a zero


def test_missing_day_is_none_not_zero() -> None:
    df = pl.DataFrame({"date": [D1, D3], "symbol": ["SPY", "SPY"], "close": [100.0, 101.0]})
    m = Market.from_long(df)
    assert m.price("SPY", D2) is None


def test_datetime_dates_become_dates() -> None:
    df = pl.DataFrame({"date": [dt.datetime(2026, 3, 2, 21)], "symbol": ["SPY"], "close": [100.0]})
    assert Market.from_long(df).dates == [D1]


def test_custom_column_names() -> None:
    df = pl.DataFrame({"day": [D1], "series": ["USDBRL"], "value": [5.0]})
    m = Market.from_long(df, date="day", symbol="series", value="value")
    assert m.price("USDBRL", D1) == 5.0


def test_duplicate_rows_raise() -> None:
    df = pl.DataFrame({"date": [D1, D1], "symbol": ["SPY", "SPY"], "close": [100.0, 101.0]})
    with pytest.raises(ValueError, match="duplicate"):
        Market.from_long(df)


def test_unknown_symbol_raises() -> None:
    m = Market({"SPY": {D1: 100.0}})
    with pytest.raises(KeyError, match="unknown symbol 'SPX'"):
        m.price("SPX", D1)


def test_extras_travel_with_the_market() -> None:
    m = Market({"SPY": {D1: 100.0}}, extras={"rates": {"USD": 4.3}})
    assert m.extras["rates"]["USD"] == 4.3
