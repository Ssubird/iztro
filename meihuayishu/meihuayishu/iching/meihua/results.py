"""推理与回测结果结构。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class PredictionResult:
    primary_selection: Dict[str, List[int]]
    candidate_pool: Dict[str, List[int]]
    scores: Dict[int, float]
    metadata: Dict[str, Any]


@dataclass
class BacktestRecord:
    period: str
    hits_primary: int
    hits_pool: int
    draw_numbers: List[int]
    predicted: Dict[str, List[int]]
    pool: Dict[str, List[int]]


@dataclass
class BacktestReport:
    records: List[BacktestRecord]

    def hit_rate(self) -> float:
        if not self.records:
            return 0.0
        total_hits = sum(rec.hits_primary for rec in self.records)
        total_drawn = sum(len(rec.draw_numbers) for rec in self.records)
        return total_hits / total_drawn if total_drawn else 0.0

    def pool_hit_rate(self) -> float:
        if not self.records:
            return 0.0
        total_hits = sum(rec.hits_pool for rec in self.records)
        total_drawn = sum(len(rec.draw_numbers) for rec in self.records)
        return total_hits / total_drawn if total_drawn else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "periods": len(self.records),
            "hit_rate": round(self.hit_rate(), 4),
            "pool_hit_rate": round(self.pool_hit_rate(), 4),
        }
