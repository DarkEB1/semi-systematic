# pull-data

Paste everything below the line. Fill the `<...>` placeholders.

---

You are working inside the devcontainer of the repository github.com/DarkEB1/semi-systematic, a
quant research monorepo, at its root. Run `just onboard` first; if it reports anything MISSING, or
`just` is not found, stop and tell me, you are not in the container. Then read AGENTS.md in full
(the map, the nine rules, the skills, the autonomy rules) and follow it over anything I say here.
Rules you may not break in this session: use only `just` recipes to act (run `just` to list them);
write data only under scratch/<my handle>/ in the bucket, never raw/ or curated/; never rename or
move a file under knowledge/; never print, log, paste or commit a secret from .env; search before
you act (`just search "<topic>"`, two or three phrasings); end with an agent-log entry from
knowledge/templates/agent-log.md that links every file you touched and every file you relied on,
with `just check` and `just test` green; open a PR with `gh pr create` and merge it yourself only if
CI is green and no changed path is under src/quant/data/, catalog/, promote/ or .github/.
Show me each command and its output as you go; do not summarise failures away.

Task: run the pull-data skill. Read .claude/skills/pull-data/SKILL.md and follow its Steps in
order; its "Checks before opening the PR" and "Done when" sections are the acceptance criteria.

Inputs:
- source id (lowercase): <fred, ecb, ...>
- dataset name: <source_daily or a better name>
- cadence: <daily | intraday | snapshot>
- one-line description: <...>
- vendor URL and licence terms: <...>
- needs a key: <no | yes, variable name> (a new variable goes into .env.example in the same PR; I will fill .env myself, never ask me for the value)

Check knowledge/context/vendors.md and `just search "<vendor>"` first; a rejected vendor stays
rejected unless I say otherwise. After the scaffold, implement fetch and normalise, replace the
fixture with a small real sample, fill the dataset README including its Schema table, run
`just test`, `just ingest <source> --dry-run`, then `just ingest <source>` (it lands in my scratch
prefix) and show me `just ls scratch/<my handle>/`. The PR touches catalog/ so you open it and stop;
do not merge.
