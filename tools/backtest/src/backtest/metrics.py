"""metrics: the summary numbers of a backtest, from its daily NAV, P&L, traded value and costs.

Every figure is computed from ``Result.daily`` with simple daily returns (the conventions):

- ``total_return``: final NAV over starting capital, minus one.
- ``ann_return``: compounded, ``(1 + total_return) ** (periods_per_year / days) - 1``.
- ``ann_vol``: sample standard deviation of daily returns times ``sqrt(periods_per_year)``.
- ``sharpe``: mean over standard deviation of daily returns times ``sqrt(periods_per_year)``.
  Cash earns nothing in the engine, so this is the Sharpe of the return over cash only for
  self-funded positions (FX with carry); subtract the cash rate yourself for funded ones.
- ``max_drawdown``: the worst fall from a running peak of the NAV, the starting capital included
  (negative, or zero).
- ``hit_rate``: share of days with a positive P&L among days whose P&L is not zero.
- ``turnover``: value traded per year as a multiple of the mean NAV.
- ``cost_drag``: costs per year as a fraction of the mean NAV.
- ``total_cost``, ``days``: as named.

``periods_per_year`` is 252 by default; a Monday-to-Friday calendar (FX) is closer to 260.
"""

from __future__ import annotations

import math

import polars as pl

from backtest.result import Result


def metrics(res: Result, *, periods_per_year: float = 252.0) -> dict[str, float]:
    """The summary of ``res``; NaN where a figure is undefined (one day, zero volatility)."""
    d = res.daily
    days = d.height
    if days == 0:
        raise ValueError("metrics: empty result")
    nav = d["nav"]
    ret = res.returns
    total = float(nav[-1]) / res.capital - 1
    std = _num(ret.std(ddof=1)) if days > 1 else math.nan
    mean_nav = _num(nav.mean())
    per_year = periods_per_year / days
    return {
        "total_return": total,
        "ann_return": (1 + total) ** per_year - 1,
        "ann_vol": std * math.sqrt(periods_per_year),
        "sharpe": _ratio(_num(ret.mean()), std) * math.sqrt(periods_per_year),
        "max_drawdown": _max_drawdown(nav, res.capital),
        "hit_rate": _hit_rate(d["pnl"]),
        "turnover": float(d["traded"].sum()) / mean_nav * per_year,
        "cost_drag": float(d["cost"].sum()) / mean_nav * per_year,
        "total_cost": float(d["cost"].sum()),
        "days": float(days),
    }


def _num(v: object) -> float:
    """A polars aggregate as a float; NaN when it is null."""
    return math.nan if v is None else float(v)  # type: ignore[arg-type]


def _ratio(a: float, b: float) -> float:
    return a / b if b and not math.isnan(b) else math.nan


def _max_drawdown(nav: pl.Series, capital: float) -> float:
    path = pl.concat([pl.Series([float(capital)]), nav.cast(pl.Float64)])
    return _num((path / path.cum_max() - 1).min())


def _hit_rate(pnl: pl.Series) -> float:
    moved = pnl.filter(pnl.abs() > 1e-9)
    return _num((moved > 0).mean()) if moved.len() else math.nan
