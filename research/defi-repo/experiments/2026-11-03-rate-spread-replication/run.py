"""Independent replication and conditional carry. Run with uv run --extra ml."""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import json
    from pathlib import Path

    import matplotlib

    matplotlib.use("Agg")
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
    import yaml
    from statsmodels.tsa.stattools import adfuller, coint

    from quant import data

    here = Path(__file__).resolve().parent
    config = yaml.safe_load((here / "config.yaml").read_text(encoding="utf-8-sig"))
    return adfuller, coint, config, data, here, json, mo, np, pd, plt, sm


@app.cell
def _(np, pd):
    def index_ratio(values, shift):
        other = values.shift(shift)
        return pd.Series(
            [
                int(a) / int(b) - 1 if pd.notna(b) else np.nan
                for a, b in zip(values, other, strict=True)
            ],
            index=values.index,
        )

    return (index_ratio,)


@app.cell
def _(index_ratio, np, pd):
    def prepare_panel(tables, params):
        raw = tables["aave_reserve_daily"].to_pandas()
        raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
        raw = raw.sort_values(["symbol", "protocol", "date"]).reset_index(drop=True)
        chunks = []
        for _, group in raw.groupby(["symbol", "protocol"], sort=False):
            g = group.copy()
            elapsed = g["block_time"].diff().dt.total_seconds()
            consecutive = g["date"].diff().dt.days.eq(1)
            g["earned_apr"] = (
                index_ratio(g["income_index"], 1) * 365 * 86400 * 100 / elapsed
            ).where(consecutive)
            g["forward_interest"] = (
                -index_ratio(g["income_index"], -1) / (1 + index_ratio(g["income_index"], -1))
            ).where(g["date"].shift(-1).sub(g["date"]).dt.days.eq(1))
            g["forward_borrow"] = (
                -index_ratio(g["borrow_index"], -1) / (1 + index_ratio(g["borrow_index"], -1))
            ).where(g["date"].shift(-1).sub(g["date"]).dt.days.eq(1))
            g["price_next"] = g["price_usd"].shift(-1)
            for field in ["base_fee_gwei", "eth_usd", "available_tokens"]:
                g[f"next_{field}"] = g[field].shift(-1)
            g["price_age_hours"] = (g["block_time"] - g["price_time"]).dt.total_seconds() / 3600
            g["next_price_age_hours"] = g["price_age_hours"].shift(-1)
            chunks.append(g)
        full = pd.concat(chunks).sort_values("date")
        switch = pd.Timestamp(params["protocol_switch"])
        selected = full[
            (full["protocol"].eq("v2") & full["date"].lt(switch))
            | (full["protocol"].eq("v3") & full["date"].ge(switch))
        ].copy()
        rates = tables["usd_reference_rates"].to_pandas()
        rates["date"] = pd.to_datetime(rates["date"]).astype("datetime64[ns]")
        sofr = rates[rates["symbol"].eq("SOFR")].sort_values("date")[["date", "rate_pct"]]
        sofr = sofr.rename(columns={"date": "sofr_effective", "rate_pct": "sofr"})
        selected = pd.merge_asof(selected, sofr, left_on="date", right_on="sofr_effective")
        assert (
            selected["date"].sub(selected["sofr_effective"]).dt.days.max()
            <= params["sofr_max_span_days"]
        )
        available = sofr.copy()
        available["available_at"] = available["sofr_effective"].shift(-1) + pd.Timedelta(days=1)
        available = available.dropna().rename(
            columns={"sofr": "known_sofr", "sofr_effective": "known_sofr_effective"}
        )
        selected = pd.merge_asof(selected, available, left_on="date", right_on="available_at")
        selected["spread_bp"] = (selected["earned_apr"] - selected["sofr"]) * 100
        selected["cash_return"] = selected["sofr"] / 100 / 360
        selected["usd_return"] = (1 + selected["forward_interest"]) * selected[
            "price_next"
        ] / selected["price_usd"] - 1
        selected["utilization"] = (
            selected["variable_debt_tokens"] + selected["stable_debt_tokens"]
        ) / selected["supply_tokens"]
        panel = selected.sort_values(["symbol", "date"]).reset_index(drop=True)
        panel["signal_bp"] = (
            panel.groupby("symbol")["supply_apr_pct"]
            .shift(params["signal_lag_days"])
            .sub(panel.groupby("symbol")["known_sofr"].shift(params["signal_lag_days"]))
            * 100
        )
        panel["price_valid"] = panel["price_usd"].gt(0) & panel["price_age_hours"].le(
            params["max_oracle_age_hours"]
        )
        # Keep old-pool withdrawal liquidity for the descriptive protocol migration.
        old = full[full["date"].eq(switch) & full["protocol"].eq("v2")].set_index("symbol")
        panel["migration_exit_liquidity"] = panel["symbol"].map(
            old["available_tokens"] * old["price_usd"]
        )
        return panel, raw

    def weekly_panel(panel, params):
        rows = []
        for symbol, g in panel.groupby("symbol"):
            g = g[g["date"].between(params["start"], params["end"])]
            g = g[g["date"].dt.day_of_week.lt(5)].set_index("date")
            w = (
                g[
                    [
                        "earned_apr",
                        "sofr",
                        "btc_usd",
                        "utilization",
                        "supply_tokens",
                        "variable_debt_tokens",
                    ]
                ]
                .resample(params["weekly_anchor"])
                .mean()
            )
            counts = g["earned_apr"].resample(params["weekly_anchor"]).count()
            w = w[counts.eq(5)].copy()
            w["spread"] = w["earned_apr"] - w["sofr"]
            w["btc_log_change"] = np.log(w["btc_usd"]).diff()
            w["symbol"] = symbol
            rows.append(w.reset_index())
        return pd.concat(rows, ignore_index=True)

    return prepare_panel, weekly_panel


