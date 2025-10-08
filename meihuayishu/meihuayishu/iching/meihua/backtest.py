"""窗口化回测与参数优化。"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from itertools import product
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from .events import EventSnapshot
from .results import BacktestRecord, BacktestReport

if TYPE_CHECKING:  # pragma: no cover
    from .framework import MeihuaInferenceFramework


class Backtester:
    def __init__(self, framework: "MeihuaInferenceFramework") -> None:
        self.framework = framework

    def run_backtest(self, window_size: int = 100, step: int = 1) -> BacktestReport:
        data = self.framework.historical_data
        if not data:
            self.framework.update_data()
            data = self.framework.historical_data

        records: List[BacktestRecord] = []
        for idx in range(window_size, len(data), step):
            history_window = data[:idx]
            target_draw = data[idx]
            self.framework.set_historical_data(history_window)
            event_time = datetime.strptime(target_draw["timestamp"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            snapshot = EventSnapshot(
                timestamp=event_time,
                reference_numbers=history_window[-1]["numbers"] if history_window else None,
            )
            result = self.framework.predict(event=snapshot)
            hits_primary, hits_pool = self.framework.adapter.evaluate(
                result.primary_selection,
                result.candidate_pool,
                target_draw,
            )
            records.append(
                BacktestRecord(
                    period=target_draw.get("period", str(idx)),
                    hits_primary=hits_primary,
                    hits_pool=hits_pool,
                    draw_numbers=target_draw.get("numbers", []),
                    predicted=result.primary_selection,
                    pool=result.candidate_pool,
                )
            )

        self.framework.set_historical_data(data)
        return BacktestReport(records=records)

    def optimize_parameters(
        self,
        hex_weight_grid: Sequence[Tuple[float, float, float]],
        history_weight_grid: Sequence[float],
        window_size: int = 100,
        step: int = 1,
    ) -> Tuple[Tuple[float, float, float], float, BacktestReport]:
        best_score = -math.inf
        best_config: Tuple[float, float, float] = self.framework.scorer.hex_weights
        best_history_weight = self.framework.scorer.history_weight
        best_report: Optional[BacktestReport] = None
        base_recency_weight = self.framework.scorer.recency_weight
        base_gap_weight = self.framework.scorer.gap_weight
        base_calendar_weight = self.framework.scorer.calendar_weight

        for hex_weights, history_weight in product(hex_weight_grid, history_weight_grid):
            self.framework.scorer = self.framework.scorer.__class__(
                hex_weights=hex_weights,
                history_weight=history_weight,
                recency_weight=base_recency_weight,
                gap_weight=base_gap_weight,
                calendar_weight=base_calendar_weight,
            )
            report = self.run_backtest(window_size=window_size, step=step)
            score = report.hit_rate() + 0.5 * report.pool_hit_rate()
            if score > best_score:
                best_score = score
                best_config = hex_weights
                best_history_weight = history_weight
                best_report = report

        if best_report is None:
            raise RuntimeError("参数优化未能生成有效报告")

        self.framework.scorer = self.framework.scorer.__class__(
            hex_weights=best_config,
            history_weight=best_history_weight,
            recency_weight=base_recency_weight,
            gap_weight=base_gap_weight,
            calendar_weight=base_calendar_weight,
        )
        return best_config, best_history_weight, best_report
