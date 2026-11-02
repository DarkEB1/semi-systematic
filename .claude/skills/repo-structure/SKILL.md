---
name: repo-structure
description: Explain where a new thing goes in this repo and which recipe or skill creates it; when a convention changes, update the templates, check_frontmatter.py, AGENTS.md and the affected skill together in one PR and verify they agree.
---

# repo-structure

Deterministic part: `.claude/skills/repo-structure/repo_structure.py`, exposed as `just where "<thing>"`
(answers) and `repo_structure.py --check` (verifies the convention files agree). Eval fixture:
`ai/evals/repo-structure/`.

## Inputs

- A question of the form "where does X go" or "how do I add X", or a convention change
  (a new frontmatter key, a new type, a new tag family, a new skill, a renamed recipe).

## Steps

1. For a question: `just where "<thing>"` prints the location, the rule that applies and the
   recipe or skill that creates it. Quote it, add the one sentence of context the asker needs,
   and point to `AGENTS.md` for the map. If the mapping is missing a case, add it to `MAP` in
   `repo_structure.py` in a small PR.
2. For a convention change, search first: `just search "<convention>"`; the ADR that set it may
   list why. A convention change is itself an ADR (template `knowledge/templates/decision.md`).
3. Change every place the convention lives, in one PR:
   `knowledge/templates/*.md`, `scripts/check_frontmatter.py` (required keys, types, statuses,
   body rules), `AGENTS.md` (rules, map, skill list, just interface), the affected
   `.claude/skills/<name>/SKILL.md` and its runner, and `ai/evals/<name>/expected.txt` via
   `just eval --update`. Never rename or move an existing knowledge file to fit a new convention.
4. Run `repo_structure.py --check`: templates per type, four sections per SKILL.md, only existing `just`
   recipes named, runner and eval present per skill, every skill listed in AGENTS.md, every
   handle with a notes dir and a CODEOWNERS line.
5. Write the agent-log entry and open the PR.

## Checks before opening the PR

- `just check`, `just test` and `just eval` pass (goldens refreshed deliberately, diff reviewed).
- `repo_structure.py --check` reports zero inconsistencies.
- `AGENTS.md` stays under 150 lines.
- If `.github/**` or `catalog/**` changed, the PR waits for the data-layer owner.

## Done when

- The question is answered with the location and rule, or the convention change is merged with
  all five places updated together and the ADR linked from the agent-log entry.