@app.cell
def _(adfuller, coint, np, pd, sm):
    def ecm_one(w, params):
        s = w["spread"].reset_index(drop=True)
        model = pd.DataFrame(
            {"dy": s.diff(), "level": s.shift(1), "btc": w["btc_log_change"].reset_index(drop=True)}
        )
        max_lags = params["ecm_max_lags"]
        for lag in range(1, max_lags + 1):
            model[f"d{lag}"] = s.diff().shift(lag)
        common = model.dropna()
        candidates = []
        for lag in range(max_lags + 1):
            cols = ["level", "btc"] + [f"d{i}" for i in range(1, lag + 1)]
            fit = sm.OLS(common["dy"], sm.add_constant(common[cols])).fit()
            candidates.append((fit.bic, lag, cols))
        _, lag, cols = min(candidates)
        sample = model[["dy", *cols]].dropna()
        fit = sm.OLS(sample["dy"], sm.add_constant(sample[cols])).fit(
            cov_type="HAC", cov_kwds={"maxlags": params["hac_lags"]}
        )
        ar = sm.OLS(s.iloc[1:].to_numpy(), sm.add_constant(s.iloc[:-1].to_numpy())).fit(
            cov_type="HAC", cov_kwds={"maxlags": params["hac_lags"]}
        )
        rho = float(ar.params[1])
        interval = fit.conf_int().loc["level"].tolist()
        return {
            "n": int(fit.nobs),
            "lags": lag,
            "level_beta": fit.params["level"],
            "level_se": fit.bse["level"],
            "level_p": fit.pvalues["level"],
            "level_ci_low": interval[0],
            "level_ci_high": interval[1],
            "btc_beta": fit.params["btc"],
            "r2": fit.rsquared,
            "ar1_rho": rho,
            "half_life_weeks": np.log(0.5) / np.log(rho) if 0 < rho < 1 else None,
            "adf_p": adfuller(s, maxlag=max_lags, autolag="BIC")[1],
            "engle_granger_p": coint(w["earned_apr"], w["sofr"], maxlag=max_lags, autolag="bic")[1],
        }

    def sequential_forecast(w, params):
        s = w["spread"].to_numpy()
        records = []
        for i in range(params["forecast_min_weeks"], len(s) - 1):
            fit = sm.OLS(s[1 : i + 1], sm.add_constant(s[:i])).fit()
            prediction = float(fit.params[0] + fit.params[1] * s[i])
            records.append(
                {
                    "date": w.iloc[i + 1]["date"],
                    "observed": s[i + 1],
                    "ar1": prediction,
                    "no_change": s[i],
                    "symbol": w.iloc[0]["symbol"],
                }
            )
        result = pd.DataFrame(records)
        model_loss = (result["observed"] - result["ar1"]) ** 2
        naive_loss = (result["observed"] - result["no_change"]) ** 2
        difference = naive_loss - model_loss
        test = sm.OLS(difference, np.ones((len(difference), 1))).fit(
            cov_type="HAC", cov_kwds={"maxlags": params["hac_lags"]}
        )
        summary = {
            "symbol": w.iloc[0]["symbol"],
            "n": len(result),
            "rmse_ar1_pp": np.sqrt(model_loss.mean()),
            "rmse_no_change_pp": np.sqrt(naive_loss.mean()),
            "mse_skill": 1 - model_loss.mean() / naive_loss.mean(),
            "loss_difference_hac_p": float(test.pvalues.iloc[0]),
        }
        return result, summary

    def statistical_evidence(weekly, panel, params):
        estimates, forecasts, forecast_summary, descriptions = [], [], [], []
        for symbol, w in weekly.groupby("symbol"):
            for label, start in [("full", params["start"]), ("exclude_2021", "2022-01-01")]:
                sample = w[w["date"].ge(start)].copy()
                estimates.append({"symbol": symbol, "sample": label, **ecm_one(sample, params)})
            forecast, summary = sequential_forecast(w, params)
            forecasts.append(forecast)
            forecast_summary.append(summary)
            daily = panel[
                panel["symbol"].eq(symbol) & panel["date"].between(params["start"], params["end"])
            ].dropna(subset=["earned_apr"])
            descriptions.append(
                {
                    "symbol": symbol,
                    "days": len(daily),
                    "mean_spread_bp": daily["spread_bp"].mean(),
                    "below_sofr_pct": daily["spread_bp"].lt(0).mean() * 100,
                    "mean_earned_apr_pct": daily["earned_apr"].mean(),
                    "weekly_delta_rate_btc_corr": w["earned_apr"].diff().corr(w["btc_log_change"]),
                    "weekly_delta_rate_utilization_corr": w["earned_apr"]
                    .diff()
                    .corr(w["utilization"].diff()),
                    "variable_borrow_below_sofr_pct": (
                        daily["forward_borrow"] < daily["cash_return"]
                    ).mean()
                    * 100,
                }
            )
        return (
            pd.DataFrame(estimates),
            pd.concat(forecasts),
            pd.DataFrame(forecast_summary),
            pd.DataFrame(descriptions),
        )

    return statistical_evidence, sequential_forecast


