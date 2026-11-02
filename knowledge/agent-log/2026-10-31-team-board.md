---
id: 2026-10-31-team-board
type: agent-log
title: "Team board: todos as files, a just recipe and a hub page"
date: 2026-10-31
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [ADR-0006-todos-are-files, 2026-10-31-llm-friendliness]
---

# Team board: todos as files, a just recipe and a hub page

## Task

Asked by @DarkEB1 on 2026-10-31: "Can we also add todo management for the team (a kanban) with
user ownership?" and then "can it be part of the dashboard? or what is the best way of doing
this". One-off change on the scaffold branch.

## Decisions with justification

- Files, not a service: a todo is `knowledge/todos/<date>-<slug>.md` of type `todo`, so ownership
  is the existing `owner` handle that `just check` already validates, and agents use the same
  recipe as people. GitHub Projects and an Obsidian kanban file were considered and rejected in
  ADR-0006 (outside the repo or unvalidated single file).
- The hub page is read-only, as `dashboards/hub/README.md` requires; `just todo <id> --move`
  changes the status line and nothing else, so no file under `knowledge/` is ever renamed.
- Statuses `todo` and `doing` were added to the checker's set; `done` already existed. `due` is a
  new optional frontmatter key, checked as an ISO date. The todo-specific checks live in their own
  function to keep `check_values` under the shape caps.
- The board page is not imported by a test: the isolation rule says the hub is imported by
  nothing, so `scripts/todo.py` carries the same `cards()` reader and the tests cover that.
- One real card was seeded from an open TODO line in `knowledge/context/universe.md`, so the
  board is not empty on first open.

## Summary

Done: template, `scripts/todo.py` with `just todo`, `dashboards/hub/pages/board.py` registered as
the sixth page with owner and status filters, checker and index support for the type, ADR-0006,
docs, tests. Verified in the devcontainer with `just check`, `just test`, `just eval` and
`just where --check`. Nothing left for a person except reading the PR.

## Files touched

- [knowledge/templates/todo.md](../templates/todo.md), `knowledge/todos/2026-10-31-decide-em-rates-and-credit-instruments.md` (since ADR-0007 on the `todos` branch)
- [scripts/todo.py](../../scripts/todo.py), [tests/test_todo.py](../../tests/test_todo.py), [justfile](../../justfile)
- [dashboards/hub/pages/board.py](../../dashboards/hub/pages/board.py), [dashboards/hub/app.py](../../dashboards/hub/app.py), [dashboards/hub/README.md](../../dashboards/hub/README.md)
- [scripts/check_frontmatter.py](../../scripts/check_frontmatter.py), [tools/brain/src/brain/index_md.py](../../tools/brain/src/brain/index_md.py), [.claude/skills/repo-structure/repo_structure.py](../../.claude/skills/repo-structure/repo_structure.py)
- [ADR-0006](../decisions/ADR-0006-todos-are-files.md), [knowledge/AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [start-here](../context/start-here.md)

## Files relied on

- [ADR-0005](../decisions/ADR-0005-llm-friendly-repo.md), [knowledge/AGENTS.md](../AGENTS.md), [dashboards/hub/README.md](../../dashboards/hub/README.md), [knowledge/templates/note.md](../templates/note.md), [knowledge/context/team.yaml](../context/team.yaml), [scripts/new_project.py](../../scripts/new_project.py)

## PR

Same branch as the scaffold: `chore/initial-scaffold` -> `main`, PR "chore: initial scaffold".
Not merged by the agent.
