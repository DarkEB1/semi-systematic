# backtest

A daily backtesting engine for any position-based strategy: a strategy says what it wants to hold
after each close, the engine fills it, pays the costs, values the book every day and reports the
P&L, split by instrument and cause. It is a tool in the sense of [tools/README.md](../README.md):
it takes market data and a strategy as arguments and never reads the bucket, `.env` or the
repository. The design and its exception to the second-use rule are
[ADR-0010](../../knowledge/decisions/ADR-0010-backtest-engine.md).

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

## Limits

Daily only; fills at the close plus a cost model, no order book or market impact; cash earns no
interest (the Sharpe is over cash for self-funded positions only); no dividends, short-borrow
cost, margin or financing; carry is simple interest on 360 days for every currency (BRL's CDI
compounds on 252); a cross is shown as its two legs; one book per run (no per-member books yet).

## Tests

`uv run pytest tools/backtest/tests -q`: about a hundred tests on hand-computed fixtures, no
network or bucket. Each module has its own file; `test_weights.py` checks that a weight table and
the equivalent hand-written `Strategy` give identical results.
