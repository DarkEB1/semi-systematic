# backtest

A daily backtesting engine for any position-based strategy: a strategy says what it wants to hold
after each close, the engine fills it, pays the costs, values the book every day and reports the
P&L, split by instrument and cause; then it evaluates the whole family of variants that was tried,
with a haircut for the search (Daniel and Paleologo). It is a tool in the sense of [tools/README.md](../README.md):
it takes market data and a strategy as arguments and never reads the bucket, `.env` or the
repository. The engine and the bridge are
[ADR-0014](../../knowledge/decisions/ADR-0014-backtest-engine.md), the evaluation layer
[ADR-0013](../../knowledge/decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md).

## Use

```python
from backtest import BpsCost, FxPair, Market, Strategy, metrics, run, run_weights

market = Market.from_long(
    spots, value="value", extras={"rates": Market.from_long(rates, symbol="currency", value="rate")}
)

# A strategy that is a table of weights (date | EURUSD | USDBRL ...), rebalanced on each row:
res = run_weights(weights, market, instruments={s: FxPair(s) for s in pairs}, costs=BpsCost(5))


# A strategy that decides day by day and keeps state:
class Mine(Strategy):
    def on_day(self, ctx):
        closes = ctx.market.closes("USDBRL", lookback=200)  # never past today
        ...
        return ctx.quantities({FxPair("USDBRL"): -0.5})  # weights of NAV -> quantities


res = run(Mine(), market, capital=1_000_000, costs=BpsCost(5))

res.daily  # date | nav | pnl | cash | gross | net | traded | cost
res.attribution()  # per instrument: price, cashflow (carry), cost, pnl
metrics(res, periods_per_year=260)  # returns, vol, Sharpe, drawdown, turnover, cost drag
```

The experiment loads the data (through `quant.data`) and builds the `Market`; the engine sees
nothing else.

Then evaluate every variant tried, out of sample, in one haircut:

```python
from backtest import evaluate, walk_forward_weights


def fit(view, window):  # view: market frozen at the last training close
    lookback = choose_on(view, window)  # the caller's model
    return lambda today: signal(today, lookback)  # today: market frozen at the decision close


results = {}
for name, f in candidates.items():  # every variant, the abandoned ones included
    w = walk_forward_weights(f, market, train=750, test=21)
    results[name] = run_weights(w, market, instruments=..., start=w["date"][0], costs=costs)

table, R = evaluate(results, kappa=0.05, delta=0.01, seed=0, start=first_test_date)
table  # candidate | days | mean | sharpe | lower_bound | ann_mean | ann_lower_bound
```

## How it works

Three layers, and the engine between them:

| piece | module | job |
|---|---|---|
| `Market` | `market.py` | prices by symbol and day, named `extras` (rates, surfaces), the accounting `currency`, `rate()` conversion; `MarketView` is the same data frozen at one day |
| `Instrument` | `instruments/` | what one unit is worth (`value`), what it pays (`cashflow`), its `exposure`; `Cash` (stocks, ETFs, indices, any quote currency), `FxPair` (spot FX with carry; crosses held as two legs) |
| `Strategy`, `Context` | `strategy.py` | the user's code: `on_day(ctx)` returns target quantities, `None` to change nothing |
| `CostModel` | `costs.py` | the charge on each fill: `BpsCost` (bp of notional, per id or bucket), `PerUnitCost`, summed with `+` |
| `run` | `engine.py` | the day loop: revalue and pay cashflows, fill due orders, ask the strategy, fill, record |
| `run_weights` | `weights.py` | wraps a weight table in a `TargetWeights` strategy and calls `run` |
| `Result`, `metrics` | `result.py`, `metrics.py` | the tables (`daily`, `positions`, `trades`, `pnl`) and the summary |

The books are cash plus marks: buying lowers cash, `nav = cash + sum(quantity * value)`, and a
day's P&L is the change in NAV, so longs, shorts and every asset class are counted the same way.
A decision taken at a close fills at that close (`delay=0`) or a later one (`delay=1`) and earns
the move from then on, never the move that produced it. A missing observation is a missing day,
never a zero return: the mark is kept and the order waits for the next price. Data a strategy
reads through `ctx.market` stops at today (`LookaheadError` otherwise); `extras` are not guarded.

## Conventions it applies

From [conventions.md](../../knowledge/context/conventions.md): simple returns, no forward-filling
of prices, a flat half-spread per trade by bucket (`BpsCost.by_bucket`), amounts in one accounting
currency (USD unless the `Market` says otherwise). FX: being long a pair is long its base; one
unit of `USDBRL` is 1 BRL owed, so a long earns `1 - S0/S1` per dollar; carry accrues daily as
`exposure * (r_base - r_quote) * days / 360` from rates known at the previous close.

