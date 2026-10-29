# Dashboard hub

One marimo app, five pages, no state of its own. Everything shown is read live from the repo
files, the catalog views or the retrieval index, so the hub is always as current as your checkout
and the bucket.

## Run it

```text
$ just dashboard
```

Then open `http://localhost:2718`. In VS Code the port is forwarded automatically; with the
devcontainer CLI add `--publish 2718:2718` or use the forwarded port the CLI prints. The page
dropdown at the top switches pages; the filter boxes (owner, tag, dataset, status, search) are
shared across pages and each page reads the ones it understands.

## The pages

| page | shows | source | when to look |
|---|---|---|---|
| experiments | one row per `research/experiments/*/`: slug, date, owner, status, datasets with snapshots, parent, hypothesis | `config.yaml` and the `results.md` frontmatter | before starting an experiment, to see what exists; to find frozen ones |
| data-health | one row per raw dataset: latest partition, expected date, days behind, owner | same code as `just data-health` | when a notebook loads less than you expected; the nightly workflow opens an issue per stale dataset |
| knowledge | search box over the chunk index plus `knowledge/INDEX.md` by type, tag and owner | `just search` and `just index` | to answer "what do we know about X" without a terminal |
| agent-log | every `knowledge/agent-log/*.md`, newest first | the files' frontmatter | weekly review of what agents did |
| signals | modules under `research/signals/` with their docstring line | the files | to see what is reusable before writing it again |

A page that cannot reach the bucket says so with the first line of the error and points to
`just onboard`; it never shows a cached table.

## Headless checks

Each page module exposes `rows()` without marimo, so tests and CI can assert on the same data the
page renders. From `dashboards/hub/`,
`uv run python -c "from pages import experiments; print(experiments.rows())"` prints the
experiments table; `just data-health` is the data-health page as text.

## Adding a page

Add `dashboards/hub/pages/<name>.py` with `rows()` and `render(mo, filters)`, import it in
`app.py` and add it to `PAGES`. Pages read; they never compute a dataset and cache it. If a page
needs a number nobody has computed yet, that number is an experiment or a `src/quant` function
with a test, not dashboard code.