@app.cell
def _():
    def reserve_open(row, capital):
        bits = int(row.reserve_hex[2:66], 16)
        active, frozen = bool(bits & (1 << 56)), bool(bits & (1 << 57))
        paused = row.protocol == "v3" and bool(bits & (1 << 60))
        cap = (bits >> 116) & ((1 << 36) - 1) if row.protocol == "v3" else 0
        space = not cap or (row.supply_tokens + capital / row.price_usd < cap)
        return active and not frozen and not paused and space

    return (reserve_open,)


@app.cell
def _(reserve_open):
    def target_position(row, state, previous_protocol, params, hurdle, capital, mode):
        rebalance = row.date.day_of_week == params["rebalance_weekday"] or previous_protocol is None
        desired = (row.signal_bp > hurdle) if mode == "switch" else True
        target = bool(desired) if rebalance else state
        migrate = state and previous_protocol != row.protocol
        if not row.price_valid:
            if state:
                raise ValueError(f"missing/stale mark while invested: {row.symbol} {row.date}")
            target = False
        if target and (not state or migrate) and not reserve_open(row, capital):
            target = False
        available = (
            row.migration_exit_liquidity if migrate else row.available_tokens * row.price_usd
        )
        if state and (not target or migrate) and available < capital:
            raise ValueError(f"withdrawal not feasible: {row.symbol} {row.date}")
        actions = int(target != state) + (2 if migrate and target else 0)
        return target, actions

    def close_position(last, cost_bp, notional, gas):
        fee = last["nav"] * cost_bp / 10000 + gas / notional
        last["token_nav"] -= last["token_nav"] * cost_bp / 10000 + gas / notional
        last["nav"] -= fee
        last["return"] = last["nav"] / last["nav_before"] - 1
        last["actions"] += 1
        last["fee_nav"] += fee
        last["gas_usd"] += gas

    return close_position, target_position


