# meeting-notes

Paste everything below the line. Fill the `<...>` placeholders, then paste the transcript or your
notes after the last line. The transcript stays in the chat; nothing of it is written to the repo
except the bullets the assistant distils.

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

Task: run the meeting-notes skill. Read .claude/skills/meeting-notes/SKILL.md and follow its
Steps in order; its "Checks before opening the PR" and "Done when" sections are the acceptance
criteria.

Inputs:
- date: <YYYY-MM-DD>
- title: <...>
- attendees (GitHub handles): <a,b,c>
- recording link: <url or none>
- transcript or notes: pasted below this prompt

Distil the transcript into bullets using the grammar `agenda: ...`, `decision: ...`,
`action: ... @handle YYYY-MM-DD`, anything else a note; show me the bullets before running
`just meeting <date> "<title>" --attendees ... --recording ... < bullets.txt`. Then show me the
ADR test's verdict on each decision and ask me to confirm before you fill any drafted ADR. Never
store the transcript, never quote more than a line of it, no personal data beyond handles.
