---
id: ADR-0003-isolation-principle
type: decision
title: "ADR-0003: everything is isolated; it comes together only in the data, the dashboard and the context docs"
date: 2026-10-30
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra]
related: [ADR-0001-initial-setup, ADR-0002-tools-are-isolated-packages, start-here]
---

# ADR-0003: everything is isolated; it comes together only in the data, the dashboard and the context docs

## Context

ADR-0002 isolated the tools. On 2026-10-30 @DarkEB1 generalised the intent: "Generally I would
like everything isolated, it only comes together in the data and the dashboard (and context docs);
this includes projects, research etc." Before this ADR the layout still had one shared research
folder (`research/signals/`) that experiments were meant to import from, the reuse rule named
`src/quant/` as a second destination for research code, and nothing checked that an experiment
did not import another.

## Decision

The repo has three integration points and everything else is an isolated unit.

Integration points, where things come together:

1. **The data layer**: the bucket, the catalog views and `src/quant/`. Units exchange results as
   datasets (scratch, then curated under the schema contract), never as imports.
2. **The dashboard**: `dashboards/hub/` reads any unit's files and views and is imported by nothing.
3. **The context docs**: `knowledge/` (and the retrieval index over it) is where decisions,
   results and notes meet; every unit writes its entry there.

Isolated units, and what each may import:

| unit | may import | never |
|---|---|---|
| a tool, `tools/<name>/` | its declared dependencies; another tool only if declared | `quant`, scripts, dashboards, research |
| an experiment, `research/<project>/experiments/<x>/` | `quant` (the data layer), tools, third-party | another experiment, dashboards, scripts |
| the data layer, `src/quant/` | third-party, tools | research, dashboards, scripts |
| scripts and skill runners | `quant`, tools | research, dashboards |

Consequences for the layout: `research/signals/` is removed; the reuse rule now reads "code moves
out of an experiment into a tool on second use, with a test, in its own PR"; `src/quant/` holds
data-layer code only; the hub's signals page becomes a tools page; rule 9 in `AGENTS.md` states
the principle and `scripts/check_isolation.py` enforces the table above in `just check`
(together with the tools contract from ADR-0002 and the ban on `sys.path` hacks).

"Projects" (a named line of research spanning several experiments) are not yet a layout element.
When they are introduced they follow the same rule: a project is a unit that meets other units
only through data, the dashboard and `knowledge/`.

## Consequences

- An experiment can be deleted, frozen or rerun without touching any other experiment.
- Adopting an external engine is one tool's dependency; swapping it changes one tool.
- Results that two units need must become a dataset, which forces a schema and a README, which
  is the memory priority doing its job.
- Some duplication inside experiments is accepted until the second use.
- The checker is import-based; it cannot see coupling through shared files on disk. The rule
  "units exchange results as datasets" is therefore also a review item.

## Alternatives considered

- Keep `research/signals/` as a lightweight shared folder: cheaper per move, but it is a second,
  unversioned library next to `tools/` and the first place isolation would erode.
- Allow experiments to import each other with a parent link: makes follow-ups easy and makes
  freezing meaningless, since a frozen parent would still be a live dependency.
- Enforce by review only: does not survive agents working unattended.
