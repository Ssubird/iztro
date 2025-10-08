"""向后兼容入口：导出拆分后的梅花易数推理组件。"""

from .meihua import (
    Backtester,
    BacktestRecord,
    BacktestReport,
    EventSnapshot,
    MeihuaHexagramEngine,
    MeihuaInferenceFramework,
    NumberScorer,
    PredictionResult,
)

__all__ = [
    "Backtester",
    "BacktestRecord",
    "BacktestReport",
    "EventSnapshot",
    "MeihuaHexagramEngine",
    "MeihuaInferenceFramework",
    "NumberScorer",
    "PredictionResult",
]
