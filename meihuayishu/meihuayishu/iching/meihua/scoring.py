"""号码评分：结合卦象、历史频率与近期走势"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, TypedDict

from .constants import SEASONAL_WEIGHTS, determine_season
from .hexagrams import Hexagram, HexagramState


class HistoryFeatures(TypedDict):
    frequency: Dict[int, float]
    recency: Dict[int, float]
    gap: Dict[int, float]


class NumberScorer:
    """以主互变卦、历史走势与黄历因子为核心的号码评分器"""

    def __init__(
        self,
        *,
        hex_weights: tuple[float, float, float] = (0.5, 0.2, 0.3),
        history_weight: float = 0.3,
        recency_weight: float = 0.25,
        gap_weight: float = 0.15,
        calendar_weight: float = 0.2,
    ) -> None:
        self.hex_weights = hex_weights
        self.history_weight = history_weight
        self.recency_weight = recency_weight
        self.gap_weight = gap_weight
        self.calendar_weight = calendar_weight

    def clone(
        self,
        *,
        hex_weights: Optional[tuple[float, float, float]] = None,
        history_weight: Optional[float] = None,
        recency_weight: Optional[float] = None,
        gap_weight: Optional[float] = None,
        calendar_weight: Optional[float] = None,
    ) -> "NumberScorer":
        """Create a shallow copy with optional overrides."""

        return NumberScorer(
            hex_weights=hex_weights if hex_weights is not None else self.hex_weights,
            history_weight=history_weight if history_weight is not None else self.history_weight,
            recency_weight=recency_weight if recency_weight is not None else self.recency_weight,
            gap_weight=gap_weight if gap_weight is not None else self.gap_weight,
            calendar_weight=calendar_weight if calendar_weight is not None else self.calendar_weight,
        )

    def score(
        self,
        state: HexagramState,
        history_features: HistoryFeatures,
        total_numbers: int,
        reference_time: datetime,
        *,
        element_map: Optional[Dict[int, str]] = None,
        calendar_profile: Optional[Dict[str, object]] = None,
    ) -> Dict[int, float]:
        weights = {
            "primary": self.hex_weights[0],
            "mutual": self.hex_weights[1],
            "changing": self.hex_weights[2],
        }
        season = determine_season(reference_time)
        season_map = SEASONAL_WEIGHTS.get(season, SEASONAL_WEIGHTS["transitional"])

        def weight_hex(hexagram: Optional[Hexagram], label: str) -> Dict[int, float]:
            if not hexagram:
                return {}
            base_number = (hexagram.decimal_value % total_numbers) + 1
            element = hexagram.element
            seasonal_factor = season_map.get(element, 1.0)
            return {
                base_number: weights[label] * 1.5 * seasonal_factor,
                (base_number + 1) % total_numbers or total_numbers: weights[label] * 1.0,
                (base_number - 1) % total_numbers or total_numbers: weights[label] * 0.8,
            }

        scores: Dict[int, float] = {}
        for label, hexagram in {
            "primary": state.primary,
            "mutual": state.mutual,
            "changing": state.changing,
        }.items():
            for number, value in weight_hex(hexagram, label).items():
                scores[number] = scores.get(number, 0.0) + value

        frequency = history_features.get("frequency", {})
        recency = history_features.get("recency", {})
        gap = history_features.get("gap", {})

        for number in range(1, total_numbers + 1):
            freq_score = frequency.get(number, 0.0)
            recent_score = recency.get(number, 0.0)
            gap_score = gap.get(number, 0.0)
            scores[number] = (
                scores.get(number, 0.0)
                + self.history_weight * freq_score
                + self.recency_weight * recent_score
                + self.gap_weight * gap_score
            )

        if calendar_profile and self.calendar_weight > 0.0:
            favored_elements = set(calendar_profile.get("favorable_elements", []) or [])
            unfavorable_elements = set(calendar_profile.get("unfavorable_elements", []) or [])
            favored_numbers = list(calendar_profile.get("favored_numbers", []) or [])

            if element_map:
                for number, element in element_map.items():
                    if element in favored_elements:
                        scores[number] = scores.get(number, 0.0) + self.calendar_weight
                    elif element in unfavorable_elements:
                        scores[number] = scores.get(number, 0.0) - self.calendar_weight * 0.6

            if favored_numbers:
                mod_base = 9
                for number in range(1, total_numbers + 1):
                    remainder = number % mod_base or mod_base
                    if any((remainder == (fav % mod_base or mod_base)) for fav in favored_numbers):
                        scores[number] = scores.get(number, 0.0) + self.calendar_weight * 0.4

        return scores
