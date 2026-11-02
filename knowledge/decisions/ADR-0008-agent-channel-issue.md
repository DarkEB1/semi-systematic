---
id: ADR-0008-agent-channel-issue
type: decision
title: "ADR-0008: one pinned issue is the channel between teammates' agents"
date: 2026-11-02
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0005-llm-friendly-repo, ADR-0007-todos-live-on-their-own-branch, working-with-agents]
---

# ADR-0008: one pinned issue is the channel between teammates' agents

## Context

Each teammate runs their own agents, and nothing lets one teammate's agent tell another's that a
PR touches their project, that a dataset they use changed, or that it needs an answer. Issues and
PRs are already the only channels (no chat notifications), but a new issue per message scatters
the conversation and nobody's agent knows which issues to read. On 2026-11-02 @DarkEB1 asked for a
pinned issue where the agents talk to each other and tag a teammate when something is needed from
them.

## Decision

- Issue [#2](https://github.com/DarkEB1/semi-systematic/issues/2), pinned, is the agent channel.
  Its body holds the message format; each comment is one message with `from`, `to` (a handle or
  `all`), `needs` (`nothing`, `answer`, `review` or `action`) and `re` (a link).
- An agent reads it at the start of a session with `gh issue view 2 --comments` and acts on
  messages to its teammate's handle or `all` that have no `done:` reply.
- `@handle` is written only when a person must act; agent-to-agent messages name the handle bare,
  so GitHub notifies people only when they are needed.
- Work items stay on the board, bugs and data problems get their own issue, decisions stay ADRs or
  minutes lines. The channel points to them and never replaces them.

## Consequences

- No new code or dependency: `gh` is already on the host and in the container.
- One long thread grows forever. When it gets unwieldy, a new pinned issue replaces it and this ADR
  is superseded with the new number.
- Reading the channel is a convention in `AGENTS.md`, not a hook, so an agent that skips it misses
  messages until its teammate is tagged.

## Alternatives considered

- A file on the `todos` branch or under `knowledge/`: needs a commit per message and gives no
  notification when a person is needed.
- GitHub Discussions: not enabled on the repo, and `gh` has no first-class discussion commands.
- A SessionStart hook that prints unread messages: more code than the problem needs today; worth
  adding if agents are seen skipping the channel.
