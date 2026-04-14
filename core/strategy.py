from __future__ import annotations

import pandas as pd

from core.strategies import StrategyEngine


_ENGINE = StrategyEngine()


def enhanced_strategy(df: pd.DataFrame) -> str:
    return _ENGINE.evaluate(df, "ma_rsi")