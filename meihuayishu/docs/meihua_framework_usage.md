# 梅花易数推理框架使用说明

## 数据准备
- 将最新的开奖记录放入 data/raw/ 目录，目前脚本默认识别 kl8_asc.txt（快乐8）和 ssq_asc.txt（双色球）。
- 首次运行或需要刷新时，可以在主程序中带上 --force-update，缓存会写入 data/meihua_cache/。
- 如需限制历史长度，可通过 --max-periods 指定读取最近多少期数据。

## 主程序入口（run_meihua.py）
- 查看所有参数：
  `ash
  python run_meihua.py --help
  `
- 常用参数说明：
  - --game {ssq,dlt,keno8}：选择玩法，默认 ssq；
  - --hex-weights、--history-weight：调整卦象与历史权重；
  - --timestamp、--reference、--custom key=value：自定义起卦上下文；
  - --backtest / --optimize：启用回测或参数搜索；
  - --window-size、--window-step：控制回测窗口。
- 示例：
  `ash
  python run_meihua.py --game ssq --max-periods 200 --force-update \
      --timestamp "2024-09-30 20:00" --reference 3,8,11,16,22,27 \
      --custom mood=calm --custom event=release
  `
  脚本将输出主选号码、候选池、评分Top5以及卦象元信息。

## 回测与参数优化
- 回测：加上 --backtest 即会使用滑动窗口输出命中率统计；
- 参数搜索：在 --optimize 的同时，可通过 --opt-hex-grid、--opt-history-grid 指定候选集合，例如：
  `ash
  python run_meihua.py --game keno8 --optimize --backtest \
      --opt-hex-grid 0.5,0.2,0.3 0.45,0.25,0.3 \
      --opt-history-grid 0.3 0.35 0.4
  `
  完成后会打印最佳参数及对应的回测指标。

## 单元测试
- 如需验证核心逻辑，可运行：
  `ash
  pytest meihuayishu/tests/iching/test_meihua_framework.py
  `
- 该测试覆盖历史数据解析、起卦与候选池生成等核心路径。