@app.cell
def _(close_position, np, pd, target_position):
    def simulate(g, params, hurdle, cost_bp, notional, mode="switch"):
        nav, benchmark, token_nav, state, previous_protocol = 1.0, 1.0, 1.0, False, None
        history = []
        for row in g.itertuples():
            target, actions = target_position(
                row, state, previous_protocol, params, hurdle, nav * notional, mode
            )
            gas_usd = (
                params["gas_units_per_action"]
                * (row.base_fee_gwei + params["priority_fee_gwei"])
                * 1e-9
                * row.eth_usd
            )
            if actions and not np.isfinite(gas_usd):
                raise ValueError("gas data missing at simulated trade")
            if target and (
                not np.isfinite(row.usd_return)
                or row.next_price_age_hours > params["max_oracle_age_hours"]
            ):
                raise ValueError(
                    "future mark missing/stale while invested; simulation cannot be valued"
                )
            fee = actions * (nav * cost_bp / 10000 + gas_usd / notional)
            token_fee = actions * (token_nav * cost_bp / 10000 + gas_usd / notional)
            before = nav
            nav = (nav - fee) * (1 + (row.usd_return if target else row.cash_return))
            token_nav = (token_nav - token_fee) * (
                1 + (row.forward_interest if target else row.cash_return)
            )
            benchmark *= 1 + row.cash_return
            history.append(
                {
                    "date": row.date,
                    "nav": nav,
                    "nav_before": before,
                    "benchmark": benchmark,
                    "token_nav": token_nav,
                    "return": nav / before - 1,
                    "cash_return": row.cash_return,
                    "invested": target,
                    "actions": actions,
                    "fee_nav": fee,
                    "gas_usd": actions * gas_usd,
                    "capacity_fraction": nav * notional / (row.supply_tokens * row.price_usd)
                    if target
                    else 0,
                    "signal_bp": row.signal_bp,
                }
            )
            state, previous_protocol = target, row.protocol
        if state:
            terminal_gas = (
                params["gas_units_per_action"]
                * (row.next_base_fee_gwei + params["priority_fee_gwei"])
                * 1e-9
                * row.next_eth_usd
            )
            if row.next_available_tokens * row.price_next < nav * notional:
                raise ValueError("terminal withdrawal liquidity insufficient")
            close_position(history[-1], cost_bp, notional, terminal_gas)
        result = pd.DataFrame(history)
        if result["nav"].min() <= 0:
            raise ValueError("simulated costs exhaust capital")
        return result

    return (simulate,)


@app.cell
def _(np):
    def performance(path):
        end = path.iloc[-1]
        years = len(path) / 365
        peak = path["nav"].cummax().clip(lower=1)
        excess = path["return"] - path["cash_return"]
        return {
            "days": len(path),
            "net_return_pct": (end["nav"] - 1) * 100,
            "cash_return_pct": (end["benchmark"] - 1) * 100,
            "excess_terminal_pp": (end["nav"] - end["benchmark"]) * 100,
            "net_cagr_pct": (end["nav"] ** (1 / years) - 1) * 100,
            "cash_cagr_pct": (end["benchmark"] ** (1 / years) - 1) * 100,
            "interest_only_return_pct": (end["token_nav"] - 1) * 100,
            "max_drawdown_pct": (path["nav"] / peak - 1).min() * 100,
            "excess_sharpe": excess.mean() / excess.std(ddof=1) * np.sqrt(365)
            if excess.std(ddof=1) > 0
            else None,
            "invested_pct": path["invested"].mean() * 100,
            "actions": int(path["actions"].sum()),
            "gas_usd": path["gas_usd"].sum(),
            "max_supply_share_pct": path["capacity_fraction"].max() * 100,
        }

    return (performance,)


