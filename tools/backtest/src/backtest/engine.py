"""The engine: replay the calendar one close at a time and keep the books.

At every close, in this order:

1. **Revalue** what is held: each instrument's mark moves to today's value (kept from the last
   observed day when today has none), and its cashflow since the previous close is paid.
2. **Fill** orders that are due (decided ``delay`` closes ago) at today's value, paying the
   cost model's charge out of cash.
3. **Ask** the strategy, through a ``Context`` that cannot see past today, what to hold.
4. With ``delay=0``, **fill** that answer now, at today's close.
5. **Record** the day.

Accounting is cash plus marks: buying lowers cash, selling raises it, and
``nav = cash + sum(quantity * mark)``. A day's P&L is the change in NAV, which covers longs, shorts
and any instrument the same way. Execution at today's close for a decision taken at today's close
is the daily convention: the position earns the move from today to the next close, never today's.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from backtest.costs import CostModel, NoCost
from backtest.instruments import Instrument
from backtest.market import Market
from backtest.result import Result
from backtest.strategy import Context, Strategy, Targets, as_instrument

EPS = 1e-12

DAILY_SCHEMA = {
    "date": pl.Date,
    "nav": pl.Float64,
    "pnl": pl.Float64,
    "cash": pl.Float64,
    "gross": pl.Float64,
    "net": pl.Float64,
    "traded": pl.Float64,
    "cost": pl.Float64,
}
POSITIONS_SCHEMA = {
    "date": pl.Date,
    "instrument": pl.String,
    "quantity": pl.Float64,
    "value": pl.Float64,
}
TRADES_SCHEMA = {
    "date": pl.Date,
    "instrument": pl.String,
    "quantity": pl.Float64,
    "price": pl.Float64,
    "cost": pl.Float64,
}


@dataclass
class _Book:
    cash: float
    positions: dict[Instrument, float] = field(default_factory=dict)
    marks: dict[Instrument, float] = field(default_factory=dict)

    def nav(self) -> float:
        return self.cash + sum(q * self.marks[i] for i, q in self.positions.items())

    def exposures(self) -> tuple[float, float]:
        values = [q * self.marks[i] for i, q in self.positions.items()]
        return sum(abs(v) for v in values), sum(values)

    def revalue(self, market: Market, prev: dt.date | None, day: dt.date) -> None:
        for inst, qty in self.positions.items():
            v = inst.value(market, day)
            if v is not None:
                self.marks[inst] = v
            if prev is not None:
                self.cash += qty * inst.cashflow(market, prev, day)

    def fill(self, inst: Instrument, qty: float, price: float) -> None:
        self.cash -= qty * price
        new = self.positions.get(inst, 0.0) + qty
        if abs(new) < EPS:
            self.positions.pop(inst, None)
        else:
            self.positions[inst] = new
        self.marks[inst] = price


@dataclass
class _Run:
    market: Market
    book: _Book
    capital: float
    costs: CostModel
    traded: float = 0.0  # today's |notional| filled
    cost: float = 0.0  # today's costs paid
    pending: dict[Instrument, tuple[int, float]] = field(default_factory=dict)
    daily: list[dict[str, Any]] = field(default_factory=list)
    holdings: list[dict[str, Any]] = field(default_factory=list)
    fills: list[dict[str, Any]] = field(default_factory=list)

    def queue(self, targets: Targets, due: int) -> None:
        wanted = {as_instrument(k): float(q) for k, q in targets.items()}
        for inst in set(self.book.positions) | set(self.pending):
            wanted.setdefault(inst, 0.0)  # left out of the answer: close it
        for inst, target in wanted.items():
            self.pending[inst] = (due, target)

    def execute(self, i: int, day: dt.date) -> None:
        for inst, (due, target) in list(self.pending.items()):
            if due > i:
                continue
            price = inst.value(self.market, day)
            if price is None:  # no market today: the order waits for the next observed close
                continue
            del self.pending[inst]
            qty = target - self.book.positions.get(inst, 0.0)
            if abs(qty) > EPS:
                self.fill(inst, qty, price, day)

    def fill(self, inst: Instrument, qty: float, price: float, day: dt.date) -> None:
        cost = self.costs.cost(inst, qty, price, day)
        if cost < 0:
            raise ValueError(f"cost model returned a negative cost for {inst.id}")
        self.book.fill(inst, qty, price)
        self.book.cash -= cost
        self.traded += abs(qty * price)
        self.cost += cost
        self.fills.append(
            {"date": day, "instrument": inst.id, "quantity": qty, "price": price, "cost": cost}
        )

    def record(self, day: dt.date) -> None:
        nav = self.book.nav()
        prev = self.daily[-1]["nav"] if self.daily else self.capital
        gross, net = self.book.exposures()
        self.daily.append(
            {"date": day, "nav": nav, "pnl": nav - prev, "cash": self.book.cash}
            | {"gross": gross, "net": net, "traded": self.traded, "cost": self.cost}
        )
        self.traded = self.cost = 0.0
        for inst, qty in sorted(self.book.positions.items(), key=lambda kv: kv[0].id):
            self.holdings.append(
                {"date": day, "instrument": inst.id, "quantity": qty}
                | {"value": qty * self.book.marks[inst]}
            )

    def context(self, day: dt.date) -> Context:
        return Context(
            date=day,
            market=self.market.view(day),
            positions=dict(self.book.positions),
            cash=self.book.cash,
            nav=self.book.nav(),
            _full=self.market,
        )

    def result(self) -> Result:
        return Result(
            daily=pl.DataFrame(self.daily, schema=DAILY_SCHEMA),
            positions=pl.DataFrame(self.holdings, schema=POSITIONS_SCHEMA),
            trades=pl.DataFrame(self.fills, schema=TRADES_SCHEMA),
            capital=self.capital,
        )


def run(
    strategy: Strategy,
    market: Market,
    *,
    capital: float = 1_000_000.0,
    start: dt.date | None = None,
    end: dt.date | None = None,
    delay: int = 0,
    costs: CostModel | None = None,
) -> Result:
    """Backtest ``strategy`` over every day of ``market`` between ``start`` and ``end``.

    ``delay`` is the number of closes between a decision and its fill: 0 fills at the close the
    decision was taken (the daily convention), 1 at the next close (more conservative).
    ``costs`` charges every fill (default: free, ``NoCost``).
    """
    if delay < 0:
        raise ValueError("run: delay must be >= 0")
    days = [d for d in market.dates if (start is None or d >= start) and (end is None or d <= end)]
    if not days:
        raise ValueError("run: no market day between start and end")
    r = _Run(market=market, book=_Book(cash=capital), capital=capital, costs=costs or NoCost())
    prev: dt.date | None = None
    for i, day in enumerate(days):
        r.book.revalue(market, prev, day)
        r.execute(i, day)
        ctx = r.context(day)
        if i == 0:
            strategy.on_start(ctx)
        targets = strategy.on_day(ctx)
        if targets is not None:
            r.queue(targets, i + delay)
            if delay == 0:
                r.execute(i, day)
        r.record(day)
        prev = day
    return r.result()
