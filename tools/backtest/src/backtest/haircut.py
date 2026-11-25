"""Evaluate a family of candidates jointly: the Rademacher Anti-Serum (RAS) and its comparators.

X is always the T x N score matrix: rows are evaluation dates on one common calendar, columns
are every candidate that was tried, including the abandoned ones.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


def rademacher(X: Array, B: int = 10_000, seed: int = 0, batch: int = 1_000) -> float:
    """Monte Carlo estimate of R = E max_n (1/T) sum_t eps_t x_tn over random signs eps.

    One sign vector per draw is shared by all columns, which preserves the dependence across
    candidates. Record `seed` and `B` with the result.
    """
    T = X.shape[0]
    rng = np.random.default_rng(seed)
    total = 0.0
    for start in range(0, B, batch):
        eps = rng.choice([-1.0, 1.0], size=(min(batch, B - start), T))
        total += float((eps @ X / T).max(axis=1).sum())
    return total / B


def ras_lower_bounds(
    X: Array,
    kappa: float,
    delta: float = 0.01,
    B: int = 10_000,
    seed: int = 0,
    mc_delta: float | None = None,
) -> tuple[Array, float]:
    """Lower bounds on every column's true mean, valid for all columns at once w.p. >= 1 - delta.

    L_n = mean_n - 2R - 3 kappa sqrt(2 log(2/delta) / T). Assumes a fixed family, iid rows and
    |x| <= kappa on every date. With `mc_delta`, R gains the Monte Carlo allowance
    kappa sqrt(2 log(1/mc_delta) / B) and coverage becomes 1 - delta - mc_delta.
    Returns (L, R) with R the plain Monte Carlo estimate. L <= 0 is inconclusive, not negative.
    """
    T = X.shape[0]
    R = rademacher(X, B, seed)
    allowance = 0.0 if mc_delta is None else kappa * np.sqrt(2 * np.log(1 / mc_delta) / B)
    est = 3 * kappa * np.sqrt(2 * np.log(2 / delta) / T)
    return X.mean(axis=0) - 2 * (R + allowance) - est, R


def subgaussian_lower_bounds(X: Array, sigma: float, delta: float = 0.01) -> Array:
    """mean_n - sigma sqrt(2 log(N/delta) / T): for scores with a justified sub-Gaussian proxy.

    Search included (a union bound over N); it does not adapt to dependence across candidates.
    """
    T, N = X.shape
    return X.mean(axis=0) - sigma * np.sqrt(2 * np.log(N / delta) / T)


def massart_bound(X: Array) -> float:
    """Scale check for `rademacher`: R <= max_n ||x_n||_2 sqrt(2 log N) / T."""
    T, N = X.shape
    return float(np.linalg.norm(X, axis=0).max() * np.sqrt(2 * np.log(N)) / T)


def block_means(X: Array, s: int) -> Array:
    """Average non-overlapping blocks of s rows (a trailing partial block is dropped).

    Diagnostic for serial dependence: rerun the bound on the T/s block rows.
    """
    n = X.shape[0] // s
    return X[: n * s].reshape(n, s, -1).mean(axis=1)


def annualize(sr: float, periods: int = 251) -> float:
    """Per-period Sharpe to annual: sr * sqrt(periods)."""
    return float(sr * np.sqrt(periods))


def sharpe_se(sr: float, T: int) -> float:
    """Standard error of one pre-chosen strategy's per-period Sharpe over T periods (iid Gaussian).

    `sr` must be in the same time unit as T. It does not account for selection.
    """
    return float(np.sqrt((1 + sr**2 / 2) / T))
