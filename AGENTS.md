# AGENTS.md

How to work in `semi-systematic`, for people and agents alike. Everything runs inside the
devcontainer through `just` recipes (run `just` to list them). Longer story: `knowledge/context/workflow.md`.

## Map: six areas

| area | where | what |
|---|---|---|
| 1. context | `knowledge/` (`context/`, `decisions/`, `meetings/`, `notes/<handle>/`, `research-log/`, `agent-log/`, `templates/`, `INDEX.md`) | the team's memory as plain text with frontmatter; opens as an Obsidian vault |
| 2. research | `research/experiments/<date>-<slug>/`, `research/signals/` | reproducible experiments (config.yaml, marimo run.py, results.md, figures/) and code reused by 2+ experiments |
| 3. dashboards | `dashboards/hub/` | one marimo hub: data-health, experiments, knowledge, agent-log, signals |
| 4. tooling we build | `tools/brain/` (retrieval index), `tools/backtest/` | uv workspace members with their own pyproject |
| 5. AI meta | `ai/prompts/`, `ai/evals/<skill>/`, `ai/tasks/<slug>.yaml`, `ai/models.yaml`; skills in `.claude/skills/` | prompts, golden evals, budgeted tasks, model names |
| 6. other | `src/quant/` (library), `tests/`, `catalog/` (views, dataset READMEs, reference CSVs), `promote/requests/`, `scripts/`, `assets/` | the data layer and plumbing |

## The eight rules

1. **Run `just test` before claiming anything works.** `just check` too; CI runs both plus `just eval`.
2. **Never write `raw/` or `curated/`.** `raw/` is written only by `ingest.yml` (may overwrite a
   partition in place); `curated/` only by `promote.yml` (append-only, schema contract). People and
   agents write `scratch/<handle>/` only; `quant.data.write_once` refuses anything else.
3. **Every experiment ends in a research-log entry** (`just experiment <slug> --finish` drafts it;
   numbers come from `outputs/` only). `status: final` freezes the folder.
4. **Decisions are ADRs by the ADR test**: a decision becomes an ADR when it changes a convention,
   a dependency, a data source, a method others will reuse, or costs money; otherwise it is a
   minutes line marked `(minor)`. A changed decision is a new ADR with `status: superseded` on the old one.
5. **Knowledge files use the templates and pass `just check`**: frontmatter `id` (= filename),
   `type`, `title`, `date`, `authors`, `owner` (in `knowledge/context/team.yaml`); optional
   `status`, `tags` (from `knowledge/context/tags.md`), `datasets`, `related`, `private` (never on notes).
   One `#` title, `##` sections under ~400 words, relative links, ISO dates.
6. **Never rename or move a file under `knowledge/`.**
7. **Every agent task ends with an agent-log entry** (`knowledge/agent-log/`, template
   `knowledge/templates/agent-log.md`) linking every file it touched and every file it relied on.
8. **Search before you act**: `just search "<topic>"` for prior decisions, experiments and notes.

## Data layer in one paragraph

`quant.data.connect()` gives a DuckDB connection with every view in `catalog/catalog.sql`
(`<source>_<dataset>` for raw, plain names for curated, `ref_<name>` for reference CSVs).
Partitions: daily `year=/month=`, intraday `date=` with one file per asset class, curated
`snapshot=YYYY-MM-DD`. `quant.data.load(config)` returns only the datasets an experiment names at
the snapshots it names. The Schema table in `catalog/datasets/<name>.md` is the contract for
`curated/<name>/`; raw is stored as received. Reuse rule: code moves from an experiment to
`research/signals/` or `src/quant/` only on second use, with a test, in its own PR.

## Skills (`.claude/skills/<name>/SKILL.md` + deterministic `run.py`)

| skill | recipe | does |
|---|---|---|
| pull-data | `just scaffold-source SOURCE` | new source: module, README, view, test + fixture, registry, workflow entry |
| refresh-data | `just refresh [--execute]` | expected vs actual partitions; re-ingest gaps; issue for the unrecoverable |
| promote-dataset | `just promote-request NAME KEY` | validate against the README schema; write the promote request; PR checklist |
| new-experiment | `just experiment SLUG [--finish]` | scaffold; flag duplicated code; draft results + research-log from outputs |
| meeting-notes | `just meeting DATE TITLE` | bullets to meeting file; ADR test; ADR drafts; actions; no transcript stored |
| build-index | `just index`, `just search Q` | rebuild chunks.parquet + INDEX.md; answer "what do we know about X" with paths |
| repo-structure | `just where THING` | where a new thing goes; keep templates, checker, AGENTS.md and skills in sync |

Every skill: searches first (`just search`), sets `owner` and `tags` on any knowledge file it
writes (tags from `just tags`; a missing tag is appended to `tags.md` with a definition in the same
PR), and ends with the agent-log entry. Each skill has a golden eval in `ai/evals/<skill>/` (`just eval`).

## Autonomy

- A skill may commit, push and **merge its own PR** when CI is green and **no changed path is
  under the data-layer CODEOWNERS block** (`src/quant/data/**`, `catalog/**`, `promote/**`,
  `.github/**`). Otherwise it opens the PR and stops.
- Loops need a budget: `just task SLUG` writes `ai/tasks/<slug>.yaml` (goal, metric,
  `max_iterations`, `max_hours`, stop conditions, `allowed_paths`); `just loop SLUG` re-invokes the
  skill until a stop condition or the budget is hit, appending every iteration to one agent-log
  entry. The runner refuses to start without a budget and stops on a write outside `allowed_paths`.
- Secrets: `.env` on a laptop (gitignored), repository secrets in CI; `.env.example` lists every
  variable any recipe reads and `just check` enforces it. Never echo, log or commit a value.
- No chat notifications; issues and PRs are the only channels.

## The `just` interface

`setup` · `onboard` · `check` · `test` · `eval` · `ingest SOURCE [--since D]` · `refresh` ·
`promote REQUEST` · `promote-request NAME KEY` · `scaffold-source SOURCE` · `data-health` · `audit` ·
`ls PREFIX` · `backup` · `index` · `index-upload` · `search QUERY` · `embed` · `tags` ·
`meeting DATE TITLE` · `where THING` · `experiment SLUG [--finish]` · `dashboard` · `task SLUG` · `loop SLUG`

Scripts, skills and workflows call these recipes, never raw commands. Storage facts (bucket,
endpoint, tokens, what was decided and why) are in `knowledge/decisions/ADR-0001-initial-setup.md`.
