---
id: 2026-11-22-weekly-call-minutes
type: agent-log
title: "Record the minutes of the weekly updates and goals call"
date: 2026-11-22
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [2026-11-22-weekly-updates-and-goals]
---

# Record the minutes of the weekly updates and goals call

## Task

@DarkEB1 pasted the notes of the weekly call into Claude Code and asked for them to be written up
and pushed, using the meeting-notes skill.

## Decisions with justification

- Meeting date 2026-11-22: the notes carry no date and were pasted on that day. Assumed, not
  confirmed.
- First names for Eleonora and Eduardo, with a visible `@TODO-owner` on their actions: neither has
  a handle in `team.yaml`, and the 2026-11-15 minutes set that precedent. Nick and Lucas carry
  their handles.
- People outside the group are not named, and the firm Eduardo's contact works at is left out:
  the repository is public and the skill allows no personal data beyond handles. The 2026-11-15
  precedent covers members' first names only. They are "the industry contact" and "a second
  contact"; the first draft named them and the reviewer subagent caught it.
- The notes do not say who sends the tips document, so that action has no owner.
- "Goals for next week" became actions dated 2026-11-29, one week after the call. The two items
  with no stated timing (the calls with the two contacts, the tips document) keep `TODO-date`.
- No ADR. The LLP line is a direction to investigate, with nothing committed and no cost yet, so
  it is `(minor)`. An ADR is due when the structure is chosen.
- "UBS strat" and "IB" are kept as written; the notes do not say what either stands for.
- The script's related links pointed at unrelated agent-log entries and were replaced by the
  previous meeting.
- No todo-board cards: not asked for, and half the owners have no handle.

## Summary

Wrote the meeting file from the pasted notes and regenerated `knowledge/INDEX.md`. `just search`
returned the 2026-11-15 meeting for the backtesting framework and nothing for the LLP, Kelly sizing
and Bloomberg phrasings tried. The 2026-11-15 meeting does cover the Kelly sizing cap and holds the
open legal set-up action this call continues; it is linked. No ADR covers any of the topics. Needs
a human: handles for Eleonora and Eduardo, an owner for the calls with the two contacts and for the
tips document, and an answer to who is involved in the project.

## Files touched

- [knowledge/meetings/2026-11-22-weekly-updates-and-goals.md](../meetings/2026-11-22-weekly-updates-and-goals.md)
- [knowledge/INDEX.md](../INDEX.md)
- [knowledge/agent-log/2026-11-22-weekly-call-minutes.md](2026-11-22-weekly-call-minutes.md)

## Files relied on

- [.claude/skills/meeting-notes/SKILL.md](../../.claude/skills/meeting-notes/SKILL.md)
- [.claude/skills/meeting-notes/meeting_notes.py](../../.claude/skills/meeting-notes/meeting_notes.py)
- [knowledge/templates/meeting.md](../templates/meeting.md)
- [knowledge/templates/agent-log.md](../templates/agent-log.md)
- [knowledge/AGENTS.md](../AGENTS.md)
- [knowledge/context/team.yaml](../context/team.yaml)
- [knowledge/context/tags.md](../context/tags.md)
- [knowledge/meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md](../meetings/2026-11-15-fund-setup-trade-ideas-and-structure.md)
- [knowledge/agent-log/2026-11-15-fund-setup-meeting-minutes.md](2026-11-15-fund-setup-meeting-minutes.md)

## PR

https://github.com/DarkEB1/semi-systematic/pull/16
