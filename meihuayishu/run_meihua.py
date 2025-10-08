import argparse
import os
from pathlib import Path
from datetime import datetime, timezone
try:
    import yaml
except Exception:
    yaml = None

from typing import Any, Dict, List, Optional, Sequence, Tuple

from meihuayishu.iching.meihua import EventSnapshot, MeihuaInferenceFramework, PredictionResult
from meihuayishu.iching.meihua.evolution import Candidate, GeneticOptimizer
from meihuayishu.iching.meihua.results import BacktestReport



def load_config(path: str) -> Dict[str, object]:
    if yaml is None:
        raise RuntimeError("需要安装 pyyaml 才能使用配置文件功能。请执行 pip install pyyaml")

    raw_path = Path(path.strip())
    script_dir = Path(__file__).resolve().parent

    if raw_path.is_absolute():
        candidates = [raw_path]
    else:
        candidates = [Path.cwd() / raw_path, script_dir / raw_path, script_dir.parent / raw_path]

    config_path: Optional[Path] = None
    tried: List[Path] = []
    for candidate in candidates:
        expanded = candidate.expanduser()
        tried.append(expanded)
        if expanded.exists():
            config_path = expanded.resolve()
            break

    if not config_path:
        tried_display = "\n".join(str(item) for item in tried)
        raise FileNotFoundError(f"未找到配置文件 {path}。尝试位置:\n{tried_display}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("配置文件根节点必须是映射 (mapping)")
    normalized: Dict[str, object] = {}
    for key, value in data.items():
        normalized[str(key).replace('-', '_')] = value
    return normalized


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    fmts = ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
    for fmt in fmts:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"无法解析的时间格式: {value}")


def parse_numbers(value: Optional[str]) -> Optional[Sequence[int]]:
    if not value:
        return None
    try:
        numbers = [int(item) for item in value.split(',') if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"号码列表必须为整数: {value}") from exc
    return numbers or None


def parse_custom(items: Optional[Sequence[str]]) -> Dict[str, str]:
    custom: Dict[str, str] = {}
    if not items:
        return custom
    for item in items:
        if '=' not in item:
            raise argparse.ArgumentTypeError(f"自定义因子必须使用key=value格式: {item}")
        key, value = item.split('=', 1)
        custom[key.strip()] = value.strip()
    return custom


def parse_hex_weights(value: str) -> Tuple[float, float, float]:
    try:
        weights = tuple(float(part) for part in value.split(','))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"十进制权重需使用逗号分隔浮点数: {value}") from exc
    if len(weights) != 3:
        raise argparse.ArgumentTypeError("hex权重需提供三个浮点数，例如0.5,0.2,0.3")
    return weights



def _coerce_history_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        patterns = ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M")
        for fmt in patterns:
            try:
                parsed = datetime.strptime(value, fmt)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
    return None


def latest_history_date(records: Sequence[Dict[str, Any]]) -> Optional[datetime]:
    latest: Optional[datetime] = None
    for row in records:
        ts = _coerce_history_timestamp(row.get("timestamp"))
        if not ts:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def print_history_status(framework: MeihuaInferenceFramework) -> None:
    today = datetime.now(timezone.utc)
    latest = latest_history_date(framework.historical_data)
    print("=== 数据缓存状态 ===")
    print(f"  当前日期: {today.date()}")
    if latest:
        latest_date = latest.date()
        print(f"  最新开奖日期: {latest_date}")
        gap = (today.date() - latest_date).days
        if gap > 0:
            print(f"  与最新数据相差 {gap} 天 (已触发每日检查)")
        else:
            print("  今日数据已同步。")
    else:
        print("  最新开奖日期: 未知")
    print(f"  已缓存期数: {len(framework.historical_data)}")


def format_bucket_label(label: str) -> str:
    clean = label.replace('_', ' ').strip()
    if not clean:
        return label
    if any('一' <= ch <= '鿿' for ch in clean):
        return clean
    return clean.title()


def print_nested_dict(data: Dict[str, Any], indent: int = 4) -> None:
    prefix = ' ' * indent
    for key, value in data.items():
        label = format_bucket_label(str(key))
        if isinstance(value, dict):
            print(f"{prefix}{label}:")
            print_nested_dict(value, indent=indent + 2)
        else:
            print(f"{prefix}{label}: {value}")




def build_event(args: argparse.Namespace) -> Optional[EventSnapshot]:
    timestamp = parse_timestamp(args.timestamp) if args.timestamp else None
    reference_numbers = parse_numbers(args.reference)
    custom_factors = parse_custom(args.custom)
    if not timestamp and not reference_numbers and not custom_factors and args.location == 'online':
        return None
    snapshot = EventSnapshot(
        timestamp=timestamp or datetime.now(timezone.utc),
        location=args.location,
        reference_numbers=reference_numbers,
        custom_factors=custom_factors,
    )
    return snapshot


