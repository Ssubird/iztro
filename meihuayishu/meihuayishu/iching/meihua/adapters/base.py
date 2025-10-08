"""玩法适配基类。"""

from __future__ import annotations

from typing import Dict, List, Protocol

from ....config.game_config import GameConfig


class GameAdapter(Protocol):
    name: str

    def select(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        ...

    def build_pool(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        ...

    def evaluate(self, selection: Dict[str, List[int]], pool: Dict[str, List[int]], draw: Dict[str, object]) -> tuple[int, int]:
        ...


class BaseAdapter:
    def __init__(self, config: GameConfig):
        self.config = config

    def _top_numbers(self, scores: Dict[int, float], count: int) -> List[int]:
        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [num for num, _ in ordered[:count]]

    def _bottom_numbers(self, scores: Dict[int, float], count: int) -> List[int]:
        ordered = sorted(scores.items(), key=lambda x: x[1])
        return [num for num, _ in ordered[:count]]
