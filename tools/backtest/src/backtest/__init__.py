"""backtest: the shared backtesting loop, once two experiments need one.

A tool: an isolated package that takes a signal table and a price table as arguments and knows
nothing about the repository, the bucket or .env. Contract: tools/README.md; conventions the loop
must follow (returns, costs, calendars, currencies): knowledge/context/conventions.md.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__: list[str] = []