@app.cell
def _(np, pd, performance, simulate):
    def carry_evidence(panel, params):
        summaries, paths, annual = [], [], []
        for symbol, group in panel.groupby("symbol"):
            g = group[group["date"].between(params["trading_start"], params["end"])].copy()
            assert g["date"].diff().dropna().dt.days.eq(1).all()
            assert g["forward_interest"].notna().all()
            for hurdle in params["entry_hurdles_bp"]:
                for cost in params["one_way_costs_bp"]:
                    for capital in params["notionals_usd"]:
                        path = simulate(g, params, hurdle, cost, capital)
                        summaries.append(
                            {
                                "symbol": symbol,
                                "hurdle_bp": hurdle,
                                "cost_bp": cost,
                                "notional_usd": capital,
                                "mode": "switch",
                                **performance(path),
                            }
                        )
                        if (hurdle, cost, capital) == (
                            params["baseline_hurdle_bp"],
                            params["baseline_cost_bp"],
                            params["baseline_notional_usd"],
                        ):
                            path["symbol"] = symbol
                            paths.append(path)
                            for year, part in path.groupby(path["date"].dt.year):
                                annual.append(
                                    {
                                        "symbol": symbol,
                                        "year": year,
                                        "net_return_pct": (np.prod(1 + part["return"]) - 1) * 100,
                                        "cash_return_pct": (np.prod(1 + part["cash_return"]) - 1)
                                        * 100,
                                        "actions": int(part["actions"].sum()),
                                    }
                                )
            gross = simulate(
                g,
                dict(params, gas_units_per_action=0),
                params["baseline_hurdle_bp"],
                0,
                params["baseline_notional_usd"],
            )
            summaries.append(
                {
                    "symbol": symbol,
                    "hurdle_bp": params["baseline_hurdle_bp"],
                    "cost_bp": 0,
                    "notional_usd": params["baseline_notional_usd"],
                    "mode": "frictionless",
                    **performance(gross),
                }
            )
            hold = simulate(
                g,
                params,
                0,
                params["baseline_cost_bp"],
                params["baseline_notional_usd"],
                mode="hold",
            )
            summaries.append(
                {
                    "symbol": symbol,
                    "hurdle_bp": -1,
                    "mode": "hold",
                    "cost_bp": params["baseline_cost_bp"],
                    "notional_usd": params["baseline_notional_usd"],
                    **performance(hold),
                }
            )
        return pd.DataFrame(summaries), pd.concat(paths), pd.DataFrame(annual)

    return (carry_evidence,)


@app.cell
def _(np, pd):
    def uncertainty(paths, params, seed):
        rng = np.random.default_rng(seed)
        rows = []
        for symbol, path in paths.groupby("symbol"):
            x = (path["return"] - path["cash_return"]).to_numpy()
            size = params["bootstrap_block_days"]
            starts = rng.integers(
                0, len(x), size=(params["bootstrap_draws"], int(np.ceil(len(x) / size)))
            )
            indices = (starts[:, :, None] + np.arange(size)) % len(x)
            means = x[indices.reshape(len(starts), -1)[:, : len(x)]].mean(axis=1) * 365 * 100
            lo, hi = np.quantile(means, [0.025, 0.975])
            rows.append(
                {
                    "symbol": symbol,
                    "annual_mean_excess_pct": x.mean() * 365 * 100,
                    "block_bootstrap_ci_low": lo,
                    "block_bootstrap_ci_high": hi,
                }
            )
        return pd.DataFrame(rows)

    return (uncertainty,)


