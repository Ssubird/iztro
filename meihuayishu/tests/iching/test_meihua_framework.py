"""梅花易数推理框架拆分模块的回归测试。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from meihuayishu.iching.meihua import EventSnapshot, MeihuaInferenceFramework
from meihuayishu.iching.meihua.data import LotteryDataManager


def build_mock_history(periods: int = 120) -> list[dict[str, object]]:
    mock_history = []
    base_date = datetime(2024, 1, 1)
    for i in range(periods):
        draw_date = base_date + timedelta(days=i)
        mock_history.append(
            {
                "period": f"test_{i}",
                "numbers": sorted(random.sample(range(1, 81), 20)),
                "timestamp": draw_date.strftime("%Y-%m-%d"),
            }
        )
    return mock_history


def test_hexagram_seed() -> None:
    framework = MeihuaInferenceFramework(game_type="keno8")
    framework.set_historical_data(build_mock_history())
    snapshot = EventSnapshot(timestamp=datetime(2024, 3, 21, 10))
    seed = framework.hex_engine.generate_seed(snapshot)
    base_sum = 2024 + 3 + 21
    expected = (base_sum % 8 or 8) - 1
    assert seed.upper_index == expected
    assert 0 <= seed.lower_index < 8
    assert 1 <= seed.moving_lines[0] <= 6


def test_candidate_pool() -> None:
    framework = MeihuaInferenceFramework(game_type="keno8")
    framework.set_historical_data(build_mock_history())
    result = framework.predict()
    assert "high_probability" in result.candidate_pool
    assert len(result.primary_selection["main"]) == 10
    assert all(1 <= num <= 80 for num in result.primary_selection["main"])


def test_local_dataset_loading(tmp_path) -> None:
    manager = LotteryDataManager("keno8", cache_dir=str(tmp_path))
    data = manager.load(max_periods=5, force_update=True)
    assert len(data) == 5
    assert all(len(draw["numbers"]) == 20 for draw in data)
    assert all("timestamp" in draw for draw in data)


def test_local_dataset_ssq(tmp_path) -> None:
    manager = LotteryDataManager("ssq", cache_dir=str(tmp_path))
    data = manager.load(max_periods=3, force_update=True)
    assert len(data) == 3
    assert all(len(draw["numbers"]) == 6 for draw in data)
    assert all("special" in draw for draw in data)
