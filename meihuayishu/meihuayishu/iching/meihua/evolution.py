"""Genetic algorithm optimizer for Meihua parameters."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Tuple

from .framework import EvolutionGuidance, MeihuaInferenceFramework
from .results import BacktestReport


@dataclass
class Candidate:
    """Represents a parameter set for evaluation."""

    hex_weights: Tuple[float, float, float]
    history_weight: float
    recency_weight: float
    gap_weight: float
    calendar_weight: float
    history_half_life: float
    history_window: int


class GeneticOptimizer:
    """GA that leverages the inference framework to evolve scoring weights."""

    def __init__(
        self,
        framework: MeihuaInferenceFramework,
        *,
        window_size: int,
        step: int,
        iterations: Optional[int] = None,
        population_size: Optional[int] = None,
        guidance: Optional[EvolutionGuidance] = None,
        seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, Optional[float]], None]] = None,
    ) -> None:
        self.framework = framework
        self.window_size = window_size
        self.step = step
        base_guidance = guidance or framework.infer_evolution_guidance(window_size=window_size, step=step)
        resolved_iterations = iterations if iterations is not None else base_guidance.iterations
        resolved_population = population_size if population_size is not None else base_guidance.population
        self.iterations = max(1, resolved_iterations)
        self.population_size = max(4, resolved_population)
        self.guidance = replace(base_guidance, iterations=self.iterations, population=self.population_size)
        base_seed = seed if seed is not None else self.guidance.seed
        if base_seed is None:
            base_seed = int(random.random() * 1_000_000)
        self.random = random.Random(base_seed)
        self._base_config = framework._initial_config  # type: ignore[attr-defined]
        self.progress_callback = progress_callback

    def evolve(self) -> Tuple[Candidate, BacktestReport]:
        """Run GA and return the best candidate with its report."""

        population = [self._random_candidate() for _ in range(self.population_size)]
        best_candidate: Optional[Candidate] = None
        best_report: Optional[BacktestReport] = None
        best_score = -math.inf
        total_steps = max(self.iterations * self.population_size, 1)
        current_step = 0
        self._emit_progress(current_step, total_steps, None)

        for iteration in range(self.iterations):
            scored: List[Tuple[float, Candidate, BacktestReport]] = []
            for candidate in population:
                score, report = self._evaluate(candidate)
                scored.append((score, candidate, report))
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
                    best_report = report
                current_step += 1
                self._emit_progress(current_step, total_steps, best_score if best_score > -math.inf else None)
            scored.sort(key=lambda item: item[0], reverse=True)

            elites = [item[1] for item in scored[:2]]
            new_population: List[Candidate] = elites.copy()
            parent_pool = scored[: max(4, int(len(scored) * (0.35 + self.guidance.exploration_bias * 0.4)))]
            while len(new_population) < self.population_size:
                if self.random.random() < self._exploration_probability():
                    new_population.append(self._random_candidate())
                    continue
                parents = self.random.sample(parent_pool, 2)
                child = self._crossover(parents[0][1], parents[1][1])
                child = self._mutate(child, iteration)
                new_population.append(child)
            population = new_population

        if best_candidate is None or best_report is None:
            raise RuntimeError("遗传算法未能找到有效的参数组合。")
        self._emit_progress(total_steps, total_steps, best_score if best_score > -math.inf else None)
        return best_candidate, best_report

    def _random_candidate(self) -> Candidate:
        base_hex = list(self._base_config["hex_weights"])  # type: ignore[index]
        focus = self.guidance.hex_focus
        if self.guidance.hex_focus_weight > 0:
            base_hex = [
                base_hex[idx] * (1.0 - self.guidance.hex_focus_weight)
                + focus[idx] * self.guidance.hex_focus_weight
                for idx in range(3)
            ]
        spread = 0.18 + self.guidance.exploration_bias * 0.14
        jitter = [self.random.uniform(1.0 - spread, 1.0 + spread) for _ in range(3)]
        weights = self._normalize_hex([base_hex[i] * jitter[i] for i in range(3)])

        weight_scale = 0.18 + self.guidance.exploration_bias * 0.12

        def jitter_value(value: float, scale: float = weight_scale) -> float:
            return max(0.01, value * self.random.uniform(1.0 - scale, 1.0 + scale))

        history_weight = jitter_value(self._base_config["history_weight"])
        recency_weight = jitter_value(self._base_config["recency_weight"], weight_scale * 0.9)
        gap_weight = jitter_value(self._base_config["gap_weight"])
        calendar_weight = jitter_value(self._base_config["calendar_weight"], weight_scale * 1.1)

        base_total = (
            self._base_config["history_weight"]
            + self._base_config["recency_weight"]
            + self._base_config["gap_weight"]
            + self._base_config["calendar_weight"]
        )
        new_total = history_weight + recency_weight + gap_weight + calendar_weight
        if new_total:
            scale = base_total / new_total
            history_weight *= scale
            recency_weight *= scale
            gap_weight *= scale
            calendar_weight *= scale

        half_life = self.random.uniform(*self.guidance.half_life_bounds)
        window = int(self.random.uniform(*self.guidance.window_bounds))
        half_life = max(10.0, half_life)
        window = max(30, window)

        return Candidate(
            hex_weights=weights,
            history_weight=history_weight,
            recency_weight=recency_weight,
            gap_weight=gap_weight,
            calendar_weight=calendar_weight,
            history_half_life=half_life,
            history_window=window,
        )

    def _mutate(self, candidate: Candidate, iteration: int) -> Candidate:
        progress = iteration / max(self.iterations - 1, 1)
        decay = max(0.05, (1.0 - progress) ** self.guidance.mutation_decay)
        mutate_scale = max(
            self.guidance.mutation_strength * decay,
            self.guidance.mutation_strength * 0.35,
        )

        def jitter_value(value: float, scale: float = mutate_scale) -> float:
            return max(0.01, value * self.random.uniform(1.0 - scale, 1.0 + scale))

        weights = [jitter_value(value) for value in candidate.hex_weights]
        focus_strength = self.guidance.hex_focus_weight * (1.0 - decay) * 0.6
        if focus_strength > 0:
            weights = [
                weights[idx] * (1.0 - focus_strength) + self.guidance.hex_focus[idx] * focus_strength
                for idx in range(3)
            ]
        weights = self._normalize_hex(weights)

        weight_scale = mutate_scale * (1.0 + self.guidance.exploration_bias * 0.2)
        history = jitter_value(candidate.history_weight, weight_scale)
        recency = jitter_value(candidate.recency_weight, weight_scale * 0.9)
        gap = jitter_value(candidate.gap_weight, weight_scale)
        calendar = jitter_value(candidate.calendar_weight, weight_scale * 1.1)

        base_total = (
            self._base_config["history_weight"]
            + self._base_config["recency_weight"]
            + self._base_config["gap_weight"]
            + self._base_config["calendar_weight"]
        )
        new_total = history + recency + gap + calendar
        if new_total:
            scale = base_total / new_total
            history *= scale
            recency *= scale
            gap *= scale
            calendar *= scale

        half_life = self._clamp(
            jitter_value(candidate.history_half_life),
            self.guidance.half_life_bounds[0],
            self.guidance.half_life_bounds[1],
        )
        window = int(
            self._clamp(
                jitter_value(float(candidate.history_window)),
                float(self.guidance.window_bounds[0]),
                float(self.guidance.window_bounds[1]),
            )
        )
        window = max(30, window)

        return Candidate(
            hex_weights=weights,
            history_weight=history,
            recency_weight=recency,
            gap_weight=gap,
            calendar_weight=calendar,
            history_half_life=half_life,
            history_window=window,
        )

    def _crossover(self, parent_a: Candidate, parent_b: Candidate) -> Candidate:
        center = self.guidance.crossover_center
        width = self.guidance.crossover_width
        low = self._clamp(center - width, 0.05, 0.95)
        high = self._clamp(center + width, 0.05, 0.95)
        mix = self.random.uniform(low, high)
        weights = self._normalize_hex(
            [parent_a.hex_weights[i] * mix + parent_b.hex_weights[i] * (1.0 - mix) for i in range(3)]
        )
        focus_strength = self.guidance.hex_focus_weight * 0.3
        if focus_strength > 0:
            weights = [
                weights[idx] * (1.0 - focus_strength) + self.guidance.hex_focus[idx] * focus_strength
                for idx in range(3)
            ]
            weights = self._normalize_hex(weights)

        history = parent_a.history_weight * mix + parent_b.history_weight * (1.0 - mix)
        recency = parent_a.recency_weight * mix + parent_b.recency_weight * (1.0 - mix)
        gap = parent_a.gap_weight * mix + parent_b.gap_weight * (1.0 - mix)
        calendar = parent_a.calendar_weight * mix + parent_b.calendar_weight * (1.0 - mix)

        base_total = (
            self._base_config["history_weight"]
            + self._base_config["recency_weight"]
            + self._base_config["gap_weight"]
            + self._base_config["calendar_weight"]
        )
        new_total = history + recency + gap + calendar
        if new_total:
            scale = base_total / new_total
            history *= scale
            recency *= scale
            gap *= scale
            calendar *= scale

        half_life = self._clamp(
            parent_a.history_half_life * mix + parent_b.history_half_life * (1.0 - mix),
            self.guidance.half_life_bounds[0],
            self.guidance.half_life_bounds[1],
        )
        window = int(
            self._clamp(
                parent_a.history_window * mix + parent_b.history_window * (1.0 - mix),
                float(self.guidance.window_bounds[0]),
                float(self.guidance.window_bounds[1]),
            )
        )
        window = max(30, window)

        return Candidate(
            hex_weights=weights,
            history_weight=history,
            recency_weight=recency,
            gap_weight=gap,
            calendar_weight=calendar,
            history_half_life=half_life,
            history_window=window,
        )

    def _normalize_hex(self, weights: List[float]) -> Tuple[float, float, float]:
        total = sum(weights) or 1.0
        normalized = [max(0.05, w / total) for w in weights]
        total_norm = sum(normalized)
        return tuple(value / total_norm for value in normalized)  # type: ignore[return-value]

    def _evaluate(self, candidate: Candidate) -> Tuple[float, BacktestReport]:
        original_dynamic = self.framework.dynamic_weights
        original_override = getattr(self.framework, "_parameter_override", None)
        original_half_life = self.framework.base_history_half_life
        original_window = getattr(self.framework, "_active_history_window", None)

        override: Dict[str, object] = {
            "hex_weights": candidate.hex_weights,
            "history_weight": candidate.history_weight,
            "recency_weight": candidate.recency_weight,
            "gap_weight": candidate.gap_weight,
            "calendar_weight": candidate.calendar_weight,
            "history_half_life": candidate.history_half_life,
            "history_window": candidate.history_window,
            "dynamic": False,
        }

        try:
            self.framework.dynamic_weights = False
            self.framework.set_parameter_override(override)
            report = self.framework.backtester.run_backtest(window_size=self.window_size, step=self.step)
            fitness = report.hit_rate() + 0.5 * report.pool_hit_rate()
        finally:
            if original_override is not None:
                self.framework.set_parameter_override(original_override)
            else:
                self.framework.clear_parameter_override()
            self.framework.dynamic_weights = original_dynamic
            self.framework.base_history_half_life = original_half_life
            self.framework._active_history_window = original_window  # type: ignore[attr-defined]
        return fitness, report

    def _emit_progress(self, step: int, total: int, best_score: Optional[float]) -> None:
        if not self.progress_callback:
            return
        bounded_step = max(0, min(step, total))
        self.progress_callback(bounded_step, total, best_score)

    def _exploration_probability(self) -> float:
        return 0.12 + 0.28 * self.guidance.exploration_bias

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))
