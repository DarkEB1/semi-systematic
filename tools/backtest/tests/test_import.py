"""backtest: tests run without the repository, the bucket or .env."""

from __future__ import annotations

import backtest


def test_import() -> None:
    assert backtest.__version__ == "0.3.0"
    assert set(backtest.__all__) >= {
        "Cash",
        "Instrument",
        "Market",
        "evaluate",
        "load_scores",
        "ras_lower_bounds",
    }
    for name in backtest.__all__:
        assert hasattr(backtest, name)
