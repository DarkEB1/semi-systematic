---
name: new-experiment
description: Create a reproducible experiment folder (config.yaml, marimo run.py, results.md, figures/), flag code duplicated from other experiments, and at the end draft results.md and the research-log entry from config.yaml and run outputs without inventing numbers.
---

# new-experiment

Deterministic part: `.claude/skills/new-experiment/new_experiment.py`, exposed as `just experiment SLUG [...]`.
Call it for the scaffold and for `--finish`; you supply the hypothesis, the datasets and the
judgement in the Verdict. The eval fixture is `ai/evals/new-experiment/`.

## Inputs

- `SLUG` (short-kebab-case), the project it belongs to (`--project`, a folder under `research/`;
  `just project <p>` creates one), the owner's handle (defaults to `R2_HANDLE`), a one-line hypothesis.
- Datasets as `name:snapshot` pairs; snapshots are dates of curated snapshots (`just search "<name>"`
  or the dashboard's data page lists them). An experiment may also read raw views, but then say so.
- Optional `--parent SLUG` when this follows a frozen experiment.

## Steps

1. Search first: `just search "<hypothesis keywords>"` and read any research-log entry that comes
   back. If the idea was killed, stop and tell the human why; link the entry.
2. Scaffold: `just experiment <slug> --project <p> --hypothesis "..." --dataset name:snapshot`
   (the project folder must exist: `just project <p>` creates it with a README). This creates
   `research/<project>/experiments/<today>-<slug>/` with `config.yaml`, `run.py`, `results.md` (status draft)
   and `figures/`. Never rename the folder afterwards.
3. Edit `config.yaml` (params, seed) and `run.py`. The notebook must read data only through
   `quant.data.load(config)` and must write anything quotable to `outputs/`.
4. Run it: `uv run research/<project>/experiments/<folder>/run.py` (headless) or `marimo edit` in the devcontainer.
5. Check for duplicated code: `just experiment <slug> --check-dupes`. A duplicate means the reuse
   rule applies: move the function to a tool (`just new-tool <name>`, or an existing one under
   `tools/`) with a test, in its own PR, before this experiment's PR. Experiments never import
   each other; they meet only in the data layer.
6. Finish: `just experiment <slug> --finish` drafts the Result sections of `results.md` and
   `knowledge/research-log/<today>-<slug>.md` from `outputs/` only. Write the Verdict yourself.
   Tags come from `just tags`; if none fits, append one to `knowledge/context/tags.md` in this PR.
7. Set `status: final` in `results.md` only when nothing will change; the folder is frozen after that.
8. Write the agent-log entry (template `knowledge/templates/agent-log.md`) linking every file
   touched and relied on, then open the PR.

## Checks before opening the PR

- `just check` and `just test` pass; `just check` would fail if a frozen folder was touched.
- Every number in `results.md` and the research-log entry appears in a file under `outputs/`.
- `config.yaml` names every dataset the notebook reads, with a snapshot.
- No function in `run.py` duplicates one in another experiment (or the move PR is linked).
- The research-log entry passes the frontmatter checker (owner in team.yaml, tags in tags.md).

## Done when

- The experiment folder, the research-log entry and the agent-log entry are in one PR with green CI.
- `just search "<slug>"` returns the research-log entry after `just index`.
- The PR is merged by the skill only if no changed path is under CODEOWNERS; otherwise it is
  left open for the human.
