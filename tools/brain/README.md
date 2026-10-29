# brain

The retrieval index over the repository: knowledge files, dataset READMEs, experiments, skills,
prompts and Python code. It is what `just search` and the hub's knowledge page read, and the
reason rule 8 ("search before you act") is cheap to follow.

## Commands

| recipe | does |
|---|---|
| `just index` | `brain build` chunks every indexed file into `.index/chunks.parquet` (gitignored), then `brain index-md` regenerates `knowledge/INDEX.md` (by type newest first, by tag, by owner). Commit INDEX.md. |
| `just search "<words>"` | DuckDB `ILIKE` over the chunk table, newest first; prints `path › heading [type, date]` and a snippet |
| `just index-upload` | CI only: uploads the chunk table to `curated/repo_index/snapshot=<sha>/`, exposed as the `repo_index` view |
| `just embed` | reserved; errors until `EMBEDDING_MODEL` is set (ADR-0001 keeps v1 repo-only and keyword-based) |

`index.yml` runs build and upload on every merge to `main`, so the index on `main` is never stale
by more than one merge. Locally, rebuild after you change files; `just search` builds it on first use.

## How chunking works

One function, `brain.build.chunk(path, text)`, decides the unit of retrieval:

- Markdown: one chunk per `##` section, with the file's frontmatter (type, date, owner, tags) attached to every chunk so filters work.
- Python: one chunk per top-level function or class, docstring first, so a search for a concept finds the function that implements it.
- Everything else indexed (YAML, SQL, CSV headers): one chunk per file.

Each chunk row has fifteen columns including `path`, `heading`, `type`, `date`, `owner`, `tags`,
`text` and a stable `chunk_id`. `knowledge/notes/` is indexed like everything else; there is no
private note.

## Answering "what do we know about X"

The build-index skill (`.claude/skills/build-index/SKILL.md`) is the procedure: search two or
three phrasings, read the hits in full, answer only from what the files say and cite each claim as
`path › heading`. `run.py answer "<question>"` prints the citation list for that. A question with
no hits is a gap; the fix is a note or an ADR, then `just index`.

## Tests

`tools/brain/tests/test_brain.py`, run by `just test`. The chunker has a golden in
`ai/evals/build-index/` (`chunk-file` over `sample.md`), so a change to chunking shows up as an
eval diff.
