---
id: 2026-11-03-defi-repo-public-research
type: agent-log
title: "Public-data reconstruction of DeFi deposit and repo-rate evidence"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: draft
tags: [crypto, macro, data, backtest]
related: [ADR-0010-defi-repo-research-sources, ADR-0011-pinned-scratch-experiment-inputs, ADR-0012-research-evidence-plots, 2026-11-03-rate-spread-replication]
---

# Public-data reconstruction of DeFi deposit and repo-rate evidence

## Task

Reconstruct the public-data evidence behind ECB WP3280, examine forecast and conditional carry performance, and record findings and further ideas in the knowledge base without choosing an investment verdict. The user confirmed no paid Aavescan access. Used the repository's new-experiment, pull-data and promote-dataset workflows. This was a finite experiment, not a configured autonomous loop.

## Decisions with justification

- [ADR-0010](../decisions/ADR-0010-defi-repo-research-sources.md): bounded public reserve state, Chainlink marks and official reference rates; no paid vendor history, wallet traces or full blocks on the server.
- [ADR-0011](../decisions/ADR-0011-pinned-scratch-experiment-inputs.md): explicit schema-checked, checksum-pinned scratch inputs through the required data loader, preserving owner-reviewed promotion.
- [ADR-0012](../decisions/ADR-0012-research-evidence-plots.md): Matplotlib in the research extra for standalone figures.
- Retained missing early oracle marks and rejected incomplete RPC responses. Handled the documented V3.2 zero-address stable-debt field explicitly, with a regression test. Independent checks compare exact reserve/index calls, balances and oracle returns on six dates.
- Registry scaffolding needed a small fix because Ruff grouped its imports. Read the golden diff before updating the pull-data matrix expectation; added grouped-import regression coverage.

## Summary

Read AGENTS.md and pinned issue #2 first; the issue had no comments requiring resolution. `just onboard` reported 23 ok, 0 missing. Searches in three research phrasings returned no prior experiment. All recipes and commits ran through scripts/in-container.sh; GitHub and pushes ran on the host. No environment-file contents were read or printed, and no dashboard was launched.

Acquired and independently checked the bounded historical panel, wrote only immutable scratch objects with contracts/provenance, verified read-back hashes, and ran the notebook on those pins. The experiment evaluates 87 scenarios and seven synthetic accounting and future-data invariants. Actual empirical figures and limitations are in the output-derived [research log](../research-log/2026-11-03-rate-spread-replication.md). No exact vendor replication, causal policy estimate, funded-arbitrage return or live execution is claimed.

Prepared two promotion requests after schema validation, read-back and confirming the curated prefixes were empty. No raw or curated writes occurred. Draft status preserves the retention gate: after owner-approved promotion, a follow-up must update the input pins to curated snapshots, rerun and freeze. The source registry/matrix would enable recurring ingest on merge; the owner should review that alongside retention. A November-only NY Fed dry run returned no observations; the available-history dry run passed. Aave's current dry run passed. Independent dRPC batch requests initially failed; bounded individual calls succeeded.

Local ignored checkpoints, probe scripts, tables and validation JSON remain under the experiment's outputs directory; they are generated artifacts, not additional committed sources. Quoted research numbers come from those outputs. The committed acquisition manifest records input hashes and storage sizes. No knowledge file was moved or renamed.

## Verification

Final checks, run through the container wrapper:

- `just check`: `All checks passed!`; `frontmatter: 46 file(s) checked, 0 problem(s)`; `links: 81 file(s) checked, 0 broken`; `Success: no issues found in 59 source files`; `no leaks found`.
- `just test`: `131 passed in 12.07s`.
- `just eval`: `eval: 7 skill(s), 0 failure(s)`.
- Final notebook rerun exited 0; all seven accounting and future-data invariants passed. Statsmodels emitted a future return-type deprecation warning; dependency versions are locked.
- Independent RPC validation and server checksum read-back passed; all three figures were visually inspected.

## Files touched