## Evaluating a family of strategies

The evaluation layer comes from one source: Daniel and Paleologo, "Backtesting: Evaluating
Excess Returns" (FINC B8420 Quantitative Investing, lecture 6, Fall 2026), and goes no further
than that lecture ([ADR-0013](../../knowledge/decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md)).
Its functions take numpy arrays and return numpy arrays; `family.py` feeds them from the engine:

| name | what it does |
|---|---|
| `walk_forward_weights(fit, market, train, test, gap, expanding)` | a weight table where `fit` sees the market at the last training close and its rule the market at each decision close; `None` holds |
| `scores(results, start)` | `date \| candidate...`: each `Result`'s daily NAV return on the dates all share |
| `evaluate(results, kappa, delta, B, seed, start, periods_per_year)` | `ras_lower_bounds` over `scores` (or a `scores` table), one row per candidate, best bound first, and R; raises if a score exceeds `kappa` |
| `save_scores(results, directory)` | each result's daily returns to `directory/<name>.parquet`; a rerun under the same name replaces it |
| `load_scores(*directories, start)` | the `scores` table of every saved candidate in those directories; a name in two of them raises |

A family tried over several runs or experiments: each run saves its candidates, e.g. to its own
`outputs/scores/`, and the evaluation loads them all, so the variants of last week count too:

```python
save_scores(results, HERE / "outputs" / "scores")
table, R = evaluate(load_scores(dir_monday, dir_wednesday), kappa=0.12, start=first_test_date)
```

`outputs/` is gitignored, so saved scores stay on the machine that ran them.

The engine books decision t at t+1, so `scores` already follows the timing convention below.

How to read it, on a real example: long BRL carry (short USDBRL when the CDI is above the EFFR),
alone or with a 50 to 250-day trend filter, plus one variant picking its filter walk-forward;
seven candidates, 2005-12 to 2026-11, net of 5 bp. Sharpe ratios run from 0.38 to 0.48 (4 to 5%
a year). `2R`, the cost of having searched, is 3.6% a year: the filters' Sharpe gain of about 0.1
is within it, and the walk-forward picker never settles on one filter. With a sub-Gaussian proxy
the best lower bound is about -8% a year: inconclusive, not a loss. Over 20 years of daily data a
candidate needs an annual Sharpe of about 0.8 to 1 to clear zero.

On daily NAV returns, use `R` and `subgaussian_lower_bounds`: the bounded bound of `evaluate`
needs `kappa` to cover the worst day (10% for USDBRL), far above the daily vol (1%), so its
estimation term alone exceeds 100% a year and the bound says nothing.

### The sequence

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

### Timing convention

Row t of a decision array (`weights`, `vol`, `alpha`) uses information available at date t. Row t
of an outcome array (`returns`, `resid`) is realised over (t-1, t]. The functions in `pnl.py` pair
decision row t with outcome row t+1 themselves and return T-1 values, so a caller never shifts.

### API

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

### What the numbers assume

- The rows of `X` are treated as iid. Columns may be arbitrarily dependent; correlated candidates
  cost less than distinct ones, and exact copies cost nothing.
- `kappa` must bound every score on every date, chosen before looking. A daily IC is not bounded
  by its typical size; use `subgaussian_lower_bounds` there.
- The family is fixed and complete. Leaving out tried variants understates the search.
- A lower bound at or below zero is inconclusive. It does not say performance is zero or negative.
- No haircut repairs leakage: point-in-time data, universe and costs must already be credible.

### Not here

The cost model in [conventions.md](../../knowledge/context/conventions.md) (the lecture names the
cost terms but gives no model, so `costs` is an input), the calibrated `a0`, `b0` screens the
lecture reports without a guarantee, data access (`quant.data`) and plotting.

## Limits

Daily only; fills at the close plus a cost model, no order book or market impact; cash earns no
interest (the Sharpe is over cash for self-funded positions only); no dividends, short-borrow
cost, margin or financing; carry is simple interest on 360 days for every currency (BRL's CDI
compounds on 252); a cross is shown as its two legs; one book per run (no per-member books yet).

## Tests

`uv run pytest tools/backtest/tests -q`: about 120 tests on hand-computed fixtures, no network or
bucket. Each module has its own file; `test_weights.py` checks that a weight table and the
equivalent hand-written `Strategy` give identical results; `test_backtest.py` pins the lecture's
worked numbers; `test_family.py` checks that walk-forward fits cannot see the future and that
`evaluate` equals `ras_lower_bounds` on the same matrix.
