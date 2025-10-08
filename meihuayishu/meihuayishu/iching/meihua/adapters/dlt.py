"""大乐透适配。"""

from __future__ import annotations

from typing import Dict, List

from ....config.game_config import GameConfig

from .base import BaseAdapter


class DLTAdapter(BaseAdapter):
    name = "dlt"

    def __init__(self, config: GameConfig | None = None) -> None:
        super().__init__(config or GameConfig("dlt"))

    def select(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        front = self._top_numbers(scores, 7)
        return {
            "front": sorted(front[:5]),
            "back": [((front[0] + i) % 12) or 12 for i in range(1, 3)],
        }

    def build_pool(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        top = self._top_numbers(scores, 15)
        bottom = self._bottom_numbers(scores, 5)
        return {
            "front_top": sorted(top),
            "front_avoid": sorted(bottom),
            "back_candidates": [((top[i] + i) % 12) or 12 for i in range(3)],
        }

    def evaluate(self, selection: Dict[str, List[int]], pool: Dict[str, List[int]], draw: Dict[str, object]) -> tuple[int, int]:
        drawn = set(draw.get("numbers", []))
        hits_primary = len(drawn.intersection(selection.get("front", [])))
        pool_hits = len(drawn.intersection(set(pool.get("front_top", []))))
        return hits_primary, pool_hits
