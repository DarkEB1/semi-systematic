"""backtest: a daily backtesting engine for any position-based strategy.

A tool: an isolated package that takes market data and a strategy as arguments and knows nothing
about the repository, the bucket or .env. Contract: tools/README.md; conventions the engine must
follow (returns, costs, calendars, currencies): knowledge/context/conventions.md.

Three layers. ``Market`` holds the data; an ``Instrument`` knows how to value itself from it
(one class per asset class: ``Cash`` for anything worth its quoted price); ``run`` replays the
calendar, asks the ``Strategy`` what to hold at each close and keeps the books.

    from backtest import Market, Strategy, run

    class Momentum(Strategy):
        def on_day(self, ctx):
            closes = ctx.market.closes("SPY", lookback=21)
            up = len(closes) == 21 and closes[-1] > closes[0]
            return {"SPY": 10 if up else 0}

    res = run(Momentum(), Market.from_wide(prices), capital=10_000)
    res.daily          # date | nav | pnl | cash | gross | net
"""

from __future__ import annotations

from backtest.engine import run
from backtest.instruments import Cash, Instrument
from backtest.market import LookaheadError, Market, MarketView
from backtest.result import Result
from backtest.strategy import Context, Strategy

__version__ = "0.1.0"
__all__ = [
    "Cash",
    "Context",
    "Instrument",
    "LookaheadError",
    "Market",
    "MarketView",
    "Result",
    "Strategy",
    "run",
]
