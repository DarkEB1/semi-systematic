---
id: data-access
type: context
title: "Data access: reading views, loading snapshots, writing to scratch"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [data, infra]
related: [start-here, walkthrough, conventions]
---

# Data access: reading views, loading snapshots, writing to scratch

Everything in the bucket is reached through `quant.data`. It reads `.env`, builds the DuckDB and
S3 clients, and enforces the prefix rules so a notebook cannot break them by accident. This page
is the examples; the signatures are in `src/quant/data/__init__.py` and the rules in
[AGENTS.md](../../AGENTS.md).

## The three prefixes

| prefix | written by | overwrite | layout |
|---|---|---|---|
| `raw/<source>/<dataset>/` | `ingest.yml` only (`QUANT_ROLE=ingest`) | a partition may be rewritten whole | daily `year=YYYY/month=MM/data.parquet`; intraday `date=YYYY-MM-DD/<asset_class>.parquet` |
| `curated/<name>/` | `promote.yml` only (`QUANT_ROLE=promote`) | never | `snapshot=YYYY-MM-DD/data.parquet` plus `README.md`, matching the Schema table in `catalog/datasets/<name>.md` |
| `scratch/<handle>/` | you, with your `<handle>-scratch` key | never (write-once) | anything; `just ingest` from a laptop mirrors to `scratch/<handle>/raw/...` with a `run=` stamp |

A laptop has the team-read key (reads everything) and a personal scratch key (writes one prefix).
Even with the right key, `write_once` checks the prefix against the role before touching S3.

## Read a view

```python
from quant import data

con = data.connect()  # DuckDB, httpfs loaded, every view in catalog/catalog.sql
con.sql("SELECT symbol, count(*) AS n FROM yahoo_prices_daily GROUP BY 1 ORDER BY 1").show()
con.sql("SELECT * FROM ref_universe").show()
```

View names: `<source>_<dataset>` for raw (`yahoo_prices_daily`), the plain name for curated
(`prices_daily`), `ref_<name>` for reference CSVs kept in git (`ref_universe`), and `repo_index`
for the retrieval index. A view whose files do not exist yet (for example `prices_daily` before
the first promotion) is skipped with a notice on stderr; pass `strict=True` to fail instead.

## Load what an experiment declares

```python
import yaml
from quant import data

config = yaml.safe_load(open("config.yaml"))
tables = data.load(config)  # {"prices_daily": pyarrow.Table}
prices = tables["prices_daily"].to_pandas()
```

`load` reads exactly `curated/<name>/snapshot=<snapshot>/` for each entry under `datasets:` in
`config.yaml`. A missing snapshot raises `FileNotFoundError` with the URL; there is no "latest".
That is what makes a frozen experiment reproducible a year later. Snapshot dates are the date of
promotion, not the last bar ([conventions](conventions.md)).

## Write to scratch

```python
import pyarrow as pa
from quant import data

table = pa.table({"date": [...], "symbol": [...], "signal": [...]})
key = data.write_once(table, "scratch/DarkEB1/em_carry_signal/data.parquet")
```

`write_once` refuses an existing key (`ExistsError`), refuses any key outside your prefix
(`PrefixError`), and accepts `overwrite=True` only under `raw/`, which you cannot write anyway.
Choose a new key per version (`.../v2/data.parquet` or a date) instead of overwriting. Read it back
with `data.read_parquet(key)`, list with `data.list_keys("scratch/DarkEB1/")`, or from the shell:

```text
$ just ls scratch/DarkEB1/
```

When the table is worth sharing, promote it: `just promote-request em_carry_signal scratch/DarkEB1/em_carry_signal/data.parquet`
validates it against the README's Schema table and writes the request ([walkthrough](walkthrough.md) step 5).

## The schema contract

```python
data.validate_schema(table, "prices_daily")  # raises SchemaMismatch naming the columns
data.schema_from_readme("prices_daily")  # the pyarrow schema parsed from the README
```

The Schema table in `catalog/datasets/<name>.md` has columns `column`, `type`, `unit`, `notes`;
types are `string`, `date`, `float64`, `int64`, `bool`, `timestamp`, `timestamp[us, UTC]`. Raw is
stored as received and not validated; curated must match exactly. Changing the contract of a
dataset others use is an ADR.

## Partitions and ingest

```python
data.partition_key("prices_daily", year=2026, month=10)
data.partition_parts("daily", day)
```

returns, in order:

```text
'prices_daily/year=2026/month=10/data.parquet'
{'year': 2026, 'month': 10}
```

Ingest modules in `src/quant/ingest/` use these through `_base.write_partitions`, which splits a
normalised table by partition and calls `write_once` per part. `just ingest yahoo --dry-run`
prints the keys it would write; `just ingest yahoo --since 2026-10-01` refetches from the first
of that month so partitions are rewritten whole (only CI may do that in `raw/`).

## Outside Python

DuckDB CLI and rclone are in the container and read the same `.env`:

```text
$ just ls raw/                                    # rclone, any prefix
$ duckdb -c "SELECT 1"                            # CLI; use the secret statement from quant.data.connect if you need S3
```

`just audit` lists keys outside the three prefixes or over 8 GB. Nothing in the bucket is ever
deleted by code; cleanup is a human with the dashboard.
