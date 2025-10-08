"""梅花易数推理框架主流程。"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from ...config.game_config import GameConfig

from .adapters.base import GameAdapter
from .adapters.dlt import DLTAdapter
from .adapters.keno8 import Keno8Adapter
from .adapters.ssq import SSQAdapter
from .backtest import Backtester
from .calendar_utils import (
    CalendarProfile,
    ELEMENT_OVERCOME,
    SYNODIC_MONTH,
    build_calendar_profile,
    moon_age_days,
)
from .data import LotteryDataManager
from .engine import MeihuaHexagramEngine
from .events import EventSnapshot
from .hexagrams import HexagramState
from .results import PredictionResult
from .scoring import HistoryFeatures, NumberScorer
from .constants import determine_season


ADAPTER_MAP: Dict[str, GameAdapter] = {
    "ssq": SSQAdapter(),
    "dlt": DLTAdapter(),
    "keno8": Keno8Adapter(),
}



@dataclass(frozen=True)
class EvolutionGuidance:
    """推理框架导出的遗传算法指导参数。"""

    iterations: int
    population: int
    mutation_strength: float
    mutation_decay: float
    crossover_center: float
    crossover_width: float
    hex_focus: tuple[float, float, float]
    hex_focus_weight: float
    half_life_bounds: tuple[float, float]
    window_bounds: tuple[int, int]
    exploration_bias: float
    seed: int | None = None

class MeihuaInferenceFramework:
    """整合“起卦 → 演卦 → 数值 → 玩法 → 评估”的全流程。"""

    def __init__(
        self,
        game_type: str = "ssq",
        *,
        moving_rule: str = "standard",
        hex_weights: tuple[float, float, float] = (0.5, 0.2, 0.3),
        history_weight: float = 0.4,
        recency_weight: float = 0.25,
        gap_weight: float = 0.15,
        calendar_weight: float = 0.2,
        history_half_life: float = 90.0,
        prefer_local_cache: bool = True,
        dynamic_weights: bool = True,
    ) -> None:
        if game_type not in ADAPTER_MAP:
            raise ValueError(f"不支持的玩法: {game_type}")
        self.game_type = game_type
        self.config = GameConfig(game_type)
        self.hex_engine = MeihuaHexagramEngine(moving_rule=moving_rule)
        self.scorer = NumberScorer(
            hex_weights=hex_weights,
            history_weight=history_weight,
            recency_weight=recency_weight,
            gap_weight=gap_weight,
            calendar_weight=calendar_weight,
        )
        self.adapter = ADAPTER_MAP[game_type]
        self.data_manager = LotteryDataManager(game_type, prefer_local=prefer_local_cache)
        self.historical_data: List[Dict[str, Any]] = []
        self._initial_config = {
            "hex_weights": hex_weights,
            "history_weight": history_weight,
            "recency_weight": recency_weight,
            "gap_weight": gap_weight,
            "calendar_weight": calendar_weight,
            "history_half_life": history_half_life,
        }
        self.dynamic_weights = dynamic_weights
        self.base_history_half_life = history_half_life
        self.history_half_life = history_half_life
        self.base_calendar_weight = calendar_weight
        self.calendar_weight = calendar_weight
        self._parameter_override: Optional[Dict[str, object]] = None
        self._active_history_window: Optional[int] = None
        self._last_mystic_profile: Optional[Dict[str, object]] = None
        self._last_evolution_guidance: Optional[EvolutionGuidance] = None
        self.backtester = Backtester(self)
        self._timestamp_cache: Dict[str, datetime] = {}


    # ------------------------------------------------------------------
    # 数据维护
    # ------------------------------------------------------------------

    def update_data(self, *, force_update: bool = False, max_periods: Optional[int] = None) -> None:
        self.historical_data = self.data_manager.load(max_periods=max_periods, force_update=force_update)
        self._timestamp_cache.clear()

    def set_historical_data(self, data: Sequence[Dict[str, Any]]) -> None:
        self.historical_data = list(data)
        self._timestamp_cache.clear()

    # ------------------------------------------------------------------
    # 推理核心
    # ------------------------------------------------------------------

    def _parse_history_timestamp(self, value: Any, fallback_days: int) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            cached = self._timestamp_cache.get(value)
            if cached is not None:
                return cached
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M"):
                try:
                    parsed = datetime.strptime(value, fmt)
                except ValueError:
                    continue
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                self._timestamp_cache[value] = parsed
                return parsed
        return datetime.now(timezone.utc) - timedelta(days=fallback_days)

    def _history_features(
        self,
        reference_time: datetime,
        *,
        half_life: Optional[float] = None,
        history_span: Optional[int] = None,
    ) -> HistoryFeatures:
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        if not self.historical_data:
            return {"frequency": {}, "recency": {}, "gap": {}}

        if history_span and history_span > 0:
            source = self.historical_data[-history_span:]
        else:
            source = self.historical_data

        frequency: Dict[int, float] = {}
        recency: Dict[int, float] = {}
        last_seen: Dict[int, int] = {}
        total_draws = len(source)
        half_life_value = max(half_life if half_life is not None else self.base_history_half_life, 1.0)
        reference_moon_age = moon_age_days(reference_time)

        for idx, draw in enumerate(source):
            numbers = draw.get("numbers", []) or []
            draw_time = draw.get("_parsed_timestamp")
            if not isinstance(draw_time, datetime):
                timestamp_value = draw.get("timestamp")
                draw_time = self._parse_history_timestamp(timestamp_value, fallback_days=total_draws - idx)
                draw["_parsed_timestamp"] = draw_time
            if draw_time.tzinfo is None:
                draw_time = draw_time.replace(tzinfo=timezone.utc)
                draw["_parsed_timestamp"] = draw_time
            delta_days = max((reference_time - draw_time).total_seconds() / 86400.0, 0.0)
            decay = math.exp(-delta_days / half_life_value)

            draw_moon_age = draw.get("_moon_age")
            if not isinstance(draw_moon_age, (int, float)):
                draw_moon_age = moon_age_days(draw_time)
                draw["_moon_age"] = draw_moon_age
            phase_delta = abs(reference_moon_age - draw_moon_age)
            phase_delta = min(phase_delta, SYNODIC_MONTH - phase_delta)
            cycle_similarity = max(1.0 - (phase_delta / (SYNODIC_MONTH / 2.0)), 0.0)
            cycle_boost = 0.7 + 0.3 * cycle_similarity
            recency_boost = 0.6 + 0.4 * cycle_similarity

            for number in numbers:
                frequency[number] = frequency.get(number, 0.0) + cycle_boost
                recency[number] = recency.get(number, 0.0) + decay * recency_boost
                last_seen[number] = idx

        if frequency:
            max_freq = max(frequency.values()) or 1.0
            frequency = {num: val / max_freq for num, val in frequency.items()}
        if recency:
            max_recency = max(recency.values()) or 1.0
            recency = {num: val / max_recency for num, val in recency.items()}

        denominator = max(total_draws - 1, 1)
        gap_scores: Dict[int, float] = {}
        for number in range(1, self.config.total_numbers + 1):
            if number not in last_seen:
                gap_scores[number] = 1.0
            else:
                gap_scores[number] = (total_draws - 1 - last_seen[number]) / denominator if denominator else 0.0

        return {"frequency": frequency, "recency": recency, "gap": gap_scores}


    @staticmethod
    def _normalize_element(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        mapping = {
            "木": "木",
            "火": "火",
            "土": "土",
            "金": "金",
            "水": "水",
            "ľ": "木",
            "ˮ": "水",
            "��": "火",
            "��": "土",
            "��": "金",
        }
        return mapping.get(value, value)

    def _number_element_map(
        self,
        *,
        reference_time: datetime,
        calendar_profile: CalendarProfile,
        state: HexagramState,
        mystic: Optional[Dict[str, object]] = None,
    ) -> Dict[int, str]:
        cycle = self._dynamic_element_cycle(calendar_profile, state, mystic=mystic)
        if not cycle:
            cycle = [self._normalize_element(elem) or elem for elem in ["木", "火", "土", "金", "水"]]

        base_offset = reference_time.toordinal()
        if state.primary:
            base_offset += state.primary.decimal_value
        if state.moving_lines:
            base_offset += sum(state.moving_lines)

        favored_numbers = calendar_profile.favored_numbers or []
        if favored_numbers:
            cycle_len = len(cycle)
            base_offset += sum(num % cycle_len for num in favored_numbers)

        if mystic:
            numeric_spell = int(mystic.get("numeric_spell") or 1)
            base_offset += numeric_spell * 3
            scalar = float(mystic.get("scalar") or 0.0)
            base_offset += int(scalar * 11)

        cycle_len = len(cycle)
        element_map: Dict[int, str] = {}
        for idx, number in enumerate(range(1, self.config.total_numbers + 1), start=1):
            element = cycle[(base_offset + idx - 1) % cycle_len]
            element_map[number] = element
        return element_map

    def _dynamic_element_cycle(
        self,
        calendar_profile: CalendarProfile,
        state: HexagramState,
        mystic: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        sequence: List[str] = []
        append = sequence.append

        if mystic and mystic.get("preferred_elements"): 
            for element in mystic["preferred_elements"]:
                normalized = self._normalize_element(element) or element
                if normalized not in sequence:
                    append(normalized)

        for element in calendar_profile.favorable_elements:
            normalized = self._normalize_element(element) or element
            if normalized not in sequence:
                append(normalized)

        for key in ("year", "month", "day", "hour"):
            element = calendar_profile.elements.get(key)
            normalized = self._normalize_element(element) if element else None
            if normalized and normalized not in sequence:
                append(normalized)

        for hexagram in (state.primary, state.mutual, state.changing):
            if hexagram and hexagram.element:
                normalized = self._normalize_element(hexagram.element) or hexagram.element
                if normalized not in sequence:
                    append(normalized)

        for element in calendar_profile.unfavorable_elements:
            normalized = self._normalize_element(element) or element
            if normalized and normalized not in sequence:
                append(normalized)

        base_cycle = [self._normalize_element(elem) or elem for elem in ["木", "火", "土", "金", "水"]]
        for element in base_cycle:
            if element not in sequence:
                append(element)
        return sequence

    def _mystic_bias(
        self,
        calendar_profile: CalendarProfile,
        reference_time: datetime,
    ) -> Dict[str, object]:
        stem_weights = {
            "甲": 1,
            "乙": 2,
            "丙": 3,
            "丁": 4,
            "戊": 5,
            "己": 6,
            "庚": 7,
            "辛": 8,
            "壬": 9,
            "癸": 10,
        }
        branch_weights = {
            "子": 1,
            "丑": 2,
            "寅": 3,
            "卯": 4,
            "辰": 5,
            "巳": 6,
            "午": 7,
            "未": 8,
            "申": 9,
            "酉": 10,
            "戌": 11,
            "亥": 12,
        }
        palace_to_element = {
            1: "水",
            2: "土",
            3: "木",
            4: "金",
            5: "火",
            6: "水",
            7: "金",
            8: "土",
            9: "火",
        }

        stems = calendar_profile.ganzhi
        stem_score = 0
        branch_score = 0
        for key in ("year", "month", "day", "hour"):
            value = stems.get(key)
            if not value:
                continue
            stem, branch = value
            stem_score += stem_weights.get(stem, 5)
            branch_score += branch_weights.get(branch, 6)
        palace = (stem_score + branch_score) % 9 or 9
        scalar = (palace - 5) / 5.0

        preferred_elements: List[str] = []
        favored = palace_to_element.get(palace)
        if favored:
            preferred_elements.append(self._normalize_element(favored) or favored)
        moon = calendar_profile.moon or {}
        illumination = float(moon.get("illumination") or 0.5)
        numeric_spell = int((stem_score * max(branch_score, 1)) % 9) + 1

        rng_seed = int(reference_time.strftime("%Y%m%d%H")) + palace * 17 + numeric_spell * 7
        rng = random.Random(rng_seed)
        if not preferred_elements:
            preferred_elements.append(["木", "火", "土", "金", "水"][rng.randint(0, 4)])
        extras = [elem for elem in ["木", "火", "土", "金", "水"] if elem not in preferred_elements]
        rng.shuffle(extras)
        preferred_elements.extend(extras)

        return {
            "palace": palace,
            "scalar": scalar,
            "preferred_elements": [self._normalize_element(elem) or elem for elem in preferred_elements],
            "numeric_spell": numeric_spell,
            "illumination": illumination,
        }

    def _compute_base_parameters(
        self,
        reference_time: datetime,
        calendar_profile: CalendarProfile,
        state: HexagramState,
        event: EventSnapshot,
    ) -> Dict[str, object]:
        base = dict(self._initial_config)
        mystic = self._mystic_bias(calendar_profile, reference_time)
        moon = calendar_profile.moon or {}
        illumination = float(moon.get("illumination") or 0.5)
        favored = calendar_profile.favorable_elements or []
        unfavorable = calendar_profile.unfavorable_elements or []
        favor_delta = len(favored) - len(unfavorable)
        moving_count = len(state.moving_lines or [])
        season = determine_season(reference_time)

        rng_seed = int(reference_time.strftime("%Y%m%d%H")) + len(favored) * 19 + moving_count * 23
        rng = random.Random(rng_seed)

        hex_weights = list(base["hex_weights"])
        season_bias = {
            "spring": (1.12, 1.02, 0.96),
            "summer": (1.05, 1.05, 0.95),
            "autumn": (1.08, 1.0, 1.05),
            "winter": (0.95, 1.02, 1.12),
            "transitional": (1.0, 1.0, 1.0),
        }
        bias = season_bias.get(season, season_bias["transitional"])
        for idx in range(3):
            hex_weights[idx] *= bias[idx]
        if moving_count:
            change_push = min(moving_count / 3.0, 1.5)
            hex_weights[2] += change_push * 0.2
            hex_weights[0] = max(hex_weights[0] - change_push * 0.1, 0.05)
        if mystic["preferred_elements"]:
            first = mystic["preferred_elements"][0]
            if first in ("木", "火"):
                hex_weights[0] *= 1.05
            elif first in ("金", "水"):
                hex_weights[1] *= 1.05
        total_hex = sum(hex_weights) or 1.0
        hex_weights = tuple(val / total_hex for val in hex_weights)

        history_weight = base["history_weight"] * (1.0 + 0.12 * -mystic["scalar"])
        recency_weight = base["recency_weight"] * (0.8 + 0.4 * illumination)
        gap_weight = base["gap_weight"] * (0.9 + 0.1 * rng.uniform(0.8, 1.2))
        calendar_weight = base["calendar_weight"] * (0.7 + 0.3 * (len(favored) / 6.0 + 0.3))

        total = history_weight + recency_weight + gap_weight + calendar_weight
        base_total = self._initial_config["history_weight"] + self._initial_config["recency_weight"] + self._initial_config["gap_weight"] + self._initial_config["calendar_weight"]
        scale = base_total / total if total else 1.0
        history_weight *= scale
        recency_weight *= scale
        gap_weight *= scale
        calendar_weight *= scale

        half_life = max(15.0, base["history_half_life"] * (0.8 + 0.6 * (1.0 - illumination)))
        half_life *= 1.0 + mystic["scalar"] * 0.15
        half_life = max(15.0, half_life)

        base_window = int(max(60, base["history_half_life"] * (1.3 - mystic["scalar"])) )
        base_window += int(rng.uniform(0, 25))
        if favor_delta > 0:
            base_window = int(base_window * 0.95)
        base_window = max(40, base_window)

        return {
            "hex_weights": hex_weights,
            "history_weight": history_weight,
            "recency_weight": recency_weight,
            "gap_weight": gap_weight,
            "calendar_weight": calendar_weight,
            "history_half_life": half_life,
            "history_window": base_window,
            "dynamic": True,
            "mystic": mystic,
        }

    def infer_evolution_guidance(
        self,
        *,
        event: Optional[EventSnapshot] = None,
        window_size: Optional[int] = None,
        step: Optional[int] = None,
    ) -> EvolutionGuidance:
        """根据当前卦象上下文推导遗传算法的关键参数。"""
        if not self.historical_data:
            self.update_data()
        event_snapshot = event or EventSnapshot()
        reference_time = event_snapshot.timestamp or datetime.now(timezone.utc)
        state = self._build_state(event_snapshot)
        calendar_profile = self._build_calendar_profile(reference_time, state)
        if self._parameter_override is not None:
            base_params = dict(self._parameter_override)
        else:
            base_params = self._compute_base_parameters(reference_time, calendar_profile, state, event_snapshot)
        mystic = base_params.get("mystic") or {}
        scalar = float(mystic.get("scalar") or 0.0)
        moving_lines = len(state.moving_lines or [])
        illumination = float((calendar_profile.moon or {}).get("illumination") or 0.5)
        favored = calendar_profile.favorable_elements or []
        unfavorable = calendar_profile.unfavorable_elements or []
        favor_delta = len(favored) - len(unfavorable)
        history_size = max(len(self.historical_data), 1)
        window_size = window_size or max(60, min(history_size, 180))
        step = max(1, step or 1)
        season = determine_season(reference_time)

        def clamp(value: float, lower: float, upper: float) -> float:
            return max(lower, min(upper, value))

        log_factor = math.log1p(history_size)
        season_factor = {
            "spring": 1.05,
            "summer": 1.0,
            "autumn": 1.08,
            "winter": 1.12,
            "transitional": 1.0,
        }.get(season, 1.0)
        coverage_ratio = clamp(window_size / max(history_size, 1), 0.3, 1.1)
        exploration_push = max(0.0, -scalar) * 0.18 + abs(favor_delta) * 0.02 + (0.5 - illumination) * 0.25
        moving_push = moving_lines * 0.08

        iterations = 48.0 + log_factor * 6.0
        iterations *= season_factor
        iterations *= 1.0 + moving_push + exploration_push
        iterations *= 0.9 + 0.25 * coverage_ratio
        iterations = clamp(iterations, 36.0, 180.0)

        population = 10.0 + log_factor * 1.2
        population += moving_lines * 0.5
        population += max(0.0, -scalar) * 3.0
        population += max(0, favor_delta) * 0.35
        population *= 1.0 + (0.5 - illumination) * 0.12
        population = clamp(population, 8.0, 28.0)

        hex_weights = base_params.get("hex_weights", self._initial_config["hex_weights"])
        base_hex_focus = tuple(float(value) for value in hex_weights)
        hex_focus_weight = clamp(0.22 + max(0.0, scalar) * 0.28 + moving_lines * 0.04, 0.18, 0.55)

        exploration_bias = clamp(
            0.4 + max(0.0, -scalar) * 0.45 + moving_lines * 0.08 + abs(favor_delta) * 0.05,
            0.2,
            1.0,
        )

        mutation_strength = clamp(0.12 * (1.0 + exploration_bias * 0.6), 0.06, 0.28)
        mutation_decay = clamp(0.85 - exploration_bias * 0.15 + max(0.0, scalar) * 0.12, 0.6, 1.05)

        crossover_center = clamp(0.5 + scalar * 0.05 - favor_delta * 0.01, 0.35, 0.65)
        crossover_width = clamp(0.18 + exploration_bias * 0.1 - max(0.0, scalar) * 0.06, 0.1, 0.28)

        base_half_life = float(base_params.get("history_half_life") or self.base_history_half_life or 90.0)
        half_min = clamp(base_half_life * (0.65 - scalar * 0.08), 12.0, base_half_life * 0.95)
        half_max = clamp(base_half_life * (1.4 + exploration_bias * 0.25), base_half_life * 1.05, base_half_life * 2.1)
        if half_max <= half_min:
            half_max = half_min + 5.0

        base_window = int(base_params.get("history_window") or max(60, base_half_life * 1.3))
        window_min = max(40, int(base_window * (0.75 - scalar * 0.08)))
        window_max = max(window_min + 12, int(base_window * (1.35 + exploration_bias * 0.25)))

        seed_source = int(reference_time.strftime("%Y%m%d%H"))
        seed = seed_source ^ (len(favored) << 5) ^ (len(unfavorable) << 7) ^ (history_size << 1) ^ step

        guidance = EvolutionGuidance(
            iterations=int(round(iterations)),
            population=int(round(population)),
            mutation_strength=mutation_strength,
            mutation_decay=mutation_decay,
            crossover_center=crossover_center,
            crossover_width=crossover_width,
            hex_focus=base_hex_focus,
            hex_focus_weight=hex_focus_weight,
            half_life_bounds=(half_min, half_max),
            window_bounds=(window_min, window_max),
            exploration_bias=exploration_bias,
            seed=seed,
        )
        self._last_evolution_guidance = guidance
        return guidance

    def set_parameter_override(self, override: Optional[Dict[str, object]]) -> None:
        self._parameter_override = override

    def clear_parameter_override(self) -> None:
        self._parameter_override = None



    def _derive_dynamic_weights(
        self,
        base_scorer: NumberScorer,
        state: HexagramState,
        calendar_profile: CalendarProfile,
        reference_time: datetime,
    ) -> tuple[Dict[str, float], float]:
        def clamp(value: float, lower: float, upper: float) -> float:
            return max(lower, min(upper, value))

        base_hex = list(base_scorer.hex_weights)
        moving_count = len(state.moving_lines or [])
        if moving_count:
            change_bias = clamp(moving_count / 3.0, 0.0, 1.5)
            base_hex[2] += change_bias * 0.18
            base_hex[0] = max(base_hex[0] - change_bias * 0.1, 0.05)
            base_hex[1] += change_bias * 0.04
        total_hex = sum(base_hex) or 1.0
        hex_weights = tuple(value / total_hex for value in base_hex)

        moon = calendar_profile.moon or {}
        illumination = float(moon.get("illumination") or 0.5)
        favored_count = len(calendar_profile.favorable_elements or [])
        unfavorable_count = len(calendar_profile.unfavorable_elements or [])
        favor_delta = favored_count - unfavorable_count

        history_weight = base_scorer.history_weight * (0.9 + 0.1 * clamp(-favor_delta / 5.0, -0.6, 0.6))
        recency_weight = base_scorer.recency_weight * (0.75 + 0.45 * illumination)
        gap_weight = base_scorer.gap_weight * (0.9 + 0.1 * clamp(favor_delta / 5.0, -0.6, 0.6))
        calendar_weight = base_scorer.calendar_weight * (0.65 + 0.35 * clamp(favored_count / 6.0, 0.0, 1.2))

        season = determine_season(reference_time)
        if season == "spring":
            recency_weight *= 1.12
        elif season == "summer":
            gap_weight *= 1.08
        elif season == "autumn":
            history_weight *= 1.1
        elif season == "winter":
            calendar_weight *= 1.15

        base_total = base_scorer.history_weight + base_scorer.recency_weight + base_scorer.gap_weight + base_scorer.calendar_weight
        dynamic_total = history_weight + recency_weight + gap_weight + calendar_weight
        scale = base_total / dynamic_total if dynamic_total else 1.0
        history_weight *= scale
        recency_weight *= scale
        gap_weight *= scale
        calendar_weight *= scale

        half_life = clamp(self.base_history_half_life * (0.7 + 0.5 * (1.0 - illumination)), 12.0, self.base_history_half_life * 1.6)

        return (
            {
                "hex_weights": hex_weights,
                "history_weight": history_weight,
                "recency_weight": recency_weight,
                "gap_weight": gap_weight,
                "calendar_weight": calendar_weight,
            },
            half_life,
        )


    def _blue_scores(self, reference_time: datetime, horizon: int) -> Dict[int, float]:
        if self.game_type != "ssq":
            return {}
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        if horizon <= 0 or not self.historical_data:
            horizon = len(self.historical_data)
        subset = self.historical_data[-horizon:] if horizon < len(self.historical_data) else self.historical_data
        frequency: Dict[int, float] = {i: 0.0 for i in range(1, 17)}
        recency: Dict[int, float] = {i: 0.0 for i in range(1, 17)}
        decay_half_life = max(horizon / 2.0, 1.0)
        for idx, draw in enumerate(reversed(subset)):
            blue = draw.get("special") or draw.get("blue") or draw.get("blue_number")
            if not isinstance(blue, int):
                continue
            decay = math.exp(-idx / decay_half_life)
            frequency[blue] = frequency.get(blue, 0.0) + 1.0
            recency[blue] = recency.get(blue, 0.0) + decay
        max_freq = max(frequency.values()) or 1.0
        max_recency = max(recency.values()) or 1.0
        scores: Dict[int, float] = {}
        for num in range(1, 17):
            freq_score = frequency.get(num, 0.0) / max_freq
            recency_score = recency.get(num, 0.0) / max_recency
            scores[num] = 0.6 * freq_score + 0.4 * recency_score
        return scores

    def _build_state(self, event: EventSnapshot) -> HexagramState:
        seed = self.hex_engine.generate_seed(event)
        return self.hex_engine.build_state(seed)

    def _build_calendar_profile(self, reference_time: datetime, state: HexagramState) -> CalendarProfile:
        profile = build_calendar_profile(reference_time)
        profile.elements = {key: self._normalize_element(value) for key, value in profile.elements.items()}
        profile.favorable_elements = [self._normalize_element(value) or value for value in profile.favorable_elements]
        profile.unfavorable_elements = [self._normalize_element(value) or value for value in profile.unfavorable_elements]

        favored = set(profile.favorable_elements)
        unfavorable = set(profile.unfavorable_elements)
        for hexagram in (state.primary, state.mutual, state.changing):
            if not hexagram or not hexagram.element:
                continue
            favored.add(self._normalize_element(hexagram.element) or hexagram.element)
            overcome = ELEMENT_OVERCOME.get(hexagram.element)
            if overcome:
                unfavorable.add(self._normalize_element(overcome) or overcome)
        profile.favorable_elements = sorted(favored)
        profile.unfavorable_elements = sorted(unfavorable)
        return profile

    def recommend_guard_sets(
        self,
        *,
        scores: Dict[int, float],
        reference_time: datetime,
        event: Optional[EventSnapshot] = None,
        num_sets: int = 3,
        horizon: int = 120,
        extra_blue: int = 5,
    ) -> List[Dict[str, List[int]]]:
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        event_snapshot = event or EventSnapshot(timestamp=reference_time)
        state = self._build_state(event_snapshot)
        calendar_profile = self._build_calendar_profile(reference_time, state)
        element_map = self._number_element_map(
            reference_time=reference_time,
            calendar_profile=calendar_profile,
            state=state,
        )

        profile_dict = asdict(calendar_profile)
        if self._last_mystic_profile:
            profile_dict["mystic"] = self._last_mystic_profile
        guard_kwargs: Dict[str, Any] = {
            "element_map": element_map,
            "calendar_profile": profile_dict,
        }

        if self.game_type == "ssq":
            blue_scores = self._blue_scores(reference_time, horizon)
            guard_kwargs.update({"extra_blue": extra_blue, "blue_scores": blue_scores})

        guard_method = getattr(self.adapter, "guard_sets", None)
        if not callable(guard_method):
            return []

        return guard_method(
            scores,
            num_sets=num_sets,
            **guard_kwargs,
        )


    def predict(self, event: Optional[EventSnapshot] = None) -> PredictionResult:
        if not self.historical_data:
            self.update_data()

        event = event or EventSnapshot()
        reference_time = event.timestamp or datetime.now(timezone.utc)

        state = self._build_state(event)
        calendar_profile = self._build_calendar_profile(reference_time, state)

        if self._parameter_override is not None:
            base_params = dict(self._parameter_override)
        else:
            base_params = self._compute_base_parameters(reference_time, calendar_profile, state, event)

        mystic = base_params.get("mystic")
        self._last_mystic_profile = mystic
        element_map = self._number_element_map(
            reference_time=reference_time,
            calendar_profile=calendar_profile,
            state=state,
            mystic=mystic,
        )

        base_hex_weights = base_params.get("hex_weights", self._initial_config["hex_weights"])
        base_history_weight = base_params.get("history_weight", self._initial_config["history_weight"])
        base_recency_weight = base_params.get("recency_weight", self._initial_config["recency_weight"])
        base_gap_weight = base_params.get("gap_weight", self._initial_config["gap_weight"])
        base_calendar_weight = base_params.get("calendar_weight", self._initial_config["calendar_weight"])
        base_half_life = base_params.get("history_half_life", self.base_history_half_life)
        self.base_history_half_life = base_half_life
        self.base_calendar_weight = base_calendar_weight
        self._active_history_window = base_params.get("history_window")

        base_scorer = self.scorer.clone(
            hex_weights=base_hex_weights,
            history_weight=base_history_weight,
            recency_weight=base_recency_weight,
            gap_weight=base_gap_weight,
            calendar_weight=base_calendar_weight,
        )

        apply_dynamic = self.dynamic_weights
        if base_params.get("dynamic") is False:
            apply_dynamic = False

        active_scorer = base_scorer
        effective_half_life = base_half_life
        derived_weights: Optional[Dict[str, object]] = None
        if apply_dynamic:
            derived_weights, effective_half_life = self._derive_dynamic_weights(
                base_scorer,
                state,
                calendar_profile,
                reference_time,
            )
            active_scorer = base_scorer.clone(
                hex_weights=derived_weights["hex_weights"],
                history_weight=derived_weights["history_weight"],
                recency_weight=derived_weights["recency_weight"],
                gap_weight=derived_weights["gap_weight"],
                calendar_weight=derived_weights["calendar_weight"],
            )

        history_features = self._history_features(
            reference_time,
            half_life=effective_half_life,
            history_span=self._active_history_window,
        )
        calendar_dict = asdict(calendar_profile)
        calendar_dict["local_time"] = calendar_profile.local_time.isoformat()
        calendar_dict["element_cycle"] = self._dynamic_element_cycle(
            calendar_profile,
            state,
            mystic=mystic,
        )
        if mystic:
            calendar_dict["mystic"] = mystic

        scores = active_scorer.score(
            state,
            history_features,
            self.config.total_numbers,
            reference_time,
            element_map=element_map,
            calendar_profile=calendar_dict,
        )
        primary = self.adapter.select(scores)
        pool = self.adapter.build_pool(scores)
        element_groups: Dict[str, List[int]] = {}
        for number, element in element_map.items():
            element_groups.setdefault(element, []).append(number)

        history_meta: Dict[str, float] = {
            "frequency": active_scorer.history_weight,
            "recency": active_scorer.recency_weight,
            "gap": active_scorer.gap_weight,
            "calendar": active_scorer.calendar_weight,
            "half_life_days": effective_half_life,
            "base_half_life_days": base_half_life,
            "history_window": self._active_history_window,
        }
        if derived_weights and apply_dynamic:
            history_meta["base_frequency"] = base_scorer.history_weight
            history_meta["base_recency"] = base_scorer.recency_weight
            history_meta["base_gap"] = base_scorer.gap_weight
            history_meta["base_calendar"] = base_scorer.calendar_weight

        metadata = {
            "hexagram": {
                "primary": state.primary.name,
                "mutual": state.mutual.name if state.mutual else None,
                "changing": state.changing.name if state.changing else None,
                "moving_lines": state.moving_lines,
            },
            "season": determine_season(reference_time),
            "history_size": len(self.historical_data),
            "history_weights": history_meta,
            "calendar": calendar_dict,
            "element_groups": {key: sorted(values) for key, values in element_groups.items()},
        }
        if derived_weights and apply_dynamic:
            metadata["dynamic_weights"] = derived_weights
        if mystic:
            metadata["mystic"] = mystic

        return PredictionResult(primary_selection=primary, candidate_pool=pool, scores=scores, metadata=metadata)

