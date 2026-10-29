---
id: ADR-0001-initial-setup
type: decision
title: "ADR-0001: initial setup of the semi-systematic monorepo"
date: 2026-10-29
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [infra, data, vendor, costs]
related: [workflow, conventions, vendors]
---

# ADR-0001: initial setup of the semi-systematic monorepo

## Context

A small remote quant research team needs one place for knowledge, code, experiments and
dashboards, kept as plain text with consistent metadata so that a retrieval index can be built over
it, AI agents can work in it safely, and routine tasks are packaged as skills. The repo
`github.com/DarkEB1/semi-systematic` existed with a README only. An R2 bucket existed on the
operator's Cloudflare account but was unconfigured. This ADR records the decisions that were made
before scaffolding (fixed, not to be reopened) and the ones made during it.

## Decision

### Fixed before scaffolding

- One monorepo. Priorities in order: reproducibility, institutional memory, AI-operability, velocity.
- Trust-based review: no required reviewer; CI must be green; CODEOWNERS on the data layer only
  (`src/quant/data/**`, `catalog/**`, `promote/**`, `.github/**`, owner DarkEB1).
- Squash-merged short-lived branches; linear history on `main`.
- Everything runs in the devcontainer, by people and agents; nothing else is supported.
- Secrets live in a hand-maintained `.env` per person and in GitHub Actions secrets for CI.
- Bucket prefixes: `raw/` overwritable by the ingest job only; `curated/` append-only, written by
  the promote step only; `scratch/<handle>/` for everyone else.
- Schema contract on `curated/` only, parsed from the dataset README's Schema table.
- marimo notebooks. Code is promoted out of experiments on second use. Experiments with
  `status: final` are frozen.
- One uv lockfile with optional groups; `src/quant` imports only the base group.
- Repo-only retrieval in v1 (DuckDB `ILIKE`; no embeddings until a model is configured).
- Skills may merge their own PRs when CI is green and no changed path is under CODEOWNERS.
- Every agent loop needs a budget. One internal dashboard hub. No chat notifications.

### Storage (Step 0, done 2026-10-28)

- Bucket `semi-sys-research-data`, Cloudflare R2, **EU jurisdiction**, account
  `21e1b5d002dff4818d0b82a9476fe41d`. S3 endpoint
  `https://21e1b5d002dff4818d0b82a9476fe41d.eu.r2.cloudflarestorage.com` (the `.eu.` differs from
  the default-jurisdiction template). No public access, no custom domain.
- Three R2 **account** API tokens (survive membership changes): `team-read` (Object Read),
  `ingest-write` (Object Read & Write), `DarkEB1-scratch` (Object Read & Write), all scoped to the
  one bucket. R2 cannot scope a token to a prefix, so the prefix rules are enforced in
  `quant.data`, by the nightly audit, and by convention.
- GitHub repository secrets: `R2_INGEST_KEY`, `R2_INGEST_SECRET`, `R2_ACCOUNT_ID`,
  `VENDOR_API_KEY` (placeholder `unset` until a vendor exists). No key value is recorded anywhere
  in the repo.
- Branch protection on `main`: required status check `ci`, strict, no required reviews, admins
  included, linear history, no force pushes. Merge settings: squash only, delete branch on merge.
  Dependabot alerts and security updates on; `dependabot.yml` opens weekly PRs for pip,
  github-actions and docker.

### Decided during scaffolding

- **Repository stays public** (operator decision, 2026-10-29). The spec assumed private. Secrets
  are not exposed by this, but every knowledge file is world-readable; the `private: true`
  frontmatter key only excludes a file from the index, not from the internet.
- **Scratch lifecycle rule skipped** for now (operator decision). TODO: add an R2 lifecycle rule
  expiring `scratch/` objects after 90 days.
- **Backblaze B2 backup deferred**. TODO: create the B2 bucket with versioning, add `B2_KEY_ID`,
  `B2_APPLICATION_KEY`, `B2_BUCKET` as repository secrets; `backup.yml` skips with a notice until then.
- Free example source is **Yahoo Finance's chart endpoint** (daily OHLCV, no key), not Stooq:
  Stooq sits behind a JavaScript challenge. FRED fixings are the documented fallback.
- Write policy is selected by `QUANT_ROLE` (`ingest`, `promote`, unset). Off-CI ingest runs write
  a run-stamped mirror under `scratch/<handle>/raw/...` and never overwrite.
- Team handles live in `knowledge/context/team.yaml`; the frontmatter checker, the audit and
  onboarding read it. Tags live in `knowledge/context/tags.md`, one line per tag.
- The devcontainer keeps the virtualenv and uv cache in named Docker volumes (not host mounts) so
  bind-mounted workspaces on Windows and macOS stay fast. Tool binaries are version-pinned in the
  Dockerfile; apt packages are pinned only through the base image tag.
- Evals compare each skill's `run.py --dry-run` stdout (dates and owners passed explicitly) with a
  golden `expected.txt`; `just eval --update` refreshes goldens in a reviewed PR.
- The loop runner executes a skill's deterministic `run.py` by default; a model-driven loop sets
  `command:` in the task YAML and inherits the same budget and path checks.
- The nightly ingest runs at 01:30 UTC Tuesday to Saturday; data-health counts business days with
  a one-day lag.

## Consequences

Easier: one command set (`just`) for people, agents and CI; a new teammate or agent can start from
`README.md` and `AGENTS.md` alone; every decision is searchable. Harder: the devcontainer is a hard
requirement; anything outside the prefix rules fails loudly. Costs: R2 storage and class A/B
operations only, within the free tier for now; Yahoo is free but unofficial.

Open TODOs tracked here: scratch lifecycle rule, B2 backup bucket, first paid vendor, per-currency
holiday calendars, embeddings for the index.

## Alternatives considered

- Private repo: preferred by the spec; the operator chose public for now. Revisit before any
  non-public knowledge is written (that would be a new ADR superseding this section).
- One token per prefix: not possible on R2; enforced in code instead.
- Branch protection via rulesets: classic protection was enough for a required check and linear
  history; rulesets are a drop-in later.
- Stooq for OHLCV: blocked. FRED alone: no OHLC, so it is a fallback, not the example.
- pre-commit's gitleaks hook (Go toolchain download): replaced by the pinned binary in the image,
  called from a `local` hook and from `just check`.
