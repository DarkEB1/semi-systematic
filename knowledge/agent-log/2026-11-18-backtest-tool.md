---
id: 2026-11-18-backtest-tool
type: agent-log
title: "Build the minimal backtesting framework in tools/backtest from the Daniel and Paleologo lecture"
date: 2026-11-18
authors: [Claude]
owner: DarkEB1
status: draft
tags: [backtest, infra]
related: [ADR-0013-backtest-tool-from-daniel-paleologo, ADR-0002-tools-are-isolated-packages]
---

# Build the minimal backtesting framework in tools/backtest from the Daniel and Paleologo lecture

## Task

@DarkEB1 asked Claude Code to read a lecture PDF on backtesting (Daniel and Paleologo, FINC B8420
lecture 6, 88 slides, kept outside the repo), extract what is useful for implementing a framework
and, if it sufficed, build the minimal version on a branch in `tools/`, with nothing from outside
the document. No skill, no loop.

## Decisions with justification

- Built it: the lecture gives formulas for splits, net PnL, the score matrix and the Rademacher
  lower bound, which is a complete evaluation pipeline. It gives no cost model, so `costs` is an
  input and the `conventions.md` half-spread was left out.
- Filled the reserved `tools/backtest` slot instead of `just new-tool`: the slot exists for this.
- numpy only: the lecture's own code is numpy; `polars` and `pyarrow` were declared but unused.
- Bounded theorem with factor 3 as the default bound; the factor-2 simulation screens and the
  calibrated `a0`, `b0` rule were left out because the lecture marks them as not guaranteed.
- ADR-0013, not 0010: 0010 to 0012 exist on the unmerged research branch.

## Summary

Three modules (`splits`, `pnl`, `haircut`), twelve public names, eleven tests that reproduce the
lecture's worked numbers. Committed on `tools/backtest-framework`; not pushed, no PR. The todo card
"Build the backtesting framework" on the `todos` branch was not moved.

## Files touched

- [tools/backtest/src/backtest/__init__.py](../../tools/backtest/src/backtest/__init__.py)
- [tools/backtest/src/backtest/splits.py](../../tools/backtest/src/backtest/splits.py)
- [tools/backtest/src/backtest/pnl.py](../../tools/backtest/src/backtest/pnl.py)
- [tools/backtest/src/backtest/haircut.py](../../tools/backtest/src/backtest/haircut.py)
- [tools/backtest/tests/test_backtest.py](../../tools/backtest/tests/test_backtest.py)
- [tools/backtest/pyproject.toml](../../tools/backtest/pyproject.toml)
- [tools/backtest/README.md](../../tools/backtest/README.md)
- [tools/README.md](../../tools/README.md)
- [knowledge/context/start-here.md](../context/start-here.md)
- [knowledge/decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md](../decisions/ADR-0013-backtest-tool-from-daniel-paleologo.md)
- [uv.lock](../../uv.lock)

## Files relied on

- [AGENTS.md](../../AGENTS.md)
- [tools/AGENTS.md](../../tools/AGENTS.md)
- [knowledge/AGENTS.md](../AGENTS.md)
- [knowledge/context/conventions.md](../context/conventions.md)
- [knowledge/decisions/ADR-0002-tools-are-isolated-packages.md](../decisions/ADR-0002-tools-are-isolated-packages.md)

## PR

None: the request was a branch. `tools/backtest-framework` is local.
