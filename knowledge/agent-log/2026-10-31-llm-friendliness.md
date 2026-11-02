---
id: 2026-10-31-llm-friendliness
type: agent-log
title: "Make the repo agent-friendly: AGENTS.md router, hooks, reviewer, code shape"
date: 2026-10-31
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0005-llm-friendly-repo, 2026-10-30-tools-library]
---

# Make the repo agent-friendly: AGENTS.md router, hooks, reviewer, code shape

## Task

Asked by @DarkEB1 on 2026-10-31: research what Anthropic and experienced Claude Code users do for
"LLM friendliness" (short simple code, a short rules file, enforcement) and propose it; then
"I want all to be implemented, but I want it all to not interfere with the dev process, or add
more human involvement, claude should just evaluate claude for permissions". One-off change on the
open scaffold branch, no loop, no budget.

## Decisions with justification

- Deleted `CLAUDE.md` instead of importing `AGENTS.md` from it: the sentence "Read AGENTS.md" was
  not loading the rules (the docs say Claude only sees the file if it decides to open it), the host
  runs Claude Code 2.1.314 which reads `AGENTS.md` directly, and nested `AGENTS.md` files load on
  demand only in that mode. `AGENTS.md` is the open format every other agent reads too.
- Cut the root file from the map, the data-layer paragraph, the skills table and the recipe list:
  all derivable from the repo (`just`, skill frontmatter, `start-here`). Kept the nine rules with
  their numbering because other files cite them; the frontmatter detail moved to `knowledge/AGENTS.md`.
- Dropped two items from my own proposal because they add a human step: no `ask` rule on
  `git push`, and no `disable-model-invocation` on the side-effect skills. Replaced with deny rules
  and command hooks for the zero-exception set, and auto mode for the rest.
- No prompt hook on every Bash call (latency on every command; the auto-mode classifier already
  judges actions). One Stop prompt hook that only fires back when a message claims a finished change
  with no verification output.
- Hook scripts are stdlib python with a `run.sh` that finds `python3` or `python`: hooks run on the
  host, which here has python but no uv, jq or ruff. The formatter hook is therefore a no-op on this
  machine and documented as such; pre-commit and CI still enforce formatting.
- Renamed the seven skill runners from `run.py` to `<skill>.py`: unique names for grep, and mypy
  refused to check two modules both named `run`.
- Split `quant/data/__init__.py` by moving the schema contract and partition helpers out, not the
  settings or write path: tests monkeypatch `data.settings` on the package, so the functions that
  call it had to stay in the package module.
- Shape caps set where the repo already stood plus a small margin (complexity 12, statements 50,
  branches 14, args 10, 400 lines); four functions were over and were split rather than exempted.
- `$comment` left out of `.claude/settings.json` (unknown keys risk a settings warning); the
  explanation is in CONTRIBUTING and ADR-0005.

## Summary

Done: root `AGENTS.md` as a router with the four working rules; per-folder `AGENTS.md` in
`research/`, `knowledge/`, `src/quant/`, `tools/`; `.claude/settings.json` with deny rules, allow
list, three command hooks and a Stop prompt hook; `scripts/hooks/` with tests; `.claude/agents/reviewer.md`;
ruff complexity, size and annotation caps; mypy in `just check`; `check_size.py` line cap; runners
renamed and every reference updated; loop `prompt:` mode with `--max-turns` and `--max-usd`;
docs (start-here, working-with-agents, CONTRIBUTING, glossary, prompts preamble, README) and
ADR-0005. Verified in the devcontainer: `just check` (incl. mypy), `just test`, `just eval`,
`just where --check`, `just index`.

Not done, needs nobody: nothing. Needs @DarkEB1 only to read the PR. The Stop hook and the Bash
guard were exercised by unit tests and by piping sample payloads; the first real session on this
branch is the end-to-end check (`/context` should list `AGENTS.md`, `/hooks` the four hooks).

## Files touched

