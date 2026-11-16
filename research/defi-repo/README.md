---
id: defi-repo
type: project
title: "DeFi deposit rates and off-chain funding"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [crypto, macro, signal, backtest]
related: [ADR-0010-defi-repo-research-sources, ADR-0011-pinned-scratch-experiment-inputs]
---

# DeFi deposit rates and off-chain funding

## Goal

Measure historical rate spreads, replication limits and conditional trading performance without making an investment decision for the user. Inspiration: [ECB WP3280](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3280~503ba7d4b0.en.pdf). Independent reconstruction is distinguished from exact replication; rate predictability is distinguished from executable profit.

## Hypotheses

- H1: stablecoin deposit-minus-SOFR spreads exhibit weekly mean reversion; estimate lagged-spread coefficients and AR(1) half-lives, with uncertainty and sample sensitivity.
- H2: rate dynamics are associated with utilization and crypto prices. These descriptive associations do not identify causal monetary-policy effects.
- H3: lagged spreads can improve sequential weekly forecasts relative to a no-change forecast. Evaluate every forecast, not selected examples.
- H4: an unlevered investor switching between the SOFR benchmark and each stablecoin's Aave deposits can earn incremental returns under explicit costs and mark assumptions. Test interest income and USD marking separately, including depeg exposure, operational constraints and capacity flags.
- H5: positive deposit spreads do not necessarily imply positive funded carry; compare actual variable-borrow index growth with the off-chain benchmark separately.

## Data

- [aave_reserve_daily](../../catalog/datasets/aave_reserve_daily.md): direct block-pinned Ethereum Aave v2/v3 state for DAI/USDC/USDT, normalized indices, quantities and Chainlink reference marks.
- [usd_reference_rates](../../catalog/datasets/usd_reference_rates.md): official New York Fed SOFR/EFFR, effective dates and revision indicators.
- Snapshot keys and digests are pinned in [the experiment config](experiments/2026-11-03-rate-spread-replication/config.yaml). No proprietary dataset copied to the server and no paid subscription purchased.

## Status

[Initial experiment](experiments/2026-11-03-rate-spread-replication/results.md) has completed acquisition, independent validation and analysis. Its evidence and follow-up ideas are in the [research log](../../knowledge/research-log/2026-11-03-rate-spread-replication.md). It remains draft pending durable retention and data-layer review. Investment verdict remains with the user. Knowledge-base findings are written after observing the outputs, not prefilled from the paper.
