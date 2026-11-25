"""backtest: a daily backtesting engine for any position-based strategy, and the evaluation of a
family of strategies (walk-forward splits, net PnL scores, the Rademacher haircut).

A tool: an isolated package that takes market data and a strategy as arguments and knows nothing
about the repository, the bucket or .env. Contract: tools/README.md; conventions the engine must
follow (returns, costs, calendars, currencies): knowledge/context/conventions.md.

Three layers. ``Market`` holds the data; an ``Instrument`` knows how to value itself from it
(one class per asset class: ``Cash`` for anything worth its quoted price, ``FxPair`` for spot FX
against USD with carry); ``run`` replays the
calendar, asks the ``Strategy`` what to hold at each close and keeps the books.

    from backtest import BpsCost, Market, Strategy, run

    class Momentum(Strategy):
        def on_day(self, ctx):
            closes = ctx.market.closes("SPY", lookback=21)
            up = len(closes) == 21 and closes[-1] > closes[0]
            return {"SPY": 10 if up else 0}

    res = run(Momentum(), Market.from_wide(prices), capital=10_000, costs=BpsCost(5))
    res.daily          # date | nav | pnl | cash | gross | net | traded | cost
    metrics(res)       # total and annual return, vol, Sharpe, max drawdown, turnover, costs

    # or, for a strategy that is just a weight per symbol per rebalance date:
    res = run_weights(weights, market, costs=BpsCost(5))   # weights: date | SPY | QQQ ...

The evaluation layer (Daniel and Paleologo, ADR-0013) works on numpy arrays: ``walk_forward`` and
``purged_kfold`` splits, ``net_pnl`` / ``risk_scaled`` / ``information_coefficient`` scores, and
``ras_lower_bounds`` for a T x N score matrix of every candidate tried. ``family`` joins the two
(ADR-0014): ``walk_forward_weights`` builds an out-of-sample weight table, ``evaluate`` haircuts
the ``Result`` of every candidate tried.
"""

from __future__ import annotations

from backtest.costs import BpsCost, CostModel, NoCost, PerUnitCost
from backtest.engine import run
from backtest.family import evaluate, scores, walk_forward_weights
from backtest.haircut import (
    annualize,
    block_means,
    massart_bound,
    rademacher,
    ras_lower_bounds,
    sharpe_se,
    subgaussian_lower_bounds,
)
from backtest.instruments import Cash, FxPair, Instrument
from backtest.market import LookaheadError, Market, MarketView
from backtest.metrics import metrics
from backtest.pnl import information_coefficient, net_pnl, risk_scaled
from backtest.result import Result
from backtest.splits import purged_kfold, walk_forward
from backtest.strategy import Context, Strategy
from backtest.weights import TargetWeights, run_weights

__version__ = "0.3.0"
__all__ = [
    "BpsCost",
    "Cash",
    "Context",
    "CostModel",
    "FxPair",
    "Instrument",
    "LookaheadError",
    "Market",
    "MarketView",
    "NoCost",
    "PerUnitCost",
    "Result",
    "Strategy",
    "TargetWeights",
    "annualize",
    "block_means",
    "evaluate",
    "information_coefficient",
    "massart_bound",
    "metrics",
    "net_pnl",
    "purged_kfold",
    "rademacher",
    "ras_lower_bounds",
    "risk_scaled",
    "run",
    "run_weights",
    "scores",
    "sharpe_se",
    "subgaussian_lower_bounds",
    "walk_forward",
    "walk_forward_weights",
]
