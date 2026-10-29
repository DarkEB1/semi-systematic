# research

Experiments and the code that graduates out of them.

## experiments/

One folder per experiment, `YYYY-MM-DD-<slug>/`, created by `just experiment <slug>` and never
renamed. Inside:

| file | role |
|---|---|
| `config.yaml` | the contract: slug, date, owner, hypothesis, datasets with snapshots, params, seed, optional `parent` |
| `run.py` | a marimo notebook; reads data only through `quant.data.load(config)`; writes anything quotable to `outputs/` |
| `results.md` | status (`draft` or `final`), hypothesis, Result drafted by `--finish` from `outputs/`, figures |
| `figures/` | PNGs under 1 MB each |
| `outputs/` | gitignored; metrics and tables the notebook wrote; the only source of numbers |

`just experiment <slug> --finish` drafts `results.md` and `knowledge/research-log/<date>-<slug>.md`
from `outputs/`. `status: final` freezes the folder (`just check` fails later diffs); a follow-up
is a new experiment with `parent: <slug>`. Full example: [knowledge/context/walkthrough.md](../knowledge/context/walkthrough.md).

## signals/

Code used by two or more experiments. The reuse rule: a function moves here (or to `src/quant/`)
on its second use, with a test, in its own PR that lands before the experiment that needs it.
`just experiment <slug> --check-dupes` finds candidates. Until a second use, duplication inside
experiments is fine. The hub's signals page lists what is here.