def display_prediction(result: PredictionResult) -> None:
    print("=== 推理结果 ===")
    print("主选号码:")
    for key, values in result.primary_selection.items():
        label = format_bucket_label(key)
        display_values = values
        if isinstance(values, set):
            display_values = sorted(values)
        elif isinstance(values, tuple):
            display_values = list(values)
        count_suffix = ""
        if isinstance(display_values, (list, tuple)):
            count_suffix = f" (共{len(display_values)}个)"
        print(f"  {label}{count_suffix}: {display_values}")

    if result.candidate_pool:
        print("候选号码池:")
        for key, values in result.candidate_pool.items():
            label = format_bucket_label(key)
            display_values = values
            if isinstance(values, set):
                display_values = sorted(values)
            elif isinstance(values, tuple):
                display_values = list(values)
            count_suffix = ""
            if isinstance(display_values, (list, tuple)):
                count_suffix = f" (共{len(display_values)}个)"
            print(f"  {label}{count_suffix}: {display_values}")

    print("评分TOP5:")
    top5 = sorted(result.scores.items(), key=lambda item: item[1], reverse=True)[:5]
    for number, score in top5:
        print(f"  {number}: {score:.4f}")

    print("元信息:")
    for key, value in result.metadata.items():
        label = format_bucket_label(str(key))
        if isinstance(value, dict):
            print(f"  {label}:")
            print_nested_dict(value, indent=4)
        else:
            print(f"  {label}: {value}")


def display_guard_sets(guard_sets: Sequence[Dict[str, List[int]]], game_type: str) -> None:
    if not guard_sets:
        return
    print("=== 守号推荐 ===")
    for idx, combo in enumerate(guard_sets, start=1):
        parts: List[str] = []
        for key, values in combo.items():
            label = format_bucket_label(str(key))
            if isinstance(values, (set, tuple)):
                display = sorted(values)
            elif isinstance(values, list):
                display = sorted(values)
            else:
                display = values
            parts.append(f"{label}: {display}")
        joined = "；".join(parts) if parts else str(combo)
        print(f"  守号 {idx}: {joined}")


def present_prediction(
    framework: MeihuaInferenceFramework,
    result: PredictionResult,
    args: argparse.Namespace,
    event: Optional[EventSnapshot],
) -> None:
    display_prediction(result)
    if args.guard_sets and args.guard_sets > 0:
        reference_time = event.timestamp if event and event.timestamp else datetime.now(timezone.utc)
        guard_sets = framework.recommend_guard_sets(
            scores=result.scores,
            reference_time=reference_time,
            event=event,
            num_sets=args.guard_sets,
            horizon=args.guard_horizon,
            extra_blue=args.guard_blue,
        )
        if guard_sets:
            display_guard_sets(guard_sets, framework.game_type)

def run_backtest(framework: MeihuaInferenceFramework, window_size: int, step: int) -> None:
    report = framework.backtester.run_backtest(window_size=window_size, step=step)
    summary = report.summary()
    print("=== 回测统计 ===")
    print(f"样本期数: {summary['periods']}")
    print(f"主选命中率: {summary['hit_rate']:.4f}")
    print(f"号码池命中率: {summary['pool_hit_rate']:.4f}")

