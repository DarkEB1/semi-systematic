"""backtest: walk-forward splits, net PnL scores and a joint haircut for a family of candidates.

A tool: an isolated package that takes arrays as arguments and knows nothing about the
repository, the bucket or .env. Contract: tools/README.md; method and its source: README.md here.
"""

from __future__ import annotations

from backtest.haircut import (
    annualize,
    block_means,
    massart_bound,
    rademacher,
    ras_lower_bounds,
    sharpe_se,
    subgaussian_lower_bounds,
)
from backtest.pnl import information_coefficient, net_pnl, risk_scaled
from backtest.splits import purged_kfold, walk_forward

__version__ = "0.2.0"
__all__ = [
    "annualize",
    "block_means",
    "information_coefficient",
    "massart_bound",
    "net_pnl",
    "purged_kfold",
    "rademacher",
    "ras_lower_bounds",
    "risk_scaled",
    "sharpe_se",
    "subgaussian_lower_bounds",
    "walk_forward",
]
