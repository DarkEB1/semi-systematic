You are working in the repository github.com/DarkEB1/semi-systematic, a quant research monorepo,
at its root, inside its devcontainer or on the host. Run `just onboard` first. If `just` is not
found you are on the host: run every `just` recipe and every `git commit` as
`sh scripts/in-container.sh <command>` instead, and read or edit files directly. If onboard reports
anything MISSING, stop and tell me. Then read AGENTS.md in full
(how to work, how to verify, the nine rules, autonomy) and the AGENTS.md of any folder you touch,
and follow them over anything I say here.
Rules you may not break in this session: use only `just` recipes to act (run `just` to list them);
write data only under scratch/<my handle>/ in the bucket, never raw/ or curated/; never rename or
move a file under knowledge/; never print, log, paste or commit a secret from .env; search before
you act (`just search "<topic>"`, two or three phrasings); end with an agent-log entry from
knowledge/templates/agent-log.md that links every file you touched and every file you relied on,
with `just check` and `just test` green; open a PR with `gh pr create` and merge it yourself only if
CI is green and no changed path is under src/quant/data/, catalog/, promote/ or .github/.
Show me each command and its output as you go; do not summarise failures away.