@app.cell
def _(np, pd, plt):
    def draw_figures(panel, weekly, paths, here, params):
        plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
        for symbol, w in weekly.groupby("symbol"):
            axes[0].plot(w["date"], w["earned_apr"], label=symbol, lw=1)
            axes[1].plot(w["date"], w["spread"] * 100, label=symbol, lw=1)
            axes[2].plot(w["date"], w["utilization"], label=symbol, lw=1)
        one = weekly[weekly["symbol"].eq("USDC")]
        axes[0].plot(one["date"], one["sofr"], label="SOFR", color="black", lw=1.5)
        axes[0].set_ylabel("Earned APR / SOFR (%)")
        axes[1].set_ylabel("Deposit minus SOFR (bp)")
        axes[1].axhline(0, color="black", lw=0.7)
        axes[2].set_ylabel("Borrowed / supplied")
        axes[0].legend(ncol=4)
        fig.suptitle("Independent daily-index reconstruction: weekly business-day averages")
        fig.tight_layout()
        fig.savefig(here / "figures/rates-and-spreads.png", dpi=140)
        plt.close(fig)
        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        for symbol, path in paths.groupby("symbol"):
            axes[0].plot(path["date"], (path["nav"] - 1) * 100, label=symbol)
            axes[1].plot(path["date"], (path["nav"] - path["benchmark"]) * 100, label=symbol)
        one = paths[paths["symbol"].eq("USDC")]
        axes[0].plot(
            one["date"], (one["benchmark"] - 1) * 100, label="SOFR benchmark", color="black"
        )
        axes[0].set_ylabel("Cumulative return (%)")
        axes[1].set_ylabel("Excess terminal wealth (pp)")
        axes[1].axhline(0, color="black", lw=0.7)
        axes[0].legend(ncol=4)
        fig.suptitle(
            "Conditional USD-marked carry: 100 bp hurdle, 5 bp/action + gas, $100k\nOracle marks are not executable prices; benchmark access is assumed"
        )
        fig.tight_layout()
        fig.savefig(here / "figures/conditional-carry.png", dpi=140)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(11, 4))
        event = panel[panel["date"].between("2023-03-05", "2023-03-20")]
        for symbol, g in event.groupby("symbol"):
            ax.plot(g["date"], g["price_usd"], label=symbol, marker=".")
        ax.axhline(1, color="black", lw=0.7)
        ax.set_ylabel("USD oracle mark")
        ax.set_title("March 2023: daily midnight marks miss intraday extremes")
        ax.legend(ncol=3)
        fig.tight_layout()
        fig.savefig(here / "figures/depeg-marks.png", dpi=140)
        plt.close(fig)

    def quality_evidence(panel, raw, params):
        study = panel[panel["date"].between(params["start"], params["end"])]
        rows = []
        for symbol, g in study.groupby("symbol"):
            assert g["date"].diff().dropna().dt.days.eq(1).all()
            assert g["earned_apr"].notna().all()
            assert g["forward_interest"].ge(0).all()
            for asset in ["btc", "eth"]:
                age = (g["block_time"] - g[f"{asset}_price_time"]).dt.total_seconds() / 3600
                assert age.between(0, params["max_oracle_age_hours"]).all()
            rows.append(
                {
                    "symbol": symbol,
                    "rows": len(g),
                    "first": str(g["date"].min().date()),
                    "last": str(g["date"].max().date()),
                    "missing_price_days": int(g["price_usd"].isna().sum()),
                    "stale_price_days": int(
                        g["price_age_hours"].gt(params["max_oracle_age_hours"]).sum()
                    ),
                    "min_oracle_price": g["price_usd"].min(),
                    "max_oracle_age_hours": g["price_age_hours"].max(),
                    "max_cutoff_gap_seconds": (
                        pd.to_datetime(g["date"], utc=True) - g["block_time"]
                    )
                    .dt.total_seconds()
                    .max(),
                }
            )
        assert not raw.duplicated(["date", "symbol", "protocol"]).any()
        return pd.DataFrame(rows)

    return draw_figures, quality_evidence


