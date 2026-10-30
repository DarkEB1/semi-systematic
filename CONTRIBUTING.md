# Contributing

How changes get into `main`, for people and agents. The rules themselves are in
[AGENTS.md](AGENTS.md); the first page to read is
[knowledge/context/start-here.md](knowledge/context/start-here.md).

## Branches and PRs

- `main` is protected: one required status check (`ci`), linear history, squash merges only,
  admins included. Nobody pushes to `main` directly, not even the data-layer owner.
- Branch names: `research/<slug>`, `data/<source-or-dataset>`, `docs/<slug>`, `chore/<slug>`,
  `fix/<slug>`. Agents use the same names.
- Commit messages are conventional (`feat(research): ...`, `docs: ...`, `chore: ...`); the squash
  keeps the PR title, so the PR title matters more than the commits.
- One PR per thing. An experiment and its research-log entry are one thing; moving a function into
  a tool under the reuse rule is a separate PR that lands first.
- Review is trust-based: when CI is green the author merges. The exception is the data-layer block
  in `.github/CODEOWNERS` (`src/quant/data/**`, `catalog/**`, `promote/**`, `.github/**`): PRs
  touching those wait for the data-layer owner. Skills follow the same rule for their own PRs.

## What CI runs and how to read a failure

CI runs exactly what you can run locally, in this order:

| step | what it checks | fix |
|---|---|---|
| `just check` → `ruff check`, `ruff format --check` | lint and formatting | `uv run ruff check --fix .` then `uv run ruff format .` |
| `check_frontmatter.py` | every `knowledge/**/*.md` and dataset README: required keys, type, status, owner in `team.yaml`, tags in `tags.md`, `id` equals filename, ISO date, no `private` on notes, meeting Decisions lines link an ADR or end with `(minor)` | the message names the file and the key |
| `check_links.py` | relative markdown links resolve | fix the path; links are relative to the file |
| `check_size.py` | no tracked or untracked file over 1 MB | move data to the bucket, figures under 1 MB |
| `check_env.py` | every environment variable a recipe or script reads is in `.env.example` | add the line, with a comment, to `.env.example` |
| `check_frozen.py` | no diff under an experiment whose `results.md` is `status: final` | new experiment with `parent:` |
| `check_isolation.py` | units are isolated: tools follow `tools/README.md`, experiments import only `quant` and tools (never each other), `src/quant` and scripts import no research or dashboard code, no `sys.path` hacks anywhere | see `tools/README.md` and ADR-0003 |
| `gitleaks dir .` | no secret in the tree | rotate the key, then remove it; a rotated key is still a finding in history |
| `just test` | pytest across `tests/` and the `tools/*` members | read the failing test |
| `just eval` | each skill's `run.py` output equals its golden in `ai/evals/<skill>/expected.txt` | if the change was intended, `just eval --update` and review the golden diff in the PR |

The pre-commit hook runs the same `check` steps, so a commit that goes through locally passes
that part of CI. Run `just test` and `just eval` yourself before pushing; they are not hooks.

## Adding things

Every "where does X go" has one answer; `just where "<thing>"` prints it with the rule and the
recipe. The common ones:

- **A note**: copy `knowledge/templates/note.md` to `knowledge/notes/<you>/<date>-<slug>.md`. No recipe needed.
- **An experiment**: `just experiment <slug>`; finish with `--finish`. See the [walkthrough](knowledge/context/walkthrough.md).
- **A data source**: `just scaffold-source <source>` and the pull-data skill. The README under `catalog/datasets/` is the contract.
- **A curated dataset**: `just promote-request <name> <scratch key>`; the merge does the copy.
- **A meeting**: `just meeting <date> "<title>" < bullets.txt`.
- **A tag**: append one line, `- <tag>: <definition>`, to the right family in `knowledge/context/tags.md`, in the PR that first uses it. Tags are few on purpose.
- **A teammate**: `knowledge/notes/<handle>/.gitkeep`, the handle in `knowledge/context/team.yaml`, a `/knowledge/notes/<handle>/ @<handle>` line in `.github/CODEOWNERS`, and an R2 token named `<handle>-scratch` created by the data-layer owner (never committed anywhere).
- **A decision**: apply the ADR test (it changes a convention, a dependency, a data source, a method others will reuse, or costs money). Yes: copy `knowledge/templates/decision.md` to `knowledge/decisions/ADR-NNNN-<slug>.md` with the next number. No: a `(minor)` line in the minutes.
- **A dependency**: it is an ADR (it changes a dependency). Add it with `uv add`, commit `uv.lock`, and keep `src/quant` free of the optional `ml` extra (ruff enforces it).
- **A tool**: `just new-tool <name>`, then `uv lock && just setup`. A tool is an isolated package that imports only what its own `pyproject.toml` declares and takes every path as an argument; the contract is `tools/README.md`. An external engine (a backtester, an optimiser) is wrapped by one tool and imported from there. Adding a tool is an ADR.
- **A skill**: `.claude/skills/<name>/SKILL.md` with the four sections, a `run.py`, an `ai/evals/<name>/` golden, a row in the AGENTS.md skills table, and a `just` recipe if it has a deterministic part. The repo-structure skill's `run.py --check` verifies all of that.
- **A convention change**: templates, `scripts/check_frontmatter.py`, `AGENTS.md`, the affected `SKILL.md` and its golden move together in one PR, plus the ADR. Never rename or move an existing knowledge file to fit a new convention.

## Secrets

`.env` is yours and gitignored; `.env.example` is the list of variables with where each comes
from. Never paste a key into a chat, a file in the repo, a PR, an issue or a log. If one leaks,
rotate it in the Cloudflare or GitHub dashboard first and tell the data-layer owner; removing it
from git does not un-leak it.

## Reporting problems

GitHub issues, with the exact failing command and its output. Data problems get the `data-health`
label (the nightly workflow uses the same one). There are no chat notifications by design.
