# 梅花易数推理使用说明

## 1. 快速开始
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   pip install lunardate chinese-calendar
   ```
   第二条用于补齐农历与日历模块，缺失时会有提示。
2. 首次运行会自动下载真实历史开奖数据并写入 `data/meihua_cache/<game>_history.json`。
3. 预测示例：
   ```bash
   python run_meihua.py --game ssq --no-proxy
   ```
   `--no-proxy` 表示直接访问数据源；若希望离线运行，可加入 `--offline`。

## 2. 常用命令行参数
| 参数 | 作用 | 默认值 |
| --- | --- | --- |
| `--config <path>` | 从 YAML 预设加载所有参数，支持布尔/列表 | 无 |
| `--game {ssq,dlt,keno8}` | 选择玩法：双色球 / 大乐透 / 快乐8 | `ssq` |
| `--moving-rule` | 起卦动爻算法，`standard` 最常用 | `standard` |
| `--hex-weights` | 主/互/变卦权重基准，格式 `0.5,0.2,0.3` | `0.5,0.2,0.3` |
| `--history-weight` | 历史频率权重基准（0.25~0.45） | `0.4` |
| `--recency-weight` | 近期走势权重基准（0.2~0.35） | `0.25` |
| `--gap-weight` | 冷热间隔权重基准（0.1~0.2） | `0.15` |
| `--calendar-weight` | 农历/月相权重基准（0.15~0.35） | `0.2` |
| `--history-half-life` | 历史半衰期(天)，越小越强调近期 | `90` |
| `--max-periods` | 限定读取的历史期数，0 表示全部 | 无 |
| `--static-weights` | 禁用动态推演，完全使用基准参数 | 关闭 |
| `--timestamp` | 指定起卦时间（`YYYY-MM-DD[ HH:MM]`） | 当前 UTC |
| `--reference` | 手动参考号码列表 `1,2,3` | 无 |
| `--custom key=value` | 自定义因子，可多次出现 | 无 |
| `--guard-sets` | 输出守号数量（0 关闭，支持 ssq/keno8） | `0` |
| `--guard-horizon` | 守号使用的历史窗口（天） | `120` |
| `--guard-blue` | 守号蓝球备选数量（仅双色球有效） | `5` |
| `--backtest` | 启用滑动窗口回测 | 关闭 |
| `--window-size` / `--window-step` | 回测窗口长度 / 步长 | `100` / `1` |
| `--optimize` | 执行参数网格搜索 | 关闭 |
| `--auto-optimize` | 推理后立即执行一次参数优化 | 关闭 |
| `--opt-hex-grid` / `--opt-history-grid` | 网格搜索候选列表 | 见默认 |
| `--evolve` | 启用遗传算法迭代权重 | 关闭 |
| `--evolve-iterations` | 遗传算法迭代次数 | 自动（推理） |
| `--evolve-population` | 遗传算法种群规模 | 自动（推理） |

> 提示：命令行提供的是“基准值”。若未加 `--static-weights`，程序会根据卦象、农历、月相自动调节最终权重与半衰期。

## 3. 动态推演设计
- **号码元素不再固定分段。** 依据起卦结果、天干地支生命盘、当日黄历的宜忌元素动态生成五行序列，再循环映射到全部号码。每次推理前都会重新计算，避免“一号永远属木”的刻板划分。
- **基准值自适应。** 命令行或配置文件中的权重/半衰期仅作为初始种子，实际推理会结合当日天象、月相、动爻和宜忌重新推导基础参数，再在此基础上叠加动态修正。
- **权重由易数推理驱动。**
  - 动爻越多，变卦权重越高；静卦则偏重主卦。
  - 月相越接近圆满，近期走势权重会增加；朔月阶段则强调历史沉淀与冷号。
  - 黄历宜用元素越多，农历权重越大；若当日忌冲明显，则会降低该元素关联号码的评分。
  - 历史半衰期随月相与宜忌动态调整，默认落在 15~1.5×基准半衰期之间。
- **元信息可查看实际生效权重。** 在预测输出的 `history_weights` 字段中，`frequency/recency/gap/calendar` 为动态权重，`base_*` 字段记录基准值，便于对比调整幅度。

## 4. 守号与快乐8支持
- `--guard-sets` 现支持双色球与快乐8：
  - 双色球：输出固定红球组合 + 多个蓝球备选，蓝球热度会参照 `guard_horizon` 期蓝球历史。
  - 快乐8：每组守号含 10 个主号以及 `reserve` 候补池，便于轮换投注。
- 守号评分会考虑：卦象偏好元素、农历宜忌、月相偏好数字，以及邻号惩罚，帮助兼顾“玄学”与历史统计。

## 5. 配置文件（YAML）
- 示例：
  ```bash
  python run_meihua.py --config configs/meihua_sample.yaml
  ```
- `configs/meihua_sample.yaml`：注释解释每个参数，适合双色球守号与自动优化。
- `configs/meihua_keno8.yaml`：针对快乐8，提供 10 号守号的默认设置。
- 所有布尔值、列表都可直接写在 YAML 中；破折号键名会自动转为命令行所需的下划线形式。

## 6. 回测与网格优化
1. 开启窗口回测：
   ```bash
   python run_meihua.py --game ssq --backtest --window-size 180 --window-step 3
   ```
   输出样本命中率与候选池命中率。
2. 自动优化：
   ```bash
   python run_meihua.py --game keno8 --auto-optimize
   ```
   会在预测后使用 `opt_hex_grid` + `opt_history_grid` 网格搜索，返回最佳权重组合。
3. 若需手动扩展网格范围，可在配置文件中追加新的候选条目。

## 7. 遗传算法迭代
- 运行示例：`python run_meihua.py --game ssq --evolve --window-size 180 --window-step 3`。
- 默认会由推理框架推导迭代次数与种群规模；通过 `--evolve-iterations`、`--evolve-population` 可覆盖推理结果。
- 推理输出会展示变异强度、交叉中心与历史窗口范围，方便跟踪算法序列的推导依据。
- GA 以回测命中率 + 候选池命中率为目标自动搜索参数，其结果会打印最佳权重与对应回测统计，可直接写回配置文件。
- 遗传算法阶段会固定使用守号推理链路（关闭动态权重），从而快速筛选下一轮的守号基准，再配合正式推理应用实时的天文/农历调节。

## 8. 数据缓存说明
- 缓存位于 `data/meihua_cache/<game>_history.json`，每日自动校验最新开奖日期。
- `--force-update` 强制刷新；`--offline` 会跳过网络请求，仅依赖缓存或本地数据集。
- 需要绕过系统代理时可使用 `--no-proxy` 或环境变量 `MEIHUA_DISABLE_PROXY=1`。

## 9. 故障排查
- **农历或黄历信息缺失**：确认 `lunardate`、`chinese-calendar` 已安装；若依然失败，相关字段会给出具体提示。
- **网络超时或数据源异常**：可切换到 `--offline` 或重试 `--force-update --no-proxy`。
- **编码问题**：Windows PowerShell 建议执行 `chcp 65001` 切换至 UTF-8，再运行脚本。

## 10. 参数调节建议
- 想“守冷号”可提高 `gap_weight` 或缩短半衰期；若期望更贴近近期走势，可增大 `recency_weight` 并让 `history_half_life` 较小。
- 想显著放大农历影响，可提高 `calendar_weight` 或关闭 `--static-weights` 让动态推演自动加权。
- 快乐8 由于一次开出 20 个号，推荐 `window_size` ≥ 150，并定期检查守号 `reserve` 列表轮换。

希望新的动态推演机制能更贴合“玄学推理”思路：历史数据提供确定性的底座，而卦象、月相、农历则在每次预测中实时调节参数，帮助你挑出最契合当日时机的号码组合。祝好运！
