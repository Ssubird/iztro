"""起卦与演卦引擎。"""

from __future__ import annotations

from .events import EventSnapshot
from .hexagrams import HexagramState, HexagramSeed, build_changing_hexagram, build_mutual_hexagram, compose_hexagram


class MeihuaHexagramEngine:
    """实现《梅花易数》年月日时起卦 → 互卦 → 变卦流程。"""

    def __init__(self, *, moving_rule: str = "standard") -> None:
        self.moving_rule = moving_rule

    def generate_seed(self, event: EventSnapshot) -> HexagramSeed:
        dt = event.timestamp
        base_sum = dt.year + dt.month + dt.day
        upper_idx = base_sum % 8 or 8
        lower_sum = base_sum + dt.hour
        lower_idx = lower_sum % 8 or 8
        moving_sum = base_sum + lower_sum
        moving = moving_sum % 6 or 6
        if self.moving_rule == "weighted" and event.reference_numbers:
            weight = sum(event.reference_numbers)
            moving = ((moving + weight) % 6) or 6
        return HexagramSeed(
            upper_index=upper_idx - 1,
            lower_index=lower_idx - 1,
            moving_lines=[moving],
        )

    def build_state(self, seed: HexagramSeed) -> HexagramState:
        primary = compose_hexagram(seed.upper_index, seed.lower_index)
        mutual = build_mutual_hexagram(primary)
        changing = build_changing_hexagram(primary, seed.moving_lines)
        return HexagramState(primary=primary, mutual=mutual, changing=changing, moving_lines=seed.moving_lines)