def run_evolution(
    framework: MeihuaInferenceFramework,
    *,
    iterations: Optional[int],
    population: Optional[int],
    window_size: int,
    step: int,
    event: Optional[EventSnapshot],
) -> Tuple[Candidate, BacktestReport]:
    guidance = framework.infer_evolution_guidance(event=event, window_size=window_size, step=step)
    progress_state = {"printed": False}

    def progress(step_count: int, total: int, best: Optional[float]) -> None:
        progress_state["printed"] = True
        total = max(total, 1)
        ratio = step_count / total if total else 1.0
        bar_length = 30
        filled = int(bar_length * ratio)
        bar = "█" * filled + "░" * (bar_length - filled)
        best_display = f"{best:.4f}" if best is not None else "--"
        print(
            f"\r=== 遗传算法进度 [{bar}] {step_count}/{total} 最优适应度: {best_display}",
            end="",
            flush=True,
        )

    print("=== 遗传算法推理设定 ===")
    print(f"推理迭代数: {guidance.iterations}")
    print(f"推理种群规模: {guidance.population}")
    print(f"推理变异幅度: {guidance.mutation_strength:.3f} (衰减 {guidance.mutation_decay:.3f})")
    print(f"推理交叉中心: {guidance.crossover_center:.3f} ± {guidance.crossover_width:.3f}")
    print(
        f"推理半衰期范围: {guidance.half_life_bounds[0]:.1f} ~ {guidance.half_life_bounds[1]:.1f}"
    )
    print(
        f"推理窗口范围: {guidance.window_bounds[0]} ~ {guidance.window_bounds[1]}"
    )

    optimizer = GeneticOptimizer(
        framework,
        window_size=window_size,
        step=step,
        iterations=iterations,
        population_size=population,
        guidance=guidance,
        progress_callback=progress,
    )
    best_candidate, report = optimizer.evolve()
    if progress_state["printed"]:
        print()

    def describe_setting(actual: int, suggested: int, override: Optional[int]) -> str:
        if override is None:
            return f"{actual}"
        return f"{actual} (建议 {suggested})"

    def source_label(value: Optional[int]) -> str:
        return "推理" if value is None else "用户"

    summary = report.summary()
    print("=== 遗传算法优化 ===")
    print(
        f"迭代次数 ({source_label(iterations)}): "
        f"{describe_setting(optimizer.iterations, guidance.iterations, iterations)}"
    )
    print(
        f"种群规模 ({source_label(population)}): "
        f"{describe_setting(optimizer.population_size, guidance.population, population)}"
    )
    print("最佳参数:")
    print(f"  卦象权重: {best_candidate.hex_weights}")
    print(f"  历史权重: {best_candidate.history_weight:.4f}")
    print(f"  近期权重: {best_candidate.recency_weight:.4f}")
    print(f"  间隔权重: {best_candidate.gap_weight:.4f}")
    print(f"  农历权重: {best_candidate.calendar_weight:.4f}")
    print(f"  历史半衰期: {best_candidate.history_half_life:.2f}")
    print(f"  历史窗口: {best_candidate.history_window}")
    print("对应回测:")
    print(f"  样本期数: {summary['periods']}")
    print(f"  主选命中率: {summary['hit_rate']:.4f}")
    print(f"  号码池命中率: {summary['pool_hit_rate']:.4f}")
    return best_candidate, report





