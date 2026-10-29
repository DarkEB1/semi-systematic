# Skill evals

One golden fixture per skill: `input.yaml` (args, optional env) and `expected.txt` (exact stdout of
`.claude/skills/<skill>/run.py` with those args). `just eval` diffs them; `just eval --update`
rewrites goldens (review the diff in the PR). Dates and owners are passed explicitly so output is
stable; `--dry-run` prints files instead of writing them.
