---
id: ADR-0004-projects-are-folders
type: decision
title: "ADR-0004: a project is a folder under research/, holding its own experiments"
date: 2026-10-30
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0003-isolation-principle, start-here, walkthrough]
---

# ADR-0004: a project is a folder under research/, holding its own experiments

## Context

ADR-0003 made isolation the rule and named projects as a future unit without a layout. Two
options were put to @DarkEB1 on 2026-10-30: a project as a context doc plus a key on each
experiment, keeping experiments in one flat folder; or a project as a folder with its own
experiments. The answer was "project is folder".

## Decision

- `research/<project>/` is a project. It holds `README.md` (frontmatter `type: project`, `id`
  equal to the folder name, template `knowledge/templates/project.md`) and `experiments/`, where
  every experiment of that project lives as `<date>-<slug>/`. Nothing else is under `research/`.
- `just project <slug>` creates one. `just experiment <slug> --project <p>` creates an
  experiment inside it; the project must exist. `config.yaml` records `project`, and the
  research-log entry that `--finish` drafts carries `project:` and links the project README.
- Projects are isolated units under ADR-0003: a project's experiments import the data layer and
  tools, never another project or another experiment. Projects exchange results as datasets.
- Project folders and experiment folders are never renamed or moved; a project that ends is set
  to `status: final` in its README with the verdicts summarised, and a follow-up is a new project.
- Checkers, the index, the dashboard and the loop runner learned the extra level: frontmatter
  validation covers `research/*/README.md`; `check_frozen` and `check_isolation` glob
  `research/*/experiments/*/`; brain indexes project READMEs (type `project`) and experiments at
  the new depth; the hub's experiments page lists projects first; the default `allowed_paths`
  for loops is `research/`.
- The existing demo experiment moved into `research/demo/` with a README; it is the one move
  this ADR allows, made before any history depends on the old path.

## Consequences

- An experiment's path says which project it belongs to; there is no second source of truth.
- Moving an experiment between projects is forbidden, like any move under `knowledge/`; start a
  new experiment with `parent:` instead.
- Every recipe that touched `research/experiments/` was updated in this change; a path with that
  prefix anywhere is now a bug.
- The project README is a knowledge file in all but location: it passes the frontmatter checker,
  is indexed, and appears in `knowledge/INDEX.md` under type `project`.

## Alternatives considered

- Context doc plus `project:` key, experiments flat: fewer moving parts and no new folder level,
  rejected by the operator in favour of stronger separation.
- One git repository per project: full isolation, but against the monorepo decision in ADR-0001.
