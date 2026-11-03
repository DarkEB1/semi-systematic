---
id: setup
type: context
title: "Setting up: one checklist per person, from a new laptop to a first agent session"
date: 2026-11-02
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra]
related: [start-here, working-with-agents, workflow, ADR-0009-agent-channel-enforced]
---

# Setting up: one checklist per person, from a new laptop to a first agent session

Everyone who works here, and every agent they run, goes through this once. It takes 30 to 60
minutes, most of it the first container build. The [README](../../README.md) has the same steps as a
prompt you can paste into an assistant; this page is the checklist to tick.

## 0. Before you start (the data-layer owner, once per person)

@DarkEB1 does this, then tells the person their handle is ready:

- [ ] Add the person's GitHub account to the repo with write access.
- [ ] In Cloudflare R2, create an API token `<handle>-scratch` with Object Read & Write on the
      `semi-sys-research-data` bucket only, and store it in the team password manager under that name.
- [ ] Share the password manager entries `R2 shared` and `team-read` with them.

## 1. Install on your machine

Your assistant (Claude Code, Codex) runs on your machine, not in the container. The container runs
the recipes. So you need both sides.

- [ ] **git**: `git --version`.
- [ ] **Docker Desktop**, running: `docker info` must print without an error.
- [ ] **GitHub CLI**, logged in: `gh auth login`, then `gh auth status`.
- [ ] **A real Python 3**: `python3 -c "print('ok')"` or `python -c "print('ok')"` must print `ok`.
      The repo's hooks run with it and **block every action when no Python works**. On Windows the
      Microsoft Store `python3` alias does not count: install from python.org or
      `winget install Python.Python.3.12`.
- [ ] **Claude Code** (`claude --version`) and/or **Codex**. Optional: VS Code with the
      Dev Containers extension, if you like a container terminal.

## 2. Get the repo and the container

- [ ] `git clone https://github.com/DarkEB1/semi-systematic.git` and `cd semi-systematic`.
- [ ] Build the container once: `sh scripts/in-container.sh just --version`. The first run builds the
      image (a few minutes) and prints the `just` version. With VS Code you can instead run
      "Dev Containers: Reopen in Container".

From here, every `just` recipe and every `git commit` runs in the container. From a host terminal,
put `sh scripts/in-container.sh` in front: `sh scripts/in-container.sh just check`. In a VS Code
container terminal, type the command as is. `git push` and `gh` run on the host.

## 3. Your `.env`

- [ ] `cp .env.example .env`, then open `.env` in your editor and fill it in yourself:
  - `R2_ACCOUNT_ID`, `R2_ENDPOINT`, `R2_BUCKET`: password manager entry `R2 shared`. The endpoint
    contains `.eu.`.
  - `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`: entry `team-read`.
  - `R2_HANDLE`: your GitHub handle, spelled exactly as on GitHub.
  - `R2_SCRATCH_ACCESS_KEY_ID`, `R2_SCRATCH_SECRET_ACCESS_KEY`: entry `<handle>-scratch`.
  - Everything else stays empty on a laptop.
- [ ] Never paste a value into a chat, an issue or a tracked file, and never ask an assistant to read
      `.env` back. Agents are blocked from reading it.

## 4. Check

- [ ] `sh scripts/in-container.sh just onboard`: every line `OK`, except the three about your handle,
      which turn `OK` after step 5.
- [ ] `sh scripts/in-container.sh just check` and `sh scripts/in-container.sh just test`: both pass.

## 5. Register yourself (one PR)

- [ ] `git checkout -b chore/onboard-<handle>`.
- [ ] Create `knowledge/notes/<handle>/.gitkeep`.
- [ ] Add `<handle>` under `handles:` in `knowledge/context/team.yaml`.
- [ ] Add `/knowledge/notes/<handle>/ @<handle>` to `.github/CODEOWNERS`, under the ownership map.
- [ ] `sh scripts/in-container.sh git add -A` and
      `sh scripts/in-container.sh git commit -m "chore: onboard <handle>"`, then
      `git push -u origin HEAD` and `gh pr create --fill`.
