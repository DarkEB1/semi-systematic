---
id: ADR-0006-todos-are-files
type: decision
title: "ADR-0006: the team board is one file per todo, rendered by the hub"
date: 2026-10-31
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0001-initial-setup, ADR-0005-llm-friendly-repo, working-with-agents]
---

# ADR-0006: the team board is one file per todo, rendered by the hub

## Context

@DarkEB1 asked on 2026-10-31 for todo management for the team, a kanban with user ownership,
and whether it could be part of the dashboard. The repo already has the pieces: knowledge files
with an `owner` handle checked against `team.yaml`, a status in frontmatter, templates the checker
enforces, meeting minutes with `@handle` actions, a retrieval index, and a read-only marimo hub
that renders repo files. Agents work through `just` recipes and files, never through a web UI.

## Decision

- A todo is a file, `knowledge/todos/<date>-<slug>.md`, of type `todo`, from
  `knowledge/templates/todo.md`. The column is `status` (`todo`, `doing`, `done`), the card belongs
  to `owner`, and `due` is an optional ISO date. `just check` enforces all of it.
- `just todo "<title>" [--owner H] [--due D] [--project P]` creates one; `just todo <id> --move
  <status>` edits only the status line; `just todo --list [--owner H]` prints the board as text.
  Files are never renamed or moved (the `knowledge/` rule); done cards stay as history.
- The hub's `board` page renders the files as three columns, filtered by the shared owner and
  status boxes. The hub stays read-only: moving a card is a commit, like every other change.
- A meeting action that outlives the meeting becomes a todo owned by its `@handle`; the minutes
  keep the checkbox and link the todo under `related`.

## Consequences

- Ownership and status are validated and searchable, and the board is as current as the checkout.
  An agent can create, move and finish todos with the same recipes a person uses.
- No drag and drop. A move is one command or one edited line, and it shows up in the PR diff.
- The chunk index and `knowledge/INDEX.md` include todos, so `just search` finds them; `done`
  cards accumulate and are filtered out by the status box rather than archived.

## Alternatives considered

- A GitHub Project board: zero code, but a person has to create it in the UI, the data lives
  outside the repo, and the hub cannot show it without a token in every checkout.
- One Obsidian kanban file (headings as columns): zero code and drag and drop in Obsidian, but one
  file everyone edits, no per-card owner or due validation, and nothing for the hub or agents.
- A single `todos.yaml`: fewer files, but merge conflicts on every move and no body for notes.
- Writing from the dashboard: breaks the hub's rule of holding no state, and a change made in a
  browser still needs a commit to reach anyone else.
