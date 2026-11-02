# research

Experiments and the code that graduates out of them.

## <project>/

A project is a folder (ADR-0004): `research/<project>/README.md` (frontmatter `type: project`, id
equal to the folder name; template `knowledge/templates/project.md`) and `experiments/`.
`just project <slug>` creates one. Projects are isolated units: they meet other projects only
through datasets, the dashboard and `knowledge/`. Never renamed; a closed project is `status: final`.

## <project>/experiments/

One folder per experiment, `YYYY-MM-DD-<slug>/`, created by `just experiment <slug> --project
<project>` and never renamed or moved between projects. Inside:

| file | role |
|---|---|
| `config.yaml` | the contract: slug, date, owner, hypothesis, datasets with snapshots, params, seed, optional `parent` |
| `run.py` | a marimo notebook; reads data only through `quant.data.load(config)`; writes anything quotable to `outputs/` |
| `results.md` | status (`draft` or `final`), hypothesis, Result drafted by `--finish` from `outputs/`, figures |
| `figures/` | PNGs under 1 MB each |
| `outputs/` | gitignored; metrics and tables the notebook wrote; the only source of numbers |

`just experiment <slug> --finish` finds the folder in any project and drafts `results.md` and `knowledge/research-log/<date>-<slug>.md`
from `outputs/`. `status: final` freezes the folder (`just check` fails later diffs); a follow-up
is a new experiment with `parent: <slug>`. Full example: [knowledge/context/walkthrough.md](../knowledge/context/walkthrough.md).

## Isolation

Every experiment is a unit on its own: it imports the data layer (`quant.data`), tools under
`tools/` and third-party packages, and nothing else. Experiments never import each other, and
nothing imports an experiment. Code used by two or more experiments moves into a tool
(`just new-tool <name>`, or an existing tool) on its second use, with a test, in its own PR that
lands before the experiment that needs it; `just experiment <slug> --check-dupes` finds
candidates. Until then, duplication inside experiments is fine. `scripts/check_isolation.py` in
`just check` enforces the import rules (ADR-0003); the hub's tools page lists what is reusable.
