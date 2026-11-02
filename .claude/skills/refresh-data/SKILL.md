---
name: refresh-data
description: Find raw datasets whose latest partition lags the cadence their README promises, re-ingest the gap with just ingest --since, summarise what was fixed, and open an issue for anything that cannot be recovered.
---

# refresh-data

Deterministic part: `.claude/skills/refresh-data/refresh_data.py`, exposed as `just refresh`. Without
flags it prints the plan; `--execute` runs it. `data-health.yml` already opens one issue per
stale dataset nightly; this skill is what closes them. Eval fixture: `ai/evals/refresh-data/`.

## Inputs

- Nothing required. Optional: `--today YYYY-MM-DD`, a specific dataset's data-health issue.
- Needs write keys for the prefix the role may write: on a laptop the result lands in
  `scratch/<handle>/raw/...` (a laptop can never fill `raw/`); in CI (`QUANT_ROLE=ingest`) it
  rewrites the `raw/` partitions in place.

## Steps

1. `just search "<dataset> gap"` and read the dataset README's Known gaps: some gaps are vendor
   holidays, not failures, and must not be "fixed".
2. `just refresh` prints each dataset's status (`ok`, `stale`, `missing`), the expected date and
   the `just ingest <source> --since <date>` command that would fill the gap.
3. `just refresh --execute` runs those commands. Each ingest re-fetches from the first day of the
   affected month so partitions are rewritten whole.
4. `just data-health` again; every dataset you touched should be `ok`.
5. For an ingest that fails (vendor down, symbol delisted, schema changed): do not retry in a
   loop. `just refresh --execute --issue` opens one issue per failure, labelled `data-health`;
   add what you learned to the README's Known gaps in the same PR if it is a permanent change.
6. Write the agent-log entry (which datasets, which commands, which issues) and, if a README or
   fixture changed, open the PR. If nothing changed in the repo, the agent-log entry alone is the PR.

## Checks before opening the PR

- `just check` and `just test` pass.
- `just data-health` shows `ok` for every dataset that was refreshed, or an issue links the failure.
- Nothing was written outside `raw/` (CI) or `scratch/<handle>/` (laptop); `just audit` is clean.

## Done when

- Stale datasets are `ok`, unrecoverable ones have an open issue with the exact failing command,
  and the agent-log entry links the datasets' READMEs and the issues.
