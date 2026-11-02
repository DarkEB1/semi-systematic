---
id: 2026-11-02-merge-readiness-and-setup
type: agent-log
title: "Merge readiness for #1 and #3, and a per-person setup checklist"
date: 2026-11-02
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [setup, start-here]
---

# Merge readiness for #1 and #3, and a per-person setup checklist

## Task

@DarkEB1 asked whether PRs #1 and #3 set up what the team needs to work here full-time, then to do
what is needed to merge and to write one setup file for each person. No skill.

## Decisions with justification

- Ran the `reviewer` subagent over #1 and #3 together before any merge. It returned `verdict: hold`
  (Yahoo summer-time dates, `.env` guard bypass); both were fixed on #3, recorded in
  `2026-11-02-review-fixes` (on [#3](https://github.com/DarkEB1/semi-systematic/pull/3)), and the re-review returned `verdict: merge`.
- Did not merge: the auto-mode classifier refused `gh pr merge` twice ("merge without review"),
  also after the reviewer's merge verdict. Merging is left to @DarkEB1 as data-layer owner.
- The setup checklist is a new context file rather than a longer README: the README keeps its
  paste-into-an-assistant prompt and links the checklist, which adds what changed today (a real
  Python for the hooks, `in-container.sh`, the agent channel, Codex not running the hooks).
- Committed to #1 rather than its own PR because `main` does not have the scaffold yet.
- Corrected an earlier claim: `backup.yml` skips with a notice when the B2 secrets are unset; it does
  not fail. There are simply no backups until the secrets exist.

## Summary

Done: review, fixes on #3, a board card for the deferred data-health fallback, and
[setup.md](../context/setup.md) linked from the README. Needs a human: merge #3 into
`chore/initial-scaffold`, then squash-merge #1 into `main`; after that, run `ingest.yml` once by hand
and confirm the catalog views load; add the B2 secrets for backups; each teammate follows setup.md.

## Files touched

- [knowledge/context/setup.md](../context/setup.md)
- [README.md](../../README.md)
- [knowledge/agent-log/2026-11-02-merge-readiness-and-setup.md](2026-11-02-merge-readiness-and-setup.md)

## Files relied on

- [.env.example](../../.env.example)
- [scripts/onboard.py](../../scripts/onboard.py)
- [scripts/in-container.sh](../../scripts/in-container.sh)
- [.github/workflows/backup.yml](../../.github/workflows/backup.yml)
- [knowledge/context/working-with-agents.md](../context/working-with-agents.md)
- [knowledge/context/team.yaml](../context/team.yaml)

## PR

Committed to [#1](https://github.com/DarkEB1/semi-systematic/pull/1); the fixes are in
[#3](https://github.com/DarkEB1/semi-systematic/pull/3).
