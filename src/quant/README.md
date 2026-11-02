# quant

The data layer and its plumbing. Everything that touches the bucket goes through here, so the
prefix rules and the schema contract live in one place and are tested once.

| module | what | entry point |
|---|---|---|
| `quant.data` | settings from `.env`, the write policy (`raw/` ingest only, `curated/` promote only, `scratch/<handle>/` for everyone), `write_once`, DuckDB `connect()` with the catalog views, `load(config)` for experiments, schema validation against dataset READMEs | imported by notebooks and scripts; see [knowledge/context/data-access.md](../../knowledge/context/data-access.md) |
| `quant.ingest` | registry of sources (`SOURCES`), one module per source with `fetch`, `normalise`, `run`; partitions by cadence | `just ingest SOURCE [--since D] [--dry-run]`, `python -m quant.ingest --list` |
| `quant.promote` | executes a `promote/requests/*.yml`: validates, copies to `curated/<name>/snapshot=<d>/`, writes the README next to it | `just promote REQUEST` (CI, `QUANT_ROLE=promote`) |
| `quant.datahealth` | latest partition versus the cadence promised in each dataset README; opens or updates one issue per stale dataset | `just data-health`, the hub's data-health page, `data-health.yml` |
| `quant.audit` | lists the bucket and flags keys outside the three prefixes or over the size cap | `just audit`, `audit.yml` |
| `quant.datasets` | parses the Source and Cadence sections of dataset READMEs | used by health and refresh |

Rules that the code enforces rather than documents: `write_once` refuses an existing key and
refuses `overwrite=True` outside `raw/`; a role may write only its prefix; `load` never falls
back to the latest snapshot; `validate_schema` compares column names and types with the Schema
table in `catalog/datasets/<name>.md`.

Adding a source is the pull-data skill (`just scaffold-source SOURCE`), which writes the module
from `.claude/skills/pull-data/template_source.py` together with its README, view, test and
workflow entry. This package depends only on the base dependency group; the optional `ml` extra
is banned here by ruff.