def run_optimization(
    framework: MeihuaInferenceFramework,
    hex_grid: Sequence[Tuple[float, float, float]],
    history_grid: Sequence[float],
    window_size: int,
    step: int,
) -> None:
    best_weights, best_history, report = framework.backtester.optimize_parameters(
        hex_weight_grid=hex_grid,
        history_weight_grid=history_grid,
        window_size=window_size,
        step=step,
    )
    print("=== 参数优化 ===")
    print(f"最佳卦象权重: {best_weights}")
    print(f"最佳历史权重: {best_history:.4f}")
    summary = report.summary()
    print("对应回测统计:")
    print(f"  样本期数: {summary['periods']}")
    print(f"  主选命中率: {summary['hit_rate']:.4f}")
    print(f"  号码池命中率: {summary['pool_hit_rate']:.4f}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="梅花易数彩票推理主程序入口")
    parser.add_argument("--config", help="从YAML文件加载参数预设")
    parser.add_argument("--game", choices=["ssq", "dlt", "keno8"], default="ssq", help="玩法类型")
    parser.add_argument("--moving-rule", default="standard", help="动爻生成规则，默认standard")
    parser.add_argument(
        "--hex-weights",
        default="0.5,0.2,0.3",
        help="主/互/变卦权重，逗号分隔，例如0.5,0.2,0.3",
    )
    parser.add_argument(
        "--history-weight",
        type=float,
        default=0.4,
        help="历史频率权重，影响号码评分",
    )
    parser.add_argument(
        "--recency-weight",
        type=float,
        default=0.25,
        help="近期走势权重，用于强调最近开奖变化",
    )
    parser.add_argument(
        "--gap-weight",
        type=float,
        default=0.15,
        help="冷热间隔权重，用于突出久未出现的号码",
    )
    parser.add_argument(
        "--calendar-weight",
        type=float,
        default=0.2,
        help="黄历/农历权重，用于叠加五行与日辰加权",
    )
    parser.add_argument(
        "--history-half-life",
        type=float,
        default=90.0,
        help="历史半衰期(天)，用于控制近期走势的衰减速度",
    )
    parser.add_argument("--max-periods", type=int, default=None, help="读取最近多少期历史数据")
    parser.add_argument("--force-update", action="store_true", help="强制刷新本地缓存")
    parser.add_argument("--offline",
        action="store_true",
        help="仅使用缓存或本地数据，不访问网络更新",
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="忽略系统代理设置，直接访问数据源",
    )
    parser.add_argument("--timestamp", help="起卦时间，格式YYYY-MM-DD或YYYY-MM-DD HH:MM")
    parser.add_argument("--location", default="online", help="事件地点描述，用于扩展起卦因子")
    parser.add_argument("--reference", help="参考号码，逗号分隔，例如1,2,3")
    parser.add_argument(
        "--custom",
        action="append",
        help="自定义因子，支持多次传递，格式key=value",
    )
    parser.add_argument("--guard-sets", type=int, default=0, help="输出守号组合数量，仅限双色球")
    parser.add_argument("--guard-horizon", type=int, default=120, help="守号蓝球评分使用的历史窗口大小")
    parser.add_argument("--guard-blue", type=int, default=5, help="每组守号提供的蓝球备选数量")
    parser.add_argument("--static-weights", action="store_true", help="禁用自动权重推演，使用固定评分参数")
    parser.add_argument("--backtest", action="store_true", help="执行窗口回测")
    parser.add_argument("--optimize", action="store_true", help="执行参数网格搜索")
    parser.add_argument("--auto-optimize", action="store_true", help="预测结束后自动执行一次参数优化")
    parser.add_argument("--evolve", action="store_true", help="使用遗传算法对参数迭代优化")
    parser.add_argument("--evolve-iterations", type=int, default=None, help="遗传算法迭代次数，默认根据推理自动调整")
    parser.add_argument("--evolve-population", type=int, default=None, help="遗传算法种群规模，默认根据推理自动调整")
    parser.add_argument("--window-size", type=int, default=100, help="回测窗口大小")
    parser.add_argument("--window-step", type=int, default=1, help="回测窗口步长")
    parser.add_argument(
        "--opt-hex-grid",
        nargs="*",
        default=["0.5,0.2,0.3", "0.6,0.2,0.2", "0.4,0.3,0.3"],
        help="参数优化时的卦象权重候选，空格分隔多组",
    )
    parser.add_argument(
        "--opt-history-grid",
        nargs="*",
        type=float,
        default=[0.3, 0.4, 0.5],
        help="参数优化时的历史权重候选",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    preliminary, _ = parser.parse_known_args()
    if getattr(preliminary, "config", None):
        config_values = load_config(preliminary.config)
        parser.set_defaults(**config_values)
    args = parser.parse_args()

    hex_weights = parse_hex_weights(args.hex_weights)
    if args.no_proxy:
        os.environ["MEIHUA_DISABLE_PROXY"] = "1"
        print("=== 网络: 忽略系统代理，直接访问数据源 ===")
    else:
        os.environ.pop("MEIHUA_DISABLE_PROXY", None)

    framework = MeihuaInferenceFramework(
        game_type=args.game,
        moving_rule=args.moving_rule,
        hex_weights=hex_weights,
        history_weight=args.history_weight,
        recency_weight=args.recency_weight,
        gap_weight=args.gap_weight,
        calendar_weight=args.calendar_weight,
        history_half_life=args.history_half_life,
        prefer_local_cache=args.offline,
        dynamic_weights=not args.static_weights,
    )

    if args.offline:
        print("=== 模式: 离线，仅使用缓存或本地数据 ===")
    else:
        print("=== 模式: 在线，将按日检查并更新数据 ===")

    framework.update_data(force_update=args.force_update, max_periods=args.max_periods)
    print_history_status(framework)

    event = build_event(args)
    result = framework.predict(event=event)
    present_prediction(framework, result, args, event)

    if args.backtest:
        run_backtest(framework, window_size=args.window_size, step=args.window_step)

    should_optimize = args.optimize or getattr(args, "auto_optimize", False)
    if should_optimize:
        hex_grid = [parse_hex_weights(item) for item in args.opt_hex_grid]
        run_optimization(
            framework,
            hex_grid=hex_grid,
            history_grid=args.opt_history_grid,
            window_size=args.window_size,
            step=args.window_step,
        )

    if args.evolve:
        best_candidate, _ = run_evolution(
            framework,
            iterations=args.evolve_iterations,
            population=args.evolve_population,
            window_size=args.window_size,
            step=args.window_step,
            event=event,
        )
        override = {
            "hex_weights": best_candidate.hex_weights,
            "history_weight": best_candidate.history_weight,
            "recency_weight": best_candidate.recency_weight,
            "gap_weight": best_candidate.gap_weight,
            "calendar_weight": best_candidate.calendar_weight,
            "history_half_life": best_candidate.history_half_life,
            "history_window": best_candidate.history_window,
            "dynamic": False,
        }
        framework.set_parameter_override(override)
        print("=== 应用遗传算法参数重新预测 ===")
        evolved_result = framework.predict(event=event)
        present_prediction(framework, evolved_result, args, event)

if __name__ == "__main__":
    main()
