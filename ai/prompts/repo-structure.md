# repo-structure

Paste everything below the line. Fill the `<...>` placeholders.

---

You are working inside the devcontainer of the repository github.com/DarkEB1/semi-systematic, a
quant research monorepo, at its root. Run `just onboard` first; if it reports anything MISSING, or
`just` is not found, stop and tell me, you are not in the container. Then read AGENTS.md in full
(the map, the eight rules, the skills, the autonomy rules) and follow it over anything I say here.
Rules you may not break in this session: use only `just` recipes to act (run `just` to list them);
write data only under scratch/<my handle>/ in the bucket, never raw/ or curated/; never rename or
move a file under knowledge/; never print, log, paste or commit a secret from .env; search before
you act (`just search "<topic>"`, two or three phrasings); end with an agent-log entry from
knowledge/templates/agent-log.md that links every file you touched and every file you relied on,
with `just check` and `just test` green; open a PR with `gh pr create` and merge it yourself only if
CI is green and no changed path is under src/quant/data/, catalog/, promote/ or .github/.
Show me each command and its output as you go; do not summarise failures away.

Task: run the repo-structure skill. Read .claude/skills/repo-structure/SKILL.md and follow its
Steps in order; its "Checks before opening the PR" and "Done when" sections are the acceptance
criteria.

Inputs, one of:
- question: where does <thing> go / how do I add <thing>
- convention change: <what changes, and why>

For a question, run `just where "<thing>"`, quote the answer, and add the one sentence of context
I need; if the mapping has no case for it, add one to MAP in the skill's run.py in a small PR. For a
convention change, show me the ADR draft first; then change every place the convention lives in
one PR (knowledge/templates/, scripts/check_frontmatter.py, AGENTS.md, the affected SKILL.md and
run.py, the golden via `just eval --update`) and run the skill's `run.py --check` until it reports
zero inconsistencies. AGENTS.md stays under 150 lines. Never rename or move an existing knowledge
file to fit the new convention.