- [ ] The PR touches `.github/`, so @DarkEB1 merges it. Once it is merged, `just onboard` shows
      every line `OK`.

## 6. Your first agent session

- [ ] Start Claude Code at the repo root. It reads `AGENTS.md` by itself. The first thing it sees is
      the agent channel line, for example `Agent channel (issue #2): no open messages for @<handle>.`
      If instead you see `hooks: no working python`, go back to step 1.
- [ ] Codex reads `AGENTS.md` too, but Claude Code's hooks do not run for it. Tell it at the start of
      each session: "read `gh issue view 2 --comments` and propose resolving anything addressed to
      me first; run recipes through `sh scripts/in-container.sh`".
- [ ] Read [start-here](start-here.md), [workflow](workflow.md) and
      [working-with-agents](working-with-agents.md).

## Every day

- **Start of a session**: your agent lists open messages for you in the pinned
  [agent channel, issue #2](https://github.com/DarkEB1/semi-systematic/issues/2) and proposes how to
  resolve them before anything else. GitHub notifies you when someone tags `@<handle>` there.
- **Someone else's work**: before your agent changes a file another person owns (`owner:` in the
  file or in the nearest README, such as a research project), it posts in #2 tagging them, and the
  edit hook blocks until it has. Questions to a teammate go there too.
- **Board**: `sh scripts/in-container.sh just todo --list`. A card you create or move is committed
  on the `todos` branch; if the push from the container fails, run `git push origin todos` on the host.
  The `.todos/` worktree was created in the container, so its git metadata points at
  `/workspaces/...`: run `git -C .todos` and `just todo` only through the container, and never run
  `git worktree prune` on the host (it drops the worktree).
- **Dashboard**: `sh scripts/in-container.sh` publishes no ports, so `just dashboard` through it is
  unreachable from your browser. Use VS Code "Reopen in Container", or run it detached with the port
  published, the same mounts as `scripts/in-container.sh`, and stop it with `docker stop semi-dash`:
  `MSYS_NO_PATHCONV=1 docker run -d --rm --name semi-dash --env-file=.env -p 2718:2718 -v "$(pwd -W 2>/dev/null || pwd):/workspaces/semi-systematic" -v semi-systematic-venv:/opt/venv -v semi-systematic-uv-cache:/root/.cache/uv -w /workspaces/semi-systematic semi-sys-dev just dashboard`,
  then open `http://localhost:2718`.
- **Work**: a branch per change, `just check` and `just test` green, a PR. Every agent task ends with
  an agent-log entry. Never write `raw/` or `curated/`; your data goes in `scratch/<handle>/`.

## When something fails

| you see | it means | do |
|---|---|---|
| `hooks: no working python` on every action | the hooks found no Python that runs | install Python 3 (step 1), restart the session |
| `Cannot connect to the Docker daemon` | Docker Desktop is stopped | start it, wait for `docker info`, retry |
| `just: command not found` | you ran a recipe on the host | prefix it with `sh scripts/in-container.sh` |
| `pre-commit not found` on commit | you committed on the host | commit through `sh scripts/in-container.sh git commit ...` |
| `fatal: not a git repository: /workspaces/semi-systematic/.git/worktrees/-todos` | you ran a board command on the host | run it through `sh scripts/in-container.sh` |
| `just dashboard` runs but `localhost:2718` does not load | `in-container.sh` publishes no ports | use the `docker run -p 2718:2718` command under Dashboard above |
| `MISSING` for an `R2_` variable | `.env` is incomplete | step 3 |
| `SignatureDoesNotMatch`, `InvalidAccessKeyId`, 403 | a key has a stray space, or the endpoint lacks the account id or `.eu.` | fix the line in `.env` |
| `blocked by scripts/hooks/agent_channel.py` | the file is someone else's | post in #2 tagging them, as the message says, then retry |
| an `owner:` handle rejected by `just check` | the handle is not in `team.yaml` | that person has not done step 5 yet |
