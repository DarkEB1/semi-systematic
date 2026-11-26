"""family: the bridge from the engine to the evaluation layer (ADR-0014).

The engine gives one ``Result`` per candidate; the haircut wants one T x N score matrix of every
candidate tried. Three functions join them:

- ``walk_forward_weights``: a weight table built out of sample. ``fit`` sees the market frozen at
  the last training close and returns a rule; the rule sees the market frozen at each test close
  and returns that day's weights. Neither can reach a later price (``LookaheadError``). Pass the
  table to ``run_weights`` with ``start`` at its first date.
- ``scores``: the daily NAV returns of each ``Result``, on the dates they all share.
- ``evaluate``: ``ras_lower_bounds`` over those scores, one row per candidate.
- ``save_scores`` / ``load_scores``: keep each candidate's scores as a file, so a family can be
  evaluated across runs and experiments. The caller chooses the directory.

Timing needs no shift: the engine fills a decision taken at the close of t at that close
(``delay=0``) or the next (``delay=1``, the default) and books the P&L from the fill on, so a row
of ``scores`` never holds a move known when its decision was taken. ``delay=0`` is exactly the
lecture's convention (``pnl.py``): decision t meets outcome t+1.
"""

from __future__ import annotations

import datetime as dt
import math
import pathlib
from collections.abc import Callable, Mapping

import numpy as np
import polars as pl

from backtest.haircut import ras_lower_bounds
from backtest.market import Market, MarketView
from backtest.result import Result
from backtest.splits import walk_forward

Rule = Callable[[MarketView], Mapping[str, float] | None]
Fit = Callable[[MarketView, list[dt.date]], Rule]


def walk_forward_weights(
    fit: Fit,
    market: Market,
    *,
    train: int,
    test: int,
    gap: int = 0,
    expanding: bool = False,
) -> pl.DataFrame:
    """A ``date | symbol...`` weight table, each row decided only with what was known then.

    For every ``walk_forward`` split of the market's dates, ``fit(view, train_dates)`` is called
    with the view at the last training date (``train_dates`` is the window to fit on; the view
    itself reaches back to the start), then its rule is called at every test date. A rule that
    returns ``None`` holds that day (no row). A symbol absent from a row is a zero weight.
    """
    dates = market.dates
    rows: list[dict[str, object]] = []
    for tr, te in walk_forward(len(dates), train, test, gap, expanding):
        window = [dates[i] for i in tr]
        rule = fit(market.view(window[-1]), window)
        for i in te:
            w = rule(market.view(dates[i]))
            if w is not None:
                rows.append({"date": dates[i], **{k: float(v) for k, v in w.items()}})
    if not rows:
        raise ValueError("walk_forward_weights: no weights (too few dates, or every rule held)")
    return pl.from_dicts(rows, infer_schema_length=None).fill_null(0.0)


def scores(results: Mapping[str, Result], *, start: dt.date | None = None) -> pl.DataFrame:
    """``date | candidate...``: each result's daily NAV return, on the dates all results share,
    from ``start`` on (use the first out-of-sample date)."""
    if not results:
        raise ValueError("scores: no results")
    out: pl.DataFrame | None = None
    for name, res in results.items():
        col = res.daily.select("date", res.returns.alias(name))
        out = col if out is None else out.join(col, on="date", how="inner")
    assert out is not None
    if start is not None:
        out = out.filter(pl.col("date") >= start)
    return out.sort("date")


def save_scores(results: Mapping[str, Result], directory: str | pathlib.Path) -> list[pathlib.Path]:
    """Write each result's daily NAV returns to ``directory/<name>.parquet`` (``date | ret``).

    Rerunning a candidate under the same name replaces its file: one name, one variant.
    """
    out = pathlib.Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, res in results.items():
        path = out / f"{name}.parquet"
        res.daily.select("date", res.returns.alias("ret")).write_parquet(path)
        paths.append(path)
    return paths


def load_scores(*directories: str | pathlib.Path, start: dt.date | None = None) -> pl.DataFrame:
    """The ``scores`` table of every file ``save_scores`` wrote in ``directories``, on the dates
    they all share. A name found in two directories raises: two variants cannot share one."""
    found: dict[str, pathlib.Path] = {}
    for d in directories:
        for path in sorted(pathlib.Path(d).glob("*.parquet")):
            if path.stem in found:
                raise ValueError(f"load_scores: {path.stem!r} in {found[path.stem].parent} and {d}")
            found[path.stem] = path
    if not found:
        raise ValueError("load_scores: no score files")
    out: pl.DataFrame | None = None
    for name, path in found.items():
        col = pl.read_parquet(path).rename({"ret": name})
        out = col if out is None else out.join(col, on="date", how="inner")
    assert out is not None
    if start is not None:
        out = out.filter(pl.col("date") >= start)
    return out.sort("date")


def evaluate(
    results: Mapping[str, Result] | pl.DataFrame,
    *,
    kappa: float,
    delta: float = 0.01,
    B: int = 10_000,
    seed: int = 0,
    start: dt.date | None = None,
    periods_per_year: float = 252.0,
) -> tuple[pl.DataFrame, float]:
    """The Rademacher haircut of every candidate in ``results``, jointly (``ras_lower_bounds``).

    ``results`` must hold every candidate tried, the abandoned ones included: ``Result`` objects,
    or a ``scores`` table (from ``scores`` or ``load_scores``). ``kappa`` bounds
    the absolute daily return of every candidate on every date and is chosen before looking; a
    score above it raises, since the bound would not hold. Returns the table
    ``candidate | days | mean | sharpe | lower_bound | ann_mean | ann_lower_bound`` (means are
    daily returns, ``ann_`` columns times ``periods_per_year``, ``sharpe`` annualised), best lower
    bound first, and R. A lower bound at or below zero is inconclusive, not a loss.
    """
    if isinstance(results, pl.DataFrame):
        table = results if start is None else results.filter(pl.col("date") >= start)
    else:
        table = scores(results, start=start)
    names = [c for c in table.columns if c != "date"]
    X = table.select(names).to_numpy().astype(np.float64)
    if X.shape[0] < 2:
        raise ValueError("evaluate: fewer than two common dates")
    worst = float(np.abs(X).max())
    if worst > kappa:
        raise ValueError(f"evaluate: a daily return of {worst:.4g} exceeds kappa={kappa}")
    L, R = ras_lower_bounds(X, kappa, delta, B, seed)
    mean = X.mean(axis=0)
    out = pl.DataFrame(
        {
            "candidate": names,
            "days": [X.shape[0]] * len(names),
            "mean": mean,
            "sharpe": mean / X.std(axis=0, ddof=1) * math.sqrt(periods_per_year),
            "lower_bound": L,
            "ann_mean": mean * periods_per_year,
            "ann_lower_bound": L * periods_per_year,
        }
    )
    return out.sort("lower_bound", descending=True), R
