"""《梅花易数》五行与节气相关常量。"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

FIVE_ELEMENTS = ("金", "木", "水", "火", "土")

FIVE_ELEMENT_RELATION: Dict[Tuple[str, str], int] = {}
for a in FIVE_ELEMENTS:
    for b in FIVE_ELEMENTS:
        if a == b:
            FIVE_ELEMENT_RELATION[(a, b)] = 1
        elif (a, b) in {("金", "木"), ("木", "土"), ("土", "水"), ("水", "火"), ("火", "金")}:
            FIVE_ELEMENT_RELATION[(a, b)] = -1
        elif (a, b) in {("金", "水"), ("水", "木"), ("木", "火"), ("火", "土"), ("土", "金")}:
            FIVE_ELEMENT_RELATION[(a, b)] = 1
        else:
            FIVE_ELEMENT_RELATION[(a, b)] = 0

SEASONAL_WEIGHTS = {
    "spring": {"木": 1.2, "火": 1.0, "土": 0.9, "金": 0.8, "水": 0.95},
    "summer": {"火": 1.2, "土": 1.0, "木": 0.95, "水": 0.8, "金": 0.9},
    "autumn": {"金": 1.2, "水": 1.05, "土": 0.95, "火": 0.85, "木": 0.9},
    "winter": {"水": 1.2, "木": 1.0, "金": 0.95, "火": 0.8, "土": 0.9},
    "transitional": {"土": 1.1, "金": 1.0, "水": 0.95, "木": 0.95, "火": 0.95},
}


def determine_season(dt: datetime) -> str:
    month = dt.month
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    if month in {12, 1, 2}:
        return "winter"
    return "transitional"
