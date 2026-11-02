---
id: ADR-0009-agent-channel-enforced
type: decision
title: "ADR-0009: hooks enforce the agent channel: inbox at session start, tag before touching others' work"
date: 2026-11-02
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0008-agent-channel-issue, ADR-0005-llm-friendly-repo, working-with-agents]
---

# ADR-0009: hooks enforce the agent channel: inbox at session start, tag before touching others' work

## Context

ADR-0008 made pinned issue #2 the channel between teammates' agents, enforced only by a line in
`AGENTS.md`. The same day @DarkEB1 asked for it to be enforceable: every session should start by
checking for tags there and propose resolving them before anything else, and an agent that
proposes touching another teammate's work, or needs to ask them something, should do it in the
channel with a tag.

## Decision

- Issue #2, its message format and the `@handle`-only-when-a-person-must-act rule stand as in
  ADR-0008.
- A SessionStart hook (`scripts/hooks/agent_channel.py inbox`) reads #2 with `gh` and lists the
  comments by others that tag the current GitHub user or name them (or `all`) in `to:`, minus those
  a later `done:` comment links to. Its output tells the agent to show them and propose how to
  resolve each before doing anything else.
- A PreToolUse hook on Edit/Write (`agent_channel.py guard`) finds the owner of the target: the
  file's own `owner:` frontmatter, else the nearest `README.md` with one (a research project, a
  tool). If the owner is not the current GitHub user, the edit is blocked until a comment in #2 by
  that user tags `@owner` and names the owned path.
- Handles are GitHub logins, as `team.yaml` already assumes.
- Questions to a teammate go to #2 with a tag; that part is a rule in `AGENTS.md`, since no hook
  can tell a question from other work.

## Consequences

- Supersedes ADR-0008's "a convention, not a hook" consequence; ADR-0008 is marked superseded.
- Every session costs two `gh` calls at start, and an edit to an owned file costs one or two more.
  Edits to unowned files cost nothing.
- The hooks fail open: with no `gh`, no login or no network, the start hook tells the agent to read
  #2 by hand and the edit hook allows the edit. Edits made through the shell (`sed`, scripts) are
  not seen by the edit hook.
- The guard asks for a tagged proposal, not an approval: the agent may proceed once it has told the
  owner. Waiting for a reply would put a person in the loop, which ADR-0005 rules out.
- With one handle in `team.yaml` today the guard never fires; it starts mattering with the second.

## Alternatives considered

- Keep the `AGENTS.md` line only (ADR-0008): already in place and judged not enough.
- Block until the owner replies: a person in the loop on every cross-owner edit.
- Use CODEOWNERS for ownership: every line there is one handle today and it maps folders, not
  projects; the `owner:` frontmatter is already per file and checked by `just check`.
