---
id: 2026-11-02-host-agents-and-failing-hooks
type: agent-log
title: "Agents on the host run recipes through in-container.sh; hooks fail closed"
date: 2026-11-02
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [2026-11-02-agent-channel-enforced, ADR-0005-llm-friendly-repo, working-with-agents]
---

# Agents on the host run recipes through in-container.sh; hooks fail closed

## Task

@DarkEB1 asked to fix the docs and the hooks after two findings: Codex stopped because the docs
say an assistant without `just` is "not in the container, stop", while the devcontainer installs
neither Claude Code nor Codex (`working-with-agents.md` claimed Claude Code was on its path); and
every hook had been failing open on this Windows host because `run.sh` picked the Microsoft Store
`python3` stub. No skill; interactive session.

## Decisions with justification

- Fixed the docs to match the container, not the container to match the docs: assistants run on
  the host (where `gh` credentials and the hooks are), recipes run in the container.
- Added `scripts/in-container.sh` instead of writing the `docker run` line into the docs: it was the
  third use of that command (this session, the project memory, Codex), and the documented
  `devcontainer exec` route needs a CLI this host does not have. It prefers that CLI when present.
- `run.sh` fails closed (exit 2) when no Python runs or a hook exits with anything but 0 or 2: the
  hooks enforce the zero-exception rules, so a silent pass is the worse failure. The channel guard
  still fails open on `gh` errors by design, inside Python. Treated as a bug fix, not a new
  decision: ADR-0005 meant the guards to enforce.
- Left the `.todos/` worktree's copies alone: that branch is never merged (ADR-0007).

## Summary

Docs: `AGENTS.md` (where you are, gotchas), `README.md`, `CONTRIBUTING.md`,
`working-with-agents.md`, `ai/prompts/README.md`, and the preamble in `_preamble.md` and all seven
prompts now say: on the host, read and edit directly, run recipes and commits through
`sh scripts/in-container.sh`; stop only on a `MISSING` line. Hooks: `run.sh` fails closed, with
four tests. `sh scripts/in-container.sh just onboard` from the host printed `23 ok, 0 missing`.
Nothing needs a human.

## Files touched

- [scripts/in-container.sh](../../scripts/in-container.sh)
- [scripts/hooks/run.sh](../../scripts/hooks/run.sh)
- [tests/test_hooks.py](../../tests/test_hooks.py)
- [AGENTS.md](../../AGENTS.md)
- [README.md](../../README.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [knowledge/context/working-with-agents.md](../context/working-with-agents.md)
- [ai/prompts/README.md](../../ai/prompts/README.md)
- [ai/prompts/_preamble.md](../../ai/prompts/_preamble.md)
- [ai/prompts/build-index.md](../../ai/prompts/build-index.md)
- [ai/prompts/meeting-notes.md](../../ai/prompts/meeting-notes.md)
- [ai/prompts/new-experiment.md](../../ai/prompts/new-experiment.md)
- [ai/prompts/promote-dataset.md](../../ai/prompts/promote-dataset.md)
- [ai/prompts/pull-data.md](../../ai/prompts/pull-data.md)
- [ai/prompts/refresh-data.md](../../ai/prompts/refresh-data.md)
- [ai/prompts/repo-structure.md](../../ai/prompts/repo-structure.md)
- [knowledge/agent-log/2026-11-02-host-agents-and-failing-hooks.md](2026-11-02-host-agents-and-failing-hooks.md)

## Files relied on

- [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)
- [.devcontainer/Dockerfile](../../.devcontainer/Dockerfile)
- [knowledge/decisions/ADR-0005-llm-friendly-repo.md](../decisions/ADR-0005-llm-friendly-repo.md)
- [knowledge/decisions/ADR-0007-todos-live-on-their-own-branch.md](../decisions/ADR-0007-todos-live-on-their-own-branch.md)

## PR

Committed to the open scaffold PR [#1](https://github.com/DarkEB1/semi-systematic/pull/1).
