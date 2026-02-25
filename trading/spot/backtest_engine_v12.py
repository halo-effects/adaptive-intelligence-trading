# Compatibility shim — all code now lives in backtest_engine_consolidated.py
from .backtest_engine_consolidated import (  # noqa: F401
    DailyScorerConductor,
    SpotBacktestEngineV12,
    LifecyclePhase,
    ExitLot,
    ShortPosition,
    BacktestResult,
    Lot,
    TradeLogEntry,
)
