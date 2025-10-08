"""快乐8适配。"""

from __future__ import annotations

from itertools import combinations

from typing import Dict, List, Optional, Tuple

from ....config.game_config import GameConfig

from .base import BaseAdapter


class Keno8Adapter(BaseAdapter):
    name = "keno8"

    def __init__(self, config: GameConfig | None = None) -> None:
        super().__init__(config or GameConfig("keno8"))

    def select(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        candidates = self._top_numbers(scores, 20)
        return {"main": sorted(candidates[:10])}

    def build_pool(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        top = self._top_numbers(scores, 20)
        bottom = self._bottom_numbers(scores, 10)
        return {
            "high_probability": sorted(top[:15]),
            "low_probability": sorted(bottom[:10]),
        }

    def guard_sets(
        self,
        scores: Dict[int, float],
        *,
        num_sets: int = 3,
        element_map: Optional[Dict[int, str]] = None,
        calendar_profile: Optional[Dict[str, object]] = None,
        **_: object,
    ) -> List[Dict[str, List[int]]]:
        combo_size = min(10, max(6, self.config.drawn_numbers // 2))
        top_candidates = self._top_numbers(scores, max(20, combo_size + 5))
        pool_limit = min(len(top_candidates), combo_size + 3)
        if pool_limit < combo_size:
            pool_limit = len(top_candidates)
        pool = top_candidates[:pool_limit]
        if not pool:
            return []

        favored_elements = set(calendar_profile.get("favorable_elements", []) if calendar_profile else [])
        unfavorable_elements = set(calendar_profile.get("unfavorable_elements", []) if calendar_profile else [])
        favored_numbers = list(calendar_profile.get("favored_numbers", []) if calendar_profile else [])
        favored_mod = {num % 9 or 9 for num in favored_numbers}

        candidate_sets: List[Tuple[float, List[int], List[int]]] = []
        combos = combinations(pool, combo_size) if len(pool) >= combo_size else [tuple(pool)]
        for combo in combos:
            selection = list(combo)
            score_total = sum(scores.get(num, 0.0) for num in selection)
            adjacency_penalty = sum(0.03 for i in range(1, len(selection)) if abs(selection[i] - selection[i - 1]) <= 1)
            score_total -= adjacency_penalty
            if element_map and favored_elements:
                covered = {element_map.get(num) for num in selection if element_map.get(num) in favored_elements}
                score_total += 0.05 * len(covered)
            if element_map and unfavorable_elements:
                cold_hits = sum(1 for num in selection if element_map.get(num) in unfavorable_elements)
                score_total -= 0.03 * cold_hits
            if favored_mod:
                score_total += 0.015 * sum(1 for num in selection if (num % 9 or 9) in favored_mod)

            reserve = [num for num in pool if num not in selection][: max(0, len(pool) - combo_size)]
            candidate_sets.append((score_total, sorted(selection), reserve))

        candidate_sets.sort(key=lambda item: item[0], reverse=True)
        results: List[Dict[str, List[int]]] = []
        seen: set[Tuple[int, ...]] = set()
        for _, selection, reserve in candidate_sets:
            key = tuple(selection)
            if key in seen:
                continue
            seen.add(key)
            results.append({"main": selection, "reserve": reserve})
            if len(results) >= num_sets:
                break

        if not results:
            fallback = sorted(pool[:combo_size])
            reserve = [num for num in pool if num not in fallback]
            results.append({"main": fallback, "reserve": reserve})
        return results

    def evaluate(self, selection: Dict[str, List[int]], pool: Dict[str, List[int]], draw: Dict[str, object]) -> tuple[int, int]:
        drawn = set(draw.get("numbers", []))
        hits_primary = len(drawn.intersection(selection.get("main", [])))
        pool_hits = len(drawn.intersection(set(pool.get("high_probability", []))))
        return hits_primary, pool_hits
