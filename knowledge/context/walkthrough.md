---
id: walkthrough
type: context
title: "Walkthrough: one experiment end to end, with real output"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra, fx, idea]
related: [start-here, workflow, data-access, working-with-agents]
---

# Walkthrough: one experiment end to end, with real output

[workflow](workflow.md) tells the story; this page runs it. Every block below was produced by
the command above it inside the devcontainer on 2026-10-29 (long outputs are cut, nothing is
retyped). Follow it once with your own slug and you have touched every part of the repo.

## 0. Where am I

```text
$ just onboard
[OK     ] tool uv
[OK     ] tool just
...
[OK     ] rclone can list the bucket
[OK     ] duckdb httpfs secret works (2 object(s) visible)

onboard: 23 ok, 0 missing
Next: read AGENTS.md and knowledge/context/workflow.md, then run `just check` and `just test`.
```

A `MISSING` line names the `.env` variable or tool to fix. `just` alone lists the 26 recipes with
a one-line description each.

## 1. Search before anything

```text
$ just search "R2"
knowledge/decisions/ADR-0001-initial-setup.md › Decision  [decision, 2026-10-29]
    …Bucket `semi-sys-research-data`, Cloudflare R2, **EU jurisdiction** …
knowledge/meetings/2026-10-28-kickoff.md › Actions  [meeting, 2026-10-28]
    - [ ] Add the scratch/ lifecycle rule in the R2 dashboard (@DarkEB1, 2026-11-30) …
.claude/skills/build-index/SKILL.md › Checks before opening the PR  [skill]
```

Each hit is `path › heading [type, date]` and a snippet, newest first. The match is literal
(`ILIKE`), so try two or three phrasings. Nothing found is an answer too: it means no file records
it yet, and `just where "<thing>"` says where such a file would live.

## 2. Create the experiment

```text
$ just experiment carry-reversion \
    --hypothesis "EM currencies with the steepest carry mean-revert after a dollar shock" \
    --dataset prices_daily:2026-10-29
research/experiments/2026-10-29-carry-reversion/config.yaml
research/experiments/2026-10-29-carry-reversion/run.py
research/experiments/2026-10-29-carry-reversion/results.md
research/experiments/2026-10-29-carry-reversion/figures/.gitkeep
```

`config.yaml` is the whole contract of the experiment. Edit `params` and `seed`; never the folder name.

```yaml
slug: carry-reversion
date: '2026-10-29'
owner: DarkEB1
hypothesis: EM currencies with the steepest carry mean-revert after a dollar shock
datasets:
- name: prices_daily
  snapshot: '2026-10-29'
params:
  cost_bp: 5
  lookback_days: 20
seed: 0
```

`run.py` is a marimo notebook with three cells: load `config.yaml`, `tables = quant.data.load(config)`,
write `outputs/metrics.json`. Add your cells between the second and the third. The rule the
notebook must keep: data comes only through `load(config)`, and every number you will ever quote
is written to `outputs/`.

## 3. Run it

```text
$ uv run research/experiments/2026-10-29-carry-reversion/run.py            # headless
$ uv run marimo edit research/experiments/2026-10-29-carry-reversion/run.py   # interactive
```

`load` reads `curated/prices_daily/snapshot=2026-10-29/`. If that snapshot does not exist the
call raises `FileNotFoundError` naming the URL; it never falls back to "latest". Until the first
promotion exists you may read the raw view `yahoo_prices_daily` through `quant.data.connect()`
instead, and say so in the research-log entry (the demo experiment does exactly this).

## 4. Finish

```text
$ just experiment carry-reversion --finish
research/experiments/2026-10-29-carry-reversion/results.md
knowledge/research-log/2026-10-29-carry-reversion.md
```

With an empty `outputs/` the Result section says so instead of inventing a number:

```markdown
## Result

No files under outputs/. Run the notebook first; --finish quotes outputs only.
```

With `outputs/metrics.json` present it pastes the JSON under `From outputs/metrics.json:`. The
research-log entry is drafted with Hypothesis, Data (`prices_daily at snapshot 2026-10-29`),
Method (params and seed from `config.yaml`, link to the notebook), Result, and a Verdict left as
`TODO: keep / park / kill`. The Verdict is the one thing only you can write.

