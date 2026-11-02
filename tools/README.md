# tools

Every folder here is a tool: an isolated Python package that can be imported or instantiated
wherever it is needed, in this repo or another, without dragging the rest of the repo along. The
repo consumes tools; tools never consume the repo. `brain` (the retrieval index) is the first
real one, `backtest` is the reserved slot for the first shared backtesting loop, and the set is
meant to grow: an optimiser, a risk model, a calendar library, a vendor client, each as its own
package.

## The contract

Enforced by `scripts/check_isolation.py` in `just check` (ADR-0002, ADR-0003).

1. **Layout**: `tools/<name>/pyproject.toml` (project name equals the folder name),
   `src/<name>/__init__.py` with `__version__` and `__all__`, `tests/test_*.py`, `README.md`.
   The src layout means the package is importable only when installed, never by accident from
   the working directory.
2. **Dependencies are declared, not assumed**: the tool's own `pyproject.toml` lists what it
   imports. It never imports `quant`, `scripts`, `dashboards` or `tests`. It may import another
   tool only if that tool is listed under its `dependencies` (and the root pyproject maps it with
   `{ workspace = true }`). One lockfile at the repo root pins everything.
3. **No knowledge of where it lives**: no `__file__` tricks to find the repository, no reading
   `.env`, no hard-coded repo paths in behaviour. Everything a tool needs is an argument or a
   small config object with defaults (see `brain.Repo`). The `just` recipes and the scripts
   supply the repo-specific values.
4. **Tests are self-contained**: they build their own fixtures under `tmp_path` and run without
   the repository content, the bucket, the network or `.env`. Tests that check the tool against
   this repo belong in the root `tests/`, where the consumer lives.
5. **A public API**: consumers import names from the package top level (`from brain import Repo,
   search`). Internal modules may change; `__all__` may not without a note in the README.
6. **Optional CLI**: a `[project.scripts]` entry is welcome when the tool has a command-line use;
   the justfile wraps it, so people and agents still type `just`.
7. **External engines are wrapped, not scattered**: if a third-party backtester or optimiser is
   adopted, it becomes a dependency of one tool here and the rest of the repo imports that tool,
   so swapping the engine is one package's concern.

## Creating one

```text
$ just new-tool calendars --description "Trading calendars and holiday rules per currency."
tools/calendars/pyproject.toml
tools/calendars/src/calendars/__init__.py
tools/calendars/tests/test_calendars.py
tools/calendars/README.md
pyproject.toml (registered)
next: uv lock && just setup, then write tools/calendars/README.md and `just check`
```

Adding a tool changes a dependency, so it is an ADR (template `knowledge/templates/decision.md`).
A tool that costs money (a paid engine, a hosted model) says so in the ADR.

## Where the repo-specific code goes instead

- Reading and writing the bucket, the prefix rules, the schema contract: `src/quant/` (the repo's own library, CODEOWNERS-gated in parts).
- Checkers, runners, onboarding: `scripts/`.
- Skill logic: `.claude/skills/<name>/<name_with_underscores>.py` today; a skill that grows a reusable core moves that core into a tool and keeps the runner as the thin wrapper.
- Dashboards: `dashboards/hub/`, which imports tools and `quant` but is imported by nothing.
