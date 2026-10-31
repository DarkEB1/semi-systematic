# new-experiment

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

Task: run the new-experiment skill. Read .claude/skills/new-experiment/SKILL.md and follow its
Steps in order; its "Checks before opening the PR" and "Done when" sections are the acceptance
criteria.

Inputs:
- slug: <short-kebab-case>
- project: <folder under research/; if it does not exist, run `just project <slug> --goal "..."` first and show me the README>
- owner: <my GitHub handle>
- hypothesis (one line, the market expectation we are betting against): <...>
- datasets with snapshots: <name:YYYY-MM-DD, ...> (if no curated snapshot exists yet, say which raw view you will read instead and record that in the research-log entry)
- parent (only if this follows a frozen experiment): <slug or none>

Before scaffolding, run `just search` on the hypothesis keywords and show me any research-log
entry that already tested this; if one killed the idea, stop and tell me why. When the notebook
has run, use `just experiment <slug> --finish` to draft results.md and the research-log entry;
never type a number that is not in outputs/. Leave the Verdict as a TODO for me unless I gave you
one. Do not set status: final.
