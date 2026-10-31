# AGENTS.md

Rules for working in `semi-systematic`, for people and agents. Everything runs inside the
devcontainer through `just` recipes; `just` lists them. This file holds only what the repo cannot
tell you by itself. Per-folder rules live next to the code as `research/AGENTS.md`,
`knowledge/AGENTS.md`, `src/quant/AGENTS.md` and `tools/AGENTS.md`; the guides are listed at the end.

## How to work

1. **Think before coding.** State your assumptions. When a request has two readings, name both and
   take the one that needs less code, or ask.
2. **Least code.** No feature, option, abstraction or error path nobody asked for. Code leaves an
   experiment for a tool only on its second use.
3. **Surgical changes.** Touch only the paths the task needs, match the surrounding style, and
   mention dead code instead of deleting it.
4. **Goal-driven.** Turn the task into a check before starting (a test, a golden eval, the frozen
   check) and show that check's output when you say it is done.

## Verify

- Everything: `just check` then `just test`. CI runs both plus `just eval`. Nothing is done until all
  three are green and their result lines are in the message or the PR.
- One test: `uv run pytest tests/test_new_project.py -q`. One skill's golden: `just eval new-experiment`.
  `just eval --update` only after reading the diff it would write.
- Where you are: `just onboard`. A `MISSING` line, or no `just`, means you are not in the container. Stop.
- Search first: `just search "<topic>"` in two or three phrasings. `just where "<thing>"` says where a
  new thing goes and which recipe creates it.

## The nine rules

1. **`just test` and `just check` before claiming anything works.**
2. **Never write `raw/` or `curated/`.** `ingest.yml` writes raw, `promote.yml` writes curated. You
   write `scratch/<handle>/`, and `quant.data.write_once` refuses the rest.
3. **Every experiment ends in a research-log entry**, drafted by `just experiment <slug> --finish`
   from `outputs/` only. `status: final` in `results.md` freezes the folder.
4. **Decisions pass the ADR test.** A new convention, dependency, data source, reusable method or
   cost is an ADR; anything else is a `(minor)` minutes line. A changed decision is a new ADR with
   `status: superseded` on the old one.
5. **Knowledge files use the templates and pass `just check`.** The keys are in `knowledge/AGENTS.md`.
6. **Never rename or move a file under `knowledge/`.**
7. **Every agent task ends with an agent-log entry** from `knowledge/templates/agent-log.md`,
   linking every file it touched and every file it relied on.
8. **Search before you act.**
9. **Everything is isolated; units meet only in the data layer, the dashboard and `knowledge/`.**
   Shared code becomes a tool (`just new-tool`). `just check` enforces the imports (ADR-0003).

## Autonomy

- A skill commits, pushes and merges its own PR when CI is green, the `reviewer` subagent
  (`.claude/agents/reviewer.md`) reports no correctness gap, and no changed path is under the
  data-layer CODEOWNERS block (`src/quant/data/**`, `catalog/**`, `promote/**`, `.github/**`).
  Otherwise it opens the PR and stops.
- Loops need a budget: `just task SLUG`, then `just loop SLUG`. The runner refuses to start without
  `max_iterations`, `max_hours` and `allowed_paths`, and stops on a write outside them.
- Permissions are judged by Claude, not by people. Sessions run in auto mode, `.claude/settings.json`
  denies the few zero-exception actions (reading `.env`, `--no-verify`, force pushes, hand edits to
  frozen experiments) and the Stop hook asks for evidence. Nothing here waits for a person to click.
- Secrets: `.env` is gitignored and never read back; `.env.example` lists every variable; CI uses
  repository secrets. No chat notifications; issues and PRs are the channels.

## Gotchas

- Commit inside the container (pre-commit hooks live there). `git push` and `gh` work from the host.
- `ruff format` also reformats python code blocks inside markdown, and the frontmatter checker counts
  a `# ` line inside a code fence as a title.
- Dates are ISO. Owners are handles from `knowledge/context/team.yaml`. Tags come from `just tags`.
- Skills: `.claude/skills/<name>/SKILL.md` plus a runner `<name_with_underscores>.py`, each with a
  golden in `ai/evals/<name>/`: new-experiment, pull-data, refresh-data, promote-dataset,
  meeting-notes, build-index, repo-structure. Prompts for other assistants: `ai/prompts/<skill>.md`.

## Read first

| when you | read |
|---|---|
| are new here | `knowledge/context/start-here.md`, then `workflow.md` and `walkthrough.md` |
| touch data | `knowledge/context/data-access.md`, `src/quant/AGENTS.md`, `knowledge/decisions/ADR-0001-initial-setup.md` |
| start research | `research/AGENTS.md`, then the project's README |
| write under `knowledge/` | `knowledge/AGENTS.md`, then the template for the type |
| build a tool | `tools/AGENTS.md`, then `tools/README.md` |
| run or review an agent | `knowledge/context/working-with-agents.md`, `CONTRIBUTING.md` |
