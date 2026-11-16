"""backtest: a daily backtesting engine for any position-based strategy.

A tool: an isolated package that takes market data and a strategy as arguments and knows nothing
about the repository, the bucket or .env. Contract: tools/README.md; conventions the engine must
follow (returns, costs, calendars, currencies): knowledge/context/conventions.md.

Three layers. ``Market`` holds the data; an ``Instrument`` knows how to value itself from it
(one class per asset class: ``Cash`` for anything worth its quoted price); the engine replays the
calendar and does the accounting. Built step by step: today the data and instrument layers.

    from backtest import Cash, Market
    market = Market.from_wide(prices)          # date | SPY | QQQ ...
    Cash("SPY").value(market, day)             # 503.2, or None on a missing day
"""

from __future__ import annotations

from backtest.instruments import Cash, Instrument
from backtest.market import Market

__version__ = "0.1.0"
__all__ = ["Cash", "Instrument", "Market"]
