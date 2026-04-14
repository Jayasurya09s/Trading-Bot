def test_repository_smoke():
    from core.strategies import StrategyEngine

    assert "ma_rsi" in StrategyEngine().available_strategies()