- [.claude/skills/new-experiment/SKILL.md](../../.claude/skills/new-experiment/SKILL.md)
- [.claude/skills/pull-data/pull_data.py](../../.claude/skills/pull-data/pull_data.py)
- [.github/workflows/ingest.yml](../../.github/workflows/ingest.yml)
- [ai/evals/pull-data/expected.txt](../../ai/evals/pull-data/expected.txt)
- [catalog/catalog.sql](../../catalog/catalog.sql)
- [catalog/datasets/aave_reserve_daily.md](../../catalog/datasets/aave_reserve_daily.md)
- [catalog/datasets/usd_reference_rates.md](../../catalog/datasets/usd_reference_rates.md)
- [knowledge/agent-log/2026-11-03-defi-repo-public-research.md](../../knowledge/agent-log/2026-11-03-defi-repo-public-research.md)
- [knowledge/context/data-access.md](../../knowledge/context/data-access.md)
- [knowledge/context/universe.md](../../knowledge/context/universe.md)
- [knowledge/context/vendors.md](../../knowledge/context/vendors.md)
- [knowledge/decisions/ADR-0010-defi-repo-research-sources.md](../../knowledge/decisions/ADR-0010-defi-repo-research-sources.md)
- [knowledge/decisions/ADR-0011-pinned-scratch-experiment-inputs.md](../../knowledge/decisions/ADR-0011-pinned-scratch-experiment-inputs.md)
- [knowledge/decisions/ADR-0012-research-evidence-plots.md](../../knowledge/decisions/ADR-0012-research-evidence-plots.md)
- [knowledge/research-log/2026-11-03-rate-spread-replication.md](../../knowledge/research-log/2026-11-03-rate-spread-replication.md)
- [promote/requests/2026-11-03-aave_reserve_daily.yml](../../promote/requests/2026-11-03-aave_reserve_daily.yml)
- [promote/requests/2026-11-03-usd_reference_rates.yml](../../promote/requests/2026-11-03-usd_reference_rates.yml)
- [pyproject.toml](../../pyproject.toml)
- [research/AGENTS.md](../../research/AGENTS.md)
- [research/defi-repo/README.md](../../research/defi-repo/README.md)
- [research/defi-repo/experiments/.gitkeep](../../research/defi-repo/experiments/.gitkeep)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/acquire.py](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/acquire.py)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/acquisition-manifest.json](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/acquisition-manifest.json)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/config.yaml](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/config.yaml)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/.gitkeep](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/.gitkeep)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/conditional-carry.png](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/conditional-carry.png)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/depeg-marks.png](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/depeg-marks.png)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/rates-and-spreads.png](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/figures/rates-and-spreads.png)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/publish_inputs.py](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/publish_inputs.py)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/report.py](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/report.py)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/results.md](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/results.md)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/run.py](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/run.py)
- [research/defi-repo/experiments/2026-11-03-rate-spread-replication/validate_acquisition.py](../../research/defi-repo/experiments/2026-11-03-rate-spread-replication/validate_acquisition.py)
- [src/quant/data/__init__.py](../../src/quant/data/__init__.py)
- [src/quant/ingest/__init__.py](../../src/quant/ingest/__init__.py)
- [src/quant/ingest/aave_archive.py](../../src/quant/ingest/aave_archive.py)
- [src/quant/ingest/nyfed.py](../../src/quant/ingest/nyfed.py)
- [tests/fixtures/aave_archive_sample.json](../../tests/fixtures/aave_archive_sample.json)
- [tests/fixtures/nyfed_sample.json](../../tests/fixtures/nyfed_sample.json)
- [tests/test_data.py](../../tests/test_data.py)
- [tests/test_ingest_aave_archive.py](../../tests/test_ingest_aave_archive.py)
- [tests/test_ingest_nyfed.py](../../tests/test_ingest_nyfed.py)
- [tests/test_scratch_load.py](../../tests/test_scratch_load.py)
- [tests/test_source_registry_patch.py](../../tests/test_source_registry_patch.py)
- [uv.lock](../../uv.lock)

## Files relied on

