def test_import() -> None:
    import backtest

    assert backtest.__all__ == []
