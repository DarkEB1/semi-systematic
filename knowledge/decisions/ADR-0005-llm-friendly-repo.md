---
id: ADR-0005-llm-friendly-repo
type: decision
title: "ADR-0005: instruction files, enforcement and code shape for agents"
date: 2026-10-31
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0001-initial-setup, ADR-0003-isolation-principle, working-with-agents, start-here]
---

# ADR-0005: instruction files, enforcement and code shape for agents

## Context

@DarkEB1 asked on 2026-10-31 for the repo to follow what Anthropic and experienced Claude Code
users recommend for agent-friendliness, with two constraints: nothing may add human involvement
to the dev process, and permissions are judged by Claude, not by people. The research (Anthropic's
best-practices and memory docs, the AGENTS.md standard, and practitioner write-ups) agrees on a
short set: write down only what the agent cannot derive from the repo; give it a pass/fail check;
enforce zero-exception rules with hooks and deny rules rather than prose; put folder-specific
guidance where it loads on demand; keep code small, typed and formatted by one tool. One audit of
the repo found that the root `CLAUDE.md` said "Read AGENTS.md" in words, which by the docs only
works if the model decides to open the file; the rules were not in context at session start.

The evidence is thinner than the advice. The one controlled study (1,650 runs, TypeScript only)
found that having an instruction file matters but its length and layout did not measurably change
adherence, and an ETH Zurich evaluation found context files raise cost without raising success on
average. Structural measures carry the weight; wording is cheap but unproven.

## Decision

- **Instruction files.** No `CLAUDE.md`. Claude Code reads `AGENTS.md` directly (v2.1.277 and
  later), which is also what Codex, Cursor and the other tools read. The root file is a router under
  100 lines: how to work (think before coding, least code, surgical changes, goal-driven), how to
  verify, the nine rules, autonomy, gotchas, and a read-first table. Folder rules live next to the
  code as `research/AGENTS.md`, `knowledge/AGENTS.md`, `src/quant/AGENTS.md` and `tools/AGENTS.md`,
  loaded when an agent opens a file there. Anything derivable from the repo (the map, the recipe
  list, the skills table) left the root file.
- **Enforcement without people.** `.claude/settings.json` is committed. Deny rules cover reading
  `.env`, force pushes and `--no-verify`. Command hooks (`scripts/hooks/`, stdlib python so they run
  on any host) block the same plus pushes to `main`, moves or deletions under `knowledge/`, hand
  edits to `.env*`, `uv.lock`, `knowledge/INDEX.md` and frozen experiments, and direct bucket writes
  to `raw/` or `curated/`. A PostToolUse hook formats every edited file when a formatter exists on
  the host and does nothing otherwise. A Stop hook asks a model whether a message that claims a
  change is done shows verification output, and sends Claude back once if not. No `ask` rules, no
  human-only skills: sessions run in auto mode and Claude's classifier judges each action.
- **Review by Claude.** `.claude/agents/reviewer.md` is a read-only subagent that checks a diff
  against the spec it was built from and ends with `verdict: merge` or `verdict: hold`. A skill
  runs it before merging its own PR; the CODEOWNERS data-layer block is unchanged.
- **Code shape.** Ruff enforces complexity 12, 14 branches, 50 statements and 10 arguments per
  function, and type annotations on public functions (tests, marimo cells and scaffolding
  templates excepted). `check_size.py` caps python files at 400 lines. Mypy runs in `just check`
  over the data layer, tools, scripts, skills and hub pages. Skill runners are named after their
  skill (`new_experiment.py`, not `run.py`), so names are unique to grep and to mypy.
- **Loops.** A task file may carry `prompt:` instead of runner args; the loop then runs
  `claude -p` in auto mode with `--max-turns` and an optional `--max-budget-usd` from the budget.
  Never `--bare`, so AGENTS.md, the skills and the hooks apply.

## Consequences

- An agent starting a session sees the rules without being told to read a file; `/context` lists
  `AGENTS.md`. Folder rules cost context only when relevant.
- The zero-exception rules no longer depend on the model remembering them. Everything else is a
  judgement call, as the docs recommend; the enforced set stays small on purpose.
- Hooks execute on the machine running Claude Code, not in the devcontainer. The guards need only
  python; the formatter hook is a no-op on a host without ruff, and pre-commit plus CI still catch
  formatting. `uv tool install ruff` on the host turns format-on-edit on.
- Auto mode cannot be set in project settings; it is the built-in default for interactive sessions
  and the loop passes `--permission-mode auto` explicitly. A person who prefers manual mode gets
  prompts, which is their choice, not the repo's.
- `/doctor prompt-audit` is the periodic check that the instruction files still agree with the
  repo; CONTRIBUTING names it.

## Alternatives considered

- Keep `CLAUDE.md` with an `@AGENTS.md` import: works in every version, but per-folder files then
  load only for `CLAUDE.md` nesting, and Windows checkouts cannot use the symlink form. Rejected
  for a repo that is already on a current version.
- `.claude/rules/` with `paths:` instead of nested `AGENTS.md`: a more robust trigger (reads,
  writes and `cat` all count) but Claude-only. Rejected to keep one format for every agent.
- `disable-model-invocation: true` on the side-effect skills, as the docs suggest for releases:
  rejected because it makes a person the only one who can start them.
- A prompt hook on every Bash call: a model call per command adds latency to all work; the
  classifier in auto mode already judges each action. Rejected; the Stop hook is once per turn.
- A Stop hook that runs `just check` itself: slow, host-bound and duplicated by pre-commit and CI.
