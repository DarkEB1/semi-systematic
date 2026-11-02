"""backtest: tests run without the repository, the bucket or .env."""

from __future__ import annotations

import backtest


def test_import() -> None:
    assert backtest.__version__ == "0.1.0"
    assert backtest.__all__ == []
