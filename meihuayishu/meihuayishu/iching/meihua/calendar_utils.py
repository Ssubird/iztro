"""Calendar, lunar, and astronomical helpers for Meihua inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import cos, pi
from typing import Dict, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    from lunardate import LunarDate  # type: ignore
except Exception:  # pragma: no cover
    LunarDate = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import chinese_calendar  # type: ignore
except Exception:  # pragma: no cover
    chinese_calendar = None  # type: ignore

CN_TZ = timezone(timedelta(hours=8))
SYNODIC_MONTH = 29.53058867

__all__ = [
    "CalendarProfile",
    "build_calendar_profile",
    "moon_age_days",
    "SYNODIC_MONTH",
    "ELEMENT_GENERATE",
    "ELEMENT_OVERCOME",
]

HEAVENLY_STEMS: Sequence[str] = (
    "甲",
    "乙",
    "丙",
    "丁",
    "戊",
    "己",
    "庚",
    "辛",
    "壬",
    "癸",
)

EARTHLY_BRANCHES: Sequence[str] = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
)

STEM_TO_ELEMENT: Dict[str, str] = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}

BRANCH_TO_ELEMENT: Dict[str, str] = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}

BRANCH_TO_ZODIAC: Dict[str, str] = {
    "子": "鼠",
    "丑": "牛",
    "寅": "虎",
    "卯": "兔",
    "辰": "龙",
    "巳": "蛇",
    "午": "马",
    "未": "羊",
    "申": "猴",
    "酉": "鸡",
    "戌": "狗",
    "亥": "猪",
}

STEM_NUMERICAL: Dict[str, int] = {
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

BRANCH_NUMERICAL: Dict[str, int] = {
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

MONTH_BRANCHES: Sequence[str] = (
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
    "子",
    "丑",
)

ELEMENT_GENERATE: Dict[str, str] = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

ELEMENT_OVERCOME: Dict[str, str] = {
    "木": "土",
    "土": "水",
    "水": "火",
    "火": "金",
    "金": "木",
}

MOON_PHASE_DATA: Sequence[Tuple[str, str, Tuple[float, float], str]] = (
    ("朔月", "新月", (0.0, 1.84566), "水"),
    ("娥眉月", "上弦前盈", (1.84566, 5.53699), "木"),
    ("上弦月", "上弦", (5.53699, 9.22831), "木"),
    ("盈凸月", "上凸", (9.22831, 12.91963), "火"),
    ("望月", "满月", (12.91963, 16.61096), "金"),
    ("亏凸月", "下凸", (16.61096, 20.30228), "金"),
    ("下弦月", "下弦", (20.30228, 23.99361), "水"),
    ("残月", "残月", (23.99361, 29.53058867), "土"),
)


@dataclass
class CalendarProfile:
    local_time: datetime
    ganzhi: Dict[str, Tuple[str, str]]
    elements: Dict[str, Optional[str]]
    zodiac: Dict[str, Optional[str]]
    lunar_date: Optional[Dict[str, int]]
    solar_term: Optional[str]
    weekday: str
    is_workday: Optional[bool]
    is_holiday: Optional[bool]
    notes: List[str] = field(default_factory=list)
    favorable_elements: List[str] = field(default_factory=list)
    unfavorable_elements: List[str] = field(default_factory=list)
    favored_numbers: List[int] = field(default_factory=list)
    moon: Dict[str, object] = field(default_factory=dict)


def moon_age_days(reference_time: datetime) -> float:
    """Return the synodic age of the moon (0-29.53)."""

    utc_time = reference_time.astimezone(timezone.utc) if reference_time.tzinfo else reference_time.replace(tzinfo=timezone.utc)
    known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    days = (utc_time - known_new_moon).total_seconds() / 86400.0
    return days % SYNODIC_MONTH


def _moon_phase_record(age: float) -> Tuple[str, str, str]:
    for name, alias, (start, end), element in MOON_PHASE_DATA:
        if start <= age < end:
            return name, alias, element
    return MOON_PHASE_DATA[-1][0], MOON_PHASE_DATA[-1][1], MOON_PHASE_DATA[-1][3]


def _moon_profile(reference_time: datetime) -> Dict[str, object]:
    age = moon_age_days(reference_time)
    illumination = (1 - cos(2 * pi * age / SYNODIC_MONTH)) / 2
    phase_name, alias, element = _moon_phase_record(age)
    favored_elements = [element]
    generated = ELEMENT_GENERATE.get(element)
    if generated:
        favored_elements.append(generated)
    unfavorable = []
    overcome = ELEMENT_OVERCOME.get(element)
    if overcome:
        unfavorable.append(overcome)
    moon_numbers = [int((age / SYNODIC_MONTH) * 9) % 9 + 1, int((illumination * 9) % 9) + 1]

    return {
        "age_days": round(age, 3),
        "illumination": round(illumination, 4),
        "phase": phase_name,
        "alias": alias,
        "element": element,
        "favored_elements": favored_elements,
        "unfavorable_elements": unfavorable,
        "favored_numbers": sorted({num if num <= 9 else num % 9 or 9 for num in moon_numbers}),
    }


def _ganzhi_from_index(stem_index: int, branch_index: int) -> Tuple[str, str]:
    return HEAVENLY_STEMS[stem_index % 10], EARTHLY_BRANCHES[branch_index % 12]


def _ganzhi_year(dt: datetime) -> Tuple[str, str]:
    year = dt.year
    stem_index = (year - 4) % 10
    branch_index = (year - 4) % 12
    return _ganzhi_from_index(stem_index, branch_index)


def _ganzhi_day(dt: datetime) -> Tuple[str, str]:
    base = datetime(1900, 1, 31, tzinfo=timezone.utc)
    base = base.astimezone(dt.tzinfo or timezone.utc)
    days = (dt.date() - base.date()).days
    return _ganzhi_from_index(days % 10, days % 12)


def _hour_branch(dt: datetime) -> str:
    hour = dt.hour
    index = ((hour + 1) // 2) % 12
    return EARTHLY_BRANCHES[index]


def _ganzhi_hour(day_stem: str, hour_branch: str) -> Tuple[str, str]:
    branch_index = EARTHLY_BRANCHES.index(hour_branch)
    day_stem_index = HEAVENLY_STEMS.index(day_stem)
    stem_index = (day_stem_index * 2 + branch_index) % 10
    return HEAVENLY_STEMS[stem_index], hour_branch


def _ganzhi_month(year_stem_index: int, lunar_month: int) -> Tuple[str, str]:
    branch = MONTH_BRANCHES[(lunar_month - 1) % 12]
    stem_index = (year_stem_index * 2 + lunar_month + 2) % 10
    return HEAVENLY_STEMS[stem_index], branch


def _preferred_numbers_from_ganzhi(ganzhi: Dict[str, Tuple[str, str]]) -> List[int]:
    numbers: List[int] = []
    for stem, branch in ganzhi.values():
        numbers.append(STEM_NUMERICAL.get(stem, 0) % 9 or 9)
        numbers.append(BRANCH_NUMERICAL.get(branch, 0) % 9 or 9)
    seen: set[int] = set()
    ordered: List[int] = []
    for num in numbers:
        if num not in seen and num != 0:
            seen.add(num)
            ordered.append(num)
    return ordered


def build_calendar_profile(reference_time: datetime) -> CalendarProfile:
    local_time = reference_time.astimezone(CN_TZ)
    notes: List[str] = []

    lunar_info: Optional[Dict[str, int]] = None
    lunar_month = local_time.month
    if LunarDate is not None:  # pragma: no branch
        try:
            lunar = LunarDate.fromSolarDate(local_time.year, local_time.month, local_time.day)
            lunar_info = {
                "year": lunar.year,
                "month": lunar.month,
                "day": lunar.day,
                "is_leap_month": bool(getattr(lunar, "isLeapMonth", False)),
            }
            lunar_month = lunar.month
        except Exception as exc:
            notes.append(f"lunardate 解析失败: {exc}")
    else:
        notes.append("安装 lunardate 获取农历信息")

    year_stem, year_branch = _ganzhi_year(local_time)
    day_stem, day_branch = _ganzhi_day(local_time)
    hour_branch = _hour_branch(local_time)
    hour_stem, hour_branch = _ganzhi_hour(day_stem, hour_branch)
    month_stem, month_branch = _ganzhi_month(HEAVENLY_STEMS.index(year_stem), lunar_month)

    ganzhi = {
        "year": (year_stem, year_branch),
        "month": (month_stem, month_branch),
        "day": (day_stem, day_branch),
        "hour": (hour_stem, hour_branch),
    }

    elements = {
        "year": STEM_TO_ELEMENT.get(year_stem) or BRANCH_TO_ELEMENT.get(year_branch),
        "month": STEM_TO_ELEMENT.get(month_stem) or BRANCH_TO_ELEMENT.get(month_branch),
        "day": STEM_TO_ELEMENT.get(day_stem) or BRANCH_TO_ELEMENT.get(day_branch),
        "hour": STEM_TO_ELEMENT.get(hour_stem) or BRANCH_TO_ELEMENT.get(hour_branch),
    }

    zodiac = {
        "year": BRANCH_TO_ZODIAC.get(year_branch),
        "month": BRANCH_TO_ZODIAC.get(month_branch),
        "day": BRANCH_TO_ZODIAC.get(day_branch),
        "hour": BRANCH_TO_ZODIAC.get(hour_branch),
    }

    solar_term: Optional[str] = None
    is_workday: Optional[bool] = None
    is_holiday: Optional[bool] = None
    if chinese_calendar is not None:
        date_obj = local_time.date()
        try:
            if hasattr(chinese_calendar, "get_solar_term"):
                solar_term = chinese_calendar.get_solar_term(date_obj)
            if hasattr(chinese_calendar, "is_workday"):
                is_workday = chinese_calendar.is_workday(date_obj)
            if hasattr(chinese_calendar, "get_holiday_detail"):
                holiday_detail = chinese_calendar.get_holiday_detail(date_obj)
                if holiday_detail:
                    is_holiday, holiday = holiday_detail
                    if is_holiday and holiday is not None:
                        notes.append(f"节日: {getattr(holiday, 'value', str(holiday))}")
        except Exception as exc:
            notes.append(f"chinese_calendar 调用失败: {exc}")
    else:
        notes.append("安装 chinese_calendar 获取节气和黄历信息")

    weekday = local_time.strftime("%A")

    favored_numbers = _preferred_numbers_from_ganzhi(ganzhi)

    day_element = elements.get("day")
    hour_element = elements.get("hour")
    favorable_elements: List[str] = []
    unfavorable_elements: List[str] = []
    for element in (day_element, hour_element):
        if not element:
            continue
        if element not in favorable_elements:
            favorable_elements.append(element)
        generated = ELEMENT_GENERATE.get(element)
        if generated and generated not in favorable_elements:
            favorable_elements.append(generated)
        overcome = ELEMENT_OVERCOME.get(element)
        if overcome and overcome not in unfavorable_elements:
            unfavorable_elements.append(overcome)

    moon = _moon_profile(local_time)
    for elem in moon.get("favored_elements", []):
        if elem not in favorable_elements:
            favorable_elements.append(elem)
    for elem in moon.get("unfavorable_elements", []):
        if elem and elem not in unfavorable_elements:
            unfavorable_elements.append(elem)
    for num in moon.get("favored_numbers", []):
        if num not in favored_numbers:
            favored_numbers.append(num)

    profile = CalendarProfile(
        local_time=local_time,
        ganzhi=ganzhi,
        elements=elements,
        zodiac=zodiac,
        lunar_date=lunar_info,
        solar_term=solar_term,
        weekday=weekday,
        is_workday=is_workday,
        is_holiday=is_holiday,
        notes=notes,
        favorable_elements=favorable_elements,
        unfavorable_elements=unfavorable_elements,
        favored_numbers=sorted(favored_numbers),
        moon=moon,
    )
    return profile
