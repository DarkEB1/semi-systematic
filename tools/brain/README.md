# brain

A retrieval index over a plain-text repository. In this repo it is what `just search` and the
hub's knowledge page read, and the reason rule 8 ("search before you act") is cheap to follow. It
is a tool in the sense of [tools/README.md](../README.md): point it at any folder and it works.

## Use as a library

```python
from brain import Repo, build, search, write_index

repo = Repo("/path/to/repo")  # defaults describe this repo's layout
build(repo)  # writes <root>/.index/chunks.parquet, returns the chunk count
hits = search("carry", repo=repo)  # list[Hit]: path, heading, date, type, snippet; newest first
write_index(repo)  # renders <root>/knowledge/INDEX.md
```

`Repo` holds the root and the relative locations: `knowledge`, `datasets`, `experiments`,
`skills`, `code` (folders of Python), `index_dir`, `index_md`, `skip_parts`. Another repository
passes its own, for example `Repo(root, knowledge="docs", index_md="docs/TOC.md")`.
`Repo.discover()` walks up from the working directory to the first `.git`, `justfile` or
`pyproject.toml`. brain never reads `.env` and never derives a path from its own file.

## Use from the shell

| recipe | brain command | does |
|---|---|---|
| `just index` | `brain build` then `brain index-md` | chunk every indexed file into `.index/chunks.parquet` (gitignored), regenerate `knowledge/INDEX.md` (by type newest first, by tag, by owner). Commit INDEX.md. |
| `just search "<words>"` | `brain search` | DuckDB `ILIKE` over text, heading and title, newest first; prints `path › heading [type, date]` and a snippet |
| `just index-upload` | (scripts/upload_index.py) | CI only: uploads the chunk table to `curated/repo_index/snapshot=<sha>/`, the `repo_index` view |
| `just embed` | `brain embed --model` | reserved; errors until an embedding model is chosen (ADR-0001 keeps v1 keyword-only) |

Every command takes `--root`; the default is discovered from the working directory. `index.yml`
runs build and upload on every merge to `main`.

## How chunking works

One function, `brain.chunk(path, text, repo)`, decides the unit of retrieval:

- Markdown: one chunk per `##` section, with the file's frontmatter (type, date, owner, tags) on every chunk so filters work. `private: true` files are skipped; `SKILL.md` gets type `skill`, an experiment's `results.md` gets type `results`.
- Experiment `config.yaml`: one chunk of type `experiment` carrying the datasets it names.
- Python: one chunk per top-level function or class, docstring first, so a search for a concept finds the function that implements it.

Each row has fifteen columns (`brain.SCHEMA`): `path`, `heading`, `type`, `title`, `date`,
`owner`, `tags`, `datasets`, `text`, a stable `chunk_id`, the git sha and the file's mtime.

## Answering "what do we know about X"

The build-index skill (`.claude/skills/build-index/SKILL.md`) is the procedure: search two or
three phrasings, read the hits in full, answer only from what the files say and cite each claim as
`path › heading`. The skill's runner, `build_index.py answer "<question>"`, prints the citation list. A question
with no hits is a gap; the fix is a note or an ADR, then `just index`.

## Tests

`tools/brain/tests/test_brain.py` builds small repositories under `tmp_path` and runs without
this repo's content. `tests/test_brain_repo.py` at the repo root is the consumer-side check that
the index over this repository finds ADR-0001 and the data layer. The chunker also has a golden in
`ai/evals/build-index/`.
