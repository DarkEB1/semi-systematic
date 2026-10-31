---
name: meeting-notes
description: Turn a pasted transcript or bullet list into a meeting file in template shape, apply the ADR test to every decision (draft an ADR for each that passes, mark the rest minor), checkbox the actions with owners and dates, link related files, and store only a link to the recording, never the transcript.
---

# meeting-notes

Deterministic part: `.claude/skills/meeting-notes/meeting_notes.py`, exposed as `just meeting DATE TITLE`.
It takes bullets on stdin (or `--input file`), writes the meeting file and ADR drafts, and never
stores the transcript. Your job is to turn a transcript into those bullets and to review the ADR
test's verdicts. Eval fixture: `ai/evals/meeting-notes/`.

## Inputs

- Date, title, attendees, the recording link (`--recording URL`), and the transcript or notes
  pasted by the human. The transcript stays in the chat; nothing of it is written to the repo
  except what you distil into bullets.
- Bullet grammar: `agenda: ...`, `decision: ...`, `action: ... @handle YYYY-MM-DD`; anything
  else becomes a Notes bullet.

## Steps

1. `just search "<topic>"` for each decision topic; an existing ADR may already cover it, in
   which case the decision line links that ADR instead of drafting a new one.
2. Distil the transcript into bullets (under ~400 words of notes; split topics into separate
   `##` sections afterwards if needed). Every decision becomes a `decision:` line; every
   commitment becomes an `action:` line with an owner handle and an ISO date.
3. `just meeting <date> "<title>" --recording <url> --attendees a,b < bullets.txt`. The ADR test
   (a decision becomes an ADR when it changes a convention, a dependency, a data source, a method
   others will reuse, or costs money) is applied by keywords; read each verdict and override by
   editing: move a wrongly-minor decision into a new ADR from the template, or delete a draft ADR
   and mark the line `(minor)`.
4. Fill each drafted ADR's Context, Consequences and Alternatives from the discussion; set
   `status: accepted` only if the meeting actually decided. If a decision supersedes an older ADR,
   set `status: superseded` on the old one in the same PR and link both ways.
5. Add tags from `just tags` to the meeting and ADR files; if none fits, append a new tag with a
   definition to `knowledge/context/tags.md` in the same PR.
6. Write the agent-log entry, then open the PR.

## Checks before opening the PR

- `just check` passes: in particular every Decisions line links an ADR or ends with `(minor)`,
  owners are in `team.yaml`, tags are in `tags.md`, ids equal filenames.
- No verbatim transcript, no quotes longer than a line, no personal data beyond handles.
- Actions have an owner and a date, or say `TODO-owner` / `TODO-date` visibly.

## Done when

- The meeting file and any ADRs are merged (the skill may merge if nothing under CODEOWNERS
  changed), `just index` has run, and `just search "<title>"` returns the meeting.