- [.github/CODEOWNERS](../../.github/CODEOWNERS)
- [.claude/agents/reviewer.md](../../.claude/agents/reviewer.md)
- [.claude/skills/new-experiment/SKILL.md](../../.claude/skills/new-experiment/SKILL.md)
- [.claude/skills/new-experiment/new_experiment.py](../../.claude/skills/new-experiment/new_experiment.py)
- [.claude/skills/promote-dataset/SKILL.md](../../.claude/skills/promote-dataset/SKILL.md)
- [.claude/skills/promote-dataset/promote_dataset.py](../../.claude/skills/promote-dataset/promote_dataset.py)
- [.claude/skills/pull-data/SKILL.md](../../.claude/skills/pull-data/SKILL.md)
- [.claude/skills/pull-data/pull_data.py](../../.claude/skills/pull-data/pull_data.py)
- [.gitignore](../../.gitignore)
- [AGENTS.md](../../AGENTS.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [justfile](../../justfile)
- [knowledge/AGENTS.md](../../knowledge/AGENTS.md)
- [knowledge/context/conventions.md](../../knowledge/context/conventions.md)
- [knowledge/context/data-access.md](../../knowledge/context/data-access.md)
- [knowledge/context/start-here.md](../../knowledge/context/start-here.md)
- [knowledge/context/strategy.md](../../knowledge/context/strategy.md)
- [knowledge/context/tags.md](../../knowledge/context/tags.md)
- [knowledge/context/team.yaml](../../knowledge/context/team.yaml)
- [knowledge/context/universe.md](../../knowledge/context/universe.md)
- [knowledge/context/vendors.md](../../knowledge/context/vendors.md)
- [knowledge/context/walkthrough.md](../../knowledge/context/walkthrough.md)
- [knowledge/context/workflow.md](../../knowledge/context/workflow.md)
- [knowledge/context/working-with-agents.md](../../knowledge/context/working-with-agents.md)
- [knowledge/decisions/ADR-0001-initial-setup.md](../../knowledge/decisions/ADR-0001-initial-setup.md)
- [knowledge/templates/agent-log.md](../../knowledge/templates/agent-log.md)
- [knowledge/templates/decision.md](../../knowledge/templates/decision.md)
- [knowledge/templates/note.md](../../knowledge/templates/note.md)
- [knowledge/templates/research-log.md](../../knowledge/templates/research-log.md)
- [research/AGENTS.md](../../research/AGENTS.md)
- [research/README.md](../../research/README.md)
- [scripts/check_frontmatter.py](../../scripts/check_frontmatter.py)
- [scripts/in-container.sh](../../scripts/in-container.sh)
- [src/quant/AGENTS.md](../../src/quant/AGENTS.md)
- [src/quant/data/__init__.py](../../src/quant/data/__init__.py)
- [src/quant/data/schema.py](../../src/quant/data/schema.py)
- [src/quant/ingest/_base.py](../../src/quant/ingest/_base.py)
- [tests/test_data.py](../../tests/test_data.py)

External primary sources: [ECB WP3280](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3280~503ba7d4b0.en.pdf), [New York Fed API](https://markets.newyorkfed.org/static/docs/markets-api.html), [NY Fed terms](https://www.newyorkfed.org/privacy/termsofuse.html), [Alchemy terms](https://legal.alchemy.com/), [Aave contracts](https://github.com/aave-dao/aave-v3-origin), [Chainlink feeds](https://docs.chain.link/data-feeds/price-feeds/addresses), [MakerDAO Multicall](https://github.com/makerdao/multicall). Earlier tool probes also assessed Aavescan access and DefiLlama reuse restrictions; neither dataset was acquired.

## PR

Pending creation after final checks. The PR touches the data-layer CODEOWNERS block and is not self-merged. The [promote-dataset skill](../../.claude/skills/promote-dataset/SKILL.md) requires: "this skill never merges its own PR"; [src/quant/AGENTS.md](../../src/quant/AGENTS.md) says a data-layer PR "waits for the data-layer owner".
