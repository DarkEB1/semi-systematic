---
id: 2026-11-03-host-container-gaps
type: agent-log
title: "Verify local setup and document the .todos and dashboard-port gaps for host agents"
date: 2026-11-03
authors: [Claude]
owner: DarkEB1
status: draft
tags: [infra]
related: [setup, 2026-11-02-host-agents-and-failing-hooks]
---

# Verify local setup and document the .todos and dashboard-port gaps for host agents

## Task

@DarkEB1 asked Claude Code to set the repo up on their Windows machine for experimenting, then to
write into the repo the two facts a host agent (Codex) would otherwise not know.

## Decisions with justification

- No setup changes: the image, volumes, `.env` and hooks were already in place; `just onboard`
  printed `23 ok, 0 missing`, and `just check`, `just test` (113 passed) and `just eval` (7 skills,
  0 failures) were green.
- Documented the gaps in `setup.md` and the hub README rather than adding a port flag to
  `scripts/in-container.sh`: a fixed `-p 2718:2718` would collide when two commands run at once, and
  the docs change needs no code.

## Summary

Added to `setup.md` ("Every day" and "When something fails") that the `.todos/` worktree only works
through the container and how to serve the dashboard with the port published; pointed the hub
README at it. The dashboard command was run and served `http://localhost:2718` in about 8 seconds.

## Files touched

- [knowledge/context/setup.md](../context/setup.md)
- [dashboards/hub/README.md](../../dashboards/hub/README.md)
- [knowledge/agent-log/2026-11-03-host-container-gaps.md](2026-11-03-host-container-gaps.md)

## Files relied on

- [AGENTS.md](../../AGENTS.md)
- [scripts/in-container.sh](../../scripts/in-container.sh)
- [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)
- [knowledge/context/start-here.md](../context/start-here.md)

## PR

Branch `docs/host-container-gaps`; link added on merge.
