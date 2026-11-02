---
id: 2026-11-02-agent-channel-enforced
type: agent-log
title: "Hooks enforce the agent channel: inbox at session start, tag before touching others' work"
date: 2026-11-02
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0009-agent-channel-enforced, ADR-0008-agent-channel-issue, 2026-11-02-agent-channel]
---

# Hooks enforce the agent channel: inbox at session start, tag before touching others' work

## Task

@DarkEB1 asked to make the agent channel (issue #2) enforceable: every session starts by checking
for tags there and proposes resolving them before anything else, and an agent that proposes
touching another teammate's work or needs to ask them something does it in the channel with a tag.
No skill; interactive session, follow-up to [2026-11-02-agent-channel](2026-11-02-agent-channel.md).

## Decisions with justification

- One stdlib script, two modes (`inbox`, `guard`), because `python -I` cannot import a sibling
  module; `run.sh` now passes extra arguments through.
- Ownership from `owner:` frontmatter (file, else nearest README), not CODEOWNERS: it is per
  project and already validated by `just check`.
- The guard requires a tagged proposal in #2, not the owner's reply: a reply would put a person in
  the loop.
- Fail open when `gh` is unavailable: a missing login should not stop all work; the start hook
  then tells the agent to read #2 by hand.
- A new ADR-0009 superseding ADR-0008, per rule 4.

## Summary

Wrote the hook script and its tests, updated `run.sh`, `AGENTS.md`, `working-with-agents.md`, the
issue #2 body, ADR-0008 (superseded) and ADR-0009. **Needs a human:** the auto-mode classifier
refused the agent's edit to `.claude/settings.json` (self-modification), so the two hook entries
and the `gh issue view*` allow rule must be added by @DarkEB1 or with their explicit go-ahead.
Until then the script exists but does not run.

## Files touched

- [scripts/hooks/agent_channel.py](../../scripts/hooks/agent_channel.py)
- [scripts/hooks/run.sh](../../scripts/hooks/run.sh)
- [tests/test_hooks.py](../../tests/test_hooks.py)
- [AGENTS.md](../../AGENTS.md)
- [knowledge/context/working-with-agents.md](../context/working-with-agents.md)
- [knowledge/decisions/ADR-0008-agent-channel-issue.md](../decisions/ADR-0008-agent-channel-issue.md)
- [knowledge/decisions/ADR-0009-agent-channel-enforced.md](../decisions/ADR-0009-agent-channel-enforced.md)
- [knowledge/agent-log/2026-11-02-agent-channel-enforced.md](2026-11-02-agent-channel-enforced.md)
- GitHub issue [#2](https://github.com/DarkEB1/semi-systematic/issues/2) (body updated)

## Files relied on

- [scripts/hooks/guard_edit.py](../../scripts/hooks/guard_edit.py)
- [tests/test_hooks.py](../../tests/test_hooks.py)
- [.claude/settings.json](../../.claude/settings.json)
- [.github/CODEOWNERS](../../.github/CODEOWNERS)
- [research/demo/README.md](../../research/demo/README.md)
- [knowledge/context/team.yaml](../context/team.yaml)

## PR

Committed to the open scaffold PR [#1](https://github.com/DarkEB1/semi-systematic/pull/1).
