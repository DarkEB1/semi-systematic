---
id: tags
type: context
title: "Tags: the controlled vocabulary"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra]
---

# Tags: the controlled vocabulary

Every `tags:` value in a knowledge file or dataset README must appear here, one line per tag with a
definition. `just check` fails on an unknown tag. To add a tag, append a line to the right family
in the same PR that first uses it; `just tags` prints the list. Keep tags few: a tag that would
apply to one file is a title, not a tag.

## Domain

- equities: single stocks and equity indices, cash or delta-one
- futures: listed futures and the curves behind them
- options: listed or OTC options and vol surfaces
- fx: spot, forwards and NDFs in G10 and EM currencies
- crypto: digital assets and their venues
- macro: rates, inflation, growth, policy and the cross-asset picture

## Stage

- idea: a hypothesis before any data has been touched
- data: data acquisition, cleaning, cataloguing and quality
- signal: a signal definition and its standalone statistics
- backtest: a signal run through costs, calendars and a portfolio rule
- portfolio: sizing, risk and combination across signals
- live-candidate: a strategy proposed for live capital

## Topic

- data-quality: gaps, revisions, survivorship, vendor errors
- infra: repo, devcontainer, bucket, CI, tooling, agents
- costs: transaction costs, slippage, funding, vendor fees
- risk: drawdown, exposure, correlation, tail events
- vendor: data vendors, licences and their quirks
