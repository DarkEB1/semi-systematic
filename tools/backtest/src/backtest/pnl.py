"""Per-date scores of one candidate: net PnL, risk-scaled return, information coefficient.

One timing convention everywhere, so the off-by-one is made once, here: row t of a decision
array (weights, vol, alpha) uses information available at date t; row t of an outcome array
(returns, resid) is realised over (t-1, t]. Decision row t is paired with outcome row t+1, so
every function returns T-1 values.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


def net_pnl(weights: npt.ArrayLike, returns: npt.ArrayLike, costs: npt.ArrayLike = 0.0) -> Array:
    """pnl[t+1] = weights[t] . returns[t+1] - costs[t].

    weights, returns: T x A (dollar positions, simple returns). costs: scalar or length T, the
    modelled execution + borrow + financing cost of weights[t], in the same dollars.
    """
    w = np.asarray(weights, dtype=np.float64)
    r = np.asarray(returns, dtype=np.float64)
    c = np.broadcast_to(np.asarray(costs, dtype=np.float64), (len(w),))
    return (w[:-1] * r[1:]).sum(axis=1) - c[:-1]


def risk_scaled(
    weights: npt.ArrayLike, returns: npt.ArrayLike, vol: npt.ArrayLike, costs: npt.ArrayLike = 0.0
) -> Array:
    """Net PnL divided by vol[t], the predicted dollar volatility of weights[t], formed at t."""
    return net_pnl(weights, returns, costs) / np.asarray(vol, dtype=np.float64)[:-1]


def information_coefficient(alpha: npt.ArrayLike, resid: npt.ArrayLike) -> Array:
    """Cosine similarity of alpha[t] with resid[t+1] (T x A each), one value per date.

    Equals the cross-sectional correlation when both rows are centred.
    """
    a = np.asarray(alpha, dtype=np.float64)[:-1]
    e = np.asarray(resid, dtype=np.float64)[1:]
    return (a * e).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(e, axis=1))