@app.cell
def _(
    prepare_panel,
    weekly_panel,
    quality_evidence,
    statistical_evidence,
    carry_evidence,
    uncertainty,
    draw_figures,
):
    pipeline = (
        prepare_panel,
        weekly_panel,
        quality_evidence,
        statistical_evidence,
        carry_evidence,
        uncertainty,
        draw_figures,
    )
    return (pipeline,)


@app.cell
def invariant_checks(config, here, index_ratio, json, np, pd, sequential_forecast, simulate):
    _params = dict(config["params"], gas_units_per_action=0, priority_fee_gwei=0)
    _frame = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=16)})
    _constants = {
        "symbol": "TEST",
        "protocol": "v3",
        "signal_bp": 200,
        "price_valid": True,
        "reserve_hex": "0x" + format(1 << 56, "064x"),
        "price_usd": 1.0,
        "price_next": 1.0,
        "available_tokens": 1e9,
        "next_available_tokens": 1e9,
        "migration_exit_liquidity": 1e9,
        "supply_tokens": 1e9,
        "base_fee_gwei": 1.0,
        "next_base_fee_gwei": 1.0,
        "eth_usd": 1.0,
        "next_eth_usd": 1.0,
        "next_price_age_hours": 0.0,
        "usd_return": 0.001,
        "forward_interest": 0.001,
        "cash_return": 0.0001,
    }
    for _key, _value in _constants.items():
        _frame[_key] = _value
    _path = simulate(_frame, _params, 100, 5, 100000, mode="hold")
    assert np.isclose(_path.iloc[-1]["nav"], (1 - 0.0005) ** 2 * 1.001**16)
    assert _path["actions"].sum() == 2
    assert np.isclose(np.prod(1 + _path["return"]), _path.iloc[-1]["nav"])
    _migration = _frame.copy()
    _migration.loc[:7, "protocol"] = "v2"
    assert simulate(_migration, _params, 100, 5, 100000, mode="hold")["actions"].sum() == 4
    _changed = _frame.copy()
    _changed.loc[10:, "signal_bp"] = -1000
    _a = simulate(_frame, _params, 100, 5, 100000)
    _b = simulate(_changed, _params, 100, 5, 100000)
    assert _a.iloc[:10]["invested"].equals(_b.iloc[:10]["invested"])
    _ratio = index_ratio(pd.Series([str(10**27), str(10**27 + 10**24)]), 1)
    assert np.isclose(_ratio.iloc[1], 0.001)
    _weekly = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-03", periods=120, freq="W-FRI"),
            "spread": np.sin(np.arange(120) / 7),
            "symbol": "TEST",
        }
    )
    _future = _weekly.copy()
    _future.loc[80:, "spread"] += 100
    _f1, _ = sequential_forecast(_weekly, _params)
    _f2, _ = sequential_forecast(_future, _params)
    assert np.allclose(
        _f1.loc[_f1["date"] < _weekly.iloc[80]["date"], "ar1"],
        _f2.loc[_f2["date"] < _weekly.iloc[80]["date"], "ar1"],
    )
    validation = {
        "checks_passed": 7,
        "checks": [
            "two-sided fees",
            "terminal liquidation",
            "daily accounting reconciliation",
            "migration costs",
            "future signal perturbation",
            "ray precision",
            "forecast future perturbation",
        ],
    }
    (here / "outputs/validation.json").write_text(json.dumps(validation, indent=2))
    return (validation,)


@app.cell
def _(config, data):
    tables = data.load(config)
    if set(tables) != {"aave_reserve_daily", "usd_reference_rates"}:
        raise ValueError("Pin both validated datasets in config.yaml before running")
    return (tables,)


