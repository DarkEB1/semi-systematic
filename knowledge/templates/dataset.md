---
id: <dataset_name>
type: dataset
title: <dataset_name>
date: YYYY-MM-DD
authors: [<handle>]
owner: <handle>
status: active
tags: []
datasets: [<dataset_name>]
---

# <dataset_name>

<!-- Lives in catalog/datasets/<name>.md. The Schema table IS the contract for curated/<name>/:
promote refuses a Parquet whose columns or types differ. Raw is stored as received. -->

<one paragraph: what it is, raw and curated prefixes, view names>

## Source

- source: <source module name, e.g. yahoo>
- url: <where it comes from>
- licence: <terms in one line>

<how it is fetched; what the ingest rewrites>

## Cadence

- cadence: daily | intraday | snapshot
- lag_days: <days after which a missing partition counts as stale>

<calendar notes>

## Schema

| column | type | units | description |
|---|---|---|---|
| date | date | calendar day (UTC) | |
| <col> | string / float64 / int64 / bool / timestamp[us, UTC] | <units> | <meaning> |

## Known gaps

- <gap>

## Owner

<handle>. <where to report problems>
