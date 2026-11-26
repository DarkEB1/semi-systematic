"""ledger: the trades of a result as round trips, and their summary.

``round_trips(res)`` reads the books, not the fills: a round trip is one instrument held from
flat to flat, and its P&L is the sum of that instrument's rows in ``Result.pnl`` over those days,
so price moves, cashflows (carry, dividends) and costs (trading and borrow) are all in it and the
trips add up to the P&L of the run. One row per trip:

``instrument``; ``idea``, ``owner`` (from the fill that opened it, null unless the result comes
from ``run_blotter`` with those columns); ``side`` (``long`` or ``short``, the sign of the
quantity); ``entry``, ``exit`` (null while open); ``days`` (calendar days from entry to exit, or
to the last day of the run); ``size`` (the largest absolute quantity held); ``entry_price``,
``exit_price`` (of the first and last fill); ``pnl`` and its ``cashflow`` and ``cost`` parts
(costs are negative, as in ``Result.pnl``); ``worst`` and ``best``, the lowest and highest the
trip's running P&L stood at a close (how far it went against you, and what it gave back).

The book nets an instrument: two ideas open in the same instrument at once are one trip, tagged
with the idea that opened it. A fill that crosses zero closes one trip and opens the next the
same day; that day's P&L, the fill's cost included, stays with the trip it closed.

``trade_stats(trips)`` summarises the closed trips; filter the table first for one idea or owner.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import polars as pl

from backtest.result import Result

TRIPS_SCHEMA = {
    "instrument": pl.String,
    "idea": pl.String,
    "owner": pl.String,
    "side": pl.String,
    "entry": pl.Date,
    "exit": pl.Date,
    "days": pl.Int64,
    "size": pl.Float64,
    "entry_price": pl.Float64,
    "exit_price": pl.Float64,
    "pnl": pl.Float64,
    "cashflow": pl.Float64,
    "cost": pl.Float64,
    "worst": pl.Float64,
    "best": pl.Float64,
}


def _open(fill: dict[str, Any], day: dt.date, quantity: float) -> dict[str, Any]:
    return {
        "instrument": fill["instrument"],
        "idea": fill.get("idea"),
        "owner": fill.get("owner"),
        "side": "long" if quantity > 0 else "short",
        "entry": day,
        "exit": None,
        "days": 0,
        "size": abs(quantity),
        "entry_price": fill["price"],
        "exit_price": None,
        "pnl": 0.0,
        "cashflow": 0.0,
        "cost": 0.0,
        "worst": 0.0,
        "best": 0.0,
    }


def round_trips(res: Result) -> pl.DataFrame:
    """One row per round trip of ``res``, in order of entry (see the module docstring)."""
    held = {
        (p["instrument"], p["date"]): p["quantity"] for p in res.positions.iter_rows(named=True)
    }
    fills: dict[tuple[str, dt.date], list[dict[str, Any]]] = {}
    for f in res.trades.iter_rows(named=True):
        fills.setdefault((f["instrument"], f["date"]), []).append(f)
    trips: list[dict[str, Any]] = []
    current: dict[str, dict[str, Any]] = {}
    for row in res.pnl.sort("date").iter_rows(named=True):
        inst, day = row["instrument"], row["date"]
        qty = held.get((inst, day), 0.0)
        today = fills.get((inst, day), [])
        trip = current.get(inst)
        if trip is None:  # nothing was held: this row is the day of the opening fill
            trip = current[inst] = _open(today[0], day, qty or today[0]["quantity"])
            trips.append(trip)
        for column in ("pnl", "cashflow", "cost"):
            trip[column] += row[column]
        trip["worst"] = min(trip["worst"], trip["pnl"])
        trip["best"] = max(trip["best"], trip["pnl"])
        trip["days"] = (day - trip["entry"]).days
        flipped = qty != 0 and (qty > 0) != (trip["side"] == "long")
        if qty == 0 or flipped:
            trip["exit"], trip["exit_price"] = day, today[-1]["price"]
            del current[inst]
            if flipped:
                current[inst] = _open(today[-1], day, qty)
                trips.append(current[inst])
        else:
            trip["size"] = max(trip["size"], abs(qty))
    return pl.DataFrame(trips, schema=TRIPS_SCHEMA).sort("entry", maintain_order=True)


def trade_stats(trips: pl.DataFrame) -> dict[str, float]:
    """The summary of the closed trips of ``round_trips``; NaN where a figure is undefined.

    ``trades`` and ``open`` count closed and open trips. ``hit_rate``: share of closed trips with
    a positive P&L. ``avg_win``, ``avg_loss``: mean P&L of the winners and of the others (zero or
    negative). ``payoff``: ``avg_win / -avg_loss``. ``expectancy``: mean P&L per closed trip.
    ``avg_days``: mean calendar days held. ``total_pnl``: P&L of the closed trips.
    """
    closed = trips.filter(pl.col("exit").is_not_null())
    pnl = closed["pnl"].to_list()
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]
    avg_win, avg_loss = _mean(wins), _mean(losses)
    return {
        "trades": float(len(pnl)),
        "open": float(trips.height - len(pnl)),
        "hit_rate": len(wins) / len(pnl) if pnl else math.nan,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff": avg_win / -avg_loss if avg_loss < 0 else math.nan,
        "expectancy": _mean(pnl),
        "avg_days": _mean(closed["days"].to_list()),
        "total_pnl": float(sum(pnl)),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan
