"""Render observed output tables into reviewable evidence, without an investment verdict."""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def table(rows, columns):
    def cell(value):
        if value is None:
            return "n/a"
        return f"{value:.4f}" if isinstance(value, float) else str(value)

    return "\n".join(
        [
            "| " + " | ".join(label for _, label in columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
            *("| " + " | ".join(cell(row[key]) for key, _ in columns) + " |" for row in rows),
        ]
    )


def main():
    metrics = json.loads((OUT / "metrics.json").read_text())
    manifest = json.loads((HERE / "acquisition-manifest.json").read_text())
    robust = json.loads((OUT / "robustness.json").read_text())
    scenarios = list(csv.DictReader((OUT / "tables/scenarios.csv").open()))
    for row in scenarios:
        for key in row:
            if key not in {"symbol", "mode"} and row[key]:
                row[key] = float(row[key])
    reference = {
        "DAI": (-0.106, 5.0, 259, 5),
        "USDC": (-0.133, 4.0, 259, 5),
        "USDT": (-0.186, 2.2, 260, 4),
    }
    comparison = []
    for row in metrics["ecm"]:
        if row["sample"] == "full":
            beta, half, n, lags = reference[row["symbol"]]
            comparison.append(
                dict(row, paper_beta=beta, paper_half=half, paper_n=n, paper_lags=lags)
            )
    evidence = {
        "paper_table_1": [
            {
                "symbol": key,
                "level_beta": val[0],
                "half_life_weeks": val[1],
                "n": val[2],
                "lags": val[3],
            }
            for key, val in reference.items()
        ],
        "paper_source": "https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3280~503ba7d4b0.en.pdf",
        "comparison": comparison,
    }
    (OUT / "paper-comparison.json").write_text(json.dumps(evidence, indent=2))
    blocks = [
        "### Scope and data integrity\n\nIndependent reconstruction of deposit/supply rates, not an exact replication of the paper's Aavescan series. The sample and protocol splice follow the paper; the observations come from public Ethereum archive calls and the official New York Fed API. No paid analytics data, wallet histories or full blocks were retained on the server.",
        table(
            manifest["datasets"],
            [("name", "Dataset"), ("rows", "Rows"), ("bytes", "Parquet bytes")],
        ),
        f"Total Parquet storage: {manifest['total_bytes']:,} bytes, plus small README/provenance objects. Independent RPC checks cover {len(manifest['checks'])} dates, including the protocol splice, depeg and stable-debt deprecation. Both providers agree on block hashes, reserves, exact indices, balances and oracle returns. Every date has a validated midnight block bracket. Inputs are SHA-256 pinned in config.yaml; scratch retention remains unresolved until owner-reviewed promotion.",
        table(
            metrics["quality"],
            [
                ("symbol", "Coin"),
                ("rows", "Days"),
                ("missing_price_days", "Missing marks"),
                ("stale_price_days", "Marks >48h"),
                ("max_cutoff_gap_seconds", "Max cutoff gap (s)"),
                ("min_oracle_price", "Min daily USD mark"),
            ],
        ),
        "Missing early oracle marks remain missing. Trading starts later than the descriptive sample. Daily midnight oracle prices neither establish executable prices nor capture intraday depeg extremes. Current-vintage reference-rate revisions are retained; a historical first-release vintage is unavailable.",
        "### Mechanisms and testable hypotheses\n\nThe paper describes segmented capital, overcollateralization and operational costs that can impede equalization of on-chain and off-chain rates. Aave rates also respond mechanically to reserve utilization. Off-chain yields can change depositors' opportunity cost while crypto demand changes borrowing demand. These are competing mechanisms, not an established causal explanation for this reconstructed sample. H1 tests spread reversal; H2 measures utilization/BTC associations; H3 tests sequential forecasting; H4 evaluates conditional unlevered carry; H5 reports borrowing-cost comparisons. Monetary-shock VARs, wallet-level differences-in-differences and intraday event studies are outside this reconstruction.",
        table(
            metrics["descriptive"],
            [
                ("symbol", "Coin"),
                ("mean_spread_bp", "Mean spread (bp)"),
                ("below_sofr_pct", "Below SOFR (%)"),
                ("weekly_delta_rate_btc_corr", "Rate-change/BTC corr."),
                ("weekly_delta_rate_utilization_corr", "Rate/utilization-change corr."),
                ("variable_borrow_below_sofr_pct", "Variable borrow below SOFR (%)"),
            ],
        ),
        "Borrow comparisons use variable-debt index growth. They are not funded-arbitrage returns: collateral capital, haircuts, liquidation, funding access and all implementation costs would still need to be modeled.",
        "### Paper comparison and sample sensitivity\n\nRealized daily deposit APR comes from normalized income-index ratios within each protocol. Business-day observations are averaged into complete Friday-ending weeks. The ECM regresses weekly spread changes on the previous spread, contemporaneous BTC log change and lagged spread changes; BIC selects from zero through eight lags on a common sample, then the selected model is refit with HAC bandwidth four. These choices are explicit reconstruction conventions: the paper does not specify the exact candidate range and HAC bandwidth. AR(1) half-lives are separate estimates, not transformations of the ECM coefficient.",
        table(
            comparison,
            [
                ("symbol", "Coin"),
                ("paper_beta", "Paper beta"),
                ("level_beta", "Reconstructed beta"),
                ("level_se", "HAC SE"),
                ("paper_half", "Paper half-life (weeks)"),
                ("half_life_weeks", "Reconstructed half-life"),
                ("paper_n", "Paper n"),
                ("n", "Reconstructed n"),
                ("lags", "Chosen lags"),
            ],
        ),
        table(
            [r for r in metrics["ecm"] if r["sample"] == "exclude_2021"],
            [
                ("symbol", "Excluding 2021"),
                ("level_beta", "Beta"),
                ("level_ci_low", "95% CI low"),
                ("level_ci_high", "95% CI high"),
                ("half_life_weeks", "Half-life (weeks)"),
            ],
        ),
        table(
            [r for r in metrics["ecm"] if r["sample"] == "full"],
            [
                ("symbol", "Full sample"),
                ("level_p", "ECM level HAC p"),
                ("adf_p", "Spread ADF p"),
                ("engle_granger_p", "Engle-Granger p"),
            ],
        ),
        "The ADF null is a unit root; the Engle-Granger null is no cointegration. These tests answer different questions from the conditional ECM coefficient and are shown without treating one test as a substitute for another. UTC sampling, vendor construction and lag choices can contribute to replication differences; their separate effects have not been identified.",
        "### Sequential forecast evidence\n\nExpanding-window AR(1) forecasts use only earlier weekly observations and are compared with no change. The first training window contains 52 weeks. Positive MSE skill means lower squared error than the benchmark. This is pseudo-out-of-sample evaluation: the paper and historical period were already known when the experiment was designed. No multiple-testing correction or untouched holdout is claimed.",
        table(
            metrics["forecast"],
            [
                ("symbol", "Coin"),
                ("n", "Forecasts"),
                ("rmse_ar1_pp", "AR1 RMSE (pp)"),
                ("rmse_no_change_pp", "No-change RMSE (pp)"),
                ("mse_skill", "MSE skill"),
                ("loss_difference_hac_p", "Loss-difference HAC p"),
            ],
        ),
        "### Conditional trading performance\n\nThe baseline starts 2022-01-03 and ends 2026-01-30, rebalances Mondays using the previous day's headline deposit-minus-known-SOFR spread, and enters above 100 bp. Capital is $100,000 per coin. Each action costs 5 bp plus 300,000 gas at historical base fee plus 2 gwei; entry, exit and protocol migration are charged. Holdings earn exact index growth, marked with the next daily oracle observation. Idle capital earns SOFR on ACT/360; on-chain APR descriptions use ACT/365. SOFR signals become available conservatively after the following publication-day proxy. Reserve flags, supply caps and daily withdrawal liquidity are checked; these do not prove a transaction would fill.",
        table(
            metrics["baseline"],
            [
                ("symbol", "Coin"),
                ("net_return_pct", "Net total (%)"),
                ("cash_return_pct", "SOFR total (%)"),
                ("excess_terminal_pp", "Excess wealth (pp)"),
                ("net_cagr_pct", "Net CAGR (%)"),
                ("max_drawdown_pct", "Daily max DD (%)"),
                ("actions", "Actions"),
                ("invested_pct", "Invested (%)"),
            ],
        ),
        "SOFR access, conversion at oracle marks, gas units and non-gas costs are scenario assumptions. There are no transaction-level execution quotes, collateralized financing returns or estimated smart-contract/default loss probabilities. Daily checks omit intraday liquidity changes and v2 global-pause status. The strategy is a separate carry rule; it does not trade the estimated ECM coefficient.",
        table(
            metrics["baseline"],
            [
                ("symbol", "Coin"),
                ("interest_only_return_pct", "Constant-peg total return (%)"),
                ("net_return_pct", "USD-marked total return (%)"),
                ("max_supply_share_pct", "Max share of supplied tokens (%)"),
            ],
        ),
        "Constant-peg returns retain costs but set conversion marks to par; this is an attribution scenario, not a dollar-return observation. The paper's fixed protocol migration is used for comparability, not claimed as a decision specified prospectively in that historical period.",
        "### Cost and scale sensitivity\n\nThe table keeps the same 100 bp hurdle and varies capital and per-action non-gas costs. All configured hurdle/cost/size combinations are retained in outputs/tables/scenarios.csv; none is selected as an optimal strategy.",
        table(
            [r for r in scenarios if r["mode"] == "switch" and r["hurdle_bp"] == 100],
            [
                ("symbol", "Coin"),
                ("notional_usd", "Capital ($)"),
                ("cost_bp", "Cost/action (bp)"),
                ("excess_terminal_pp", "Excess wealth (pp)"),
            ],
        ),
        "### Benchmarks, uncertainty and stress\n\nFrictionless uses the same switching rule with zero gas and zero non-gas costs. Hold uses continuous deposit exposure subject to observed entry constraints and the baseline costs.",
        table(
            [r for r in scenarios if r["mode"] != "switch"],
            [
                ("symbol", "Coin"),
                ("mode", "Scenario"),
                ("net_return_pct", "Total return (%)"),
                ("excess_terminal_pp", "Excess wealth (pp)"),
            ],
        ),
        table(
            metrics["uncertainty"],
            [
                ("symbol", "Coin"),
                ("annual_mean_excess_pct", "Annual mean daily excess (%)"),
                ("block_bootstrap_ci_low", "Block-bootstrap CI low"),
                ("block_bootstrap_ci_high", "CI high"),
            ],
        ),
        "Bootstrap intervals resample 28-day blocks with 1,000 draws and seed 3280; they do not capture unobserved disasters or model-selection uncertainty. Historical chronological splits are descriptive, not independent validation.",
        table(
            robust["chronological_partitions"],
            [
                ("symbol", "Coin"),
                ("period", "Period"),
                ("net_return_pct", "Net (%)"),
                ("cash_return_pct", "SOFR (%)"),
                ("days_above_capacity_diagnostic", "Days >1% supply"),
            ],
        ),
        table(
            robust["terminal_wealth_haircuts"],
            [
                ("symbol", "Coin"),
                ("loss_pct", "Hypothetical terminal loss (%)"),
                ("terminal_excess_after_loss_pp", "Remaining excess (pp)"),
            ],
        ),
        "Terminal haircuts are arithmetic stress scenarios with no assigned probability. They are not event-timed loss simulations.",
        "### Reproduction and further experiments\n\nRun acquire.py, validate_acquisition.py and publish_inputs.py in order for a new acquisition; published objects are write-once. With the pinned snapshot available, run `uv run --extra ml python research/defi-repo/experiments/2026-11-03-rate-spread-replication/run.py`, then report.py. The notebook writes full daily, weekly, forecast, scenario and accounting tables plus figures. Synthetic invariants check two-sided costs, terminal liquidation, migration costs, accounting reconciliation, index precision and future-data perturbation.\n\nNext experiments could replace oracle marks with independently licensed executable conversion data; model actual borrowing access and collateral economics; obtain the paper's exact daily vendor series and estimation code for residual reconciliation; replicate its policy-shock design; and preregister a forward evaluation. These are research proposals, not investment recommendations. No keep/park/kill decision is assigned.",
        "### Attribution\n\nSource: ECB WP3280 (paper Table 1); public Ethereum Aave/Chainlink contract state via Alchemy, checked against dRPC; New York Fed SOFR/EFFR API. The SOFR and EFFR data are subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not responsible for publication of these data by semi-systematic, does not endorse this republication, and has no liability for your use. semi-systematic is not affiliated with the New York Fed. The New York Fed does not sanction, endorse, or recommend any products or services offered by semi-systematic.",
    ]
    text = "\n\n".join(blocks) + "\n"
    assert len(text.encode()) < 20_000
    (OUT / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
