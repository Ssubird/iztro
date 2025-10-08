"""事件建模：依据《梅花易数》时间取象规则封装起卦上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Sequence


@dataclass
class EventSnapshot:
    """《梅花易数》年月日时取象所需的事件快照。

    对齐《梅花易数原典》“年月日时起例”与“今日动静”篇章的记载，默认以
    当前时间生成时辰卦，也允许外部注入参考号码与自定义因子，用于后续
    体用判别或扩展卦义。"""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    location: str = "online"
    reference_numbers: Sequence[int] | None = None
    custom_factors: Dict[str, Any] = field(default_factory=dict)
