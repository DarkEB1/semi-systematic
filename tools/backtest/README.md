# backtest

The minimal backtesting framework from one source: Daniel and Paleologo, "Backtesting: Evaluating
Excess Returns" (FINC B8420 Quantitative Investing, lecture 6, Fall 2026). Nothing here goes beyond
that lecture (ADR-0013). It takes numpy arrays and returns numpy arrays; data access, cost models,
portfolio construction and plotting stay with the caller.

## The sequence

1. **Split** the T dates so every fit sees only the past: `walk_forward` (rolling or expanding,
   with a gap), or `purged_kfold` for development-sample model selection.
2. **Reconstruct** each candidate's positions with those fits, then score every date:
   `net_pnl`, `risk_scaled` (strategies) or `information_coefficient` (signals).
3. **Stack** every candidate tried, including the abandoned ones, into one T x N matrix `X` on a
   common calendar.
4. **Haircut** the family jointly: `ras_lower_bounds(X, kappa)`. Act only on a candidate whose
   lower bound is still positive.

```python
import numpy as np
import backtest as bt

columns = []
for fit_candidate in family:  # every variant, not only the survivors
    weights = np.zeros_like(returns)
    for train, test in bt.walk_forward(len(returns), train=500, test=21, gap=1):
        weights[test] = fit_candidate(train)(test)  # the caller's model
    columns.append(bt.risk_scaled(weights, returns, vol, costs))
X = np.column_stack(columns)[501:]  # drop the rows before the first test date (train + gap)
L, R = bt.ras_lower_bounds(X, kappa=kappa, delta=0.01, seed=0)  # kappa fixed in advance
```

## Timing convention

Row t of a decision array (`weights`, `vol`, `alpha`) uses information available at date t. Row t
of an outcome array (`returns`, `resid`) is realised over (t-1, t]. The functions in `pnl.py` pair
decision row t with outcome row t+1 themselves and return T-1 values, so a caller never shifts.

## API

| name | what it computes |
|---|---|
| `walk_forward(n, train, test, gap, expanding)` | (train, test) indices, training strictly before the test |
| `purged_kfold(n, k, purge, embargo)` | K contiguous folds; `purge` dates dropped before the test fold, `embargo` after |
| `net_pnl(weights, returns, costs)` | `w[t] . r[t+1] - costs[t]`; `costs` is the caller's execution + borrow + financing total |
| `risk_scaled(weights, returns, vol, costs)` | net PnL over the volatility predicted at t |
| `information_coefficient(alpha, resid)` | cosine of `alpha[t]` with `resid[t+1]`, per date |
| `rademacher(X, B, seed)` | how well the best column lines up with random signs |
| `ras_lower_bounds(X, kappa, delta, B, seed, mc_delta)` | `mean - 2R - 3 kappa sqrt(2 log(2/delta)/T)` per column, and R |
| `subgaussian_lower_bounds(X, sigma, delta)` | `mean - sigma sqrt(2 log(N/delta)/T)`, for unbounded scores with a justified proxy |
| `massart_bound(X)` | `max ||x_n|| sqrt(2 log N)/T`, a scale check on R |
| `block_means(X, s)` | block-averaged rows, to test sensitivity to serial dependence |
| `annualize(sr)`, `sharpe_se(sr, T)` | `sr sqrt(251)`; `sqrt((1 + sr^2/2)/T)` for one pre-chosen strategy |

## What the numbers assume

- The rows of `X` are treated as iid. Columns may be arbitrarily dependent; correlated candidates
  cost less than distinct ones, and exact copies cost nothing.
- `kappa` must bound every score on every date, chosen before looking. A daily IC is not bounded
  by its typical size; use `subgaussian_lower_bounds` there.
- The family is fixed and complete. Leaving out tried variants understates the search.
- A lower bound at or below zero is inconclusive. It does not say performance is zero or negative.
- No haircut repairs leakage: point-in-time data, universe and costs must already be credible.

## Not here

The cost model in [conventions.md](../../knowledge/context/conventions.md) (the lecture names the
cost terms but gives no model, so `costs` is an input), the calibrated `a0`, `b0` screens the
lecture reports without a guarantee, data access (`quant.data`) and plotting.