`--finish` also runs the duplicate check. A line such as
`duplicate: run.py:zscore == 2026-10-29-demo/run.py:zscore; second use -> move to a tool (tools/<name>, `just new-tool`) with a test, in its own PR`
means the reuse rule applies before this PR.

Set `status: final` in `results.md` when nothing will change. From then on `just check` fails any
diff that touches the folder; a follow-up is a new experiment with `parent: carry-reversion`.

## 5. Promote a dataset the experiment produced

Write the table to your scratch prefix from the notebook (see [data-access](data-access.md)), then:

```text
$ just promote-request em_carry_signal scratch/DarkEB1/em_carry_signal/data.parquet --write-readme
--- schema ok: 2 rows, 9 columns
PR checklist (paste into the PR body):

- [ ] `promote/requests/2026-10-29-em_carry_signal.yml` requests `em_carry_signal` at snapshot `2026-10-29`
- [ ] the Parquet matched `catalog/datasets/em_carry_signal.md` (schema contract) locally
- [ ] the README's Source, Cadence, Known gaps and Owner are filled, not TODO
- [ ] `just check` and `just test` are green
- [ ] no existing snapshot with the same date (promote never overwrites)
- [ ] `promote/**` and `catalog/**` are under CODEOWNERS: this PR waits for the data-layer owner
```

The request file is six lines of YAML (`name`, `scratch_key`, `snapshot`, `requested_by`, `date`,
`notes`). On merge, `promote.yml` copies the Parquet to `curated/em_carry_signal/snapshot=2026-10-29/`
with the README next to it. A schema mismatch exits 1 and prints the differing columns.

## 6. The PR

```text
$ git checkout -b research/carry-reversion
$ git add -A && git commit -m "research: carry reversion experiment and log entry"
$ git push -u origin HEAD
$ gh pr create --fill
```

The pre-commit hook runs the same checks as `just check`. CI runs `just check`, `just test` and
`just eval`; the required status is `ci`. Review is trust-based: squash-merge when green, unless a
changed path is under the data-layer CODEOWNERS block, in which case the data-layer owner merges.
After the merge `index.yml` rebuilds the index, so `just search "carry reversion"` finds this week.

## 7. Data health and refresh

```text
$ just data-health
dataset              source   status   latest     expected   behind  owner
--------------------------------------------------------------------------
prices_daily         yahoo    missing  -          2026-10-28      -  DarkEB1
1 dataset(s) not ok
```

`missing` here is expected until the first nightly `ingest.yml` run fills `raw/`. For a stale
dataset `just refresh` prints the exact command that fills the gap, and `just refresh --execute`
runs it (on a laptop the result lands in `scratch/<you>/raw/...`; only CI writes `raw/`):

```text
refresh: prices_daily is stale -> just ingest yahoo --since 2026-10-01
```

## 8. A meeting

Bullets in, files out. The grammar is `agenda:`, `decision:`, `action: ... @handle YYYY-MM-DD`;
anything else is a note.

```text
$ just meeting 2026-11-03 "weekly sync" --attendees DarkEB1 --recording <url> < bullets.txt
knowledge/meetings/2026-11-03-weekly-sync.md
knowledge/decisions/ADR-0002-switch-prices-daily-source-from-yahoo-to.md
```

The Decisions section the skill wrote:

```markdown
## Decisions

- switch prices_daily source from yahoo to fred if yahoo breaks again ([ADR-0002](../decisions/ADR-0002-switch-prices-daily-source-from-yahoo-to.md))
- weekly sync moves to Tuesdays (minor)
```

The first decision passed the ADR test (it changes a data source), so an ADR draft with
`status: proposed` and TODO Context, Consequences and Alternatives was created; you fill it and set
`status: accepted`. The second did not, so it is a minutes line marked `(minor)`. `just check`
fails a Decisions line that is neither. The transcript itself is never stored.

## 9. Hand a piece to an agent

```text
$ just task sweep-lookbacks --skill new-experiment \
    --goal "find the lookback at which carry reversion stops improving" \
    --metric "sharpe after 5 bp costs from outputs/metrics.json"
ai/tasks/sweep-lookbacks.yaml
$ just loop sweep-lookbacks
loop sweep-lookbacks: 2 iteration(s); budget: max_iterations reached
agent-log: knowledge/agent-log/2026-10-29-loop-sweep-lookbacks.md
```

What the task file and the agent-log look like, and how to run a model-driven loop instead of the
deterministic one, is in [working-with-agents](working-with-agents.md).
