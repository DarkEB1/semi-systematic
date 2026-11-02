---
id: universe
type: context
title: "Universe: what we look at"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [fx, macro]
related: [strategy, conventions]
---

# Universe: what we look at

TODO: decide the EM rates and credit instruments to add once a data source for them exists.

## FX

The machine-readable list is `catalog/reference/universe.csv` (exposed as the `ref_universe`
view): three G10 pairs for reference and twelve USD-based EM pairs across LatAm, CEEMEA and Asia.
Symbols follow market convention (`USDBRL`, `EURUSD`), never the vendor ticker; the vendor
ticker lives in its own column.

## Not yet

- EM local rates and sovereign credit: no free daily source identified.
- Equities, futures, options, crypto: out of scope until the FX and macro views are built.

## Changing the universe

Edit the CSV in a PR. Adding an instrument class is an ADR; adding a pair to an existing class is
a minutes line marked (minor).
