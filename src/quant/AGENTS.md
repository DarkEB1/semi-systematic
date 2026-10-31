# src/quant/

The data layer. Rules beyond the root `AGENTS.md`:

- Bucket prefixes: `raw/` is written only by `ingest.yml` (a partition may be overwritten in
  place), `curated/` only by `promote.yml` (append-only, schema contract from the dataset README),
  `scratch/<handle>/` by everyone else. `write_once` enforces this; never add a bypass or a default.
- Imports: the base dependency group only (ruff bans the `ml` extra here), third-party packages and
  tools. Never research, dashboards or scripts.
- `src/quant/data/**`, `catalog/**`, `promote/**` and `.github/**` form the data-layer CODEOWNERS
  block. A PR touching them waits for the data-layer owner; a skill opens it and stops.
- Settings come from the environment (`.env` locally, repository secrets in CI). Every variable
  read here must be listed in `.env.example` (`check_env.py`). Never log or print a value.
- A new source starts with `just scaffold-source <source>` (the pull-data skill). The README under
  `catalog/datasets/` is the contract, and the fixture test must run offline.
- Typed and small: mypy runs here in `just check`, public functions carry annotations, and the
  complexity caps in `pyproject.toml` apply. Split a module before it passes 400 lines.
