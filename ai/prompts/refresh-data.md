# refresh-data

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

Task: run the refresh-data skill. Read .claude/skills/refresh-data/SKILL.md and follow its Steps
in order; its "Checks before opening the PR" and "Done when" sections are the acceptance criteria.

Inputs:
- scope: <all stale datasets | the dataset named in issue #N>

Run `just data-health` and `just refresh` and show me the plan before executing anything. Read
each affected dataset README's Known gaps: a vendor holiday is not a gap to fill. Then
`just refresh --execute`; on a laptop this writes to my scratch prefix only, which is expected.
For an ingest that fails, do not retry in a loop: `just refresh --execute --issue` opens one issue
per failure with the exact command. If no repo file changed, the agent-log entry alone is the PR.
