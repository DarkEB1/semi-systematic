---
id: glossary
type: context
title: "Glossary"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: active
tags: [infra]
---

# Glossary

TODO: grow this as terms are used in discussion; one line per term, alphabetical within a section.

## Repo terms

- ADR: an architecture/analysis decision record in `knowledge/decisions/`, created by the ADR test.
- agent-log: the entry every agent task ends with, linking the files it touched and relied on.
- catalog view: a DuckDB view in `catalog/catalog.sql` over bucket paths or reference CSVs.
- curated: the `curated/` prefix; promoted, schema-checked, append-only snapshots.
- project: a folder `research/<project>/` with a README and its own `experiments/`; an isolated unit.
- experiment: a folder under `research/<project>/experiments/` with config.yaml, run.py, results.md, figures/.
- frozen experiment: one whose results.md has `status: final`; `just check` refuses changes to it.
- promote: moving a scratch Parquet to `curated/` through a request file and the schema contract.
- raw: the `raw/` prefix; data as received, written only by the nightly ingest.
- scratch: the `scratch/<handle>/` prefix; the only place people and agents write.
- skill: a packaged routine task under `.claude/skills/<name>/`: a `SKILL.md` and a deterministic runner `<name_with_underscores>.py`.
- reviewer: the read-only subagent in `.claude/agents/reviewer.md` that checks a PR against its spec before a merge.
- hook: a command or model check in `.claude/settings.json` that Claude Code runs around tool calls; the zero-exception rules live there.
- snapshot: a dated, immutable copy of a curated dataset, `snapshot=YYYY-MM-DD`.

## Market terms

- cogs and oil: the two kinds of market participant in the README; cogs express views and take
  prices, oil keeps the machine from mispricing too much.
- EM: emerging-market currencies, rates and credit.
- fixing: an official daily reference rate for a currency pair.
- NDF: non-deliverable forward, the usual hedging instrument for restricted EM currencies.
