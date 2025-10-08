"""历史开奖数据管理与自动更新。"""

from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from ...config.game_config import GameConfig

try:  # pragma: no cover - 动态依赖
    from ...data.data_loader import RealDataLoader as _RealDataLoader
except Exception:  # pragma: no cover - 缺省时允许退化
    _RealDataLoader = None  # type: ignore[misc]


PROJECT_ROOT = Path(__file__).resolve().parents[3]
# 针对缓存目录，约定以 iztro 目录作为相对路径基准（避免随执行目录变化）
IZTRO_ROOT = Path(__file__).resolve().parents[4]


class LotteryDataManager:
    """封装真实数据下载、缓存与模拟回退。"""

    DATASET_PARSERS: Dict[str, tuple[str, Callable[[str], Optional[Dict[str, Any]]]]] = {
        "keno8": ("data/raw/kl8_asc.txt", lambda line: LotteryDataManager._parse_line(line, 20)),
        "ssq": (
            "data/raw/ssq_asc.txt",
            lambda line: LotteryDataManager._parse_ssq_line(line),
        ),
    }

    def __init__(
        self,
        game_type: str,
        cache_dir: str = "data/meihua_cache",
        *,
        prefer_local: bool = True,
    ) -> None:
        self.game_type = game_type
        base_cache = Path(cache_dir)
        # 相对路径时，统一相对于 iztro 根目录解析，确保缓存位于 iztro/data/meihua_cache
        self.cache_dir = base_cache if base_cache.is_absolute() else (IZTRO_ROOT / base_cache)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = GameConfig(game_type)
        self.cache_path = self.cache_dir / f"{game_type}_history.json"
        self.prefer_local = prefer_local
        self.loader: Optional[_RealDataLoader] = None
        if not self.prefer_local and _RealDataLoader is not None:
            try:
                self.loader = _RealDataLoader(self.config)
            except Exception as exc:  # pragma: no cover - 初始化失败时回退
                logging.warning("真实数据加载器初始化失败，使用本地/模拟数据: %s", exc)
                self.loader = None

    # ------------------------------------------------------------------
    # 缓存管理
    # ------------------------------------------------------------------

    def _load_cache(self) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logging.warning("缓存文件损坏，重新下载数据。")
            return []

    def _save_cache(self, data: List[Dict[str, Any]]) -> None:
        self.cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _latest_date(self, data: Sequence[Dict[str, Any]]) -> Optional[datetime]:
        dates: List[datetime] = []
        for row in data:
            ts = row.get("timestamp")
            if isinstance(ts, str):
                try:
                    dates.append(datetime.strptime(ts, "%Y-%m-%d"))
                except ValueError:
                    continue
        return max(dates) if dates else None

    # ------------------------------------------------------------------
    # 数据加载接口
    # ------------------------------------------------------------------

    def load(self, *, max_periods: Optional[int] = None, force_update: bool = False) -> List[Dict[str, Any]]:
        cache = self._load_cache()
        latest = self._latest_date(cache)
        needs_update = force_update
        if latest:
            delta = datetime.now(timezone.utc).date() - latest.date()
            needs_update = needs_update or delta >= timedelta(days=1)
        else:
            needs_update = True

        if needs_update:
            logging.info("更新历史开奖数据……")
            cache = []
            if self.loader is not None:
                try:
                    cache = self.loader.load_historical_data(force_update=True, max_periods=max_periods)
                except Exception as exc:  # pragma: no cover - 网络异常回退
                    logging.warning("真实数据下载失败，尝试使用本地数据: %s", exc)
                    cache = []
            if not cache:
                cache = self._load_local_dataset(max_periods=max_periods)
            if not cache:
                cache = self._generate_simulated_data(max_periods or 200)
            self._save_cache(cache)
        elif max_periods:
            cache = cache[-max_periods:]
        return cache

    # ------------------------------------------------------------------
    # 模拟数据
    # ------------------------------------------------------------------

    def _generate_simulated_data(self, periods: int) -> List[Dict[str, Any]]:
        simulated: List[Dict[str, Any]] = []
        base = datetime.now(timezone.utc) - timedelta(days=periods)
        for idx in range(periods):
            draw_date = base + timedelta(days=idx)
            numbers = sorted(random.sample(range(1, self.config.total_numbers + 1), self.config.drawn_numbers))
            simulated.append(
                {
                    "period": f"sim_{idx}",
                    "numbers": numbers,
                    "timestamp": draw_date.strftime("%Y-%m-%d"),
                }
            )
        return simulated

    # ------------------------------------------------------------------
    # 本地数据集解析
    # ------------------------------------------------------------------

    def _load_local_dataset(self, *, max_periods: Optional[int] = None) -> List[Dict[str, Any]]:
        spec = self.DATASET_PARSERS.get(self.game_type)
        if not spec:
            return []
        rel_path, parser = spec
        dataset_path = PROJECT_ROOT / rel_path
        if not dataset_path.exists():
            logging.warning("未找到本地数据集: %s", dataset_path)
            return []

        draws: List[Dict[str, Any]] = []
        for line in dataset_path.read_text(encoding="utf-8").splitlines():
            record = parser(line)
            if record:
                draws.append(record)

        if not draws:
            return []

        draws.sort(key=lambda item: item["timestamp"])
        if max_periods:
            draws = draws[-max_periods:]
        return draws

    @staticmethod
    def _parse_line(line: str, required_numbers: int, *, sort_numbers: bool = True) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None
        if not re.match(r"^\d{7}\s+\d{4}-\d{2}-\d{2}", line):
            return None
        tokens = re.split(r"\s+", line)
        if len(tokens) < 2:
            return None

        period, draw_date = tokens[0], tokens[1]
        extracted: List[int] = []
        for token in tokens[2:]:
            clean = token.replace(",", "")
            if not clean.isdigit():
                continue
            extracted.append(int(clean))
            if len(extracted) >= required_numbers:
                break

        if len(extracted) < required_numbers:
            return None

        numbers = list(extracted[:required_numbers])
        if sort_numbers:
            numbers.sort()

        return {
            "period": period,
            "numbers": numbers,
            "timestamp": draw_date,
        }

    @staticmethod
    def _parse_ssq_line(line: str) -> Optional[Dict[str, Any]]:
        parsed = LotteryDataManager._parse_line(line, 7, sort_numbers=False)
        if not parsed:
            return None

        numbers = parsed["numbers"]
        if len(numbers) < 7:
            return None

        reds = sorted(numbers[:6])
        blue = numbers[6]
        parsed["numbers"] = reds
        parsed["special"] = blue
        return parsed
