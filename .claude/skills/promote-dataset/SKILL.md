---
name: promote-dataset
description: Move a dataset from scratch/ to curated/ under the schema contract - validate the Parquet against the dataset README (write the README if missing), create the promote request file, and open the PR with a checklist; promote.yml does the copy on merge.
---

# promote-dataset

Deterministic part: `.claude/skills/promote-dataset/promote_dataset.py`, exposed as
`just promote-request NAME SCRATCH_KEY`. It validates and writes the request; the copy to
`curated/<name>/snapshot=<date>/` happens in `promote.yml` with `QUANT_ROLE=promote` after the
merge. Eval fixture: `ai/evals/promote-dataset/`.

## Inputs

- `NAME` (the dataset, which is also the curated view name) and the `scratch/<handle>/.../*.parquet`
  key holding the file to promote (`just ls scratch/<handle>/` to find it).
- Optional `--snapshot YYYY-MM-DD` (default today), `--notes "..."`.

## Steps

1. `just search "<name>"`: an earlier snapshot, an ADR about the dataset, or a README may exist.
2. `just promote-request <name> <scratch_key>`. If `catalog/datasets/<name>.md` is missing, rerun
   with `--write-readme`: the Schema table is generated from the Parquet and everything else is
   TODO. Fill Source, Cadence, Known gaps and Owner before going on; the README is the contract.
3. On a schema mismatch the command exits 1 and prints the differing columns or types. Fix the
   data (preferred) or, if the contract was wrong, change the README and say why in the PR; a
   contract change on a dataset others use is an ADR.
4. The command writes `promote/requests/<date>-<name>.yml` and prints a checklist. Put the
   checklist in the PR body.
5. Write the agent-log entry linking the request, the README and the scratch key; open the PR.

## Checks before opening the PR

- `just check` and `just test` pass.
- The request's `scratch_key` exists (`just ls <prefix>`) and the owner has read it back once.
- No `curated/<name>/snapshot=<date>/` exists yet (`just ls curated/<name>/`); promote never overwrites.
- README tags are in `tags.md`; owner is in `team.yaml`.

## Done when

- The PR is merged by the data-layer owner (`promote/**` and `catalog/**` are under CODEOWNERS,
  so this skill never merges its own PR) and the `promote.yml` run is green.
- `just search "<name>"` returns the README and `prices_daily`-style queries work through
  the curated view in `catalog/catalog.sql` (add the view in the same PR if the dataset is new).