- [AGENTS.md](../../AGENTS.md), [research/AGENTS.md](../../research/AGENTS.md), [knowledge/AGENTS.md](../AGENTS.md), [src/quant/AGENTS.md](../../src/quant/AGENTS.md), [tools/AGENTS.md](../../tools/AGENTS.md); `CLAUDE.md` deleted
- [.claude/settings.json](../../.claude/settings.json), [.claude/agents/reviewer.md](../../.claude/agents/reviewer.md), [scripts/hooks/run.sh](../../scripts/hooks/run.sh), [guard_bash.py](../../scripts/hooks/guard_bash.py), [guard_edit.py](../../scripts/hooks/guard_edit.py), [format_file.py](../../scripts/hooks/format_file.py), [tests/test_hooks.py](../../tests/test_hooks.py)
- [pyproject.toml](../../pyproject.toml), [uv.lock](../../uv.lock), [justfile](../../justfile), [scripts/check_size.py](../../scripts/check_size.py), [scripts/check_frontmatter.py](../../scripts/check_frontmatter.py), [scripts/check_isolation.py](../../scripts/check_isolation.py), [scripts/run_evals.py](../../scripts/run_evals.py)
- [scripts/loop.py](../../scripts/loop.py), [scripts/task.py](../../scripts/task.py), [tests/test_loop_prompt.py](../../tests/test_loop_prompt.py)
- [src/quant/data/__init__.py](../../src/quant/data/__init__.py), [src/quant/data/schema.py](../../src/quant/data/schema.py), [src/quant/data/keys.py](../../src/quant/data/keys.py), [src/quant/data/_paths.py](../../src/quant/data/_paths.py)
- skill runners renamed: [new_experiment.py](../../.claude/skills/new-experiment/new_experiment.py) (+ [template_run.py](../../.claude/skills/new-experiment/template_run.py)), [pull_data.py](../../.claude/skills/pull-data/pull_data.py), [refresh_data.py](../../.claude/skills/refresh-data/refresh_data.py), [promote_dataset.py](../../.claude/skills/promote-dataset/promote_dataset.py), [meeting_notes.py](../../.claude/skills/meeting-notes/meeting_notes.py), [build_index.py](../../.claude/skills/build-index/build_index.py), [repo_structure.py](../../.claude/skills/repo-structure/repo_structure.py); their `SKILL.md` files
- [dashboards/hub/pages](../../dashboards/hub/README.md) (render signatures), [tools/brain/src/brain/build.py](../../tools/brain/src/brain/build.py)
- [ADR-0005](../decisions/ADR-0005-llm-friendly-repo.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [start-here](../context/start-here.md), [working-with-agents](../context/working-with-agents.md), [glossary](../context/glossary.md), [workflow](../context/workflow.md), [README.md](../../README.md), [ai/prompts/_preamble.md](../../ai/prompts/_preamble.md), [ai/prompts/repo-structure.md](../../ai/prompts/repo-structure.md), [ai/evals/README.md](../../ai/evals/README.md), [tools/README.md](../../tools/README.md), [tools/brain/README.md](../../tools/brain/README.md), [ADR-0001](../decisions/ADR-0001-initial-setup.md), [ADR-0002](../decisions/ADR-0002-tools-are-isolated-packages.md), [2026-10-29-initial-scaffold](2026-10-29-initial-scaffold.md), [2026-10-30-tools-library](2026-10-30-tools-library.md), [.gitignore](../../.gitignore)

## Files relied on

- Anthropic docs: [best practices](https://code.claude.com/docs/en/best-practices), [memory and AGENTS.md](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks-guide), [subagents](https://code.claude.com/docs/en/sub-agents), [permission modes](https://code.claude.com/docs/en/permission-modes)
- [AGENTS.md standard](https://agents.md/), [Marmelab: agent experience](https://marmelab.com/blog/2026/01/21/agent-experience.html), [Clean code for AI agents](https://akitaonrails.com/en/2026/04/20/clean-code-for-ai-agents/), [Dunlop: CLAUDE.md evidence](https://www.alexdunlop.com/writing/claude-md-best-practices)
- [ADR-0001](../decisions/ADR-0001-initial-setup.md), [ADR-0003](../decisions/ADR-0003-isolation-principle.md), the previous `AGENTS.md` (git history before this commit)

## PR

Same branch as the scaffold: `chore/initial-scaffold` -> `main`, PR "chore: initial scaffold".
Not merged by the agent.
