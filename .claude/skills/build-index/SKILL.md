---
name: build-index
description: Rebuild the repo retrieval index (chunks.parquet and knowledge/INDEX.md) and answer "what do we know about X" from it, citing file paths, without inventing facts that are not in the indexed text.
---

# build-index

Deterministic part: `.claude/skills/build-index/build_index.py` (`build`, `search`, `answer`,
`chunk-file`), exposed as `just index` and `just search "..."`. The index is repo-only in v1
(DuckDB `ILIKE`); `just embed` errors until an embedding model is configured. Eval fixture:
`ai/evals/build-index/` (chunking of a sample file).

## Inputs

- A question ("what do we know about X") or nothing (rebuild after files changed).
- The index lives at `.index/chunks.parquet` (gitignored); `index.yml` uploads it to
  `curated/repo_index/snapshot=<sha>/` on every merge to main, exposed as the `repo_index` view.

## Steps

1. `just index` whenever knowledge, catalog, experiments, skills or code changed. It also
   regenerates `knowledge/INDEX.md` (by type newest first, by tag, by owner); commit that file.
2. To answer a question: `just search "<words>"` (or `build_index.py answer "<question>"` for a citation
   list). Try two or three phrasings: the index matches text literally.
3. Read the hits that matter in full (the snippet is not the source). Answer only from what the
   files say, and cite every claim as `path › heading`. If nothing matches, say so and suggest
   where such a note would live (`just where "<thing>"`).
4. If the question exposed a gap (a decision everyone knows but no file records), write it as a
   note or an ADR in the same session and rebuild the index.
5. Write the agent-log entry: the question, the paths cited, and any file created.

## Checks before opening the PR

- `just check` passes (INDEX.md is generated, do not hand-edit it).
- `knowledge/INDEX.md` lists every non-private knowledge file and dataset README.
- `just search "R2"` returns `knowledge/decisions/ADR-0001-initial-setup.md`.

## Done when

- The question is answered with citations, or a new file closes the gap and is in a PR with the
  regenerated INDEX.md, and the agent-log entry links the files relied on.
