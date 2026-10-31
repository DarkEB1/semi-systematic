# research/

Rules for anything under `research/`. The root `AGENTS.md` applies as well.

- A project is a folder: `research/<project>/` with `README.md` (frontmatter `type: project`, `id`
  equal to the folder name) and `experiments/`. `just project <slug>` creates one (ADR-0004).
- An experiment is `research/<project>/experiments/<date>-<slug>/`, created by
  `just experiment <slug> --project <p>`. Never rename or move either kind of folder.
- `config.yaml` is the whole contract: datasets with snapshots, params, seed. The notebook reads
  data only through `quant.data.load(config)`; a missing snapshot is an error, never "latest".
- Every number that will be quoted is written to `outputs/` (gitignored). `--finish` drafts
  `results.md` and the research-log entry from `outputs/` only. You write the Verdict.
- `status: final` in `results.md` freezes the folder; `just check` refuses later diffs. A follow-up
  is a new experiment with `parent: <slug>`.
- An experiment imports `quant`, tools and third-party packages. Never another experiment, a
  script or the dashboard. Code a second experiment needs moves to a tool first, in its own PR;
  `just experiment <slug> --check-dupes` finds the candidates.
- Run headless with `uv run research/<project>/experiments/<folder>/run.py`. Figures are PNG under
  1 MB in `figures/`.