@app.cell
def _(config, here, json, mo, pipeline, tables):
    (
        _prepare_panel,
        _weekly_panel,
        _quality_evidence,
        _statistical_evidence,
        _carry_evidence,
        _uncertainty,
        _draw_figures,
    ) = pipeline
    params = config["params"]
    out = here / "outputs"
    detail = out / "tables"
    detail.mkdir(exist_ok=True, parents=True)
    panel, raw = _prepare_panel(tables, params)
    weekly = _weekly_panel(panel, params)
    quality = _quality_evidence(panel, raw, params)
    estimates, forecasts, forecast_summary, descriptions = _statistical_evidence(
        weekly, panel, params
    )
    scenarios, paths, annual = _carry_evidence(panel, params)
    intervals = _uncertainty(paths, params, config["seed"])
    baseline = scenarios[
        scenarios["hurdle_bp"].eq(params["baseline_hurdle_bp"])
        & scenarios["cost_bp"].eq(params["baseline_cost_bp"])
        & scenarios["notional_usd"].eq(params["baseline_notional_usd"])
    ].copy()
    for name, frame in {
        "daily_panel": panel,
        "weekly_panel": weekly,
        "ecm": estimates,
        "forecasts": forecasts,
        "scenarios": scenarios,
        "baseline_paths": paths,
        "annual_returns": annual,
        "uncertainty": intervals,
        "quality": quality,
    }.items():
        frame.to_csv(detail / f"{name}.csv", index=False)
    _draw_figures(panel, weekly, paths, here, params)
    metrics = {
        "status": "conditional research; no investment verdict",
        "quality": quality.to_dict("records"),
        "descriptive": descriptions.to_dict("records"),
        "ecm": estimates.to_dict("records"),
        "forecast": forecast_summary.to_dict("records"),
        "baseline": baseline.to_dict("records"),
        "uncertainty": intervals.to_dict("records"),
        "scenarios_evaluated": len(scenarios),
        "limitations": [
            "Independent reconstruction, not exact Aavescan replication",
            "No causal policy-shock or wallet-level replication",
            "Current-vintage SOFR with conservative publication timing",
            "Oracle marks are not executable prices; daily marks miss intraday losses",
            "SOFR investment access and trading costs are explicit scenarios",
            "No collateralized funded-arbitrage performance is claimed",
            "Scratch inputs require promotion before final freezing",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False))
    mo.vstack(
        [
            mo.md(
                "# DeFi / repo rate evidence\nConditional simulations, not an investment verdict."
            ),
            mo.ui.table(baseline),
            mo.ui.table(estimates),
            mo.ui.table(quality),
        ]
    )
    return baseline, estimates, forecast_summary, metrics, panel, paths, quality, scenarios, weekly


@app.cell
def _(config, here, json, np, paths):
    # Chronological partitions are descriptive: this entire history inspired the study.
    _rows, _stress = [], []
    for _symbol, _path in paths.groupby("symbol"):
        _split = _path["date"].lt(config["params"]["evaluation_split"])
        for _label, _part in [("before_split", _path[_split]), ("after_split", _path[~_split])]:
            _rows.append(
                {
                    "symbol": _symbol,
                    "period": _label,
                    "days": len(_part),
                    "net_return_pct": (np.prod(1 + _part["return"]) - 1) * 100,
                    "cash_return_pct": (np.prod(1 + _part["cash_return"]) - 1) * 100,
                    "days_above_capacity_diagnostic": int(
                        (_part["capacity_fraction"] > config["params"]["capacity_fraction"]).sum()
                    ),
                }
            )
        for _loss in config["params"]["permanent_loss_stress_pct"]:
            # One hypothetical unrecovered loss to terminal wealth; no probability assigned.
            _stress.append(
                {
                    "symbol": _symbol,
                    "loss_pct": _loss,
                    "terminal_excess_after_loss_pp": (
                        _path.iloc[-1]["nav"] * (1 - _loss / 100) - _path.iloc[-1]["benchmark"]
                    )
                    * 100,
                }
            )
    robustness = {
        "chronological_partitions": _rows,
        "terminal_wealth_haircuts": _stress,
        "interpretation": "Descriptive splits, not an untouched holdout. Haircuts are scenarios, not estimated loss probabilities or execution backtests.",
    }
    (here / "outputs/robustness.json").write_text(json.dumps(robustness, indent=2))
    return (robustness,)


if __name__ == "__main__":
    app.run()
