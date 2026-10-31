---
id: ADR-0007-todos-live-on-their-own-branch
type: decision
title: "ADR-0007: the board lives on the todos branch, the same from every checkout"
date: 2026-10-31
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0006-todos-are-files, ADR-0005-llm-friendly-repo, working-with-agents]
---

# ADR-0007: the board lives on the todos branch, the same from every checkout

## Context

ADR-0006 made a todo a file under `knowledge/todos/` and gave the hub a board page. On the same
day @DarkEB1 asked for the board to be branch-independent: a card created or moved on any branch
should be visible everywhere at once, and nobody should see a stale board because their feature
branch is behind `main`. Cards that ride along with feature branches cannot give that: two branches
moving the same card conflict on merge, a card created on a branch is invisible until the PR
merges, and `main` is protected (PR plus a green `ci` check, linear history, enforced for admins),
so landing every move on `main` directly would cost a PR and a CI run per move.

## Decision

- Cards live on one unprotected branch, `todos`, and nowhere else. `knowledge/todos/` does not
  exist on `main` or on feature branches; the `todo` type, its template and its checks stay.
- `just todo` keeps that branch checked out as a git worktree at `.todos/` (gitignored). Every
  command fetches and fast-forwards first; create and `--move` write the file there, validate it
  with the same checker `just check` uses, commit on `todos` and push. On a push race it rebases
  once and retries; offline it keeps the commit and `just todo --sync` pushes later.
- `just todo --list` and the hub's board page read `.todos/knowledge/todos/`; `just dashboard`
  syncs before starting. So every checkout, on any branch, shows the same board within one fetch.
- The `todos` branch is never merged into `main`; it only ever gains card commits. It was created
  from the scaffold branch so that its pre-commit hooks already know the `todo` type.

## Consequences

- Supersedes the location in ADR-0006 (the file shape, ownership and the hub page stand);
  ADR-0006 is marked superseded. The two cards created under ADR-0006 moved to the new branch
  unchanged.
- A card move is one commit on `todos`, not a PR, and takes seconds to reach everyone. Branch
  protection on `main` is untouched; the `--no-verify`, force-push and `push main` guards still apply.
- Cards are not part of `main`, so `knowledge/INDEX.md` and `just search` do not see them; the
  board and `just todo --list` are the views. Links from other knowledge files to a card are
  therefore plain text ids, not relative links.
- Pushing needs git credentials inside the container. VS Code forwards them; a plain `docker run`
  does not, in which case the commit waits on the local `todos` branch and `just todo --sync`
  (or `git push origin todos` from the host) sends it.
- Nothing asks a person: an agent creates and moves cards with the same recipe.

## Alternatives considered

- Cards on `main` via an automatic PR per change (workflow opens it, auto-merge on green CI):
  works without a person but costs a CI run and a minute per move, and the branch that created
  the card still conflicts with `main` when it merges. More machinery for a worse result.
- Cards on each feature branch, lifted to `main` by a workflow: same conflict problem, plus a
  stale board on every branch until it rebases.
- Cards outside git (a bucket prefix or a small service): the hub and agents could read them, but
  it adds a new write path to the data layer and loses the diff, the checker and the history.
- A single kanban markdown file on `main`: the conflict problem in its worst form.
