---
id: 2026-11-02-agent-channel
type: agent-log
title: "Pinned issue as the channel between teammates' agents"
date: 2026-11-02
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0008-agent-channel-issue, working-with-agents]
---

# Pinned issue as the channel between teammates' agents

## Task

@DarkEB1 asked for a pinned issue where each teammate's agents talk to each other and tag a
teammate when something is needed from them. No skill; interactive session.

## Decisions with justification

- One pinned issue, one comment per message: issues are already the only channel, and a single
  known number is something every agent can be told to read. Ruled out a file on a branch (a
  commit per message, no notifications) and Discussions (not enabled, weak `gh` support).
- `@handle` only when a person must act; agent-to-agent messages name the handle bare: this is
  what keeps "tag a teammate when something is needed" meaningful instead of noise.
- A convention line in `AGENTS.md` rather than a SessionStart hook: least code; the ADR names the
  hook as the follow-up if agents skip the channel.
- Recorded as ADR-0008 because it is a new convention (rule 4).

## Summary

Created and pinned issue #2 with the message format, wrote ADR-0008, and added the convention to
`AGENTS.md` and `working-with-agents.md`. Nothing needs a human.

## Files touched

- [knowledge/decisions/ADR-0008-agent-channel-issue.md](../decisions/ADR-0008-agent-channel-issue.md)
- [AGENTS.md](../../AGENTS.md)
- [knowledge/context/working-with-agents.md](../context/working-with-agents.md)
- [knowledge/agent-log/2026-11-02-agent-channel.md](2026-11-02-agent-channel.md)
- GitHub issue [#2](https://github.com/DarkEB1/semi-systematic/issues/2) (created and pinned)

## Files relied on

- [knowledge/context/working-with-agents.md](../context/working-with-agents.md)
- [knowledge/context/team.yaml](../context/team.yaml)
- [knowledge/decisions/ADR-0007-todos-live-on-their-own-branch.md](../decisions/ADR-0007-todos-live-on-their-own-branch.md)
- [knowledge/templates/agent-log.md](../templates/agent-log.md)
- [AGENTS.md](../../AGENTS.md)

## PR

Committed to the open scaffold PR [#1](https://github.com/DarkEB1/semi-systematic/pull/1).
