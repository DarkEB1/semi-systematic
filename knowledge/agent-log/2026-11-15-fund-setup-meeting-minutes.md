---
id: 2026-11-15-fund-setup-meeting-minutes
type: agent-log
title: "Record the minutes of the fund setup, trade ideas and structure meeting"
date: 2026-11-15
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [2026-11-15-fund-setup-trade-ideas-and-structure]
---

# Record the minutes of the fund setup, trade ideas and structure meeting

## Task

@DarkEB1 pasted the minutes of the meeting into Claude Code and asked for them to be recorded with
the meeting-notes skill, plus a link and a todo list to share with the group.

## Decisions with justification

- First names only, no surnames: the repository is public and the skill allows no personal data
  beyond handles. Only @DarkEB1 has a handle, so action owners are first names with a visible
  `@TODO-owner`, and dates are `TODO-date` because none were set.
- No ADR. The skill's keyword test drafted one for the fund name; that draft was deleted and the
  line marked `(minor)`, since a name changes no convention, dependency, data source, method or
  cost. The pod structure is a direction, not a settled rule: voting and limits are still open, so
  it is `(minor)` with a note that the ADR follows the risk + voting proposal.
- Added one action the pasted todo list did not have, "Auditable trade records, NAV and PnL", since
  the notes call it a precondition and nobody holds it. It is marked unclaimed.
- No todo-board cards: card owners must be handles in `team.yaml`, and the assignees have none yet.
- @DarkEB1 confirmed in the session that first names may be published in this public repo, that
  the meeting took place on 2026-11-15, that they are the Nick of the minutes, and that Alec and
  Eduardo were assigned in their absence.
- A clause about members' personal circumstances was removed from the fund-structure action after
  review: it is personal data the action does not need.

## Summary

Wrote the meeting file from the pasted minutes and regenerated `knowledge/INDEX.md`. Needs a human:
handles for the members in `team.yaml`, then owners and dates on the actions. `just search` returned
no results for any of the meeting topics before the file was written.

## Files touched

- [knowledge/meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md](../meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md)
- [knowledge/INDEX.md](../INDEX.md)
- [knowledge/agent-log/2026-11-15-fund-setup-meeting-minutes.md](2026-11-15-fund-setup-meeting-minutes.md)

## Files relied on

- [.claude/skills/meeting-notes/SKILL.md](../../.claude/skills/meeting-notes/SKILL.md)
- [.claude/skills/meeting-notes/meeting_notes.py](../../.claude/skills/meeting-notes/meeting_notes.py)
- [knowledge/templates/meeting.md](../templates/meeting.md)
- [knowledge/AGENTS.md](../AGENTS.md)
- [knowledge/context/team.yaml](../context/team.yaml)
- [knowledge/context/tags.md](../context/tags.md)
- [knowledge/meetings/2026-10-28-kickoff.md](../meetings/2026-10-28-kickoff.md)

## PR

https://github.com/DarkEB1/semi-systematic/pull/11
