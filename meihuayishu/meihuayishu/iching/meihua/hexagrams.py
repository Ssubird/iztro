"""卦象结构与演卦运算。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class HexagramSeed:
    """依据事件数字求得的上卦、下卦与动爻。"""

    upper_index: int
    lower_index: int
    moving_lines: List[int]


@dataclass
class Hexagram:
    """六十四卦的抽象表示。"""

    name: str
    element: str
    lines: Tuple[int, ...]
    index: int

    @property
    def decimal_value(self) -> int:
        value = 0
        for idx, bit in enumerate(self.lines):
            value += bit << idx
        return value


@dataclass
class HexagramState:
    """主卦、互卦、变卦组成的演卦结果。"""

    primary: Hexagram
    mutual: Optional[Hexagram]
    changing: Optional[Hexagram]
    moving_lines: List[int]


TRIGRAMS: Tuple[Dict[str, object], ...] = (
    {"name": "乾", "element": "金", "lines": (1, 1, 1)},
    {"name": "兑", "element": "金", "lines": (0, 1, 1)},
    {"name": "离", "element": "火", "lines": (1, 0, 1)},
    {"name": "震", "element": "木", "lines": (0, 0, 1)},
    {"name": "巽", "element": "木", "lines": (1, 1, 0)},
    {"name": "坎", "element": "水", "lines": (0, 1, 0)},
    {"name": "艮", "element": "土", "lines": (1, 0, 0)},
    {"name": "坤", "element": "土", "lines": (0, 0, 0)},
)


def compose_hexagram(upper_index: int, lower_index: int) -> Hexagram:
    upper = TRIGRAMS[upper_index % 8]
    lower = TRIGRAMS[lower_index % 8]
    lines = lower["lines"] + upper["lines"]
    name = f"{upper['name']}{lower['name']}"
    element = upper["element"] if upper["element"] == lower["element"] else upper["element"]
    return Hexagram(name=name, element=str(element), lines=lines, index=upper_index * 8 + lower_index)


def build_mutual_hexagram(primary: Hexagram) -> Optional[Hexagram]:
    lines = primary.lines
    if len(lines) != 6:
        return None
    middle = lines[1:5]
    lower = middle[:3]
    upper = middle[1:]
    if lower == upper == (1, 1, 1):
        return None
    upper_idx = next((i for i, tri in enumerate(TRIGRAMS) if tri["lines"] == upper), 0)
    lower_idx = next((i for i, tri in enumerate(TRIGRAMS) if tri["lines"] == lower), 0)
    return compose_hexagram(upper_idx, lower_idx)


def build_changing_hexagram(primary: Hexagram, moving_lines: Sequence[int]) -> Optional[Hexagram]:
    if not moving_lines:
        return None
    lines = list(primary.lines)
    for line in moving_lines:
        idx = max(1, min(6, line)) - 1
        lines[idx] = 1 - lines[idx]
    lower = tuple(lines[:3])
    upper = tuple(lines[3:])
    upper_idx = next((i for i, tri in enumerate(TRIGRAMS) if tri["lines"] == upper), 0)
    lower_idx = next((i for i, tri in enumerate(TRIGRAMS) if tri["lines"] == lower), 0)
    return compose_hexagram(upper_idx, lower_idx)
