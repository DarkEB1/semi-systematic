---
id: 2026-11-25-backtest-merge
type: agent-log
title: "Merge the daily engine and the Paleologo evaluation into one tools/backtest"
date: 2026-11-25
authors: [Claude]
owner: lucasvilliers
status: draft
tags: [backtest, infra]
related: [ADR-0014-backtest-engine, ADR-0013-backtest-tool-from-daniel-paleologo, 2026-11-17-backtest-engine, 2026-11-18-backtest-tool]
---

# Merge the daily engine and the Paleologo evaluation into one tools/backtest

## Task

@lucasvilliers asked to merge the two backtesters built in parallel in `tools/backtest`: the daily
engine (branch `feat/backtest`, PR #15) and @DarkEB1's walk-forward and Rademacher haircut layer
(branch `tools/backtest-framework`), agreed between them beforehand. Goal of the 2026-11-22
meeting: the framework merged by 2026-11-29. No skill or loop.

## Decisions with justification

- @DarkEB1's commit cherry-picked as is (authorship kept), conflicts resolved as the union: both APIs exported, `numpy`, `polars` and `pyarrow` declared, `test_import.py` kept. His modules stay flat (`splits.py`, `pnl.py`, `haircut.py`) rather than moved into a subpackage: no change to his imports or tests, and no clash with the name `evaluate`.
- A bridge, `family.py`, rather than reshaping either side: `walk_forward_weights` (fit on a `MarketView` frozen at the last training close, rule on a view frozen at each decision close, so lookahead raises), `scores` (daily NAV returns on common dates) and `evaluate` (`ras_lower_bounds` plus a per-candidate table). No timing shift: the engine already books decision t at t+1.
- `save_scores` / `load_scores` added at @lucasvilliers's request, in the same PR: a family is rarely tried in one script, and leaving out earlier variants understates the search. One parquet per candidate name in a caller-given directory (the tool reads no repo path); one name in two directories raises. Shared storage (the bucket) stays with the caller.
- `evaluate` raises when a score exceeds `kappa`, since the bounded theorem would not hold; `ras_lower_bounds` itself is unchanged.
- ADR-0010 renumbered ADR-0014 (0010 to 0012 are taken on `research/defi-repo-replication`); the file was never on `main`, so no link outside this branch breaks. It now records the merge and the bridge and leaves ADR-0013 standing.
- Version 0.3.0: new public functions on top of both 0.2.0 releases.

## Summary

Done: one package, 121 tests (103 engine, 11 lecture, 7 bridge), and a sandbox run on real data
(`research/test-data/experiments/2026-11-25-backtest-family-carry`, not tracked): BRL carry,
plain or with a 50 to 250-day trend filter, plus one walk-forward filter picker, 2005-12-23 to
2026-11-06, net of 5 bp. Sharpe 0.38 to 0.48; the filters cut vol from 16% to 10% and the drawdown
from -44% to -27%. Search cost 2R = 3.6% a year, sub-Gaussian lower bound about -8% a year
(inconclusive). The bounded theorem is not informative on daily NAV returns (`kappa` ten times the
daily vol); a risk-scaled or calibrated score is a follow-up. A first run on FX momentum (Sharpe
0.13 at best) showed no edge.

Needs a human: @DarkEB1 to review PR #15 (his `start-here.md` line was shortened to name both
halves); close `tools/backtest-framework` once merged.

## Files touched

- [tools/backtest/src/backtest/family.py](../../tools/backtest/src/backtest/family.py)
- [tools/backtest/src/backtest/__init__.py](../../tools/backtest/src/backtest/__init__.py)
- [tools/backtest/tests/test_family.py](../../tools/backtest/tests/test_family.py)
- [tools/backtest/tests/test_import.py](../../tools/backtest/tests/test_import.py)
- [tools/backtest/pyproject.toml](../../tools/backtest/pyproject.toml)
- [tools/backtest/README.md](../../tools/backtest/README.md)
- [tools/README.md](../../tools/README.md)
- [knowledge/decisions/ADR-0014-backtest-engine.md](../decisions/ADR-0014-backtest-engine.md)
- [knowledge/agent-log/2026-11-17-backtest-engine.md](2026-11-17-backtest-engine.md)
- [knowledge/context/start-here.md](../context/start-here.md)
- [uv.lock](../../uv.lock)

## Files relied on

- [knowledge/decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md](../decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md)
- [tools/backtest/src/backtest/haircut.py](../../tools/backtest/src/backtest/haircut.py)
- [tools/backtest/src/backtest/splits.py](../../tools/backtest/src/backtest/splits.py)
- [tools/AGENTS.md](../../tools/AGENTS.md)

## PR

[#15](https://github.com/DarkEB1/semi-systematic/pull/15)
