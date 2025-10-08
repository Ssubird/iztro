

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Tuple

from ....config.game_config import GameConfig

from .base import BaseAdapter


class SSQAdapter(BaseAdapter):
    name = "ssq"

    def __init__(self, config: GameConfig | None = None) -> None:
        super().__init__(config or GameConfig("ssq"))

    @staticmethod
    def _segment_index(number: int) -> int:
        # 1-11, 12-22, 23-33 涓夋鍒嗗尯
        return min((number - 1) // 11, 2)

    def _segmented_selection(self, scores: Dict[int, float], total: int, distribution: tuple[int, int, int]) -> List[int]:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        buckets = {idx: [] for idx in range(len(distribution))}
        for number, _ in ordered:
            segment = self._segment_index(number)
            if len(buckets[segment]) < distribution[segment]:
                buckets[segment].append(number)
            if all(len(buckets[idx]) >= distribution[idx] for idx in range(len(distribution))):
                break
        selected: List[int] = []
        for idx in range(len(distribution)):
            selected.extend(sorted(buckets[idx]))
        if len(selected) < total:
            for number, _ in ordered:
                if number not in selected:
                    selected.append(number)
                if len(selected) >= total:
                    break
        return sorted(selected)

    def select(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        reds = self._segmented_selection(scores, total=6, distribution=(2, 2, 2))
        red_sum = sum(reds)
        blue = (red_sum % 16) or 16
        return {
            "red": reds,
            "blue": [blue],
        }

    def build_pool(self, scores: Dict[int, float]) -> Dict[str, List[int]]:
        red_candidates = self._segmented_selection(scores, total=8, distribution=(3, 3, 2))
        bottom = self._bottom_numbers(scores, 6)
        return {
            "red_top": red_candidates,
            "red_avoid": sorted(bottom),
            "blue_top": [((sum(red_candidates) + i) % 16) or 16 for i in range(1, 4)],
        }

    def guard_sets(
        self,
        scores: Dict[int, float],
        *,
        num_sets: int = 3,
        extra_blue: int = 5,
        blue_scores: Optional[Dict[int, float]] = None,
        element_map: Optional[Dict[int, str]] = None,
        calendar_profile: Optional[Dict[str, object]] = None,
    ) -> List[Dict[str, List[int]]]:
        segment_targets = (2, 2, 2)
        top_per_segment = 5
        segment_scores: Dict[int, List[Tuple[int, float]]] = {0: [], 1: [], 2: []}
        for number, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
            if number < 1 or number > self.config.total_numbers:
                continue
            segment = self._segment_index(number)
            segment_scores[segment].append((number, score))
        for segment in segment_scores:
            segment_scores[segment] = segment_scores[segment][:top_per_segment]
            if len(segment_scores[segment]) < segment_targets[segment]:
                segment_scores[segment] = sorted(segment_scores[segment], key=lambda item: item[1], reverse=True)

        if any(len(segment_scores[idx]) < segment_targets[idx] for idx in segment_scores):
            return []

        favored_elements = set(calendar_profile.get("favorable_elements", []) if calendar_profile else [])
        unfavorable_elements = set(calendar_profile.get("unfavorable_elements", []) if calendar_profile else [])
        favored_numbers = list(calendar_profile.get("favored_numbers", []) if calendar_profile else [])
        favored_mod = {num % 9 or 9 for num in favored_numbers}

        candidate_sets: List[Tuple[float, List[int]]] = []
        for reds_a in combinations(segment_scores[0], segment_targets[0]):
            for reds_b in combinations(segment_scores[1], segment_targets[1]):
                for reds_c in combinations(segment_scores[2], segment_targets[2]):
                    combined = list(reds_a + reds_b + reds_c)
                    reds = sorted(num for num, _ in combined)
                    score_total = sum(scores[num] for num in reds)
                    adjacency_penalty = sum(0.05 for i in range(1, len(reds)) if abs(reds[i] - reds[i - 1]) <= 1)
                    score_total -= adjacency_penalty

                    if element_map and favored_elements:
                        covered = {element_map.get(num) for num in reds if element_map.get(num) in favored_elements}
                        score_total += 0.06 * len(covered)
                    if element_map and unfavorable_elements:
                        cold_hits = sum(1 for num in reds if element_map.get(num) in unfavorable_elements)
                        score_total -= 0.04 * cold_hits
                    if favored_mod:
                        score_total += 0.02 * sum(1 for num in reds if (num % 9 or 9) in favored_mod)

                    candidate_sets.append((score_total, reds))

        candidate_sets.sort(key=lambda item: item[0], reverse=True)
        unique: List[List[int]] = []
        seen: set[Tuple[int, ...]] = set()
        for _, reds in candidate_sets:
            key = tuple(reds)
            if key in seen:
                continue
            seen.add(key)
            unique.append(reds)
            if len(unique) >= num_sets:
                break

        if not unique:
            return []

        if blue_scores:
            sorted_blue = sorted(blue_scores.items(), key=lambda item: item[1], reverse=True)
            blue_pool = [num for num, _ in sorted_blue[: max(extra_blue, len(unique))]]
        else:
            blue_pool: List[int] = []
            for reds in unique:
                base = sum(reds)
                for offset in range(1, extra_blue + 2):
                    candidate = (base + offset) % 16 or 16
                    if candidate not in blue_pool:
                        blue_pool.append(candidate)
                    if len(blue_pool) >= max(extra_blue, len(unique)):
                        break
                if len(blue_pool) >= max(extra_blue, len(unique)):
                    break

        results: List[Dict[str, List[int]]] = []
        for reds in unique:
            blues = blue_pool[:extra_blue] if blue_pool else [((sum(reds) + i) % 16) or 16 for i in range(1, extra_blue + 1)]
            results.append({"red": reds, "blue": blues})
        return results


    def evaluate(self, selection: Dict[str, List[int]], pool: Dict[str, List[int]], draw: Dict[str, object]) -> tuple[int, int]:
        drawn_reds = set(draw.get("numbers", []))
        hits_primary = len(drawn_reds.intersection(selection.get("red", [])))
        pool_hits = len(drawn_reds.intersection(set(pool.get("red_top", []))))
        return hits_primary, pool_hits

