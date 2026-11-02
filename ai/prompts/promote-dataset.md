# promote-dataset

Paste everything below the line. Fill the `<...>` placeholders.

---

You are working in the repository github.com/DarkEB1/semi-systematic, a quant research monorepo,
at its root, inside its devcontainer or on the host. Run `just onboard` first. If `just` is not
found you are on the host: run every `just` recipe and every `git commit` as
`sh scripts/in-container.sh <command>` instead, and read or edit files directly. If onboard reports
anything MISSING, stop and tell me. Then read AGENTS.md in full
(the map, the nine rules, the skills, the autonomy rules) and follow it over anything I say here.
Rules you may not break in this session: use only `just` recipes to act (run `just` to list them);
write data only under scratch/<my handle>/ in the bucket, never raw/ or curated/; never rename or
move a file under knowledge/; never print, log, paste or commit a secret from .env; search before
you act (`just search "<topic>"`, two or three phrasings); end with an agent-log entry from
knowledge/templates/agent-log.md that links every file you touched and every file you relied on,
with `just check` and `just test` green; open a PR with `gh pr create` and merge it yourself only if
CI is green and no changed path is under src/quant/data/, catalog/, promote/ or .github/.
Show me each command and its output as you go; do not summarise failures away.

Task: run the promote-dataset skill. Read .claude/skills/promote-dataset/SKILL.md and follow its
Steps in order; its "Checks before opening the PR" and "Done when" sections are the acceptance
criteria.

Inputs:
- dataset name (also the curated view name): <name>
- scratch key of the Parquet to promote: <scratch/<handle>/.../data.parquet> (`just ls scratch/<handle>/` to confirm it exists)
- snapshot date: <YYYY-MM-DD, default today>
- notes for the request: <...>

Run `just promote-request <name> <key>`; if the README is missing, rerun with `--write-readme`
and fill Source, Cadence, Known gaps and Owner from what I tell you, never leaving TODO. On a
schema mismatch, show me the differing columns and stop; do not edit the README to make the data
fit unless I say the contract was wrong (that is an ADR). Paste the printed checklist into the PR
body. This PR touches promote/ and catalog/, so you open it and stop; the data-layer owner merges.
