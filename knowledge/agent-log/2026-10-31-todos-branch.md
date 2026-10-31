---
id: 2026-10-31-todos-branch
type: agent-log
title: "Board on its own branch: just todo syncs through the todos worktree"
date: 2026-10-31
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0007-todos-live-on-their-own-branch, 2026-10-31-team-board]
---

# Board on its own branch: just todo syncs through the todos worktree

## Task

Asked by @DarkEB1 on 2026-10-31: "can we make it so that the todo is always synced (as in no
matter what branch todo stuff is on, it always goes to main, and main todo always syncs with
branches?". Follow-up to the team board added earlier the same day.

## Decisions with justification

- Cards moved off feature branches onto one unprotected `todos` branch, checked out as a worktree
  at `.todos/`, instead of being pushed to `main`: `main` requires a PR and a green `ci` run
  (enforced for admins, linear history), so "always goes to main" would mean a PR and a CI run per
  card move; a dedicated branch gives the same single source of truth in one fetch and one push.
  The user's goal (one board, branch-independent) is met; the literal "to main" is not, and the
  reason is in ADR-0007.
- The branch was created from the scaffold branch head rather than `main`, because pre-commit
  hooks run inside the worktree too and `main` does not yet know the `todo` type.
- The container can fetch the public repo but cannot push through plain `docker run` (no
  credentials); VS Code's devcontainer forwards them. The recipe therefore never fails on a push:
  it keeps the commit and `--sync` retries. The bootstrap push of the `todos` branch was done from
  the host.
- `knowledge/todos/` was removed from the scaffold branch and the two cards became the first
  commit of `todos`, same paths and contents. That is a move of knowledge files, done under an
  ADR that changes the convention, not a rename.
- ADR-0006 is marked superseded per the ADR rule, although it is a day old and unmerged.

## Summary

Done: `scripts/todo.py` rewritten around the worktree (fetch, validate, commit, push, `--sync`),
board page and `just dashboard` read and sync the worktree, `.todos/` gitignored, ADR-0007,
ADR-0006 superseded, docs and template updated, tests rewritten with a fake worktree and a
recorded git. Verified in the devcontainer with `just check`, `just test`, `just eval`,
`just where --check`, and `just todo --list` against the real branch.

## Files touched

- [scripts/todo.py](../../scripts/todo.py), [tests/test_todo.py](../../tests/test_todo.py), [justfile](../../justfile), [.gitignore](../../.gitignore)
- [dashboards/hub/pages/board.py](../../dashboards/hub/pages/board.py), [dashboards/hub/README.md](../../dashboards/hub/README.md)
- [ADR-0007](../decisions/ADR-0007-todos-live-on-their-own-branch.md), [ADR-0006](../decisions/ADR-0006-todos-are-files.md), [knowledge/templates/todo.md](../templates/todo.md), [knowledge/AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [start-here](../context/start-here.md), [.claude/skills/repo-structure/repo_structure.py](../../.claude/skills/repo-structure/repo_structure.py), [2026-10-31-team-board](2026-10-31-team-board.md)
- branch `todos`: `knowledge/todos/2026-10-31-decide-em-rates-and-credit-instruments.md`, `knowledge/todos/2026-10-31-build-the-backtesting-framework-tools-ba.md` (moved from this branch)

## Files relied on

- [ADR-0006](../decisions/ADR-0006-todos-are-files.md), [knowledge/AGENTS.md](../AGENTS.md), [scripts/check_frontmatter.py](../../scripts/check_frontmatter.py), [.github/workflows/ci.yml](../../.github/workflows/ci.yml), the branch protection of `main` (read with `gh api`)

## PR

Same branch as the scaffold: `chore/initial-scaffold` -> `main`, PR "chore: initial scaffold".
Not merged by the agent.
