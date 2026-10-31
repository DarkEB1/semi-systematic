---
id: conventions
type: context
title: "Conventions: returns, costs, calendars, currencies"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [fx, costs, risk]
related: [universe, strategy]
---

# Conventions: returns, costs, calendars, currencies

TODO: confirm each convention against the first backtest and record changes as ADRs.

## Returns

- Simple daily returns from close to close in the quote currency; log returns only inside models.
- Dates are the bar date in UTC as stored; no forward-filling across missing days.
- FX pairs are quoted as units of quote per one unit of base (`USDBRL` = BRL per USD). A long
  `USDBRL` position profits when the number goes up.

## Costs

- Until a cost model exists, assume a flat half-spread per trade: 1 bp for G10, 5 bp for liquid
  EM, 15 bp for the rest. Record the assumption in each experiment's `config.yaml` under `params`.
- Funding and carry are not in `prices_daily`; a strategy that needs them must say so in its
  research-log entry.

## Calendars

- A missing day in a daily dataset is a holiday or a vendor gap, not a zero return. Data-health
  counts business days (Mon to Fri) only; per-currency holiday calendars are a TODO.
- Snapshot dates for curated data are the date of promotion, not the last bar.

## Currencies

- Everything is reported in USD unless a file says otherwise.
- The universe symbol never changes; if a vendor renames a ticker, only the vendor column moves.
