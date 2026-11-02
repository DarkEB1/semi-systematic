# tools/

Rules beyond the root `AGENTS.md`:

- Each tool is an isolated package: `tools/<name>/` with src layout, its own `pyproject.toml`
  (project name equals the folder), tests, a README, `__version__` and `__all__`. The contract is
  `tools/README.md`; `just new-tool NAME` scaffolds it; `scripts/check_isolation.py` enforces it.
- A tool imports only what its `pyproject.toml` declares. Never `quant`, scripts, dashboards or
  research; no repo paths derived from `__file__`; no `.env`. Every path and setting arrives as an
  argument (brain takes a `Repo`).
- One tool's tests: `uv run pytest tools/<name>/tests -q`. After editing a `pyproject.toml`:
  `uv lock`, then `just setup`.
- Adding a tool is an ADR. Code enters a tool from an experiment on its second use, with a test,
  in its own PR, before the experiment's PR.
