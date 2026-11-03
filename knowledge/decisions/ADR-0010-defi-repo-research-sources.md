---
id: ADR-0010-defi-repo-research-sources
type: decision
title: "ADR-0010: bound DeFi-repo research to public contract state and official rates"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [crypto, macro, data, vendor]
related: [vendors, universe]
---

# ADR-0010: bound DeFi-repo research to public contract state and official rates

## Context

The user requested an experiment inspired by [ECB WP3280](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3280~503ba7d4b0.en.pdf), with particular care over datasets retained on the research server. This authorizes a research-only extension of the preliminary universe to Ethereum Aave DAI, USDC and USDT, and USD reference rates. It does not authorize live trading or a vendor subscription.

## Decision

Acquire daily historical view-call results from Ethereum through the [Alchemy public RPC](https://www.alchemy.com/rpc/ethereum). Read only the selected Aave reserves, normalized interest indices, token balances, Chainlink reference marks and block metadata. No wallet-level activity or full blockchain replication. Preserve exact integer indices, protocol identity, block number/hash, cutoff bracket and acquisition time. Cross-check selected calls against a second public RPC. Provider access is subject to [Alchemy terms](https://legal.alchemy.com/), including internal business use and usage limits; this is public contract-state extraction, not a purchased proprietary analytics dataset.

Acquire SOFR and EFFR through the [New York Fed API](https://markets.newyorkfed.org/static/docs/markets-api.html), under its [terms](https://www.newyorkfed.org/privacy/termsofuse.html), with source attribution and required notices accompanying stored data and presentations. No subscription or new dependency. Store the bounded panel under `scratch/DarkEB1/` only after validation; promotion remains owner-reviewed. Estimate storage and record actual serialized bytes in the acquisition manifest.

The primary study uses 2021-01-04 through 2026-01-30, with boundary observations for realized index returns. Report individual coins; use the paper's fixed 2023-10-15 protocol splice for descriptive comparability and explicitly charge migration in simulations. Do not divide indices across different protocols. Preserve missing oracle values. Treat Chainlink marks as non-executable reference prices, with stale observations identified.

For reference-rate accrual only, a published overnight rate applies across its contractual non-business-day span (ACT/360); this is not interpolation of missing market bars. Signal eligibility uses the next observation's business date as the publication-day proxy, conservatively available only after that UTC date. Flag long gaps. Daily Aave accrual uses index ratios; annualized descriptive rates use ACT/365. Cost scenarios, access to benchmark funding, oracle execution and collateral economics must be explicit, not asserted as facts.

## Consequences

The rate/quantity panel supports independent descriptive replication and conditional carry simulations. It cannot reproduce the paper's proprietary source exactly or identify causal monetary-policy transmission without the separate shock series and estimation work. Oracle marks do not establish executable prices or intraday depeg drawdowns. The data-source PR touches CODEOWNERS paths and remains open for the data-layer owner. No paid source is procured and no raw/curated object is written by this session.

## Alternatives considered

- Aavescan: closest match to the paper, but full exports/API require paid access; no access assumed.
- DefiLlama: evaluated but not acquired because published terms restrict copying/mirroring and commercial reuse without permission.
- PublicNode and LlamaRPC: test requests failed; do not rely on them.
- Wallet-level event histories: unnecessary bulk and scope for the initial rate experiment.
- Substituting headline APY for earned index returns: changes the measured quantity; do not use as an undisclosed substitute.
