---
name: pull-data
description: Add a new data source end to end - scaffold the ingest module from the template, the dataset README with its Schema table, the catalog view, a test with a small fixture, the registry entry and the nightly workflow entry - then fill in fetch and normalise and open the PR.
---

# pull-data

Deterministic part: `.claude/skills/pull-data/pull_data.py`, exposed as `just scaffold-source SOURCE`.
It writes the scaffold from `template_source.py` in this folder; you write `fetch`/`normalise`,
the Schema table and the licence line. Eval fixture: `ai/evals/pull-data/`.

## Inputs

- `SOURCE`: lowercase identifier (`fred`, `ecb`), `--dataset NAME` (default `<source>_daily`),
  `--cadence daily|intraday|snapshot`, `--description "..."`.
- The vendor URL, its licence terms, and whether it needs a key (`VENDOR_API_KEY` or a new
  variable added to `.env.example` in the same PR).

## Steps

1. `just search "<vendor> <dataset>"` for prior decisions: a source may have been rejected
   (see `knowledge/context/vendors.md`) or may already exist under another name.
2. `just scaffold-source <source> --dataset <name> --cadence <c> --description "..."`.
   It creates `src/quant/ingest/<source>.py`, `catalog/datasets/<name>.md`, the `<source>_<name>`
   view in `catalog/catalog.sql`, `tests/test_ingest_<source>.py` + `tests/fixtures/<source>_sample.json`,
   registers the module in `src/quant/ingest/__init__.py` and adds it to the `ingest.yml` matrix.
3. Implement `fetch` (raise on any error, never return partial data) and `normalise` (typed
   columns, one row per observation). Replace the fixture with a real, small vendor sample and
   adjust the test. Keep the module importing only the base dependency group.
4. Fill the README: Source lines (`source`, `url`, `licence`), Cadence (`cadence`, `lag_days`),
   the Schema table (this becomes the contract if the dataset is ever promoted), Known gaps, Owner.
   Tags from `just tags`; add a vendor tag line to `tags.md` only if a new family is really needed.
5. `just test`, then `just ingest <source> --dry-run`, then `just ingest <source>` which writes to
   `scratch/<handle>/raw/<source>/...` from a laptop. Check the output with `just ls scratch/<handle>/`.
6. If the source costs money or replaces an existing one, draft an ADR (template
   `knowledge/templates/decision.md`) and update `knowledge/context/vendors.md`.
7. Write the agent-log entry linking every file touched and relied on; open the PR.

## Checks before opening the PR

- `just check`, `just test` and `just eval` pass.
- `python -m quant.ingest --list` shows the source; `just data-health` shows the dataset as
  `missing` (raw/ is filled only by the nightly job after merge).
- `.env.example` lists any new variable the module reads (the env audit in `just check` enforces it).
- No key or sample containing a key is in the diff (`gitleaks` runs in `just check`).

## Done when

- The PR is merged (by the skill only if nothing under CODEOWNERS changed; `catalog/**` is under
  CODEOWNERS, so a new dataset README always waits for the data-layer owner).
- The next nightly `ingest.yml` run is green and `just data-health` shows the dataset `ok`.
